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
  Meshing it (walls ~558k triangles at 25 mm) takes ~55 s.

## sim-therm-env, sim-thermostat

- **gap** (2026-11-15, scoping): neither is building heat transfer. sim-therm-env is "a typed
  builder producing SimEnv/VecEnv from thermodynamic circuit descriptions" and sim-thermostat a
  "Langevin thermostat + passive-component framework for thermodynamic computing"
  (their Cargo.toml descriptions; sim-thermostat's src is Ising models, double wells, ratchets).
  A data center's heat (racks to coolant to dry coolers or a district heat network) and a house's
  heat loss need conduction, convection and fluid loops; we write those ourselves.

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
  single-band A-weighted method in Python (`src/brownfield/noise.py`).
