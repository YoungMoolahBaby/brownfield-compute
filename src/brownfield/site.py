"""The site plan as modules (D12): every piece a rectangle with a size (from its own model), a position
and a rotation; rules every layout must pass; scores; and an optimizer that proposes layouts for Jon
to edit (`brownfield site`).

Security is designed in, in rings (D12): the community outside (natural surveillance), a landscape
stand-off band round the data hall that no public vehicle enters (pedestrian places such as the
square and the winter garden may sit in it), and trucks screened at a remote delivery building.
Only published principles and distances are used: this repo is public.

Distances in the search are along the street grid (Manhattan); the drawings route on a 5 m grid.
Frame as forge `garden`: metres; x east, y south (toward the town); the hall's south face at y = -3.
"""

from __future__ import annotations

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
        ("winter garden", "garden", 66.6, 37.6, {}),
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


def cap_rect(p: dict) -> tuple:
    s = "site.cap."
    return (p[s + "x0"], p[s + "x1"], p[s + "y0"], p[s + "y1"])


def by(mods: list[Module], name: str) -> Module:
    return next(m for m in mods if m.name == name)


def rules(p: dict, mods: list[Module]) -> list[str]:
    """What a layout breaks (empty: it passes)."""
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
        if m.name == "neighbourhood":
            pass
        if m.vehicles and gap(m.rect, hall) < p[s + "standoff_m"]:
            bad.append(f"{m.name} (public vehicles) inside the stand-off band ({gap(m.rect, hall):.0f} m < {p[s + 'standoff_m']:g} m)")
        if not m.on_cap_ok and m.name != "data hall" and overlaps(m.rect, cap_rect(p)):
            bad.append(f"{m.name} built on the ash cap")
        x0, x1, y0, y1 = m.rect
        if x0 < p[s + "bounds.x0"] or x1 > p[s + "bounds.x1"] or y0 < p[s + "bounds.y0"] or y1 > p[s + "bounds.y1"]:
            bad.append(f"{m.name} off the site")
    mm = metrics(p, mods, 0.0)
    if mm["stop_m"] > p[s + "walk_stop_m"]:
        bad.append(f"a door {mm['stop_m']:.0f} m from the nearest shuttle stop (> {p[s + 'walk_stop_m']:g} m)")
    return bad


def metrics(p: dict, mods: list[Module], food_t: float) -> dict:
    """The scores of a layout, along the street grid."""
    s, w = "site.", p["village.walking.speed_hcm_sidewalk"] * 60.0
    homes = by(mods, "neighbourhood").rect
    near_home = (centre(homes)[0], homes[2])  # the neighbourhood's edge nearest the hall
    far_home = (centre(homes)[0], homes[3])
    gh = by(mods, "greenhouse").rect
    food_door = (gh[0] + 40.0, gh[3])  # the head house on the greenhouse's town-side corner (forge food.rs)
    places = {"the square": centre(by(mods, "square").rect), "the food court": food_door,
              "the community center": centre(by(mods, "community center").rect), "the field": centre(by(mods, "field and loop").rect),
              "the winter garden": centre(by(mods, "winter garden").rect)}
    walks = {k: (manhattan(centre(homes), v) / w, manhattan(far_home, v) / w) for k, v in places.items()}
    gate = (p[s + "gate.x"], p[s + "gate.y"])
    dock = centre(by(mods, "remote delivery building").rect)
    hall_dock = (HALL[1], centre(HALL)[1])  # the hall's service side (east)
    truck_m = manhattan(gate, dock) + 0.5 * (manhattan(dock, food_door) + manhattan(dock, hall_dock))
    trips = food_t / p[s + "truck_t"] + p[s + "hall_trucks_yr"]
    # Truck routes that cross the walks between the homes and the places people walk to.
    walk_box = (min(near_home[0], *(v[0] for v in places.values())), max(near_home[0], *(v[0] for v in places.values())),
                min(near_home[1], *(v[1] for v in places.values())), max(near_home[1], *(v[1] for v in places.values())))
    crossings = sum(1 for a, b in [(gate, dock), (dock, food_door), (dock, hall_dock)] if _seg_hits(a, b, walk_box))
    src = (centre(HALL)[0], HALL[3])
    heated = ["winter garden", "greenhouse", "community center", "field and loop", "neighbourhood"]
    main_m = sum(manhattan(src, centre(by(mods, n).rect)) for n in heated)
    hub = centre(by(mods, "mobility hub").rect)
    parking_walk = {k: manhattan(hub, v) / w for k, v in [("center and rink", places["the community center"]),
                                                         ("field", places["the field"]), ("food court", food_door)]}
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
    return {"walks": walks, "truck_km_yr": truck_m * trips / 1000.0, "truck_crossings": crossings, "main_m": main_m,
            "main_usd": main_m * p["pass3.block.main_usd_m"], "parking_walk": parking_walk,
            "land_ha": (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e4, "stop_m": stop_m, "heated_walk_m2": walk_m2,
            "homes_from_hall_m": gap(homes, HALL)}


def _seg_hits(a: tuple, b: tuple, box: tuple) -> bool:
    """Whether the street-grid route a -> b (x first, then y) passes through the box."""
    corner = (b[0], a[1])
    for p0, p1 in [(a, corner), (corner, b)]:
        lo, hi = (min(p0[0], p1[0]), max(p0[0], p1[0])), (min(p0[1], p1[1]), max(p0[1], p1[1]))
        if lo[0] <= box[1] and hi[0] >= box[0] and lo[1] <= box[3] and hi[1] >= box[2]:
            return True
    return False


def score(p: dict, m: dict) -> float:
    """Lower is better: the weighted sum of the layout's costs (weights are Jon's priorities)."""
    s = "site.weights."
    walk = np.mean([v[0] for v in m["walks"].values()])
    park = np.mean(list(m["parking_walk"].values()))
    return (p[s + "walk_min"] * walk + p[s + "parking_min"] * park + p[s + "truck_km"] * m["truck_km_yr"] / 1000.0
            + p[s + "crossing"] * m["truck_crossings"] + p[s + "main_km"] * m["main_m"] / 1000.0 + p[s + "land_ha"] * m["land_ha"] / 100.0)


def optimise(p: dict, mods: list[Module], food_t: float, n_starts: int = 16, steps: int = 2500, seed: int = 3) -> list[tuple]:
    """Simulated annealing from the current layout and from random legal arrangements, moving one
    movable module at a time on a 10 m grid (and turning it 90 degrees now and then), keeping only
    layouts that pass every rule. Returns the best few (score, metrics, modules)."""
    rng = np.random.default_rng(seed)
    s = "site.bounds."
    movable = [i for i, m in enumerate(mods) if m.movable]
    found = []
    for start in range(n_starts):
        cur = list(mods)
        if start:  # scatter the movable modules to a random legal arrangement
            for _ in range(3000):
                trial = list(cur)
                for i in movable:
                    trial[i] = replace(trial[i], x=float(rng.integers(p[s + "x0"] // 10, p[s + "x1"] // 10) * 10),
                                       y=float(rng.integers(p[s + "y0"] // 10, p[s + "y1"] // 10) * 10), rot=int(rng.choice([0, 90])))
                if not rules(p, trial):
                    cur = trial
                    break
            else:
                continue
        if rules(p, cur):
            continue
        cur_sc = score(p, metrics(p, cur, food_t))
        best, best_sc = cur, cur_sc
        for k in range(steps):
            temp = 2.0 * (1 - k / steps) + 1e-3
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
        found.append((best_sc, metrics(p, best, food_t), best))
    found.sort(key=lambda t: t[0])
    out, seen = [], set()
    for f in found:
        key = tuple((round(m.x, -1), round(m.y, -1), m.rot) for m in f[2])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out[:3]


def homes_rect(p: dict) -> tuple:
    from . import village

    homes = village.lots(p, "gap")
    xs, ys = [x for x, _ in homes], [y for _, y in homes]
    lot_w = p["village.townhouse.width_gap"] + p["village.townhouse.gap_gap"]
    return (min(xs) - lot_w, max(xs) + lot_w, min(ys) - 12.0, max(ys) + 12.0)


def report(p: dict, mods: list[Module], m: dict, proposals: list[tuple]) -> str:
    L = ["**The current layout** (params/site.yaml)", ""]
    bad = rules(p, mods)
    L.append("Rules: " + ("all pass." if not bad else "; ".join(bad)))
    L += ["", "| Walk from the homes to | Average | Furthest door |", "|---|---|---|"]
    L += [f"| {k} | {v[0]:.1f} min | {v[1]:.1f} min |" for k, v in m["walks"].items()]
    L += ["", f"- Trucks: {m['truck_km_yr']:,.0f} truck-km a year from the site entrance through the remote delivery building; "
          f"{m['truck_crossings']} route(s) crossing the walks between the homes and the places they walk to.",
          f"- Warm main from the hall to the heated modules: {m['main_m']:,.0f} m (about ${m['main_usd'] / 1e6:,.1f}M at pass 3's cost).",
          "- Walk from the mobility hub: " + ", ".join(f"{k} {v:.1f} min" for k, v in m["parking_walk"].items()) + "; "
          f"the furthest door is {m['stop_m']:.0f} m from a shuttle stop.",
          f"- Heated walks (snow-free all winter on the warm water): about {m['heated_walk_m2']:,.0f} m2.",
          f"- Homes {m['homes_from_hall_m']:.0f} m from the hall (noise setback {p['village.site.home_setback_m']:g} m); "
          f"public vehicles kept {p['site.standoff_m']:g} m off it.",
          f"- The layout spans {m['land_ha']:.0f} ha. Score {score(p, m):.2f} (lower is better; weights are placeholders for Jon's priorities)."]
    L += ["", "**Proposals** (simulated annealing; every one passes every rule)", "",
          "| | Score | Walk to the square / food court / center / field / garden (min) | Truck-km a year | Crossings | Warm main | Land |",
          "|---|---|---|---|---|---|---|"]
    for k, (sc, mm, ms) in enumerate(proposals):
        w = " / ".join(f"{v[0]:.1f}" for v in mm["walks"].values())
        L.append(f"| {k + 1} | {sc:.2f} | {w} | {mm['truck_km_yr']:,.0f} | {mm['truck_crossings']} | {mm['main_m']:,.0f} m | {mm['land_ha']:.0f} ha |")
    return chr(10).join(L)


def spec(mods: list[Module], proposals: list[tuple]) -> dict:
    """out/pass3/site.json for forge: each module's rectangle in the current layout and the proposals."""
    lay = lambda ms: [{"name": m.name, "rect": list(m.rect), "rot": m.rot} for m in ms]
    return {"source": "brownfield site (D12): the modular site plan", "current": lay(mods),
            "proposals": [{"score": sc, "modules": lay(ms)} for sc, _, ms in proposals]}
