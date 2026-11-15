# Pass 2: the good-neighbour data center at Homer City (draft)

**Status: in progress.** Water and heat v1 are done; noise, backup power, jobs and the checks
are next (PLAN.md, pass 2).

## The site and the plan

The former Homer City Generating Station (Indiana County, PA) is being redeveloped: a 4.5 GW gas
plant by Homer City Redevelopment, and an AWS campus of 39 two-storey data centers on ~2,200
acres, built in phases from December 2026 to 2036. AWS projects 1,500-2,000 permanent staff and
asks for no property-tax breaks; a Community Benefits Agreement is still to be written. DEP is
reviewing a water permit for up to 6.8 million gallons a day into Two Lick and Blacklick Creeks,
at up to 110 F. Sources and quotes: RESEARCH.md.

What this pass is: an independent, public estimate of what a good-neighbour design would deliver
on this site, measure by measure, against a conventional one. It doesn't know AWS's cooling
design (their filing doesn't state it) and doesn't guess it.

## One module, two designs

A 100 MW (IT) module at 80% average load, over the typical year at the plant (PVGIS: mean 11.2
C, 82 hours above 30 C, -13.9 to 36.1 C). Same load, same weather, same power.

- **Conventional**: chillers move the heat to evaporative cooling towers.
- **Good neighbour**: direct-to-chip liquid cooling (80% of the heat) on a 40 C loop, the rest on
  an air-side loop; dry coolers, no water; small chillers trim the hottest hours; heat pumps lift
  the loop's heat to 75 C for a town network (5,000 homes) and 10 ha of greenhouses.

`uv run brownfield module`, first run 2026-11-15:

| Per 100 MW module, per year | Unit | conventional | good neighbour |
|---|---|---|---|
| IT energy | GWh | 701 | 701 |
| Cooling electricity (chillers, trim, fans, pumps) | GWh | 137.2 | 29.7 |
| PUE (IT + cooling; electrical losses left out of both) |  | 1.196 | 1.042 |
| Water withdrawn | million m3 | 1.46 | 0.00 |
| Water withdrawn | million US gal a day | 1.05 | 0.00 |
| Water evaporated (consumed) | million m3 | 1.09 | 0.00 |
| WUE (withdrawn per IT kWh) | L/kWh | 2.08 | 0.00 |
| Heat leaving the site | GWh | 838 | 730 |
| Heat delivered to town + greenhouses | GWh | 0 | 116 |
|   of it to the town | GWh | 0 | 75 |
|   of it to greenhouses | GWh | 0 | 41 |
| Data center heat reused | share of heat out | 0% | 14% |
| Heat pump electricity | GWh | 0.0 | 16.6 |

Checked: the conventional water use (2.08 L/kWh) lands inside the published range for
evaporative and water-cooled data centers (1.55 to 2.8 L/kWh, RESEARCH.md), and the cooling
tower rule of thumb matches thermodynamics (tests).

What the first numbers say:

- **Water is a design choice, not a law of nature.** Each conventional module draws about a
  million gallons a day; the coal plant drew 5.6 million in 2020. The good-neighbour module
  draws none, for ~0.15 points of PUE better, not worse, because the warm loop rarely needs
  chillers in this climate.
- **A town can't use most of the heat.** 5,000 homes and 10 ha of greenhouses take 14% of one
  module's heat; the rest still goes to the air (in the good-neighbour design, never to the
  creek). The campus is many modules. Using more of the heat means bigger greenhouses, other
  heat users, or accepting that most of it is rejected.

## What we don't know yet

- **Many inputs are placeholders** (`conf: placeholder` in `params/pass2.yaml`): fan and pump
  power, the liquid-cooled share, the heat pump COP (7.0 here, likely optimistic), the load
  factor. The next step sources them and checks the heat side against Odense.
- **AWS's actual design.** Their filing says non-contact cooling water is "returned to the Homer
  City Station for reuse"; where that heat goes in the end isn't stated.
- **The gas plant's own water and heat** are outside this comparison (same for both designs) and
  likely larger than the data centers'.
- **The campus size in IT megawatts** isn't public, so results are per 100 MW module.
- **Greenhouse heat** ignores the sun, so it's an upper bound on what greenhouses can take.
