# Pass 2f: the water budget

HCR says the whole campus, the gas plant and the data centers, will use water "in line with the
historical usage levels of the former coal plant". The towns' first question to AWS is how much
water the campus will use up ([township brief](../township-brief.md)). This follows the water from
Two Lick Creek Reservoir, through the plant, to the creeks:
- what the coal plant actually drew;
- what the gas plant and the data centers would draw, by heat balance and as filed with DEP;
- whether the reservoir can carry them through the droughts on record.

Run: `uv run brownfield water` (`src/brownfield/water.py`, `params/water.yaml`; the gas plant's
permit inputs in `params/creek.yaml`). It writes `out/pass2/water.md` and the figure below.

![Top: what each case draws from Two Lick Creek and uses up, against the coal plant's highest month (21 MGD), the intake's pumps (37.6 MGD) and the creek's natural low flow (6 MGD). Bottom: the reservoir through the 1952 drought: the coal plant as it ran stays above 72%, the gas plant's own condensers near 58%, with the data centers as filed 53%, the intake's pumps at full capacity fall to 7%, and with the AI halls' towers on top it runs dry from late October](water.png)

## What it says

*Revised 2026-11-18 (D24) from the station's own water balance in its NPDES renewal application
(May 2026). The first version read DEP's 36 MGD as the gas plant's need and asked whether the
data halls' heat was in it. The filing shows the halls' water as a separate, small stream, and
36-37.6 MGD as the intake's ceiling.*

- **"In line with history" means the same intake, not the same use.**
  - **The intake** has four 8,700 gpm pumps, three of which run at most: 37.6 million gallons a
    day (MGD). It "will not be modified"; the pumps are replaced in kind. HCR's 14 and 5.9 gallons
    a minute per MW come to the same ~38 MGD for both plants.
  - **The coal plant never drew near that.** EIA's records give 16.1 MGD in its busiest recent
    year (2014, at 69% of capacity) and 21.0 MGD in its highest month (June 2014). At full output
    it would have drawn ~23 MGD.
- **The station's filed water balance gives the data centers 1,400 gallons a minute.**
  - **The drawing** (D-352-1801, design maximums) splits the intake's 37.6 MGD:
    - 34.35 MGD to the station's towers and service water;
    - 2.0 MGD (1,400 gpm) to the "tenant cooling equipment", the data centers, with 0.58 MGD
      (400 gpm) returned to the station's towers;
    - 0.66 to the boilers and 0.57 back to the creek as screen wash.
  - **What the data centers use up:** at most 1.44 MGD. Evaporated, that carries ~174 MW of heat:
    6% of a 3,000 MW campus's. The rest would have to leave dry, through dry coolers or outside
    air. That is close to what the township brief asks for. The ask now is to make it binding.
- **DEP's 36 MGD is the intake's ceiling, not the gas plant's need.**
  - **The filed figures fill the pumps.** The towers are to run at 5 cycles of concentration. At
    that, the drawing's 34.9 MGD of tower makeup gives 6.98 MGD of blowdown (Outfall 027 is 6.84)
    and 27.9 MGD evaporated.
  - **That is more than the plant's heat calls for.** Evaporating 27.9 MGD takes ~3,380 MW of heat.
    By heat balance the condensers send ~2,070 MW at full output. DEP's inputs (36 drawn, 29.16 not
    returned) sit just under the same ceiling.
  - **The filing says as much:** "The total makeup water rate would remain the same" as the coal
    plant's (316(b) report, p.3-4).
- **The gas plant's own condensers need about what the coal plant drew at full output.**
  - **By heat balance:** at full output, ~2,070 MW of heat to the towers, which evaporate ~17 MGD.
    At 5 cycles the plant draws ~21 MGD.
  - **The reservoir copes:** at worst it falls to 57% (October 2020).
  - **With the data centers as filed:** 22.8 MGD drawn, and the reservoir's lowest is 53%.
- **At the intake's ceiling every day, the reservoir would run low.**
  - **The record:** 7% in the 1952 drought and 12% in 2020. It drops below half in 15 of the
    record's 73 years.
  - **With a smaller pool:** if only 13,000 acre-ft is usable, it runs dry for 53 days.
  - **Read it as a bound:** the plant would draw at the ceiling only on its hottest, busiest days.
- **Towers at the data halls are beyond this intake.**
  - **The draw:** liquid-cooled AI halls with their own towers, at 3,000 MW of IT, add ~27 MGD. On
    top of the gas plant's condensers that is 48.6 MGD, more than the three pumps can draw. They
    would need a new intake and new approvals.
  - **The reservoir:** it would run dry in the 1952 drought and again in 1991, short on 196 days
    in 73 years. On 17 of them it couldn't pass even what Indiana's water plant draws just below
    the dam.
  - **Dry coolers or outside air add almost nothing:** the good neighbour none, the cloud halls
    ~0.2 MGD.
- **Where the water goes, at design maximum.**
  - **Blacklick Creek:** 6.84 MGD of blowdown at Outfall 027.
  - **Two Lick Creek:** 4.32 MGD at Outfall 001, below the low dam (2.74 in July), part of it
    treated landfill leachate. Another 0.57 MGD of screen wash goes back at the intake.
  - **Used up:** 25.9 MGD (27.4 in July).
  - **The coal plant** returned what it didn't evaporate to Two Lick Creek.
- **Two Lick Creek below the intake keeps 11 cfs.** A consent order (Docket 81-060-W) requires
  that flow "over the Two Lick dam located downstream of the HCGS intake", the low dam that holds
  the intake's pool (renewal application).

**For the scorecard and the brief:**
- **The filing already plans the halls around little water.** The towns can ask AWS and HCR to cap
  the halls at the filed 1,400 gpm and to publish the metered figures. The state's yearly data
  center report will require water use and peak-day demand from 2027.
- **Towers at the halls would need a new intake.** They would draw from a reservoir that already
  carries the gas plant and supplies Indiana's water plant below its dam.

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

| Case | Drawn, MGD | Used up, MGD | Returned to | Reservoir at its lowest | Lowest since the dam (1969-) | Years it falls below half | Days short | Of them, under 2.2 MGD at the dam (Indiana's draw) |
|---|---|---|---|---|---|---|---|---|
| The coal plant as it ran in 2014, its busiest recent year (EIA) | 16.1 | 14.9 | Two Lick Creek | 70% (Oct 2020) | 70% (Oct 2020) | 0 | 0 | 0 |
| The coal plant at full output (2014's gallons a MWh) | 23.2 | 21.4 | Two Lick Creek | 52% (Dec 1952) | 52% (Oct 2020) | 0 | 0 | 0 |
| The coal plant's maximum intake rate (HCR's 14 gpm/MW) | 38.3 | | | 5% (Dec 1952) | 10% (Nov 2020) | 15 | 0 | 0 |
| The gas plant's maximum intake rate (HCR's 5.9 gpm/MW) | 38.2 | | | 5% (Dec 1952) | 10% (Nov 2020) | 15 | 0 | 0 |
| The gas plant's own condensers at full output (heat balance) | 21.4 | 17.1 | Blacklick Creek (Outfall 027) | 57% (Oct 2020) | 57% (Oct 2020) | 0 | 0 | 0 |
| The station at its intake pumps' capacity, as filed (with the data centers' makeup) | 37.6 | 25.9 | both creeks (Outfalls 001, 002, 027) | 7% (Dec 1952) | 12% (Nov 2020) | 15 | 0 | 0 |
| The gas plant's condensers, plus the data centers as filed (1,400 gpm in, 400 back) | 22.8 | 18.5 | the creeks | 53% (Dec 1952) | 54% (Oct 2020) | 0 | 0 | 0 |
| The gas plant's condensers, plus the good neighbour (dry coolers) | 21.4 | 17.1 | the creeks | 57% (Oct 2020) | 57% (Oct 2020) | 0 | 0 | 0 |
| The gas plant's condensers, plus the cloud halls (outside air and pads) | 21.6 | 17.3 | the creeks | 57% (Oct 2020) | 57% (Oct 2020) | 0 | 0 | 0 |
| The gas plant's condensers, plus the AI halls (liquid and towers) * | 48.6 | 37.5 | the creeks | 0% (Oct 1952) | 0% (Nov 1991) | 29 | 196 | 17 |
| The gas plant's condensers, plus the old design (chillers and towers) * | 53.0 | 40.8 | the creeks | 0% (Oct 1952) | 0% (Oct 1991) | 34 | 428 | 41 |

- **Days short:** the reservoir is empty, so the plant's draw and the consent order's 11 cfs over
  the low dam below the intake can't both be met.
- **Under 2.2 MGD at the dam:** the reservoir can't pass even what Indiana's water plant, just
  below it, draws.
- **\*:** more than the intake's three pumps can draw (37.6 MGD), so it would need a new intake.

**3. The same, with a smaller usable pool and with 11 cfs kept at the reservoir's dam too**

| Case | Central | Pool 16,240 -> 13,000 acre-ft | 11 cfs also at the reservoir's dam |
|---|---|---|---|
| The gas plant's own condensers at full output (heat balance) | lowest 57%, 0 days short | lowest 47%, 0 days short | lowest 57%, 0 days short |
| The station at its intake pumps' capacity, as filed (with the data centers' makeup) | lowest 7%, 0 days short | lowest 0%, 53 days short | lowest 7%, 0 days short |
| The gas plant's condensers, plus the data centers as filed (1,400 gpm in, 400 back) | lowest 53%, 0 days short | lowest 42%, 0 days short | lowest 53%, 0 days short |
| The gas plant's condensers, plus the AI halls (liquid and towers) | lowest 0%, 196 days short | lowest 0%, 546 days short | lowest 0%, 200 days short |

## How it was done

- **The coal plant:** EIA's thermoelectric cooling water data, monthly withdrawal and consumption
  for plant 3122, 2014-2023 (`data/eia_cooling_3122.csv`, derived from EIA's yearly summary files).
- **The gas plant's own condensers:** a heat balance at full output (4,500 MW, 62% efficient,
  7% of the fuel's heat up the stacks and 2.5% lost elsewhere). The rest goes to the towers, which
  evaporate 88% of it (pass 2's tower figure) at 2.43 MJ/kg. Blowdown is the evaporation over
  (cycles - 1), at the 5 cycles the 316(b) report gives for the new towers.
- **The station as filed:** the flows on drawing D-352-1801 (`params/water.yaml`, `filed`), all
  design maximums.
  - **One label is off:** the drawing labels the data centers' makeup "1,400 GPM, 2.88 MGD", but
    1,400 gpm is 2.02 MGD. The gallons a minute are used, since they are what adds up to the intake
    (396 + 1,400 + 23,851 + 455 = 26,102 of 26,100).
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
  - **Releases:** at least 2.2 MGD at its dam, what Indiana's water plant draws just below it
    (a placeholder: no release rule at that dam is public). More when the plant's draw plus the
    11 cfs kept over the low dam below the intake exceeds the natural flow of the 97 mi2 between
    the dam and the gauge.
  - **The intake** is below the gauge (see the checks).

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
  - **Where the intake is:** the 316(b) report places it 1.1 km south-west of the gauge,
    downstream.
- **The filed balance closes:** its gallons a minute add up to the intake. At 5 cycles its tower
  makeup gives 6.98 MGD of blowdown, against Outfall 027's 6.84 (tests).
- **The coal plant's own months:** with EIA's monthly draws for 2014-2023, on that period's natural
  flows, the reservoir never falls below 89%. It carried the plant then, and the model agrees.
- **The mass balance** conserves water day by day (tests). The flow and reservoir checks run in
  `brownfield check`.

## What we don't know

- **AWS's cooling equipment.** The filing gives the water the station will supply the halls, not
  what uses it, and not the campus's load. Nor does it say whether the halls take water from
  anywhere else, such as a public water system.
- **The reservoir's rules:**
  - its usable storage (USGS gives 16,240 acre-ft; the National Inventory of Dams lists 23,000 at
    the crest);
  - any release rule at its own dam (here a placeholder, what Indiana's water plant draws);
  - the text of the consent order behind the 11 cfs (Docket 81-060-W, not posted);
  - any drought plan for the plant's draw.
- **The draw's seasons.** Wet towers evaporate more in summer, and the plant may not run flat out.
  Here every case draws its yearly average every day.
- **Why the filed tower figures exceed the heat balance.** Hot days, duct firing and design
  margin could each account for part of it. The split isn't public.
- **The lake's evaporation** is a placeholder (30 inches a year).
- **Smaller pieces left out:**
  - Yellow Creek Lake, upstream of the gauge, is treated as natural flow;
  - Indiana's water plant returns most of what it draws above the gauge, through the borough's
    sewage plant: not counted.
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
- **The station's NPDES renewal application** (GAI Consultants for Homer City Generation, May
  2026; DEP's Homer City page, "NPDES Renewal Application"):
  - the narrative: the 11 cfs "over the Two Lick dam located downstream of the HCGS intake" (p.7);
    the intake "will not be modified" (p.10); the permit list (Consent Order and Agreement, Docket
    81-060-W, "Two Lick Dam (flow requirements)");
  - Attachment 7, drawing D-352-1801 rev 29, "NPDES Permit - Proposed Water Balance/Sampling
    Diagram" ("All flows are design maximums unless otherwise noted");
  - Attachment 9, ASA's 316(b) report (February 2026): the pumps and the 37.6 MGD design intake
    flow, the 2017-2021 actual intake flow, the intake's location, 5 cycles of concentration.
- **PA DEP:**
  - NPDES PA0005037 amendment A-2, fact sheet Attachment 2 (intake 36 MGD, consumptive loss 29.16
    MGD);
  - NPDES PA0000302 draft fact sheet (2025): Pennsylvania American Water's Two Lick Creek plant,
    just below the dam.
- **Indiana's draw:** ~2.2 MGD (Indiana Gazette via Yahoo News, 2026).
- **The method:** QPPQ (Fennessey 1994; Archfield and Vogel 2010).
- **The turbines:** 7HA.02 combined-cycle efficiency, 61.7-63.4% (GE catalog; Keentel's table).
