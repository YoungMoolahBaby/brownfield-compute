//! Pass 3d: the food houses and the arboretum (D10), added to the campus model.
//!
//! - Food houses: gutter-connected glasshouses beside the data hall, Venlo-style ridges on 4 m bays,
//!   on a low stone base, with a stone head house facing the town (packing, the growers' rooms).
//!   Their area comes from the food model (`brownfield food` writes out/pass3/food.json). Inside:
//!   the crop in rows and the grow lights above it.
//! - The warm main: a paved walk from the hall's east face to the head house, over the pipes.
//! - The arboretum: native Pennsylvania trees in groves, each species kept back from every
//!   foundation by its own distance (food.json, from params/food.yaml), clear of the views.
//!
//! Frame as garden.rs: metres in the code, millimetres in the meshes; x east, y south (the town),
//! z up from the upper pool's water.

use std::path::Path;

use cortenforge::cf_design::Solid;
use cortenforge::mesh::types::IndexedMesh;
use nalgebra::{Point3, Vector3};

use crate::garden::{M, Rng, append, b, stone_mass_s, tree};

type V = Vector3<f64>;

pub struct TreeSpec {
    pub name: String,
    pub height: f64,
    pub form: String,
    pub colour: [f64; 3],
    pub setback: f64,
    pub count: usize,
}

pub struct Spec {
    pub ha: f64,
    pub crop: String,
    pub bay: f64,
    pub gutter: f64,
    pub roof_deg: f64,
    pub trees: Vec<TreeSpec>,
}

/// out/pass3/food.json, written by `brownfield food`; a small default if it isn't there yet.
pub fn spec(root: &Path) -> Spec {
    let text = std::fs::read_to_string(root.join("out/pass3/food.json")).unwrap_or_default();
    let j: serde_json::Value = serde_json::from_str(&text).unwrap_or(serde_json::Value::Null);
    let f = |k: &str, d: f64| j["forge"][k].as_f64().unwrap_or(d);
    let trees = j["forge"]["trees"].as_array().map(|a| {
        a.iter().map(|t| TreeSpec {
            name: t["name"].as_str().unwrap_or("tree").to_string(),
            height: t["height_m"].as_f64().unwrap_or(18.0),
            form: t["form"].as_str().unwrap_or("round").to_string(),
            colour: [0, 1, 2].map(|i| t["colour"][i].as_f64().unwrap_or(0.5)),
            setback: t["setback_m"].as_f64().unwrap_or(15.0),
            count: t["count"].as_u64().unwrap_or(10) as usize,
        }).collect()
    }).unwrap_or_default();
    if text.is_empty() {
        println!("  (no out/pass3/food.json yet: run `brownfield food` for the food houses' area and the arboretum)");
    }
    Spec { ha: f("ha", 10.0), crop: j["forge"]["crop"].as_str().unwrap_or("lettuce").to_string(),
           bay: f("bay_m", 4.0), gutter: f("gutter_m", 6.0), roof_deg: f("roof_deg", 22.0), trees }
}

fn p(a: [f64; 3]) -> Point3<f64> {
    Point3::new(a[0] * M, a[1] * M, a[2] * M)
}

pub(crate) fn tri(out: &mut IndexedMesh, a: [f64; 3], b_: [f64; 3], c: [f64; 3]) {
    let base = out.vertices.len() as u32;
    out.vertices.extend([p(a), p(b_), p(c)]);
    out.faces.push([base, base + 1, base + 2]);
}

pub(crate) fn quad(out: &mut IndexedMesh, a: [f64; 3], b_: [f64; 3], c: [f64; 3], d: [f64; 3]) {
    tri(out, a, b_, c);
    tri(out, a, c, d);
}

/// A conifer (hemlock, white pine): a slim trunk and five stacked cones, tiered.
pub fn conifer(trunk: &mut IndexedMesh, crowns: &mut IndexedMesh, shade: &mut IndexedMesh, rng: &mut Rng, x: f64, y: f64, z0: f64, h: f64) {
    let r = rng.range(0.16, 0.26);
    b(trunk, [x - r, y - r, z0], [x + r, y + r, z0 + h * 0.35]);
    let (mut s, mut d): (Option<Solid>, Option<Solid>) = (None, None);
    let w = rng.range(0.9, 1.1);
    for k in 0..5 {
        let top = z0 + h * (1.0 - 0.15 * k as f64);
        let cone = Solid::cone(h * (0.09 + 0.045 * k as f64) * w * M, h * 0.32 * M)
            .translate(V::new(x + rng.range(-0.15, 0.15), y + rng.range(-0.15, 0.15), top) * M);
        if k % 2 == 1 {
            d = Some(match d { Some(t) => t.union(cone), None => cone });
        } else {
            s = Some(match s { Some(t) => t.union(cone), None => cone });
        }
    }
    append(crowns, &s.expect("tiers").mesh_adaptive_par(160.0).geometry);
    append(shade, &d.expect("tiers").mesh_adaptive_par(160.0).geometry);
}

pub struct Houses {
    pub glass: IndexedMesh,
    pub frame: IndexedMesh,
    pub crops: IndexedMesh,
    pub lamps: IndexedMesh,
    pub paving: IndexedMesh,
    /// (x0, x1, y0, y1) of the glasshouses and of the head house.
    pub block: (f64, f64, f64, f64),
    pub head: (f64, f64, f64, f64),
    pub floor_m2: f64,
}

/// The glasshouses: x from `x0` east, their south wall on y = `y1`, on ground at `z`. Ridges run
/// north-south. Returns the meshes and footprints; stone goes into `stone`.
pub fn houses(s: &Spec, stone: &mut [IndexedMesh; 5], concrete: &mut IndexedMesh, rng: &mut Rng, x0: f64, y1: f64, z: f64,
              hall_east: f64, hall_y: f64) -> (Houses, usize) {
    let (mut glass, mut frame, mut crops, mut lamps, mut paving) =
        (IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new());
    let area = s.ha * 1e4;
    let bays = ((area.sqrt() / s.bay).ceil() as usize).max(4);
    let w = bays as f64 * s.bay;
    let d = (area / w / 5.0).round() * 5.0;
    let (x1, y0) = (x0 + w, y1 - d);
    let (base, g) = (z + 1.0, z + s.gutter);
    let rise = s.bay / 2.0 * s.roof_deg.to_radians().tan();
    let mut n = 0;
    // A low stone base all round, then glass walls to the gutter, with bars every 2 m.
    for (lo, hi, f) in [([x0, y0, z], [x1, y0 + 0.4, base], [false, false, true, false]), ([x0, y1 - 0.4, z], [x1, y1, base], [false, false, false, true]),
                        ([x0, y0, z], [x0 + 0.4, y1, base], [true, false, false, false]), ([x1 - 0.4, y0, z], [x1, y1, base], [false, true, false, false])] {
        n += stone_mass_s(stone, rng, lo, hi, f, 1.3);
    }
    for (a, c) in [([x0, y0], [x1, y0]), ([x1, y1], [x0, y1]), ([x0, y1], [x0, y0]), ([x1, y0], [x1, y1])] {
        quad(&mut glass, [a[0], a[1], base], [c[0], c[1], base], [c[0], c[1], g], [a[0], a[1], g]);
    }
    let mut x = x0;
    while x <= x1 + 1e-6 {
        b(&mut frame, [x - 0.04, y0 - 0.05, base], [x + 0.04, y0 + 0.05, g]);
        b(&mut frame, [x - 0.04, y1 - 0.05, base], [x + 0.04, y1 + 0.05, g]);
        x += 2.0;
    }
    let mut y = y0;
    while y <= y1 + 1e-6 {
        b(&mut frame, [x0 - 0.05, y - 0.04, base], [x0 + 0.05, y + 0.04, g]);
        b(&mut frame, [x1 - 0.05, y - 0.04, base], [x1 + 0.05, y + 0.04, g]);
        y += 2.0;
    }
    // The roof: a ridge per bay, glass on both slopes, a gutter between bays, bars every 1.25 m;
    // a glass gable at each end of each ridge.
    for i in 0..bays {
        let xa = x0 + i as f64 * s.bay;
        let (xm, xb) = (xa + s.bay / 2.0, xa + s.bay);
        quad(&mut glass, [xa, y0, g], [xa, y1, g], [xm, y1, g + rise], [xm, y0, g + rise]);
        quad(&mut glass, [xm, y0, g + rise], [xm, y1, g + rise], [xb, y1, g], [xb, y0, g]);
        tri(&mut glass, [xa, y0, g], [xm, y0, g + rise], [xb, y0, g]);
        tri(&mut glass, [xa, y1, g], [xb, y1, g], [xm, y1, g + rise]);
        b(&mut frame, [xa - 0.08, y0, g - 0.18], [xa + 0.08, y1, g]);
        b(&mut frame, [xm - 0.04, y0, g + rise - 0.06], [xm + 0.04, y1, g + rise + 0.02]);
        let mut yb = y0 + 1.25;
        while yb < y1 {
            for (xs, xe) in [(xa, xm), (xb, xm)] {
                let zs = |xx: f64| g + rise * (1.0 - (xx - xm).abs() / (s.bay / 2.0)) + 0.02;
                quad(&mut frame, [xs, yb - 0.025, zs(xs)], [xe, yb - 0.025, zs(xe)], [xe, yb + 0.025, zs(xe)], [xs, yb + 0.025, zs(xs)]);
            }
            yb += 1.25;
        }
        // Posts on the gutter lines every 5 m.
        let mut yp = y0 + 5.0;
        while yp < y1 - 1.0 && i > 0 {
            b(&mut frame, [xa - 0.06, yp - 0.06, z], [xa + 0.06, yp + 0.06, g]);
            yp += 5.0;
        }
        // The crop and the lights over it.
        let tall = s.crop == "tomato";
        for k in 0..2 {
            let xc = xa + 0.6 + k as f64 * 1.9;
            if tall {
                b(&mut crops, [xc, y0 + 3.0, z], [xc + 0.7, y1 - 3.0, z + 3.4]);
            } else {
                b(&mut crops, [xc, y0 + 3.0, z + 0.85], [xc + 1.3, y1 - 3.0, z + 1.0]);
                b(&mut frame, [xc, y0 + 3.0, z + 0.7], [xc + 1.3, y1 - 3.0, z + 0.85]);
            }
            let mut yl = y0 + 4.0;
            while yl < y1 - 3.0 {
                b(&mut lamps, [xc + 0.3, yl, g - 0.75], [xc + 0.42, yl + 1.1, g - 0.68]);
                yl += 2.6;
            }
        }
    }
    // A concrete floor through the houses (walks and the crop's footings).
    b(&mut paving, [x0 + 0.4, y0 + 0.4, z], [x1 - 0.4, y1 - 0.4, z + 0.02]);
    // The head house, at the corner nearest the town: the entrance, the vegan food court (a Costco-
    // style hall at the front door) and packing; stone ends and piers, glass between them on two
    // storeys, an ochre band and a deep ochre roof slab, as on the garden and the hall.
    let xc = x0 + 40.0;
    let head = (xc - 32.0, xc + 32.0, y1 + 2.0, y1 + 20.0);
    let (hz1, hz2) = (z + 4.2, z + 8.4);
    n += stone_mass_s(stone, rng, [head.0, head.2, z], [head.0 + 6.0, head.3, hz2], [true, false, false, true], 1.4);
    n += stone_mass_s(stone, rng, [head.1 - 6.0, head.2, z], [head.1, head.3, hz2], [false, true, false, true], 1.4);
    n += stone_mass_s(stone, rng, [head.0 + 6.0, head.2, z], [head.1 - 6.0, head.2 + 1.0, hz2], [false, false, true, false], 1.4);
    let mut xp = head.0 + 6.0 + 7.0;
    while xp < head.1 - 8.0 {
        n += stone_mass_s(stone, rng, [xp - 0.7, head.3 - 1.4, z], [xp + 0.7, head.3, hz2], [true, true, false, true], 1.4);
        xp += 7.0;
    }
    b(&mut glass, [head.0 + 6.0, head.3 - 1.0, z + 0.3], [head.1 - 6.0, head.3 - 0.96, hz2 - 0.2]);
    b(&mut frame, [head.0 + 6.0, head.2 + 1.0, z], [head.1 - 6.0, head.3 - 1.0, z + 0.05]);
    b(concrete, [head.0 - 0.6, head.3 - 1.0, hz1 - 0.35], [head.1 + 0.6, head.3 + 1.6, hz1]);
    b(concrete, [head.0 - 3.0, head.2 - 1.0, hz2], [head.1 + 3.0, head.3 + 4.0, hz2 + 0.55]);
    // The warm main: a paved walk over the pipes, from the hall's east face to the houses.
    b(&mut paving, [hall_east, hall_y - 2.5, z], [x0, hall_y + 2.5, z + 0.03]);
    b(&mut paving, [xc - 2.5, y1, z], [xc + 2.5, head.2, z + 0.03]);
    (Houses { glass, frame, crops, lamps, paving, block: (x0, x1, y0, y1), head, floor_m2: w * d }, n)
}

/// The arboretum: each species in a grove of its own, in the open ground round the campus, every
/// tree at least its species' setback from all `built` footprints (x0, x1, y0, y1), clear of the
/// views (`eyes`) and of the pools. Returns how many of each were placed.
pub fn arboretum(s: &Spec, trunks: &mut IndexedMesh, crowns: &mut [IndexedMesh], dark: &mut [IndexedMesh], rng: &mut Rng,
                 built: &[(f64, f64, f64, f64)], eyes: &[(f64, f64)], groves: &[(f64, f64)], ground_z: impl Fn(f64, f64) -> f64) -> Vec<usize> {
    let gap = |x: f64, y: f64, r: &(f64, f64, f64, f64)| {
        let dx = (r.0 - x).max(x - r.1).max(0.0);
        let dy = (r.2 - y).max(y - r.3).max(0.0);
        dx.hypot(dy)
    };
    let mut placed = vec![0; s.trees.len()];
    let mut taken: Vec<(f64, f64, f64)> = Vec::new();
    for (i, t) in s.trees.iter().enumerate() {
        let (cx, cy) = groves[i % groves.len()];
        let mut tries = 0;
        while placed[i] < t.count && tries < 400 {
            tries += 1;
            let (x, y) = (cx + rng.range(-28.0, 28.0), cy + rng.range(-28.0, 28.0));
            if built.iter().any(|r| gap(x, y, r) < t.setback) || eyes.iter().any(|(ex, ey)| (x - ex).hypot(y - ey) < 22.0) {
                continue;
            }
            // Keep crowns apart: no closer than the two crowns' radii (~0.3 of each height).
            if taken.iter().any(|(tx, ty, th)| (x - tx).hypot(y - ty) < 0.3 * (t.height + th)) {
                continue;
            }
            taken.push((x, y, t.height));
            let h = t.height * rng.range(0.85, 1.05);
            let z0 = ground_z(x, y);
            match t.form.as_str() {
                "cone" => conifer(trunks, &mut crowns[i], &mut dark[i], rng, x, y, z0, h),
                "oval" => tree(trunks, &mut crowns[i], &mut dark[i], rng, x, y, z0, h, 0.19, 0.36),
                _ => tree(trunks, &mut crowns[i], &mut dark[i], rng, x, y, z0, h, 0.32, 0.27),
            }
            placed[i] += 1;
        }
    }
    placed
}
