//! The build sequence in sim-core (pass 3b): the walk-up goes up the way a crew builds a
//! platform frame. Walls are framed flat on the deck in panels and tilted up about their
//! bottom edge (a hinge and a position servo; the servo's torque is what the crew lifts); cap
//! plates, joists and rims are set onto what's already built (free bodies released just above
//! their seats, which have to settle where the drawings put them).
//!
//! sim-core works in metres and kilograms: `framing` members (mm) are scaled on the way in.

use cortenforge::sim::core::{Data, Model};
use cortenforge::sim::mjcf::load_model;
use nalgebra::{UnitQuaternion, Vector3};

pub const G: f64 = 9.81;

/// A box geom (lo, hi in mm, world or body frame relative to `origin` mm) as MJCF, in metres.
pub fn geom(lo: &Vector3<f64>, hi: &Vector3<f64>, origin: &Vector3<f64>, density: f64, extra: &str) -> String {
    let c = ((lo + hi) / 2.0 - origin) / 1e3;
    let h = (hi - lo) / 2e3;
    format!(r#"<geom type="box" pos="{:.6} {:.6} {:.6}" size="{:.6} {:.6} {:.6}" density="{density}" {extra}/>"#,
            c.x, c.y, c.z, h.x, h.y, h.z)
}

/// The torque (N m) gravity puts about a hinge on a rigid set of boxes, at hinge angle `q` from
/// the design (vertical) pose, rotating about `axis` through `pivot` (mm): the moment of the
/// weight's position after the rotation.
pub fn gravity_torque(boxes: &[(Vector3<f64>, Vector3<f64>, f64)], pivot: &Vector3<f64>, axis: &Vector3<f64>, q: f64) -> f64 {
    let rot = UnitQuaternion::from_axis_angle(&nalgebra::Unit::new_normalize(*axis), q);
    let (mut m, mut mc) = (0.0, Vector3::zeros());
    for (lo, hi, density) in boxes {
        let v = (hi - lo).product() / 1e9;
        m += density * v;
        mc += density * v * ((lo + hi) / 2.0 - pivot) / 1e3;
    }
    let r = rot * (mc / m);
    // Torque of the weight (0, 0, -m g) at r, about the axis.
    r.cross(&Vector3::new(0.0, 0.0, -m * G)).dot(&axis.normalize())
}

pub struct Lift {
    pub mass_kg: f64,
    /// Servo torque (N m) and gravity's (N m), sampled through the lift: (angle from flat, servo, gravity).
    pub samples: Vec<(f64, f64, f64)>,
    pub peak_torque: f64,
    pub height_m: f64,
    pub final_angle_err: f64,
}

/// Tilt a rigid panel (boxes in mm, design pose vertical) up from flat: hinge along `axis`
/// through `pivot`, flat at q = pi/2, a position servo ramps it to 0 over `secs`.
pub fn tilt_up(boxes: &[(Vector3<f64>, Vector3<f64>, f64)], pivot: &Vector3<f64>, axis: &Vector3<f64>, secs: f64) -> Lift {
    let geoms: String = boxes.iter().map(|(lo, hi, density)| geom(lo, hi, pivot, *density, r#"contype="0" conaffinity="0""#)).collect::<Vec<_>>().join("\n        ");
    let a = axis.normalize();
    let mass: f64 = boxes.iter().map(|(lo, hi, density)| density * (hi - lo).product() / 1e9).sum();
    let top = boxes.iter().map(|(_, hi, _)| hi.z).fold(f64::NEG_INFINITY, f64::max) - pivot.z;
    // Servo stiff enough to hold the panel within ~0.1 degrees at its heaviest, damped.
    let kp = (mass * G * top / 1e3) * 500.0;
    let xml = format!(r#"<mujoco model="panel">
  <option timestep="0.001" gravity="0 0 -{G}"/>
  <worldbody>
    <body name="panel" pos="{:.6} {:.6} {:.6}">
      <joint name="hinge" type="hinge" axis="{:.6} {:.6} {:.6}" pos="0 0 0"/>
        {geoms}
    </body>
  </worldbody>
  <actuator>
    <position joint="hinge" kp="{kp:.3}" kv="{:.3}"/>
  </actuator>
</mujoco>"#, pivot.x / 1e3, pivot.y / 1e3, pivot.z / 1e3, a.x, a.y, a.z, kp * 0.05);
    let model = load_model(&xml).expect("panel model loads");
    let mut d = model.make_data();
    let q0 = std::f64::consts::FRAC_PI_2;
    d.qpos[0] = q0;
    d.ctrl[0] = q0;
    let steps = (secs / 0.001) as usize;
    let mut samples = Vec::new();
    let mut peak: f64 = 0.0;
    // Held flat for a second (the servo takes up the weight), then lifted, then held upright.
    let hold = 1000;
    for i in 0..hold + steps + 500 {
        // A smooth lift (no jerk at the start or the end): the servo's target follows a half cosine.
        let u = (i.saturating_sub(hold) as f64 / steps as f64).min(1.0);
        d.ctrl[0] = q0 * (1.0 + (std::f64::consts::PI * u).cos()) / 2.0;
        d.step(&model).expect("step");
        if i < hold {
            continue;
        }
        let q = d.qpos[0];
        let servo = d.actuator_force[0];
        peak = peak.max(servo.abs());
        if (i - hold) % (steps / 20).max(1) == 0 {
            samples.push(((q0 - q).to_degrees(), servo, gravity_torque(boxes, pivot, axis, q)));
        }
    }
    Lift { mass_kg: mass, samples, peak_torque: peak, height_m: top / 1e3, final_angle_err: d.qpos[0].abs().to_degrees() }
}

pub struct Landing {
    /// For each dropped body: how far it ended from its design pose (mm, rad).
    pub errors: Vec<(f64, f64)>,
    pub max_depth_mm: f64,
    pub steps: usize,
}

/// Static boxes (the built frame, mm) and bodies to set (each a set of boxes in design pose, mm),
/// released `lift` mm above their seats as free bodies; settle for `secs`.
pub fn set_down(statics: &[(Vector3<f64>, Vector3<f64>)], bodies: &[Vec<(Vector3<f64>, Vector3<f64>)>], density: f64, lift: f64, secs: f64) -> Landing {
    let zero = Vector3::zeros();
    let stat: String = statics.iter().map(|(lo, hi)| geom(lo, hi, &zero, density, "")).collect::<Vec<_>>().join("\n    ");
    let mut dyn_xml = String::new();
    let mut origins = Vec::new();
    for (i, b) in bodies.iter().enumerate() {
        let (mut lo, mut hi) = (Vector3::repeat(f64::INFINITY), Vector3::repeat(f64::NEG_INFINITY));
        for (a, c) in b {
            lo = lo.inf(a);
            hi = hi.sup(c);
        }
        let o = (lo + hi) / 2.0;
        origins.push(o);
        // Half a millimetre off every side face, so neighbours touching face to face don't hold
        // each other up by friction.
        let gs: String = b.iter().map(|(a, c)| {
            let shrink = Vector3::new(0.5, 0.5, 0.0);
            geom(&(a + shrink), &(c - shrink), &o, density, "")
        }).collect::<Vec<_>>().join("");
        dyn_xml += &format!(r#"<body name="b{i}" pos="{:.6} {:.6} {:.6}"><freejoint/>{gs}</body>
    "#, o.x / 1e3, o.y / 1e3, (o.z + lift) / 1e3);
    }
    let xml = format!(r#"<mujoco model="set">
  <option timestep="0.0005" gravity="0 0 -{G}"/>
  <worldbody>
    {stat}
    {dyn_xml}
  </worldbody>
</mujoco>"#);
    let model = load_model(&xml).expect("set-down model loads");
    let mut d = model.make_data();
    let steps = (secs / 0.0005) as usize;
    let mut max_depth: f64 = 0.0;
    for _ in 0..steps {
        d.step(&model).expect("step");
        for c in d.contacts.iter().take(d.ncon) {
            max_depth = max_depth.max(c.depth);
        }
    }
    let errors = origins.iter().enumerate().map(|(i, o)| {
        let p = d.xpos[i + 1] * 1e3;
        ((p - o).norm(), d.xquat[i + 1].angle())
    }).collect();
    Landing { errors, max_depth_mm: max_depth * 1e3, steps }
}

pub fn body_pose(d: &Data, model: &Model, i: usize) -> (Vector3<f64>, UnitQuaternion<f64>) {
    let _ = model;
    (d.xpos[i], d.xquat[i])
}

/// Probe: one wall panel tilted up, a joist set on two plates, and one on a single plate.
pub fn probe() {
    let rho = 457.0;
    // A 4.06 m x 2.73 m panel of 2x6s: plates and 11 studs (mm, vertical, along y, x = 0..140).
    let (l, h, t, d) = (4064.0, 2728.0, 38.1, 139.7);
    let mut boxes = vec![(Vector3::new(0.0, 0.0, 0.0), Vector3::new(d, l, t), rho),
                         (Vector3::new(0.0, 0.0, h - t), Vector3::new(d, l, h), rho)];
    for k in 0..11 {
        let y = (k as f64 * 406.4).min(l - t);
        boxes.push((Vector3::new(0.0, y, t), Vector3::new(d, y + t, h - t), rho));
    }
    let pivot = Vector3::new(d, 0.0, 0.0);
    let axis = Vector3::new(0.0, 1.0, 0.0); // z x (+x inward)
    let t0 = std::time::Instant::now();
    let lift = tilt_up(&boxes, &pivot, &axis, 20.0);
    let flat = gravity_torque(&boxes, &pivot, &axis, std::f64::consts::FRAC_PI_2);
    println!("panel {:.1} kg, {:.2} m tall: peak servo {:.1} N m, gravity at flat {:.1} N m ({:+.2}%), ends {:.3} deg from vertical ({:.2} s)",
             lift.mass_kg, lift.height_m, lift.peak_torque, flat, 100.0 * (lift.peak_torque / flat.abs() - 1.0),
             lift.final_angle_err, t0.elapsed().as_secs_f64());
    for (deg, servo, grav) in lift.samples.iter().step_by(4) {
        println!("  {deg:5.1} deg up: servo {servo:9.1}, gravity {grav:9.1} N m");
    }
    // A 5.8 m I-joist on two plates, then on one.
    let plate = |y0: f64| (Vector3::new(0.0, y0, -38.1), Vector3::new(140.0, y0 + 5900.0, 0.0));
    let (w, dd, fl, web) = (58.7, 301.6, 38.1, 9.5);
    let joist = |x0: f64| vec![(Vector3::new(x0, 0.0, 0.0), Vector3::new(x0 + w, 5800.0, fl)),
                               (Vector3::new(x0, 0.0, dd - fl), Vector3::new(x0 + w, 5800.0, dd)),
                               (Vector3::new(x0 + w / 2.0 - web / 2.0, 0.0, fl), Vector3::new(x0 + w / 2.0 + web / 2.0, 5800.0, dd - fl))];
    let _ = plate;
    // Supports under its two ends: plates running across the joist (along x), 140 mm wide.
    let support = |y0: f64| (Vector3::new(-500.0, y0, -38.1), Vector3::new(500.0, y0 + 140.0, 0.0));
    for (name, statics) in [("on two plates", vec![support(0.0), support(5800.0 - 140.0)]), ("on one plate", vec![support(0.0)])] {
        let t0 = std::time::Instant::now();
        let land = set_down(&statics, &[joist(0.0)], rho, 10.0, 1.0);
        println!("joist {name}: ends {:.2} mm / {:.4} rad from its seat, deepest contact {:.2} mm ({} steps, {:.2} s)",
                 land.errors[0].0, land.errors[0].1, land.max_depth_mm, land.steps, t0.elapsed().as_secs_f64());
    }
}
