//! The walk-up's wood frame, member by member (pass 3b, step 3), from the sizes
//! `brownfield frame` chose (`../out/pass3/frame.json`).
//!
//! Platform framing: on the slab and its perimeter stem walls, each storey's walls (bottom plate,
//! studs, double top plate; king and jack studs, a header and cripples at every opening; a rough
//! sill under windows), then the floor above (rim boards on the facades, joists 16 in. apart from
//! each facade to the spine), and the next storey on that. The joists span front to back, so the
//! facades and the spine (two rows of studs, a double-stud party wall) bear the floors; the end
//! walls and the stair walls don't, except that the roof over the stair spans between the stair
//! walls. Not framed: sheathing and subfloor panels, the stair, the walls inside the flats.
//!
//! Same frame as `apartment.rs` (mm; x across the depth from the front facade, y along the length,
//! z up from the top of the slab). Every member is a box (an I-joist is three); `Member::solid`
//! gives CortenForge's solid for measuring, `Member::mesh` the exact 12-triangle boxes
//! (cortenforge::mesh::types::unit_cube) for drawing.

use cortenforge::cf_design::Solid;
use cortenforge::mesh::types::{IndexedMesh, unit_cube};
use nalgebra::{Point3, Vector3};
use serde_json::Value;

use crate::apartment::{Building, Face, Opening};

const IN: f64 = 25.4;
const GYP: f64 = 0.625 * IN; // the gypsum lining inside the studs
const RO: f64 = 0.5 * IN; // rough opening play each side

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Kind {
    Stud,
    King,
    Jack,
    Cripple,
    Plate,
    CapPlate,
    Sill,
    Header,
    Rim,
    FloorJoist,
    RoofJoist,
    Footing,
    Stem,
    Slab,
    Block,
    Lintel,
    Plank,
}

impl Kind {
    pub fn name(self) -> &'static str {
        match self {
            Kind::Stud => "studs",
            Kind::King => "king studs",
            Kind::Jack => "jack studs",
            Kind::Cripple => "cripples",
            Kind::Plate => "plates",
            Kind::CapPlate => "cap plates",
            Kind::Sill => "rough sills",
            Kind::Header => "headers (plies)",
            Kind::Rim => "rim boards",
            Kind::FloorJoist => "floor joists",
            Kind::RoofJoist => "roof joists",
            Kind::Footing => "footings",
            Kind::Stem => "stem walls",
            Kind::Slab => "slab",
            Kind::Block => "blocks",
            Kind::Lintel => "lintels",
            Kind::Plank => "planks",
        }
    }
    pub fn concrete(self) -> bool {
        matches!(self, Kind::Footing | Kind::Stem | Kind::Slab)
    }
}

#[derive(Clone, Debug)]
pub struct Member {
    pub kind: Kind,
    /// 0 for the foundation, 1-3 for a storey's walls, 1-3 also for the floor or roof framing on top
    /// of that storey.
    pub storey: usize,
    /// Nominal size for board feet ("2x6"), or None (I-joists, rim, concrete).
    pub nominal: Option<String>,
    pub boxes: Vec<(Vector3<f64>, Vector3<f64>)>,
    /// The wall panel it was framed in, if any (`Panel::id`); for masonry pieces, the course they
    /// are laid in (the build's order).
    pub panel: Option<usize>,
}

impl Member {
    fn one(kind: Kind, storey: usize, nominal: Option<&str>, lo: Vector3<f64>, hi: Vector3<f64>) -> Self {
        Member { kind, storey, nominal: nominal.map(String::from), boxes: vec![(lo, hi)], panel: None }
    }
    pub fn volume_m3(&self) -> f64 {
        self.boxes.iter().map(|(lo, hi)| (hi - lo).product()).sum::<f64>() / 1e9
    }
    /// Its longest dimension (m).
    pub fn length_m(&self) -> f64 {
        let (lo, hi) = self.bounds();
        (hi - lo).max() / 1e3
    }
    pub fn bounds(&self) -> (Vector3<f64>, Vector3<f64>) {
        let mut lo = Vector3::repeat(f64::INFINITY);
        let mut hi = Vector3::repeat(f64::NEG_INFINITY);
        for (a, b) in &self.boxes {
            lo = lo.inf(a);
            hi = hi.sup(b);
        }
        (lo, hi)
    }
    /// Board feet by nominal size (a 2x6 is one board foot a foot).
    pub fn board_feet(&self) -> f64 {
        let Some(n) = &self.nominal else { return 0.0 };
        let (t, w) = n.split_once('x').map(|(a, b)| (a.parse::<f64>().unwrap_or(0.0), b.parse::<f64>().unwrap_or(0.0))).unwrap_or((0.0, 0.0));
        t * w / 12.0 * self.length_m() / 0.3048
    }
    /// Mass density to give each of its boxes (kg/m3): from the member's weight per metre where the
    /// schedule has one (steel, whose boxes are the sections' outlines), otherwise `wood`.
    pub fn density(&self, linear_kg_m: &std::collections::HashMap<String, f64>, wood: f64) -> f64 {
        let Some(kgm) = self.nominal.as_ref().and_then(|n| linear_kg_m.get(n)) else { return wood };
        let (lo, hi) = self.bounds();
        let mut d = [(hi - lo).x, (hi - lo).y, (hi - lo).z];
        d.sort_by(f64::total_cmp);
        kgm / (d[0] * d[1] / 1e6)
    }
    /// CortenForge's solid of the member (boxes unioned).
    pub fn solid(&self) -> Solid {
        self.boxes.iter().map(|(lo, hi)| Solid::cuboid((hi - lo) / 2.0).translate((hi + lo) / 2.0))
            .reduce(|a, b| a.union(b)).expect("a member has a box")
    }
    /// Exact triangles: CortenForge's unit cube, scaled and moved onto each box.
    pub fn append_mesh(&self, out: &mut IndexedMesh) {
        let cube = unit_cube();
        for (lo, hi) in &self.boxes {
            let base = out.vertices.len() as u32;
            let d = hi - lo;
            out.vertices.extend(cube.vertices.iter().map(|v| Point3::new(lo.x + v.x * d.x, lo.y + v.y * d.y, lo.z + v.z * d.z)));
            out.faces.extend(cube.faces.iter().map(|f| [f[0] + base, f[1] + base, f[2] + base]));
        }
    }
    /// The same, turned by `rot` about `pivot` (a wall panel part-way up) and then moved by `shift`.
    pub fn append_mesh_moved(&self, out: &mut IndexedMesh, rot: &nalgebra::UnitQuaternion<f64>, pivot: &Vector3<f64>, shift: &Vector3<f64>) {
        let start = out.vertices.len();
        self.append_mesh(out);
        for v in &mut out.vertices[start..] {
            let r = rot * (v.coords - pivot) + pivot + shift;
            *v = Point3::from(r);
        }
    }
}

/// Colours by drawing layer (concrete, wall framing, headers, rims, joists) for a system.
pub fn palette(system: &str) -> [[f64; 3]; 5] {
    if system == "steel" {
        [[0.66, 0.66, 0.64], [0.74, 0.77, 0.80], [0.52, 0.56, 0.62], [0.50, 0.53, 0.58], [0.84, 0.86, 0.89]]
    } else {
        [[0.66, 0.66, 0.64], [0.84, 0.70, 0.50], [0.62, 0.42, 0.26], [0.55, 0.45, 0.35], [0.92, 0.82, 0.62]]
    }
}

/// Which wall lines a panel belongs to, in the order a crew raises them.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Group {
    Facade,
    EndWall,
    Spine,
    Stair,
}

impl Group {
    pub fn name(self) -> &'static str {
        match self {
            Group::Facade => "facades",
            Group::EndWall => "end walls",
            Group::Spine => "spine rows",
            Group::Stair => "stair walls",
        }
    }
}

/// A wall panel framed flat on the deck and tilted up: it turns about `axis` through `pivot`
/// (its bottom edge on the side it lies on), from flat (+90 degrees) to its place (0).
#[derive(Clone, Debug)]
pub struct Panel {
    pub id: usize,
    pub storey: usize,
    pub group: Group,
    pub pivot: Vector3<f64>,
    pub axis: Vector3<f64>,
    pub length_mm: f64,
    /// Sheathing on its outer face (facades and end walls), the box it would occupy (mm).
    pub sheathing: Option<(Vector3<f64>, Vector3<f64>)>,
}

/// What `brownfield frame` chose, read back.
pub struct Schedule {
    pub spacing: f64,
    pub stud_len: f64,
    pub subfloor: f64,
    pub floor_joist: Joist,
    pub roof_joist: Joist,
    pub studs: Vec<(String, f64, String, f64)>, // per storey: exterior size, spacing; spine row size, spacing
    pub headers: Vec<(usize, f64, usize, String, usize)>, // storey, opening m, plies, size, jacks
    pub sizes: std::collections::HashMap<String, (f64, f64)>,
    pub facade_footing: f64,
    pub spine_footing: f64,
    pub footing_t: f64,
    /// Longest wall panel a crew frames and raises (mm).
    pub panel_max: f64,
    /// "wood" or "steel".
    pub system: String,
    /// A stud's width along the wall, a plate's (or track's) thickness, the rim's thickness (mm).
    pub ply: f64,
    pub plate: f64,
    pub rim: f64,
    /// A second top plate lapping the panels (wood); steel has a single top track.
    pub cap: bool,
    /// The track that goes with each stud (steel), the rim's name, and weights per metre (kg/m) by
    /// member name where they are known (steel); wood members weigh by their volume.
    pub track_for: std::collections::HashMap<String, String>,
    pub rim_name: Option<String>,
    pub linear_kg_m: std::collections::HashMap<String, f64>,
    pub stair_stud: String,
}

pub struct Joist {
    pub ijoist: bool,
    pub name: String,
    pub width: f64,
    pub depth: f64,
    pub flange: f64,
    pub web: f64,
    pub nominal: Option<String>,
}

fn f(v: &Value, k: &str) -> f64 {
    v[k].as_f64().unwrap_or_else(|| panic!("frame.json: no number {k}"))
}

impl Schedule {
    pub fn from_json(v: &Value) -> Self {
        let joist = |j: &Value| {
            let ijoist = j["kind"] == "ijoist";
            let name = j["name"].as_str().unwrap_or("").to_string();
            Joist {
                ijoist, width: f(j, "width_mm"), depth: f(j, "depth_mm"),
                flange: j["flange_mm"].as_f64().unwrap_or(0.0), web: j["web_mm"].as_f64().unwrap_or(0.0),
                nominal: if ijoist { None } else { name.split_whitespace().last().map(String::from) },
                name,
            }
        };
        let studs = (1..=3).map(|k| {
            let s = &v["studs"][k.to_string()];
            (s["exterior"]["size"].as_str().unwrap_or("2x6").to_string(), f(&s["exterior"], "spacing_mm"),
             s["spine_row"]["size"].as_str().unwrap_or("2x4").to_string(), f(&s["spine_row"], "spacing_mm"))
        }).collect();
        let headers = v["headers"].as_array().into_iter().flatten().map(|h| {
            (h["storey"].as_u64().unwrap_or(1) as usize, f(h, "opening_m"), h["plies"].as_u64().unwrap_or(2) as usize,
             h["size"].as_str().unwrap_or("2x6").to_string(), h["jacks"].as_u64().unwrap_or(1) as usize)
        }).collect();
        let sizes = v["sizes_mm"].as_object().into_iter().flatten()
            .map(|(k, a)| (k.clone(), (a[0].as_f64().unwrap_or(0.0), a[1].as_f64().unwrap_or(0.0)))).collect();
        Schedule {
            spacing: f(v, "spacing_mm"), stud_len: f(v, "stud_length_mm"), subfloor: f(v, "subfloor_mm"),
            floor_joist: joist(&v["floor_joist"]), roof_joist: joist(&v["roof_joist"]), studs, headers, sizes,
            facade_footing: f(&v["footings"], "facade_width_mm"), spine_footing: f(&v["footings"], "spine_width_mm"),
            footing_t: f(&v["footings"], "thickness_mm"),
            panel_max: v["build"]["panel_max_mm"].as_f64().unwrap_or(16.0 * 12.0 * IN),
            system: v["dims"]["system"].as_str().unwrap_or("wood").to_string(),
            ply: v["dims"]["ply_mm"].as_f64().unwrap_or(1.5 * IN),
            plate: v["dims"]["plate_mm"].as_f64().unwrap_or(1.5 * IN),
            rim: v["dims"]["rim_mm"].as_f64().unwrap_or(1.125 * IN),
            cap: v["dims"]["cap"].as_bool().unwrap_or(true),
            track_for: v["track_for"].as_object().into_iter().flatten().map(|(k, x)| (k.clone(), x.as_str().unwrap_or("").to_string())).collect(),
            rim_name: v["rim_name"].as_str().map(String::from),
            linear_kg_m: v["linear_kg_m"].as_object().into_iter().flatten().map(|(k, x)| (k.clone(), x.as_f64().unwrap_or(0.0))).collect(),
            stair_stud: v["stair_stud"].as_str().unwrap_or("2x4").to_string(),
        }
    }
    fn depth_of(&self, size: &str) -> f64 {
        self.sizes[size].1
    }
    fn header_for(&self, storey: usize, width_m: f64) -> (usize, String, usize) {
        let at: Vec<_> = self.headers.iter().filter(|h| h.0 == storey).collect();
        let h = at.iter().find(|h| (h.1 - width_m).abs() < 0.01)
            .or_else(|| at.iter().max_by(|a, b| a.1.total_cmp(&b.1))).expect("headers for every storey");
        (h.2, h.3.clone(), h.4)
    }
}

/// A wall line: studs `depth` deep between `c0` and `c0 + depth` across the wall, running `a0..a1`
/// along it; `along_y` when the wall runs along y (the facades and the spine rows).
struct Line<'a> {
    along_y: bool,
    c0: f64,
    depth: f64,
    a0: f64,
    a1: f64,
    nominal: &'a str,
    spacing: f64,
    openings: Vec<&'a Opening>,
}

impl Line<'_> {
    fn bx(&self, a0: f64, a1: f64, c0: f64, c1: f64, z0: f64, z1: f64) -> (Vector3<f64>, Vector3<f64>) {
        if self.along_y {
            (Vector3::new(c0, a0, z0), Vector3::new(c1, a1, z1))
        } else {
            (Vector3::new(a0, c0, z0), Vector3::new(a1, c1, z1))
        }
    }
}

fn wall(line: &Line, s: &Schedule, storey: usize, zb: f64, panel: Option<usize>, out: &mut Vec<Member>) {
    wall_h(line, s, storey, zb, s.stud_len, panel, out);
}

/// `wall` with its own stud length (the annex's walls are a storey of their own height).
#[allow(clippy::too_many_arguments)]
fn wall_h(line: &Line, s: &Schedule, storey: usize, zb: f64, stud_len: f64, panel: Option<usize>, out: &mut Vec<Member>) {
    let (c0, c1) = (line.c0, line.c0 + line.depth);
    let nom = Some(line.nominal);
    let (ply, plate) = (s.ply, s.plate);
    let track = Some(s.track_for.get(line.nominal).map(String::as_str).unwrap_or(line.nominal));
    let push = |out: &mut Vec<Member>, kind, nominal: Option<&str>, b: (Vector3<f64>, Vector3<f64>)| {
        let mut m = Member::one(kind, storey, nominal, b.0, b.1);
        m.panel = panel;
        out.push(m);
    };
    let stud0 = zb + plate;
    let stud1 = stud0 + stud_len;
    // Openings: rough opening, then jacks and kings either side, the header on the jacks.
    struct Hole { ro0: f64, ro1: f64, out0: f64, out1: f64, bottom: f64, top: f64, door: bool }
    let mut holes = Vec::new();
    for o in &line.openings {
        let (ro0, ro1) = (o.along - o.width / 2.0 - RO, o.along + o.width / 2.0 + RO);
        let door = (o.sill - zb).abs() < 1.0;
        let (bottom, top) = (if door { stud0 } else { o.sill - RO }, o.sill + o.height + RO);
        let (plies, hsize, jacks) = s.header_for(storey, o.width / 1e3);
        let hdepth = s.depth_of(&hsize);
        let j = jacks as f64 * ply;
        for side in [-1.0, 1.0] {
            let edge = if side < 0.0 { ro0 } else { ro1 };
            for k in 0..jacks {
                let (a0, a1) = if side < 0.0 { (edge - (k + 1) as f64 * ply, edge - k as f64 * ply) } else { (edge + k as f64 * ply, edge + (k + 1) as f64 * ply) };
                push(out, Kind::Jack, nom, line.bx(a0, a1, c0, c1, stud0, top));
            }
            let (a0, a1) = if side < 0.0 { (edge - j - ply, edge - j) } else { (edge + j, edge + j + ply) };
            push(out, Kind::King, nom, line.bx(a0, a1, c0, c1, stud0, stud1));
        }
        // The header: plies side by side across the wall, centred, over the jacks.
        let hw = plies as f64 * ply;
        let cm = (c0 + c1) / 2.0;
        for k in 0..plies {
            let cc = cm - hw / 2.0 + k as f64 * ply;
            push(out, Kind::Header, Some(hsize.as_str()), line.bx(ro0 - j, ro1 + j, cc, cc + ply, top, (top + hdepth).min(stud1)));
        }
        if !door {
            push(out, Kind::Sill, track, line.bx(ro0, ro1, c0, c1, bottom - plate, bottom));
        }
        holes.push(Hole { ro0, ro1, out0: ro0 - j - ply, out1: ro1 + j + ply, bottom: bottom - if door { 0.0 } else { plate }, top: (top + hdepth).min(stud1), door });
    }
    // Plates: the bottom plate stops at door openings.
    let mut cuts: Vec<(f64, f64)> = holes.iter().filter(|h| h.door).map(|h| (h.ro0, h.ro1)).collect();
    cuts.sort_by(|a, b| a.0.total_cmp(&b.0));
    let mut a = line.a0;
    for (x0, x1) in cuts.iter().chain(std::iter::once(&(line.a1, line.a1))) {
        if *x0 - a > 1.0 {
            push(out, Kind::Plate, track, line.bx(a, *x0, c0, c1, zb, zb + plate));
        }
        a = *x1;
    }
    // The first top plate; the cap plate goes on after the panels are up, lapping their joints.
    push(out, Kind::Plate, track, line.bx(line.a0, line.a1, c0, c1, stud1, stud1 + plate));
    // Studs on the layout, full height away from openings, cripples above headers and below sills.
    let mut positions = vec![line.a0];
    let mut p = line.a0 + line.spacing;
    while p + ply / 2.0 < line.a1 - ply {
        positions.push(p - ply / 2.0);
        p += line.spacing;
    }
    positions.push(line.a1 - ply);
    for p0 in positions {
        let p1 = p0 + ply;
        match holes.iter().find(|h| p1 > h.out0 && p0 < h.out1) {
            None => push(out, Kind::Stud, nom, line.bx(p0, p1, c0, c1, stud0, stud1)),
            Some(h) => {
                if p0 >= h.ro0 && p1 <= h.ro1 {
                    if stud1 - h.top > 1.0 {
                        push(out, Kind::Cripple, nom, line.bx(p0, p1, c0, c1, h.top, stud1));
                    }
                    if !h.door && h.bottom - stud0 > 1.0 {
                        push(out, Kind::Cripple, nom, line.bx(p0, p1, c0, c1, stud0, h.bottom));
                    }
                }
            }
        }
    }
}

/// Joists `width` wide between `y0` and `y1` (the first and last flush with the ends), spanning
/// x from `x0` to `x1` at height z0.
fn joists(j: &Joist, kind: Kind, storey: usize, spacing: f64, y0: f64, y1: f64, x0: f64, x1: f64, z0: f64, out: &mut Vec<Member>) {
    let mut ys = vec![y0];
    let mut c = y0 + spacing;
    while c + j.width / 2.0 < y1 - j.width {
        ys.push(c - j.width / 2.0);
        c += spacing;
    }
    ys.push(y1 - j.width);
    for y in ys {
        out.push(joist_member(j, kind, storey, Vector3::new(x0, y, z0), Vector3::new(x1, y + j.width, z0 + j.depth), true));
    }
}

/// One joist in the box lo..hi; `along_x` when its length runs along x.
fn joist_member(j: &Joist, kind: Kind, storey: usize, lo: Vector3<f64>, hi: Vector3<f64>, along_x: bool) -> Member {
    if !j.ijoist {
        return Member::one(kind, storey, j.nominal.as_deref(), lo, hi);
    }
    // Flanges top and bottom, the web centred between them.
    let (w0, w1) = if along_x { (lo.y, hi.y) } else { (lo.x, hi.x) };
    let mid = (w0 + w1) / 2.0;
    let web = |a: f64, b: f64| if along_x {
        (Vector3::new(lo.x, a, lo.z + j.flange), Vector3::new(hi.x, b, hi.z - j.flange))
    } else {
        (Vector3::new(a, lo.y, lo.z + j.flange), Vector3::new(b, hi.y, hi.z - j.flange))
    };
    Member {
        kind, storey, nominal: None, panel: None,
        boxes: vec![
            (lo, Vector3::new(hi.x, hi.y, lo.z + j.flange)),
            (Vector3::new(lo.x, lo.y, hi.z - j.flange), hi),
            web(mid - j.web / 2.0, mid + j.web / 2.0),
        ],
    }
}

/// Where a wall line is cut into panels: at most `max` long, each cut where it clears every
/// opening's rough opening, jack and king studs and the panel's own end stud (every panel gets
/// its own end studs, so the joint is a double stud). Crews cut walls wherever there's room, so
/// the cut needn't fall on the stud layout.
fn panel_bounds(line: &Line, max: f64, ply: f64) -> Vec<f64> {
    let need = RO + 4.0 * ply + 10.0; // play, up to two jacks and a king, the end stud, a little slack
    let clear = |x: f64| line.openings.iter().all(|o| (x - o.along).abs() > o.width / 2.0 + need);
    let mut b = vec![line.a0];
    let mut cur = line.a0;
    while line.a1 - cur > max {
        let mut cut = None;
        let mut x = cur + max;
        while x > cur + 2.0 * line.spacing {
            if clear(x) { cut = Some(x); break; }
            x -= 10.0;
        }
        let Some(x) = cut else { break };
        // Don't leave a sliver at the end.
        if line.a1 - x < 0.25 * max { break; }
        b.push(x);
        cur = x;
    }
    b.push(line.a1);
    b
}

pub fn build(b: &Building, s: &Schedule) -> (Vec<Member>, Vec<Panel>) {
    let mut out = Vec::new();
    let mut panels: Vec<Panel> = Vec::new();
    let (w, l, t, p) = (b.depth, b.length, b.ext_t, b.party_t);
    let (s0, s1) = (b.flat_len, l - b.flat_len);
    let ext_d = s.depth_of(&s.studs[0].0);
    let xf = t - GYP - ext_d; // the facade studs' outer face, front
    let xb = w - xf; // back
    let yl = t - GYP - ext_d; // the end walls' outer face, left
    let yr = l - yl;
    let cx = w / 2.0;

    // Foundation: perimeter footings and stem walls (frost depth 36 in. below grade, grade 8 in. below
    // the slab), a thickened footing under the spine, the slab inside the stems.
    let (grade, frost, stem_t) = (-8.0 * IN, 36.0 * IN, 8.0 * IN);
    let (fb, ft) = (grade - frost, grade - frost + s.footing_t);
    let fw = s.facade_footing;
    let foot = |out: &mut Vec<Member>, kind, lo, hi| out.push(Member::one(kind, 0, None, lo, hi));
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
    let slab_t = 4.0 * IN;
    let sw = s.spine_footing;
    for (y0, y1) in [(stem_t, s0 + p / 2.0), (s1 - p / 2.0, l - stem_t)] {
        foot(&mut out, Kind::Footing, Vector3::new(cx - sw / 2.0, y0, -slab_t - 12.0 * IN), Vector3::new(cx + sw / 2.0, y1, -slab_t));
    }
    foot(&mut out, Kind::Slab, Vector3::new(stem_t, stem_t, -slab_t), Vector3::new(w - stem_t, l - stem_t, 0.0));

    for storey in 1..=b.storeys {
        let zb = (storey - 1) as f64 * b.storey;
        let (ext_size, ext_sp, spine_size, spine_sp) = s.studs[storey - 1].clone();
        let at = |face: Face| -> Vec<&Opening> {
            b.openings.iter().filter(|o| o.face == face && o.sill >= zb - 1.0 && o.sill < zb + b.storey - 1.0).collect()
        };
        let ext = |along_y, c0, a0, a1, face| Line { along_y, c0, depth: ext_d, a0, a1, nominal: ext_size.as_str(), spacing: ext_sp, openings: at(face) };
        let sd = s.depth_of(&spine_size);
        let stair_row = s.depth_of(&s.stair_stud);
        // Every wall line, with the way its panels lie on the deck before they go up (`inward`,
        // a unit vector across the wall) and whether it is sheathed before raising. Facades run
        // the full length, the end walls fit between them; the spine is two rows 1 in. apart from
        // the end walls to the stair walls; the stair walls two rows of 2x4 each, facade to facade.
        let mut lines: Vec<(Group, Line, Vector3<f64>, bool)> = vec![
            (Group::Facade, ext(true, xf, yl, yr, Face::Front), Vector3::x(), true),
            (Group::Facade, ext(true, xb - ext_d, yl, yr, Face::Back), -Vector3::x(), true),
            (Group::EndWall, ext(false, yl, xf + ext_d, xb - ext_d, Face::Left), Vector3::y(), true),
            (Group::EndWall, ext(false, yr - ext_d, xf + ext_d, xb - ext_d, Face::Right), -Vector3::y(), true),
        ];
        for (c0, inward, (a0, a1)) in [(cx - 0.5 * IN - sd, -Vector3::x(), (yl + ext_d, s0 - 0.5 * IN - stair_row)),
                                       (cx + 0.5 * IN, Vector3::x(), (yl + ext_d, s0 - 0.5 * IN - stair_row)),
                                       (cx - 0.5 * IN - sd, -Vector3::x(), (s1 + 0.5 * IN + stair_row, yr - ext_d)),
                                       (cx + 0.5 * IN, Vector3::x(), (s1 + 0.5 * IN + stair_row, yr - ext_d))] {
            lines.push((Group::Spine, Line { along_y: true, c0, depth: sd, a0, a1, nominal: spine_size.as_str(), spacing: spine_sp, openings: vec![] }, inward, false));
        }
        for sy in [s0, s1] {
            // The row on the flat's side lies into the flat, the other into the stair core.
            let toward_flat = if sy == s0 { -Vector3::y() } else { Vector3::y() };
            for c0 in [sy - 0.5 * IN - stair_row, sy + 0.5 * IN] {
                let flat_side = (c0 < sy) == (sy == s0);
                let inward = if flat_side { toward_flat } else { -toward_flat };
                lines.push((Group::Stair, Line { along_y: false, c0, depth: stair_row, a0: xf + ext_d, a1: xb - ext_d, nominal: s.stair_stud.as_str(), spacing: s.spacing, openings: vec![] }, inward, false));
            }
        }
        let cap_top = zb + if s.cap { 3.0 } else { 2.0 } * s.plate + s.stud_len;
        let wall_top = cap_top - if s.cap { s.plate } else { 0.0 };
        for (group, line, inward, sheathed) in &lines {
            let bounds = panel_bounds(line, s.panel_max, s.ply);
            for pair in bounds.windows(2) {
                let id = panels.len();
                let seg = Line { along_y: line.along_y, c0: line.c0, depth: line.depth, a0: pair[0], a1: pair[1], nominal: line.nominal,
                                 spacing: line.spacing, openings: line.openings.iter().filter(|o| o.along > pair[0] && o.along < pair[1]).copied().collect() };
                wall(&seg, s, storey, zb, Some(id), &mut out);
                // The hinge: the panel's bottom edge on the side it lies on.
                let across = if inward.dot(&if line.along_y { Vector3::x() } else { Vector3::y() }) > 0.0 { line.c0 + line.depth } else { line.c0 };
                let pivot = if line.along_y { Vector3::new(across, pair[0], zb) } else { Vector3::new(pair[0], across, zb) };
                let sheathing = sheathed.then(|| {
                    // 7/16 in. panels on the outer face, the panel's full length and height.
                    let outer = if inward.dot(&if line.along_y { Vector3::x() } else { Vector3::y() }) > 0.0 { line.c0 } else { line.c0 + line.depth };
                    let t = 11.1 * if inward.dot(&if line.along_y { Vector3::x() } else { Vector3::y() }) > 0.0 { -1.0 } else { 1.0 };
                    let (c0, c1) = (outer.min(outer + t), outer.max(outer + t));
                    line.bx(pair[0], pair[1], c0, c1, zb, wall_top)
                });
                panels.push(Panel { id, storey, group: *group, pivot, axis: Vector3::z().cross(inward), length_mm: pair[1] - pair[0], sheathing });
            }
            // The cap plate, in pieces joined at the middle of every panel but the first, so each
            // joint between panels lies under a whole piece (lapped by half a panel either way).
            let mut cuts = vec![line.a0];
            cuts.extend(bounds.windows(2).skip(1).map(|q| (q[0] + q[1]) / 2.0));
            cuts.push(line.a1);
            for pair in cuts.windows(2).filter(|_| s.cap) {
                let (lo, hi) = line.bx(pair[0], pair[1], line.c0, line.c0 + line.depth, cap_top - s.plate, cap_top);
                out.push(Member::one(Kind::CapPlate, storey, Some(line.nominal), lo, hi));
            }
        }
        // On top: the floor above, or the roof.
        let top = cap_top;
        let roof = storey == b.storeys;
        // Plates, studs, joists and subfloor must close on the next floor level (a stale
        // frame.json for another building wouldn't).
        if !roof {
            let next = top + s.floor_joist.depth + s.subfloor;
            assert!((next - storey as f64 * b.storey).abs() < 1.0, "storey {storey} closes at {next:.1} mm, not {:.1}", storey as f64 * b.storey);
        }
        let (j, kind) = if roof { (&s.roof_joist, Kind::RoofJoist) } else { (&s.floor_joist, Kind::FloorJoist) };
        let rim_nom = s.rim_name.as_deref();
        for (x0, x1) in [(xf, xf + s.rim), (xb - s.rim, xb)] {
            out.push(Member::one(Kind::Rim, storey, rim_nom, Vector3::new(x0, yl, top), Vector3::new(x1, yr, top + j.depth)));
        }
        let bays = [(yl, s0 - 0.5 * IN), (s1 + 0.5 * IN, yr)];
        for (y0, y1) in bays {
            joists(j, kind, storey, s.spacing, y0, y1, xf + s.rim, cx - 0.5 * IN, top, &mut out);
            joists(j, kind, storey, s.spacing, y0, y1, cx + 0.5 * IN, xb - s.rim, top, &mut out);
        }
        if roof {
            // Over the stair the roof joists span between the stair walls' inner rows (along y).
            let (y0, y1) = (s0 + 0.5 * IN, s1 - 0.5 * IN);
            let mut x = xf + s.rim;
            while x + j.width <= xb - s.rim {
                out.push(joist_member(j, kind, storey, Vector3::new(x, y0, top), Vector3::new(x + j.width, y1, top + j.depth), false));
                x += s.spacing;
            }
        }
    }
    (out, panels)
}

/// Joists `width` wide between `x0` and `x1` (the first and last flush with the ends), spanning
/// y from `y0` to `y1` at height z0.
#[allow(clippy::too_many_arguments)]
fn joists_along_y(j: &Joist, kind: Kind, storey: usize, spacing: f64, x0: f64, x1: f64, y0: f64, y1: f64, z0: f64, out: &mut Vec<Member>) {
    let mut xs = vec![x0];
    let mut c = x0 + spacing;
    while c + j.width / 2.0 < x1 - j.width {
        xs.push(c - j.width / 2.0);
        c += spacing;
    }
    xs.push(x1 - j.width);
    for x in xs {
        out.push(joist_member(j, kind, storey, Vector3::new(x, y0, z0), Vector3::new(x + j.width, y1, z0 + j.depth), false));
    }
}

/// A wall framed from a plan box: studs `nominal` deep from `c0` across it (along y when
/// `along_y`), from `a.0` to `a.1` along it, `stud_len` long, with the cap plate in one piece.
#[allow(clippy::too_many_arguments)]
fn box_wall(s: &Schedule, storey: usize, zb: f64, stud_len: f64, along_y: bool, c0: f64, a: (f64, f64),
            nominal: &str, openings: Vec<&Opening>, out: &mut Vec<Member>) {
    let depth = s.depth_of(nominal);
    let line = Line { along_y, c0, depth, a0: a.0, a1: a.1, nominal, spacing: s.spacing, openings };
    wall_h(&line, s, storey, zb, stud_len, None, out);
    let top = zb + 3.0 * s.plate + stud_len;
    let (lo, hi) = line.bx(a.0, a.1, c0, c0 + depth, top - s.plate, top);
    out.push(Member::one(Kind::CapPlate, storey, Some(nominal), lo, hi));
}

/// Addendum 5 (pass 3g step 7, D28): what the services are routed through, framed onto the
/// shell `build` gives (appended after it, so the shell's members keep their order):
/// - **the flats' partitions** (2x4 at the schedule's spacing, centred in the 4.5 in. wall) and
///   **plumbing walls** (2x6 against the wall's spine side, the room side's gypsum in front), each
///   a storey's height under the floor or roof above, like the shell's walls;
/// - **the service annex:** its three walls (the facades' studs, the inner face's gypsum inside
///   them, its two doors framed with jacks, kings and headers from the schedule), the partition
///   between its rooms, a roof of the roof joist spanning across it between rims, and its
///   foundation (footings to the shell's frost depth, stem walls, the slab);
/// - **the stair halls' floors** on storeys 2-3, the floor joist spanning across the core between
///   the stair walls' inner rows (the hall beyond the centre wall to that wall);
/// - **the roof hatch's opening** (`hatch`, x0 y0 x1 y1 in plan, mm) in the roof over the stair:
///   the joists it cuts replaced by doubled trimmers either side, a doubled header at its far
///   edge, and tail joists from the header to the far wall (its near edge is the stair wall).
pub fn addendum_5(b: &Building, lay: &crate::rooms::Layout, s: &Schedule, hatch: [f64; 4], out: &mut Vec<Member>) {
    let (t, w, l) = (b.ext_t, b.depth, b.length);
    let ext_d = s.depth_of(&s.studs[0].0);
    let xf = t - GYP - ext_d;
    let (s0, s1) = (b.flat_len, l - b.flat_len);
    let cx = w / 2.0;
    let ply = s.ply;

    // The roof hatch: out with the over-stair roof joists it touches (trimmer room included).
    let [hx0, _hy0, hx1, hy1] = hatch;
    let (ty0, ty1) = (s0 + 0.5 * IN, s1 - 0.5 * IN);
    let rj = &s.roof_joist;
    let top_roof = (b.storeys - 1) as f64 * b.storey + 3.0 * s.plate + s.stud_len;
    let over_stair = |m: &Member| m.kind == Kind::RoofJoist && m.storey == b.storeys && (m.bounds().0.y - ty0).abs() < 1.0
        && (m.bounds().1.y - ty1).abs() < 1.0;
    let mut tails = Vec::new();
    out.retain(|m| {
        if !over_stair(m) {
            return true;
        }
        let (lo, hi) = m.bounds();
        let cut = hi.x > hx0 - 2.0 * ply && lo.x < hx1 + 2.0 * ply;
        if cut && lo.x >= hx0 && hi.x <= hx1 {
            tails.push(lo.x);
        }
        !cut
    });
    let storey = b.storeys;
    let nom = rj.nominal.as_deref();
    for k in 0..2 {
        for x in [hx0 - (k + 1) as f64 * ply, hx1 + k as f64 * ply] {
            out.push(Member::one(Kind::RoofJoist, storey, nom, Vector3::new(x, ty0, top_roof), Vector3::new(x + ply, ty1, top_roof + rj.depth)));
        }
        out.push(Member::one(Kind::Header, storey, nom, Vector3::new(hx0, hy1 + k as f64 * ply, top_roof),
                             Vector3::new(hx1, hy1 + (k + 1) as f64 * ply, top_roof + rj.depth)));
    }
    for x in tails {
        out.push(Member::one(Kind::RoofJoist, storey, nom, Vector3::new(x, hy1 + 2.0 * ply, top_roof), Vector3::new(x + rj.width, ty1, top_roof + rj.depth)));
    }

    // The flats' partitions and plumbing walls.
    for p in lay.walls(b) {
        let along_y = p.hi.y - p.lo.y > p.hi.x - p.lo.x;
        let (c_lo, c_hi, a) = if along_y { (p.lo.x, p.hi.x, (p.lo.y, p.hi.y)) } else { (p.lo.y, p.hi.y, (p.lo.x, p.hi.x)) };
        let zb = (p.storey - 1) as f64 * b.storey;
        let (nominal, c0) = if p.kind == "plumbing_wall" {
            let d = s.depth_of("2x6");
            // Studs against the spine side; the gypsum is on the room side.
            if c_hi <= cx { ("2x6", c_hi - d) } else { ("2x6", c_lo) }
        } else {
            ("2x4", (c_lo + c_hi) / 2.0 - s.depth_of("2x4") / 2.0)
        };
        box_wall(s, p.storey, zb, s.stud_len, along_y, c0, a, nominal, vec![], out);
    }

    // The annex: walls, partition, roof, foundation.
    let parts: std::collections::HashMap<String, crate::apartment::Part> = lay.annex_parts(b).into_iter().map(|p| (p.id.clone(), p)).collect();
    let (lw, rw, bw, pt, roof) = (&parts["annex-left"], &parts["annex-right"], &parts["annex-back"], &parts["annex-partition"], &parts["annex-roof"]);
    let zw = lw.hi.z;
    let a_len = zw - 3.0 * s.plate;
    let d6 = s.depth_of("2x6");
    let (yl_in, yr_in, xb_in) = (lw.hi.y - GYP, rw.lo.y + GYP, bw.lo.x + GYP); // the studs' inner faces
    let x_out = xb_in + d6; // the back wall's studs' outer face
    let doors: Vec<Opening> = lay.annex_doors(b).iter().map(|d| Opening {
        face: d.face, along: if d.face == Face::Back { (d.lo.y + d.hi.y) / 2.0 } else { (d.lo.x + d.hi.x) / 2.0 },
        sill: 0.0, width: d.width, height: d.height, glazed: false,
    }).collect();
    let on = |f: Face| doors.iter().filter(|o| o.face == f).collect::<Vec<_>>();
    box_wall(s, 1, 0.0, a_len, false, yl_in - d6, (lw.lo.x, x_out), "2x6", on(Face::Left), out);
    box_wall(s, 1, 0.0, a_len, false, yr_in, (rw.lo.x, x_out), "2x6", on(Face::Right), out);
    box_wall(s, 1, 0.0, a_len, true, xb_in, (yl_in, yr_in), "2x6", on(Face::Back), out);
    let d4 = s.depth_of("2x4");
    box_wall(s, 1, 0.0, a_len, true, (pt.lo.x + pt.hi.x) / 2.0 - d4 / 2.0, (pt.lo.y, pt.hi.y), "2x4", vec![], out);
    let (ry0, ry1) = (yl_in - d6, yr_in + d6); // the walls' studs' outer faces
    let rim_nom = s.rim_name.as_deref();
    for (y0, y1) in [(ry0, ry0 + s.rim), (ry1 - s.rim, ry1)] {
        out.push(Member::one(Kind::Rim, 1, rim_nom, Vector3::new(lw.lo.x, y0, zw), Vector3::new(x_out, y1, zw + rj.depth)));
    }
    joists_along_y(rj, Kind::RoofJoist, 1, s.spacing, lw.lo.x, x_out, ry0 + s.rim, ry1 - s.rim, zw, out);
    debug_assert!(zw + rj.depth <= roof.hi.z + 1.0);
    // Its foundation as the shell's: footings at frost depth under 8 in. stem walls, the annex's
    // own footings from the edge of the building's back footing out; the slab inside the stems.
    let (grade, frost, stem_t) = (-8.0 * IN, 36.0 * IN, 8.0 * IN);
    let (fb, ft) = (grade - frost, grade - frost + s.footing_t);
    let fw = s.facade_footing;
    let x_foot = w - stem_t / 2.0 + fw / 2.0; // the building's back footing's far edge
    let (ax1, ay0, ay1) = (lw.hi.x, lw.lo.y, rw.hi.y);
    let foot = |out: &mut Vec<Member>, kind, lo: Vector3<f64>, hi: Vector3<f64>| out.push(Member::one(kind, 0, None, lo, hi));
    for (y0, y1) in [(ay0, ay0 + stem_t), (ay1 - stem_t, ay1)] {
        let yc = (y0 + y1) / 2.0;
        foot(out, Kind::Footing, Vector3::new(x_foot, yc - fw / 2.0, fb), Vector3::new(ax1 - stem_t / 2.0 + fw / 2.0, yc + fw / 2.0, ft));
        foot(out, Kind::Stem, Vector3::new(w, y0, ft), Vector3::new(ax1, y1, 0.0));
    }
    let xc = ax1 - stem_t / 2.0;
    foot(out, Kind::Footing, Vector3::new(xc - fw / 2.0, ay0 + stem_t / 2.0 + fw / 2.0, fb), Vector3::new(xc + fw / 2.0, ay1 - stem_t / 2.0 - fw / 2.0, ft));
    foot(out, Kind::Stem, Vector3::new(ax1 - stem_t, ay0 + stem_t, ft), Vector3::new(ax1, ay1 - stem_t, 0.0));
    foot(out, Kind::Slab, Vector3::new(w, ay0 + stem_t, -4.0 * IN), Vector3::new(ax1 - stem_t, ay1 - stem_t, 0.0));

    // The stair halls' floors: the floor joist across the core, on the stair walls' inner rows;
    // past the hall's end, to the centre wall.
    let fj = &s.floor_joist;
    let st = crate::stair::Stair::example();
    let (ha, hb) = st.hall_end(b);
    let c0 = st.parts(b).iter().find(|p| p.id == "floor-2-hall-a").map(|p| p.hi.y).expect("a hall beyond the centre wall");
    for k in 1..b.storeys {
        let z0 = (k - 1) as f64 * b.storey + 3.0 * s.plate + s.stud_len;
        joists_along_y(fj, Kind::FloorJoist, k, s.spacing, xf + s.rim, hb, ty0, ty1, z0, out);
        joists_along_y(fj, Kind::FloorJoist, k, s.spacing, hb, ha, ty0, c0, z0, out);
    }
}

/// Totals by kind: (count, total length m, volume m3, board feet).
pub fn quantities(members: &[Member]) -> Vec<(Kind, usize, f64, f64, f64)> {
    let mut m: std::collections::BTreeMap<Kind, (usize, f64, f64, f64)> = Default::default();
    for x in members {
        let e = m.entry(x.kind).or_default();
        e.0 += 1;
        e.1 += x.length_m();
        e.2 += x.volume_m3();
        e.3 += x.board_feet();
    }
    m.into_iter().map(|(k, (n, len, v, bf))| (k, n, len, v, bf)).collect()
}
