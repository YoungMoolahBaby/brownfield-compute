# CortenForge findings

What this project needs from the published `cortenforge` 0.9.0 crates, what works, and what is
missing. Each entry: type (bug, docs, API, perf, setup, works, gap), date, and file:line under
`~/.cargo/registry/src/*/cortenforge-*-0.9.0/` where there is one. The **Suggestions** list at
the end collects the features this project wanted, with what we built instead.

## cf-design

- **bug / docs** (2026-11-15, pass 3, the house): `mass_properties` (mechanism/mass.rs:78)
  over-counts solids made by `subtract` when the cutter is nearly flush with the faces it cuts.
  Its grid gives cells near a surface the partial weight `clamp(0.5 - d / cell)` (mass.rs:240),
  which assumes `d` is a true distance; `Subtract` evaluates `a.max(-b)` (evaluate.rs:60), which
  inside the cut reads only how far the cutter overshoots, not the distance to the remaining
  solid. A house's walls (outer box minus an inner box overshooting 1 mm top and bottom): 19.718
  m3 at 50 mm cells, 17.632 at 25 mm, exact 16.606 (+18.7% / +6.2%): the room's whole floor layer
  counted at ~40% weight. The same walls with the cutter overshooting 1 m: 16.651 / 16.613 (+0.27%
  / +0.04%). Probe: `forge` mode `probe`. Workaround: every cutter overshoots generously
  (`house::CUT`). Relates to custom-skate's note that two parts 0.1 mm apart weigh as an overlap.
- **API** (2026-11-15): `mass_properties` assumes millimetres (density kg/m3, cell volume mm3,
  mass.rs:107), so a building is modelled in mm; nothing in the signature says so.
- **works** (2026-11-15, pass 3): with cutters overshooting, a 24 x 40 ft house measures to its
  exact dimensions: interior 200.899 vs 200.867 m3 (+0.02%, 50 mm cells), walls with eleven
  openings 13.718 vs 13.699 m3 (+0.14%, 25 mm), slab +0.08% (`forge` mode `check`, 2.6 s).
  Meshing it with `Solid::mesh` took ~60 s, nearly all of it the glass at 10 mm (53.8 s); see
  the next two entries.
- **perf** (2026-11-15, pass 3b, the 12-flat walk-up): `Solid::mesh` (solid/query.rs:82) is a
  uniform grid that visits and interval-evaluates every cell of the bounding box
  (mesher.rs:42). A 30 x 12 x 9.5 m building with 114 openings, glass at 15 mm and the rest at
  40 mm, took **3,808.6 s** (63 min). `Solid::mesh_adaptive_par` (adaptive octree dual
  contouring on rayon, solid/query.rs:175) meshed the same layers in ~201 s, enclosing the right
  volumes (exterior walls 109.187 vs exact 109.262 m3, floor systems 197.182 vs 197.202). On the
  house: walls at 25 mm 6.8 s -> 1.1 s, glass at 10 mm 53.8 s -> 0.7 s, the same triangle counts
  within ~1% (`forge` mode `meshers`). The `mesh` docs say "tolerance (voxel size)" but not that
  the grid is uniform, nor point to the adaptive meshers for large scenes.
- **setup** (2026-11-15): the `cortenforge` 0.9.0 crate depends on cf-design with
  `default-features = false` (cortenforge-0.9.0/Cargo.toml:76-79), which drops cf-design's
  default `parallel-meshing` feature, so `Solid::mesh_adaptive_par` doesn't exist through
  `cortenforge` (error E0599, no method). Workaround: also depend on `cortenforge-design =
  "=0.9.0"` directly; Cargo unifies the features and the method appears (`forge/Cargo.toml`).
- **perf** (2026-11-15, pass 3b): even adaptively, a solid's cost grows with its boolean
  children, because `Union`/`Subtract` evaluate both sides at every point with no bounds check
  (evaluate.rs:59-60). At 40 mm, the walk-up's exterior walls (114 opening cutters) took 83.8 s
  and its floor systems (a few boxes) 2.1 s, for the same ~1.7 million triangles.
  `check` with `mass_properties` on those walls at 25 mm cells took 420.8 s in all (now 50 mm:
  +0.31%, 58 s for everything).
- **bug** (2026-11-15, pass 3b, the frame): `Solid::mesh_to_tolerance` (solid/query.rs:230)
  destroys boxes. A 2x6 stud (38 x 140 x 2,600 mm) at 19 mm came back as **4 triangles enclosing
  0.0027 m3 of its 0.0138** (-80%); at 10 mm, 12 triangles but -9.5% (and 7.4 s for one stud). An
  I-joist (three boxes) at 19 mm: 18 triangles, -38%. The adaptive mesher alone gets them right
  (stud: 4,412 triangles, -0.04%, 6 ms). Its own docs warn the simplified surface isn't an
  envelope; here it isn't even the right volume. `forge` mode `member`.
- **works** (2026-11-15, pass 3b): `cortenforge::mesh::types::unit_cube()` (mesh-types mesh.rs:20),
  scaled and moved onto each box, draws the 3,027-member frame exactly in ~43,000 triangles; the
  members stay cf-design solids for measuring (one of each kind measured at -0.15% to +1.6% of
  exact by `mass_properties`, thin members reading heavy as before).

## sim-therm-env, sim-thermostat

- **gap** (2026-11-15, scoping): neither is building heat transfer. sim-therm-env is "a typed
  builder producing SimEnv/VecEnv from thermodynamic circuit descriptions" and sim-thermostat a
  "Langevin thermostat + passive-component framework for thermodynamic computing"
  (their Cargo.toml descriptions; sim-thermostat's src is Ising models, double wells, ratchets).
  A data center's heat (racks to coolant to dry coolers or a district heat network) and a house's
  heat loss need conduction, convection and fluid loops; we write those ourselves.

## sim-core, sim-mjcf

- **works** (2026-11-15, pass 3b, the build): MJCF from strings (`sim::mjcf::load_model`) with box
  geoms, hinge and free joints and a `<position>` servo carried the whole build. A wall panel
  (up to ~40 boxes) raised on a hinge by the servo: its torque matches statics within 0.4% at
  the start of the lift and stays within ~4 N m of gravity's through it (the panel's inertia),
  and the panel ends within 0.005 degrees of upright (138 panels, 0.03-0.06 s each). Members set down as free bodies (I-joists as three
  boxes) on fixed boxes settle within 0.11 mm of their seats; with a support missing, 132 of 142
  fall, as they should.
- **docs** (2026-11-15): a `<position>` actuator's `actuator_force` includes whatever it takes to
  move the joint, so damping on the joint shows up in it: with `damping` on the hinge the servo
  read ~9x gravity's torque (my model's error, not sim-core's; MuJoCo behaves the same). Worth a
  line in the docs for anyone reading actuator force as a load.
- **perf** (2026-11-15): setting a storey's floor down (142 free bodies, ~430 boxes, on ~100
  fixed boxes, every contact a box-box pair) runs ~0.1 s a step at 0.5 ms (800 steps: 92 s; the
  roof's 172 bodies 137 s). Fine for a build sequence, slow next to MuJoCo for the size; contacts
  sink ~3 mm under default contact softness at impact.
- **works** (2026-11-15, pass 3b, three systems): the same approach carried a light steel frame
  (3,190 members) and a block-and-plank building (13,614 pieces: every block, lintel and plank)
  without strain: exact `unit_cube` meshes, sim-core set-downs of 44-54 precast planks (1.9 t
  each) onto ~260-310 bearing blocks in 18-23 s, all within 0.02 mm. The overlap and support
  checks across 13,614 pieces are our own sorted sweeps (cf-spatial may have the structure for
  it; not tried).
- **works** (2026-11-16, pass 2d, the wall robot): a four-axis gantry in MJCF carried 111 bricks
  one at a time, with no trouble from sim-core:
  - three nested `slide` joints and a `hinge`, each on a `<position>` servo with `kv`;
  - a `<weld>` from the wrist to a free-body brick, its relative pose taken from the starting
    pose as in MuJoCo (sim-mjcf builder/equality.rs:190);
  - box geoms turned by `quat`.

  The brick is let go by switching the weld off between steps: `model.eq_active[0] = false`.
  It settled within 0.01 mm of where it was released. Each brick is a fresh model of ~12 geoms
  (~1.6 s of sim at 0.5 ms), so 222 placements took 9.7 s.
- **API / docs** (2026-11-16, pass 2d): `eq_active` lives on `Model`
  (sim-core types/model.rs:815, read in constraint/assembly.rs:140). So switching a constraint on
  or off at run time means mutating the model, which works only because `Data::step` borrows
  `&Model`. MuJoCo 3.x keeps the run-time flag in `mjData.eq_active`, with `mjModel.eq_active0`
  as the default (from memory). A gripper that welds and lets go, the usual pick-and-place
  pattern, would read more naturally with the flag on `Data`, and two `Data`s sharing one
  `Model` can't differ here. Worth a line in the docs either way.

## cf-geometry

- **works** (2026-11-17, D18, the conference drawn): `HeightFieldData` (heightfield.rs:54) samples
  the real ground (USGS 10 m, resampled to 2 m) bilinearly for every road, tree and lot in
  `forge/src/conference.rs`. Its origin is the grid's corner with y increasing by row, so our
  north-to-south rows are flipped on loading.
- **gap** (2026-11-17, D18): no mesh from a `HeightFieldData` (nor from a raster), and nothing to
  drape a polyline or a polygon on one. We wrote our own:
  - the terrain as an indexed grid mesh split by land cover, with a canopy over the far woods;
  - roads as ribbons draped on the ground;
  - existing buildings extruded from footprints, ear-clipping their flat roofs.

## Expected gaps (scoping, not yet hit in code)

Listed so they can be confirmed or struck once code meets them:

- **Outdoor sound propagation**: confirmed 2026-11-15 (pass 2). No acoustics in 0.9; we wrote
  ISO 9613-2's A-weighted method ourselves (`src/brownfield/noise.py`, ~80 lines).
- **Geographic data**: coordinates, projections, rasters, map layers. Pass 1 and the city work
  are GIS-heavy; CortenForge is geometry in a local frame. Confirmed 2026-11-15: pass 1 (EIA,
  Census, FEMA, PVGIS, ranking, maps) used no CortenForge at all, as expected; it isn't a GIS
  tool and isn't trying to be. CortenForge comes in with the buildings (pass 3).
- **Fluid networks**: coolant loops and district heating pipes (flow, pressure drop, heat loss).
- **Frame and beam elements** for building structures (studs, joists, trusses, steel frames):
  sim-soft meshes solids into tetrahedra, heavy for a house of slender members; custom-skate
  found sim-soft usable as a linear-elastic solver at a scaled load.
- **Orthotropic materials** (wood is ~10-20x stiffer along the grain): sim-soft's materials are
  isotropic (Neo-Hookean, Yeoh).

## Suggestions

Nice-to-haves for CortenForge, with what this project built instead.

- **Building physics** (2026-11-15): heat transfer through assemblies and a room-level thermal
  network (RC model), coolant and district heat loops, heat pumps. Instead: an hourly energy
  balance in Python (`src/brownfield/module.py`: cooling towers, dry coolers, trim chillers, heat
  pumps, a degree-hour town load).
- **Outdoor acoustics** (2026-11-15): ISO 9613-2 propagation (spreading, air absorption, ground,
  barriers) from sources placed in a CortenForge scene to receivers, ideally by octave band, with
  terrain from a height field (cf-geometry already has HeightFieldData). Instead: the standard's
  single-band A-weighted method in Python (`src/brownfield/noise.py`). Pass 2d (2026-11-16) added
  barrier diffraction (ISO 9613-2 7.4: one and two edges, the tight path over many walls, the
  meteorological correction) over an area source in `src/brownfield/wall.py`. That is the part a
  scene-aware acoustics module would most help: the walls are already geometry in forge.
- **The fast mesher by default** (2026-11-15, pass 3b): turn on `parallel-meshing` in the
  `cortenforge` crate (or forward a feature), and say in `Solid::mesh`'s docs that it is a uniform
  grid and that `mesh_adaptive_par` is the choice for anything building-sized (63 min vs ~3.4
  min here). Instead: a direct `cortenforge-design` dependency to turn the feature on.
- **Bounds culling in booleans** (2026-11-15, pass 3b): skip a `Union`/`Subtract` child when the
  point is far outside its bounding box (or a BVH over many-child unions), so a facade with 114
  openings evaluates about like one with a few. A building is mostly boxes cut by many small
  boxes. Instead: we wait (~3 min a mesh, ~1 min for the checks at 50 mm cells).
- **An n-ary union/subtract** (2026-11-15, pass 3b): `Solid::union_all(&[..])` /
  `subtract_all`, so 114 openings don't make a 114-deep binary tree; would pair with bounds
  culling. Instead: a fold over `subtract` (`forge/src/apartment.rs`), a
  114-deep chain.
- **Assemblies of many simple parts** (2026-11-15, pass 3b): a building frame is thousands of
  boxes. A scene or assembly type holding parts with materials, exact meshes for primitives
  (a `cuboid` meshes to 12 triangles, not thousands), instancing of repeated parts, and part
  metadata (kind, storey) would carry it, and the same parts could become sim-core bodies for the
  build sequence. Instead: our own `Member` list of boxes, `unit_cube` for drawing, one cf-design
  solid per member for measuring.
- **Construction sequencing** (2026-11-15, pass 3b): adding and removing bodies (or switching
  them on) between stages, so one model can carry a whole build instead of a fresh MJCF per
  stage; joints that become welds when a member is nailed. Instead: a new model per panel lift
  and per set-down stage, with what's built as fixed geometry.
- **Structural members and checks** (2026-11-15, pass 3b): beam and column elements with
  orthotropic wood (and steel) properties, load combinations, and code checks (NDS, AISC/AISI)
  over a frame. Instead: `src/brownfield/frame.py` (NDS 2018 ASD by hand-coded formulas, checked
  against published span tables). Pass 2d (2026-11-16) added reinforced masonry: cracked
  sections, pier-and-panel walls under ASCE 7-16 wind, and drilled-shaft embedment, in
  `src/brownfield/wallstruct.py`, checked against BIA TN 45A and CMHA TEK worked examples.
- **Oriented boxes and plan polygons** (2026-11-16, pass 2d): bricks turned about the vertical
  need overlap, clearance and contact-area queries between oriented boxes. Instead: separating
  axes, point-to-segment distance and Sutherland-Hodgman clipping in `forge/src/wall.rs`
  (~80 lines); cf-geometry not checked for these.
- **Run-time constraint switches on `Data`** (2026-11-16, pass 2d): see the sim-core entry above.
  Instead: mutating `Model::eq_active` between steps, one model per brick.
- **Sweeps along a polyline, and placing a part with a transform** (2026-11-17, pass 3, the site
  plan): the roads and walks routed by `brownfield site` are polylines on the ground, and every
  module is placed (moved, sometimes turned) from `out/pass3/site.json`. A strip of given width
  swept along a 2D polyline over a height function, and an `IndexedMesh` moved and turned by an
  isometry, would cover both. Instead: `forge/src/site.rs` lays 2 m quads along each segment with
  an octagon at each corner, and turned boxes by hand (~60 lines); modules are rebuilt at their
  plan positions rather than moved. cf-geometry not checked for a sweep. Then (D15) the whole
  winter garden had to move and turn to the community center: `Place` in `forge/src/garden.rs`
  turns a built part's vertices a quarter-turn about z and moves them (~40 lines, quarter-turns
  only). Then (D16) the site plan turned the community center itself: `Turn` in
  `forge/src/village.rs` (~40 lines) maps each box, quad and stone face as it is drawn, a second
  quarter-turn helper because the center's meshes are shared with the rest of the neighbourhood
  and can't be moved after the fact. One isometry on a set of meshes, applied while building or
  after, would have covered both.
- **Terrain and site tools** (2026-11-17, D18): a mesh from a `HeightFieldData` (by cell, with
  per-cell tags for land cover), draping polylines and polygons on it (roads, lots), grading a
  footprint into it (a level pad blending out), and extruding a footprint with a roof. With
  instancing, thousands of trees on it. Instead: `forge/src/conference.rs` builds each by hand
  (~350 lines), the grading done in Python (`neighbourhood._grade`).
