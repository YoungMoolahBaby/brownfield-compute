# Pass 2f: the water budget

HCR says the whole campus, the gas plant and the data centers, will use water "in line with the
historical usage levels of the former coal plant". The towns' first question to AWS is how much
water the campus will use up ([township brief](../township-brief.md)). This follows the water from
Two Lick Creek Reservoir, through the plant, to the creeks:
- what the coal plant actually drew;
- what the gas plant and each data center design would draw;
- whether the reservoir can carry them through the droughts on record.

Run: `uv run brownfield water` (`src/brownfield/water.py`, `params/water.yaml`; the gas plant's
permit inputs in `params/creek.yaml`). It writes `out/pass2/water.md` and the figure below.

![Top: what each case draws from Two Lick Creek and uses up, against the coal plant's highest month (21 MGD) and the creek's natural low flow (6 MGD). Bottom: the reservoir through the 1952 drought: the coal plant as it ran stays above 70%, the gas plant's own condensers near 50%, DEP's intake falls to 12%, and with the AI halls' towers on top it runs dry for most of the autumn](water.png)

## What it says

- **"In line with history" compares maximum intake rates, not use.**
  - **The rates:** HCR's figures are 14 gallons a minute per MW for the coal plant and 5.9 for the
    gas plant. At each plant's size that is the same ~38 million gallons a day (MGD).
  - **The coal plant never drew near that.** EIA's records give 16.1 MGD in its busiest recent year
    (2014, at 69% of capacity) and 21.0 MGD in its highest month (June 2014). At full output it
    would have drawn ~23 MGD.
- **The gas plant's own condensers need about what the coal plant drew at full output.**
  - **By heat balance:** at full output, its condensers send ~2,070 MW of heat to the towers.
    Those towers evaporate ~17 MGD. With DEP's 6.84 MGD of blowdown, the plant draws ~24 MGD.
  - **The reservoir copes:** on that draw it falls to 49% in the 1952 drought of record. That is
    like the coal plant at full output (51%).
- **DEP's permit inputs are 12 MGD higher than that.** They give 36 MGD drawn and 29.2 MGD not
  returned.
  - **What the extra matches:** 12 MGD more evaporated is what towers rejecting ~1,460 MW more heat
    would use.
  - **One explanation that fits the filings:** AWS's filing says the data halls take "non-contact
    cooling water" from the station and return it "for reuse". If the station's towers carry part
    of the halls' heat, this is where it would show. It isn't established; HCR and AWS can say.
  - **What 36 MGD does to the reservoir:**
    - it falls to 12% in the 1952 drought and 16% in 2020;
    - it drops below half in 14 of the record's 73 years;
    - if only 13,000 acre-ft of the pool is usable, it runs dry for 31 days.
- **Towers at the data halls, on top of the gas plant, would empty the reservoir.**
  - **The draw:** liquid-cooled AI halls with their own towers, at 3,000 MW of IT, add ~27 MGD.
  - **The reservoir:** it runs dry in the 1952 drought and again in 1991. Over the 73 years it is
    short on 334 days.
  - **Indiana's water:** on 187 of those days it can't release even the consent order's 11 cfs at
    the dam. Indiana's water plant draws from the creek just below the dam.
  - **On top of DEP's 36 MGD,** the same towers leave it short on 949 days.
- **Dry coolers or outside air add almost nothing:** the good neighbour none, the cloud halls
  ~0.3 MGD.
- **Where the water goes.**
  - **The coal plant** returned what it didn't evaporate to Two Lick Creek.
  - **The gas plant** sends its blowdown to Blacklick Creek (Outfall 027).
  - **Two Lick Creek below the intake** carries only what is left down to the confluence: the 11
    cfs if the consent order holds there, or nothing if it binds only at the dam.

**For the scorecard and the brief:** at this site the creeks' case against cooling towers is also a
reservoir case. Towers for 3 GW of halls would need more water than the gas plant itself, from a
reservoir that already carries the gas plant and supplies Indiana's water plant below the dam.

## The tables

**1. The coal plant as it ran** (EIA, plant 3122)

| Year | Output, share of capacity | Drawn, MGD | Used up, MGD | Drawn, gal a MWh |
|---|---|---|---|---|
| 2014 | 69% | 16.1 | 14.9 | 511 |
| 2015 | 55% | 13.8 | 12.1 | 558 |
| 2016 | 40% | 10.5 | 9.8 | 580 |
| 2017 | 31% | 6.7 | 5.5 | 481 |
| 2018 | 31% | 6.4 | 4.9 | 456 |
| 2019 | 41% | 9.6 | 7.6 | 511 |
| 2020 | 18% | 4.7 | 3.2 | 582 |
| 2021 | 27% | 8.8 | 6.7 | 720 |
| 2022 | 20% | 6.4 | 3.9 | 701 |

Its highest month: 21.0 MGD drawn (June 2014). Its maximum intake rate, 14 gpm/MW (HCR), is
38.3 MGD.

**2. Each case against the reservoir** (16,240 acre-ft, 5,292 million gallons; daily, 1952-2025;
Two Lick Creek's natural Q7-10 at Graceton 9.1 cfs, 5.9 MGD)

| Case | Drawn, MGD | Used up, MGD | Returned to | Reservoir at its lowest | Lowest since the dam (1969-) | Years it falls below half | Days short | Of them, under 11 cfs at the dam |
|---|---|---|---|---|---|---|---|---|
| The coal plant as it ran in 2014, its busiest recent year (EIA) | 16.1 | 14.9 | Two Lick Creek | 69% (Oct 2020) | 69% (Oct 2020) | 0 | 0 | 0 |
| The coal plant at full output (2014's gallons a MWh) | 23.2 | 21.4 | Two Lick Creek | 51% (Dec 1952) | 52% (Oct 2020) | 0 | 0 | 0 |
| The coal plant's maximum intake rate (HCR's 14 gpm/MW) | 38.3 | | | 5% (Dec 1952) | 9% (Nov 2020) | 16 | 0 | 0 |
| The gas plant's maximum intake rate (HCR's 5.9 gpm/MW) | 38.2 | | | 5% (Dec 1952) | 9% (Nov 2020) | 16 | 0 | 0 |
| The gas plant's own condensers at full output (heat balance) | 23.9 | 17.1 | Blacklick Creek (Outfall 027) | 49% (Dec 1952) | 50% (Oct 2020) | 1 | 0 | 0 |
| The gas plant as DEP's permit inputs have it | 36.0 | 29.2 | Blacklick Creek (Outfall 027) | 12% (Dec 1952) | 16% (Nov 2020) | 14 | 0 | 0 |
| The gas plant's condensers, plus the good neighbour (dry coolers) | 23.9 | 17.1 | the creeks | 49% (Dec 1952) | 50% (Oct 2020) | 1 | 0 | 0 |
| The gas plant's condensers, plus the cloud halls (outside air and pads) | 24.2 | 17.3 | the creeks | 49% (Dec 1952) | 50% (Nov 2020) | 2 | 0 | 0 |
| The gas plant's condensers, plus the AI halls (liquid and towers) | 51.1 | 37.5 | the creeks | 0% (Oct 1952) | 0% (Oct 1991) | 32 | 334 | 187 |
| The gas plant's condensers, plus the old design (chillers and towers) | 55.6 | 40.8 | the creeks | 0% (Oct 1952) | 0% (Oct 1991) | 35 | 551 | 328 |
| DEP's intake, plus the AI halls' own towers | 63.2 | 49.5 | the creeks | 0% (Sep 1952) | 0% (Sep 1991) | 43 | 949 | 546 |

- **Days short:** the reservoir is empty, so the plant's draw and the flow kept below the intake
  can't both be met.
- **Under 11 cfs at the dam:** not even the consent order's release, just above Indiana's water
  plant.

**3. The same, with a smaller usable pool and with nothing left below the intake**

| Case | Central | Pool 16,240 -> 13,000 acre-ft | No flow kept below the intake |
|---|---|---|---|
| The gas plant's own condensers at full output (heat balance) | lowest 49%, 0 days short | lowest 37%, 0 days short | lowest 68%, 0 days short |
| The gas plant as DEP's permit inputs have it | lowest 12%, 0 days short | lowest 0%, 31 days short | lowest 34%, 0 days short |
| The gas plant's condensers, plus the AI halls (liquid and towers) | lowest 0%, 334 days short | lowest 0%, 689 days short | lowest 0%, 53 days short |
| DEP's intake, plus the AI halls' own towers | lowest 0%, 949 days short | lowest 0%, 1,462 days short | lowest 0%, 575 days short |

## How it was done

- **The coal plant:** EIA's thermoelectric cooling water data, monthly withdrawal and consumption
  for plant 3122, 2014-2023 (`data/eia_cooling_3122.csv`, derived from EIA's yearly summary files).
- **The gas plant's own condensers:** a heat balance at full output (4,500 MW, 62% efficient,
  7% of the fuel's heat up the stacks and 2.5% lost elsewhere). The rest goes to the towers, which
  evaporate 88% of it (pass 2's tower figure) at 2.43 MJ/kg, plus DEP's 6.84 MGD of blowdown.
  - **A check:** that implies 3.5 cycles of concentration, inside the 3-6 towers run at.
- **The data centers:** pass 2's module models at the scorecard's 3,000 MW of IT, as yearly
  averages.
- **Two Lick Creek's natural flow at Graceton** (USGS 03042500):
  - **Before the dam (to November 1968):** as measured.
  - **After it:** transferred from Blacklick Creek at Josephine (03042000, unregulated) by flow
    duration, month by month. Each day takes the same exceedance probability in each creek's
    flow-duration curve for that month (the QPPQ method). The curves are fitted on 1952-1968, when
    both creeks were gauged and neither was regulated.
  - **Why not scale by area:** Blacklick carries about twice Two Lick's low flow per square mile,
    probably from mine drainage. Scaling by area would put Two Lick's natural Q7-10 at 23.7 cfs,
    against 11.3 measured.
- **The reservoir:** a daily mass balance from full, in April 1952.
  - **Inflow:** its 74 mi2's share of the natural flow.
  - **Losses:** it spills when full and loses evaporation from its surface.
  - **Releases:** at least 11 cfs at the dam, and more when the plant's draw plus the flow kept
    below the intake exceeds the natural flow of the 97 mi2 between the dam and the gauge.
  - **The intake** is taken to be below the gauge (see the checks).

## Checks

- **The transfer, before the dam:** it gives Two Lick a Q7-10 of 11.5 cfs, against 11.3 measured
  (USGS publishes 11.3).
  - **The driest 90 days:** 16.9 against 15.8 cfs.
  - **The driest 180 days:** 37.5 against 30.3 cfs. The transfer is wetter in the longest
    droughts, so the reservoir results lean optimistic.
- **Split sample:** fitted to 1952-1960 only, it gives 12.9 cfs for 1960-1968, against 12.4
  measured.
- **Since the dam:** the gauge's mean flow is 302.6 cfs, against the reconstructed natural mean of
  304.8 (-0.7%). A reservoir moves water in time, not away.
  - **What it says about the intake:** a coal-plant-sized draw above the gauge would cut the
    gauge's mean by ~5-8%. The match is consistent with the intake sitting below it.
- **The coal plant's own months:** with EIA's monthly draws for 2014-2023, on that period's natural
  flows, the reservoir never falls below 89%. It carried the plant then, and the model agrees.
- **The mass balance** conserves water day by day (tests). All three checks run in `brownfield
  check`.

## What we don't know

- **AWS's cooling.** Whether any of the data halls' heat goes to the station's towers (the 12 MGD
  gap), and what the halls draw on their own. This decides every case above.
- **The reservoir's rules:**
  - its usable storage (USGS gives 16,240 acre-ft; the National Inventory of Dams lists 23,000 at
    the crest);
  - the consent order behind the 11 cfs and where it applies;
  - any drought plan for the plant's draw.
- **Where the gas plant's 29.2 MGD goes.** DEP's sheet gives intake minus Outfall 027. If other
  outfalls return some of it to Two Lick Creek, less is used up, though the reservoir still has to
  supply the full draw.
- **The draw's seasons.** Wet towers evaporate more in summer and the plant may not run flat out.
  Here every case draws its yearly average every day.
- **The lake's evaporation** is a placeholder (30 inches a year).
- **Smaller pieces left out:**
  - Yellow Creek Lake, upstream of the gauge, is treated as natural flow;
  - Indiana's water plant draws ~2.2 MGD just below the dam and returns most of it above the
    gauge through the borough's sewage plant: not counted.
- **A drying creek.** Blacklick's low flows have fallen over the record (pass 2e). The 1952 and
  1991 droughts may not be the worst ahead.

## Sources

- **EIA, thermoelectric cooling water data** (https://www.eia.gov/electricity/data/water/): "Water
  cooling by generator and boiler", summary files 2014-2023, plant 3122.
- **USGS:**
  - daily flows at 03042500 (Two Lick Creek at Graceton) and 03042000 (Blacklick Creek at
    Josephine), Water Data OGC API;
  - water data reports for 03042500 (WDR PA-01-3, PA-02-3): drainage area 171 mi2, regulated
    since December 1968 by Two Lick Creek Reservoir (capacity 16,240 acre-ft) and since July 1971
    by Yellow Creek Lake.
- **National Inventory of Dams,** PA00285 (Two Lick Creek): drainage area 191.7 km2, 23,000 acre-ft,
  510 acres.
- **HCR:** the Homer City Generation fact sheet on campus water usage (October 2026); the press
  release of 2025-04-02 (seven 7HA.02 turbines, up to 4.5 GW).
- **PA DEP:**
  - NPDES PA0005037 amendment A-2, fact sheet Attachment 2 (intake 36 MGD, consumptive loss 29.16
    MGD);
  - the 11 cfs consent order as quoted in GAI's memo (application Att. 8-2);
  - NPDES PA0000302 draft fact sheet (2025): Pennsylvania American Water's Two Lick Creek plant,
    just below the dam.
- **The method:** QPPQ (Fennessey 1994; Archfield and Vogel 2010).
- **The turbines:** 7HA.02 combined-cycle efficiency, 61.7-63.4% (GE catalog; Keentel's table).
