# The site plan: modules, routes and rings (D12)

Jon, after the neighbourhood drawings: "get everything modular so we can move things around for
optimal transportation, security, etc." The optimizer suggests and Jon edits. On security: "like
pentagon style. no fence, the community will be the fence/wall". Then, on the weights and the pick
(2026-11-17): "i will let you decide what matters most given the research backing it. same with
layout." D12 and D14 in [PLAN.md](../PLAN.md) have the brief and the steers.

Every piece of the campus is a module: a rectangle sized by its own model, at a position and a
turn (0 or 90 degrees) set in `params/site.yaml`.
- The modules:
  - the data hall (fixed);
  - the winter garden;
  - the greenhouse with its food court;
  - the community center and rink;
  - the square;
  - the field;
  - the homes;
  - the mobility hub;
  - the remote delivery building.
- `uv run brownfield site` (`src/brownfield/site.py`):
  - checks a layout against the rules;
  - prices it;
  - proposes cheaper ones. It never edits the params.
- It writes `out/pass3/site.md` and `out/pass3/site.json` (each layout's modules and routes, which
  the drawings read), and draws the figure below.

![The chosen layout and the optimizer's three proposals, on one scale, north up, the town below](site_plans.png)

## The answer

**The layout: the current one with two edits taken from the optimizer.** It costs $1,462k a year in
walking time, truck running and pipe, against $1,714k before the edits.
- **The field moves beside the mobility hub,** where its visitors park. It now stands 55 m from the
  nearest homes, close enough to overlook, far enough off their windows. All of the optimizer's
  early best finds had put it there. This saves $66k a year.
- **The hub moves 21 m west, against the community center's door** (6 m apart). The center and rink
  draw about 1,450 visitors a day, so each minute of their walk from the car park costs about
  $712,000 a year at US DOT's value of walking time. This saves $186k a year.

**What it keeps:**
- **The line from the town to the garden.** The public street runs from the town through the homes
  to the square, then on to the winter garden. The square stays the neighbourhood's heart, between
  the homes and the garden, with the center beside it.
- **Short walks:**
  - 3.3 minutes to the winter garden;
  - 2.6 to the square;
  - 2.5 to the center;
  - 1.9 to the field;
  - 5.8 to the food court.
- **No truck near the homes, and none across a walk.** The hall's trucks come in at its back, round
  the greenhouse's far side. All the site's trucks cost $40k a year to run; an underpass would cost
  $177k a year.

| | Cost a year | Walk from the homes to the square / food court / center / field / garden (min) | From the town (min) | Truck-km a year | Underpasses / raised crossings | Warm main |
|---|---|---|---|---|---|---|
| **Chosen** | **$1,462k** | 2.6 / 5.8 / 2.5 / 1.9 / 3.3 | 8.1 | 13,708 | 0 / 2 | 1,724 m |
| Before the two edits | $1,714k | 2.6 / 5.8 / 2.5 / 2.9 / 3.3 | 8.5 | 13,708 | 0 / 1 | 1,550 m |
| Proposal 1 | $1,456k | 3.2 / 3.0 / 5.5 / 2.8 / 5.5 | 6.2 | 8,300 | 0 / 3 | 1,438 m |
| Proposal 2 | $1,806k | 2.4 / 8.8 / 4.4 / 6.2 / 9.8 | 7.0 | 7,218 | 0 / 5 | 2,224 m |
| Proposal 3 | $1,867k | 2.4 / 10.1 / 3.4 / 5.8 / 3.5 | 7.9 | 8,886 | 0 / 1 | 2,506 m |

**Proposal 1 ties it, and the model can't tell them apart.** It is $6k a year cheaper (0.4%).
Moving each uncertain input to its low and its high (27 cases), proposal 1 is cheaper in 15 and the
chosen layout in 12. They stay within 6% of each other in all but two cases:
- with 400 walkers a day from the town, proposal 1 is 11% cheaper;
- with none, the chosen layout is 8% cheaper.

What proposal 1 does:
- puts the greenhouse against the hall's east side, with its food court beside the homes (3.0
  minutes);
- puts the center and the hub on the hall's west side, 5.5 minutes from the homes;
- puts the square at the town end of the neighbourhood.

Its edge is the town's walk in, which rests on a placeholder count of walkers. With no walkers from
the town, the chosen layout is $87k a year cheaper. The residents walk less in the chosen layout
($354k a year of their time against $396k). And it keeps the square between the homes and the
garden. So the chosen layout stays.

**An earlier find turned down.** An earlier search found a layout about 6% cheaper ($1,370k). It
moves the square to the town end and puts the 24-hour center and rink 6 m from the first row of
homes. Its whole advantage is the town's walk in again. With no walkers from the town, the chosen
layout is cheaper ($1,066k against $1,070k).

## What matters most, by the research

The score is what a layout costs a year, in dollars. Each term rests on a published value:

| Term | Value | Source |
|---|---|---|
| Walking time | $40.20 an hour (2024 dollars) | US DOT Benefit-Cost Analysis Guidance, 2026 Update, Table A-2: walking, waiting and transfer time, twice personal time in a vehicle ($20.10) |
| Running a truck | $2.336 a mile, $1.45 a km (2025), driver's pay included | ATRI, Operational Costs of Trucking, 2026 Update |
| An underpass | $2.2M (2024 dollars) | Bushell et al. 2013 (UNC HSRC): pedestrian underpasses $1.6-10.7M (2012 dollars), the low end brought to 2024 with the CPI |
| A raised crossing | $9,700 | Bushell et al. 2013: median $7,110 over 14 (2012 dollars), to 2024 with the CPI |
| The warm main | $1,100 a metre | pass 3 (a placeholder) |
| Paying off pipes and structures | 7% real, over 30 years | US DOT's rate since May 2025; the 30 years is a placeholder |
| Residents' visits | 300 people, 2.5 a home | ACS 2024 household size; trips by purpose from NHTS 2022, shared among the places by judgement |
| Visitors | about 1,450 a day to the center and rink, 36 to the field | ITE trip rates: community center 28.82 a day per 1,000 ft2; the rink scaled by its evening peak; soccer 71.33 a field |

What this says matters most, in order:
1. **People on foot are never asked to cross a truck road.** FHWA's Safe System hierarchy puts
   separation in space first. Physical separation "can permanently eliminate conflicts that lead to
   severe crashes". In 2024, 375 of the 6,144 pedestrians killed in single-vehicle crashes were hit
   by large trucks (NHTSA). The model sends trucks round any walk until an underpass would be cheaper:
   - the hall's trucks will go 9.3 km round before an underpass pays;
   - the produce trucks, fewer, 37 km.

   No layout above needs one. Many people won't use a bridge or tunnel if crossing at street level
   takes about the same time (FHWA, PEDSAFE). So where one is built, the walk stays level and the
   road dips.
2. **Visitors' walks:** the largest cost, $913k a year in the chosen layout.
   - About $520k is the walk from the car park to the doors (about 1,450 visitors a day). The hub
     belongs against the center.
   - The rest is the town's walk in, on a placeholder count.
3. **Residents' walks:** $354k a year. A minute more to the food court costs $29k a year.
4. **The warm main:** $153k a year.
5. **Truck distance matters least:** $40k a year. The trucks' extra kilometres round the
   greenhouse are cheap next to anything else.

The public road to the hub meets the walks in two places. Each gets a raised crossing, which slows
cars where people cross (Safe System: manage speeds where users mix).

## The rules

A layout that breaks any of these is never proposed:
- **Modules don't overlap.** Each keeps 5 m clear of the next; the winter garden is built
  against the hall.
- **Homes:**
  - none inside the 150 m noise setback (pass 3e);
  - all on the town side of the hall, so the neighbourhood grows toward Homer City borough;
  - rows run east-west, so every house has a wall facing south for the winter sun. The DOE's
    guidance is windows within 30 degrees of true south
    ([Energy Saver](https://www.energy.gov/energysaver/passive-solar-homes)). A skinny townhouse's windows are at its
    front and back, so rows running north-south would face east and west.
  - every door within 400 m of a shuttle stop (D14).
- **The public side faces the town (D12's rings).** The square, the center, the field, the hub
  and the food court never stand behind the hall, which is its service side.
- **The stand-off band.** No public vehicle within 15.24 m (50 ft) of the hall, the distance in
  the federal and defense criteria (UFC 4-010-01). Pedestrian places may sit in it.
- **Trucks are screened where they come in**, as at the Pentagon: the remote delivery building
  stands within 150 m of the site entrance. The 150 m is schematic.
- **Trucks stay on the service side.** No truck road comes within 100 m of the homes, the square,
  the center or the field; the hall's trucks come in at its back. The public road never runs
  behind the hall. The 100 m is judgement, as town truck routes keep off residential streets.
- **The homes' view of the winter garden stays open.** Jon wanted homes round the garden "having
  that as a view". No building stands in a 40 m wide band between them.
- **Nothing is built on the ash cap.** Only the field may go there.

One condition comes with the greenhouse wherever it stands: blackout curtains at night. Its grow
lights would otherwise light the sky over the homes. Leamington, Ontario, North America's greenhouse
capital, now requires growers to cover ceilings, side walls and end walls from an hour before sunset
to an hour after sunrise
([Greenhouse Canada](https://www.greenhousecanada.com/north-americas-greenhouse-capital-passes-light-abatement-by-law/)).

The winter garden stays on the hall's face, where the warm water comes in, until Jon chooses
whether it moves to the community center.

## How the routes are found

- **The search** prices thousands of layouts by street-grid distances, to each building's nearest
  door. This is fast but blind to buildings in the way.
- **The check** takes the best layout from each search, and the current layout, and routes them
  on a 10 m grid round the buildings (Dijkstra; 8 directions, no corner cutting):
  - **Walks** go from the homes to each place, and from the hub to its draws.
  - **Roads:**
    - every road keeps a road's clearance off every module;
    - produce trucks, visitors' cars and the shuttle stay out of the stand-off band;
    - trucks keep 100 m off the homes and the public places, and the public road keeps off the
      hall's back;
    - the hall's trucks go through the screening building first, then to the hall's back.
  - **Crossings:**
    - a truck road goes round a walk until the detour costs more than an underpass;
    - the public road keeps off the walks where a way round is under 50 m (a drawing choice), and
      crosses them on raised crossings.
- **The tests** check by hand:
  - the router: the route round a wall in a 100 x 30 m strip is 4 x 14.1 + 5 x 10 m;
  - a road goes round a walk when the detour is short, and straight across when there's no way
    round;
  - the detour at which an underpass pays;
  - the capital recovery factor;
  - that a minute more on a walk costs what its visits are worth;
  - that each rule catches the layout it's meant to.

## The drawings

![The chosen layout from the air, from the town side: the hall and the winter garden, the square, the community center with the car park at its door, the field, the homes, and the greenhouse with the trucks' road round its far side to the hall's back](site_aerial.png)

Forge `garden` now places every module from `out/pass3/site.json`, so moving a module in
`params/site.yaml` and rerunning `brownfield site` and `brownfield village` moves it in the
drawings. They also draw:
- the roads and walks the plan routes;
- the hub's car park with its shuttle stop;
- the remote delivery building;
- the raised crossings;
- stone planters along the stand-off line.

![The mobility hub: the car park with trees in islands and the shuttle stop's canopy, the community center beyond it, the field in front](site_hub.png)

**A correction to every earlier render.** The model's frame is x east, y south, z up, and the
renderer treated it as a right-handed frame. So every view before 2026-11-17 was the site's mirror
image: east and west were swapped. The renderer now puts east on the right when looking north (its
shadow-length check still passes, 3,480 mm against 3,464 mm). All the campus and garden views are
redrawn.

## What we don't know

- **The real site:** where the access road meets the site, where the way to the borough leaves
  it, and the ground's slopes. The entrance and the town point are placeholders. The cap's
  outline is schematic.
- **How often people go where:**
  - the shares of NHTS's trips that go to each campus place are judgement;
  - the count of walkers from the borough (100 a day) is a placeholder;
  - ITE's rates come from suburban sites people drive to, and the rink's daily rate was not found.
- **The underpass's cost** for a campus truck road: Bushell's underpasses were mostly under
  highways. It decides nothing here, since no layout needs one.
- **How far the screening building should stand from the hall.** The model keeps it at the
  entrance. The operator's security advisers would set the real distance; this repo stays at
  published principles.
- **Traffic volumes:** visitors' cars and shuttle trips are priced at the door, not routed by count.
  Truck counts are pass 3d's produce at 29,509 t a year (to rerun at 40 ha) and about 18 a day for
  the hall.
- **The walks** start from the middle of the neighbourhood, not from each door.
