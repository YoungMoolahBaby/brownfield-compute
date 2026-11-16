"""Pass 3e: the neighbourhood at the campus edge (D11).

Townhouses over their own two-car garages, set back from the data hall so that night noise from the
roof's coolers stays under the guideline at their windows; between them and the garden, the square
(the food hall and its market-garden house, the community center with its courts, rink, gym and
makerspace); heated grass fields on the capped ash site. The model:

- Heat: each townhouse variant's envelope, through pass 3's `house.heat` (walls, windows, doors,
  roof, air), plus the floor over the garage and the garage itself, both kept warm off the loop.
- Noise: the roof's coolers at each floor's windows (`garden.rooftop_noise` at the window height).
- Walks: from every door to the square, the food hall, the community center, the fields and the
  garden, along the street grid.
- Heat by month, money, growth: once the research inputs are in (params/village.yaml).

Frame as forge `garden`: metres; x east, y south (the town), the hall's south face at y = -3.
"""

from __future__ import annotations

import numpy as np

from . import garden, house

HALL_FACE_Y = -3.0
VARIANTS = ("gap", "narrow", "twin")  # detached with a ~3 m gap; detached with ~1 m; attached on twin walls


def townhouse_env(p: dict, variant: str, end: bool = False) -> dict:
    """The heated part of a townhouse (the storeys over the garage) in `house.ua`'s shape. Side walls
    lose heat on detached houses and on the ends of a twin-wall row; between twin walls they don't
    (each wall faces its neighbour's across an air gap: counted as no loss)."""
    t = "village.townhouse."
    w, d = p[t + "width_" + variant], p[t + "depth_m"]
    n, h = int(p[t + "storeys"]), p[t + "storey_m"]
    floor = w * d * n
    front_back = 2 * w * h * n
    sides = 2 * d * h * n if variant != "twin" or end else 0.0
    glaze = p[t + "glazing_front_back"] * front_back + (p[t + "glazing_sides"] * sides if variant == "gap" else 0.0)
    door = p[t + "door_m2"]
    return {"floor_m2": floor, "interior_volume_m3": floor * (h - 0.3), "wall_net_m2": front_back + sides - glaze - door,
            "glazed_m2": glaze, "door_m2": door, "ceiling_m2": w * d, "slab_perimeter_m": 0.0,
            "garage_m2": w * d, "width_m": w, "depth_m": d}


def townhouse_heat(env: dict, temp: np.ndarray, p: dict) -> dict:
    """The house's heat (pass 3's `house.heat`), plus the floor over the garage and the garage, held
    at its own set point (a workshop you can stand in all winter), off the loop."""
    t, e = "village.townhouse.", "pass3.envelope."
    h = house.heat(env, temp, p)
    garage_c = p[t + "garage_c"]
    over = p[t + "garage_floor_u"] * house.BTU_FT2 * env["garage_m2"] * (p["pass3.loads.indoor_c"] - garage_c)  # W, house to garage
    perim = 2 * (env["width_m"] + env["depth_m"])
    walls = perim * p[t + "garage_h_m"] - p[t + "garage_door_m2"]
    garage_ua = (p[e + "wall_u"] * house.BTU_FT2 * walls + p[t + "garage_door_u_si"] * p[t + "garage_door_m2"]
                 + p[e + "slab_f"] * house.BTU_FT * perim)
    # The garage loses through its own walls, door and slab edge; the floor above gives it `over`.
    garage_w = np.clip(garage_ua * np.clip(garage_c - temp, 0.0, None) - over, 0.0, None)
    space = h["space_mwh"] + over * 8760 / 1e6
    design_garage_kw = max(garage_ua * (garage_c - p["pass3.loads.design_c"]) - over, 0.0) / 1e3
    return dict(h, floor_over_garage_w=over, garage_ua_w_k=garage_ua, garage_mwh=garage_w.sum() / 1e6,
                house_mwh=space, total_mwh=space + garage_w.sum() / 1e6 + h["hot_water_mwh"],
                design_kw=h["design_kw"] + over / 1e3 + design_garage_kw)


def noise_by_floor(p: dict, distance_m: float, fan_cut_db: float) -> list[tuple[float, float]]:
    """Night level (dB(A)) at a home `distance_m` from the hall's face, at each floor's windows."""
    t = "village.townhouse."
    heights = [1.5] + [p[t + "garage_h_m"] + (k + 0.5) * p[t + "storey_m"] for k in range(int(p[t + "storeys"]) + 1)]
    return [(h, float(garden.rooftop_noise(p, fan_cut_db=fan_cut_db, distances=[distance_m], h_r=h)["levels"][0]))
            for h in heights]


def lots(p: dict, variant: str) -> list[tuple[float, float]]:
    """Phase 1's lot centres: east-west streets south of the setback line, lots both sides, either side
    of a public spine street that runs from the town (south) straight to the square, so townspeople
    reach the square through the neighbourhood, not round it (no gates, no private roads)."""
    t, s = "village.townhouse.", "village.site."
    n = int(p[s + "phase1_homes"])
    lot_w = p[t + "width_" + variant] + p[t + "gap_" + variant]
    half = (p[s + "street_m"] - p[s + "spine_w_m"]) / 2
    per_half = int(half // lot_w)
    y0 = HALL_FACE_Y + p[s + "home_setback_m"] + p[s + "lot_depth_m"] / 2
    xc = p[s + "square_x"]
    out = []
    street = 0
    while len(out) < n:
        y_street = y0 + street * (2 * p[s + "lot_depth_m"] + p[s + "street_w_m"])
        for side in (0, 1):
            y = y_street + side * (p[s + "lot_depth_m"] + p[s + "street_w_m"])
            for k in range(per_half):
                for sign in (-1, 1):
                    if len(out) < n:
                        out.append((xc + sign * (p[s + "spine_w_m"] / 2 + (k + 0.5) * lot_w), y))
        street += 1
    return out


def walks(p: dict, homes: list[tuple[float, float]]) -> dict[str, np.ndarray]:
    """Minutes on foot from each door to each place, along the street grid (x then y)."""
    s = "village.site."
    places = {"the square": (p[s + "square_x"], p[s + "square_y"]), "the winter garden": (p[s + "garden_x"], p[s + "garden_y"]),
              "the fields": (p[s + "fields_x"], p[s + "fields_y"])}
    speed = p["village.walk.speed_m_s"] * 60.0
    return {k: np.array([(abs(x - px) + abs(y - py)) / speed for x, y in homes]) for k, (px, py) in places.items()}
