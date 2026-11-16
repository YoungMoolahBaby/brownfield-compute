//! Architectural renders (pass 3c): a sun in the world, shadows, perspective, glass and water.
//!
//! A second path beside `render.rs` (whose callers stay as they are): a software rasterizer with
//! - a sun fixed in the world frame, Lambert shading plus a sky dome term;
//! - shadows from a shadow map (depth rendered from the sun, 3 x 3 filtered);
//! - orthographic or perspective cameras, triangles clipped at the near plane so a camera can
//!   stand inside a building;
//! - smooth (vertex) normals for CortenForge's curved solids, flat facets for boxes;
//! - translucent layers (glass, water) drawn after the opaque ones, blended, not writing depth;
//! - a sky gradient behind perspective views, and optional outlines.
//!
//! Meshes are in millimetres, as everywhere in `forge`.

use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

use cortenforge::mesh::types::IndexedMesh;
use nalgebra::{Point3, Vector3};

type V = Vector3<f64>;

pub struct SLayer<'a> {
    pub mesh: &'a IndexedMesh,
    pub color: [f64; 3],
    /// 1 = opaque; below 1 drawn in the translucent pass.
    pub alpha: f64,
    pub smooth: bool,
    pub casts: bool,
    /// A reflection in still water at this height (mm): drawn where it is (mirrored below the
    /// water), lit and shadowed as the real thing above it.
    pub mirror_z: Option<f64>,
    /// Water surface (translucent) of pool k, or a reflection that shows only in pool k (0: none).
    pub pool: u8,
}

impl<'a> SLayer<'a> {
    pub fn solid(mesh: &'a IndexedMesh, color: [f64; 3]) -> Self {
        SLayer { mesh, color, alpha: 1.0, smooth: false, casts: true, mirror_z: None, pool: 0 }
    }
    /// A reflection in pool `pool`, whose water is at height z (mm).
    pub fn mirrored(mut self, z: f64, pool: u8) -> Self {
        self.mirror_z = Some(z);
        self.casts = false;
        self.pool = pool;
        self
    }
    /// The water surface of pool `pool`.
    pub fn water(mesh: &'a IndexedMesh, color: [f64; 3], alpha: f64, pool: u8) -> Self {
        SLayer { mesh, color, alpha, smooth: false, casts: false, mirror_z: None, pool }
    }
    pub fn smooth(mut self) -> Self {
        self.smooth = true;
        self
    }
    pub fn translucent(mesh: &'a IndexedMesh, color: [f64; 3], alpha: f64) -> Self {
        SLayer { mesh, color, alpha, smooth: false, casts: false, mirror_z: None, pool: 0 }
    }
    pub fn no_shadow(mut self) -> Self {
        self.casts = false;
        self
    }
}

pub enum Camera {
    /// Looking along `dir`, `px_per_mm` pixels a millimetre, sized to fit.
    Ortho { dir: V, up: V, px_per_mm: f64 },
    /// From `eye` toward `target`, vertical field of view in degrees, `w` x `h` pixels.
    Persp { eye: Point3<f64>, target: Point3<f64>, up: V, fov_deg: f64, w: usize, h: usize },
}

pub struct Light {
    /// Direction toward the sun (world).
    pub sun: V,
    pub sun_k: f64,
    pub sky_k: f64,
    /// Light bounced up from the ground onto downward faces (ceilings, soffits).
    pub bounce_k: f64,
    pub shadow_px: usize,
    pub sky_top: [f64; 3],
    pub sky_horizon: [f64; 3],
    pub outline: bool,
    /// Multiplies every shaded colour (an interior needs more than daylight outside).
    pub exposure: f64,
    /// Only geometry inside this world box (mm) sizes the shadow map (finer shadows where they
    /// matter); geometry outside it casts no shadow.
    pub shadow_focus: Option<(V, V)>,
}

impl Light {
    /// A sun `elev` degrees up from `azim` degrees (from +x toward +y).
    pub fn sun_at(azim_deg: f64, elev_deg: f64) -> Self {
        let (a, e) = (azim_deg.to_radians(), elev_deg.to_radians());
        Light {
            sun: V::new(e.cos() * a.cos(), e.cos() * a.sin(), e.sin()),
            sun_k: 0.78, sky_k: 0.42, bounce_k: 0.24, shadow_px: 4096,
            sky_top: [0.55, 0.70, 0.88], sky_horizon: [0.88, 0.91, 0.93], outline: false, exposure: 1.0, shadow_focus: None,
        }
    }
}

/// Right, up and back (toward the viewer) for a view along `dir`.
fn basis(dir: &V, up: &V) -> (V, V, V) {
    let back = -dir.normalize();
    let hint = if back.cross(up).norm() < 1e-6 { V::x() } else { *up };
    let right = hint.cross(&back).normalize();
    (right, back.cross(&right), back)
}

fn vertex_normals(mesh: &IndexedMesh) -> Vec<V> {
    let mut n = vec![V::zeros(); mesh.vertices.len()];
    for f in &mesh.faces {
        let [a, b, c] = f.map(|i| mesh.vertices[i as usize].coords);
        let fnorm = (b - a).cross(&(c - a));
        for i in f {
            n[*i as usize] += fnorm;
        }
    }
    for v in &mut n {
        let l = v.norm();
        if l > 0.0 {
            *v /= l;
        }
    }
    n
}

/// Depth seen from the sun: the largest "toward the sun" coordinate in each cell.
struct ShadowMap {
    r: (V, V, V),
    lo: (f64, f64),
    scale: f64,
    n: usize,
    depth: Vec<f32>,
}

impl ShadowMap {
    fn build(layers: &[SLayer], sun: &V, n: usize, focus: Option<(V, V)>) -> Self {
        let inside = |p: &V| focus.is_none_or(|(a, b)| p.x >= a.x && p.y >= a.y && p.z >= a.z && p.x <= b.x && p.y <= b.y && p.z <= b.z);
        let back = sun.normalize();
        let hint = if back.z.abs() < 0.99 { V::z() } else { V::x() };
        let right = hint.cross(&back).normalize();
        let up = back.cross(&right);
        let (mut lo, mut hi) = ((f64::MAX, f64::MAX), (f64::MIN, f64::MIN));
        let proj: Vec<Vec<V>> = layers.iter().map(|l| {
            l.mesh.vertices.iter().map(|p| {
                let q = V::new(p.coords.dot(&right), p.coords.dot(&up), p.coords.dot(&back));
                if l.casts && inside(&p.coords) {
                    lo = (lo.0.min(q.x), lo.1.min(q.y));
                    hi = (hi.0.max(q.x), hi.1.max(q.y));
                }
                q
            }).collect()
        }).collect();
        let range = (hi.0 - lo.0).max(hi.1 - lo.1).max(1.0);
        let scale = (n as f64 - 1.0) / range;
        let mut depth = vec![f32::MIN; n * n];
        for (l, q) in layers.iter().zip(&proj) {
            if !l.casts {
                continue;
            }
            for f in &l.mesh.faces {
                if !f.iter().all(|i| inside(&l.mesh.vertices[*i as usize].coords)) {
                    continue;
                }
                let [a, b, c] = f.map(|i| q[i as usize]);
                let to = |p: &V| ((p.x - lo.0) * scale, (p.y - lo.1) * scale, p.z);
                raster(to(&a), to(&b), to(&c), n, n, |x, y, _w0, _w1, _w2, z| {
                    let i = y * n + x;
                    if z as f32 > depth[i] {
                        depth[i] = z as f32;
                    }
                });
            }
        }
        ShadowMap { r: (right, up, back), lo, scale, n, depth }
    }

    /// Share of the 3 x 3 neighbourhood that sees the sun from world point p, whose surface meets
    /// the sun at cos `ndl`: the depth bias grows with the slope (a face lit at a glancing angle
    /// spans more depth per shadow texel), so flat faces don't shadow themselves.
    fn lit(&self, p: &V, ndl: f64) -> f64 {
        let texel = 1.0 / self.scale;
        let tan = (1.0 - ndl * ndl).max(0.0).sqrt() / ndl.max(1e-3);
        let bias = 20.0 + texel * (1.5 + 2.0 * tan.min(10.0));
        let (x, y, z) = ((p.dot(&self.r.0) - self.lo.0) * self.scale, (p.dot(&self.r.1) - self.lo.1) * self.scale, p.dot(&self.r.2));
        let (cx, cy) = (x.round() as i64, y.round() as i64);
        let mut lit = 0.0;
        for dy in -1..=1 {
            for dx in -1..=1 {
                let (sx, sy) = (cx + dx, cy + dy);
                if sx < 0 || sy < 0 || sx >= self.n as i64 || sy >= self.n as i64 {
                    lit += 1.0;
                    continue;
                }
                if (self.depth[sy as usize * self.n + sx as usize] as f64) <= z + bias {
                    lit += 1.0;
                }
            }
        }
        lit / 9.0
    }
}

/// Rasterize a screen triangle (x, y in pixels, z any linear attribute), calling `put(x, y, w0,
/// w1, w2, z)` for each covered pixel centre with its barycentric weights.
fn raster(a: (f64, f64, f64), b: (f64, f64, f64), c: (f64, f64, f64), w: usize, h: usize, mut put: impl FnMut(usize, usize, f64, f64, f64, f64)) {
    let area = (b.0 - a.0) * (c.1 - a.1) - (c.0 - a.0) * (b.1 - a.1);
    if area.abs() < 1e-12 {
        return;
    }
    let xmin = a.0.min(b.0).min(c.0).floor().max(0.0) as usize;
    let ymin = a.1.min(b.1).min(c.1).floor().max(0.0) as usize;
    let xmax = (a.0.max(b.0).max(c.0).ceil().max(0.0) as usize).min(w.saturating_sub(1));
    let ymax = (a.1.max(b.1).max(c.1).ceil().max(0.0) as usize).min(h.saturating_sub(1));
    if xmin > xmax || ymin > ymax {
        return;
    }
    // Walk only each row's span inside the triangle (long thin triangles lying across the screen
    // have bounding boxes far larger than themselves); the barycentric test below still decides.
    let edges = [(a, b), (b, c), (c, a)];
    for y in ymin..=ymax {
        let py = y as f64 + 0.5;
        let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
        for (p, q) in edges {
            let (y0, y1) = (p.1.min(q.1), p.1.max(q.1));
            if py < y0 - 1.0 || py > y1 + 1.0 {
                continue;
            }
            let xs = if (q.1 - p.1).abs() < 1e-12 {
                [p.0, q.0]
            } else {
                let t = ((py - p.1) / (q.1 - p.1)).clamp(0.0, 1.0);
                let x = p.0 + t * (q.0 - p.0);
                [x, x]
            };
            lo = lo.min(xs[0].min(xs[1]));
            hi = hi.max(xs[0].max(xs[1]));
        }
        if lo > hi {
            continue;
        }
        let x0 = ((lo - 1.0).floor().max(xmin as f64)) as usize;
        let x1 = ((hi + 1.0).ceil().min(xmax as f64)) as usize;
        for x in x0.max(xmin)..=x1.min(xmax) {
            let px = x as f64 + 0.5;
            let w0 = ((b.0 - px) * (c.1 - py) - (c.0 - px) * (b.1 - py)) / area;
            let w1 = ((c.0 - px) * (a.1 - py) - (a.0 - px) * (c.1 - py)) / area;
            let w2 = 1.0 - w0 - w1;
            if w0 < -1e-9 || w1 < -1e-9 || w2 < -1e-9 {
                continue;
            }
            put(x, y, w0, w1, w2, w0 * a.2 + w1 * b.2 + w2 * c.2);
        }
    }
}

#[derive(Clone, Copy)]
struct Vert {
    c: V,     // camera coordinates
    world: V, // world position
    n: V,     // normal (world)
}

fn lerp(a: &Vert, b: &Vert, t: f64) -> Vert {
    Vert { c: a.c + (b.c - a.c) * t, world: a.world + (b.world - a.world) * t, n: a.n + (b.n - a.n) * t }
}

/// Clip a triangle to z <= -near (in front of a perspective camera).
fn clip_near(tri: [Vert; 3], near: f64) -> Vec<Vert> {
    let inside = |v: &Vert| v.c.z <= -near;
    let mut out = Vec::with_capacity(4);
    for i in 0..3 {
        let (cur, nxt) = (tri[i], tri[(i + 1) % 3]);
        if inside(&cur) {
            out.push(cur);
        }
        if inside(&cur) != inside(&nxt) {
            let t = (-near - cur.c.z) / (nxt.c.z - cur.c.z);
            out.push(lerp(&cur, &nxt, t));
        }
    }
    out
}

/// Render `layers` from `cam` under `light` to a PNG; returns its size.
pub fn render_scene(layers: &[SLayer], cam: &Camera, light: &Light, ssaa: usize, path: &Path) -> std::io::Result<(u32, u32)> {
    let k = ssaa.max(1);
    let sun = light.sun.normalize();
    let shadow = ShadowMap::build(layers, &sun, light.shadow_px, light.shadow_focus);
    // Camera frame and image size.
    let (rot, eye, persp, f_px, w, h, lo) = match cam {
        Camera::Ortho { dir, up, px_per_mm } => {
            let b = basis(dir, up);
            let (mut lo, mut hi) = ((f64::MAX, f64::MAX), (f64::MIN, f64::MIN));
            for l in layers {
                for p in &l.mesh.vertices {
                    let (x, y) = (p.coords.dot(&b.0), p.coords.dot(&b.1));
                    lo = (lo.0.min(x), lo.1.min(y));
                    hi = (hi.0.max(x), hi.1.max(y));
                }
            }
            let ppm = px_per_mm * k as f64;
            let pad = 12.0 * k as f64;
            let w = ((hi.0 - lo.0) * ppm + 2.0 * pad).ceil() as usize;
            let h = ((hi.1 - lo.1) * ppm + 2.0 * pad).ceil() as usize;
            (b, V::zeros(), false, ppm, w, h, (lo.0 - pad / ppm, lo.1 - pad / ppm))
        }
        Camera::Persp { eye, target, up, fov_deg, w, h } => {
            let b = basis(&(target - eye), up);
            let (w, h) = (w * k, h * k);
            let f_px = (h as f64 / 2.0) / (fov_deg.to_radians() / 2.0).tan();
            (b, eye.coords, true, f_px, w, h, (0.0, 0.0))
        }
    };
    let to_cam = |p: &V| { let d = p - eye; V::new(d.dot(&rot.0), d.dot(&rot.1), d.dot(&rot.2)) };
    let near = 100.0;
    // Screen position, depth (larger = nearer) and 1/w for a camera-space point.
    let project = |c: &V| -> (f64, f64, f64, f64) {
        if persp {
            let iw = 1.0 / (-c.z);
            (w as f64 / 2.0 + f_px * c.x * iw, h as f64 / 2.0 - f_px * c.y * iw, iw, iw)
        } else {
            ((c.x - lo.0) * f_px, h as f64 - (c.y - lo.1) * f_px, c.z, 1.0)
        }
    };
    let mut img: Vec<[f64; 3]> = (0..w * h).map(|i| {
        let t = (i / w) as f64 / h as f64;
        if persp { [0, 1, 2].map(|c| light.sky_top[c] * (1.0 - t) + light.sky_horizon[c] * t) } else { [0.965, 0.965, 0.95] }
    }).collect();
    let mut zbuf = vec![f64::MIN; w * h];
    let mut id = vec![usize::MAX; w * h];
    let mut dist = vec![f64::MAX; w * h];
    let mut stencil = vec![0u8; w * h];
    let mut mbuf = vec![f64::MIN; w * h];
    let shade = |base: [f64; 3], n: &V, world: &V, alpha_pass: bool, mirror: Option<f64>| -> [f64; 3] {
        let view = if persp { (world - eye).normalize() } else { -rot.2 };
        let mut n = n.normalize();
        if n.dot(&view) > 0.0 {
            n = -n;
        }
        // A reflection is lit as the thing it reflects.
        let (n, world) = match mirror {
            Some(z) => (V::new(n.x, n.y, -n.z), V::new(world.x, world.y, 2.0 * z - world.z)),
            None => (n, *world),
        };
        let ndl = n.dot(&sun);
        let lit = if ndl > 0.0 && !alpha_pass { shadow.lit(&world, ndl) } else if ndl > 0.0 { 1.0 } else { 0.0 };
        let sky = 0.55 + 0.45 * n.z;
        let k_ = (light.sky_k * sky + light.bounce_k * (0.5 - 0.5 * n.z) + light.sun_k * ndl.max(0.0) * lit) * light.exposure;
        base.map(|c| (c * k_).clamp(0.0, 1.0))
    };
    for pass in 0..4 {
        for (li, l) in layers.iter().enumerate() {
            let translucent = l.alpha < 1.0;
            let reflection = l.mirror_z.is_some();
            let wanted = match pass {
                0 => !translucent && !reflection,
                1 => translucent && l.pool > 0,
                2 => reflection,
                _ => translucent,
            };
            if !wanted {
                continue;
            }
            let cam_v: Vec<V> = l.mesh.vertices.iter().map(|p| to_cam(&p.coords)).collect();
            let vn = if l.smooth { Some(vertex_normals(l.mesh)) } else { None };
            for f in &l.mesh.faces {
                let idx = f.map(|i| i as usize);
                let wv = idx.map(|i| l.mesh.vertices[i].coords);
                let fnorm = (wv[1] - wv[0]).cross(&(wv[2] - wv[0]));
                if fnorm.norm() == 0.0 {
                    continue;
                }
                let tri = [0, 1, 2].map(|j| Vert { c: cam_v[idx[j]], world: wv[j], n: vn.as_ref().map_or(fnorm, |n| n[idx[j]]) });
                let poly = if persp { clip_near(tri, near) } else { tri.to_vec() };
                if poly.len() < 3 {
                    continue;
                }
                let pr: Vec<(f64, f64, f64, f64)> = poly.iter().map(|v| project(&v.c)).collect();
                for t in 1..poly.len() - 1 {
                    let (va, vb, vc) = (&poly[0], &poly[t], &poly[t + 1]);
                    let (pa, pb, pc) = (pr[0], pr[t], pr[t + 1]);
                    raster((pa.0, pa.1, pa.2), (pb.0, pb.1, pb.2), (pc.0, pc.1, pc.2), w, h, |x, y, w0, w1, w2, z| {
                        let i = y * w + x;
                        if pass == 2 {
                            // A reflection: only where its pool's water shows, nearest first.
                            if stencil[i] != l.pool || z <= mbuf[i] {
                                return;
                            }
                        } else if z <= zbuf[i] {
                            return;
                        }
                        if pass == 1 {
                            stencil[i] = l.pool;
                            return;
                        }
                        // Perspective-correct world position and normal.
                        let (q0, q1, q2) = (w0 * pa.3, w1 * pb.3, w2 * pc.3);
                        let s = q0 + q1 + q2;
                        let world = (va.world * q0 + vb.world * q1 + vc.world * q2) / s;
                        let n = (va.n * q0 + vb.n * q1 + vc.n * q2) / s;
                        let col = shade(l.color, &n, &world, translucent, l.mirror_z);
                        if pass == 2 {
                            mbuf[i] = z;
                            img[i] = col;
                        } else if translucent {
                            img[i] = [0, 1, 2].map(|c| img[i][c] * (1.0 - l.alpha) + col[c] * l.alpha);
                        } else {
                            zbuf[i] = z;
                            id[i] = li;
                            dist[i] = (world - if persp { eye } else { world - rot.2 * 1e6 }).norm();
                            img[i] = col;
                        }
                    });
                }
            }
        }
    }
    if light.outline {
        let mut edge = vec![false; w * h];
        for y in 0..h.saturating_sub(1) {
            for x in 0..w.saturating_sub(1) {
                let i = y * w + x;
                for j in [i + 1, i + w] {
                    if id[i] != id[j] || (id[i] != usize::MAX && (dist[i] - dist[j]).abs() > (0.02 * dist[i]).max(60.0)) {
                        edge[i] = true;
                    }
                }
            }
        }
        for (i, e) in edge.iter().enumerate() {
            if *e {
                img[i] = img[i].map(|c| c * 0.55);
            }
        }
    }
    // Downsample and write.
    let (w2, h2) = (w / k, h / k);
    let mut out = vec![0u8; w2 * h2 * 3];
    for y in 0..h2 {
        for x in 0..w2 {
            let mut acc = [0.0; 3];
            for dy in 0..k {
                for dx in 0..k {
                    let p = img[(y * k + dy) * w + x * k + dx];
                    for c in 0..3 {
                        acc[c] += p[c];
                    }
                }
            }
            let o = (y * w2 + x) * 3;
            for c in 0..3 {
                out[o + c] = ((acc[c] / (k * k) as f64).clamp(0.0, 1.0) * 255.0).round() as u8;
            }
        }
    }
    let file = File::create(path)?;
    let mut enc = png::Encoder::new(BufWriter::new(file), w2 as u32, h2 as u32);
    enc.set_color(png::ColorType::Rgb);
    enc.set_depth(png::BitDepth::Eight);
    let mut writer = enc.write_header().map_err(std::io::Error::other)?;
    writer.write_image_data(&out).map_err(std::io::Error::other)?;
    Ok((w2 as u32, h2 as u32))
}

/// The renderer against a closed form: a 2 m cube on the ground under a sun 30 degrees up casts
/// a shadow h / tan(30 deg) = 3,464 mm long. Rendered from straight above at 20 mm a pixel, the
/// shadow's length is read off the image along the cube's centre line.
pub fn check(root: &Path) -> std::io::Result<bool> {
    let mut ground = IndexedMesh::new();
    add_box(&mut ground, V::new(-12_000.0, -6_000.0, -200.0), V::new(6_000.0, 6_000.0, 0.0));
    let mut cube = IndexedMesh::new();
    add_box(&mut cube, V::new(0.0, -1_000.0, 0.0), V::new(2_000.0, 1_000.0, 2_000.0));
    let mut light = Light::sun_at(0.0, 30.0); // the sun toward +x: the shadow falls toward -x
    light.shadow_px = 2048;
    let layers = [SLayer::solid(&ground, [0.8, 0.8, 0.8]), SLayer::solid(&cube, [0.6, 0.5, 0.4])];
    let path = root.join("out/pass3/scene_check.png");
    std::fs::create_dir_all(path.parent().unwrap())?;
    let ppm = 1.0 / 20.0;
    let (w, h) = render_scene(&layers, &Camera::Ortho { dir: -V::z(), up: V::y(), px_per_mm: ppm }, &light, 1, &path)?;
    let dec = png::Decoder::new(std::io::BufReader::new(File::open(&path)?));
    let mut reader = dec.read_info().map_err(std::io::Error::other)?;
    let mut buf = vec![0u8; reader.output_buffer_size().unwrap_or(0)];
    reader.next_frame(&mut buf).map_err(std::io::Error::other)?;
    // Image x runs with world x (looking down, y up); the ground spans x -12,000..6,000 mm.
    let (w, h) = (w as usize, h as usize);
    let row = h / 2;
    let px = |x: usize| buf[(row * w + x) * 3] as f64;
    let x_of = |mm: f64| ((mm + 12_000.0) * ppm + 12.0) as usize; // 12 px pad
    let lit = px(x_of(-11_000.0));
    let mut x = x_of(-20.0);
    while x > 0 && px(x) < lit * 0.8 {
        x -= 1;
    }
    let len = (x_of(0.0) - x) as f64 / ppm;
    let want = 2_000.0 / 30f64.to_radians().tan();
    println!("scene check: shadow {len:.0} mm against {want:.0} mm (h / tan 30 deg), {:.1}%", 100.0 * (len / want - 1.0));
    Ok((len - want).abs() < 2.0 / ppm + 30.0)
}

/// Append a box (mm) to a mesh, with its own corners (flat shading stays crisp).
pub fn add_box(out: &mut IndexedMesh, lo: V, hi: V) {
    let cube = cortenforge::mesh::types::unit_cube();
    let base = out.vertices.len() as u32;
    let d = hi - lo;
    out.vertices.extend(cube.vertices.iter().map(|v| Point3::new(lo.x + v.x * d.x, lo.y + v.y * d.y, lo.z + v.z * d.z)));
    out.faces.extend(cube.faces.iter().map(|f| [f[0] + base, f[1] + base, f[2] + base]));
}

/// Append `m` moved by `shift` (our own instancing: CortenForge has none).
pub fn add_moved(out: &mut IndexedMesh, m: &IndexedMesh, shift: V) {
    let base = out.vertices.len() as u32;
    out.vertices.extend(m.vertices.iter().map(|p| Point3::from(p.coords + shift)));
    out.faces.extend(m.faces.iter().map(|f| [f[0] + base, f[1] + base, f[2] + base]));
}

/// Append `m` mirrored in the plane z = 0 (a reflection in still water), winding flipped.
pub fn add_mirrored(out: &mut IndexedMesh, m: &IndexedMesh) {
    let base = out.vertices.len() as u32;
    out.vertices.extend(m.vertices.iter().map(|p| Point3::new(p.x, p.y, -p.z)));
    out.faces.extend(m.faces.iter().map(|f| [f[0] + base, f[2] + base, f[1] + base]));
}
