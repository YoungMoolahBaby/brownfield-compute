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

    fn opening_box(&self, o: &Opening) -> Solid {
        let (t, e) = (self.ext_t, CUT);
        let (z0, z1) = (o.sill, o.sill + o.height);
        let (a0, a1) = (o.along - o.width / 2.0, o.along + o.width / 2.0);
        match o.face {
            Face::Front => cuboid(Vector3::new(-e, a0, z0), Vector3::new(t + e, a1, z1)),
            Face::Back => cuboid(Vector3::new(self.depth - t - e, a0, z0), Vector3::new(self.depth + e, a1, z1)),
            Face::Left => cuboid(Vector3::new(a0, -e, z0), Vector3::new(a1, t + e, z1)),
            Face::Right => cuboid(Vector3::new(a0, self.length - t - e, z0), Vector3::new(a1, self.length + e, z1)),
        }
    }

    pub fn ground_slab(&self) -> Solid {
        cuboid(Vector3::new(0.0, 0.0, -self.slab_t), Vector3::new(self.depth, self.length, 0.0))
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
        let (w, l, h, t, p) = (self.depth, self.length, self.height(), self.ext_t, self.party_t);
        let (s0, s1) = (self.flat_len, l - self.flat_len);
        union_all(vec![
            cuboid(Vector3::new(w / 2.0 - p / 2.0, t, 0.0), Vector3::new(w / 2.0 + p / 2.0, s0 - p / 2.0, h)),
            cuboid(Vector3::new(w / 2.0 - p / 2.0, s1 + p / 2.0, 0.0), Vector3::new(w / 2.0 + p / 2.0, l - t, h)),
            cuboid(Vector3::new(t, s0 - p / 2.0, 0.0), Vector3::new(w - t, s0 + p / 2.0, h)),
            cuboid(Vector3::new(t, s1 - p / 2.0, 0.0), Vector3::new(w - t, s1 + p / 2.0, h)),
        ])
    }

    /// The floor systems between storeys (inside the exterior walls; the stair keeps its opening).
    pub fn floors(&self) -> Solid {
        let (w, l, t) = (self.depth, self.length, self.ext_t);
        let (s0, s1) = (self.flat_len + self.party_t / 2.0, l - self.flat_len - self.party_t / 2.0);
        let mut parts = Vec::new();
        for k in 1..self.storeys {
            let top = k as f64 * self.storey;
            let z0 = top - self.floor_t;
            parts.push(cuboid(Vector3::new(t, t, z0), Vector3::new(w - t, s0, top)));
            parts.push(cuboid(Vector3::new(t, s1, z0), Vector3::new(w - t, l - t, top)));
        }
        union_all(parts)
    }

    pub fn roof(&self) -> Solid {
        let h = self.height();
        cuboid(Vector3::new(-150.0, -150.0, h), Vector3::new(self.depth + 150.0, self.length + 150.0, h + self.roof_t))
    }

    fn panels(&self, glazed: bool, pane: f64) -> Solid {
        let mid = self.ext_t / 2.0;
        let parts = self.openings.iter().filter(|o| o.glazed == glazed).map(|o| {
            let (z0, z1) = (o.sill, o.sill + o.height);
            let (a0, a1) = (o.along - o.width / 2.0, o.along + o.width / 2.0);
            match o.face {
                Face::Front => cuboid(Vector3::new(mid - pane / 2.0, a0, z0), Vector3::new(mid + pane / 2.0, a1, z1)),
                Face::Back => cuboid(Vector3::new(self.depth - mid - pane / 2.0, a0, z0), Vector3::new(self.depth - mid + pane / 2.0, a1, z1)),
                Face::Left => cuboid(Vector3::new(a0, mid - pane / 2.0, z0), Vector3::new(a1, mid + pane / 2.0, z1)),
                Face::Right => cuboid(Vector3::new(a0, self.length - mid - pane / 2.0, z0), Vector3::new(a1, self.length - mid + pane / 2.0, z1)),
            }
        });
        union_all(parts.collect())
    }

    pub fn glass(&self) -> Solid {
        self.panels(true, 20.0)
    }

    pub fn doors(&self) -> Solid {
        self.panels(false, 45.0)
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
}
