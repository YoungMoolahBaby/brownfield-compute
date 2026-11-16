//! The wall in front of the coolers (pass 2d, D7), brick by brick.
//!
//! A two-wythe brick wall: a backing wythe in running bond and a face wythe in which every brick is
//! turned about its own vertical axis by an angle read from a pattern, so the face catches light
//! brick by brick (the method of Gramazio Kohler's Gantenbein winery facade, 2006, whose bricks a
//! robot glued; here a solid wall in mortar, so a mason can repair it). Between the wythes a grouted collar joint takes the vertical bars;
//! piers (if any) at a spacing; a coping course; a strip footing. Sizes come from
//! `brownfield wall` (`../out/pass2/wall.json`); without it a provisional spec is used.
//!
//! Frame: mm; y along the wall, x through it (x = 0 the face toward the homes, + toward the
//! yard), z up from the top of the footing.
//!
//! Checks, per brick of the face wythe: no two bricks overlap (separating axes, in plan), every
//! head joint at least `min_joint` and at most `max_joint` wide at its narrowest and widest, the
//! share of its bed resting on the course below (polygon clipping), and how far its back corners
//! reach into the collar joint.

use std::path::Path;

use cortenforge::mesh::types::{IndexedMesh, unit_cube};
use nalgebra::{Point3, Vector2, Vector3};
use serde_json::{Value, json};

use crate::render::{self, Layer, Style, View};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Kind {
    Face,
    Back,
    Pier,
    Coping,
    Footing,
    /// Drawn, not counted: the bed and head joints seen between the face bricks, and the grout.
    Mortar,
}

#[derive(Clone, Debug)]
pub struct Brick {
    pub kind: Kind,
    /// Centre (mm).
    pub c: Vector3<f64>,
    /// Half sizes (mm) in the brick's own frame: x along its length, y through, z up.
    pub h: Vector3<f64>,
    /// Turn about the vertical (radians); the brick's length lies along the wall at yaw = 0.
    pub yaw: f64,
    pub course: usize,
}

impl Brick {
    /// Plan corners (y along the wall, x through it), counter-clockwise.
    pub fn plan(&self) -> [Vector2<f64>; 4] {
        let (s, c) = self.yaw.sin_cos();
        // Length along y, width along x at yaw 0.
        let along = Vector2::new(s, c); // (x, y) of the length axis
        let across = Vector2::new(c, -s);
        let o = Vector2::new(self.c.x, self.c.y);
        [o - along * self.h.x - across * self.h.y, o - along * self.h.x + across * self.h.y,
         o + along * self.h.x + across * self.h.y, o + along * self.h.x - across * self.h.y]
    }
    pub fn volume_m3(&self) -> f64 {
        8.0 * self.h.x * self.h.y * self.h.z / 1e9
    }
    pub fn append_mesh(&self, out: &mut IndexedMesh) {
        let cube = unit_cube();
        let base = out.vertices.len() as u32;
        let (s, c) = self.yaw.sin_cos();
        for v in &cube.vertices {
            // unit_cube spans 0..1; local: length (lx) along the wall, width (wx) through it.
            let lx = (v.x * 2.0 - 1.0) * self.h.x;
            let wx = (v.y * 2.0 - 1.0) * self.h.y;
            let z = (v.z * 2.0 - 1.0) * self.h.z;
            // Length axis at yaw: (x, y) = (sin, cos); width axis (cos, -sin).
            let x = self.c.x + lx * s + wx * c;
            let y = self.c.y + lx * c - wx * s;
            out.vertices.push(Point3::new(x, y, self.c.z + z));
        }
        out.faces.extend(cube.faces.iter().map(|f| [f[0] + base, f[1] + base, f[2] + base]));
    }
}

#[derive(Clone)]
pub struct Spec {
    pub unit: Vector3<f64>, // length, width (bed depth), height of a brick (mm)
    pub joint: f64,
    pub height: f64,
    pub length: f64,
    pub collar: f64,
    pub pier_spacing: f64, // 0 = none
    pub pier_w: f64,       // along the wall
    pub pier_d: f64,       // projection behind the backing wythe (toward the yard)
    pub footing_w: f64,
    pub footing_t: f64,
    pub amp_deg: f64,
    pub wavelength: f64,
    pub centres: Vec<(f64, f64)>,
    pub min_joint: f64,
    pub max_joint: f64,
    pub source: String,
}

impl Spec {
    /// Provisional: US modular brick (7-5/8 x 3-5/8 x 2-1/4 in., 3/8 in. joints), a 6 m wall, a
    /// 2 in. grouted collar joint, piers every 16 ft. Replaced by `wall.json` when it exists.
    pub fn provisional() -> Self {
        Spec {
            unit: Vector3::new(193.7, 92.1, 57.2), joint: 9.5, height: 6000.0, length: 24_384.0, collar: 50.8,
            pier_spacing: 4877.0, pier_w: 406.4, pier_d: 304.8, footing_w: 1200.0, footing_t: 450.0,
            amp_deg: 13.0, wavelength: 3200.0, centres: vec![(7000.0, 4400.0), (18500.0, 1500.0)],
            min_joint: 3.0, max_joint: 25.0, source: "provisional (no ../out/pass2/wall.json)".into(),
        }
    }
    pub fn from_json(v: &Value) -> Self {
        let mut s = Spec::provisional();
        let f = |k: &str, d: f64| v[k].as_f64().unwrap_or(d);
        s.unit = Vector3::new(f("unit_l_mm", s.unit.x), f("unit_w_mm", s.unit.y), f("unit_h_mm", s.unit.z));
        s.joint = f("joint_mm", s.joint);
        s.height = f("height_mm", s.height);
        s.length = f("length_mm", s.length);
        s.collar = f("collar_mm", s.collar);
        s.pier_spacing = f("pier_spacing_mm", s.pier_spacing);
        s.pier_w = f("pier_w_mm", s.pier_w);
        s.pier_d = f("pier_d_mm", s.pier_d);
        s.footing_w = f("footing_w_mm", s.footing_w);
        s.footing_t = f("footing_t_mm", s.footing_t);
        s.amp_deg = f("pattern_amp_deg", s.amp_deg);
        s.wavelength = f("pattern_wavelength_mm", s.wavelength);
        if let Some(cs) = v["pattern_centres_mm"].as_array() {
            s.centres = cs.iter().filter_map(|c| Some((c[0].as_f64()?, c[1].as_f64()?))).collect();
        }
        s.source = v["source"].as_str().unwrap_or("wall.json").to_string();
        s
    }
    pub fn course(&self) -> f64 {
        self.unit.z + self.joint
    }
    pub fn module(&self) -> f64 {
        self.unit.x + self.joint
    }
    pub fn courses(&self) -> usize {
        (self.height / self.course()).floor() as usize
    }
    /// The face's turn (radians) at (y, z): rings spreading from the pattern's centres, like rain on
    /// still water, fading with distance; capped at the amplitude.
    pub fn angle(&self, y: f64, z: f64) -> f64 {
        let mut a = 0.0;
        for (cy, cz) in &self.centres {
            let r = ((y - cy).powi(2) + (z - cz).powi(2)).sqrt();
            a += (2.0 * std::f64::consts::PI * r / self.wavelength).sin() * (-r / (3.0 * self.wavelength)).exp();
        }
        (a.clamp(-1.0, 1.0) * self.amp_deg).to_radians()
    }
}

fn n_courses(s: &Spec) -> usize {
    s.courses()
}

/// The wall's bricks, course by course.
pub fn build(s: &Spec) -> Vec<Brick> {
    let mut out = Vec::new();
    let (l, w, hgt) = (s.unit.x, s.unit.y, s.unit.z);
    let half = Vector3::new(l / 2.0, w / 2.0, hgt / 2.0);
    let x_face = w / 2.0;
    let x_back = w + s.collar + w / 2.0;
    let thick = 2.0 * w + s.collar;
    let piers: Vec<f64> = if s.pier_spacing > 0.0 {
        let n = (s.length / s.pier_spacing).floor() as usize;
        (0..=n).map(|i| i as f64 * s.pier_spacing).filter(|y| *y <= s.length).collect()
    } else {
        Vec::new()
    };
    // Footing under everything (one box; drawn and measured, not a brick).
    let fd = thick + if piers.is_empty() { 0.0 } else { s.pier_d };
    let fx = fd / 2.0;
    out.push(Brick { kind: Kind::Footing, c: Vector3::new(fx, s.length / 2.0, -s.footing_t / 2.0),
                     h: Vector3::new(s.length / 2.0 + 150.0, s.footing_w.max(fd + 300.0) / 2.0, s.footing_t / 2.0), yaw: 0.0, course: 0 });
    // The mortar, for drawing only: a plane 10 mm behind the face (tooled joints) and the collar
    // joint's grout, both the wall's full length and height.
    let top = s.joint + (n_courses(s) - 1) as f64 * s.course();
    out.push(Brick { kind: Kind::Mortar, c: Vector3::new((10.0 + w) / 2.0, s.length / 2.0, top / 2.0),
                     h: Vector3::new(s.length / 2.0, (w - 10.0) / 2.0, top / 2.0), yaw: 0.0, course: 0 });
    out.push(Brick { kind: Kind::Mortar, c: Vector3::new(w + s.collar / 2.0, s.length / 2.0, top / 2.0),
                     h: Vector3::new(s.length / 2.0, s.collar / 2.0, top / 2.0), yaw: 0.0, course: 0 });
    let n = n_courses(s);
    for k in 0..n {
        let z = s.joint + k as f64 * s.course() + hgt / 2.0;
        let offset = if k % 2 == 1 { s.module() / 2.0 } else { 0.0 };
        let coping = k + 1 == n;
        // Positions along the wall (running bond), cut at the ends.
        let mut y = -offset;
        while y < s.length - 20.0 {
            let (a, b) = (y.max(0.0), (y + l).min(s.length));
            if b - a > 40.0 {
                let c = (a + b) / 2.0;
                let hh = Vector3::new((b - a) / 2.0, half.y, half.z);
                if coping {
                    // A coping course across both wythes and the collar joint, plain.
                    out.push(Brick { kind: Kind::Coping, c: Vector3::new(thick / 2.0, c, z), h: Vector3::new(hh.x, thick / 2.0, hh.z), yaw: 0.0, course: k });
                } else {
                    // Full bricks turn; cut ends at the wall's ends stay square.
                    let yaw = if (b - a - l).abs() < 1.0 { s.angle(c, z) } else { 0.0 };
                    out.push(Brick { kind: Kind::Face, c: Vector3::new(x_face, c, z), h: hh, yaw, course: k });
                    out.push(Brick { kind: Kind::Back, c: Vector3::new(x_back, c, z), h: hh, yaw: 0.0, course: k });
                }
            }
            y += s.module();
        }
        // Piers behind the backing wythe: header-bonded blocks of brick, one per course.
        if !coping {
            for py in &piers {
                let (a, b) = ((py - s.pier_w / 2.0).max(0.0), (py + s.pier_w / 2.0).min(s.length));
                out.push(Brick { kind: Kind::Pier, c: Vector3::new(thick + s.pier_d / 2.0, (a + b) / 2.0, z),
                                 h: Vector3::new((b - a) / 2.0, s.pier_d / 2.0, half.z), yaw: 0.0, course: k });
            }
        }
    }
    out
}

fn cross(a: Vector2<f64>, b: Vector2<f64>) -> f64 {
    a.x * b.y - a.y * b.x
}

/// Do two convex polygons overlap (separating axis theorem)?
fn overlap(p: &[Vector2<f64>], q: &[Vector2<f64>]) -> bool {
    for poly in [p, q] {
        for i in 0..poly.len() {
            let e = poly[(i + 1) % poly.len()] - poly[i];
            let n = Vector2::new(-e.y, e.x);
            let (pa, pb) = p.iter().map(|v| v.dot(&n)).fold((f64::MAX, f64::MIN), |(a, b), x| (a.min(x), b.max(x)));
            let (qa, qb) = q.iter().map(|v| v.dot(&n)).fold((f64::MAX, f64::MIN), |(a, b), x| (a.min(x), b.max(x)));
            if pb <= qa + 1e-9 || qb <= pa + 1e-9 {
                return false;
            }
        }
    }
    true
}

fn seg_dist(p: Vector2<f64>, a: Vector2<f64>, b: Vector2<f64>) -> f64 {
    let ab = b - a;
    let t = ((p - a).dot(&ab) / ab.norm_squared()).clamp(0.0, 1.0);
    (a + ab * t - p).norm()
}

/// Least distance between two non-overlapping convex polygons.
fn gap(p: &[Vector2<f64>], q: &[Vector2<f64>]) -> f64 {
    let mut d = f64::MAX;
    for (a, b) in [(p, q), (q, p)] {
        for v in a {
            for i in 0..b.len() {
                d = d.min(seg_dist(*v, b[i], b[(i + 1) % b.len()]));
            }
        }
    }
    d
}

fn area(p: &[Vector2<f64>]) -> f64 {
    (0..p.len()).map(|i| cross(p[i], p[(i + 1) % p.len()])).sum::<f64>().abs() / 2.0
}

/// Sutherland-Hodgman: `subject` clipped by convex `clip` (counter-clockwise).
fn clip(subject: &[Vector2<f64>], clip: &[Vector2<f64>]) -> Vec<Vector2<f64>> {
    let mut out = subject.to_vec();
    let ccw = (0..clip.len()).map(|i| cross(clip[i], clip[(i + 1) % clip.len()])).sum::<f64>() > 0.0;
    for i in 0..clip.len() {
        let (a, b) = (clip[i], clip[(i + 1) % clip.len()]);
        let inside = |p: Vector2<f64>| { let c = cross(b - a, p - a); if ccw { c >= 0.0 } else { c <= 0.0 } };
        let input = std::mem::take(&mut out);
        for j in 0..input.len() {
            let (cur, prev) = (input[j], input[(j + input.len() - 1) % input.len()]);
            let isect = |p: Vector2<f64>, q: Vector2<f64>| {
                let (r, s2) = (q - p, b - a);
                let t = cross(a - p, s2) / cross(r, s2);
                p + r * t
            };
            match (inside(cur), inside(prev)) {
                (true, true) => out.push(cur),
                (true, false) => { out.push(isect(prev, cur)); out.push(cur); }
                (false, true) => out.push(isect(prev, cur)),
                _ => {}
            }
        }
        if out.is_empty() {
            break;
        }
    }
    out
}

pub struct Checks {
    pub face_bricks: usize,
    pub turned: usize,
    pub max_turn_deg: f64,
    pub overlaps: usize,
    pub min_joint: f64,
    pub max_joint: f64,
    pub joints_out_of_range: usize,
    pub min_bearing: f64,
    pub mean_bearing: f64,
    pub max_intrusion: f64,
    pub max_projection: f64,
}

/// The face wythe's joints, bearing and reach, course by course.
pub fn check(bricks: &[Brick], s: &Spec) -> Checks {
    let face: Vec<&Brick> = bricks.iter().filter(|b| b.kind == Kind::Face).collect();
    let n = s.courses();
    let mut by_course: Vec<Vec<&Brick>> = vec![Vec::new(); n];
    for b in &face {
        by_course[b.course].push(b);
    }
    for c in &mut by_course {
        c.sort_by(|a, b| a.c.y.total_cmp(&b.c.y));
    }
    let (mut overlaps, mut min_j, mut max_j, mut out_of_range) = (0, f64::MAX, 0.0f64, 0);
    let (mut min_bear, mut sum_bear, mut n_bear) = (f64::MAX, 0.0, 0usize);
    let (mut intrude, mut project) = (0.0f64, 0.0f64);
    let w = s.unit.y;
    for (k, course) in by_course.iter().enumerate() {
        for pair in course.windows(2) {
            let (p, q) = (pair[0].plan(), pair[1].plan());
            if overlap(&p, &q) {
                overlaps += 1;
                continue;
            }
            let g = gap(&p, &q);
            // Widest point of the joint, on the faces: the distance between the ends' outer and
            // inner corners along the wall.
            let span = |poly: &[Vector2<f64>; 4], end_max: bool| -> (f64, f64) {
                // (y at the outer face x = min, y at the inner face x = max) of the end facing the joint.
                let mut v: Vec<&Vector2<f64>> = poly.iter().collect();
                v.sort_by(|a, b| a.y.total_cmp(&b.y));
                let ends: Vec<&Vector2<f64>> = if end_max { v[2..].to_vec() } else { v[..2].to_vec() };
                let (o, i) = if ends[0].x < ends[1].x { (ends[0], ends[1]) } else { (ends[1], ends[0]) };
                (o.y, i.y)
            };
            let (po, pi) = span(&p, true);
            let (qo, qi) = span(&q, false);
            let widest = (qo - po).max(qi - pi);
            min_j = min_j.min(g);
            max_j = max_j.max(widest);
            if g < s.min_joint || widest > s.max_joint {
                out_of_range += 1;
            }
        }
        for b in course {
            let poly = b.plan();
            for v in &poly {
                project = project.max(-v.x);
                intrude = intrude.max(v.x - w);
            }
            if k == 0 || b.kind != Kind::Face {
                continue;
            }
            // Bearing on the course below: the overlap of footprints over the brick's own area.
            let below = &by_course[k - 1];
            let i0 = below.partition_point(|o| o.c.y < b.c.y - 2.0 * s.unit.x);
            let mut a = 0.0;
            for o in below[i0..].iter().take_while(|o| o.c.y < b.c.y + 2.0 * s.unit.x) {
                let cp = clip(&poly, &o.plan());
                if cp.len() >= 3 {
                    a += area(&cp);
                }
            }
            let share = a / area(&poly);
            min_bear = min_bear.min(share);
            sum_bear += share;
            n_bear += 1;
        }
    }
    Checks {
        face_bricks: face.len(),
        turned: face.iter().filter(|b| b.yaw.abs() > 1e-6).count(),
        max_turn_deg: face.iter().map(|b| b.yaw.abs().to_degrees()).fold(0.0, f64::max),
        overlaps, min_joint: min_j, max_joint: max_j, joints_out_of_range: out_of_range,
        min_bearing: min_bear, mean_bearing: sum_bear / n_bear.max(1) as f64,
        max_intrusion: intrude, max_projection: project,
    }
}

/// Count and volume by kind.
pub fn quantities(bricks: &[Brick]) -> Value {
    let mut v = json!({});
    for (kind, name) in [(Kind::Face, "face"), (Kind::Back, "back"), (Kind::Pier, "pier"), (Kind::Coping, "coping"), (Kind::Footing, "footing")] {
        let sel: Vec<&Brick> = bricks.iter().filter(|b| b.kind == kind).collect();
        v[name] = json!({"pieces": sel.len(), "m3": sel.iter().map(|b| b.volume_m3()).sum::<f64>()});
    }
    v
}

pub fn draw(bricks: &[Brick], path: &Path, views: &[View], px_per_mm: f64, style: Style) -> std::io::Result<()> {
    let colours = [[0.70, 0.36, 0.26], [0.62, 0.33, 0.25], [0.58, 0.31, 0.24], [0.55, 0.53, 0.50], [0.66, 0.66, 0.64], [0.72, 0.70, 0.66]];
    let mut meshes: Vec<IndexedMesh> = (0..6).map(|_| IndexedMesh::new()).collect();
    for b in bricks {
        let i = match b.kind { Kind::Face => 0, Kind::Back => 1, Kind::Pier => 2, Kind::Coping => 3, Kind::Footing => 4, Kind::Mortar => 5 };
        b.append_mesh(&mut meshes[i]);
    }
    let layers: Vec<Layer> = meshes.iter().zip(colours).filter(|(m, _)| !m.vertices.is_empty()).map(|(m, c)| Layer::solid(m, c)).collect();
    render::render_styled(&layers, views, px_per_mm, path, style)?;
    Ok(())
}

/// The gantry as boxes (mm): rails both sides of `len` mm of wall, two legs at `y`, a bridge
/// across at `z`, the trolley under it and the mast down to `z_work` over the face wythe.
fn gantry(s: &Spec, len: f64, y: f64, z: f64, z_work: f64) -> Vec<Brick> {
    let thick = 2.0 * s.unit.y + s.collar + s.pier_d;
    let (x0, x1) = (-1200.0, thick + 1200.0);
    let b = |c: Vector3<f64>, h: Vector3<f64>| Brick { kind: Kind::Footing, c, h, yaw: 0.0, course: 0 };
    let mut v = Vec::new();
    for x in [x0, x1] {
        v.push(b(Vector3::new(x, len / 2.0, 60.0), Vector3::new(len / 2.0 + 400.0, 60.0, 60.0))); // rail
        v.push(b(Vector3::new(x, y, (z + 120.0) / 2.0), Vector3::new(80.0, 80.0, (z - 120.0) / 2.0 + 60.0))); // leg
    }
    v.push(b(Vector3::new((x0 + x1) / 2.0, y, z + 60.0), Vector3::new(140.0, (x1 - x0) / 2.0 + 80.0, 90.0))); // bridge
    v.push(b(Vector3::new(s.unit.y / 2.0, y, z - 150.0), Vector3::new(120.0, 160.0, 120.0))); // trolley
    let top = z - 270.0;
    v.push(b(Vector3::new(s.unit.y / 2.0, y, (top + z_work) / 2.0), Vector3::new(40.0, 40.0, ((top - z_work) / 2.0).max(20.0)))); // mast
    v
}

/// The build in frames: `every` courses at a time over the first `len` mm of wall, the gantry at
/// the working course; frames to `dir` for `brownfield wall` to make the GIF.
fn frames(s: &Spec, bricks: &[Brick], len: f64, every: usize, dir: &Path) -> std::io::Result<usize> {
    let _ = std::fs::remove_dir_all(dir);
    std::fs::create_dir_all(dir)?;
    let part: Vec<&Brick> = bricks.iter().filter(|b| b.kind != Kind::Mortar && b.c.y < len).collect();
    let n = s.courses();
    let view = [View::looking(Vector3::new(0.62, 0.62, -0.42), Vector3::z())];
    let style = Style { smooth: false, outline: true, ssaa: 2, key: None };
    let mut k = 0;
    let mut i = 0;
    while k <= n {
        let upto = k.min(n);
        let mut shown: Vec<Brick> = part.iter().filter(|b| b.kind == Kind::Footing || b.course < upto).map(|b| {
            let mut b = (*b).clone();
            if b.kind == Kind::Footing { b.c.y = len / 2.0; b.h.x = len / 2.0 + 150.0; }
            b
        }).collect();
        let z_work = s.joint + upto as f64 * s.course() + 300.0;
        let y_work = if upto == n { len + 900.0 } else { 0.15 * len + (i as f64 * 0.37 * len) % (0.7 * len) };
        shown.extend(gantry(s, len, y_work, s.height + 900.0, z_work));
        draw(&shown, &dir.join(format!("f{i:03}.png")), &view, 0.05, style)?;
        i += 1;
        if k == n { break; }
        k = (k + every).min(n);
    }
    Ok(i)
}

pub fn run(root: &Path) -> std::io::Result<()> {
    let t0 = std::time::Instant::now();
    let spec_path = root.join("out/pass2/wall.json");
    let s = match std::fs::read_to_string(&spec_path) {
        Ok(t) => Spec::from_json(&serde_json::from_str(&t).expect("wall.json parses")),
        Err(_) => Spec::provisional(),
    };
    let bricks = build(&s);
    let c = check(&bricks, &s);
    let q = quantities(&bricks);
    let area_m2 = s.length * s.courses() as f64 * s.course() / 1e6;
    let face_per_m2 = c.face_bricks as f64 / area_m2;
    println!("wall: {} m long x {} courses ({:.2} m), spec: {}", s.length / 1e3, s.courses(), s.courses() as f64 * s.course() / 1e3, s.source);
    println!("  {} face bricks ({:.1} per m2), {} turned, up to {:.1} deg; overlaps {}; head joints {:.1}-{:.1} mm ({} outside {}-{} mm)",
             c.face_bricks, face_per_m2, c.turned, c.max_turn_deg, c.overlaps, c.min_joint, c.max_joint, c.joints_out_of_range, s.min_joint, s.max_joint);
    println!("  bed bearing on the course below: min {:.0}%, mean {:.0}%; corners reach {:.1} mm into the collar joint ({:.1} mm wide), {:.1} mm proud of the face",
             100.0 * c.min_bearing, 100.0 * c.mean_bearing, c.max_intrusion, s.collar, c.max_projection);
    println!("  pieces: {q}");
    let out = root.join("out/pass2");
    std::fs::create_dir_all(&out)?;
    std::fs::write(out.join("wall_forge.json"), serde_json::to_string_pretty(&json!({
        "source": "forge `wall` (CortenForge 0.9): the wall built brick by brick",
        "spec": s.source, "length_m": s.length / 1e3, "courses": s.courses(), "height_m": s.courses() as f64 * s.course() / 1e3,
        "face_bricks_per_m2": face_per_m2, "quantities": q,
        "checks": {"face_bricks": c.face_bricks, "turned": c.turned, "max_turn_deg": c.max_turn_deg, "overlaps": c.overlaps,
                   "min_joint_mm": c.min_joint, "max_joint_mm": c.max_joint, "joints_out_of_range": c.joints_out_of_range,
                   "min_bearing": c.min_bearing, "mean_bearing": c.mean_bearing, "max_intrusion_mm": c.max_intrusion,
                   "max_projection_mm": c.max_projection},
    }))?)?;
    let docs = root.join("docs/pass2");
    std::fs::create_dir_all(&docs)?;
    // The face from the homes' side, in a raking light from the left.
    let face_only: Vec<Brick> = bricks.iter().filter(|b| matches!(b.kind, Kind::Face | Kind::Coping | Kind::Mortar)).cloned().collect();
    let style = Style { smooth: false, outline: false, ssaa: 2, key: Some(Vector3::new(-0.85, 0.25, 0.45)) };
    draw(&face_only, &docs.join("wall_face.png"), &[View::looking(Vector3::x(), Vector3::z())], 0.075, style)?;
    // A bay end-on and from above the yard side: wythes, collar joint, pier.
    let bay: Vec<Brick> = bricks.iter().filter(|b| b.kind != Kind::Mortar && b.c.y < s.pier_spacing.max(3000.0) + 500.0).cloned().collect();
    draw(&bay, &docs.join("wall_bay.png"), &[View::looking(Vector3::new(-0.45, 0.8, -0.4), Vector3::z())], 0.12,
         Style { smooth: false, outline: true, ssaa: 2, key: None })?;
    println!("drawn: docs/pass2/wall_face.png, wall_bay.png ({:.1} s)", t0.elapsed().as_secs_f64());

    // The robot lays the same stretch twice: with the pattern, and plain.
    let lim = crate::wall_robot::Limits::provisional();
    let (y0, bay, k0, nk) = (s.pier_spacing.max(3000.0) + 300.0, s.pier_spacing.max(3000.0) - 600.0, 58, 6);
    let t1 = std::time::Instant::now();
    let robot = crate::wall_robot::run_bay(&s, &bricks, y0, bay, k0, nk, &lim);
    let mut plain = s.clone();
    plain.amp_deg = 0.0;
    let robot_plain = crate::wall_robot::run_bay(&plain, &build(&plain), y0, bay, k0, nk, &lim);
    for (name, r) in [("patterned", &robot), ("plain", &robot_plain)] {
        println!("  robot, {name}: {} bricks; motion {:.2} s a brick (max {:.2}); placed within {:.2} mm in plan (mean {:.2}), {:.2} deg, settled {:.2} mm into the bed; grip tracking {:.2} mm",
                 r["bricks"], r["motion_s_mean"].as_f64().unwrap_or(0.0), r["motion_s_max"].as_f64().unwrap_or(0.0),
                 r["err_plan_mm_max"].as_f64().unwrap_or(0.0), r["err_plan_mm_mean"].as_f64().unwrap_or(0.0), r["err_deg_max"].as_f64().unwrap_or(0.0),
                 -r["err_z_mm_mean"].as_f64().unwrap_or(0.0), r["track_mm_max"].as_f64().unwrap_or(0.0));
    }
    println!("  ({:.1} s)", t1.elapsed().as_secs_f64());
    let nf = frames(&s, &bricks, 2.0 * s.pier_spacing.max(4000.0), 6, &out.join("wall_frames"))?;
    println!("  {nf} frames of the build in out/pass2/wall_frames");
    let path = out.join("wall_forge.json");
    let mut v: Value = serde_json::from_str(&std::fs::read_to_string(&path)?).expect("wall_forge.json");
    v["robot"] = json!({"limits": {"v_m_s": lim.v, "a_m_s2": lim.a, "w_rad_s": lim.w, "alpha_rad_s2": lim.alpha, "lift_m": lim.lift,
                                   "release_m": lim.release, "dwell_s": lim.dwell, "settle_s": lim.settle},
                        "stretch": {"y0_mm": y0, "length_mm": bay, "first_course": k0, "courses": nk},
                        "patterned": robot, "plain": robot_plain});
    std::fs::write(&path, serde_json::to_string_pretty(&v)?)?;
    Ok(())
}
