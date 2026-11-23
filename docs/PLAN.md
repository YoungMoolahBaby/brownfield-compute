# Plan

**The question:** when a data center comes to a retired coal plant in a shrinking town, how should
it be designed so that the town comes out ahead? Answered with public data, against a conventional
data center on the same site.

## Status (2026-11-15)

**Pass 3g SCOPED (2026-11-21), the walk-up's systems designed up front (D28).** Plumbing,
heating, cooling, ventilation, electrical and sprinklers, designed in full before bidding, to US
code as Pennsylvania enforces it plus PHIUS, with no DIN standards. Then a round of installers'
feedback, and the inspection plan. Only the engineered design is drawn; the usual walk-up is
priced from sources as the baseline. Found while scoping: Pennsylvania now enforces the 2021
I-codes, and the bid set was checked to IBC 2018. Decided: one central water heater; two service
rooms (electrical; mechanical and plumbing) in an annex behind the stair. Step 0 (sources) done;
step 1 (rooms and annex) built in forge as Addendum 2, checked against IBC 2021 (14 checks; the
escape windows must be casements) and run through the bid set's IFC as a reviewed change against
Addendum 1 (34 checks pass). Step 2 under way: heat and ventilation room by room built. Found:
the walls didn't meet Pennsylvania's 2021 energy code, so Addendum 3 brings the envelope to code
(continuous insulation, the heated slab's). The plan room now reads as an exchange's project page
(D29): an addenda dropdown, the documents in folders, the viewer with rooms, framing and each
addendum's changes (live). Step 2 finished: cooling, water, drainage, hot water and electrical
loads, each with a known case. Step 3 designed: radiant floors on REHAU's own data, an ERV and a
ducted mini-split a flat from certified ratings, the building loop off the data center's 50 C
return. Found: pass 3's floor was optimistic (the flats need 35.1-40.2 C water, not ~30; still no
heat pump), and the ERV's air reaches the bedrooms at 6.8 C on the coldest hour. Jon took both
recommendations and ENERGY STAR: Addendum 4 specifies the glass at ENERGY STAR's Northern zone (U
0.22) with SHGC 0.17-0.25 (published in the plan room), so a 12k mini-split serves each flat, and
an electric preheater ahead of each ERV keeps it from defrosting and brings its air to 16.5 C.
Step 4 designed: a central hot-water plant that takes 75% of its heat from the data
center's return, a recirculating loop held at WHO's temperatures, every pipe sized by the code's
pressure method, cast-iron stacks for quiet. It needs at least 49.5 psi at the street main, which
the water authority doesn't publish: a hydrant test to ask for. Step 5 designed: a 208Y/120 V
service with the meters outdoors (FirstEnergy's rule), each flat's circuits, feeder and panel held
to the code's tables and a 5% voltage drop, a 600 A main (the code's load needs more than 400 A).
Found on the way: step 4's hot-water heat pump had no real unit at its 122 F source. Jon took the
fix: it takes its heat from the data center's water after the preheat (a rated unit, COP 4.4), and
the loop returns to a swing tank, so the data center gives about 89% of the hot water's heat. No
chargers at the walk-up: D14 puts them at the mobility hub. Step 6 designed: NFPA 13R sprinklers
throughout (116) on a separate, monitored fire service (Jon's choice), sized by a hydraulic
calculation to the street; the one stair holds (it depends on them), no building fire alarm is
required, smoke alarms in every flat. Found: the annex's walls and its mechanical room's door near
the stair need fire ratings (IBC 1023.7), an addendum item with the roof hatch. Step 7 planned in
five parts (Jon approved); 7a done: forge frames the inside (partitions, plumbing walls, annex, the
hatch's opening), and the fixtures, risers, feeder chases, soffits, ERV terminations, roof units
and equipment are placed to it. Found:
- each water closet must sit in a joist bay;
- the ERVs' terminations need two fixed living-room windows a flat;
- the hall is too narrow for the mini-split without its soffit reaching over the bath;
- the heating loop needs a riser pair a column;
- the floors below the top need a vent stack;
- the fire service's backflow assembly needs listed shutoff valves of its own.

7b done: forge routes all 430 runs through the frame with no clashes, keeping APA's hole rules and
the drains' and vents' grades, and the checks, worked again in Python, all pass. Found:
- APA's hole spacing spreads the runs over each plumbing wall into lanes;
- each flat's lavatory, sink and washer share one 2 in. drain;
- the building drain leaves under the front footing's top, which steps down there;
- each mini-split's condensate drains by gravity, in soffits 2.5 in. deeper (Jon's choice);
- step 6's hall and study sprinklers stood 6.4 ft apart (8 ft asked);
- the ERV's fresh air goes through the mini-split (Jon's choice).

7c done: steps 3 to 6 rerun on the routes, every check passing, with all 430 runs routed again at
the sizes they asked for. Found:
- the stair's sprinkler riser and the fire main grow to 2-1/2 in., with 0.3 psi to spare on a
  placeholder street pressure;
- the living rooms' strip soffits block the sprinklers' spray, so each side gets its own (four
  more);
- the mini-splits' fans are set to 0.38-0.80 in. w.c. for their routed ducts, four of them at the
  unit's most;
- the water passes only with the PEX bent through its turns, with 0.6 psi to spare at the worst
  hot shower;
- the heating pump's head rises from 8.1 to 13.1 ft;
- two vents needed forge to retry a failed outlet first.

7d done: the services as an IFC of their own (3,124 elements), checked against forge's routes to
0.000 mm and read by a second reader; the schedules read back from it; the viewer's Plumbing,
Heating cooling and air, Wiring and Sprinklers layers live; published to the plan room as
preliminary. Found:
- seven feeders' conduits have 450-630° of bends between the meter and the panel, where NEC
  352.26 allows 360°;
- of 453 openings through rated assemblies, listed firestop systems fit 68 (40 with the PEX's
  insulation stopped at the floor), partly fit 25, and none was found for 320 (296 up through top
  plates, 24 CPVC drops);
- the top storey's ceiling is unrated in Type V-B, so its 188 openings need fireblocking only.

7e done: Addendum 5 issues the services and the completed frame as bid documents, with the
annex's rated walls and door, the stair's back wall, the roof hatch and its ladder, and the floors
between flats rated. Found and settled:
- the feeders run straight under the slab, 335-356° of bends each (NEC 352.26: 360);
- the floor wasn't WIJ-1.1 (the PRI-60's flanges are too small); it is now AWC's WIJ-1.3, and no
  UL L500 design matches it, so 345 rated openings take STI's engineering judgment;
- the floor's IIC under a hard finish (46) is short of 1206.3's 50: flagged for the interiors.

Step 8 under way, the installers' round: a plumber, an HVAC contractor, an electrician and a
sprinkler contractor (Jon's choices, 2026-11-22). 8a done: the services drawn as 21 sheets from
the published models (plans of each storey for each trade, the plumbing walls in elevation, the
plants, the one-line, the panel schedules, the hydraulic summary), every element of the model on
a sheet. Found:
- Addendum 5 left out the fire service's listed, supervised shutoff valves (7a's finding);
- the house load takes the swing tank's element at 1,747 VA, not its 2.0 kW: 44.9 A on a 45 A
  breaker, or 47.3 A (a 50 A breaker) if it counts as continuous.

Addendum 6 (Jon's decision) fixes both before the round and issues the sheets:
- the valves cost the governing sprinkler design 0.06 psi, so it needs 44.79 of 45;
- the element runs 4.9 h on the design day, so it's continuous, and the house position is
  50 A;
- no model element changes.

8b done: a question sheet for each trade, letter-size forms with the design's own figures:
- the plumber 9 questions, the HVAC contractor 9, the electrician 7, the sprinkler contractor 6;
- five for every trade, among them how they'd usually do it and what it would cost (step 10's
  baseline).

8c done: a packet for each trade (a letter from the study, its questions, its sheets), a private
log for what comes back with only what a commenter agreed to published, and the round's folder in
the plan room with the four question forms.

8d, the round itself, is Jon's: send the packets, then relay the replies.

Step 9 started (Jon: the code's tests, the design's claims and the control sequence, as Addendum
7; step 10 from free sources). 9a done: when the data center's heat is gone.
- Each flat is heated by its mini-split alone at the design temperature, with at least twice its
  need to give.
- The hot water falls to a 12.3 kW backup heater on the plant's heater circuit.
- Found: step 5 had counted the mini-split only as cooling. Counted as the heat pump it is, with
  the preheater, the service rises to 455 A, still on its 600 A main. The house panel goes to
  100 A, so it can take less PV (8.3 kW AC).

9b done: the control sequence.
- The plant switches between the data center's heat and its backup heater, one at a time, by a
  wired interlock.
- The radiant floors run on an outdoor reset.
- Each flat's mini-split sits 2 K under the floor and takes over when the floor can't hold the
  room.
- Found: eight of the sixteen control points, among them the heater circuit's pump and the two
  data-center valves, have never been chosen. They're part of the plant's wall-hung equipment no
  step has placed.

9c started: reading the energy code's tests found three hot-water rules the design broke, now
fixed for Addendum 7. A plant serving several flats falls under the commercial chapter (R403.8).
- Each flat's hot water now circulates in a loop of its own and back through a balancing valve,
  so every fixture is within half a gallon of hot water (C404.5); before, 52 of 60 were over.
- The flats' hot pipe takes 1 in. of insulation (C404.4).
- The recirculation pump stops at temperature (C404.6.1).
- The cost: the loop loses 2,120 W, not 793. The swing tank's element goes from 2.0 to 4.5 kW,
  the house panel from 100 to 110 A, and the PV it takes from 8.3 to 6.7 kW AC.
- Then the two open items:
  - **The building loop's pump:** its curve, read off Grundfos's leaflet, covers the worst path,
    10.8 ft against 12.3. The routed head had taken the risers smaller than the model has them.
  - **The balancing valves:** each flat's loop now ends at its lavatory, the valve in the vanity
    where it can be reached. Each fixture's own pipe takes its own size, and the worst fixture
    holds 53 of 64 fl oz.
- 9c done: the tests and inspections, 28 items, each with its code's words or the design's figure
  (specification section 01 45 00).

9d done: Addendum 7 published, with the revised services model, 23 sheets and the two
specification sections. Addenda 1-6 are left as issued.
- Found: 9c's loops raised the storage the plant needs to 255-259 gal, over the 250 gal tank in the
  model. It's now two 150 gal tanks in series. Lochinvar's next single tank, 450 gal, won't pass
  the mechanical room's door.
- The backup heater is placed in the room, and three new checks guard the room: each piece's
  service space, the door and the ceiling, and the drops through the slab.
- In 3D, Addendum 7's changes to the services are marked on their layers.

Next: the installers' round (8d, Jon's), its packets now with Addendum 7's sheets; step 10.

**The walk-up's website (2026-11-20).** Jon: "can we make a github pages for the building", then
"what if we just put the files on the page? so its like a project from a builders exchange?".
- **The site:** https://youngmoolahbaby.github.io/brownfield-compute/
  - **A plan room (`index.html`):** the project, then its bid documents to download (drawings,
    model, schedule, openings, quantities, elevations, the IDS), then Addendum 1 (its PDF, the
    revised model and schedule, what changed, the RFI).
  - **The 3D viewer (`model.html`):** links back to the plan room; `#addendum` opens Addendum 1.
    It is also embedded on the plan room's front page (`model.html?embed`, which hides its own
    notice and link), at Jon's ask ("can we have the 3d model on the front/main page as well?").
    Every visit to the front page now loads the viewer, about 7.5 MB before compression. Embedded,
    the model starts inert under a "Click to explore the model" label, so a wheel or a swipe over it
    scrolls the page. A click turns it on, and a mouse leaving turns it off again. Without that, it
    trapped the page's scroll: 80% of a phone's screen couldn't be scrolled past.
- **What it won't do:** it says plainly that the building is made up, with no owner, bid date or
  plan holders, and it carries no real exchange's name or look.
- **Built and deployed by `.github/workflows/pages.yml`:**
  - triggered by a push that changes `tools/viewer/` or `docs/pass3/bidset/`;
  - npm ci from the viewer's lock, with install scripts off and Node 24.19.0;
  - the actions pinned to their release commits.

  It runs `tools/viewer/build_site.py`, which is stdlib only and builds a site of 33 files and
  10.2 MB.
- **The page's numbers are read from the published files when it is built:** 101 windows in 2
  types, 25 doors in 3, 38 openings needing safety glass, the number of addenda, the file sizes,
  and the addendum's items from the RFI.
- **What is written in the template is held to the model and the PDF set by tests:** the building's
  description (3 storeys, 100 x 40 ft, 12 flats) and the sheet list.
- **Pages was enabled with `gh`** (build type workflow, HTTPS enforced).
- **The viewer** now loads by relative paths, so it works under the site's `/brownfield-compute/`
  prefix and at the local server's root.
- **`tests/test_website.py` (8 tests):**
  - every link in the plan room is in the built site;
  - every file the viewer loads or links is there, by a relative path;
  - the counts and the type counts are the model's;
  - the description and the sheets are the model's and the PDF set's;
  - the addendum's items are the RFI's, whole;
  - the builder refuses the repository, `out/`, or a folder it didn't make.
- **After a code review (15 findings, all addressed):**
  - the addendum's items no longer stop at a decimal point;
  - the builder won't delete a folder it didn't make (it used to replace any output folder);
  - the viewer links back to the plan room at once, and at `/model` too, and `#addendum` opens
    the addendum without loading the bid set first;
  - web-ifc's source (release 0.78, commit 4310503, npm 0.0.78's) and both licences are linked, as
    MPL-2.0 asks of a distributor;
  - the build job runs with read-only permissions, and only deploy gets Pages'.
  - Smaller fixes:
    - the two schedules download under different names;
    - `site/` is gitignored;
    - the `.nojekyll` file is dropped, since the deploy leaves it out anyway.

**The repository's front door (2026-11-20, Jon: "go ahead with 1-3").**
- **`README.md` is a front page:** the question, who it's for, headline findings each linked to its
  report, the design in brief, and a map of the folders. It's 154 lines, down from 303.
- **`docs/README.md` indexes every report** in reading order, under plain titles with a one-line
  finding each. It also holds:
  - the campus's full design description and the garden's numbers, which lived only in the
    README;
  - the working files and a glossary (pass, D-number, module, known cases);
  - each report's command and code.

The pass-by-pass detail that was in the README is in the index and the reports, and every link
was checked. Not done, on purpose: moving `docs/pass3/`'s images (16 source files write there),
splitting `src/brownfield/` into subpackages, and renaming passes.

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
asks for the 34 fields a quote needs, and the model carries 10 of them. IBC 2018 2406.4 calls for
safety glazing in 38 openings, 26 of them windows (type W2). The one stair is allowed
(IBC 2018 Table 1006.3.3(1)) only with sprinklers and an escape window in every bedroom, 16 of
them upstairs. Whether a window clears 1030's sizes depends on its operation, which the model
lacks. The schedule, elevations and quantities now come from the IFC alone (step 4). A made-up
RFI and Addendum 1 ran as a reviewed change (step 5). As PDFs only (step 6), bidding means counting
114 tags by eye, and the addendum means finding changed places on 3 sheets; the data side lists
them. The report is [docs/pass3/bidset.md](pass3/bidset.md) (step 7). Seen in 3D (2026-11-20): the
model had no stair, no hall floors upstairs and no doors into the 12 flats. Step 8 modelled them
(forge `stair`) and checked them against IBC 2018 1010-1015, 1023 and 716 (Jon saved UpCodes'
chapters 7, 10 and 24):
- 17 stair checks pass;
- the 12 flat doors are 1-hour fire doors (D3);
- safety glazing is 38 of 126 openings, and 14 after the addendum;
- the addendum changes 41 places on the sheets;
- the report and files are republished.

Waiting on Jon: the rep
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
         - **Done 2026-11-20.** Jon saved UpCodes' chapter 24.
           - **The code:** 2406.4.4-2406.4.7 were read from it; no Pennsylvania note shows under
             2406. The limits are in `params/bidset.yaml` (`code.safety_glazing.stair_*`,
             `bottom_landing_*`), quotes checked against the page, and recorded in RESEARCH.md.
           - **`safety_glazing` now assesses 2406.4.6 and 2406.4.7** from the geometry. The
             files and drawings name what was assessed (`ASSESSED`), and each type and schedule
             row the sections its units are under.
             - The two back stair windows over the landings are also under 2406.4.6.
             - Nothing is under 2406.4.7: the nearest glass is 103 in from a bottom nosing.
             - The count stays 38 of 126.
             - A test turns a flight to face the windows and finds 2406.4.7.
             - 2406.4.4 doesn't arise (the guard and handrails have no glass). 2406.4.5 (wet
               areas) isn't assessed: no rooms.
           - **Republished:** `brownfield pdfset --publish` passed its 60 checks and wrote
             `docs/pass3/bidset/` (now ~1.1 MB).
           - **The report** (`docs/pass3/bidset.md`) and the README carry the new numbers:
             - 10 of 34 fields;
             - safety glazing in 38 of 126 openings, 26 of them windows;
             - the stair's 17 checks and the 12 1-hour doors;
             - 114 tags plus D3 on the schedule only;
             - 41 places for the addendum;
             - 38 to 14 safety-glazed openings after it.

             "What we don't know" now holds what the stair leaves open: it is boxes, the
             landing windows' operation (1015.8) and rail alternative, the doors' placeholder
             clear width, the 44 in width.
           - **After a code review (12 findings, all addressed):**
             - **Every section that applies is listed:** each reason gives the first and "also" the
               others. The schedule and the PDF's remarks show all of them (W2: 2406.4.2,
               2406.4.3, 2406.4.6), so nobody reads the rail as an alternative for the stair
               windows. Each type's description cites only its units' sections, where before
               every type cited all of them.
             - **The element diff** says what changed on a kept type. W2's description drops
               2406.4.2 after the addendum, so it lists 3 types.
             - **2406.4.7:**
               - the landing side works either way a flight runs;
               - the stairway's bottom comes from the model's levels;
               - "within" includes the arc's edge.
             - **Walls block a straight line** only at their own height.
             - **2406.4.4** is said not to arise (no glass in the guard or handrails), not claimed
               as assessed.
             - **Params:** the code limits carry low and high (equal to the value).
             - **New tests:**
               - the reach alone deciding (48 in exempt, 22 in caught);
               - 2406.4.7 either way;
               - the types' citations.
           - **The suite:** 264 passing. A repeat publish is byte-for-byte the same (25 files).
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

- **D28** (2026-11-21) The walk-up's systems, designed before anyone bids (pass 3g, scoped;
  report to be `docs/pass3/systems.md`).
  - **Jon's direction:** "making it essentially a complete spec/plan. like plumbing, electrical,
    hvac. something highly engineered, like a german building", then "system designed upfront
    imo. letting the ones making a profit from implementing the system should not be designing
    it", then "instead of buying the plumbing noise code we can engineer it/look into it from free
    us resources", and "design, open to feedback from the installers/contractors, then inspect."
  - **The question:** can the walk-up's plumbing, heating, cooling, ventilation, electrical and
    sprinklers be designed in full before bidding, so the trades price a design rather than
    design what they price? What does that design cost, and what does it buy?
  - **Jon asked whether Americans won't pay for that engineering up front.** The steer: mostly
    true for this building type, but not for that reason.
    - **What's true:** on a small wood walk-up the architect usually draws the building and each
      trade designs its own system as part of its bid, often only to what the permit needs. In
      Germany a building-services engineer designs the systems before bidding, and the trades bid
      on a priced list of every item.
    - **Why the US does it that way:** where the owner keeps the bills (hospitals, labs, data
      centers, this campus) US buildings are engineered in full. A rental walk-up's developer
      usually sells or refinances, and the tenant pays the power bill: who pays later, not
      thrift.
    - **Pennsylvania already pays for it:** PHFA has given tax-credit points for Passive House
      since its 2015 plan, with a certified Passive House consultant on the team (PHFA's 2019
      presentation to DEP's Climate Change Advisory Committee; NCSHA 2018). Pass 4 found the
      walk-up pencils only with tax credits.
    - **Germany doesn't choose it either:** most of it is law (energy, sound, a ventilation plan,
      balanced heating), and Germany is drafting "Gebäudetyp E" to let builders depart from the
      standards because they made housing too costly. A draft still in 2026, as far as found
      (Bundestag lobby register, RV0026538).
  - **Only the engineered design is drawn** (Jon: "only B"). The usual US walk-up is priced
    from sources (what contractors install in walk-ups, and its cost), not designed: the
    project's rule needs a conventional baseline, and B alone can't show it's worth the money.
  - **The rules it's designed to:**
    - US code as Pennsylvania enforces it: the 2021 I-codes from 2026-01-01 (55 Pa.B. 7701, Doc.
      No. 25-1513; step 0), with the 2020 NEC and 2019 NFPA 13R and 72. The codes are free to read
      on ICC's and NFPA's sites, as is ASHRAE 62.2.
    - PHIUS where it goes further (ventilation, airtightness). The envelope stays as built; the
      report says what PHIUS would ask of it.
    - **No DIN standards.** They are sold one at a time (DIN 1946-6 from EUR 229.30, DIN EN
      12831-1 from EUR 209.50, DIN 1988-300 ~EUR 133 from a reseller), mostly in German, and
      aren't Pennsylvania's code.
    - **Plumbing noise is engineered from free sources.** US code limits sound through walls and
      floors between flats (IBC 1206) but not the noise of a neighbour's drain; DIN 4109 does,
      and isn't bought. Found so far: a CMHC research project on drain noise in cast iron, PVC
      and ABS (publications.gc.ca), a Quebec plumbing-noise study (mjm.qc.ca), CIB W062 papers,
      and the pipe makers' own data (CISPI, Charlotte Pipe: trade sources, to be marked so).
  - **The process:** design, then a round of feedback from installers, then inspection.
    - The designer keeps the design. Each installer's comment is logged like an RFI and is
      either taken (as an addendum) or answered.
    - Inspection can't happen on paper, so the set carries the inspection and commissioning plan:
      the pressure tests, the balancing report, the ventilation flows, a blower door.
  - **Decided (2026-11-21):**
    - **Hot water: one central plant for the building.** Jon: "yeah probably 1 water heater for
      the apartment building. maybe for condos id say individual per unit." Each flat gets its
      own hot-water meter and heat meter so it pays for what it uses. Whether Pennsylvania lets a
      landlord bill by submeter is to check.
    - **Rooms in the flats:** the draft layout stands unless Jon changes it. Two bedrooms at the
      end-wall corner; the bath, a utility closet and the kitchen in a line on the spine, back to
      back across it and stacked floor over floor; the rooms sum to the flat's 836 sq ft.
    - **Service rooms** (Jon: "there will probably need to be an electrical room, plumbing room,
      maybe even heating/hvac room etc."). Proposed: two rooms, a dry electrical room and a wet
      mechanical and plumbing room, in a one-storey annex behind the stair core, each with its
      own outside door. No HVAC room, since ventilation and cooling are per flat. Jon: "ok go
      with two rooms in the annex". The annex changes the published bid set (its walls, and the
      ground-floor stair window behind it), so it goes out as a revision with its diff.
  - **Steps:**
    0. **Ground truth.** The code editions in force in Indiana County, from the Pennsylvania
       Bulletin. The free source for each system. A known case for each calculation: NEC Annex
       D's multifamily load examples; the plumbing code's fixture-unit tables; IAPMO's free Water
       Demand Calculator (UPC Appendix M; whether Pennsylvania accepts it under the IPC is to
       check); ASHRAE 62.2 (already in the model); pipe and duct friction against closed forms.
       - **Found while scoping:** the bid set's checks (D27, steps 3-8) are to IBC 2018, one
         edition behind what Pennsylvania now enforces. To recheck (Jon to say when).
       - **Done 2026-11-21** (a research agent, then the Bulletin read again):
         - **The rule:** 55 Pa.B. 7701 (2025-11-08), Doc. No. 25-1513: "These regulations will
           be effective January 1, 2026." Not 25-1602, which York City's page links, a different
           rule (industrialized housing).
           - 34 Pa. Code §403.21(a) adopts the IBC, IMC, IPC (accessibility excepted) and IECC of
             2021.
           - §403.21(c): "Appendices to a code or standard listed in subsection (a) are not
             adopted", the IEBC's and two named ones excepted. So IPC Appendix E (pipe sizing) is
             not in force, and IAPMO's Water Demand Calculator could serve only as a method the
             code official approves (IPC 604.1).
           - Projects contracted under the 2018 codes could use them until mid-2026; that has
             passed.
         - **NFPA editions (IBC 2021 chapter 35, on UpCodes):** NFPA 70-2020, 13R-2019, 72-2019.
           Pennsylvania's IBC 903.3.1.2 allows 13R for R-2 up to 4 storeys.
         - **Climate zone 5A** for Indiana County (PNNL-33270, 2022). A 3-storey R-2 falls under
           the IECC's residential provisions (R202).
           - IECC 2021 R403.6.1 requires heat-recovery ventilation only in zones 7-8, so here
             it goes beyond code.
           - Air leakage: 3.0 ACH50 prescriptive (R402.4.1.3); for attached units tested one by
             one, 0.30 cfm50 per ft2 of enclosure.
           - Phius 2024 (Certification Guidebook v26.1.2, free) asks 0.06 cfm50/ft2, outdoor air
             to every bedroom, and supply and exhaust balanced within 10%.
           - IMC 2021 ventilation: Eq. 4-9 and Table 403.3.2.3 (kitchen 100 cfm intermittent or
             25 continuous, bath 50 or 20).
         - **Known cases found:**
           - **NEC 220.84:** Mike Holt's 12-unit example (EC&M, 2009, free). 460,800 VA connected
             x 0.41 = 188,928 VA. The NEC's own Annex D examples sit behind NFPA's login viewer:
             unread.
           - **Water demand:** the Water Demand Calculator's user guide (IAPMO, 2026). A one-bath
             house gives 9.0 gpm.
           - **Radiant floor:** REHAU's design guide 855.601 and pressure-loss tables 855.681.
           - **I-joist holes:** APA Z725E (2012) Table 5, hole size against distance from the
             support for 11-7/8 in. joists. The 2024 edition is to check.
         - **Plumbing noise, free:**
           - **The limit:** a neighbour's plumbing at no more than 33 dBA Leq (CMHC Research
             Highlight 99-112).
           - **Pipe data:** cast iron, PVC and ABS drains bare and enclosed (CMHC RH 02-117,
             paid for by CISPI, so trade-sponsored). Clamps, sleeves and drywall (NRC, Warnock
             and Morin 1990). Water pressure, mounts and wall contact (MJM's 1990 summary for
             CMHC).
         - **Fees:** Washington OFM's A/E fee guidelines (2027-29), Schedule B: ~10% of
           construction for design-bid-build at $2M. No split by discipline.
         - **Baseline:** Census, Characteristics of New Housing 2025, new multifamily units:
           - US: heat pump 52%, furnace 35%, air conditioning 99%;
           - Northeast: heat pump 43%, furnace 36%.
         - **Unread or unresolved:**
           - the 2021 IBC's corridor width (Table 1020.2) and escape openings (1031): UpCodes'
             chapter 10 page cuts off at 1010, as in D27, so Jon to save them;
           - 1208's exact wording: UpCodes' page was read only in summary, giving 1208.1 7 ft,
             1208.2 7 ft 6 in, 1208.3 one room of 120 ft2 and others 70;
           - NEC Annex D;
           - the 62.2 edition the codes cite;
           - a free shaft-wall STC source;
           - the MEP share of a fee;
           - WHO's bedroom levels at first hand.
    1. **Rooms.** The model has none (bidset.md). Two-bedroom flats with kitchens and baths
       stacked floor over floor and back to back across the spine, so a few shafts serve all
       12. A mechanical and meter room. Each escape window assigned to its bedroom, which closes
       D27's open item. Forge writes them to `out/pass3/apartment.json`.
       - **Forge done 2026-11-21** (`forge/src/rooms.rs`;
         `cargo run --release -- apartment-json addendum-2 60` writes
         `out/pass3/apartment-addendum-2.json`, Addendum 1 plus Addendum 2):
         - **122 rooms:** 10 a flat and the annex's two. In a flat, bed 1 113 ft2, bed 2 96,
           living 274, kitchen 82, bath 44 (5.35 x 8.12 ft clear), entry 86, study nook 61,
           utility 17, hall and passage 33.
         - **84 walls:** 6 partitions and a plumbing wall a flat. The plumbing wall is 2x6 with
           gypsum on the room side, a half inch clear of the spine. It runs behind the bath, the
           utility closet and the kitchen, so no pipe touches or pierces the party wall.
         - **The annex:** 20 x 10.8 ft behind the stair core, walls 9 ft. Mechanical and plumbing
           room 114 ft2 with a 42 in. door in its side; electrical room 70 ft2 with a 36 in. door
           at the far end. Both are provisional until steps 4-5 size the equipment.
         - **Removed:** the ground floor's back stair window (`1-stair/back/0`), which the annex
           covers (`Building::addendum_2`). It is the only opening that changes: 114 to 113.
         - **Forge's own checks pass:**
           - no room or wall overlaps another, the building's parts, the stair's or the annex's;
           - every flat is covered exactly: rooms, walls and the plumbing wall's gap sum to its
             floor;
           - every bedroom has a window in an outside wall;
           - the annex covers no opening left, and its doors sit in its walls.
         - **Found:** the stair splits the building in two. Its enclosure may be pierced only for
           fire protection, security and communication systems and the stair's own ventilation
           and power (IBC 2021 1023.5), not the flats' water, heat or power. So the annex's pipes
           and conduits reach both halves under the ground-floor slab: pre-insulated buried pipe,
           as district heating is laid.
       - **Checked against the code 2026-11-21** (`uv run brownfield systems`;
         `src/brownfield/systems.py`, `params/systems.yaml`). IBC 2021 1208, Table 1020.3 and
         1031 were read verbatim from UpCodes' pages as Jon saved them. 14 checks, all pass:
         - **Addendum 2 changes only the one stair window:** parts and the stair are unchanged.
         - **Each flat's rooms and walls cover its floor exactly,** measured against pass 3b's
           `flat_envelope`, an independent number.
         - **Room sizes:**
           - habitable rooms 7 ft in plan and 70 ft2: the narrowest is bed 1 at 9.23 ft, the
             smallest bed 2 at 96 ft2;
           - one room of 120 ft2 a flat: living 274;
           - ceilings 106.5 in on the upper floors, against 90 (84 in wet rooms); no soffits yet.
         - **Clearances:**
           - the hall 37.5 in clear, against 36 (Table 1020.3);
           - the kitchen 65.5 in clear past a 25 in counter, against 36.
         - **Escape windows:** every bedroom has one, named on the window. A 3 x 4 ft window can
           clear 1031 only side-hinged: hung, it opens under 24 in high; sliding, under 20 in
           wide. So the escape windows are casements. That closes D27's open question.
         - **Wet rooms** stack floor over floor and sit back to back across the spine.
         - **Plumbing walls** stand 0.5 in clear of the party wall.
         - **The annex** has its two rooms, each with an outside door.
       - **Tests:** `tests/test_walkup_systems.py`, 15 tests. Each check is broken on purpose
         and must catch it: a 69 ft2 bedroom, a 6.9 ft one, a 35 in hall, a low ceiling, a
         bedroom without a window, 52 in windows (a hung sash would then do), and one such window
         alone; a bath out of stack, a plumbing wall touching the spine, and one pushed into it;
         any other change to the building, a missing annex door.
       - **Review before commit (2026-11-21) fixed:**
         - the casement check took `all()` over the windows, so one window that could be hung
           would have slipped through;
         - the plumbing wall's gap was an `abs()`, so a wall pushed an inch into the spine read
           as clear;
         - `brownfield systems` now leaves the published plan sheet alone when a check fails;
         - 1023.5 is reworded to the 2021 text (fire protection, security and communication may
           pierce the stair; the flats' services may not).
       - **Plan sheet:** `docs/pass3/systems_plan.png`.
       - **Also closed:** safety glazing at wet areas (2406.4.5), which D27 couldn't assess
         without rooms. The baths have no windows.
       - **CORTENFORGE.md:** spaces (rooms) as part of the model, under Suggestions.
         **RESEARCH.md:** the Bulletin, IBC 2021 1208, 1020.3 and 1031, and step 0's sources.
       - **In the bid set's IFC, 2026-11-21** (`uv run brownfield systems --ifc`, written to
         `out/pass3/bidset/addendum-2/`; the published bid set is untouched). Addendum 2 is run as
         a reviewed change against Addendum 1, as `brownfield addendum` ran Addendum 1.
         - **The items:**
           - 122 rooms as IfcSpace, each with its use, the openings in its walls and its net
             floor area (Qto_SpaceBaseQuantities);
           - 72 partitions and 12 plumbing walls (IFC4's PLUMBINGWALL);
           - the annex's walls, slab, roof and two doors: D4 (36 in, electrical) and D5 (42 in,
             mechanical);
           - the stair window removed;
           - the 24 escape windows their own type, W3, side-hinged (BidSet_Unit.Operation
             "casement"), with every window carrying Pset_WindowCommon.FireExit yes or no.
         - **The diff against Addendum 1:**
           - 92 elements added, 1 deleted (the stair window), no opening moved;
           - new types W3, D4, D5 and 4 wall types; marks W1, W2 and D1-D3 keep their
             numbers and GlobalIds (escape types number after the others).
         - **The removed window was safety glazed,** so safety glazing goes 14 -> 13 openings.
         - **Checks:** all 34 pass.
           - IfcOpenShell (22): every element, opening and room once, each where forge has it
             (to 1 mm), no clashes among 130 walls and slabs, schema valid;
           - a second export byte for byte the same;
           - web-ifc (11).
         - **The checklist (IDS):** "escape window (yes or no)" 0 -> 100 of 100 windows;
           "operation" 0 -> 24. The escape windows' clear-opening fields are 0 of 24: those are the
           maker's numbers, for the window quote.
         - **Schedule:** W3 new (24), D4 and D5 new; W1 99 -> 75; W2 2 -> 1.
         - **Unchanged:** the base bid set's and Addendum 1's IFC regenerate byte for byte as
           published.
         - **Fixed on the way:**
           - the schedule diff matched types by kind and size alone, so the 42 in entry door and
             the 42 in mechanical-room door collided ("D2 renumbered D5"); it now matches on the
             unit named in the description too;
           - Addendum 1's wording rebuilt a type key by hand and broke when keys grew; it counts
             by mark now.
         - **Review before commit fixed:** every window with no hazard carried "2406.4.5, wet
           areas, not assessed: the model has no rooms" into the IFC, false once the rooms are in.
           With rooms, `safety_glazing` now assesses 2406.4.5 (glazing in a bath's walls: none),
           and the units say so. The base bid set and Addendum 1 still regenerate as published.
         - **Our choice, for Jon:** the annex is inside the thermal envelope, since its pipes
           mustn't freeze, so its doors take the exterior door's U-factor.
         - **Open for step 6 (fire):** where the annex abuts the stair, the stair's back wall
           stops being an exterior wall. It must carry the enclosure's 1-hour rating (IBC 2021
           1023.2) there; the model rates the stair's side walls only. (Step 6: confirmed, and
           1023.7 reaches further into the annex; see step 6.)
         - **Tests:** `tests/test_walkup_systems.py` gains 5 (20 in all):
           - the checks pass;
           - marks and type GlobalIds kept;
           - the diff is the addendum;
           - an escape window left unmarked fails;
           - a window put in a bath's wall is found under 2406.4.5.

           `test_bidset.py`'s type-key test now names the escape element. The suite: 291 pass.
       - **To do:** publish Addendum 2 in the plan room (the website) if Jon wants it.
    2. **Loads, room by room:** heat (the existing model split by room), cooling, ventilation,
       water demand, drainage and electrical load.
       - **Sources, read verbatim 2026-11-21** (a research agent, then checked against its saved
         pages; `params/systems.yaml`):
         - **IMC 2021:** 403.3.2.1 Equation 4-9, Q = 0.01 A_floor + 7.5(N_br + 1); Table 403.3.2.3,
           kitchen 25 cfm and bath 20 continuous.
         - **Phius 2024 Guidebook:**
           - 15 cfm per occupant supplied (18 recommended), outdoor air to every bedroom;
           - occupants are bedrooms + 1;
           - supply and exhaust within 10%;
           - 0.06 cfm50 per ft2 of gross enclosure.
         - **2025 ASHRAE Handbook, Indiana County Airport** (climate.onebuilding.org's .stat):
           heating 99.6% -16.3 C; cooling 0.4% 30.9 C dry bulb / 22.6 C wet bulb. ERA5 at the
           site, 2005-2023: the 0.4% hour 30.1 C.
         - **PA's 2021 IECC, zone 5:** frame walls U-0.051 (R-23, 13 + 7.5 or 20 + 3.8);
           ceiling U-0.026; windows U-0.30; a heated slab needs R-5 under its full area besides
           its edge insulation (Table R402.1.3 footnote d).
         - **For later steps:**
           - IPC 2021 Tables 604.3, 604.4, 709.1, 710.1(1), 710.1(2) and 906.1;
           - Appendix E (Hunter), read from Michigan's 2021 IPC, since Pennsylvania doesn't
             adopt it;
           - Mike Holt's 12-unit NEC 220.84 example (0.41);
           - Ecotope's Ecosizer manual (25 gal per person per day at 120 F; peak hour 15.2% of
             the day; recirculation ~100 W a flat).
       - **Found: the walls as drawn don't meet the code now in force.** The bid set carries pass
         3's U-0.060 (R-20, IECC 2018). Pennsylvania's 2021 code asks U-0.051, so the walls need
         continuous insulation (R-20 + 3.8 or R-13 + 7.5). The ground floor's heated slab needs
         R-5 under it.
       - **Addendum 3, the envelope to code, 2026-11-21.** Jon: "yes addendum 3 - and it should
         bring the envelope to code".
         - **Forge:** `apartment-json addendum-3 60 1`; `Building::addendum_3`, the insulation
           thickness from `params/systems.yaml` `addendum_3.ci_in`.
         - **Item 1, walls:** the exterior walls and the annex's take R-3.8 continuous
           insulation (1 in.) over the R-20 cavities, U-0.051 (Table R402.1.3's 20 + 3.8). They
           thicken inward from 7 to 8 in.: the building stays 100 x 40 ft outside, the rooms
           along the outside walls lose an inch (a flat 836 -> 831 ft2), and the stair, set
           against the back wall, moves an inch with it.
         - **Item 2, slabs:** the heated ground slab sits on R-5 under its full area, with R-10
           at the edge to 4 ft; the annex's slab takes the same edge.
         - **Unchanged:** windows (U-0.30) and roof (R-49) already meet the 2021 code.
         - **Checks:**
           - Addendum 3's own: walls thicker by exactly the insulation, the outside and every
             opening unchanged;
           - the 14 room checks;
           - the 17 stair checks;
           - the IFC's (both readers).

           All pass.
         - **RFI 002 (BCF)** asks which code the walls meet and points at the 15 exterior walls.
           Addendum 3 answers it.
         - **The diff against Addendum 2:**
           - nothing added or deleted;
           - the 15 walls changed type and properties, every wall and unit moved with the
             thickness;
           - 50 rooms resized, 2 slabs gained their insulation;
           - no window or door changed type or size.
         - **Fixed on the way:** the element diff couldn't take a resized room (an IfcSpace)
           and crashed; it reports spaces on their own now.
         - **The loads** take the walls' U-factor from the model (U-0.051 in Addendum 3).
         - **Unchanged:** the base, Addendum 1 and Addendum 2 regenerate byte for byte (models
           and IFC), and so does RFI 001.
       - **2a, heat room by room, built 2026-11-21** (`src/brownfield/loads.py`). Each flat's
         envelope is shared among its rooms by what each touches: walls and slab edge by length
         along the outside walls, windows its own, roof by area, leakage by exterior area,
         ventilation where the air is supplied.
         - **The check:** in pass 3b's case every flat's rooms sum to `house.ua`, part by part,
           within 4e-15 W/K.
         - **The radiant floor** is sized per room on its heated area (less the kitchen's
           cabinets and the tub). The flat's manifold supplies its hardest room's water.
         - **Found:** pass 3b's whole-flat average said ~29-31 C water. Room by room, the ground
           floor's corner bedroom (two outside walls and the slab edge) needs 38.3 C at 92 W/m2,
           the floor at 28.4 C against the 29 C limit.
       - **2b, ventilation, built 2026-11-21.**
         - **Each flat:** 45 cfm balanced, the Phius supply and the IMC's exhaust governing
           alike; the IMC's own floor is 30.9.
         - **Supply** to the bedrooms by occupant (30 and 15); exhaust from the kitchen (25)
           and the bath (20). The air passes through the hall and the living room between.
         - **Checks:** 5, all pass.
       - **The engineered design's heat** (`design_case`):
         - **Inputs:** that ventilation with an ERV (sensible recovery 0.75, a placeholder
           until step 3; step 3 put in the chosen unit's HVI ratings, 0.64 at the design hour),
           Phius's airtightness on each flat's share of the enclosure, and ASHRAE 2025's -16.3 C.
         - **Result:** design loads 31-41% under pass 3b's case. The ground floor's corner
           bedroom still sets the water at 36.8 C (36.3 C with the walls at code).
       - **Cooling groundwork:**
         - NOAA's sun position against PVGIS's sun height: within 0.24 degrees.
         - The beam on each vertical wall by geometry against PVGIS's: within 1.5% a year.
         - The isotropic diffuse model reads the south and west walls' peak hours more than 5% low
           (a test holds it), so cooling uses PVGIS's own sun-on-wall series, 2005-2023, cached.
       - **Tests:** `tests/test_walkup_loads.py`, 9.
       - **Step 2 finished 2026-11-21** (`uv run brownfield loads`, on Addendum 3; writes
         `out/pass3/loads.json` for steps 3-6). All 8 checks pass.
         - **Sources, read verbatim from saved pages:**
           - the IECC reference design's internal gains (IGain = 17,900 + 23.8 CFA + 4,104 Nbr
             Btu/day) and its 75 F cooling setpoint (Table R405.4.2(1));
           - Indiana County Airport's 428 m and 96,288 Pa;
           - IPC 2021 Tables E103.3(2)-(3) (Michigan's copy), 709.1 and 710.1(1)-(2);
           - Ecosizer's manual and its engine's load shape (commit 7586430);
           - Holt's 220.82 and 220.84 articles.

           Multi-row tables are in `data/` with their sources.
         - **Corrections to the research agent's reading:**
           - Table 709.1 counts a kitchen sink with its dishwasher as 2 dfu together, so a flat
             is 9 dfu, not 11;
           - the Ecosizer occupancy table's layout text is shifted a row. The raw text, and
             each column's own pattern (CTCAC 1.5 a bedroom; ASHRAE market rate 1.49 + 0.45 a
             bedroom), give a 2-bedroom flat 2.57 / 3 / 2.39 / 2.83: the agent was right.
         - **Heat:** the engineered design on Addendum 3's envelope takes 1,629-2,432 W a flat
           against pass 3b's case 2,744-3,502 (with step 3's ERV; 1,524-2,327 with the
           placeholder). The floor water on pass 3's floor model is 33.1-37.6 C, the corner
           bedroom setting it; step 3 replaces that floor model with REHAU's.
         - **Ventilation:** 45 cfm a flat (above).
         - **Cooling** (`room_cooling`, `cooling_design`):
           - **Method:** every hour of 2005-2023, PVGIS's sun on each wall, the air shifted
             +0.78 K so its 0.4% hour meets ASHRAE's 30.9 C. Conduction at the hour's air (the
             slab edge left out), sun through the glass at an SHGC of 0.35 (a placeholder: the
             schedule has none), leakage and ventilation (the ERV's recovery), IGain spread by
             floor area. Indoors 75 F; the four ways the building could face, the worst taken.
           - **Results:** each flat 3.23-3.36 kW sensible (0.92-0.95 ton) at the 0.4% hour,
             worst with the long facade west (front flats) or east (back). The living room
             about 1.9 kW, worst facing south on the lower floors (low autumn sun on its glass)
             and west on the top. Outdoor air latent 89-106 W a flat with step 3's ERV (its
             HVI moisture transfer, 0.74; 160-180 W with the placeholder 0.5).
           - **On Addendum 4's glass (U 0.22, SHGC 0.25):** 2.49-2.60 kW sensible (0.71-0.74
             ton). Its heat (ERV alone): 1,431-2,234 W a flat.
           - **Limit:** no thermal mass, so peaks lean high.
         - **Water** (Hunter, IPC Appendix E as the approved method under 604.1):
           - a flat 7.8 wsfu (cold 4.7, hot 4.9) and 9 dfu;
           - demand: a flat 12.6 gpm, a stack of three 20.9, half the building 28.2, the
             building 41.9 (hot 31.7).
         - **Drains:** 3 in. branches and stacks (a water closet's minimum; a stack carries 27
           dfu against 48). The building drain is 4 in. (108 dfu; 3 in. takes 42 at 1/4 in./ft).
         - **Hot water, the design day** (Ecosizer: 25 gal a person, 3 a flat):
           - 900 gal at 120 F;
           - the busiest hour (07:00-08:00) 137 gal, 24.7 kW of heat;
           - 163 kWh a day from a 46.0 F inlet (step 4's mains correlation; 154 kWh from the
             50 F placeholder it replaced);
           - recirculation 1.2 kW.
         - **Electrical:**
           - **Known case:** Holt's 12-unit example reproduced exactly (460,800 VA, 188,928
             VA, 787 A).
           - **Each flat's feeder (220.82):** 18.3 kVA, 76 A, with step 3's 12k mini-split at
             its 14.2 A MCA (16.6 kVA and 69 A with the placeholder). The optional method wants a
             feeder of 100 A or more, so 100 A.
           - **The 12 flats (220.84):** 307.8 kVA connected x 0.41 = 126.2 kVA, 526 A at
             120/240 V or 350 A at 208Y/120 V, before house loads (287.3 kVA, 491 A with the
             placeholder). The ERV preheaters (482 W each) aren't in it yet: step 5.
           - **Placeholders:** the appliance nameplates, until chosen.
           - **Restated by step 5** with the appliances chosen, at 208 V: a flat's feeder 19.1
             kVA; the 12 flats 339.1 kVA connected x 0.41 = 139.0 kVA, 386 A at 208Y/120 V before
             the house.
         - **Tests:** `tests/test_walkup_loads.py`, 17, the known cases among them.
         - **Review before commit fixed:** `weather()` carried the site's coordinates as numbers
           in the code; it takes them from `land.PLANT` (EIA-860), as the test now does. An unused
           import went, and the module's docstring covers 2a-2f.
         - **What we don't know:**
           - the windows' SHGC (a placeholder; the ERV's recoveries were placeholders until
             step 3);
           - the appliance nameplates;
           - the cold inlet's temperature (step 4 computes it);
           - Hunter against IAPMO's Water Demand Calculator (free, by email form: Jon to fetch
             if wanted). Hunter is known to read apartments high;
           - cooling's thermal mass;
           - the house loads (steps 4-5).
    3. **Heating, cooling and ventilation:** radiant floor loops on the loop's ~30 C water, a
       manifold and a heat meter in each flat, every loop balanced; heat-recovery ventilation in
       each flat; cooling sized to the real load (a radiant floor can't cool); ducts sized.
       - **Step 3 designed 2026-11-21** (`uv run brownfield hvac`, on the latest revision, now
         Addendum 4; writes `out/pass3/hvac.json`). Code: `src/brownfield/hvac.py`, and
         `loads.erv_sensible`, `loads.preheat_c` and `design_case(preheat=True)`. Parameters:
         `params/systems.yaml` `radiant`, `substation`, `heat_meter`, `ducts`, `erv`,
         `minisplit_12`, `minisplit_18`, `minisplit`, `addendum_4`. Tests:
         `tests/test_walkup_hvac.py`, 12; all 12 checks pass.
         - **Sources:**
           - REHAU's radiant design guide (855.601) and PEX pressure-loss tables (855.681);
           - HVI's certified-products spreadsheets (Section III, generated 2026-11-18);
           - Broan's, Fujitsu's and Kamstrup's data sheets and submittals, and the Danish type
             approval of Kamstrup's meter;
           - the PHI comfort criterion for supply air.

           A research agent found the equipment; I read the REHAU chart and Kamstrup's tables
           myself.
       - **3a, the radiant floors:**
         - **The floor's output:**
           - **Calibration:** REHAU's worked example for this construction (a 1.5 in. pour, ½ in.
             pipe at 6 in.: 25 Btu/h ft2 under R-1.0 carpet at a mean water 62 F over the room).
             With EN 1264's surface relation it gives the pour's own resistance, 0.169 m2K/W.
           - **Checked** against REHAU's performance chart (Fig. 6.5, an image read by eye, ±1
             Btu/h ft2): bare at 6 in. 14.5, R-0.25 11.8, bare at 4 in. 17.4 Btu/h ft2, all at
             20 F. The model asks 0.8-1.8 F more water than the chart: the safe side.
         - **Found: pass 3's floor (6 W/m2K water to room, "judgement, to source") was
           optimistic.** This floor, bare, is about 4.
           - Pass 3's "every flat runs on ~30 C water" becomes 35.1-40.2 C here (Addendum 4's
             glass; 36.7-41.5 C on Addendum 3's).
           - Its conclusion holds: no heat pump for space heat, the flats run off the data
             center's 50 C return. But the margin is 9.8 K, not ~20.
           - To correct in pass 3's report.
         - **Coverings:** sheet linoleum or vinyl (R-0.26) in the living rooms, bedrooms and halls;
           tile (R-0.23) in the wet rooms. Laminated hardwood (R-0.87) would ask 47.3 C on the
           ground floor, just over the 47 C the exchanger can give (49.2 C on Addendum 3's glass):
           the covering is a design decision, not a finish to leave to the end.
         - **Loops:**
           - ½ in. PEX at 6 in.; 4 in. where a room needs over 60 W/m2 (the ground floor's
             corner bedrooms, 66 W/m2).
           - No circuit in the inside rooms. The top floor's low-heat rooms (under 15 W/m2:
             hall, bath, utility, passage, kitchen, entry, 164 W together) share one circuit, in
             series.
           - That gives 5-7 circuits a flat, near REHAU's preferred manifold of up to 6 (without
             the sharing, the top floor had 12).
           - Every circuit is under 330 ft, every surface under its limit (the warmest 26.2 C).
         - **The water:** one supply for the building, set by its hardest room (the ground
           floor's corner bedroom): 40.2 C. Every other loop is balanced to the flow that
           delivers its heat, the water cooling toward the room along the loop.
         - **Friction:** Darcy-Weisbach with Churchill's factor, the PEX taken as smooth (0.485 in.
           bore for ½ in.), within 3% of REHAU's Table 1A in turbulent flow.
       - **3b, ventilation:** one ERV a flat in the utility closet's ceiling.
         - **The unit:** Broan EDGE BLP120E80NS-HW, the basis of design.
           - **Why it:** 120 V, four 4 in. ports. HVI rates it at 49 cfm against the flats' 45:
             sensible recovery 80% at 32 F and 55% at -13 F (over its defrost), moisture
             transfer 0.74 in cooling, 28 W.
           - **Alternatives the agent ruled out:**
             - Zehnder's ComfoAir 160 ERV needs 240 V, and its PHI certificate lapses on
               2026-12-31;
             - Panasonic's FV-12ESC1 has 6 in. ports, and its defrost recirculates.
         - **Its recovery at the design hour** (-16.3 C = 2.7 F), on a straight line between
           HVI's two tests: 0.64. The 0.75 placeholder was optimistic; step 2's loads are rerun
           with it (above).
         - **Found: the fresh air reaches the bedrooms at 6.8 C at the design hour,** under the
           Passive House Institute's 16.5 C comfort minimum. It lands on the bedroom floors, the
           rooms that set the water.
         - **Found: the Broan defrosts by stopping its supply fan** (HVI's -13 F test: 69%
           imbalance), so in the coldest hours a flat runs on exhaust only.
         - **The fix, Jon's decision 2026-11-21: an electric preheater ahead of each ERV.**
           - Broan's manual permits an in-line duct heater, electric (with its own airflow and
             over-temperature sensors, 12 in. from the collar). It says warming the outdoor air
             to 0 C keeps the unit out of defrost.
           - **Set to 2.5 C:** at HVI's 32 F recovery (80%), that brings the ERV's own supply to
             16.5 C.
           - **At design:** 482 W a flat. Over a year 345 kWh a flat (about 4,100 for the
             building), over about 2,400 hours (ERA5 2005-2023).
           - **It replaces** the hot-water post-heater coil step 3 first added (248 W a flat off
             the manifold): after the preheater, the coil would add 0.5 K at most.
           - **The price, plainly:**
             - it spends 482 W of electricity at design to save 248 W of the loop's heat, since
               a warmer inlet leaves the ERV less to recover;
             - what it buys is ventilation that never unbalances, and warm air.
           - **Not asked of Broan:** a hydronic preheater off the loop, which would make it
             waste heat. Broan's manual names only an electric one. For the installers' round.
           - **Effect** (on Addendum 3's glass): the ground floor's water drops from 45.6 C (ERV
             alone) to 41.5 C.
         - **Ducts:** ACCA Manual D's friction-rate method on round galvanized steel (ASHRAE's
           0.0003 ft roughness), the unit holding 0.4 in. w.c. across its range.
           - Every branch 4 in. (none under the unit's ports); outdoor-air and exhaust ducts 4
             in., 16 ft to the facade.
           - The worst path 0.24 in. w.c. on the supply and 0.22 on the exhaust, against 0.4.
       - **3c, cooling:** one ducted mini-split a flat, its indoor unit over the hall, its
         outdoor unit on the roof.
         - **Selection:** the smallest of Fujitsu's ARUH12KUAS and ARUH18KUAS that covers the
           flat. Capacity is taken at our design point (87.6 F out, 75/63 F in, from Fujitsu's
           tables) and derated for the line set to the roof (16-36 ft) by Fujitsu's own factors.
         - **The glass decides the size.** Each 0.1 of SHGC moves a flat's peak by about 780 W.
           - At the placeholder SHGC 0.35 (Addendum 3): the 18k in every flat, 3.90-3.94 kW
             sensible against 3.23-3.37 kW. The 12k gives 2.77 kW sensible on the ground floor's
             36 ft line set: short.
           - **Addendum 4 (Jon's decisions 2026-11-21): SHGC 0.17-0.25, U 0.22.** The 12k in every
             flat, 2.77-2.96 kW sensible against 2.49-2.60 kW: 8% to spare on the ground floor,
             14% on the top.
         - **Ducts** (Addendum 4), at 0.3 in. w.c. (a setting inside the unit's 0.12-0.80):
           supplies to the bedrooms, study and living room by their loads.
           - On 2-front-left: living 276 cfm in 8 in., bed-1 117 in 6 in., bed-2 57 and study 50
             in 5 in.; a 10 in. return in the hall.
           - The rooms under 150 W (182 W together) take the hall's moving air.
         - **Addendum 4,** published to the plan room:
           - **The item:** every window and patio door rated, whole unit, at ENERGY STAR v7's
             Northern zone (all of western Pennsylvania): a U-factor of at most 0.22 (the code
             asks 0.30), an SHGC from 0.17 to 0.25, air leakage of at most 0.3 cfm/ft2.
           - **Where it lives:** the schedule and the IFC carry the U-factor and the SHGC. The IDS
             holds the SHGC to its range: 0 of 112 glazed units pass on Addendum 3, all 112 on
             Addendum 4. Its U line stays the code's 0.30, as Addenda 2 and 3 print it.
           - **Nothing drawn changes:** 112 units changed in properties, on 4 types.
           - **Such units are sold, NFRC-certified, all Pella 250 Series vinyl:**
             - the casement with SunDefense+ glass and the foam-insulated frame, U 0.22 / SHGC
               0.18;
             - the fixed unit, 0.22 / 0.22;
             - the sliding patio door with 1 in. triple-pane SunDefense glass, 0.19 / 0.23.

             The patio doors go triple-pane: the dual-pane doors don't reach 0.22.
           - **The effect:** the windows from U 0.30 to 0.22 take the building's design heat from
             21.8 to 19.4 kW and its water from 41.5 to 40.2 C; the cooling barely moves.
           - **The model:** Addendum 4 draws nothing, so its model is Addendum 3's plus the glass,
             made in Python (`systems.addendum_4`), not forge.
       - **3d, the building loop:**
         - **The plant:** a plate heat exchanger in the annex's mechanical room off the data
           center's liquid loop (its 50 C return, pass 2), keeping a 3 K approach (judgement,
           until selected).
         - **At design** (Addendum 4): 19.4 kW for the 12 flats, 40.2 C out and 27.9 C back,
           6.04 gpm. The data center's water drops from 50 C to 30.9 C at 3.90 gpm.
         - **Pipes:** pre-insulated PEX mains below the slab to two risers, one in each plumbing
           wall, six flats each.
           - Sized to 4 ft/s, half REHAU's 8 ft/s limit, for quiet.
           - A 1 in. header (3.2 ft/s) and ¾ in. risers (2.7 ft/s).
           - Lengths taken square until step 7 routes them: 55 ft of main and 20 ft up.
         - **Heat meters:** one per flat, Kamstrup MULTICAL 403, qp 0.6 m3/h, its smallest. At
           design 61-183 l/h, 10-31% of qp, inside its 6-1,200 l/h; 0.01-0.04 psi.
         - **The pump:** 8.1 ft at 6.04 gpm along the worst path (the riser at its whole flow,
           the meter, the index circuit). The exchanger's and the valves' drops come with their
           selection. A small circulator.
       - **Jon's decisions (2026-11-21):**
         - "we can go with your recommendations": the glass at SHGC 0.25 or under (Addendum 4,
           above), and an electric preheater ahead of each ERV (3b);
         - ENERGY STAR's Northern zone for the glass, "yes": U 0.22, SHGC at least 0.17, folded
           into Addendum 4 before it went out.
       - **For the installers' round (step 8):**
         - the low-heat loops are balanced to 0.015-0.1 gpm; can a manifold's valves and flow
           gauges be set that fine, or does each room's actuator cycle its loop instead?
         - at part load a flat's flow falls toward the meter's 3 l/h cut-off, under which it
           counts nothing;
         - a hydronic preheater for the ERV off the loop, instead of the electric one.
       - **Not yet:**
         - the routes (step 7, CortenForge), which replace every length taken square;
         - the duct fittings' equivalent length (70 ft a path, judgement until routed);
         - the exchanger and the pump selected;
         - the ground slab's own chart (taken as the pour);
         - the slab edge's F-factor (pass 3's 0.6, judgement), which drives the ground floor;
         - the mini-split's back-up heat and the stair's heat (step 6: with no heater the stair
           holds about 55 F at the design hour, enough for wet sprinkler pipe; comfort is apart);
         - the preheater's circuit in each flat's panel (step 5: done, and the preheater grew
           to 1 kW so it covers the design hour at the voltage it gets);
         - a bath floor warmed for comfort;
         - the hall's dropped ceiling for the indoor unit against IBC 1208.2's 7 ft.
    4. **Plumbing:** cold and hot water and recirculation, the hot-water plant (central or per
       flat, to choose), drains and vents, plumbing noise.
       - **Step 4 designed 2026-11-21** (`uv run brownfield plumbing`, on Addendum 4; writes
         `out/pass3/plumbing.json`). Code: `src/brownfield/plumbing.py`. Data:
         `data/ecosizer_multifamily_stream.csv`, `data/ipc2021_e103_3_4_taps.csv`,
         `data/ipc2021_906_1_vents_3in.csv`. Parameters: `params/systems.yaml` `plumbing`,
         `hot_water`, `noise`. Tests: `tests/test_walkup_plumbing.py`, 9; all 12 checks pass.
         - **Sources:**
           - the IPC 2021's chapters 6, 7 and 9, and its Appendix E (Michigan's copy);
           - Ecotope's Ecosizer manual (2025) and its engine's source (EcosizerEngine, commit
             7586430), read, not run;
           - WHO's Legionella guide (2007) and CDC's Legionella toolkit;
           - the CDA Copper Tube Handbook (2026) and REHAU's PEX plumbing guide (855.739);
           - EnergyPlus 26.1 and NREL's Building America protocols (the mains correlation);
           - NAIMA's pipe heat-loss table and ASHRAE 90.1-2019 Addendum aq (insulation);
           - Watts', Neptune's, Badger's and Leonard's data sheets;
           - CMHC Research Highlights 99-112 and 02-117, and Warnock and Morin (NRC, 1990);
           - the EPA's water-system record for the Central Indiana County Water Authority.

           A research agent read the device curves, the codes' pages and the guides; I read
           Ecosizer's code, the CMHC and NRC papers and Appendix E myself.
       - **Known cases:**
         - **Ecosizer against its engine's own regression results, to a millionth:** 100
           people at 25 gal a day give 84.84 kBtu/h and 567.72 gal. With a swing tank on a 5 gpm
           loop returning at 110 F: 106.71 kBtu/h, 624.06 gal, an 80 gal swing tank and 43.86
           kBtu/h (the parallel loop tank's case, 187.5 gal, was held until step 5 replaced it).
           - Its manual's worked example (270 gal running) doesn't reproduce from the engine's
             load shape (321 gal): the shape changed after the manual.
         - **Appendix E's sample problem:** 9.36 psi left for friction, exactly.
         - **Pipe heat loss against NAIMA's table:** within 1-4% at every insulation thickness,
           never under. Bare pipe within 0.03%.
       - **4a, the cold water's temperature:** EnergyPlus's mains correlation (Burch and
         Christensen) on the site's ERA5 air, 2005-2023: 50.1 F a year, monthly means 43.9 F
         apart. The mains run 46.0 F on the coldest day and 56.1 F on average. That replaces step
         2's 50 F placeholder.
       - **4a, the hot-water plant** (one, in the annex's mechanical room, Jon's decision):
         - **The temperatures:**
           - stored and leaving the heater at 140 F (WHO: "not less than 60 C"; CDC: "above
             140 F");
           - sent out at 125 F through an ASSE 1017 master mixing valve;
           - back at 122 F or more (WHO: the return "not less than 50 C"; CDC's floor for
             circulating water is 120 F).
         - **Sized by Ecosizer,** with a swing tank (revised in step 5, Jon's decision): the
           design day's 900 gal at 120 F is 843 gal at 125 F. That takes 38.0 kBtu/h (11.1 kW)
           over 16 hours and 239 gal of storage at 140 F (141 gal running, against a floor of 64).
           Ecosizer sizes a swing-tank plant's heater from the inlet to the storage temperature,
           so it's larger than the first sizing's 34.8.
         - **The heat comes from the data center.** A plate exchanger off its 50 C return
           preheats the heater's own circuit to 116.6 F, with no lukewarm water stored. That is
           75% of the plant's heat: 8.4 kW, 133 kWh on the design day.
           - **A water-to-water heat pump** on the same circuit lifts the rest to 140 F: 2.8 kW
             of heat. Its own heat comes from the same data center water after the exchanger,
             whose flow (1.68 times the heater circuit's) is throttled so it leaves at 80 F.
           - **Why:** first drawn on the data center's 122 F water, it had no real unit: none in
             the US is rated there (step 5).
           - **Basis of design:** ClimateMaster Tranquility SW036. Its published rating is source
             80 F, load in 120 F, 141 F out, COP 4.4. That gives 44 kWh of heat for 10.0 kWh on
             the design day.
           - The 4.4 replaces pass 2's Carnot-share model's 9.3, which was flagged as
             overstated.
           - The unit gives 34.6 kBtu/h against the 9.5 it's asked for: the smallest made,
             cycling against the storage.
         - **The loop:**
           - 998 W lost, 83 W a flat, within Ecosizer's 66-175 W spread of measured
             buildings;
           - 2.27 gpm holds 125 F out and 122 F back;
           - ½ in. returns, mains and risers, at most 2.0 ft/s (REHAU's limit for returns).
           - **It returns to a swing tank** (Ecosizer's, revised in step 5; Jon: "go with your
             recommendations"). A 40 gal tank in series between the storage and the building,
             with a 1.75 kW element.
             - Every draw passes through it, fed by the plant's 140 F water, so the plant's heat
               (three quarters of it the data center's) covers the loop's loss while hot water
               is used.
             - The element runs only in the quiet hours: 5.6 h on the design day, 9.8 kWh.
             - The plant carries 59% of the loop's 24 kWh.
             - No water-to-water heat pump is made small enough for a separate loop tank; an
               element alone would take all 24 kWh at COP 1.
         - **The whole design day:** about 89% of the hot water's heat comes from the data
           center (the preheat, and what the heat pump draws from its water); 20 kWh of
           electricity (the heat pump and the swing tank's element).
         - **The hot pipes:** insulated 1 in., and 1½ in. from 1½ in. pipe up (ASHRAE 90.1
           Addendum aq, past the IECC's R-3). No hot pipe is more than 31 ft from the loop to a
           fixture, against IPC 607.2's 50.
       - **4b, cold and hot water** (IPC Appendix E, from the building's pressure-reducing valve
         to the top floor's shower, the highest outlet needing 20 psi):
         - **The water side:**
           - a reducing valve set to 60 psi static, for quiet: Warnock and Morin found noise
             rises 5 dB from 40 to 100 psi;
           - PEX throughout, at CDA's velocities for quiet (8 ft/s cold, 5 hot), stricter than
             REHAU's 10 and 8 for its own pipe;
           - a 2 in. double check valve assembly; the authority may ask for a
             reduced-pressure zone assembly instead, at 8.5 psi more at the peak.
         - **Sizes:** cold 1½ in. mains, 1¼ in. risers, 1 in. to each flat; hot 2 in., 1½ in.,
           1 in.
         - **Pressure to spare at the top floor's shower:** 11.2 psi cold, 8.9 hot (the master
           mixing valve takes 7.0).
         - **The street must give 49.5 psi at the peak.** That's the hot path's needs plus the
           meter (0.6), the tap (0.2), the backflow assembly (6.0) and the main's depth (2.2).
           - The Central Indiana County Water Authority (EPA PWSID PA5320040) publishes no
             pressures or hydrant tests, and has no website.
           - **To do:** ask for a hydrant flow test (NFPA 291). Under 49.5 psi the building
             needs a booster.
       - **4c, drains and vents:**
         - four 3 in. stacks, one per column of flats (27 dfu each);
         - stack vents through the roof, 1½ in. at least (Table 906.1 at 11 ft developed);
         - no vent stack (904.2 asks one at five branch intervals; three here) and no frost
           closure (903.2: the site's design air is above 0 F);
         - a 4 in. building drain below the slab (108 dfu).
       - **4d, plumbing noise** (no DIN 4109; CMHC's 33 dBA for a neighbour's plumbing):
         - **Cast-iron stacks and branches above the slab.**
           - Each stack runs down through the plumbing walls of the flats below, so their
             rooms hear a neighbour's flush through drywall. CMHC measured that case: cast iron
             25 dBA, 8 dB under the limit; PVC 33, none to spare.
           - The caveats: the measurements are trade-sponsored (by the cast-iron makers'
             association) and in a reverberation chamber, not a furnished room.
           - PVC below the slab.
         - **The stacks face only wet rooms:** every plumbing wall bounds a bath, a utility
           closet and a kitchen, checked from the model on every floor.
         - **Supply pipes:**
           - plastic, in closed-cell sleeves at every support, at 60 psi: 26 dB under copper
             clamped rigidly at 80 psi, on Warnock and Morin's relative scale;
           - batts in the plumbing walls.
       - **Submetering:** each flat gets a cold and a hot water meter (Badger E-Series ¾ in.,
         1.0 psi at design flow).
         - The hot meter's stated accuracy ends at 122 F, and the loop runs 122-125 F: a meter
           rated for hot water to confirm.
         - **Pennsylvania:** the PUC has held a landlord who bills tenants for water isn't a
           public utility (Glazier v. Energy Management Systems, 2005, after Peter Daniels
           Realty, Pa. Super. 2003). 66 Pa.C.S. § 1313 caps a reseller's bill at the utility's
           residential rate. Whether that reaches a municipal authority's water is for counsel.
       - **Not yet:**
         - the street pressure (the hydrant test);
         - the plant's control sequence: the data center's flow through the exchanger held so
           its water leaves at 80 F while the heat pump runs (step 9);
         - the routes (step 7), which replace every length taken square, and with them the
           mains' and risers' lengths;
         - the hot meter's rating;
         - the stack vents' height above the roof (IPC 903.1.1 leaves it to the adopting
           jurisdiction; Pennsylvania's not found);
         - the building drain's route to the sewer, and the sewer's depth;
         - the inspection tests (step 9).
    5. **Electrical:** the service, meter room, feeders, panels and circuits, and space for EV
       chargers and solar.
       - **Step 5 designed 2026-11-21** (`uv run brownfield electrical`, on Addendum 4; writes
         `out/pass3/electrical.json`). Code: `src/brownfield/electrical.py`, and
         `climate.pvgis_pv` (PVGIS's PV estimate). Data: `data/nec2020_table_310_16.csv`,
         `nec2020_ch9_table_8.csv`, `nec2020_ch9_table_9.csv`, `nec2020_240_6_a.csv`,
         `nec2020_table_250_66.csv`, `nec2020_table_250_122.csv`, `bussmann_c_values.csv`.
         Parameters: `params/systems.yaml` `electrical` (the appliances), `wiring`,
         `flat_panel`, `meter_stack`, `electrical_room`, `house_panel`, `service`, `pv`, `ev`,
         `house`. Tests: `tests/test_walkup_electrical.py`, 10; all 19 checks pass.
         - **Sources:**
           - the 2020 NEC (what the 2021 IBC references) through free sources that quote it:
             NFPA's own TIAs and development records, Holt, EC&M, IAEI, ElectricalLicenseRenewal,
             and Public.Resource.Org's scan of the 2017 edition for sections 2020 didn't change;
           - FirstEnergy's Customer Guide for Electric Service, Pennsylvania (September 2021),
             its tariff and its interconnection guides;
           - Eaton Bussmann's "Short Circuit Current Calculations" (its point-to-point method);
           - the makers' sheets for every piece of equipment chosen;
           - the IFC 2021 (rooftop PV pathways) and IMC 2021 (roof access) through UpCodes'
             state copies; PVGIS.

           Three research agents read them; I checked each number used against its saved text,
           and read the ampacity table's 600-1000 kcmil rows off the scan myself.
       - **Known cases:**
         - **NEC 220.84:** Holt's 12-unit example, exactly (step 2's check, kept).
         - **NEC 220.82:** Holt's 1,500 ft2 house (EC&M, 2020): 28,600 VA connected, 28,710 VA,
           120 A at 240 V, exactly.
         - **Fault current:** Bussmann's two worked examples, within 0.1% (its own rounding):
           300 kVA at 208 V gives 46,273, then 39,425, then 18,687 A; 75 kVA single-phase gives
           22,322, then 18,453 A line to line.
         - **Voltage drop:** the phasor calculation gives 2 K I L / CM exactly (12 AWG, 16 A, 100
           ft: 6.336 V).
         - **The tables agree:** Table 9's AC resistance within 3.4% of Table 8's DC, copper 14
           AWG to 250 kcmil.
       - **5a, each flat's panel and circuits:**
         - **The panel:** a 30-space Square D QO load centre (125 A main lugs), flush in the
           hall's wall behind the bath. The hall's 37.5 in. gives the 36 in. of working space
           110.26(A) asks. 23 of 30 spaces used; the legs within 1%.
         - **The circuits:** 19 a flat.
           - Lights on two 15 A circuits of their own, the sleeping side and the living side, so
             a tripped receptacle never darkens a room; the smoke alarms on the sleeping side's.
           - Receptacles on four 20 A circuits (each bedroom, the living room, the study and
             halls); the ground floor's living-room circuit takes the patio's outdoor receptacle
             (210.52(E)(2)).
           - The code's required circuits: two kitchen small-appliance, the laundry closet's
             receptacle, the bathroom's (210.11(C)).
           - One for each appliance at its maker's breaker:
             - the induction range (Frigidaire GCRI306TBF, 11.3 kW at 208 V, 40 A);
             - the dishwasher (Bosch SHX53DM5N);
             - the refrigerator (Whirlpool WRF540CWH, its own current a placeholder);
             - the over-the-range microwave, which is also the recirculating hood (GE
               JVM3160RF);
             - the washer and the heat-pump dryer (Bosch 500 Series, both 208 V; no 24 in.
               heat-pump dryer runs on 120 V);
             - the ERV with the manifold's controls;
             - the ERV's preheater;
             - the mini-split's outdoor unit on the roof (15 A, Fujitsu's maximum).
         - **Protection:**
           - AFCI on every 120 V circuit in a room 210.12(A) lists (everywhere but the bath);
           - GFCI where 210.8 reaches: the bath, the countertop and laundry receptacles, the
             dishwasher (210.8(D)), the washer's and dryer's 240 V receptacles in the laundry
             area (210.8(A) covers 125-250 V in 2020);
           - the mini-split's outdoor unit (210.8(F)). Pennsylvania didn't amend 210.8(F), and
             the 2020 TIA's exception for listed HVAC equipment expired 2026-09-01; the panel
             vote to extend it split 10-10 and is under appeal. Inverter mini-splits are known
             to trip ordinary GFCIs: the set asks for one Schneider says is made for them
             (QO 2-pole "HF-rated", no catalogue number published): a question for the
             installers' round.
         - **Conductors:** copper NM at its 60 C ampacity (334.80), the smallest its breaker
           protects (240.4(D)), then larger until the circuit drops at most 3% at its design
           load. That's its maker's nameplate, or for a receptacle circuit 1,500 VA at the
           farthest outlet. The living room's lights and receptacles went to 12 AWG for it.
       - **5b, the feeders:**
         - **The meters go outdoors,** on the annex's long wall that has no door:
           - FirstEnergy wants meters outdoors without its written approval otherwise;
           - each tenant must reach the breaker on their own feeder (240.24(B): a feeder
             breaker serving one flat isn't one "supplying more than one occupancy"), so a
             locked meter room wouldn't do;
           - so each flat's breaker sits with its meter.
         - **The stack:** Square D EZ Meter-Pak, 208Y/120 V in, each flat 120/208 V on 5-jaw
           sockets (FirstEnergy asks the fifth jaw for 120/208 V). Four columns of four (its
           most is four high), sockets 33-60 in. up (its limits 30 and 72), 9 in. apart (its
           least 8). Twelve flats, the house and three spares, a main ahead (FirstEnergy past six
           meters). 68 in. wide, 85 of the wall's 240 in. with the PV disconnect and the surge
           protector.
         - **Each feeder:** from its meter under the slab to a riser in the hall's wall and up,
           79-130 ft taken square. 19.1 kVA by 220.82, 88 A a leg; a 100 A breaker.
         - **Its copper:** at least 83% of the breaker (310.12(B) reaches a 120/208 V flat's
           feeder), so 3 AWG; then larger until it drops at most 2% at that load, so 3, 2 or
           1 AWG by length. Copper in PVC, EGC 8 AWG.
           - The drop is computed by phasors on two phases and the neutral. On 120/208 V the
             neutral carries current even when the legs are balanced, and the 120 V loads lose
             more than VA / 208 suggests.
           - Feeder and branch together: at most 4.72% at any outlet, inside the
             informational notes' 5% (not enforceable; no energy code reaches a 3-storey R-2).
       - **5c, the house loads** (one 45 A position on the stack, 120/208 V like a flat):
         9.5 kVA calculated (step 6 sourced the alarm panel: 120 VA, not the 240 placeholder).
         - the plant's heat pump (ClimateMaster SW036, MCA 22.3 A, on a 25 A breaker);
         - the swing tank's 1.75 kW element (step 4's plant);
         - the two circulators (Grundfos ALPHA2, 45 W);
         - five stair luminaires (Lithonia TSL9, 27.8 W, with sensor and 90-minute battery),
           one at each landing;
         - the annex's and the doors' lights, four receptacles (the roof's service receptacle,
           210.63; one at the meter wall, 210.63(B)(1)), the fire alarm and telecom
           (placeholders).
       - **5d, the service** (208Y/120 V three-phase, offered by FirstEnergy):
         - **The calculation:** the flats 339.1 kVA x 0.41 = 139.0 kVA (220.84), the house 9.5;
           148.6 kVA, 412 A.
           - **The preheater counts as space heating** (a duct heater, Article 424), so under
             220.84(C)(5) and 220.82(C) only the larger of it and the air conditioning counts.
         - **The main:**
           - the meter stack offers 400 and 600 A mains, none between;
           - 412 A takes the 600 A main;
           - its lugs take cable to 500 kcmil, so two sets of 250 kcmil copper (510 A).
           FirstEnergy asks for approval of parallel sets to a meter stack: a question for it.
         - **The calculation is the code's, not the building's.** No 12 all-electric flats on a
           warm-water loop will draw 149 kVA together, but the code sizes the service.
         - **Fault current, with placeholder inputs** (a 150 kVA transformer at 1.5% Z, 40 ft
           of lateral; FirstEnergy gives the real ones on request):
           - 24.2 kA at the meter stack, so QOH tenant breakers (42 kA);
           - at most 4.9 kA at a flat's panel, under its QO breakers' 10 kA.
         - **The rest:**
           - a surge protector at the main (230.67, every service supplying dwelling units);
           - the grounding electrode is the footing's rebar (4 AWG to it); 1/0 AWG by Table
             250.66 to any other.
       - **5e, the electrical room** (70 ft2): the house panel and space for a later panel
         and PV inverters on its long wall (46 of 114 in.); the fire alarm and the telecom
         backboard on its side wall; 36 in. of working space before each.
       - **5f, room for solar, and none for chargers:**
         - **Solar:**
           - the flat roof holds 31 kWp (72 modules) inside IFC 1205.3.1's 4 ft perimeter, less
             the 12 outdoor units, the four stack vents and a roof hatch;
           - 37.1 MWh a year (PVGIS, ERA5, 10 degrees south, 1,197 kWh/kWp);
           - the house panel takes 16.6 kW AC of it under the 120% rule (705.12(B)(3)(2)); the
             rest needs FirstEnergy's interconnection, its own meter position (three spares) and
             its lockable disconnect by the meters.
         - **No chargers at the walk-up.** D14 made cars optional and put EV charging at the
           site's mobility hub (Jon: "ev chargin would work, given the people even have cars").
           - If that ever changes, the 600 A main (which the code's load needs anyway) leaves
             67 kVA. That's 7 chargers at 7.2 kW unmanaged (continuous, 625.42; the 2023 NEC's
             7.2 kW least), or 4.5 kW each for one a flat under an energy management system
             (625.42).
       - **Found:**
         - **The plant's heat pump, as step 4 drew it, isn't sold.**
           - Step 4 fed it the data center's 122 F water. No US water-to-water unit is rated
             there: Trane's range ends at 120 F; ClimateMaster's heating tables end at an 80 F source
             and allow no extrapolation.
           - The fix, taken: feed it the same water after it has preheated the hot water, held
             at 80 F (the data center's flow through the exchanger sets it). ClimateMaster's
             SW036 is rated there: source 80 F, load in 120 F, 141 F out, 34,605 Btu/h for 2,313
             W, COP 4.4 (step 4, revised).
           - No water-to-water unit is small enough for the loop tank's 1.75 kW, so the loop
             returns to a swing tank instead (step 4, revised).
         - **The roof has no way up.** IMC 2021 306.5 asks a permanent means of access where
           servicing equipment means climbing more than 16 ft, and the 12 outdoor units sit 30
           ft up. A roof hatch with a fixed ladder: an addendum item. Where it goes is for step 6,
           since an exit stair's enclosure limits what may open into it.
         - **The 500 W preheater would fall short:** 470 W at a 3% drop against the design
           hour's 482 W. Ouellet's 1 kW unit gives 940 W at the voltage it gets. It takes a 5
           in. duct, so the outdoor-air duct goes from 4 to 5 in. (less friction), with the
           heater 24 in. from the ERV (Ouellet's distance, past Broan's 12).
       - **Decided** (Jon, 2026-11-21: "go with your recommendations"):
         1. The plant's heat pump takes its heat from the data center's water after the
            preheat; ClimateMaster's SW036 the basis of design (step 4 revised).
         2. The loop returns to Ecosizer's swing tank, its element 1.75 kW: 9.8 kWh on the
            design day against 24 for a loop tank's element alone (step 4 revised).
         3. No chargers at the walk-up (D14's mobility hub has them).
       - **Not yet:**
         - the routes (step 7), which replace every length taken square;
         - the transformer and the fault current from FirstEnergy, and its approval of the
           parallel sets and the meter stack;
         - the luminaires, the controls, the fire alarm (step 6) and the telecom, now
           placeholders;
         - the refrigerator's own current;
         - the PV modules and inverters, and FirstEnergy's interconnection;
         - Fujitsu's roof clearances for the outdoor units;
         - the roof hatch in the model (an addendum);
         - step 3's outdoor-air duct at 5 in. for the heater (its model still sizes it 4 in.).
    6. **Sprinklers and alarms:** NFPA 13R with a hydraulic calculation; the single stair
       depends on it.
       - **Step 6 designed 2026-11-21** (`uv run brownfield fire`, on Addendum 4; writes
         `out/pass3/fire.json`). Code: `src/brownfield/fire.py`. Data:
         `data/tyco_lfii_residential_sprinklers.csv`, `data/blazemaster_cpvc_sdr13_5.csv`,
         `data/watts_lf007_dcva_chartread.csv`, `data/nfpa13r_2019_fixture_loads.csv`,
         `data/nfpa13r_2019_domestic_demand.csv`. Parameters: `params/systems.yaml` `fire_code`,
         `sprinkler`. Tests: `tests/test_walkup_fire.py`, 9; all 12 checks pass.
         - **Sources:**
           - **IBC 2021, Pennsylvania's:** UpCodes' chapters 4, 5, 7, 9 and 10 saved whole, with
             the amendments UpCodes marks (903.3.1.2 among them).
           - **NFPA 13R-2019:** NFPA's own public development records, whose Second Draft prints
             the standard. Those are committee drafts, so the published wording may differ.
           - **IMC 2021 306.5:** UpCodes' Connecticut copy.
           - **The makers' sheets:** Tyco's sprinklers, BlazeMaster CPVC (from its fabricators'
             manuals), Watts' backflow assembly (its loss chart read by eye), Potter's switches
             and panel, First Alert's smoke alarm.
           - **The US Fire Administration's plans-review manual (2023),** for a worked example.

           Two research agents read them; I checked each quote used against the saved text.
       - **Known cases:**
         - **The USFA's worked example:** Q = K√P gives 7.66 psi, and Hazen-Williams gives 0.081
           psi/ft and 0.87 psi.
           - Its slide prints the bore as 1.087 in., but 0.081 is what 1 in. Schedule 40's 1.049
             in. gives (both bores are in its own pipe table); 1.087 would give 0.068. The worked
             numbers are reproduced at 1.049.
         - **Tyco's listing tables hold to Q = K√P,** within 0.3% on all 12 rows, and to 13R's
           0.05 gpm/ft2.
       - **6a, the one stair:** IBC 2021 Table 1006.3.4(1) allows one exit up to the third storey
         with four flats a storey and 125 ft of travel. The building has four flats a storey and
         at most 61 ft of travel, taken square from any room's far corner to the flat's door into
         the stair. The table's note a asks for sprinklers (903.3.1.1 or .2) and escape openings
         (1031, step 1): the stair depends on the sprinklers.
       - **The code's frame:**
         - **13R is allowed.** 903.3.1.2 as Pennsylvania amends it: four storeys or fewer, and an
           R-2's roof under 45 ft above the fire department's road. This roof is 32 ft up, with the
           road a placeholder 1 ft below the slab.
         - **Type V-B is enough with 13R:** 3 storeys, 60 ft, 7,000 ft2 a storey (Tables 504.3,
           504.4, 506.2), against 3 storeys, 32 ft and 4,000 ft2.
         - **The flats' walls and floors stay 1-hour.** 708.3's and 711.2.4.3's half-hour
           exceptions need NFPA 13, not 13R.
         - **No building fire alarm system** (907.2.9.1): no flat is three storeys above the
           exit (the top ones are two), and there are 12 flats, not more than 16.
         - **No carbon monoxide alarms** (915.1.1): nothing burns fuel, and there's no garage.
       - **6b, the stair's enclosure** (1-hour, 1023.2):
         - **The wall it shares with the annex is now part of it.**
         - **1023.7 reaches the annex.** The stair's back windows on floors 2 and 3 are unrated
           and sit above the annex, whose side walls meet that wall at 90 degrees.
           - So the annex's two side walls are 1-hour for their first 10 ft from the stair,
             ground to roof.
           - The mechanical room's 42 in. door, 5.4 ft from a window in plan, needs a 3/4-hour
             fire door.
           - That's an addendum item: wall types and door D5. Alternatively, rated windows in the
             stair (1023.7 only applies where its walls or openings are unrated).
       - **6c, the sprinklers** (116 in all):
         - **In each flat, 9:** Tyco TY2236 residential pendents (K 4.9), every room but the bath.
           - 6 in the open living area (living room 2; study, kitchen, entry and hall 1 each),
             each bedroom 1.
           - The laundry closet 1, intermediate-temperature: 13R 6.6.4 asks a sprinkler in a closet
             with a washer or dryer, and 6.2.3.3.4 the temperature for a ventless dryer.
           - The 44 ft2 bath goes without: 6.6.2 allows up to 55 ft2.
           - Coverage: 12x12 to 14x14 ft at 13 gpm, 7 psi.
         - **The stair, 6:** quick-response (K 5.6), two a storey, at 225 ft2 each. 13R 6.6.9.1
           asks for sprinklers throughout an enclosed stair, and 6.6.9.4 designs it to NFPA 13.
         - **The annex, 2:** one in each room. 13R has no omission for mechanical or electrical
           rooms; NFPA 13's for electrical rooms would need the authority's say.
         - **None in the roof's joist space or the floors:** 13R 6.6.6, which omits concealed
           spaces that aren't lived in, used for storage or fuel-fired.
         - **CPVC throughout** (BlazeMaster, C 150), concealed in the ceilings and walls.
       - **6d, the hydraulics** (Hazen-Williams, each compartment its own design; 13R 7.1.1.3.1:
         all its sprinklers up to four):
         - **The route:** the fire service enters the annex's mechanical room: a 2 in. double
           check assembly, which 13R 6.8.5-6.8.6 lets serve as the check and the control valve.
           It runs into the stair (1023.5 lets fire protection pierce it), up a 2 in. riser at the
           back of each storey's hall, and through the stair's side walls into each flat at its
           door.
         - **Sizes:** each flat's feed 1½ in., its branch lines 1¼ in. With 1 in. branches the
           top flats' living area would ask the street 50.2 psi, over the 45 allowed; at 1¼ in.
           it asks 38.1.
         - **What governs:** the stair, read the safe way, every one of its 6 sprinklers flowing
           (127 gpm, 40.4 psi). Whether 13R 7.2.3.1's four-sprinkler limit applies to the stair
           is the authority's call. The top flats' living areas come next: 4 sprinklers, 55 gpm,
           38.1 psi.
         - **The street's 55 psi is step 4's placeholder,** held to 45 for its seasonal swing
           (903.3.5 asks for that adjustment). The hydrant test (NFPA 291) settles it.
           - It needs a 3,800 gal supply over 30 minutes (13R 9.2.1).
         - **A separate fire service,** so no domestic demand is added (13R 9.3.1).
       - **The stair needs no heater for its pipe.** With no heater it holds about 55 F at the
         design hour (47 F with the walls' low U-values). It is tied about four times as closely
         to the flats (190 m2 of party wall and their doors) as to outdoors (its two end walls,
         roof, slab edge and air leakage). 13R 5.4.1 asks 40 F for wet pipe. The party walls' and
         doors' U-values are placeholders.
       - **6e, the alarms:**
         - **36 smoke alarms,** three a flat: each bedroom and the hall outside them (907.2.11.2).
           - Photoelectric, as the hall's is 7.8 ft from the kitchen (6 ft is the least,
             907.2.11.3).
           - Interconnected within the flat (907.2.11.5), on the building wiring with a battery
             (907.2.11.6): step 5's sleeping-side lighting circuit.
         - **The sprinkler system's own:**
           - a waterflow switch and an exterior horn-strobe (903.4.2);
           - tamper switches on the backflow assembly's two valves (903.4: electrically
             supervised by a listed panel);
           - a monitoring panel (Potter PFC-6006) sending to a supervising station (903.4.1),
             on an 8 Ah battery (3.6 needed for 24 h and 5 min). Step 5's house panel carries it
             (120 VA, now sourced).
         - **A separate, supervised fire service** (Jon, 2026-11-21: "keep it separate").
           - **The other way:** a main shared with the taps. 903.4's exception 3 would then drop
             the panel and the monitoring, if there were no separate sprinkler shutoff.
           - **But a shared main must add the flats' domestic demand** (13R 9.3.1). That's 93.6
             fixture load units and 42.9 gpm (Tables 9.3.2(a) and (b)), so 170 gpm under the
             stair's reading and 98 for the flats.
             - That outgrows step 4's 2 in. service and meter, on a street pressure not yet
               known.
             - Any shutoff of the water for plumbing would also shut off every sprinkler, and no
               fire department call goes out.
           - **The one stair depends on these sprinklers.** Their valves shouldn't be closable
             unseen, and a monitored flow calls the fire department.
           - **The cost difference is for step 10's baseline:** a second service, its backflow
             assembly and the monitoring contract against the bigger shared service. It needs
             sourced prices.
         - **A fire department connection** (13R 6.11.1: over 2,000 ft2 or one storey), on the
           street side (912.2.1), with a check valve and an automatic drip.
       - **6f, the roof hatch** (step 5's finding):
         - **Over the top storey's stair hall,** 30 x 36 in., with a fixed ladder (IBC 1011.16
           and IMC 306.5).
         - **It may open from the stair:** 1023.4 limits only the enclosure's openings other than
           unprotected exterior ones.
         - **No guards needed:** it sits 10.5 ft from the roof's edge (1011.13 asks for them
           within 10).
         - **The ladder leaves 73 in. of hall beside it,** clear of the flats' doors.
       - **Not yet:**
         - **The hydrant test,** and with it the water authority's fire service (size, tap,
           backflow device).
         - **The site plan:** the access road's grade, the main's distance, the fire department
           connection's place.
         - **The routes (step 7),** which replace every length taken square and place each
           sprinkler exactly.
           - The sprinkler at each room's cell centre is a layout, not yet checked against the
             lights, the ducts' outlets or the 9 in. from the range 13R's table asks of an
             intermediate sprinkler.
         - **The NFPA 13 design for the stair and the annex,** the authority's reading.
         - **The addendum** (with step 7): the annex's rated walls and door, the roof hatch and
           its ladder, the stair's back wall rated where the annex meets it.
         - **The inspection tests (step 9):** 116 sprinklers, so the NFPA 13 hydrostatic test
           (13R 10.2.2.1), a forward-flow test of the backflow assembly (6.8.9), and the alarms'
           acceptance.
    7. **In the model and the IFC:** every pipe, duct, riser and piece of equipment; routes
       through the I-joists only where the maker's hole chart allows; a clash check; the
       schedules and the priced item list from the IFC, as the window schedule is.
       - **Planned 2026-11-21** (Jon: "go ahead with step 7"), in five parts, each reported and
         committed on its own:
         - **7a:** what the routes connect, and the frame they go through;
         - **7b:** the router, written in forge on cf-spatial's voxel grid (it ships no
           search);
         - **7c:** the routed lengths back into steps 3-6, whose checks rerun on them;
         - **7d:** the services as an IFC, with schedules and the viewer's layers;
         - **7e:** Addendum 5.
       - **Decided in the plan** (Jon approved it):
         - the flats' ducts run in soffits under the rated ceiling, not in the joists;
         - a vent stack per column;
         - each column's plumbing wall carries its vertical services, the lower flats' line
           sets among them;
         - branch circuits are routed too (step 5's worst outlet sits at 4.72% of the 5%
           limit);
         - quantities now, prices in step 10.
       - **7a done 2026-11-21** (`uv run brownfield routes`; writes `out/pass3/routes-7a.json`).
         Code: `src/brownfield/routing.py`, and forge `framing::addendum_5` (run by `framing-json
         addendum-5 ...`, which the command prints). Data: `data/nec2020_ch9_table_4_pvc.csv`,
         `data/nec2020_ch9_table_5.csv`, `data/pvc_sched40_od.csv`. Parameters:
         `params/systems.yaml` `routing`. Tests: `tests/test_walkup_routes.py`, 6; all 24
         checks pass.
         - **Sources:**
           - **Pennsylvania's 2021 code text from UpCodes:**
             - **IBC chapter 23:** 2308.4.2.4 (holes in sawn joists), 2308.4.3 (holes in
               I-joists only as the maker allows), 2308.5.8 (a steel tie wherever a pipe cuts a
               plate), 2308.5.9 and 2308.5.10 (studs: holes 40% of the depth, 60% in a
               nonbearing partition, 5/8 in. from the edge), 2308.7.4 and Table 2308.5.1;
             - **IPC chapter 4:** 405.3.1, 406.3, 409.2.
           - **NEC Chapter 9 Tables 1, 4 and 5** from Public.Resource.Org's scan of the 2017
             edition, read from its page images by a research agent. Every row matches PDHonline
             E276's transcription, and NFPA's 2020-cycle records change neither table.
           - **Wavin's Schedule 40 PVC conduit submittal,** for outside diameters.
           - **Fujitsu's design manual,** for the outdoor unit's size and installation space.
           - **Broan's EDGE installation manual,** for its hoods and its Tandem kit.
           - **APA Z725E Table 5,** the I-joist hole chart (already on hand).
           - **The equipment's sizes and service spaces,** from the makers' sheets, by a research
             agent:
             - Broan's EDGE spec sheet;
             - Fujitsu's manual, pages 8, 11 and 12;
             - ClimateMaster RP3006;
             - Lochinvar's HP tanks;
             - Bradford White;
             - Square D;
             - Bosch;
             - REHAU's manifolds and cabinets.

             REHAU's server refused plain downloads, and the agent got its sheets through WebFetch
             after a retry was refused. Jon accepted that (2026-11-21).

           Every saved text is kept under `data/raw/pass3g/` (gitignored), out of the session's
           temporary folder.
         - **The frame:** forge's Addendum 5 has 4,604 members.
           - It keeps the shell: 3,416 of Addendum 3's 3,418 members, the other two being the roof
             joists the hatch cuts.
           - It adds the flats' 84 partitions and plumbing walls (2x4 and 2x6 at 16 in.), the
             annex (walls with their two doors framed, its roof, its foundation), the stair halls'
             floors and the hatch's opening (doubled trimmers and header).
           - No two members overlap.
         - **Found: each water closet must sit in a joist bay.** The joists bear on the spine just
           behind the plumbing wall.
           - There, APA's chart lets no hole bigger than 1½ in. through them: a 2 in. hole needs
             7 in. from the support, a 4 in. hole 3 ft.
           - So each closet bend runs along its bay to the stack in the same bay. The water closet
             is set 21.6 in. from the tub (15 at least), the lavatory 30.9 in. on (30 at least).
           - The ground floor's water closets stand under the upper floors', one stack a column.
         - **Each plumbing wall's 10 vertical services** (stack, vent stack, hot, return, cold,
           the heating loop's two, three line sets):
           - each sits in a stud bay that is also a joist bay on both upper floors, so none passes
             through a joist;
           - the hot riser, 4.6 in. with its insulation, fits the 5½ in. cavity with 0.4 in. to
             spare.
         - **The panels move into whole stud bays,** up to 7.3 in. from step 5's point. The upper
           flats' feeders (1 and 1-1/4 in. PVC by NEC Chapter 9's fill) go up the bays beside
           them.
         - **The soffits:** 14 in. under the rated ceiling, over the hall, passage, utility closet
           and kitchen, plus a strip across the living room to the facade.
           - They leave at least 90.8 in. under them, against 84.
           - The strip covers at most 6% of the room, against a third (1208.2.1).
         - **Found: the ERVs' wall terminations need fixed windows.**
           - Broan asks 3 ft from an exhaust to any operable opening in a multifamily building.
             The facade's widest wall between openings is 3.4 ft, and the soffit sits 1.3 ft over
             the window heads.
           - So each flat's Tandem termination (one combination fitting, which IMC 401.4 lets
             skip the intake-exhaust separation) goes between two living-room windows specified
             fixed: 24 windows, an Addendum 5 item. No bedroom's escape window is among them.
           - The middle floor's goes one pier along, since stacked storeys are exactly 10 ft
             apart and 401.4 asks an intake 10 ft from another's exhaust or 3 ft below it.
         - **The roof:** 12 outdoor units, three to a column (Fujitsu: at most three side by side,
           10 in. apart), back to back across the spine. They are inside the 4 ft perimeter
           pathway and clear of the hatch's path.
         - **The equipment:**
           - **In each flat:**
             - the washer and dryer stacked against the plumbing wall;
             - the ERV in the closet's soffit, over its open floor, with room for Broan's 20 x 30
               in. access door;
             - the manifold's cabinet 16 in. up on the closet's wall to the bath;
             - the load centre flush in its bay.
           - **Found: the hall is too narrow for the mini-split.** Its 27-9/16 in. width with
             Fujitsu's 6 and 12 in. side spaces needs 45.6 in., and the hall is 37.5. So the hall's
             soffit reaches 8.1 in. past it, over the partition and the bath, along the unit. The
             partition stops at the soffit there (framed in 7b).
           - **The mechanical room holds the plant** with each piece's service space clear and
             the door's way in open:
             - **the storage tank:** Lochinvar HP250G, 250 gal (step 4 needs 238.6), 37 in. across
               and 97 in. high. Its anodes are on its side, so 36 in. beside it;
             - **the heat pump:** ClimateMaster SW036, 36 in. in front;
             - **the swing tank:** Bradford White RE340S6, 24 in. in front.
             - The tanks and the plate exchangers weren't chosen before; these are the basis of
               design.
         - **Found by the equipment's sheets:**
           - **No 1.75 kW element is made for the swing tank** (Bradford White offers 1.5-6
             kW), so step 4's element is 2.0 kW.
           - **The fire service's backflow assembly:** Watts says the LF007 is "UL Classified
             without shutoff valves only". Step 6 let it be the system's check and control
             valve, so the fire service takes listed, supervised shutoff valves of its own: an
             Addendum 5 item, and step 6's tamper switches go on them.
           - **Step 5's meter stack main** was named as the 400 A module in params. It is the
             600 A EZM3600CB, the same frame, rated 65 kA, and its lugs take step 5's two 250
             kcmil a phase. The wording is corrected; no number changes.
           - **The dishwasher's installation manual** cited in step 5 may be the 18 in. models'.
             Its circuit rule is to re-read (Jon: left open for now).
       - **7b done 2026-11-21: every service routed through the frame, and checked.**
         - **The router:**
           - `forge/src/routing.rs`, run by `routes-json`, with the requests from
             `src/brownfield/routes.py` (`brownfield routes --requests`). A* runs on a dense voxel
             grid of each request's zones: 1 in. voxels, 2 in. under the slab. Summed-volume tables
             make a pipe's clearance one lookup.
           - Each member is blocked, or crossable only along its bore axis and only where its rule
             allows the hole: APA Table 5 for the I-joists, IBC 2308 for studs, plates and sawn
             joists. The footings and the slab are crossed straight down only, in sleeves.
           - Every hole cut in an I-joist's web keeps later holes there more than twice the larger
             hole's diameter away, edge to edge (APA's rule 6), the request's own included; a joist
             with three maximum-size holes takes only smaller ones (rule 11).
           - Drains fall as they run (1/4 in./ft at 2-1/2 in. and under, 1/8 above, IPC Table
             704.1; the condensate 1%, IMC 307.2.1) and vents rise toward their stack (1/8 in./ft,
             IPC 905.2). The search keeps room for the pipe where its grade puts it; a drain's tree
             grows from its farthest fixture, and a branch joins only where the trunk has fallen at
             least as far.
           - Other trees grow from the nearest terminal. A request may join what it comes off
             anywhere along it (a stack, a riser).
           - After a pass, a run that failed moves one place earlier among its own flat's runs, and
             all are routed again (`passes`).
           - The clash check uses cf-spatial's grid as the broad phase and the boxes as the narrow.
         - **Known cases** (`routes-check`, all 8 pass):
           - an empty box routes at its square length;
           - a wall with one gap routes at the detour's closed form;
           - a member bored across one axis refuses a pipe along it;
           - APA's PRI-60 row is reproduced, with its span reduction;
           - a second hole near a first in a web moves to over twice its diameter away;
           - a joist with three maximum-size holes refuses a fourth, but not a smaller hole;
           - a drain falls, and a vent rises, by exactly its slope along every level run.
         - **Run:** 430 runs, all routed, no clashes, in one pass of about 2-1/2 minutes.
         - **Checks** (`brownfield routes`, `src/brownfield/routecheck.py`): worked again in Python
           from the frame and the code's numbers, not from forge's records. All pass:
           - the boxes overlapped again: no clash;
           - 2,518 holes in I-joist webs, the largest 96% of what APA's chart allows where it is;
             rule 6's closest pair 0.08 in. past its limit; no joist with over three maximum-size
             holes (rule 11);
           - 18 holes in studs, the largest 79% of IBC 2308.5.10's limit, 1.07 in. to the stud's
             edge at least; 1,191 in the roof's sawn joists, the largest 95% of 2308.4.2.4's third;
           - 876 cut plates, each tied with 2308.5.8's 16 ga strap;
           - every drain and the condensate falling, every vent rising, by its slope;
           - no duct through a rated ceiling, so no ceiling radiation dampers (IBC 717.6.2);
           - every wall holding a vertical service runs across the joists under it, so none needs
             2308.5.8's doubled joists;
           - the sprinklers moved still cover their cells and stand 8 ft apart.
         - **Counted for the firestop schedule** (7d), each needing a listed system (IBC 714.5):
           106 penetrations of the floors between flats, 532 up through walls' top plates into the
           floor/ceiling space, 39 through the ceilings' membrane (36 of them sprinkler drops) and
           13 through the party and stair walls (the sprinkler arms into the flats).
         - **Sleeves for the structural engineer:** 12 through the footings, 12 through the slab,
           30 through the stem walls.
         - **Routed lengths** (7c sizes them; 7d prices them): water 548 m, vents 288 m, the flats'
           drains 106 m and the building drain 43 m, sprinklers 380 m, ducts 320 m, line sets 98 m,
           the manifolds' tails 174 m, condensate 60 m, branch-circuit cable 1,716 m, feeders 263 m,
           the mains under the slab 90 m.
         - **Found** (each now a rule the requests keep):
           - **The plumbing wall carries no horizontal runs.** A riser fills the 2x6 cavity floor to
             ceiling, so nothing passes it along the wall.
             - The risers cluster at the wall's far end, past the last fixture.
             - In the wall, only straight up and down: supplies from the ceiling, vents to it.
             - Across, in the ceiling cavity: supplies, and the vents as one header a flat.
             - Drains go down through the floor and along the joists' space under it, or under the
               slab on the ground floor, to the stack.
             - Each vertical stands in a stud bay that is also a joist bay above.
             - **The joists' space directly over the wall is for the verticals only:** each run
               keeps out of it but where it goes up or down itself. Runs along the wall's top
               (the roof's sawn joists allow them) shut the other risers' way.
             - **Below the top floor, a flat's supplies tee off the riser in the joists' space**,
               not in the wall, where a branch beside the riser had no room for its own hole.
           - **APA's hole spacing decides the ceiling's layout.** In the first ~19 in. from the
             spine the joists take only small holes, and the vents, supplies and drains all ran
             along the next lane, stacked. Stacked holes count as one hole drawn round them
             (rule 12), which would need about 5 ft from the support. With rule 6 kept, the runs
             along the wall spread into lanes about 7 in. apart, and the crossings find room.
           - **A flat's lavatory, sink and washer drain into one 2 in. branch** (5 dfu; IPC Table
             710.1(2) gives a 2 in. horizontal branch 6), as a plumber runs it. Three drains side by
             side had shut the joists' space to the flat below.
           - **The building drain falls about 7 in.** over its 16.5 m from the far stacks, so it
             reaches the front wall 40 in. below the slab, under the perimeter footing's top
             (36 in.). The footing steps down where it leaves (for the structural engineer), and the
             sewer lateral takes it at that depth (a site item).
           - **The mini-split's condensate drains by gravity** (Jon, 2026-11-21: "gravity first").
             The ARUH12KUAS has no pump (Fujitsu lists none among its options), and its drain is
             1-1/8 in. above its bottom, which was the soffit's floor: no room to fall 1% to the
             washer's standpipe. So the hall's, the passage's and the closet's soffits go 2.5 in.
             deeper under the unit and the ERV, both hung from the top. It falls 1% over about 5 m;
             the soffits still leave 88.3 in. under them (7 ft asked). The other way was a pump
             beside each unit: twelve more parts that can fail into a ceiling.
           - **The washer's standpipe** stands in the wall from its trap to the washer box; the
             washer's vent beside it, the condensate dropping into the box.
           - **24 sprinklers sat under equipment** (each hall's under the mini-split, each closet's
             under the ERV) and **8 under the middle storey's strip soffit**. Each moves clear;
             under the strip, the two in that line shift together so each still covers its cell.
           - **Step 6 put the hall's and the study's sprinklers 6.4 ft apart in every flat**, in one
             compartment; Tyco's sheet asks 8 ft. The study's moves 0.36 m, still covering its cell.
             44 moved in all; step 6's hydraulics rerun in 7c.
           - **NEC 110.26(E):** no soffit may run over a panel's footprint, since that space is
             dedicated to the electrical work. The panels move up to 29 in., each still facing its
             hall with its working space.
           - **A flat's hot branches at the code's R-3** (IECC R403.5.2), not ASHRAE 90.1's 1 in.:
             at 1 in. a 1 in. branch needs a 3-3/8 in. hole, over the 60% (3.3 in.) a 2x6 stud
             allows. The manifold's tails go bare: they run under 105 F (R403.4).
           - **The partitions stop under the soffits** wherever a soffit runs over or on both sides
             of one, so ducts cross without boring studs.
           - **The ERV's outdoor-air and exhaust ducts** are 8 in. with their insulation, so the strip
             soffit widens to 22 in. The Tandem kit's ports need to sit 9 in. apart (to confirm
             with its sheet).
           - **The middle storey's strip needs a leg.** Its termination is a pier past the kitchen's
             end, so the strip turns an L along the kitchen's side of the living room (11% of the
             room furred at most, under 1208.2.1's third). Two 8 in. ducts can't cross in a 14 in.
             soffit, so each keeps its own lane round the corner. The duct behind passes the other's
             port on the leg's side and takes the inside lane; the kit stays as drawn.
           - **The mini-split turns:** its return faces the passage, where the ERV's air comes in,
             and its supply the bedrooms. The ERV's duct taps the return collar at its end away
             from the living room's grille, so the living room's duct passes beside it.
         - **Decided (Jon, 2026-11-21: "Through the mini-split"):** the hall can't hold both
           systems' ducts. The mini-split fills its middle, and the ERV's bedroom supplies couldn't
           get past it.
           - So the ERV's fresh air goes into the mini-split's return, at its back, and the
             mini-split's ducts carry it to every room they serve, both bedrooms included.
           - Not into the unit's side knockout (4-15/16 in.): there the ERV's duct would cross the
             mini-split's supplies, and the 14 in. soffit has no room for one over the other.
           - The mini-split's fan runs on at low speed with the ERV; its energy goes into step 10
             once the fan's power is read.
           - The other options were 20 in. soffits (halls at about 7 ft 2 in.) or the supplies in
             the joists with 16 ceiling radiation dampers.
         - **Tried and dropped:**
           - Moving every failed run to the front of the order: fewer routed each pass (402, 378,
             386, 374 of 454).
           - A 30 in. band of the ceiling kept for the plumbing alone: the baths' circuits couldn't
             reach their boxes.
         - **What we don't know:**
           - The Tandem kit's port spacing; the return collar's height (read off a drawing).
           - APA's "maximum-size hole" (rule 11) read strictly: one that needs its location's row of
             the chart, not only one at the very limit.
           - The units over finished ceilings and IMC 307.2.3's overflow protection (a second drain
             pan or a switch that stops the unit): 7c.
           - Fittings: the bends are counted, not yet weighed (7c, with Manual D's and the pipe
             tables' equivalent lengths).
           - The vents' 1/8 in./ft is our figure; IPC 905.2 gives none.
           - The router rounds each pipe up to whole voxels, so what it routes fits, and some runs
             it refused might fit by hand. Its order is set in `routes.py`, with the reasons;
             another order could find shorter runs.
           - The sprinklers near the soffits against Tyco's obstruction rules (TFP490), and the
             CPVC drops through the ceiling's membrane against IBC 714.5.2's exceptions: 7c.
           - The firestop systems themselves: counted here, chosen in 7d.
         - **Found for 7c:**
           - **The routed lengths, bends and moved sprinklers** go back into steps 3 to 6; the
             units' overflow protection (IMC 307.2.3); the building drain's depth to the site.
           - **The vent stack** (see Decided).
           - **Step 3's heating loop has one riser pair per side of the stair, serving six flats
             each.** The front and back flats' plumbing walls stand either side of the spine,
             which no pipe may pierce (rooms.rs). So one riser pair a column, four in all.
       - **7c done 2026-11-22: steps 3 to 6 on the routes.**
         - **How** (`src/brownfield/routed.py`, run by `brownfield routes` after 7b's checks):
           - Forge's routes are read back as trees: pieces between junctions, each with its length,
             its bends and the outlets beyond it. Each design runs on them in place of steps 3-6's
             square lengths and allowances.
           - **Sprinklers:** from each flowing sprinkler back to the riser assembly through every
             tee. Where two ways meet, the one asking more sets the pressure and the other flows
             more for it. On a single line it gives step 6's figures exactly. Every set of up to
             four sprinklers in each compartment is tried (13R 7.1.1.3.1); the stair's six all flow.
           - **Ducts:** Manual D's friction-rate method on each routed tree; a piece two rooms'
             ducts share carries both rooms' air. Fittings from Field Controls' FC80 manual for the
             ERVs, and Southwark Metal's Manual D-style guide for the mini-splits.
           - **Water:** IPC Appendix E along each flat's routed path, from the reducing valve to
             its shower, with every fitting counted: a sweep where the PEX bends (PPI's guide;
             Crane's loss for a bend at six diameters), Uponor's elbows and tees where fittings
             stand. The loop's heat loss is summed piece by piece, and IPC 607.2 checked along each
             routed hot branch.
           - **Wiring:** each branch circuit and feeder along its route, with 6 in. of free
             conductor at each end (NEC 300.14) and the drop down the wall to its outlet.
           - **The heating loop and the line sets:** the pump's head along each flat's routed path;
             each mini-split's capacity on its routed line set.
           - **Sizes only grow.** Where a routed design asks a larger pipe than was routed, the
             size goes into `data/route_sizes.json` and everything is routed again. The file is kept
             in git because the routes depend on the order sizes grew in. Where a design asks a
             smaller size, the smaller is taken: it fits where the larger was routed.
         - **Run (2026-11-22):** all 430 runs routed on the third pass, no clashes, in 390 s. 7b's
           checks all pass again on them (2,506 holes in the joists' webs, the largest 96% of what
           APA's chart allows there). All 16 of 7c's checks pass. 7c's tests: the tree hydraulics
           equal step 6's on a single line, Manual D sizes a shared piece for both rooms, a strip
           splits its room's coverage at its centreline, and a failed run fails 7c.
         - **Square (steps 3-6) against routed:**
           - the hardest sprinkler design: the stair's, 127 gpm at 40.4 psi, becomes 3-front-left's
             open area, 56 gpm at 44.7 psi, against the street's 55 psi less a 10 psi margin;
           - the ERVs' ducts: effective length 165-182 ft becomes 191-260 ft; worst path 0.264 of
             the fan's 0.4 in. w.c.;
           - the mini-splits' ducts: 162 ft becomes 222-363 ft; their static pressure is set at
             0.38-0.80 in. w.c. (step 3 had 0.30);
           - the line sets: 16-36 ft become 30-51 ft; the least cooling to spare is 33 W sensible
             (1-front-left);
           - the heating loop's pump: 8.1 ft of head becomes 13.1 ft;
           - the hot-water loop's loss: 998 W becomes 793 W (66 W a flat). Its mains under the slab
             are one branching run each, 58 ft hot and 59 ft return, where the square figure ran a
             61 ft main to each side of the stair;
           - the worst shower's path: 132 ft becomes 225 ft (cold) and 226 ft (hot); pressure to
             spare 11.2 psi becomes 3.0 (cold, 3-front-left), and 8.9 becomes 0.6 (hot,
             3-front-right);
           - the street at the peak: 49.5 psi needed becomes 54.4, of 55;
           - the longest hot pipe to a fixture: 30.5 ft becomes 39.5 ft (IPC 607.2: 50);
           - the feeders: 79-130 ft become 71-119 ft; the worst outlet's drop 4.72% becomes 4.69%
             (5%);
           - the longest branch vent: 32.6 ft (IPC 906.2 takes a vent a size up past 40).
         - **Found:**
           - **The stair's riser and the fire main grow from 2 to 2-1/2 in.** On the routes the
             flats' pipe is longer and turns more, and the hardest design moves into a flat.
             Growing the riser and the main (two runs, in the stair and under the slab) saves the
             most; growing every flat's branch lines instead would mean larger holes through every
             joist they cross. The margin is 0.3 psi, on a street pressure that is a placeholder
             until the hydrant test.
           - **The strip soffits are obstructions to the sprinklers' spray.** NFPA 13R
             6.4.6.3.6.4: "A sprinkler shall be installed on the other side of the obstruction";
             Tyco's TFP490 (Figure 2) allows sprinklers on both sides of one up to 4 ft wide, each
             within half its spacing of the centreline. So each side of a strip is covered by its
             own sprinklers. The middle storey's four living rooms get a third sprinkler (112 in
             all, from 108). The strips are 1.8 ft wide at most, and the floor under each strip's
             leg is 13.4 ft² of shadow (13R 6.4.6.3.3.1 allows 15).
           - **Each mini-split's static pressure is set to its routed ducts,** 0.38 to 0.80 in.
             w.c. Fujitsu's manual: set it "according to the resistance of the connecting duct".
             Four flats (1-, 2- and 3-front-right, 2-back-right) need 0.78 to 0.80, the unit's
             most, with 0.008 in. to spare. There the router ran the ducts as one trunk for about
             2 ft before they split, so they leave the plenum by one starting collar and two more
             elbows. The ducts can't grow (the soffits hold them at 8 in.). The fan's extra energy
             goes into step 10.
           - **The water passes only because the PEX bends.** With an elbow at every turn, the hot
             water would need 2 in. mains and risers, and the hot riser has 0.4 in. to spare in
             its wall. So the specification asks for bend supports at the turns, and elbows only
             at the fixtures' stub-outs, the risers' feet and where the top flat's branch leaves
             its riser (PPI: elbows "only when necessary, such as within tight cavities"). The
             margins are thin: 0.6 psi at the worst hot shower, and 54.4 of the street's 55 psi.
           - **The hot-water return main near the plant grows from 1/2 to 3/4 in.,** for its
             routed flow.
           - **The heating loop's pump head rises from 8.1 to 13.1 ft,** with a riser pair in each
             column and each flat's tails to its manifold counted.
           - **Six living rooms' lighting circuits drop from 12 to 14 AWG, and four feeders a
             size,** on their routed lengths.
           - **Two middle-storey water closets' vents (2-back-left, 2-front-left) found no path.**
             A vent's tree grows from its farthest fixture, the sink, so its header came first and
             crossed the joists 0.20 m from the floor above's drain. APA's rule 6 (holes over
             twice the larger apart) then left the water closet's vent no lane between them. Now
             forge routes an outlet that failed first in its own tree on the next pass, and all
             430 route on the third.
           - **Forge measured sloped runs along the axes,** overcounting a drain by its fall. It
             now measures each straight run end to end.
           - **The code items 7b left open:**
             - IMC 307.2.3, the mini-splits over finished ceilings: its option 4, a UL 508
               water-level switch in each unit's drain pan, wired to its forced-stop input
               (Fujitsu's function 46-02, a dry contact). 12, for 7d's schedule.
             - IBC 714.5.2: none of its exceptions covers the CPVC sprinkler drops through the
               rated ceilings (exception 1 is for metal pipe, 5 for a sprinkler's own annular
               space under a metal escutcheon). Each of the 36 takes a listed membrane-penetration
               firestop system with F and T ratings of 1 hour (714.5.1.2), chosen in 7d.
             - IPC Table 906.1 asks for the 2 in. vent stack 7a placed (27 dfu, 33 ft).
         - **Tried and dropped:**
           - An elbow at every bend of the water pipe: 230 ft more equivalent length on the worst
             path, and the pipes grew.
           - Growing the flats' branch lines and feeds first: to 2 in., with a larger hole through
             every joist.
           - One 20 ft sprinkler on the deeper side of each middle-storey strip: it needs 16.7 psi,
             which would push the riser and the main to 3 in.
           - The two middle-storey vents at 2 in., when an earlier route ran 54.4 ft (906.2): the
             water closet's vent found no path. At 1-1/2 in. they now route within 40 ft.
         - **What we don't know:**
           - The street's pressure, a placeholder until the hydrant test: the sprinklers need 44.7
             of the 45 psi after margin, and the water 54.4 of 55.
           - Duct fittings: ACCA's own table (Manual D Appendix 3) is paid and not opened. The
             mini-splits' pressures rest on Southwark's 30 ft elbow, at the high end of the
             published figures (McGill's ASHRAE data make a five-piece elbow about 7 ft).
           - The mini-split's fan power at each static-pressure setting, not published as a
             number: step 10.
           - Read second-hand or not at all: Crane's tables (through python-fluids), NFPA 13R
             2019's text (the 2022 draft was read), NEC 300.14 and the 15 in. outlet height.
           - The supply plenum's 12 in. depth is judgement.
           - The loop's loss, at 66 W a flat, sits at the bottom of Ecosizer's spread.
           - The routes depend on order: the requests', the sizes' growth and the retries. A
             rerun from git reproduces them.
       - **7d done 2026-11-22: the services as IFC, their schedules and the viewer's layers.**
         - **How** (`src/brownfield/servicesifc.py`, run by `brownfield routes --ifc`; `--publish`
           puts it in the plan room):
           - **The model:** one IFC4 file of its own (`services-addendum-5.ifc`), beside the bid
             set's and the frame's: 3,124 elements in 11 distribution systems.
             - Every routed run is cut into its pieces between junctions, each a pipe, duct,
               conduit or cable along the polyline forge routed.
             - Each piece's size comes from 7c's designs, edge by edge: the sprinklers' branch
               lines and feeds, each Manual D duct piece, the mains, each circuit's wire, each
               feeder's conduit by NEC Chapter 9.
             - It also holds 7a's risers, stacks and closet bends, the equipment (87), the fixtures
               (60), the sprinklers where 7b left them (118), a register, grille or wall cap at
               each duct's end (96), and the 12 water-level switches 7c found IMC 307.2.3 asks.
             - Each element carries its system, size, material, run, bends and holes through the
               frame (`BF_Service`).
           - **Fittings, as each material takes them** (1,588):
             - CPVC, cast iron, PVC, duct and conduit: a fitting at every bend and tee.
             - PEX: bent on a support at its turns (812 sweeps), with elbows only where 7c counted
               them.
             - Nothing on cable or the copper line sets, which are bent.
             - The drains' fittings by IPC Table 706.3: a quarter bend from horizontal to vertical,
               a long sweep otherwise, a sanitary tee where a branch enters a stack, a combination
               wye and eighth bend elsewhere.
           - **The schedules,** read back from the file (`out/pass3/services/schedules`, 11
             published):
             - lengths by system, material and size: 14,673 ft (plumbing 4,008; heating, cooling
               and air 2,678; sprinklers 1,319; wiring 6,667);
             - fittings, equipment, fixtures, sprinklers, registers, the switches;
             - 4,645 holes through the frame (forge's bores);
             - the steel plates over pipe and cable near a member's edge (none, bored at the
               centre);
             - the firestop schedule: every opening through an assembly and what IBC 714 asks of
               it.
           - **The viewer:** Plumbing, Heating cooling and air, Wiring and Sprinklers are live,
             each filtering the one services model by layer and coloured by system. A click shows
             a piece's system, size, material, length, bends and holes. URL options: `?plumbing`,
             `?hvac`, `?wiring`, `?sprinklers`. Seen working in headless Chrome (SwiftShader),
             clicked through its debugging protocol: a line set's riser, a 1 in. PEX cold-water
             piece, a 1-1/2 in. cast-iron vent.
           - **The plan room:** a "05 Services model" folder, preliminary, its open findings in its
             note.
         - **Checks,** all passing but the two findings below:
           - every element once (3,124);
           - every routed run's pieces where forge routed them and as long (0.000 mm);
           - every other element where 7a placed it;
           - schema valid with express rules (0 issues);
           - web-ifc reads every element and draws each where it should be;
           - the file's penetrations are forge's own count.
           - Tests: `tests/test_walkup_services.py`, 8: pieces, fittings by material, IPC Table
             706.3, IBC 714's rules, a riser as one opening, the feeders' bends, and the model
             whole on forge's routes.
         - **Found:**
           - **Seven feeders break NEC 352.26.** It allows 360° of bends between pull points. Each
             feeder runs from the meter in the annex under the slab to its riser, turning up at
             both ends, with no pull point between. As routed, 1-front-left, 1-front-right,
             2-front-right and 3-front-left reach 630°, 2-front-left and 3-front-right 540°, and
             2-back-right 450°. The other five are at 270-360°.
             - The router turns only at right angles. All twelve conduits leave one meter at one
               depth, so the later ones jog around the earlier.
             - Under a slab a conduit can run straight at any angle: two bends each (180°).
             - A pull box can't go under the slab (it must stay accessible).
             - Open, for Jon (see Next).
           - **Most rated openings have no listed firestop system that fits as tested.** 453
             openings pass through rated assemblies: 80 risers through the floor/ceiling, 296 up
             through partitions' top plates into it, 40 drains down through the subfloor, 24 CPVC
             sprinkler drops through the ceiling, and 13 sprinkler arms through party and stair
             walls. From the makers' published system sheets:
             - **Fit:**
               - STI F-C-1074 for the cast-iron stacks (16);
               - STI F-C-2032 for the feeders' PVC conduit (12) and the PEX risers (40). For the
                 risers, the insulation must stop at each face of the floor, since the system
                 lists no pipe covering (IBC 714.3).
             - **Partly:**
               - STI F-C-8021 for the line sets (12): their 14 AWG control cable is outside its
                 listed cables;
               - STI W-L-2816 (BlazeMaster Caulk & Walk Pro) for the CPVC through walls (13): it
                 is listed in single 2x4 walls, not double-stud ones.
             - **None found:**
               - for anything that goes up through top plates and ends in the floor/ceiling's
                 cavity (cable 144, PEX 112, cast-iron vents 40);
               - for CPVC through the ceiling's membrane (24).
             - The International Firestop Council: top-plate penetrations must be protected "as
               per a tested and listed penetration firestop system".
             - Every floor system found is listed in a UL L500 floor; ours follows AWC's generic
               WIJ-1.1. So even the systems that fit ask the authority to accept the floor, or
               the floor to be specified as an L500 design.
             - The drains down through the subfloor are iron and need only their annular space
               protected (714.5.2 exception 1). Hilti F-C-1134 and F-C-1135 list the closet
               flange and the tub's drain, if a tested system is wanted.
           - **The top storey's ceiling is unrated.** Type V-B rates no roof/ceiling (Table 601),
             so the 188 openings there need fireblocking only (718.2.1.4), and so do the stair
             riser's 3 through the stair's halls. 7b counted them as rated, and it missed 16 rated
             crossings at the pieces' short ends to their terminals and the top storey's four
             line-set risers. Its count now takes the ends and marks what's rated. The closet bends
             and the tubs' drains (16 more), which forge didn't route, are counted from the model.
           - **714.5.2 exception 7 asks the partitions under a rated ceiling to be sheathed in Type
             X** and the ceiling tight to their double top plates, so the plates can stand in for
             the ceiling: a specification item.
           - **No steel plates are needed if the holes are bored at each member's centre** (NEC
             300.4(A)(1), IPC 305.6, IMC 305.5, NFPA 13R 5.2.3.7). Forge drew 596 holes nearer an
             edge than those allow; every one clears bored at the centre. A specification item.
         - **What we don't know:**
           - The firestop systems' current revisions: UL Product iQ needs a login, and Lubrizol's
             BlazeMaster compatibility list wouldn't load. Several STI sheets are old (2011-2015).
           - NEC 352.26 and 300.4(A)(1) are from secondary sources (EC&M, IAEI), not the code. 300.4
             may exempt PVC conduit from steel plates; the schedule plates it anyway.
           - The fixtures' sizes are placeholders for the drawing (no fixture is chosen).
           - Whether the authority reads IPC Table 706.3's limit on quarter bends onto the 3 in.
             closet bends.
           - Not modelled:
             - the ports that connect each element to the next;
             - the mechanical room's wall-hung assemblies (the riser assembly, the backflow
               preventers, the plate exchangers, the pumps, the mixing valve: 7a placed none);
             - the smoke alarms;
             - the outlets and switches at the circuits' ends.
           - A riser that rises through every storey is filed on its lowest one, so the viewer's
             storey filter shows it on Level 1 only.
         - **Open, for Jon:**
           - **The feeders.** Recommended: let the router run straight at any angle under the
             slab, where nothing but the soil holds a conduit to the lattice. Each feeder then has
             two bends (180°) and runs shorter. Then reroute and rerun 7b-7d. Not recommended:
             - a meter stack at each column's riser, which changes step 5's service;
             - a high cost a turn, which still leaves 360° at best, at the limit.
           - **The firestop systems.** Recommended:
             - name one maker's engineering judgments for the conditions with no listed system
               that fits, submitted for the authority's approval (the usual way in wood-frame
               flats);
             - specify the floor as a UL L500 design that matches WIJ-1.1, so the listed systems
               apply as tested.
             - Optionally, feed the soffits' sprinklers inside the soffits, which removes the 24
               CPVC drops through the ceiling.
           - **Taken 2026-11-22** (Jon: "we can go with your recommendations"): see 7e.
       - **7e done 2026-11-22: Addendum 5, the services, the frame, the stair's enclosure and the
         roof hatch.** Jon took both recommendations above ("we can go with your
         recommendations"), and WIJ-1.3 for the floor when the L500 one fell through.
         - **How:**
           - **The building** (`systems.addendum_5`, from Addendum 4's model; forge's building
             draws none of it):
             - the annex's side walls 1-hour, the mechanical room's door a 45-minute fire door
               (1023.7);
             - the ground storey's back wall cut where the stair walls meet it, the middle piece
               part of the stair's 1-hour enclosure (1023.2);
             - the floors between flats 1-hour (711.2.4.3), named as AWC's WIJ-1.3;
             - the roof hatch, an opening in the roof filled by a trapdoor (D6, U-0.20, an opaque
               door the IECC holds to the fenestration U-factor: R402.3.4 exempts only a
               side-hinged one), and its fixed ladder.
             - `bidset.write_ifc` writes the ratings (`Pset_WallCommon`, `Pset_SlabCommon` and
               `Pset_DoorCommon` FireRating, with why in `BF_Fire`), the hatch and the ladder (IFC4
               has no ladder: an `IfcStair`, USERDEFINED "fixed ladder").
           - **The frame and the services** issued as bid documents: `framing-addendum-5.ifc` (4,832
             members) and `services-addendum-5.ifc`; the firestop, lengths and fittings schedules among
             the addendum's files, all eleven in the services' folder.
           - **The feeders straight under the slab** (forge `pull`, `sight`): forge's search, then
             the chain of straight runs through points along it that turns least, each run in clear
             sight with the conduit's width or as searched, crossing the stem walls and footings as
             searched. Requests ask it with `straight` (the feeders only); the conduit may touch the
             other feeders and its column's feeder risers.
           - The routes on Addendum 5's model: the roof ladder an obstacle; `data/route_sizes.json`
             keyed to the new model, so the fire riser and main (2-1/2 in.) and the return main (3/4
             in.) were asked again and routed at.
         - **Run (2026-11-22):** forge routed all 430 on its third pass, no clashes, 406 s. Every check
           of 7a-7d passes (71), Addendum 5's (both readers, a second export byte for byte), and the
           suite.
           - The feeders: 335-356° of bends from the meter to a panel (NEC 352.26: 360), 61-114 ft
             (square 79-130), six a size smaller; the worst outlet's drop 4.60% (5%).
           - Addendum 5 against Addendum 4: 4 elements added (the hatch, its opening, the ladder,
             the back wall's middle piece), 9 changed (the rated walls, door and floors; the roof's
             and the back wall's geometry), one type new (D6). The checklist's "in a wall" reads 27
             of 28 doors: the hatch is in the roof.
           - The services model: 3,118 elements; wiring 6,567 ft.
         - **Found:**
           - **The floor between flats wasn't WIJ-1.1.** WIJ-1.1 (AWC DCA 3, Feb 2024, p. 21) asks
             I-joist flanges at least 1-1/2 in. deep and 5.25 in.2; pass 3b's PRI-60's are 1-1/2 x
             2-5/16 in. (3.47 in.2). It also asks Type C board and mineral wool, where the repo said
             Type X. WIJ-1.3 (p. 23: flanges 1-5/16 in. and 2.25 in.2, web 3/8 in.) fits the PRI-60:
             2 in. of 3.5 pcf mineral wool on 1x4 setting strips, resilient channels 16 in. o.c., one
             layer of 5/8 in. Type C screwed 7 in. o.c., 23/32 in. sheathing. The ceiling's depth
             doesn't change.
           - **No UL L500 design matches the floor.** Every I-joist design found names Weyerhaeuser's
             TJI and two layers of board under resilient channels (L589, L570, L518 and the rest;
             L530, one layer, is on CSC clips with Thermafiber). Taking L589 would have meant TJI
             560 joists, a second layer and every route again. So the listed floor firestop systems
             (tested in L500 floors) take the authority's acceptance or STI's engineering judgment.
           - **The floor's IIC under a hard finish is short.** AWC's estimates for WIJ-1.3 at 16 in.
             o.c. with 1 in. of gypsum concrete: STC 57; IIC 59 under carpet and pad, 46 under
             cushioned vinyl, where IBC 1206.3 asks 50. Flagged in Addendum 5; the finish is chosen
             with the interiors (Jon).
           - **The feeders' bends:** the square search left 450-630°. Pulled to the farthest point in
             sight, 402-437° on four. Turning least, all twelve pass. A turn cost on the search (5 m
             a turn) changed nothing and was taken out.
           - **Addendum 4's published model had drifted from the code** (d92622a reworded its
             building's description after it was issued); the code now reads as issued, so a
             publish leaves Addenda 1-4 byte for byte.
         - **What we don't know:**
           - Whether the authority accepts STI's engineering judgments (345 openings) and the listed
             floor systems in a WIJ-1.3 floor: a question for the building department before bids.
           - The feeders' ends: a piece under 0.16 m at either end is counted as that end's sweep
             (forge lands a run up to two voxels short of its riser). A sweep's own radius may need
             more room than the riser's bay gives.
           - The hatch's U-factor and the ladder's make: placeholders and IMC 306.5's minimums.
           - The PRI-60's flange from pass 3b's schedule (`frame.json`), not a maker's sheet.
           - The UL directory's current designs and revisions: the L500 designs and the firestop
             systems were read from makers' reprints and a 2014 archive, not UL Product iQ (it needs a
             login).
           - NEC 2020 352.26 and 300.4(A)(1) were read through IAEI and EC&M, not NFPA 70's text.
    8. **The installers' round (Jon):** the set to a plumber, an HVAC contractor, an electrician
       and a sprinkler contractor; their comments logged, then taken or answered (Addendum 7).
       - **Jon's decisions (2026-11-22),** all four recommendations:
         - **The sheets first.** The services went out as a model, its schedules and the viewer's
           layers, and a trade reviews and bids from sheets: sent as they were, the set would
           likely get no comment or a request for drawings.
         - **A sprinkler contractor added.** NFPA 13R work is usually a fire-protection
           contractor's, and the one stair depends on the sprinklers.
         - **Jon relays the replies.** Each trade gets a PDF packet (its sheets, a question sheet,
           the plan room's link), and answers by email, a marked-up PDF or a call.
         - **Each trade is also asked how they'd usually do this building, and roughly what it
           would cost.** That's step 10's baseline: one contractor's word, low confidence, cited
           by trade and county with their OK.
       - **The parts:**
         - 8a, the sheets;
         - 8b, a question sheet for each trade, from the items flagged for this round;
         - 8c, the log and the packets. Each comment is an RFI (a BCF topic, as RFIs 001 and
           002), by trade and county only; nothing is published without the commenter's OK;
         - 8d, the round itself (Jon), then Addendum 7 with what's taken (Addendum 6 went out
           first, with 8a's two findings).
       - **8a done 2026-11-22: the services drawn as sheets** (`uv run brownfield sheets`;
         `src/brownfield/servicesheets.py`; writes `out/pass3/services/sheets/`).
         - **How:** 21 sheets, 36 x 24 in., drawn from the published files, as pass 3f drew the
           bid set's sheets from its IFC:
           - **G-001:** the index, the general notes (Addendum 5's items 4 and 5), what the model
             doesn't have, and the legend.
           - **Each trade's plan of each storey** at 1/4" = 1'-0" (P-, M-, E- and FP-101 to 103,
             and M-104 the roof, all trades):
             - the building's walls, doors, windows and rooms, cut 4 ft above the floor;
             - each run tagged with its system and size;
             - each riser on every storey it passes;
             - each register with its size and air.
           - **The four plumbing walls in elevation** at 3/8" = 1'-0" (P-201, P-202): every trade
             in them, over the frame's studs, plates and joists.
           - **The diagrams and schedules:**
             - P-601, the water service and the hot-water plant;
             - M-601, the building loop, and the flats' heat, cooling and air;
             - E-601, the one-line and the feeders; E-602, the 12 panel schedules;
             - FP-601, the fire service and the hydraulic summary.

             Their figures are 7c's designs on the routes, which the model doesn't carry. Each
             sheet says which it uses.
           - **A flat's own runs are drawn on its own storey's plan,** wherever in the joist
             spaces they go. A ceiling's sprinkler pipe runs in the joist space of the floor
             above, where that floor's drains run too, so drawing by height alone put each
             storey's sprinklers on the plan above it.
         - **Run (2026-11-22):** 21 sheets in 59 s.
           - Every element of the services model is on a sheet but its 1,570 fittings, which are
             counted in their schedule: 1,548 of 1,548.
           - The model was built from the routes the figures come from (requests
             365808aadcbf8ac1).
           - Every sheet's number reads as text in the PDF.
           - 1,089 tags placed, 154 left off where they would overlap another. Most of those are
             on the plumbing plans (P-102: 103 of 140); the plumbing walls' elevations carry all
             theirs (144 of 144).
           - Tests: `tests/test_walkup_sheets.py`, 10.
         - **Found:**
           - **Addendum 5 left out the fire service's shutoff valves.**
             - 7a found that Watts lists the LF007 as "UL Classified without shutoff valves
               only". So the fire service needs listed, supervised shutoff valves of its own,
               called "an Addendum 5 item".
             - Addendum 5 doesn't carry it. FP-601 shows the valves; it's an Addendum 6 item.
           - **The house load takes the swing tank's element at 1,747 VA,** Ecosizer's size. 7a
             found the tank takes 2.0 kW (Bradford White makes 1.5-6 kW).
             - At 2.0 kW, counted as step 5 counts it (noncontinuous), the house feeder is
               44.9 A on its 45 A breaker.
             - Counted continuous, it's 47.3 A, a 50 A breaker. The element runs about 5 h in
               the quiet hours, and NEC 215.2(A)(1) takes a continuous load at 125%.
           - **The annex's rooms hold only the tanks and the heat pump in the model** (known since
             7d). These are on the diagrams only:
             - the exchangers, the pumps and the mixing valve;
             - the backflow assemblies, the riser assembly and the pressure-reducing valve;
             - the meter stack and the house panel.
         - **What we don't know:**
           - Whether a trade reads these sheets as it would a consulting engineer's: the round
             will say.
           - Whether the plumbing plans need enlarged plans of the baths, kitchens and utility
             closets. The sizes left off them are in the elevations, the schedules and the
             model. A question for this round.
       - **Addendum 6 done 2026-11-22, before the round** (Jon: "yes fix both as addendum 6, then
         8b"). The two findings above, and the sheets issued.
         - **How:**
           - **Item 1, the fire service's control valves** (`fire.valves_psi`):
             - a listed indicating shutoff valve on each side of the 2 in. double check
               assembly, OS&Y gate valves as the basis of design, each with a tamper switch to
               the monitoring panel;
             - both the step 6 and the 7c hydraulics count them, from NFPA 13's chart as the
               USFA's plans-review manual reprints it: a 2 in. gate valve is 1 ft of Schedule 40
               steel pipe (2.067 in., C 120). A butterfly valve would be 6 ft.
           - **Item 2, the house panel** (`electrical.house_loads`):
             - the swing tank's element at its 2.0 kW nameplate (`house.swing_element_va`);
             - continuous when its design day's heat takes it 3 h or more at that
               (`house.continuous_h`, NEC Article 100).
           - **Item 3:** the sheets of 8a, revised to Addendum 6
             (`services-sheets-addendum-6.pdf`).
           - **It changes no model element,** so it has no model of its own. The manifest gives
             it none, the plan room links nothing to mark in 3D, and the viewer opens at the
             latest addendum with a model (Addendum 5). It's checked on the designs it changes and
             the sheets it issues (`systems.addendum_6_run`, in `brownfield systems --ifc`).
         - **Run (2026-11-22):** all checks pass.
           - 7a-7d: 71 checks pass. The services model came out byte for byte as published.
           - `brownfield systems --ifc --publish`: Addenda 1-5's published files are byte for
             byte as they were; Addendum 6 adds `addendum-6.md` and the sheets.
           - Tests: `tests/test_walkup_addendum6.py`, 4.
           - The plan room seen in headless Chrome: "Addenda (6)", the viewer at Addendum 5.
         - **Found:**
           - **The valves cost 0.06 psi at the governing design** (3-front-left's open area,
             56 gpm), which now needs 44.79 of the 45 psi (44.73 before).
             - The stair's six sprinklers: 0.30 psi, 36.4 psi in all.
             - Step 6's square figures: the stair from 40.4 to 40.7 psi, the top flats' living
               areas from 38.1 to 38.2.
             - Nothing has to grow with gate valves. A butterfly valve, the usual alternative, is
               6 ft on the same chart and would put the governing design at 45.1 psi, over the 45.
               So Item 1 says an equal may lose no more than a gate valve.
           - **The element runs 4.9 h on the design day at 2.0 kW, so it's continuous.**
             - The house comes to 10,291 VA calculated (9,538 before), 47.3 A, a 50 A position
               (45 before).
             - The service: 149,317 VA and 414 A (412 before), still on the 600 A main.
             - The PV the house panel can take under the 120% rule falls from 17.5 to 16.6 kW
               AC.
         - **What we don't know:**
           - Whether the sprinkler contractor would fit gate valves. A listed butterfly valve with a
             built-in supervisory switch is the usual choice, and this design can't take its loss
             on the placeholder street pressure: the hydrant test, or a larger pipe, decides it. A
             question for the round.
           - Whether the element's 4.9 h run at a stretch: the quiet hours' control decides it
             (step 9). Counted continuous until then.
         - **Found on the way, in the sheets:** P-601 carried figures typed in, not read from
           the design.
           - The temperatures, the storage's 16 h, the 60 psi setting, the loop's 66-175 W
             spread and the exchanger's 3 K now come from the params.
           - The RPZ's extra loss now comes from Watts' figure, a new param (`rpz_psi_40`):
             8.4 psi at the routed peak, where the sheet had step 4's 8.5.
           - The data center's "89%" of the hot water's heat was step 4's whole-day figure: the
             sheet now gives the preheat's share it computes (75%).
       - **8b done 2026-11-22: a question sheet for each trade** (`uv run brownfield questions`;
         `src/brownfield/questions.py`; writes `out/pass3/round/`).
         - **How:** for each trade, its questions, then five for every trade.
           - **The trade's own questions** come from the items flagged for this round in steps
             3-8. Each points at its sheet or schedule and says why we ask, with the design's own
             figure (the designs on the routes, the published schedules, the params):
             - **plumber, 9:** the PEX bent through its turns, the cast-iron stacks, the shared
               drain, the vent stacks, the bored holes, the plant, the street's pressure, the
               RPZ, the fixtures;
             - **HVAC contractor, 9:** the loops' balancing, the heat meters' cut-off, a hot-water
               preheater, the soffits, the fans' settings, the condensate, the line sets, the
               ERV into the return, the building loop;
             - **electrician, 7:** the GFCI on the inverter units, the feeders' bends, the
               plates, the meter stack's parallel sets, pricing without a device layout, the
               upsized circuits, the 50 A house panel;
             - **sprinkler contractor, 6:** the calculation on a placeholder street, the valves,
               the stair's six, the layout, the CPVC drops' firestopping, the fire service.
           - **For every trade:**
             - how they'd usually do it and roughly what it would cost (step 10's baseline);
             - what costs more than it buys;
             - what's missing to price it;
             - whether they used the model or the viewer (D27's open question);
             - whether we may publish their comments, by trade and county only.
           - **Each trade's sheet is a letter-size PDF form,** to print and write on, three
             pages each. The study's own references ("step 7c", "D27") are kept off the forms
             and in the Markdown we use.
         - **Run (2026-11-22):** 31 questions for the trades and 5 for every one.
           - Tests: `tests/test_walkup_questions.py`, 4. They check:
             - the figures are the designs';
             - every sheet a question names is in the set;
             - the forms read as text.
         - **Found:** nothing new in the design. Putting the questions into words showed which
           figures were only in step 4's prose (the RPZ's loss, the data center's share), fixed
           in the sheets above.
         - **What we don't know:** whether the questions are the ones a trade would want to
           answer. The round will say, and C3 asks what's missing.
       - **8c done 2026-11-22: the packets and the log** (`uv run brownfield round`, `--publish`;
         `src/brownfield/installers.py`). Jon took all four recommendations:
         - **The log is private, and only what a commenter agreed to is published.** It lives at
           `data/raw/round/comments.yaml`, gitignored, so it stays on Jon's machine.
         - **The letter is from "the brownfield-compute study", with no name in it.** Jon's own
           message introduces him.
         - **The questions are in the plan room now.** Comments go there as RFIs when their
           authors agree.
         - **No reply-by date.**
         - **How:**
           - **A packet for each trade** (`out/pass3/round/packets/`, for Jon to send):
             - a one-page letter: what this is (a design study, not a job, nothing to win), what
               we ask (an hour), how to reply, the plan room's link, and what we publish (only
               with a yes, by trade and county);
             - the trade's question form;
             - G-001 and the trade's sheets from Addendum 6's set. The HVAC contractor and the
               electrician also get the plumbing walls, which their line sets, loop risers and
               feeders run in.

             9-12 pages each. The letter says the sheets are 36 x 24 in., read on a screen or
             printed at 11 x 17.
           - **The log:** one entry a comment Jon relays, with:
             - trade, county, when it came and by what;
             - the questions or sheets it's about, and the services elements if any;
             - their words, and their yes or no to publishing (question C5);
             - open, taken (with its addendum) or answered (with the answer and its date).

             `check_log` names what an entry lacks: a trade outside the round, a question or
             sheet that doesn't exist, no yes or no, an answer or date missing.
           - **Publishing** (`--publish`, only from a sound log) writes the plan room's "06
             Installers' round" folder:
             - the four question forms;
             - the public log, with the counts and each comment its author let us show;
             - each such comment as a BCF 3.0 topic in "03 RFIs": its author a role
               (`plumber@example.com`), a viewpoint on any services elements it names, our answer
               as a comment, closed once taken or answered.

             A comment without a yes is counted, never written there. One taken back is removed
             on the next publish. `brownfield systems --publish` keeps the round's entry in the
             manifest.
         - **Run (2026-11-22):** four packets (plumber 11 pages, HVAC contractor 12,
           electrician 12, sprinkler contractor 9). The log is empty; the round is published to
           the plan room: the four forms and an empty log.
           - Tests: `tests/test_walkup_installers.py`, 14, on synthetic entries in temporary
             folders only. They check:
             - every problem an entry can have is named;
             - a comment without a yes never reaches the published files;
             - a comment taken back leaves;
             - the BCF repeats byte for byte;
             - each packet's pages are its letter, form and sheets.
         - **What we don't know:** whether trades will answer an unpaid request about a made-up
           building. Jon's own contacts, and the hour we ask for, are what we have.
       - **8d, the round itself (Jon):** send the packets; relay each reply (an entry in the log);
         then each comment taken (Addendum 7) or answered, and published if its author agreed.
    9. **The inspection and commissioning plan.**
       - **Jon's decisions (2026-11-22), all four recommendations:**
         - **The depth:** the code's tests, the design's own claims verified, and the plant's
           control sequence, issued as Addendum 7, not full third-party commissioning (ASHRAE
           Guideline 0, rare on a 12-flat walk-up).
         - **The fallback is designed here:** what heats the flats and the water when the data
           center's heat stops. It's the first question anyone asks of waste heat, and the design
           didn't answer it.
         - **Step 10's costs from free sources** (Jon: "free sources then"), with honest ranges:
           - the difference priced item by item;
           - equipment from list prices;
           - labour from the county's prevailing wages and stated hours, or NREL's installed costs;
           - the usual walk-up's totals from public surveys.

           RSMeans is paid, and its licence bars republishing its data in a public repo. Test
           whether the report's conclusion survives the range; only if it doesn't, cross-check
           privately.
         - **Addendum 7 is step 9's;** the round's outcomes go in the addendum after it.
       - **The parts:**
         - 9a, the fallback: the flats on their mini-splits, the hot water on a backup heater,
           and what that does to the wiring;
         - 9b, the control sequence, the fallback included;
         - 9c, the tests and inspections: what, who, when, the pass criteria and the code behind
           each;
         - 9d, Addendum 7, published.
       - **Found while scoping (2026-11-22):** step 5 counted each flat's mini-split only as air
         conditioning, taking the larger of it and the ERV's preheater ("never runs with the
         cooling"). But it's a heat pump: a tenant can set it to heat, and the fallback needs it
         to, with the preheater running too. 9a counts the two together.
       - **9a done 2026-11-22: when the data center's heat is gone** (`uv run brownfield fallback`;
         `src/brownfield/fallback.py`).
         - **How:**
           - **The flats on their mini-splits:**
             - Fujitsu's own heating table for the 12k unit, at 70 F indoor
               (`data/fujitsu_aruh12_heating.csv`): 4.54 kW at -15 C and 4.09 at -20.6 C, so
               4.44 at the design -16.3 C, drawing 2.24 kW. Its 70 F column is a little under
               the design's 20 C indoor, so it errs low.
             - Corrected for each flat's routed line set and the outdoor unit's height above
               the indoor one, from Fujitsu's heating pipe-length table
               (`data/fujitsu_aouh12_heating_pipe_factors.csv`).
             - The mini-split serves the same rooms the radiant floors heat.
           - **The hot water on a backup heater:** an A. O. Smith DRE-52-12, the line's smallest
             (12.3 kW, three 4,100 W elements, 59 A at 208 V single phase, its own 50 gal tank;
             spec sheet AOSCE15300, 2021).
             - It goes on the plant's heater circuit after HP-1, so it heats the 237 gal of
               storage as the data center's heat does now, and the plant works as Ecosizer sized
               it. Placed after the storage instead, it would have only its own 50 gal, and the
               peak hours would fail.
             - Its elements are locked out unless the data center's heat is gone: no
               electricity in normal running (9b's sequence).
           - **The wiring:**
             - **Each flat's heating is its heat pump at its nameplate plus the preheater**, 65%
               under 220.82 and 100% under 220.84 (`electrical.hvac_va`). It's larger than the
               cooling, so it governs.
             - **The backup heater is on the house panel, continuous.** It's interlocked
               against HP-1, so of the two only the larger counts (220.60).
         - **Run (2026-11-22):** 8 checks pass.
           - **Two known cases:**
             - the recovery against A. O. Smith's own table: 50.4 gal/h at a 100 F rise
               (theirs 50);
             - Fujitsu's tables read back at their own rows.
           - **The flats:** every one is heated by its mini-split alone at -16.3 C. The tightest
             is 1-back-left: 4,080 W against 1,986 W, the derate 0.920 for 51 ft of line with
             the outdoor unit 7.6 m above. The top floor's units give 4,366-4,375 W against
             1,687.
           - **The hot water:** 12.3 kW against the plant's 11.02 kW; 54 gal/h through the
             coldest inlet's 94 F rise.
           - **The house panel:** 19,888 VA calculated, 93.4 A: a 100 A position (50 A after
             Addendum 6).
           - **Each flat's feeder:** 91.0 A on its 100 A breaker (87.8 before), the worst drop
             1.98% against 2%.
           - **The service:** 163,833 VA, 455 A (414 before), still on the 600 A main and its
             two sets of 250 kcmil.
           - **Rerouted:** on the square lengths the requests ask, 1-front-right's feeder now
             needs 2 AWG, so its conduit was requested at 1-1/4 in. (1 in. before). Forge routed
             all 430 runs again with no clashes (459 s), and 7a-7d pass (71).
             - In the services model only that conduit and its five fittings change. The routed
               design still sizes it 1 in. (its Size), on room for 1-1/4.
             - So the published services model and Addendum 6's sheets are now a reroute behind
               the routes. The sheets' check says so, and Addendum 7 issues both again (9d).
           - Tests: `tests/test_walkup_fallback.py`, 5.
         - **Found:**
           - **Step 5's heating slip** (above): each flat's feeder 3.2 A more, the service 41 A
             more. Step 2's load estimate had the same slip in its 220.84 figure, now counted the
             same way.
           - **The PV the house panel can take falls from 16.6 to 8.3 kW AC.** Its 100 A main
             uses up most of the 120% rule's room on its 125 A bus. A bigger bus would give it
             back, or the PV goes in on the supply side with FirstEnergy (the rest already must).
           - **The flats' baths, kitchens and halls have no supply of their own** in the
             fallback, as in cooling. They take the hall's moving air, so they run cooler than
             the radiant floors keep them.
         - **What we don't know:**
           - Defrost: Fujitsu's tables are "based on the maximum capacity" and don't say whether
             they count defrost. The tightest flat has twice its need to give.
           - How long the data center's heat can be gone. The backup carries the design day for
             as long as it lasts, at the electricity's cost: step 10 prices it.
       - **9b done 2026-11-22: the control sequence** (`uv run brownfield sequence`;
         `src/brownfield/sequence.py`; writes `out/pass3/sequence.md`, specification section
         23 09 93, for Addendum 7).
         - **How:** each system in its modes, every setpoint the design's own. The few the
           sequence sets itself are judgements, set at commissioning (`controls`): the fallback's
           timers, the warm-weather shutdown, the mini-splits' offset and the loop's alarm.
           - **The hot-water plant:**
             - **Normal:** the heater circuit's pump P-2 runs on ST-1's aquastat (140 F, at half
               the tank's height: Ecosizer's). V-1 throttles the data center's water so it
               leaves HX-1 at 80 F, the heat pump's source. HP-1 lifts the circuit to 140 F. The
               swing tank's element switches on at 125 F and off at 133 F (Ecosizer's, not a
               clock: "quiet hours" earlier was loose wording). The mixing valve sends 125 F; the
               return comes back at 122 F or more.
             - **Fallback:** entered when the data center's water at the annex falls below 80 F,
               or stops, for 10 min. HP-1 is locked out first, then BK-1 released, and its own
               thermostats hold 140 F. It's left after 30 min of the water back: BK-1 locked out
               first, then HP-1.
             - **Alarms:** the fallback, the storage below 125 F, the return below 122 F, a fault.
           - **The building loop:** the outdoor reset, a straight line from the room's 20 C to
             the design's 40.2 C at -16.3 C, as REHAU describes weather compensation. A starting
             curve: 31.1 C at 0 C outdoors. It shuts off above 15.5 C. In the fallback V-2 closes
             and P-1 stops: cold or still water would only cool the floors.
           - **Each flat's mini-split** heats at 18 C, 2 K under the floor's 20 C, so it runs only
             when the floor can't hold the room. Fujitsu's units take no outside mode signal (only
             operation/stop and a forced stop, the latter already the condensate switch's). So the
             takeover is each flat's setpoint, not a wire from the plant, and the manager confirms
             it at the season's change and on the plant's alarm.
           - **The ERV** runs continuously; its preheater holds 2.5 C only with its airflow
             proved. The mini-split's fan runs on low with the ERV. Fire protection's signals
             are as step 6 designed them.
           - **Three interlocks are wired, not programmed:**
             - BK-1 never with HP-1: its contactor coil goes through a normally closed contact
               of HP-1's enable. The house panel's 100 A rests on this.
             - The preheater on its own airflow sensor.
             - The water-level switch on each mini-split's forced stop.
         - **Run (2026-11-22):** 9 checks pass.
           - The reset gives the design's supply at the design dry bulb and the room's at the
             room's temperature, never falling as it gets colder, and still heating (22.5 C) at
             the shutdown.
           - Every setpoint is within its equipment's range: the heat pump's source, BK-1's
             thermostats, the swing tank under the storage, the preheater at least Broan's 0 C.
           - Leaving the fallback is slower than entering it.
           - The house panel counts BK-1 and HP-1 as the interlock runs them.
           - 30 steps in 5 systems, 16 control points. Tests: `tests/test_walkup_sequence.py`, 4.
         - **Found:**
           - **Eight of the sixteen control points have never been chosen.** They're the plant
             controller, the heater circuit's pump, the two data-center valves, the flow switch,
             and three temperature sensors. Like the exchangers and the mixing valve, they're
             part of the plant's wall-hung equipment that 7a placed no box for. The design sized
             the heater circuit's flow, not its pump. A question already for the plumber (P6),
             and a gap step 10's pricing has to carry.
           - **A building-wide switch to the mini-splits isn't possible with these units.** The
             takeover rests on each flat's setting, so a tenant who has switched theirs off
             gets a cold flat until it's switched on. The plant's alarm tells the manager.
         - **What we don't know:** the reset's slope against the building as built. The floors'
           own heat and the flats' gains bend it; the balancing tunes it (9c).
       - **9c, first: the energy code's hot-water rules the design broke, fixed for Addendum 7
         (2026-11-22).** The test schedule starts from the code's own tests, so 9c read the energy
         code's hot-water sections. The residential chapter's R403.8 sends a plant serving several
         flats to the commercial chapter: "Systems serving multiple dwelling units shall comply with
         Sections C403 and C404 ... instead of Section R403." Step 4 had read only R403. Three of
         C404's rules failed:
         - **C404.5, the water between circulating water and a fixture:** at most half a gallon
           (64 fl oz, C404.5.2), counting a circulating loop as a source. The risers were the
           nearest circulating water, and 52 of the 60 hot fixtures were over. The worst was
           154 fl oz: 39.5 ft of 1 in. pipe to a tub.
         - **C404.4, the flats' hot pipe insulated by Table C403.12.3:** 1 in. at 105-140 F under
           1-1/2 in., not R403.5.2's R-3 (0.75 in.). Step 7 had kept R-3 so a 1 in. branch's hole
           stayed under 60% of a 2x6 stud. But C404.4 lets the insulation stop where the pipe
           passes a framing member, so the hole only has to fit the bare pipe.
         - **C404.6.1, the recirculation pump turned off when the loop is at temperature:** 9b ran
           it continuously.
         - **The building loop isn't caught:** C403.12.3 exempts piping between 60 and 105 F, and
           piping heated neither by fuel nor electricity.
         - **Jon chose** recirculating into each flat, and fixing it before the test schedule
           ("Recirculate into each flat", "Fix first, then 9c"). The alternatives, checked first:
           - **A manifold per flat with a 1/2 in. home run to each fixture:** the tub's 4 gpm
             makes 6.95 ft/s in 1/2 in., over the design's 5 ft/s for hot water. In 3/4 in. its
             39.5 ft holds 93 fl oz.
           - **Heat trace on each flat's branch:** no return pipe, so less loss, but twelve
             electric circuits in the flats' walls. Recirculation is the plain plumbing an
             installer and an inspector expect.
         - **The fix:**
           - **Each flat's own loop.** Its hot branch goes on to the joists' space over its
             farthest hot fixture. There a 1/2 in. return leaves it, a tee, for the return riser,
             through a thermostatic balancing valve: Caleffi's ThermoSetter 116, 1/2 in., basis
             of design. It's set at 124 F, between the 122 F return and the 125 F supply.
             Caleffi's design Cv of 0.52 goes into the pump's head.
           - **The flats' hot pipe insulated 1 in.,** stopped at each plate and joist it passes.
           - **P-3 runs while the return at the swing tank is under 122 F and stops at 124 F.**
           - **P-3's head is checked now,** round the longest circuit: the mains at the whole
             loop's flow, the flat's valve and the mixing valve. It's held against the sheet's
             rated point of 10.7 gpm at 8.2 ft; the curve gives more head at less flow.
         - **The router, for the thicker pipe and the tee** (forge's known cases, now 11, pass):
           - **Each request can give the bare pipe's diameter for its holes** (`bore_m`).
           - **Each flat's hot branch is on a 3/4 in. grid.** At 1 in. the 3-1/8 in. insulated
             pipe rounds up to 5 in., which the plumbing wall's bays don't hold as the router
             opens them. In those bays it gets the studs' whole depth: only its bare pipe passes
             the plates, and any stud it bores is still held to 5/8 in. Its joists' space is kept
             to 7 ft from the wall, so the finer grid is no larger than the old one.
           - **The return starts in the hot pipe itself.** Forge opens the hot pipe to it only
             within 6 in. of the loop's end (`attach_near`): a fixed point past the far fixture
             was boxed in by the right-hand flats' tub vents. Forge's passes never move a return
             ahead of its hot branch (`after`): pass 3 had routed one first, over its own tub's
             drop.
           - **The top floor's return riser goes up into its joists' space,** so the top flats'
             returns join it there, as on the floors below. That alone didn't route the top
             right-hand flats' returns; the tee did.
           - **Results:** routed 442 of 442 on the third pass, with no clash. The return main grew
             to 1-1/4 in. and was routed again. Every check of 7a-7c passes.
         - **Run (2026-11-22), routed:**
           - every hot fixture is within half a gallon: the worst is 56 of 64 fl oz, 2-front-left's
             washer. IPC 607.2's longest hot pipe from circulating water is 14.2 ft (30.5 from the
             risers);
           - the loop loses 2,230 W, against 793 before: 1,353 W of it in the flats' loops, 186 W
             a flat. That's over Ecosizer's 75th percentile of 175 W. The risers and mains alone
             are 73 W a flat, within its spread, and the check now compares that part;
           - the loop's flow rises from 1.80 to 5.06 gpm, 0.42 a flat. The returns are 1-1/4 in.
             mains, 3/4 in. risers and 1/2 in. in each flat. P-3 needs 3.7 ft, and each valve
             takes 0.66 psi, within Caleffi's 15;
           - the swing tank's element goes from 2.0 to 4.5 kW. Ecosizer asks 4.03 kW on the square
             lengths and 3.90 on the routes, and Bradford White makes 4.0, then 4.5, at 208 V.
             The plant: Ecosizer's primary rises from 11.02 to 11.62 kW and its storage from 237
             to 259 gal. The 12.3 kW backup heater still covers it;
           - the house panel goes from 100 to 110 A (108.4 A). The PV it can take falls from
             8.3 to 6.7 kW AC. The service is 463 A, on its 600 A main.
           - Tests: `tests/test_walkup_c404.py`, 6. `tests/test_walkup_addendum6.py`'s element
             test now reads the element from the params.
         - **Found, not fixed:**
           - **The energy.** The loops add 1,437 W of loss, about 12.6 MWh a year at the design's
             temperatures. Much of it comes from the swing tank's resistance element: Ecosizer has
             the plant carrying 40% of the loop's heat. That's the code's price on this layout,
             with its fixtures spread 17 ft along the wall. Step 10 prices it.
           - **The building loop's pump.** 7c's routed head is 13.4 ft (13.1 then). Nothing
             checks it against the ALPHA2 15-55F, whose CP2 setting holds about 8.9 ft at 6 gpm,
             as step 3 read the curve. (Checked in 9c's second part, below.)
           - **The balancing valves aren't placed.** Each needs its access panel. The routes join
             each return to its riser wherever there's room: in the wall, or in the joists' space
             over a rated ceiling, where an access door would have to be listed. (Placed in 9c's
             second part, below.)
         - **What we don't know:**
           - the balancing valves' real flows: Caleffi's design curve stands for all of them;
           - whether the 1 in. insulation is kept continuous in the walls as built;
           - how the loss model fits in-flat loops. Ecosizer's buildings don't say how their
             loops run.
       - **9c, second: the two open items (2026-11-22).** Jon: "please continue with the rest of 9c
         and fold in the two open items".
         - **The building loop's pump, checked against its curve.**
           - **The curve:** Grundfos's US leaflet for the ALPHA2 15-55 (literature 6511597) has it
             only as a drawing. It was read off curve III, the highest fixed speed: rendered, then
             calibrated by the plot's frame and ticks, and traced pixel by pixel
             (`data/grundfos_alpha2_15_55_curve3.csv`). Two checks: the leaflet's own "max. 19
             ft" (the read curve gives 18.9 at 0.5 gpm), and the 15-55SF sheet's rated 10.7 gpm at
             8.202 ft (the curve reads 8.39 there, 2.3% over).
           - **Found:** at the loop's 6.04 gpm the curve gives 12.3 ft, under 7c's 13.4. But 13.4
             took each column's risers at 1/2 in., the velocity limit's size for a column's flow,
             while 7a had placed them at the square design's 3/4 in. Taken at the 3/4 in. in the
             model, the worst path needs 10.8 ft. With the 10% kept in hand (`pump_margin`, a
             judgement) that's 11.9, under the curve's 12.3.
           - **The rule now:** the risers grow until the pump's highest speed covers the worst
             path with that margin. A size the model doesn't have would be asked of the router
             (`loop_riser_in`); none was. Steps 3 and 7c both check it.
         - **The balancing valves, placed.** IECC C404.6: "Automatic controls, temperature sensors
           and pumps shall be in a location with access."
           - **Not at the riser:** the risers are packed side by side and fill the 2x6 wall's
             depth floor to ceiling, so nothing can come down beside one to a valve.
           - **Not in the joists' space:** an access door would cut the rated ceilings of floors
             1 and 2, and would have to be fire-rated.
           - **Under the lavatory:** where plumbers usually take a recirculation return. Each
             flat's loop now runs through its hot branch to its lavatory's stub. The valve sits in
             the vanity between that stub and its return's, 5 in. away in the right-hand flats and
             15 in. in the left, reached through the vanity's doors with no access panel. The
             return rises in the wall beside the lavatory to the joists' space and goes back to its
             riser.
           - **Each fixture's own pipe now takes its own size,** as Appendix E sizes a pipe for the
             fixtures it serves. That's Hunter's demand at the fixture's Table E103.3(2) units,
             within 5 ft/s: the tub, sink, dishwasher and washer 3/4 in., the lavatory 1/2 in.
             Pieces serving more than one fixture keep the flat's 1 in. Ending at the lavatory,
             the tub became a longer dead leg: 87 fl oz at 1 in. in the worst flat, 53 at its own
             3/4 in.
           - **The pressure path still runs the flat's whole demand through 1 in. to the top
             shower:** 4.4 psi per 100 ft at its 9.26 gpm, against 2.0 for the tub's own 3 gpm in
             3/4 in., so it's on the safe side. The cold water keeps step 4's 1 in. throughout.
           - **In the services model:** each valve is a box in the vanity (`IfcValve`, REGULATING).
             Its size is Caleffi's 12-11/16 in. with its ball valves by 4-1/2 in.; its access is
             recorded on it.
           - **The router:** the return starts from its own stub, so the tee inside the hot pipe
             (`attach_near`) is no longer used. Forge keeps it, with its known case.
           - **Results:** routed 442 of 442 on the third pass, with no clash; every check of 7a-7c
             passes, with nothing to route again.
         - **Run (2026-11-22), routed:**
           - every hot fixture within half a gallon: the worst 53 of 64 fl oz, 1-back-left's tub.
             IPC 607.2's longest pipe from circulating water is 22.4 ft;
           - the loop loses 2,120 W, 1,242 of it in the flats' loops: 177 W a flat. The risers
             and mains alone are 73 W a flat. The flow is 4.81 gpm, 0.40 a flat; P-3 needs 3.4 ft;
           - the building loop's pump needs 10.8 ft at 6.04 gpm, against its curve's 12.3;
           - the swing tank's 4.5 kW element, the house panel's 110 A and the service's 463 A
             still hold. The loops' extra loss over the design before 9c is now 1,327 W, about 11.6
             MWh a year.
       - **9c, third: the tests and inspections (2026-11-22)** (`uv run brownfield acceptance`;
         `src/brownfield/acceptance.py`; writes `out/pass3/acceptance.md`, specification section 01
         45 00, for Addendum 7).
         - **How:** 28 items in 9 areas. Each says what is tested, who does it, when, what passes
           and on what it rests:
           - **the codes' own tests,** quoted from the copies saved under `data/raw/`. A check finds
             all 32 quotations word for word, and a made-up one is caught:
             - IPC 312's water, drain and backflow tests;
             - IMC 1110's line-set tests, 1208.1's hydrostatic test, and 1209.2's test before the
               topping;
             - the energy code's blower door (R402.4.1.2-.3), ventilation test (R403.6.3) and hot
               water rules (C404.4-.6);
             - NFPA 13R's acceptance tests (its 2022 edition's second draft, chapter 10);
             - Pennsylvania's inspections, 34 Pa. Code 403.45. A 12-flat R-2 building comes under
               its commercial section, not 403.64's for houses;
           - **the design's own claims, with their figures from the design runs:**
             - each flat's return at or over 122 F, and P-3's control;
             - the plant's setpoints, interlock and fallback;
             - the building loop's flows and pump, and the outdoor reset;
             - each mini-split's static pressure and water-level switch.
         - **Choices in it:**
           - **The blower door holds each flat to the 3.0 ACH50 the heat loads assume.** The
             code's 0.30 cfm/ft2 for attached flats would pass a leakier one.
           - **The ERVs are held to the design's 45 cfm each way,** within 10% of each other. The
             code's floor is 30.8 cfm, and the kitchen and bath exhaust 25 and 20.
           - **No duct leakage test:** R403.3.5 exempts ducts and units wholly inside the thermal
             envelope, and every flat's are.
         - **Tests:** `tests/test_walkup_acceptance.py`, 3; `tests/test_walkup_c404.py`, now 8.
         - **What we don't know:**
           - NFPA 13's own hydrostatic test: its 200 psi is from the USFA manual, and its duration
             isn't in anything saved;
           - 13R's published 2022 text, which the second draft may differ from;
           - the building loop's design pressure, for IMC 1208.1's 1.5 times: the expansion tank
             and relief valve aren't chosen. The 100 psi floor stands until they are.
       - **9d done 2026-11-23: Addendum 7, published** (Jon: "lets do 9d"; `uv run brownfield systems
         --ifc --publish`; `systems.addendum_7_run`).
         - **What it issues (seven items):**
           - 9c's hot water: each flat's loop, the balancing valves, the insulation, P-3's control;
           - the plant, revised (below);
           - 9a's fallback: BK-1, the mini-splits heating alone, the wiring;
           - P-1 against its curve;
           - the sequence and the tests as specification sections 23 09 93 and 01 45 00
             (`spec-23-09-93-sequence.md`, `spec-01-45-00-tests.md`);
           - the services model and the sheets, reissued: `services-addendum-7.ifc` with its
             schedules, and `services-sheets-addendum-7.pdf`, 23 sheets. Two are new: G-002, the
             tests as a schedule, and M-602, the sequence and its 17 points. P-601 now draws the two
             tanks, BK-1 on the heater circuit, P-3's control, and an inset of one flat's loop with
             every flat's loop as routed. M-601 gives P-1 against its curve.
         - **Found while drawing the plant: the storage tank no longer held the storage.**
           - 9c's loops raised Ecosizer's storage to 255 gal on the routes and 259 on the square
             lengths. 7a had placed Lochinvar's HP250G, 250 gal, for step 4's 238.6, and nothing
             checked the tank against the plant. Now both `plumbing.summary` and 7c do.
           - **Two HP150G in series, 300 gal** (basis of design). Ecotope's design guidance:
             "multiple storage tanks plumbed in series ... enables a high degree of temperature
             stratification" (Heller and Oram, 2015, saved under `data/raw/pass3g/step9/ecotope/`).
             Ecosizer sizes the storage as one volume; its aquastat, at half the storage, goes where
             ST-1B's top joins ST-1A's bottom.
           - **Lochinvar's next single tank won't go in.** The HP500G is 49 in. across, wider than
             the mechanical room's 42 in. door. Stood up, its diagonal is 109 in., under a 108 in.
             ceiling.
         - **BK-1 placed.** 9a chose it, but the model had no box for it. The room's floor now holds:
           - the two tanks along the far wall;
           - the heat pump by the door;
           - the swing tank and BK-1 on the back wall, BK-1 with NEC 110.26(A)'s 36 in. of
             working space in front.

           Its footprint is taken at 27 in. each way. A. O. Smith's table gives 21-3/4 and 27 in., and
           its text doesn't say which is the diameter. The plant's drop through the slab moved from
           24 to 12 in. off the wall, out of that space.

           Three checks now: each piece inside the room with its service space clear, each through
           the door and stood up under the ceiling, and both drops clear. Forge routed all 442
           runs again with no clash (505 s), and 7a-7d pass (77).
         - **Publishing leaves every issued addendum as it was.**
           - Addendum 5's text had been read from the latest services run, so a publish would have
             rewritten it. It now reads Addendum 5's issued model and schedules, and comes out byte
             for byte.
           - Addendum 6 stays as issued. Its sheets were drawn from the services Addendum 7 reissues,
             so its run (`addendum_6_run`, git d6d99c7) is retired, and its items come from the
             manifest.
           - The services model is named for its issuing addendum (`servicesifc.ISSUE`). Its
             GlobalIds stay keyed on the frame it's routed through, so the two issues compare
             element by element.
           - `brownfield routes --publish` no longer publishes the services alone; they go out with
             their addendum.
         - **What changed, marked in 3D:** `changes-services-addendum-7.json`, by GlobalId: 59 added,
           532 changed, 15 removed, of 3,162 (3,118 before).
           - **Added:** each flat's return and its balancing valve, the two tanks and BK-1.
           - **Changed:** mostly cold pipe, the loop's tails, vents and branch circuits routed again
             around the returns. No sprinkler, duct or line set moved.
           - **In the viewer:** with a services layer on, "Mark what Addendum 7 changed in the
             services" colours them as an addendum's changes. The plan room's Addendum 7 links
             straight to it.
         - **Run (2026-11-23):** every check passes (`systems --ifc`, 223 lines). Addendum 7's own 31
           include 7c's 20, the plant's three, the fallback's, the sequence's and the tests', the
           diff read from both files, and the sheets'. Addenda 2-5 came out byte for byte; Addendum
           7's issue time is 2026-11-23 08:35:59 (UTC-8).
           - **On the routes:**
             - the worst fixture holds 53 of 64 fl oz, and IPC 607.2's longest pipe is 22.4 ft;
             - the loop loses 2,112 W, 1,242 of it in the flats' loops;
             - P-3 moves 4.79 gpm at 3.3 ft, and P-1 needs 10.7 ft at 6.04 gpm against its curve's
               12.3;
           - **The plant:** 11.63 kW, BK-1's 12.3 covering it; the swing tank's element 4.5 kW
             against 3.70.
           - **The wiring:** the house panel 108.4 A on 110 A; the service 463 A on its 600 A main;
             6.7 kW AC of PV on the house panel.
           - **The viewer**, seen in headless Chrome: the Level 1 plumbing, with the added runs in
             green.
           - Tests: `tests/test_walkup_addendum7.py`, 6. `test_website.py` and `test_walkup_sheets.py`
             updated.
         - **What we don't know:**
           - **The room's wall-hung equipment.** The exchangers, the pumps, the mixing valve, the
             backflow assemblies, the riser assembly and the expansion tanks hang on what wall is
             left. With five pieces on its floor, the room may now be short of wall, and no one has
             laid it out. A question for the plumber.
           - **BK-1's diameter,** taken at the larger figure until its drawing is read.
           - **Whether two tanks in series stratify as Ecosizer's one volume does.** Ecotope's
             guidance says they do; it's not measured here.
           - **The installers' round.** Its packets carried Addendum 6's sheets, and its forms carry
             figures 9a and 9c changed (the house panel's 50 A among them). The packets now take
             Addendum 7's sheets (`installers.SHEETS_PDF`). Whether to rebuild and republish the
             forms is Jon's: it depends on whether they've gone out.
    10. **The baseline and the report:** the usual walk-up priced from sources; the engineering
        fee, energy, noise and comfort against it; who gets the savings. `docs/pass3/systems.md`.
  - **Out of scope:** sealed construction documents (the line D27 drew); DIN standards; changing
    the envelope.
  - **What we expect not to know:** what US engineers charge for this on a 12-flat building
    (the fee needs a source); installers' real comments until Jon's round; plumbing noise in
    the walk-up's own walls, which only a test in a built one would show.

- **D29** (2026-11-21) The plan room grows with the design, as a builders exchange's project page
  does.
  - **Jon:** "as we build this we should be making the plan room site page look more and more like
    a legit builders exchange. a dropdown tab for "addenda {number of addendas/latest date/time of
    latest addendum}" bid docs organized by hierarchy of folders. advancing the 3d viewer."
  - **The steer:** take an exchange's conventions, which are generic: a project page, a document
    tree, addenda with their issue dates, a viewer. Keep D27's lines:
    - no real exchange's name, logo or look;
    - the notice that the building is made up;
    - no plan holders, owner or bid date presented as real.
  - **The addenda's dates** are the days we issued them (Addendum 1 2026-11-19, Addendum 2 when
    published), recorded with each addendum, not made up.
  - **To build:**
    - an "Addenda (N, latest <date time>)" dropdown, each addendum with its items, files and
      what changed;
    - the bid documents in folders (drawings, model, schedules, specifications, addenda, RFIs);
    - Addendum 2 published into it;
    - the viewer: click an element for its properties, one storey at a time, rooms on and off,
      and an addendum's changes highlighted.
  - **Layers** (Jon: "it would be nice if the viewer had a toggle to show the framing too", then
    "framing, plumbing, conduit, ducts, etc. cf has routing"): a toggle a system.
    - **Framing first:** forge `framing`'s 3,027 members, built for the latest revision's
      building, as their own IFC (studs and plates as members, joists and headers as beams).
    - **Plumbing, ducts and conduit** join as D28 sizes them (steps 3-6) and routes them
      (step 7). Routing before sizing would draw pipes that mean nothing.
    - **What CortenForge 0.9 has for routing** (read from the published crates, 2026-11-21):
      - `Solid::pipe` and `pipe_spline`, a pipe solid along a path;
      - cf-design's tendon routing, a route of waypoints through named parts that carves its
        channel through each, which is drilling the joists and plates;
      - cf-spatial's voxel grid with overlap and ray queries, for clashes.
    - **What it lacks:** a path search. cf-spatial's docs name "A* and other algorithms on
      voxelized space" as a use case but ship none. We write the search on its grid and log the
      gap (CORTENFORGE.md).
  - **Built 2026-11-21** (not yet pushed, so the live site is as before):
    - **Publishing** (`uv run brownfield systems --ifc --publish`, only if every check passes).
      Into `docs/pass3/bidset/`:
      - Addenda 2 and 3: their IFCs, drawings and reports, and RFI 002;
      - `changes-addendum-{1,2,3}.json`, what each changed by GlobalId, with the rooms added or
        resized by name;
      - the framing model;
      - `addenda.json`, each addendum's number, title, issue time, items, files, model and
        changes.

      The issue times:
      - Addendum 1, 2026-11-19 23:29 (UTC-8), when first published (git 8a9d200);
      - Addendum 2, 2026-11-21 08:43, when produced and checked (2f6623f);
      - Addendum 3, 2026-11-21 09:15, when published. RFI 002 was asked at 08:45, when the
        walls' shortfall was confirmed.

      Nothing already published changed.
    - **The framing model** (`src/brownfield/framingifc.py`; forge `framing-json addendum-3 60
      1`):
      - pass 3b's frame built on Addendum 3's building, 3,418 members with no overlaps (the
        base's has 3,432);
      - IFC4, 4.4 MB: studs and plates as IfcMember, joists and headers as IfcBeam, footings
        and stem walls as IfcFooting;
      - checked: every member once, each where forge has it to 1 mm, schema valid.

      Not in it yet: the flats' partitions and plumbing walls, and the annex.
    - **The plan room** (`tools/viewer/planroom.html`, `build_site.py`, read from the
      manifest):
      - a project header with the "made up" tag, where and what, the bid documents' issue date,
        and section links;
      - an "Addenda (3), latest Nov 21, 2026, 9:15 AM (UTC-8)" dropdown, newest first, each
        with its items, files and a link to its changes in 3D;
      - the documents in folders: 01 Bid documents (Drawings, Model, Schedules, Requirements),
        02 Addenda (one folder each), 03 RFIs, 04 Framing model. Each file has its type,
        issue date and size, and keeps its published path, so old links still work;
      - counts as of the latest addendum.

      The site is 64 files, 22.3 MB.
    - **The viewer** (`tools/viewer/index.html`):
      - **models:** the bid set and Addenda 1-3 from the manifest, opening at the latest;
        `#addendum-N` and `#addendum-N-changes` links; `#addendum` still opens Addendum 1;
      - **rooms:** web-ifc's default stream leaves spaces out (checked in Node: 0 of 122), so
        they're streamed by type. They're coloured by use, placed on their storey through
        their aggregate, and a click shows use, flat, floor area (its quantity set read),
        openings and escape window;
      - **framing:** an overlay layer, with a member's kind and size on click;
      - **changes:** an addendum's marked, added green and changed amber, with what was
        removed listed;
      - **coming:** plumbing, ducts and conduit shown, greyed, until designed;
      - **URL options:** `?rooms`, `?frame`, `?xray`, `?storey=N`, `?view=back`.
    - **Seen working in headless Chrome** (swiftshader) on the built site: Addendum 3 loaded
      (392 elements); rooms on the second floor; the framing layer; Addendum 2's changes (the
      annex green, 92 added, 114 changed, the stair window removed); the plan room page.
      - Found and fixed there: `#addendum-2-changes` opened Addendum 3, since the link pattern
        didn't allow the suffix; and added rooms weren't named in the changes, so they couldn't
        show green.
    - **Tests:**
      - `test_website.py` holds the page to the manifest: the addenda's count, latest date,
        items and files, the folders and the in-page links;
      - the counts are now Addendum 3's;
      - the frame's published model is forge's (`test_walkup_systems.py`).

      The suite: 306 pass.
    - **CORTENFORGE.md:** cf-spatial's missing path search, logged with a suggestion.
    - **Review before commit fixed:**
      - Addendum 3's wall type named its insulation's thickness from params, not the model;
        it reads the model now (the published IFC is unchanged, byte for byte);
      - the plan sheet, now drawn from Addendum 3, still said "in Addendum 2";
      - `--publish` without `--ifc` did nothing and said nothing; it says so now;
      - the isotropic-sky functions in `climate.py`, which nothing used, are gone, and a test
        now reproduces the finding they served (peaks more than 5% low on the south and west
        walls).

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
