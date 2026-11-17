//! D18: each town's new homes and clubhouse, drawn on the real ground (`cargo run --release -- conference`).
//!
//! From `out/pass3/conference/<region>.json` and its ground grids (`brownfield conference`):
//! - the ground at 2 m round the new homes and at 10 m for 3 km round, coloured by NLCD land cover,
//!   the far woods as a canopy;
//! - the towns as they are: Microsoft's building footprints, walls to the eaves and a gable on the
//!   small ones, in pale tones so the old reads apart from the new; PennDOT's roads; every tree in
//!   NLCD's woods near the homes, in autumn;
//! - the new homes, lot by lot: `village.rs`'s walk-ups, townhouses and houses with their gardens,
//!   each turned to its street and set on its lot's graded plane, the building on a level pad with a
//!   stone plinth taking up the fall;
//! - the clubhouse (D18): a court hall with a clerestory behind a low stone-and-timber wing (cafe,
//!   lobby, fitness room, workshop), its plaza, bike racks and six parking spaces;
//! - AWS's buildings where they are in view, as plain massing.
//!
//! Frame: forge's (x east, y south, z up), metres in the code and millimetres in the meshes; z from
//! the region's lowest inner point. The data are north-up, so y is negated on reading.

use std::path::Path;

use cortenforge::cf_geometry::HeightFieldData;
use cortenforge::mesh::types::IndexedMesh;
use nalgebra::{Point3, Vector3};
use serde_json::Value;

use crate::food::{quad, tri};
use crate::garden::{b, stone_mass_s, Rng, M, STONE};
use crate::scene::{self, Camera, Light, SLayer};
use crate::village::{self, Ring, Village, Z as ZV};

type V = Vector3<f64>;

// --- The ground --------------------------------------------------------------------------------------

struct Field {
    x0: f64,
    y1: f64,
    step: f64,
    nx: usize,
    ny: usize,
    z: Vec<f32>,
    c: Vec<u8>,
    /// The same grid as CortenForge's height field (its origin at the south-west corner, y north),
    /// for sampling anywhere.
    hf: HeightFieldData,
}

impl Field {
    fn load(dir: &Path, region: &str, which: &str, meta: &Value) -> std::io::Result<Field> {
        let zb = std::fs::read(dir.join(format!("{region}_{which}.f32")))?;
        let c = std::fs::read(dir.join(format!("{region}_{which}.u8")))?;
        let z: Vec<f32> = zb.chunks_exact(4).map(|q| f32::from_le_bytes([q[0], q[1], q[2], q[3]])).collect();
        let f = |k: &str| meta[k].as_f64().unwrap_or(0.0);
        let (nx, ny) = (meta["nx"].as_u64().unwrap_or(0) as usize, meta["ny"].as_u64().unwrap_or(0) as usize);
        // Our rows run north to south; the height field's y runs north, so its row 0 is our last.
        let south_up: Vec<f64> = (0..ny).rev().flat_map(|j| z[j * nx..(j + 1) * nx].iter().map(|&v| v as f64)).collect();
        let hf = HeightFieldData::new(south_up, nx, ny, f("step"));
        Ok(Field { x0: f("x0"), y1: f("y1"), step: f("step"), nx, ny, z, c, hf })
    }
    /// A grid point (column i, row j; rows run north to south) in north-up metres.
    fn xy(&self, i: usize, j: usize) -> (f64, f64) {
        (self.x0 + i as f64 * self.step, self.y1 - j as f64 * self.step)
    }
    fn at(&self, i: usize, j: usize) -> f64 {
        self.z[j * self.nx + i] as f64
    }
    fn inside(&self, x: f64, yn: f64) -> bool {
        x >= self.x0 && x <= self.x0 + (self.nx - 1) as f64 * self.step && yn <= self.y1 && yn >= self.y1 - (self.ny - 1) as f64 * self.step
    }
    /// Ground level at a north-up point: CortenForge's bilinear sample, clamped at the edges.
    fn h(&self, x: f64, yn: f64) -> f64 {
        let south = self.y1 - (self.ny - 1) as f64 * self.step;
        self.hf.sample_clamped(x - self.x0, yn - south)
    }
}

struct Ground {
    inner: Field,
    outer: Field,
}

impl Ground {
    fn h(&self, x: f64, yn: f64) -> f64 {
        if self.inner.inside(x, yn) { self.inner.h(x, yn) } else { self.outer.h(x, yn) }
    }
}

/// NLCD's classes (and 200, the new homes' lawns) to the ground's colour groups.
fn group(c: u8) -> usize {
    match c {
        200 => 0,
        21 => 1,
        22 => 2,
        23 | 24 | 31 => 3,
        41 | 42 | 43 | 90 => 4,
        71 | 81 | 52 => 5,
        82 => 6,
        11 => 7,
        _ => 8,
    }
}

const GROUND: [[f64; 3]; 9] = [
    [0.42, 0.56, 0.30], // the new homes' lawns and verges
    [0.44, 0.54, 0.31], // developed open space: lawns, parks
    [0.46, 0.54, 0.33], // low-intensity developed: yards between houses
    [0.53, 0.55, 0.44], // medium and high: lawns, lots, parking
    [0.36, 0.30, 0.21], // the woods' floor, in leaf litter
    [0.60, 0.60, 0.38], // hay, pasture and grass in October
    [0.66, 0.57, 0.40], // cropland after harvest
    [0.28, 0.38, 0.44], // water
    [0.47, 0.51, 0.35], // wetland and the rest
];

const AUTUMN: [[f64; 3]; 5] = [[0.80, 0.45, 0.18], [0.86, 0.70, 0.26], [0.66, 0.22, 0.16], [0.52, 0.50, 0.24], [0.46, 0.36, 0.22]];

/// Value noise: `hash` on a lattice `k` cells apart, bilinear between (0..1).
fn noise(i: usize, j: usize, k: usize) -> f64 {
    let (a, c) = (i / k, j / k);
    let (u, v) = ((i % k) as f64 / k as f64, (j % k) as f64 / k as f64);
    let (u, v) = (u * u * (3.0 - 2.0 * u), v * v * (3.0 - 2.0 * v));
    (1.0 - v) * ((1.0 - u) * hash(a, c) + u * hash(a + 1, c)) + v * ((1.0 - u) * hash(a, c + 1) + u * hash(a + 1, c + 1))
}

fn hash(i: usize, j: usize) -> f64 {
    let mut h = (i as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15) ^ (j as u64).wrapping_mul(0xC2B2_AE3D_27D4_EB4F);
    h ^= h >> 31;
    h = h.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    h ^= h >> 29;
    (h >> 11) as f64 / (1u64 << 53) as f64
}

/// One grid as terrain, split by colour group, with shared vertices (smooth). Cells wholly inside
/// `hole` are left out (the finer grid covers them); vertices inside it drop `drop` m. With `canopy`,
/// wooded cells also get a canopy 15-22 m up, in autumn patches, skirted where the woods end.
fn terrain(f: &Field, hole: Option<&Field>, drop: f64, out: &mut [IndexedMesh; 9], mut canopy: Option<&mut [IndexedMesh; 6]>) {
    let n = f.nx * f.ny;
    let mut idx: Vec<Vec<u32>> = (0..9).map(|_| vec![u32::MAX; n]).collect();
    let mut cidx: Vec<Vec<u32>> = (0..5).map(|_| vec![u32::MAX; n]).collect();
    let inside = |i: usize, j: usize| hole.is_some_and(|h| {
        let (x, y) = f.xy(i, j);
        h.inside(x, y)
    });
    let vert = |i: usize, j: usize| {
        let (x, y) = f.xy(i, j);
        let z = f.at(i, j) - if inside(i, j) { drop } else { 0.0 };
        Point3::new(x * M, -y * M, z * M)
    };
    let woods = |i: usize, j: usize| i < f.nx - 1 && j < f.ny - 1 && group(f.c[j * f.nx + i]) == 4;
    // A canopy 16-21 m up, rolling over ~40 m rather than cell by cell.
    let top = |i: usize, j: usize| {
        let (a, c) = (i / 4, j / 4);
        let (u, v) = ((i % 4) as f64 / 4.0, (j % 4) as f64 / 4.0);
        let n = (1.0 - v) * ((1.0 - u) * hash(a, c) + u * hash(a + 1, c)) + v * ((1.0 - u) * hash(a, c + 1) + u * hash(a + 1, c + 1));
        f.at(i, j) + 16.0 + 5.0 * n
    };
    for j in 0..f.ny - 1 {
        for i in 0..f.nx - 1 {
            if inside(i, j) && inside(i + 1, j) && inside(i, j + 1) && inside(i + 1, j + 1) {
                continue;
            }
            let g = group(f.c[j * f.nx + i]);
            let corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)];
            let mut k = [0u32; 4];
            for (q, &(a, c)) in corners.iter().enumerate() {
                let id = &mut idx[g][c * f.nx + a];
                if *id == u32::MAX {
                    *id = out[g].vertices.len() as u32;
                    out[g].vertices.push(vert(a, c));
                }
                k[q] = *id;
            }
            out[g].faces.push([k[0], k[1], k[2]]);
            out[g].faces.push([k[0], k[2], k[3]]);
            if let Some(cn) = canopy.as_deref_mut() {
                let near_hole = corners.iter().any(|&(a, c)| inside(a, c));
                if g == 4 && !near_hole {
                    // Patches of colour with irregular edges: smooth noise over ~60 m, plus a little
                    // over ~20 m, cut into five bands.
                    let p = ((0.75 * noise(i, j, 6) + 0.25 * noise(i + 31, j + 17, 2)) * 5.0) as usize % 5;
                    let mut kk = [0u32; 4];
                    for (q, &(a, c)) in corners.iter().enumerate() {
                        let id = &mut cidx[p][c * f.nx + a];
                        if *id == u32::MAX {
                            *id = cn[p].vertices.len() as u32;
                            let (x, y) = f.xy(a, c);
                            cn[p].vertices.push(Point3::new(x * M, -y * M, top(a, c) * M));
                        }
                        kk[q] = *id;
                    }
                    cn[p].faces.push([kk[0], kk[1], kk[2]]);
                    cn[p].faces.push([kk[0], kk[2], kk[3]]);
                    // Skirts down to the ground where the woods end.
                    let edges = [((i, j), (i + 1, j), (i, j.wrapping_sub(1))), ((i + 1, j), (i + 1, j + 1), (i + 1, j)),
                                 ((i + 1, j + 1), (i, j + 1), (i, j + 1)), ((i, j + 1), (i, j), (i.wrapping_sub(1), j))];
                    for ((a0, b0), (a1, b1), (ni, nj)) in edges {
                        if ni < f.nx && nj < f.ny && woods(ni, nj) {
                            continue;
                        }
                        let (x0, y0) = f.xy(a0, b0);
                        let (x1, y1) = f.xy(a1, b1);
                        quad(&mut cn[5], [x0, -y0, f.at(a0, b0)], [x1, -y1, f.at(a1, b1)], [x1, -y1, top(a1, b1)], [x0, -y0, top(a0, b0)]);
                    }
                }
            }
        }
    }
}

// --- Trees, roads, the towns as built ----------------------------------------------------------------

struct Trees {
    trunks: IndexedMesh,
    crowns: [IndexedMesh; 5],
    conifers: IndexedMesh,
}

/// A ball (8 x 5, shared vertices) squashed vertically by `sz`.
fn ball(out: &mut IndexedMesh, c: [f64; 3], r: f64, sz: f64) {
    let (nu, nv) = (8usize, 5usize);
    let base = out.vertices.len() as u32;
    out.vertices.push(Point3::new(c[0] * M, c[1] * M, (c[2] + r * sz) * M));
    for j in 1..nv {
        let v = j as f64 / nv as f64 * std::f64::consts::PI;
        for i in 0..nu {
            let u = i as f64 / nu as f64 * std::f64::consts::TAU;
            out.vertices.push(Point3::new((c[0] + r * v.sin() * u.cos()) * M, (c[1] + r * v.sin() * u.sin()) * M, (c[2] + r * sz * v.cos()) * M));
        }
    }
    out.vertices.push(Point3::new(c[0] * M, c[1] * M, (c[2] - r * sz) * M));
    let ring = |j: usize, i: usize| base + 1 + ((j - 1) * nu + i % nu) as u32;
    let last = base + 1 + ((nv - 1) * nu) as u32;
    for i in 0..nu {
        out.faces.push([base, ring(1, i), ring(1, i + 1)]);
        for j in 1..nv - 1 {
            out.faces.push([ring(j, i), ring(j + 1, i), ring(j + 1, i + 1)]);
            out.faces.push([ring(j, i), ring(j + 1, i + 1), ring(j, i + 1)]);
        }
        out.faces.push([ring(nv - 1, i), last, ring(nv - 1, i + 1)]);
    }
}

/// A cone of 8 sides.
fn cone(out: &mut IndexedMesh, x: f64, y: f64, z0: f64, r: f64, h: f64) {
    let base = out.vertices.len() as u32;
    out.vertices.push(Point3::new(x * M, y * M, (z0 + h) * M));
    for i in 0..8 {
        let a = i as f64 / 8.0 * std::f64::consts::TAU;
        out.vertices.push(Point3::new((x + r * a.cos()) * M, (y + r * a.sin()) * M, z0 * M));
    }
    for i in 0..8u32 {
        out.faces.push([base, base + 1 + i, base + 1 + (i + 1) % 8]);
    }
}

fn tree(t: &mut Trees, rng: &mut Rng, x: f64, y: f64, z: f64, h: f64, conifer: bool) {
    let r = if conifer { 0.18 } else { 0.22 };
    b(&mut t.trunks, [x - r, y - r, z - 0.3], [x + r, y + r, z + h * 0.5]);
    if conifer {
        let w = h * rng.range(0.16, 0.2);
        cone(&mut t.conifers, x, y, z + h * 0.25, w, h * 0.55);
        cone(&mut t.conifers, x, y, z + h * 0.5, w * 0.72, h * 0.5);
    } else {
        let k = { let u = rng.next(); if u < 0.28 { 0 } else if u < 0.52 { 1 } else if u < 0.66 { 2 } else if u < 0.88 { 3 } else { 4 } };
        let cr = h * rng.range(0.24, 0.3);
        ball(&mut t.crowns[k], [x, y, z + h * 0.66], cr, 1.1);
        if h > 12.0 {
            let a = rng.range(0.0, std::f64::consts::TAU);
            ball(&mut t.crowns[k], [x + 0.45 * cr * a.cos(), y + 0.45 * cr * a.sin(), z + h * 0.56], cr * 0.7, 1.0);
        }
    }
}

/// A strip `w` wide along a polyline (north-up metres) draped on the ground `lift` m up, `across`
/// strips wide, sampled every ~5 m.
fn ribbon(out: &mut IndexedMesh, g: &Ground, pts: &[(f64, f64)], w: f64, off: f64, lift: f64, across: usize) {
    for s in pts.windows(2) {
        let (a, c) = (s[0], s[1]);
        let len = ((c.0 - a.0).powi(2) + (c.1 - a.1).powi(2)).sqrt();
        if len < 0.1 {
            continue;
        }
        let (dx, dy) = ((c.0 - a.0) / len, (c.1 - a.1) / len);
        let (nx, ny) = (-dy, dx);
        let k = (len / 5.0).ceil().max(1.0) as usize;
        let row = |t: f64| -> Vec<[f64; 3]> {
            let (px, py) = (a.0 + dx * t, a.1 + dy * t);
            (0..=across).map(|q| {
                let s_ = off - w / 2.0 + w * q as f64 / across as f64;
                let (x, y) = (px + nx * s_, py + ny * s_);
                [x, -y, g.h(x, y) + lift]
            }).collect()
        };
        let mut prev = row(0.0);
        for m in 1..=k {
            let cur = row(len * m as f64 / k as f64);
            for q in 0..across {
                quad(out, prev[q], prev[q + 1], cur[q + 1], cur[q]);
            }
            prev = cur;
        }
    }
}

/// Triangles of a simple polygon (ear clipping).
fn ear_clip(p: &[(f64, f64)]) -> Vec<[usize; 3]> {
    let n = p.len();
    if n < 3 {
        return vec![];
    }
    let area: f64 = (0..n).map(|i| { let (a, c) = (p[i], p[(i + 1) % n]); a.0 * c.1 - c.0 * a.1 }).sum();
    let s = area.signum();
    let cross = |a: (f64, f64), b_: (f64, f64), c: (f64, f64)| (b_.0 - a.0) * (c.1 - a.1) - (b_.1 - a.1) * (c.0 - a.0);
    let mut v: Vec<usize> = (0..n).collect();
    let mut out = vec![];
    let mut guard = 0;
    while v.len() > 3 && guard < 4 * n * n {
        guard += 1;
        let m = v.len();
        let mut cut = None;
        for k in 0..m {
            let (i0, i1, i2) = (v[(k + m - 1) % m], v[k], v[(k + 1) % m]);
            if cross(p[i0], p[i1], p[i2]) * s <= 1e-9 {
                continue;
            }
            let inside = v.iter().any(|&q| q != i0 && q != i1 && q != i2 && {
                let (a, b_, c) = (cross(p[i0], p[i1], p[q]) * s, cross(p[i1], p[i2], p[q]) * s, cross(p[i2], p[i0], p[q]) * s);
                a >= 0.0 && b_ >= 0.0 && c >= 0.0
            });
            if !inside {
                cut = Some(k);
                out.push([i0, i1, i2]);
                break;
            }
        }
        match cut {
            Some(k) => { v.remove(k); }
            None => break,
        }
    }
    if v.len() == 3 {
        out.push([v[0], v[1], v[2]]);
    }
    out
}

/// A building as it stands: walls from its lowest ground to its eaves; a gable over a small
/// rectangle, otherwise a flat roof.
fn existing(walls: &mut IndexedMesh, roofs: &mut IndexedMesh, pts: &[(f64, f64)], z: f64, h: f64) {
    let w: Vec<(f64, f64)> = pts.iter().map(|&(x, y)| (x, -y)).collect();
    let n = w.len();
    let top = z + h;
    for i in 0..n {
        let (a, c) = (w[i], w[(i + 1) % n]);
        quad(walls, [a.0, a.1, z - 0.4], [c.0, c.1, z - 0.4], [c.0, c.1, top], [a.0, a.1, top]);
    }
    let side = |i: usize| ((w[(i + 1) % n].0 - w[i].0).powi(2) + (w[(i + 1) % n].1 - w[i].1).powi(2)).sqrt();
    if n == 4 && side(0) * side(1) < 450.0 {
        // Ridge along the long sides' middle, a 30-degree pitch.
        let (l0, l1) = if side(0) >= side(1) { (0, 1) } else { (1, 0) };
        let short = side(l1);
        let rise = short / 2.0 * 0.58;
        let mid = |i: usize| ((w[i].0 + w[(i + 1) % 4].0) / 2.0, (w[i].1 + w[(i + 1) % 4].1) / 2.0);
        let (ma, mb) = (mid(l1), mid(l1 + 2));
        let (r0, r1) = ([ma.0, ma.1, top + rise], [mb.0, mb.1, top + rise]);
        let p = |i: usize| [w[i % 4].0, w[i % 4].1, top];
        // The two slopes run along the long sides; r0 stands over short side l1, r1 over l1 + 2.
        if l0 == 0 {
            quad(roofs, p(0), p(1), r0, r1);
            quad(roofs, p(2), p(3), r1, r0);
        } else {
            quad(roofs, p(1), p(2), r1, r0);
            quad(roofs, p(3), p(0), r0, r1);
        }
        tri(walls, p(l1), p(l1 + 1), r0);
        tri(walls, p(l1 + 2), p(l1 + 3), r1);
    } else {
        for t in ear_clip(&w) {
            tri(roofs, [w[t[0]].0, w[t[0]].1, top], [w[t[1]].0, w[t[1]].1, top], [w[t[2]].0, w[t[2]].1, top]);
        }
    }
}

// --- The new homes, set on their lots ------------------------------------------------------------------

/// A lot's frame: local x along the street, local y toward it (as `village.rs` builds with facing +1
/// at the origin), turned and moved onto the lot; buildings on the pad, gardens on the lot's plane.
struct Tf {
    cx: f64,
    cy: f64,
    cs: f64,
    sn: f64,
    pad: f64,
    zc: f64,
    su: f64,
    so: f64,
}

impl Tf {
    fn of(l: &Value) -> Tf {
        let f = |k: &str| l[k].as_f64().unwrap_or(0.0);
        // Out toward the street in forge's frame (y south) is (ox, -oy); local +y maps onto it.
        let (ox, oy) = (f("ox"), -f("oy"));
        Tf { cx: f("x"), cy: -f("y"), cs: oy, sn: -ox, pad: f("pad"), zc: f("zc"), su: f("su"), so: f("so") }
    }
    fn xy(&self, lx: f64, ly: f64) -> (f64, f64) {
        (self.cx + lx * self.cs - ly * self.sn, self.cy + lx * self.sn + ly * self.cs)
    }
    /// The lot's graded ground at a local point.
    fn ground(&self, lx: f64, ly: f64) -> f64 {
        self.zc + self.su * lx + self.so * ly
    }
    fn add(&self, dst: &mut IndexedMesh, src: &IndexedMesh, on_ground: bool) {
        let base = dst.vertices.len() as u32;
        dst.vertices.extend(src.vertices.iter().map(|p| {
            let (lx, ly, lz) = (p.x / M, p.y / M, p.z / M);
            let (x, y) = self.xy(lx, ly);
            let z = if on_ground { self.ground(lx, ly) + (lz - ZV) + 0.03 } else { self.pad + (lz - ZV) };
            Point3::new(x * M, y * M, z * M)
        }));
        dst.faces.extend(src.faces.iter().map(|f| [f[0] + base, f[1] + base, f[2] + base]));
    }
}

/// Everything in `s` into `d` through `tf`: the buildings on the pad, the gardens on the ground.
fn transfer(d: &mut Village, s: &Village, tf: &Tf) {
    for (a, c) in [(&mut d.base, &s.base), (&mut d.body, &s.body), (&mut d.trim, &s.trim), (&mut d.windows, &s.windows),
                   (&mut d.doors, &s.doors), (&mut d.glass, &s.glass), (&mut d.frame, &s.frame), (&mut d.roofs, &s.roofs),
                   (&mut d.sedum, &s.sedum), (&mut d.deck, &s.deck)] {
        tf.add(a, c, false);
    }
    for (a, c) in d.tones.iter_mut().zip(s.tones.iter()) {
        tf.add(a, c, false);
    }
    for (a, c) in [(&mut d.paving, &s.paving), (&mut d.plaza, &s.plaza), (&mut d.grass, &s.grass), (&mut d.lines, &s.lines),
                   (&mut d.greens, &s.greens), (&mut d.sward, &s.sward), (&mut d.blades, &s.blades), (&mut d.stems, &s.stems),
                   (&mut d.purple, &s.purple), (&mut d.yellow, &s.yellow), (&mut d.centres, &s.centres), (&mut d.hedge, &s.hedge),
                   (&mut d.shrub, &s.shrub), (&mut d.white, &s.white), (&mut d.small_trunks, &s.small_trunks), (&mut d.rain, &s.rain),
                   (&mut d.beds, &s.beds), (&mut d.pavers, &s.pavers)] {
        tf.add(a, c, true);
    }
    for (a, c) in d.meadow.iter_mut().zip(s.meadow.iter()).chain(d.small.iter_mut().zip(s.small.iter())) {
        tf.add(a, c, true);
    }
}

/// Sizes of the homes (`neighbourhood._types`).
struct Types {
    th: (f64, f64, usize, f64, f64),             // townhouse w, d, storeys, storey, garage height
    flats: (f64, f64, usize, f64),               // walk-up w, d, storeys, storey
    house: (f64, f64, usize, f64, f64, f64, f64), // w, d, storeys, storey, garage w, d, h
}

impl Types {
    fn of(t: &Value) -> Types {
        let f = |a: &str, k: &str| t[a][k].as_f64().unwrap_or(0.0);
        let u = |a: &str| t[a]["storeys"].as_u64().unwrap_or(2) as usize;
        Types { th: (f("townhouse", "w"), f("townhouse", "d"), u("townhouse"), f("townhouse", "storey_m"), f("townhouse", "garage_h")),
                flats: (f("flats", "w"), f("flats", "d"), u("flats"), f("flats", "storey_m")),
                house: (f("house", "w"), f("house", "d"), u("house"), f("house", "storey_m"), f("house", "garage_w"), f("house", "garage_d"),
                        f("house", "garage_h")) }
    }
}

/// One home and its garden in its own frame, with a stone plinth under the building down to the
/// lowest ground beneath it.
fn home(v: &mut Village, rng: &mut Rng, l: &Value, t: &Types, tf: &Tf) {
    let f = |k: &str| l[k].as_f64().unwrap_or(0.0);
    let (lw, ld) = (f("w"), f("d"));
    let tone = (rng.next() * 5.0) as usize % 5;
    // The building's footprint in the frame: x from x0 to x1, y from y0 to y1.
    let (x0, x1, y0, y1) = match l["kind"].as_str().unwrap_or("") {
        "flats" => {
            let (_, d, n, sh) = t.flats;
            let w = if f("bw") > 0.0 { f("bw") } else { t.flats.0 };
            village::walkup(v, 0.0, 0.0, 1.0, w, d, n, sh, ld, tone);
            village::walkup_lot(v, rng, 0.0, 0.0, 1.0, w, d, lw, ld);
            let front = ld / 2.0 - 6.0;
            (-w / 2.0, w / 2.0, front - d, front)
        }
        "townhouses" => {
            let (w, d, n, sh, gh) = t.th;
            village::townhouse(v, 0.0, 0.0, 1.0, w, d, n, sh, gh, Some(tone));
            village::lot(v, rng, 0.0, 0.0, 1.0, w, lw - w, d, ZV + gh + sh * n as f64);
            (-w / 2.0, w / 2.0, 8.0 - d, 8.0)
        }
        "houses" => {
            let (w, d, n, sh, gw, gd, gh) = t.house;
            let r = Ring { kind: "houses".into(), homes: vec![], streets_y: vec![], greens: vec![], street_x: (0.0, 0.0), spine_x: 0.0,
                           spine_y: (0.0, 0.0), lot_w: lw, lot_d: ld, w, d, storeys: n, storey_m: sh, garage: (gw, gd, gh) };
            let mut roofs = IndexedMesh::new();
            village::house_big(v, 0.0, 0.0, 1.0, &r, tone, &mut roofs);
            village::house_lot(v, rng, 0.0, 0.0, 1.0, &r);
            scene::add_moved(&mut v.roofs, &roofs, V::zeros());
            let front = ld / 2.0 - 8.0;
            (-(w + gw) / 2.0, (w + gw) / 2.0, front - d.max(gd + 0.6), front)
        }
        _ => return,
    };
    let low = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)].iter().map(|&(x, y)| tf.ground(x, y)).fold(f64::INFINITY, f64::min);
    if low < tf.pad {
        b(&mut v.base, [x0 + 0.02, y0 + 0.02, ZV - (tf.pad - low) - 0.3], [x1 - 0.02, y1 - 0.02, ZV + 0.02]);
    }
}

// --- The clubhouse ---------------------------------------------------------------------------------------

/// The clubhouse in its lot's frame (60 x 60 m, the road at +y): the court hall (34 x 19.7 m = the
/// 670 m2 court hall, 7 m clear, roof at 8.6 m, a clerestory band all round) behind a low wing on the
/// street (cafe 150 m2, lobby and toilets 85, fitness 120, workshop 90: 34 x 13.1 m, 4.4 m), a stone
/// base, timber above, a planted roof on the wing, a metal one on the hall; inside, the court, the
/// cafe's counter and tables, the machines, the benches; outside, the plaza, racks, parking, lawn.
#[derive(Default)]
struct Club {
    stone: [IndexedMesh; 5],
    clad: IndexedMesh,
    trim: IndexedMesh,
    glass: IndexedMesh,
    doors: IndexedMesh,
    roof: IndexedMesh,
    sedum: IndexedMesh,
    floor: IndexedMesh,
    court: IndexedMesh,
    lines: IndexedMesh,
    walls: IndexedMesh,
    wood: IndexedMesh,
    dark: IndexedMesh,
    mats: IndexedMesh,
    hoops: IndexedMesh,
    // On the ground:
    pavers: IndexedMesh,
    asphalt: IndexedMesh,
    paint: IndexedMesh,
    blue: IndexedMesh,
    lawn: IndexedMesh,
    racks: IndexedMesh,
    trunks: IndexedMesh,
    crowns: [IndexedMesh; 3],
}

/// A wall from (x0, y0) to (x1, y1) (axis-aligned, `t` thick, outward face `out` as stone's faces
/// west, east, north, south): stone to `stone_top`, timber to `top`.
#[allow(clippy::too_many_arguments)]
fn wall(c: &mut Club, rng: &mut Rng, lo: [f64; 2], hi: [f64; 2], z0: f64, stone_top: f64, top: f64, out: [bool; 4]) {
    if stone_top > z0 {
        stone_mass_s(&mut c.stone, rng, [lo[0], lo[1], z0], [hi[0], hi[1], stone_top], out, 1.0);
    }
    if top > stone_top {
        b(&mut c.clad, [lo[0], lo[1], stone_top], [hi[0], hi[1], top]);
    }
}

/// A parapet: four strips round a rectangle, `w` wide, from z0 to z1.
fn parapet(m: &mut IndexedMesh, x0: f64, y0: f64, x1: f64, y1: f64, z0: f64, z1: f64, w: f64) {
    b(m, [x0, y0, z0], [x1, y0 + w, z1]);
    b(m, [x0, y1 - w, z0], [x1, y1, z1]);
    b(m, [x0, y0, z0], [x0 + w, y1, z1]);
    b(m, [x1 - w, y0, z0], [x1, y1, z1]);
}

fn clubhouse(c: &mut Club, rng: &mut Rng) {
    let f = ZV;
    let (wx0, wx1, wy0, wy1) = (-28.0, 6.0, 4.9, 18.0); // the wing
    let (hy0, hy1) = (-14.8, 4.9); // the hall, as wide as the wing
    let (wh, hh) = (4.4, 8.6);
    let t = 0.35;
    // The hall's walls: stone to 3 m outside, timber above, the clerestory band 6.4-8.0 m.
    wall(c, rng, [wx0, hy0], [wx1, hy0 + t], f, f + 3.0, f + hh, [false, false, true, false]);
    wall(c, rng, [wx0, hy0], [wx0 + t, hy1], f, f + 3.0, f + hh, [true, false, false, false]);
    wall(c, rng, [wx1 - t, hy0], [wx1, hy1], f, f + 3.0, f + hh, [false, true, false, false]);
    b(&mut c.clad, [wx0, hy1 - t, f], [wx1, hy1, f + hh]); // between the hall and the wing
    for (y, s) in [(hy0, -1.0), (hy1, 1.0)] {
        let (ya, yb) = if s < 0.0 { (y - 0.05, y) } else { (y, y + 0.05) };
        let mut x = wx0 + 0.8;
        while x < wx1 - 2.0 {
            b(&mut c.glass, [x, ya, f + 6.4], [x + 2.6, yb, f + 8.0]);
            x += 3.0;
        }
    }
    for x in [wx0, wx1] {
        let (xa, xb) = if x == wx0 { (x - 0.05, x) } else { (x, x + 0.05) };
        let mut y = hy0 + 0.8;
        while y < hy1 - 2.0 {
            b(&mut c.glass, [xa, y, f + 6.4], [xb, y + 2.6, f + 8.0]);
            y += 3.0;
        }
    }
    parapet(&mut c.trim, wx0 - 0.15, hy0 - 0.15, wx1 + 0.15, hy1 + 0.15, f + hh, f + hh + 0.6, 0.5);
    b(&mut c.roof, [wx0 + 0.3, hy0 + 0.3, f + hh], [wx1 - 0.3, hy1 - 0.3, f + hh + 0.3]);
    // The wing: stone to 1 m, timber above, its front mostly glass.
    wall(c, rng, [wx0, wy1 - t], [wx1, wy1], f, f + 1.0, f + wh, [false, false, false, true]);
    wall(c, rng, [wx0, wy0], [wx0 + t, wy1], f, f + 1.0, f + wh, [true, false, false, false]);
    wall(c, rng, [wx1 - t, wy0], [wx1, wy1], f, f + 1.0, f + wh, [false, true, false, false]);
    parapet(&mut c.trim, wx0 - 0.15, wy0, wx1 + 0.15, wy1 + 0.15, f + wh, f + wh + 0.5, 0.45);
    b(&mut c.roof, [wx0 + 0.3, wy0 + 0.3, f + wh], [wx1 - 0.3, wy1 - 0.3, f + wh + 0.2]);
    b(&mut c.sedum, [wx0 + 0.4, wy0 + 0.3, f + wh + 0.2], [wx1 - 0.4, wy1 - 0.4, f + wh + 0.35]);
    let fy = (wy1, wy1 + 0.06);
    // Rooms along the wing (x): cafe to -16.6, lobby to -10.1, fitness to -0.9, workshop to the end.
    let mut x = -27.4;
    while x < -17.2 {
        b(&mut c.glass, [x, fy.0, f + 1.0], [x + 2.2, fy.1, f + 3.9]);
        b(&mut c.trim, [x + 2.2, fy.0, f + 1.0], [x + 2.4, fy.1 + 0.04, f + 3.9]);
        x += 2.4;
    }
    let mut y = wy0 + 1.2;
    while y < wy1 - 2.0 {
        b(&mut c.glass, [wx0 - 0.06, y, f + 1.0], [wx0, y + 2.2, f + 3.9]);
        y += 2.4;
    }
    b(&mut c.doors, [-15.4, fy.0, f], [-11.3, fy.1, f + 2.7]);
    b(&mut c.glass, [-15.4, fy.0, f + 2.7], [-11.3, fy.1, f + 3.9]);
    b(&mut c.trim, [-16.9, wy1, f + 3.1], [-9.8, wy1 + 2.2, f + 3.35]); // the entrance canopy
    for k in 0..3 {
        let x = -9.4 + 3.0 * k as f64;
        b(&mut c.glass, [x, fy.0, f + 1.2], [x + 2.2, fy.1, f + 3.4]);
    }
    for k in 0..2 {
        let x = -0.2 + 3.2 * k as f64;
        b(&mut c.glass, [x, fy.0, f + 2.4], [x + 2.4, fy.1, f + 3.6]);
    }
    b(&mut c.doors, [wx1, 8.5, f], [wx1 + 0.06, 12.1, f + 3.2]); // the workshop's roll-up door, to the parking
    // Inside: floors, the court and its lines and hoops, the rooms' walls and furniture.
    b(&mut c.court, [wx0 + t, hy0 + t, f], [wx1 - t, hy1 - t, f + 0.06]);
    b(&mut c.floor, [wx0 + t, wy0, f], [wx1 - t, wy1 - t, f + 0.05]);
    let (cxm, cym) = ((wx0 + wx1) / 2.0, (hy0 + hy1) / 2.0);
    let (hl, hw) = (25.6 / 2.0, 15.2 / 2.0);
    let ln = |c: &mut Club, a: [f64; 2], e: [f64; 2]| b(&mut c.lines, [a[0], a[1], f + 0.06], [e[0], e[1], f + 0.07]);
    ln(c, [cxm - hl, cym - hw], [cxm + hl, cym - hw + 0.05]);
    ln(c, [cxm - hl, cym + hw - 0.05], [cxm + hl, cym + hw]);
    ln(c, [cxm - hl, cym - hw], [cxm - hl + 0.05, cym + hw]);
    ln(c, [cxm + hl - 0.05, cym - hw], [cxm + hl, cym + hw]);
    ln(c, [cxm - 0.025, cym - hw], [cxm + 0.025, cym + hw]);
    for s in [-1.0, 1.0] {
        let e = cxm + s * hl;
        let k = e - s * 5.8;
        ln(c, [e.min(k), cym - 2.45], [e.max(k), cym - 2.4]);
        ln(c, [e.min(k), cym + 2.4], [e.max(k), cym + 2.45]);
        ln(c, [k - 0.025, cym - 2.45], [k + 0.025, cym + 2.45]);
        let post = e + s * 1.0;
        b(&mut c.hoops, [post - 0.15, cym - 0.15, f], [post + 0.15, cym + 0.15, f + 3.0]);
        let bb = e - s * 1.2;
        b(&mut c.hoops, [bb.min(bb + s * 0.05), cym - 0.9, f + 2.9], [bb.max(bb + s * 0.05), cym + 0.9, f + 3.95]);
        b(&mut c.wood, [(bb - s * 0.5).min(bb), cym - 0.23, f + 3.05], [(bb - s * 0.5).max(bb), cym + 0.23, f + 3.07]);
    }
    for (x, len) in [(-16.6, 1.0), (-10.1, 1.0), (-0.9, 1.0)] {
        b(&mut c.walls, [x - 0.08, wy0, f], [x + 0.08, wy1 - t, f + 3.6 * len]);
    }
    b(&mut c.wood, [-20.6, 6.0, f], [-17.4, 7.0, f + 1.05]); // the cafe's counter
    for k in 0..8 {
        let (tx, ty) = (-26.0 + 2.6 * (k % 4) as f64, 10.5 + 3.4 * (k / 4) as f64);
        b(&mut c.wood, [tx, ty, f + 0.72], [tx + 0.9, ty + 0.9, f + 0.76]);
        b(&mut c.wood, [tx + 0.4, ty + 0.4, f], [tx + 0.5, ty + 0.5, f + 0.72]);
        for (dx, dy) in [(-0.55, 0.25), (1.0, 0.25)] {
            b(&mut c.dark, [tx + dx, ty + dy, f], [tx + dx + 0.45, ty + dy + 0.45, f + 0.45]);
        }
    }
    b(&mut c.wood, [-15.8, 7.0, f], [-12.0, 7.8, f + 1.0]); // the lobby's desk
    for k in 0..8 {
        let (mx, my) = (-9.4 + 2.2 * (k % 4) as f64, 7.0 + 4.2 * (k / 4) as f64);
        b(&mut c.dark, [mx, my, f], [mx + 0.8, my + 1.9, f + 1.3]);
    }
    b(&mut c.mats, [-9.4, 13.4, f], [-1.6, 16.8, f + 0.04]);
    for k in 0..2 {
        let by = 7.5 + 4.0 * k as f64;
        b(&mut c.wood, [0.3, by, f], [4.8, by + 1.0, f + 0.9]);
    }
    b(&mut c.wood, [-0.6, wy1 - t - 0.1, f + 1.2], [5.4, wy1 - t, f + 2.6]); // the tool wall
    b(&mut c.dark, [3.0, 14.0, f], [4.4, 15.2, f + 1.1]);
    // Outside: the plaza to the road, its tables, the racks, the parking and its drive, the lawn.
    b(&mut c.pavers, [-30.0, wy1, ZV], [8.0, 30.0, ZV + 0.05]);
    for k in 0..4 {
        let tx = -26.0 + 4.5 * k as f64;
        b(&mut c.racks, [tx, 23.0, ZV], [tx + 1.2, 23.8, ZV + 0.75]);
        b(&mut c.racks, [tx - 0.6, 23.1, ZV], [tx - 0.2, 23.7, ZV + 0.45]);
        b(&mut c.racks, [tx + 1.4, 23.1, ZV], [tx + 1.8, 23.7, ZV + 0.45]);
    }
    for k in 0..6 {
        let x = -6.0 + 1.6 * k as f64;
        b(&mut c.racks, [x, 21.0, ZV], [x + 0.06, 21.8, ZV + 0.85]);
    }
    b(&mut c.asphalt, [9.0, 8.0, ZV], [29.0, 21.0, ZV + 0.04]);
    b(&mut c.asphalt, [21.0, 21.0, ZV], [28.0, 30.0, ZV + 0.04]);
    let mut x = 9.6;
    for k in 0..6 {
        let w = if k < 2 { 3.6 } else { 2.7 };
        if k < 2 {
            b(&mut c.blue, [x + 0.1, 8.2, ZV + 0.04], [x + w - 0.1, 13.3, ZV + 0.05]);
        }
        b(&mut c.paint, [x + w - 0.05, 8.2, ZV + 0.04], [x + w + 0.05, 13.5, ZV + 0.05]);
        x += w;
    }
    b(&mut c.lawn, [-30.0, -30.0, ZV], [30.0, hy0 - 0.5, ZV + 0.04]);
    b(&mut c.lawn, [wx1 + 0.5, -30.0, ZV], [30.0, 8.0, ZV + 0.04]);
    // Trees at the plaza's two ends and along the parking; the cafe's front stays open to the road.
    for (k, (tx, ty)) in [(-29.0, 20.0), (-29.0, 26.0), (7.6, 21.0), (7.6, 27.0), (30.0, 9.0), (30.0, 15.0)].into_iter().enumerate() {
        let h = rng.range(7.5, 9.5);
        b(&mut c.trunks, [tx - 0.12, ty - 0.12, ZV], [tx + 0.12, ty + 0.12, ZV + h * 0.55]);
        ball(&mut c.crowns[k % 3], [tx, ty, ZV + h * 0.7], h * 0.27, 0.95);
    }
    for k in 0..5 {
        let (tx, ty) = (-26.0 + 11.0 * k as f64, -24.0 + rng.range(-2.0, 2.0));
        let h = rng.range(9.0, 12.0);
        b(&mut c.trunks, [tx - 0.15, ty - 0.15, ZV], [tx + 0.15, ty + 0.15, ZV + h * 0.55]);
        ball(&mut c.crowns[(k + 1) % 3], [tx, ty, ZV + h * 0.68], h * 0.28, 0.95);
    }
}

struct ClubWorld {
    stone: [IndexedMesh; 5],
    parts: Vec<(IndexedMesh, [f64; 3], bool)>, // (mesh, colour, roof)
}

fn place_club(c: &Club, tf: &Tf) -> ClubWorld {
    let mut stone: [IndexedMesh; 5] = Default::default();
    for (a, s) in stone.iter_mut().zip(c.stone.iter()) {
        tf.add(a, s, false);
    }
    let mut parts = vec![];
    let mut put = |m: &IndexedMesh, col: [f64; 3], ground: bool, roof: bool| {
        let mut o = IndexedMesh::new();
        tf.add(&mut o, m, ground);
        parts.push((o, col, roof));
    };
    put(&c.clad, [0.82, 0.68, 0.52], false, false);
    put(&c.trim, [0.93, 0.92, 0.88], false, false);
    put(&c.glass, [0.22, 0.28, 0.32], false, false);
    put(&c.doors, [0.40, 0.38, 0.35], false, false);
    put(&c.roof, [0.34, 0.36, 0.38], false, true);
    put(&c.sedum, [0.50, 0.58, 0.30], false, true);
    put(&c.floor, [0.78, 0.68, 0.52], false, false);
    put(&c.court, [0.84, 0.66, 0.43], false, false);
    put(&c.lines, [0.97, 0.97, 0.97], false, false);
    put(&c.walls, [0.88, 0.86, 0.82], false, false);
    put(&c.wood, [0.62, 0.46, 0.30], false, false);
    put(&c.dark, [0.22, 0.23, 0.25], false, false);
    put(&c.mats, [0.25, 0.40, 0.62], false, false);
    put(&c.hoops, [0.92, 0.92, 0.92], false, false);
    put(&c.pavers, [0.70, 0.64, 0.55], true, false);
    put(&c.asphalt, [0.33, 0.33, 0.34], true, false);
    put(&c.paint, [0.95, 0.95, 0.93], true, false);
    put(&c.blue, [0.22, 0.42, 0.75], true, false);
    put(&c.lawn, [0.42, 0.56, 0.30], true, false);
    put(&c.racks, [0.55, 0.57, 0.60], true, false);
    put(&c.trunks, [0.32, 0.26, 0.22], true, false);
    for (m, col) in c.crowns.iter().zip([AUTUMN[0], AUTUMN[1], AUTUMN[2]]) {
        put(m, col, true, false);
    }
    // The plinth under the building, down to the lowest ground beneath it.
    let (x0, x1, y0, y1) = (-28.0, 6.0, -14.8, 18.0);
    let low = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)].iter().map(|&(x, y)| tf.ground(x, y)).fold(f64::INFINITY, f64::min);
    if low < tf.pad {
        let mut m = IndexedMesh::new();
        b(&mut m, [x0 + 0.02, y0 + 0.02, ZV - (tf.pad - low) - 0.3], [x1 - 0.02, y1 - 0.02, ZV + 0.02]);
        let mut o = IndexedMesh::new();
        tf.add(&mut o, &m, false);
        parts.push((o, [0.66, 0.60, 0.52], false));
    }
    ClubWorld { stone, parts }
}

// --- A region, built and drawn ----------------------------------------------------------------------------

struct Scene {
    ground: [IndexedMesh; 9],
    canopy: [IndexedMesh; 6],
    roads: IndexedMesh,
    lane: IndexedMesh,
    walks: IndexedMesh,
    walls: [IndexedMesh; 4],
    roofs: [IndexedMesh; 3],
    halls: IndexedMesh,
    hall_roofs: IndexedMesh,
    trees: Trees,
    homes: Village,
    clubs: Vec<ClubWorld>,
}

fn pts(v: &Value) -> Vec<(f64, f64)> {
    v.as_array().map(|a| a.iter().map(|q| (q[0].as_f64().unwrap_or(0.0), q[1].as_f64().unwrap_or(0.0))).collect()).unwrap_or_default()
}

fn build(j: &Value, g: &Ground, seed: u64) -> Scene {
    let mut rng = Rng(seed);
    let mut s = Scene {
        ground: Default::default(), canopy: Default::default(), roads: IndexedMesh::new(), lane: IndexedMesh::new(), walks: IndexedMesh::new(),
        walls: Default::default(), roofs: Default::default(), halls: IndexedMesh::new(), hall_roofs: IndexedMesh::new(),
        trees: Trees { trunks: IndexedMesh::new(), crowns: Default::default(), conifers: IndexedMesh::new() },
        homes: Village::default(), clubs: vec![],
    };
    terrain(&g.inner, None, 0.0, &mut s.ground, None);
    terrain(&g.outer, Some(&g.inner), 0.6, &mut s.ground, Some(&mut s.canopy));
    for r in j["roads"].as_array().into_iter().flatten() {
        let w = r["w"].as_f64().unwrap_or(7.0);
        ribbon(&mut s.roads, g, &pts(&r["pts"]), w, 0.0, 0.12, if w > 12.0 { 4 } else { 2 });
    }
    for st in j["streets"].as_array().into_iter().flatten().chain(j["spines"].as_array().into_iter().flatten()) {
        let p = pts(st);
        ribbon(&mut s.lane, g, &p, 6.0, 0.0, 0.10, 3);
        for side in [-1.0, 1.0] {
            ribbon(&mut s.walks, g, &p, 1.8, side * 5.3, 0.13, 1);
        }
        // Street trees in the verges, every 15 m.
        for w2 in p.windows(2) {
            let (a, c) = (w2[0], w2[1]);
            let len = ((c.0 - a.0).powi(2) + (c.1 - a.1).powi(2)).sqrt();
            let (dx, dy) = ((c.0 - a.0) / len.max(1e-9), (c.1 - a.1) / len.max(1e-9));
            let mut t = 9.0;
            while t < len - 6.0 {
                for side in [-1.0, 1.0] {
                    let (x, y) = (a.0 + dx * t - dy * side * 6.9, a.1 + dy * t + dx * side * 6.9);
                    let h = rng.range(7.0, 9.0);
                    tree(&mut s.trees, &mut rng, x, -y, g.h(x, y), h, false);
                }
                t += 15.0;
            }
        }
    }
    for (k, bd) in j["buildings"].as_array().into_iter().flatten().enumerate() {
        let (z, h) = (bd["z"].as_f64().unwrap_or(0.0), bd["h"].as_f64().unwrap_or(5.0));
        existing(&mut s.walls[(k * 7 + 3) % 4], &mut s.roofs[k % 3], &pts(&bd["pts"]), z, h);
    }
    for hl in j["halls"].as_array().into_iter().flatten() {
        let z = hl["z"].as_f64().unwrap_or(0.0);
        let h = hl["h"].as_f64().unwrap_or(21.3);
        let mut flat = IndexedMesh::new();
        existing(&mut s.halls, &mut flat, &pts(&hl["pts"]), z, h);
        scene::add_moved(&mut s.hall_roofs, &flat, V::zeros());
    }
    for t in j["trees"].as_array().into_iter().flatten() {
        let (x, y, h) = (t[0].as_f64().unwrap_or(0.0), t[1].as_f64().unwrap_or(0.0), t[2].as_f64().unwrap_or(15.0));
        tree(&mut s.trees, &mut rng, x, -y, g.h(x, y), h, t[3].as_u64().unwrap_or(0) == 1);
    }
    let types = Types::of(&j["types"]);
    for l in j["lots"].as_array().into_iter().flatten() {
        let tf = Tf::of(l);
        if l["kind"].as_str() == Some("club") {
            let mut c = Club::default();
            clubhouse(&mut c, &mut rng);
            s.clubs.push(place_club(&c, &tf));
            continue;
        }
        let mut v = Village::default();
        home(&mut v, &mut rng, l, &types, &tf);
        transfer(&mut s.homes, &v, &tf);
    }
    s
}

fn layers<'a>(s: &'a Scene, roof_off: bool) -> Vec<SLayer<'a>> {
    let mut out = vec![];
    for (m, c) in s.ground.iter().zip(GROUND.iter()) {
        out.push(SLayer::solid(m, *c).smooth().no_shadow());
    }
    // The far woods, muted toward an olive-brown with distance.
    for (m, c) in s.canopy.iter().take(5).zip(AUTUMN.iter()) {
        let mix = [0.50, 0.44, 0.27];
        out.push(SLayer::solid(m, [0, 1, 2].map(|k| 0.45 * c[k] + 0.55 * mix[k])).smooth().no_shadow());
    }
    out.push(SLayer::solid(&s.canopy[5], [0.40, 0.34, 0.22]).no_shadow());
    out.push(SLayer::solid(&s.roads, [0.36, 0.36, 0.37]).no_shadow());
    out.push(SLayer::solid(&s.lane, [0.33, 0.33, 0.34]).no_shadow());
    out.push(SLayer::solid(&s.walks, [0.72, 0.68, 0.60]).no_shadow());
    for (m, c) in s.walls.iter().zip([[0.90, 0.89, 0.86], [0.84, 0.83, 0.80], [0.80, 0.78, 0.74], [0.88, 0.86, 0.80]]) {
        out.push(SLayer::solid(m, c));
    }
    for (m, c) in s.roofs.iter().zip([[0.36, 0.36, 0.38], [0.42, 0.34, 0.30], [0.30, 0.31, 0.33]]) {
        out.push(SLayer::solid(m, c));
    }
    out.push(SLayer::solid(&s.halls, [0.80, 0.80, 0.78]));
    out.push(SLayer::solid(&s.hall_roofs, [0.64, 0.65, 0.66]));
    out.push(SLayer::solid(&s.trees.trunks, [0.30, 0.25, 0.21]));
    for (m, c) in s.trees.crowns.iter().zip(AUTUMN.iter()) {
        out.push(SLayer::solid(m, *c).smooth());
    }
    out.push(SLayer::solid(&s.trees.conifers, [0.17, 0.29, 0.19]));
    village::layers(&s.homes, &mut out);
    for c in &s.clubs {
        for (m, col) in c.stone.iter().zip(STONE.iter()) {
            out.push(SLayer::solid(m, *col));
        }
        for (m, col, roof) in &c.parts {
            if roof_off && *roof {
                continue;
            }
            out.push(SLayer::solid(m, *col));
        }
    }
    village::glass_layer(&s.homes, &mut out);
    out
}

fn tris(s: &Scene) -> usize {
    let n = |m: &IndexedMesh| m.faces.len();
    s.ground.iter().map(n).sum::<usize>() + s.canopy.iter().map(n).sum::<usize>() + n(&s.roads) + n(&s.lane) + n(&s.walks)
        + s.walls.iter().map(n).sum::<usize>() + s.roofs.iter().map(n).sum::<usize>() + n(&s.halls) + n(&s.trees.trunks)
        + s.trees.crowns.iter().map(n).sum::<usize>() + n(&s.trees.conifers)
        + s.clubs.iter().map(|c| c.stone.iter().map(n).sum::<usize>() + c.parts.iter().map(|p| n(&p.0)).sum::<usize>()).sum::<usize>()
}

pub fn run(root: &Path) -> std::io::Result<()> {
    let dir = root.join("out/pass3/conference");
    let docs = root.join("docs/pass3");
    let stamp = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let run_dir = root.join("out/pass3/renders").join(stamp.to_string());
    std::fs::create_dir_all(&run_dir)?;
    std::fs::create_dir_all(&docs)?;
    println!("  renders to {}", run_dir.display());
    // CONF_REGIONS=homer_city,... and CONF_VIEWS=aerial,clubhouse,... draw only those.
    let only = |var: &str| std::env::var(var).ok().map(|s| s.split(',').map(|v| v.trim().to_string()).collect::<Vec<_>>());
    let (regions, views) = (only("CONF_REGIONS"), only("CONF_VIEWS"));
    for region in ["homer_city", "lucerne_mines", "black_lick", "graceton_coral"] {
        if regions.as_ref().is_some_and(|r| !r.iter().any(|n| n == region)) {
            continue;
        }
        let path = dir.join(format!("{region}.json"));
        let Ok(text) = std::fs::read_to_string(&path) else {
            println!("  (no {}: run `brownfield conference`)", path.display());
            continue;
        };
        let t0 = std::time::Instant::now();
        let j: Value = serde_json::from_str(&text)?;
        let g = Ground { inner: Field::load(&dir, region, "inner", &j["inner"])?, outer: Field::load(&dir, region, "outer", &j["outer"])? };
        let s = build(&j, &g, 0x00D1_8C0F_u64 ^ region.len() as u64);
        println!("{region}: {} triangles, built in {:.1} s", tris(&s) + village_tris(&s.homes), t0.elapsed().as_secs_f64());
        let all = layers(&s, false);
        let open = layers(&s, true);
        for cam in j["cameras"].as_array().into_iter().flatten() {
            let name = cam["name"].as_str().unwrap_or("view");
            if views.as_ref().is_some_and(|v| !v.iter().any(|n| n == name)) {
                continue;
            }
            let p3 = |k: &str| {
                let a = &cam[k];
                Point3::new(a[0].as_f64().unwrap_or(0.0) * M, -a[1].as_f64().unwrap_or(0.0) * M, a[2].as_f64().unwrap_or(0.0) * M)
            };
            let (eye, target) = (p3("eye"), p3("target"));
            // An October afternoon; the roof-off view at midday, to see into the court hall.
            let mut light = if name == "clubhouse_inside" { Light::sun_at(160.0, 52.0) } else { Light::sun_at(150.0, 30.0) };
            light.shadow_px = 8192;
            let r = if name == "aerial" { (eye - target).norm() / M * 1.2 } else { 160.0 };
            light.shadow_focus = Some((V::new(target.x / M - r, target.y / M - r, -20.0) * M, V::new(target.x / M + r, target.y / M + r, 120.0) * M));
            let cam_ = Camera::Persp { eye, target, up: V::z(), fov_deg: cam["fov"].as_f64().unwrap_or(50.0), w: 1600, h: 1000 };
            let file = if name == "aerial" { format!("conference_{region}.png") } else { format!("conference_{region}_{name}.png") };
            let t = std::time::Instant::now();
            let out = run_dir.join(&file);
            scene::render_scene(if name == "clubhouse_inside" { &open } else { &all }, &cam_, &light, 2, &out)?;
            if let Err(e) = std::fs::copy(&out, docs.join(&file)) {
                println!("    (not copied to docs/pass3: {e})");
            }
            println!("  {file} ({:.1} s)", t.elapsed().as_secs_f64());
        }
    }
    Ok(())
}

fn village_tris(v: &Village) -> usize {
    let n = |m: &IndexedMesh| m.faces.len();
    n(&v.base) + n(&v.body) + v.tones.iter().map(n).sum::<usize>() + n(&v.trim) + n(&v.windows) + n(&v.doors) + n(&v.roofs)
        + n(&v.blades) + n(&v.stems) + n(&v.purple) + n(&v.yellow) + n(&v.centres) + v.meadow.iter().map(n).sum::<usize>()
        + v.small.iter().map(n).sum::<usize>() + n(&v.pavers) + n(&v.sward) + n(&v.hedge) + n(&v.shrub) + n(&v.white)
}
