//! A robot lays the wall's face (pass 2d, D7), in sim-core.
//!
//! A four-axis gantry straddling the wall: a bridge sliding along it (y), a trolley across it (x),
//! a mast up and down (z) and a wrist turning about the vertical, each on a position servo. The
//! gripper holds a brick by a weld; for each brick the gantry lifts it from a hopper beside the
//! wall, carries it over its place while turning it to its angle, lowers it to 2 mm above its
//! mortar bed and lets go (the weld switched off), and the brick has to settle onto the bed where
//! the drawing puts it, between the bricks already laid.
//!
//! Paths are minimum-jerk (quintic) moves, each as long as the slowest axis needs at the speed and
//! acceleration limits; the axes share the time. Mortar is a rigid slab at the bed's height (its
//! give is not modelled). What comes out: the time a brick's motion takes, with the pattern and
//! without, and where the bricks end up.

use cortenforge::sim::mjcf::load_model;
use nalgebra::{UnitQuaternion, Vector2, Vector3};
use serde_json::{Value, json};

use crate::wall::{Brick, Kind, Spec};

pub struct Limits {
    pub v: f64,       // m/s, linear axes
    pub a: f64,       // m/s2
    pub w: f64,       // rad/s, wrist
    pub alpha: f64,   // rad/s2
    pub lift: f64,    // m, clearance above the course while moving
    pub release: f64, // m, gap under the brick when it's let go
    pub dwell: f64,   // s, held still before letting go
    pub settle: f64,  // s, watched after letting go
}

impl Limits {
    /// Placeholders until robot specs are sourced: a gantry moving at 1 m/s and 2 m/s2 (the
    /// slower end of industrial gantries), a wrist at 180 deg/s.
    pub fn provisional() -> Self {
        Limits { v: 1.0, a: 2.0, w: std::f64::consts::PI, alpha: 4.0 * std::f64::consts::PI, lift: 0.08, release: 0.002, dwell: 0.15, settle: 0.4 }
    }
}

/// Time (s) of a minimum-jerk move of `d` under speed `v` and acceleration `a` (peak speed
/// 1.875 d / T, peak acceleration 5.774 d / T^2).
pub fn quintic_time(d: f64, v: f64, a: f64) -> f64 {
    let d = d.abs();
    if d < 1e-12 { 0.0 } else { (1.875 * d / v).max((5.7735 * d / a).sqrt()) }
}

fn quintic(s: f64) -> f64 {
    let s = s.clamp(0.0, 1.0);
    s * s * s * (10.0 - 15.0 * s + 6.0 * s * s)
}

fn quat_str(yaw: f64) -> String {
    let q = UnitQuaternion::from_axis_angle(&Vector3::z_axis(), yaw);
    format!("{:.9} {:.9} {:.9} {:.9}", q.w, q.i, q.j, q.k)
}

/// A brick's box geom, in metres, about the world z by its yaw. The brick's length lies along y
/// at yaw 0 (wall.rs), so the box's half sizes are (width, length, height) in x, y, z, and a turn
/// of `yaw` in wall.rs (length axis (sin, cos)) is a turn of -yaw about z.
fn brick_geom(b: &Brick, extra: &str) -> String {
    format!(r#"<geom type="box" pos="{:.6} {:.6} {:.6}" quat="{}" size="{:.6} {:.6} {:.6}" {extra}/>"#,
            b.c.x / 1e3, b.c.y / 1e3, b.c.z / 1e3, quat_str(-b.yaw), b.h.y / 1e3, b.h.x / 1e3, b.h.z / 1e3)
}

pub struct Placed {
    pub motion_s: f64,
    pub err_plan_mm: f64,
    pub err_z_mm: f64,
    pub err_deg: f64,
    pub track_mm: f64,
    pub final_c: Vector3<f64>,
    pub final_yaw: f64,
}

/// Lay one brick `b` (its design pose) from the hopper at `pick` (m, wrist at rest there), with
/// `laid` (already placed, final poses) and the bed slab under it as fixed geometry.
pub fn lay(b: &Brick, laid: &[Brick], bed: (Vector3<f64>, Vector3<f64>), pick: Vector3<f64>, lim: &Limits, density: f64) -> Placed {
    let grip = 0.06; // m from the wrist's origin down to the brick's centre
    let target = Vector3::new(b.c.x, b.c.y, b.c.z) / 1e3;
    let hz = b.h.z / 1e3;
    let statics: String = laid.iter().map(|o| brick_geom(o, r#"density="2000""#)).collect::<Vec<_>>().join("\n    ");
    let (blo, bhi) = bed;
    let bc = (blo + bhi) / 2e3;
    let bh = (bhi - blo) / 2e3;
    // Wrist targets relative to the pick pose (joint coordinates).
    let (dx, dy) = (target.x - pick.x, target.y - pick.y);
    let z_over = target.z + lim.lift - (pick.z - grip); // above the course, brick's centre
    let z_rel = target.z + lim.release - (pick.z - grip);
    let yaw = -b.yaw;
    let xml = format!(r#"<mujoco model="gantry">
  <option timestep="0.0005" gravity="0 0 -9.81"/>
  <worldbody>
    <geom type="box" pos="{:.6} {:.6} {:.6}" size="{:.6} {:.6} {:.6}" density="2000"/>
    {statics}
    <body name="bridge" pos="{:.6} {:.6} {:.6}">
      <joint name="y" type="slide" axis="0 1 0"/>
      <geom type="box" size="0.1 0.1 0.1" mass="300" contype="0" conaffinity="0"/>
      <body name="trolley">
        <joint name="x" type="slide" axis="1 0 0"/>
        <geom type="box" size="0.08 0.08 0.08" mass="50" contype="0" conaffinity="0"/>
        <body name="mast">
          <joint name="z" type="slide" axis="0 0 1"/>
          <geom type="box" size="0.05 0.05 0.05" mass="20" contype="0" conaffinity="0"/>
          <body name="wrist">
            <joint name="yaw" type="hinge" axis="0 0 1"/>
            <geom type="box" size="0.04 0.04 0.02" mass="5" contype="0" conaffinity="0"/>
          </body>
        </body>
      </body>
    </body>
    <body name="brick" pos="{:.6} {:.6} {:.6}">
      <freejoint/>
      <geom type="box" size="{:.6} {:.6} {:.6}" density="{density}"/>
    </body>
  </worldbody>
  <equality>
    <weld name="grip" body1="wrist" body2="brick"/>
  </equality>
  <actuator>
    <position joint="y" kp="2000000" kv="60000"/>
    <position joint="x" kp="1000000" kv="16000"/>
    <position joint="z" kp="1000000" kv="11000"/>
    <position joint="yaw" kp="400" kv="5"/>
  </actuator>
</mujoco>"#,
        bc.x, bc.y, bc.z, bh.x, bh.y, bh.z,
        pick.x, pick.y, pick.z,
        pick.x, pick.y, pick.z - grip, b.h.y / 1e3, b.h.x / 1e3, hz);
    let mut model = load_model(&xml).expect("gantry model loads");
    let mut d = model.make_data();
    let dt = 0.0005;
    // Moves: (1) lift and carry over the place, turning; (2) lower to the release height.
    let carry = [dx, dy, z_over].iter().map(|v| quintic_time(*v, lim.v, lim.a)).fold(quintic_time(yaw, lim.w, lim.alpha), f64::max);
    let lower = quintic_time(z_over - z_rel, lim.v, lim.a);
    let t_motion = carry + lower;
    let total = 0.2 + t_motion + lim.dwell + lim.settle;
    let steps = (total / dt) as usize;
    let mut released = false;
    let mut track = 0.0;
    for i in 0..steps {
        let t = i as f64 * dt - 0.2; // 0.2 s held at the hopper first
        let (cx, cy, cz, cw) = if t < 0.0 {
            (0.0, 0.0, 0.0, 0.0)
        } else if t < carry {
            let s = quintic(t / carry);
            (dx * s, dy * s, z_over * s, yaw * s)
        } else {
            let s = quintic((t - carry) / lower.max(1e-9));
            (dx, dy, z_over + (z_rel - z_over) * s, yaw)
        };
        d.ctrl[0] = cy;
        d.ctrl[1] = cx;
        d.ctrl[2] = cz;
        d.ctrl[3] = cw;
        if !released && t >= t_motion + lim.dwell {
            // Where the brick is when it's let go, against where it should be (lifted by the gap).
            let p = Vector3::new(d.qpos[4], d.qpos[5], d.qpos[6]);
            track = (p - (target + Vector3::new(0.0, 0.0, lim.release))).norm() * 1e3;
            model.eq_active[0] = false;
            released = true;
        }
        d.step(&model).expect("step");
    }
    let p = Vector3::new(d.qpos[4], d.qpos[5], d.qpos[6]);
    let q = UnitQuaternion::from_quaternion(nalgebra::Quaternion::new(d.qpos[7], d.qpos[8], d.qpos[9], d.qpos[10]));
    let (_, _, yaw_now) = q.euler_angles();
    let e = p - target;
    Placed {
        motion_s: t_motion,
        err_plan_mm: Vector2::new(e.x, e.y).norm() * 1e3,
        err_z_mm: e.z * 1e3,
        err_deg: (yaw_now - yaw).to_degrees(),
        track_mm: track,
        final_c: p * 1e3,
        final_yaw: -yaw_now,
    }
}

/// Lay `courses` courses of the face wythe over `bay` mm of wall from `y0`, in order, each brick
/// onto its bed between those already laid; the course below as laid by design (the robot's own
/// earlier courses are checked the same way).
pub fn run_bay(s: &Spec, bricks: &[Brick], y0: f64, bay: f64, k0: usize, courses: usize, lim: &Limits) -> Value {
    let density = 2000.0;
    let mut rows = Vec::new();
    let mut all: Vec<Placed> = Vec::new();
    for k in k0..k0 + courses {
        let mut course: Vec<&Brick> = bricks.iter().filter(|b| b.kind == Kind::Face && b.course == k && b.c.y > y0 && b.c.y < y0 + bay).collect();
        course.sort_by(|a, b| a.c.y.total_cmp(&b.c.y));
        let bed_top = course.first().map(|b| b.c.z - b.h.z).unwrap_or(0.0);
        let bed = (Vector3::new(0.0, y0 - 300.0, bed_top - 60.0), Vector3::new(s.unit.y, y0 + bay + 300.0, bed_top));
        let mut laid: Vec<Brick> = Vec::new();
        for b in course {
            // The hopper rides with the bridge: 0.6 m out from the face, 0.3 m back along the wall,
            // the wrist 0.25 m above the brick's place.
            let pick = Vector3::new(-0.6, (b.c.y - 300.0) / 1e3, b.c.z / 1e3 + 0.06 + 0.25);
            let near: Vec<Brick> = laid.iter().filter(|o| (o.c.y - b.c.y).abs() < 600.0).cloned().collect();
            let p = lay(b, &near, bed, pick, lim, density);
            laid.push(Brick { kind: Kind::Face, c: p.final_c, h: b.h, yaw: p.final_yaw, course: k });
            all.push(p);
        }
        rows.push(json!({"course": k, "bricks": laid.len()}));
    }
    let n = all.len().max(1) as f64;
    let mean = |f: &dyn Fn(&Placed) -> f64| all.iter().map(f).sum::<f64>() / n;
    let max = |f: &dyn Fn(&Placed) -> f64| all.iter().map(f).fold(0.0, f64::max);
    json!({
        "bricks": all.len(), "courses": rows,
        "motion_s_mean": mean(&|p| p.motion_s), "motion_s_max": max(&|p| p.motion_s),
        "err_plan_mm_mean": mean(&|p| p.err_plan_mm), "err_plan_mm_max": max(&|p| p.err_plan_mm),
        "err_z_mm_mean": mean(&|p| p.err_z_mm), "err_z_mm_min": all.iter().map(|p| p.err_z_mm).fold(f64::MAX, f64::min),
        "err_deg_max": max(&|p| p.err_deg.abs()), "track_mm_max": max(&|p| p.track_mm),
    })
}
