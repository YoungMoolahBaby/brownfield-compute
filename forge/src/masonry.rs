//! The walk-up in 8 in. concrete block bearing walls with 8 in. hollow-core plank floors and roof
//! (pass 3b), on the same plan as the wood and steel frames, from `brownfield masonry`'s sizes
//! (`../out/pass3/masonry.json`).
//!
//! Every block is laid: 16 x 8 in. units on 3/8 in. joints in running bond, 14 courses a storey
//! below the planks, the walls cut round the openings (which move to the 8 in. coursing: windows
//! from a 40 in. sill to an 88 in. head, the same 48 in. tall; doors 80 in.), a precast lintel over
//! each opening bearing 8 in. either side. The planks bear 3 in. on the facades and the spine (the
//! roof over the stair on the stair walls); at plank level a half-width filler course carries the
//! facade's outer face up past the plank ends. Not modelled: grout, reinforcement and bond beams
//! (as cores and courses), corner bonding, the stair, the walls inside the flats.
//!
//! Same frame as `apartment.rs` (mm; x across the depth from the front facade, y along the length,
//! z up from the top of the slab).

use nalgebra::Vector3;
use serde_json::Value;

use crate::apartment::{Building, Face, Opening};
use crate::framing::{Kind, Member};

pub struct Spec {
    pub t: f64,
    pub course: f64,
    pub unit: f64,
    pub joint: f64,
    pub courses: usize,
    pub sill: f64,
    pub head: f64,
    pub door_head: f64,
    pub lintel_bearing: f64,
    pub plank_w: f64,
    pub plank_t: f64,
    pub bearing: f64,
    pub facade_footing: f64,
    pub spine_footing: f64,
    pub footing_t: f64,
    pub plank_density: f64,
    pub lintel_density: f64,
    pub plank_kg: f64,
    pub block_kg: f64,
}

impl Spec {
    pub fn from_json(v: &Value) -> Self {
        let f = |k: &str| v[k].as_f64().unwrap_or_else(|| panic!("masonry.json: no {k} (run `uv run brownfield masonry`)"));
        Spec {
            t: f("cmu_t_mm"), course: f("course_mm"), unit: f("unit_mm"), joint: f("joint_mm"),
            courses: v["courses_below_plank"].as_u64().unwrap_or(14) as usize, sill: f("window_sill_mm"), head: f("window_head_mm"),
            door_head: f("door_head_mm"), lintel_bearing: f("lintel_bearing_mm"), plank_w: f("plank_w_mm"), plank_t: f("plank_t_mm"),
            bearing: f("bearing_mm"), facade_footing: v["footings"]["facade_width_mm"].as_f64().unwrap_or(1000.0),
            spine_footing: v["footings"]["spine_width_mm"].as_f64().unwrap_or(1500.0),
            footing_t: v["footings"]["thickness_mm"].as_f64().unwrap_or(305.0), plank_density: f("plank_density"),
            lintel_density: f("lintel_density"), plank_kg: f("plank_kg"), block_kg: f("block_kg"),
        }
    }
    /// Courses a storey: those below the planks and the plank course.
    pub fn per_storey(&self) -> usize {
        self.courses + 1
    }
}

/// A block wall line: `t` thick from `c0` across, running `a0..a1` along x or y.
struct Line {
    along_y: bool,
    c0: f64,
    a0: f64,
    a1: f64,
    face: Option<Face>,
}

impl Line {
    fn bx(&self, a0: f64, a1: f64, c0: f64, c1: f64, z0: f64, z1: f64) -> (Vector3<f64>, Vector3<f64>) {
        if self.along_y { (Vector3::new(c0, a0, z0), Vector3::new(c1, a1, z1)) } else { (Vector3::new(a0, c0, z0), Vector3::new(a1, c1, z1)) }
    }
}

fn member(kind: Kind, storey: usize, course: usize, nominal: &str, b: (Vector3<f64>, Vector3<f64>)) -> Member {
    let mut m = Member { kind, storey, nominal: Some(nominal.to_string()), boxes: vec![b], panel: None };
    m.panel = Some(course); // the course it's laid in (the build's order)
    m
}

/// The along-intervals of `[lo, hi]` left after taking out `cuts`.
fn subtract(lo: f64, hi: f64, cuts: &[(f64, f64)]) -> Vec<(f64, f64)> {
    let mut pieces = vec![(lo, hi)];
    for &(c0, c1) in cuts {
        pieces = pieces.into_iter().flat_map(|(a, b)| {
            if c1 <= a || c0 >= b { vec![(a, b)] } else { [(a, c0.max(a)), (c1.min(b), b)].into_iter().filter(|(x, y)| y - x > 20.0).collect() }
        }).collect();
    }
    pieces
}

/// One course of a line: running bond (alternate courses offset half a unit), cut round openings
/// and lintels; `c0..c1` across (a full course, or a half-width filler).
fn course(line: &Line, s: &Spec, storey: usize, k: usize, zb: f64, c0: f64, c1: f64, openings: &[&Opening], nominal: &str, out: &mut Vec<Member>) {
    let gk = (storey - 1) * s.per_storey() + k;
    let zc = zb + k as f64 * s.course;
    let mut cuts = Vec::new();
    for o in openings {
        let door = (o.sill - zb).abs() < 1.0;
        let (k0, k1) = if door { (0, (s.door_head / s.course).round() as usize) } else { ((s.sill / s.course).round() as usize, (s.head / s.course).round() as usize) };
        let half = o.width / 2.0;
        if k >= k0 && k < k1 {
            cuts.push((o.along - half, o.along + half));
        }
        if k == k1 {
            let (l0, l1) = (o.along - half - s.lintel_bearing, o.along + half + s.lintel_bearing);
            cuts.push((l0, l1));
            out.push(member(Kind::Lintel, storey, gk, "8 in. precast lintel", line.bx(l0, l1, c0, c1, zc + s.joint, zc + s.course)));
        }
    }
    let offset = if gk % 2 == 1 { s.unit / 2.0 } else { 0.0 };
    let mut p = line.a0 - offset;
    while p < line.a1 {
        let (lo, hi) = (p.max(line.a0), (p + s.unit - s.joint).min(line.a1));
        for (a, b) in subtract(lo, hi, &cuts).into_iter().filter(|(a, b)| b - a > 20.0) {
            out.push(member(Kind::Block, storey, gk, nominal, line.bx(a, b, c0, c1, zc + s.joint, zc + s.course)));
        }
        p += s.unit;
    }
}

pub fn build(b: &Building, s: &Spec) -> Vec<Member> {
    let mut out = Vec::new();
    let (w, l, t) = (b.depth, b.length, s.t);
    let (s0, s1) = (b.flat_len, l - b.flat_len);
    let cx = w / 2.0;
    let filler = t - s.bearing - 25.0; // the wall's outer part at plank level, 25 mm (grout) clear of the plank ends

    // Foundation: as for the frames, under the block walls.
    let (grade, frost, stem_t) = (-8.0 * 25.4, 36.0 * 25.4, 8.0 * 25.4);
    let (fb, ft) = (grade - frost, grade - frost + s.footing_t);
    let fw = s.facade_footing;
    let foot = |out: &mut Vec<Member>, kind, lo, hi| out.push(Member { kind, storey: 0, nominal: None, boxes: vec![(lo, hi)], panel: None });
    for (x0, x1) in [(0.0, stem_t), (w - stem_t, w)] {
        let xc = (x0 + x1) / 2.0;
        foot(&mut out, Kind::Footing, Vector3::new(xc - fw / 2.0, -fw / 2.0 + stem_t / 2.0, fb), Vector3::new(xc + fw / 2.0, l + fw / 2.0 - stem_t / 2.0, ft));
        foot(&mut out, Kind::Stem, Vector3::new(x0, 0.0, ft), Vector3::new(x1, l, 0.0));
    }
    for (y0, y1) in [(0.0, stem_t), (l - stem_t, l)] {
        let yc = (y0 + y1) / 2.0;
        foot(&mut out, Kind::Footing, Vector3::new(fw / 2.0 + stem_t / 2.0, yc - fw / 2.0, fb), Vector3::new(w - fw / 2.0 - stem_t / 2.0, yc + fw / 2.0, ft));
        foot(&mut out, Kind::Stem, Vector3::new(stem_t, y0, ft), Vector3::new(w - stem_t, y1, 0.0));
    }
    let slab_t = 4.0 * 25.4;
    let sw = s.spine_footing;
    for (y0, y1) in [(stem_t, s0 + t / 2.0), (s1 - t / 2.0, l - stem_t)] {
        foot(&mut out, Kind::Footing, Vector3::new(cx - sw / 2.0, y0, -slab_t - s.footing_t), Vector3::new(cx + sw / 2.0, y1, -slab_t));
    }
    foot(&mut out, Kind::Slab, Vector3::new(stem_t, stem_t, -slab_t), Vector3::new(w - stem_t, l - stem_t, 0.0));

    let front = Line { along_y: true, c0: 0.0, a0: 0.0, a1: l, face: Some(Face::Front) };
    let back = Line { along_y: true, c0: w - t, a0: 0.0, a1: l, face: Some(Face::Back) };
    let left = Line { along_y: false, c0: 0.0, a0: t, a1: w - t, face: Some(Face::Left) };
    let right = Line { along_y: false, c0: l - t, a0: t, a1: w - t, face: Some(Face::Right) };
    let spine = [Line { along_y: true, c0: cx - t / 2.0, a0: t, a1: s0 - t / 2.0, face: None },
                 Line { along_y: true, c0: cx - t / 2.0, a0: s1 + t / 2.0, a1: l - t, face: None }];
    let stair = [Line { along_y: false, c0: s0 - t / 2.0, a0: t, a1: w - t, face: None },
                 Line { along_y: false, c0: s1 - t / 2.0, a0: t, a1: w - t, face: None }];

    for storey in 1..=b.storeys {
        let zb = (storey - 1) as f64 * b.storey;
        let roof = storey == b.storeys;
        let at = |line: &Line| -> Vec<&Opening> {
            line.face.map(|f| b.openings.iter().filter(|o| o.face == f && o.sill >= zb - 1.0 && o.sill < zb + b.storey - 1.0).collect()).unwrap_or_default()
        };
        for k in 0..s.courses {
            for line in [&front, &back, &left, &right] {
                course(line, s, storey, k, zb, line.c0, line.c0 + t, &at(line), "8 in. block", &mut out);
            }
            for line in spine.iter().chain(stair.iter()) {
                course(line, s, storey, k, zb, line.c0, line.c0 + t, &[], "8 in. block", &mut out);
            }
        }
        // The plank course.
        let k = s.courses;
        let gk = (storey - 1) * s.per_storey() + k;
        let zc = zb + k as f64 * s.course;
        // Facades: a half-width filler outside the plank ends along the flats; full blocks along
        // the stair core (no planks bear there, except on the roof, where they run the other way).
        for (line, outer0, outer1) in [(&front, 0.0, filler), (&back, w - filler, w)] {
            // Full blocks at the corners and where the stair walls meet (no plank bears there), the filler along the bays.
            for (a0, a1, half) in [(0.0, t, false), (t, s0 - t / 2.0, true), (s0 - t / 2.0, s1 + t / 2.0, false), (s1 + t / 2.0, l - t, true), (l - t, l, false)] {
                let seg = Line { along_y: true, c0: line.c0, a0, a1, face: None };
                if half { course(&seg, s, storey, k, zb, outer0, outer1, &[], "filler", &mut out); } else { course(&seg, s, storey, k, zb, line.c0, line.c0 + t, &[], "8 in. block", &mut out); }
            }
        }
        for line in [&left, &right] {
            course(line, s, storey, k, zb, line.c0, line.c0 + t, &[], "8 in. block", &mut out);
        }
        // The stair walls: full at floor levels; on the roof the planks over the stair bear on their
        // core side, so a filler on the flat side.
        for (i, line) in stair.iter().enumerate() {
            if roof {
                let (c0, c1) = if i == 0 { (line.c0, line.c0 + filler) } else { (line.c0 + t - filler, line.c0 + t) };
                course(line, s, storey, k, zb, c0, c1, &[], "filler", &mut out);
            } else {
                course(line, s, storey, k, zb, line.c0, line.c0 + t, &[], "8 in. block", &mut out);
            }
        }
        // Planks: two bays, front and back, facade to spine; on the roof also over the stair core.
        let z = (zc, zc + s.plank_t);
        let plank = |out: &mut Vec<Member>, lo: Vector3<f64>, hi: Vector3<f64>| out.push(member(Kind::Plank, storey, gk, if roof { "roof plank" } else { "floor plank" }, (lo, hi)));
        for (y0, y1) in [(t, s0 - t / 2.0), (s1 + t / 2.0, l - t)] {
            let mut y = y0;
            while y1 - y > 100.0 {
                let ye = (y + s.plank_w).min(y1);
                plank(&mut out, Vector3::new(t - s.bearing, y, z.0), Vector3::new(cx - t / 2.0 + s.bearing, ye, z.1));
                plank(&mut out, Vector3::new(cx + t / 2.0 - s.bearing, y, z.0), Vector3::new(w - t + s.bearing, ye, z.1));
                y += s.plank_w;
            }
        }
        if roof {
            let mut x = t;
            while (w - t) - x > 100.0 {
                let xe = (x + s.plank_w).min(w - t);
                plank(&mut out, Vector3::new(x, s0 + t / 2.0 - s.bearing, z.0), Vector3::new(xe, s1 - t / 2.0 + s.bearing, z.1));
                x += s.plank_w;
            }
        }
    }
    out
}

/// The share of `m`'s underside resting on the tops of `others` (those within a mortar joint
/// below it); for planks and lintels, the worse of their two bearing ends.
pub fn support(m: &Member, others: &[&Member], s: &Spec) -> f64 {
    let (lo, hi) = m.bounds();
    let under = |x0: f64, x1: f64, y0: f64, y1: f64| -> f64 {
        let mut a = 0.0;
        for o in others {
            for (olo, ohi) in &o.boxes {
                if ohi.z > lo.z - s.joint - 1.0 && ohi.z < lo.z + 1.0 {
                    let dx = (x1.min(ohi.x) - x0.max(olo.x)).max(0.0);
                    let dy = (y1.min(ohi.y) - y0.max(olo.y)).max(0.0);
                    a += dx * dy;
                }
            }
        }
        a / ((x1 - x0) * (y1 - y0))
    };
    // Planks and lintels span: they bear only at their ends.
    if matches!(m.kind, Kind::Plank | Kind::Lintel) {
        let along_x = (hi.x - lo.x) > (hi.y - lo.y);
        let b = if m.kind == Kind::Plank { s.bearing } else { s.lintel_bearing };
        if along_x { under(lo.x, lo.x + b, lo.y, hi.y).min(under(hi.x - b, hi.x, lo.y, hi.y)) } else { under(lo.x, hi.x, lo.y, lo.y + b).min(under(lo.x, hi.x, hi.y - b, hi.y)) }
    } else {
        under(lo.x, hi.x, lo.y, hi.y)
    }
}
