//! The first house of the neighbourhood (pass 3): the 24 x 40 ft example house from D1, one storey,
//! 8 ft walls of 2x6 framing, a 6:12 gable roof with 12 in. overhangs, on a slab.
//!
//! Frame: millimetres (cf-design's `mass_properties` assumes mm), x across the 24 ft width, y along
//! the 40 ft length (the ridge runs along y), z up from the top of the slab. The front wall is at
//! x = 0. Walls are measured to their outside faces.
//!
//! Two kinds of numbers come out: the analytic envelope areas the heat model uses (exact, from the
//! dimensions), and CortenForge's own measurements of the same solids (volumes by
//! `mass_properties`), compared in `check` before the areas are trusted.

use cortenforge::cf_design::Solid;
use nalgebra::Vector3;

pub const FT: f64 = 304.8; // mm
/// How far every cutter overshoots the faces it cuts (mm); see `walls`.
const CUT: f64 = 1000.0;

/// An opening in a wall: which wall, its centre along the wall, sill height, width, height.
#[derive(Clone, Copy, Debug)]
pub struct Opening {
    pub wall: Wall,
    pub along: f64,
    pub sill: f64,
    pub width: f64,
    pub height: f64,
    pub glazed: bool,
    pub name: &'static str,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Wall {
    Front, // x = 0, runs along y
    Back,  // x = W
    Left,  // y = 0, runs along x
    Right, // y = L
}

pub struct House {
    pub width: f64,
    pub length: f64,
    pub wall_height: f64,
    pub wall_t: f64,
    pub slab_t: f64,
    pub pitch: f64, // rise per run
    pub overhang: f64,
    pub roof_t: f64,
    pub openings: Vec<Opening>,
}

impl House {
    /// The D1 example: 24 x 40 ft, 8 ft walls, 2x6 wall ~7 in. thick, 6:12 roof, 12 in. overhangs;
    /// 8 windows 3 x 4 ft (sills at 3 ft), a 6 ft sliding patio door, two entry doors 3 ft x 6'8".
    pub fn example() -> Self {
        let win = |wall, along: f64, name| Opening { wall, along, sill: 3.0 * FT, width: 3.0 * FT, height: 4.0 * FT, glazed: true, name };
        let door = |wall, along: f64, name| Opening { wall, along, sill: 0.0, width: 3.0 * FT, height: 80.0 * 25.4, glazed: false, name };
        let (w, l) = (24.0 * FT, 40.0 * FT);
        House {
            width: w,
            length: l,
            wall_height: 8.0 * FT,
            wall_t: 7.0 * 25.4,
            slab_t: 4.0 * 25.4,
            pitch: 6.0 / 12.0,
            overhang: 12.0 * 25.4,
            roof_t: 10.0 * 25.4,
            openings: vec![
                win(Wall::Front, 1500.0, "front window 1"),
                win(Wall::Front, 3500.0, "front window 2"),
                door(Wall::Front, l / 2.0, "front door"),
                win(Wall::Front, l - 3500.0, "front window 3"),
                win(Wall::Front, l - 1500.0, "front window 4"),
                win(Wall::Back, 1500.0, "back window 1"),
                Opening { wall: Wall::Back, along: 4500.0, sill: 0.0, width: 6.0 * FT, height: 80.0 * 25.4, glazed: true, name: "patio door" },
                door(Wall::Back, l - 3500.0, "back door"),
                win(Wall::Back, l - 1500.0, "back window 2"),
                win(Wall::Left, w / 2.0, "end window 1"),
                win(Wall::Right, w / 2.0, "end window 2"),
            ],
        }
    }

    fn cuboid(lo: Vector3<f64>, hi: Vector3<f64>) -> Solid {
        Solid::cuboid((hi - lo) / 2.0).translate((hi + lo) / 2.0)
    }

    /// The box an opening cuts through its wall (a little deeper than the wall).
    fn opening_box(&self, o: &Opening) -> Solid {
        let (t, e) = (self.wall_t, CUT);
        let (z0, z1) = (o.sill, o.sill + o.height);
        let (a0, a1) = (o.along - o.width / 2.0, o.along + o.width / 2.0);
        match o.wall {
            Wall::Front => Self::cuboid(Vector3::new(-e, a0, z0), Vector3::new(t + e, a1, z1)),
            Wall::Back => Self::cuboid(Vector3::new(self.width - t - e, a0, z0), Vector3::new(self.width + e, a1, z1)),
            Wall::Left => Self::cuboid(Vector3::new(a0, -e, z0), Vector3::new(a1, t + e, z1)),
            Wall::Right => Self::cuboid(Vector3::new(a0, self.length - t - e, z0), Vector3::new(a1, self.length + e, z1)),
        }
    }

    pub fn slab(&self) -> Solid {
        Self::cuboid(Vector3::new(0.0, 0.0, -self.slab_t), Vector3::new(self.width, self.length, 0.0))
    }

    /// The four walls up to the top plate, with the openings cut out.
    pub fn walls(&self) -> Solid {
        let (w, l, h, t) = (self.width, self.length, self.wall_height, self.wall_t);
        let outer = Self::cuboid(Vector3::new(0.0, 0.0, 0.0), Vector3::new(w, l, h));
        // The cutter overshoots by a metre: with a near-flush cutter, max(a, -b) reads ~0 inside
        // the cut and mass_properties' partial-cell weighting counts empty room (CORTENFORGE.md).
        let inner = Self::cuboid(Vector3::new(t, t, -CUT), Vector3::new(w - t, l - t, h + CUT));
        let mut s = outer.subtract(inner);
        for o in &self.openings {
            s = s.subtract(self.opening_box(o));
        }
        s
    }

    /// The conditioned space: inside the walls, slab to ceiling.
    pub fn interior(&self) -> Solid {
        let (w, l, h, t) = (self.width, self.length, self.wall_height, self.wall_t);
        Self::cuboid(Vector3::new(t, t, 0.0), Vector3::new(w - t, l - t, h))
    }

    /// Height of the roof's top surface at x, measured on the outside wall line.
    fn roof_top_planes(&self, drop: f64) -> Solid {
        // Below z = h + pitch x (+ the eave lift) and below z = h + pitch (w - x): two half-spaces
        // with normals (-pitch, 0, 1) and (pitch, 0, 1). The sheathing meets the wall's outer face
        // at the top plate plus the roof thickness (a raised heel).
        let (w, h, p) = (self.width, self.wall_height + self.roof_t - drop, self.pitch);
        Solid::plane(Vector3::new(-p, 0.0, 1.0), h).intersect(Solid::plane(Vector3::new(p, 0.0, 1.0), h + p * w))
    }

    /// The roof: a slab of `roof_t` (measured vertically) following both slopes, out to the
    /// overhangs.
    pub fn roof(&self) -> Solid {
        let (w, l, oh, h) = (self.width, self.length, self.overhang, self.wall_height);
        let ridge = h + self.roof_t + self.pitch * w / 2.0;
        let bounds = Self::cuboid(Vector3::new(-oh, -oh, h - 10.0), Vector3::new(w + oh, l + oh, ridge + 10.0));
        self.roof_top_planes(0.0).intersect(bounds).subtract(self.roof_top_planes(self.roof_t))
    }

    /// The gable ends: wall triangles from the top plate up to the underside of the roof.
    pub fn gables(&self) -> Solid {
        let (w, l, h, t) = (self.width, self.length, self.wall_height, self.wall_t);
        let top = h + self.roof_t + self.pitch * w / 2.0;
        let ends = Self::cuboid(Vector3::new(0.0, 0.0, h), Vector3::new(w, t, top))
            .union(Self::cuboid(Vector3::new(0.0, l - t, h), Vector3::new(w, l, top)));
        ends.intersect(self.roof_top_planes(self.roof_t))
    }

    /// Thin panes standing in each glazed opening (for the drawing only).
    pub fn glass(&self) -> Solid {
        self.panels(true, 20.0)
    }

    /// Door leaves in the opaque openings (for the drawing only).
    pub fn doors(&self) -> Solid {
        self.panels(false, 45.0)
    }

    fn panels(&self, glazed: bool, pane: f64) -> Solid {
        let mut out: Option<Solid> = None;
        for o in self.openings.iter().filter(|o| o.glazed == glazed) {
            let (z0, z1) = (o.sill, o.sill + o.height);
            let (a0, a1) = (o.along - o.width / 2.0, o.along + o.width / 2.0);
            let mid = self.wall_t / 2.0;
            let b = match o.wall {
                Wall::Front => Self::cuboid(Vector3::new(mid - pane / 2.0, a0, z0), Vector3::new(mid + pane / 2.0, a1, z1)),
                Wall::Back => Self::cuboid(Vector3::new(self.width - mid - pane / 2.0, a0, z0), Vector3::new(self.width - mid + pane / 2.0, a1, z1)),
                Wall::Left => Self::cuboid(Vector3::new(a0, mid - pane / 2.0, z0), Vector3::new(a1, mid + pane / 2.0, z1)),
                Wall::Right => Self::cuboid(Vector3::new(a0, self.length - mid - pane / 2.0, z0), Vector3::new(a1, self.length - mid + pane / 2.0, z1)),
            };
            out = Some(match out { Some(s) => s.union(b), None => b });
        }
        out.expect("the house has openings of both kinds")
    }

    // ---- Analytic envelope (m, m2, m3): what the heat model uses ----

    pub fn glazed_area_m2(&self) -> f64 {
        self.openings.iter().filter(|o| o.glazed).map(|o| o.width * o.height).sum::<f64>() / 1e6
    }

    pub fn door_area_m2(&self) -> f64 {
        self.openings.iter().filter(|o| !o.glazed).map(|o| o.width * o.height).sum::<f64>() / 1e6
    }

    /// Above-grade wall area to the outside faces, slab to top plate.
    pub fn wall_gross_m2(&self) -> f64 {
        2.0 * (self.width + self.length) * self.wall_height / 1e6
    }

    pub fn wall_net_m2(&self) -> f64 {
        self.wall_gross_m2() - self.glazed_area_m2() - self.door_area_m2()
    }

    /// The insulated ceiling under the attic, taken at the outside footprint (conservative).
    pub fn ceiling_m2(&self) -> f64 {
        self.width * self.length / 1e6
    }

    pub fn floor_m2(&self) -> f64 {
        (self.width - 2.0 * self.wall_t) * (self.length - 2.0 * self.wall_t) / 1e6
    }

    pub fn slab_perimeter_m(&self) -> f64 {
        2.0 * (self.width + self.length) / 1e3
    }

    pub fn interior_volume_m3(&self) -> f64 {
        self.floor_m2() * self.wall_height / 1e3
    }

    /// Wall material volume (m3): the shell minus openings, slab to top plate.
    pub fn wall_volume_m3(&self) -> f64 {
        let (w, l, h, t) = (self.width, self.length, self.wall_height, self.wall_t);
        let shell = (w * l - (w - 2.0 * t) * (l - 2.0 * t)) * h;
        let cut: f64 = self.openings.iter().map(|o| o.width * o.height * t).sum();
        (shell - cut) / 1e9
    }
}
