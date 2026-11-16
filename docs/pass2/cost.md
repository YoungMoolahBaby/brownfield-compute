# Pass 2b: what it costs, and who pays and gains

## Bottom line (read this first)

Against the **old** conventional design (water-cooled chillers and towers) the good neighbour
looked cheaper and better. Against the **strongest** modern designs it is a little dearer or about
even, and the heat for the town needs its own funding:

- **Against a liquid-cooled AI hall with cooling towers** (the same loops, towers instead of dry
  coolers): the good neighbour costs ~$22 million more per 100 MW module over 20 years (P10-P90
  -$39 to -$4 million, ahead in 6% of draws), $5.4 million of it up front for the walls between
  its coolers ([pass 2d](wall.md)). For that it uses no water (~0.9 million gallons a day saved)
  and is much quieter at night: 40 dB(A) at 34-80 m from its cooler yard against ~700 m for
  towers. It spends ~8 GWh a year more electricity on fans and trim.
- **Against an air-cooled cloud hall with evaporative pads** (AWS-style): at Homer City's cool
  climate both use almost no water and the same energy (PUE 1.040 vs 1.039, cooling only), so
  there is nothing to pay for anything: the good neighbour's cooling plant would have to cost
  about the same as an air plant (break-even +$0.5 million, P10-P90 -$6 to +$19 million), and
  public data can't say which is cheaper. Air-cooled halls can't take AI racks of ~120 kW.
- **Dropping diesel is the site's opportunity, not the design's**: any design at Homer City could
  lean on the on-site gas plant and batteries.
- **For AI** (section 3) the good neighbour works as it is; its premium over a liquid hall with
  towers runs from ~$14 million (chips on 45 C water) to ~$39 million (32 C) per module over 20 years.
- **So "better at the same cost" holds only against the old design.** Against modern designs the
  good neighbour buys zero water and quiet for a small premium, and the town's heat network
  (-$159 million on its own) needs someone to choose to fund it.

Run: `uv run brownfield cost`, 2026-11-15, with the inputs firmed up in [firm-up.md](firm-up.md);
rerun 2026-11-16 with pass 2d's walls between the coolers ($5.4 million, robot-laid brick) in
place of the $1 million berm placeholder. Section 1 below is against the old conventional design;
section 2 against the strongest designs.

## 1. Against the old conventional design

`uv run brownfield cost`, run 2026-11-16. Per 100 MW (IT) module at Homer City, US dollars,
inputs and sources in `params/cost.yaml`. Two ledgers, because different people pay and gain: the
**data center operator** (good neighbour minus conventional) and the **heat business** that would
own the heat pumps, the main and the town network (a utility, the town, or the operator).

Cooling hardware is priced only where the designs differ: industry sources say towers and
closed-circuit coolers of similar capacity cost about the same installed, so what changes is
the dry coolers' oversizing (for quiet) and the size of the chiller plant.

| Per 100 MW module, million USD | Central |
|---|---|
| **Operator, good neighbour minus conventional** | |
| Dry coolers oversized | +15.8 |
| Trim chillers (41 MW) instead of a full chiller plant | -14.7 |
| Batteries instead of diesel generators | -58.5 |
| Walls round and between the coolers (pass 2d) | +5.4 |
| **Up-front difference** | **-52.0** |
| Cooling electricity saved, a year | 10.41 |
| Water saved, a year | 1.65 |
| Generator upkeep saved, a year | 1.30 |
| **Heat business** | |
| Heat pumps (51 MW) | 70.8 |
| Main to Indiana borough | 41.9 |
| Town network | 34.5 |
| Home connections | 32.5 |
| **Up-front** | **179.6** |
| Net heat income a year (sales at $46/MWh less pump power and upkeep) | 1.98 |
| Each home saves, a year (USD) | 174 |

| 20-year value, million USD | Central | P10 / P50 / P90 | Positive in | Worst corner |
|---|---|---|---|---|
| Operator, no diesel | +194 | +150 / +196 / +250 | 100% | -102 |
| Operator, keeps its diesel | +121 | +95 / +133 / +182 | 100% | -61 |
| Heat business alone | -159 | -269 / -198 / -129 | 0% |  |
| Operator + heat business | +35 | -86 / -1 / +86 | 49% |  |

Monte Carlo: 2,000 draws of every range in `params/` (triangular, independent), seed 7. The
worst corner sets every input at the end that hurts the good neighbour at once (`cost.WORST`).
The walls' design choices (heights, layout) are held as chosen; their prices, the robot's rate,
wind and soil vary.

## What it says

- **For the operator the good-neighbour module pays, mostly through electricity.** It costs ~$52
  million less up front (no diesel, a smaller chiller plant, less $5.4 million of walls) and saves
  ~$13 million a year, $10 million of it cooling electricity. Even keeping its diesel, the
  operator comes out ~$121 million ahead over 20 years. It is positive in every Monte Carlo draw,
  but not in the worst corner (every input against it at once: -$102 million), so it is robust,
  not unconditional.
- **District heat doesn't pay for itself here.** Pennsylvania gas is cheap: heat a home's furnace
  makes costs ~$58/MWh, so heat sold 20% below that brings in little against ~$180 million of
  heat pumps, a 13 km main, a town network and connections. It is negative in every draw.
- **Together it's a coin flip.** The operator's savings roughly cover the heat network (+$35
  million central, positive in 49% of draws). That is the shape of a deal a benefits agreement
  could write down: the operator funds the heat network out of what the design saves it, and
  ~5,000 households save ~$170 a year each on heat.
- **Hydrogen backup costs over five times diesel.** Fuel cells plus 187 t of stored hydrogen for
  a day of full load: ~$380 million (290-580), against ~$72 million of diesel. Batteries bridge
  either way; hydrogen only replaces diesel for long outages, which at Homer City means losing
  the grid and a 4.5 GW gas plant next door at once. It makes sense where there is no such
  plant, or once fuel cells and storage get much cheaper.

## 2. Against the strongest conventional designs

Added 2026-11-15 after Jon asked whether the good neighbour is "a better neighbor at the same
cost?": the honest test is against the best designs, not the weakest. Same weather (with humidity,
for wet bulb by Stull 2011), same load, cooling only (backup the same on both sides).

| Per 100 MW module | PUE (IT + cooling) | Water |
|---|---|---|
| Old conventional (water-cooled chillers + towers) | 1.196 | 2.08 L/kWh |
| Strong cloud (outside air + evaporative pads) | 1.040 | 0.015 L/kWh |
| Strong AI (liquid loop + cooling towers) | 1.028 | 1.79 L/kWh |
| Good neighbour (liquid loop + dry coolers + heat pumps) | 1.039 | none |

| Good neighbour against | Central (million USD) | P10 / P50 / P90 | Good neighbour ahead in | Worst corner |
|---|---|---|---|---|
| Strong AI, 20-year value (up front +28.3; a year +0.64) | -21.6 | -38.9 / -20.8 / -4.0 | 6% | -123.0 |
| Strong cloud, most its cooling plant may cost extra up front and still break even | +0.5 | -5.9 / +5.7 / +19.1 | 73% | -23.5 |

Against the strong AI hall the good neighbour spends 8.3 GWh a year more electricity and saves 0.91 million gallons of water a day. Backup is the same on both sides here. Monte Carlo: 2,000 draws, seed 7.

Calibration: AWS reports a fleet PUE of 1.15 (2024) and 1.14 (2025) and a fleet WUE of 0.15
L/kWh (2024) and 0.12 (2025) (Amazon sustainability report and AWS fact sheets). Our cloud hall's
1.040 counts cooling only (no electrical losses), so it sits below the fleet's total as it should.
Its 0.015 L/kWh is a tenth of the fleet's: Homer City is cool (pads run ~362 hours a year), and
the model leaves out winter humidification and pads used below 27 C; read it as a low end.

## 3. Can the good neighbour run AI?

Yes: it is an AI design. Direct-to-chip liquid cooling on a warm-water loop is what AI racks of
~120 kW need (85% of the heat into liquid, the figure used here); the air-cooled cloud hall in
section 2 can't take them. So for AI the comparison is the liquid-cooled hall with cooling towers.
Added 2026-11-15 (Jon: "can good neighbor be used for ai"), `uv run brownfield cost` (rerun
2026-11-16 with the walls), central values per 100 MW module:

| Case | Good neighbour PUE | AI towers PUE | Heat pump COP | Heat reused | Water saved, million gal/day | Good neighbour vs AI towers, 20 years, million USD | Electricity bill a year, million USD |
|---|---|---|---|---|---|---|---|
| Today's AI racks: 40 C water, 80% load | 1.039 | 1.028 | 5.55 | 13% | 0.91 | -21.6 | 69 |
| AI training: 40 C water, 95% load | 1.040 | 1.028 | 5.55 | 11% | 1.08 | -20.9 | 82 |
| Chips that need colder water: 32 C, 95% load | 1.044 | 1.028 | 4.52 | 10% | 1.08 | -38.7 | 83 |
| Chips that take warm water: 45 C, 95% load | 1.040 | 1.028 | 6.47 | 11% | 1.08 | -14.2 | 82 |

- **It works for AI as it is.** The only change from the AI alternative is how the heat leaves:
  dry coolers behind walls instead of towers. That costs ~$22 million over 20 years for ~1
  million gallons of water a day saved and a quieter night, about 3% of the module's ~$69 million
  a year electricity bill (21.6 / 10.59 annuity = $2.0 million a year).
- **The coolant temperature the chips accept decides the premium.** Warm-water chips (45 C) cut
  it to ~$14 million and lift the heat pumps' COP to 6.5, because the heat comes off hotter.
  Chips that need 32 C water nearly double it (~$39 million) and drop the COP to
  4.5: dry coolers cool toward the dry bulb and need trim chillers more often; towers cool toward
  the wet bulb and hardly notice. ASHRAE TC 9.9 warned in 2021 that higher-power chips may only run
  on W32 (RESEARCH.md).
- **More load doesn't mean more heat used.** At 95% load there is more heat, but the town and the
  greenhouses can't take more, so the share falls (11%).
- **What a buyer or a benefits agreement could ask for:** hardware rated for warm water (W40-W45),
  which is what makes zero water cheap.

## What we don't know yet

- **Many prices are placeholders** (`conf: placeholder` or `low`): dry coolers and chillers per
  kW (no published figure found), batteries for 15 minutes, the walls' robot rates and prices
  (pass 2d), fuel cells, water
  treatment. The operator result leans most on the cooling electricity saved (PUE) and on the
  diesel avoided.
- **Converting forced-air homes to hot-water heat** isn't priced (no US source found); most
  houses in the area likely have furnaces with ducts, so the real connection cost per home could
  be well above the $6,500 used.
- **Heat pumps are sized for the coldest hour** (51 MW); a gas or electric peak boiler for the
  coldest days would cut that, and is how Danish networks are built.
- **Electricity price** for the campus isn't public (power comes from FirstEnergy, backed by the
  on-site gas plant).
- **Whether an operator accepts backup without diesel** is a reliability policy question, not a
  cost one.
- **Water's price** here is a Pennsylvania utility's industrial tariff ($4.34 per 1,000 gal,
  York Water); the developer's own treatment cost isn't public.
- No grants or tax credits are counted (federal and state programmes for district energy and
  heat pumps could change the heat ledger).
