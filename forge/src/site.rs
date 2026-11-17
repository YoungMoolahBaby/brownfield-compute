//! The site plan (D12), drawn into the campus scene from out/pass3/site.json (`brownfield site`):
//! the modules where the plan puts them, the roads and walks it routes round the buildings, the
//! mobility hub (D14), the remote delivery building where trucks are screened, and where a road
//! still meets a walk an underpass (truck roads) or a raised crossing (the public road). Round the
//! hall, the landscape stand-off band: a line of stone planters on the stand-off distance, which no
//! vehicle can pass and no one reads as a fence.
//!
//! Frame as garden.rs: metres in the code, millimetres in the meshes; x east, y south, z up.

use std::path::Path;

use cortenforge::mesh::types::IndexedMesh;

use crate::food::quad;
use crate::garden::{Rng, b, stone_mass_s};

type Pt = (f64, f64);

pub struct Plan {
    pub modules: Vec<(String, [f64; 4], i64)>,
    pub trucks: Vec<Vec<Pt>>,
    pub cars: Vec<Vec<Pt>>,
    pub walks: Vec<Vec<Pt>>,
    pub underpasses: Vec<Pt>,
    pub raised: Vec<Pt>,
    pub hall: [f64; 4],
    pub gate: Pt,
    pub town: Pt,
    pub standoff: f64,
    /// The bearing the winter garden faces (D15; 180 south, 270 west).
    pub garden_faces: i64,
}

impl Plan {
    pub fn rect(&self, name: &str) -> Option<[f64; 4]> {
        self.modules.iter().find(|(n, _, _)| n == name).map(|(_, r, _)| *r)
    }
    pub fn rot(&self, name: &str) -> i64 {
        self.modules.iter().find(|(n, _, _)| n == name).map(|(_, _, r)| *r).unwrap_or(0)
    }
}

/// out/pass3/site.json's layout in params/site.yaml (its "current"), if `brownfield site` has run.
pub fn plan(root: &Path) -> Option<Plan> {
    let text = std::fs::read_to_string(root.join("out/pass3/site.json")).ok()?;
    let j: serde_json::Value = serde_json::from_str(&text).ok()?;
    let c = &j["current"];
    let pt = |v: &serde_json::Value| (v[0].as_f64().unwrap_or(0.0), v[1].as_f64().unwrap_or(0.0));
    let lines = |k: &str| -> Vec<Vec<Pt>> {
        c[k].as_array().map(|a| a.iter().map(|l| l.as_array().map(|q| q.iter().map(pt).collect()).unwrap_or_default()).collect())
            .unwrap_or_default()
    };
    let pts = |k: &str| -> Vec<Pt> { c[k].as_array().map(|a| a.iter().map(pt).collect()).unwrap_or_default() };
    let r4 = |v: &serde_json::Value| [0, 1, 2, 3].map(|i| v[i].as_f64().unwrap_or(0.0));
    Some(Plan {
        modules: c["modules"].as_array()?.iter()
            .map(|m| (m["name"].as_str().unwrap_or("").to_string(), r4(&m["rect"]), m["rot"].as_i64().unwrap_or(0))).collect(),
        trucks: lines("trucks"), cars: lines("cars"), walks: lines("walks"),
        underpasses: pts("underpasses"), raised: pts("raised_crossings"),
        hall: r4(&j["hall"]), gate: pt(&j["gate"]), town: pt(&j["town"]), standoff: j["standoff_m"].as_f64().unwrap_or(15.24),
        garden_faces: c["modules"].as_array()?.iter().find(|m| m["name"] == "winter garden")
            .and_then(|m| m["faces"].as_i64()).unwrap_or(180),
    })
}

/// The ground's height (m): the upper ground north of the step at y = 20, the lower ground south of
/// it (garden.rs). Roads and walks come down the step on a ramp 30 m long south of it.
pub fn ground(y: f64) -> f64 {
    if y <= 20.0 { 0.2 } else if y >= 50.0 { -2.2 } else { 0.2 - 2.4 * (y - 20.0) / 30.0 }
}

pub fn ground_at(_x: f64, y: f64) -> f64 {
    if y < 20.0 { 0.2 } else { -2.2 }
}

#[derive(Default)]
pub struct Drawn {
    pub asphalt: IndexedMesh,
    pub walks: IndexedMesh,
    pub lines: IndexedMesh,
    pub pavers: IndexedMesh,
    pub concrete: IndexedMesh,
    pub dark: IndexedMesh,
    pub cars: [IndexedMesh; 4],
    pub planting: IndexedMesh,
    pub ramps: IndexedMesh,
    /// Footprints (x0, x1, y0, y1) trees keep off: the hub, the delivery building, and every road
    /// and walk, piece by piece.
    pub rects: Vec<(f64, f64, f64, f64)>,
}

fn inside(r: &[f64; 4], x: f64, y: f64, pad: f64) -> bool {
    x > r[0] - pad && x < r[1] + pad && y > r[2] - pad && y < r[3] + pad
}

/// A strip `w` m wide along a polyline, on the ground (+`dz`), in 2 m pieces; pieces inside any of
/// `skip` are left out (walks inside a module are its own streets and floors). Where the ground
/// steps down, the strip ramps, on a bank of earth under it.
fn strip(out: &mut IndexedMesh, bank: &mut IndexedMesh, rects: &mut Vec<(f64, f64, f64, f64)>, line: &[Pt], w: f64, dz: f64, skip: &[[f64; 4]]) {
    for seg in line.windows(2) {
        let ((ax, ay), (bx, by)) = (seg[0], seg[1]);
        let len = (bx - ax).hypot(by - ay);
        if len < 1e-6 {
            continue;
        }
        let (ux, uy) = ((bx - ax) / len, (by - ay) / len);
        let (nx, ny) = (-uy * w / 2.0, ux * w / 2.0);
        let n = (len / 2.0).ceil() as usize;
        for k in 0..n {
            let (t0, t1) = (k as f64 * len / n as f64, ((k + 1) as f64 * len / n as f64 + 0.3).min(len));
            let (p0, p1) = ((ax + ux * t0, ay + uy * t0), (ax + ux * t1, ay + uy * t1));
            let (mx, my) = ((p0.0 + p1.0) / 2.0, (p0.1 + p1.1) / 2.0);
            if skip.iter().any(|r| inside(r, mx, my, 0.0)) {
                continue;
            }
            let (z0, z1) = (ground(p0.1) + dz, ground(p1.1) + dz);
            quad(out, [p0.0 + nx, p0.1 + ny, z0], [p0.0 - nx, p0.1 - ny, z0], [p1.0 - nx, p1.1 - ny, z1], [p1.0 + nx, p1.1 + ny, z1]);
            if my > 20.0 && my < 50.0 {
                // The bank under the ramp.
                let zt = z0.min(z1) - 0.02;
                b(bank, [mx - w / 2.0, my - 1.1, -2.25], [mx + w / 2.0, my + 1.1, zt]);
            }
            rects.push((mx - w / 2.0, mx + w / 2.0, my - w / 2.0, my + w / 2.0));
        }
        // A round-ish pad at each corner so the pieces join.
        if !skip.iter().any(|r| inside(r, bx, by, 0.0)) {
            let z = ground(by) + dz;
            let r = w / 2.0;
            let pts: Vec<[f64; 3]> = (0..8).map(|i| {
                let a = i as f64 * std::f64::consts::PI / 4.0 + std::f64::consts::PI / 8.0;
                [bx + r * a.cos(), by + r * a.sin(), z]
            }).collect();
            for i in 1..7 {
                crate::food::tri(out, pts[0], pts[i + 1], pts[i]);
            }
        }
    }
}

/// The nearest segment's direction (unit) to a point, over a set of polylines.
fn direction_at(lines: &[Vec<Pt>], q: Pt) -> Pt {
    let mut best = (f64::MAX, (1.0, 0.0));
    for l in lines {
        for s in l.windows(2) {
            let ((ax, ay), (bx, by)) = (s[0], s[1]);
            let (dx, dy) = (bx - ax, by - ay);
            let len2 = dx * dx + dy * dy;
            if len2 < 1e-9 {
                continue;
            }
            let t = (((q.0 - ax) * dx + (q.1 - ay) * dy) / len2).clamp(0.0, 1.0);
            let d = (ax + t * dx - q.0).hypot(ay + t * dy - q.1);
            if d < best.0 {
                let len = len2.sqrt();
                best = (d, (dx / len, dy / len));
            }
        }
    }
    best.1
}

/// A flat rectangle turned to direction (ux, uy): `l` along it, `w` across, at height z, `h` thick.
fn turned_box(out: &mut IndexedMesh, c: Pt, u: Pt, l: f64, w: f64, z: f64, h: f64) {
    let (ax, ay) = (u.0 * l / 2.0, u.1 * l / 2.0);
    let (nx, ny) = (-u.1 * w / 2.0, u.0 * w / 2.0);
    let p = |sa: f64, sn: f64, zz: f64| [c.0 + sa * ax + sn * nx, c.1 + sa * ay + sn * ny, zz];
    let (z0, z1) = (z, z + h);
    quad(out, p(-1.0, -1.0, z1), p(1.0, -1.0, z1), p(1.0, 1.0, z1), p(-1.0, 1.0, z1));
    for (a, bb) in [((-1.0, -1.0), (1.0, -1.0)), ((1.0, -1.0), (1.0, 1.0)), ((1.0, 1.0), (-1.0, 1.0)), ((-1.0, 1.0), (-1.0, -1.0))] {
        quad(out, p(a.0, a.1, z0), p(bb.0, bb.1, z0), p(bb.0, bb.1, z1), p(a.0, a.1, z1));
    }
}

/// Everything the plan adds to the campus: roads, walks, the hub, the delivery building, the
/// crossings and the planters. Stone goes into the shared stone meshes.
pub fn draw(pl: &Plan, stone: &mut [IndexedMesh; 5], rng: &mut Rng) -> (Drawn, usize) {
    let mut d = Drawn::default();
    let mut n = 0;
    let mods: Vec<[f64; 4]> = pl.modules.iter().map(|(_, r, _)| *r).collect();
    // Walks first (4 m, heated, snow-free: D14), then the roads over them (7.2 m: two 3.6 m lanes).
    let mut bank = IndexedMesh::new();
    for w in &pl.walks {
        strip(&mut d.walks, &mut bank, &mut d.rects, w, 4.0, 0.06, &mods);
    }
    for r in pl.trucks.iter().chain(pl.cars.iter()) {
        strip(&mut d.asphalt, &mut bank, &mut d.rects, r, 7.2, 0.10, &mods);
    }
    crate::garden::append(&mut d.ramps, &bank);

    // Raised crossings on the public road: a stone-paved table the width of the walk and more, with
    // a bollard each side of the walk.
    for &q in &pl.raised {
        let u = direction_at(&pl.cars, q);
        let z = ground(q.1);
        turned_box(&mut d.pavers, q, u, 8.0, 7.6, z + 0.10, 0.12);
        for s in [-1.0, 1.0] {
            let c = (q.0 - u.1 * s * 4.4, q.1 + u.0 * s * 4.4);
            for k in [-1.0, 1.0] {
                turned_box(&mut d.dark, (c.0 + u.0 * k * 2.5, c.1 + u.1 * k * 2.5), u, 0.25, 0.25, z, 1.0);
            }
        }
    }
    // Underpasses where a truck road still meets a walk: the road on a short bridge (a concrete deck
    // between stone parapets), the walk down a few steps in a stone-lined cut beneath it.
    for &q in &pl.underpasses {
        let u = direction_at(&pl.trucks, q);
        let z = ground(q.1);
        turned_box(&mut d.dark, q, (u.1, -u.0), 16.0, 5.0, z - 0.02, 0.10); // the cut, across the road
        turned_box(&mut d.concrete, q, u, 9.0, 8.4, z + 0.10, 0.16);
        for s in [-1.0, 1.0] {
            // A parapet along the road each side of the deck (boxes run along x or y, the road's
            // main direction).
            let c = (q.0 - u.1 * s * 4.1, q.1 + u.0 * s * 4.1);
            let (lo, hi) = if u.0.abs() > u.1.abs() {
                ([c.0 - 4.5, c.1 - 0.3, z + 0.26], [c.0 + 4.5, c.1 + 0.3, z + 1.3])
            } else {
                ([c.0 - 0.3, c.1 - 4.5, z + 0.26], [c.0 + 0.3, c.1 + 4.5, z + 1.3])
            };
            n += stone_mass_s(stone, rng, lo, hi, [true, true, true, true], 1.2);
        }
    }

    // The mobility hub (D14): the shared car park in double rows (5.5 m stalls either side of a 7 m
    // aisle), trees in islands, chargers at the row ends; on its side nearest the homes, the shuttle
    // stop under a concrete canopy on stone piers, and covered bikes.
    if let Some(h) = pl.rect("mobility hub") {
        let z = ground_at(0.0, (h[2] + h[3]) / 2.0);
        b(&mut d.asphalt, [h[0], h[2], z], [h[1], h[3], z + 0.08]);
        d.rects.push((h[0], h[1], h[2], h[3]));
        let along_x = (h[1] - h[0]) >= (h[3] - h[2]);
        let (a0, a1, c0, c1) = if along_x { (h[0], h[1], h[2], h[3]) } else { (h[2], h[3], h[0], h[1]) };
        // Shelter strip on the side toward the town (+y) or east, 12 m.
        let rows_end = c1 - 12.0;
        let mut c = c0 + 2.0;
        let mut k = 0;
        while c + 18.0 <= rows_end {
            for (s0, s1) in [(c, c + 5.5), (c + 12.5, c + 18.0)] {
                let mut a = a0 + 4.0;
                let mut stall = 0;
                let line = |out: &mut IndexedMesh, a: f64| {
                    if along_x { b(out, [a - 0.06, s0, z + 0.08], [a + 0.06, s1, z + 0.09]); } else { b(out, [s0, a - 0.06, z + 0.08], [s1, a + 0.06, z + 0.09]); }
                };
                while a + 2.6 <= a1 - 4.0 {
                    line(&mut d.lines, a);
                    if stall % 11 == 10 {
                        // A planted island with a small tree.
                        let (ix, iy) = if along_x { ((a + a + 2.6) / 2.0, (s0 + s1) / 2.0) } else { ((s0 + s1) / 2.0, (a + a + 2.6) / 2.0) };
                        b(&mut d.planting, [ix - 1.1, iy - 2.5, z + 0.08], [ix + 1.1, iy + 2.5, z + 0.25]);
                        let (mut cr, mut cd) = (IndexedMesh::new(), IndexedMesh::new());
                        crate::garden::tree(&mut d.dark, &mut cr, &mut cd, rng, ix, iy, z + 0.25, 7.5, 0.30, 0.27);
                        crate::garden::append(&mut d.planting, &cr);
                        crate::garden::append(&mut d.planting, &cd);
                    } else if rng.next() < 0.55 {
                        // A parked car, one of four muted colours.
                        let (cx, cy) = if along_x { ((a + a + 2.6) / 2.0, (s0 + s1) / 2.0) } else { ((s0 + s1) / 2.0, (a + a + 2.6) / 2.0) };
                        let (hw, hl) = if along_x { (0.9, 2.25) } else { (2.25, 0.9) };
                        let col = (rng.next() * 4.0) as usize % 4;
                        b(&mut d.cars[col], [cx - hw, cy - hl, z + 0.25], [cx + hw, cy + hl, z + 0.95]);
                        let (tw, tl) = if along_x { (0.8, 1.2) } else { (1.2, 0.8) };
                        b(&mut d.cars[col], [cx - tw, cy - tl, z + 0.95], [cx + tw, cy + tl, z + 1.45]);
                        b(&mut d.dark, [cx - hw + 0.05, cy - hl + 0.05, z + 0.08], [cx + hw - 0.05, cy + hl - 0.05, z + 0.25]);
                    }
                    a += 2.6;
                    stall += 1;
                }
                line(&mut d.lines, a);
                // Chargers at the row's ends.
                for e in [a0 + 2.5, a1 - 2.5] {
                    let (ex, ey) = if along_x { (e, (s0 + s1) / 2.0) } else { ((s0 + s1) / 2.0, e) };
                    b(&mut d.concrete, [ex - 0.25, ey - 0.15, z + 0.08], [ex + 0.25, ey + 0.15, z + 1.6]);
                }
            }
            c += 18.0;
            k += 1;
        }
        let _ = k;
        // The shuttle stop: a canopy 30 m long on stone piers along the hub's town-side edge, and
        // covered bike racks beside it.
        let (sa0, sa1) = ((a0 + a1) / 2.0 - 15.0, (a0 + a1) / 2.0 + 15.0);
        let (sc0, sc1) = (c1 - 9.0, c1 - 3.0);
        let bx_ = |a: f64, cc: f64| if along_x { (a, cc) } else { (cc, a) };
        let mut a = sa0;
        while a <= sa1 + 1e-6 {
            let (px, py) = bx_(a, sc0 + 0.5);
            n += stone_mass_s(stone, rng, [px - 0.4, py - 0.4, z + 0.08], [px + 0.4, py + 0.4, z + 3.2], [true, true, true, true], 1.2);
            a += 7.5;
        }
        let (l0, l1) = (bx_(sa0 - 1.0, sc0 - 0.5), bx_(sa1 + 1.0, sc1));
        b(&mut d.concrete, [l0.0.min(l1.0), l0.1.min(l1.1), z + 3.2], [l0.0.max(l1.0), l0.1.max(l1.1), z + 3.55]);
        let (p0, p1) = (bx_(sa0 - 1.0, sc0 - 0.5), bx_(sa1 + 1.0, c1));
        b(&mut d.pavers, [p0.0.min(p1.0), p0.1.min(p1.1), z + 0.08], [p0.0.max(p1.0), p0.1.max(p1.1), z + 0.12]);
        let (q0, q1) = (bx_(sa1 + 4.0, sc0), bx_(sa1 + 22.0, sc1));
        b(&mut d.concrete, [q0.0.min(q1.0), q0.1.min(q1.1), z + 2.4], [q0.0.max(q1.0), q0.1.max(q1.1), z + 2.6]);
        let mut a = sa1 + 4.5;
        while a < sa1 + 21.5 {
            let (rx, ry) = bx_(a, (sc0 + sc1) / 2.0);
            b(&mut d.dark, [rx - 0.04, ry - 1.5, z + 0.08], [rx + 0.04, ry + 1.5, z + 0.9]);
            a += 0.8;
        }
    }

    // The remote delivery building (D12): stone walls, a deep concrete roof, loading doors on the
    // side toward the entrance, and a yard in front of them.
    if let Some(r) = pl.rect("remote delivery building") {
        let z = ground_at(0.0, (r[2] + r[3]) / 2.0);
        for (lo, hi, f) in [([r[0], r[2], z], [r[1], r[2] + 0.6, z + 8.0], [false, false, true, false]),
                            ([r[0], r[3] - 0.6, z], [r[1], r[3], z + 8.0], [false, false, false, true]),
                            ([r[0], r[2], z], [r[0] + 0.6, r[3], z + 8.0], [true, false, false, false]),
                            ([r[1] - 0.6, r[2], z], [r[1], r[3], z + 8.0], [false, true, false, false])] {
            n += stone_mass_s(stone, rng, lo, hi, f, 1.4);
        }
        b(&mut d.concrete, [r[0] - 1.5, r[2] - 1.5, z + 8.0], [r[1] + 1.5, r[3] + 1.5, z + 8.7]);
        b(&mut d.concrete, [r[0] + 0.6, r[2] + 0.6, z], [r[1] - 0.6, r[3] - 0.6, z + 7.9]);
        // Doors on the side facing the entrance.
        let (gx, gy) = pl.gate;
        let (cx, cy) = ((r[0] + r[1]) / 2.0, (r[2] + r[3]) / 2.0);
        let east = (gx - cx).abs() * (r[3] - r[2]) >= (gy - cy).abs() * (r[1] - r[0]);
        if east {
            let xs = if gx > cx { r[1] + 0.01 } else { r[0] - 0.11 };
            let mut y = r[2] + 3.0;
            while y + 3.6 <= r[3] - 2.0 {
                b(&mut d.dark, [xs, y, z + 1.2], [xs + 0.1, y + 3.6, z + 5.2]);
                y += 5.5;
            }
            let (y0, y1) = (r[2], r[3]);
            let (x0, x1) = if gx > cx { (r[1], r[1] + 30.0) } else { (r[0] - 30.0, r[0]) };
            b(&mut d.asphalt, [x0, y0, z], [x1, y1, z + 0.08]);
            d.rects.push((x0, x1, y0, y1));
        } else {
            let ys = if gy > cy { r[3] + 0.01 } else { r[2] - 0.11 };
            let mut x = r[0] + 3.0;
            while x + 3.6 <= r[1] - 2.0 {
                b(&mut d.dark, [x, ys, z + 1.2], [x + 3.6, ys + 0.1, z + 5.2]);
                x += 5.5;
            }
            let (y0, y1) = if gy > cy { (r[3], r[3] + 30.0) } else { (r[2] - 30.0, r[2]) };
            b(&mut d.asphalt, [r[0], y0, z], [r[1], y1, z + 0.08]);
            d.rects.push((r[0], r[1], y0, y1));
        }
        d.rects.push((r[0], r[1], r[2], r[3]));
    }

    // The stand-off band: stone planters on the line `standoff` m out from the hall, on its west,
    // north and east sides (the garden and its pools hold the south), 1.2 m apart, planted; none
    // across a road or walk or inside a module.
    let [hx0, hx1, hy0, hy1] = pl.hall;
    let s = pl.standoff;
    let mut posts: Vec<(Pt, bool)> = Vec::new(); // (centre, runs along x)
    let mut x = hx0 - s;
    while x <= hx1 + s {
        posts.push(((x, hy0 - s), true));
        x += 3.7;
    }
    let mut y = hy0 - s + 3.7;
    while y <= hy1 + 2.0 {
        posts.push(((hx0 - s, y), false));
        posts.push(((hx1 + s, y), false));
        y += 3.7;
    }
    let near_route = |q: Pt| {
        pl.trucks.iter().chain(pl.cars.iter()).chain(pl.walks.iter()).any(|l| l.windows(2).any(|sg| {
            let ((ax, ay), (bx, by)) = (sg[0], sg[1]);
            let (dx, dy) = (bx - ax, by - ay);
            let len2 = (dx * dx + dy * dy).max(1e-9);
            let t = (((q.0 - ax) * dx + (q.1 - ay) * dy) / len2).clamp(0.0, 1.0);
            (ax + t * dx - q.0).hypot(ay + t * dy - q.1) < 7.0
        }))
    };
    for ((px, py), along_x) in posts {
        if mods.iter().any(|r| inside(r, px, py, 1.5)) || near_route((px, py)) {
            continue;
        }
        let z = ground_at(px, py);
        let (hx, hy) = if along_x { (1.25, 0.6) } else { (0.6, 1.25) };
        n += stone_mass_s(stone, rng, [px - hx, py - hy, z], [px + hx, py + hy, z + 0.9], [true, true, true, true], 1.0);
        b(&mut d.planting, [px - hx + 0.1, py - hy + 0.1, z + 0.9], [px + hx - 0.1, py + hy - 0.1, z + 1.25]);
        d.rects.push((px - hx, px + hx, py - hy, py + hy));
    }
    (d, n)
}
