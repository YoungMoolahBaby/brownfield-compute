//! The apartment building of the neighbourhood (pass 3b): the dense case where the data center's
//! warm loop pays (pass 3). A 3-storey walk-up, 100 x 40 ft, a central stair, four corner flats a
//! floor of 45 x 20 ft (~900 sq ft) each: 12 flats.
//!
//! Frame: millimetres, x across the 40 ft depth (front facade at x = 0), y along the 100 ft length,
//! z up from the top of the ground slab. Floor to floor 10 ft, wood floor systems 12 in. deep, a
//! flat roof. Flats are named by floor (1-3) and corner: front-left, back-left, front-right,
//! back-right; the stair core runs y = 45-55 ft through the full depth.
//!
//! As with the house: every cutter overshoots the faces it cuts by a metre (`CUT`), so
//! `mass_properties` measures true volumes (see docs/CORTENFORGE.md).

use cortenforge::cf_design::Solid;
use nalgebra::Vector3;

use crate::house::FT;

const CUT: f64 = 1000.0;
const IN: f64 = 25.4;
/// The glass and the door panels as drawn: slabs this thick (mm) at the middle of the wall.
const GLASS: f64 = 20.0;
const DOOR_PANEL: f64 = 45.0;

fn cuboid(lo: Vector3<f64>, hi: Vector3<f64>) -> Solid {
    Solid::cuboid((hi - lo) / 2.0).translate((hi + lo) / 2.0)
}

fn union_all(parts: Vec<Solid>) -> Solid {
    parts.into_iter().reduce(|a, b| a.union(b)).expect("at least one part")
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Face {
    Front, // x = 0
    Back,  // x = W
    Left,  // y = 0
    Right, // y = L
}

#[derive(Clone, Copy, Debug)]
pub struct Opening {
    pub face: Face,
    pub along: f64, // centre along the face (y for Front/Back, x for Left/Right)
    pub sill: f64,  // above the top of the slab
    pub width: f64,
    pub height: f64,
    pub glazed: bool,
}

/// What an opening is: a door starts at its storey's floor (glazed: the patio door; solid: the
/// stair's entry door), a window above it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum OpeningKind {
    Window,
    PatioDoor,
    EntryDoor,
}

impl OpeningKind {
    pub fn name(self) -> &'static str {
        match self {
            OpeningKind::Window => "window",
            OpeningKind::PatioDoor => "patio_door",
            OpeningKind::EntryDoor => "entry_door",
        }
    }
}

impl Face {
    pub fn name(self) -> &'static str {
        match self {
            Face::Front => "front",
            Face::Back => "back",
            Face::Left => "left",
            Face::Right => "right",
        }
    }

    /// The outward normal in the building's frame.
    pub fn outward(self) -> Vector3<f64> {
        match self {
            Face::Front => Vector3::new(-1.0, 0.0, 0.0),
            Face::Back => Vector3::new(1.0, 0.0, 0.0),
            Face::Left => Vector3::new(0.0, -1.0, 0.0),
            Face::Right => Vector3::new(0.0, 1.0, 0.0),
        }
    }
}

/// One opening as the bid set names it (pass 3f, D27). The id is `<space>/<face>/<index>`: the
/// space is the flat (`2-back-right`) or the stair of a storey (`1-stair`), found from where the
/// opening is, and the index counts along the face within that space. So an id stays put while
/// the layout does, whatever order the openings were made in.
#[derive(Clone, Debug)]
pub struct OpeningRecord {
    pub id: String,
    pub kind: OpeningKind,
    pub storey: usize,
    pub flat: Option<String>,
    pub index: usize,
    pub opening: Opening,
    /// The opening through the wall's full thickness (mm), no overshoot.
    pub lo: Vector3<f64>,
    pub hi: Vector3<f64>,
}

/// One box of the building (mm): a wall, a floor system, the ground slab or the roof.
#[derive(Clone, Debug)]
pub struct Part {
    pub id: String,
    pub kind: &'static str,
    /// The storey it belongs to: every wall is one storey's; a floor system is the floor of the
    /// storey above it; the roof sits on the top storey.
    pub storey: usize,
    pub lo: Vector3<f64>,
    pub hi: Vector3<f64>,
}

#[derive(Clone, Debug)]
pub struct Flat {
    pub name: String,
    pub floor: usize, // 1..=3
    pub front: bool,  // on the x = 0 side
    pub left: bool,   // on the y = 0 end
}

pub struct Building {
    pub depth: f64,
    pub length: f64,
    pub storey: f64,
    pub storeys: usize,
    pub ext_t: f64,
    pub party_t: f64,
    pub floor_t: f64,
    pub roof_t: f64,
    pub slab_t: f64,
    pub flat_len: f64, // along y
    pub stair_len: f64,
    pub openings: Vec<Opening>,
    pub flats: Vec<Flat>,
}

impl Building {
    pub fn example() -> Self {
        let (w, l, h, flat_len) = (40.0 * FT, 100.0 * FT, 10.0 * FT, 45.0 * FT);
        let mut b = Building {
            depth: w,
            length: l,
            storey: h,
            storeys: 3,
            ext_t: 7.0 * IN,
            party_t: 10.0 * IN, // a double-stud fire and sound wall
            floor_t: 12.0 * IN,
            roof_t: 14.0 * IN,
            slab_t: 4.0 * IN,
            flat_len,
            stair_len: l - 2.0 * flat_len,
            openings: Vec::new(),
            flats: Vec::new(),
        };
        let win = 3.0 * FT;
        for floor in 1..=b.storeys {
            let base = (floor - 1) as f64 * h;
            for (front, face) in [(true, Face::Front), (false, Face::Back)] {
                for left in [true, false] {
                    let name = format!("{}-{}{}", floor, if front { "front" } else { "back" }, if left { "-left" } else { "-right" });
                    b.flats.push(Flat { name, floor, front, left });
                    // Along the long facade: six windows and a 6 ft patio door, evenly spread.
                    let y0 = if left { 0.0 } else { l - flat_len };
                    let slots = 7.0;
                    for i in 0..7 {
                        let along = y0 + flat_len * (i as f64 + 0.5) / slots;
                        let door = i == 3;
                        b.openings.push(Opening {
                            face,
                            along,
                            sill: base + if door { 0.0 } else { 3.0 * FT },
                            width: if door { 6.0 * FT } else { win },
                            height: if door { 80.0 * IN } else { 4.0 * FT },
                            glazed: true,
                        });
                    }
                    // Two windows in the end wall, in this flat's half of the depth.
                    let (x0, x1) = if front { (0.0, w / 2.0) } else { (w / 2.0, w) };
                    for j in [1.0, 2.0] {
                        b.openings.push(Opening {
                            face: if left { Face::Left } else { Face::Right },
                            along: x0 + (x1 - x0) * j / 3.0,
                            sill: base + 3.0 * FT,
                            width: win,
                            height: 4.0 * FT,
                            glazed: true,
                        });
                    }
                }
            }
            // The stair core: an entry door at the front on the ground floor, a window on every
            // other face and landing.
            let mid = l / 2.0;
            if floor == 1 {
                b.openings.push(Opening { face: Face::Front, along: mid, sill: base, width: 3.5 * FT, height: 80.0 * IN, glazed: false });
            } else {
                b.openings.push(Opening { face: Face::Front, along: mid, sill: base + 3.0 * FT, width: win, height: 4.0 * FT, glazed: true });
            }
            b.openings.push(Opening { face: Face::Back, along: mid, sill: base + 3.0 * FT, width: win, height: 4.0 * FT, glazed: true });
        }
        b
    }

    pub fn height(&self) -> f64 {
        self.storeys as f64 * self.storey
    }

    /// An opening's box through the wall, overshooting both faces by `e` (mm).
    fn opening_span(&self, o: &Opening, e: f64) -> (Vector3<f64>, Vector3<f64>) {
        let t = self.ext_t;
        let (z0, z1) = (o.sill, o.sill + o.height);
        let (a0, a1) = (o.along - o.width / 2.0, o.along + o.width / 2.0);
        match o.face {
            Face::Front => (Vector3::new(0.0 - e, a0, z0), Vector3::new(t + e, a1, z1)),
            Face::Back => (Vector3::new(self.depth - t - e, a0, z0), Vector3::new(self.depth + e, a1, z1)),
            Face::Left => (Vector3::new(a0, 0.0 - e, z0), Vector3::new(a1, t + e, z1)),
            Face::Right => (Vector3::new(a0, self.length - t - e, z0), Vector3::new(a1, self.length + e, z1)),
        }
    }

    fn opening_box(&self, o: &Opening) -> Solid {
        let (lo, hi) = self.opening_span(o, CUT);
        cuboid(lo, hi)
    }

    pub fn ground_slab(&self) -> Solid {
        let s = self.ground_slab_part();
        cuboid(s.lo, s.hi)
    }

    fn ground_slab_part(&self) -> Part {
        Part { id: "slab-ground".into(), kind: "ground_slab", storey: 1,
               lo: Vector3::new(0.0, 0.0, -self.slab_t), hi: Vector3::new(self.depth, self.length, 0.0) }
    }

    /// The exterior walls, full height, openings cut.
    pub fn exterior_walls(&self) -> Solid {
        let (w, l, h, t) = (self.depth, self.length, self.height(), self.ext_t);
        let outer = cuboid(Vector3::new(0.0, 0.0, 0.0), Vector3::new(w, l, h));
        let inner = cuboid(Vector3::new(t, t, -CUT), Vector3::new(w - t, l - t, h + CUT));
        self.openings.iter().fold(outer.subtract(inner), |s, o| s.subtract(self.opening_box(o)))
    }

    /// Party walls: the spine between front and back flats, and the two stair walls.
    pub fn party_walls(&self) -> Solid {
        union_all(self.party_wall_parts().iter().map(|p| cuboid(p.lo, p.hi)).collect())
    }

    /// The spine and stair walls, a storey at a time, platform-framed as `framing` builds them:
    /// each storey's walls stand on the floor below and stop under the floor above, which bears on
    /// them (pass 3f, D27; until then they ran full height and the floors ran through them).
    fn party_wall_parts(&self) -> Vec<Part> {
        let (w, l, t, p) = (self.depth, self.length, self.ext_t, self.party_t);
        let (s0, s1) = (self.flat_len, l - self.flat_len);
        let mut v = Vec::new();
        for k in 1..=self.storeys {
            let (z0, z1) = self.wall_z(k, true);
            let mut part = |id: &str, lo: Vector3<f64>, hi: Vector3<f64>| v.push(Part {
                id: format!("{id}-{k}"), kind: "party_wall", storey: k, lo: Vector3::new(lo.x, lo.y, z0), hi: Vector3::new(hi.x, hi.y, z1) });
            part("spine-left", Vector3::new(w / 2.0 - p / 2.0, t, 0.0), Vector3::new(w / 2.0 + p / 2.0, s0 - p / 2.0, 0.0));
            part("spine-right", Vector3::new(w / 2.0 - p / 2.0, s1 + p / 2.0, 0.0), Vector3::new(w / 2.0 + p / 2.0, l - t, 0.0));
            part("stair-left", Vector3::new(t, s0 - p / 2.0, 0.0), Vector3::new(w - t, s0 + p / 2.0, 0.0));
            part("stair-right", Vector3::new(t, s1 - p / 2.0, 0.0), Vector3::new(w - t, s1 + p / 2.0, 0.0));
        }
        v
    }

    /// A storey's walls from bottom to top (mm): from its floor level up to the floor system above
    /// (`under_floor`, the walls the floors bear on) or the next level (the exterior walls, which
    /// the floors stop inside); the top storey's walls run to the roof.
    fn wall_z(&self, k: usize, under_floor: bool) -> (f64, f64) {
        let z0 = (k - 1) as f64 * self.storey;
        let top = k as f64 * self.storey;
        (z0, if under_floor && k < self.storeys { top - self.floor_t } else { top })
    }

    /// The floor systems between storeys (inside the exterior walls; the stair keeps its opening).
    pub fn floors(&self) -> Solid {
        union_all(self.floor_parts().iter().map(|p| cuboid(p.lo, p.hi)).collect())
    }

    fn floor_parts(&self) -> Vec<Part> {
        let (w, l, t) = (self.depth, self.length, self.ext_t);
        let (s0, s1) = (self.flat_len + self.party_t / 2.0, l - self.flat_len - self.party_t / 2.0);
        let mut parts = Vec::new();
        for k in 1..self.storeys {
            let top = k as f64 * self.storey;
            let z0 = top - self.floor_t;
            let part = |side: &str, lo, hi| Part { id: format!("floor-{}-{side}", k + 1), kind: "floor", storey: k + 1, lo, hi };
            parts.push(part("left", Vector3::new(t, t, z0), Vector3::new(w - t, s0, top)));
            parts.push(part("right", Vector3::new(t, s1, z0), Vector3::new(w - t, l - t, top)));
        }
        parts
    }

    fn roof_part(&self) -> Part {
        let h = self.height();
        Part { id: "roof".into(), kind: "roof", storey: self.storeys,
               lo: Vector3::new(-150.0, -150.0, h), hi: Vector3::new(self.depth + 150.0, self.length + 150.0, h + self.roof_t) }
    }

    pub fn roof(&self) -> Solid {
        let r = self.roof_part();
        cuboid(r.lo, r.hi)
    }

    /// The glass or door panel in an opening: a slab `pane` thick at the middle of the wall (mm).
    pub fn panel_span(&self, o: &Opening) -> (Vector3<f64>, Vector3<f64>) {
        let pane = if o.glazed { GLASS } else { DOOR_PANEL };
        let mid = self.ext_t / 2.0;
        let (z0, z1) = (o.sill, o.sill + o.height);
        let (a0, a1) = (o.along - o.width / 2.0, o.along + o.width / 2.0);
        match o.face {
            Face::Front => (Vector3::new(mid - pane / 2.0, a0, z0), Vector3::new(mid + pane / 2.0, a1, z1)),
            Face::Back => (Vector3::new(self.depth - mid - pane / 2.0, a0, z0), Vector3::new(self.depth - mid + pane / 2.0, a1, z1)),
            Face::Left => (Vector3::new(a0, mid - pane / 2.0, z0), Vector3::new(a1, mid + pane / 2.0, z1)),
            Face::Right => (Vector3::new(a0, self.length - mid - pane / 2.0, z0), Vector3::new(a1, self.length - mid + pane / 2.0, z1)),
        }
    }

    fn panels(&self, glazed: bool) -> Solid {
        union_all(self.openings.iter().filter(|o| o.glazed == glazed).map(|o| {
            let (lo, hi) = self.panel_span(o);
            cuboid(lo, hi)
        }).collect())
    }

    pub fn glass(&self) -> Solid {
        self.panels(true)
    }

    pub fn doors(&self) -> Solid {
        self.panels(false)
    }

    // ---- Analytic envelope per flat (m, m2, m3) ----

    fn flat_openings(&self, f: &Flat) -> impl Iterator<Item = &Opening> {
        let base = (f.floor - 1) as f64 * self.storey;
        let (long, end) = (if f.front { Face::Front } else { Face::Back }, if f.left { Face::Left } else { Face::Right });
        let (y0, y1) = if f.left { (0.0, self.flat_len) } else { (self.length - self.flat_len, self.length) };
        let (x0, x1) = if f.front { (0.0, self.depth / 2.0) } else { (self.depth / 2.0, self.depth) };
        self.openings.iter().filter(move |o| {
            o.sill >= base - 1.0 && o.sill < base + self.storey - 1.0
                && ((o.face == long && o.along > y0 && o.along < y1) || (o.face == end && o.along > x0 && o.along < x1))
        })
    }

    /// One flat's envelope, in the house's JSON shape (`ceiling_m2` is the roof over a top-floor
    /// flat, `slab_perimeter_m` the slab edge under a ground-floor flat; party walls and floors
    /// between flats lose nothing).
    pub fn flat_envelope(&self, f: &Flat) -> serde_json::Value {
        let (t, p) = (self.ext_t, self.party_t);
        let floor_m2 = (self.depth / 2.0 - t - p / 2.0) * (self.flat_len - t - p / 2.0) / 1e6;
        let ceiling_h = self.storey - self.floor_t;
        let gross = (self.flat_len + self.depth / 2.0) * self.storey / 1e6;
        let glazed: f64 = self.flat_openings(f).filter(|o| o.glazed).map(|o| o.width * o.height).sum::<f64>() / 1e6;
        let top = f.floor == self.storeys;
        let ground = f.floor == 1;
        serde_json::json!({
            "name": f.name, "floor": f.floor,
            "floor_m2": floor_m2, "interior_volume_m3": floor_m2 * ceiling_h / 1e3,
            "wall_gross_m2": gross, "wall_net_m2": gross - glazed, "glazed_m2": glazed, "door_m2": 0.0,
            "ceiling_m2": if top { self.flat_len * self.depth / 2.0 / 1e6 } else { 0.0 },
            "slab_perimeter_m": if ground { (self.flat_len + self.depth / 2.0) / 1e3 } else { 0.0 },
        })
    }

    /// Exterior wall material (m3), openings out.
    pub fn exterior_wall_volume_m3(&self) -> f64 {
        let (w, l, h, t) = (self.depth, self.length, self.height(), self.ext_t);
        let shell = (w * l - (w - 2.0 * t) * (l - 2.0 * t)) * h;
        let cut: f64 = self.openings.iter().map(|o| o.width * o.height * t).sum();
        (shell - cut) / 1e9
    }

    /// Floor systems (m3): two pieces a level, each from the end wall to the stair wall's far face.
    pub fn floors_volume_m3(&self) -> f64 {
        let (w, t) = (self.depth, self.ext_t);
        let piece = self.flat_len + self.party_t / 2.0 - t;
        (self.storeys - 1) as f64 * (w - 2.0 * t) * 2.0 * piece * self.floor_t / 1e9
    }

    // ---- The model as named parts, for the bid set (pass 3f, D27) ----

    /// The storey an opening is in (1-based), from its sill.
    pub fn storey_of(&self, o: &Opening) -> usize {
        ((o.sill + 1.0) / self.storey).floor() as usize + 1
    }

    pub fn kind_of(&self, o: &Opening) -> OpeningKind {
        let above_floor = o.sill - (self.storey_of(o) - 1) as f64 * self.storey;
        match (above_floor < 1.0, o.glazed) {
            (false, _) => OpeningKind::Window,
            (true, true) => OpeningKind::PatioDoor,
            (true, false) => OpeningKind::EntryDoor,
        }
    }

    /// Addendum 1 (made up, pass 3f step 5, to run a change through the bid set): the patio doors
    /// take a new `width` (mm), centred where they were. The width comes from params
    /// (`bidset.addendum_1.patio_door_width_in`, passed on the command line), not from here.
    /// Everything else follows from the model as usual.
    pub fn addendum_1(&mut self, width: f64) {
        let doors: Vec<usize> = (0..self.openings.len())
            .filter(|&i| self.kind_of(&self.openings[i]) == OpeningKind::PatioDoor)
            .collect();
        for i in doors {
            self.openings[i].width = width;
        }
    }

    /// Addendum 2 (pass 3g step 1, D28): the service annex behind the stair core covers the
    /// ground floor's back stair window, so it goes. The annex itself, and the rooms, are
    /// `rooms::Layout`'s, built from this building as `stair` is.
    pub fn addendum_2(&mut self) {
        let (mid, storey) = (self.length / 2.0, self.storey);
        self.openings.retain(|o| !(o.face == Face::Back && (o.along - mid).abs() < 1.0 && o.sill < storey));
    }

    /// The flat an opening belongs to, from where its centre is (None in the stair core). Found
    /// from the geometry, not from `flat_openings`, so the two can check each other.
    fn flat_at(&self, storey: usize, c: Vector3<f64>) -> Option<String> {
        let side = if c.y < self.flat_len { "left" } else if c.y > self.length - self.flat_len { "right" } else { return None };
        Some(format!("{storey}-{}-{side}", if c.x < self.depth / 2.0 { "front" } else { "back" }))
    }

    /// Every opening with its stable id (see `OpeningRecord`), in id order.
    pub fn opening_records(&self) -> Vec<OpeningRecord> {
        let mut recs: Vec<OpeningRecord> = self.openings.iter().map(|o| {
            let storey = self.storey_of(o);
            let (lo, hi) = self.opening_span(o, 0.0);
            OpeningRecord { id: String::new(), kind: self.kind_of(o), storey, flat: self.flat_at(storey, (lo + hi) / 2.0),
                            index: 0, opening: *o, lo, hi }
        }).collect();
        let space = |r: &OpeningRecord| r.flat.clone().unwrap_or_else(|| format!("{}-stair", r.storey));
        recs.sort_by(|a, b| (a.storey, space(a), a.opening.face.name()).cmp(&(b.storey, space(b), b.opening.face.name()))
            .then(a.opening.along.total_cmp(&b.opening.along)));
        let mut prev = String::new();
        let mut n = 0;
        for r in recs.iter_mut() {
            let group = format!("{}/{}", space(r), r.opening.face.name());
            n = if group == prev { n + 1 } else { 0 };
            r.index = n;
            r.id = format!("{group}/{n}");
            prev = group;
        }
        recs
    }

    /// The exterior walls, four boxes a storey (`ext-front-2`): front and back run the full length,
    /// the end walls fit between them, each storey from its level to the next (the floors stop
    /// inside them). Together they are exactly the shell `exterior_walls` cuts its openings from.
    pub fn exterior_wall_parts(&self) -> Vec<Part> {
        let (w, l, t) = (self.depth, self.length, self.ext_t);
        let mut v = Vec::new();
        for k in 1..=self.storeys {
            let (z0, z1) = self.wall_z(k, false);
            let mut part = |face: Face, lo: (f64, f64), hi: (f64, f64)| v.push(Part {
                id: format!("ext-{}-{k}", face.name()), kind: "exterior_wall", storey: k,
                lo: Vector3::new(lo.0, lo.1, z0), hi: Vector3::new(hi.0, hi.1, z1) });
            part(Face::Front, (0.0, 0.0), (t, l));
            part(Face::Back, (w - t, 0.0), (w, l));
            part(Face::Left, (t, 0.0), (w - t, t));
            part(Face::Right, (t, l - t), (w - t, l));
        }
        v
    }

    /// The exterior wall an opening is in: its face, its storey.
    pub fn wall_of(&self, r: &OpeningRecord) -> String {
        format!("ext-{}-{}", r.opening.face.name(), r.storey)
    }

    /// Every part of the building but its openings: walls, the ground slab, floors and the roof.
    pub fn parts(&self) -> Vec<Part> {
        let mut v = self.exterior_wall_parts();
        v.extend(self.party_wall_parts());
        v.push(self.ground_slab_part());
        v.extend(self.floor_parts());
        v.push(self.roof_part());
        v
    }

    /// The model's own checks before it is written out (empty when it holds): ids unique, every
    /// opening in a known flat or the stair, inside its wall and its storey (under the floor system
    /// above), clear of the party and stair walls where they meet the facade, no two openings
    /// overlapping, no two parts overlapping, and the wall boxes summing to the shell.
    pub fn model_errors(&self) -> Vec<String> {
        let mut errs = Vec::new();
        let recs = self.opening_records();
        let parts = self.parts();
        let vol = |lo: Vector3<f64>, hi: Vector3<f64>| (hi - lo).map(|d| d.max(0.0)).product();
        let overlap = |a: (Vector3<f64>, Vector3<f64>), b: (Vector3<f64>, Vector3<f64>)| vol(a.0.sup(&b.0), a.1.inf(&b.1));
        let mut ids: Vec<&str> = recs.iter().map(|r| r.id.as_str()).collect();
        ids.sort();
        ids.dedup();
        if ids.len() != recs.len() {
            errs.push(format!("{} openings but {} distinct ids", recs.len(), ids.len()));
        }
        let (p, mid) = (self.party_t, self.depth / 2.0);
        let junctions = [self.flat_len, self.length - self.flat_len];
        for r in &recs {
            if let Some(f) = &r.flat {
                if !self.flats.iter().any(|g| &g.name == f) {
                    errs.push(format!("{}: no flat {f}", r.id));
                }
            }
            let Some(wall) = parts.iter().find(|w| w.id == self.wall_of(r)) else {
                errs.push(format!("{}: no wall {}", r.id, self.wall_of(r)));
                continue;
            };
            if (0..3).any(|i| r.lo[i] < wall.lo[i] - 0.01 || r.hi[i] > wall.hi[i] + 0.01) {
                errs.push(format!("{}: outside {}", r.id, wall.id));
            }
            let base = (r.storey - 1) as f64 * self.storey;
            if r.opening.sill < base - 0.01 || r.opening.sill + r.opening.height > base + self.storey - self.floor_t + 0.01 {
                errs.push(format!("{}: not within storey {} under the floor system", r.id, r.storey));
            }
            let (a0, a1) = (r.opening.along - r.opening.width / 2.0, r.opening.along + r.opening.width / 2.0);
            let walls_meeting: Vec<f64> = match r.opening.face {
                Face::Front | Face::Back => junctions.to_vec(),
                Face::Left | Face::Right => vec![mid],
            };
            if walls_meeting.iter().any(|&c| a1 > c - p / 2.0 && a0 < c + p / 2.0) {
                errs.push(format!("{}: meets a party or stair wall", r.id));
            }
        }
        for (i, a) in recs.iter().enumerate() {
            for b in &recs[i + 1..] {
                if overlap((a.lo, a.hi), (b.lo, b.hi)) > 0.0 {
                    errs.push(format!("openings {} and {} overlap", a.id, b.id));
                }
            }
        }
        // Every pair of parts: no clashes (an IFC checker would flag any).
        for (i, a) in parts.iter().enumerate() {
            for b in &parts[i + 1..] {
                if overlap((a.lo, a.hi), (b.lo, b.hi)) > 0.0 {
                    errs.push(format!("parts {} and {} overlap", a.id, b.id));
                }
            }
        }
        let (w, l, h, t) = (self.depth, self.length, self.height(), self.ext_t);
        let shell = (w * l - (w - 2.0 * t) * (l - 2.0 * t)) * h;
        let walls: f64 = self.exterior_wall_parts().iter().map(|p| vol(p.lo, p.hi)).sum();
        if ((walls - shell) / shell).abs() > 1e-9 {
            errs.push(format!("wall boxes {:.6} m3 against the shell's {:.6}", walls / 1e9, shell / 1e9));
        }
        errs
    }
}
