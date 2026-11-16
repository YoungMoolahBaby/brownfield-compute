//! `cargo run --release -- <mode>` (from `forge/`)
//!
//! - `check` (default): CortenForge's measurements of the house against its exact dimensions.
//! - `house`: the first house, built, measured and drawn: `../out/pass3/house.json` (the envelope
//!   the heat model reads) and `../docs/pass3/house.png`.
//! - `apartment`: the 12-flat walk-up (pass 3b), built, measured and drawn:
//!   `../out/pass3/apartment.json` (every flat's envelope) and `../docs/pass3/apartment.png`.
//! - `meshers`: CortenForge's uniform-grid mesher against its parallel adaptive one (time, triangles,
//!   enclosed volume).

mod apartment;
mod house;
mod render;

use std::path::Path;
use std::time::Instant;

use cortenforge::cf_design::Solid;
use cortenforge::cf_design::mechanism::mass::mass_properties;
use cortenforge::mesh::types::IndexedMesh;
use nalgebra::Vector3;
use serde_json::json;

use house::House;
use render::{Layer, Style, View};

/// Volume (m3) of a solid in mm, by CortenForge's grid integration at `cell` mm.
fn volume_m3(solid: &Solid, cell: f64) -> f64 {
    // mass_properties takes kg/m3 and mm; at 1000 kg/m3 the mass in kg is the volume in litres.
    mass_properties(solid, 1000.0, cell).map_or(0.0, |m| m.mass / 1000.0)
}

fn check() -> bool {
    let h = House::example();
    let mut ok = true;
    let mut test = |name: &str, got: f64, want: f64, tol: f64| {
        let err = (got - want) / want;
        let pass = err.abs() <= tol;
        ok &= pass;
        println!("{} {name}: CortenForge {got:.3}, exact {want:.3} ({:+.2}%, tolerance {:.1}%)",
                 if pass { "ok  " } else { "FAIL" }, 100.0 * err, 100.0 * tol);
    };
    let t = Instant::now();
    test("interior volume, m3 (50 mm cells)", volume_m3(&h.interior(), 50.0), h.interior_volume_m3(), 0.005);
    // Walls are 178 mm thick: thin against the cells, so cf-design's partial-cell weighting reads a
    // little heavy at coarse cells (custom-skate's finding); 25 mm cells.
    test("wall volume, m3 (25 mm cells)", volume_m3(&h.walls(), 25.0), h.wall_volume_m3(), 0.02);
    let slab_exact = h.width * h.length * h.slab_t / 1e9;
    test("slab volume, m3 (25 mm cells)", volume_m3(&h.slab(), 25.0), slab_exact, 0.02);
    let b = apartment::Building::example();
    test("apartment exterior walls, m3 (50 mm cells)", volume_m3(&b.exterior_walls(), 50.0), b.exterior_wall_volume_m3(), 0.02);
    test("apartment floor systems, m3 (50 mm cells)", volume_m3(&b.floors(), 50.0), b.floors_volume_m3(), 0.01);
    println!("({:.1} s)", t.elapsed().as_secs_f64());
    ok
}

fn apartment_mode(root: &Path) -> std::io::Result<()> {
    let b = apartment::Building::example();
    let t = Instant::now();
    let parts = [
        (mesh_of(&b.ground_slab(), 40.0), [0.62, 0.62, 0.60], 0.0),
        (mesh_of(&b.exterior_walls(), 40.0), [0.80, 0.70, 0.58], 0.0),
        (mesh_of(&b.party_walls(), 40.0), [0.70, 0.70, 0.68], 0.0),
        (mesh_of(&b.floors(), 40.0), [0.66, 0.60, 0.52], 0.0),
        (mesh_of(&b.roof(), 40.0), [0.30, 0.30, 0.32], 0.0),
        (mesh_of(&b.glass(), 15.0), [0.45, 0.62, 0.80], 0.6),
        (mesh_of(&b.doors(), 15.0), [0.48, 0.34, 0.22], 0.0),
    ];
    println!("meshed in {:.1} s", t.elapsed().as_secs_f64());
    let layers: Vec<Layer> = parts.iter().map(|(m, c, sp)| Layer::solid(m, *c).with_spec(*sp)).collect();
    let views = [
        View::looking(Vector3::new(0.8, 0.5, -0.25), Vector3::z()),
        View::looking(Vector3::x(), Vector3::z()),
        View::looking(Vector3::y(), Vector3::z()),
    ];
    std::fs::create_dir_all(root.join("docs/pass3"))?;
    let (w, h) = render::render_styled(&layers, &views, 0.025, &root.join("docs/pass3/apartment.png"), Style::pretty())?;
    println!("drew docs/pass3/apartment.png ({w} x {h})");
    let flats: Vec<_> = b.flats.iter().map(|f| b.flat_envelope(f)).collect();
    let env = json!({
        "source": "forge `apartment` (CortenForge 0.9): 3-storey walk-up, 100 x 40 ft, 12 flats",
        "depth_m": b.depth / 1e3, "length_m": b.length / 1e3, "storeys": b.storeys, "storey_m": b.storey / 1e3,
        "frontage_per_flat_m": b.length / 1e3 / b.flats.len() as f64,
        "flats": flats,
    });
    std::fs::create_dir_all(root.join("out/pass3"))?;
    std::fs::write(root.join("out/pass3/apartment.json"), serde_json::to_string_pretty(&env)?)?;
    for f in env["flats"].as_array().into_iter().flatten() {
        println!("{:>16}: floor {:.1} m2, wall net {:.1} m2, glazed {:.1} m2, roof {:.1} m2, slab edge {:.1} m",
                 f["name"].as_str().unwrap_or(""), f["floor_m2"].as_f64().unwrap_or(0.0), f["wall_net_m2"].as_f64().unwrap_or(0.0),
                 f["glazed_m2"].as_f64().unwrap_or(0.0), f["ceiling_m2"].as_f64().unwrap_or(0.0), f["slab_perimeter_m"].as_f64().unwrap_or(0.0));
    }
    Ok(())
}

/// CortenForge's parallel adaptive octree mesher: `mesh` (a uniform grid) took 63 min on the walk-up,
/// this ~3 min (`meshers` mode).
fn mesh_of(s: &Solid, tol: f64) -> IndexedMesh {
    s.mesh_adaptive_par(tol).geometry
}

fn mesh_uniform(s: &Solid, tol: f64) -> IndexedMesh {
    s.mesh(tol).geometry
}

/// Volume enclosed by a closed triangle mesh in mm (divergence theorem), in m3.
fn mesh_volume_m3(m: &IndexedMesh) -> f64 {
    m.faces.iter().map(|f| {
        let [a, b, c] = f.map(|i| m.vertices[i as usize].coords);
        a.dot(&b.cross(&c)) / 6.0
    }).sum::<f64>() / 1e9
}

fn house(root: &Path) -> std::io::Result<()> {
    let h = House::example();
    let t = Instant::now();
    let (slab, walls, gables, roof, glass, doors) =
        (mesh_of(&h.slab(), 25.0), mesh_of(&h.walls(), 25.0), mesh_of(&h.gables(), 25.0), mesh_of(&h.roof(), 25.0),
         mesh_of(&h.glass(), 10.0), mesh_of(&h.doors(), 10.0));
    println!("meshed in {:.1} s ({} wall triangles)", t.elapsed().as_secs_f64(), walls.faces.len());

    let layers = [
        Layer::solid(&slab, [0.62, 0.62, 0.60]),
        Layer::solid(&walls, [0.86, 0.82, 0.74]),
        Layer::solid(&gables, [0.86, 0.82, 0.74]),
        Layer::solid(&roof, [0.36, 0.30, 0.28]),
        Layer::solid(&glass, [0.45, 0.62, 0.80]).with_spec(0.6),
        Layer::solid(&doors, [0.48, 0.34, 0.22]),
    ];
    let views = [
        View::looking(Vector3::new(0.8, 0.5, -0.22), Vector3::z()), // three-quarter, front-left, low
        View::looking(Vector3::x(), Vector3::z()),                     // the front, looking at x = 0
        View::looking(-Vector3::x(), Vector3::z()),                    // the back
        View::looking(Vector3::y(), Vector3::z()),                     // the left end
    ];
    std::fs::create_dir_all(root.join("docs/pass3"))?;
    let (w, ht) = render::render_styled(&layers, &views, 0.045, &root.join("docs/pass3/house.png"), Style::pretty())?;
    println!("drew docs/pass3/house.png ({w} x {ht})");

    let env = json!({
        "source": "forge `house` (CortenForge 0.9), the D1 example house",
        "width_m": h.width / 1e3, "length_m": h.length / 1e3, "wall_height_m": h.wall_height / 1e3,
        "wall_thickness_m": h.wall_t / 1e3, "pitch": h.pitch, "overhang_m": h.overhang / 1e3,
        "floor_m2": h.floor_m2(), "interior_volume_m3": h.interior_volume_m3(),
        "wall_gross_m2": h.wall_gross_m2(), "wall_net_m2": h.wall_net_m2(),
        "glazed_m2": h.glazed_area_m2(), "door_m2": h.door_area_m2(),
        "ceiling_m2": h.ceiling_m2(), "slab_perimeter_m": h.slab_perimeter_m(),
        "openings": h.openings.iter().map(|o| json!({"name": o.name, "wall": format!("{:?}", o.wall),
            "width_m": o.width / 1e3, "height_m": o.height / 1e3, "glazed": o.glazed})).collect::<Vec<_>>(),
    });
    std::fs::create_dir_all(root.join("out/pass3"))?;
    std::fs::write(root.join("out/pass3/house.json"), serde_json::to_string_pretty(&env)?)?;
    println!("{}", serde_json::to_string_pretty(&env)?);
    Ok(())
}

fn main() {
    let root = Path::new("..");
    let mode = std::env::args().nth(1).unwrap_or_else(|| "check".into());
    match mode.as_str() {
        "check" => {
            let ok = check();
            println!("check: {}", if ok { "passed" } else { "FAILED" });
            if !ok {
                std::process::exit(1);
            }
        }
        "house" => {
            if let Err(e) = house(root) {
                eprintln!("{e}");
                std::process::exit(1);
            }
        }
        "probe" => {
            let h = House::example();
            let (w, l, ht, t) = (h.width, h.length, h.wall_height, h.wall_t);
            let shell_exact = (w * l - (w - 2.0 * t) * (l - 2.0 * t)) * ht / 1e9;
            let outer = Solid::cuboid(Vector3::new(w, l, ht) / 2.0).translate(Vector3::new(w, l, ht) / 2.0);
            // A cutter flush to 1 mm (what found the problem), then one overshooting by a metre.
            let inner = Solid::cuboid(Vector3::new(w - 2.0 * t, l - 2.0 * t, ht + 2.0) / 2.0).translate(Vector3::new(w, l, ht) / 2.0);
            let deep = Solid::cuboid(Vector3::new(w - 2.0 * t, l - 2.0 * t, ht + 2000.0) / 2.0).translate(Vector3::new(w, l, ht) / 2.0);
            for cell in [50.0, 25.0] {
                println!("cell {cell}: flush cutter {:.3}, overshooting cutter {:.3}, exact {shell_exact:.3}",
                         volume_m3(&outer.clone().subtract(inner.clone()), cell), volume_m3(&outer.clone().subtract(deep.clone()), cell));
            }
            let shell = outer.clone().subtract(inner.clone());
            let pts = [(t / 2.0, l / 2.0, ht / 2.0, -t / 2.0), (w / 2.0, l / 2.0, ht / 2.0, w / 2.0 - t),
                       (-100.0, l / 2.0, ht / 2.0, 100.0), (t + 10.0, l / 2.0, ht / 2.0, 10.0),
                       (t / 2.0, l / 2.0, 30.0, -30.0), (t / 2.0, l / 2.0, -30.0, 30.0),
                       (t / 2.0, l / 2.0, ht - 30.0, -30.0), (t / 2.0, l / 2.0, ht + 30.0, 30.0)];
            for (x, y, z, want) in pts {
                let p = nalgebra::Point3::new(x, y, z);
                println!("at ({x:.0}, {y:.0}, {z:.0}): shell {:.2}, outer {:.2}, inner {:.2}; expected shell {want:.2}",
                         shell.evaluate(&p), outer.evaluate(&p), inner.evaluate(&p));
            }
            for cell in [50.0, 25.0, 12.5] {
                let shell = volume_m3(&outer.clone().subtract(inner.clone()), cell);
                println!("cell {cell}: shell {shell:.3} vs exact {shell_exact:.3} ({:+.2}%), walls {:.3} vs {:.3}",
                         100.0 * (shell / shell_exact - 1.0), volume_m3(&h.walls(), cell), h.wall_volume_m3());
            }
        }
        "meshers" => {
            // The uniform-grid mesher (`mesh`) against the parallel adaptive octree (`mesh_adaptive_par`):
            // time, triangles and the enclosed volume, on the house's walls and the walk-up's layers.
            let h = House::example();
            let b = apartment::Building::example();
            let cases: [(&str, Solid, f64, Option<f64>, bool); 5] = [
                ("house walls", h.walls(), 25.0, Some(h.wall_volume_m3()), true),
                ("house glass", h.glass(), 10.0, None, true),
                ("walk-up exterior walls", b.exterior_walls(), 40.0, Some(b.exterior_wall_volume_m3()), false),
                ("walk-up floor systems", b.floors(), 40.0, Some(b.floors_volume_m3()), false),
                ("walk-up glass", b.glass(), 15.0, None, false),
            ];
            for (name, s, tol, exact, uniform_too) in cases {
                let ex = exact.map_or(String::new(), |e| format!(", exact {e:.3} m3"));
                if uniform_too {
                    let t = Instant::now();
                    let m = mesh_uniform(&s, tol);
                    println!("{name} at {tol} mm, uniform: {:.1} s, {} triangles, {:.3} m3{ex}",
                             t.elapsed().as_secs_f64(), m.faces.len(), mesh_volume_m3(&m));
                }
                let t = Instant::now();
                let m = mesh_of(&s, tol);
                println!("{name} at {tol} mm, adaptive parallel: {:.1} s, {} triangles, {:.3} m3{ex}",
                         t.elapsed().as_secs_f64(), m.faces.len(), mesh_volume_m3(&m));
            }
        }
        "apartment" => {
            if let Err(e) = apartment_mode(root) {
                eprintln!("{e}");
                std::process::exit(1);
            }
        }
        other => {
            eprintln!("unknown mode {other}: check | house | apartment | meshers | probe");
            std::process::exit(2);
        }
    }
}
