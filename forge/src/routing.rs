//! Pass 3g step 7b (D28): the walk-up's services routed through its frame.
//!
//! `brownfield routes --requests` (Python) writes `out/pass3/route-requests.json`: the rules (the
//! I-joists' hole chart, the code's limits on holes in studs, plates and sawn joists, the costs),
//! the obstacles (equipment, the pinned risers), and one request per service: its size, its
//! root and terminals, and the zones it may run in (a flat's ceiling cavity, its soffits, a wall's
//! stud cavity, under the slab). This mode, `routes-json`, routes them in the requests' order and
//! writes `out/pass3/routes.json`; Python takes the lengths back into steps 3-6 (7c).
//!
//! **The grid:** each request is searched on a dense voxel grid of its own zones (cf-spatial's
//! `VoxelGrid` is a sparse hash map, and a search over a whole ceiling cavity touches most of it).
//! A voxel is free, blocked, or crossable along one axis: an I-joist's web only across it and only
//! where APA's chart allows the hole at that distance from the support; a stud along its wall
//! (a nonbearing wall's 60% of its depth, a bearing wall's 40%); a plate up through it (a steel
//! tie, IBC 2308.5.8); a sawn joist across it, a third of its depth and 2 in. from its edges.
//! Anything else in the frame is blocked, as are the equipment, the pinned services and every
//! service routed before. Summed-volume tables make a pipe's clearance (its cross-section, which
//! must not touch a blocked voxel nor a member bored the wrong way) one lookup.
//!
//! **The search:** A* over the 6 neighbours, its cost the length plus a cost per bend and per
//! voxel of member crossed, with a Manhattan heuristic to the goal's box. Never diagonal, so no
//! route is shorter than its square length. A request with several terminals grows a tree: each
//! terminal, nearest first, joins the nearest point of what is already routed (a tee).
//!
//! **What comes back:** each branch as a polyline (bends merged), where it tees into the tree,
//! and every member it bores: which member, the hole's centre and size, and for an I-joist its
//! distance from the support against the chart's. Then a clash check over every routed service on
//! one cf-spatial grid.

use std::collections::{BinaryHeap, HashSet};

use cortenforge::cf_spatial::{VoxelCoord, VoxelGrid};
use nalgebra::Point3;
use serde_json::{Value, json};

const FREE: u8 = 0;
const BLOCK: u8 = 1;
const BORE: u8 = 2; // BORE + axis: crossable along that axis only

type V3 = [f64; 3];

fn v3(v: &Value) -> V3 {
    [v[0].as_f64().unwrap_or(0.0), v[1].as_f64().unwrap_or(0.0), v[2].as_f64().unwrap_or(0.0)]
}

fn boxes(v: &Value) -> Vec<(V3, V3)> {
    v.as_array().into_iter().flatten().map(|b| (v3(&b["lo"]), v3(&b["hi"]))).collect()
}

/// The rules, every number from Python's params and data.
pub struct Rules {
    apa: Vec<(f64, f64)>, // (hole, least distance from the support's face to its centre), m, ascending
    saf: f64,             // the chart's span adjustment factor (m)
    min_edge: f64,        // a reduced distance's least, support face to hole edge (m)
    any_hole: f64,        // a hole this size or less anywhere in the web (m)
    stud_nb: f64,
    stud_b: f64,
    plate_nb: f64,
    plate_b: f64,
    sawn_frac: f64,
    sawn_edge: f64,
    nonbearing: Vec<(V3, V3)>,
    turn: f64,
    cross: f64,
    sleeve: f64,
}

impl Rules {
    pub fn from_json(v: &Value) -> Self {
        let f = |k: &str| v[k].as_f64().unwrap_or_else(|| panic!("rules: no {k}"));
        Rules {
            apa: v["apa_table_m"].as_array().into_iter().flatten().map(|r| (r[0].as_f64().unwrap(), r[1].as_f64().unwrap())).collect(),
            saf: f("apa_saf_m"), min_edge: f("apa_min_edge_m"), any_hole: f("apa_any_hole_m"),
            stud_nb: f("stud_nonbearing"), stud_b: f("stud_bearing"), plate_nb: f("plate_nonbearing"), plate_b: f("plate_bearing"),
            sawn_frac: f("sawn_frac"), sawn_edge: f("sawn_edge_m"), nonbearing: boxes(&v["nonbearing"]),
            turn: f("turn_cost_m"), cross: f("cross_cost_m"), sleeve: f("sleeve_cost_m"),
        }
    }

    /// The chart's largest hole smaller than `allowed` (rule 9's small hole the least; 0 under it): a
    /// hole over this is a maximum-size one where `allowed` is the limit (rule 11).
    pub fn smaller_size(&self, allowed: f64) -> f64 {
        self.apa.iter().map(|r| r.0).chain(std::iter::once(self.any_hole)).filter(|&h| h < allowed - 1e-9).fold(0.0, f64::max)
    }

    /// The largest round hole APA's chart allows `d` from the nearer support's face, on a clear span
    /// `span` (its note e: the distance reduced by span / SAF, but never under `min_edge` to the
    /// hole's edge); rule 9's small hole anywhere.
    pub fn apa_max_hole(&self, d: f64, span: f64) -> f64 {
        let k = (span / self.saf).min(1.0);
        let mut best = self.any_hole;
        for &(hole, dist) in &self.apa {
            let need = if k < 1.0 { (dist * k).max(self.min_edge + hole / 2.0) } else { dist };
            if need <= d + 1e-9 {
                best = best.max(hole);
            }
        }
        best
    }
}

#[derive(Clone, Copy, Debug)]
enum Limit {
    Fixed(f64),
    /// An I-joist's web: its length along `axis`, the supports' faces, the clear span.
    Apa { axis: usize, faces: (f64, f64) },
}

#[derive(Clone, Debug)]
struct Piece {
    member: usize,
    lo: V3,
    hi: V3,
    bore: Option<(usize, Limit)>,
    sleeve: bool,
}

/// The frame as pieces with their boring rule.
pub struct Frame {
    ids: Vec<String>,
    kinds: Vec<String>,
    pieces: Vec<Piece>,
}

fn inside(p: V3, lo: V3, hi: V3) -> bool {
    (0..3).all(|i| p[i] >= lo[i] - 1e-6 && p[i] <= hi[i] + 1e-6)
}

fn mid(lo: V3, hi: V3) -> V3 {
    [(lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0, (lo[2] + hi[2]) / 2.0]
}

impl Frame {
    pub fn from_json(v: &Value, r: &Rules) -> Self {
        let ms = v["members"].as_array().expect("framing JSON: members");
        let mb: Vec<(String, String, Vec<(V3, V3)>)> = ms.iter().map(|m| {
            let bx = m["boxes"].as_array().unwrap().iter().map(|b| (v3(&b[0]), v3(&b[1]))).collect();
            (m["id"].as_str().unwrap().to_string(), m["kind"].as_str().unwrap().to_string(), bx)
        }).collect();
        let caps: Vec<(V3, V3)> = mb.iter().filter(|m| m.1 == "cap plates").flat_map(|m| m.2.clone()).collect();
        let bounds = |bx: &[(V3, V3)]| {
            let mut lo = [f64::INFINITY; 3];
            let mut hi = [f64::NEG_INFINITY; 3];
            for (a, b) in bx {
                for i in 0..3 {
                    lo[i] = lo[i].min(a[i]);
                    hi[i] = hi[i].max(b[i]);
                }
            }
            (lo, hi)
        };
        let nonbearing = |p: V3| r.nonbearing.iter().any(|(a, b)| inside(p, *a, *b));
        let mut pieces = Vec::new();
        for (k, (_, kind, bx)) in mb.iter().enumerate() {
            let (lo, hi) = bounds(bx);
            let ext = [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]];
            let horiz_thin = if ext[0] < ext[1] { 0 } else { 1 };
            let horiz_long = 1 - horiz_thin;
            let push = |pieces: &mut Vec<Piece>, lo, hi, bore, sleeve| pieces.push(Piece { member: k, lo, hi, bore, sleeve });
            match kind.as_str() {
                "floor joists" | "roof joists" if bx.len() == 3 => {
                    // An I-joist: flanges blocked, the web bored across it by APA's chart. Its supports:
                    // the cap plates under its ends.
                    let axis = if ext[0] > ext[1] { 0 } else { 1 };
                    // A support crosses the joist: short along its length (a wall's width), under its end.
                    // (A cap plate running beside the joist, under its whole length, isn't one.)
                    let under = |end: f64, low: bool| caps.iter().filter(|(a, b)| (b[2] - lo[2]).abs() < 3e-3
                        && a[1 - axis] < hi[1 - axis] && b[1 - axis] > lo[1 - axis] && a[axis] <= end + 1e-6 && b[axis] >= end - 1e-6
                        && b[axis] - a[axis] < 0.4)
                        .map(|(a, b)| if low { b[axis] } else { a[axis] })
                        .fold(None, |acc: Option<f64>, x| Some(acc.map_or(x, |y| if low { y.max(x) } else { y.min(x) })));
                    let f0 = under(lo[axis] + 0.01, true).unwrap_or(lo[axis] + 0.0381);
                    let f1 = under(hi[axis] - 0.01, false).unwrap_or(hi[axis] - 0.0381);
                    for (i, (a, b)) in bx.iter().enumerate() {
                        if i == 2 {
                            push(&mut pieces, *a, *b, Some((1 - axis, Limit::Apa { axis, faces: (f0, f1) })), false);
                        } else {
                            push(&mut pieces, *a, *b, None, false);
                        }
                    }
                }
                "floor joists" | "roof joists" => {
                    // Sawn: 2 in. off each edge blocked, the middle bored across by a third of its depth.
                    let d = hi[2] - lo[2];
                    let e = r.sawn_edge;
                    push(&mut pieces, lo, [hi[0], hi[1], lo[2] + e], None, false);
                    push(&mut pieces, [lo[0], lo[1], hi[2] - e], hi, None, false);
                    push(&mut pieces, [lo[0], lo[1], lo[2] + e], [hi[0], hi[1], hi[2] - e], Some((horiz_thin, Limit::Fixed(r.sawn_frac * d))), false);
                }
                "studs" => {
                    let depth = ext[horiz_long];
                    let f = if nonbearing(mid(lo, hi)) { r.stud_nb } else { r.stud_b };
                    push(&mut pieces, lo, hi, Some((horiz_thin, Limit::Fixed(f * depth))), false);
                }
                "plates" | "cap plates" => {
                    let width = ext[horiz_thin];
                    let f = if nonbearing(mid(lo, hi)) { r.plate_nb } else { r.plate_b };
                    push(&mut pieces, lo, hi, Some((2, Limit::Fixed(f * width))), false);
                }
                "stem walls" => push(&mut pieces, lo, hi, Some((horiz_thin, Limit::Fixed(10.0))), true),
                // A footing or the slab only straight down through it, in a sleeve (a stack's or a
                // riser's foot, a ground-floor fixture's drain).
                "footings" | "slab" => {
                    for (a, b) in bx {
                        push(&mut pieces, *a, *b, Some((2, Limit::Fixed(10.0))), true);
                    }
                }
                _ => {
                    for (a, b) in bx {
                        push(&mut pieces, *a, *b, None, false);
                    }
                }
            }
        }
        Frame { ids: mb.iter().map(|m| m.0.clone()).collect(), kinds: mb.iter().map(|m| m.1.clone()).collect(), pieces }
    }

}

/// A request's grid: its zones' bounding box in voxels of `h`.
struct Grid {
    o: V3,
    h: f64,
    n: [usize; 3],
    cls: Vec<u8>,
    hole: Vec<f32>,
    ps: [Vec<u32>; 4], // summed counts: blocked, bored along x, y, z
}

impl Grid {
    fn len(&self) -> usize {
        self.n[0] * self.n[1] * self.n[2]
    }
    fn at(&self, c: [usize; 3]) -> usize {
        (c[2] * self.n[1] + c[1]) * self.n[0] + c[0]
    }
    fn cell(&self, i: usize) -> [usize; 3] {
        let (nx, ny) = (self.n[0], self.n[1]);
        [i % nx, (i / nx) % ny, i / (nx * ny)]
    }
    fn centre(&self, c: [usize; 3]) -> V3 {
        [self.o[0] + (c[0] as f64 + 0.5) * self.h, self.o[1] + (c[1] as f64 + 0.5) * self.h, self.o[2] + (c[2] as f64 + 0.5) * self.h]
    }
    /// The cells a box overlaps (by more than a hair), clipped; None if none.
    fn span(&self, lo: V3, hi: V3) -> Option<([usize; 3], [usize; 3])> {
        let mut a = [0usize; 3];
        let mut b = [0usize; 3];
        for i in 0..3 {
            let x0 = ((lo[i] - self.o[i]) / self.h + 1e-6).floor() as i64;
            let x1 = ((hi[i] - self.o[i]) / self.h - 1e-6).ceil() as i64 - 1;
            let (x0, x1) = (x0.max(0), x1.min(self.n[i] as i64 - 1));
            if x1 < x0 {
                return None;
            }
            a[i] = x0 as usize;
            b[i] = x1 as usize;
        }
        Some((a, b))
    }
    fn prefix(&mut self) {
        let (nx, ny, nz) = (self.n[0] + 1, self.n[1] + 1, self.n[2] + 1);
        let idx = |x: usize, y: usize, z: usize| (z * ny + y) * nx + x;
        for k in 0..4 {
            let mut s = vec![0u32; nx * ny * nz];
            for z in 1..nz {
                for y in 1..ny {
                    for x in 1..nx {
                        let c = self.cls[self.at([x - 1, y - 1, z - 1])];
                        let v = match k { 0 => (c == BLOCK) as u32, a => (c == BORE + (a as u8 - 1)) as u32 };
                        s[idx(x, y, z)] = v + s[idx(x - 1, y, z)] + s[idx(x, y - 1, z)] + s[idx(x, y, z - 1)]
                            - s[idx(x - 1, y - 1, z)] - s[idx(x - 1, y, z - 1)] - s[idx(x, y - 1, z - 1)] + s[idx(x - 1, y - 1, z - 1)];
                    }
                }
            }
            self.ps[k] = s;
        }
    }
    /// How many cells of kind `k` in the inclusive box a..b.
    fn count(&self, k: usize, a: [usize; 3], b: [usize; 3]) -> u32 {
        let (nx, ny) = (self.n[0] + 1, self.n[1] + 1);
        let s = &self.ps[k];
        let g = |x: usize, y: usize, z: usize| s[(z * ny + y) * nx + x] as i64;
        let (x0, y0, z0, x1, y1, z1) = (a[0], a[1], a[2], b[0] + 1, b[1] + 1, b[2] + 1);
        (g(x1, y1, z1) - g(x0, y1, z1) - g(x1, y0, z1) - g(x1, y1, z0) + g(x0, y0, z1) + g(x0, y1, z0) + g(x1, y0, z0) - g(x0, y0, z0)) as u32
    }
    /// Whether a pipe of `r` cells' half width may sit at `c` running along `axis`: its cross-section
    /// in the grid, touching nothing blocked and no member bored another way.
    fn passable(&self, c: [usize; 3], axis: usize, r: usize) -> bool {
        self.passable_shift(c, axis, r, 0.0, 0.0)
    }
    /// As `passable`, for a pipe running level `off` m over `c`'s centre (under it if negative: a
    /// drain's fall, a vent's rise) with `half` its half width and clearance: across it vertically,
    /// the cells that pipe overlaps (`r` when `off` is 0).
    fn passable_shift(&self, c: [usize; 3], axis: usize, r: usize, off: f64, half: f64) -> bool {
        let mut a = c;
        let mut b = c;
        for i in 0..3 {
            if i != axis {
                let (r, ci) = (r as i64, c[i] as i64);
                let (lo, hi) = if i == 2 && off != 0.0 {
                    let k0 = ((off - half) / self.h - 0.5 + 1e-9).floor() as i64 + 1;
                    let k1 = ((off + half) / self.h + 0.5 - 1e-9).ceil() as i64 - 1;
                    (ci + k0, ci + k1)
                } else {
                    (ci - r, ci + r)
                };
                if lo < 0 || hi >= self.n[i] as i64 {
                    return false;
                }
                a[i] = lo as usize;
                b[i] = hi as usize;
            }
        }
        if self.count(0, a, b) > 0 {
            return false;
        }
        let bored: u32 = (0..3).filter(|&k| k != axis).map(|k| self.count(1 + k, a, b)).sum();
        bored == 0
    }
}

fn ordered(x: f64) -> u64 {
    x.to_bits() // non-negative costs order as their bits
}

/// A* from any of `starts` to any cell `goal` accepts, a pipe of half width `r` cells. A drain
/// (`slope` > 0, its fall per unit run) falls as it runs: at a cell its pipe lies `slope` times its
/// level run so far below it (over it for a vent, `grade` > 0, which rises toward its stack), and
/// every move needs room for the pipe there; the goal is told that run. Returns the path and each
/// cell's run.
#[allow(clippy::too_many_arguments)]
fn search(g: &Grid, r: usize, starts: &[usize], goal: &dyn Fn(usize, f64) -> bool, gbox: ([usize; 3], [usize; 3]),
          turn: f64, cross: f64, sleeve_cost: f64, sleeve: &[bool], grade: i8, slope: f64, half: f64) -> Option<(Vec<usize>, Vec<f64>)> {
    let n = g.len();
    let mut cost = vec![f64::INFINITY; n];
    let mut from = vec![u32::MAX; n];
    let mut dir = vec![6u8; n];
    let mut run = if slope > 0.0 { vec![0f64; n] } else { Vec::new() };
    let dirn = if grade > 0 { 1.0 } else { -1.0 };
    let fall = |d: f64| dirn * slope * d;
    let mut open = BinaryHeap::new();
    let h = |i: usize| {
        let c = g.cell(i);
        (0..3).map(|k| if c[k] < gbox.0[k] { gbox.0[k] - c[k] } else if c[k] > gbox.1[k] { c[k] - gbox.1[k] } else { 0 }).sum::<usize>() as f64 * g.h
    };
    for &s in starts {
        cost[s] = 0.0;
        open.push(std::cmp::Reverse((ordered(h(s)), s)));
    }
    while let Some(std::cmp::Reverse((_, i))) = open.pop() {
        let ri = if slope > 0.0 { run[i] } else { 0.0 };
        if goal(i, ri) {
            let mut path = vec![i];
            let mut k = i;
            while from[k] != u32::MAX {
                k = from[k] as usize;
                path.push(k);
            }
            path.reverse();
            let runs = path.iter().map(|&k| if slope > 0.0 { run[k] } else { 0.0 }).collect();
            return Some((path, runs));
        }
        let c = g.cell(i);
        for d in 0..6u8 {
            let axis = (d / 2) as usize;
            if dir[i] != 6 && (dir[i] ^ 1) == d {
                continue; // no turning back
            }
            // The search runs from a terminal to the root: a drain may only fall (no +z from the
            // fixture toward its stack), a vent only rise (no -z toward its vent stack).
            if (grade < 0 && d == 4) || (grade > 0 && d == 5) {
                continue;
            }
            let mut nc = c;
            if d % 2 == 0 {
                if c[axis] + 1 >= g.n[axis] { continue; }
                nc[axis] += 1;
            } else {
                if c[axis] == 0 { continue; }
                nc[axis] -= 1;
            }
            let j = g.at(nc);
            let turning = dir[i] != 6 && (dir[i] / 2) as usize != axis;
            let rj = if axis == 2 { ri } else { ri + g.h };
            let (ej, ei) = (fall(rj), fall(ri));
            let ok = if axis != 2 {
                g.passable_shift(nc, axis, r, ej, half) && (!(turning || dir[i] == 6) || g.passable_shift(c, axis, r, ei, half))
            } else {
                // Straight down or up, where the pipe is: in the cell `e` m off the path's.
                let at = |q: [usize; 3], e: f64| {
                    let z = q[2] as i64 + (e / g.h).round() as i64;
                    z >= 0 && (z as usize) < g.n[2] && g.passable([q[0], q[1], z as usize], 2, r)
                };
                at(nc, ej) && (!(turning || dir[i] == 6) || at(c, ei))
            };
            if !ok {
                continue;
            }
            let bore = g.cls[j] >= BORE;
            let step = g.h + if bore { if sleeve[j] { sleeve_cost } else { cross } } else { 0.0 } + if turning { turn } else { 0.0 };
            let nd = cost[i] + step;
            if nd + 1e-12 < cost[j] {
                cost[j] = nd;
                from[j] = i as u32;
                dir[j] = d;
                if slope > 0.0 {
                    run[j] = rj;
                }
                open.push(std::cmp::Reverse((ordered(nd + h(j)), j)));
            }
        }
    }
    None
}

struct Request {
    id: String,
    od: f64,
    /// The diameter its holes in framing must pass (`bore_m`; its `od` unless set): an insulated pipe
    /// whose insulation stops at each member it passes (IECC C404.4) bores for the bare pipe.
    bore: f64,
    clear: f64,
    hole_clear: f64,
    h: f64,
    root: V3,
    terminals: Vec<(String, V3)>,
    zones: Vec<(V3, V3)>,
    snap: f64,
    attach: HashSet<String>,
    /// -1 a drain (falls from its terminals to its root), +1 a vent (rises), 0 either.
    grade: i8,
    /// Where it may join what it comes off, besides its root: a stack's or a riser's box (a drain
    /// joins its stack anywhere below its fixture, a branch tees off its riser anywhere).
    goals: Vec<(V3, V3)>,
    /// Boxes kept from it alone (a band reserved for another trade).
    blocks: Vec<(V3, V3)>,
    /// A drain's least fall per unit of horizontal run (IPC 704.1); 0 for the rest.
    slope: f64,
    /// The flat it serves ("" for the building's).
    flat: String,
    /// The request it must come after (`after`; "" for none): a flat's loop's return after its hot
    /// branch, whose end it joins. The passes never move it ahead of that one.
    after: String,
    /// Attached routes it may enter only near a point (`attach_near`: [{id, at, m}]): a flat's
    /// loop's return leaves its hot branch's end within `m` of it (the tee), and keeps clear of the
    /// rest of that pipe.
    near: std::collections::HashMap<String, (V3, f64)>,
    /// Terminals routed before the rest, in this order: those that failed in an earlier pass (`run`),
    /// so a branch with little room isn't shut out by its own tree's earlier branches.
    first: Vec<String>,
    /// Run straight at any angle where nothing holds it to the lattice (`pull`): a feeder's conduit
    /// under the slab, whose bends NEC 352.26 counts in degrees (D28 step 7e).
    straight: bool,
}

impl Request {
    /// Whether this request may touch `owner`'s solid: one it tees into or starts from (an id, or a
    /// family of ids by a trailing `*`).
    fn attached(&self, owner: &str) -> bool {
        owner == self.id || self.attach.iter().any(|a| match (a.strip_suffix('*'), a.strip_prefix('*')) {
            (Some(pre), _) => owner.starts_with(pre),
            (_, Some(suf)) => owner.ends_with(suf),
            _ => a == owner,
        })
    }
    fn from_json(v: &Value) -> Self {
        Request {
            id: v["id"].as_str().unwrap().to_string(),
            od: v["od_m"].as_f64().unwrap(),
            bore: v["bore_m"].as_f64().or_else(|| v["od_m"].as_f64()).unwrap(),
            clear: v["clear_m"].as_f64().unwrap_or(0.0),
            hole_clear: v["hole_clear_m"].as_f64().unwrap_or(0.0),
            h: v["voxel_m"].as_f64().unwrap(),
            root: v3(&v["root"]),
            terminals: v["terminals"].as_array().into_iter().flatten().map(|t| (t["ref"].as_str().unwrap().to_string(), v3(&t["xyz"]))).collect(),
            zones: boxes(&v["zones"]),
            snap: v["snap_m"].as_f64().unwrap_or(0.15),
            attach: v["attach"].as_array().into_iter().flatten().filter_map(|x| x.as_str().map(String::from)).collect(),
            grade: v["grade"].as_i64().unwrap_or(0) as i8,
            goals: boxes(&v["goals"]),
            blocks: boxes(&v["blocks"]),
            slope: v["slope"].as_f64().unwrap_or(0.0),
            flat: v["flat"].as_str().unwrap_or("").to_string(),
            after: v["after"].as_str().unwrap_or("").to_string(),
            near: v["attach_near"].as_array().into_iter().flatten()
                .map(|x| (x["id"].as_str().unwrap().to_string(), (v3(&x["at"]), x["m"].as_f64().unwrap()))).collect(),
            first: vec![],
            straight: v["straight"].as_bool().unwrap_or(false),
        }
    }
}

/// A hole a route cut in an I-joist's web: its member, centre, diameter and the axis it runs along.
#[derive(Clone, Debug)]
struct Hole {
    member: usize,
    c: V3,
    d: f64,
    axis: usize,
    /// A maximum-size hole where it is (over the chart's next size down from the limit there).
    max: bool,
}

/// APA's rule 11: "Limit three maximum-size holes per span." A joist with three takes no more: its
/// web's limit everywhere drops to the chart's next size down, and where that's under `need`, the
/// web is blocked.
fn limit_full(g: &mut Grid, who: &[u32], web: &[bool], member: usize, rules: &Rules, need: f32) {
    for at in 0..g.len() {
        if who[at] == member as u32 && web[at] && g.cls[at] >= BORE {
            let lower = rules.smaller_size(g.hole[at] as f64) as f32;
            g.hole[at] = g.hole[at].min(lower);
            if g.hole[at] < need {
                g.cls[at] = BLOCK;
            }
        }
    }
}

/// APA Z725E's rule 6: "the distance between adjacent hole edges shall exceed twice the diameter of
/// the largest round hole". Blocks the voxels of `hole`'s web where a pipe of half width `r` cells
/// cutting a hole `d2` would bring the two holes' edges closer than that (centres, in the web's
/// plane, under d/2 + d2/2 + 2 max(d, d2)), less the cells in `keep`.
fn exclude(g: &mut Grid, who: &[u32], web: &[bool], hole: &Hole, d2: f64, r: usize, keep: &HashSet<usize>) {
    let sep = hole.d / 2.0 + d2 / 2.0 + 2.0 * hole.d.max(d2);
    let rad = sep - r as f64 * g.h;
    if rad <= 0.0 {
        return;
    }
    let mut lo = [hole.c[0] - sep, hole.c[1] - sep, hole.c[2] - sep];
    let mut hi = [hole.c[0] + sep, hole.c[1] + sep, hole.c[2] + sep];
    lo[hole.axis] = hole.c[hole.axis] - 0.1;
    hi[hole.axis] = hole.c[hole.axis] + 0.1;
    let Some((x, y)) = g.span(lo, hi) else { return };
    for k in x[2]..=y[2] {
        for j in x[1]..=y[1] {
            for i in x[0]..=y[0] {
                let at = g.at([i, j, k]);
                if who[at] != hole.member as u32 || !web[at] || keep.contains(&at) {
                    continue;
                }
                let c = g.centre([i, j, k]);
                let dd: f64 = (0..3).filter(|&a| a != hole.axis).map(|a| (c[a] - hole.c[a]).powi(2)).sum();
                if dd.sqrt() <= rad + 1e-9 { // "shall exceed": equal is too close
                    g.cls[at] = BLOCK;
                }
            }
        }
    }
}

/// A pipe's half width in cells: its cross-section of 2r + 1 cells covers its outside diameter
/// and clearance.
fn half_cells(req: &Request, h: f64) -> usize {
    let half = req.od / 2.0 + req.clear;
    ((2.0 * half) / (2.0 * h) - 0.5).ceil().max(0.0) as usize
}

/// A routed service's solid, as boxes, for the requests after it and the clash check.
#[derive(Clone)]
struct Solid {
    owner: String,
    lo: V3,
    hi: V3,
}

fn build_grid(req: &Request, frame: &Frame, rules: &Rules, obstacles: &[(String, V3, V3)], routed: &[Solid], holes: &[Hole])
              -> (Grid, Vec<bool>, Vec<u32>, Vec<bool>) {
    let mut lo = [f64::INFINITY; 3];
    let mut hi = [f64::NEG_INFINITY; 3];
    for (a, b) in &req.zones {
        for i in 0..3 {
            lo[i] = lo[i].min(a[i]);
            hi[i] = hi[i].max(b[i]);
        }
    }
    let h = req.h;
    let n = [((hi[0] - lo[0]) / h).ceil() as usize, ((hi[1] - lo[1]) / h).ceil() as usize, ((hi[2] - lo[2]) / h).ceil() as usize];
    let total = n[0] * n[1] * n[2];
    let mut g = Grid { o: lo, h, n, cls: vec![BLOCK; total], hole: vec![f32::INFINITY; total], ps: [vec![], vec![], vec![], vec![]] };
    for (a, b) in &req.zones {
        if let Some((x, y)) = g.span(*a, *b) {
            for k in x[2]..=y[2] {
                for j in x[1]..=y[1] {
                    for i in x[0]..=y[0] {
                        let c = g.centre([i, j, k]);
                        if inside(c, *a, *b) {
                            let at = g.at([i, j, k]);
                            g.cls[at] = FREE;
                        }
                    }
                }
            }
        }
    }
    let mut sleeve = vec![false; total];
    let mut who = vec![u32::MAX; total];
    let mut web = vec![false; total];
    for p in &frame.pieces {
        let Some((x, y)) = g.span(p.lo, p.hi) else { continue };
        for k in x[2]..=y[2] {
            for j in x[1]..=y[1] {
                for i in x[0]..=y[0] {
                    let at = g.at([i, j, k]);
                    let c = g.cls[at];
                    if c == BLOCK {
                        continue;
                    }
                    match p.bore {
                        None => g.cls[at] = BLOCK,
                        Some((axis, l)) => {
                            if c >= BORE && c != BORE + axis as u8 {
                                g.cls[at] = BLOCK;
                                continue;
                            }
                            let (allowed, _) = frame.limit_at_rules(&l, g.centre([i, j, k]), rules);
                            g.cls[at] = BORE + axis as u8;
                            g.hole[at] = g.hole[at].min(allowed as f32);
                            sleeve[at] = p.sleeve;
                            who[at] = p.member as u32;
                            web[at] = matches!(l, Limit::Apa { .. });
                        }
                    }
                }
            }
        }
    }
    let block = |lo: V3, hi: V3, g: &mut Grid| {
        if let Some((x, y)) = g.span(lo, hi) {
            for k in x[2]..=y[2] {
                for j in x[1]..=y[1] {
                    for i in x[0]..=y[0] {
                        let at = g.at([i, j, k]);
                        g.cls[at] = BLOCK;
                    }
                }
            }
        }
    };
    for (id, a, b) in obstacles {
        if !req.attached(id) {
            block(*a, *b, &mut g);
        }
    }
    for s in routed {
        if !req.attached(&s.owner) {
            block(s.lo, s.hi, &mut g);
        } else if let Some(&(at, m)) = req.near.get(&s.owner) {
            // Attached only near `at`: its solid blocks every cell farther off.
            if let Some((x, y)) = g.span(s.lo, s.hi) {
                for k in x[2]..=y[2] {
                    for j in x[1]..=y[1] {
                        for i in x[0]..=y[0] {
                            let c = g.centre([i, j, k]);
                            if (0..3).any(|a| (c[a] - at[a]).abs() > m) {
                                let ix = g.at([i, j, k]);
                                g.cls[ix] = BLOCK;
                            }
                        }
                    }
                }
            }
        }
    }
    for (a, b) in &req.blocks {
        block(*a, *b, &mut g);
    }
    let need = (req.bore + req.hole_clear) as f32;
    let r = half_cells(req, h);
    let none = HashSet::new();
    for hole in holes {
        exclude(&mut g, &who, &web, hole, need as f64, r, &none);
    }
    let mut maxes: std::collections::HashMap<usize, usize> = std::collections::HashMap::new();
    for hole in holes.iter().filter(|h| h.max) {
        *maxes.entry(hole.member).or_default() += 1;
    }
    for (&m, &n) in &maxes {
        if n >= 3 {
            limit_full(&mut g, &who, &web, m, rules, need);
        }
    }
    for i in 0..total {
        if g.cls[i] >= BORE && g.hole[i] < need {
            g.cls[i] = BLOCK;
        }
    }
    g.prefix();
    (g, sleeve, who, web)
}

impl Frame {
    /// The largest hole a member's rule allows at `p`, and for an I-joist its distance from the
    /// nearer support (for the record).
    fn limit_at_rules(&self, l: &Limit, p: V3, rules: &Rules) -> (f64, f64) {
        match *l {
            Limit::Fixed(h) => (h, f64::NAN),
            Limit::Apa { axis, faces } => {
                let d = (p[axis] - faces.0).min(faces.1 - p[axis]);
                (if d < 0.0 { 0.0 } else { rules.apa_max_hole(d, faces.1 - faces.0) }, d)
            }
        }
    }
}

/// The nearest cell to `p` within `max` (m) where a pipe of half width `r` may run along some axis.
fn snap(g: &Grid, p: V3, r: usize, max: f64) -> Option<usize> {
    let c0: Vec<i64> = (0..3).map(|i| ((p[i] - g.o[i]) / g.h).floor() as i64).collect();
    let m = (max / g.h).ceil() as i64;
    let mut best: Option<(f64, usize)> = None;
    for dz in -m..=m {
        for dy in -m..=m {
            for dx in -m..=m {
                let c = [c0[0] + dx, c0[1] + dy, c0[2] + dz];
                if (0..3).any(|i| c[i] < 0 || c[i] >= g.n[i] as i64) {
                    continue;
                }
                let cu = [c[0] as usize, c[1] as usize, c[2] as usize];
                let q = g.centre(cu);
                let d = ((q[0] - p[0]).powi(2) + (q[1] - p[1]).powi(2) + (q[2] - p[2]).powi(2)).sqrt();
                if d > max || best.is_some_and(|(bd, _)| bd <= d) {
                    continue;
                }
                if (0..3).any(|a| g.passable(cu, a, r)) {
                    best = Some((d, g.at(cu)));
                }
            }
        }
    }
    best.map(|b| b.1)
}

/// A route's solids from its points: each straight run as a box of the pipe's outside diameter and
/// clearance across it (the router clears a pipe's cross-section cell by cell; its ends are its
/// fittings). A drain's sloped run goes in pieces of `PIECE_M`, each boxed to its own heights, so
/// the box doesn't reach over what the run passes above.
const PIECE_M: f64 = 0.25;
/// A straight run's diagonal (`Request::straight`) goes in pieces this long: each piece's box is
/// the pipe's and a few centimetres more, not the diagonal's whole rectangle.
const DIAG_M: f64 = 0.05;
fn solids_of(owner: &str, pts: &[V3], half: f64, straight: bool) -> Vec<Solid> {
    let mut out = Vec::new();
    for w in pts.windows(2) {
        let (a, c) = (w[0], w[1]);
        let run = (0..3).max_by(|&i, &j| (c[i] - a[i]).abs().total_cmp(&(c[j] - a[j]).abs())).unwrap();
        let skew = (0..3).filter(|&i| (c[i] - a[i]).abs() > 1e-9).count() > 1;
        let n = if straight && skew {
            (dist(a, c) / DIAG_M).ceil().max(1.0) as usize
        } else if run != 2 && (c[2] - a[2]).abs() > 1e-9 {
            ((c[run] - a[run]).abs() / PIECE_M).ceil().max(1.0) as usize
        } else {
            1
        };
        for k in 0..n {
            let (t0, t1) = (k as f64 / n as f64, (k + 1) as f64 / n as f64);
            let p0: V3 = std::array::from_fn(|i| a[i] + (c[i] - a[i]) * t0);
            let p1: V3 = std::array::from_fn(|i| a[i] + (c[i] - a[i]) * t1);
            let e = |i: usize| if i == run { 0.0 } else { half };
            out.push(Solid { owner: owner.to_string(), lo: std::array::from_fn(|i| p0[i].min(p1[i]) - e(i)),
                             hi: std::array::from_fn(|i| p0[i].max(p1[i]) + e(i)) });
        }
    }
    out
}

/// The indices along `path` where it turns, and its ends.
fn turns(g: &Grid, path: &[usize]) -> Vec<usize> {
    let pts: Vec<[usize; 3]> = path.iter().map(|&i| g.cell(i)).collect();
    let mut out = vec![0];
    for w in 1..pts.len() {
        let last = w + 1 == pts.len();
        let turn = !last && {
            let a: Vec<i64> = (0..3).map(|k| pts[w][k] as i64 - pts[w - 1][k] as i64).collect();
            let b: Vec<i64> = (0..3).map(|k| pts[w + 1][k] as i64 - pts[w][k] as i64).collect();
            a != b
        };
        if turn || last {
            out.push(w);
        }
    }
    out
}

/// Whether a pipe of `r` cells' half width can run straight from `a` to `b` (m): every cell within
/// `r` of the line (sampled every quarter cell) inside the grid, not blocked, and no member's.
fn sight(g: &Grid, a: V3, b: V3, r: usize) -> bool {
    let n = ((dist(a, b) / (0.25 * g.h)).ceil() as usize).max(1);
    for k in 0..=n {
        let t = k as f64 / n as f64;
        let mut lo = [0usize; 3];
        let mut hi = [0usize; 3];
        for i in 0..3 {
            let c = ((a[i] + (b[i] - a[i]) * t - g.o[i]) / g.h).floor() as i64;
            let (l, u) = (c - r as i64, c + r as i64);
            if l < 0 || u >= g.n[i] as i64 {
                return false;
            }
            lo[i] = l as usize;
            hi[i] = u as usize;
        }
        if (0..4).any(|kk| g.count(kk, lo, hi) > 0) {
            return false;
        }
    }
    true
}

/// A level path (cells, from the tree out) pulled straight: the chain of straight runs through
/// points along it (its corners and every `PULL_STEP`th cell) that turns least in all, a shorter
/// chain breaking ties. A run may jump between any two points in straight sight (`sight`), or go
/// on to the next point along the path as searched. A member it crosses (a stem wall's sleeve, a
/// footing) it crosses as searched: the points `r` + 1 cells before and after are among the
/// points, so a straight run meets the crossing clear of the member. NEC 352.26 counts a conduit's
/// bends in degrees: the least turning is what it asks, not the shortest line (2026-11-22: the
/// farthest point in sight left a feeder a square turn past a footing a 76 degree one avoided).
/// Returns the kept indices, its ends among them.
const PULL_STEP: usize = 2;
fn pull(g: &Grid, path: &[usize], r: usize) -> Vec<usize> {
    let mut cand: Vec<usize> = turns(g, path);
    cand.extend((0..path.len()).step_by(PULL_STEP));
    for k in 1..path.len() {
        let (was, is) = (g.cls[path[k - 1]] >= BORE, g.cls[path[k]] >= BORE);
        if !was && is {
            cand.push(k.saturating_sub(r + 2));
            cand.push(k - 1);
        }
        if was && !is {
            cand.push(k);
            cand.push((k + r + 1).min(path.len() - 1));
        }
    }
    cand.sort_unstable();
    cand.dedup();
    let n = cand.len();
    if n < 3 {
        return cand;
    }
    let pts: Vec<V3> = cand.iter().map(|&k| g.centre(g.cell(path[k]))).collect();
    let dir = |i: usize, j: usize| -> V3 {
        let d = dist(pts[i], pts[j]).max(1e-12);
        std::array::from_fn(|k| (pts[j][k] - pts[i][k]) / d)
    };
    let turn = |h: usize, i: usize, j: usize| -> f64 {
        let (u, v) = (dir(h, i), dir(i, j));
        (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]).clamp(-1.0, 1.0).acos().to_degrees()
    };
    const PER_M: f64 = 1e-3; // degrees a metre: length only breaks ties
    // ok[i][j]: a run may go straight from point i to point j.
    let mut ok = vec![vec![false; n]; n];
    for i in 0..n - 1 {
        ok[i][i + 1] = true;
        for j in i + 2..n {
            ok[i][j] = sight(g, pts[i], pts[j], r);
        }
    }
    // best[i][j]: the least turning of a chain from point 0 whose last run is i -> j.
    let mut best = vec![vec![f64::INFINITY; n]; n];
    let mut from = vec![vec![usize::MAX; n]; n];
    for j in 1..n {
        if ok[0][j] {
            best[0][j] = PER_M * dist(pts[0], pts[j]);
        }
    }
    for i in 1..n - 1 {
        for j in i + 1..n {
            if !ok[i][j] {
                continue;
            }
            for h in 0..i {
                if best[h][i].is_finite() {
                    let c = best[h][i] + turn(h, i, j) + PER_M * dist(pts[i], pts[j]);
                    if c < best[i][j] {
                        best[i][j] = c;
                        from[i][j] = h;
                    }
                }
            }
        }
    }
    let last = n - 1;
    let mut i = (0..last).min_by(|&a, &b| best[a][last].total_cmp(&best[b][last])).unwrap();
    let mut chain = vec![last];
    let mut j = last;
    while i != usize::MAX {
        chain.push(i);
        let h = if i == 0 { usize::MAX } else { from[i][j] };
        j = i;
        i = h;
    }
    chain.reverse();
    chain.into_iter().map(|k| cand[k]).collect()
}

/// A polyline's length: each straight run's, end to end (a drain's sloped run along its slope).
fn length(pl: &[V3]) -> f64 {
    pl.windows(2).map(|w| dist(w[0], w[1])).sum()
}

/// Route one request: a tree from its root to its terminals. Returns the JSON record and the
/// solids it adds.
fn route(req: &Request, frame: &Frame, rules: &Rules, obstacles: &[(String, V3, V3)], routed: &[Solid], holes: &[Hole])
         -> (Value, Vec<Solid>, Vec<Hole>) {
    let (mut g, sleeve, who, web) = build_grid(req, frame, rules, obstacles, routed, holes);
    let half = req.od / 2.0 + req.clear;
    let r = half_cells(req, g.h);
    let fail = |why: String| (json!({"id": req.id, "ok": false, "why": why}), vec![], vec![]);
    let mut cut: Vec<Hole> = Vec::new();
    let mut maxes: std::collections::HashMap<usize, usize> = std::collections::HashMap::new();
    for hole in holes.iter().filter(|h| h.max) {
        *maxes.entry(hole.member).or_default() += 1;
    }
    // The goal at first: the root's cell, and every cell of the goal boxes (`goals`).
    let mut tree: Vec<usize> = Vec::new();
    for (a, b) in &req.goals {
        if let Some((x, y)) = g.span(*a, *b) {
            for k in x[2]..=y[2] {
                for j in x[1]..=y[1] {
                    for i in x[0]..=y[0] {
                        if inside(g.centre([i, j, k]), *a, *b) {
                            tree.push(g.at([i, j, k]));
                        }
                    }
                }
            }
        }
    }
    let root = match snap(&g, req.root, r, req.snap) {
        Some(c) => c,
        None if !tree.is_empty() => tree[0],
        None => return fail("root: no room for the pipe near it".into()),
    };
    tree.insert(0, root);
    let mut in_tree: HashSet<usize> = tree.iter().copied().collect();
    // Each tree cell's run from its farthest fixture (a drain's; infinite on the root and the goal
    // boxes, which take a branch at any height).
    let mut run_at: std::collections::HashMap<usize, f64> = tree.iter().map(|&i| (i, f64::INFINITY)).collect();
    let slope = req.slope;
    let mut snaps = vec![json!({"ref": "root", "m": dist(g.centre(g.cell(root)), req.root)})];
    let mut todo: Vec<(String, V3, usize)> = Vec::new();
    let mut failed = Vec::new();
    for (name, p) in &req.terminals {
        match snap(&g, *p, r, req.snap) {
            Some(c) => {
                snaps.push(json!({"ref": name, "m": dist(g.centre(g.cell(c)), *p)}));
                todo.push((name.clone(), *p, c));
            }
            None => failed.push(json!({"ref": name, "why": "no room for the pipe near it"})),
        }
    }
    let mut branches = Vec::new();
    while !todo.is_empty() {
        // The terminal nearest (square) to what is routed so far goes next.
        let near = |c: usize| tree.iter().map(|&t| {
            let (a, b) = (g.cell(c), g.cell(t));
            (0..3).map(|k| (a[k] as i64 - b[k] as i64).unsigned_abs()).sum::<u64>()
        }).min().unwrap_or(0);
        // A drain's farthest fixture first: its branch is the trunk, which the nearer ones join where
        // it has fallen at least as far as they have. Before either, a terminal that failed in an
        // earlier pass (`first`).
        let pick = req.first.iter().find_map(|f| todo.iter().position(|t| &t.0 == f));
        let (k, _) = if let Some(k) = pick {
            (k, 0)
        } else if slope > 0.0 {
            todo.iter().enumerate().map(|(k, t)| (k, near(t.2))).max_by_key(|x| (x.1, std::cmp::Reverse(x.0))).unwrap()
        } else {
            todo.iter().enumerate().map(|(k, t)| (k, near(t.2))).min_by_key(|x| (x.1, x.0)).unwrap()
        };
        let (name, p, c) = todo.remove(k);
        let mut gb = (g.cell(tree[0]), g.cell(tree[0]));
        for &t in &tree {
            let q = g.cell(t);
            for i in 0..3 {
                gb.0[i] = gb.0[i].min(q[i]);
                gb.1[i] = gb.1[i].max(q[i]);
            }
        }
        let runs_now = run_at.clone();
        let goal = move |i: usize, ran: f64| runs_now.get(&i).is_some_and(|&t| ran <= t + 1e-9);
        match search(&g, r, &[c], &goal, gb, rules.turn, rules.cross, rules.sleeve, &sleeve, req.grade, slope, half) {
            None => failed.push(json!({"ref": name, "why": "no path"})),
            Some((mut path, mut ran)) => {
                // Where the pipe is: a drain's under its path by its fall so far.
                let dirn = if req.grade > 0 { 1.0 } else { -1.0 };
                let at = |i: usize, ran: f64| {
                    let mut c = g.centre(g.cell(i));
                    c[2] += dirn * slope * ran;
                    c
                };
                // The cell the pipe is in (a drain's under its path, a vent's over it).
                let own = |i: usize, ran: f64| {
                    let c = g.cell(i);
                    let e = if slope > 0.0 { ((slope * ran / g.h) + 0.5).floor() as i64 } else { 0 };
                    let z = (c[2] as i64 + dirn as i64 * e).clamp(0, g.n[2] as i64 - 1) as usize;
                    g.at([c[0], c[1], z])
                };
                for (&i, &d) in path.iter().zip(&ran) {
                    run_at.entry(i).or_insert(d);
                }
                path.reverse(); // from the tree out to the terminal
                ran.reverse();
                let attach = path[0];
                let keep = if req.straight && slope == 0.0 { pull(&g, &path, r) } else { turns(&g, &path) };
                let pl: Vec<V3> = keep.into_iter().map(|k| at(path[k], ran[k])).collect();
                let mut bores = Vec::new();
                let mut seen = HashSet::new();
                for (k, &i0) in path.iter().enumerate() {
                    let i = own(i0, ran[k]);
                    if g.cls[i] >= BORE && who[i] != u32::MAX && seen.insert(who[i]) {
                        let m = who[i] as usize;
                        let c = at(i0, ran[k]);
                        let piece = frame.pieces.iter().find(|q| q.member == m && q.bore.is_some()).unwrap();
                        let (allowed, d) = frame.limit_at_rules(&piece.bore.unwrap().1, c, rules);
                        bores.push(json!({"member": frame.ids[m], "kind": frame.kinds[m], "at": c, "hole_m": req.bore + req.hole_clear,
                                          "allowed_m": allowed, "from_support_m": if d.is_nan() { Value::Null } else { json!(d) },
                                          "axis": (g.cls[i] - BORE) as u64, "sleeve": sleeve[i]}));
                    }
                }
                branches.push(json!({"terminal": name, "to": p, "attach": at(attach, ran[0]), "points": pl,
                                     "length_m": length(&pl), "bends": pl.len().saturating_sub(2), "bores": bores,
                                     "run_m": ran.iter().cloned().fold(0.0, f64::max), "slope": slope}));
                // Its cells join the tree: the next terminals tee into it.
                for &i in &path {
                    if in_tree.insert(i) {
                        tree.push(i);
                    }
                }
                // Its holes in I-joists' webs keep the next branch's holes off (APA's rule 6).
                let mut seen = HashSet::new();
                let mut new = Vec::new();
                for (k, &i0) in path.iter().enumerate() {
                    let i = own(i0, ran[k]);
                    if g.cls[i] >= BORE && web[i] && seen.insert(who[i]) {
                        let d = req.bore + req.hole_clear;
                        new.push(Hole { member: who[i] as usize, c: at(i0, ran[k]), d, axis: (g.cls[i] - BORE) as usize,
                                        max: d > rules.smaller_size(g.hole[i] as f64) + 1e-9 });
                    }
                }
                if !new.is_empty() {
                    for hole in &new {
                        exclude(&mut g, &who, &web, hole, req.bore + req.hole_clear, r, &in_tree);
                        if hole.max {
                            let n = maxes.entry(hole.member).or_default();
                            *n += 1;
                            if *n == 3 {
                                limit_full(&mut g, &who, &web, hole.member, rules, (req.bore + req.hole_clear) as f32);
                            }
                        }
                    }
                    g.prefix();
                    cut.extend(new);
                }
            }
        }
    }
    let mut solids = Vec::new();
    for b in &branches {
        let pts: Vec<V3> = b["points"].as_array().unwrap().iter().map(v3).collect();
        solids.extend(solids_of(&req.id, &pts, half, req.straight));
    }
    let total: f64 = branches.iter().map(|b| b["length_m"].as_f64().unwrap()).sum();
    (json!({"id": req.id, "ok": failed.is_empty(), "branches": branches, "failed": failed, "snaps": snaps, "length_m": total,
            "voxel_m": g.h, "cells": g.len(), "half_cells": r, "first": req.first}), solids, cut)
}

fn dist(a: V3, b: V3) -> f64 {
    ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2) + (a[2] - b[2]).powi(2)).sqrt()
}

/// Every routed and pinned solid: cf-spatial's grid as the broad phase (the solids sharing a
/// voxel), the boxes themselves as the narrow one. Two services' solids (pipe and clearance) that
/// overlap by more than `tol`, neither teeing into the other, are a clash.
fn clashes(solids: &[Solid], attach: &std::collections::HashMap<String, Request>, h: f64, tol: f64) -> Vec<Value> {
    let mut grid: VoxelGrid<Vec<u32>> = VoxelGrid::new(h);
    let owners: Vec<&str> = solids.iter().map(|s| s.owner.as_str()).collect();
    let mut found: HashSet<(u32, u32)> = HashSet::new();
    let overlap = |a: &Solid, b: &Solid| (0..3).all(|i| a.hi[i].min(b.hi[i]) - a.lo[i].max(b.lo[i]) > tol);
    for (k, s) in solids.iter().enumerate() {
        let a = grid.world_to_grid(Point3::new(s.lo[0], s.lo[1], s.lo[2]));
        let b = grid.world_to_grid(Point3::new(s.hi[0], s.hi[1], s.hi[2]));
        for z in a.z..=b.z {
            for y in a.y..=b.y {
                for x in a.x..=b.x {
                    let c = VoxelCoord::new(x, y, z);
                    let here = grid.get_or_insert_default(c);
                    for &j in here.iter() {
                        let (o1, o2) = (owners[j as usize], s.owner.as_str());
                        if o1 == o2 || found.contains(&(j, k as u32)) {
                            continue;
                        }
                        let related = attach.get(o2).is_some_and(|a| a.attached(o1)) || attach.get(o1).is_some_and(|a| a.attached(o2));
                        let pinned = !attach.contains_key(o1) && !attach.contains_key(o2); // placed and checked in 7a
                        if !related && !pinned && overlap(&solids[j as usize], s) {
                            found.insert((j, k as u32));
                        }
                    }
                    here.push(k as u32);
                }
            }
        }
    }
    let mut pairs: Vec<(String, String)> = found.into_iter().map(|(a, b)| {
        let (x, y) = (owners[a as usize].to_string(), owners[b as usize].to_string());
        if x < y { (x, y) } else { (y, x) }
    }).collect();
    pairs.sort();
    pairs.dedup();
    pairs.into_iter().map(|(a, b)| json!([a, b])).collect()
}

/// `routes-json`: every request, in order, then the clash check.
pub fn run(root: &std::path::Path) -> std::io::Result<()> {
    let t0 = std::time::Instant::now();
    let rq: Value = serde_json::from_str(&std::fs::read_to_string(root.join("out/pass3/route-requests.json"))?)?;
    let rules = Rules::from_json(&rq["rules"]);
    let fv: Value = serde_json::from_str(&std::fs::read_to_string(root.join(rq["frame"].as_str().unwrap()))?)?;
    let frame = Frame::from_json(&fv, &rules);
    let obstacles: Vec<(String, V3, V3)> = rq["obstacles"].as_array().into_iter().flatten()
        .map(|o| (o["id"].as_str().unwrap().to_string(), v3(&o["lo"]), v3(&o["hi"]))).collect();
    let pinned: Vec<Solid> = obstacles.iter().filter(|o| o.0.contains('/')).map(|o| Solid { owner: o.0.clone(), lo: o.1, hi: o.2 }).collect();
    let mut reqs: Vec<Request> = rq["requests"].as_array().into_iter().flatten().map(Request::from_json).collect();
    // Up to `passes` passes: after each, each request that failed moves one place earlier among its
    // flat's requests (before the one routed just before it there, which may have shut its way),
    // and the terminals it failed at go first in its own tree (its earlier branches may have shut
    // theirs: a vent's header, from its farthest fixture, took the lane a boxed-in water closet's
    // vent needed, 2026-11-22); all are routed again, and the pass that routes the most is kept.
    // (Sequential routing depends on order; moving the failures to the front of the whole order made
    // things worse, 2026-11-21.)
    let passes = rq["passes"].as_u64().unwrap_or(1).max(1) as usize;
    let mut order: Vec<usize> = (0..reqs.len()).collect();
    let mut best: Option<(usize, Vec<Value>, Vec<Solid>)> = None;
    for pass in 0..passes {
        let mut solids = pinned.clone();
        let mut holes: Vec<Hole> = Vec::new();
        let mut recs: Vec<Option<Value>> = vec![None; reqs.len()];
        for &k in &order {
            let req = &reqs[k];
            let t = std::time::Instant::now();
            let (mut rec, s, hs) = route(req, &frame, &rules, &obstacles, &solids, &holes);
            rec["seconds"] = json!(t.elapsed().as_secs_f64());
            solids.extend(s);
            holes.extend(hs);
            recs[k] = Some(rec);
        }
        let recs: Vec<Value> = recs.into_iter().map(|r| r.unwrap()).collect();
        let ok = recs.iter().filter(|r| r["ok"].as_bool() == Some(true)).count();
        println!("pass {}: {ok} of {} routed", pass + 1, reqs.len());
        let failed: Vec<usize> = order.iter().copied().filter(|&k| recs[k]["ok"].as_bool() != Some(true)).collect();
        for &k in &failed {
            for f in recs[k]["failed"].as_array().into_iter().flatten().filter_map(|f| f["ref"].as_str()) {
                if !reqs[k].first.iter().any(|x| x == f) {
                    reqs[k].first.push(f.to_string());
                }
            }
        }
        if best.as_ref().is_none_or(|b| ok > b.0) {
            best = Some((ok, recs, solids));
        }
        if failed.is_empty() {
            break;
        }
        for &k in &failed {
            if reqs[k].flat.is_empty() {
                continue;
            }
            let pos = order.iter().position(|&x| x == k).unwrap();
            if let Some(prev) = (0..pos).rev().find(|&q| reqs[order[q]].flat == reqs[k].flat) {
                if reqs[order[prev]].id == reqs[k].after {
                    continue;
                }
                let item = order.remove(pos);
                order.insert(prev, item);
            }
        }
    }
    let (_, out, solids) = best.unwrap();
    for (req, rec) in reqs.iter().zip(&out) {
        println!("{:<44} {} {:>7.2} m", req.id, if rec["ok"].as_bool() == Some(true) { "ok  " } else { "FAIL" }, rec["length_m"].as_f64().unwrap_or(0.0));
    }
    let attach: std::collections::HashMap<String, Request> = reqs.into_iter().map(|r| (r.id.clone(), r)).collect();
    let cl = clashes(&solids, &attach, rq["clash_voxel_m"].as_f64().unwrap_or(0.0254), rq["clash_tol_m"].as_f64().unwrap_or(0.001));
    let env = json!({"source": "forge `routes-json` (CortenForge 0.9, cf-spatial's grid; our A*)", "geometry_sha": rq["geometry_sha"],
                     "framing_sha": rq["framing_sha"], "requests_sha": rq["requests_sha"], "routes": out, "clashes": cl,
                     "seconds": t0.elapsed().as_secs_f64()});
    let path = root.join("out/pass3/routes.json");
    std::fs::write(&path, serde_json::to_string(&env)?)?;
    println!("{} routes, {} clashes, {:.1} s: {}", env["routes"].as_array().unwrap().len(), cl.len(), t0.elapsed().as_secs_f64(), path.display());
    Ok(())
}

/// `routes-debug <id>`: one request's grid, written out to look at (`out/pass3/route-debug.json`):
/// its origin, voxel and size, each cell's class run-length coded, and where its ends snapped.
pub fn debug(root: &std::path::Path, id: &str) -> std::io::Result<()> {
    let rq: Value = serde_json::from_str(&std::fs::read_to_string(root.join("out/pass3/route-requests.json"))?)?;
    let rules = Rules::from_json(&rq["rules"]);
    let fv: Value = serde_json::from_str(&std::fs::read_to_string(root.join(rq["frame"].as_str().unwrap()))?)?;
    let frame = Frame::from_json(&fv, &rules);
    let obstacles: Vec<(String, V3, V3)> = rq["obstacles"].as_array().into_iter().flatten()
        .map(|o| (o["id"].as_str().unwrap().to_string(), v3(&o["lo"]), v3(&o["hi"]))).collect();
    let v = rq["requests"].as_array().into_iter().flatten().find(|r| r["id"] == id)
        .ok_or_else(|| std::io::Error::other(format!("no request {id}")))?;
    let req = Request::from_json(v);
    // The services routed before it, from the last run, as the router saw them.
    let mut routed = Vec::new();
    let mut holes = Vec::new();
    let index: std::collections::HashMap<&str, usize> = frame.ids.iter().enumerate().map(|(k, s)| (s.as_str(), k)).collect();
    if let Ok(t) = std::fs::read_to_string(root.join("out/pass3/routes.json")) {
        let rv: Value = serde_json::from_str(&t)?;
        let reqs: std::collections::HashMap<String, &Value> = rq["requests"].as_array().into_iter().flatten()
            .map(|r| (r["id"].as_str().unwrap().to_string(), r)).collect();
        for rec in rv["routes"].as_array().into_iter().flatten() {
            let rid = rec["id"].as_str().unwrap_or("");
            if rid == id { break; }
            let r0 = reqs[rid];
            let half = r0["od_m"].as_f64().unwrap() / 2.0 + r0["clear_m"].as_f64().unwrap_or(0.0);
            for b in rec["branches"].as_array().into_iter().flatten() {
                for bo in b["bores"].as_array().into_iter().flatten() {
                    if let Some(&m) = bo["member"].as_str().and_then(|s| index.get(s)) {
                        let d = bo["hole_m"].as_f64().unwrap();
                        let max = d > rules.smaller_size(bo["allowed_m"].as_f64().unwrap_or(f64::INFINITY)) + 1e-9;
                        holes.push(Hole { member: m, c: v3(&bo["at"]), d, axis: bo["axis"].as_u64().unwrap() as usize, max });
                    }
                }
                let pts: Vec<V3> = b["points"].as_array().unwrap().iter().map(v3).collect();
                routed.extend(solids_of(rid, &pts, half, r0["straight"].as_bool().unwrap_or(false)));
            }
        }
    }
    let (g, _, _, _) = build_grid(&req, &frame, &rules, &obstacles, &routed, &holes);
    let r = half_cells(&req, g.h);
    let mut rle: Vec<(u8, u32)> = Vec::new();
    for &c in &g.cls {
        match rle.last_mut() {
            Some((k, n)) if *k == c => *n += 1,
            _ => rle.push((c, 1)),
        }
    }
    let root_s = snap(&g, req.root, r, req.snap).map(|i| g.cell(i));
    // Where each terminal can reach (the search's moves, without costs), and how near that comes
    // to the goal: the root's cell and the goal boxes' cells.
    let mut goal: Vec<usize> = root_s.map(|c| vec![g.at(c)]).unwrap_or_default();
    for (a, b) in &req.goals {
        if let Some((x, y)) = g.span(*a, *b) {
            for k in x[2]..=y[2] { for j in x[1]..=y[1] { for i in x[0]..=y[0] {
                if inside(g.centre([i, j, k]), *a, *b) { goal.push(g.at([i, j, k])); }
            } } }
        }
    }
    let open_goal = goal.iter().filter(|&&i| (0..3).any(|a| g.passable(g.cell(i), a, r))).count();
    // (A drain's fall as the search keeps it, its run taken at a cell's first reaching.)
    let dirn = if req.grade > 0 { 1.0 } else { -1.0 };
    let fall = |d: f64| dirn * req.slope * d;
    let half = req.od / 2.0 + req.clear;
    let reach = |s: usize| -> Vec<bool> {
        let mut seen = vec![false; g.len()];
        let mut run = vec![0f64; g.len()];
        let mut q = std::collections::VecDeque::from([s]);
        seen[s] = true;
        while let Some(i) = q.pop_front() {
            let c = g.cell(i);
            for d in 0..6u8 {
                let axis = (d / 2) as usize;
                if (req.grade < 0 && d == 4) || (req.grade > 0 && d == 5) { continue; }
                let mut nc = c;
                if d % 2 == 0 { if c[axis] + 1 >= g.n[axis] { continue; } nc[axis] += 1; }
                else { if c[axis] == 0 { continue; } nc[axis] -= 1; }
                let j = g.at(nc);
                let rj = if axis == 2 { run[i] } else { run[i] + g.h };
                let (ej, ei) = (fall(rj), fall(run[i]));
                let ok = if axis != 2 {
                    g.passable_shift(nc, axis, r, ej, half) && g.passable_shift(c, axis, r, ei, half)
                } else {
                    let at = |q: [usize; 3], e: f64| {
                        let z = q[2] as i64 + (e / g.h).round() as i64;
                        z >= 0 && (z as usize) < g.n[2] && g.passable([q[0], q[1], z as usize], 2, r)
                    };
                    at(nc, ej) && at(c, ei)
                };
                if !seen[j] && ok {
                    seen[j] = true;
                    run[j] = rj;
                    q.push_back(j);
                }
            }
        }
        seen
    };
    let ends: Vec<Value> = req.terminals.iter().map(|(n, p)| {
        let s = snap(&g, *p, r, req.snap);
        let mut info = json!({"ref": n, "cell": s.map(|i| g.cell(i))});
        if let Some(s) = s {
            let seen = reach(s);
            let cells: Vec<usize> = (0..g.len()).filter(|&i| seen[i]).collect();
            let mut lo = [usize::MAX; 3];
            let mut hi = [0usize; 3];
            for &i in &cells { let c = g.cell(i); for k in 0..3 { lo[k] = lo[k].min(c[k]); hi[k] = hi[k].max(c[k]); } }
            let mut best = (u64::MAX, 0usize, 0usize);
            for &i in cells.iter().step_by(1.max(cells.len() / 20000)) {
                let a = g.cell(i);
                for &t in goal.iter().step_by(1.max(goal.len() / 200)) {
                    let b = g.cell(t);
                    let m: u64 = (0..3).map(|k| (a[k] as i64 - b[k] as i64).unsigned_abs()).sum();
                    if m < best.0 { best = (m, i, t); }
                }
            }
            info["reached"] = json!(cells.len());
            info["reached_lo"] = json!(lo);
            info["reached_hi"] = json!(hi);
            info["nearest"] = json!({"cells": best.0, "from": g.cell(best.1), "to": g.cell(best.2)});
        }
        info
    }).collect();
    println!("goal cells {}, {} open to the pipe", goal.len(), open_goal);
    for e in &ends { println!("{e}"); }
    std::fs::write(root.join("out/pass3/route-debug.json"), serde_json::to_string(&json!({
        "id": id, "o": g.o, "h": g.h, "n": g.n, "half_cells": r, "rle": rle, "root": root_s, "terminals": ends,
    }))?)?;
    println!("{id}: {:?} cells of {:.4} m, half width {r}; root {:?}", g.n, g.h, root_s);
    Ok(())
}

/// `routes-check`: the router on cases with known answers.
pub fn check() -> bool {
    let rules = Rules {
        apa: vec![(2.0, 7.0), (3.0, 21.0), (4.0, 36.0), (5.0, 52.0), (6.0, 69.0), (6.25, 73.0), (7.0, 86.0), (8.0, 105.0), (8.625, 118.0)]
            .into_iter().map(|(a, b)| (a * 0.0254, b * 0.0254)).collect(),
        saf: 214.0 * 0.0254, min_edge: 6.0 * 0.0254, any_hole: 1.5 * 0.0254, stud_nb: 0.6, stud_b: 0.4, plate_nb: 0.6, plate_b: 0.4,
        sawn_frac: 1.0 / 3.0, sawn_edge: 2.0 * 0.0254, nonbearing: vec![], turn: 0.3, cross: 0.05, sleeve: 0.5,
    };
    let mut ok = true;
    let mut say = |label: &str, pass: bool, detail: String| {
        println!("{}  {label}: {detail}", if pass { "ok  " } else { "FAIL" });
        ok &= pass;
    };
    let empty = Frame { ids: vec![], kinds: vec![], pieces: vec![] };
    let h = 0.0254;
    let req = |zones: Vec<(V3, V3)>, a: V3, b: V3| Request {
        id: "check".into(), od: 0.02, bore: 0.02, clear: 0.0, hole_clear: 0.0, h, root: a, terminals: vec![("t".into(), b)], zones, snap: 0.05,
        attach: HashSet::new(), grade: 0, goals: vec![], blocks: vec![], slope: 0.0, flat: String::new(), after: String::new(), near: std::collections::HashMap::new(), first: vec![],
        straight: false,
    };
    // 1. An empty box: the route is the square length, with at most two bends.
    let (a, b) = ([0.1, 0.1, 0.1], [0.8, 0.7, 0.5]);
    let (rec, _, _) = route(&req(vec![([0.0; 3], [1.0, 1.0, 0.6])], a, b), &empty, &rules, &[], &[], &[]);
    let br = &rec["branches"][0];
    let l = br["length_m"].as_f64().unwrap_or(0.0);
    let sq = (b[0] - a[0]).abs() + (b[1] - a[1]).abs() + (b[2] - a[2]).abs();
    say("an empty box routes at its square length with at most two bends", (l - sq).abs() <= 3.0 * h && br["bends"].as_u64().unwrap_or(9) <= 2,
        format!("{l:.3} m against {sq:.3}, {} bends", br["bends"]));
    // 1b. The same box with the run asked straight (a feeder's conduit under the slab): one line,
    // its length the straight distance between its cells, no bend.
    let (rec, sol, _) = route(&Request { straight: true, ..req(vec![([0.0; 3], [1.0, 1.0, 0.6])], a, b) }, &empty, &rules, &[], &[], &[]);
    let br = &rec["branches"][0];
    let l = br["length_m"].as_f64().unwrap_or(0.0);
    let line = dist(a, b);
    let widest = sol.iter().map(|s| (0..3).map(|i| s.hi[i] - s.lo[i]).fold(0.0, f64::max)).fold(0.0, f64::max);
    say("asked straight, an empty box routes as one line, boxed in short pieces", (l - line).abs() <= 2.0 * h && br["bends"].as_u64() == Some(0)
        && widest <= DIAG_M + 2.0 * 0.01 + 1e-9, format!("{l:.3} m against {line:.3}, {} bends; widest box {widest:.3} m", br["bends"]));
    // 2. A wall with one gap: the detour's closed form.
    let wall = Frame { ids: vec!["wall".into(), "wall".into()], kinds: vec!["x".into(), "x".into()], pieces: vec![
        Piece { member: 0, lo: [0.95, 0.0, 0.0], hi: [1.05, 0.8, 0.1], bore: None, sleeve: false },
        Piece { member: 1, lo: [0.95, 0.9, 0.0], hi: [1.05, 1.0, 0.1], bore: None, sleeve: false }] };
    let (a, b) = ([0.2, 0.2, 0.05], [1.8, 0.2, 0.05]);
    let (rec, _, _) = route(&req(vec![([0.0; 3], [2.0, 1.0, 0.1])], a, b), &wall, &rules, &[], &[], &[]);
    let l = rec["branches"][0]["length_m"].as_f64().unwrap_or(0.0);
    let closed = (b[0] - a[0]) + 2.0 * (0.85 - 0.2);
    say("a wall with one gap routes through it at the detour's closed form", (l - closed).abs() <= 3.0 * h,
        format!("{l:.3} m against {closed:.3}"));
    // 3. A member bored only across one axis blocks a pipe running along another.
    let stud = Frame { ids: vec!["stud".into()], kinds: vec!["studs".into()], pieces: vec![
        Piece { member: 0, lo: [0.0, 0.48, 0.0], hi: [1.0, 0.52, 0.1], bore: Some((1, Limit::Fixed(0.06))), sleeve: false }] };
    let (rec, _, _) = route(&req(vec![([0.0; 3], [1.0, 1.0, 0.1])], [0.5, 0.1, 0.05], [0.5, 0.9, 0.05]), &stud, &rules, &[], &[], &[]);
    let bores = rec["branches"][0]["bores"].as_array().map(|v| v.len()).unwrap_or(0);
    let (rec2, _, _) = route(&req(vec![([0.0, 0.48, 0.0], [1.0, 0.52, 0.1])], [0.1, 0.5, 0.05], [0.9, 0.5, 0.05]), &stud, &rules, &[], &[], &[]);
    say("a member bored across y lets a pipe through along y, not along it", bores == 1 && rec2["ok"] == false,
        format!("across: {bores} bore; along: {}", if rec2["ok"] == false { "refused" } else { "ROUTED" }));
    // 3b. An insulated pipe whose insulation stops at the member it passes (IECC C404.4) bores for
    // its bare pipe: through the 0.06 m the stud allows by its 0.04 m pipe, not by its 0.07 m whole.
    let fat = |bore: f64| Request { od: 0.07, bore, ..req(vec![([0.0; 3], [1.0, 1.0, 0.1])], [0.5, 0.1, 0.05], [0.5, 0.9, 0.05]) };
    let (bare, _, _) = route(&fat(0.04), &stud, &rules, &[], &[], &[]);
    let (whole, _, _) = route(&fat(0.07), &stud, &rules, &[], &[], &[]);
    let holes: Vec<f64> = bare["branches"][0]["bores"].as_array().into_iter().flatten().filter_map(|b| b["hole_m"].as_f64()).collect();
    say("an insulated pipe bores for its bare pipe where its insulation stops at the member (IECC C404.4)",
        holes.len() == 1 && (holes[0] - 0.04).abs() < 1e-9 && whole["ok"] == false,
        format!("0.07 m insulated, 0.06 m allowed: by its 0.04 m pipe {:?} m; by its whole {}", holes,
                if whole["ok"] == false { "refused" } else { "ROUTED" }));
    // 3c. A pipe attached to another only near a point (a flat's loop's return at its hot branch's
    // end) leaves it there and keeps clear of the rest of it: off that point, never nearer the first
    // pipe's line than their two halves.
    let room = vec![([0.0; 3], [1.0, 1.0, 0.1])];
    let (_, a_sol, _) = route(&Request { id: "a".into(), ..req(room.clone(), [0.1, 0.5, 0.05], [0.9, 0.5, 0.05]) }, &empty, &rules, &[], &[], &[]);
    let mut near = std::collections::HashMap::new();
    near.insert("a".to_string(), ([0.9, 0.5, 0.05], 0.1));
    let b = Request { id: "b".into(), attach: ["a".to_string()].into_iter().collect(), near, ..req(room, [0.1, 0.9, 0.05], [0.9, 0.5, 0.05]) };
    let (rb, _, _) = route(&b, &empty, &rules, &[], &a_sol, &[]);
    let pts: Vec<V3> = rb["branches"][0]["points"].as_array().into_iter().flatten().map(v3).collect();
    let mut least = f64::INFINITY;
    for w in pts.windows(2) {
        for s in 0..=100 {
            let t = s as f64 / 100.0;
            let q: V3 = std::array::from_fn(|i| w[0][i] + t * (w[1][i] - w[0][i]));
            if (q[0] - 0.9).abs() > 0.1 + h || (q[1] - 0.5).abs() > 0.1 + h {
                least = least.min((q[1] - 0.5).abs().max(if q[0] > 0.9 { q[0] - 0.9 } else if q[0] < 0.1 { 0.1 - q[0] } else { 0.0 }));
            }
        }
    }
    say("a pipe attached to another only near a point leaves it there and keeps clear of the rest of it",
        rb["ok"] != false && pts.len() > 1 && least >= 0.02 - 1e-9,
        format!("off the point, at least {least:.3} m from the first pipe's line (their halves 0.020)"));
    // 4. APA's chart: the holes Table 5 allows on a full span, and note e's reduction on a short one.
    let full: Vec<f64> = [6.0, 7.0, 21.0, 36.0, 52.0, 69.0, 118.0].iter().map(|d| rules.apa_max_hole(d * 0.0254, 20.0 * 0.3048) / 0.0254).collect();
    let want = [1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.625];
    // A 10 ft span: the distances shrink by 120/214, so at 36 in. a 5 in. hole (52 x 0.56 = 29.2) but not a 6 (38.7).
    let short = rules.apa_max_hole(36.0 * 0.0254, 10.0 * 0.3048) / 0.0254;
    say("APA Table 5's PRI-60 row, and its span reduction", full.iter().zip(want).all(|(a, b)| (a - b).abs() < 1e-9) && (short - 5.0).abs() < 1e-9,
        format!("{full:?} in. at 6-118 in.; 10 ft span at 36 in.: {short} in."));
    // 5. APA's rule 6: two 2 in. pipes across one I-joist's web, the second asked to cross 2 in.
    // from the first, must cross where the holes' edges are over twice 2 in. apart (centres 6 in.).
    let joist = Frame { ids: vec!["joist".into()], kinds: vec!["floor joists".into()], pieces: vec![
        Piece { member: 0, lo: [0.0, 0.495, 0.0], hi: [6.0, 0.505, 0.3], bore: Some((1, Limit::Apa { axis: 0, faces: (0.0, 6.0) })), sleeve: false }] };
    let pipe = |x: f64| Request { od: 0.0508, bore: 0.0508, ..req(vec![([0.0; 3], [6.0, 1.0, 0.3])], [x, 0.1, 0.15], [x, 0.9, 0.15]) };
    let (r1, _, h1) = route(&pipe(3.0), &joist, &rules, &[], &[], &[]);
    let (r2, _, h2) = route(&pipe(3.05), &joist, &rules, &[], &[], &h1);
    let (r3, _, _) = route(&pipe(3.05), &joist, &rules, &[], &[], &[]);
    let gap = match (h1.first(), h2.first()) {
        (Some(a), Some(b)) => ((a.c[0] - b.c[0]).powi(2) + (a.c[2] - b.c[2]).powi(2)).sqrt(),
        _ => 0.0,
    };
    let alone = r3["length_m"].as_f64().unwrap_or(0.0);
    say("APA's rule 6: a second hole keeps its edge over twice the larger hole from the first",
        r1["ok"] == true && r2["ok"] == true && gap > 6.0 * 0.0254 + 1e-9 && (alone - 0.8).abs() <= h,
        format!("centres {:.2} in. apart (over 6 in.); alone it crosses straight, {alone:.3} m", gap / 0.0254));
    // 6. A drain falls by its slope along every level run, from its fixture to its stack.
    let slope = 0.25 / 12.0;
    let drain = Request { grade: -1, slope, ..req(vec![([0.0; 3], [3.0, 1.0, 0.4])], [0.1, 0.5, 0.1], [2.9, 0.5, 0.3]) };
    let (rd, _, _) = route(&drain, &empty, &rules, &[], &[], &[]);
    let pts: Vec<V3> = rd["branches"][0]["points"].as_array().map(|v| v.iter().map(v3).collect()).unwrap_or_default();
    let worst = pts.windows(2).filter(|w| (w[1][0] - w[0][0]).abs() + (w[1][1] - w[0][1]).abs() > 1e-9)
        .map(|w| ((w[1][2] - w[0][2]) - slope * ((w[1][0] - w[0][0]).abs() + (w[1][1] - w[0][1]).abs())).abs()).fold(0.0, f64::max);
    let drop = pts.last().map(|q| q[2]).unwrap_or(0.0) - pts.first().map(|q| q[2]).unwrap_or(0.0);
    say("a drain rises toward its fixture by its slope along every level run (1/4 in./ft)",
        rd["ok"] == true && !pts.is_empty() && worst < 1e-9,
        format!("{} points, {:.3} m from its stack to its fixture, level runs off their slope by at most {worst:.1e} m", pts.len(), drop));
    // 7. A vent rises toward its stack by its slope along every level run (it drains back).
    let vent = Request { grade: 1, slope: 0.125 / 12.0, ..req(vec![([0.0; 3], [3.0, 1.0, 0.4])], [0.1, 0.5, 0.3], [2.9, 0.5, 0.1]) };
    let (rv, _, _) = route(&vent, &empty, &rules, &[], &[], &[]);
    let pts: Vec<V3> = rv["branches"][0]["points"].as_array().map(|v| v.iter().map(v3).collect()).unwrap_or_default();
    let worst = pts.windows(2).filter(|w| (w[1][0] - w[0][0]).abs() + (w[1][1] - w[0][1]).abs() > 1e-9)
        .map(|w| ((w[0][2] - w[1][2]) - vent.slope * ((w[1][0] - w[0][0]).abs() + (w[1][1] - w[0][1]).abs())).abs()).fold(0.0, f64::max);
    say("a vent falls toward its fixture by its slope along every level run (1/8 in./ft)", rv["ok"] == true && !pts.is_empty() && worst < 1e-9,
        format!("{} points, level runs off their slope by at most {worst:.1e} m", pts.len()));
    // 8. APA's rule 11: a joist with three maximum-size holes refuses a fourth (here a 2 in. hole
    // 8 in. from the support, where 2 in. is the limit) but takes a smaller one (1-1/2 in.).
    let three: Vec<Hole> = [3.0, 4.0, 5.0].iter().map(|&x| Hole { member: 0, c: [x, 0.5, 0.15], d: 0.1, axis: 1, max: true }).collect();
    let near = |od: f64| Request { od, bore: od, ..req(vec![([0.15, 0.0, 0.0], [0.25, 1.0, 0.3])], [0.2, 0.1, 0.15], [0.2, 0.9, 0.15]) };
    let (r4, _, _) = route(&near(0.0508), &joist, &rules, &[], &[], &three);
    let (r5, _, _) = route(&near(0.0381), &joist, &rules, &[], &[], &three);
    let (r6, _, _) = route(&near(0.0508), &joist, &rules, &[], &[], &[]);
    say("APA's rule 11: a joist with three maximum-size holes refuses a fourth, not a smaller hole",
        r4["ok"] == false && r5["ok"] == true && r6["ok"] == true,
        format!("2 in. with three there: {}; 1-1/2 in.: {}; 2 in. alone: {}", if r4["ok"] == true { "ROUTED" } else { "refused" },
                if r5["ok"] == true { "routed" } else { "REFUSED" }, if r6["ok"] == true { "routed" } else { "REFUSED" }));
    ok
}
