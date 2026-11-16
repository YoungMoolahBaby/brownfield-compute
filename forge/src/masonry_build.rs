//! The block-and-plank walk-up built in order (pass 3b): on the foundation, each storey's courses
//! laid two at a time (lintels as their courses come), the plank course's blocks and fillers, then
//! the planks set by crane: in sim-core each plank is released 10 mm above its bearings as a free
//! body and has to settle onto them. Writes `../out/pass3/build_masonry.json` and the animation's
//! frames (`../out/pass3/build_frames_masonry/`).

use std::path::Path;

use cortenforge::mesh::types::IndexedMesh;
use nalgebra::{Point3, Vector3};
use serde_json::json;

use crate::apartment::Building;
use crate::build::set_down;
use crate::framing::{Kind, Member};
use crate::masonry::Spec;
use crate::render::{self, Layer, Style, View};

fn draw(members: &[Member], placed: &[bool], corners: &[Vector3<f64>], path: &Path) -> std::io::Result<()> {
    let layer_of = |k: Kind| match k { Kind::Footing | Kind::Stem | Kind::Slab => 0, Kind::Block => 1, Kind::Lintel => 2, _ => 3 };
    let colours = [[0.66, 0.66, 0.64], [0.80, 0.78, 0.72], [0.56, 0.55, 0.52], [0.90, 0.90, 0.88], [0.0, 0.0, 0.0]];
    let mut meshes: Vec<IndexedMesh> = (0..5).map(|_| IndexedMesh::new()).collect();
    for (i, m) in members.iter().enumerate() {
        if placed[i] {
            m.append_mesh(&mut meshes[layer_of(m.kind)]);
        }
    }
    meshes[4].vertices.extend(corners.iter().map(|c| Point3::from(*c)));
    let layers: Vec<Layer> = meshes.iter().zip(colours).filter(|(m, _)| !m.vertices.is_empty()).map(|(m, c)| Layer::solid(m, c)).collect();
    render::render_styled(&layers, &[View::looking(Vector3::new(0.8, 0.5, -0.35), Vector3::z())], 0.02, path, Style::pretty())?;
    Ok(())
}

pub fn run(root: &Path, b: &Building, s: &Spec, members: &[Member]) -> std::io::Result<()> {
    let t_all = std::time::Instant::now();
    let frames = root.join("out/pass3/build_frames_masonry");
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
    let mut snap = |placed: &[bool]| -> std::io::Result<()> {
        draw(members, placed, &corners, &frames.join(format!("f{frame:03}.png")))?;
        frame += 1;
        Ok(())
    };
    snap(&placed)?;
    let per = s.per_storey();
    let mut levels = Vec::new();
    let mut courses_laid = Vec::new();
    for storey in 1..=b.storeys {
        // Courses, two at a time (a course's lintels with it).
        let base = (storey - 1) * per;
        let mut k = 0;
        while k < s.courses {
            for (i, m) in members.iter().enumerate() {
                if let Some(c) = m.panel.filter(|_| matches!(m.kind, Kind::Block | Kind::Lintel)) {
                    if c >= base + k && c < base + (k + 2).min(s.courses) {
                        placed[i] = true;
                    }
                }
            }
            snap(&placed)?;
            k += 2;
        }
        let blocks: usize = members.iter().filter(|m| m.storey == storey && m.kind == Kind::Block).count();
        let lintels: usize = members.iter().filter(|m| m.storey == storey && m.kind == Kind::Lintel).count();
        courses_laid.push(json!({"storey": storey, "block_pieces": blocks, "lintels": lintels}));
        // The plank course's blocks and fillers, then the planks.
        for (i, m) in members.iter().enumerate() {
            if m.kind == Kind::Block && m.panel == Some(base + s.courses) {
                placed[i] = true;
            }
        }
        let planks: Vec<usize> = (0..members.len()).filter(|&i| members[i].kind == Kind::Plank && members[i].storey == storey).collect();
        let zmin = planks.iter().map(|&i| members[i].bounds().0.z).fold(f64::INFINITY, f64::min);
        // What the planks bear on: placed pieces whose tops are at the planks' underside, under a plank.
        let near = |m: &Member| -> bool {
            let (mlo, mhi) = m.bounds();
            mhi.z > zmin - 2.0 && mhi.z < zmin + 1.0 && planks.iter().any(|&p| {
                let (plo, phi) = members[p].bounds();
                mlo.x < phi.x + 10.0 && mhi.x > plo.x - 10.0 && mlo.y < phi.y + 10.0 && mhi.y > plo.y - 10.0
            })
        };
        let statics: Vec<_> = members.iter().enumerate().filter(|(i, m)| placed[*i] && near(m)).flat_map(|(_, m)| m.boxes.clone()).collect();
        let bodies: Vec<_> = planks.iter().map(|&i| members[i].boxes.clone()).collect();
        let densities = vec![s.plank_density; planks.len()];
        let t0 = std::time::Instant::now();
        let land = set_down(&statics, &bodies, &densities, 10.0, 0.4);
        let secs = t0.elapsed().as_secs_f64();
        let max_err = land.errors.iter().map(|e| e.0).fold(0.0, f64::max);
        let off = land.errors.iter().filter(|e| e.0 > 3.0 || e.1 > 0.01).count();
        let heaviest = planks.iter().map(|&i| members[i].volume_m3() * s.plank_density).fold(0.0, f64::max);
        println!("storey {storey}: {blocks} block pieces and {lintels} lintels laid; {} planks set on {} bearing pieces, worst {max_err:.2} mm, {off} off their bearings, deepest contact {:.2} mm ({secs:.1} s)",
                 planks.len(), statics.len(), land.max_depth_mm);
        levels.push(json!({"storey": storey, "planks": planks.len(), "bearing_boxes": statics.len(), "max_err_mm": max_err, "off_seat": off,
                           "max_depth_mm": land.max_depth_mm, "heaviest_kg": heaviest, "secs": secs}));
        for &i in &planks {
            placed[i] = true;
        }
        snap(&placed)?;
    }
    // Out of order: the second floor's planks with the spine wall's top two courses not yet laid.
    let planks: Vec<usize> = (0..members.len()).filter(|&i| members[i].kind == Kind::Plank && members[i].storey == 1).collect();
    let zmin = planks.iter().map(|&i| members[i].bounds().0.z).fold(f64::INFINITY, f64::min);
    let cx = b.depth / 2.0;
    let statics: Vec<_> = members.iter().filter(|m| {
        let (mlo, mhi) = m.bounds();
        m.kind == Kind::Block && m.storey == 1 && mhi.z > zmin - 2.0 && mhi.z < zmin + 1.0 && !(mlo.x < cx && mhi.x > cx)
    }).flat_map(|m| m.boxes.clone()).collect();
    let bodies: Vec<_> = planks.iter().map(|&i| members[i].boxes.clone()).collect();
    let land = set_down(&statics, &bodies, &vec![s.plank_density; planks.len()], 10.0, 0.4);
    let fell = land.errors.iter().filter(|e| e.0 > 50.0).count();
    println!("  negative control (spine not up): {fell} of {} planks fell", planks.len());

    std::fs::write(root.join("out/pass3/build_masonry.json"), serde_json::to_string_pretty(&json!({
        "source": "forge `build masonry` (CortenForge 0.9 sim-core): the walk-up in block and hollow-core planks, laid and set",
        "plank_kg": s.plank_kg, "block_kg": s.block_kg, "levels": levels, "courses": courses_laid,
        "negative_control": {"stage": "second-floor planks with the spine wall not yet up", "bodies": planks.len(), "fell": fell},
        "frames": frame, "secs": t_all.elapsed().as_secs_f64(),
    }))?)?;
    println!("{frame} frames in out/pass3/build_frames_masonry; build_masonry.json written ({:.1} s)", t_all.elapsed().as_secs_f64());
    Ok(())
}
