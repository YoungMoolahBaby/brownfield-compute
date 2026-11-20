//! The walk-up's stair, its halls and the flats' entry doors (pass 3f step 8, D27). Pass 3b's
//! `apartment::Building` left the stair core empty: no flights, no hall floors upstairs, no doors
//! into the flats. This builds them from the building, without changing it, so pass 3b's framing,
//! masonry and costs (which read `Building::openings`) keep their numbers.
//!
//! The design (dimensions here; the code limits they are checked against live in
//! `params/bidset.yaml`, `code.stair` and `code.door`, and the check is `brownfield bidset`):
//! - **A stair that turns back on itself, at the back of the core.** A wall between the two
//!   flights means neither has an open side. Each storey has:
//!   - 6 risers of 6 in up from the floor towards the back, to a landing against the back wall;
//!   - then 12 of 7 in back towards the front, up to the next floor.
//!
//!   The landing's top is at the back stair windows' 36 in sill, so it doesn't cross them. Risers
//!   differ between the two flights, which IBC 2018 1011.5.4 allows: it asks for uniformity
//!   within a flight. The shorter upper flight leaves room for a 36 in door between the spine
//!   and the end of its handrail.
//!   - An even 9 + 9 would put the landing across the windows.
//!   - 5 + 13 would leave no room for that door.
//! - **Hall floors on levels 2 and 3** from the front wall to the stair, full width in front of
//!   the upper flight and on along the lower flight's side up to its first riser.
//! - **A wall closing the space under the ground-floor upper flight,** where headroom falls below
//!   a person's height.
//! - **A guard on level 3,** across the lower flight's side, where no flight goes on up.
//! - **Handrails on both sides of every flight,** as rail paths along the nosing line:
//!   - extended one tread past the bottom riser, sloping;
//!   - and 12 in level past the top riser.
//! - **The 12 flat doors,** 36 x 84 in, in the stair walls. Two a wall a storey, opening off the
//!   hall and swinging into the flats.
//!
//! Frame and units as `apartment` (mm; x across the depth from the front, y along the length, z up
//! from the top of the ground slab). Side A of the core is the stair-left side (y below the centre
//! wall), side B the stair-right side.

use nalgebra::Vector3;

use crate::apartment::{Building, Part};

const IN: f64 = 25.4;

/// One flight: `risers` risers of `riser` up from the walking surface at `z0`, treads `tread` deep,
/// the bottom riser's face at `x_bottom`, rising towards +x (`dir` 1) or -x (`dir` -1), across y
/// from `y0` to `y1` (wall face to wall face).
#[derive(Clone, Debug)]
pub struct Flight {
    pub id: String,
    pub storey: usize,
    pub side: &'static str,
    pub risers: usize,
    pub riser: f64,
    pub tread: f64,
    pub x_bottom: f64,
    pub dir: f64,
    pub y0: f64,
    pub y1: f64,
    pub z0: f64,
}

impl Flight {
    pub fn treads(&self) -> usize {
        self.risers - 1
    }

    /// The face of the top riser, where the landing or floor above begins.
    pub fn x_top(&self) -> f64 {
        self.x_bottom + self.dir * self.treads() as f64 * self.tread
    }

    pub fn z_top(&self) -> f64 {
        self.z0 + self.risers as f64 * self.riser
    }

    pub fn width(&self) -> f64 {
        self.y1 - self.y0
    }

    /// The steps as boxes, each one riser tall and one tread deep, its top the tread.
    pub fn steps(&self) -> Vec<Part> {
        (0..self.treads()).map(|i| {
            let (xa, xb) = (self.x_bottom + self.dir * i as f64 * self.tread, self.x_bottom + self.dir * (i + 1) as f64 * self.tread);
            Part {
                id: format!("{}-{i}", self.id), kind: "step", storey: self.storey,
                lo: Vector3::new(xa.min(xb), self.y0, self.z0 + i as f64 * self.riser),
                hi: Vector3::new(xa.max(xb), self.y1, self.z0 + (i + 1) as f64 * self.riser),
            }
        }).collect()
    }
}

/// A handrail as a path (its centreline, mm) beside one side of a flight.
#[derive(Clone, Debug)]
pub struct Rail {
    pub id: String,
    pub storey: usize,
    pub flight: String,
    pub points: Vec<Vector3<f64>>,
    pub above_nosing: f64,
    pub diameter: f64,
}

/// A flat's entry door, in a stair wall: `right` is the stair-right wall (y = L - flat length),
/// else the stair-left one; `along` is its centre in x.
#[derive(Clone, Debug)]
pub struct FlatDoor {
    pub id: String,
    pub storey: usize,
    pub flat: String,
    pub right: bool,
    pub along: f64,
    pub width: f64,
    pub height: f64,
}

pub struct Stair {
    /// The landing's top above each floor, and the risers below and above it.
    pub landing_top: f64,
    pub risers_lower: usize,
    pub risers_upper: usize,
    pub tread: f64,
    pub landing_depth: f64,
    pub landing_t: f64,
    pub centre_t: f64,
    pub guard_h: f64,
    pub guard_t: f64,
    pub rail_above_nosing: f64,
    pub rail_diameter: f64,
    pub rail_clear: f64,
    pub rail_top_extension: f64,
    pub door_width: f64,
    pub door_height: f64,
    /// Flat doors' centres in x: one in the front flats' half of the core, one in the back's.
    pub door_x: [f64; 2],
}

impl Stair {
    pub fn example() -> Self {
        Stair {
            landing_top: 36.0 * IN,
            risers_lower: 6,
            risers_upper: 12,
            tread: 11.0 * IN,
            landing_depth: 48.0 * IN,
            landing_t: 12.0 * IN,
            centre_t: 4.5 * IN, // 2x4 studs, 1/2 in gypsum each side
            guard_h: 42.0 * IN,
            guard_t: 2.0 * IN,
            rail_above_nosing: 36.0 * IN,
            rail_diameter: 1.5 * IN,
            rail_clear: 1.5 * IN,
            rail_top_extension: 12.0 * IN,
            door_width: 36.0 * IN,
            door_height: 84.0 * IN,
            door_x: [211.5 * IN, 268.5 * IN],
        }
    }

    /// The two flights' risers: up to the landing, and from it to the next floor.
    pub fn risers(&self, b: &Building) -> (f64, f64) {
        (self.landing_top / self.risers_lower as f64, (b.storey - self.landing_top) / self.risers_upper as f64)
    }

    /// The core between the stair walls' faces, in y.
    pub fn core_y(&self, b: &Building) -> (f64, f64) {
        (b.flat_len + b.party_t / 2.0, b.length - b.flat_len - b.party_t / 2.0)
    }

    /// The centre wall between the flights, in y.
    pub fn centre_y(&self, b: &Building) -> (f64, f64) {
        let mid = b.length / 2.0;
        (mid - self.centre_t / 2.0, mid + self.centre_t / 2.0)
    }

    /// The landing against the back wall, in x.
    pub fn landing_x(&self, b: &Building) -> (f64, f64) {
        (b.depth - b.ext_t - self.landing_depth, b.depth - b.ext_t)
    }

    /// Both flights of each storey that has one above it (storeys 1 and 2).
    pub fn flights(&self, b: &Building) -> Vec<Flight> {
        let ((ra, rb), (c0, c1), (y0, y1), lx) = (self.risers(b), self.centre_y(b), self.core_y(b), self.landing_x(b).0);
        let mut v = Vec::new();
        for k in 1..b.storeys {
            let base = (k - 1) as f64 * b.storey;
            v.push(Flight { id: format!("flight-{k}a"), storey: k, side: "a", risers: self.risers_lower, riser: ra, tread: self.tread,
                            x_bottom: lx - (self.risers_lower - 1) as f64 * self.tread, dir: 1.0, y0, y1: c0, z0: base });
            v.push(Flight { id: format!("flight-{k}b"), storey: k, side: "b", risers: self.risers_upper, riser: rb, tread: self.tread,
                            x_bottom: lx, dir: -1.0, y0: c1, y1, z0: base + self.landing_top });
        }
        v
    }

    /// Where the hall ends on each side: side A at the lower flight's bottom riser, side B at the
    /// upper flight's top riser.
    pub fn hall_end(&self, b: &Building) -> (f64, f64) {
        let f = self.flights(b);
        if f.len() < 2 {
            let lx = self.landing_x(b).0; // a one-storey building has no stair
            return (lx, lx);
        }
        (f[0].x_bottom, f[1].x_top())
    }

    /// Every box of the stair and its core: steps, landings, hall floors, the centre wall, the
    /// wall under the ground-floor upper flight, and the guard.
    pub fn parts(&self, b: &Building) -> Vec<Part> {
        let (t, h) = (b.ext_t, b.storey);
        let ((y0, y1), (c0, c1), (lx0, lx1), (ha, hb)) = (self.core_y(b), self.centre_y(b), self.landing_x(b), self.hall_end(b));
        let mut v = Vec::new();
        for f in self.flights(b) {
            v.extend(f.steps());
        }
        for k in 1..b.storeys {
            let top = (k - 1) as f64 * h + self.landing_top;
            v.push(Part { id: format!("landing-{k}"), kind: "landing", storey: k,
                          lo: Vector3::new(lx0, y0, top - self.landing_t), hi: Vector3::new(lx1, y1, top) });
        }
        for k in 2..=b.storeys {
            let (z1, z0) = ((k - 1) as f64 * h, (k - 1) as f64 * h - b.floor_t);
            v.push(Part { id: format!("floor-{k}-hall"), kind: "floor", storey: k,
                          lo: Vector3::new(t, y0, z0), hi: Vector3::new(hb, y1, z1) });
            v.push(Part { id: format!("floor-{k}-hall-a"), kind: "floor", storey: k,
                          lo: Vector3::new(hb, y0, z0), hi: Vector3::new(ha, c0, z1) });
        }
        for k in 1..=b.storeys {
            let z0 = (k - 1) as f64 * h;
            v.push(Part { id: format!("stair-centre-{k}"), kind: "stair_partition", storey: k,
                          lo: Vector3::new(hb, c0, z0), hi: Vector3::new(lx0, c1, z0 + h) });
        }
        v.push(Part { id: "stair-closure-1".into(), kind: "stair_partition", storey: 1,
                      lo: Vector3::new(hb - self.centre_t, c1, 0.0), hi: Vector3::new(hb, y1, h - b.floor_t) });
        let top = (b.storeys - 1) as f64 * h;
        v.push(Part { id: format!("guard-{}", b.storeys), kind: "guard", storey: b.storeys,
                      lo: Vector3::new(ha - self.guard_t, y0, top), hi: Vector3::new(ha, c0, top + self.guard_h) });
        v
    }

    /// Handrails on both sides of every flight, along the nosing line `rail_above_nosing` up: from
    /// one tread past the bottom riser (sloping) to `rail_top_extension` past the top riser (level).
    pub fn rails(&self, b: &Building) -> Vec<Rail> {
        let off = self.rail_clear + self.rail_diameter / 2.0;
        let mut v = Vec::new();
        for f in self.flights(b) {
            // The nosing line: z = z0 + riser * (1 + steps from the bottom riser), through the top
            // riser's edge at z_top.
            let slope = f.riser / f.tread;
            let z_at = |x: f64| f.z0 + f.riser + slope * (x - f.x_bottom) * f.dir + self.rail_above_nosing;
            let (xb, xt) = (f.x_bottom - f.dir * f.tread, f.x_top());
            for (side, y) in [("wall", if f.side == "a" { f.y0 + off } else { f.y1 - off }),
                              ("centre", if f.side == "a" { f.y1 - off } else { f.y0 + off })] {
                v.push(Rail {
                    id: format!("rail-{}-{side}", f.id.trim_start_matches("flight-")), storey: f.storey, flight: f.id.clone(),
                    points: vec![Vector3::new(xb, y, z_at(xb)), Vector3::new(xt, y, z_at(xt)),
                                 Vector3::new(xt + f.dir * self.rail_top_extension, y, z_at(xt))],
                    above_nosing: self.rail_above_nosing, diameter: self.rail_diameter,
                });
            }
        }
        v
    }

    /// The 12 flat doors: on every storey, in each stair wall, one into the front flat and one into
    /// the back flat. The id is `<flat>/stair/0`, as the openings' ids go (`<space>/<face>/<index>`).
    pub fn doors(&self, b: &Building) -> Vec<FlatDoor> {
        let mut v = Vec::new();
        for k in 1..=b.storeys {
            for right in [false, true] {
                for (x, front) in [(self.door_x[0], true), (self.door_x[1], false)] {
                    let flat = format!("{k}-{}-{}", if front { "front" } else { "back" }, if right { "right" } else { "left" });
                    v.push(FlatDoor { id: format!("{flat}/stair/0"), storey: k, flat, right, along: x,
                                      width: self.door_width, height: self.door_height });
                }
            }
        }
        v
    }

    /// A door's opening through its stair wall (no overshoot), and its leaf, `pane` thick at the
    /// middle of the wall.
    pub fn door_span(&self, b: &Building, d: &FlatDoor) -> (Vector3<f64>, Vector3<f64>) {
        let yc = if d.right { b.length - b.flat_len } else { b.flat_len };
        let z0 = (d.storey - 1) as f64 * b.storey;
        (Vector3::new(d.along - d.width / 2.0, yc - b.party_t / 2.0, z0), Vector3::new(d.along + d.width / 2.0, yc + b.party_t / 2.0, z0 + d.height))
    }

    pub fn door_leaf(&self, b: &Building, d: &FlatDoor, pane: f64) -> (Vector3<f64>, Vector3<f64>) {
        let (lo, hi) = self.door_span(b, d);
        let yc = (lo.y + hi.y) / 2.0;
        (Vector3::new(lo.x, yc - pane / 2.0, lo.z), Vector3::new(hi.x, yc + pane / 2.0, hi.z))
    }

    /// Into the flat: -y through the stair-left wall, +y through the stair-right one.
    pub fn door_outward(&self, d: &FlatDoor) -> Vector3<f64> {
        Vector3::new(0.0, if d.right { 1.0 } else { -1.0 }, 0.0)
    }

    pub fn door_wall(&self, d: &FlatDoor) -> String {
        format!("stair-{}-{}", if d.right { "right" } else { "left" }, d.storey)
    }

    /// The stair's own checks against the building (empty when it holds). The flights rise a
    /// storey by construction (`risers`); `brownfield bidset` measures it from the boxes.
    /// - every box clear of every other box, the building's included, and no landing across a
    ///   window;
    /// - every door inside its stair wall, under the floor above, clear of the spine, on the hall,
    ///   not overlapping another;
    /// - every door's approach (44 in into the core, its full width and height) clear of the
    ///   stair's parts, and no handrail across it.
    pub fn errors(&self, b: &Building) -> Vec<String> {
        let mut errs = Vec::new();
        // Boxes clash when they overlap by more than 0.01 mm on every axis (float noise in a
        // shared face isn't a clash).
        let overlap = |a: (Vector3<f64>, Vector3<f64>), c: (Vector3<f64>, Vector3<f64>)| {
            let d = a.1.inf(&c.1) - a.0.sup(&c.0);
            if d.iter().all(|&v| v > 0.01) { d.product() } else { 0.0 }
        };
        let flights = self.flights(b);
        if flights.is_empty() {
            errs.push("no flights: the building has one storey".into());
            return errs;
        }
        let mine = self.parts(b);
        let theirs = b.parts();
        for (i, a) in mine.iter().enumerate() {
            for c in mine[i + 1..].iter().chain(theirs.iter()) {
                if overlap((a.lo, a.hi), (c.lo, c.hi)) > 0.0 {
                    errs.push(format!("parts {} and {} overlap", a.id, c.id));
                }
            }
        }
        // A landing against a wall mustn't cross a window in it: the opening through the wall,
        // grown by the wall's thickness, against the landing.
        for r in b.opening_records() {
            let grow = Vector3::new(b.ext_t, b.ext_t, 0.0);
            for l in mine.iter().filter(|p| p.kind == "landing") {
                if overlap((r.lo - grow, r.hi + grow), (l.lo, l.hi)) > 0.0 {
                    errs.push(format!("{} crosses window {}", l.id, r.id));
                }
            }
        }
        let (ha, hb) = self.hall_end(b);
        let doors = self.doors(b);
        for (i, d) in doors.iter().enumerate() {
            let (lo, hi) = self.door_span(b, d);
            let Some(wall) = theirs.iter().find(|w| w.id == self.door_wall(d)) else {
                errs.push(format!("{}: no wall {}", d.id, self.door_wall(d)));
                continue;
            };
            if (0..3).any(|j| lo[j] < wall.lo[j] - 0.01 || hi[j] > wall.hi[j] + 0.01) {
                errs.push(format!("{}: outside {}", d.id, wall.id));
            }
            let mid = b.depth / 2.0;
            if hi.x > mid - b.party_t / 2.0 && lo.x < mid + b.party_t / 2.0 {
                errs.push(format!("{}: meets the spine wall", d.id));
            }
            if hi.x > if d.right { hb } else { ha } + 0.01 {
                errs.push(format!("{}: past the end of the hall", d.id));
            }
            if (d.along < mid) != d.flat.contains("front") {
                errs.push(format!("{}: not in its flat's half of the core", d.id));
            }
            for e in &doors[i + 1..] {
                if overlap((lo, hi), self.door_span(b, e)) > 0.0 {
                    errs.push(format!("doors {} and {} overlap", d.id, e.id));
                }
            }
            // The approach: the landing in front of the door, 44 in into the core (IBC 2018
            // 1010.1.6; `brownfield bidset` checks it from params), its width, its height.
            let reach = 44.0 * IN;
            let (y_face, into) = if d.right { (lo.y, -1.0) } else { (hi.y, 1.0) };
            let (ya, yb) = (y_face, y_face + into * reach);
            let (alo, ahi) = (Vector3::new(lo.x, ya.min(yb), lo.z + 1.0), Vector3::new(hi.x, ya.max(yb), hi.z));
            for p in &mine {
                if overlap((alo, ahi), (p.lo, p.hi)) > 0.0 {
                    errs.push(format!("{}: {} stands in its approach", d.id, p.id));
                }
            }
            for r in self.rails(b) {
                for w in r.points.windows(2) {
                    let (p, q) = (w[0], w[1]);
                    let (x0, x1) = (p.x.min(q.x), p.x.max(q.x));
                    if x1 > lo.x + 0.01 && x0 < hi.x - 0.01 && p.y > alo.y && p.y < ahi.y
                        && p.z.max(q.z) > lo.z && p.z.min(q.z) < hi.z {
                        errs.push(format!("{}: handrail {} runs across it", d.id, r.id));
                    }
                }
            }
        }
        errs
    }

    /// The stair for the bid set's JSON (metres, rounded as `r6` does).
    pub fn json(&self, b: &Building, r6: &dyn Fn(f64) -> f64) -> serde_json::Value {
        let m = |v: Vector3<f64>| [r6(v.x), r6(v.y), r6(v.z)];
        let flights: Vec<_> = self.flights(b).iter().map(|f| serde_json::json!({
            "id": f.id, "storey": f.storey, "side": f.side, "risers": f.risers, "treads": f.treads(),
            "riser_m": r6(f.riser), "tread_m": r6(f.tread), "width_m": r6(f.width()),
            "x_bottom_m": r6(f.x_bottom), "x_top_m": r6(f.x_top()), "dir": f.dir,
            "y0_m": r6(f.y0), "y1_m": r6(f.y1), "z0_m": r6(f.z0), "z_top_m": r6(f.z_top()),
            "steps": f.steps().iter().map(|s| s.id.clone()).collect::<Vec<_>>(),
        })).collect();
        let parts: Vec<_> = self.parts(b).iter().map(|p| serde_json::json!({
            "id": p.id, "kind": p.kind, "storey": p.storey, "lo_m": m(p.lo), "hi_m": m(p.hi),
        })).collect();
        let rails: Vec<_> = self.rails(b).iter().map(|r| serde_json::json!({
            "id": r.id, "storey": r.storey, "flight": r.flight, "points_m": r.points.iter().map(|p| m(*p)).collect::<Vec<_>>(),
            "above_nosing_m": r6(r.above_nosing), "diameter_m": r6(r.diameter),
        })).collect();
        let doors: Vec<_> = self.doors(b).iter().map(|d| {
            let (lo, hi) = self.door_span(b, d);
            let (plo, phi) = self.door_leaf(b, d, 45.0);
            serde_json::json!({
                "id": d.id, "kind": "flat_door", "glazed": false, "storey": d.storey, "flat": d.flat,
                "face": "stair", "wall": self.door_wall(d), "index": 0,
                "width_m": r6(d.width), "height_m": r6(d.height), "along_m": r6(d.along),
                "sill_m": r6(lo.z), "sill_above_floor_m": 0.0,
                "lo_m": m(lo), "hi_m": m(hi), "panel_lo_m": m(plo), "panel_hi_m": m(phi),
                "outward": m(self.door_outward(d) * 1e3), "swing": "into the flat",
            })
        }).collect();
        let (ha, hb) = self.hall_end(b);
        let (y0, y1) = self.core_y(b);
        serde_json::json!({
            "source": "forge `stair` (pass 3f step 8): the walk-up's stair, halls and flat doors, built from `apartment`",
            "core_y_m": [r6(y0), r6(y1)], "hall_end_m": {"a": r6(ha), "b": r6(hb)},
            "landing_top_m": r6(self.landing_top), "tread_m": r6(self.tread),
            "flights": flights, "parts": parts, "rails": rails, "doors": doors,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn errs_with(change: impl Fn(&mut Stair)) -> Vec<String> {
        let b = Building::example();
        let mut s = Stair::example();
        change(&mut s);
        s.errors(&b)
    }

    #[test]
    fn the_example_holds() {
        let (b, s) = (Building::example(), Stair::example());
        assert_eq!(s.errors(&b), Vec::<String>::new());
        assert_eq!(s.flights(&b).len(), 4);
        // Every flat gets exactly one door.
        let mut flats: Vec<String> = s.doors(&b).iter().map(|d| d.flat.clone()).collect();
        flats.sort();
        flats.dedup();
        assert_eq!((s.doors(&b).len(), flats.len()), (12, b.flats.len()));
    }

    #[test]
    fn a_landing_across_a_window_is_caught() {
        // 9 + 9 risers: the landing's top at 60 in, across the back stair windows (36-84 in).
        assert!(errs_with(|s| { s.landing_top = 60.0 * IN; s.risers_lower = 9; s.risers_upper = 9; })
            .iter().any(|e| e.contains("crosses window")));
    }

    #[test]
    fn a_landing_into_the_slab_is_caught() {
        // 40 in thick: landing-1's underside goes 4 in below the ground slab's top.
        assert!(errs_with(|s| s.landing_t = 40.0 * IN).iter().any(|e| e.contains("landing-1 and slab-ground overlap")));
    }

    #[test]
    fn a_door_past_the_hall_or_in_the_spine_is_caught() {
        assert!(errs_with(|s| s.door_x[1] = 300.0 * IN).iter().any(|e| e.contains("past the end of the hall")));
        assert!(errs_with(|s| s.door_x[0] = 230.0 * IN).iter().any(|e| e.contains("meets the spine wall")));
    }

    #[test]
    fn a_door_too_tall_for_its_wall_is_caught() {
        assert!(errs_with(|s| s.door_height = 120.0 * IN).iter().any(|e| e.contains("outside stair-left-1")));
    }

    #[test]
    fn a_handrail_across_a_door_is_caught() {
        // The back-right door moved 10 in towards the stair: the upper flight's handrail
        // extension (292-304 in) runs across it.
        assert!(errs_with(|s| s.door_x[1] = 278.5 * IN).iter().any(|e| e.contains("handrail rail-2b-wall runs across it")));
    }

    #[test]
    fn a_door_onto_the_guard_is_caught() {
        // The back-left door moved up to the hall's end on side A (370 in): on level 3 the guard
        // stands in front of it.
        assert!(errs_with(|s| s.door_x[1] = 352.0 * IN).iter().any(|e| e.contains("guard-3 stands in its approach")));
    }
}
