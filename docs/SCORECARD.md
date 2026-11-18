# Scorecard

What every design is scored on, conventional and good-neighbour side by side on the same site. A
measure enters the scorecard once it can be computed or sourced; until then it says which pass
fills it. Targets come from cited guidelines, never from what our design happens to reach.

| Measure | Unit | What it answers | Pass |
|---|---|---|---|
| Water withdrawn and consumed | m3/yr, and per MWh of IT load | the cooling water complaint | 2 |
| Peak grid demand, and who pays for upgrades | MW, $ | grid strain and power bills | 2, 4 |
| Night sound at the nearest homes | dB(A), outdoors | the hum | 2 |
| Backup power: diesel run hours and emissions | h/yr, t/yr | generator testing, air | 2 |
| Waste heat used | share of heat out, MWh/yr | heat dumped into the air | 2, 3 |
| Land reclaimed | acres; coal ash left in place or removed | cleared land, old contamination | 1, 2 |
| Permanent jobs on site | jobs, and per MW | "few jobs" | 2, 4 |
| Local tax revenue | $/yr, and what it funds | tax breaks | 4 |
| Housing cost | share of median local income | affordable housing | 4 |
| Hospital access | minutes to an emergency room | health care | 4 |

Targets to source in pass 2: night noise (WHO guidelines), water (best published WUE), backup
(battery-only data centers in service).

Checked against the public record of the Homer City campus (2026-11-16,
[hearing-record.md](hearing-record.md)): people raise jobs, water, night sound, power bills and
taxes, but raise most often what isn't here. That covers process and transparency, the
creek's ecology, the gas plant's air, monitoring and enforcement, private wells, local hiring and
cleanup liability. No one raised housing, hospital access or reuse of waste heat. Candidate
additions are listed there, for a decision. The first, heat to the creek in degrees, is computed
in [pass 2e](pass2/creek.md).

## The scorecard at Homer City, as the design now stands (2026-11-17)

`uv run brownfield scorecard` (`src/brownfield/scorecard.py`, `campus`). Pass 2's table (one
module, [pass2/README.md](pass2/README.md)) scored a design that sent its heat to a 5,000-home
network. Since then the homes join the towns and heat themselves (D18), and the glass is sized
by what the market buys (pass 3d). This scores the design as it stands:
- against the three conventional designs pass 2 priced ([pass2/cost.md](pass2/cost.md));
- at the campus's scale;
- for the towns.

### What it says

- **Against the old water-cooled design, the good neighbour wins on everything:** no water, a lower
  PUE, quiet nights, no diesel. It's +$118M a module over 20 years keeping diesel. But nobody
  builds the old design any more.
- **Against the modern designs the case is narrower, and it's about the neighbours, not money.**
  - **The cloud hall (outside air and pads):** it uses almost no water here either and a little
    less energy. The good neighbour's plant would have to cost $2.7M less to break even.
  - **The AI hall (liquid and towers):** it's $24.8M a module cheaper over 20 years. But at
    3 GW it withdraws ~27 million gallons a day and sends ~6.8 million of blowdown to the creeks,
    and its towers need ~700 m to fall to 40 dB(A) at night. The good neighbour withdraws none and
    is quiet 34-80 m from its walled yard.
    - **The reservoir:** on top of the gas plant, those towers would empty Two Lick Creek
      Reservoir in the droughts of 1952 and 1991 ([pass 2f](pass2/water.md)).
  - **Diesel:** dropping it is the site's opportunity: any design here could bridge to the gas
    plant with batteries.
- **The heat is no longer part of the case.** With the homes on heat pumps and the glass sized by
  the market, the good neighbour puts **~0.7% of its heat** to use: 156 GWh a year, the 38.5 ha of
  glass.
  - **What remains:** the heat is still worth giving the glass. But "waste heat for the town"
    should not be claimed for this site; its homes are 1-5 km off.
- **Most of what the towns get comes whichever design is built.**
  - **Either way:** the 1,500-2,000 jobs, ~$96M a year of property tax (about 70% of it school
    tax), and a decade of construction peaking near 3,300 on site in mid-2029.
  - **What the good-neighbour deal adds is the benefits agreement, funded from that tax:** 242
    homes at the towns' edges, two clubhouses and the arena, the crews' housing plan, and 270
    jobs in the glass.
- **So a town has two kinds of asks:**
  - **Design asks:** no water draw or blowdown to the creeks; 40 dB(A) at night at the nearest
    homes; no diesel tests.
  - **Deal asks:** a housing fund, the crews' plan, the third places.

  The first are cheap against the modern designs, or free against the cloud hall. The second are
  paid from the tax either way.

### The tables

**1. The data center: one 100 MW module, four designs** (the typical year at the plant; cooling only, electrical losses left out)

| Per module | Old conventional (chillers + towers) | Strong cloud (outside air + pads) | Strong AI (liquid + towers) | Good neighbour |
|---|---|---|---|---|
| Water withdrawn, million gal/day | 1.05 | 0.01 | 0.91 | 0 |
| PUE (IT + cooling) | 1.196 | 1.040 | 1.028 | 1.044 |
| Night sound: 40 dB(A) at | ~698 m (towers) | not modelled (fans on the halls) | ~698 m (towers) | 34-80 m from its walled cooler yard |
| Diesel generators (tested 24 h a year each) | 44 | 44 | 44 | 0 (batteries to the gas plant) |
| NOx from generator tests, t a year | 10.1 | 10.1 | 10.1 | 0 |
| Heat put to use | none | none | none | 5.2 GWh a year to its share of the glass (1.28 ha): 0.7% of its heat |
| The good neighbour over 20 years, million USD (+ means it's cheaper) | +118.1 keeping diesel (+190.4 dropping it) | -2.7: its plant must cost that much less to break even | -24.8 | |
| The same against the AI hall, as a sum each year, million USD | | | -2.3 (-3.4% of the AI hall's power bill at $95/MWh; -70 across the campus) | |

**2. The campus: AWS's 39 buildings at ~3,000 MW of IT (30 modules; AWS states no load, range 1,500-3,750 MW)**

| The campus | Old conventional | Strong cloud | Strong AI | Good neighbour |
|---|---|---|---|---|
| Water withdrawn, million gal/day | 31.6 | 0.2 | 27.2 | 0 |
| Of it, blowdown to the creeks, million gal/day | 7.9 | 0.1 | 6.8 | 0 |
| Cooling electricity, GWh a year | 4,117 | 841 | 583 | 925 |
| Diesel generators | 1,320 | 1,320 | 1,320 | 0 |
| NOx from their tests, t a year | 304 | 304 | 304 | 0 |
| Heat put to use | none | none | none | 156 GWh a year, the 38.5 ha of glass |
| Greenhouse jobs | 0 | 0 | 0 | 270 |

**3. The towns** (Homer City, Graceton, Coral, Lucerne Mines, Black Lick: 3,794 people)

| | Whichever design is built | What the good-neighbour deal adds |
|---|---|---|
| Permanent jobs | AWS: 1,500-2,000 at $80,000-100,000 (its filing) | 270 in the glass |
| Property tax at build-out | $96M a year (school $68M, county $23M, townships $6M); AWS seeks no abatement | a set share into a housing fund and the trust |
| Construction, 2026-2036 | peak ~3,300 on site in June 2029 (2,893-5,341); beds for crews from away short in 32% of draws; US 119 at 0.55 of capacity in the shift hour | a crew housing plan, protection for the towns' renters, park-and-ride (pass 4) |
| New homes | none planned | 242 (high case 664) at the towns' edges, each town growing ~15%: 121 flats, 98 townhouses, 23 houses; every one on its own heat pump |
| The flats' funding gap | | $20.2M at market rents, $18.7M with 4% tax credits, $6.1M with 9%; from the housing fund |
| Third places | | 2 clubhouses ($9.6M to build, $1.02M a year: $577 a household) and the arena ($3.18M a year to run, less leagues and memberships) |
| Limits | | 242 homes against room for ~1,346 on Homer City's sewage plant; ~9 children a grade against Homer-Center's ~60 |

### How it was done

- **The four designs:** pass 2's models (`module.py`) over the typical year at the plant.
  - The good neighbour has no town network, and its share of the 38.5 ha of glass is 1.28 ha a
    module.
  - The glass's heat is its loss through the cover with no sun, an upper bound.
- **Costs:** pass 2's ledgers and strong-design comparison (`cost.py`), central values. The ranges
  are in [pass2/cost.md](pass2/cost.md).
- **Night sound:** pass 2's ISO 9613-2 model. The towers' figure is the old design's, used for the
  AI hall's towers too; the cloud hall's fans weren't modelled.
- **The campus:** 30 modules at 3,000 MW of IT. AWS states no load, so this is a placeholder
  bounded by the 4.5 GW gas plant (1,500-3,750 MW). Every campus figure scales with it.
- **The towns:** pass 4 and D16-D19:
  - jobs and tax from `econ.py`;
  - homes, the flats' gap, the clubhouses and the limits from `conference.py` and `rings.py`;
  - the arena from `center.py`;
  - the crews from `workforce.py`.

### What we don't know

- **AWS's actual cooling.** Its narrative says non-contact cooling water through the station's
  existing withdrawal rights, returned to the station for reuse. That is neither tower blowdown nor
  dry coolers, and it isn't scored here. How much water it consumes, and what goes back to the
  creeks at what temperature, is the question to ask.
  - **A clue ([pass 2f](pass2/water.md)):** DEP's permit inputs for the gas plant run 12 MGD above
    what its own condensers need. That gap is what towers rejecting ~1.5 GW of the halls' heat
    would use, so it is worth asking whether that is where the halls' heat goes.
- **The campus's IT load.** It sets every campus figure above.
- **The cloud hall's night sound,** and the towers' at the AI hall's warmer water.
- **Measures still to fill:**
  - hospital access (pass 4);
  - housing cost as a share of income for the towns' own renters;
  - land reclaimed and the ash cap;
  - monitoring and private wells, from the hearing record.

