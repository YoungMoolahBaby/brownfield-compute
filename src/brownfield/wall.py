"""Pass 2d: the wall in front of the coolers (D7), against the earth berm pass 2 assumed.

Acoustics, by ISO 9613-2's screening method (section 7.4) at 500 Hz, the band of the A-weighted
single-band method `noise.py` already uses:

    D_z   = 10 lg[3 + (C2 / lambda) C3 z K_met]                       eq. (14), capped 20 / 25 dB
    C3    = 1 (one edge),  [1 + (5 lambda / e)^2] / [1/3 + (5 lambda / e)^2] (two edges, e apart)
    z     = [(d_ss + e + d_sr)^2 + a^2]^(1/2) - d                     eqs. (16), (17)
    K_met = exp[-(1/2000) (d_ss d_sr d / 2z)^(1/2)]                   eq. (18)
    A_bar = D_z - A_gr  (>= 0) over the top edge                        eq. (12)

so a screen replaces the ground effect rather than adding to it: the excess attenuation on a
screened path is max(D_z, A_gr). Pass 2 added a flat 10 dB on top of the ground term.

The yard: dry coolers in a W x D rectangle, their fans (the source) at height h_s; a home at
distance r from the yard's edge, ear at h_r. The yard's sound power is spread evenly over a grid
of points, each path screened by the profile between it and the home: a thin wall (two edges a
wall's thickness apart) or a berm (its crest's two edges). The diffracting edges are the ones on
the upper convex hull of source, profile and receiver (a string pulled tight over the screen).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import noise

C_SOUND = 340.0  # m/s
F_BAND = 500.0  # Hz, the A-weighted method's band (ISO 9613-2 section 7.1)


def wavelength(f: float = F_BAND) -> float:
    return C_SOUND / f


def d_z(z: float, d_ss: float, d_sr: float, d: float, e: float = 0.0, c2: float = 20.0,
        k_met: bool = True, f: float = F_BAND) -> float:
    """ISO 9613-2 eq. (14): screening by diffraction over a top edge (one edge if e = 0, two edges
    e apart otherwise), capped at 20 dB (one edge) or 25 dB (two)."""
    if z <= 0.0:
        return 0.0
    lam = wavelength(f)
    c3 = 1.0 if e <= 0.0 else (1 + (5 * lam / e) ** 2) / (1 / 3 + (5 * lam / e) ** 2)
    km = float(np.exp(-np.sqrt(d_ss * d_sr * d / (2 * z)) / 2000.0)) if k_met else 1.0
    return min(10.0 * np.log10(3.0 + (c2 / lam) * c3 * z * km), 20.0 if e <= 0.0 else 25.0)


def kurze_anderson(n: float) -> float:
    """Kurze and Anderson's (1971) closed-form fit to Maekawa's measured barrier attenuation for a
    point source, by Fresnel number N = 2z / lambda: 5 + 20 lg[sqrt(2 pi N) / tanh sqrt(2 pi N)]."""
    s = np.sqrt(2 * np.pi * n)
    return float(5.0 + 20.0 * np.log10(s / np.tanh(s)))


def upper_hull(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Upper convex hull of points sorted by x (Andrew's monotone chain): the path a string
    pulled tight from the first point to the last takes over the others."""
    hull: list[tuple[float, float]] = []
    for p in sorted(pts):
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) >= 0:  # not a right turn
                hull.pop()
            else:
                break
        hull.append(p)
    return hull


def path(src: tuple[float, float], rcv: tuple[float, float], edges: list[tuple[float, float]]):
    """(d_ss, e, d_sr, profile length) of the tight path from src over edges to rcv, in the
    vertical plane across the screen; d_ss = d_sr = 0 when the line of sight is clear."""
    hull = upper_hull([src, *[q for q in edges if src[0] < q[0] < rcv[0]], rcv])
    seg = [float(np.hypot(b[0] - a[0], b[1] - a[1])) for a, b in zip(hull, hull[1:])]
    if len(hull) == 2:
        return 0.0, 0.0, 0.0, seg[0]
    return seg[0], sum(seg[1:-1]), seg[-1], sum(seg)


@dataclass(frozen=True)
class Screen:
    """A screen's profile: its diffracting edges (x from the yard's edge, height), its footprint
    width (m) and what it is."""
    name: str
    edges: tuple[tuple[float, float], ...]
    footprint_m: float


def wall_screen(gap: float, height: float, thick: float) -> Screen:
    return Screen("wall", ((gap, height), (gap + thick, height)), thick)


def berm_screen(gap: float, height: float, slope: float, crest: float) -> Screen:
    """A berm whose inner toe is `gap` from the yard, sides at 1:`slope` (rise:run), `crest` wide."""
    x0 = gap + slope * height
    return Screen("berm", ((x0, height), (x0 + crest, height)), 2 * slope * height + crest)


def open_ground() -> Screen:
    return Screen("open ground", (), 0.0)


def yard_grid(width: float, depth: float, nx: int = 12, ny: int = 25) -> np.ndarray:
    """Source points (x <= 0 into the yard, y along it), cell-centred."""
    xs = -(np.arange(nx) + 0.5) * depth / nx
    ys = (np.arange(ny) + 0.5) * width / ny - width / 2
    return np.array([(x, y) for x in xs for y in ys])


def level(lw: float, r: float, screen: Screen, width: float, depth: float, h_s: float, h_r: float,
          p: dict, c2: float = 20.0, k_met: bool = True, grid=None, f: float = F_BAND) -> float:
    """Sound pressure level (dB(A)) at a home r metres from the yard's edge, opposite its middle,
    from a yard of sound power lw spread evenly over its plan, screened by `screen`."""
    pts = yard_grid(width, depth) if grid is None else grid
    lw_pt = lw - 10.0 * np.log10(len(pts))
    alpha, h_m = p["pass2.noise.alpha_db_km"], p["pass2.noise.h_m"]
    total = 0.0
    for x, y in pts:
        d = float(np.sqrt((r - x) ** 2 + y ** 2 + (h_r - h_s) ** 2))
        a_gr = float(noise.a_gr(np.array(d), h_m))
        d_ss, e, d_sr, prof = path((x, h_s), (r, h_r), list(screen.edges))
        excess = a_gr
        if d_ss > 0.0:
            z = float(np.sqrt(prof ** 2 + y ** 2)) - d
            excess = max(d_z(z, d_ss, d_sr, d, e, c2, k_met, f), a_gr)
        lp = lw_pt - float(noise.a_div(np.array(d))) - alpha * d / 1000.0 - excess
        total += 10.0 ** (lp / 10.0)
    return 10.0 * np.log10(total)


def insertion_loss(r: float, screen: Screen, width: float, depth: float, h_s: float, h_r: float, p: dict, **kw) -> float:
    """How much quieter (dB) the home is with the screen than over open ground."""
    return (level(100.0, r, open_ground(), width, depth, h_s, h_r, p, **kw)
            - level(100.0, r, screen, width, depth, h_s, h_r, p, **kw))


def distance_for(target: float, lw: float, screen: Screen, width: float, depth: float, h_s: float,
                 h_r: float, p: dict) -> float:
    """Distance from the yard's edge (m) beyond which a home hears less than target dB(A)."""
    lo, hi = max(screen.edges[-1][0] + 1.0, 2.0) if screen.edges else 2.0, 20_000.0
    if level(lw, lo, screen, width, depth, h_s, h_r, p) <= target:
        return lo
    for _ in range(40):
        mid = (lo * hi) ** 0.5
        if level(lw, mid, screen, width, depth, h_s, h_r, p) > target:
            lo = mid
        else:
            hi = mid
    return hi


# ---------------------------------------------------------------------------------------------
# The yard: dry coolers in rows, at the maker's clearances; walls round it, between its courts
# and across its cells.

LAYOUTS = ("open", "berm", "perimeter", "courts", "cells")
NAMES = {"open": "no screen", "berm": "6 m earth berm round the yard", "perimeter": "6 m wall round the yard",
         "courts": "walls between every second row (courts)", "cells": "courts and cross walls (cells)"}


def _axis(n: int, size: float, gap: float, group: int, wall_gap: float, wall_t: float):
    """n units of `size` in a line, `gap` apart, with a wall after every `group` units (0: none)
    standing `wall_gap` clear of the units each side: (length, wall centres from the start)."""
    pos, walls = 0.0, []
    for i in range(n):
        pos += size
        if i == n - 1:
            break
        if group and (i + 1) % group == 0:
            walls.append(pos + wall_gap + wall_t / 2)
            pos += 2 * wall_gap + wall_t
        else:
            pos += gap
    return pos, walls


@dataclass(frozen=True)
class Yard:
    layout: str
    units: int
    rows: int
    per_row: int
    depth: float  # m across the rows (outer unit edge to outer unit edge)
    length: float  # m along the rows
    walls_across: tuple  # interior wall centres across the rows (court walls), from the near edge
    walls_along: tuple  # interior wall centres along the rows (cross walls)
    airflow: float  # m3/s at the design fan speed
    footprint: float  # m2 of units


def yard(p: dict, layout: str) -> Yard:
    y, d = "wall.yard.", "wall.design."
    k = p["pass2.noise.dry_oversize"]
    heat_kw = p["pass2.module.it_mw"] * 1.2 * 1000  # the heat pass 2 rejects at full IT load
    units = int(np.ceil(k * heat_kw / p[y + "unit_kw"]))
    rows = int(p[y + "rows"])
    per_row = int(np.ceil(units / rows))
    pier = p[d + "pier_d_in"] * 0.0254
    courts = int(p[d + "court_rows"]) if layout in ("courts", "cells") else 0
    cells = 2 if layout == "cells" else 0
    depth, wa = _axis(rows, p[y + "unit_w_m"], p[y + "side_by_side_m"], courts, p[y + "side_to_wall_m"], pier)
    length, wl = _axis(per_row, p[y + "unit_l_m"], p[y + "end_to_end_m"], cells, p[y + "end_to_wall_m"], pier)
    return Yard(layout, units, rows, per_row, depth, length, tuple(wa), tuple(wl),
                units * p[y + "unit_airflow_m3s"] / k, units * p[y + "unit_l_m"] * p[y + "unit_w_m"])


def well_velocity(p: dict, yd: Yard) -> float:
    """Downward air speed (m/s) into the tightest walled space: the whole yard inside its wall, or
    one court or cell (airflow over the open area left between the units)."""
    y = "wall.yard."
    per_unit = yd.airflow / yd.units
    if yd.layout in ("open", "berm", "perimeter"):
        area = (yd.depth + 2 * p[y + "side_to_wall_m"]) * (yd.length + 2 * p[y + "end_to_wall_m"])
        return yd.airflow / (area - yd.footprint)
    rows = int(p["wall.design.court_rows"])
    across = rows * p[y + "unit_w_m"] + (rows - 1) * p[y + "side_by_side_m"] + 2 * p[y + "side_to_wall_m"]
    n_along = 2 if yd.layout == "cells" else yd.per_row
    along = n_along * p[y + "unit_l_m"] + (n_along - 1) * p[y + "end_to_end_m"] + 2 * p[y + "end_to_wall_m"]
    n = rows * n_along
    return n * per_unit / (across * along - n * p[y + "unit_l_m"] * p[y + "unit_w_m"])


def wall_thick(p: dict) -> float:
    return (2 * p["wall.brick.unit_w_in"] + p["wall.brick.collar_in"]) * 0.0254


def screen_for(p: dict, yd: Yard, direction: str) -> tuple[Screen, float, float]:
    """The profile a home sees looking at the yard `across` its rows (off a long side) or `along`
    them (off an end), and the yard's depth and width that way."""
    d, y = "wall.design.", "wall.yard."
    across = direction == "across"
    depth, width = (yd.depth, yd.length) if across else (yd.length, yd.depth)
    interior = yd.walls_across if across else yd.walls_along
    gap = p[y + "side_to_wall_m"] if across else p[y + "end_to_wall_m"]
    hp, hc = p[d + "perimeter_h_m"], p[d + "court_h_m"]
    t = wall_thick(p)
    if yd.layout == "open":
        return open_ground(), depth, width
    if yd.layout == "berm":
        return berm_screen(gap, hp, p["wall.acoustics.berm_slope"], p["wall.acoustics.berm_crest_m"]), depth, width
    edges = [(gap, hp), (gap + t, hp)]
    for c in interior:  # centres measured from the near edge into the yard (x < 0)
        edges += [(-c - t / 2, hc), (-c + t / 2, hc)]
    return Screen(yd.layout, tuple(sorted(edges)), t), depth, width


def acoustics(p: dict, distances=(120.0, 300.0, 700.0)) -> list[dict]:
    lw = noise.module_lw("good neighbour", p["pass2.module.it_mw"] * 1.2, p)
    hs, hr = p["wall.yard.fan_h_m"], p["wall.acoustics.ear_h_m"]
    target = p["pass2.noise.target_night_db"]
    rows = []
    for layout in LAYOUTS:
        yd = yard(p, layout)
        for direction in ("across", "along"):
            s, depth, width = screen_for(p, yd, direction)
            il = [insertion_loss(r, s, width, depth, hs, hr, p) for r in distances]
            rows.append({"layout": layout, "direction": direction, "il": il,
                         "dist": distance_for(target, lw, s, width, depth, hs, hr, p), "well": well_velocity(p, yd)})
    return rows


# ---------------------------------------------------------------------------------------------
# Quantities, cost and carbon per module.

M2_FT2 = 10.7639
M3_CY = 1.30795


def wall_lengths(p: dict, yd: Yard) -> dict:
    """Metres of perimeter wall and of interior walls (court walls and cross walls)."""
    y = "wall.yard."
    w_across = yd.depth + 2 * p[y + "side_to_wall_m"]
    w_along = yd.length + 2 * p[y + "end_to_wall_m"]
    return {"perimeter": 2 * (w_across + w_along), "interior": len(yd.walls_across) * w_along + len(yd.walls_along) * w_across,
            "inside_m2": w_across * w_along}


def berm(p: dict, yd: Yard) -> dict:
    """The perimeter berm: earth (m3), topsoil on its faces (m3), footprint (m2), face area (m2)."""
    a = "wall.acoustics."
    h, s, c = p["wall.design.perimeter_h_m"], p[a + "berm_slope"], p[a + "berm_crest_m"]
    lens = wall_lengths(p, yd)
    width = 2 * s * h + c
    centre = lens["perimeter"] + 8 * (width / 2)  # the rectangle grows by half the berm each side
    face = 2 * np.hypot(s * h, h)
    return {"earth_m3": h * (c + s * h) * centre, "topsoil_m3": 0.15 * face * centre, "footprint_m2": width * centre,
            "face_m2": h * lens["perimeter"], "length_m": centre}


OPTIONS = ("berm", "precast perimeter", "precast cells", "brick cells, plain, by hand",
           "brick cells, patterned, by hand", "brick cells, patterned, by robot")


def masonry_quantities(p: dict, yd: Yard) -> dict:
    """Bricks, mortar, grout, concrete, steel for the brick walls of a layout: piers and bars sized
    for the body of each wall, and for the ends (two heights from each corner) at the end-region wind."""
    from . import wallstruct as ws

    d = "wall.design."
    lens = wall_lengths(p, yd)
    q = {"bricks": 0.0, "face_bricks": 0.0, "pier_bricks": 0.0, "mortar_m3": 0.0, "grout_m3": 0.0, "concrete_m3": 0.0,
         "steel_kg": 0.0, "face_m2": 0.0, "footprint_m2": 0.0}
    walls = [("perimeter", lens["perimeter"], p[d + "perimeter_h_m"], 4)]
    if lens["interior"] > 0:
        walls.append(("interior", lens["interior"], p[d + "court_h_m"], 2 * (len(yd.walls_across) + len(yd.walls_along))))
    designs = {}
    for name, length, h, ends in walls:
        body, end = ws.design(p, h, p["wall.wind.cf_body"]), ws.design(p, h, p["wall.wind.cf_end"])
        designs[name] = {"body": body, "end": end, "length_m": length, "h_m": h}
        end_len = min(ends * 2 * h, length)
        for dz, ln in ((body, length - end_len), (end, end_len)):
            pm = ws.per_metre(p, h, dz)
            for k_ in ("mortar_m3", "grout_m3", "concrete_m3", "steel_kg"):
                q[k_] += pm[k_] * ln
            q["bricks"] += pm["bricks"] * ln
            q["face_bricks"] += pm["bricks_per_m2_wythe"] * h * ln
            q["pier_bricks"] += (pm["bricks"] - 2 * pm["bricks_per_m2_wythe"] * h) * ln
            q["footprint_m2"] += pm["pier_d_m"] * ln
        q["face_m2"] += h * length
    q["designs"] = designs
    q["lengths"] = lens
    return q


def option_cost(p: dict, option: str, yd_cells: Yard, yd_perim: Yard) -> dict:
    """Installed cost (USD) and A1-A3 carbon (kg CO2e) of one option for one module, and its land."""
    c, cb = "wall.cost.", "wall.carbon."
    if option == "berm":
        b = berm(p, yd_perim)
        usd = b["earth_m3"] * M3_CY * p[c + "earthwork_usd_cy"] + b["topsoil_m3"] * M3_CY * p[c + "topsoil_usd_cy"]
        return {"usd": usd, "kg": b["earth_m3"] * p[cb + "earthwork_kg_m3"], "land_m2": b["footprint_m2"], "face_m2": b["face_m2"],
                "usd_ft2": usd / (b["face_m2"] * M2_FT2), "earth_m3": b["earth_m3"]}
    if option.startswith("precast"):
        q = masonry_quantities(p, yd_perim if option == "precast perimeter" else yd_cells)
        return {"usd": q["face_m2"] * M2_FT2 * p[c + "precast_usd_ft2"], "kg": q["face_m2"] * p[cb + "precast_kg_m2"],
                "land_m2": q["footprint_m2"], "face_m2": q["face_m2"], "usd_ft2": p[c + "precast_usd_ft2"]}
    q = masonry_quantities(p, yd_cells)
    patterned, robot = "patterned" in option, "robot" in option
    bricks = q["bricks"] * (1 + p[c + "waste"])
    materials = (bricks * p[c + "brick_usd_per_1000"] / 1000 + q["mortar_m3"] * p[c + "mortar_usd_m3"]
                 + q["grout_m3"] * p[c + "grout_usd_m3"] + q["steel_kg"] * p[c + "rebar_usd_kg"]
                 + q["concrete_m3"] * p["pass3.cost.concrete_usd_m3"])
    b = p[c + "burden"]
    crew_day = 8 * (p[c + "mason_usd_h"] + p[c + "helpers_per_mason"] * p[c + "helper_usd_h"]) * b  # per mason-day
    rate = p[c + "brick_per_mason_day"]
    pier_labour = q["pier_bricks"] * p[c + "pier_brick_factor"] / rate * crew_day
    if robot:
        r_usd = p[c + "robot_usd"]
        per_h = (r_usd / (p[c + "robot_years"] * p[c + "robot_hours_yr"]) + r_usd * p[c + "robot_upkeep"] / p[c + "robot_hours_yr"]
                 + (p[c + "robot_crew"] * p[c + "operator_usd_h"] + p[c + "robot_mason_share"] * p[c + "mason_usd_h"]) * b)
        wall_labour = 2 * q["face_bricks"] / p[c + "robot_bricks_per_h"] * per_h
    else:
        face_rate = rate * (p[c + "pattern_productivity"] if patterned else 1.0)
        wall_labour = (q["face_bricks"] / face_rate + q["face_bricks"] / rate) * crew_day
    access = q["face_m2"] * p[c + "access_usd_m2"]
    usd = (materials + wall_labour + pier_labour + access) * (1 + p[c + "overhead_profit"])
    kg = (bricks * p[cb + "brick_kg_each"] * p[cb + "brick_kg_kg"] + q["mortar_m3"] * p[cb + "mortar_kg_m3"]
          + (q["grout_m3"] + q["concrete_m3"]) * p["pass3.carbon.readymix_kg_m3"] + q["steel_kg"] * p["pass3.carbon.steel_kg_t"] / 1000)
    return {"usd": usd, "kg": kg, "land_m2": q["footprint_m2"], "face_m2": q["face_m2"], "usd_ft2": usd / (q["face_m2"] * M2_FT2),
            "labour_usd": (wall_labour + pier_labour) * (1 + p[c + "overhead_profit"]), "materials_usd": materials * (1 + p[c + "overhead_profit"]),
            "bricks": bricks}


def costs(p: dict) -> dict[str, dict]:
    yc, yp = yard(p, "cells"), yard(p, "perimeter")
    return {o: option_cost(p, o, yc, yp) for o in OPTIONS}


def monte_carlo(params: dict, n: int = 2000, seed: int = 7) -> dict[str, dict[str, np.ndarray]]:
    from .params import draw

    d = draw(params, n, seed)
    # Design choices and the coolers' own geometry stay as chosen: the spread is in prices, rates,
    # wind, soil and materials.
    fixed = ("wall.design.", "wall.brick.", "wall.yard.", "wall.acoustics.", "pass2.noise.dry_oversize", "pass2.module.")
    for k in d:
        if k.startswith(fixed):
            d[k] = np.full(n, params[k].value)
    out = {o: {"usd": np.empty(n), "kg": np.empty(n)} for o in OPTIONS}
    for i in range(n):
        p = {k: float(v[i]) for k, v in d.items()}
        for o, r in costs(p).items():
            out[o]["usd"][i], out[o]["kg"][i] = r["usd"], r["kg"]
    return out


def forge_spec(p: dict) -> dict:
    """What forge `wall` builds: a stretch of the perimeter wall, in mm."""
    b, d, mm = "wall.brick.", "wall.design.", 25.4
    t = (2 * p[b + "unit_w_in"] + p[b + "collar_in"]) * mm
    span = p[d + "pier_spacing_ft"] * 304.8
    length = 6 * span
    return {"source": "brownfield wall (params/wall.yaml): the perimeter wall, six bays",
            "unit_l_mm": p[b + "unit_l_in"] * mm, "unit_w_mm": p[b + "unit_w_in"] * mm, "unit_h_mm": p[b + "unit_h_in"] * mm,
            "joint_mm": p[b + "joint_in"] * mm, "height_mm": p[d + "perimeter_h_m"] * 1000, "length_mm": length,
            "collar_mm": p[b + "collar_in"] * mm, "pier_spacing_mm": span, "pier_w_mm": p[d + "pier_w_in"] * mm,
            "pier_d_mm": p[d + "pier_d_in"] * mm - t, "footing_w_mm": p[d + "grade_beam_w_in"] * mm,
            "footing_t_mm": p[d + "grade_beam_d_in"] * mm, "pattern_amp_deg": p[b + "turn_deg"],
            "pattern_wavelength_mm": 3200.0, "pattern_centres_mm": [[0.28 * length, 4400.0], [0.76 * length, 1500.0]]}


def figure(p: dict, path) -> None:
    """Night level at a home against its distance from the yard, both ways, for four layouts."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .figures import GRID, INK, INK2, MUTED, SURFACE, _style

    lw = noise.module_lw("good neighbour", p["pass2.module.it_mw"] * 1.2, p)
    hs, hr = p["wall.yard.fan_h_m"], p["wall.acoustics.ear_h_m"]
    target = p["pass2.noise.target_night_db"]
    rs = np.geomspace(30, 1000, 26)  # from beyond the berm's outer toe (~27 m)
    # (layout, label, colour, where its label sits: distance, offset in points, alignment)
    # The berm and the perimeter wall run almost together: the legend names them; the other two
    # carry direct labels, set above their lines (which fall to the right).
    series = [("open", "no screen", MUTED, 40, 5, "bottom", "left"), ("perimeter", "6 m wall round the yard", "#2a78d6", None, 0, "", ""),
              ("berm", "6 m berm round the yard", "#eb6834", None, 0, "", ""), ("cells", "walled cells (6 m)", "#1baf7a", 200, -5, "top", "right")]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=150, facecolor=SURFACE, sharey=True)
    for ax, direction, title in zip(axes, ("across", "along"), ("A home off a long side (across the rows)", "A home off an end (along the rows)")):
        _style(ax)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.set_xscale("log")
        for layout, label, colour, x_lab, dy, va, ha in series:
            s, depth, width = screen_for(p, yard(p, layout), direction)
            lv = [level(lw, r, s, width, depth, hs, hr, p) for r in rs]
            ax.plot(rs, lv, color=colour, linewidth=1.6, label=label, solid_capstyle="round")
            if x_lab:
                ax.annotate(label, (x_lab, float(np.interp(np.log(x_lab), np.log(rs), lv))), xytext=(0, dy), textcoords="offset points",
                            fontsize=7, color=INK2, va=va, ha=ha)
        ax.axhline(target, color=INK2, linewidth=0.8, linestyle=(0, (4, 3)))
        ax.text(560, target + 0.6, f"{target:.0f} dB(A), WHO night guideline", fontsize=7, color=INK2, ha="center")
        ax.set_xlim(30, 1100)
        ax.set_xticks([30, 50, 100, 200, 500, 1000])
        ax.set_xticklabels(["30", "50", "100", "200", "500", "1,000"])
        ax.set_xlabel("distance from the cooler yard's edge (m)", color=INK2, fontsize=8.5)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
    axes[0].set_ylabel("night level outside the home, dB(A)", color=INK2, fontsize=8.5)
    axes[0].legend(loc="lower left", frameon=False, fontsize=7.5, labelcolor=INK2)
    fig.suptitle(f"One 100 MW module's dry coolers ({lw:.0f} dB(A) of sound power), ISO 9613-2 at 500 Hz", x=0.01, ha="left", fontsize=10, color=INK)
    fig.text(0.01, 0.01, "Cells: walls between every second row of coolers and across every second unit. The berm and the wall round the yard "
             "do about the same. Ear 4 m up." + chr(10) +
             "The walls cut less at the fans' low hum (cells: 6.5 dB at 125 Hz vs 12 at 500 Hz, 300 m).", fontsize=6.8, color=MUTED)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def report(p: dict, params: dict, forge: dict | None = None) -> str:
    from . import wallstruct as ws

    lines = []
    yc = yard(p, "cells")
    lines += ["**The yard (one 100 MW module, dry coolers at twice minimum size)**", "",
              f"{yc.units} V-coil units of {p['wall.yard.unit_kw']:,.0f} kW ({p['wall.yard.unit_l_m']} x {p['wall.yard.unit_w_m']} m, "
              f"fans at {p['wall.yard.fan_h_m']} m), {yc.rows} rows of {yc.per_row}; {yc.airflow:,.0f} m3/s of air at half fan speed.", "",
              "| Layout | Yard inside the walls | Wall (m) round / inside | Air down into the tightest walled space |", "|---|---|---|---|"]
    for layout in ("perimeter", "courts", "cells"):
        yd = yard(p, layout)
        ln = wall_lengths(p, yd)
        lines.append(f"| {NAMES[layout]} | {ln['inside_m2']:,.0f} m2 | {ln['perimeter']:,.0f} / {ln['interior']:,.0f} | "
                     f"{well_velocity(p, yd):.2f} m/s (most {p['wall.yard.well_v_max']}) |")
    ac = acoustics(p)
    lines += ["", "**Sound at a home (ISO 9613-2 at 500 Hz; ear 4 m up)**", "",
              "| Layout | Home off | Quieter by, at 120 / 300 / 700 m | 40 dB(A) at night beyond |", "|---|---|---|---|"]
    for r in ac:
        lines.append(f"| {NAMES[r['layout']]} | {'a long side' if r['direction'] == 'across' else 'an end'} | "
                     + " / ".join(f"{x:.1f}" for x in r["il"]) + f" dB | {r['dist']:,.0f} m |")
    hs, hr = p["wall.yard.fan_h_m"], p["wall.acoustics.ear_h_m"]
    s, depth, width = screen_for(p, yc, "across")
    low = {f: level(100, 300, open_ground(), width, depth, hs, hr, p, f=f) - level(100, 300, s, width, depth, hs, hr, p, f=f) for f in (63, 125, 250, 500)}
    lines += ["", "Pass 2's sound power budget (the most a module may emit for 40 dB(A) at a home), and what walled cells add to it:", "",
              "| Nearest home | Budget, open ground | Cells take off (across / along) | Budget with cells (across / along) |", "|---|---|---|---|"]
    views = [screen_for(p, yc, direction) for direction in ("across", "along")]
    for r in (300.0, 500.0, 1000.0, 2000.0):
        b0 = float(noise.budget(p["pass2.noise.target_night_db"], r, p))
        il = [insertion_loss(r, s_, wid, dep, hs, hr, p) for s_, dep, wid in views]
        lines.append(f"| {r:,.0f} m | {b0:.0f} dB(A) | {il[0]:.1f} / {il[1]:.1f} dB | {b0 + il[0]:.0f} / {b0 + il[1]:.0f} dB(A) |")
    lines += ["", "Cells, across, at 300 m by band: " + ", ".join(f"{f} Hz {v:.1f} dB" for f, v in low.items())
              + " (the screening term only; the ground term is the A-weighted method's)."]
    q = masonry_quantities(p, yc)
    lines += ["", "**The brick walls (pier and panel, TMS 402-16 allowable stress, ASCE 7-16 wind)**", ""]
    lines += ["| Wall | Region | Wind (ASD) | Panel bars | Pier bars (each face) | Shaft (24 in.) |", "|---|---|---|---|---|---|"]
    for name, dz in q["designs"].items():
        for region in ("body", "end"):
            z = dz[region]
            lines.append(f"| {name}, {dz['h_m']:g} m, {dz['length_m']:,.0f} m | {region} (Cf {z['cf']:.2f}) | {z['w_psf']:.1f} psf | "
                         f"#{z['panel']['bar']} at {z['panel']['spacing_in']} in. (fs {z['panel']['fs'] / 1000:.1f} ksi) | "
                         f"{z['pier']['bars_per_face']} #{z['pier']['bar']} (fs {z['pier']['fs'] / 1000:.1f} ksi, fb {z['pier']['fb']:.0f} psi) | "
                         f"{z['shaft_depth_ft']:.1f} ft |")
    lines += ["", f"Per module: {q['bricks'] / 1e6:.2f} million bricks, {q['mortar_m3']:,.0f} m3 mortar, {q['grout_m3']:,.0f} m3 grout, "
              f"{q['concrete_m3']:,.0f} m3 concrete, {q['steel_kg'] / 1e3:,.0f} t of bars; {q['face_m2']:,.0f} m2 of wall."]
    cs = costs(p)
    mc = monte_carlo(params)
    lines += ["", "**Cost, carbon and land per module**", "",
              "| Option | Installed cost | P10 / P90 | per sq ft of wall | A1-A3 carbon | Land |", "|---|---|---|---|---|---|"]
    for o in OPTIONS:
        r = cs[o]
        p10, p90 = np.percentile(mc[o]["usd"], [10, 90]) / 1e6
        lines.append(f"| {o} | ${r['usd'] / 1e6:.2f}M | ${p10:.2f}M / ${p90:.2f}M | ${r['usd_ft2']:.0f} | {r['kg'] / 1e3:,.0f} t | {r['land_m2'] / 1e4:.2f} ha |")
    robot, hand = mc["brick cells, patterned, by robot"]["usd"], mc["brick cells, patterned, by hand"]["usd"]
    plain, pre = mc["brick cells, plain, by hand"]["usd"], mc["precast cells"]["usd"]
    lines += ["", f"In the Monte Carlo ({len(robot):,} draws): the robot's patterned wall is cheaper than the hand-laid patterned wall in "
              f"{(robot < hand).mean():.0%}, cheaper than plain brick by hand in {(robot < plain).mean():.0%}, cheaper than precast in "
              f"{(robot < pre).mean():.0%}; the pattern by hand costs ${np.median(hand - plain) / 1e6:.2f}M more than plain (median)."]
    bk = cs["brick cells, plain, by hand"]
    bm = cs["berm"]
    lines += ["", "Known cases:",
              f"- Plain brick by hand, bottom-up: ${bk['usd_ft2']:.0f} per sq ft of wall; FHWA's brick barrier average "
              f"${p['wall.cost.brick_fhwa_usd_ft2']:.2f} (2022 $, range {p['wall.cost.brick_fhwa_usd_ft2'] and '32-70'}).",
              f"- The berm, bottom-up: ${bm['usd_ft2']:.0f} per sq ft of face (at ${p['wall.cost.earthwork_usd_cy']:.0f}/cy); at the mass-grading price "
              f"${option_cost(dict(p, **{'wall.cost.earthwork_usd_cy': 4.67}), 'berm', yc, yard(p, 'perimeter'))['usd_ft2']:.0f}; "
              f"FHWA's berm average ${p['wall.cost.berm_fhwa_usd_ft2']:.2f}."]
    if forge:
        ch, rb = forge["checks"], forge.get("robot", {})
        lines += ["", "**CortenForge (forge `wall`)**", "",
                  f"- {forge['length_m']:.1f} m of the perimeter wall, {forge['courses']} courses: {ch['face_bricks']:,} face bricks, "
                  f"{forge['face_bricks_per_m2']:.1f} per m2 (BIA: 73.81); turned up to {ch['max_turn_deg']:.1f} deg; {ch['overlaps']} overlaps; "
                  f"head joints {ch['min_joint_mm']:.1f}-{ch['max_joint_mm']:.1f} mm; bearing on the course below at least {100 * ch['min_bearing']:.0f}% "
                  f"(mean {100 * ch['mean_bearing']:.0f}%); corners {ch['max_projection_mm']:.0f} mm proud of the face."]
        if rb:
            pt, pl = rb["patterned"], rb["plain"]
            lines.append(f"- The gantry in sim-core laid {pt['bricks']} face bricks twice: {pt['motion_s_mean']:.2f} s of motion a brick with the "
                         f"pattern, {pl['motion_s_mean']:.2f} s plain (the wrist turns while the gantry carries); released 2 mm above the bed, every brick "
                         f"settled within {max(pt['err_plan_mm_max'], pl['err_plan_mm_max'], 0.01):.2f} mm and {max(pt['err_deg_max'], pl['err_deg_max'], 0.01):.2f} deg "
                         "of where it was let go (an ideal servo; a real robot's accuracy is its own).")
    return "\n".join(lines)
