# CortenForge findings

What this project needs from the published `cortenforge` 0.9.0 crates, what works, and what is
missing. Each entry: type (bug, docs, API, perf, setup, works, gap), date, and file:line under
`~/.cargo/registry/src/*/cortenforge-*-0.9.0/` where there is one. The **Suggestions** list at
the end collects the features this project wanted, with what we built instead.

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
