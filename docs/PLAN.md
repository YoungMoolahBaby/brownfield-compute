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
**Pass 3 done, 3b in progress (Jon: "go with pass 3", then "go with the apartment building in
CortenForge"): [docs/pass3/](pass3/README.md).** Step 1: the first house in CortenForge (`forge/`,
measured to its exact dimensions; found a mass_properties pitfall with flush cutters). Step 2: its
heat (`brownfield house`): 5.3 kW at design, 8.7 MWh of space heat a year; a radiant floor needs ~34
C water (43.5 C at the worst corner) against the data center's 50 C return: new homes heat straight
off the loop, no heat pump. Step 3 (pass 3b): a 12-flat, 3-storey walk-up in CortenForge (checked
to +0.31% / +0.08%; meshing it took 63 min with cf-design's default mesher, ~3.4 min with the
parallel adaptive one the `cortenforge` crate leaves off). A flat needs 3.98 MWh a year, under half
the house; per square metre 0.49 of the house, same as RECS 2020 (5+ unit apartments vs detached,
0.49); every flat runs on ~30 C water. Step 4, the money (`brownfield block`): the loop loses for
detached homes and townhouses. With real flats, apartments win against gas only for ~1,000 within
0.5 km of the campus (at most ~$0.9k per dwelling, ~4%; 32% of draws), and against a heat pump (an
all-electric neighbourhood) from 500 within 1 km or 1,000 within 1.5 km (up to ~$2.7k, ~12%; 66% of
draws). So: dense all-electric housing right against the campus costs residents about the same or a
little less; heat pumps for the existing town. Step 5 (3b, Jon: "commit, then start on the framing"):
the walk-up framed in wood (`brownfield frame` sizes it by NDS 2018 / APA / ASCE 7-16, reproducing
SFPA spans to 0.4 in. and APA I-joist spans within 2%; forge `framing` builds 3,027 members, none
overlapping): 11-7/8 in. I-joists (no sawn joist spans the 19 ft at L/480), 2x6 facade studs at 16
in. (ground floor limited by plate crushing), 2x4 spine rows at 12 in. on the ground floor; 51 m3 of
wood, 69 m3 of concrete. Step 6 (3b, Jon: "do the build sequence next please"): built in order in
sim-core (forge `build`, `brownfield build`, docs/pass3/build.gif): 138 wall panels (up to 16 ft) framed
flat and tilted up on a hinge servo (torque = statics within 0.4%): the heaviest, a sheathed end-wall
panel, 243 kg / 267 lbf at the top plate = a crew of 6 at NIOSH's 51 lb (4 before sheathing), no wall
jacks; cap plates and joists set as free bodies land within 0.11 mm; joists set before the spine fall
(132 of 142). Step 7 (3b, Jon: "Light steel and concrete block with precast floors on the same plan"):
light steel (SFIA tables, joist spans reproduced to 0.5 in.; 12 in. C-joists, 600S162 studs; 22 t,
crew of 5 per panel) and 8 in. block + 8 in. hollow-core planks (Oldcastle table, TMS ASD example to
0.09%; 475 t, footings 45 / 70 in., 142 crane picks of 1.9 t, ~12,200 blocks, floors 8 in. deep),
each built in CortenForge and sim-core; `brownfield compare`. Wood and steel are near twins; block +
precast is 20x heavier but thinner, quieter-floored (unmodelled) and noncombustible. Step 8 (Jon: "do
cost and embodied carbon next please"): `brownfield costcarbon`: A1-A3 carbon (CLF baselines via
Washington's code table) wood 32 t / steel 79 t / block + precast 97 t (2.6 / 6.6 / 8.1 t a flat;
wood lowest in 100% of draws); installed cost (low confidence) $0.36M / $0.52M / $0.48M ($30k /
$43k / $40k a flat; wood cheapest in 98%); wood framing $24.8/sq ft vs NAHB $26.8. Next: wind and
bracing, local bids, or pass 4.

**Pass 4 in progress (Jon: "push, then go with pass 4 please"): [docs/pass4/](pass4/README.md).**
`brownfield economy`: AWS's 1,500-2,000 staff bring ~120 renter households who'd live in Homer City
or Center Township (85-220), not the ~1,000 flats pass 3's warm loop needs; Homer City has 16 homes
for rent and ~209 rent-burdened renters (ACS 2019-23). A 2-bedroom walk-up costs ~$305k (HUD 2024
TDC, Johnstown): no flat pencils here, even at market rent (gap $183k), tax-credit flats leave $161k
(4%) or $47k (9%). The campus's property tax at build-out ~$96M/yr (AWS: no abatements; 25.899
mills, CLR 0.704, $600/sq ft taxable), $68M of it school tax (~3x Homer-Center's budget, can't buy
housing); the gap for every newcomer and every burdened household ~$55M. Steer: 100-250 mixed flats
at the campus edge, funded in the community benefits agreement.

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
- **D7** (2026-11-16) Architecture and craft. Jon: "do you want to show what you can do for
  architecture/elegance for this project?"; robots that build what "even the best builders would
  look at and be like 'yeah no fucking way i could build that'", with builders overseeing them;
  then "if we want to like make our own bricks for cheaper and make the molds/casts for that,
  cortenforge can do that." The steer:
  - Ornament went because skilled hours got expensive, not because builders couldn't make it. The
    target is detail no one could afford to build by hand, and what it costs is the result.
  - The data hall stays a plain, repeated box; the craft goes on the edge the town sees, on parts
    that do a job the scorecard measures.
  - First piece: pass 2's earth berm (10 dB and $1M per module, both placeholders) replaced by a
    patterned brick wall in front of the coolers, built in CortenForge and laid by a modelled arm
    in sim-core. Compared with the berm, a precast concrete wall, plain brick, hand-laid and
    robot-laid patterned brick, and units made on site from its coal ash or spoil in moulds
    designed in CortenForge; scored on cost, night sound at the nearest homes, land, embodied
    carbon and upkeep. In FHWA's barrier inventory brick and concrete cost about the same per
    square foot and berms about a quarter (RESEARCH.md).
  - A mason must be able to repair it: standard units and mortar.
  - The cultural case stays in the README's "Why"; reports say "architecture" and "craft".
- **D8** (2026-11-16) Jon: a city on cheap desert land, "like 1-5k an acre, has some sort of well
  water supply, and you could use rammed earth ... going big might be the right bet ... im not
  saying we should change the project". The steer, which Jon accepted ("for an actual town,
  having an effect on the the actual population of america, your correction is right"): the
  land is cheap because nothing is there, and land is a small part of what a town costs
  (California City, Arcosanti and Telosa all stayed mostly empty or on paper); desert
  groundwater runs out (Arizona paused new groundwater-only subdivision approvals around Phoenix
  in 2023, RESEARCH.md); dry coolers work worst in desert heat, and empty land has no grid
  connection. Rammed earth itself suits dry climates. Jon: the desert "might be good for some sort
  of earthship like those tire homes, just updated": an off-grid home, closer to mothership than
  to this project. Kept from it: making units on site in our own moulds (D7).

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
