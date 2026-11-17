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
//! It is built in its own frame and placed where the site plan puts it (D15: against the community
//! center's west face, onto the square), its back to the building, a stone hearth tower where the
//! data center's warm water comes in; the rooms' stone floors are heated by it. Without a site plan
//! it stands against the data hall's south face, as first drawn.
//!
//! The data hall: one stone hall with its dry coolers in rows on the roof behind a 3 m stone
//! parapet. Its front (D15) is a monument to the machines that keep the town warm: two stone pylons
//! and a pair of bronze doors 14 m high on a stepped base, and before them two warm basins spilling
//! over a ledge into two lower pools, either side of a causeway and a stair to the square. Round the
//! hall, the food houses as its moat (food.rs, pass 3d, D16: the site plan's blocks, a road between
//! them and the hall, the mall through them to the square; east of the hall without a site plan); round
//! it all, an arboretum of native trees kept back from every foundation.
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

/// The forecourt (D15), symmetric about the hall's centre line x = 31: two warm basins on the upper
/// ground either side of the causeway to the great doors (x0, x1, y0, y1), spilling over the ledge at
/// y = 20 into two lower pools; the stair down the step on the axis between them.
const FRONT_UP: [[f64; 4]; 2] = [[0.0, 26.0, 7.0, 18.0], [36.0, 62.0, 7.0, 18.0]];
const FRONT_LOW: [[f64; 4]; 2] = [[0.0, 25.0, 20.0, 34.0], [37.0, 62.0, 20.0, 34.0]];
const FRONT_STAIR: [f64; 4] = [26.0, 36.0, 18.0, 26.0];

/// The garden's own frame: x along its back wall (-4 to 62.6 m), y out from it (-3 to 34.6 m), the
/// way it faces. A quarter-turn about z and a move put it where the plan says.
#[derive(Clone, Copy)]
pub struct Place {
    ox: f64,
    oy: f64,
    c: f64,
    s: f64,
}

impl Place {
    /// Onto the rectangle `r` (m), facing the bearing `faces` (180 south, as first drawn; 270 west).
    pub fn new(r: [f64; 4], faces: i64) -> Place {
        let th = ((faces - 180) as f64).to_radians();
        let (c, s) = (th.cos().round(), th.sin().round());
        let (mut mx, mut my) = (f64::MAX, f64::MAX);
        for (x, y) in [(-4.0, -3.0), (62.6, -3.0), (-4.0, 34.6), (62.6, 34.6)] {
            mx = mx.min(c * x - s * y);
            my = my.min(s * x + c * y);
        }
        Place { ox: r[0] - mx, oy: r[2] - my, c, s }
    }
    /// A point in the garden's frame (m) on the site (m).
    pub fn xy(&self, x: f64, y: f64) -> (f64, f64) {
        (self.ox + self.c * x - self.s * y, self.oy + self.s * x + self.c * y)
    }
    pub fn pt(&self, x: f64, y: f64, z: f64) -> Point3<f64> {
        let (u, v) = self.xy(x, y);
        Point3::new(u * M, v * M, z * M)
    }
    /// A mesh (mm) in the garden's frame, on the site: turned (a rotation, so the faces keep their
    /// winding) and moved.
    pub fn mesh(&self, m: &IndexedMesh) -> IndexedMesh {
        let mut out = m.clone();
        for p in out.vertices.iter_mut() {
            let (x, y) = (p.x, p.y);
            p.x = self.ox * M + self.c * x - self.s * y;
            p.y = self.oy * M + self.s * x + self.c * y;
        }
        out
    }
}

/// Where the plan puts the winter garden (its rectangle and bearing), and its placing.
fn garden_place(pl: Option<&site::Plan>) -> (Place, [f64; 4], i64) {
    let (r, f) = pl.and_then(|p| p.rect("winter garden").map(|r| (r, p.garden_faces))).unwrap_or(([-4.0, 62.6, -3.0, 34.6], 180));
    (Place::new(r, f), r, f)
}

/// The winter garden's meshes in its own frame (m, scaled to mm), its stone count, glass areas and trays.
pub struct GardenParts {
    pub stone: [IndexedMesh; 5],
    pub concrete: IndexedMesh,
    pub glass: IndexedMesh,
    pub sash: IndexedMesh,
    pub floor: IndexedMesh,
    pub ground: IndexedMesh,
    pub water: IndexedMesh,
    pub water_low: IndexedMesh,
    pub falls: IndexedMesh,
    pub plants: IndexedMesh,
    pub trunks: IndexedMesh,
    pub n: usize,
    pub g1: f64,
    pub g2: f64,
    pub trays: [([f64; 3], [f64; 3]); 3],
}

/// The winter garden (pass 3c, D9), in its own frame: its upper level on a stone podium at +0.2 with
/// the upper pool at 0, the lower pool at -2.4 below a ledge at y = 20 (the heights of the site's own
/// step, so the reflections hold wherever it stands). `own_back`: its own stone back wall (against the
/// community center); without it, the hall's bluff is its back. `tower`: the hearth tower's top (m).
fn fallingwater(rng: &mut Rng, own_back: bool, tower: f64) -> GardenParts {
    let mut stone: [IndexedMesh; 5] = Default::default();
    let (mut concrete, mut glass, mut sash, mut floor, mut ground) =
        (IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new());
    let (mut water, mut water_low, mut falls, mut plants, mut trunks) =
        (IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new(), IndexedMesh::new());
    let mut n = 0;

    // --- Its ground: the podium's top at +0.2 round the upper pool, the lower ground (-2.19, just
    // over the site's) west of the lower pool, and a skirt just under the site's ground round its edge.
    let rows: Vec<(f64, f64, f64)> = (0..20).map(|k| (k as f64, k as f64 + 1.0, 0.2))
        .chain((20..34).map(|k| (k as f64, k as f64 + 1.0, -2.19))).chain([(34.0, 34.6, -2.19)]).collect();
    for (y0, y1, t) in rows {
        let cy = (y0 + y1) / 2.0;
        let cut = |x: f64| if t > 0.0 {
            (x > -4.0 && x < 52.0 && cy > 1.0 && cy < 18.0) || (x > 14.0 && x < 40.0 && cy > 18.0)
        } else {
            x > 7.4
        };
        let mut run: Option<f64> = None;
        let mut x = -4.0;
        while x <= 62.6 + 1e-9 {
            let keep = x < 62.6 - 1e-9 && !cut(x + 0.1);
            match (keep, run) {
                (true, None) => run = Some(x),
                (false, Some(x0)) => {
                    b(&mut ground, [x0, y0, t - 0.6], [x.min(62.6), y1, t]);
                    run = None;
                }
                _ => {}
            }
            x += 0.2;
        }
    }
    for (lo, hi) in [([-5.0, -3.0, -2.81], [-4.0, 35.6, -2.21]), ([62.6, -3.0, -2.81], [63.6, 35.6, -2.21]),
                     ([-4.0, 34.6, -2.81], [62.6, 35.6, -2.21])] {
        b(&mut ground, lo, hi);
    }
    // The podium's stone sides, and its south face either side of the ledge.
    n += stone_mass(&mut stone, rng, [-4.6, -3.0, -2.8], [-4.0, 20.0, 0.2], [true, false, false, false]);
    n += stone_mass(&mut stone, rng, [62.6, -3.0, -2.8], [63.2, 20.0, 0.2], [false, true, false, false]);
    n += stone_mass(&mut stone, rng, [-4.6, 19.4, -2.8], [14.0, 20.0, 0.2], [false, false, false, true]);
    n += stone_mass(&mut stone, rng, [40.0, 19.4, -2.8], [63.2, 20.0, 0.2], [false, false, false, true]);
    // Water surfaces, and the falling water over the ledge (y = 20) into the lower pool.
    b(&mut water, [-4.0, 1.0, -0.02], [52.0, 18.0, 0.0]);
    b(&mut water_low, [8.0, 20.0, -2.42], [62.0, 34.0, -2.4]);
    b(&mut falls, [14.0, 20.0, -2.4], [40.0, 20.08, -0.02]);
    // The ledge the water spills over, and the lower pool's stone banks.
    n += stone_mass(&mut stone, rng, [14.0, 18.0, -2.8], [40.0, 19.95, -0.06], [false, false, false, true]);
    n += stone_mass(&mut stone, rng, [8.0, 34.0, -2.9], [62.0, 34.6, -2.12], [false, false, true, false]);
    n += stone_mass(&mut stone, rng, [7.4, 20.0, -2.9], [8.0, 34.6, -2.12], [false, true, false, false]);
    n += stone_mass(&mut stone, rng, [62.0, 20.0, -2.9], [62.6, 34.6, -2.12], [true, false, false, false]);

    // --- Its back: its own stone wall against the community center, or the hall's bluff.
    if own_back {
        n += stone_mass(&mut stone, rng, [-4.6, -3.0, -2.8], [63.2, 0.0, 8.0], [true, true, false, true]);
    }
    n += stone_mass(&mut stone, rng, [11.0, -3.0, 8.0], [35.0, 0.0, 9.0], [true, true, false, true]); // behind the upper room

    // --- Stone masses: three piers out of the upper pool, and the hearth tower.
    n += stone_mass(&mut stone, rng, [6.0, 0.0, -0.6], [8.5, 12.0, 2.1], [true, true, false, true]);
    n += stone_mass(&mut stone, rng, [22.0, 0.0, -0.6], [24.5, 13.0, 2.1], [true, true, false, true]);
    n += stone_mass(&mut stone, rng, [37.0, 0.0, -0.6], [39.5, 11.0, 2.1], [true, true, false, true]);
    n += stone_mass(&mut stone, rng, [48.0, 0.0, -0.6], [50.5, 10.0, 5.9], [true, true, false, true]); // under level 2's east end
    n += stone_mass(&mut stone, rng, [23.0, -2.5, 0.0], [26.2, 0.7, tower], [true, true, false, true]); // where the warm water comes in
    // A stone wall closing the lower room's west end, and one between the upper room's ends.
    n += stone_mass(&mut stone, rng, [7.4, 0.0, 3.0], [8.0, 6.0, 5.9], [true, true, false, true]);

    // --- The trays: light ochre concrete, rounded edges, each crossing the one below.
    let t1 = ([0.0, 0.0, 2.1], [44.0, 18.5, 3.0]); // level 1: east-west, out over the falls; 900 mm deep (ACI 318 deflection)
    let t2 = ([8.0, 0.0, 5.9], [54.0, 12.0, 6.5]); // level 2: shifted east, past the last pier
    let t3 = ([11.0, -0.5, 9.0], [35.5, 9.8, 9.45]); // roof
    for (lo, hi) in [t1, t2, t3] {
        b(&mut concrete, lo, hi);
    }
    // Parapets round the terraces (0.3 m thick, 0.95 m high).
    b(&mut concrete, [0.0, 18.2, 3.0], [44.0, 18.5, 3.95]); // level 1, south
    b(&mut concrete, [0.0, 6.0, 3.0], [0.3, 15.6, 3.95]); // level 1, west (open for the stair at its south end)
    b(&mut concrete, [43.7, 12.0, 3.0], [44.0, 18.5, 3.95]); // level 1, east
    b(&mut concrete, [34.0, 11.7, 6.5], [54.0, 12.0, 7.45]); // level 2, south of the east terrace
    b(&mut concrete, [53.7, 0.0, 6.5], [54.0, 12.0, 7.45]); // level 2, east
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
        n += stone_mass(&mut stone, rng, [x0, y0, 3.04], [x1, y1, 3.55], [true, true, true, true]);
        let mut x = x0 + 0.6;
        while x < x1 - 0.4 {
            let s = Solid::ellipsoid(V::new(0.55, 0.5, rng.range(0.4, 0.9)) * M).translate(V::new(x, rng.range(y0 + 0.5, y1 - 0.5), 3.7) * M);
            append(&mut plants, &s.mesh_adaptive_par(120.0).geometry);
            x += rng.range(0.7, 1.2);
        }
    }
    for (x, y) in [(13.0, 2.2), (32.0, 2.0), (19.0, 7.2)] {
        let (mut cr, mut cd) = (IndexedMesh::new(), IndexedMesh::new());
        tree(&mut trunks, &mut cr, &mut cd, rng, x, y, 3.55, 2.3, 0.30, 0.27);
        append(&mut plants, &cr);
        append(&mut plants, &cd);
    }
    GardenParts { stone, concrete, glass, sash, floor, ground, water, water_low, falls, plants, trunks, n, g1, g2, trays: [t1, t2, t3] }
}

/// The hall's front (D15): a monument to the machines that keep the town warm, in the line of the
/// great waterworks and pumping stations (Fairmount, Abbey Mills) rather than a temple. On a stepped
/// stone base, two stone pylons rise past the hall's towers; between them, in a deep stone reveal
/// under a lintel and a heavy cornice, a pair of bronze doors 10 m wide and 14 m high (for people:
/// the hall's working doors are at its back, on the service side). In front, the
/// forecourt's warm basins (`FRONT_UP`, `FRONT_LOW`). Pedestrians only, inside the stand-off band.
/// Returns the stone count and the basins' open water (m2).
#[allow(clippy::too_many_arguments)]
fn hall_front(stone: &mut [IndexedMesh; 5], concrete: &mut IndexedMesh, bronze: &mut IndexedMesh, floor: &mut IndexedMesh,
              water: &mut IndexedMesh, water_low: &mut IndexedMesh, falls: &mut IndexedMesh, rng: &mut Rng, end_y: f64) -> (usize, f64) {
    let mut n = 0;
    // The stepped base the width of the gateway, and three steps down to the forecourt.
    n += stone_mass(stone, rng, [13.0, -3.0, -0.6], [49.0, 4.4, 0.8], [true, true, false, true]);
    b(&mut stone[2], [13.0, 4.4, -0.6], [49.0, 5.0, 0.6]);
    b(&mut stone[2], [13.0, 5.0, -0.6], [49.0, 5.6, 0.4]);
    // The pylons, 7 m square, to 26.5 m (the hall's towers reach 21 m), capped.
    for x0 in [17.0, 38.0] {
        n += stone_mass_s(stone, rng, [x0, -3.0, 0.8], [x0 + 7.0, 4.0, 26.5], [true, true, false, true], 1.4);
        b(concrete, [x0 - 0.6, -3.0, 26.5], [x0 + 7.6, 4.6, 27.2]);
    }
    // The portal: deep reveals either side of the doors, the head over them, the lintel between the
    // pylons, and the cornice across the gateway.
    n += stone_mass_s(stone, rng, [24.0, -3.0, 0.8], [26.0, 2.0, 14.8], [false, true, false, true], 1.4);
    n += stone_mass_s(stone, rng, [36.0, -3.0, 0.8], [38.0, 2.0, 14.8], [true, false, false, true], 1.4);
    n += stone_mass_s(stone, rng, [24.0, -3.0, 14.8], [38.0, 2.0, 16.0], [false, false, false, true], 1.4);
    n += stone_mass_s(stone, rng, [24.0, -3.0, 16.0], [38.0, 4.0, 19.0], [false, false, false, true], 1.4);
    b(concrete, [16.0, -3.0, 19.0], [46.0, 5.0, 19.9]);
    // The great doors: two bronze leaves, each 5 m by 14 m, in raised panels three across and seven up.
    for (x0, x1) in [(26.0, 30.97), (31.03, 36.0)] {
        b(bronze, [x0, -0.9, 0.8], [x1, -0.6, 14.8]);
        let pw = (x1 - x0 - 0.6) / 3.0;
        for i in 0..3 {
            for j in 0..7 {
                let (px, pz) = (x0 + 0.3 + i as f64 * pw, 1.3 + j as f64 * 1.9);
                b(bronze, [px + 0.12, -0.6, pz], [px + pw - 0.12, -0.52, pz + 1.6]);
            }
        }
    }
    // The causeway from the steps to the stair, paved.
    b(floor, [26.4, 5.6, 0.2], [35.6, 18.0, 0.23]);
    b(floor, [26.0, 26.0, -2.2], [36.0, end_y, -2.17]); // on to the square
    if end_y > 60.0 {
        // The mall between the glass (D16): a walk along each side of it.
        b(floor, [-4.0, 36.0, -2.2], [0.0, end_y, -2.18]);
        b(floor, [62.0, 36.0, -2.2], [66.0, end_y, -2.18]);
    }
    let mut area = 0.0;
    // The warm basins in their stone kerbs, each spilling over its ledge.
    for r in FRONT_UP {
        b(water, [r[0], r[2], -0.02], [r[1], r[3], 0.0]);
        area += (r[1] - r[0]) * (r[3] - r[2]);
        n += stone_mass(stone, rng, [r[0] - 0.4, r[2] - 0.4, -0.6], [r[1] + 0.4, r[2], 0.45], [true, true, true, true]);
        n += stone_mass(stone, rng, [r[0] - 0.4, r[2], -0.6], [r[0], r[3], 0.45], [true, true, false, false]);
        n += stone_mass(stone, rng, [r[1], r[2], -0.6], [r[1] + 0.4, r[3], 0.45], [true, true, false, false]);
        n += stone_mass(stone, rng, [r[0], r[3], -2.8], [r[1], 19.95, -0.06], [false, false, false, true]);
        b(falls, [r[0] + 1.0, 20.0, -2.4], [r[1] - 1.0, 20.08, -0.02]);
    }
    // The lower pools and their banks.
    for r in FRONT_LOW {
        b(water_low, [r[0], r[2], -2.42], [r[1], r[3], -2.4]);
        area += (r[1] - r[0]) * (r[3] - r[2]);
        n += stone_mass(stone, rng, [r[0] - 0.6, r[3], -2.9], [r[1] + 0.6, r[3] + 0.6, -2.12], [false, false, false, true]);
    }
    n += stone_mass(stone, rng, [-0.6, 20.0, -2.9], [0.0, 34.0, -2.12], [true, false, false, false]);
    n += stone_mass(stone, rng, [62.0, 20.0, -2.9], [62.6, 34.0, -2.12], [false, true, false, false]);
    n += stone_mass(stone, rng, [25.0, 26.0, -2.9], [25.6, 34.0, -2.12], [false, true, false, false]);
    n += stone_mass(stone, rng, [36.4, 26.0, -2.9], [37.0, 34.0, -2.12], [true, false, false, false]);
    // The stair down the step on the axis, twelve risers of 0.2 m, between stone cheek walls.
    let [sx0, sx1, sy0, sy1] = FRONT_STAIR;
    for k in 0..12 {
        let y0 = sy0 + k as f64 * (sy1 - sy0) / 12.0;
        b(&mut stone[2], [sx0, y0, -2.8], [sx1, sy1, 0.2 - 0.2 * (k + 1) as f64]);
    }
    n += stone_mass(stone, rng, [sx0 - 1.0, sy0, -2.8], [sx0, sy1, 0.45], [true, false, false, true]);
    n += stone_mass(stone, rng, [sx1, sy0, -2.8], [sx1 + 1.0, sy1, 0.45], [false, true, false, true]);
    (n, area)
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
    pub bronze: IndexedMesh,
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

    // --- Where things stand (D15): the winter garden where the site plan puts it, turned the way it
    // faces; without a plan, against the hall's south face as first drawn. With a plan, the hall's
    // front holds the great doors and the forecourt's warm basins.
    let (place, grect, _) = garden_place(pl);
    let front = pl.is_some();

    // --- The land: upper ground +0.2 north of the step at y = 20, lower ground -2.2 south of it, in
    // 1 m strips round the hall's front; the forecourt's basins, ledges and stair cut out, and the
    // garden's footprint (it brings its own ground).
    let (up, low) = if front { (FRONT_UP.to_vec(), FRONT_LOW.to_vec()) } else { (vec![], vec![]) };
    let inside = |r: &[f64; 4], x: f64, y: f64| x > r[0] && x < r[1] && y > r[2] && y < r[3];
    let cut = |x: f64, y: f64| {
        up.iter().chain(low.iter()).any(|r| inside(r, x, y))
            || (front && y > 18.0 && y < 20.0 && up.iter().any(|r| x > r[0] && x < r[1])) // the ledges
            || (front && inside(&FRONT_STAIR, x, y))
            || inside(&grect, x, y)
    };
    let (gx0, gx1) = ((-60.0f64).min(grect[0] - 4.0).floor(), 130.0f64.max(grect[1] + 4.0).ceil());
    let (gy0, gy1) = (-3.0, 110.0f64.max(grect[3] + 4.0).ceil());
    let top = |y: f64| if y < 20.0 { 0.2 } else { -2.2 };
    let mut y = gy0;
    while y < gy1 {
        let (cy, t) = (y + 0.5, top(y + 0.5));
        let mut run: Option<f64> = None;
        let mut x = gx0;
        while x <= gx1 {
            let keep = x < gx1 && !cut(x + 0.5, cy);
            match (keep, run) {
                (true, None) => run = Some(x),
                (false, Some(x0)) => {
                    b(&mut ground, [x0, y, t - 0.6], [x, y + 1.0, t]);
                    run = None;
                }
                _ => {}
            }
            x += 1.0;
        }
        y += 1.0;
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
    // The step in the land along y = 20, in stone, except where the forecourt or the garden meets it.
    let mut gaps: Vec<(f64, f64)> = Vec::new();
    if front {
        gaps.push((-0.6, 62.6));
    }
    if grect[2] < 20.0 && grect[3] > 20.0 {
        gaps.push((grect[0] - 0.6, grect[1] + 0.6));
    }
    gaps.sort_by(|a, b| a.0.total_cmp(&b.0));
    let mut x0 = gx0;
    for (a, c) in gaps.iter().cloned().chain([(gx1, gx1)]) {
        if a > x0 + 0.1 {
            n += stone_mass(&mut stone, &mut rng, [x0, 19.4, -2.8], [a, 20.0, 0.2], [false, false, false, true]);
        }
        x0 = x0.max(c);
    }

    // --- The bluff: the data hall's stone base along its south face; with the great doors, it stops
    // at the pylons.
    let bluff: Vec<(f64, f64)> = if front { vec![(-30.0, 17.0), (45.0, 92.0)] } else { vec![(-30.0, 92.0)] };
    for (a, c) in bluff {
        n += stone_mass(&mut stone, &mut rng, [a, -3.0, -0.6], [c, 0.0, 8.0], [true, true, false, true]);
    }
    n += stone_mass(&mut stone, &mut rng, [-30.0, 0.0, 0.2], [-4.0, 2.4, 3.2], [true, true, false, true]); // lower ledges
    n += stone_mass(&mut stone, &mut rng, [52.0, 0.0, 0.2], [92.0, 2.0, 2.6], [true, true, false, true]);

    // --- The hall's front (D15): the great doors and the forecourt's warm basins.
    let mut bronze = IndexedMesh::new();
    let basins_m2 = if front {
        let end_y = pl.and_then(|p| p.rect("square")).map(|r| r[2]).unwrap_or(60.0).max(60.0);
        let (nf, a) = hall_front(&mut stone, &mut concrete, &mut bronze, &mut floor, &mut water, &mut water_low, &mut falls, &mut rng, end_y);
        n += nf;
        a
    } else {
        0.0
    };

    // --- The winter garden, built in its own frame and placed.
    let gp = fallingwater(&mut rng, front, if front { 15.0 } else { 21.0 });
    n += gp.n;
    for (i, m) in gp.stone.iter().enumerate() {
        append(&mut stone[i], &place.mesh(m));
    }
    for (out, m) in [(&mut concrete, &gp.concrete), (&mut glass, &gp.glass), (&mut sash, &gp.sash), (&mut floor, &gp.floor),
                     (&mut ground, &gp.ground), (&mut water, &gp.water), (&mut water_low, &gp.water_low), (&mut falls, &gp.falls),
                     (&mut plants, &gp.plants), (&mut trunks, &gp.trunks)] {
        append(out, &place.mesh(m));
    }
    let (g1, g2, [t1, t2, t3]) = (gp.g1, gp.g2, gp.trays);

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
    // With the site plan's moat (D16) the glasshouses are its blocks round the hall, the food court at
    // the town end of the south-east block, on the mall's mouth.
    let names = ["greenhouse west", "greenhouse east", "greenhouse north-west", "greenhouse north-east", "greenhouse south-west", "greenhouse south-east"];
    let moat: Vec<(&str, [f64; 4])> = pl.map(|p| names.iter().filter_map(|nm| p.rect(nm).map(|r| (*nm, r))).collect()).unwrap_or_default();
    let (fh, nf) = if !moat.is_empty() {
        let rects: Vec<[f64; 4]> = moat.iter().map(|(_, r)| *r).collect();
        let food_i = moat.iter().position(|(nm, _)| *nm == "greenhouse south-east")
            .or_else(|| moat.iter().position(|(nm, _)| *nm == "greenhouse east")).unwrap_or(0);
        food::moat(spec, &mut stone, &mut concrete, &mut rng, &rects, food_i, 20.0, |y: f64| if y < 20.0 { 0.2 } else { -2.2 })
    } else {
        let (x_food, y_food, z_food) = match pl.and_then(|p| p.rect("greenhouse")) {
            Some(r) => {
                let w = ((spec.ha * 1e4).sqrt() / spec.bay).ceil().max(4.0) * spec.bay;
                ((r[0] + r[1]) / 2.0 - w / 2.0, r[3] - 20.0, site::ground_at(0.0, r[3] - 20.0))
            }
            None => (hx1 + 2.0 * reach + 12.0, 0.0, 0.2),
        };
        food::houses(spec, &mut stone, &mut concrete, &mut rng, x_food, y_food, z_food, hx1 + 1.5, -40.0)
    };
    n += nf;
    let (fx0, fx1, fy0, fy1) = fh.block;
    // The fire and service road all round the hall between it and the glass, and the covered crossing
    // through the north blocks to the hall's service side (D16).
    let mut ring_road = (hx0, hx1, hy0, hy1);
    if let Some((_, w)) = moat.iter().find(|(nm, _)| *nm == "greenhouse west") {
        let r = hx0 - w[1];
        ring_road = (hx0 - r, hx1 + r, hy0 - r, hy1);
        for (lo, hi) in [([hx0 - r, hy0 - r], [hx0, hy1]), ([hx1, hy0 - r], [hx1 + r, hy1]), ([hx0, hy0 - r], [hx1, hy0])] {
            b(&mut yard, [lo[0], lo[1], 0.2], [hi[0], hi[1], 0.24]);
        }
        if let (Some((_, nw)), Some((_, ne))) = (moat.iter().find(|(nm, _)| *nm == "greenhouse north-west"),
                                                moat.iter().find(|(nm, _)| *nm == "greenhouse north-east")) {
            b(&mut yard, [nw[1], nw[2] - 30.0, 0.2], [ne[0], nw[3], 0.24]);
            // The crossing's cover: a roof slab on stone piers between the glass either side.
            b(&mut concrete, [nw[1] - 0.5, nw[2], 6.2], [ne[0] + 0.5, nw[3], 6.6]);
            let mut y = nw[2] + 5.0;
            while y < nw[3] - 2.0 {
                n += stone_mass_s(&mut stone, &mut rng, [nw[1] - 0.2, y, 0.2], [nw[1] + 0.6, y + 0.8, 6.2], [true, true, true, true], 1.0);
                n += stone_mass_s(&mut stone, &mut rng, [ne[0] - 0.6, y, 0.2], [ne[0] + 0.2, y + 0.8, 6.2], [true, true, true, true], 1.0);
                y += 12.0;
            }
        }
    }
    let mall = pl.and_then(|p| p.rect("hall front")).unwrap_or([-4.0, 66.0, -3.0, 36.0]);
    let mut built: Vec<(f64, f64, f64, f64)> = vec![(hx0 - 1.5, hx1 + 1.5, hy0 - 1.5, hy1), (grect[0], grect[1], grect[2], grect[3]),
                                                   (mall[0], mall[1], mall[2], mall[3]), (-30.0, 92.0, -3.0, 3.0), ring_road, fh.head];
    if fh.blocks.is_empty() {
        built.push((fx0, fx1, fy0, fy1));
    } else {
        built.extend(fh.blocks.iter().cloned());
    }
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
    let groves: Vec<(f64, f64)> = if moat.is_empty() {
        vec![(-110.0, 10.0), ((hx1 + fx0) / 2.0, -70.0), (210.0, 200.0), (-75.0, -20.0), (220.0, 90.0), (-75.0, -110.0),
             ((fx0 + fx1) / 2.0, fh.head.3 + 60.0), (30.0, hy0 - 60.0), (-330.0, 230.0), (30.0, 460.0)]
    } else {
        // Round the moat's outer edge and on the town side either side of the mall's mouth.
        let (mx, my) = ((fx0 + fx1) / 2.0, (fy0 + fy1) / 2.0);
        vec![(fx0 - 55.0, my), (fx1 + 55.0, my), (mx, fy0 - 55.0), (fx0 - 55.0, fy0 + 120.0), (fx1 + 55.0, fy0 + 120.0),
             (fx0 - 55.0, fy1 - 60.0), (fx1 + 55.0, fy1 - 60.0), (mx - 200.0, fy0 - 55.0), (mx + 200.0, fy0 - 55.0), (-120.0, fy1 + 45.0)]
    };
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
        "basins_m2": basins_m2,
        "food_houses": {"floor_m2": fh.floor_m2, "block": [fx0, fx1, fy0, fy1], "head_house": [fh.head.0, fh.head.1, fh.head.2, fh.head.3]},
        "arboretum": trees_json,
    });
    let crown_colours = spec.trees.iter().map(|t| t.colour).collect();
    Garden { stone, concrete, glass, sash, floor, ground, yard, coolers, fans, halls, roofs, water, water_low, falls, bronze, trunks, crowns, crowns_dark,
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
    // Inside: the largest block of glass (with the moat, one of its parts).
    let ib = fh.blocks.iter().cloned().max_by(|a, c| ((a.1 - a.0) * (a.3 - a.2)).total_cmp(&((c.1 - c.0) * (c.3 - c.2)))).unwrap_or(fh.block);
    // Down the walk between a bay's two crop rows (food.rs: rows at 0.6-1.3 and 2.5-3.2 m into each 4 m bay).
    let ix = ib.0 + (((ib.0 + ib.1) / 2.0 - ib.0) / 4.0).floor() * 4.0 + 0.7;
    let iz = if ib.3 < 20.0 { 0.2 } else { -2.2 };
    let moat = fh.blocks.len() > 1;
    // The garden's views in its own frame, placed with it.
    let (gp, _, _) = garden_place(pl);
    let mut v = vec![
        View("garden_falls.png", gp.pt(36.0, 46.0, -0.6), gp.pt(23.0, 10.0, 3.6), 52.0, 1.0),
        View("garden_hero.png", gp.pt(62.0, 58.0, 4.0), gp.pt(24.0, 8.0, 3.0), 46.0, 1.0),
        View("garden_inside.png", gp.pt(11.0, 8.6, 4.7), gp.pt(40.0, 5.5, 3.9), 70.0, 1.7),
        View("garden_aerial.png", gp.pt(105.0, 90.0, 62.0), gp.pt(24.0, -12.0, 0.0), 46.0, 1.0),
        View("campus_aerial.png", p(125.0, 165.0, 115.0), p(31.0, -45.0, 0.0), 50.0, 1.0),
        View("campus_hall.png", p(150.0, -40.0, 1.7), p(92.0, -80.0, 10.0), 56.0, 1.0),
        View("campus_front.png", if moat { p(-30.0, fy1 + 35.0, 16.0) } else { p(-30.0, 95.0, 14.0) }, p(31.0, -10.0, 9.0), 52.0, 1.0),
        View("campus_food.png", p(fx1 + 260.0, fy1 + 330.0, 330.0), p((31.0 + fxm) / 2.0, fym, 0.0), 50.0, 1.0),
        View("food_inside.png", p(ix + 1.2, ib.3 - 4.0, iz + 1.8), p(ix + 1.0, ib.3 - 60.0, iz + 2.4), 68.0, 1.3),
        View("food_head.png", p(hm - 40.0, fh.head.3 + 55.0, fz - 0.6), p(hm, fy1 + 6.0, fz + 3.8), 56.0, 1.0),
        View("arboretum.png", p(-130.0, 210.0, -0.5), p(30.0, 40.0, 6.0), 60.0, 1.0),
    ];
    let r = |n: &str, d: [f64; 4]| pl.and_then(|q| q.rect(n)).unwrap_or(d);
    if let Some(vs) = vspec {
        let fr = r("flats", [-110.0, 124.0, 175.0, 316.0]);
        let th = r("townhouses", [-68.0, 128.0, 147.0, 450.0]);
        let sq = r("square", [0.0, 60.0, 60.0, 120.0]);
        let c = r("community center", [72.0, 162.0, 12.0, 140.0]);
        let fl = r("field and loop", [-207.0, -93.0, 34.0, 186.0]);
        let gd = r("winter garden", [-4.0, 63.0, -3.0, 35.0]);
        let (tcx, sqx, sqy) = ((th[0] + th[1]) / 2.0, (sq[0] + sq[1]) / 2.0, (sq[2] + sq[3]) / 2.0);
        let (fcx, fcy) = ((fl[0] + fl[1]) / 2.0, (fl[2] + fl[3]) / 2.0);
        // The community center's own frame, turned as the site plan turns it (village.rs, Turn).
        let crot = vs.center_rot % 180 != 0;
        let cw = if crot { c[3] - c[2] } else { c[1] - c[0] };
        let cp = |lx: f64, ly: f64, z: f64| if crot { p(c[0] + ly, c[2] + cw - lx, z) } else { p(c[0] + lx, c[2] + ly, z) };
        let mid = (th[2] + th[3]) / 2.0;
        let street = vs.streets_y.iter().cloned().min_by(|a, b| (a - mid).abs().total_cmp(&(b - mid).abs())).unwrap_or(mid);
        let green = vs.greens.first().map(|g| (g[2] + g[3]) / 2.0).unwrap_or(th[2] + 64.0);
        // The neighbourhood from the air: over its town side, toward its middle.
        let ms: Vec<[f64; 4]> = [Some(fr), Some(th), pl.and_then(|q| q.rect("houses")), Some(sq), Some(c), Some(fl)].into_iter().flatten().collect();
        let k = ms.len() as f64 * 2.0;
        let (mx, my) = (ms.iter().map(|q| q[0] + q[1]).sum::<f64>() / k, ms.iter().map(|q| q[2] + q[3]).sum::<f64>() / k);
        v.extend([
            View("campus_village.png", p(mx + 350.0, my + 440.0, 330.0), p(mx, my, 0.0), 50.0, 1.0),
            // From an upper window of the flats nearest the garden, toward it.
            View("village_balcony.png", p(fr[1] - 6.0, (gd[2] + gd[3]) / 2.0, 5.3), p((gd[0] + gd[1]) / 2.0, (gd[2] + gd[3]) / 2.0, 2.0), 62.0, 1.0),
            View("village_square.png", p(sqx + 18.0, sqy + 24.0, -0.5), p(sqx - 8.0, sqy - 45.0, 2.0), 60.0, 1.0),
            View("village_street.png", p(tcx + 30.0, street, -0.5), p(tcx - 70.0, street, 2.5), 60.0, 1.0),
            View("village_center.png", cp(68.0, 120.0, 3.5), cp(24.0, 73.0, -2.2), 72.0, 1.5),
            View("village_green.png", p(th[0] + 18.0, green, -0.6), p(th[0] + 108.0, green + 1.8, 0.8), 62.0, 1.0),
            View("village_climbing.png", cp(38.0, 32.0, -0.6), cp(28.0, 9.0, 0.6), 66.0, 1.6),
            View("village_fields.png", p(fcx + 30.0, fcy + 95.0, 1.5), p(fcx, fcy - 15.0, 0.0), 62.0, 1.0),
        ]);
        // A street of each outer ring (D16): the walk-ups, and the houses.
        for (name, kind) in [("village_flats.png", "flats"), ("village_houses.png", "houses")] {
            if let Some(rg) = vs.rings.iter().find(|q| q.kind == kind) {
                if let Some(&st) = rg.streets_y.first() {
                    v.push(View(name, p(rg.spine_x + 45.0, st + 1.0, -0.5), p(rg.spine_x - 70.0, st - 4.0, 3.0), 60.0, 1.0));
                }
            }
        }
    }
    if let Some(q) = pl {
        // The great doors from the mall, on the axis (D15); with the moat (D16), the mall between the glass
        // from the square, and the moat from the air.
        if let Some(m) = q.rect("hall front").filter(|m| m[3] > 60.0) {
            v.push(View("hall_front.png", p(31.0, m[3] - 30.0, -0.4), p(31.0, -3.0, 10.0), 50.0, 1.0));
            let sq_y = q.rect("square").map(|s| s[2] + 15.0).unwrap_or(m[3] + 30.0);
            v.push(View("mall.png", p(31.0, sq_y, 1.2), p(31.0, -3.0, 9.0), 42.0, 1.0));
            v.push(View("moat_aerial.png", p(fx1 + 230.0, fy1 + 330.0, 360.0), p(31.0, -140.0, 0.0), 46.0, 1.0));
        } else {
            v.push(View("hall_front.png", p(31.0, 58.0, -0.4), p(31.0, -3.0, 10.0), 55.0, 1.0));
        }
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
        let mut v: Vec<IndexedMesh> = (0..9 + 2 * ns).map(|_| IndexedMesh::new()).collect();
        for (i, m) in g.stone.iter().enumerate() {
            add_mirrored_at(&mut v[i], m, zw);
        }
        add_mirrored_at(&mut v[5], &g.concrete, zw);
        add_mirrored_at(&mut v[6], &g.sash, zw);
        add_mirrored_at(&mut v[7], &g.trunks, zw);
        add_mirrored_at(&mut v[8], &g.bronze, zw);
        for (i, m) in g.crowns.iter().chain(g.crowns_dark.iter()).enumerate() {
            add_mirrored_at(&mut v[9 + i], m, zw);
        }
        v
    };
    let refl = [reflect(0.0), reflect(-2.4 * M)];
    const CONCRETE: [f64; 3] = [0.94, 0.85, 0.66];
    const SASH: [f64; 3] = [0.46, 0.17, 0.12];
    const BRONZE: [f64; 3] = [0.50, 0.34, 0.19];
    let mut layers: Vec<SLayer> = Vec::new();
    for (i, m) in g.stone.iter().enumerate() {
        layers.push(SLayer::solid(m, STONE[i]));
    }
    layers.push(SLayer::solid(&g.concrete, CONCRETE));
    layers.push(SLayer::solid(&g.sash, SASH));
    layers.push(SLayer::solid(&g.bronze, BRONZE));
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
        layers.push(SLayer::solid(&set[8], dim(BRONZE)).mirrored(zw, pool));
        let ns = g.crowns.len();
        for i in 0..2 * ns {
            let c = g.crown_colours[i % ns].map(|v| if i >= ns { v * 0.8 } else { v });
            layers.push(SLayer::solid(&set[9 + i], dim(c)).smooth().mirrored(zw, pool));
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
    // GARDEN_VIEWS=a.png,b.png renders only those (for checking a change before the whole set).
    let only: Option<Vec<String>> = std::env::var("GARDEN_VIEWS").ok().map(|s| s.split(',').map(|v| v.trim().to_string()).collect());
    let views: Vec<_> = views(pl.as_ref(), vspec.as_ref(), &g.food).into_iter()
        .filter(|v| only.as_ref().is_none_or(|o| o.iter().any(|n| n == v.0)))
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
