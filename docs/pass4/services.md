# Pass 4b: where the tax goes, the schools, and the hospital

Pass 4 left open "the hospital, schools and services a growing town needs", and the scorecard's
"hospital access" was unfilled. Scoping them turned up a mistake in pass 4 first. The campus
straddles a township line, and with it a school district line.

Run: `uv run brownfield services` (`src/brownfield/services.py`, `src/brownfield/districts.py`,
`params/services.yaml`). It writes `out/pass4/services.md` and the figure below.

![Left: pupils in Homer-Center (766 in 2025-26, down from 873 in 2017-18) and River Valley (1,429, down from 1,634 in 2014-15), with the newcomers' children as a dot on each: +85 and +31. Right: the campus's school tax at today's millage against each district's 2023-24 budget: Homer-Center $33.0M against $19.5M, River Valley $32.6M against $35.8M](services.png)

## What it says

- **Half the campus is in another school district.**
  - **The correction:** pass 4 taxed all 39 buildings at Center Township's rates, so all the
    school tax went to Homer-Center.
  - **The lines:** the Census Bureau's township and school district lines and the county's master
    plan put 51% of AWS's buildings in Black Lick Township:
    - West and Harvey/Gaston wholly;
    - about half of Bruner;
    - small parts of Helen and Green.
  - **The district:** Black Lick Township is in the River Valley School District (formerly
    Blairsville-Saltsburg).
  - **At 2026 millage** the campus's ~$92M a year divides as:
    - Indiana County $22.6M;
    - Center Township $2.8M and Black Lick Township $1.0M;
    - **Homer-Center $33.0M and River Valley $32.6M.**
  - **The total** falls from pass 4's $96M because Black Lick's side has lower rates.
- **Each district's share is about the size of a whole district.**
  - **Homer-Center:** $33.0M against its 2023-24 revenue of $19.5M.
  - **River Valley:** $32.6M against $35.8M.
  - **Where it goes:** a Pennsylvania district levies one millage on all its property, so the
    money mostly comes back as a lower millage for everyone.
    - **At today's spending,** everyone else's school real estate tax would fall by about 90% in
      Homer-Center and 81% in River Valley: the campus would be 90% and 81% of each district's
      market value.
- **State aid would fall, and it doesn't change the answer.**
  - **The aid ratio:** PDE's market value / personal income aid ratio, recomputed with the
    campus's value, falls from 0.71 to 0.34 in Homer-Center and from 0.65 to 0.31 in River Valley.
    State money that follows a district's relative wealth would fall with it.
  - **The worst case:** even if every dollar of state revenue were lost ($11.3M and $20.0M),
    everyone else's real estate tax would still fall by 68% and 42%.
- **The schools have room for the newcomers.**
  - **The children:** D18's 242 homes bring ~117 school-age children.
    - ~85 to Homer-Center, from Homer City, Lucerne Mines, Graceton and Coral: ~6.6 a grade
      against ~59.
    - ~31 to River Valley, from Black Lick: ~2.4 a grade against ~110.
  - **The space:** both districts had more pupils within the last decade: Homer-Center 873 in
    2017-18 (now 766), River Valley 1,634 in 2014-15 (now 1,429).
- **The hospital is close; serious trauma is not.**
  - **Indiana Regional Medical Center's emergency department** is 9-17 minutes by car from the
    towns. It became a Level IV trauma centre on 1 January 2026.
  - **The nearest Level I centre,** Conemaugh Memorial in Johnstown, is 44-48 minutes from the
    towns and 49-60 from AWS's sites.
  - **The same whichever design is built.**
- **What the campus adds is demand on fire and EMS, not on the hospital.**
  - **The build:** ~12,900 worker-years on site from 2026 to 2036. At BLS's construction rates
    that is ~300 recorded injuries and illnesses, and ~1 death, over the decade; ~76 injuries in
    the peak year.
  - **Its backup:** either ~975 MWh of batteries (the good neighbour) or ~1,320 diesel generators
    and their fuel (the others). Both are what a fire company plans for.
  - **The county's capacity:** its director of emergency management has written that "funding a
    full-time emergency medical service can't be done with raffle ticket sales, bingo and chicken
    dinners" (PublicSource, 2025-05-05).

**For the brief:**
- **River Valley belongs at the table** alongside Homer-Center.
- **The agreement should pay for the emergency services before the build:** fire training and
  equipment for battery and fuel fires, and a campus emergency plan with the county.
- **The design doesn't change the hospital's minutes.**

## The tables

**1. Where the tax goes** (AWS's 39 buildings by township and school district; pass 4's tax at
full build-out)

| Site | Township | School district | Buildings |
|---|---|---|---|
| Bruner | Black Lick township | River Valley | 6.1 |
| Bruner | Center township | Homer-Center | 5.9 |
| Helen | Center township | Homer-Center | 3.6 |
| Helen | Black Lick township | River Valley | 1.4 |
| Green | Center township | Homer-Center | 4.6 |
| Green | Black Lick township | River Valley | 0.4 |
| West | Black Lick township | River Valley | 7.0 |
| Harvey/Gaston | Black Lick township | River Valley | 5.0 |
| Rura | Center township | Homer-Center | 5.0 |

| Taxing body | Mills (2026) | A year |
|---|---|---|
| Indiana County | 6.105 | $22.6M |
| Center Township | 1.530 | $2.8M |
| Black Lick Township | 0.521 | $1.0M |
| Homer-Center School District | 18.2639 | $33.0M |
| River Valley School District | 17.16 | $32.6M |
| **Total** | | **$92.0M** |

**2. The schools** (PDE, October 1 enrolment; the newcomers' children from D18's homes)

| District | 2025-26 | Most since 2014-15 (year) | Room against that | Pupils a grade now | Newcomers' children | A grade |
|---|---|---|---|---|---|---|
| Homer-Center | 766 | 873 (2017-2018) | 107 | 59 | 85 | 6.6 |
| River Valley | 1,429 | 1,634 (2014-2015) | 205 | 110 | 31 | 2.4 |

**3. The money** (each district's 2023-24 revenue, PDE; its share of the campus's school tax at
today's millage; the aid ratio recomputed with the campus's market value)

| District | Revenue | State | Real estate tax | Campus's school tax | Aid ratio now (PDE) | With the campus | Everyone else's share of the market value | Their real estate tax, same spending | If all state aid were lost |
|---|---|---|---|---|---|---|---|---|---|
| Homer-Center | $19.5M | $11.3M | $5.27M | $33.0M | 0.7125 | 0.3406 | 10% | $0.53M (-90%) | $1.67M (-68%) |
| River Valley | $35.8M | $20.0M | $9.67M | $32.6M | 0.6470 | 0.3104 | 19% | $1.84M (-81%) | $5.64M (-42%) |

**4. The hospital** (car minutes, free-flow, by the public OSRM router; not an ambulance's)

| From | Indiana Regional (ED, Level IV) | Nearest Level I or II trauma centre | Its minutes |
|---|---|---|---|
| Homer City | 11 | Conemaugh Memorial Medical Center (I) | 45 |
| Graceton | 13 | Conemaugh Memorial Medical Center (I) | 48 |
| Coral | 14 | Conemaugh Memorial Medical Center (I) | 48 |
| Lucerne Mines | 9 | Conemaugh Memorial Medical Center (I) | 46 |
| Black Lick | 17 | Conemaugh Memorial Medical Center (I) | 44 |
| AWS Bruner | 27 | Conemaugh Memorial Medical Center (I) | 60 |
| AWS Helen | 21 | Conemaugh Memorial Medical Center (I) | 54 |
| AWS Green | 19 | Conemaugh Memorial Medical Center (I) | 52 |
| AWS West | 27 | Conemaugh Memorial Medical Center (I) | 55 |
| AWS Harvey/Gaston | 25 | Conemaugh Memorial Medical Center (I) | 53 |
| AWS Rura | 16 | Conemaugh Memorial Medical Center (I) | 49 |

## How it was done

- **The split:** each site's drawn building pixels on the county's master plan, already fitted to
  the ground for D17 (`land.aws_sites`), placed in the Census Bureau's TIGERweb county
  subdivisions and unified school districts. Each site's share of the filing's 39 buildings is
  divided by where its pixels fall (`data/aws_buildings_districts.csv`). The township and school
  district lines coincide here.
- **The tax:** pass 4's campus value ($600 a sq ft of taxable real property, the county's common
  level ratio). Each side is at its own 2026 millage from the county's sheet.
- **The schools:**
  - **Enrolment:** PDE's October 1 counts (its 10-year file, and the 2014-15 and 2025-26 files by
    grade; `data/pde_enrollment_districts.csv`).
  - **Money:** PDE's Annual Financial Report summaries for 2023-24, the last year both districts
    are in.
  - **Market value:** the 2023 STEB market value from the same file.
  - **The newcomers' children:** each town's middle placed in a district, with D18's per-town
    children.
- **The aid ratio:** PDE's published formula, MV/PI AR = 0.6 x MV AR + 0.4 x PI AR, with
  MV AR = 1 - 0.5 x (district / state market value per weighted pupil).
  - **The state's per-pupil figures** are implied by PDE's own file.
  - **The floors** are those in the file: 0.10 for each part and 0.15 combined.
  - **The test:** the campus's market value is added and the ratio recomputed.
- **Everyone else's tax:** with one millage across the district, each owner's share of the school
  real estate tax is its share of the district's market value (STEB's, which equalizes across
  counties).
  - **At constant spending,** everyone else pays their share of today's real estate tax.
  - **With all state aid lost,** they pay their share of today's real estate tax plus the lost
    aid.
- **The drive:** the public OSRM router's car times, free-flow, from each town's middle and each
  AWS site's centre (cached in `data/raw/care/`).
  - **The hospitals:** OpenStreetMap's locations, and the Pennsylvania Trauma Systems Foundation's
    trauma levels (`data/hospitals.csv`).
- **The build:** the workforce model's monthly workers on site, 2026-2036, with BLS's 2023
  construction rates: 2.3 recorded injuries and illnesses per 100 full-time workers, 9.6 deaths
  per 100,000.

## Checks

- **PDE's aid ratios recomputed** from its own file's market value, income and weighted pupils:
  0.7126 for Homer-Center against PDE's 0.7125, and 0.6472 for River Valley against 0.6470. This
  runs in `brownfield check`.
- **The millage:** each side's county, township and school mills add to the county sheet's totals,
  25.899 and 23.786 (`brownfield check`).
- **The split** covers all 39 buildings, each site once (tests). The tax by hand on a 50/50 split
  (tests).
- **The drive:** Homer City to Indiana Regional is 11 minutes and 9.1 km by road, against 7.5 km
  in a straight line.

## What we don't know

- **Where Bruner's buildings fall.** It straddles the township line, 51/49 on the drawn plan. The
  plan's fit to the ground agrees within ~5 m (D17), and the deeded parcels aren't public. A few points either
  way moves the split between the districts.
- **The assessment.** $600 a sq ft is a judgement, and the tax runs $46-215M a year across it.
  Every dollar here scales with it.
- **The state aid's exact dollars.** Which programs follow the aid ratio, and by how much, isn't
  worked out here. The bound is each district's whole state revenue.
- **Building capacity.** Neither district publishes it. The decade's peak enrolment is a floor
  on what the buildings held.
- **When the money comes.** The tax arrives building by building over ten years. The aid ratio
  lags the market value by two years.
- **Ambulance response times.** These are car times. Neither the ambulance services' times nor the
  fire companies' staffing were found.
- **Who covers the site:** the fire companies and the ambulance service for each part of the
  campus, and the campus's own emergency plan.

## Sources

- **Census Bureau, TIGERweb:** county subdivisions (layer 22) and unified school districts (layer
  14), queried 2026-11-18.
- **Indiana County Assessment Office, 2026 millage sheet** (updated 7/16/2026;
  https://www.indianacountypa.gov/wp-content/uploads/School-2026-Millage.pdf):
  - "Blacklick Township - R/V": 6.105 / 0.521 / 17.16;
  - Center Township: 6.105 / 1.530 / 18.2639.
- **PDE:**
  - public school enrolments (October 1, the 10-year LEA file and the yearly files);
  - Annual Financial Report summaries, 2023-24 (revenues by source; taxes collected and STEB
    market value);
  - aid ratios 2025-26 and the aid ratio calculation methodology.
  - River Valley SD carries Blairsville-Saltsburg's AUN, 128321103.
- **Pennsylvania Trauma Systems Foundation:**
  - December 2025 board update: Indiana Regional Medical Center an adult Level IV trauma centre
    from 2026-01-01;
  - the list as of 2025-04-23, as reported by WJET (Conemaugh Memorial, UPMC Presbyterian, AHN
    Allegheny General and UPMC Mercy Level I; AHN Forbes Level II).
- **OpenStreetMap** (Nominatim) for the hospitals' locations; the **OSRM** public router for the
  drives.
- **BLS:**
  - Survey of Occupational Injuries and Illnesses, 2023: construction 2.3 per 100 FTE (as reported
    by Construction Dive);
  - Census of Fatal Occupational Injuries, 2023: construction 9.6 per 100,000 FTE (as reported by
    AGC).
- **PublicSource** (2025-05-05; https://www.publicsource.org/coal-gas-transition-homer-city-pennsylvania/), on
  Homer City's coal-to-gas transition: the county's director of emergency management on EMS
  funding.
