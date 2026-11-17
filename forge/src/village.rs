//! Pass 3e: the neighbourhood at the campus edge (D11), drawn into the campus scene.
//!
//! From out/pass3/village.json (`brownfield village`): phase 1's townhouses over their garages,
//! either side of a public spine street from the town to the square; the square with the food hall
//! and its market-garden glasshouse; the community center (ice rink, roller hockey floor, a two-court
//! gym, the makerspace) under one roof; two heated grass fields. Townhouses are drawn as plain
//! massing (Jon hasn't chosen their look); `facade_study` renders three looks side by side.
//!
//! Frame as garden.rs: metres in the code, millimetres in the meshes; x east, y south, z up; the
//! ground south of y = 20 is at -2.2.

use std::path::Path;

use cortenforge::mesh::types::IndexedMesh;
use nalgebra::{Point3, Vector3};

use crate::food::{quad, tri};
use crate::garden::{M, Rng, b, stone_mass_s, STONE};
use crate::scene::{self, Camera, Light, SLayer};

type V = Vector3<f64>;
const Z: f64 = -2.2; // the lower ground

pub struct Home {
    pub x: f64,
    pub y: f64,
    pub facing: f64,
}

pub struct Spec {
    pub house_w: f64,
    pub house_d: f64,
    pub storeys: usize,
    pub storey_m: f64,
    pub garage_h: f64,
    pub homes: Vec<Home>,
    pub streets_y: Vec<f64>,
    pub greens: Vec<[f64; 4]>,
    pub street_w: f64,
    pub street_x: (f64, f64),
    pub spine_x: f64,
    pub spine_w: f64,
    pub spine_y: (f64, f64),
    pub square: [f64; 4],
    pub food_hall: [f64; 4],
    pub market_garden: [f64; 4],
    pub center: [f64; 4],
    pub fields: Vec<(f64, f64, f64, f64)>, // cx, cy, width, length
}

pub fn spec(root: &Path) -> Option<Spec> {
    let text = std::fs::read_to_string(root.join("out/pass3/village.json")).ok()?;
    let j: serde_json::Value = serde_json::from_str(&text).ok()?;
    let v = &j["village"];
    let f = |k: &str| v[k].as_f64().unwrap_or(0.0);
    let r4 = |k: &str| [0, 1, 2, 3].map(|i| v[k][i].as_f64().unwrap_or(0.0));
    let pair = |k: &str| (v[k][0].as_f64().unwrap_or(0.0), v[k][1].as_f64().unwrap_or(0.0));
    Some(Spec {
        house_w: f("house_w"), house_d: f("house_d"), storeys: v["storeys"].as_u64().unwrap_or(2) as usize, storey_m: f("storey_m"),
        garage_h: f("garage_h"),
        homes: v["homes"].as_array()?.iter().map(|h| Home { x: h["x"].as_f64().unwrap_or(0.0), y: h["y"].as_f64().unwrap_or(0.0),
            facing: h["facing"].as_f64().unwrap_or(1.0) }).collect(),
        streets_y: v["streets_y"].as_array()?.iter().filter_map(|y| y.as_f64()).collect(),
        greens: v["greens"].as_array().map(|a| a.iter().map(|g| [0, 1, 2, 3].map(|i| g[i].as_f64().unwrap_or(0.0))).collect()).unwrap_or_default(),
        street_w: f("street_w"), street_x: pair("street_x"), spine_x: f("spine_x"), spine_w: f("spine_w"), spine_y: pair("spine_y"),
        square: r4("square"), food_hall: r4("food_hall"), market_garden: r4("market_garden"), center: r4("center"),
        fields: v["fields"].as_array()?.iter().map(|q| (q["cx"].as_f64().unwrap_or(0.0), q["cy"].as_f64().unwrap_or(0.0),
            q["w"].as_f64().unwrap_or(60.0), q["l"].as_f64().unwrap_or(100.0))).collect(),
    })
}

#[derive(Default)]
pub struct Village {
    pub base: IndexedMesh,
    pub body: IndexedMesh,
    /// The site's houses in five muted tones (the look is still Jon's to choose).
    pub tones: [IndexedMesh; 5],
    pub trim: IndexedMesh,
    pub windows: IndexedMesh,
    pub doors: IndexedMesh,
    pub paving: IndexedMesh,
    pub plaza: IndexedMesh,
    pub glass: IndexedMesh,
    pub frame: IndexedMesh,
    pub courts: IndexedMesh,
    pub roller: IndexedMesh,
    pub ice: IndexedMesh,
    pub grass: IndexedMesh,
    pub lines: IndexedMesh,
    pub greens: IndexedMesh,
    /// Native planting in three tones (grasses, goldenrod, coneflower), rain gardens, green roofs,
    /// roof decks, raised kitchen beds, street pavers.
    pub meadow: [IndexedMesh; 3],
    /// The modelled planting: grass blades, stems, petals (purple coneflower, yellow black-eyed
    /// Susan, goldenrod plumes) and the flowers' dark centres.
    pub blades: IndexedMesh,
    pub stems: IndexedMesh,
    pub purple: IndexedMesh,
    pub yellow: IndexedMesh,
    pub centres: IndexedMesh,
    pub sward: IndexedMesh,
    /// The bouldering walls, their holds in four colours, and the crash pads.
    pub climb: IndexedMesh,
    pub holds: [IndexedMesh; 4],
    pub pads: IndexedMesh,
    /// Clipped inkberry hedges, shrubs, smooth hydrangea's white heads, and the small native trees
    /// (serviceberry, redbud, dogwood) along the walks.
    pub hedge: IndexedMesh,
    pub shrub: IndexedMesh,
    pub white: IndexedMesh,
    pub small_trunks: IndexedMesh,
    pub small: [IndexedMesh; 3],
    pub rain: IndexedMesh,
    pub sedum: IndexedMesh,
    pub deck: IndexedMesh,
    pub beds: IndexedMesh,
    pub pavers: IndexedMesh,
    /// Footprints (x0, x1, y0, y1) the trees keep their distance from.
    pub rects: Vec<(f64, f64, f64, f64)>,
}

/// One townhouse: a garage storey, `storeys` above, a bay on the street side of each upper storey,
/// a garage door and a front door on the street, windows at the back, a cornice. `facing` +1: the
/// street is to the south (+y).
pub fn townhouse(v: &mut Village, x: f64, y: f64, facing: f64, w: f64, d: f64, storeys: usize, sh: f64, gh: f64, tone: Option<usize>) {
    let (x0, x1) = (x - w / 2.0, x + w / 2.0);
    // The house stands 4 m back from its lot's street edge (lot 24 m deep).
    let front = y + facing * 8.0;
    let back = front - facing * d;
    let (y0, y1) = (front.min(back), front.max(back));
    let top = Z + gh + sh * storeys as f64;
    b(&mut v.base, [x0, y0, Z], [x1, y1, Z + gh]);
    let body = match tone { Some(t) => &mut v.tones[t % 5], None => &mut v.body };
    b(body, [x0, y0, Z + gh], [x1, y1, top]);
    b(&mut v.trim, [x0 - 0.15, y0 - 0.15, top], [x1 + 0.15, y1 + 0.15, top + 0.35]);
    let out = |t: f64| front + facing * t;
    // The lane face: the garage door and plain windows. The green face (the front): the front door
    // and a bay on each storey above (Radburn: living rooms to the green, cars to the lane).
    let (gx0, gx1) = (x0 + 0.5, x0 + 0.5 + 4.9);
    let (ya, yb) = (out(0.0).min(out(0.04)), out(0.0).max(out(0.04)));
    b(&mut v.doors, [gx0, ya, Z], [gx1.min(x1 - 0.1), yb, Z + 2.13]);
    let inward = |t: f64| back - facing * t; // out from the green face
    let (da, db) = (inward(0.0).min(inward(0.05)), inward(0.0).max(inward(0.05)));
    b(&mut v.doors, [x1 - 1.6, da, Z], [x1 - 0.6, db, Z + 2.2]);
    for k in 0..storeys {
        let z0 = Z + gh + sh * k as f64;
        let (wy0, wy1) = (out(0.0).min(out(0.04)), out(0.0).max(out(0.04)));
        b(&mut v.windows, [x0 + 1.2, wy0, z0 + 0.9], [x1 - 1.2, wy1, z0 + sh - 0.8]);
        let out = inward;
        let (by0, by1) = (out(0.0).min(out(0.6)), out(0.0).max(out(0.6)));
        let body = match tone { Some(t) => &mut v.tones[t % 5], None => &mut v.body };
        b(body, [x0 + 0.8, by0, z0 + 0.5], [x1 - 0.8, by1, z0 + sh - 0.3]);
        let (wy0, wy1) = (out(0.6).min(out(0.64)), out(0.6).max(out(0.64)));
        b(&mut v.windows, [x0 + 1.2, wy0, z0 + 0.9], [x1 - 1.2, wy1, z0 + sh - 0.6]);
        b(&mut v.trim, [x0 + 0.7, by0.min(wy0) - 0.05, z0 + sh - 0.35], [x1 - 0.7, by1.max(wy1) + 0.05, z0 + sh - 0.25]);
    }
}

/// A low-poly ball (lat-long, 8 x 5), squashed vertically by `sz`.
fn blob(out: &mut IndexedMesh, c: [f64; 3], r: f64, sz: f64) {
    let (nu, nv) = (14, 8);
    let pt = |i: usize, j: usize| {
        let u = i as f64 / nu as f64 * std::f64::consts::TAU;
        let v = j as f64 / nv as f64 * std::f64::consts::PI;
        [c[0] + r * v.sin() * u.cos(), c[1] + r * v.sin() * u.sin(), c[2] + r * sz * v.cos()]
    };
    for i in 0..nu {
        for j in 0..nv {
            let (a, b_, cc, d) = (pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1));
            quad(out, a, d, cc, b_);
        }
    }
}

/// A small tree: a trunk and a rounded crown of a few balls.
fn small_tree(v: &mut Village, rng: &mut Rng, x: f64, y: f64, h: f64) {
    let k = (rng.next() * 3.0) as usize % 3;
    b(&mut v.small_trunks, [x - 0.1, y - 0.1, Z], [x + 0.1, y + 0.1, Z + h * 0.55]);
    let (cr, cz) = (h * 0.28, Z + h * 0.68);
    for _ in 0..7 {
        let (dx, dy, dz) = (rng.range(-0.6, 0.6) * cr, rng.range(-0.6, 0.6) * cr, rng.range(-0.4, 0.5) * cr);
        blob(&mut v.small[k], [x + dx, y + dy, cz + dz], cr * rng.range(0.45, 0.7), 0.85);
    }
}

/// A shrub mound, with smooth hydrangea's white heads on some.
fn shrub(v: &mut Village, rng: &mut Rng, x: f64, y: f64) {
    let r = rng.range(0.4, 0.7);
    blob(&mut v.shrub, [x, y, Z + r * 0.5], r, 0.8);
    if rng.next() < 0.6 {
        for _ in 0..5 {
            let a = rng.range(0.0, std::f64::consts::TAU);
            blob(&mut v.white, [x + 0.6 * r * a.cos(), y + 0.6 * r * a.sin(), Z + r * 1.05], r * 0.22, 0.8);
        }
    }
}

/// A clump of grass: blades leaning out from a point, each a thin triangle.
fn grass(v: &mut Village, rng: &mut Rng, x: f64, y: f64) {
    let n = 7 + (rng.next() * 6.0) as usize;
    let h0 = rng.range(0.35, 0.7);
    for _ in 0..n {
        let a = rng.range(0.0, std::f64::consts::TAU);
        let lean = rng.range(0.05, 0.25);
        let h = h0 * rng.range(0.7, 1.1);
        let (dx, dy) = (a.cos(), a.sin());
        let (wx, wy) = (-dy * 0.015, dx * 0.015);
        tri(&mut v.blades, [x - wx, y - wy, Z], [x + wx, y + wy, Z], [x + dx * lean, y + dy * lean, Z + h]);
    }
}

/// A flower on a stem: `kind` 0 coneflower (purple petals drooping round a dark cone), 1 black-eyed
/// Susan (yellow petals, dark centre), 2 goldenrod (a yellow plume).
fn flower(v: &mut Village, rng: &mut Rng, x: f64, y: f64, kind: usize) {
    let h = rng.range(0.55, 0.95);
    let (sx, sy) = (x + rng.range(-0.05, 0.05), y + rng.range(-0.05, 0.05));
    tri(&mut v.stems, [x - 0.008, y, Z], [x + 0.008, y, Z], [sx, sy, Z + h]);
    tri(&mut v.stems, [x, y - 0.008, Z], [x, y + 0.008, Z], [sx, sy, Z + h]);
    if kind == 2 {
        // A plume: small yellow triangles along an arching tip.
        for k in 0..8 {
            let t = k as f64 / 8.0;
            let (px, py, pz) = (sx + t * 0.12, sy, Z + h - 0.25 + t * 0.25);
            let r = 0.05 * (1.0 - t * 0.6);
            for j in 0..3 {
                let a = j as f64 * 2.1 + t;
                tri(&mut v.yellow, [px, py, pz], [px + r * a.cos(), py + r * a.sin(), pz + 0.03], [px + r * (a + 0.8).cos(), py + r * (a + 0.8).sin(), pz - 0.02]);
            }
        }
        return;
    }
    let petals = if kind == 0 { &mut v.purple } else { &mut v.yellow };
    let (r, droop) = if kind == 0 { (0.06, 0.03) } else { (0.045, 0.005) };
    let z = Z + h;
    for k in 0..12 {
        let a = k as f64 * std::f64::consts::TAU / 12.0;
        let b = a + 0.22;
        tri(petals, [sx, sy, z], [sx + r * a.cos(), sy + r * a.sin(), z - droop], [sx + r * b.cos(), sy + r * b.sin(), z - droop]);
    }
    let c = if kind == 0 { 0.02 } else { 0.014 };
    for k in 0..6 {
        let a = k as f64 * std::f64::consts::TAU / 6.0;
        let b = a + std::f64::consts::TAU / 6.0;
        tri(&mut v.centres, [sx, sy, z + c * 1.4], [sx + c * a.cos(), sy + c * a.sin(), z + 0.005], [sx + c * b.cos(), sy + c * b.sin(), z + 0.005]);
    }
}

/// Native planting over a rectangle (no lawn): a soil-and-litter base, clumps of grass, and
/// flowers among them, mostly coneflower and black-eyed Susan, goldenrod in drifts.
fn meadow(v: &mut Village, rng: &mut Rng, x0: f64, x1: f64, y0: f64, y1: f64) {
    b(&mut v.meadow[0], [x0, y0, Z], [x1, y1, Z + 0.04]);
    let area = (x1 - x0).max(0.0) * (y1 - y0).max(0.0);
    for _ in 0..((area / 0.22) as usize).max(1) {
        let (gx, gy) = (rng.range(x0 + 0.1, x1 - 0.1), rng.range(y0 + 0.1, y1 - 0.1));
        grass(v, rng, gx, gy);
    }
    for _ in 0..((area / 0.3) as usize) {
        let u = rng.next();
        let kind = if u < 0.45 { 0 } else if u < 0.8 { 1 } else { 2 };
        let (fx, fy) = (rng.range(x0 + 0.1, x1 - 0.1), rng.range(y0 + 0.1, y1 - 0.1));
        flower(v, rng, fx, fy, kind);
    }
}

/// A townhouse's lot: a paved drive to the garage and a path to the door, native planting and a rain
/// garden in front, planting and raised kitchen beds behind, the side strip planted, and on the roof
/// a green (sedum) roof with a deck at the back.
pub fn lot(v: &mut Village, rng: &mut Rng, x: f64, y: f64, facing: f64, w: f64, gap: f64, d: f64, top: f64) {
    let (x0, x1) = (x - w / 2.0, x + w / 2.0);
    let front = y + facing * 8.0;
    let street = y + facing * 12.0;
    let back = front - facing * d;
    let lot_back = y - facing * 12.0;
    let (fa, fb) = (front.min(street), front.max(street));
    let (ba, bb) = (back.min(lot_back), back.max(lot_back));
    // The drive and the path.
    b(&mut v.pavers, [x0 + 0.4, fa, Z], [x0 + 5.6, fb, Z + 0.04]);
    b(&mut v.pavers, [x1 - 1.1, fa, Z], [x1 - 0.1, fb, Z + 0.04]);
    meadow(v, rng, x0 + 5.7, x1 - 1.2, fa + 0.2, fb - 0.2);
    // A rain garden by the corner downspout, in the front strip.
    let ry = if facing > 0.0 { fa + 0.3 } else { fb - 1.5 };
    b(&mut v.rain, [x1 - 1.1, ry, Z - 0.15], [x1 - 0.1, ry + 1.2, Z + 0.02]);
    // The front garden, on the green: a path from the door to the green's walk, a clipped inkberry hedge
    // along the lot line, shrubs and smooth hydrangea, one small native tree (low water demand, ~7 m
    // from the house: within the root rule for a ~9 m tree), native planting, one raised bed.
    let (pa, pb) = (back.min(lot_back), back.max(lot_back));
    b(&mut v.pavers, [x1 - 1.6, pa, Z], [x1 - 0.6, pb, Z + 0.04]);
    let edge = lot_back + facing * 0.6;
    let (ha, hb) = (lot_back.min(edge), lot_back.max(edge));
    b(&mut v.hedge, [x0, ha, Z], [x1 - 1.7, hb, Z + 0.9]);
    meadow(v, rng, x0 + 0.2, x1 - 1.8, ba + 1.0, bb - 1.0);
    for k in 0..3 {
        let sy = back - facing * (1.2 + 2.4 * k as f64);
        let sx = x0 + rng.range(0.7, 1.4);
        shrub(v, rng, sx, sy);
    }
    let th = rng.range(7.0, 9.0);
    small_tree(v, rng, x0 + 2.6, back - facing * 7.0, th);
    let yb = back - facing * 3.6;
    let (ya, yz) = (yb.min(yb - facing * 1.2), yb.max(yb - facing * 1.2));
    b(&mut v.beds, [x0 + 2.0, ya, Z], [x1 - 2.0, yz, Z + 0.45]);
    b(&mut v.greens, [x0 + 2.1, ya + 0.1, Z + 0.45], [x1 - 2.1, yz - 0.1, Z + 0.7]);
    // The side strip (half the gap is this lot's).
    if gap > 1.0 {
        meadow(v, rng, x1 + 0.2, x1 + gap / 2.0, fa.min(ba), fb.max(bb));
    }
    // The roof: sedum over most of it, a deck at the back.
    let (ra, rb) = (front.min(back), front.max(back));
    let deck_at = back + facing * 3.5;
    let (da, db) = (back.min(deck_at), back.max(deck_at));
    b(&mut v.sedum, [x0 + 0.3, ra + 0.3, top + 0.35], [x1 - 0.3, rb - 0.3, top + 0.5]);
    b(&mut v.deck, [x0 + 0.3, da + 0.3, top + 0.35], [x1 - 0.3, db, top + 0.55]);
}

/// A small glasshouse: ridges east-west on 4 m bays over the rectangle, a low base, the crop inside.
fn glasshouse(v: &mut Village, r: [f64; 4]) {
    let [x0, x1, y0, y1] = r;
    let (g, rise) = (Z + 4.5, 2.0 * 22f64.to_radians().tan());
    for (a, c) in [([x0, y0], [x1, y0]), ([x1, y1], [x0, y1]), ([x0, y1], [x0, y0]), ([x1, y0], [x1, y1])] {
        quad(&mut v.glass, [a[0], a[1], Z + 0.6], [c[0], c[1], Z + 0.6], [c[0], c[1], g], [a[0], a[1], g]);
    }
    b(&mut v.base, [x0, y0, Z], [x1, y0 + 0.3, Z + 0.6]);
    b(&mut v.base, [x0, y1 - 0.3, Z], [x1, y1, Z + 0.6]);
    let mut y = y0;
    while y < y1 - 0.1 {
        let (ym, yb) = (y + 2.0, (y + 4.0).min(y1));
        quad(&mut v.glass, [x0, y, g], [x1, y, g], [x1, ym, g + rise], [x0, ym, g + rise]);
        quad(&mut v.glass, [x0, ym, g + rise], [x1, ym, g + rise], [x1, yb, g], [x0, yb, g]);
        tri(&mut v.glass, [x0, y, g], [x0, ym, g + rise], [x0, yb, g]);
        tri(&mut v.glass, [x1, y, g], [x1, yb, g], [x1, ym, g + rise]);
        b(&mut v.frame, [x0, y - 0.05, g - 0.12], [x1, y + 0.05, g]);
        b(&mut v.greens, [x0 + 1.0, y + 0.6, Z + 0.8], [x1 - 1.0, y + 1.6, Z + 1.0]);
        b(&mut v.greens, [x0 + 1.0, y + 2.4, Z + 0.8], [x1 - 1.0, y + 3.4, Z + 1.0]);
        y += 4.0;
    }
}

pub fn build(s: &Spec, stone: &mut [IndexedMesh; 5], concrete: &mut IndexedMesh, rng: &mut Rng) -> (Village, usize) {
    let mut v = Village::default();
    let mut n = 0;
    let gap = 3.0_f64.min((s.homes.get(1).map(|h| (h.x - s.homes[0].x).abs()).unwrap_or(9.1) - s.house_w).max(0.0));
    for h in &s.homes {
        // Rows beyond ~245 m from the hall may go a storey higher (the noise check); each house steps a
        // little in or out of line.
        let storeys = if h.y > 245.0 { s.storeys + 1 } else { s.storeys };
        let shift = rng.range(-0.8, 0.8);
        let y = h.y + shift * h.facing;
        let tone = (rng.next() * 5.0) as usize;
        townhouse(&mut v, h.x, y, h.facing, s.house_w, s.house_d, storeys, s.storey_m, s.garage_h, Some(tone));
        let (fr, bk) = (y + h.facing * 8.0, y + h.facing * 8.0 - h.facing * s.house_d);
        v.rects.push((h.x - s.house_w / 2.0, h.x + s.house_w / 2.0, fr.min(bk), fr.max(bk)));
        let top = Z + s.garage_h + s.storey_m * storeys as f64;
        lot(&mut v, rng, h.x, y, h.facing, s.house_w, gap, s.house_d, top);
    }
    let xs: Vec<f64> = s.homes.iter().map(|h| h.x).collect();
    let ys: Vec<f64> = s.homes.iter().map(|h| h.y).collect();
    let (hx0, hx1) = (xs.iter().cloned().fold(f64::MAX, f64::min) - 4.0, xs.iter().cloned().fold(f64::MIN, f64::max) + 4.0);
    let (hy0, hy1) = (ys.iter().cloned().fold(f64::MAX, f64::min) - 12.0, ys.iter().cloned().fold(f64::MIN, f64::max) + 12.0);
    let _ = (hx0, hx1, hy0, hy1);
    // Streets, the spine from the town toward the square, the square (the site plan's walks join them up).
    // Living streets: a 5.5 m paved lane down the middle, planted swales for the rain either side, and
    // walks; the spine the same, wider.
    for &y in &s.streets_y {
        let (x0, x1, hw) = (s.street_x.0, s.street_x.1, s.street_w / 2.0);
        b(&mut v.pavers, [x0, y - 2.75, Z], [x1, y + 2.75, Z + 0.03]);
        for side in [-1.0, 1.0] {
            let (a, c) = (y + side * 2.75, y + side * 5.25);
            meadow(&mut v, rng, x0, x1, a.min(c), a.max(c));
            let (wa, wc) = (y + side * 5.25, y + side * hw);
            b(&mut v.plaza, [x0, wa.min(wc), Z], [x1, wa.max(wc), Z + 0.03]);
        }
    }
    for g in &s.greens {
        let [x0, x1, y0, y1] = *g;
        b(&mut v.sward, [x0, y0, Z], [x1, y1, Z + 0.03]);
        for (wy, dir) in [(y0, 1.0), (y1, -1.0)] {
            let (a, c) = (wy, wy + dir * 2.4);
            b(&mut v.plaza, [x0, a.min(c), Z], [x1, a.max(c), Z + 0.05]); // the walk past the front gardens
            let (pa, pc) = (wy + dir * 2.4, wy + dir * 5.4);
            meadow(&mut v, rng, x0, x1, pa.min(pc), pa.max(pc));
            let mut x = x0 + 4.0;
            while x < x1 - 2.0 {
                let ty = wy + dir * 3.9;
                let th = rng.range(7.0, 9.0);
                if rng.next() < 0.5 { small_tree(&mut v, rng, x, ty, th); } else { shrub(&mut v, rng, x, ty); }
                x += rng.range(6.0, 9.0);
            }
        }
    }
    let (sx, sw) = (s.spine_x, s.spine_w / 2.0);
    b(&mut v.pavers, [sx - 3.5, s.spine_y.0, Z], [sx + 3.5, s.spine_y.1, Z + 0.03]);
    for side in [-1.0, 1.0] {
        let (a, c) = (sx + side * 3.5, sx + side * (sw - 3.0));
        meadow(&mut v, rng, a.min(c), a.max(c), s.spine_y.0, s.spine_y.1);
        let (wa, wc) = (sx + side * (sw - 3.0), sx + side * sw);
        b(&mut v.plaza, [wa.min(wc), s.spine_y.0, Z], [wa.max(wc), s.spine_y.1, Z + 0.03]);
    }
    let [sx0, sx1, sy0, sy1] = s.square;
    b(&mut v.plaza, [sx0, sy0, Z], [sx1, sy1, Z + 0.04]);
    // The food hall on the square's north side: stone ends, glass to the square, a deep ochre roof.
    let [fx0, fx1, fy0, fy1] = s.food_hall;
    if fx1 > fx0 {
    n += stone_mass_s(stone, rng, [fx0, fy0, Z], [fx0 + 4.0, fy1, Z + 5.0], [true, false, true, true], 1.2);
    n += stone_mass_s(stone, rng, [fx1 - 4.0, fy0, Z], [fx1, fy1, Z + 5.0], [false, true, true, true], 1.2);
    n += stone_mass_s(stone, rng, [fx0 + 4.0, fy0, Z], [fx1 - 4.0, fy0 + 0.6, Z + 5.0], [false, false, true, false], 1.2);
    b(&mut v.glass, [fx0 + 4.0, fy1 - 0.04, Z + 0.2], [fx1 - 4.0, fy1, Z + 4.8]);
    let mut x = fx0 + 6.0;
    while x < fx1 - 4.5 {
        b(&mut v.frame, [x - 0.05, fy1 - 0.08, Z + 0.2], [x + 0.05, fy1 + 0.02, Z + 4.8]);
        x += 2.0;
    }
    b(concrete, [fx0 - 1.5, fy0 - 1.0, Z + 5.0], [fx1 + 1.5, fy1 + 4.0, Z + 5.5]);
    v.rects.push((fx0, fx1, fy0, fy1));
    }
    if s.market_garden[1] > s.market_garden[0] {
        glasshouse(&mut v, s.market_garden);
        v.rects.push((s.market_garden[0], s.market_garden[1], s.market_garden[2], s.market_garden[3]));
    }
    // The community center: a stone base, a glass band, an ochre roof; inside, the ice, the roller
    // hockey floor and two courts.
    let [cx0, cx1, cy0, cy1] = s.center;
    let (base_h, eave) = (3.0, 9.0);
    for (lo, hi, f) in [([cx0, cy0, Z], [cx1, cy0 + 0.6, Z + base_h], [false, false, true, false]),
                        ([cx0, cy1 - 0.6, Z], [cx1, cy1, Z + base_h], [false, false, false, true]),
                        ([cx0, cy0, Z], [cx0 + 0.6, cy1, Z + base_h], [true, false, false, false]),
                        ([cx1 - 0.6, cy0, Z], [cx1, cy1, Z + base_h], [false, true, false, false])] {
        n += stone_mass_s(stone, rng, lo, hi, f, 1.4);
    }
    for (a, c) in [([cx0, cy0], [cx1, cy0]), ([cx1, cy1], [cx0, cy1]), ([cx0, cy1], [cx0, cy0]), ([cx1, cy0], [cx1, cy1])] {
        quad(&mut v.glass, [a[0], a[1], Z + base_h], [c[0], c[1], Z + base_h], [c[0], c[1], Z + eave], [a[0], a[1], Z + eave]);
    }
    let mut x = cx0;
    while x <= cx1 + 1e-6 {
        n += stone_mass_s(stone, rng, [x - 0.5, cy1 - 0.9, Z], [x + 0.5, cy1 + 0.1, Z + eave], [true, true, false, true], 1.4);
        x += 9.0;
    }
    b(concrete, [cx0 - 2.5, cy0 - 2.5, Z + eave], [cx1 + 2.5, cy1 + 2.5, Z + eave + 0.7]);
    b(&mut v.plaza, [cx0 + 0.6, cy0 + 0.6, Z], [cx1 - 0.6, cy1 - 0.6, Z + 0.02]); // the floor
    b(&mut v.ice, [cx0 + 8.0, cy0 + 12.0, Z], [cx0 + 34.0, cy0 + 73.0, Z + 0.05]);
    b(&mut v.lines, [cx0 + 8.0, cy0 + 42.3, Z + 0.05], [cx0 + 34.0, cy0 + 42.7, Z + 0.06]);
    for (lo, hi) in [([cx0 + 7.8, cy0 + 11.8], [cx0 + 34.2, cy0 + 12.0]), ([cx0 + 7.8, cy0 + 73.0], [cx0 + 34.2, cy0 + 73.2]),
                     ([cx0 + 7.8, cy0 + 11.8], [cx0 + 8.0, cy0 + 73.2]), ([cx0 + 34.0, cy0 + 11.8], [cx0 + 34.2, cy0 + 73.2])] {
        b(&mut v.trim, [lo[0], lo[1], Z], [hi[0], hi[1], Z + 1.07]); // the boards round the ice
    }
    b(&mut v.roller, [cx0 + 40.0, cy0 + 12.0, Z], [cx0 + 66.0, cy0 + 73.0, Z + 0.05]);
    for k in 0..2 {
        let y = cy0 + 10.0 + k as f64 * 36.0;
        b(&mut v.courts, [cx0 + 71.0, y, Z], [cx0 + 86.0, y + 28.0, Z + 0.05]);
        b(&mut v.lines, [cx0 + 71.0, y + 13.8, Z + 0.05], [cx0 + 86.0, y + 14.2, Z + 0.06]);
    }
    // Bouldering along the north wall: angled panels and overhangs (~4.5 m) with coloured holds over
    // crash pads.
    b(&mut v.pads, [cx0 + 2.0, cy0 + 0.7, Z], [cx0 + 62.0, cy0 + 9.0, Z + 0.35]);
    let mut x = cx0 + 2.0;
    let mut k = 0;
    while x < cx0 + 60.0 {
        let lean = [0.0, 1.2, 2.2, 0.6][k % 4]; // vertical, overhang, roof, slab
        let (w0, w1) = (x, x + 6.0);
        quad(&mut v.climb, [w0, cy0 + 0.8, Z], [w1, cy0 + 0.8, Z], [w1, cy0 + 0.8 + lean, Z + 4.5], [w0, cy0 + 0.8 + lean, Z + 4.5]);
        for _ in 0..40 {
            let (u, h) = (rng.range(0.2, 0.9), rng.range(0.3, 4.3));
            let (hx, hy) = (w0 + 0.3 + u * 5.4, cy0 + 0.85 + lean * h / 4.5);
            let c = (rng.next() * 4.0) as usize % 4;
            b(&mut v.holds[c], [hx - 0.08, hy, Z + h - 0.06], [hx + 0.08, hy + 0.08, Z + h + 0.06]);
        }
        x += 6.0;
        k += 1;
    }
    // The sports lab, facing the ice through glass (skate sharpening, sticks and fitting, 3D printing,
    // electronics, video), and behind a fire wall the heavy shop with its own outside door (west).
    let (ly0, ly1) = (cy0 + 76.0, cy0 + 92.0);
    b(&mut v.plaza, [cx0 + 0.6, ly0, Z], [cx0 + 58.0, ly1, Z + 0.03]);
    b(&mut v.trim, [cx0 + 22.0, ly0, Z], [cx0 + 22.4, ly1, Z + 5.0]); // the fire wall
    b(&mut v.trim, [cx0 + 0.6, ly1 - 0.3, Z], [cx0 + 58.0, ly1, Z + 5.0]); // the back wall
    quad(&mut v.glass, [cx0 + 22.4, ly0, Z], [cx0 + 58.0, ly0, Z], [cx0 + 58.0, ly0, Z + 4.0], [cx0 + 22.4, ly0, Z + 4.0]);
    for k in 0..6 {
        let x = cx0 + 25.0 + k as f64 * 5.5;
        b(&mut v.beds, [x, ly0 + 4.0, Z], [x + 3.6, ly0 + 5.2, Z + 0.95]); // benches
        b(&mut v.trim, [x + 0.4, ly0 + 9.0, Z], [x + 1.4, ly0 + 9.8, Z + 1.3]); // machines
    }
    for k in 0..3 {
        let x = cx0 + 3.0 + k as f64 * 6.0;
        b(&mut v.beds, [x, ly0 + 3.0, Z], [x + 4.0, ly0 + 5.0, Z + 0.9]); // shop benches
    }
    b(&mut v.doors, [cx0 - 0.02, ly0 + 5.0, Z], [cx0 + 0.6, ly0 + 9.0, Z + 3.5]); // the shop's own door
    // A low traverse wall along the gym's east wall.
    quad(&mut v.climb, [cx1 - 1.0, cy0 + 10.0, Z], [cx1 - 1.0, cy0 + 74.0, Z], [cx1 - 1.0, cy0 + 74.0, Z + 2.8], [cx1 - 1.0, cy0 + 10.0, Z + 2.8]);
    for _ in 0..160 {
        let (hy, h) = (rng.range(cy0 + 10.5, cy0 + 73.5), rng.range(0.3, 2.6));
        let c = (rng.next() * 4.0) as usize % 4;
        b(&mut v.holds[c], [cx1 - 1.08, hy - 0.08, Z + h - 0.06], [cx1 - 1.0, hy + 0.08, Z + h + 0.06]);
    }
    for k in 0..8 {
        let x = cx0 + 1.0 + k as f64 * 11.0;
        b(&mut v.roller, [x, cy1 - 32.0, Z], [x + 10.4, cy1 - 12.5, Z + 0.05]);
        b(&mut v.courts, [x + 1.5, cy1 - 29.5, Z + 0.05], [x + 8.9, cy1 - 15.0, Z + 0.06]);
        b(&mut v.lines, [x + 1.5, cy1 - 22.3, Z + 0.06], [x + 8.9, cy1 - 22.1, Z + 0.07]);
    }
    v.rects.push((cx0, cx1, cy0, cy1));
    // Two heated grass fields with their lines and goals.
    for &(fcx, fcy, w, l) in &s.fields {
        let (x0, x1, y0, y1) = (fcx - w / 2.0, fcx + w / 2.0, fcy - l / 2.0, fcy + l / 2.0);
        b(&mut v.grass, [x0 - 3.0, y0 - 3.0, Z], [x1 + 3.0, y1 + 3.0, Z + 0.03]);
        for (lo, hi) in [([x0, y0], [x1, y0 + 0.12]), ([x0, y1 - 0.12], [x1, y1]), ([x0, y0], [x0 + 0.12, y1]), ([x1 - 0.12, y0], [x1, y1]),
                         ([x0, (y0 + y1) / 2.0 - 0.06], [x1, (y0 + y1) / 2.0 + 0.06])] {
            b(&mut v.lines, [lo[0], lo[1], Z + 0.03], [hi[0], hi[1], Z + 0.04]);
        }
        for ye in [y0, y1] {
            b(&mut v.lines, [fcx - 3.7, ye - 0.06, Z], [fcx - 3.6, ye + 0.06, Z + 2.44]);
            b(&mut v.lines, [fcx + 3.6, ye - 0.06, Z], [fcx + 3.7, ye + 0.06, Z + 2.44]);
            b(&mut v.lines, [fcx - 3.7, ye - 0.06, Z + 2.34], [fcx + 3.7, ye + 0.06, Z + 2.44]);
        }
        v.rects.push((x0 - 3.0, x1 + 3.0, y0 - 3.0, y1 + 3.0));
        let (lx0, lx1, ly0, ly1) = (x0 - 20.0, x1 + 20.0, y0 - 20.0, y1 + 20.0);
        for (lo, hi) in [([lx0, ly0], [lx1, ly0 + 3.0]), ([lx0, ly1 - 3.0], [lx1, ly1]), ([lx0, ly0], [lx0 + 3.0, ly1]), ([lx1 - 3.0, ly0], [lx1, ly1])] {
            b(&mut v.plaza, [lo[0], lo[1], Z], [hi[0], hi[1], Z + 0.05]);
        }
    }
    (v, n)
}

/// The neighbourhood's layers for the campus scene (neutral massing for the homes).
pub fn layers<'a>(v: &'a Village, out: &mut Vec<SLayer<'a>>) {
    out.push(SLayer::solid(&v.base, [0.70, 0.67, 0.61]));
    out.push(SLayer::solid(&v.body, [0.88, 0.85, 0.79]));
    for (m, c) in v.tones.iter().zip([[0.90, 0.86, 0.78], [0.86, 0.80, 0.68], [0.76, 0.80, 0.70], [0.86, 0.74, 0.66], [0.76, 0.80, 0.84]]) {
        out.push(SLayer::solid(m, c));
    }
    out.push(SLayer::solid(&v.trim, [0.95, 0.93, 0.88]));
    out.push(SLayer::solid(&v.windows, [0.20, 0.25, 0.29]));
    out.push(SLayer::solid(&v.doors, [0.55, 0.52, 0.47]));
    out.push(SLayer::solid(&v.paving, [0.52, 0.52, 0.52]).no_shadow());
    out.push(SLayer::solid(&v.plaza, [0.80, 0.75, 0.66]).no_shadow());
    out.push(SLayer::solid(&v.frame, [0.84, 0.85, 0.84]));
    out.push(SLayer::solid(&v.courts, [0.74, 0.55, 0.33]).no_shadow());
    out.push(SLayer::solid(&v.roller, [0.30, 0.42, 0.58]).no_shadow());
    out.push(SLayer::solid(&v.ice, [0.93, 0.96, 0.98]).no_shadow());
    out.push(SLayer::solid(&v.grass, [0.33, 0.56, 0.27]).no_shadow());
    out.push(SLayer::solid(&v.lines, [0.97, 0.97, 0.97]));
    out.push(SLayer::solid(&v.greens, [0.36, 0.60, 0.28]));
    out.push(SLayer::solid(&v.meadow[0], [0.33, 0.40, 0.23]).no_shadow()); // low growth and litter under the planting
    out.push(SLayer::solid(&v.sward, [0.42, 0.56, 0.30]).no_shadow());
    out.push(SLayer::solid(&v.climb, [0.62, 0.60, 0.58]));
    for (m, c) in v.holds.iter().zip([[0.85, 0.20, 0.20], [0.20, 0.55, 0.85], [0.95, 0.80, 0.20], [0.30, 0.70, 0.35]]) {
        out.push(SLayer::solid(m, c));
    }
    out.push(SLayer::solid(&v.pads, [0.25, 0.27, 0.32]));
    out.push(SLayer::solid(&v.hedge, [0.20, 0.33, 0.18]));
    out.push(SLayer::solid(&v.shrub, [0.30, 0.45, 0.24]).smooth());
    out.push(SLayer::solid(&v.white, [0.93, 0.94, 0.88]).smooth());
    out.push(SLayer::solid(&v.small_trunks, [0.32, 0.26, 0.22]));
    for (m, c) in v.small.iter().zip([[0.84, 0.42, 0.20], [0.86, 0.72, 0.30], [0.62, 0.20, 0.18]]) {
        out.push(SLayer::solid(m, c).smooth());
    }
    out.push(SLayer::solid(&v.blades, [0.47, 0.58, 0.30]).no_shadow());
    out.push(SLayer::solid(&v.stems, [0.36, 0.46, 0.24]).no_shadow());
    out.push(SLayer::solid(&v.purple, [0.78, 0.48, 0.70]).no_shadow());
    out.push(SLayer::solid(&v.yellow, [0.95, 0.76, 0.18]).no_shadow());
    out.push(SLayer::solid(&v.centres, [0.30, 0.18, 0.10]).no_shadow());
    out.push(SLayer::solid(&v.rain, [0.27, 0.40, 0.30]).no_shadow());
    out.push(SLayer::solid(&v.sedum, [0.50, 0.58, 0.30]));
    out.push(SLayer::solid(&v.deck, [0.62, 0.47, 0.32]));
    out.push(SLayer::solid(&v.beds, [0.50, 0.38, 0.26]));
    out.push(SLayer::solid(&v.pavers, [0.62, 0.58, 0.52]).no_shadow());
}

pub fn glass_layer<'a>(v: &'a Village, out: &mut Vec<SLayer<'a>>) {
    out.push(SLayer::translucent(&v.glass, [0.74, 0.84, 0.88], 0.24));
}

/// Three looks for the townhouses, side by side, five houses each, for Jon to choose from:
/// (1) a sandstone garage storey with painted bays above; (2) San Francisco, painted top to bottom,
/// each house its own colour; (3) the campus's stone with ochre bands. Rendered on its own.
pub fn facade_study(root: &Path, s: &Spec) -> std::io::Result<()> {
    let mut rng = Rng(0xA5A5_1234_5678_9ABC);
    let (w, d, n_st, sh, gh) = (s.house_w, s.house_d, s.storeys, s.storey_m, s.garage_h);
    let lot = w + 3.0;
    let paints = [[0.80, 0.56, 0.45], [0.55, 0.66, 0.70], [0.86, 0.78, 0.55], [0.62, 0.70, 0.56], [0.78, 0.66, 0.74]];
    let mut stone: [IndexedMesh; 5] = Default::default();
    let mut ground = IndexedMesh::new();
    let mut bodies: Vec<(Village, [f64; 3], [f64; 3])> = Vec::new();
    let mut ochre = IndexedMesh::new();
    b(&mut ground, [-400.0, -300.0, Z - 0.6], [500.0, 400.0, Z]);
    for look in 0..3 {
        for k in 0..5 {
            let x = (2 - look) as f64 * (5.0 * lot + 12.0) + (4 - k) as f64 * lot; // seen from the street, look 1 on the left
            let mut v = Village::default();
            townhouse(&mut v, x, 0.0, 1.0, w, d, n_st, sh, gh, None);
            let (x0, x1, front) = (x - w / 2.0, x + w / 2.0, 8.0);
            match look {
                0 => {
                    stone_mass_s(&mut stone, &mut rng, [x0, front - d, Z], [x1, front, Z + gh], [true, true, false, true], 1.0);
                    bodies.push((v, paints[k], [0.95, 0.93, 0.88]));
                }
                1 => bodies.push((v, paints[k], [0.97, 0.96, 0.92])),
                _ => {
                    stone_mass_s(&mut stone, &mut rng, [x0, front - d, Z], [x1, front, Z + gh + sh * n_st as f64], [true, true, false, true], 1.2);
                    for st in 0..n_st {
                        let z = Z + gh + sh * st as f64;
                        b(&mut ochre, [x0 - 0.2, front - 0.2, z - 0.2], [x1 + 0.2, front + 0.9, z + 0.1]);
                    }
                    bodies.push((v, STONE[k % 5], [0.94, 0.85, 0.66]));
                }
            }
        }
    }
    let mut layers: Vec<SLayer> = Vec::new();
    layers.push(SLayer::solid(&ground, [0.44, 0.50, 0.30]).no_shadow());
    for (i, m) in stone.iter().enumerate() {
        layers.push(SLayer::solid(m, STONE[i]));
    }
    layers.push(SLayer::solid(&ochre, [0.94, 0.85, 0.66]));
    for (i, (v, body, trim)) in bodies.iter().enumerate() {
        let look = i / 5;
        if look == 1 {
            layers.push(SLayer::solid(&v.base, *body));
        } else if look == 0 {
            layers.push(SLayer::solid(&v.base, [0.70, 0.62, 0.50])); // hidden under the stone
        }
        if look < 2 {
            layers.push(SLayer::solid(&v.body, *body));
        } else {
            layers.push(SLayer::solid(&v.body, *body));
        }
        layers.push(SLayer::solid(&v.trim, *trim));
        layers.push(SLayer::solid(&v.windows, [0.20, 0.25, 0.29]));
        layers.push(SLayer::solid(&v.doors, [0.45, 0.30, 0.22]));
    }
    let mut light = Light::sun_at(150.0, 32.0);
    light.shadow_px = 4096;
    light.shadow_focus = Some((V::new(-30.0, -20.0, -3.0) * M, V::new(150.0, 30.0, 15.0) * M));
    let p = |x: f64, y: f64, z: f64| Point3::new(x * M, y * M, z * M);
    let cam = Camera::Persp { eye: p(76.0, 80.0, 2.5), target: p(76.0, 0.0, 3.6), up: V::z(), fov_deg: 30.0, w: 2100, h: 700 };
    let path = root.join("out/pass3/renders/village_facades.png");
    std::fs::create_dir_all(path.parent().unwrap())?;
    scene::render_scene(&layers, &cam, &light, 2, &path)?;
    let _ = std::fs::copy(&path, root.join("docs/pass3/village_facades.png"));
    println!("  village_facades.png");
    Ok(())
}
