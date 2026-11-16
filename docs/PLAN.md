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
      a hearth tower up the hall's face; pools with a 2.4 m fall;
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
