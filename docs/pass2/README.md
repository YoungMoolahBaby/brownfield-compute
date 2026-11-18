# Pass 2: the good-neighbour data center at Homer City

**Status: v1 complete (2026-11-15); costs in [cost.md](cost.md); firmed up in
[firm-up.md](firm-up.md) (sensitivity, homes around the campus, sourced inputs).** Read with cost.md's bottom
line: the conventional design here is the old water-cooled one. Against the strongest modern
designs the water and energy gaps shrink a lot at this cool site (cost.md, section 2). Every row comes from `uv run brownfield module`; inputs and
their sources are in `params/pass2.yaml`, and many are still placeholders (listed at the end).

Later passes on this site: [the wall](wall.md) (2d), [the creek](creek.md) (2e), and
[the water budget](water.md) (2f): the reservoir against the gas plant and each data center design;
[the air](air.md) (2g): the gas plant's permit against the coal plant's emissions, and the diesel.

## The site and the plan

The former Homer City Generating Station (Indiana County, PA) is being redeveloped: a 4.5 GW gas
plant by Homer City Redevelopment, and an AWS campus of 39 two-storey data centers on ~2,200
acres, built in phases from December 2026 to 2036. AWS projects 1,500-2,000 permanent staff and
asks for no property-tax breaks; a Community Benefits Agreement is still to be written. DEP is
reviewing a water permit for up to 6.8 million gallons a day into Two Lick and Blacklick Creeks,
at up to 110 F. Sources and quotes: RESEARCH.md.

This pass is an independent, public estimate of what a good-neighbour design would deliver on
this site, measure by measure, against a conventional one. AWS's filing doesn't state its cooling
design, and this pass doesn't guess it.

## One module, two designs

A 100 MW (IT) module at 80% average load, over the typical year at the plant (PVGIS: mean 11.2
C, 82 hours above 30 C, -13.9 to 36.1 C). Same load, same weather, same power (the site's gas
plant), so the difference is the data center.

- **Conventional**: chillers move the heat to evaporative cooling towers; diesel generators for
  backup.
- **Good neighbour**: direct-to-chip liquid cooling (85% of the heat) on a 40 C loop, the rest on
  an air-side loop; dry coolers, no water, oversized so the fans turn at half speed, screened
  (pass 2d: walled cells, not the berm first assumed); small chillers trim the hottest hours; heat pumps lift the loop's heat to 75 C for
  a district heating network (5,000 homes) and 10 ha of greenhouses; batteries bridge to the
  on-site gas plant instead of diesel.

## The scorecard

Pass 2's design, with heat to a 5,000-home network. The design as it now stands (homes on heat pumps,
the glass sized by the market) is scored in [SCORECARD.md](../SCORECARD.md), against all three conventional
designs and at campus scale.

| Per 100 MW module | Unit | Conventional | Good neighbour |
|---|---|---|---|
| Water withdrawn | million US gal/day | 1.05 | 0 |
| Water consumed (evaporated) | million m3/yr | 1.09 | 0 |
| WUE | L/kWh IT | 2.08 | 0 |
| PUE (IT + cooling) |  | 1.196 | 1.039 |
| Heat put to use | GWh/yr | 0 | 116 |
| Heat put to use | share of heat out | 0% | 13% |
| Homes heated | homes | 0 | 5,000 |
| Sound power of heat rejection | dB(A) | 114 | 106 |
|   dry coolers at minimum size instead (fans at full speed) | dB(A) |  | 118 |
| Distance to 40 dB(A) at night (the module as a point, no screen) | m | 698 | 317 |
|   from the cooler yard's edge, 6 m berm round it (pass 2d) | m |  | 218 |
|   from the yard's edge, walled cells (pass 2d), across / along the rows | m |  | 34 / 80 |
| Diesel generators | units | 44 | 0 |
| Diesel test hours | engine-hours/yr | 1,056 | 0 |
| NOx from tests | t/yr | 10.1 | 0 |
| Batteries | MWh | - | 32 |
| Jobs, data center | per AWS building | 45 | 45 |
| Jobs, greenhouses | jobs | 0 | 70 (10 ha) |

PUE leaves out electrical losses in both designs. Heat pump electricity (20.8 GWh/yr) is
reported apart: it is spent to sell heat, replacing the town's furnaces.

## What it says

- **Water is a design choice.** A conventional module draws about a million gallons a day; the
  coal plant drew 5.6 million in 2020, and the campus will be many modules. The good-neighbour
  module draws none, and in this climate it also uses less cooling energy (PUE 1.04 vs 1.20),
  because a 40 C loop rarely needs chillers in western Pennsylvania.
- **A town can use only a slice of the heat.** Indiana borough's ~4,700 households, 13 km away,
  plus 10 ha of greenhouses take 13% of one module's heat. Every home within reach (~14,000
  households, Census) would still leave most of it to the air; using more means much larger
  greenhouses or other heat users. In the good-neighbour design the rest goes to the air, never
  to the creek.
- **Quiet isn't automatic.** Dry coolers need ~40 times the fans of cooling towers; at minimum
  size they are louder (118 vs 114 dB(A)). Oversized so the fans run at half speed, they are
  8 dB quieter than the towers.
- **Corrected in [pass 2d](wall.md):** this report first gave the berm a flat 10 dB and put
  40 dB(A) at ~120 m. Sized from the coolers' real layout by ISO 9613-2's barrier method, a 6 m
  berm round the yard takes ~1 dB off at 300 m. Walls between the rows of coolers ("cells") take
  ~12 dB off for homes across the rows and ~6.5 dB for homes off the ends.
- **The measure that holds without vendor data is the sound power budget**: what a module may
  emit for 40 dB(A) outside a home at night (WHO 2009), from ISO 9613-2 propagation, and what
  walled cells add to it (pass 2d):

  | Nearest home | Budget, open ground | Budget with walled cells (homes across / off the ends) |
  |---|---|---|
  | 300 m | 105 dB(A) | 117 / 112 dB(A) |
  | 500 m | 110 dB(A) | 121 / 115 dB(A) |
  | 1,000 m | 118 dB(A) | 126 / 120 dB(A) |
  | 2,000 m | 126 dB(A) | 131 / 127 dB(A) |

  A commitment written as "40 dB(A) at night at any home" can be checked against a design with
  this table.
- **Diesel is avoidable here** more than at most sites: the campus has its own 4.5 GW gas plant
  next to the grid, so batteries only have to bridge the switch. Whether operators accept
  backup without diesel is the open question.
- **Jobs barely change.** The data center's jobs are the same in both designs; greenhouses add
  ~7 per hectare.

## Checks

- The cooling tower rule of thumb (~1% of the circulation evaporated per 10 F) matches
  thermodynamics, c_p dT / h_fg = 0.96%.
- The conventional module's 2.08 L/kWh lands inside the published range for evaporative and
  water-cooled data centers, 1.55-2.8 L/kWh.
- The heat pump model, at our central settings, stays below a measured Danish unit (COP 3.58 at
  -4.5 C source, 55 C sink), and matches it at the high end.
- ISO 9613-2 terms against hand-worked values; the fan law (50 lg speed ratio) matches a fan
  maker's claim that EC fans at half airflow are 15 dB(A) quieter.
- Meta's Odense data center (45 MW of heat pumps, 100,000-215,000 MWh a year, 6,900-12,000
  homes) can't be a numeric check: its IT load isn't published. Its 14.5-17.9 MWh per home
  brackets our 15.

## What we don't know yet

- **Placeholders** (`conf: placeholder`): fan power for towers and dry coolers, per-fan sound
  levels, MW per fan, the load factor, backup sizing, generator test load. Water and efficiency
  hold across the ranges: with every conventional input at its best end and every
  good-neighbour input at its worst, the conventional module still draws 1.52 L/kWh and has
  PUE 1.142, the good neighbour none and 1.112 (run 2026-11-15). Heat reuse moves a lot with
  who takes the heat: 3% for 2,000 homes, 24% for all ~14,000 households in reach, 46% with
  100 ha of greenhouses as well. The noise figures lean on the placeholders, so the budget
  table is the firmer result.
- **Distances to real homes.** OpenStreetMap shows only 29 buildings within 3 km of the plant,
  far from complete. The six AWS sites' boundaries aren't public in a usable form. Next:
  building footprints or the county's address points.
- **AWS's actual design.** Their filing says non-contact cooling water is "returned to the Homer
  City Station for reuse". The station's filed water balance gives the halls 1,400 gpm, with 400
  returned ([pass 2f](water.md)). That is enough to evaporate away ~6% of a 3,000 MW campus's
  heat, so most must leave dry. The equipment isn't stated.
- **The gas plant's own water and heat** are outside this comparison (same for both designs)
  and likely larger than the data centers'.
- **The campus in IT megawatts** isn't public, so results are per 100 MW module.
- **Cost.** Dry coolers oversized 2x, berms, heat pumps and a 13 km heat main all cost money;
  pass 4 prices them against what the town gains.
- **Greenhouse heat** ignores the sun, so it's an upper bound on what greenhouses can take.
