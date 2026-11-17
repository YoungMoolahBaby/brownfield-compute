"""The site plan as modules (D12): every piece a rectangle with a size (from its own model), a position
and a rotation; rules every layout must pass; scores; and an optimizer that proposes layouts for Jon
to edit (`brownfield site`).

Security is designed in, in rings (D12): the community outside (natural surveillance), a landscape
stand-off band round the data hall that no public vehicle enters (pedestrian places such as the
hall's front and its basins may sit in it), and trucks screened at a remote delivery building.
Only published principles and distances are used: this repo is public.

Distances in the search are along the street grid (Manhattan), which is fast; the layouts reported
are checked with walks and roads routed on a 10 m grid round the buildings (`routes`).
Frame as forge `garden`: metres; x east, y south (toward the town); the hall's south face at y = -3.
"""

from __future__ import annotations

import heapq
import json
import math
from dataclasses import dataclass, replace

import numpy as np

from . import OUT_DIR

HALL = (-30.0, 92.0, -132.0, -3.0)  # the data hall (fixed: the anchor)
# The hall's front (D15): the great doors on its stepped base, and the forecourt's warm basins and falls
# down to the square, on the hall's centre line (forge `garden`, hall_front). With the moat (D16) the
# court runs on as an open mall between the glass to the moat's town edge.
FRONT = (-4.0, 66.0, -3.0, 36.0)
GARDEN_HOST = "community center"  # the winter garden is built against its face (D15)
# The greenhouse as the hall's moat (D16): blocks round the hall, joined into one glasshouse.
MOAT = ["greenhouse west", "greenhouse east", "greenhouse north-west", "greenhouse north-east",
        "greenhouse south-west", "greenhouse south-east"]
ATTACHED = ({frozenset(("data hall", "hall front")), frozenset((GARDEN_HOST, "winter garden"))}  # built against each other
            | {frozenset((a, b)) for a in MOAT for b in MOAT if a < b})


@dataclass(frozen=True)
class Module:
    name: str
    w: float  # m along x at rotation 0
    d: float  # m along y at rotation 0
    x: float  # centre
    y: float
    rot: int = 0  # 0 or 90 (a rectangle's 180/270 are the same footprint)
    movable: bool = True
    vehicles: bool = False  # public vehicles come to it (parking, roads): kept out of the stand-off band
    on_cap_ok: bool = False  # may stand on the capped ash site (open uses only)
    sleeps: bool = False  # people sleep there: kept beyond the noise setback
    faces: int = 180  # the bearing its front faces (180: south, toward the town; 270: west)

    @property
    def rect(self) -> tuple[float, float, float, float]:
        w, d = (self.d, self.w) if self.rot % 180 else (self.w, self.d)
        return (self.x - w / 2, self.x + w / 2, self.y - d / 2, self.y + d / 2)


def gap(a: tuple, b: tuple) -> float:
    """Clear distance between two rectangles (0 if they touch or overlap)."""
    dx = max(a[0] - b[1], b[0] - a[1], 0.0)
    dy = max(a[2] - b[3], b[2] - a[3], 0.0)
    return math.hypot(dx, dy)


def overlaps(a: tuple, b: tuple, margin: float = 0.0) -> bool:
    return a[0] < b[1] + margin and b[0] < a[1] + margin and a[2] < b[3] + margin and b[2] < a[3] + margin


def centre(r: tuple) -> tuple[float, float]:
    return ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)


def manhattan(a: tuple[float, float], b: tuple[float, float]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


RINGS = ("flats", "townhouses", "houses")  # the rings of homes, nearest the centre first (D16)


def modules(p: dict, greenhouse_ha: float, homes: dict) -> list[Module]:
    """The modules, sized from their own models, placed from params/site.yaml. `homes`: each ring's
    footprint (`homes_rect`)."""
    s = "site."
    side = math.sqrt(greenhouse_ha * 1e4)
    f = "village.fields."
    pos = lambda k: (p[s + k + ".x"], p[s + k + ".y"], int(p[s + k + ".rot"]))
    # One mobility hub (D14): a shared car park at a share of the code minimums for the center and
    # rink, the field and the food court, plus the shuttle stop, bikes and charging.
    hub_m2 = p[s + "car_share"] * (p[s + "park_center_m2"] + p[s + "park_field_m2"] + p[s + "park_food_m2"]) + p[s + "hub_extra_m2"]
    hub_side = hub_m2 ** 0.5
    # The community center and its rink under one roof, 90 m wide (forge `garden` draws the same).
    center_m2 = (p["village.amenities.center_ft2"] + p["village.rink.building_area_single_sheet"]) / 10.7639
    moat = moat_on(p)
    front = (FRONT[0], FRONT[1], FRONT[2], HALL[3] + p[s + "moat.south_m"]) if moat else FRONT
    out = [Module("data hall", HALL[1] - HALL[0], HALL[3] - HALL[2], *centre(HALL), movable=False),
           Module("hall front", front[1] - front[0], front[3] - front[2], *centre(front), movable=False),
           # The Fallingwater garden, 66.6 m along its back wall and 37.6 m from it to its lower pool's
           # edge; placed against the community center by `attach`.
           Module("winter garden", 66.6, 37.6, 0.0, 0.0, movable=False, faces=int(p[s + "garden.faces_deg"]))]
    if moat:
        for name, r in moat_blocks(p, greenhouse_ha).items():
            out.append(Module(name, r[1] - r[0], r[3] - r[2], *centre(r), movable=False))
    for name, key, w, d, kw in [
        *([] if moat else [("greenhouse", "greenhouse", side, side + 20.0, {})]),  # the head house and food court on its town side
        ("community center", "center", 90.0, center_m2 / 90.0, {}),
        ("square", "square", 60.0, 60.0, {}),
        ("field and loop", "field", p[f + "pitch_width_soccer"] + 46.0, p[f + "pitch_length_soccer"] + 46.0, {"on_cap_ok": True}),
        *[(k, k, homes[k][1] - homes[k][0], homes[k][3] - homes[k][2], {"sleeps": True}) for k in RINGS],
        ("mobility hub", "hub", hub_side, hub_side, {"vehicles": True}),
        ("remote delivery building", "delivery", 40.0, 30.0, {"vehicles": True}),
    ]:
        x, y, rot = pos(key)
        out.append(Module(name, w, d, x, y, rot, **kw))
    return attach(out)


def garden_on(g: Module, host: tuple) -> Module:
    """The winter garden with its back to the host's face opposite the way it faces, centred on it."""
    hx, hy = centre(host)
    half = g.d / 2  # from its back wall to its lower pool's edge
    at = {180: (hx, host[3] + half, 0), 0: (hx, host[2] - half, 0), 270: (host[0] - half, hy, 90), 90: (host[1] + half, hy, 90)}
    x, y, rot = at[g.faces % 360]
    return replace(g, x=x, y=y, rot=rot)


def attach(mods: list[Module]) -> list[Module]:
    """The layout with the winter garden moved to its host (it moves when the host does)."""
    host = by(mods, GARDEN_HOST).rect
    return [garden_on(m, host) if m.name == "winter garden" else m for m in mods]


def moat_on(p: dict) -> bool:
    return bool(p.get("site.moat.on", 0))


def moat_blocks(p: dict, greenhouse_ha: float) -> dict[str, tuple]:
    """The greenhouse round the hall (D16), as blocks: a column west and east of the hall, a band north
    of it split by the service crossing, and two blocks either side of the court and mall on the town
    side, the road ring between them and the hall. West, east and north are the same depth `b`, found
    so the blocks hold the greenhouse's area."""
    s = "site.moat."
    r, g, c, south = p[s + "road_m"], p["site.clear_m"], p[s + "crossing_m"], p[s + "south_m"]
    hx0, hx1, hy0, hy1 = HALL
    cx = centre(HALL)[0]
    ys = hy1 + south  # the moat's town edge
    sw, se = (FRONT[0] - g) - (hx0 - r), (hx1 + r) - (FRONT[1] + g)
    town = (sw + se) * max(south - r, 0.0)
    inner_w = hx1 - hx0 + 2 * r
    # Area: 2 b (ys - (hy0 - r - b)) + (inner_w - c) b + town = A, a quadratic in b.
    qa, qb, qc = 2.0, 2.0 * (ys - hy0 + r) + inner_w - c, town - greenhouse_ha * 1e4
    b = (-qb + math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa)
    y0 = hy0 - r - b
    out = {"greenhouse west": (hx0 - r - b, hx0 - r, y0, ys), "greenhouse east": (hx1 + r, hx1 + r + b, y0, ys),
           "greenhouse north-west": (hx0 - r, cx - c / 2, y0, hy0 - r), "greenhouse north-east": (cx + c / 2, hx1 + r, y0, hy0 - r)}
    if south > r:
        out["greenhouse south-west"] = (hx0 - r, FRONT[0] - g, hy1 + r, ys)
        out["greenhouse south-east"] = (FRONT[1] + g, hx1 + r, hy1 + r, ys)
    return out


def gh_rects(mods: list[Module]) -> list[tuple]:
    """The greenhouse's footprint: its one block, or the moat's blocks."""
    return [m.rect for m in mods if m.name == "greenhouse" or m.name in MOAT]


def gh_centre(mods: list[Module]) -> tuple[float, float]:
    """The greenhouse's middle, weighted by area (where its heat goes, on average)."""
    rs = gh_rects(mods)
    a = [(r[1] - r[0]) * (r[3] - r[2]) for r in rs]
    return (sum(w * centre(r)[0] for w, r in zip(a, rs)) / sum(a), sum(w * centre(r)[1] for w, r in zip(a, rs)) / sum(a))


def food_door(mods: list[Module]) -> tuple[float, float]:
    """The food court's door: in the head house on the greenhouse's town-side corner (forge food.rs);
    with the moat, on the south-east block's town edge beside the mall, at the square (D16)."""
    if any(m.name == "greenhouse south-east" for m in mods):
        r = by(mods, "greenhouse south-east").rect
        return (r[0] + 20.0, r[3])
    if any(m.name in MOAT for m in mods):  # a moat too shallow for town-side blocks: the east block's town corner
        r = by(mods, "greenhouse east").rect
        return (r[0] + 20.0, r[3])
    gh = by(mods, "greenhouse").rect
    return (gh[0] + 40.0, gh[3])


def produce_dock(mods: list[Module], gate: tuple) -> tuple[float, float]:
    """Where the produce trucks load: the side of the greenhouse nearest their way in, never its town
    side; with the moat, the east block's outer side."""
    if any(m.name in MOAT for m in mods):
        return docks(by(mods, "greenhouse east").rect)[1]
    return min(docks(by(mods, "greenhouse").rect), key=lambda q: manhattan(q, gate))


def glass_walls_m(rects: list[tuple]) -> float:
    """The outside walls of touching blocks: their perimeters less twice each shared edge."""
    per = sum(2 * ((r[1] - r[0]) + (r[3] - r[2])) for r in rects)
    shared = 0.0
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            if abs(a[1] - b[0]) < 1e-6 or abs(b[1] - a[0]) < 1e-6:
                shared += max(0.0, min(a[3], b[3]) - max(a[2], b[2]))
            if abs(a[3] - b[2]) < 1e-6 or abs(b[3] - a[2]) < 1e-6:
                shared += max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    return per - 2 * shared


BEARING = {0: "north", 90: "east", 180: "south", 270: "west"}
PUBLIC = ["square", "community center", "field and loop", "mobility hub"]


def view_blockers(mods: list[Module]) -> list[str]:
    return [m.name for m in mods if m.name == "greenhouse" or m.name in MOAT] + ["community center", "remote delivery building"]


def blocks_view(garden: tuple, homes: tuple, r: tuple, half_w: float = 20.0) -> bool:
    """Whether a building stands in the 40 m wide view from the homes' nearest edge to the garden."""
    a = centre(garden)
    b = (min(max(a[0], homes[0]), homes[1]), min(max(a[1], homes[2]), homes[3]))
    for k in range(1, 40):
        q = (a[0] + (b[0] - a[0]) * k / 40, a[1] + (b[1] - a[1]) * k / 40)
        if r[0] - half_w < q[0] < r[1] + half_w and r[2] - half_w < q[1] < r[3] + half_w:
            return True
    return False


def cap_rect(p: dict) -> tuple:
    s = "site.cap."
    return (p[s + "x0"], p[s + "x1"], p[s + "y0"], p[s + "y1"])


def by(mods: list[Module], name: str) -> Module:
    return next(m for m in mods if m.name == name)


def rules(p: dict, mods: list[Module]) -> list[str]:
    """What a layout breaks (empty: it passes)."""
    s = "site."
    bad = module_rules(p, mods)
    # The homes look out on the winter garden (Jon: homes round the garden, "having that as a view"):
    # the nearest ring, the flats. The garden's own host blocks it only if the view runs through the
    # building itself.
    for n in view_blockers(mods):
        if blocks_view(by(mods, "winter garden").rect, by(mods, "flats").rect, by(mods, n).rect,
                       0.0 if n == GARDEN_HOST else 20.0):
            bad.append(f"{n} blocks the homes' view of the winter garden")
    mm = metrics(p, mods, 0.0)
    if mm["stop_m"] > p[s + "walk_stop_m"]:
        bad.append(f"a door {mm['stop_m']:.0f} m from the nearest shuttle stop (> {p[s + 'walk_stop_m']:g} m)")
    # The rings in order (D16): the flats nearest the centre, then the townhouses, the houses furthest.
    sq = centre(by(mods, "square").rect)
    d = [manhattan(centre(by(mods, k).rect), sq) for k in RINGS]
    if not d[0] < d[1] < d[2]:
        bad.append("the rings out of order (flats, townhouses, houses: " + " / ".join(f"{x:.0f}" for x in d) + " m from the square)")
    return bad


def module_rules(p: dict, mods: list[Module]) -> list[str]:
    """The rules that hold module by module and pair by pair (so they also check a part-built layout)."""
    bad = []
    s = "site."
    for i, a in enumerate(mods):
        for b in mods[i + 1:]:
            margin = -0.5 if frozenset((a.name, b.name)) in ATTACHED else p[s + "clear_m"]
            if overlaps(a.rect, b.rect, margin):
                bad.append(f"{a.name} overlaps {b.name}")
    hall = HALL
    front = next((m.rect for m in mods if m.name == "hall front"), FRONT)
    for m in mods:
        if m.sleeps and gap(m.rect, hall) < p["village.site.home_setback_m"]:
            bad.append(f"{m.name} inside the noise setback ({gap(m.rect, hall):.0f} m < {p['village.site.home_setback_m']:g} m)")
        if m.name in RINGS and m.rot % 180:
            bad.append(f"{m.name} turned: its rows must run east-west so every house has a wall facing south (DOE)")
        if m.name in RINGS and m.rect[2] < hall[3]:
            bad.append(f"{m.name} not between the hall and the town (it must lie on the town side, y > {hall[3]:g})")
        if m.vehicles and gap(m.rect, hall) < p[s + "standoff_m"]:
            bad.append(f"{m.name} (public vehicles) inside the stand-off band ({gap(m.rect, hall):.0f} m < {p[s + 'standoff_m']:g} m)")
        if not m.on_cap_ok and m.name != "data hall" and overlaps(m.rect, cap_rect(p)):
            bad.append(f"{m.name} built on the ash cap")
        x0, x1, y0, y1 = m.rect
        if x0 < p[s + "bounds.x0"] or x1 > p[s + "bounds.x1"] or y0 < p[s + "bounds.y0"] or y1 > p[s + "bounds.y1"]:
            bad.append(f"{m.name} off the site")
        # The public side faces the town (D12's rings): no public place behind the hall, its service side.
        if m.name in PUBLIC and centre(m.rect)[1] < hall[2]:
            bad.append(f"{m.name} behind the hall (its service side)")
        # The square stands before the hall's front, on its axis: the forecourt's stair (and with the
        # moat, the mall) comes down into it from the great doors (D15, D16).
        if m.name == "square":
            sx, _ = centre(m.rect)
            if abs(sx - centre(front)[0]) > p[s + "axis_m"] or not 0.0 <= m.rect[2] - front[3] <= p[s + "forecourt_gap_m"]:
                bad.append(f"square off the hall's axis (its middle {sx - centre(front)[0]:+.0f} m across, its edge "
                           f"{m.rect[2] - front[3]:.0f} m from the forecourt)")
        if m.name == "greenhouse" and food_door([m])[1] < hall[2]:
            bad.append("the food court behind the hall (its service side)")
        # Trucks are screened where they come in (D12, as at the Pentagon): unscreened trucks never
        # drive into the site's interior.
        gate = (p[s + "gate.x"], p[s + "gate.y"])
        if m.name == "remote delivery building" and math.dist(centre(m.rect), gate) > p[s + "delivery_gate_m"]:
            bad.append(f"remote delivery building {math.dist(centre(m.rect), gate):.0f} m from the site entrance "
                       f"(> {p[s + 'delivery_gate_m']:g} m: trucks are screened where they come in)")
    return bad


def scatter(p: dict, mods: list[Module], rng: np.random.Generator, tries: int = 200) -> list[Module] | None:
    """A random legal layout, built up one module at a time: each at a random spot (half the time
    within 500 m of a module already placed) where the part-built layout still passes."""
    s = "site.bounds."
    movable = [i for i, m in enumerate(mods) if m.movable]
    gi = next(k for k, m in enumerate(mods) if m.name == "winter garden")  # placed with its host
    for _ in range(tries):
        cur, placed = list(mods), [i for i, m in enumerate(mods) if not m.movable and i != gi]
        for i in movable:
            for _ in range(300):
                if rng.random() < 0.5:
                    near = cur[int(rng.choice(placed))]
                    x, y = near.x + rng.uniform(-500, 500), near.y + rng.uniform(-500, 500)
                else:
                    x, y = rng.uniform(p[s + "x0"], p[s + "x1"]), rng.uniform(p[s + "y0"], p[s + "y1"])
                cand = replace(mods[i], x=float(round(x, -1)), y=float(round(y, -1)), rot=int(rng.choice([0, 90])))
                new = [(i, cand)] + ([(gi, garden_on(mods[gi], cand.rect))] if cand.name == GARDEN_HOST else [])
                if not module_rules(p, [cur[j] for j in placed] + [m for _, m in new]):
                    for j, m in new:
                        cur[j] = m
                        placed.append(j)
                    break
            else:
                break
        else:
            if not rules(p, cur):
                return cur
    return None


def metrics(p: dict, mods: list[Module], food_t: float, routed: bool = False) -> dict:
    """The scores of a layout: along the street grid (fast, for the search), or with the truck
    routes found on the grid round the buildings (`routed`, for the layouts reported)."""
    s, w = "site.", p["village.walking.speed_hcm_sidewalk"] * 60.0
    ring = {k: by(mods, k).rect for k in RINGS}
    fd = food_door(mods)
    # Walks end at a building's nearest door (the field's and the garden's nearest edge), the square's
    # middle (its shuttle stop) and the food court's door; from each ring's middle (its average door) and
    # its far edge on the spine (its furthest door).
    cen, fld, gdn = by(mods, "community center").rect, by(mods, "field and loop").rect, by(mods, "winter garden").rect
    sq = centre(by(mods, "square").rect)
    to = lambda hc: {"the square": sq, "the food court": fd, "the community center": door(cen, hc, 0.0),
                     "the field": door(fld, hc, 0.0), "the winter garden": door(gdn, hc, 0.0)}
    ring_walks = {k: {pl: manhattan(centre(r), v) / w for pl, v in to(centre(r)).items()} for k, r in ring.items()}
    far_walks = {k: {pl: manhattan((centre(r)[0], r[3]), v) / w for pl, v in to(centre(r)).items()} for k, r in ring.items()}
    people = ring_people(p)
    places = to(centre(ring["flats"]))
    walks = {pl: (sum(people[k] * ring_walks[k][pl] for k in RINGS) / sum(people.values()), max(far_walks[k][pl] for k in RINGS))
             for pl in places}
    gate = (p[s + "gate.x"], p[s + "gate.y"])
    dock = centre(by(mods, "remote delivery building").rect)
    # Loading docks on a side away from the town (the town side holds the food court and the garden):
    # the side nearest the truck's way in. The hall's trucks are screened at the delivery building first;
    # the produce trucks go from the entrance straight to the greenhouse.
    gh_dock = produce_dock(mods, gate)
    hall_dock = docks(HALL)[2]  # the hall's trucks come in on its service side, behind it
    food_trips, hall_trips = food_t / p[s + "truck_t"], p[s + "hall_trucks_yr"]
    truck_km = (food_trips * manhattan(gate, gh_dock) + hall_trips * (manhattan(gate, dock) + manhattan(dock, hall_dock))) / 1000.0
    town = (p[s + "town.x"], p[s + "town.y"])
    hub = centre(by(mods, "mobility hub").rect)
    truck_legs = [(gate, gh_dock), (gate, dock), (dock, hall_dock)]
    car_legs = [(gate, hub), (town, hub)]  # visitors' cars and the shuttle to the mobility hub
    # Walks a road cuts across whichever way round it goes: each leg runs x-then-y or y-then-x,
    # whichever cuts fewer; a walk is cut if it is cut whichever way round it goes too.
    walk_legs = [((centre(r)[0], r[2]), v) for r in ring.values() for v in to(centre(r)).values()]
    cuts = lambda legs: sum(min(sum(1 for wa, wb in walk_legs if all(_paths_cross(lp, wp) for wp in _ls(wa, wb))) for lp in _ls(a, b))
                            for a, b in legs)
    crossings, car_crossings = cuts(truck_legs), cuts(car_legs)
    town_walk = {k: manhattan(town, v) / w for k, v in [("the square", places["the square"]), ("the food court", fd),
                                                         ("the community center", door(cen, town, 0.0)), ("the field", door(fld, town, 0.0))]}
    src = (centre(HALL)[0], HALL[3])
    # The houses heat themselves (`rings.houses_on_loop`: pass 3's comparison at their frontage), so the
    # warm main runs to the flats and the townhouses.
    heated = ["hall front", "winter garden", "community center", "field and loop", "flats", "townhouses"]
    main_m = sum(manhattan(src, centre(by(mods, n).rect)) for n in heated) + manhattan(src, gh_centre(mods))
    # From the hub's middle (the average parking space) to the door.
    parking_walk = {k: manhattan(hub, v) / w for k, v in [("center and rink", door(cen, hub, 0.0)),
                                                         ("field", door(fld, hub, 0.0)), ("food court", fd)]}
    # Shuttle stops: the hub, the square, and on each ring's spine at its far end (the last where the
    # town begins).
    stops = [hub, sq] + [(centre(r)[0], r[3]) for r in ring.values()]
    corners = [(r[i], r[j]) for r in ring.values() for i in (0, 1) for j in (2, 3)]
    stop_m = max(min(manhattan(c, st) for st in stops) for c in corners)
    # Heated walks (D14): each ring's spine and a walk on each side of every green, the square, and the
    # walk to the hub.
    s2 = "village.site."
    walk_m2 = 60.0 * 60.0 + manhattan(hub, sq) * 3.0
    for r in ring.values():
        rows = max(1, round((r[3] - r[2]) / (2 * p[s2 + "lot_depth_m"] + p[s2 + "street_w_m"] + p[s2 + "green_w_m"])))
        walk_m2 += (r[3] - r[2]) * 6.0 + rows * 2 * (r[1] - r[0]) * 2.4
    xs = [v for m in mods for v in m.rect[:2]]
    ys = [v for m in mods for v in m.rect[2:]]
    out = {"walks": walks, "ring_walks": ring_walks, "truck_km_yr": truck_km, "truck_crossings": crossings, "car_crossings": car_crossings,
           "truck_legs": truck_legs, "town_walk": town_walk,
           "main_m": main_m, "main_usd": main_m * p["pass3.block.main_usd_m"], "parking_walk": parking_walk,
           "land_ha": (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e4, "stop_m": stop_m, "heated_walk_m2": walk_m2,
           "homes_from_hall_m": min(gap(r, HALL) for r in ring.values()), "routed": False}
    if routed:
        out.update(routes(p, mods, food_t), routed=True)
    return out


def docks(r: tuple) -> list[tuple[float, float]]:
    """The middles of a building's west, east and north sides (not its town side)."""
    xm, ym = centre(r)
    return [(r[0], ym), (r[1], ym), (xm, r[2])]


def _ls(a: tuple, b: tuple) -> list[list[tuple]]:
    """The two street-grid routes from a to b: x first, then y; or y first, then x."""
    return [[a, (b[0], a[1]), b], [a, (a[0], b[1]), b]]


def _segs_cross(a0: tuple, a1: tuple, b0: tuple, b1: tuple) -> bool:
    """Whether two axis-aligned segments meet (touching counts)."""
    return (min(a0[0], a1[0]) <= max(b0[0], b1[0]) and min(b0[0], b1[0]) <= max(a0[0], a1[0])
            and min(a0[1], a1[1]) <= max(b0[1], b1[1]) and min(b0[1], b1[1]) <= max(a0[1], a1[1]))


def _paths_cross(p: list, q: list) -> bool:
    return any(_segs_cross(p[i], p[i + 1], q[j], q[j + 1]) for i in range(len(p) - 1) for j in range(len(q) - 1))


def door(r: tuple, toward: tuple, out_m: float) -> tuple[float, float]:
    """The point on a building's edge nearest `toward`, stepped `out_m` outside it."""
    x, y = min(max(toward[0], r[0]), r[1]), min(max(toward[1], r[2]), r[3])
    k = int(np.argmin([x - r[0], r[1] - x, y - r[2], r[3] - y]))
    return [(r[0] - out_m, y), (r[1] + out_m, y), (x, r[2] - out_m), (x, r[3] + out_m)][k]


class Grid:
    """A 10 m grid over the layout for routing round buildings (8-way, no corner cutting)."""

    def __init__(self, p: dict, mods: list[Module], cell: float = 10.0, pad: float = 150.0):
        s = "site."
        xs = [v for m in mods for v in m.rect[:2]] + [p[s + "gate.x"], p[s + "town.x"]]
        ys = [v for m in mods for v in m.rect[2:]] + [p[s + "gate.y"], p[s + "town.y"]]
        self.x0, self.y0 = max(min(xs) - pad, p[s + "bounds.x0"]), max(min(ys) - pad, p[s + "bounds.y0"])
        x1, y1 = min(max(xs) + pad, p[s + "bounds.x1"]), min(max(ys) + pad, p[s + "bounds.y1"])
        self.cell = cell
        self.nx, self.ny = int(math.ceil((x1 - self.x0) / cell)), int(math.ceil((y1 - self.y0) / cell))
        self.X, self.Y = np.meshgrid(self.x0 + (np.arange(self.nx) + 0.5) * cell, self.y0 + (np.arange(self.ny) + 0.5) * cell)

    def mask(self, rects: list[tuple], inflate: float = 0.0) -> np.ndarray:
        m = np.zeros(self.X.shape, bool)
        for r in rects:
            m |= (self.X > r[0] - inflate) & (self.X < r[1] + inflate) & (self.Y > r[2] - inflate) & (self.Y < r[3] + inflate)
        return m

    def idx(self, q: tuple) -> int:
        i = min(max(int((q[0] - self.x0) // self.cell), 0), self.nx - 1)
        j = min(max(int((q[1] - self.y0) // self.cell), 0), self.ny - 1)
        return j * self.nx + i

    def xy(self, k: int) -> tuple[float, float]:
        return (float(self.X.flat[k]), float(self.Y.flat[k]))

    def paths(self, blocked: np.ndarray, mult: np.ndarray, src: tuple, targets: list[tuple]) -> list[list[int]]:
        """Least-cost routes (Dijkstra) from src to each target, as cell indices; [] where none."""
        nx, ny, c = self.nx, self.ny, self.cell
        free = (~blocked).ravel().tolist()
        s, ts = self.idx(src), [self.idx(q) for q in targets]
        for k in [s, *ts]:
            free[k] = True
        w = mult.ravel().tolist()
        dist, prev = [math.inf] * (nx * ny), [-1] * (nx * ny)
        dist[s], heap, left = 0.0, [(0.0, s)], set(ts)
        r2 = math.sqrt(2.0)
        steps = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0), (-1, -1, r2), (1, -1, r2), (-1, 1, r2), (1, 1, r2)]
        while heap and left:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            left.discard(u)
            ux, uy = u % nx, u // nx
            for dx, dy, step in steps:
                vx, vy = ux + dx, uy + dy
                if not (0 <= vx < nx and 0 <= vy < ny):
                    continue
                v = vy * nx + vx
                if not free[v] or (dx and dy and not (free[uy * nx + vx] and free[vy * nx + ux])):
                    continue
                nd = d + step * c * 0.5 * (w[u] + w[v])
                if nd < dist[v]:
                    dist[v], prev[v] = nd, u
                    heapq.heappush(heap, (nd, v))
        out = []
        for k in ts:
            if dist[k] == math.inf:
                out.append([])
                continue
            path = [k]
            while path[-1] != s:
                path.append(prev[path[-1]])
            out.append(path[::-1])
        return out

    def length(self, path: list[int]) -> float:
        return sum(math.dist(self.xy(a), self.xy(b)) for a, b in zip(path, path[1:]))

    def line(self, path: list[int]) -> list[tuple[float, float]]:
        """The route as its corner points (for drawing)."""
        pts = [self.xy(k) for k in path]
        if len(pts) < 3:
            return pts
        keep = [pts[0]] + [b for a, b, c in zip(pts, pts[1:], pts[2:])
                           if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0])] + [pts[-1]]
        return keep


def routes(p: dict, mods: list[Module], food_t: float) -> dict:
    """The walks and roads on the grid, round the buildings. Walks: from the homes to each place,
    and from the mobility hub to its draws. Roads: a road's clearance off every module; the
    produce trucks, visitors' cars and the shuttle (unscreened) kept out of the stand-off band;
    every road routed round the walks where the detour is shorter than the one a designer would
    accept (params). The places where a road still meets a walk are its crossings."""
    s = "site."
    g = Grid(p, mods)
    rect = lambda n: by(mods, n).rect
    homes, cen = [rect(k) for k in RINGS], rect("community center")
    ghs = gh_rects(mods)
    fd0 = food_door(mods)
    fd = (fd0[0], fd0[1] + 1.5 * g.cell)
    hub = centre(rect("mobility hub"))
    walk_block = g.mask([HALL, *ghs, cen, rect("remote delivery building")])
    ones = np.ones(g.X.shape)
    walks = []
    for h in homes:
        walks += g.paths(walk_block, ones, centre(h), [centre(rect("square")), fd, door(cen, centre(h), 1.5 * g.cell),
                                                       centre(rect("field and loop")), centre(rect("winter garden"))])
    walks += g.paths(walk_block, ones, hub, [door(cen, hub, 1.5 * g.cell), fd, centre(rect("field and loop"))])
    on_walk = np.zeros(g.X.size, bool)
    for w in walks:
        on_walk[w] = True
    on_walk = on_walk.reshape(g.X.shape)
    grown = on_walk.copy()  # a walk and its verges, one cell either side
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            grown |= np.roll(np.roll(on_walk, dy, 0), dx, 1)
    road = p[s + "road_clear_m"]
    # Crossing a walk and its verges (3 cells) costs a road the detour it would accept to go round.
    mult = lambda detour_m: 1.0 + grown * detour_m / (3.0 * g.cell)
    food_trips, hall_trips = food_t / p[s + "truck_t"], p[s + "hall_trucks_yr"]
    blocked = g.mask([m.rect for m in mods], road)
    gate = (p[s + "gate.x"], p[s + "gate.y"])
    dl = rect("remote delivery building")
    dl_door = door(dl, gate, road + 1.5 * g.cell)
    gd = produce_dock(mods, gate)
    gh_dock = door(min(ghs, key=lambda r: gap(r, (gd[0], gd[0], gd[1], gd[1]))), gd, road + 1.5 * g.cell)
    # The hall's service side, behind it; with the moat, its trucks reach it through the covered
    # crossing in the north blocks, the glass's edge as the road's kerb (D16).
    hall_dock = door(HALL, docks(HALL)[2], road + 1.5 * g.cell)
    moat = [m.rect for m in mods if m.name in MOAT]
    to_hall_block = (g.mask([m.rect for m in mods if m.name not in MOAT], road) | g.mask(moat)) if moat else blocked
    public = blocked | g.mask([HALL], p[s + "standoff_m"])  # unscreened vehicles stay out of the stand-off band
    # Trucks stay on the service side: no truck road near the homes or the public places.
    away = g.mask([*homes, cen, rect("square"), rect("field and loop")], p[s + "truck_clear_m"])
    (produce,) = g.paths(public | away, mult(truck_detour_m(p, food_trips)), gate, [gh_dock])
    (to_dl,) = g.paths(blocked | away, mult(truck_detour_m(p, hall_trips)), gate, [dl_door])
    (to_hall,) = g.paths(to_hall_block | away, mult(truck_detour_m(p, hall_trips)), dl_door, [hall_dock])
    trucks = [produce, to_dl, to_hall]
    # Visitors' cars and the shuttle: from the public road and from the town to the mobility hub.
    town = (p[s + "town.x"], p[s + "town.y"])
    hb = rect("mobility hub")
    # The public road stays on the public side too: never behind the hall, its service side.
    cars_ok = public | (g.Y < HALL[2])
    (car_gate,) = g.paths(cars_ok, mult(p[s + "car_detour_m"]), gate, [door(hb, gate, road + 1.5 * g.cell)])
    (car_town,) = g.paths(cars_ok, mult(p[s + "car_detour_m"]), town, [door(hb, town, road + 1.5 * g.cell)])
    cars = [car_gate, car_town]
    ok = all(trucks) and all(cars) and all(walks)
    # Crossings: the separate places where the roads meet the walks: the truck roads' (underpasses),
    # then the public road's where no truck road already crosses (raised crossings).
    flat = grown.ravel()

    def meets(roads: list, skip: np.ndarray | None = None) -> list[tuple[float, float]]:
        meet = np.zeros(g.X.size, bool)
        for t in roads:
            meet[t] |= flat[t]
        if skip is not None:
            meet &= ~skip
        cells, at = set(np.flatnonzero(meet).tolist()), []
        while cells:
            todo, grp = [cells.pop()], []
            while todo:
                k = todo.pop()
                grp.append(k)
                for d in (-g.nx - 1, -g.nx, -g.nx + 1, -1, 1, g.nx - 1, g.nx, g.nx + 1):
                    if k + d in cells:
                        cells.discard(k + d)
                        todo.append(k + d)
            at.append(g.xy(sorted(grp)[len(grp) // 2]))
        return at

    under = meets(trucks)
    truck_cells = np.zeros(g.X.size, bool)
    for t in trucks:
        truck_cells[t] = True
    raised = meets(cars, truck_cells)
    km = (food_trips * g.length(produce) + hall_trips * (g.length(to_dl) + g.length(to_hall))) / 1000.0 if ok else math.inf
    return {"truck_km_yr": km, "truck_crossings": len(under), "car_crossings": len(raised), "routes_ok": ok,
            "car_road_m": sum(g.length(c) for c in cars),
            "lines": {"trucks": [g.line(t) for t in trucks if t], "cars": [g.line(c) for c in cars if c],
                      "walks": [g.line(w) for w in walks if w], "underpasses": under, "raised_crossings": raised}}


def crf(r: float, n: float) -> float:
    """Capital recovery factor: the share of a capital cost paid each year over n years at rate r."""
    return r / (1.0 - (1.0 + r) ** -n)


def truck_detour_m(p: dict, trips_yr: float) -> float:
    """How far a truck road should go round a walk before an underpass is cheaper: the underpass's
    yearly cost over what each extra metre costs the trucks on that road (there and back)."""
    v = "site.value."
    underpass_yr = p[v + "underpass_usd"] * crf(p[v + "discount"], p[v + "life_yr"])
    return underpass_yr / max(trips_yr * 2.0 * p[v + "truck_usd_km"] / 1000.0, 1e-9)


PLACE_VISITS = {"the square": "square_wk", "the food court": "food_court_wk", "the community center": "center_wk",
                "the field": "field_wk", "the winter garden": "garden_wk"}


def hub_visitors(p: dict) -> dict:
    """Visitors a day arriving at the mobility hub for the center and rink and for the field: ITE's
    weekday vehicle trip ends, halved to arrivals, one person each (a floor: cars carry more). The
    rink's daily rate is the center's scaled by their evening-peak rates. The food court's visitors
    are mostly the center's and the residents' already, so they are not added."""
    s = "site.visits."
    center = p["village.amenities.center_ft2"] / 1000.0 * p[s + "ite_center_kft2"]
    rink = p["village.rink.building_area_single_sheet"] / 1000.0 * p[s + "ite_center_kft2"] * p[s + "ite_rink_pm"] / p[s + "ite_center_pm"]
    return {"center and rink": (center + rink) / 2.0, "field": p[s + "ite_soccer_field"] / 2.0}


def costs(p: dict, m: dict) -> dict:
    """What a layout costs a year, in US dollars: the walking time of residents, of visitors from the
    mobility hub and of people walking in from the town, at US DOT's value of walking time; the
    trucks' running cost (there and back); and the warm main, underpasses (truck roads) and raised
    crossings (the public road) paid off over their life."""
    v, s = "site.value.", "site.visits."
    per_min = p[v + "walk_usd_h"] / 60.0
    people = ring_people(p)
    walk = sum(people[r] * p[s + k] * 52.0 * 2.0 * m["ring_walks"][r][place] for r in RINGS for place, k in PLACE_VISITS.items()) * per_min
    hub = sum(n * m["parking_walk"][k] for k, n in hub_visitors(p).items()) * 365.0 * 2.0 * per_min
    town = p[s + "town_walkers_day"] * 365.0 * 2.0 * float(np.mean(list(m["town_walk"].values()))) * per_min
    k = crf(p[v + "discount"], p[v + "life_yr"])
    return {"residents' walks": walk, "visitors' walks": hub + town,
            "trucks": m["truck_km_yr"] * 2.0 * p[v + "truck_usd_km"],
            "underpasses": m["truck_crossings"] * p[v + "underpass_usd"] * k,
            "raised crossings": m.get("car_crossings", 0) * p[v + "raised_crossing_usd"] * k,
            "warm main": m["main_m"] * p["pass3.block.main_usd_m"] * k}


def score(p: dict, m: dict) -> float:
    """Lower is better: what the layout costs a year, in thousands of dollars (`costs`)."""
    return sum(costs(p, m).values()) / 1000.0


def optimise(p: dict, mods: list[Module], food_t: float, n_starts: int = 16, steps: int = 2500, seed: int = 3) -> list[tuple]:
    """Simulated annealing from the current layout and from random legal arrangements, moving one
    movable module at a time on a 10 m grid (and turning it 90 degrees now and then), keeping only
    layouts that pass every rule; then checks the finds with routes round the buildings. Returns
    the best three that differ from the current layout (score, metrics, modules)."""
    rng = np.random.default_rng(seed)
    movable = [i for i, m in enumerate(mods) if m.movable]
    found = []
    for start in range(n_starts):
        cur = list(mods)
        if start:  # a random legal arrangement to start from
            cur = scatter(p, mods, rng)
            if cur is None:
                continue
        if rules(p, cur):
            continue
        cur_sc = score(p, metrics(p, cur, food_t))
        best, best_sc = cur, cur_sc
        t0 = 0.07 * cur_sc  # the share of the score the first search's temperature was (2 on ~30)
        for k in range(steps):
            temp = t0 * (1 - k / steps) + 1e-3
            i = int(rng.choice(movable))
            step = rng.choice([10, 20, 50, 100, 200])
            dx, dy = rng.choice([-1, 0, 1], 2) * step
            trial = list(cur)
            trial[i] = replace(cur[i], x=cur[i].x + dx, y=cur[i].y + dy, rot=cur[i].rot if rng.random() > 0.1 else 90 - cur[i].rot)
            trial = attach(trial)
            if rules(p, trial):
                continue
            sc = score(p, metrics(p, trial, food_t))
            if sc < cur_sc or rng.random() < math.exp(-(sc - cur_sc) / temp):
                cur, cur_sc = trial, sc
                if sc < best_sc:
                    best, best_sc = trial, sc
        found.append(best)
    # The search scores on the street grid; check its finds, and the current layout, with the routes
    # found round the buildings, and keep the best three by that.
    out, seen = [], {tuple((round(m.x, -1), round(m.y, -1), m.rot) for m in mods)}
    for ms in found:
        key = tuple((round(m.x, -1), round(m.y, -1), m.rot) for m in ms)
        if key in seen:
            continue
        seen.add(key)
        m = metrics(p, ms, food_t, routed=True)
        if m["routes_ok"]:
            out.append((score(p, m), m, ms))
    out.sort(key=lambda t: t[0])
    return out[:3]


def homes_rect(p: dict) -> dict[str, tuple]:
    """Each ring's footprint from its lots (`rings.rect`)."""
    from . import rings

    return {k: rings.rect(p, k) for k in RINGS}


def ring_people(p: dict) -> dict[str, float]:
    """The people living in each ring (`rings.persons`)."""
    from . import rings

    return rings.persons(p)


TOWN_SIDE = ["square", "community center", "winter garden", "mobility hub", "field and loop", *RINGS]


def depths(p: dict, mods: list[Module], food_t: float, tries=(40.0, 100.0, 150.0, 250.0)) -> list[dict]:
    """The moat's town side at other depths (D16): the town-side modules moved by the change in depth,
    the rest as they are; each layout's rules, cost and the night noise at the first homes' windows."""
    from . import rings

    s = "site.moat.south_m"
    out = []
    for south in tries:
        q = dict(p, **{s: south})
        dy = south - p[s]
        ms = [replace(m, y=m.y + dy) if m.name in TOWN_SIDE else m for m in modules(q, p["site.greenhouse_ha"], homes_rect(p))]
        ms = attach(ms)
        mm = metrics(q, ms, food_t, routed=True)
        d = min(gap(by(ms, k).rect, HALL) for k in RINGS)
        loud = {cut: max(rings.night_db(q, k, gap(by(ms, k).rect, HALL), cut) for k in RINGS) for cut in (0.0, 3.0)}
        vehicles = min(gap(m.rect, HALL) for m in ms if m.vehicles)
        out.append({"south_m": south, "rules": rules(q, ms), "score": score(q, mm), "metrics": mm, "homes_m": d,
                    "night_db": loud, "vehicles_m": vehicles, "band_m": moat_band(q)})
    return out


def moat_band(p: dict) -> float:
    """The moat's depth west, east and north of the road ring."""
    r = moat_blocks(p, p["site.greenhouse_ha"])["greenhouse west"]
    return r[1] - r[0]


def moat_lines(p: dict, mods: list[Module]) -> list[str]:
    """The moat's glass against one block of the same area, and the hall's winter shadow on it."""
    s = "site.moat."
    rs = gh_rects(mods)
    area = sum((r[1] - r[0]) * (r[3] - r[2]) for r in rs)
    side = math.sqrt(area)
    one = 2 * (side + side + 20.0)  # one block (side x side + 20 m), as before D16
    roof = area / math.cos(math.radians(p[s + "roof_deg"]))
    h = p[s + "gutter_m"]
    walls = glass_walls_m(rs)
    extra = (walls - one) * h / (roof + one * h)
    sun = 90.0 - p[s + "lat_deg"] - 23.44  # noon on the winter solstice
    shadow = p[s + "hall_top_m"] / math.tan(math.radians(sun))
    north = [r for n, r in zip([m.name for m in mods if m.name in MOAT], [m.rect for m in mods if m.name in MOAT]) if "north" in n]
    shade = sum((r[1] - r[0]) for r in north) * max(shadow - p[s + "road_m"], 0.0)
    front = by(mods, "hall front").rect
    return [f"- **The greenhouse is the hall's moat** (D16): {len(rs)} blocks, {area / 1e4:.1f} ha, "
            f"{moat_band(p):.0f} m deep west, east and north of a {p[s + 'road_m']:g} m fire and service road round the hall, "
            f"{p[s + 'south_m']:g} m on the town side, where the court and an open mall {front[1] - front[0]:.0f} m wide run "
            f"{front[3] - front[2]:.0f} m from the great doors to the square. The hall's trucks come through a "
            f"{p[s + 'crossing_m']:g} m covered crossing in the north blocks.",
            f"- Glass: {walls:,.0f} m of outside wall against {one:,.0f} m for one block of the same area, so "
            f"{extra:+.1%} more glass in all ({h:g} m walls, roofs at {p[s + 'roof_deg']:g} degrees).",
            f"- The hall's shadow at noon on the shortest day (sun {sun:.0f} degrees up, parapet {p[s + 'hall_top_m']:g} m): "
            f"{shadow:.0f} m, so {shade / 1e4:.2f} ha of the north blocks beyond the road is in its shade at midwinter noon "
            "(longer morning and evening): for packing, cold store and loading, not crops."]


def same(a: list[Module], b: list[Module]) -> bool:
    return all(round(m.x, -1) == round(n.x, -1) and round(m.y, -1) == round(n.y, -1) and m.rot == n.rot for m, n in zip(a, b))


def report(p: dict, mods: list[Module], m: dict, proposals: list[tuple], deep: list[dict] | None = None) -> str:
    L = ["**The current layout** (params/site.yaml)", ""]
    bad = rules(p, mods)
    L.append("Rules: " + ("all pass." if not bad else "; ".join(bad)))
    if any(x.name in MOAT for x in mods):
        L += [""] + moat_lines(p, mods)
    if deep:
        L += ["", "**The moat's town side at other depths** (the town-side modules moved with its edge; night noise at the "
              "first homes' worst window, WHO's guideline 40 dB(A))", "",
              "| Town side | Band W/E/N | Cost a year | Walks: square / food court / center / field / garden (min) | First homes "
              "| Night, pass 2's fans | Fans 3 dB quieter | Public vehicles kept off | Rules |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in deep:
            w = " / ".join(f"{v[0]:.1f}" for v in r["metrics"]["walks"].values())
            cost = f"${r['score']:,.0f}k" if math.isfinite(r["score"]) else "no route"
            L.append(f"| {r['south_m']:g} m | {r['band_m']:.0f} m | {cost} | {w} | {r['homes_m']:.0f} m "
                     f"| {r['night_db'][0.0]:.1f} dB(A) | {r['night_db'][3.0]:.1f} dB(A) | {r['vehicles_m']:.0f} m "
                     f"| {'pass' if not r['rules'] else '; '.join(r['rules'])} |")
    L += ["", "| Walk from the homes to | Average | Furthest door |", "|---|---|---|"]
    L += [f"| {k} | {v[0]:.1f} min | {v[1]:.1f} min |" for k, v in m["walks"].items()]
    L += ["", "- Walk from where the town's way comes in: " + ", ".join(f"{k} {v:.1f} min" for k, v in m["town_walk"].items()) + ".",
          f"- Trucks: {m['truck_km_yr']:,.0f} truck-km a year on site (one way): the produce trucks from the entrance to the "
          f"greenhouse's dock, the hall's through the remote delivery building. Routed round the buildings, the truck roads cross "
          f"the main walks in {m['truck_crossings']} place(s) (an underpass each); the public road to the mobility hub "
          f"({m['car_road_m']:,.0f} m from the entrance and from the town) in {m['car_crossings']} more (a raised crossing each).",
          f"- Warm main from the hall to the heated modules: {m['main_m']:,.0f} m (about ${m['main_usd'] / 1e6:,.1f}M at pass 3's cost).",
          "- Walk from the mobility hub: " + ", ".join(f"{k} {v:.1f} min" for k, v in m["parking_walk"].items()) + "; "
          f"the furthest door is {m['stop_m']:.0f} m from a shuttle stop.",
          f"- Heated walks (snow-free all winter on the warm water): about {m['heated_walk_m2']:,.0f} m2.",
          f"- Homes {m['homes_from_hall_m']:.0f} m from the hall (noise setback {p['village.site.home_setback_m']:g} m), "
          "on the town side of it; public vehicles kept "
          f"{p['site.standoff_m']:g} m off it.",
          f"- The layout spans {m['land_ha']:.0f} ha.",
          f"- **What it costs a year: ${score(p, m):,.0f}k** (lower is better): "
          + ", ".join(f"{k} ${v / 1000:,.0f}k" for k, v in costs(p, m).items()) + ".",
          f"- The winter garden stands against the community center, facing {BEARING[by(mods, 'winter garden').faces % 360]}, "
          "and moves with it; the hall's front holds the great doors and the warm basins (D15)."]
    L += ["", "**Proposals** (simulated annealing on the street grid, then every find and the current layout checked with the "
          "routes found round the buildings; every one passes every rule)", "",
          "| | Cost a year | Walk to the square / food court / center / field / garden (min) | From the town (min) | Truck-km a year "
          "| Underpasses / raised crossings | Warm main | Land |",
          "|---|---|---|---|---|---|---|---|"]
    for k, (sc, mm, ms) in enumerate([(score(p, m), m, mods), *proposals], start=-1):
        w = " / ".join(f"{v[0]:.1f}" for v in mm["walks"].values())
        tw = sum(mm["town_walk"].values()) / len(mm["town_walk"])
        name = "Current" if k < 0 else f"{k + 1}"
        L.append(f"| {name} | ${sc:,.0f}k | {w} | {tw:.1f} | {mm['truck_km_yr']:,.0f} | {mm['truck_crossings']} / {mm['car_crossings']} "
                 f"| {mm['main_m']:,.0f} m "
                 f"| {mm['land_ha']:.0f} ha |")
    return chr(10).join(L)


def spec(p: dict, mods: list[Module], m: dict, proposals: list[tuple]) -> dict:
    """out/pass3/site.json for forge and the plan figure: each layout's module rectangles and routes."""
    lay = lambda ms, mm: {"modules": [{"name": n.name, "rect": list(n.rect), "rot": n.rot, "faces": n.faces} for n in ms], **mm["lines"],
                          "crossings": mm["truck_crossings"], "car_crossings": mm["car_crossings"], "truck_km_yr": mm["truck_km_yr"],
                          "costs_usd_yr": costs(p, mm)}
    return {"source": "brownfield site (D12): the modular site plan", "hall": list(HALL), "cap": list(cap_rect(p)),
            "gate": [p["site.gate.x"], p["site.gate.y"]], "town": [p["site.town.x"], p["site.town.y"]],
            "standoff_m": p["site.standoff_m"], "setback_m": p["village.site.home_setback_m"],
            "current": {"score": score(p, m), **lay(mods, m)},
            "proposals": [{"score": sc, "is_current": same(ms, mods), **lay(ms, mm)} for sc, mm, ms in proposals]}
