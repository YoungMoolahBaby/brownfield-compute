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
10 ha of greenhouses; 40 dB(A) at night beyond ~700 m vs ~220 m from the cooler yard behind a
berm (first given as ~120 m; corrected in pass 2d) or 34-80 m with walled cells; 44 diesel
gensets vs batteries.

**Pass 2d, the wall (D7; Jon: "commit, then do both please, start with the wall"):
[docs/pass2/wall.md](pass2/wall.md).**
- **Acoustics.** `brownfield wall` sizes the cooler yard from the makers' data: 175 units, about
  109 x 116 m, fans at 2.9 m. By ISO 9613-2's barrier method pass 2's 10 dB berm is worth ~1 dB
  at 300 m. Walls between every second row and across every second unit ("cells") take ~12 dB
  off across the rows and ~6.5 off the ends, and pass the makers' well rule (1.75 of 2.03 m/s).
- **The wall.** Brick pier and panel to TMS 402-16 under ASCE 7-16 wind, checked against BIA
  45A, TEK 14-19B/14-15B, Caltrans and MECA examples. Forge `wall` builds it brick by brick (face
  bricks turned up to 13° in a ripple, every joint and bearing checked), and a gantry in sim-core
  lays it: 1.84 s a brick with the pattern or without.
- **Cost and carbon per module.** Brick cells by robot $5.43M (P10-P90 $5.0-6.5M), by hand
  $5.83M plain or $6.60M patterned; precast cells $6.04M (robot brick cheaper in 51% of draws);
  6 m berm $2.25M but only ~1 dB. Bricks from the site's coal ash: not ready.
- **Hearing record:** [docs/hearing-record.md](hearing-record.md). The full records are of the
  gas plant, not the data centers. People raise jobs, water, noise, bills and taxes, but more
  often process, the creek, the gas plant's air, monitoring, wells and cleanup. No one raised
  how the campus looks, housing or hospitals.

Pass 2b rerun with the walls (2026-11-16, Jon: "yes go with 1 then 2 please"): the premium over AI
towers grows from ~$17M to ~$22M per module over 20 years.

**Pass 2e, the creek: [docs/pass2/creek.md](pass2/creek.md).**
- **The check.** `brownfield creek` reproduces DEP's Outfall 027 temperature limits exactly (19
  of 19, and the first draft) from its public Thermal Limits Spreadsheet, then reruns them with
  the creek's measured temperatures (USGS, 2013-2024; July's median 74.7 F, already above the 74 F
  criterion) and Blacklick's own low flow (23.1 cfs, the outfall being above the Two Lick
  confluence).
- **What changes.** With both corrections the applicant's projected 85 F blowdown is over the limit
  in February, June, July and December (December 66.2 F). An 85 F discharge switched on at once
  would break the 2 F-an-hour rule in 11 of 19 periods. Over the 2013-2024 record, the creek
  would be warmer than DEP's own target on 10-11% of days and 27-34% of July days.
- **The scorecard.** A conventional module adds ~0.26 MGD of its own blowdown; the good neighbour
  none.

Next: the site's ASCE wind speed (Hazard Tool); a timed mason mock-up of the turned face; candidate
scorecard measures (hearing record) for Jon; the renewal permit for Outfall 027 when DEP drafts it.

**Pass 3c IN PROGRESS (2026-11-16), the winter garden and campus (D9, to write up):**
- **Jon's direction:** "stone and light" and a public winter garden, then "it definetely should be
  fallingwater inspired". Then: the whole campus nice, not a mask on a plain box; no trees near
  buildings (roots); one connected building; no walls on the roof. Approved the result: "thats what
  im talking about!"
- **Built (uncommitted):**
  - `forge/src/scene.rs`: renderer with a sun, shadow map (slope bias, focus box), perspective
    with near clip, glass, stencilled pool reflections and exposure. `scene-check` gives the shadow
    within 0.5% of h/tan.
  - `forge/src/garden.rs` (mode `garden`; renders to `out/pass3/renders/<stamp>/`, copied to
    `docs/pass3/`):
    - one stone data hall, 122 x 129 m;
    - coolers on its roof deck (14 m) in rows with sedum strips between, behind a 3 m stone
      parapet;
    - stone piers, ochre bands and towers;
    - the Fallingwater-inspired winter garden built into its south face: trays, tray 1 900 mm deep;
      a hearth tower up the hall's face; pools with a 2.4 m fall (moved whole to the community
      center on 2026-11-17, D15; the hall's front now holds the great doors);
    - trees at least 10 m from anything built.
  - `src/brownfield/garden.py` with `params/garden.yaml`: heat 36-64 MWh/yr; floor water 23-31 C
    against the ~50 C loop.
- **Findings:**
  - **Cantilever (ACI 318):** a 600 mm tray sags 44 mm long-term against a 23 mm limit, which is
    Fallingwater's own failure (sag up to ~7 in., an $11.5M program); 900 mm passes at 20 mm.
  - **Rooftop noise (`brownfield garden`):** a 3 m parapet plus low-noise fans (-6 dB) gives at
    most 37.0 dB(A) at any distance.
    - Corrected the same day: like for like, pass 2d's walled ground cells are quieter at the
      distances where homes are. With pass 2 fans the cells are above 40 dB(A) out to 32-76 m,
      the roof to 221 m.
    - So the roof meets the guideline because of the fans, which would help the cells equally.
    - The roof was chosen for the building (one roofed hall, no walls), not for noise.
- **Done since:** the rooftop noise check is in `brownfield garden` (`rooftop_noise`, `ground_cells`)
  with `tests/test_garden.py` (8 tests).
- **To do:**
  - Cost and carbon, from the research notes: Sheffield Winter Garden GBP 3,570/m2 (2002); WVDOT
    concrete $1,695/CY; stone $36-49/ft2 (low conf); NSI stone EPD; IGU 42 kg/m2.
  - An orbit GIF.
  - `docs/pass3/garden.md`, including "the machines' side" from the food research notes:
    - rooftop isolators (cooling towers 3.0-4.5 in., UH spec; the ASHRAE table rows not found);
    - G1 copper 300 / silver 200 A/month, ISO class 8;
    - W40/W45 water classes, 25 um loop filtration (OCP 2025).
  - D9, CORTENFORGE (no instancing; DC-mesh striping on flat slabs; eq_active; our scene renderer
    walks row spans now), README.

**Pass 3d IN PROGRESS (2026-11-16), winter food (D10): [docs/pass3/food.md](pass3/food.md).**
- `brownfield food` (`food.py`, `params/food.yaml`, `tests/test_food.py`, 8 tests);
  `climate.hourly_weather` adds PVGIS sunlight.
- Design point: 43.5 ha of lit tomato glasshouses per 100 MW module, heated straight off the 50 C
  return (twice the usual pipe), with a 200 m3/ha tank.
  - 24% of the module's heat; a third with the town network.
  - 29,500 t a year, the fresh tomatoes of 3.4 million people (more than Pittsburgh); 478 jobs.
  - Lamps 84 GWh a year (+11% electricity), 29 MW at peak.
  - Margin before overheads $17M a year on the module's heat, against $10M on gas; 35,000 t CO2 a
    year saved.
- Lettuce loses money at field prices.
- Known cases: the yield is calibrated on Leamington. The model's heat is 24% above Ontario
  growers', and it overstates the lit/unlit gain (1.49 against 1.27).
- Stellarator (option): the lamps are 8% of its output; its rejected heat could carry ~330 ha more.
  The limit is the market.
- Forge `garden` draws the houses from `out/pass3/food.json`, plus the arboretum of 8 native
  species set back by NHBC zones x mature height.
- Research notes (scratchpad `food_inputs.md`) are folded into params and RESEARCH is still to do.
- **To do:** RESEARCH.md entries; SCORECARD rows (food grown, lamp power, heat put to use); README.

**Pass 3e IN PROGRESS (2026-11-16), the neighbourhood (D11): [docs/pass3/village.md](pass3/village.md).**
- `brownfield village` (`village.py`, `params/village.yaml`, 10 tests) writes out/pass3/village.json.
- forge `village.rs` draws the townhouses, the spine and streets, the square, the food hall, the
  glasshouse, the community center (ice, roller hockey, courts) and the fields, plus a three-look
  facade study.
- The real land (D17, [land](pass3/land.md)): AWS's six sites mapped from the county's master plan on
  public data. The conference ([conference](pass3/conference.md)) is the towns already there.
  - D18: the newcomers are shared by the towns' people (each grows ~15%) and laid out at each town's
    edge on the real ground.
  - Two clubhouses (Homer City, Black Lick) and the arena are the members' home grounds.
  - forge `conference` draws it all on the real terrain.
- Phase 1 (D16): 242 homes in rings from pass 4's newcomers. 121 flats in 11 walk-ups nearest
  the centre, 98 townhouses, then 23 houses; the nearest are 258 m from the hall.
- The neighbourhood takes 16.8 GWh a year with the heated walks (D14) and the hall's warm basins (D15),
  peaking at 10.4 MW; tomato houses go 43.5 -> 38.5 ha.
- A home's heat over 20 years: $23k on the loop if the operator pays for the network, $32k for a
  heat pump.
- A townhouse ~$441k as a price against ~$360k affordable at the median income.
- The shared places cost $63.4M to build; the trust's share is $1.4M a year. Running them costs
  $3.2M a year, about $32 a month from 7,200 members after leagues and ice (D16).
- Sewage binds growth at ~1,350 homes.
- **To do:**
  - Jon to choose the townhouses' look;
  - check the held-back sources;
  - RESEARCH.md entries for D11's cases and the village inputs;
  - SCORECARD rows: homes heated within a 10-minute walk, and a home's heat against gas.

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
over AI towers now ~$17M per module (ahead in 12%); conclusions stand. Rerun with pass 2d's
walls ($5.4M in place of the $1M berm, 2026-11-16): premium over AI towers ~$22M (ahead in 6%),
operator vs the old design +$194M, both ledgers +$35M (49%).
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
housing; corrected by D26: $92M, the school tax split $33M Homer-Center and $33M River Valley); the gap for every newcomer and every burdened household ~$55M. Steer: 100-250 mixed flats
at the campus edge, funded in the community benefits agreement.

**Pass 3f SCOPED (2026-11-19), the bid set as data (D27).** The walk-up goes out to bid as an
open model (IFC4) with a machine-checked list of what a bid set must carry (buildingSMART's IDS).
Its window schedule and elevations are generated from that model, and a made-up addendum is run as
a reviewed change: an element-level diff, the checks rerun, the drawings regenerated. All of it is
set against the same building issued as PDFs only. It is not an exchange and not construction
documents. Jon: a window quote needs every field on the list in D27. The spike passed (D27 step
0), and forge now writes the whole walk-up with a stable id on every opening (step 1).
`brownfield bidset` writes it as IFC4 and holds the file to forge's model on every check (step 2).
A second reader, That Open's web-ifc, reads the same building on every export. The IDS (step 3)
asks for the 32 fields a quote needs, and the model carries 8 of them. IBC 2018 2406.4.1-2406.4.3
call for safety glazing in 36 openings, 24 of them windows (type W2). The one stair is allowed
(IBC 2018 Table 1006.3.3(1)) only with sprinklers and an escape window in every bedroom, 16 of
them upstairs. Whether a window clears 1030's sizes depends on its operation, which the model
lacks. The schedule, elevations and quantities now come from the IFC alone (step 4). A made-up
RFI and Addendum 1 ran as a reviewed change (step 5): 36 elements changed, safety glazing fell
from 36 openings to 12, and every check passed on the revision. As PDFs only (step 6), bidding
means counting 114 tags by eye, and the addendum means finding 40 changed places on 3 sheets; the
data side lists them. The report is [docs/pass3/bidset.md](pass3/bidset.md) (step 7). Seen in
3D (2026-11-20): the model has no stair, no hall floors upstairs, and no doors into the 12 flats,
so the door schedule lists 13 of the shell's 25 doors; the report now says so. IBC 2018 1010, 1011, 1014,
1015, 1019, 1023 and 716 are now read (Jon saved UpCodes' chapters 7 and 10) and in
`params/bidset.yaml`. Next: model the stair and the flats' 1-hour doors. Waiting on Jon: the rep
test. Then the township brief's ask.

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
    carbon and upkeep. In FHWA's 2010-dollar barrier table brick and concrete cost about the same
    per square foot and berms about a quarter; corrected 2026-11-16: FHWA's 1963-2022 averages in
    2022 dollars put brick at $55, precast at $43 ($47 in 2020-22) and berms at $12 (RESEARCH.md).
  - Found in pass 2d: Gantenbein's bricks were glued, not mortared. The wall here stays mortared
    (repairable); robots lay brick in mortar (SAM, Monumental), though not yet turned brick.
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
- **D9** (2026-11-16) The campus as one building. Jon: "stone and light", a "public winter garden",
  "it definetely should be fallingwater inspired"; then "i dont want it to look decieving. we should
  just build nice things ... even if its a data center"; no trees near buildings ("the roots could
  potentially hurt the building"); the buildings connected; no walls on the roof. Approved: "thats
  what im talking about!" Built as one stone hall with its coolers on the roof behind a 3 m parapet,
  the garden on its town face. Steers: the terraces sized to ACI 318 (Fallingwater's sagged); the
  roof chosen for the building, not for noise (like for like the ground cells are quieter).
- **D10** (2026-11-16) Winter food. Jon: "im just trying to maximize that warm air going to
  something inspiring/usefful", "i definetely think it should be put into growing food in the
  winter", "native pa trees outside would look great", and "the stellarator in the future, so we
  will estimate that into this model where energy might take away from anything"; "this amount of
  compute is a blessing or a curse. and we need to honor it like a blessing". The steer:
  - Winter food needs light: the lamps' electricity is the energy that "takes away", shown in the
    model.
  - The stellarator stays an option (CLAUDE.md): it covers the lamps and more heat, and nothing
    depends on it.
  - The market, not the heat, is the limit (AppHarvest).
  - The machines' health is engineering: vibration under rooftop coolers, intake air near the gas
    plant and ash site, loop water quality, lightning on the towers.
- **D11** (2026-11-16) The neighbourhood at the campus edge (next pass, to plan). Jon: "personally id wanna live by
  this place ... a foodcourt order for the robot to bring me my fresh produce ... that data center is heating my
  house in the winter, the gym ... id be thankful for the data center"; then homes "around the garden ... apartment
  buildings like what we built", a food court where "a robot chef makes you meals with food directly from the
  garden", "a seedbank given what people have been ordering, so it knows what to plant", a community center with
  roller hockey, basketball, volleyball and pickleball courts, real grass fields for soccer and football, an ice
  hockey rink; "basically like an entire town, just scaled down"; no pool ("theyre kind of sketchy"); "if we plan for
  homer city its gonna be like a dollar tree and a snap fitness"; the food "should be vegetarian". The steer:
  - Amenities sized for the region (Indiana County's 83,000, the university 13 km away, Pittsburgh an hour off),
    which the campus's property tax and the benefits agreement can carry, used even if no one moves.
  - Housing in phases that follow demand: the first 100-250 flats around the garden (pass 4's floor); each next
    phase once the last fills. Pass 4 gets a scenario for people moving for the place (Tulsa Remote, Ascend WV).
  - Robots assemble (as Sweetgreen's Infinite Kitchen does today), cooks oversee; full robot chefs aren't there.
  - Orders steer a small market-garden house (greens, herbs, strawberries turn in weeks), not the big tomato
    houses (planted a year ahead on contracts).
  - Heated natural-grass fields (as at Lambeau Field) on the capped ash site, subject to DEP's closure terms; the
    rink makes heat rather than using it; summer heat otherwise goes to the dry coolers, using no water.
  - Vegan menu (Jon: "honestly i think it should be vegan"), built round the houses; staples (grains, beans,
    flour) bought from Pennsylvania farms. Risk to watch: an all-vegan food hall draws fewer regulars in a rural
    county, so it has to be the best food in the county, not a niche; track phase 1's sales.
  - Checks: rooftop-cooler noise at upper-floor windows; walk times; heat by month; cost and who pays.
  - Later the same day (Jon):
    - Homes face greens with big trees ("neighborhoods with big trees") and native gardens rather
      than lawns ("yards are dumb").
    - One greenhouse, with the vegan food court at its entrance "like in costco".
    - Pickleball and golf simulators indoors.
    - One real-grass field, multi-use, with a walking loop; a dome or field house only if bookings
      show demand.
    - Proposed: the data hall's front as a monument with a working, steaming basin instead of a
      temple; the Fallingwater garden on the community center ("the beloved 3rd space"), both
      built on 2026-11-17 (D15); a golf short course on the ash cap (Old Works, Anaconda MT, as
      precedent), still open.
  - The community center, later still (Jon):
    - A bouldering section, and a traverse wall in the gym.
    - The makerspace joined to the sports ("every sport would use the makerspace. especially hockey
      which at an elite level is half engineering"): a clean sports lab facing the rink and courts
      through glass (skate sharpening with extraction, sticks and fitting, 3D printing,
      electronics, sensors, video), with the heavy shop behind a fire wall, its own extraction and
      its own outside door.
    - Open 24 hours ("the center should be 24 hours as a whole"): the campus works around the clock
      (data hall, gas plant, greenhouse shifts), and people there all night are D12's natural
      surveillance.
    - Rules: key-card access as at 24-hour gyms; staff trained in first aid at night; the heavy
      shop at night only for members signed off on each machine, with a second person present;
      short overnight closures to resurface the ice; hours for under-18s.
    - Running costs (staff, including the night shift) are still to model.
  - Housing type (Jon, the same day): narrow townhouses "san fran style" with an air gap between them, not flats,
    so one household's noise never reaches another's sleep; modest size; a two-car garage at ground level that
    doubles as a private workshop, two or three storeys above; workouts shared at the community center ("people
    usually like to wrench alone, but people like to work out by eachother"). The steer:
    - About 3 m between houses (1.5 m each side of the lot line) lets the side walls have windows; narrower
      gaps mean fire-rated, mostly blank side walls (IRC R302.1), as in San Francisco.
    - Twin walls with an air gap and no ties between them give nearly the same quiet at higher density and lower
      cost: model both, draw Jon's first.
    - A 25 ft (7.6 m) lot fits the garage and a door; 100-250 homes still sit within a few hundred metres of
      the garden, as pass 3's loop needs. Detached houses lose more heat (more of the module's heat used; garages
      heated off the loop too) and cost more per home than the walk-up; townhouses suit buyers where pass 4
      found mostly renters, so phase 1 may mix them.
    - Also a shared shop bay at the community center (Men's Sheds show some like to wrench together).
  - Then (Jon): the shared shop is "a shenzhen x aussie makerspace/garage": the hardware-prototyping side
    (electronics benches, 3D printers, CNC, a parts counter) with the Men's Shed side (wood and metal, a car lift,
    a welder), heated off the loop; each home keeps "your own customizable 2 car garage" for small projects,
    "introvert tinkering" or storage. Both housing options are in: detached with a gap, and twin walls with an
    air gap between them. Idea to test, not a promise: the makerspace as where local people learn to run and
    repair the machines that build and look after the campus (D7).
  - Mixing, not an enclave (Jon OK'd 2026-11-16; real cases, to cite in the pass's report):
    - Living next door doesn't make people mix. Shared places, one set of rules and one voice, and
      regular small groups do.
    - Cases:
      - Chicago's mixed-income developments: little interaction; owners had an association and renters
        didn't (Chaskin & Joseph, J. Urban Affairs 33(2), 2011).
      - About half the rich-poor friendship gap is never sharing the same groups (Chetty et al., Nature
        608, 2022).
      - Contact reduces prejudice, most with equal status and common goals (Pettigrew & Tropp, JPSP
        90(5), 2006; 515 studies).
      - Pullman, where people could only rent, was ordered by the Illinois Supreme Court (1898) to sell
        its houses; in Hershey people could buy.
      - New York banned separate "poor doors" in 2015.
    - Design changes:
      - A public street from the town straight to the square, lined by the new homes; no gates or
        private roads.
      - The shared places run by one body with renters, owners and townspeople on it; the operator
        funds, and a trust, co-op or the township runs them.
      - First option on homes for current Homer City and Indiana County residents.
      - The housing mix a rule for every phase in the benefits agreement.
      - Leagues, classes and makerspace projects, and a welcome for newcomers.
      - Amenities priced for the town.
    - Still to check before citing: Columbia MD's segregation figures (an advocacy source), and
      reporting on Starbase TX.
  - Running the shared places (Jon OK'd 2026-11-16; real cases, to cite in the pass's report):
    - Shared places last when the money can't be switched off by one party and their users run them by
      clear rules.
    - Each single source of money fails on its own: membership fees alone (TechShop closed all its US
      sites in 2017), volunteers alone (burnout), yearly gifts from an operator (the town comes to
      depend on them), land with no owner (neglect).
    - Cases:
      - Ostrom's design principles, well supported across 91 studies as tendencies, mostly for natural
        resources (Cox, Arnold & Villamayor Tomas, Ecology and Society 15(4):38, 2010).
      - Public money with its own vote: Minneapolis's elected park board (1883, its own levy); the
        Seattle Park District (2014).
      - Back alleys gated for the adjoining homes in Liverpool: burglary down ~37% (Bowers, Johnson &
        Hirschfield 2004).
    - Design changes:
      - Two streams the operator can't switch off: an endowment and maintenance reserve paid up front
        under the benefits agreement, and a set share of the campus's property tax. The model sizes it
        as pass 4 sized the housing share.
      - Gifts from the operator only on top; small user fees, low or none for county residents on low
        incomes.
      - A nonprofit trust or a township authority owns and runs the places: renters, owners,
        townspeople and the township on the board; the operator one seat, not control.
      - Each place has its own users' committee and a paid lead.
      - Makerspace: tool sign-offs, members' cleanup rules with small penalties first, free open hours
        for county residents.
      - Courts, rink and fields: a public booking calendar, drop-in hours, a cap for each league, some
        slots for county youth.
      - The garden and arboretum: a paid gardener and a friends group.
      - The trust serves the whole county, so the old town's parks don't decline beside the new ones.
      - Every metre of the strips between townhouses belongs to one home, with a recorded easement for
        the neighbour (twin walls leave almost none).
    - Still to check before citing: the Men's Sheds funding history, library makerspace staffing, the
      Central Park Conservancy critiques, and the zero-lot-line code example.
  - Who owns the heat loop (Jon OK'd 2026-11-16; real cases, to cite in the pass's report):
    - Customer- or town-owned networks with cost-based, published prices keep trust and prices in
      check. Private sales raised prices, mostly through the fixed charge. Homes stay warm when the
      heat source stops only if the network owns its own backup.
    - Cases:
      - Denmark's Heat Supply Act (1979): non-profit pricing, prices equal to costs; consumer co-ops and
        municipal companies supply most of its district heat; the regulator (Forsyningstilsynet)
        publishes every network's prices.
      - Sweden after 1996: many towns sold networks and prices rose. Private networks charge ~7% more
        than municipal ones, mostly in the fixed part (Lundin, IFN WP 1532, 2025).
      - The UK: Ofgem has regulated heat networks since January 2026, with last-resort directions to
        keep heat on.
      - Pennsylvania: the PUC already regulates Philadelphia's steam network (Vicinity), with a
        cost-based rate.
      - Odense: Meta's heat goes into Fjernvarme Fyn's network, and Fyn owns the heat pumps.
      - Mantsala, Finland (2022): the data center lost grid power in a dispute and put in little or
        no heat; the town's utility heated the town on oil and gas.
      - 107 Swedish industrial excess-heat deals: ~6% of recovered heat lost to closures (Werner &
        Lygnerud, Energy 151, 2018).
    - Design changes:
      - The operator pays to build the network; a customer co-op or a municipal or joint authority
        owns the pipes, heat pumps and backup. The data center sells heat into it and never owns the
        network serving homes.
      - Cost-based prices in the bylaws or the benefits agreement, published yearly, with a
        replacement reserve; the fixed charge capped and its make-up published.
      - A price ceiling: no home pays more a year than with its own efficient heat pump. The model
        tests it with pass 3's comparison.
      - Backup, owned by the network, sized to heat every home with the data center fully off. The
        model adds its cost.
      - A long heat contract with a notice period and a bond that pays for backup heat if the data
        center leaves early; a named step-in party in the benefits agreement.
      - Expect PA PUC regulation; to confirm with a PA utility lawyer, including for a co-op or an
        authority.
    - Still to check before citing: the Danish share of heat (a trade-association figure), the
      Odense household count, and the Mantsala reporting (DCD, The Register).
  - The construction-workforce surge (Jon OK'd 2026-11-16; real cases, to cite in the pass's report):
    - A surge hits renters first, the town's costs arrive before its tax money, and the bust leaves
      peak-sized housing empty. Towns recover in about a decade. Local hiring shrinks the surge.
    - Cases:
      - Abilene TX (Stargate, 2024-27): rents up ~50% in a year, RV parks spreading, waits to rehouse
        people from shelters from ~1 month to up to 6 (news reporting).
      - The Bakken: Williston's population roughly doubled; Watford City got $10M of the $190M it asked
        the state for (Raimi & Newell, RFF 2016).
      - Oil-patch rents fell 15-20% in two months in 2015.
      - Delta UT recovered on most measures about a decade after its boom (Brown, Dorius & Krannich,
        Rural Sociology 70(1), 2005).
      - Homer City's gas plant already had 1,800+ workers on site in September 2026 (company figures:
        ~95% local, "local" undefined).
      - Norris TN: built by the TVA for dam workers, later a town.
      - PA's Act 13 (2012) shale impact fee: a precedent for local funding.
    - Design and timing changes:
      - A local-hiring target and training in the benefits agreement, "local" defined, the share
        published quarterly.
      - Peak worker lodging on campus land: modular, paid for by the operator and contractors, with site
        transport, and removed or converted afterwards. The land reserved for later phases can carry it
        during the build.
      - Permanent homes sized to the long-run jobs.
      - Phase 1 opens before the AWS peak, with first option to current local renters.
      - An impact fund for police, EMS, schools and roads, paid before the surge.
      - Short-term-rental rules and lease protections as far as PA law allows.
      - A public dashboard from day one, with thresholds that release more of the fund.
      - Trades compete with the campus, so build early or budget a premium.
      - The model treats the out-of-town peak as a range.
  - Whether the benefits agreement holds (Jon OK'd 2026-11-16; real cases, to cite in the pass's report):
    - Agreements with powerful developers hold when government can enforce them, the money is tied to
      the land and paid early, the developer's own benefits depend on delivery, the community side is
      independent and paid, a monitor publishes the numbers, and the agreement binds the next owner.
    - Cases:
      - Atlantic Yards (2005): a private agreement with soft targets that faded (mostly critics'
        accounts).
      - Enforcement of these agreements is untested in court (Been, U. Chicago Law Review 77(1), 2010).
      - Pittsburgh's Hill District (2015): a LERTA tied ten years of property tax on the site to the
        land, so the money outlasted a developer's exit (Next City 2026).
      - Foxconn WI: credits only after jobs were shown, renegotiated from 13,000 jobs to 1,454.
      - Data center owners appeal assessments (Cook County cuts of 24-90% sought; Amazon's appeal in
        Canton MS denied, 2026).
      - The Dalles OR fought for 13 months to keep Google's water use secret; it had roughly tripled
        since 2017.
    - Design changes:
      - The agreement is part of the township's land-use approval, with the community coalition a party
        too.
      - Payments tied to the parcels (a LERTA-style district) and the first years prepaid.
      - The operator's tax treatment and later permits conditional on delivery, with clawbacks.
      - A floor on yearly payments, so the trust doesn't hang on an appeal (PA legality to check).
      - An independent monitor publishes water, power, noise, heat delivered and local hiring: the
        scorecard as the yearly public report.
      - No operator staff in township government or as a majority on the trust.
      - A review every five years, with the community side's consent for changes.
    - For the model: a tax-appeal scenario (a 24-90% cut) against what the trust, the impact fund and
      the housing share still receive.
    - Still to check before citing: the Abilene, Bakken, Detroit and Waukee details (news and
      secondary sources), and Starbase.
- **D12** (2026-11-16) A modular site plan, secured by design.
  - Jon: "get everything modular so we can move things around for optimal transportation, security,
    etc."; the optimizer suggests and Jon edits; security "like pentagon style. no fence, the
    community will be the fence/wall".
  - The steer: security in layers, designed in.
    - The community is the outer ring of natural surveillance (CPTED, ISO 22341).
    - A landscape stand-off band at a published distance (UFC 4-010-01): the basin, the pools,
      steps, planters and a ha-ha as hidden vehicle barriers, as at the US Embassy in London.
    - The hall's hardened skin is the inner ring.
    - Trucks are screened at a remote delivery building, as at the Pentagon.
  - Residents watch, they don't guard; professional security stays the operator's.
  - The repo is public, so security stays at the level of published principles and distances.
  - Built (2026-11-16): `brownfield site`, [docs/pass3/site.md](pass3/site.md).
    - Every module a rectangle sized by its own model, placed and turned in `params/site.yaml`; rules
      every layout must pass; a score; simulated annealing that proposes layouts and never edits the params.
    - Routes found on a 10 m grid round the buildings: walks, truck roads and the public road to the hub.
    - Rules added from Jon's words and the rings: homes on the town side of the hall; no public place
      behind it; the homes' view of the winter garden kept open; trucks screened at the entrance.
  - Weights and layout (2026-11-17). Jon: "i will let you decide what matters most given the research
    backing it. same with layout."
    - The score became what a layout costs a year, every term on a published value:
      - walking time at US DOT's $40.20 an hour;
      - trucks at ATRI's $2.336 a mile;
      - an underpass and a raised crossing at Bushell et al.'s costs;
      - US DOT's 7% discount rate;
      - residents' visits from NHTS 2022 and visitors from ITE's trip rates.
    - What that says matters most:
      1. no truck road crosses a main walk (Safe System: separate in space). Trucks go round until an
         underpass would pay; none is needed.
      2. the visitors' walk from the car park to the center's door;
      3. the residents' walks;
      4. the warm main;
      5. truck distance, least.
    - New rules:
      - the homes' rows run east-west, so every house has a south wall (DOE);
      - trucks keep 100 m off the homes and the public places, and come in at the hall's back;
      - the public road never runs behind the hall.
    - New condition: blackout curtains on the greenhouse at night (Leamington's bylaw).
    - Chosen: the current layout with two edits from the optimizer. It costs $1,462k a year, against
      $1,714k before the edits.
      - The field moves beside the mobility hub.
      - The hub moves against the community center's door.
    - The best proposal ties it ($1,456k; cheaper in 15 of 27 cases across the inputs' ranges, the
      chosen layout in 12). It was turned down:
      - its edge rests on the placeholder count of walkers from the town;
      - residents walk less in the chosen layout;
      - the chosen layout keeps the square between the homes and the garden.
    - The drawings (forge `garden`) now place every module from `out/pass3/site.json`, with the
      routes, the hub, the delivery building, the crossings and the stand-off planters.
    - Found and fixed: every render until now was the site's mirror image. The frame is
      left-handed (x east, y south, z up) and the renderer's camera treated it as right-handed.
      All the campus and garden views are redrawn.
    - Still open: the site's real entrance and way to the borough (placeholders until the site is
      mapped); the share of trips to each place; the count of walkers from the town.
- **D13** (2026-11-16) An AI medicine facility.
  - Jon: "there also needs to be an ai medicine facility. once people understand what ai can do for
    medicine like what google deepmind is working on, they gonna be begging for more data centers.
    let's make it clear we are aware of the benefits in our planning phase".
  - The steer: state the benefits precisely and sourced, because opponents will check them.
    - Working today: protein structure prediction (AlphaFold; the 2024 Nobel Prize in Chemistry); the
      FDA's list of AI-enabled devices (mostly radiology); autonomous diabetic retinopathy screening
      in primary care (IDx-DR, cleared 2018).
    - Promising, not yet routine: AI-designed drugs (Isomorphic Labs) and diagnostic dialogue
      (AMIE), both still research.
    - Medical AI doesn't need to sit next to the data center; building the clinic here is a choice
      to share the benefit locally.
    - All figures to be sourced in the research step before they go into public docs.
  - Plan: an AI-assisted clinic and health research center on the square, run in partnership with
    Indiana Regional Medical Center and Pittsburgh's academic centers, not competing with them.
    - Screening, primary care and telehealth to specialists.
    - Research jobs and training with the university.
    - Health data under HIPAA, used with the community's consent.
    - Its own module in the site plan.
    - A short, sourced README and PLAN section: what AI can and can't yet do for medicine.
- **D14** (2026-11-16) Cars optional, even in winter.
  - Jon: "it being car centric is gonna be a problem. cars should be optional, even in the winter.
    probably would start with a waymo style fleet before rolling out a rail sytem if things expanded
    a lot".
  - The steer:
    - Heated walks and bike paths off the data center's warm water: the spine, the greens' walks,
      the square, and a route to Homer City borough, as in Holland, Michigan's snowmelt system on
      its power plant's waste heat (to source: area, loads, ASHRAE snowmelt design).
    - Self-driving fleets are the goal, but snow is their weak point today. Start with on-demand
      electric shuttles (driven, then driverless once proven in snow) to the borough, Indiana (the
      university, the hospital) and the Pittsburgh bus, with the county's transit authority.
    - Rail on the plant's freight line kept open as a later option, if the town grows.
  - In the site plan:
    - The three car parks become one mobility hub at the site edge: the shuttle stop, bikes, EV
      charging and a small shared car park.
    - Parking maximums in place of minimums (as in Buffalo 2017 and Minneapolis 2021; to source).
    - A new rule: every door within a few minutes of a stop.
    - The heated walks' heat counted against the module's spare heat.

- **D15** (2026-11-17) The hall's great doors; the Fallingwater garden on the community center.
  - Jon, early on 2026-11-17, with a reference image: "what if we did something liek this to the
    front of it instead, as its kind of like the store of our sacred compute, then the frank lloyd
    wright front off the data center went on the front of the community center? as its the beloved
    3rd space of the community". Later: "we still have the frank lloyd wright doors on the front of
    the data center and not the larger doors like we had talked about earlier".
  - The steer: his reference's qualities, not the temple itself. The temple is a sacred form, and
    "a temple to AI" would hand opponents a headline. Instead, the tradition of monuments to
    infrastructure: Philadelphia's Fairmount Water Works, London's Abbey Mills pumping station.
  - Built:
    - **The hall's front:** a stepped stone base and two stone pylons to 26.5 m, past the hall's
      towers. Between them, in a deep stone reveal under a lintel and a cornice, a pair of bronze
      doors 10 m wide and 14 m high. They are for people; the hall's working doors are at its back.
    - **The forecourt:** two warm basins either side of a causeway, spilling over the ledge into
      two lower pools, and a stair down to the square on the hall's axis. Pedestrians only, inside
      the stand-off band.
    - **The winter garden moved whole** to the community center's west face, onto the square.
      - The center moved 31 m east, the hub with it, and the greenhouse 25 m east.
      - The center's heavy shop moved to its east end, its own door onto the hub, so no shop door
        opens into the garden.
    - **A new rule:** the square stands before the forecourt, on the hall's axis. Without it the
      optimizer moved the square away from the doors.
      - With it, the hand layout is the cheapest in 25 of 27 cases across the inputs' ranges.
      - It costs $1,500k a year against $1,462k before: the center is further from the homes and
        the warm main is longer.
  - The warm basins, checked (`brownfield garden`):
    - The method: ASHRAE's pool evaporation equation, convection and sky radiation, over PVGIS's
      typical year, with no sun. The heat is an upper bound; the water is not, since the summer sun
      warms the basins past 20 C and the falls throw spray.
    - At 20 C: 4.6 GWh a year, 1.7 MW at the coldest, windiest hour, and 3,725 m3 of water
      evaporated a year. That is about nine families' home use (EPA WaterSense: over 300 gallons a
      day each). The hall itself evaporates none (pass 2).
    - At 30 C: 9.8 GWh and 9,400 m3.
    - The basins now count in the neighbourhood's heat balance: 15.2 GWh a year in all; tomato
      houses 43.5 -> 39.5 ha.
  - Open:
    - whether a smaller warm basin, or a cover at night, keeps the meaning for less heat and water;
    - the steam, which isn't drawn;
    - the golf short course;
    - the townhouses' look.

- **D16** (2026-11-17) The town centre: the hall inside a greenhouse moat, the homes in rings
  round it, memberships for the centre, and a checklist of what a real application needs.
  - Jon, the same day:
    - "so maybe some people actually just will want a small apartment ... smaller apartments are
      closer to the city center while the larger/more remote the house gets, the further away
      from our city center we get. i think the city center should be the massive greenhouse, 3rd
      space community center and the data center is protected within all of it too. this is
      basically like a next generation costco x planet fitness x your adult rec sports type of
      town. but we cant leave out any details or else it will just look like concept art
      instead of an actual plan".
    - Then: "i keep thinking about putting the data center inside the greenhouse. like if the
      greenhouse was like its moat ... security on the crops and the data center perimeter
      together. but itll require more glass. but also that solves the sound insulation too while
      keeping the data center central".
  - The steer:
    - **The moat holds, partly for other reasons.**
      - The glass doesn't stop the noise: it comes off the roof's coolers, 14-17 m up, and goes
        over 6 m glasshouses.
      - What quiets the homes is distance. Nobody may sleep in the ring anyway, and the moat
        fills it.
      - Security gains for real, kept to published principles. Public vehicles stay 320 m from
        the hall instead of 15 m (FEMA 426: stand-off distance first). One controlled entry
        serves the crops' biosecurity and the hall's outer layer, and the hall keeps its own
        inner layer.
    - **The rings hold.**
      - The centre is where no one sleeps.
      - The loop pays only for dense homes (pass 3).
      - Pass 4's newcomers are mostly renters, and flats suit renters.
    - **The changes to what Jon asked:**
      - The flats are 3-storey walk-ups, held down by the hall's noise at upper windows.
      - Their floors beat the code, so a neighbour's noise doesn't reach another's sleep
        (Jon's rule for the townhouses).
      - The public ground stays free. A members-only centre would be an enclave and lose D12's
        natural surveillance; memberships pay for the facilities.
      - What still makes it concept art is the land. Every position is schematic, and the
        checklist says so.
  - **The moat** (`brownfield site`):
    - The greenhouse's 38.5 ha in six blocks round the hall: 285 m deep west, east and north,
      150 m on the town side.
    - A 20 m fire and service road all round the hall (IFC 503).
    - The hall's trucks enter through a 15 m covered crossing in the north blocks.
    - The court with the warm basins runs on as an open mall, 70 m wide and 150 m long, from the
      great doors to the square. It is open rather than glazed: visitors see the crops through
      glass but never walk among them (tomato growers bar visitors because of viruses), and the
      basins still steam in the open air.
    - The food court is at the town end of the south-east block, on the mall's mouth.
    - Glass +2.0% against one block. The hall's midwinter noon shadow, 35 m, falls on 0.22 ha of
      the north blocks: packing and loading go there, not crops.
    - The town-side depth, tried at 40, 100, 150 and 250 m: 150 m is cheapest of those that pass
      ($1,776k a year; 100 m $1,786k; 40 m puts the flats inside the noise setback; 250 m runs
      off the site).
    - At 150 m every home is under 40 dB(A) at night with pass 2's own fans. So Jon's "solves the
      sound" holds, by distance rather than by glass.
  - **The rings** (`brownfield village`, `src/brownfield/rings.py`):
    - Pass 4's newcomers near the campus: 121 renting, 121 buying.
      - Renters take flats in the mix now built to rent (Census 2025: studio 8%, 1 bed 43%, 2 bed
        39%, 3+ 9%): 10 studios, 52 one-beds, 48 two-beds and 11 three-beds in 11 walk-ups.
      - Buyers take townhouses (98), or houses (23) if they need 4 bedrooms, as 19% of Indiana
        County's owners do (ACS B25042).
      - 584 people, 117 school-age children: ~9 a grade against Homer-Center's ~60.
    - Night noise at the worst window: flats 39.7 dB(A) at 258 m, townhouses 36.1 at 404 m,
      houses 39.5 at 261 m, all with pass 2's fans.
    - Sound between flats: an I-joist floor rates STC 48 / IIC 61, under the code's 50. With 1 in.
      of gypsum concrete it rates STC 63 / IIC 65 (AWC DCA 3), so they get it.
    - Heat:
      - The flats beat a heat pump on the loop even paying for their pipes.
      - The townhouses tie and stay on the loop because the operator pays the pipes (D11).
      - The houses heat themselves: over 20 years $45,488 on the loop against $38,512 for a heat
        pump.
    - Money:
      - The flats leave a gap of $20.2M at market rents, $18.7M as 4% tax-credit flats, $6.1M as
        9%.
      - An AWS household ($117,000) can buy a townhouse ($441k) with $60,604 to spare. The
        county's median household is $81,866 short.
      - A house ($617k) is $114,849 beyond an AWS household.
    - Land: 37 homes a hectare in the flats, 20 in the townhouses, 7 in the houses.
  - **The layout:**
    - The optimizer's best find was cheaper than the hand layout in all 29 cases across the
      inputs' ranges ($1,777k against $1,914k a year), so it was taken:
      - the community center turned and south of the square, the winter garden on its west face
        looking at the flats;
      - the flats west of the square, the townhouses south, the houses beyond the flats.
    - Now $1,776k a year. No proposal beats it (the best is $1,953k).
    - Not comparable with D15's $1,500k: twice the residents (584 against 300) walk further.
  - **Running the centre** (`src/brownfield/center.py`):
    - It costs $3.18M a year: 19.7 full-time posts to keep it open 24 hours (NRPA's $120,639 a
      post), the rink (a 2025 two-sheet study, halved) and the field.
    - Leagues and ice rental cover $0.43M of that.
    - At 7,200 members (Planet Fitness's average club) the rest is $31.78 a month each: between
      Planet Fitness's $15 and the Indiana County Y's $47.50.
    - Free memberships for the township and borough (1,526 people) cost the trust $0.58M of its
      $1.41M a year ($1.32M after D26's tax correction).
  - **The checklist:** [docs/pass3/checklist.md](pass3/checklist.md) lists what the county ordinance
    (SALDO §302.6, for a land development with buildings) and the MPC (§707, §709) ask for.
    - It is strongest where hearings press: noise, water, heat, homes, money and shared places.
    - The gap is the ground: parcels, ground levels, wetlands, mine workings, gas wells, utilities.
  - Open:
    - map the real site;
    - ask Center Township whether it has zoning here;
    - the placeholders: people per home, members, the rink's running cost, the topping's cost;
    - the townhouses' look; the golf short course.

- **D17** (2026-11-17) The real land, AWS's six sites, and the conference of communities.
  - Jon: "so what about building communities that are pulling heat and eating the food from the
    greenhouse? ... so its like a conference of communities, which makes it fun. your community can
    play the other community in your sport, etc. also defense wise i like that more". Then, on the
    steer to map the real sites first: "let's go with your plan".
  - The steer:
    - The economics don't come from heat or food. The greenhouse grows enough tomatoes for ~3 million
      people, and a home's heat on the loop costs about what a heat pump does.
    - People are the limit (pass 4: 808 newcomer households, 2,215 in the high case), then sewage
      and schools.
    - So: map the real ground first, then size each site's community by its jobs.
  - **The land** (`brownfield land`, [docs/pass3/land.md](pass3/land.md)):
    - Every layer the county's ordinance asks for, from public services: 10 m ground levels, flood
      zones, wetlands, streams, wells, old mines, roads, power lines, towns.
    - AWS's six sites, from the county's posted master plan (sheet C050.00), fitted to the roads:
      9.47 m a pixel, half the line work within 30 m of a real line. The township line and DEP's
      permit points agree.
    - Buildings by drawn area: Bruner 12, West 7, and Helen, Green, Harvey/Gaston and Rura 5 each
      (39); 1,314 acres drawn.
    - Half the 22,639 ha box is clear. Old mines lie under 10,940 ha. There are 1,414 active
      conventional gas wells. Every site has 70-186 ha buildable within 700 m.
  - **The conference** (`brownfield conference`, [docs/pass3/conference.md](pass3/conference.md)):
    - Each site's homes by its buildings: 30-74 homes a site, 242 in all (84-205 in the high case).
    - They stand 700 m from AWS's buildings (pass 2's conventional cooling), on flat clear land,
      next to the nearest town.
    - Six clubhouses would cost $12,597 a new home a year to run. Too small to stand alone.
    - The towns already there have 3,794 people, six times the newcomers. So the conference is three
      members, the new homes joining them:
      - Homer City and Lucerne Mines (Bruner's homes);
      - Graceton and Coral (West's, Helen's, Green's and Rura's);
      - Black Lick (Harvey/Gaston's).
    - Three clubhouses cost $866 a household a year. The arena (D16's centre) stands between Homer
      City and the plant.
    - The 38.5 ha of glass is shared by homes, each share a food gate beside its site.
  - Open:
    - the real setback, which depends on AWS's cooling (150 m with the good-neighbour design);
    - the full application package and its parcels;
    - who owns the communities' land;
    - soils and the 1 m lidar there;
    - the 3D drawings of each member's new homes and clubhouse (done in D18).

- **D18** (2026-11-17) The conference drawn: each town's new homes and clubhouse on the real ground.
  - Jon: "draw the 3D homes and clubhouses".
  - The steer: D17's placement left Bruner's 74 homes in the woods 3.1 km from Homer City. A drawing
    of that would show an enclave, the opposite of the conclusion.
    - Homes at a town's edge use its mains, its school bus and its shops.
    - The warm loop doesn't hold the homes near the sites: D16 found heat pumps cheaper for the
      houses.
    - So the newcomers join the towns by the towns' people (each grows ~15%), laid out at their edges.
  - **The model** (`brownfield conference`, [docs/pass3/conference.md](pass3/conference.md)):
    - Homes by town: Homer City 109, Black Lick 65, Lucerne Mines 49, Coral 13, Graceton 6 (242;
      664 in the high case). D17 more than doubled Graceton and Coral.
    - The layout (`neighbourhood.py`):
      - a spine off an existing local street, with D16's living streets, lots and greens;
      - the lots in rings from the spine's mouth;
      - each lot at least 95% clear, within a 400 m walk, its building's ground falling under 3 m;
      - up to three clusters a town.
      Every home placed.
    - A clubhouse where it costs a household under $1,200 a year:
      - Homer City (with Lucerne Mines), $442;
      - Black Lick, $1,085;
      - Graceton and Coral ($3,593) play at the arena.
      Two cost $1.02M a year, $577 a household.
    - The clubhouse: a 670 m2 court hall (an NFHS court, 7 m clear) behind a cafe, lobby, fitness
      room and workshop; 12,000 ft2.
    - Black Lick has no level ground near its middle (floodplain, steep hills): its clubhouse lands
      833 m up the road. An existing building in the village made over is probably better.
    - Heat (2026-11-17, after the drawings): at the towns' edges, 1-5 km from AWS's buildings, the
      warm loop's main costs $38,000-197,000 a home. Every new home heats itself with a heat pump
      ($23,143 a two-bed flat over 20 years against $65,953-249,903 on the loop). Pass 4's "flats at
      the fence line" is superseded; the loop's heat goes to the food gates' glass.
  - **The drawings** (forge `conference`, 11 views):
    - USGS ground and NLCD woods in autumn;
    - Microsoft's footprints for the towns as they stand, PennDOT's roads;
    - pass 3's walk-ups and D16's townhouses and houses, turned to their streets on graded lots;
    - the clubhouse inside and out;
    - AWS's Rura buildings on Graceton's skyline.
  - Open:
    - what the towns say;
    - who owns the edge land;
    - the sewer and water mains;
    - how Graceton's and Coral's homes cross US 119;
    - Black Lick's clubhouse in an existing building;
    - the real setback.

- **D19** (2026-11-17) The construction workforce, 2026-2036 (pass 4).
  - Jon, on the steer to model it next: "go with your plan".
  - The steer: the developers' "10,000+ construction jobs" is a total, not a head count, and the
    towns carry the crews for a decade before the permanent jobs arrive.
  - **The model** (`brownfield workforce`, [docs/pass4/workforce.md](pass4/workforce.md)):
    - the gas plant from HCR's reported counts (1,000 / 1,800 / ~2,000 in 2026);
    - AWS's 39 buildings on the filed schedule (Project Narrative, p. 2), ~150 workers a building
      under construction (AWS New Carlisle);
    - the region's trades (BLS QCEW), beds (ACS vacant rentals, hotel listings) and US 119 (PennDOT,
      the Highway Capacity Manual).
  - **Findings:**
    - Peak ~3,300 on site in mid-2029 (2,900-5,300), 12,900 worker-years in all; 6.4% of the
      construction jobs within a daily commute.
    - At 30% from away, ~660 rooms or homes at the peak against 962 available without squeezing the
      town: Indiana County's 1,455 vacant rentals (13.3% vacancy) and its hotels. Short in 32% of
      draws, for ~16 months round 2029.
    - Homer City, Black Lick and Center have no spare rentals: the risk is crews outbidding local
      renters there.
    - US 119 has room (0.55 of capacity in the shift hour); the site gates are the pinch.
  - **Corrected:** leasing the new flats to crews won't pay down their gap. With Indiana's vacant
    rentals at ~$806, crews won't pay lodging-allowance rents for new flats.
  - **For the benefits agreement:**
    - a crew housing plan (master leases in Indiana and White Township);
    - protection and a rental registry for the towns next to the site;
    - park-and-ride and staggered shifts;
    - a camp on campus land if the peak runs past ~4,500.
  - Open:
    - AWS's own construction workforce plan;
    - a survey of the gas plant's crews (where they live);
    - a landlord survey in Indiana;
    - the site gates' traffic plan.

- **D20** (2026-11-17) The scorecard as the design now stands.
  - Jon: "please start on the scorecard" (after the steer that the scorecard, untouched since pass
    2e, is where the project's result lives).
  - `brownfield scorecard` ([docs/SCORECARD.md](SCORECARD.md)) scores three things:
    - one module against the three conventional designs;
    - the campus at 3,000 MW of IT (a placeholder: AWS states no load; 1,500-3,750 MW, bounded by
      the 4.5 GW gas plant);
    - the towns.
  - **Findings:**
    - **Against the old design, the good neighbour wins on everything:** +$118M a module over 20
      years keeping diesel.
    - **Against modern designs, its case is the creeks and quiet nights, not money:**
      - the AI hall (liquid and towers) is $24.8M a module cheaper, but at 3 GW it withdraws ~27
        million gal/day, sends ~6.8 million of blowdown to the creeks, and needs ~700 m to reach
        40 dB(A);
      - the cloud hall uses almost no water here; the good neighbour's plant must cost $2.7M less
        to break even.
    - **The heat is no longer part of the case:** with the homes on heat pumps (D18) and the
      glass sized by the market, ~0.7% of the heat is used (156 GWh a year, the 38.5 ha).
    - **Most of what the towns get comes whichever design is built:** the jobs, ~$96M a year of
      tax ($92M after D26), the construction decade. What the deal adds is the benefits agreement (homes,
      clubhouses, the arena, the crews' plan, 270 jobs in the glass), paid from that tax.
  - Open:
    - AWS's actual cooling (its narrative: non-contact water from the station, returned to it) and
      its campus load;
    - the cloud hall's night sound;
    - hospital access, the towns' own housing cost, land reclaimed, monitoring and private wells.

- **D21** (2026-11-17) A brief for the townships ([docs/township-brief.md](township-brief.md)).
  - Jon: "please start on the township brief" (after D20's split into design asks and deal asks).
  - **The steer it rests on:**
    - **New local rules can't reshape AWS's plan.** It was filed under the county's land development
      ordinance on 2026-10-14, and MPC §508(4) shields a filed plan from later ordinance changes.
    - **The towns' levers are the GRID standards and the benefits agreement.** The governor's
      executive order (2026-08-18, as reported) requires:
      - local approval;
      - early consultation on "key design decisions";
      - a water-consumption report;
      - a benefits agreement covering noise and air quality.

      *(Corrected by D24 from the order's text: early consultation and the benefits agreement
      are not in it.)*
  - **What it asks:**
    - **Of the design:** disclose the cooling water; no evaporated or discharged cooling water; 40
      dB(A) at night at the nearest homes; no routine diesel tests. Each comes with what it costs
      AWS: nothing against air-cooled halls, ~3.4% of the power bill against liquid-cooled halls
      with towers (now printed by `brownfield scorecard`).
    - **In the agreement:** independent monitoring, published; a housing fund ($6-20M for the 121
      flats); the crews' plan; Homer City Borough as a party (most new homes, no tax); a clean-up
      bond; the clubhouses and arena.
    - **Six questions for the county Planning Commission,** 2026-11-18.
  - Open:
    - the executive order's own text;
    - Center Township's zoning;
    - who signs the benefits agreement.

- **D22** (2026-11-17) The water budget (pass 2f, [docs/pass2/water.md](pass2/water.md)).
  - Jon: "please start on the water budget".
  - **The steer:** the brief's first question, how much water the campus will use up, had no
    number behind it, and HCR's "in line with history" had never been checked.
  - **The model** (`brownfield water`):
    - the coal plant's monthly use from EIA (2014-2023);
    - the gas plant by heat balance and by DEP's permit inputs;
    - the data centers from pass 2's models;
    - Two Lick Creek's natural flow, transferred from Blacklick Creek by flow duration (checked on
      the pre-dam record);
    - a daily mass balance of the reservoir, 1952-2025.
  - **Findings:**
    - **"In line with history" is the maximum intake rate:** ~38 MGD for both plants. The coal
      plant drew at most 21 MGD in a month (16.1 in 2014).
    - **The gas plant's own condensers draw ~24 MGD**, like the coal plant at full output; the
      reservoir falls no lower than 49%, in the 1952 drought.
    - **DEP's permit inputs are 12 MGD higher** (36 drawn, 29.2 not returned). That is what towers
      rejecting ~1.5 GW more heat would evaporate: one fit is the data halls' heat in the station's
      towers. On 36 MGD the reservoir falls to 12% in 1952. *(Overturned by D24: 36-37.6 MGD is
      the intake's ceiling, and the halls' water is a separate, small stream.)*
    - **Towers at the data halls on top would empty it** in 1952 and 1991: 334 days short in 73
      years, 187 of them without even the 11 cfs at the dam, just above Indiana's water plant. Dry
      coolers or outside air add almost nothing.
  - Open:
    - AWS's cooling (whether the halls' heat is in the 36 MGD);
    - the reservoir's usable storage and rules;
    - where the 29.2 MGD goes;
    - the draw's seasons.

- **D23** (2026-11-17) Who it's for, stated in the README.
  - Jon asked whether the project is a template for Amazon or a data center to show its benefits.
  - **The steer:** no. AWS has its own engineers, and some findings cut against the usual pitch:
    - the heat case collapsed to ~0.7%;
    - the good neighbour is a premium against modern AI halls;
    - most benefits come whichever design is built.

    Its value is the towns' side of the table, and that depends on independence.
  - Jon: "i like this". The README now says who it's for:
    1. independent public analysis for host communities first;
    2. a method any town can reuse;
    3. a standard developers can be held to.

- **D24** (2026-11-18) What is already posted, read before asking for anything.
  - **The question:** Jon, on records requests: "i think we have done our part as i dont live in
    this county". The steer:
    - requests, comments and meetings belong to residents and their officials;
    - reading what is posted is checking our own numbers;
    - one handoff of the brief to the county is his call.

    Jon: "let's proceed with what you suggested".
  - **Found:**
    - **The station's NPDES renewal application** (May 2026, DEP's Homer City page), with:
      - its water balance (drawing D-352-1801);
      - the 316(b) report on the intake;
      - the permit list naming the 11 cfs consent order (Docket 81-060-W);
    - **Executive Order 2026-05's own text,** and DCED's summary of the GRID requirements;
    - **the county's posting:** the full application package (a Dropbox folder that can't be
      listed without a browser) and a public comment form.
  - **What changed:**
    - **The halls' water is in the filing:** 1,400 gpm of makeup, 400 back, at most 1.44 MGD used
      up. That would carry ~174 MW of heat by evaporation, 6% of a 3,000 MW campus's.
    - **DEP's 36 MGD is the intake's ceiling** (three 8,700 gpm pumps, 37.6 MGD), not the gas
      plant's need. D22's reading, the halls' heat in the station's towers, is withdrawn.
    - **The gas plant's towers run at 5 cycles,** so its own condensers draw ~21.4 MGD, not 23.9.
      The reservoir's lowest is 57%; with the halls as filed, 53%.
    - **The 11 cfs is kept over the low dam below the intake,** as the model assumed. No release
      rule at the reservoir's own dam is public, so the model now holds only Indiana's ~2.2 MGD
      there (a placeholder). 11 cfs at that dam too is a sensitivity.
    - **Towers at the halls are beyond the intake:** 48.6 MGD with the gas plant, against the
      pumps' 37.6.
    - **The brief:**
      - its GRID section now follows the order's text. Local approval comes first; there is a
        GRID consent order with DEP; the sales tax exemption depends on GRID; the yearly water
        report starts 2027-07-01; the NDA bar covers state agencies. The benefits-agreement
        and early-consultation terms are only reported, not in the text.
      - its water ask is now to hold the halls to the filed 1,400 gpm;
      - a seventh question asks whether AWS will sign a GRID consent order.
  - **Not posted:**
    - the consent order's text;
    - the reservoir's usable storage and any operating or drought rules;
    - DEP's 2026-10-14 discharge hearing transcript;
    - DEP's GRID template;
    - the county Planning Commission's minutes.

- **D25** (2026-11-18) The air (pass 2g, [docs/pass2/air.md](pass2/air.md)).
  - **The asks:**
    - Jon: "yes add the link, then start on the air please". The README now links
      new-melting-pot as the companion study of how people behave.
    - 15 of 40 hearing speakers raised the gas plant's air and health.
  - **The model** (`brownfield air`):
    - the coal plant's emissions from EIA, 2013-2023;
    - the gas plant's facility caps (Plan Approval 32-00457A);
    - DEP's summaries of the modelling and the risk assessment;
    - each design's energy at the plant's permitted rates;
    - the diesel tests at Tier 2 and Tier 4.
  - **Check:** EIA's 2021-22 SO2 reproduces the application's CEMS baseline, 4,460.5 against
    4,460.6 tons a year.
  - **Findings:**
    - **Per MWh, the gas plant is far cleaner than the coal plant in 2014:** SO2 -99.95%, NOx
      -98.5%, CO2 -59%.
    - **In total, at its caps:** 45% more greenhouse gases than in 2014 (17.6 million tons). Against
      the coal plant's last two years, four times the CO2 and nearly four times the PM2.5.
    - **At the worst point off the site:** annual PM2.5 at 85% of the standard; cancer risk 0.54 in
      a million.
    - **NO2 and ozone were never modelled,** because NOx netted out against the coal plant's
      retirement.
    - **The design's lever is the diesel:** Tier 2 tests add up to 335 tons of NOx a year, +55% on
      the gas plant's NOx for the halls. Tier 4, which DEP required of the gas plant's own engines,
      adds 35 tons. PUE moves the plant's emissions 1-2% among modern designs.
    - The scorecard's Tier 2 figure is now confirmed (40 CFR 60.4202, 1039 appendix I).
  - **The brief:**
    - the gas plant's air under "whichever design";
    - Tier 4 and real-time logs if diesel is kept;
    - air monitors near the homes;
    - a question on AWS's generator permits;
    - the appeal's environmental justice claim.
  - Open:
    - AWS's generators (no permit found);
    - NO2 near the homes;
    - actual running;
    - the Environmental Hearing Board appeal (filed 2025-12-17).

- **D26** (2026-11-18) Where the tax goes, the schools and the hospital (pass 4b,
  [docs/pass4/services.md](pass4/services.md)).
  - Jon: "proceed" (next after the air: the hospital and schools, pass 4's open question).
  - **The correction, found while scoping:**
    - **What was wrong:** pass 4 put all 39 buildings at Center Township's rates, so all ~$68M of
      school tax went to Homer-Center.
    - **What the lines show:** the Census Bureau's township and school district lines and the
      master plan's building pixels (`districts.py`) put 51% of the buildings in Black Lick
      Township, in the River Valley School District (formerly Blairsville-Saltsburg).
    - **At 2026 millage** (the county's sheet): $92.0M a year in all:
      - Homer-Center $33.0M and River Valley $32.6M;
      - Center Township $2.8M and Black Lick Township $1.0M;
      - the county $22.6M.
    - **Updated with it:** `econ.campus_tax` now splits by side, and the brief, scorecard, README,
      pass 4 and the village's trust figures follow.
  - **The schools** (PDE):
    - **Enrolment:** Homer-Center has 766 pupils (873 in 2017-18), and River Valley 1,429 (1,634 in
      2014-15).
    - **The newcomers' ~117 children:** ~6.6 a grade for Homer-Center and ~2.4 for River Valley.
      Room enough.
    - **The money:** each district's campus tax is about a whole budget.
      - **Uniformity:** one millage per district, so it mostly becomes a lower millage for
        everyone: -90% in Homer-Center and -81% in River Valley at today's spending.
      - **If all state aid were lost:** -68% and -42%.
    - **State aid:** the aid ratio, recomputed with PDE's own formula (checked against PDE's file),
      falls from 0.71 to 0.34 and from 0.65 to 0.31.
  - **The hospital:**
    - **Indiana Regional's emergency department** (Level IV trauma since 2026-01-01) is 9-17
      minutes from the towns. Conemaugh's Level I is 44-48 minutes away.
    - **Same for every design.**
  - **Emergency services:**
    - the build's ~12,900 worker-years give ~300 recorded injuries at BLS's rates;
    - the campus keeps ~975 MWh of batteries or ~1,320 generators.
    - The brief now asks for fire and EMS readiness in the agreement, and puts both school
      districts at the table.
  - Open:
    - where Bruner's buildings fall on the line;
    - the aid formula's dollars;
    - capacity;
    - ambulance response times.

- **D27** (2026-11-19) The bid set as data (pass 3f, scoped; `brownfield bidset`, report
  `docs/pass3/bidset.md`).
  - **The question:** bid sets reach subcontractors as PDFs, so every bidder, and every supplier's
    rep, redraws the same building (the window elevations, say) before pricing it. Jon likened
    RFIs, addenda and submittals to pull requests, and asked whether we should build a
    construction exchange.
  - **The steer:** not an exchange.
    - An exchange sits downstream of the problem: it posts what the architect sends, and the
      architect sends PDFs.
    - It can't start without jobs and bidders, and the incumbents (Dodge, ConstructConnect,
      Autodesk's BuildingConnected) hold both.
    - AI takeoff from PDFs is already sold (Togal.AI is one), and the incumbents will add it.
    - The lever is the owner's contract. The formats mostly exist: IFC (the model), BCF (issues
      tied to model elements, i.e. RFIs), IDS (a machine-checkable list of what a model must
      carry, v1.0 in 2024). What's missing is a definition of what a bid set must carry, and
      addenda as diffs.
    - So: write that definition as an IDS and show it working on a building of ours. A town can
      ask for it for the buildings it pays for (D23's "a standard developers can be held to"),
      and it lets small local subs bid them cheaply.
  - Jon: "this is good. let's scope it".
  - **The building:** pass 3b's walk-up, 114 openings by its layout: 101 windows (3'-0" x 4'-0",
    sill 3'-0"), 12 patio doors (6'-0" x 6'-8") and 1 entry door (3'-6" x 6'-8").
  - **Steps:**
    0. **Spike first.** Pin IfcOpenShell 0.9.0.post1, ifctester 0.9.0 and ifcdiff 0.9.0 (PyPI,
       2026-09/10; wheels of 43 MB and 25 MB, the rest small). One wall and one window to IFC4;
       export it twice and get an empty diff; check it against a one-line IDS. If any of that
       fails, stop and report.
       - **Done 2026-11-19, passed** (a scratch environment, 230 MB installed):
         - all 18 GlobalIds and the file's entity text are identical across two exports;
         - `ifcdiff`: nothing on the re-export; W1's height 4'-0" to 4'-6" changes exactly that
           window;
         - schema validation finds 0 errors;
         - the IDS passes width, U-factor and MasterFormat section, and fails SHGC as expected;
           without the type's property set it fails the U-factor too;
         - the window's geometry reads back at 0.9144 x 1.2192 m with its sill at 0.9144 m.
       - **Built:** the API gives property sets and relationships random GlobalIds, so we derive
         them from what they join (~20 lines).
    1. **Forge writes the whole model** to `out/pass3/apartment.json`: every opening with a
       stable id (storey, flat, face, index) and its size and position; walls, slabs and the roof.
       Today the file carries only the opening widths.
       - **Done 2026-11-19** (`cargo run --release -- apartment-json`, under a second). The file
         gains three keys and its old ones are unchanged (all 181 tests pass):
         - `openings`: all 114, each with id, kind, storey, flat, face, size, sill, its box
           through the wall, outward normal and wall;
         - `parts`: 14 boxes, namely the four exterior walls, the spine and stair walls, the
           ground slab, four floor systems and the roof;
         - `levels`: the three storeys.
       - **Ids** are `<space>/<face>/<index>`: `2-back-right/back/3` is a patio door,
         `1-stair/front/0` the entry door. The space comes from where the opening is, so an id
         doesn't depend on the order openings were made in.
       - **Checks:** forge refuses to write a model that fails its own checks
         (`Building::model_errors`, also in `check` mode). `tests/test_bidset.py` has 5 tests:
         - the counts by kind and storey, and ids that are unique;
         - glazing per flat, found from the openings, equals pass 3b's `flat_envelope` exactly;
         - every opening sits in its wall at its size;
         - the four wall boxes make exactly the shell.
       - **Found:** the solid model's floor systems run through the spine and stair walls (the
         framed model's members don't). In an IFC that is a clash, so step 2 stops them at the
         walls.
       - CORTENFORGE.md: no identity on a `Solid`, no IFC export (gap and suggestion).
    2. **The IFC** (`src/brownfield/bidset.py`): site, building, three storeys; walls, slabs and
       roof; windows and doors with their types (W1, D1, D2) and voids.
       - GlobalIds derived from the stable ids, so a re-export changes nothing.
       - Thermal transmittance from `params/pass3.yaml` `window_u` (the number the heat model
         used); a MasterFormat classification per type (our choice, marked judgement).
       - **Done 2026-11-19** (`uv run brownfield bidset`, ~7 s): `out/pass3/bidset/apartment.ifc`,
         310 kB.
         - **Walls and slabs:** 24 walls, a storey at a time (12 exterior, 12 spine and stair), with
           the ground slab, 4 floor systems and the roof. The 4 wall types come from the frame's
           stud schedule: exterior 2x6 at 16 in.; party double 2x4 at 12 in. (storey 1) and 16 in.
           (storeys 2-3); stair double 2x4 at 16 in.
         - **Bearing walls follow `framing`:** the facades and the spine bear the floors and the
           roof, and the stair walls bear the roof over the stair. The end walls bear neither.
         - **Windows and doors:** W1 (101), D1 (12), D2 (1). Their U-factors come from
           `window_u` and `door_u`: 1.70 W/m2K, and 1.14 W/m2K for D2, a **placeholder**. Each
           U-factor's description in the file names its params entry, confidence and source, so
           the placeholder reads as one there too.
         - **MasterFormat:** 08 50 00, 08 00 00 and 08 10 00, each marked "judgement" in the file.
           A window's level-3 section is its frame material, and the patio door gets only the
           division until we know whether it swings or slides.
         - Every opening voids its own storey's wall. Each window and door carries its id, flat,
           face, index and sill height (`BF_Opening`, the sill as a length in metres).
       - **The clash fixed in forge:** the spine and stair walls are now a storey at a time and
         stop under each floor, as `framing` builds them. The exterior walls are per storey too.
         The floors are unchanged (CortenForge still measures them at 197.35 against 197.20 m3),
         and forge's check now holds every pair of parts clash-free. `docs/pass3/apartment.png`
         isn't redrawn: the walls and floors together look the same.
       - **Checks** (`bidset.check`, reading the file back), all passing:
         - every wall, slab, opening, window and door of forge's model is in the file once, and
           nothing else is;
         - 101 / 12 / 1 by type, and every size exact;
         - every wall, slab, window, door and opening where forge has it (worst 0.0000 mm);
         - every opening voids its own wall and holds its own unit;
         - 0 clashes among the 30 walls and slabs;
         - glazing per flat equals pass 3b's `flat_envelope`;
         - 807 unique GlobalIds;
         - IfcOpenShell's schema validation with the express rules finds 0 issues;
         - a second export is the same file, header aside.

         A mismatch is reported as a failure, not a crash. `tests/test_bidset.py` has 14 tests,
         including these:
         - the check catches a window moved 5 mm or made 1 mm wider, and a part missing from the
           file;
         - dropping one window removes only that window's six records;
         - the bearing walls follow the frame;
         - the placeholder is labelled in the file.

         All 195 tests pass.
       - **Built:**
         - IfcOpenShell writes IFC SETs in an order that changes from run to run, so `_sort_sets`
           sorts them (by GlobalId, or entity number).
         - A relationship's GlobalId is keyed on its relating side, plus the one related element
           for a void or a filling. So an addendum that adds or drops a window leaves the storey's
           and the type's relationships alone.

         Those two and the derived GlobalIds make the file repeatable, and make a diff show only
         what changed.
       - **Code review** (2026-11-19, before the commit): 14 findings, all fixed. The 2 important
         ones were the stair walls marked non-bearing and the check never confirming that every
         part was in the file.
       - **A second, independent reader** (Jon chose That Open's web-ifc), done 2026-11-19.
         - **What it is:** web-ifc is That Open's parser and geometry kernel (MPL-2.0), separate
           from IfcOpenShell. `brownfield bidset` now runs it on every export, and fails, saying
           why, if it can't (no Node, not installed, or a version other than the lock's).
         - **The parts:**
           - Node 24.19.0 comes from the `nodejs-wheel-binaries` wheel, so there is no system
             install. It is pinned in its own `webifc` group, which is installed by default;
             `uv sync --no-group webifc` leaves it out where no wheel fits the platform.
           - web-ifc 0.0.78 (2026-09-21) is pinned by its sha512 in `tools/webifc/package-lock.json`.
           - Install it once with `uv run brownfield bidset --setup-reader` (`npm ci`, install
             scripts off).
           - `tools/webifc/check.mjs` writes what web-ifc finds to a report file (web-ifc logs on
             stdout, which is passed on), and `bidset.check_webifc` compares that with forge's
             model. Each class is read with its subclasses, as IfcOpenShell's `by_type` reads
             them.
         - **What it confirms:**
           - it is the web-ifc the lock pins;
           - every element of forge's model once, by class, and nothing else: 24 walls, 6 slabs,
             114 openings, 101 windows, 13 doors;
           - 101 / 12 / 1 by type, and every size exact;
           - every element in its storey, and every opening voiding its own wall and holding its
             own unit;
           - every unit's id, kind, flat, face, index and sill height;
           - each type's U-factor is its params value;
           - glazing per flat equals pass 3b's;
           - web-ifc's own geometry puts every wall, slab, window and door where forge has it,
             worst 0.0003 mm (its vertices are 32-bit floats). Its meshes are y-up, so the file's
             (x, y, z) is web-ifc's (x, -z, y).
         - **Tests:** 3 more in `tests/test_bidset.py` (17 now):
           - the check catches a window moved 5 mm and a wrong sill;
           - a mesh with no vertices, or a unit with no width, fails the check rather than
             passing or crashing.

           They skip, saying why, if the reader isn't ready. All 198 tests pass.
         - **Code review** (2026-11-19, before the commit): 12 findings, all fixed. The 4
           important ones:
           - an empty mesh passed, because its box became NaN and `max` dropped it;
           - web-ifc's own messages on stdout would have broken the JSON report;
           - a unit with no size crashed the check;
           - the main command needed a dev-only module.
         - **For looking:** That Open's browser viewer, built on the same parser, reads the file
           locally.
    3. **The IDS**, generated from `params/bidset.yaml` so its numbers live in params: type,
       storey, overall width and height, external or not, U-factor, MasterFormat section,
       operation (casement, slider...), safety glazing where IBC 2406 requires it, escape size
       where IBC 1031 requires it.
       - It is expected to fail at first: the model has no operation type or clear opening.
         Finding what a design model leaves out is the point.
       - The list is checked against what a window quote needs: from Jon, and from the published
         rating fields (NFRC U-factor and SHGC; NAFS performance grade, edition to confirm).
       - **Done 2026-11-19.** `uv run brownfield bidset` now also writes
         `out/pass3/bidset/bidset.ids` and `checklist.md`, whether or not the second reader can
         run.
         - **The IDS:** 52 specifications (buildingSMART IDS 1.0), one per field and class, and
           checked against the IDS schema when read back.
           - They cover 28 fields: Jon's list, plus type mark, storey, exterior or not, which wall
             the unit is in, and the wall's construction.
           - 16 fields use IFC4 standard properties or attributes. 12 are ours (`BidSet_`), each
             saying why, e.g. "IFC's opening element is the hole in the model; this is the size to
             frame".
           - The U-factor limit comes from `params/bidset.yaml`: 2018 IECC zone 5, U-0.30. That's
             1.704 W/m2K, rounded up to 3 decimals so a rated U-0.30 written rounded still passes.
         - **What the walk-up carries: 8 of the 28 fields.** These are the type mark, storey,
           exterior or not, unit width and height, a U-factor within the code's limit, which wall
           it's in, and that wall's construction (`BidSet_Wall`, from the frame's stud schedule).
           **It carries none of the other 20**: rough opening; operation; frame material and both
           colours; the glass (low-e, gas, tempered, obscure); SHGC; the design pressure rating;
           escape windows; screens; grilles; hardware finish; install type; a level-3 MasterFormat
           section; and safety glazing where the code calls for it.
         - **Safety glazing, IBC 2018 2406.4.1-2406.4.3:** read on UpCodes' Pennsylvania IBC
           2018; the numbers are in `params/bidset.yaml`. It applies to 36 of the 114 openings:
           - the 12 patio doors (glazing in a door, 2406.4.1);
           - 24 windows, the two beside each patio door. Their edges are 23.1 in from the door's,
             inside the 24 in arc, and their sills are 36 in up, under 60 (2406.4.2). None of
             2406.4.2's four exceptions applies, and none of them is about a patio door's fixed
             panel.

           2406.4.2 is measured in plan on the same storey, round corners as well as along a wall.
           Round a corner, exception 4 turns on the door's handing, which the model lacks, so the
           reason says so. 2406.4.3 doesn't reach the windows, because their sills are above
           18 in.
         - **The 24 are their own type, W2.** The schedule is W1 77, W2 24, D1 12, D2 1, so a quote
           priced by type can't miss them, and both readers confirm the split. A quote that prices
           them as ordinary glass is wrong, and nothing in the model said so until now. Each
           unit's `BF_Opening` carries the flag and the reason.
         - **Checks:**
           - the IDS passes a copy of the model with every field filled in (made-up values), and
             every specification applies to something (24 windows and 12 doors for safety
             glazing);
           - it fails exactly the one requirement broken, a window without its width;
           - read back, each specification has the identifier it was written with;
           - the safety-glazing count and the 23.1 in follow from the layout;
           - a sidelite tight against a door, gap 0 to rounding, is caught;
           - a window round a corner from a door is caught, with the handing caveat.

           `tests/test_bidset.py` has 6 more tests (23 now). All 204 pass. The IFC is now 339 kB
           with 814 GlobalIds: the 4 wall types' construction property sets, and type W2 with its
           property set and type relationship.
         - **Not yet, and what we don't know:**
           - **Escape opening sizes** (IBC 2018 1030): the text came later from Jon, and they are
             in now (below).
           - **2406.4.4-2406.4.7 not assessed:** guards and railings, wet areas, beside stairs and
             landings, and the bottom of a stair. The model has no stair flights or landings, so
             the 5 stair windows wait for them.
           - **2406.4.3's walking surface is assumed:** the floor inside runs to the wall, so it is
             always within the 36 in.
           - **The whole unit stands in for its largest pane**, because the model has no panes.
         - **Built:** ifctester 0.9.0 writes each specification's `identifier` but doesn't read
           it back, so `read_ids` restores it from the XML.
         - **Code review** (before the commit): 13 findings, all fixed. The 3 important ones:
           - the count was written as "IBC 2406.4" when only 4.1-4.3 were checked;
           - a sidelite tight against a door could be missed to rounding;
           - one type, W1, mixed the windows that need safety glazing with those that don't.
       - **The one stair and escape windows**, done 2026-11-19. The source is IBC 2018 1006.3.3,
         Table 1006.3.3(1) and 1030, which Jon read in an online IBC 2018 viewer and shared as
         screenshots, since the fetch tools couldn't reach them. The numbers are in
         `params/bidset.yaml`.
         - **The table** allows one exit on the first to third storey above grade, with at most 4
           dwelling units and 125 ft of common path. The walk-up has 3 storeys and 4 flats a storey.
           Its common path is bounded by straight lines, since interior walls aren't modelled:
           - ~65 ft from a flat's far corner to its door to the stair;
           - ~90 ft on to the front door on the ground floor, if the stair hall there is exit
             access rather than part of the stair's enclosure.

           **So it fits the table, but footnote a allows one stair only with:**
           - sprinklers throughout (903.3.1.1 or 903.3.1.2). The village assumes NFPA 13R (pass
             3e). Whether pass 4's cost covers them is unchecked: HUD's per-unit limit is a cap,
             not an itemised estimate;
           - escape openings by 1030.

           **The model doesn't meet that yet.** It marks no escape windows, has no rooms to say
           which windows serve bedrooms, and has no sprinkler system in it.
         - **1030.1 then needs an escape window in every sleeping room.** That's 16 on the upper
           storeys, at 2 bedrooms a flat as pass 4 prices them (`flat_bedrooms`, 1-3 across the
           village's mix; counts round up). The ground floor's 8 are needed too unless its patio
           doors count as a second way out. Exception 2 would need a door from the bedroom itself
           to the yard or an exit balcony, and the model has no rooms.
         - **Each one must clear 5.7 ft2, 24 in high and 20 in wide "in normal operation", with the
           bottom of the opening no more than 44 in up.**
           - The units' sills are at 36 in. The clear opening's bottom sits a little higher (frame
             and sash), so it is likely under 44 in, but that's unchecked until the clear opening
             is known.
           - The clear opening is the window's operation. A 3'-0" x 4'-0" casement swings fully
             open. A double-hung of that size opens about half its height, and a slider about half
             its width, so they likely miss 24 in or 20 in.
           - **The field that decides code compliance is one the design model leaves out.**
           - Whether a window is an escape window belongs on each window, not its type: W1 serves
             bedrooms and living rooms alike.
         - **The IDS gains 4 fields** (32 now, 56 specifications) for any window marked as an
           escape window: clear opening area, width, height, and its bottom above the floor.
           - They are `BidSet_` properties, since IFC4 has no net clear opening.
           - The bounds are in metres, to 0.1 mm, so a value written rounded still passes. That
             leans to the supplier, by under 0.1 mm.
           - On the walk-up they apply to no window, and the checklist says "none marked; 16 needed
             (24 with the ground floor)" so the rows can't read as a pass.
         - **`brownfield bidset` says all this** in its summary.
         - **Tests:**
           - the table's result (3 storeys, 4 flats, 65 and ~90 ft) and footnote a unmet;
           - the table fails past each limit (a fourth storey, a fifth flat, a 130 ft flat);
           - escape counts round up;
           - the complete model passes with casement-sized clear openings;
           - a window marked as an escape window but too short (0.55 m, as a double-hung) fails
             exactly the clear height and area, while windows marked as not escape windows are
             left out.

           `tests/test_bidset.py` has 27 tests. All 208 pass.
         - **Code review** (before the commit): 10 findings, all fixed. The important one: the
           escape sizes applied only to windows marked as escape windows, so with none marked
           they could never fail. The checklist and summary now say what's needed.
    4. **From the IFC alone** (not from forge, to show the file is enough): the window and door
       schedule (CSV), the four elevations with tags (SVG), and quantities (glazed area per flat,
       net wall area).
       - **Done 2026-11-19.** `uv run brownfield bidset` now also writes, to
         `out/pass3/bidset/drawings/`, from the IFC alone (`bidset.read_back` opens nothing
         else). Missing optional attributes read as "not in the model", never as a crash.
         - **`schedule.csv`:** one row per type, 35 columns.
           - **Every IDS field** has a column, read from the units' own properties over their
             type's, as IFC has it, or "not in the model". It reads W1 77, W2 24 (safety glazing,
             2406.4.2), D1 12 (2406.4.1) and D2 1, with sizes in feet and inches and mm, the count
             per storey, the U-factor and the MasterFormat section.
           - **Where a number comes from shows:** D2's U-factor source reads
             "params pass3.envelope.door_u (placeholder)", and the sections are marked
             "(judgement)".
           - **Where a type's units differ** (a size, a property), the cell says "varies" and
             lists them.
           - **The fields the model lacks say "not in the model".** This is the sheet to hand a
             rep for the rep test.
         - **`openings.csv`:** all 114 units with id, type, storey, flat, face, size, sill height
           and safety glazing.
         - **`elevation_{front,back,left,right}.svg`:** each facade seen from outside, with the
           storey levels, the roofs' edges, and every unit in an exterior wall tagged with its
           type. The safety-glazed ones are outlined in red, with a legend. Text from the IFC is
           escaped. Rendered and looked at (resvg, in a scratch folder).
         - **`quantities.csv`:** each facade's wall, gross, openings and net. In all: 780.4 m2
           gross, 159.4 m2 of openings, 621.0 m2 net (8,400 / 1,715 / 6,685 ft2), and the glazing
           in each flat.
         - **Checks (tests):**
           - the schedule's counts, sizes, safety glazing and sources, with the missing fields
             showing as missing and every IDS field having a column;
           - every unit on the elevations where forge has it (within 1 mm), on the right facade,
             once. Left to right is written out in the test, so a mirrored drawing fails;
           - gross wall area equals 2 x (width + length) x height, and the openings' total equals
             forge's;
           - glazing per flat equals pass 3b's `flat_envelope`;
           - the SVG files as written are well-formed, with one titled rectangle per unit;
           - an odd file (a window without its width, half a rough opening, a U-factor on one
             window over its type's, a material layer set, an ampersand in a storey's name) reads
             without crashing, the differences showing as "varies";
           - units in a wall that isn't exterior are left off the facades.

           `tests/test_bidset.py` has 33 tests. All 214 pass.
         - **Code review** (before the commit): 15 findings, all fixed. The important ones:
           - the schedule left out fields and dropped the placeholder note;
           - missing attributes crashed it;
           - it read only types' properties and showed only the first unit's size;
           - it took in interior doors;
           - its SVG text wasn't escaped;
           - it missed materials that aren't plain IfcMaterial;
           - it drew walls from z = 0 and only one roof.
    5. **The addendum as a reviewed change:** an RFI as a BCF topic on the patio door type (the
       schedule doesn't say its glass) answered by an addendum with one data change (D1 tempered)
       and one size change (W1's height, the escape question). Re-export, `ifcdiff`, the IDS
       rerun and the drawings regenerated. That is the CI step.
       - **Done 2026-11-19** (`uv run brownfield addendum`, after forge `apartment-json` and
         `apartment-json addendum-1 60`; written to `out/pass3/bidset/addendum-1/`, with the base
         as diffed beside it, `base.ifc`). The addendum is made up, to run a change through the
         bid set, but it follows from the code check.
         - **The RFI** (`rfi-001.bcf`, BCF 3.0): "what glass goes in the patio doors (D1)?" It
           also asks whether the 24 windows beside them (W2), 23.1 in from a door's edge and
           inside the 24 in arc, take safety glazing too, or whether the doors can narrow.
           - Its words, and the answer's, are built from the model, the params and the code
             check, so they can't drift from the run.
           - A viewpoint selects the 12 doors by GlobalId, the camera in front of the building
             looking at its middle.
           - The answer is a comment a day later; the topic is closed. Topic type, statuses and
             the two made-up roles (bidder, architect) are declared in the file's extensions, as
             BCF 3.0 asks.
         - **Addendum 1:**
           - item 1 (data): D1 is glazed tempered, as properties on the patio door type;
           - item 2 (size): the patio doors narrow to 5'-0", a stock width
             (`bidset.addendum_1.patio_door_width_in`, a placeholder: made up), centred where they
             were. This is made in forge (`Building::addendum_1`, the width on the command line),
             so the model's own checks and the flats' glazing follow.
           - Before anything runs, the revision is checked to be the base plus exactly this: the
             same parts and openings, and only the patio doors moved, to the params width.
         - **What changed** (`element_diff`): 36 units, 12 openings and 3 types; no other element,
           opening or type.
           - The 12 patio doors changed in attributes, geometry and properties, and their type:
             the 5'-0" door is a new type object.
           - The 24 windows beside them changed type (W2 -> W1) and properties.
           - The 12 doors' openings in the walls narrowed.
           - Types: D1 at 6'-0" and W2 withdrawn, D1 at 5'-0" new. Type GlobalIds are keyed on what
             a type is (kind, size, safety glazing), not its mark, which is numbered by position.
           - ifcdiff does only the attributes and geometry, because it stops at the first
             relationship that differs. Type, storey and properties are compared directly, the
             properties without the entity numbers ifcdiff counts. ifcdiff alone flags all 114
             units.
         - **The revision passes everything:** both readers, the schema, and a repeat export. The
           report says so if the second reader couldn't run.
         - **What moved:**
           - safety glazing falls from 36 openings to 12: the windows are now 29.1 in from a
             door's edge, outside the arc;
           - in the IDS, tempered on the doors goes from 0 of 12 to 12 of 12, and so does safety
             glazing on the doors;
           - in the schedule, W2 is withdrawn, W1 becomes 101, and D1 is 5'-0" and tempered. The
             schedule's changes match types by what they are, and report a renumbered mark as
             such;
           - the openings in the exterior walls go from 1,715 to 1,635 ft2;
           - the elevations are redrawn. The revised front was rendered and looked at.
         - **Tests:** `tests/test_addendum.py` has 10:
           - forge changes only the patio doors;
           - the code check follows the change;
           - the diff is exactly the units, openings and types above;
           - the revision must be the base plus the addendum, and a tampered one is refused;
           - the revision passes its checks;
           - the RFI is a closed topic on the 12 doors, answered later, with the camera on the
             building;
           - the words follow the params (a 30 in arc leaves the windows needing safety glazing);
           - the schedule moves as the addendum says, and renumbering reads as renumbering;
           - a spec adds to a property set the type already has.

           All 224 tests pass.
         - **Built:** a property comparison without entity numbers, and type and storey compared
           directly (ifcdiff 0.9.0). bcf-client 0.9.0 is pinned (ifctester brought it in). The
           BCF topic's own GUID and dates are new each run, since an issue is made once.
         - **Code review** (before the commit): 15 findings, all fixed. The 5 important ones:
           - the camera faced away from the building;
           - the diff missed the openings and the types;
           - ifcdiff's early return hid storey moves;
           - marks renumbered by position would mislabel the schedule's changes and alias type
             GlobalIds;
           - nothing checked the revision against the base.
    6. **The conventional side:** the same building issued as a PDF set (elevations and the
       schedule sheet, generated). For each change in the addendum, count the places a bidder
       must find by eye on the sheets against the rows in the diff. Our sheets are cleaner than a
       real set, so the count is a lower bound.
       - **Done 2026-11-19** (`uv run brownfield pdfset`, after forge's `apartment-json` and
         `apartment-json addendum-1 60`). It rebuilds both IFCs from forge's current model and
         checks the revision is the base plus the addendum, so the narrative, the sheets and the
         counts come from one run.
         - **The sets:** the walk-up's bid set as an architect issues it, drawn from the IFC by
           `pdfset.py`, on 36 x 24 in sheets at 1/4" = 1'-0", every title block marked "NOT FOR
           CONSTRUCTION, a made-up bid set for a study". The drawings are checked to fit inside
           the border and clear of the title block.
           - `out/pass3/bidset/pdf/bidset.pdf`: A-201 and A-202 the front and back elevations,
             A-203 the two ends, and A-601 the window and door schedule.
           - On the schedule, blanks show as a dash, and U-factors are in the unit NFRC rates them
             (U-0.30, with 1.70 W/m2K after). The remarks include "SAFETY GLAZING REQ'D" and, for
             the entry door (mark D2), whose U-factor is a placeholder, "U-FACTOR TO BE
             CONFIRMED".
           - `out/pass3/bidset/addendum-1/pdf/addendum-1.pdf`: Addendum 1's narrative page, its
             words from the run, then the revised sheets. Every change is in a revision cloud
             with a delta, and the withdrawn W2 row is shown struck through as deleted, clouded.
         - **What a bidder with only the PDFs does** (`addendum-1/conventional.md`):
           - **to bid:** count 114 tags by eye on 3 elevation sheets (45, 45, 24) and tally them by
             mark (W1 77, W2 24, D1 12, D2 1), then read the schedule's 4 rows. From the data,
             `schedule.csv` carries the counts and `openings.csv` lists all 114 units, so there's
             nothing to count;
           - **for Addendum 1:** find 40 changed places on 3 revised sheets:
             - A-201 and A-202: 18 each (6 doors narrower, 12 windows W2 -> W1);
             - A-601: 3 cells (W1's quantity, D1's width and glazing) and W2's row gone.

             From the data, the element diff lists 36 windows and doors, 12 openings and 3 types
             by GlobalId, and the schedule 8 changes, so there's nothing to find.
           - Units are matched across the two sets by their id, which the sheets don't show, so
             a moved unit counts once.
         - **A lower bound:** these sheets have no floor plans, sections, details, dimension
           strings or specifications, where the same change shows up again. And every change here
           is clouded, which in practice they aren't always.
         - **Read back:** the PDFs keep their text (TrueType, set for these pages only), and pypdf
           reads the tags back tallying to the schedule, as a takeoff tool would. The revised
           sheets carry exactly 40 deltas, one per place counted. A scanned or flattened set
           wouldn't allow that reading.
         - **Checked by looking:** the revised front and the schedule were rendered and looked at.
         - **Tests:** `tests/test_pdfset.py` has 10:
           - every unit and schedule cell is a place;
           - the addendum changes exactly those 40;
           - the PDFs carry the tags as text;
           - the addendum PDF clouds every place counted;
           - an addendum that touches no sheet issues only its narrative;
           - the schedule reads as a US set, with laminated glazing shown;
           - a moved unit counts once;
           - a building too long for the sheet is refused;
           - drawing leaves matplotlib's settings alone;
           - a schedule row that comes or goes counts once.

           pypdf 6.21.4 is pinned in the dev group. All 234 tests pass.
         - **Code review** (before the commit): 14 findings, all fixed. The 5 important ones:
           - a withdrawn row had no cloud;
           - an added row couldn't get one;
           - laminated glazing printed as a dash;
           - the narrative and the sheets could come from different runs;
           - an addendum touching no sheet would have re-issued them all.
    7. **Report** with figures (an elevation from the IFC, the diff) and what we don't know.
       - **Done 2026-11-19:** [docs/pass3/bidset.md](pass3/bidset.md), with two figures:
         - the front elevation from the IFC (`bidset_front.svg`);
         - the revised A-201 sheet with its clouds (`bidset_addendum.png`).

         `brownfield pdfset --publish` publishes the figures and the files to `docs/pass3/bidset/`
         (~0.9 MB): both IFCs, the IDS and its checklist, each IFC's drawings and schedule, the
         RFI and the addendum's diff, both PDF sets and the comparison. The README and pass 3's
         README link the report.
    8. **The stair and the flats' doors** (2026-11-20, Jon: "go with the stair step"), after the
       3D viewer showed neither was modelled. The code limits are in `params/bidset.yaml`
       (`code.stair`, `code.exit_stair`, `code.door`). In three parts, each committed on its own:
       - **8a, forge and the stair's code check.**
         - **The stair:** a stair that turns back on itself, at the back of the core, with 11 in
           treads. Each storey has:
           - 6 risers of 6 in up to a landing whose top is the back stair windows' 36 in sill;
           - then 12 risers of 7 in back towards the front.

           Risers differ between the flights, which 1011.5.4 allows (it asks for uniformity
           within a flight).
           - **Why not 9 + 9:** it puts the landing across the windows, so they would move, and
             pass 3b's framing, masonry and costs (which read the openings) would change.
           - **Why not 5 + 13** (the first try): the review found the upper flight's handrail
             extension ran across the back-right flats' doors, and that layout leaves no room
             to move them.
         - **The rest of the core:**
           - a wall between the two flights, so the flights have no open sides;
           - hall floors on levels 2 and 3;
           - a wall closing the low space under the ground-floor upper flight;
           - a 42 in guard on level 3, the one open edge;
           - handrails on both sides of every flight, as rail paths with their extensions.
         - **The 12 flat doors:** 36 x 84 in, in the stair walls, opening off the hall and
           swinging into the flats.
         - **Where they go:** forge's output gains a `stair` block. Nothing that reads the
           existing model changes, and `bidset.load` rejects a model without it.
         - **Done 2026-11-20**, after a code review (15 findings, all addressed).
           - **forge** (`forge/src/stair.rs`) builds the stair from `apartment::Building`
             without changing it. Pass 3b's volumes are unchanged (109.262 m3 of exterior wall,
             197.202 m3 of floor systems), and the 114 openings and 30 parts are untouched.
           - **What it adds:**
             - 4 flights, 52.75 in wide;
             - 2 landings 48 x 110 in;
             - 4 hall floor pieces;
             - the centre wall and the closure;
             - one guard;
             - 8 handrails;
             - the 12 doors, one into every flat.
           - **forge's checks** (`check` and the JSON writer) reject:
             - parts overlapping by more than 0.01 mm on every axis;
             - a landing across a window;
             - a door outside its wall, in the spine or past the hall;
             - a stair part in a door's 44 in approach, or a handrail across it.

             Its 7 tests: the example holds, and 6 break it in those ways.
           - **`brownfield bidset`** runs 17 checks against `code.stair` and `code.door`,
             measured from the boxes rather than taken from forge. All pass:
             - risers are 6-7 in, measured from the floor or landing found at each end;
             - the least headroom is 101.00 in, landing 2 over flight 1b's first nosing.
               Anything rising through the nosing line counts as an obstruction;
             - every end of every flight has 48 in of landing or floor;
             - of 6,944 edge samples none is an open drop, and 144 are at windows;
             - each door has a clear 44 in landing (1010.1.6), with no part or handrail in it;
             - the doors are 33.5 in clear wide, which takes a placeholder for what the leaf and
               stop take off (`flat_door_clear_loss_in`, 2.5 in).
           - **What the bid set doesn't show yet:** the back stair windows on levels 1 and 2 now
             rise from the landings.
             - 2406.4.3 makes both safety glazing, measured from the landing.
             - The level-2 one also falls under 1015.8 (sill 13 ft up): if it opens, it needs a
               fall measure, and the model doesn't say whether it opens.

             `brownfield bidset` reports both. The bid set's types change in 8b.
           - **Tests:** `tests/test_stair.py` (13 tests). Every check passes on the model.
             - **Breaking the model fails the matching check:** a column on a tread, a low duct,
               a hall floor 2 in low, a short hall, no guard, an uneven step, a missing
               handrail, a narrow door, a door slid into a handrail.
             - **Known values:** the headroom over two flights.
             - **Not shown failing:** 9 of the 17 checks (a landing at each end, flight rise,
               tread depth, width, handrail heights, extensions, reach and projection, and guard
               height).
           - **The review also fixed the viewer:**
             - a file picked while another was parsing now replaces it;
             - the server serves only the page itself outside its three routes.

             The suite is 255 passing.
           - **Not yet:** the IFC, which 8b does.
       - **8b, the IFC and what's drawn from it.**
         - `IfcStair` with `IfcStairFlight` (risers and treads), landing `IfcSlab`s and
           `IfcRailing`s.
         - The flat doors as door type D3: 1-hour fire door assemblies, self-closing, with
           `Pset_DoorCommon.FireRating`.
         - A fire rating on the stair walls.
         - The checklist asks for a fire rating on doors into the stair, and not for a
           U-factor on interior doors.
         - The schedule, drawings, quantities and the web-ifc check follow.
         - **Done 2026-11-20.**
           - **`bidset.load` joins the stair to the bid set's model** (`with_stair`). The 12 doors
             join the openings (126), and the hall floors, landings and partitions join the parts
             (40). Pass 3b reads the building alone, so its numbers don't move.
           - **The IFC:**
             - an `IfcStair` a storey, aggregating its two `IfcStairFlight`s (their step boxes,
               with `NumberOfRisers`, `NumberOfTreads`, `RiserHeight`, `TreadLength`), its landing
               (`IfcSlab` LANDING) and four handrails (`IfcRailing` HANDRAIL, an
               `IfcSweptDiskSolid` along each path);
             - the guard (`IfcRailing` GUARDRAIL) on level 3;
             - the partitions as walls with their own type;
             - the stair walls with `Pset_WallCommon.FireRating` "1 h", and its source noted;
             - the flat doors as D3, 36 x 84 in: `IsExternal` false, `FireRating` "1 h",
               `SelfClosing`, no U-factor, MasterFormat 08 10 00 (our judgement).
           - **Safety glazing:** 2406.4.3 is now measured from the stair's landings and hall floors
             too, for a surface in front of the glass (overlapping it along the wall; the first
             try also caught flat windows behind a stair wall). So the two back stair windows
             join W2:
             - the types are W1 75, W2 26, D1 12, D2 1, D3 12;
             - safety glazing is 38 of 126 openings.
           - **The checklist** has 34 fields (58 specifications). Fire rating and self-closing
             apply to doors into the stair, and the model carries both. Design pressure, install
             type and outside colour apply to exterior units only. The model carries 10 of the
             34 fields.
           - **From the IFC:**
             - the schedule and the openings list take units in every wall;
             - a unit in an inside wall is "interior", on no elevation;
             - the PDF schedule's remarks give D3 "1 H FIRE DOOR, SELF-CLOSING".
           - **The addendum's wording:** "W2 is withdrawn" was now false (W2 keeps the 2 stair
             windows). A type is said to be withdrawn only if no unit keeps it: "they are W1; W2
             stays for the 2 other units that still need it". The addendum changes 41 places on
             the sheets (it was 40): W2's quantity (26 to 2) and remarks change, and its row is
             no longer deleted.
           - **Both readers check the stair:**
             - IfcOpenShell: 6 new checks (every flight and railing once, flights and the guard
               to 1 mm, handrails along their paths, risers and treads, each part in its
               storey's IfcStair, the doors' and walls' ratings);
             - web-ifc reads the stairs, flights and railings (`check.mjs` now resolves a part's
               storey through its stair), meshes the swept handrails, and agrees.

             `brownfield pdfset`'s 60 checks pass.
           - **The viewer** colours the stair and names a flat door's fire rating.
             `uv run brownfield viewer --latest` shows this run's models (out/) before they are
             published.
           - **Tests:** 2 new (the stair in the IFC; a missing flight, a moved step and a wrong
             door rating each fail their check), and the counts above updated. The suite is 257
             passing.
           - **For 8c:** the paper set shows the flat doors only as a quantity on the schedule
             (it has no floor plans), so a bidder working from PDFs can't count them on a sheet.
           - **After a code review (15 findings, all addressed):**
             - **The report's count:** the PDF set's report counts the units in openings.csv
               (126, the 12 on no elevation among them), not the elevations' tags.
             - **The addendum:** its wording matches types by what they are, not by mark (marks
               renumber when a type is withdrawn), with a test that says "withdrawn" when
               nothing keeps W2. Its revision check covers the stair too.
             - **Safety glazing (2406.4.3):** it counts a landing at any height under the glass's
               top (a landing 2 mm off the sill still counts, tested). It takes the straight
               line from the glass's inside face with no wall in between (vectorised: 0.02 s).
             - **Ratings:** the D3 description and the guard's come from params and the model.
               The checklist asks for the params' fire rating, not just any.
             - **Robustness:** every entry point joins the stair itself. A landing on a storey
               without a stair stands on its own.
             - **The viewer** asks a flat door only what the checklist asks of it.
             - **`--latest`** has a test.

             The suite is 260 passing.
       - **8c, the PDF set, the addendum and the report:** republish, recount, and assess the
         stair windows under 2406.4.6-2406.4.7 once Jon saves UpCodes' chapter 24 (the fetch
         tools only get a summary of those sections).
         - It publishes only after both readers' checks pass on both IFCs, 46 in all, with a
           byte-for-byte repeat export. Otherwise it exits 1 and publishes nothing.
         - The published files repeat byte for byte, and carry no local time or time zone:
           - the IFC header's time is fixed (`bidset.HEADER_TIME`);
           - the PDFs have no creation date;
           - the BCF's random ids and dates are settled.
         - 4 more tests (`tests/test_addendum.py` 11, `tests/test_pdfset.py` 13). All 238 pass.
         - Code review (before the commit): 11 findings, all fixed. The important one: it
           published IFCs nothing had checked.
         - The report states what a town could ask for: the model as IFC, checked against an
           IDS like this one, and addenda as revised models with a diff. That goes into the
           township brief once the rep test is in.
         - Still open from Jon: the rep test.
         - **Gaps seen in the 3D viewer** (2026-11-20, Jon: "i dont see the stairs"):
           - no doors into the 12 flats, so the door schedule lists 13 of the shell's 25 doors;
           - no stair flights, landings or railings, and no hall floors on levels 2 and 3, where
             the floors stop at the stair walls.

           Added to the report's "what we don't know". The code is read (2026-11-20):
           - 1011.1-1011.7 from Jon's screenshots;
           - the rest of chapter 10 and 716 from UpCodes' chapter 7 and 10 pages as Jon saved them.

           Its limits are in `params/bidset.yaml` (`code.stair`, `code.exit_stair`, `code.door`).
           The fit, worked by hand from them: 18 risers of 6.67 in and two 44 in flights need 88 x 176 in
           of the 110 x 466 in core. The flat doors are 1-hour fire door assemblies (Table
           716.1(2)).

           Next step: model the stair, the hall floors and the 12 flat doors, and check them
           against those limits.
       - **A local 3D viewer** (2026-11-19, Jon: "please do the native version", then "move it
         to tools/viewer in the repo"). Run `uv run brownfield viewer` and open
         http://127.0.0.1:8765/.
         - **How it works:** That Open's web-ifc parses the IFC in the browser (WebAssembly):
           the bid set in ~100-140 ms on Jon's machine. three.js draws it.
         - **What it does:** click a unit for what the model says and what a quote still needs;
           switch to Addendum 1; open any IFC file.
         - **The parts:**
           - `tools/viewer/` holds the page and a lock file pinning web-ifc 0.0.78 (the same as
             `tools/webifc`) and three.js 0.160.0. `node_modules` is gitignored, and the
             packages are installed from the lock the first time it runs.
           - `src/brownfield/viewer.py` serves the page, the two packages and `docs/pass3/bidset/`
             on 127.0.0.1 only: no directory listings, nothing outside those places.
           - `tests/test_viewer.py` has 4 tests.
         - **Review fixes before the first commit:**
           - The server checks a request's path as text before touching the filesystem. On
             Windows, a path naming a network share would otherwise have made the machine
             connect out to that host over SMB. It also refuses device names and NUL, binds its
             port alone, and re-installs when the lock moves.
           - The page fixes see-through walls (three.js bakes transparency into the shader),
             selection by GlobalId, the title per model, overlapping loads, a missing file
             reported as one, sizes in the file's own length unit, files with no geometry,
             freeing memory, and frame material read from the file.
  - **Checks (known cases):**
    - read back from the IFC: 114 openings, 101 / 12 / 1 by type, sizes exact, positions within
      1 mm of forge's;
    - the file passes IfcOpenShell's schema validation and opens in a second, independent viewer;
    - the IDS passes a good model and fails a broken one (a window without width, a type
      without a section) with exactly those failures;
    - re-exporting the unchanged model gives an empty diff; the addendum's diff lists exactly
      the elements it changed;
    - glazed area per flat equals pass 3b's `flat_envelope`; the elevations put every opening
      where forge's drawing does.
  - **From Jon:**
    - what a rep needs on a schedule to quote a window. Jon (2026-11-19), asked about each: "i
      believe youd need all of those". So the IDS asks for every one:
      - rough opening or unit size (and which);
      - operation (casement, double-hung, slider, picture);
      - frame material, and inside and outside colors;
      - glass (low-e, argon, tempered, obscure);
      - U-factor, SHGC and performance grade (the design pressure rating);
      - which windows are escape windows;
      - screens, grilles and hardware finish;
      - install type (nail fin or replacement) and the wall it goes in;
    - the rep test: hand the schedule, the IFC and the PDFs to a rep and ask whether the quoting
      software takes it, what's missing, and the time against working from PDFs. One data point,
      reported as one, with no names.
  - **Out of scope:** an exchange or any hosting; construction documents (they need a licensed
    architect's or engineer's seal); the data halls, whose operators keep designs confidential
    for security; framing members and MEP (framing is a later step, its board feet against
    `brownfield frame`'s); costs.
  - **What we expect not to know:** liability wording (untested here); what producing it costs
    an architect; whether quoting software imports it; real takeoff error rates (no source yet);
    Pennsylvania's public-bidding rules for town-owned buildings (the Separations Act among them).
  - **If it holds:** an ask in the township brief that the buildings the benefits agreement pays
    for go out to bid with their model as data, and a line in D23's standard. CortenForge gets an
    entry: no IFC export and no stable part ids.

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
