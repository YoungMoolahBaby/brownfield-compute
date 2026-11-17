# What a real application needs, and what this plan has (D16)

Jon, 2026-11-17: "we cant leave out any details or else it will just look like concept art instead
of an actual plan." This page lists what Pennsylvania's law and Indiana County's ordinance require
an applicant to show, and against each item says where this repo answers it, or that it doesn't
yet.

## What governs

- **Indiana County's Subdivision and Land Development Ordinance (SALDO)**, Ord. 2023-0412, applies
  in Center Township.
  - The county applies it everywhere except White, East Wheatfield and Burrell Townships and
    Indiana, Blairsville and Homer City boroughs, which have their own (county quick guide, rev.
    2/11/26).
  - AWS's Homer City Energy Campus plan (about 2,200 acres in Center and Black Lick Townships) was
    filed under it on 2026-10-14. The county's 90-day review ends 2027-01-12.
  - A campus with homes, a community center and glasshouses is a **Class VI land development with
    buildings** (§302.6). It falls in Group 1: assembly, business, residential, utility.
- **Pennsylvania's Municipalities Planning Code (Act 247)**, Article VII, for a planned
  residential development: mixed homes, common open space and shared places in one plan.
  - A planned residential development sits inside a municipal zoning ordinance (§702).
  - Whether Center Township has zoning for this site wasn't confirmed: its website shows none,
    and the county zones only around its parks.
  - So the route may be the county SALDO alone. **To find out from the township first.**

Status key:
- **Have:** a model or drawing in this repo answers it.
- **Partial:** answered in principle or schematically, not to an applicant's standard.
- **Missing:** not yet answered.

## The planned development's application (MPC §707(4)) and findings (§709(b))

| Item | Status | Where, or what it needs |
|---|---|---|
| (i) Location, size and topography of the site; the landowner's interest | Partial | D17 maps AWS's six sites on the real ground, from the county's posted master plan fitted to the roads, with 10 m ground levels ([land.md](land.md)). Owners are PASDA's, as of ~2021; AWS's purchases aren't in it |
| (ii) Density of land use for each part | Have | The rings: homes a hectare for the flats, the townhouses and the houses (`brownfield village`, [village.md](village.md)) |
| (iii) Common open space: where, how big, who owns and keeps it | Partial | The square, the mall, the winter garden, the field and its loop, the greens between rows ([site.md](site.md)); owned by the trust (D11). The field's upkeep is costed (`brownfield village`, running the centre); the greens' upkeep isn't |
| (iv) Buildings' use, approximate height, bulk and location | Partial | Every type is sized: 3-storey walk-ups, the townhouses, 2-storey houses, the community center, the 17 m hall and its 26.5 m pylons, the glasshouses, the clubhouses (D18). D18 lays each town's new homes and clubhouse out lot by lot on the real ground ([conference.md](conference.md)); the campus itself is still schematic |
| (v) Water supply, sewage and stormwater | Partial | Sewage: Homer City's plant has room for ~1,350 homes on average, but a wet month already reached its rating ([village.md](village.md)). Water supply for the homes and the basins' top-up isn't sized against a source. Stormwater: rain gardens and swales named, not calculated |
| (vi) Covenants, easements and other restrictions, utility easements | Missing | The trust's set share of the campus tax (D11) and free public ground (D16) are principles, not drafted covenants. Easements for the warm loop, power and the service road through the moat aren't drawn |
| (vii) Parking; location and width of streets and public ways | Partial | Streets 15 m, the spine 24 m, the hub's car park sized at a share of the code minimums (D14). Positions schematic; no street sections drawn |
| (viii) Changes to municipal rules needed | Missing | Waits on whether Center Township has zoning here |
| (viii.1) Energy conservation and renewable energy | Have | The data center's heat warms the homes, the shared buildings, the walks and the glasshouses ([village.md](village.md), pass 3d); the outer houses on heat pumps (D16) |
| (ix) For a plan in phases, a schedule of filings | Partial | Phases follow demand (D11): phase 1 is ~240 homes from pass 4's newcomers. No dated schedule |
| §709(b)(1) Consistent with the comprehensive plan | Missing | Indiana County's comprehensive plan not yet read against this |
| §709(b)(2) Departures from the rules, and why they serve the public | Missing | Waits on (viii) |
| §709(b)(3) Open space: purpose, amount, reliable upkeep | Partial | As (iii) |
| §709(b)(4) Public services, traffic, light and air, recreation | Partial | Walks, roads, crossings and truck routes priced ([site.md](site.md)); recreation in full; traffic counts at the public road not modelled (ITE trip rates are in, for the car park) |
| §709(b)(5) Effect on the neighbourhood | Partial | Night noise at every home's windows; the hall's water use (none) and the creek ([pass 2](../pass2/creek.md)); the hearing record ([hearing-record.md](../hearing-record.md)) |
| §709(b)(6) For phases, protections for the public and residents | Missing | Improvement guarantees per phase |

## The county's preliminary plan for a land development with buildings (SALDO §302.6.B.3)

| Item | Status | Where, or what it needs |
|---|---|---|
| c. **Existing site features, resources and constraints:** context map; photos and an aerial; deeds or surveys | Partial | A context map of the ~15 x 15 km round the plant (D17, [land.md](land.md)); no photos, deeds or surveys |
| c. Existing conditions within 1,000 ft, at 1 in. = 50 ft: 2 ft contours, water features and flood zones, soils and geology, vegetation, sensitive areas (PNDI), viewsheds, roads, bridges, easements, utilities, hazards, historic sites | Partial | D17 maps 10 m ground levels and slopes, flood zones, wetlands, streams, mined-out ground, coal refuse, abandoned mine land, wells, roads, rail and power lines ([land.md](land.md)). D18 adds the buildings as they stand (Microsoft's footprints) and the vegetation's cover (NLCD 2021, 30 m). Still missing: 2 ft contours (from the 1 m lidar), soils, PNDI, viewsheds, easements, historic sites |
| c. **Spoiled land** | Partial | The capped ash site is kept to open uses (D12 rule); its real outline and DEP's closure terms are still to get |
| d. Preliminary site plan: parcels and zoning; streets, rights of way and easements; buildings and setbacks; vehicle and walking circulation; water features; parking and loading; phases; street sections | Partial | The modular site plan ([site.md](site.md)) has every module, road, walk, crossing and loading point, priced; schematic, not surveyed |
| d. **Outdoor lighting**, with a computer model of what's lit | Missing | The glasshouses' grow lights need full blackout curtains (Leamington's by-law, D10); the site's own lighting isn't modelled |
| e. **Stormwater** plan and report: watersheds, discharge points, impervious area, BMP designs, hydrology before and after, runoff volumes, upkeep plan | Missing | The roofs alone (~40 ha of glass, the hall, the homes) make this a large item. PA DEP's Chapter 102 rules apply |
| f. Grading plan, existing and proposed contours | Missing | The 10 m ground levels are in (D17); grading needs the 1 m lidar and a design |
| g. Parking plan, shared parking | Partial | The hub's car park at a share of code minimums (D14), cars optional; no shared-parking analysis |
| h. Resource protection plan | Missing | |
| i. **Erosion and sedimentation** control | Missing | PA DEP Chapter 102 (NPDES permit for construction over 1 acre) |
| j. Water and sewage service levels | Partial | Sewage as (v); water supply missing |
| k.-l. Variances, conditional uses | Missing | Waits on zoning |
| m. Proof of filing with agencies: PennDOT highway occupancy and signals; DEP sewage planning (Act 537), NPDES, water obstruction (Chapter 105) | Missing | Listed here so nothing is forgotten |
| o. Sealed survey and plat | Missing | A licensed surveyor's work |
| p. **Landscape plan**: species, sizes, quantities | Partial | Native Pennsylvania trees, kept 10 m from foundations, drawn by species in the arboretum (pass 3c); no planting schedule with sizes |
| q. Construction details: storm and sanitary sewers, detention, utilities | Partial | The walk-up's framing, its build sequence and its floors (pass 3b, D16), the cooler wall (pass 2d), the garden's cantilever; no sewer or utility details |
| r. Phasing plan and improvement guarantees | Partial | As (ix) |
| s. Highway occupancy permit | Missing | Trip generation exists for the car park (ITE); the access road isn't in the model |
| t. **Gas and oil wells** | Partial | DEP's records map 1,414 active conventional wells, 10 unconventional and 164 plugged or abandoned in the box, each kept clear of homes (D17). Unrecorded old wells need a field search |
| u. **Geotechnical report and slope analysis**, environmental hazard statement | Partial | Slopes from 10 m ground levels; old mine workings under about half the land are mapped from DEP (D17). Boreholes, subsidence studies and the ash and fill still to do |
| v. Impervious surface worksheet | Partial | Computable from the modules (roofs, glass, streets, the car park); not yet tabulated |
| w. Environmental analysis base map | Partial | D17's land map ([land.md](land.md)) |
| x. Wetland impact statement | Partial | The National Wetlands Inventory is mapped and kept clear (D17); a field delineation is still needed |

## What this says

- **The plan is strongest on the questions people raise at hearings:**
  - noise at every window;
  - the hall's water (none);
  - heat;
  - homes, their costs and who pays;
  - the shared places and their running costs;
  - walks and trucks.
  These are the items most proposals leave vague.
- **The ground is now mapped, coarsely (D17, [land.md](land.md)).** Ground levels, flood zones,
  wetlands, streams, old mine workings, wells, roads and power lines are on the map, with AWS's six
  sites fitted from the county's master plan. It is good enough to place things, not to engineer
  them. What's still missing:
  - soils;
  - 2 ft contours (from the 1 m lidar);
  - the ash cap's and the sites' real boundaries;
  - who owns the land today;
  - field checks of wells, wetlands and old mines.
- **Next**, in order:
  1. Ask Center Township whether it has zoning here, which settles the route.
  2. Get the full application package from the county, with its sheets at full resolution and
     its parcel list.
  3. Put each town's new homes ([conference.md](conference.md), laid out in D18) on parcels: who
     owns them, and whether they would sell; and ask the towns.
  4. Soils (USDA's Web Soil Survey) and the 1 m lidar for the communities' land only.
