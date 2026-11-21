//! The walk-up's rooms, plumbing walls and service annex (pass 3g step 1, D28). Pass 3b's
//! `apartment::Building` has flats but no rooms, and the systems are laid out room by room. This
//! builds them from the building without changing it, as `stair` does, so the base model and
//! Addendum 1 keep their numbers. They are issued with Addendum 2 (`apartment-json addendum-2`).
//!
//! The design (dimensions here; the code limits the rooms are checked against live in
//! `params/systems.yaml`, and the check is `brownfield systems`):
//! - **Every flat alike, mirrored** across the spine (front and back) and across the stair (left
//!   and right), and the same on every storey, so wet rooms stack floor over floor.
//! - **Two bedrooms at the end-wall corner.** Bed 1 at the facade corner (two facade windows and
//!   one in the end wall), bed 2 against the spine (the other end-wall window).
//! - **A wet run on the spine:** the bath, a utility closet (laundry, the radiant manifold, the
//!   heat and water meters) and the kitchen in a line. They sit back to back with the neighbour's
//!   across the spine.
//! - **A plumbing wall in front of the spine** along that run: 2x6 studs with gypsum on the room
//!   side, standing a half inch clear of the party wall. The pipes are in it, so none touch or
//!   pierce the party wall, which stays whole for fire and sound.
//! - **Open living, dining, kitchen and entry** along the facade with the patio door. A study nook
//!   off the living room, open to it: at 6.5 ft wide it is too narrow to be a bedroom.
//! - **The service annex** (D28): one storey behind the stair core, as wide as the core, with a
//!   mechanical and plumbing room against the building and an electrical room at the far end,
//!   each with its own outside door. It covers the ground floor's back stair window, which
//!   Addendum 2 removes (`Building::addendum_2`).
//!
//! The stair splits the building in two, and its enclosure may be pierced only for fire
//! protection, security and communication systems and the stair's own ventilation and power (IBC
//! 2021 1023.5): not the flats' water, heat or power. So those leave the annex under the
//! ground-floor slab. Steps 4-5 route them.
//!
//! Frame and units as `apartment` (mm; x across the depth from the front, y along the length, z up
//! from the top of the ground slab).

use nalgebra::Vector3;
use serde_json::json;

use crate::apartment::{Building, Face, OpeningRecord, Part};
use crate::house::FT;

const IN: f64 = 25.4;
/// An interior partition: 2x4 studs (3.5 in) with 1/2 in gypsum on each face.
pub const PARTITION: f64 = 4.5 * IN;
/// The plumbing wall: 2x6 studs (5.5 in) with 1/2 in gypsum on the room side.
pub const PLUMBING_WALL: f64 = 6.0 * IN;
/// Its air gap to the party wall.
pub const PLUMBING_GAP: f64 = 0.5 * IN;

/// What a room is for.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Use {
    Bedroom,
    Living,
    Study,
    Kitchen,
    Bath,
    Utility,
    Hall,
    Entry,
    Mechanical,
    Electrical,
}

impl Use {
    pub fn name(self) -> &'static str {
        match self {
            Use::Bedroom => "bedroom",
            Use::Living => "living",
            Use::Study => "study",
            Use::Kitchen => "kitchen",
            Use::Bath => "bath",
            Use::Utility => "utility",
            Use::Hall => "hall",
            Use::Entry => "entry",
            Use::Mechanical => "mechanical",
            Use::Electrical => "electrical",
        }
    }
}

/// One room: a box from its floor to the ceiling (the underside of the floor system above, or of
/// the roof), between the faces of its walls. Open-plan rooms meet at a line with no wall.
#[derive(Clone, Debug)]
pub struct Room {
    pub id: String,
    pub flat: Option<String>,
    pub storey: usize,
    pub use_: Use,
    pub lo: Vector3<f64>,
    pub hi: Vector3<f64>,
}

impl Room {
    pub fn area_m2(&self) -> f64 {
        (self.hi.x - self.lo.x) * (self.hi.y - self.lo.y) / 1e6
    }
}

/// A door in the annex's walls: `face` is the wall's outward side (`left` -y, `right` +y, `back`
/// +x, away from the building).
#[derive(Clone, Debug)]
pub struct AnnexDoor {
    pub id: String,
    pub room: String,
    pub face: Face,
    pub wall: String,
    pub lo: Vector3<f64>,
    pub hi: Vector3<f64>,
    pub width: f64,
    pub height: f64,
}

/// The layout: where the lines between rooms fall in the front-left flat (mm, in the building's
/// frame), mirrored to the others; and the annex's size.
pub struct Layout {
    /// Bed 1 | bed 2 and the hall (x).
    pub bed_split_x: f64,
    /// The living room's inner edge, open to the kitchen and the entry (x).
    pub living_x: f64,
    /// The hall | the bath and the utility closet (x).
    pub hall_x: f64,
    /// Bed 2 | the hall and the bath (y).
    pub bed2_y: f64,
    /// Bed 1 | the study nook (y).
    pub bed1_y: f64,
    /// The bath | the utility closet; also where the study, the hall and the living room meet (y).
    pub bath_y: f64,
    /// The utility closet | the kitchen (y).
    pub utility_y: f64,
    /// The kitchen | the entry, and the end of the plumbing wall (y).
    pub kitchen_y: f64,
    /// The annex out from the back wall, the mechanical room's depth to the partition's centre,
    /// its walls' height.
    pub annex_depth: f64,
    pub mech_depth: f64,
    pub annex_wall_h: f64,
    pub mech_door_w: f64,
    pub elec_door_w: f64,
    pub door_h: f64,
}

impl Layout {
    pub fn example() -> Self {
        Layout {
            bed_split_x: 10.0 * FT,
            living_x: 11.5 * FT,
            hall_x: 13.5 * FT,
            bed2_y: 11.0 * FT,
            bed1_y: 13.0 * FT,
            bath_y: 19.5 * FT,
            utility_y: 23.0 * FT,
            kitchen_y: 34.0 * FT,
            annex_depth: 20.0 * FT,
            mech_depth: 12.0 * FT,
            annex_wall_h: 9.0 * FT,
            // 42 in for the water heater's tanks; 36 in for the electrical room.
            mech_door_w: 42.0 * IN,
            elec_door_w: 36.0 * IN,
            door_h: 80.0 * IN,
        }
    }

    /// A storey's floor and ceiling (mm): partitions and rooms run from the floor to the floor
    /// system above, or to the roof on the top storey.
    fn storey_z(&self, b: &Building, k: usize) -> (f64, f64) {
        let z0 = (k - 1) as f64 * b.storey;
        (z0, if k < b.storeys { k as f64 * b.storey - b.floor_t } else { k as f64 * b.storey })
    }

    /// The front-left flat's inside faces: the facade's and the end wall's, the spine's, the
    /// stair wall's (mm).
    fn faces(&self, b: &Building) -> (f64, f64, f64) {
        (b.ext_t, b.depth / 2.0 - b.party_t / 2.0, b.flat_len - b.party_t / 2.0)
    }

    /// The front-left flat's rooms and walls as plan rectangles (x0, x1, y0, y1), mm.
    #[allow(clippy::type_complexity)]
    fn plan(&self, b: &Building) -> (Vec<(&'static str, Use, [f64; 4])>, Vec<(&'static str, &'static str, [f64; 4])>) {
        let (e, sf, tf) = self.faces(b);
        let h = PARTITION / 2.0;
        let pw = sf - PLUMBING_GAP - PLUMBING_WALL;
        let (xa, xb, xc) = (self.bed_split_x, self.living_x, self.hall_x);
        let (ya, yb, yc, yd, ye) = (self.bed2_y, self.bed1_y, self.bath_y, self.utility_y, self.kitchen_y);
        let rooms = vec![
            ("bed-1", Use::Bedroom, [e, xa - h, e, yb - h]),
            ("bed-2", Use::Bedroom, [xa + h, sf, e, ya - h]),
            ("hall", Use::Hall, [xa + h, xc - h, ya + h, yc]),
            ("study", Use::Study, [e, xa + h, yb + h, yc]),
            ("bath", Use::Bath, [xc + h, pw, ya + h, yc - h]),
            ("utility", Use::Utility, [xc + h, pw, yc + h, yd - h]),
            ("living", Use::Living, [e, xb, yc, tf]),
            ("passage", Use::Hall, [xb, xc - h, yc, yd + h]),
            ("kitchen", Use::Kitchen, [xb, pw, yd + h, ye]),
            ("entry", Use::Entry, [xb, sf, ye, tf]),
        ];
        let walls = vec![
            ("p1", "partition", [xa - h, xa + h, e, yb + h]),
            ("p2", "partition", [e, xa - h, yb - h, yb + h]),
            ("p3", "partition", [xa + h, sf, ya - h, ya + h]),
            ("p4", "partition", [xc - h, xc + h, ya + h, yd + h]),
            ("p5", "partition", [xc + h, pw, yc - h, yc + h]),
            ("p6", "partition", [xc + h, pw, yd - h, yd + h]),
            ("plumbing-wall", "plumbing_wall", [pw, sf - PLUMBING_GAP, ya + h, ye]),
        ];
        (rooms, walls)
    }

    /// A front-left plan rectangle mirrored into a flat (front/back across the spine, left/right
    /// across the stair), as a box over storey `k`.
    fn place(&self, b: &Building, r: [f64; 4], front: bool, left: bool, k: usize) -> (Vector3<f64>, Vector3<f64>) {
        let (mut x0, mut x1, mut y0, mut y1) = (r[0], r[1], r[2], r[3]);
        if !front {
            (x0, x1) = (b.depth - x1, b.depth - x0);
        }
        if !left {
            (y0, y1) = (b.length - y1, b.length - y0);
        }
        let (z0, z1) = self.storey_z(b, k);
        (Vector3::new(x0, y0, z0), Vector3::new(x1, y1, z1))
    }

    /// The annex's plan: x from the back wall out, y across the stair core's outer faces (mm).
    fn annex_xy(&self, b: &Building) -> (f64, f64, f64, f64) {
        let (y0, y1) = (b.flat_len - b.party_t / 2.0, b.length - b.flat_len + b.party_t / 2.0);
        (b.depth, b.depth + self.annex_depth, y0, y1)
    }

    /// Every room: the flats' (in flat order, then plan order) and the annex's two.
    pub fn rooms(&self, b: &Building) -> Vec<Room> {
        let (plan, _) = self.plan(b);
        let mut v = Vec::new();
        for f in &b.flats {
            for (name, use_, r) in &plan {
                let (lo, hi) = self.place(b, *r, f.front, f.left, f.floor);
                v.push(Room { id: format!("{}/{name}", f.name), flat: Some(f.name.clone()), storey: f.floor, use_: *use_, lo, hi });
            }
        }
        let (x0, x1, y0, y1) = self.annex_xy(b);
        let (e, h) = (b.ext_t, PARTITION / 2.0);
        let xm = x0 + self.mech_depth;
        let z1 = self.annex_wall_h;
        v.push(Room { id: "annex/mechanical".into(), flat: None, storey: 1, use_: Use::Mechanical,
                      lo: Vector3::new(x0, y0 + e, 0.0), hi: Vector3::new(xm - h, y1 - e, z1) });
        v.push(Room { id: "annex/electrical".into(), flat: None, storey: 1, use_: Use::Electrical,
                      lo: Vector3::new(xm + h, y0 + e, 0.0), hi: Vector3::new(x1 - e, y1 - e, z1) });
        v
    }

    /// The flats' partitions and plumbing walls (`<flat>/p1`, `<flat>/plumbing-wall`).
    pub fn walls(&self, b: &Building) -> Vec<Part> {
        let (_, walls) = self.plan(b);
        let mut v = Vec::new();
        for f in &b.flats {
            for (name, kind, r) in &walls {
                let (lo, hi) = self.place(b, *r, f.front, f.left, f.floor);
                v.push(Part { id: format!("{}/{name}", f.name), kind, storey: f.floor, lo, hi });
            }
        }
        v
    }

    /// The annex's parts: slab, three walls (the building's back wall is its fourth), the
    /// partition between its rooms, and its roof.
    pub fn annex_parts(&self, b: &Building) -> Vec<Part> {
        let (x0, x1, y0, y1) = self.annex_xy(b);
        let (e, h) = (b.ext_t, PARTITION / 2.0);
        let (zw, xm) = (self.annex_wall_h, x0 + self.mech_depth);
        let part = |id: &str, kind: &'static str, lo: [f64; 3], hi: [f64; 3]| Part {
            id: id.into(), kind, storey: 1, lo: Vector3::from(lo), hi: Vector3::from(hi) };
        vec![
            part("annex-slab", "annex_slab", [x0, y0, -b.slab_t], [x1, y1, 0.0]),
            part("annex-left", "annex_wall", [x0, y0, 0.0], [x1, y0 + e, zw]),
            part("annex-right", "annex_wall", [x0, y1 - e, 0.0], [x1, y1, zw]),
            part("annex-back", "annex_wall", [x1 - e, y0 + e, 0.0], [x1, y1 - e, zw]),
            part("annex-partition", "annex_partition", [xm - h, y0 + e, 0.0], [xm + h, y1 - e, zw]),
            part("annex-roof", "annex_roof", [x0, y0 - 150.0, zw], [x1 + 150.0, y1 + 150.0, zw + b.roof_t]),
        ]
    }

    /// The annex's doors: the mechanical room's in the left wall near the building, the
    /// electrical room's in the far end.
    pub fn annex_doors(&self, b: &Building) -> Vec<AnnexDoor> {
        let (x0, x1, y0, y1) = self.annex_xy(b);
        let e = b.ext_t;
        let mx = x0 + 6.0 * FT;
        let ym = (y0 + y1) / 2.0;
        let (wm, we, dh) = (self.mech_door_w, self.elec_door_w, self.door_h);
        vec![
            AnnexDoor { id: "annex-mechanical/left/0".into(), room: "annex/mechanical".into(), face: Face::Left,
                        wall: "annex-left".into(), width: wm, height: dh,
                        lo: Vector3::new(mx - wm / 2.0, y0, 0.0), hi: Vector3::new(mx + wm / 2.0, y0 + e, dh) },
            AnnexDoor { id: "annex-electrical/back/0".into(), room: "annex/electrical".into(), face: Face::Back,
                        wall: "annex-back".into(), width: we, height: dh,
                        lo: Vector3::new(x1 - e, ym - we / 2.0, 0.0), hi: Vector3::new(x1, ym + we / 2.0, dh) },
        ]
    }

    /// The openings in a room's outside walls: the building's (ids) whose centre lies along the
    /// room's side of the wall, or the annex's doors.
    pub fn openings_of(&self, b: &Building, recs: &[OpeningRecord], r: &Room) -> Vec<String> {
        let tol = 1.0;
        let mut v: Vec<String> = recs.iter().filter(|o| o.storey == r.storey && o.flat == r.flat && r.flat.is_some()).filter(|o| {
            let c = (o.lo + o.hi) / 2.0;
            match o.opening.face {
                Face::Front => r.lo.x <= b.ext_t + tol && c.y > r.lo.y && c.y < r.hi.y,
                Face::Back => r.hi.x >= b.depth - b.ext_t - tol && c.y > r.lo.y && c.y < r.hi.y,
                Face::Left => r.lo.y <= b.ext_t + tol && c.x > r.lo.x && c.x < r.hi.x,
                Face::Right => r.hi.y >= b.length - b.ext_t - tol && c.x > r.lo.x && c.x < r.hi.x,
            }
        }).map(|o| o.id.clone()).collect();
        v.extend(self.annex_doors(b).into_iter().filter(|d| d.room == r.id).map(|d| d.id));
        v
    }

    /// Why the layout doesn't hold (empty when it does):
    /// - every room and wall inside its flat (or the annex) and its storey;
    /// - no two of them overlapping, nor any of them a part of the building or the stair;
    /// - each flat covered exactly: rooms, walls and the plumbing wall's air gap sum to its floor;
    /// - every bedroom with an opening in an outside wall (whether it is an escape opening is
    ///   `brownfield systems`'s check);
    /// - the annex clear of every opening left in the building, its doors inside their walls.
    pub fn errors(&self, b: &Building, stair_parts: &[Part]) -> Vec<String> {
        let mut errs = Vec::new();
        let overlap = |a: (Vector3<f64>, Vector3<f64>), c: (Vector3<f64>, Vector3<f64>)| {
            let d = a.1.inf(&c.1) - a.0.sup(&c.0);
            if d.iter().all(|&v| v > 0.01) { d.product() } else { 0.0 }
        };
        let rooms = self.rooms(b);
        let walls = self.walls(b);
        let annex = self.annex_parts(b);
        let recs = b.opening_records();
        let (e, sf, tf) = self.faces(b);
        // Boxes: rooms and walls together.
        let mut boxes: Vec<(String, Vector3<f64>, Vector3<f64>)> = rooms.iter().map(|r| (r.id.clone(), r.lo, r.hi)).collect();
        boxes.extend(walls.iter().map(|p| (p.id.clone(), p.lo, p.hi)));
        for (i, a) in boxes.iter().enumerate() {
            if (0..3).any(|j| a.2[j] - a.1[j] <= 0.0) {
                errs.push(format!("{}: empty", a.0));
            }
            for c in &boxes[i + 1..] {
                if overlap((a.1, a.2), (c.1, c.2)) > 0.0 {
                    errs.push(format!("{} and {} overlap", a.0, c.0));
                }
            }
            for p in b.parts().iter().chain(stair_parts).chain(annex.iter()) {
                if overlap((a.1, a.2), (p.lo, p.hi)) > 0.0 {
                    errs.push(format!("{} and {} overlap", a.0, p.id));
                }
            }
        }
        for (i, a) in annex.iter().enumerate() {
            for c in annex[i + 1..].iter().chain(b.parts().iter()).chain(stair_parts) {
                if overlap((a.lo, a.hi), (c.lo, c.hi)) > 0.0 {
                    errs.push(format!("{} and {} overlap", a.id, c.id));
                }
            }
        }
        // Each flat inside its own faces, its storey, and covered exactly.
        let floor = (sf - e) * (tf - e);
        let gap = PLUMBING_GAP * (self.kitchen_y - self.bed2_y - PARTITION / 2.0);
        for f in &b.flats {
            let (lo, hi) = self.place(b, [e, sf, e, tf], f.front, f.left, f.floor);
            let mine: Vec<_> = boxes.iter().filter(|x| x.0.starts_with(&format!("{}/", f.name))).collect();
            for x in &mine {
                if (0..3).any(|j| x.1[j] < lo[j] - 0.01 || x.2[j] > hi[j] + 0.01) {
                    errs.push(format!("{}: outside its flat", x.0));
                }
            }
            let covered: f64 = mine.iter().map(|x| (x.2.x - x.1.x) * (x.2.y - x.1.y)).sum::<f64>() + gap;
            if ((covered - floor) / floor).abs() > 1e-9 {
                errs.push(format!("{}: rooms and walls cover {:.4} m2 of its {:.4}", f.name, covered / 1e6, floor / 1e6));
            }
        }
        for r in rooms.iter().filter(|r| r.use_ == Use::Bedroom) {
            if self.openings_of(b, &recs, r).is_empty() {
                errs.push(format!("{}: a bedroom with no opening in an outside wall", r.id));
            }
        }
        // The annex covers no opening left in the building's back wall, with a wall's thickness
        // to spare on each side, up to the top of its roof.
        let (x0, _, y0, y1) = self.annex_xy(b);
        let top = self.annex_wall_h + b.roof_t;
        for o in recs.iter().filter(|o| o.opening.face == Face::Back) {
            if o.hi.y > y0 - e && o.lo.y < y1 + e && o.lo.z < top && o.hi.x >= x0 - 0.01 {
                errs.push(format!("the annex covers {}", o.id));
            }
        }
        for d in self.annex_doors(b) {
            let Some(w) = annex.iter().find(|p| p.id == d.wall) else {
                errs.push(format!("{}: no wall {}", d.id, d.wall));
                continue;
            };
            if (0..3).any(|j| d.lo[j] < w.lo[j] - 0.01 || d.hi[j] > w.hi[j] + 0.01) {
                errs.push(format!("{}: outside {}", d.id, w.id));
            }
            if !rooms.iter().any(|r| r.id == d.room) {
                errs.push(format!("{}: no room {}", d.id, d.room));
            }
        }
        errs
    }

    /// The layout for the bid set's JSON (metres, rounded as `r6` does).
    pub fn json(&self, b: &Building, r6: &dyn Fn(f64) -> f64) -> serde_json::Value {
        let m = |v: Vector3<f64>| [r6(v.x), r6(v.y), r6(v.z)];
        let recs = b.opening_records();
        let rooms: Vec<_> = self.rooms(b).iter().map(|r| json!({
            "id": r.id, "flat": r.flat, "storey": r.storey, "use": r.use_.name(),
            "lo_m": m(r.lo), "hi_m": m(r.hi), "area_m2": (r.area_m2() * 1e6).round() / 1e6,
            "openings": self.openings_of(b, &recs, r),
        })).collect();
        let part = |p: &Part| json!({"id": p.id, "kind": p.kind, "storey": p.storey, "lo_m": m(p.lo), "hi_m": m(p.hi)});
        let walls: Vec<_> = self.walls(b).iter().map(part).collect();
        let annex: Vec<_> = self.annex_parts(b).iter().map(part).collect();
        let doors: Vec<_> = self.annex_doors(b).iter().map(|d| {
            let out = d.face.outward();
            json!({
                "id": d.id, "kind": "service_door", "glazed": false, "storey": 1, "room": d.room, "face": d.face.name(),
                "wall": d.wall, "index": 0, "width_m": r6(d.width), "height_m": r6(d.height),
                "sill_m": 0.0, "sill_above_floor_m": 0.0, "lo_m": m(d.lo), "hi_m": m(d.hi),
                "outward": m(out * 1e3), "swing": "out",
            })
        }).collect();
        json!({
            "source": "forge `rooms` (pass 3g step 1, D28): the walk-up's rooms, plumbing walls and service annex, built from `apartment`",
            "partition_t_m": r6(PARTITION), "plumbing_wall_t_m": r6(PLUMBING_WALL), "plumbing_gap_m": r6(PLUMBING_GAP),
            "rooms": rooms, "walls": walls, "annex": {"parts": annex, "doors": doors},
        })
    }
}
