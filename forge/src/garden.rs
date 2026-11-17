//! Pass 3c: the winter garden, on the campus's edge facing the town (D9).
//!
//! Fallingwater's principles, applied to this site and drawn fresh:
//! - horizontal trays of light ochre concrete that cantilever over water, crossing each other;
//! - vertical masses of local sandstone, rough and coursed, every stone its own length, course
//!   height and set-out (the stone a robot would place from a scan, as ETH's autonomous excavator
//!   placed irregular boulders in 2023);
//! - glass running between the trays and turning the corners: the winter garden's rooms;
//! - water under and in front of it: two pools stepping down over a stone ledge.
//!
//! It is built against the data hall's south face: one stone hall with its dry coolers in rows on
//! the roof behind a 3 m stone parapet. A stone hearth tower climbs the hall's face where the data
//! center's warm water comes in; the rooms' stone floors are heated by it. East of the hall, the
//! food houses (food.rs, pass 3d); round it all, an arboretum of native trees kept back from every
//! foundation.
//!
//! Frame: millimetres; x east along the frontage, y south toward the town, z up from the upper
//! pool's water. Dimensions below are written in metres and scaled.

use std::path::Path;

use cortenforge::cf_design::Solid;
use cortenforge::mesh::types::IndexedMesh;
use nalgebra::{Point3, Vector3};
use serde_json::json;

use crate::food;
use crate::site;
use crate::village;
use crate::scene::{self, Camera, Light, SLayer, add_box};

/// Reflected in still water at height `zw` (mm): z -> 2 zw - z.
fn add_mirrored_at(out: &mut IndexedMesh, m: &IndexedMesh, zw: f64) {
    let base = out.vertices.len() as u32;
    out.vertices.extend(m.vertices.iter().map(|p| Point3::new(p.x, p.y, 2.0 * zw - p.z)));
    out.faces.extend(m.faces.iter().map(|f| [f[0] + base, f[2] + base, f[1] + base]));
}

type V = Vector3<f64>;
pub(crate) const M: f64 = 1000.0;

/// A small, seeded generator (xorshift64*), so every stone lands the same way every run.
pub(crate) struct Rng(pub(crate) u64);

impl Rng {
    pub(crate) fn next(&mut self) -> f64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        (self.0.wrapping_mul(0x2545F4914F6CDD1D) >> 11) as f64 / (1u64 << 53) as f64
    }
    pub(crate) fn range(&mut self, a: f64, b: f64) -> f64 {
        a + (b - a) * self.next()
    }
}

pub(crate) fn b(out: &mut IndexedMesh, lo: [f64; 3], hi: [f64; 3]) {
    add_box(out, V::new(lo[0], lo[1], lo[2]) * M, V::new(hi[0], hi[1], hi[2]) * M);
}

/// Sandstone tones: buff, tan, grey-brown, ochre, pale.
pub const STONE: [[f64; 3]; 5] = [[0.72, 0.61, 0.47], [0.64, 0.55, 0.44], [0.78, 0.67, 0.52], [0.59, 0.52, 0.44], [0.74, 0.62, 0.43]];

/// Coursed rough sandstone over a rectangular mass (m): a core, and on each exposed face
/// (-x, +x, -y, +y) stones in courses 60-220 mm high, 0.3-1.5 m long, each standing 0-45 mm
/// proud of the face, with 10 mm joints; the top capped by flat stones. Returns the stone count.
fn stone_mass(out: &mut [IndexedMesh; 5], rng: &mut Rng, lo: [f64; 3], hi: [f64; 3], faces: [bool; 4]) -> usize {
    stone_mass_s(out, rng, lo, hi, faces, 1.0)
}

/// As `stone_mass`, with every stone's course height and length scaled by `k`.
pub(crate) fn stone_mass_s(out: &mut [IndexedMesh; 5], rng: &mut Rng, lo: [f64; 3], hi: [f64; 3], faces: [bool; 4], k: f64) -> usize {
    let j = 0.010 * k.sqrt();
    b(&mut out[0], [lo[0] + 0.03, lo[1] + 0.03, lo[2]], [hi[0] - 0.03, hi[1] - 0.03, hi[2] - 0.02]);
    let mut n = 0;
    let mut z = lo[2];
    while z < hi[2] - 0.02 {
        let h = (k * if rng.next() < 0.25 { rng.range(0.05, 0.09) } else { rng.range(0.09, 0.22) }).min(hi[2] - z);
        for (fi, on) in faces.iter().enumerate() {
            if !on {
                continue;
            }
            let along_x = fi >= 2;
            let (a0, a1) = if along_x { (lo[0], hi[0]) } else { (lo[1], hi[1]) };
            let mut a = a0 - rng.range(0.0, 0.6 * k); // stagger the joints course to course
            while a < a1 {
                let len = k * rng.range(0.3, 1.5);
                let (s0, s1) = (a.max(a0), (a + len - j).min(a1));
                if s1 - s0 > 0.05 {
                    let proud = rng.range(0.0, 0.045);
                    let c = (rng.next() * 5.0) as usize % 5;
                    let (zl, zh) = (z + j, z + h);
                    let (l, hh) = match fi {
                        0 => ([lo[0] - proud, s0, zl], [lo[0] + 0.25, s1, zh]),
                        1 => ([hi[0] - 0.25, s0, zl], [hi[0] + proud, s1, zh]),
                        2 => ([s0, lo[1] - proud, zl], [s1, lo[1] + 0.25, zh]),
                        _ => ([s0, hi[1] - 0.25, zl], [s1, hi[1] + proud, zh]),
                    };
                    b(&mut out[c], l, hh);
                    n += 1;
                }
                a += len;
            }
        }
        z += h;
    }
    // Cap stones.
    let mut x = lo[0];
    while x < hi[0] - 0.05 {
        let len = (k * rng.range(0.6, 1.4)).min(hi[0] - x);
        b(&mut out[(rng.next() * 5.0) as usize % 5], [x, lo[1] - 0.02, hi[2] - 0.02], [x + len - j, hi[1] + 0.02, hi[2] + rng.range(0.06, 0.10)]);
        x += len;
        n += 1;
    }
    n
}

/// A slab with rounded edges (m), meshed by CortenForge's adaptive mesher.
fn rounded(lo: [f64; 3], hi: [f64; 3], r: f64, tol_mm: f64) -> IndexedMesh {
    let (lo, hi) = (V::new(lo[0], lo[1], lo[2]) * M, V::new(hi[0], hi[1], hi[2]) * M);
    let half = (hi - lo) / 2.0 - V::repeat(r * M);
    Solid::cuboid(half).round(r * M).translate((hi + lo) / 2.0).mesh_adaptive_par(tol_mm).geometry
}

pub(crate) fn append(out: &mut IndexedMesh, m: &IndexedMesh) {
    scene::add_moved(out, m, V::zeros());
}

/// A tree: a trunk and a crown of lumps inside an ellipsoid `wf` x h wide and `zf` x h tall
/// (round crowns ~0.32 / 0.27; tall ovals such as tulip poplar ~0.19 / 0.36).
pub(crate) fn tree(trunk: &mut IndexedMesh, crowns: &mut IndexedMesh, shade: &mut IndexedMesh, rng: &mut Rng, x: f64, y: f64, z0: f64, h: f64,
                   wf: f64, zf: f64) {
    let r = rng.range(0.18, 0.3);
    b(trunk, [x - r, y - r, z0], [x + r, y + r, z0 + h * 0.62]);
    // The crown: a cluster of lumps (spheres) inside an ellipsoid, unioned, so it reads as foliage.
    let c = V::new(x, y, z0 + h * 0.66) * M;
    let (rw, rz) = (h * wf * rng.range(0.85, 1.12) * M, h * zf * M);
    let (mut s, mut d): (Option<Solid>, Option<Solid>) = (None, None);
    for k in 0..40 {
        let (u, v, w) = loop {
            let q = (rng.range(-1.0, 1.0), rng.range(-1.0, 1.0), rng.range(-1.0, 1.0));
            if q.0 * q.0 + q.1 * q.1 + q.2 * q.2 <= 1.0 {
                break q;
            }
        };
        let r = rw * rng.range(0.22, 0.36);
        let lump = Solid::sphere(r).translate(c + V::new(u * rw * 0.8, v * rw * 0.8, w * rz * 0.78));
        if k % 3 == 0 {
            d = Some(match d { Some(t) => t.union(lump), None => lump });
        } else {
            s = Some(match s { Some(t) => t.union(lump), None => lump });
        }
    }
    let tol = 180.0 * (h / 15.0).max(1.0);
    append(crowns, &s.expect("lumps").mesh_adaptive_par(tol).geometry);
    append(shade, &d.expect("lumps").mesh_adaptive_par(tol).geometry);
}

pub struct Garden {
    pub stone: [IndexedMesh; 5],
    pub concrete: IndexedMesh,
    pub glass: IndexedMesh,
    pub sash: IndexedMesh,
    pub floor: IndexedMesh,
    pub ground: IndexedMesh,
    pub yard: IndexedMesh,
    pub coolers: IndexedMesh,
    pub fans: IndexedMesh,
    pub halls: IndexedMesh,
    pub roofs: IndexedMesh,
    pub water: IndexedMesh,
    pub water_low: IndexedMesh,
    pub falls: IndexedMesh,
    pub trunks: IndexedMesh,
    pub crowns: Vec<IndexedMesh>,
    pub crowns_dark: Vec<IndexedMesh>,
    pub crown_colours: Vec<[f64; 3]>,
    pub plants: IndexedMesh,
    pub food: food::Houses,
    pub village: Option<village::Village>,
    pub site: Option<site::Drawn>,
    pub view: (f64, f64, f64, f64),
    pub stones: usize,
    pub areas: serde_json::Value,
}

pub fn build(spec: &food::Spec, vspec: Option<&village::Spec>, pl: Option<&site::Plan>) -> Garden {
    let mut rng = Rng(0x9E3779B97F4A7C15);
    let mut stone: [IndexedMesh; 5] = Default::default();
    let mut concrete = IndexedMesh::new();
    let (mut glass, mut sash, mut floor, mut ground) = (IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new());
    let (mut yard, mut coolers, mut fans, mut halls) = (IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new());
    let mut roofs = IndexedMesh::new();
    let (mut water, mut falls, mut trunks, mut plants) = (IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new());
    let mut water_low = IndexedMesh::new();
    let ns = spec.trees.len();
    let mut crowns: Vec<IndexedMesh> = (0..ns).map(|_| IndexedMesh::new()).collect();
    let mut crowns_dark: Vec<IndexedMesh> = (0..ns).map(|_| IndexedMesh::new()).collect();
    let mut n = 0;

    // --- The land and the water: upper ground +0.2 and the upper pool at 0 north of the ledge
    // (y < 20); lower ground -2.2 and the lower pool at -2.4 south of it: the water falls 2.4 m.
    let pools = [([-4.0, 1.0], [52.0, 18.0]), ([8.0, 20.0], [62.0, 34.0])];
    let (gx0, gx1, gy0, gy1) = (-60.0, 130.0, -3.0, 110.0);
    let top = |y: f64| if y < 20.0 { 0.2 } else { -2.2 };
    let mut y = gy0;
    while y < gy1 {
        let mut x = gx0;
        while x < gx1 {
            let inside = pools.iter().any(|(lo, hi)| x + 1.0 > lo[0] && x + 1.0 < hi[0] && y + 1.0 > lo[1] && y + 1.0 < hi[1]);
            let ledge = x + 1.0 > 14.0 && x + 1.0 < 40.0 && y + 1.0 > 18.0 && y + 1.0 < 20.0;
            if !inside && !ledge {
                let t = top(y + 1.0);
                b(&mut ground, [x, y, t - 0.6], [x + 2.0, y + 2.0, t]);
            }
            x += 2.0;
        }
        y += 2.0;
    }
    // Ground out to the horizon round the site.
    let far = 3000.0;
    for (lo, hi) in [([-far, -far, -0.6], [gx0, 20.0, 0.2]), ([-far, 20.0, -2.8], [gx0, far, -2.2]), ([gx1, -far, -0.6], [far, 20.0, 0.2]),
                     ([gx1, 20.0, -2.8], [far, far, -2.2]), ([gx0, -far, -0.6], [gx1, gy0, 0.2]), ([gx0, gy1, -2.8], [gx1, far, -2.2])] {
        b(&mut ground, lo, hi);
    }
    // The step continues beyond the site as earth.
    b(&mut ground, [-far, 19.4, -2.8], [gx0, 20.0, 0.2]);
    b(&mut ground, [gx1, 19.4, -2.8], [far, 20.0, 0.2]);
    // The step in the land along y = 20, in stone, either side of the ledge.
    n += stone_mass(&mut stone, &mut rng, [-60.0, 19.4, -2.8], [14.0, 20.0, 0.2], [false, false, false, true]);
    n += stone_mass(&mut stone, &mut rng, [40.0, 19.4, -2.8], [130.0, 20.0, 0.2], [false, false, false, true]);
    // Water surfaces, and the falling water over the ledge (y = 20) into the lower pool.
    b(&mut water, [-4.0, 1.0, -0.02], [52.0, 18.0, 0.0]);
    b(&mut water_low, [8.0, 20.0, -2.42], [62.0, 34.0, -2.4]);
    b(&mut falls, [14.0, 20.0, -2.4], [40.0, 20.08, -0.02]);
    // The ledge the water spills over, and the lower pool's stone banks.
    n += stone_mass(&mut stone, &mut rng, [14.0, 18.0, -2.8], [40.0, 19.95, -0.06], [false, false, false, true]);
    n += stone_mass(&mut stone, &mut rng, [8.0, 34.0, -2.9], [62.0, 34.6, -2.12], [false, false, true, false]);
    n += stone_mass(&mut stone, &mut rng, [7.4, 20.0, -2.9], [8.0, 34.6, -2.12], [false, true, false, false]);
    n += stone_mass(&mut stone, &mut rng, [62.0, 20.0, -2.9], [62.6, 34.6, -2.12], [true, false, false, false]);

    // --- The bluff: the data hall's stone base along its whole south face; the garden is built
    // against it.
    n += stone_mass(&mut stone, &mut rng, [-30.0, -3.0, -0.6], [92.0, 0.0, 8.0], [true, true, false, true]);
    n += stone_mass(&mut stone, &mut rng, [11.0, -3.0, 8.0], [35.0, 0.0, 9.0], [true, true, false, true]); // behind the upper room
    n += stone_mass(&mut stone, &mut rng, [-30.0, 0.0, 0.2], [-4.0, 2.4, 3.2], [true, true, false, true]); // lower ledges
    n += stone_mass(&mut stone, &mut rng, [52.0, 0.0, 0.2], [92.0, 2.0, 2.6], [true, true, false, true]);

    // --- Stone masses: three piers out of the upper pool, and the hearth tower.
    n += stone_mass(&mut stone, &mut rng, [6.0, 0.0, -0.6], [8.5, 12.0, 2.1], [true, true, false, true]);
    n += stone_mass(&mut stone, &mut rng, [22.0, 0.0, -0.6], [24.5, 13.0, 2.1], [true, true, false, true]);
    n += stone_mass(&mut stone, &mut rng, [37.0, 0.0, -0.6], [39.5, 11.0, 2.1], [true, true, false, true]);
    n += stone_mass(&mut stone, &mut rng, [48.0, 0.0, -0.6], [50.5, 10.0, 5.9], [true, true, false, true]); // under level 2's east end
    n += stone_mass(&mut stone, &mut rng, [23.0, -2.5, 0.0], [26.2, 0.7, 21.0], [true, true, false, true]); // up the hall's face, past its roof
    // A stone wall closing the lower room's west end, and one between the upper room's ends.
    n += stone_mass(&mut stone, &mut rng, [7.4, 0.0, 3.0], [8.0, 6.0, 5.9], [true, true, false, true]);

    // --- The trays: light ochre concrete, rounded edges, each crossing the one below.
    let t1 = ([0.0, 0.0, 2.1], [44.0, 18.5, 3.0]); // level 1: east-west, out over the falls; 900 mm deep (ACI 318 deflection)
    let t2 = ([8.0, 0.0, 5.9], [54.0, 12.0, 6.5]); // level 2: shifted east, past the last pier
    let t3 = ([11.0, -0.5, 9.0], [35.5, 9.8, 9.45]); // roof
    for (lo, hi) in [t1, t2, t3] {
        b(&mut concrete, lo, hi);
    }
    // Parapets round the terraces (0.3 m thick, 0.95 m high).
    let par = |c: &mut IndexedMesh, lo: [f64; 3], hi: [f64; 3]| b(c, lo, hi);
    par(&mut concrete, [0.0, 18.2, 3.0], [44.0, 18.5, 3.95]); // level 1, south
    par(&mut concrete, [0.0, 6.0, 3.0], [0.3, 15.6, 3.95]); // level 1, west (open for the stair at its south end)
    par(&mut concrete, [43.7, 12.0, 3.0], [44.0, 18.5, 3.95]); // level 1, east
    par(&mut concrete, [34.0, 11.7, 6.5], [54.0, 12.0, 7.45]); // level 2, south of the east terrace
    par(&mut concrete, [53.7, 0.0, 6.5], [54.0, 12.0, 7.45]); // level 2, east
    // Trellis over the east terrace: slender beams on a beam along y = 10.4.
    b(&mut concrete, [35.5, 10.2, 9.0], [53.0, 10.6, 9.4]);
    let mut x = 36.4;
    while x < 53.0 {
        b(&mut concrete, [x, -0.2, 9.0], [x + 0.22, 10.6, 9.4]);
        x += 1.25;
    }
    // A stair hung from level 1 down to a landing on the ledge, its steps on two steel rods.
    for k in 0..14 {
        let z = 3.0 - 0.2 * (k + 1) as f64;
        let x0 = -0.24 - 0.2 * k as f64;
        b(&mut concrete, [x0, 15.8, z - 0.05], [x0 + 0.24, 17.8, z]);
    }
    for yr in [15.85, 17.75] {
        b(&mut sash, [-0.04, yr - 0.02, 0.2], [0.0, yr + 0.02, 3.0]);
    }

    // --- Glass between the trays, turning the corners; deep red steel sash.
    let glass_band = |gl: &mut IndexedMesh, sh: &mut IndexedMesh, x0: f64, x1: f64, y0: f64, y1: f64, z0: f64, z1: f64, sides: [bool; 3]| -> f64 {
        // sides: west (x0), south (y1), east (x1); the north is stone.
        let mut area = 0.0;
        let t = 0.03;
        let mull = |sh: &mut IndexedMesh, lo: [f64; 3], hi: [f64; 3]| b(sh, lo, hi);
        if sides[1] {
            b(gl, [x0, y1 - t, z0], [x1, y1, z1]);
            area += (x1 - x0) * (z1 - z0);
            let mut x = x0 + 1.2;
            while x < x1 - 0.3 {
                mull(sh, [x - 0.03, y1 - 0.08, z0], [x + 0.03, y1 + 0.02, z1]);
                x += 1.2;
            }
            mull(sh, [x0, y1 - 0.08, z0 + 2.1], [x1, y1 + 0.02, z0 + 2.16]);
        }
        for (on, xs) in [(sides[0], x0), (sides[2], x1 - t)] {
            if on {
                b(gl, [xs, y0, z0], [xs + t, y1, z1]);
                area += (y1 - y0) * (z1 - z0);
                let mut y = y0 + 1.2;
                while y < y1 - 0.3 {
                    mull(sh, [xs - 0.05, y - 0.03, z0], [xs + t + 0.05, y + 0.03, z1]);
                    y += 1.2;
                }
                mull(sh, [xs - 0.05, y0, z0 + 2.1], [xs + t + 0.05, y1, z0 + 2.16]);
            }
        }
        area
    };
    let g1 = glass_band(&mut glass, &mut sash, 8.0, 44.0 - 4.0, 0.0, 11.0, 3.0, 5.9, [false, true, true]);
    let g2 = glass_band(&mut glass, &mut sash, 12.0, 34.0, 0.0, 8.5, 6.5, 9.0, [true, true, true]);
    // Stone floors inside (heated), and planting: beds, shrubs and a few small trees.
    b(&mut floor, [8.0, 0.0, 3.0], [40.0, 11.0, 3.04]);
    b(&mut floor, [12.0, 0.0, 6.5], [34.0, 8.5, 6.54]);
    for (x0, x1, y0, y1) in [(10.0, 16.0, 1.0, 3.5), (28.0, 36.0, 1.0, 3.0), (17.0, 21.0, 6.0, 8.5)] {
        n += stone_mass(&mut stone, &mut rng, [x0, y0, 3.04], [x1, y1, 3.55], [true, true, true, true]);
        let mut x = x0 + 0.6;
        while x < x1 - 0.4 {
            let s = Solid::ellipsoid(V::new(0.55, 0.5, rng.range(0.4, 0.9)) * M).translate(V::new(x, rng.range(y0 + 0.5, y1 - 0.5), 3.7) * M);
            append(&mut plants, &s.mesh_adaptive_par(120.0).geometry);
            x += rng.range(0.7, 1.2);
        }
    }
    for (x, y) in [(13.0, 2.2), (32.0, 2.0), (19.0, 7.2)] {
        let (mut cr, mut cd) = (IndexedMesh::new(), IndexedMesh::new());
        tree(&mut trunks, &mut cr, &mut cd, &mut rng, x, y, 3.55, 2.3, 0.30, 0.27);
        append(&mut plants, &cr);
        append(&mut plants, &cd);
    }

    // --- The data hall: one stone building holding the IT, the cooler courts on its roof (the
    // makers' clearances and the walled cells of pass 2d, on the roof deck); the courts' outer
    // walls are its parapet. Stone plinth, stone piers every 7 m with warm panels between, an ochre
    // band at mid-height and a deep ochre overhang at the roof, stone towers rising past the parapet.
    let (hx0, hx1, hy0, hy1, deck) = (-30.0, 92.0, -132.0, -3.0, 14.0);
    n += stone_mass_s(&mut stone, &mut rng, [hx0, hy0, 0.25], [hx1, hy1, 1.4], [true, true, true, false], 1.4);
    b(&mut halls, [hx0 + 0.3, hy0 + 0.3, 1.4], [hx1 - 0.3, hy1 - 0.3, deck - 1.0]);
    let mut x = hx0 + 3.5;
    while x < hx1 - 2.0 {
        n += stone_mass_s(&mut stone, &mut rng, [x - 0.6, hy0 - 0.6, 1.4], [x + 0.6, hy0 + 0.3, deck - 1.0], [true, true, true, false], 1.4);
        n += stone_mass_s(&mut stone, &mut rng, [x - 0.6, hy1 - 0.3, 8.0], [x + 0.6, hy1 + 0.2, deck - 1.0], [true, true, false, true], 1.4);
        x += 7.0;
    }
    let mut y = hy0 + 3.5;
    while y < hy1 - 2.0 {
        n += stone_mass_s(&mut stone, &mut rng, [hx0 - 0.6, y - 0.6, 1.4], [hx0 + 0.3, y + 0.6, deck - 1.0], [true, false, true, true], 1.4);
        n += stone_mass_s(&mut stone, &mut rng, [hx1 - 0.3, y - 0.6, 1.4], [hx1 + 0.6, y + 0.6, deck - 1.0], [false, true, true, true], 1.4);
        y += 7.0;
    }
    b(&mut concrete, [hx0 - 1.0, hy0 - 1.0, 6.6], [hx1 + 1.0, hy1 - 0.3, 7.1]);
    b(&mut concrete, [hx0 - 2.6, hy0 - 2.6, deck - 1.0], [hx1 + 2.6, hy1 + 0.6, deck]);
    b(&mut yard, [hx0, hy0, deck], [hx1, hy1, deck + 0.25]); // the roof deck
    // The coolers on the roof: rows at the makers' spacing, no court walls. A stone parapet 3 m
    // above the deck (just below the fans' discharge, as the makers require) hides them from the
    // ground; the building's own edge screens the homes below (garden.py's rooftop noise check).
    // Sedum in the aisles between the rows.
    let (xd0, xd1, yd0, yd1) = (hx0 + 0.5, hx1 - 0.5, hy0 + 0.5, hy1 - 0.5);
    let z0 = deck + 0.25;
    let par_top = deck + 3.0;
    for (lo, hi, f) in [([xd0, yd0, deck], [xd1, yd0 + 0.4, par_top], [false, false, true, true]),
                        ([xd0, yd1 - 0.4, deck], [xd1, yd1, par_top], [false, false, true, true]),
                        ([xd0, yd0, deck], [xd0 + 0.4, yd1, par_top], [true, true, false, false]),
                        ([xd1 - 0.4, yd0, deck], [xd1, yd1, par_top], [true, true, false, false])] {
        n += stone_mass_s(&mut stone, &mut rng, lo, hi, f, 1.4);
        b(&mut concrete, [lo[0] - 0.06, lo[1] - 0.06, par_top], [hi[0] + 0.06, hi[1] + 0.06, par_top + 0.14]);
    }
    let (row, unit_l, unit_w) = (2.38 + 3.05, 12.01, 2.38);
    let (rows, per_row) = (22, 8);
    let ys = yd1 - 0.4 - 1.52 - ((yd1 - yd0 - 0.8 - 3.04) - (rows as f64 * row - 3.05)) / 2.0;
    let xs = xd0 + 0.4 + ((xd1 - xd0 - 0.8) - (per_row as f64 * (unit_l + 1.83) - 1.83)) / 2.0;
    for r in 0..rows {
        let yc = ys - unit_w - r as f64 * row;
        for k in 0..per_row {
            let xc = xs + k as f64 * (unit_l + 1.83);
            b(&mut coolers, [xc, yc, z0], [xc + unit_l, yc + unit_w, deck + 2.88]);
            for f in 0..10 {
                for side in 0..2 {
                    let fx = xc + 0.35 + f as f64 * 1.18;
                    let fy = yc + 0.25 + side as f64 * 1.12;
                    b(&mut fans, [fx, fy, deck + 2.88], [fx + 0.9, fy + 0.9, deck + 2.92]);
                }
            }
        }
        if r + 1 < rows {
            b(&mut roofs, [xd0 + 0.6, yc - 3.05 + 0.3, deck + 0.25], [xd1 - 0.6, yc - 0.3, deck + 0.33]);
        }
    }
    // Towers: corners and mid-sides (stairs, electrical rooms), rising past the parapet.
    let (xm, ym) = ((hx0 + hx1) / 2.0, (hy0 + hy1) / 2.0);
    for (tx, ty) in [(hx0 - 1.5, hy0 - 1.5), (hx1 - 4.5, hy0 - 1.5), (hx0 - 1.5, hy1 - 4.5), (hx1 - 4.5, hy1 - 4.5),
                     (xm - 3.0, hy0 - 1.5), (hx0 - 1.5, ym - 3.0), (hx1 - 4.5, ym - 3.0)] {
        n += stone_mass_s(&mut stone, &mut rng, [tx, ty, 0.25], [tx + 6.0, ty + 6.0, deck + 7.0], [true, true, true, true], 1.4);
        b(&mut concrete, [tx - 0.8, ty - 0.8, deck + 7.0], [tx + 6.8, ty + 6.8, deck + 7.5]);
    }

    // --- The food houses (pass 3d), east of the hall past a belt of the arboretum, and the
    // arboretum: native trees in groves, each species kept back from every foundation by its own
    // distance (params/food.yaml via food.json), none between buildings, clear of the views.
    let reach = spec.trees.iter().map(|t| t.setback).fold(10.0, f64::max);
    let (x_food, y_food, z_food) = match pl.and_then(|p| p.rect("greenhouse")) {
        Some(r) => {
            let w = ((spec.ha * 1e4).sqrt() / spec.bay).ceil().max(4.0) * spec.bay;
            ((r[0] + r[1]) / 2.0 - w / 2.0, r[3] - 20.0, site::ground_at(0.0, r[3] - 20.0))
        }
        None => (hx1 + 2.0 * reach + 12.0, 0.0, 0.2),
    };
    let (fh, nf) = food::houses(spec, &mut stone, &mut concrete, &mut rng, x_food, y_food, z_food, hx1 + 1.5, -40.0);
    n += nf;
    let (fx0, fx1, fy0, fy1) = fh.block;
    let mut built: Vec<(f64, f64, f64, f64)> = vec![(hx0 - 1.5, hx1 + 1.5, hy0 - 1.5, hy1), (-4.0, 62.6, -3.0, 34.6), (-30.0, 92.0, -3.0, 3.0),
                                                   (fx0, fx1, fy0, fy1), fh.head];
    // The neighbourhood (pass 3e), if `brownfield village` has written its plan.
    let vg = vspec.map(|vs| {
        let (vg, nv) = village::build(vs, &mut stone, &mut concrete, &mut rng);
        n += nv;
        vg
    });
    let mut vg = vg;
    if let (Some(vg), None) = (&mut vg, pl) {
        let hx = (fh.head.0 + fh.head.1) / 2.0;
        b(&mut vg.plaza, [60.0, 86.0, -2.2], [hx + 2.0, 92.0, -2.15]);
        b(&mut vg.plaza, [hx - 3.0, fh.head.3, -2.2], [hx + 3.0, 92.0, -2.15]);
    }
    if let Some(vg) = &vg {
        built.extend(vg.rects.iter().cloned());
    }
    // The site plan's roads, walks, hub, delivery building, crossings and planters (D12).
    let sd = pl.map(|p| {
        let (d, ns) = site::draw(p, &mut stone, &mut rng);
        n += ns;
        d
    });
    if let Some(d) = &sd {
        built.extend(d.rects.iter().cloned());
    }
    let eyes: Vec<(f64, f64)> = views(pl, vspec, &fh).iter().map(|v| (v.1.x / M, v.1.y / M)).collect();
    let groves = [(-110.0, 10.0), ((hx1 + fx0) / 2.0, -70.0), (210.0, 200.0), (-75.0, -20.0), (220.0, 90.0), (-75.0, -110.0),
                  ((fx0 + fx1) / 2.0, fh.head.3 + 60.0), (30.0, hy0 - 60.0), (-330.0, 230.0), (30.0, 460.0)];
    let mut placed = food::arboretum(spec, &mut trunks, &mut crowns, &mut crowns_dark, &mut rng, &built, &eyes, &groves,
                                     |_x: f64, y: f64| if y < 20.0 { 0.2 } else { -2.2 });
    // Big trees on the neighbourhood's greens, each species only where its own root setback from every
    // house holds (the same rule as the arboretum).
    if let Some(vs) = vspec {
        let gx: Vec<(f64, f64)> = vs.greens.iter()
            .flat_map(|g| { let ym = (g[2] + g[3]) / 2.0; (0..5).map(move |k| (g[0] + 20.0 + k as f64 * (g[1] - g[0] - 40.0) / 4.0, ym)) })
            .collect();
        if !gx.is_empty() {
            // Species whose setback fits the green's clear distance to the nearest houses, six at each spot.
            let clear = vs.greens.first().map(|g| (g[3] - g[2]) / 2.0 + vs.house_d.min(12.0)).unwrap_or(20.0);
            let mut extra = vec![0; spec.trees.len()];
            for c in &gx {
                let sub = food::Spec { ha: spec.ha, crop: spec.crop.clone(), bay: spec.bay, gutter: spec.gutter, roof_deg: spec.roof_deg,
                    trees: spec.trees.iter().map(|t| food::TreeSpec { name: t.name.clone(), height: t.height, form: t.form.clone(), colour: t.colour,
                        setback: t.setback, count: if t.setback <= clear { 2 } else { 0 } }).collect() };
                let k = food::arboretum(&sub, &mut trunks, &mut crowns, &mut crowns_dark, &mut rng, &built, &eyes, &vec![*c; sub.trees.len()],
                                        |_x: f64, _y: f64| -2.2);
                for (e, n) in extra.iter_mut().zip(k) {
                    *e += n;
                }
            }
            for (a, b) in placed.iter_mut().zip(extra) {
                *a += b;
            }
        }
    }
    let mut view: (f64, f64, f64, f64) = (hx0.min(-90.0).min(if vg.is_some() { -320.0 } else { -90.0 }), fx1 + 60.0, fy0.min(hy0) - 80.0,
                    if vg.is_some() { 470.0 } else { 140.0 });
    if let Some(p) = pl {
        for (_, r, _) in &p.modules {
            view = (view.0.min(r[0] - 60.0), view.1.max(r[1] + 60.0), view.2.min(r[2] - 80.0), view.3.max(r[3] + 20.0));
        }
    }
    let trees_json: Vec<serde_json::Value> = spec.trees.iter().zip(&placed)
        .map(|(t, k)| json!({"name": t.name, "placed": k, "height_m": t.height, "setback_m": t.setback})).collect();

    let areas = json!({
        "glass_m2": {"level1": g1, "level2": g2},
        "floor_m2": {"level1": 32.0 * 11.0, "level2": 22.0 * 8.5},
        "height_m": {"level1": 2.9, "level2": 2.5},
        "roof_m2": {"level1_under_level2": 32.0 * 11.0, "level2_roof": 22.0 * 8.5},
        "terraces_m2": 44.0 * 18.5 - 32.0 * 11.0 + 46.0 * 12.0 - 22.0 * 8.5,
        "trays": {"level1": {"lo": t1.0, "hi": t1.1}, "level2": {"lo": t2.0, "hi": t2.1}, "roof": {"lo": t3.0, "hi": t3.1}},
        "cantilevers_m": {"level1_south_beyond_piers": 18.5 - 13.0, "level2_east_beyond_pier": 54.0 - 50.5},
        "level1_tray_depth_m": 0.9,
        "food_houses": {"floor_m2": fh.floor_m2, "block": [fx0, fx1, fy0, fy1], "head_house": [fh.head.0, fh.head.1, fh.head.2, fh.head.3]},
        "arboretum": trees_json,
    });
    let crown_colours = spec.trees.iter().map(|t| t.colour).collect();
    Garden { stone, concrete, glass, sash, floor, ground, yard, coolers, fans, halls, roofs, water, water_low, falls, trunks, crowns, crowns_dark,
             crown_colours, plants, food: fh, village: vg, site: sd, view, stones: n, areas }
}

/// A view: file name, eye and target (mm), field of view, exposure.
pub struct View(pub &'static str, pub Point3<f64>, pub Point3<f64>, pub f64, pub f64);

/// The views, each placed from where the plan puts its module (the garden and the hall are fixed).
fn views(pl: Option<&site::Plan>, vspec: Option<&village::Spec>, fh: &food::Houses) -> Vec<View> {
    let p = |x: f64, y: f64, z: f64| Point3::new(x * M, y * M, z * M);
    let (fx0, fx1, fy0, fy1) = fh.block;
    let (fxm, fym) = ((fx0 + fx1) / 2.0, (fy0 + fy1) / 2.0);
    let hm = (fh.head.0 + fh.head.1) / 2.0;
    let fz = if fy1 < 20.0 { 0.2 } else { -2.2 };
    let mut v = vec![
        View("garden_falls.png", p(36.0, 46.0, -0.6), p(23.0, 10.0, 3.6), 52.0, 1.0),
        View("garden_hero.png", p(62.0, 58.0, 4.0), p(24.0, 8.0, 3.0), 46.0, 1.0),
        View("garden_inside.png", p(11.0, 8.6, 4.7), p(40.0, 5.5, 3.9), 70.0, 1.7),
        View("garden_aerial.png", p(105.0, 90.0, 62.0), p(24.0, -12.0, 0.0), 46.0, 1.0),
        View("campus_aerial.png", p(190.0, 90.0, 120.0), p(30.0, -70.0, 0.0), 50.0, 1.0),
        View("campus_hall.png", p(150.0, -40.0, 1.7), p(92.0, -80.0, 10.0), 56.0, 1.0),
        View("campus_front.png", p(-30.0, 95.0, 14.0), p(28.0, -25.0, 8.0), 52.0, 1.0),
        View("campus_food.png", p(fx1 + 260.0, fy1 + 330.0, 330.0), p((31.0 + fxm) / 2.0, fym, 0.0), 50.0, 1.0),
        View("food_inside.png", p(fxm + 1.2, fy1 - 4.0, fz + 1.8), p(fxm + 1.0, fy1 - 60.0, fz + 2.4), 68.0, 1.3),
        View("food_head.png", p(hm - 40.0, fh.head.3 + 55.0, fz - 0.6), p(hm, fy1 + 6.0, fz + 3.8), 56.0, 1.0),
        View("arboretum.png", p(-130.0, 210.0, -0.5), p(30.0, 40.0, 6.0), 60.0, 1.0),
    ];
    let r = |n: &str, d: [f64; 4]| pl.and_then(|q| q.rect(n)).unwrap_or(d);
    if let Some(vs) = vspec {
        let homes = r("neighbourhood", [-68.0, 128.0, 147.0, 450.0]);
        let sq = r("square", [0.0, 60.0, 60.0, 120.0]);
        let c = r("community center", [72.0, 162.0, 12.0, 140.0]);
        let fl = r("field and loop", [-207.0, -93.0, 34.0, 186.0]);
        let gd = r("winter garden", [-4.0, 63.0, -3.0, 35.0]);
        let (hcx, sqx, sqy) = ((homes[0] + homes[1]) / 2.0, (sq[0] + sq[1]) / 2.0, (sq[2] + sq[3]) / 2.0);
        let (fcx, fcy) = ((fl[0] + fl[1]) / 2.0, (fl[2] + fl[3]) / 2.0);
        let street = vs.streets_y.iter().cloned().min_by(|a, b| (a - homes[2] - 124.5).abs().total_cmp(&(b - homes[2] - 124.5).abs()))
            .unwrap_or(homes[2] + 124.5);
        let green = vs.greens.first().map(|g| (g[2] + g[3]) / 2.0).unwrap_or(homes[2] + 64.0);
        // The neighbourhood from the air: over its town side, toward its middle.
        let ms = [homes, sq, c, fl];
        let (mx, my) = (ms.iter().map(|q| q[0] + q[1]).sum::<f64>() / 8.0, ms.iter().map(|q| q[2] + q[3]).sum::<f64>() / 8.0);
        v.extend([
            View("campus_village.png", p(mx + 350.0, my + 440.0, 330.0), p(mx, my, 0.0), 50.0, 1.0),
            View("village_balcony.png", p(hcx + 10.0, homes[2] + 0.5, 5.3), p((gd[0] + gd[1]) / 2.0, gd[3] - 5.0, 2.0), 62.0, 1.0),
            View("village_square.png", p(sqx + 18.0, sqy + 24.0, -0.5), p(sqx - 8.0, sqy - 45.0, 2.0), 60.0, 1.0),
            View("village_street.png", p(hcx + 30.0, street, -0.5), p(hcx - 70.0, street, 2.5), 60.0, 1.0),
            View("village_center.png", p(c[0] + 68.0, c[2] + 120.0, 3.5), p(c[0] + 24.0, c[2] + 73.0, -2.2), 72.0, 1.5),
            View("village_green.png", p(homes[0] + 18.0, green, -0.6), p(homes[0] + 108.0, green + 1.8, 0.8), 62.0, 1.0),
            View("village_climbing.png", p(c[0] + 38.0, c[2] + 32.0, -0.6), p(c[0] + 28.0, c[2] + 9.0, 0.6), 66.0, 1.6),
            View("village_fields.png", p(fcx + 30.0, fcy + 95.0, 1.5), p(fcx, fcy - 15.0, 0.0), 62.0, 1.0),
        ]);
    }
    if let Some(q) = pl {
        // The whole plan from the air, from the south-east, toward its middle.
        let (mut x0, mut x1, mut y0, mut y1) = (f64::MAX, f64::MIN, f64::MAX, f64::MIN);
        for (_, r, _) in &q.modules {
            (x0, x1, y0, y1) = (x0.min(r[0]), x1.max(r[1]), y0.min(r[2]), y1.max(r[3]));
        }
        let (cx, cy, d) = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (x1 - x0).max(y1 - y0));
        v.push(View("site_aerial.png", p(cx - 0.10 * d, cy + 0.85 * d, 0.45 * d), p(cx + 0.02 * d, cy - 0.05 * d, 0.0), 46.0, 1.0));
        if let Some(h) = q.rect("mobility hub") {
            let (hx, hy) = ((h[0] + h[1]) / 2.0, (h[2] + h[3]) / 2.0);
            let z = site::ground_at(hx, hy);
            v.push(View("site_hub.png", p(hx + 70.0, h[3] + 60.0, z + 18.0), p(hx, hy, z), 56.0, 1.0));
        }
    }
    v
}

pub fn run(root: &Path) -> std::io::Result<()> {
    let t0 = std::time::Instant::now();
    let spec = food::spec(root);
    let vspec = village::spec(root);
    if vspec.is_none() {
        println!("  (no out/pass3/village.json yet: run `brownfield village` for the neighbourhood)");
    }
    let pl = site::plan(root);
    if pl.is_none() {
        println!("  (no out/pass3/site.json yet: run `brownfield site` for the site plan)");
    }
    let g = build(&spec, vspec.as_ref(), pl.as_ref());
    let tris = |m: &IndexedMesh| m.faces.len();
    let total: usize = g.stone.iter().map(tris).sum::<usize>() + tris(&g.concrete) + tris(&g.glass) + tris(&g.sash) + tris(&g.ground)
        + tris(&g.yard) + tris(&g.coolers) + tris(&g.fans) + g.crowns.iter().chain(g.crowns_dark.iter()).map(tris).sum::<usize>() + tris(&g.plants)
        + tris(&g.food.glass) + tris(&g.food.frame) + tris(&g.food.crops) + tris(&g.food.lamps);
    println!("garden: {} stones, {} triangles, built in {:.1} s", g.stones, total, t0.elapsed().as_secs_f64());

    // Reflections: everything standing above the water, mirrored at each pool's water line; each
    // set shows only where its own pool's water does (the renderer's stencil).
    let reflect = |zw: f64| -> Vec<IndexedMesh> {
        let ns = g.crowns.len();
        let mut v: Vec<IndexedMesh> = (0..8 + 2 * ns).map(|_| IndexedMesh::new()).collect();
        for (i, m) in g.stone.iter().enumerate() {
            add_mirrored_at(&mut v[i], m, zw);
        }
        add_mirrored_at(&mut v[5], &g.concrete, zw);
        add_mirrored_at(&mut v[6], &g.sash, zw);
        add_mirrored_at(&mut v[7], &g.trunks, zw);
        for (i, m) in g.crowns.iter().chain(g.crowns_dark.iter()).enumerate() {
            add_mirrored_at(&mut v[8 + i], m, zw);
        }
        v
    };
    let refl = [reflect(0.0), reflect(-2.4 * M)];
    const CONCRETE: [f64; 3] = [0.94, 0.85, 0.66];
    const SASH: [f64; 3] = [0.46, 0.17, 0.12];
    let mut layers: Vec<SLayer> = Vec::new();
    for (i, m) in g.stone.iter().enumerate() {
        layers.push(SLayer::solid(m, STONE[i]));
    }
    layers.push(SLayer::solid(&g.concrete, CONCRETE));
    layers.push(SLayer::solid(&g.sash, SASH));
    layers.push(SLayer::solid(&g.floor, [0.72, 0.64, 0.53]));
    layers.push(SLayer::solid(&g.ground, [0.44, 0.50, 0.30]).no_shadow());
    layers.push(SLayer::solid(&g.yard, [0.66, 0.63, 0.58]).no_shadow());
    layers.push(SLayer::solid(&g.coolers, [0.70, 0.69, 0.65]));
    layers.push(SLayer::solid(&g.fans, [0.20, 0.21, 0.23]));
    layers.push(SLayer::solid(&g.halls, [0.80, 0.73, 0.60]));
    layers.push(SLayer::solid(&g.roofs, [0.40, 0.50, 0.28]));
    layers.push(SLayer::solid(&g.trunks, [0.30, 0.24, 0.19]));
    for (i, m) in g.crowns.iter().enumerate() {
        layers.push(SLayer::solid(m, g.crown_colours[i]).smooth());
    }
    for (i, m) in g.crowns_dark.iter().enumerate() {
        layers.push(SLayer::solid(m, g.crown_colours[i].map(|c| c * 0.8)).smooth());
    }
    layers.push(SLayer::solid(&g.food.frame, [0.84, 0.85, 0.84]));
    layers.push(SLayer::solid(&g.food.crops, [0.32, 0.55, 0.25]));
    layers.push(SLayer::solid(&g.food.lamps, [1.0, 0.88, 0.66]).no_shadow());
    layers.push(SLayer::solid(&g.food.paving, [0.70, 0.66, 0.58]).no_shadow());
    if let Some(v) = &g.village {
        village::layers(v, &mut layers);
    }
    if let Some(d) = &g.site {
        layers.push(SLayer::solid(&d.asphalt, [0.36, 0.36, 0.37]).no_shadow());
        layers.push(SLayer::solid(&d.walks, [0.80, 0.75, 0.66]).no_shadow());
        layers.push(SLayer::solid(&d.lines, [0.95, 0.95, 0.93]).no_shadow());
        layers.push(SLayer::solid(&d.pavers, [0.74, 0.66, 0.54]).no_shadow());
        layers.push(SLayer::solid(&d.concrete, CONCRETE));
        layers.push(SLayer::solid(&d.dark, [0.24, 0.23, 0.22]));
        for (m, c) in d.cars.iter().zip([[0.62, 0.63, 0.64], [0.22, 0.24, 0.28], [0.80, 0.80, 0.78], [0.40, 0.30, 0.26]]) {
            layers.push(SLayer::solid(m, c));
        }
        layers.push(SLayer::solid(&d.planting, [0.32, 0.50, 0.26]).smooth());
        layers.push(SLayer::solid(&d.ramps, [0.44, 0.50, 0.30]));
    }
    layers.push(SLayer::solid(&g.plants, [0.36, 0.55, 0.30]).smooth());
    // Water reflects only part of the light: the reflections are dimmed.
    let dim = |c: [f64; 3]| c.map(|v| v * 0.62);
    for (k, set) in refl.iter().enumerate() {
        let (zw, pool) = (if k == 0 { 0.0 } else { -2.4 * M }, k as u8 + 1);
        for i in 0..5 {
            layers.push(SLayer::solid(&set[i], dim(STONE[i])).mirrored(zw, pool));
        }
        layers.push(SLayer::solid(&set[5], dim(CONCRETE)).mirrored(zw, pool));
        layers.push(SLayer::solid(&set[6], dim(SASH)).mirrored(zw, pool));
        layers.push(SLayer::solid(&set[7], dim([0.30, 0.24, 0.19])).mirrored(zw, pool));
        let ns = g.crowns.len();
        for i in 0..2 * ns {
            let c = g.crown_colours[i % ns].map(|v| if i >= ns { v * 0.8 } else { v });
            layers.push(SLayer::solid(&set[8 + i], dim(c)).smooth().mirrored(zw, pool));
        }
    }
    // Translucent last: glass, the water's skin, the falling water.
    layers.push(SLayer::translucent(&g.glass, [0.70, 0.82, 0.86], 0.28));
    layers.push(SLayer::translucent(&g.food.glass, [0.78, 0.86, 0.88], 0.22));
    if let Some(v) = &g.village {
        village::glass_layer(v, &mut layers);
    }
    layers.push(SLayer::water(&g.water, [0.10, 0.18, 0.20], 0.42, 1));
    layers.push(SLayer::water(&g.water_low, [0.10, 0.18, 0.20], 0.42, 2));
    layers.push(SLayer::translucent(&g.falls, [0.92, 0.95, 0.96], 0.6));

    let docs = root.join("docs/pass3");
    std::fs::create_dir_all(&docs)?;
    let out = root.join("out/pass3");
    std::fs::create_dir_all(&out)?;
    let mut light = Light::sun_at(150.0, 32.0); // an autumn afternoon sun from the south-west
    light.shadow_px = 6144;
    light.shadow_px = 8192;
    let (vx0, vx1, vy0, vy1) = g.view;
    light.shadow_focus = Some((V::new(vx0, vy0, -5.0) * M, V::new(vx1, vy1, 40.0) * M));
    let views: Vec<_> = views(pl.as_ref(), vspec.as_ref(), &g.food).into_iter()
        .map(|v| (v.0, Camera::Persp { eye: v.1, target: v.2, up: V::z(), fov_deg: v.3, w: 1600, h: 1000 }, v.4, false))
        .collect();
    let stamp = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let run_dir = out.join("renders").join(stamp.to_string());
    println!("  renders to {}", run_dir.display());
    for (name, cam, exposure, outline) in &views {
        let t = std::time::Instant::now();
        light.exposure = *exposure;
        light.outline = *outline;
        let rendered = run_dir.join(name);
        std::fs::create_dir_all(rendered.parent().unwrap())?;
        scene::render_scene(&layers, cam, &light, 2, &rendered)?;
        if let Err(e) = std::fs::copy(&rendered, docs.join(name)) {
            println!("    (not copied to docs/pass3: {e}; it is in out/pass3/renders)");
        }
        println!("  {name} ({:.1} s)", t.elapsed().as_secs_f64());
    }
    std::fs::write(out.join("garden.json"), serde_json::to_string_pretty(&json!({
        "source": "forge `garden` (CortenForge 0.9): the winter garden, pass 3c", "stones": g.stones, "triangles": total, "areas": g.areas,
    }))?)?;
    if let Some(vs) = &vspec {
        village::facade_study(root, vs)?;
    }
    println!("garden done ({:.1} s)", t0.elapsed().as_secs_f64());
    Ok(())
}
