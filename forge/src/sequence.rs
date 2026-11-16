//! The whole build in order (pass 3b): foundation; then each storey's walls raised group by
//! group (facades, end walls, spine rows, stair walls), every panel tilted up in sim-core; cap
//! plates and then the floor (or roof) set onto what's built. Writes `../out/pass3/build.json`
//! and the frames of the animation (`../out/pass3/build_frames/`).

use std::path::Path;

use cortenforge::mesh::types::IndexedMesh;
use nalgebra::{Point3, Unit, UnitQuaternion, Vector3};
use serde_json::{Value, json};

use crate::apartment::Building;
use crate::build::{Landing, gravity_torque, set_down, tilt_up};
use crate::framing::{Group, Kind, Member, Panel};
use crate::render::{self, Layer, Style, View};

pub struct Settings {
    pub density: f64,
    pub osb_kgm2: f64,
    pub crew_lbf: f64,
    pub crew_max: f64,
}

impl Settings {
    pub fn from_json(v: &Value) -> Self {
        let b = &v["build"];
        let g = |k: &str| b[k].as_f64().unwrap_or_else(|| panic!("frame.json build.{k}: run `uv run brownfield frame`"));
        Settings { density: g("wood_density_kgm3"), osb_kgm2: g("osb_kgm2"), crew_lbf: g("crew_lift_lbf"), crew_max: g("crew_max") }
    }
}

const LBF: f64 = 4.448222;

/// The panel's boxes with their densities (sheathing too, when `sheathed` and it has some).
fn panel_boxes(members: &[Member], p: &Panel, st: &Settings, sheathed: bool) -> Vec<(Vector3<f64>, Vector3<f64>, f64)> {
    let mut boxes: Vec<_> = members.iter().filter(|m| m.panel == Some(p.id))
        .flat_map(|m| m.boxes.iter().map(|(lo, hi)| (*lo, *hi, st.density))).collect();
    if let (true, Some((lo, hi))) = (sheathed, p.sheathing) {
        let t = (hi - lo).min() / 1e3;
        boxes.push((lo, hi, st.osb_kgm2 / t));
    }
    boxes
}

/// Draws the build as it stands: `placed` members fixed, the `moving` panels turned `deg` from
/// their place (90 = flat on the deck). The finished building's corners go into every frame as
/// bare vertices, so all frames share one scale and framing.
fn draw_state(members: &[Member], panels: &[Panel], placed: &[bool], moving: &[usize], deg: f64, corners: &[Vector3<f64>], path: &Path) -> std::io::Result<()> {
    let layer_of = |k: Kind| match k {
        Kind::Footing | Kind::Stem | Kind::Slab => 0,
        Kind::Header => 2,
        Kind::Rim => 3,
        Kind::FloorJoist | Kind::RoofJoist => 4,
        _ => 1,
    };
    let colours = [[0.66, 0.66, 0.64], [0.84, 0.70, 0.50], [0.62, 0.42, 0.26], [0.55, 0.45, 0.35], [0.92, 0.82, 0.62], [0.0, 0.0, 0.0]];
    let mut meshes: Vec<IndexedMesh> = (0..6).map(|_| IndexedMesh::new()).collect();
    for (i, m) in members.iter().enumerate() {
        if placed[i] {
            m.append_mesh(&mut meshes[layer_of(m.kind)]);
        } else if let Some(p) = m.panel.filter(|id| moving.contains(id)) {
            let pan = &panels[p];
            let rot = UnitQuaternion::from_axis_angle(&Unit::new_normalize(pan.axis), deg.to_radians());
            m.append_mesh_moved(&mut meshes[layer_of(m.kind)], &rot, &pan.pivot, &Vector3::zeros());
        }
    }
    meshes[5].vertices.extend(corners.iter().map(|c| Point3::from(*c)));
    let layers: Vec<Layer> = meshes.iter().zip(colours).filter(|(m, _)| !m.vertices.is_empty()).map(|(m, c)| Layer::solid(m, c)).collect();
    render::render_styled(&layers, &[View::looking(Vector3::new(0.8, 0.5, -0.35), Vector3::z())], 0.02, path, Style::pretty())?;
    Ok(())
}

/// Sets the `stage` members down on what's placed (only placed members near their level take
/// part, less any `exclude`d).
fn set_stage(members: &[Member], placed: &[bool], stage: &[usize], st: &Settings, exclude: &dyn Fn(&Member) -> bool) -> Landing {
    let zmin = stage.iter().map(|&i| members[i].bounds().0.z).fold(f64::INFINITY, f64::min);
    let zmax = stage.iter().map(|&i| members[i].bounds().1.z).fold(f64::NEG_INFINITY, f64::max);
    let statics: Vec<_> = members.iter().enumerate()
        .filter(|(i, m)| placed[*i] && !exclude(m) && m.bounds().1.z > zmin - 60.0 && m.bounds().0.z < zmax)
        .flat_map(|(_, m)| m.boxes.clone()).collect();
    let bodies: Vec<_> = stage.iter().map(|&i| members[i].boxes.clone()).collect();
    set_down(&statics, &bodies, st.density, 10.0, 0.4)
}

pub fn run(root: &Path, b: &Building, members: &[Member], panels: &[Panel], st: &Settings) -> std::io::Result<()> {
    let t_all = std::time::Instant::now();
    let frames = root.join("out/pass3/build_frames");
    let _ = std::fs::remove_dir_all(&frames);
    std::fs::create_dir_all(&frames)?;
    let mut placed: Vec<bool> = members.iter().map(|m| m.kind.concrete()).collect();
    let (mut lo, mut hi) = (Vector3::repeat(f64::INFINITY), Vector3::repeat(f64::NEG_INFINITY));
    for m in members {
        let (a, c) = m.bounds();
        lo = lo.inf(&a);
        hi = hi.sup(&c);
    }
    let corners: Vec<Vector3<f64>> = (0..8)
        .map(|k| Vector3::new(if k & 1 == 0 { lo.x } else { hi.x }, if k & 2 == 0 { lo.y } else { hi.y }, if k & 4 == 0 { lo.z } else { hi.z }))
        .collect();
    let mut frame = 0usize;
    let mut snap = |placed: &[bool], moving: &[usize], deg: f64| -> std::io::Result<()> {
        draw_state(members, panels, placed, moving, deg, &corners, &frames.join(format!("f{frame:03}.png")))?;
        frame += 1;
        Ok(())
    };
    snap(&placed, &[], 0.0)?;

    let mut lifts = Vec::new();
    let mut stages = Vec::new();
    let mut negative = Value::Null;
    for storey in 1..=b.storeys {
        // Walls: each group of panels framed flat and raised; the simulation lifts every panel.
        for group in [Group::Facade, Group::EndWall, Group::Spine, Group::Stair] {
            let ids: Vec<usize> = panels.iter().filter(|p| p.storey == storey && p.group == group).map(|p| p.id).collect();
            let t0 = std::time::Instant::now();
            for &id in &ids {
                let p = &panels[id];
                let framed = panel_boxes(members, p, st, false);
                let boxes = panel_boxes(members, p, st, true);
                let lift = tilt_up(&boxes, &p.pivot, &p.axis, 20.0);
                let flat = gravity_torque(&boxes, &p.pivot, &p.axis, std::f64::consts::FRAC_PI_2).abs();
                let framed_flat = gravity_torque(&framed, &p.pivot, &p.axis, std::f64::consts::FRAC_PI_2).abs();
                let framed_kg: f64 = framed.iter().map(|(a, c, r)| r * (c - a).product() / 1e9).sum();
                let force = lift.peak_torque / lift.height_m / LBF;
                let crew = (force / st.crew_lbf).ceil();
                lifts.push(json!({
                    "panel": id, "storey": storey, "group": group.name(), "length_m": p.length_mm / 1e3,
                    "framed_kg": framed_kg, "kg": lift.mass_kg, "sheathed": p.sheathing.is_some(),
                    "peak_servo_nm": lift.peak_torque, "statics_flat_nm": flat, "framed_flat_nm": framed_flat,
                    "height_m": lift.height_m, "lift_lbf": force, "framed_lift_lbf": framed_flat / lift.height_m / LBF,
                    "crew": crew, "jack": crew > st.crew_max, "upright_err_deg": lift.final_angle_err,
                }));
            }
            let secs = t0.elapsed().as_secs_f64();
            for deg in [90.0, 60.0, 30.0] {
                snap(&placed, &ids, deg)?;
            }
            for (i, m) in members.iter().enumerate() {
                if m.panel.is_some_and(|p| ids.contains(&p)) {
                    placed[i] = true;
                }
            }
            snap(&placed, &[], 0.0)?;
            println!("storey {storey} {}: {} panels raised ({secs:.1} s)", group.name(), ids.len());
        }
        // Cap plates, then the floor (or roof) on top.
        let caps: Vec<usize> = (0..members.len()).filter(|&i| members[i].storey == storey && members[i].kind == Kind::CapPlate).collect();
        let floor: Vec<usize> = (0..members.len())
            .filter(|&i| members[i].storey == storey && matches!(members[i].kind, Kind::FloorJoist | Kind::RoofJoist | Kind::Rim)).collect();
        let roof = storey == b.storeys;
        for (name, stage) in [("cap plates", caps), (if roof { "roof joists and rims" } else { "floor joists and rims" }, floor)] {
            if storey == 1 && name.starts_with("floor") {
                // Negative control: the same joists with the spine not yet built (out of order).
                let cx = b.depth / 2.0;
                let no_spine = |m: &Member| ((m.bounds().0.x + m.bounds().1.x) / 2.0 - cx).abs() < 150.0 && m.kind != Kind::Rim;
                let t0 = std::time::Instant::now();
                let land = set_stage(members, &placed, &stage, st, &no_spine);
                let fell = land.errors.iter().filter(|e| e.0 > 50.0).count();
                negative = json!({"stage": "storey 1 floor joists with the spine not yet built", "bodies": stage.len(), "fell": fell,
                                  "secs": t0.elapsed().as_secs_f64()});
                println!("  negative control (no spine): {fell} of {} fell ({:.1} s)", stage.len(), t0.elapsed().as_secs_f64());
            }
            let t0 = std::time::Instant::now();
            let land = set_stage(members, &placed, &stage, st, &|_| false);
            let secs = t0.elapsed().as_secs_f64();
            let max_err = land.errors.iter().map(|e| e.0).fold(0.0, f64::max);
            let max_ang = land.errors.iter().map(|e| e.1).fold(0.0, f64::max);
            let off = land.errors.iter().filter(|e| e.0 > 3.0 || e.1 > 0.01).count();
            println!("storey {storey} {name}: {} set, worst {max_err:.2} mm / {max_ang:.4} rad, {off} off their seats, deepest contact {:.2} mm ({secs:.1} s)",
                     stage.len(), land.max_depth_mm);
            stages.push(json!({"storey": storey, "stage": name, "bodies": stage.len(), "max_err_mm": max_err, "max_angle_rad": max_ang,
                               "off_seat": off, "max_depth_mm": land.max_depth_mm, "secs": secs}));
            for &i in &stage {
                placed[i] = true;
            }
            snap(&placed, &[], 0.0)?;
        }
    }
    std::fs::write(root.join("out/pass3/build.json"), serde_json::to_string_pretty(&json!({
        "source": "forge `build` (CortenForge 0.9 sim-core): the walk-up's wood frame, raised and set",
        "density_kgm3": st.density, "osb_kgm2": st.osb_kgm2, "crew_lift_lbf": st.crew_lbf, "crew_max": st.crew_max,
        "lifts": lifts, "stages": stages, "negative_control": negative, "frames": frame,
        "secs": t_all.elapsed().as_secs_f64(),
    }))?)?;
    println!("{frame} frames in out/pass3/build_frames; build.json written ({:.1} s)", t_all.elapsed().as_secs_f64());
    Ok(())
}
