# Pass 2g: the air

At the hearings, 15 of 40 speakers raised the gas plant's air and health
([hearing record](../hearing-record.md)). This pass compares the gas plant's permit with what the
coal plant actually emitted, sets out what DEP's modelling puts at the worst point off the site, and
works out what each data center design adds.

Run: `uv run brownfield air` (`src/brownfield/air.py`, `params/air.yaml`). It writes
`out/pass2/air.md` and the figure below.

![Top: the coal plant's SO2 and NOx by year, 2013-2023, on log scales, against the gas plant's caps of 212 and 1,143 tons a year. Bottom left: the coal plant's CO2, at most 12.1 million tons a year, against the gas plant's cap of 17.6 million tons of CO2e. Bottom right: annual PM2.5 at the worst point off the site, 6.8 background plus 0.86 from the gas plant, against the standard of 9](air.png)

## What it says

- **The air case is the gas plant's, and it comes whichever data center is built.**
  - **The plant:** HCR's gas plant is 4,678 MW: seven combined-cycle and ten simple-cycle
    turbines.
  - **The caps:** DEP's permit (Plan Approval 32-00457A, November 2025) caps it, startups
    included, at 1,143 tons a year of NOx, 212 of SO2, 840 of PM2.5 and 17.6 million of
    greenhouse gases.
  - **Who emits it:** AWS's campus would draw half or more of that output, but the permit and the
    emissions are HCR's.
- **Per unit of power it is far cleaner than the coal plant.** Against the coal plant in 2014, its
  busiest recent year, the gas plant's permitted rate at full output is:
  - **SO2:** 0.01 lb per MWh against 21.5 (-99.95%);
  - **NOx:** 0.056 lb per MWh against 3.8 (-98.5%);
  - **CO2:** 857 lb per MWh against 2,095 (-59%).
- **In total it is a different story, because it is 2.5 times the size and built to run.** At its
  caps, against the coal plant in 2014:
  - **SO2 and NOx:** 99.8% and 95% less.
  - **Greenhouse gases:** 45% more, 17.6 million tons a year against 12.1.
  - **Against the coal plant's last two years** (2021-22), when it ran little:
    - **Greenhouse gases:** four times its CO2 (4.4 million tons).
    - **PM2.5:** nearly four times, 840 tons against 220.
  - **The coal plant's SO2** helped make Indiana County a nonattainment area for the 1-hour SO2
    standard. EPA approved the state's plan for it in 2024. The gas plant's cap is 212 tons a year,
    against 123,856 in 2014.
- **What reaches the ground, by DEP's review of the modelling:**
  - **Annual PM2.5 at the worst point off the site:** the plant adds 0.86 µg/m3 to a measured
    background of 6.8. That makes 7.66, 85% of the 9.0 standard.
  - **24-hour PM2.5 and PM10:** 67% and 40% of their standards.
  - **Toxics:** a lifetime cancer risk of 0.54 in a million at the most exposed point (0.48 at the
    most exposed home or school), against DEP's benchmark of 10. Every chronic and short-term hazard
    is below its limit; the closest is cadmium at 0.49 of it.
- **NO2 and ozone at the homes were not modelled.**
  - **Why:** NOx "netted out" of the air quality review. The coal plant's retirement was credited
    with 2,032 tons a year (its 2021-22 NOx, discounted to what the federal rules allowed). That is
    more than the new cap.
  - **What it leaves open:** DEP's finding is a net decrease against those years. Nobody has
    published what the gas plant's own NOx does near the homes.
- **What the data center design changes: the energy, a little, and the diesel, a lot.**
  - **The energy:** the campus at 3,000 MW of IT draws 53-61% of the plant's full output a year.
    At the permitted rates that is 600-700 tons of NOx, 450-515 of PM2.5 and 9.3-10.8 million of
    CO2e.
  - **Old design against modern ones:** the old design's PUE (1.196) costs 89 tons of NOx and 1.4
    million of CO2e a year more than the good neighbour's. The modern designs are within 2% of
    each other.
  - **Routine diesel tests:** 1,320 generators tested 24 hours a year put out up to 335 tons of NOx
    a year at EPA Tier 2. That is +55% on the gas plant's NOx for the cloud halls.
    - **Where it comes out:** from generators at the halls, not the plant's 190-ft stacks.
    - **At Tier 4:** 35 tons (+6%).
    - **With batteries,** as the good neighbour has them: none.
  - **Tier 4 is already the standard here:** DEP required it of the gas plant's own twelve
    emergency generators. Federal rules ask only Tier 2 of emergency engines this size.
- **The permit is under appeal.** Clean Air Council, PennFuture and Sierra Club appealed it to the
  Environmental Hearing Board on 2025-12-17. Among their grounds:
  - the site is in or within half a mile of Center Township, "a recognized Environmental Justice
    community";
  - DEP reviewed the gas plant without the data center campus it serves.

**For the scorecard and the brief:**
- **The gas plant's air is decided by DEP and the appeal, not by the data center's design.**
- **What the towns can ask of AWS is the diesel:** batteries, or Tier 4 engines like the gas
  plant's own, with tests logged in real time as the GRID requirements expect.
- **What they can ask in the agreement:** monitors near the nearest homes for PM2.5 and NO2,
  published. The nearest PM2.5 monitor is 24 km away.

## The tables

**1. The coal plant as it ran** (EIA, plant 3122; tons a year, and lb a MWh)

| Year | Generation, TWh | SO2, tons | NOx, tons | CO2, million tons | SO2, lb/MWh | NOx, lb/MWh | CO2, lb/MWh |
|---|---|---|---|---|---|---|---|
| 2013 | 10.54 | 114,245 | 17,309 | 11.11 | 21.67 | 3.28 | 2,106 |
| 2014 | 11.54 | 123,856 | 22,116 | 12.09 | 21.46 | 3.83 | 2,095 |
| 2015 | 9.04 | 98,263 | 18,030 | 9.65 | 21.75 | 3.99 | 2,135 |
| 2016 | 6.63 | 20,482 | 11,288 | 7.16 | 6.18 | 3.41 | 2,161 |
| 2017 | 5.12 | 5,587 | 4,904 | 5.54 | 2.18 | 1.92 | 2,165 |
| 2018 | 5.13 | 5,127 | 4,805 | 5.64 | 2.00 | 1.87 | 2,200 |
| 2019 | 6.83 | 7,717 | 4,374 | 7.44 | 2.26 | 1.28 | 2,181 |
| 2020 | 2.98 | 3,681 | 1,875 | 3.46 | 2.47 | 1.26 | 2,324 |
| 2021 | 4.44 | 4,736 | 3,144 | 4.94 | 2.13 | 1.42 | 2,227 |
| 2022 | 3.31 | 4,185 | 2,472 | 3.78 | 2.53 | 1.49 | 2,282 |
| 2023 | 1.01 | 737 | 620 | 1.22 | 1.45 | 1.22 | 2,399 |

Its SO2 fell after 2015. That fits the semi-dry scrubbers (NID) on Units 1 and 2, whose SO2 limits
DEP set in its 2013 and 2015 approvals; Unit 3 already had a wet scrubber.

**2. The gas plant as permitted** (4,678 MW; caps in tons a year; rates at full output all year,
41.0 TWh)

| Pollutant | Gas plant's cap | Its rate, lb/MWh | Coal plant 2014 | Coal plant 2021-22 | Cap against 2014 | Rate against 2014 |
|---|---|---|---|---|---|---|
| SO2 | 212 | 0.0103 | 123,856 | 4,460 | -99.83% | -99.95% |
| NOx | 1,143 | 0.0558 | 22,116 | 2,808 | -95% | -98.5% |
| CO2 (CO2e for the gas plant) | 17,551,454 | 857 | 12,092,728 | 4,357,535 | +45% | -59% |
| PM2.5 | 840 | 0.041 | (not in EIA) | 220 (application) | | |

CO 1,105, VOC 332 and hazardous air pollutants 57.1 tons a year are also capped.

**3. What reaches the ground** (DEP's review of the modelling: the worst point off the site, µg/m3)

| | The plant | Background (monitored) | Total | Standard | Total, share of the standard |
|---|---|---|---|---|---|
| PM2.5, annual | 0.86 | 6.8 | 7.66 | 9 | 85% |
| PM2.5, 24-hour | 4.55 | 19 | 23.55 | 35 | 67% |
| PM10, 24-hour | 6.53 | 54 | 60.53 | 150 | 40% |

**4. What each data center design adds** (the campus at 3,000 MW of IT; the gas plant's emissions
at its permitted rates for the energy each design draws; diesel tests at 24 h a year)

| Design | PUE | Energy, TWh a year | Share of the plant's full output | NOx from the gas plant, tons | PM2.5 from the gas plant, tons | CO2e, million tons | Diesel generators | Their NOx, Tier 2 / Tier 4, tons | Diesel NOx against the gas plant's |
|---|---|---|---|---|---|---|---|---|---|
| the old design (chillers and towers) | 1.196 | 25.1 | 61% | 701 | 515 | 10.8 | 1,320 | 335 / 35 | +48% / +5% |
| the cloud halls (outside air and pads) | 1.040 | 21.9 | 53% | 610 | 448 | 9.4 | 1,320 | 335 / 35 | +55% / +6% |
| the AI halls (liquid and towers) | 1.028 | 21.6 | 53% | 603 | 443 | 9.3 | 1,320 | 335 / 35 | +56% / +6% |
| the good neighbour (dry coolers, batteries) | 1.044 | 21.9 | 54% | 612 | 450 | 9.4 | 0 | 0 | - |

Tier 2 caps NOx and hydrocarbons together, so its figure is an upper bound for NOx. The gas plant's
figures are its permitted rates, also upper bounds.

## How it was done

- **The coal plant:** EIA's yearly "Emissions by plant" files, 2013-2023, for plant 3122
  (`data/eia_emissions_3122.csv`).
  - **The SO2 and NOx:** the "Selected" emissions (CEMS where reported).
  - **The trap:** the files repeat the plant-level columns on each of a plant's rows, so summing
    them doubles the plant. Only the per-row columns are summed (tests).
- **The gas plant:** the permit's facility-wide caps (condition #007), which include startups. A
  cap spread over a year at full output, 4,678 MW for 8,760 hours, is its permitted rate per MWh.
- **What reaches the ground:** DEP's summaries of the applicant's modelling and risk assessment,
  as published. Nothing is re-modelled here: without the model's inputs it wouldn't be credible.
- **The data centers:**
  - **The energy:** pass 2's module models at the scorecard's 3,000 MW of IT (IT energy times PUE,
    on the plant's typical weather year), at the gas plant's permitted rates.
  - **The diesel:** the scorecard's generators, 1.3 MW of backup per MW of IT in 3 MW sets, tested
    24 hours a year at half load. Their NOx at EPA Tier 2 (6.4 g/kWh, NOx plus hydrocarbons) or
    Tier 4 (0.67 g/kWh).
- **Tons are US short tons (2,000 lb),** as in DEP's permit.

## Checks

- **EIA against the application:** EIA's SO2 for the coal plant's last two years averages
  4,460.5 tons a year. The application's CEMS baseline, which DEP accepted, is 4,460.6. This runs
  in `brownfield check`.
- **The NOx credit:** EIA gives 2,808 tons a year for 2021-22. The application credits 2,032,
  discounted to the federal NOx rules (its Table 3-9).
  - **So the netting is conservative:** it counts less than the coal plant actually emitted.
- **The arithmetic** (tests):
  - the rates by hand;
  - each design's share of the caps;
  - Tier 4 against Tier 2 as the ratio of the standards.

## What we don't know

- **NO2 and ozone near the homes.** They were not modelled, because NOx netted out. The nearest
  monitors are far: PM2.5 at Strongstown, 24 km, and PM10 at Johnstown, 32 km.
- **How the plant will actually run.** The caps assume full output all year. The campus alone
  would take half or more of it, so the plant is unlikely to run much below that. Actual emissions
  will be reported, but aren't known yet.
- **AWS's own generators.** No air permit for them was found, so their number, size and tier
  aren't public. The figures here are the scorecard's.
- **The appeal.** The Environmental Hearing Board hasn't ruled. Its grounds include the
  environmental justice policy and reviewing the plant without the campus.
- **The coal plant's PM in its busy years.** EIA doesn't report PM. The application gives only
  2021-22.
- **Health beyond the standards.** The standards and benchmarks are thresholds DEP applies. The
  health effect of the added PM2.5 below them isn't estimated here.

## Sources

- **PA DEP, Homer City Generation, Air Quality** (DEP's Homer City page):
  - Plan Approval 32-00457A (final, 2025-11-18): facility caps (Section C, #007); Tier 4 for the
    emergency generators; 500 hours a year.
  - The technical review memo (2025-11-18): the turbines, 4,678 MWe, the netting, the stack
    heights (190 ft).
  - DEP's summary of the air quality analyses for PSD (2025-11-17), Tables 1, 3, 6, 8 and 10.
  - DEP's summary of the inhalation risk assessment (2025-11-17), Tables 3-5.
  - The comment response document (2025-11-18): the netting; the 1-hour SO2 nonattainment area and
    its 2023 plan; the environmental justice process.
- **The PSD application** (AECOM for Homer City Generation, revised August 2025), Tables 3-9 to
  3-11: the 2021-22 baseline and the netting.
- **EIA, Emissions by plant and by region,** 2013-2023 (https://www.eia.gov/electricity/data/emissions/).
- **The appeal:** Notice of Appeal, Clean Air Council, PennFuture and Sierra Club v. DEP,
  Plan Approval 32-00457A (Environmental Hearing Board, filed 2025-12-17; PennFuture's copy).
- **EPA engine standards:**
  - Tier 2, 40 CFR part 1039 appendix I, Table 2;
  - Tier 4, 40 CFR 1039.101 Table 1;
  - what emergency engines must meet, 40 CFR 60.4202.
