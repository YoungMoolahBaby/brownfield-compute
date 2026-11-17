"""The site plan as modules (D12): every piece a rectangle with a size (from its own model), a position
and a rotation; rules every layout must pass; scores; and an optimizer that proposes layouts for Jon
to edit (`brownfield site`).

Security is designed in, in rings (D12): the community outside (natural surveillance), a landscape
stand-off band round the data hall that no public vehicle enters (pedestrian places such as the
square and the winter garden may sit in it), and trucks screened at a remote delivery building.
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
ATTACHED = {frozenset(("data hall", "winter garden")), frozenset(("data hall", "front"))}  # built against each other


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


def modules(p: dict, greenhouse_ha: float, homes_rect: tuple) -> list[Module]:
    """The modules, sized from their own models, placed from params/site.yaml."""
    s = "site."
    side = math.sqrt(greenhouse_ha * 1e4)
    hw, hd = homes_rect[1] - homes_rect[0], homes_rect[3] - homes_rect[2]
    f = "village.fields."
    pos = lambda k: (p[s + k + ".x"], p[s + k + ".y"], int(p[s + k + ".rot"]))
    # One mobility hub (D14): a shared car park at a share of the code minimums for the center and
    # rink, the field and the food court, plus the shuttle stop, bikes and charging.
    hub_m2 = p[s + "car_share"] * (p[s + "park_center_m2"] + p[s + "park_field_m2"] + p[s + "park_food_m2"]) + p[s + "hub_extra_m2"]
    hub_side = hub_m2 ** 0.5
    # The community center and its rink under one roof, 90 m wide (forge `garden` draws the same).
    center_m2 = (p["village.amenities.center_ft2"] + p["village.rink.building_area_single_sheet"]) / 10.7639
    out = [Module("data hall", HALL[1] - HALL[0], HALL[3] - HALL[2], *centre(HALL), movable=False)]
    for name, key, w, d, kw in [
        ("winter garden", "garden", 66.6, 37.6, {"movable": False}),  # built against the hall (or the center: Jon to choose)
        ("greenhouse", "greenhouse", side, side + 20.0, {}),  # the head house and food court on its town side
        ("community center", "center", 90.0, center_m2 / 90.0, {}),
        ("square", "square", 60.0, 60.0, {}),
        ("field and loop", "field", p[f + "pitch_width_soccer"] + 46.0, p[f + "pitch_length_soccer"] + 46.0, {"on_cap_ok": True}),
        ("neighbourhood", "homes", hw, hd, {"sleeps": True}),
        ("mobility hub", "hub", hub_side, hub_side, {"vehicles": True}),
        ("remote delivery building", "delivery", 40.0, 30.0, {"vehicles": True}),
    ]:
        x, y, rot = pos(key)
        out.append(Module(name, w, d, x, y, rot, **kw))
    return out


PUBLIC = ["square", "community center", "field and loop", "mobility hub"]
VIEW_BLOCKERS = ["greenhouse", "community center", "remote delivery building"]


def food_door(gh: tuple) -> tuple[float, float]:
    """The food court's door: the head house on the greenhouse's town-side corner (forge food.rs)."""
    return (gh[0] + 40.0, gh[3])


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
    # The homes look out on the winter garden (Jon: homes round the garden, "having that as a view").
    for n in VIEW_BLOCKERS:
        if blocks_view(by(mods, "winter garden").rect, by(mods, "neighbourhood").rect, by(mods, n).rect):
            bad.append(f"{n} blocks the homes' view of the winter garden")
    mm = metrics(p, mods, 0.0)
    if mm["stop_m"] > p[s + "walk_stop_m"]:
        bad.append(f"a door {mm['stop_m']:.0f} m from the nearest shuttle stop (> {p[s + 'walk_stop_m']:g} m)")
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
    for m in mods:
        if m.sleeps and gap(m.rect, hall) < p["village.site.home_setback_m"]:
            bad.append(f"{m.name} inside the noise setback ({gap(m.rect, hall):.0f} m < {p['village.site.home_setback_m']:g} m)")
        if m.name == "neighbourhood" and m.rot % 180:
            bad.append(f"{m.name} turned: its rows must run east-west so every house has a wall facing south (DOE)")
        if m.name == "neighbourhood" and m.rect[2] < hall[3]:
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
        if m.name == "greenhouse" and food_door(m.rect)[1] < hall[2]:
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
    for _ in range(tries):
        cur, placed = list(mods), [i for i, m in enumerate(mods) if not m.movable]
        for i in movable:
            for _ in range(300):
                if rng.random() < 0.5:
                    near = cur[int(rng.choice(placed))]
                    x, y = near.x + rng.uniform(-500, 500), near.y + rng.uniform(-500, 500)
                else:
                    x, y = rng.uniform(p[s + "x0"], p[s + "x1"]), rng.uniform(p[s + "y0"], p[s + "y1"])
                cand = replace(mods[i], x=float(round(x, -1)), y=float(round(y, -1)), rot=int(rng.choice([0, 90])))
                if not module_rules(p, [cur[j] for j in placed] + [cand]):
                    cur[i] = cand
                    placed.append(i)
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
    homes = by(mods, "neighbourhood").rect
    near_home = (centre(homes)[0], homes[2])  # the neighbourhood's edge nearest the hall
    far_home = (centre(homes)[0], homes[3])
    gh = by(mods, "greenhouse").rect
    fd = food_door(gh)
    # Walks end at a building's nearest door (the field's and the garden's nearest edge), the square's
    # middle (its shuttle stop) and the food court's door.
    cen, fld, gdn = by(mods, "community center").rect, by(mods, "field and loop").rect, by(mods, "winter garden").rect
    hc = centre(homes)
    places = {"the square": centre(by(mods, "square").rect), "the food court": fd, "the community center": door(cen, hc, 0.0),
              "the field": door(fld, hc, 0.0), "the winter garden": door(gdn, hc, 0.0)}
    walks = {k: (manhattan(centre(homes), v) / w, manhattan(far_home, v) / w) for k, v in places.items()}
    gate = (p[s + "gate.x"], p[s + "gate.y"])
    dock = centre(by(mods, "remote delivery building").rect)
    # Loading docks on a side away from the town (the town side holds the food court and the garden):
    # the side nearest the truck's way in. The hall's trucks are screened at the delivery building first;
    # the produce trucks go from the entrance straight to the greenhouse.
    gh_dock = min(docks(gh), key=lambda q: manhattan(q, gate))
    hall_dock = docks(HALL)[2]  # the hall's trucks come in on its service side, behind it
    food_trips, hall_trips = food_t / p[s + "truck_t"], p[s + "hall_trucks_yr"]
    truck_km = (food_trips * manhattan(gate, gh_dock) + hall_trips * (manhattan(gate, dock) + manhattan(dock, hall_dock))) / 1000.0
    town = (p[s + "town.x"], p[s + "town.y"])
    hub = centre(by(mods, "mobility hub").rect)
    truck_legs = [(gate, gh_dock), (gate, dock), (dock, hall_dock)]
    car_legs = [(gate, hub), (town, hub)]  # visitors' cars and the shuttle to the mobility hub
    # Walks a road cuts across whichever way round it goes: each leg runs x-then-y or y-then-x,
    # whichever cuts fewer; a walk is cut if it is cut whichever way round it goes too.
    walk_legs = [(near_home, v) for v in places.values()]
    cuts = lambda legs: sum(min(sum(1 for wa, wb in walk_legs if all(_paths_cross(lp, wp) for wp in _ls(wa, wb))) for lp in _ls(a, b))
                            for a, b in legs)
    crossings, car_crossings = cuts(truck_legs), cuts(car_legs)
    town_walk = {k: manhattan(town, v) / w for k, v in [("the square", places["the square"]), ("the food court", fd),
                                                         ("the community center", door(cen, town, 0.0)), ("the field", door(fld, town, 0.0))]}
    src = (centre(HALL)[0], HALL[3])
    heated = ["winter garden", "greenhouse", "community center", "field and loop", "neighbourhood"]
    main_m = sum(manhattan(src, centre(by(mods, n).rect)) for n in heated)
    # From the hub's middle (the average parking space) to the door.
    parking_walk = {k: manhattan(hub, v) / w for k, v in [("center and rink", door(cen, hub, 0.0)),
                                                         ("field", door(fld, hub, 0.0)), ("food court", fd)]}
    # Shuttle stops: the hub, the square, and the spine's far end where the town begins.
    stops = [hub, places["the square"], (centre(homes)[0], homes[3])]
    corners = [(homes[0], homes[2]), (homes[1], homes[2]), (homes[0], homes[3]), (homes[1], homes[3])]
    stop_m = max(min(manhattan(c, st) for st in stops) for c in corners)
    # Heated walks (D14): the spine, a walk on each side of every green, the square, and the walk to the hub.
    s2 = "village.site."
    rows = max(1, round((homes[3] - homes[2]) / (2 * p[s2 + "lot_depth_m"] + p[s2 + "street_w_m"] + p[s2 + "green_w_m"])))
    walk_m2 = ((homes[3] - homes[2]) * 6.0 + rows * 2 * (homes[1] - homes[0]) * 2.4 + 60.0 * 60.0
               + manhattan(hub, places["the square"]) * 3.0)
    xs = [v for m in mods for v in m.rect[:2]]
    ys = [v for m in mods for v in m.rect[2:]]
    out = {"walks": walks, "truck_km_yr": truck_km, "truck_crossings": crossings, "car_crossings": car_crossings,
           "truck_legs": truck_legs, "town_walk": town_walk,
           "main_m": main_m, "main_usd": main_m * p["pass3.block.main_usd_m"], "parking_walk": parking_walk,
           "land_ha": (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e4, "stop_m": stop_m, "heated_walk_m2": walk_m2,
           "homes_from_hall_m": gap(homes, HALL), "routed": False}
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
    homes, gh, cen = rect("neighbourhood"), rect("greenhouse"), rect("community center")
    fd = (food_door(gh)[0], gh[3] + 1.5 * g.cell)
    hub = centre(rect("mobility hub"))
    walk_block = g.mask([HALL, gh, cen, rect("remote delivery building")])
    ones = np.ones(g.X.shape)
    places = [centre(rect("square")), fd, door(cen, centre(homes), 1.5 * g.cell), centre(rect("field and loop")),
              centre(rect("winter garden"))]
    walks = g.paths(walk_block, ones, centre(homes), places)
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
    gh_dock = door(gh, min(docks(gh), key=lambda q: manhattan(q, gate)), road + 1.5 * g.cell)
    hall_dock = door(HALL, docks(HALL)[2], road + 1.5 * g.cell)  # the hall's service side, behind it
    public = blocked | g.mask([HALL], p[s + "standoff_m"])  # unscreened vehicles stay out of the stand-off band
    # Trucks stay on the service side: no truck road near the homes or the public places.
    away = g.mask([homes, cen, rect("square"), rect("field and loop")], p[s + "truck_clear_m"])
    (produce,) = g.paths(public | away, mult(truck_detour_m(p, food_trips)), gate, [gh_dock])
    (to_dl,) = g.paths(blocked | away, mult(truck_detour_m(p, hall_trips)), gate, [dl_door])
    (to_hall,) = g.paths(blocked | away, mult(truck_detour_m(p, hall_trips)), dl_door, [hall_dock])
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
    residents = p["village.site.phase1_homes"] * p[s + "persons_per_home"]
    walk = sum(residents * p[s + k] * 52.0 * 2.0 * m["walks"][place][0] for place, k in PLACE_VISITS.items()) * per_min
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


def homes_rect(p: dict) -> tuple:
    from . import village

    homes = village.lots(p, "gap")
    xs, ys = [x for x, _ in homes], [y for _, y in homes]
    lot_w = p["village.townhouse.width_gap"] + p["village.townhouse.gap_gap"]
    return (min(xs) - lot_w, max(xs) + lot_w, min(ys) - 12.0, max(ys) + 12.0)


def same(a: list[Module], b: list[Module]) -> bool:
    return all(round(m.x, -1) == round(n.x, -1) and round(m.y, -1) == round(n.y, -1) and m.rot == n.rot for m, n in zip(a, b))


def report(p: dict, mods: list[Module], m: dict, proposals: list[tuple]) -> str:
    L = ["**The current layout** (params/site.yaml)", ""]
    bad = rules(p, mods)
    L.append("Rules: " + ("all pass." if not bad else "; ".join(bad)))
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
          "- The winter garden stays against the hall's face (its warm water comes in at the hearth tower) until Jon chooses "
          "whether it moves to the community center."]
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
    lay = lambda ms, mm: {"modules": [{"name": n.name, "rect": list(n.rect), "rot": n.rot} for n in ms], **mm["lines"],
                          "crossings": mm["truck_crossings"], "car_crossings": mm["car_crossings"], "truck_km_yr": mm["truck_km_yr"],
                          "costs_usd_yr": costs(p, mm)}
    return {"source": "brownfield site (D12): the modular site plan", "hall": list(HALL), "cap": list(cap_rect(p)),
            "gate": [p["site.gate.x"], p["site.gate.y"]], "town": [p["site.town.x"], p["site.town.y"]],
            "standoff_m": p["site.standoff_m"], "setback_m": p["village.site.home_setback_m"],
            "current": {"score": score(p, m), **lay(mods, m)},
            "proposals": [{"score": sc, "is_current": same(ms, mods), **lay(ms, mm)} for sc, mm, ms in proposals]}
