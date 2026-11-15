# Plan

**The question:** when a data center comes to a retired coal plant in a shrinking town, how should
it be designed so that the town comes out ahead? Answered with public data, against a conventional
data center on the same site.

## Status (2026-11-15)

**Pass 1 done (first full run): [docs/pass1/](pass1/README.md).** 205 coal plant sites, 154.8 GW
of coal leaving; both known cases pass (Homer City 3rd of 205 on *can host*, Bull Run 38th); 18
sites in the top quarter on both axes. Jon picked **Homer City** for pass 2 (D6).

**Pass 2 v1 complete: [docs/pass2/](pass2/README.md).** Per 100 MW module at Homer City:
water 1.05 million gallons a day vs none; PUE 1.20 vs 1.04; 13% of the heat to 5,000 homes and
10 ha of greenhouses; 40 dB(A) at night beyond ~700 m vs ~120 m (oversized dry coolers + berm);
44 diesel gensets vs batteries.

**Pass 2b, costs (Jon: "price it first"): [docs/pass2/cost.md](pass2/cost.md).** Operator: ~$56M
less up front and ~$14M a year saved per module, +$129-201M over 20 years (positive in every
Monte Carlo draw, negative only in the all-worst corner); the heat network alone loses ~$159M;
together a coin flip (+$42M central, 51%). Hydrogen backup ~$380M vs diesel ~$72M (Jon asked).
Then (Jon: "yes run it") against the STRONGEST designs: vs a liquid-cooled AI hall with towers the
good neighbour costs ~$13-15M more per module over 20 years (zero water, quieter; ahead in 18%);
vs an AWS-style air + evaporative cloud hall it's about even (PUE 1.040 vs 1.039, almost no water
either way at Homer City). So "better at the same cost" held only against the old design; dropping
diesel is the site's option; the town's heat needs its own funding.
AI (Jon: "can good neighbor be used for ai"): yes, it is an AI design; premium over liquid + towers
~$14M per module over 20 years, ~$7M if chips take 45 C water, ~$31M if they need 32 C (cost.md s3).
FIRMED UP (pass 2c, Jon: "firm up pass 2 first"): [docs/pass2/firm-up.md](pass2/firm-up.md):
sensitivity ranking (`brownfield sensitivity`), homes around the campus from county parcels
(`brownfield homes`: 109 within 300 m of the edge, 259 within 700 m, nearest ~20 m), water priced
from a PA tariff, tower fans checked against ASHRAE 90.1, chip coolant from GB200 specs. Premium
over AI towers now ~$17M per module (ahead in 12%); conclusions stand.
Next: Jon's call, pass 3 (CortenForge, new homes on low-temperature heat) or vendor quotes.

## Decisions

- **D1** (2026-11-15) Jon asked for "a repo modeling and building a house in cortenforge". He
  chose an example house first (then his own), both a buildable design and a simulated build,
  three structural systems compared on one plan, public. Scoped: 24 x 40 ft, one storey, 6:12
  gable, on a cold-climate stand-in site under Minnesota code loads. Superseded the same day by
  D2-D4 before any code; the example house becomes the first house of pass 3.
- **D2** (2026-11-15) Jon: "should we do like a data center? maybe like a livable one? and then
  like architect it around complaints with modern data center? like the usage of resources,
  noise, etc? then we can even power it with the nuclear fusion stellarator?"
- **D3** (2026-11-15) Jon: "a city based around a data center. like how china builds cities at a
  time ... find a bunch of worthless land, land that needs to be cleaned/reclaimed, then model a
  data center then a city around it ... plan/simulate it upfront, then it can be a megaproject all
  in one ... a bunch of affordable housing around the economy of the data center/fusion project
  ... give value to land that is deserted, dying"; also a community center, hospital, therapy
  buildings, research institutions; "a civil engineering/architectural probiotic. for humans and
  AI operating in harmony/synergy"; "a bridge to the mothership".
- **D4** (2026-11-15) Jon asked for a firm steer toward something that will be taken seriously.
  The steer, and why:
  - **One question first, the city later.** A hyperscale data center has a few dozen to a few
    hundred permanent jobs, a fusion plant hundreds more: a town's worth, not a city's. What a
    data center brings is power, fiber, waste heat and a large tax base, so it pays for things
    while other employers (hospital, research, manufacturing) fill a town.
  - **China proves building speed, not demand.** Shenzhen grew; Ordos Kangbashi and many new
    districts stood empty, and overbuilding fed the property crash. The bottleneck is people
    choosing to come, and China's speed rests on state-owned land and state banks.
  - **Plan up front, then build fast, in modules.** This part of Jon's idea is what the
    megaproject research supports (Flyvbjerg and Gardner, *How Big Things Get Done*, 2023): the
    projects that come in on budget plan long with detailed models, then build fast, and repeat a
    small unit. So the unit here is one data hall plus one neighbourhood block, repeated.
  - **Fusion is an option, not a foundation.** No fusion plant has made net electricity yet;
    Infinity Two is aimed at the mid-2030s, and one-off giant plants are the projects that most
    often blow up (nuclear, Olympics in Flyvbjerg's data).
  - **Residents own and vote.** Company towns: Hershey worked, Pullman ended in a national strike.
  - **Retired coal plants are the right land**, and real developers already agree (Bull Run,
    Homer City), which gives the screen a check.
  - **CortenForge does the buildings** (pass 3 on). City-scale work is mostly GIS, energy,
    economics and transport, written here and logged in `docs/CORTENFORGE.md` as gaps.
- **D6** (2026-11-15) Jon picked **Homer City, PA** for pass 2 ("homer city"), then noticed "it
  looks like this is already getting developed". Kept, because it is: AWS filed a 39-building
  campus plan with Indiana County (August 2026), a Community Benefits Agreement is still to be
  written under the state's GRID standards, and DEP is reviewing a water permit for up to 6.8
  million gallons a day into Two Lick and Blacklick Creeks at up to 110 F (RESEARCH.md). So pass
  2 is independent public analysis of what a good-neighbour design would deliver on this site,
  measure by measure, against what is planned, while those decisions are open. Tone: factual,
  their published numbers cited, nothing about their design guessed.
- **D5** (2026-11-15) Name `brownfield-compute`; Python (uv) for the model, Rust + CortenForge
  under `forge/` from pass 3; Apache-2.0; public on GitHub when Jon says push.

## Pass 1: site screen (done 2026-11-15, first full run)

Goal: a ranked, mapped list of US coal plant sites, retired or set to retire, with what each
offers a data center and what its town needs. Jon picks the case-study site from the top.

1. **Plant universe** from EIA-860M (monthly generator inventory; September 2026 release, EIA,
   2026-10-23): coal generators that retired, or have a planned retirement year, grouped by plant:
   coal MW (a proxy for the size of the grid connection), years retired, what still runs there,
   coordinates, county, balancing authority.
2. **Known cases** present and correct in that list: Bull Run (TN), Homer City (PA). Naughton
   (WY) dropped: EIA lists it still burning coal, one unit converted to gas (RESEARCH.md).
3. **Town**: county population change, Census 2010 to July 2025 estimates, and median household
   income (SAIPE 2024). Bulk files: the Census data API now needs a key.
4. **Climate** (PVGIS typical year): hours too hot for dry coolers, and heating degree days (how
   much waste heat a town could use).
5. **Flood**: FEMA flood zone at the plant (coal plants sit on rivers).
6. **Rank** on two axes kept separate, *can host* and *would help*, with every component shown.
   Then the check: do the known cases rank high on *can host*?
7. **Report**: `docs/pass1/` with the map, the table and what we don't know (interconnection
   rights after retirement, coal ash, fiber, land ownership).

## Pass 2: the good-neighbour data center at Homer City (v1 complete 2026-11-15)

One 100 MW (IT) module, conventional vs good neighbour, same weather (PVGIS typical year at the
plant), same load, same power (the site's gas plant, so the difference is the data center).

1. **Site facts** (done, RESEARCH.md): AWS's filed plan, the water fact sheet, the water permit
   hearing. To do: homes in reach (Census counts for Indiana and Homer City boroughs), nearest
   homes to the six AWS sites, coal ash on the site.
2. **Water and heat, hour by hour** (v1 done, `uv run brownfield module`, `src/brownfield/module.py`,
   `params/pass2.yaml`): conventional 1.05 million gallons a day withdrawn per module (2.08 L/kWh,
   inside the published 1.55-2.8), PUE 1.196 without electrical losses; good neighbour no water,
   PUE 1.042, 14% of the heat delivered to 5,000 homes and 10 ha of greenhouses. Many inputs are
   placeholders (fan power, heat pump COP, liquid share): source them next.
3. **Checks**: the heat side against Meta's Odense heat recovery (45 MW of heat pumps, 100,000
   to 215,000 MWh a year, 6,900-12,000 homes); heat pump COP from a published large unit.
4. **Noise** at the nearest homes (ISO 9613-2), both designs, against WHO night guidelines.
5. **Backup power**: diesel testing hours and emissions vs batteries.
6. **Jobs and taxes**: AWS's 1,500-2,000 permanent staff, 50 per building at the peak shift.
7. **Report** `docs/pass2/`: the scorecard side by side, and what we don't know.
8. **Costs** (pass 2b, done): `uv run brownfield cost`, `src/brownfield/cost.py`,
   `params/cost.yaml`; two ledgers (operator, heat business), Monte Carlo, worst corner,
   hydrogen backup as a third option (Jon, 2026-11-15: "what about hydrogen instead of
   batteries?").

## Later passes

3. The first neighbourhood module: heat network, greenhouse, the first house (D1's example
   house), in CortenForge.
4. The economic base: employers, housing cost, hospital access.
5. Fusion-ready: a 350 MWe stellarator plant on the site.

## Carried over from the house scoping (D1)

Researched 2026-11-15, for pass 3: Minnesota ground snow load 60 psf in the northern counties
listed in Minn. R. 1303.1700, 50 psf elsewhere; frost footing depth 5 ft (Zone I) or 3.5 ft
(Zone II) by county (Minn. R. 1303.1600); span checks for `forge` against the SFPA species
comparison (2013): SPF No.2 floor joists at 16 in., L/360, 10 psf dead: 2x10 at 30 psf live
17-2, 2x12 at 40 psf live 17-10 (see RESEARCH.md; both reproduced by hand).
