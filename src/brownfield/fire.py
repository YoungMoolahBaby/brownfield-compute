"""Pass 3g step 6 (D28): sprinklers and alarms (`design`, `summary`).

**6a, the one stair** (`single_exit`): IBC 2021 Table 1006.3.4(1) lets a Group R-2 building have
one exit on its first three storeys with at most four flats a storey and 125 ft of exit access
travel, if it is sprinklered throughout (903.3.1.1 or 903.3.1.2) and every bedroom has an escape
opening (1031). The travel is measured in the model, square, from every room's far corner to the
flat's door into the stair; the escape windows were checked in step 1.

**6b, the stair's enclosure** (`enclosure`): 1-hour (1023.2), its openings limited (1023.4), its
penetrations limited to the fire protection and the stair's own (1023.5). Where the annex abuts it,
the stair's back wall is no longer exterior; and 1023.7 reaches the annex's walls near the stair's
unrated windows above it.

**6c, the sprinklers** (`layout`): NFPA 13R-2019, residential sprinklers in each room by their
listed coverage; the rooms 13R lets go without.

**6d, the hydraulics** (`hydraulics`): the four sprinklers of the hardest compartment, back along
the pipe by Hazen-Williams to the street, against what the street gives.

**6e, the alarms** (`alarms`): smoke alarms in each flat (907.2.11), the sprinkler system's flow
alarm and supervision (903.4), whether a building fire alarm is required (907.2.9).

**6f, the roof hatch** (`roof_access`): step 5's finding (IMC 306.5), placed.
"""

from __future__ import annotations

import math

from .systems import FT, IN, by_flat


# ---- 6a: the one stair ----

def single_exit(apt: dict, p: dict) -> dict:
    """Each storey against Table 1006.3.4(1): its flats, and each flat's longest exit access
    travel, square, from the far corner of any of its rooms to its door into the stair."""
    c = "systems.fire_code."
    doors = {d["flat"]: d for d in apt["stair"]["doors"] if d.get("flat")}
    per_storey: dict[int, int] = {}
    travel = {}
    for f in apt["flats"]:
        per_storey[f["floor"]] = per_storey.get(f["floor"], 0) + 1
        d = doors[f["name"]]
        dx, dy = (d["lo_m"][0] + d["hi_m"][0]) / 2, (d["lo_m"][1] + d["hi_m"][1]) / 2
        travel[f["name"]] = max((abs(x - dx) + abs(y - dy)) / FT for r in by_flat(apt)[f["name"]]
                                for x in (r["lo_m"][0], r["hi_m"][0]) for y in (r["lo_m"][1], r["hi_m"][1]))
    return {"storeys": apt["storeys"], "per_storey": per_storey, "travel_ft": travel,
            "ok": (apt["storeys"] <= p[c + "single_exit_max_storeys"]
                   and max(per_storey.values()) <= p[c + "single_exit_max_units"]
                   and max(travel.values()) <= p[c + "single_exit_max_travel_ft"])}


# ---- 6b: the stair's enclosure and the annex ----

def enclosure(apt: dict, p: dict) -> dict:
    """The annex against 1023.7: the stair's unrated windows above the annex, and every annex wall
    and door within 10 ft of one in plan, which must be 1-hour (walls) and 3/4-hour (openings)
    from the ground to the annex's roof; and the wall the stair and the annex share, which becomes
    part of the stair's 1-hour enclosure (1023.2)."""
    c = "systems.fire_code."
    reach = p[c + "exterior_wall_reach_ft"] * FT
    annex = apt["rooms"]["annex"]
    back = max(x["hi_m"][0] for x in apt["parts"] if x["kind"] == "exterior_wall")
    windows = [o for o in apt["openings"] if o["id"].split("/")[0].endswith("-stair") and o["face"] == "back" and o["kind"] == "window"]

    def near(lo, hi):
        """The least plan distance (m) from a box to any of the stair's back windows."""
        out = math.inf
        for w in windows:
            dx = max(lo[0] - w["hi_m"][0], w["lo_m"][0] - hi[0], 0.0)
            dy = max(lo[1] - w["hi_m"][1], w["lo_m"][1] - hi[1], 0.0)
            out = min(out, math.hypot(dx, dy))
        return out

    walls = [{"id": w["id"], "m": near(w["lo_m"], w["hi_m"])} for w in annex["parts"] if w["kind"] == "annex_wall"]
    doors = [{"id": d["id"], "room": d["room"], "width_in": d["width_m"] / IN, "m": near(d["lo_m"], d["hi_m"])} for d in annex["doors"]]
    rated = [w for w in walls if w["m"] <= reach]
    for w in rated:
        part = next(x for x in annex["parts"] if x["id"] == w["id"])
        # The stretch of the wall within reach of a window, from the stair's side.
        w["rated_ft"] = min(part["hi_m"][0] - back, reach) / FT
    return {"windows": [w["id"] for w in windows], "walls": walls, "rated_walls": rated,
            "doors": doors, "protected_doors": [d for d in doors if d["m"] <= reach],
            "shared_wall_hr": p[c + "stair_enclosure_hr"]}


# ---- 6f: the roof hatch ----

def roof_access(apt: dict, p: dict) -> dict:
    """The roof hatch the outdoor units need (IMC 2021 306.5: a permanent means of access where
    one climbs more than 16 ft; IBC 1011.16 lets a permanent ladder serve an unoccupied roof that
    needs no stair, 1011.12.1, and equipment IMC 306.5 serves). Over the stair's top hall, which
    may open to the outside (1023.4 limits only the enclosure's other openings): its ladder against
    the hall's side wall, short of the flats' doors, the hatch far enough from the roof's edge to
    need no guards (1011.13: within 10 ft). What's left of the hall beside the ladder and its
    climbing clearance (306.5 item 7) against the stair's width, which its landings keep (1011.6)."""
    c = "systems.fire_code."
    hall = next(x for x in apt["stair"]["parts"] if x["id"] == f"floor-{apt['storeys']}-hall")
    roof = next(x for x in apt["parts"] if x["kind"] == "roof")
    w, l = p[c + "hatch_w_in"] * IN, p[c + "hatch_l_in"] * IN
    x0 = roof["lo_m"][0] + p[c + "hatch_guard_ft"] * FT + p[c + "hatch_margin_in"] * IN
    y0 = hall["lo_m"][1]
    lo, hi = (x0, y0), (x0 + l, y0 + w)
    edge = min(lo[0] - roof["lo_m"][0], roof["hi_m"][0] - hi[0], lo[1] - roof["lo_m"][1], roof["hi_m"][1] - hi[1]) / FT
    doors = [d for d in apt["stair"]["doors"] if d.get("flat") and d["storey"] == apt["storeys"]]
    clear_of_doors = all(hi[0] <= d["lo_m"][0] or lo[0] >= d["hi_m"][0] for d in doors)
    left_in = (hall["hi_m"][1] - hall["lo_m"][1]) / IN - p[c + "ladder_depth_in"] - p[c + "ladder_clearance_in"]
    climb = (apt["storey_m"] * apt["storeys"]) / FT
    return {"lo": lo, "hi": hi, "edge_ft": edge, "guards": edge < p[c + "hatch_guard_ft"], "climb_ft": climb,
            "needed": climb > p[c + "imc_access_ft"], "area_ft2": w * l / FT ** 2, "clear_of_doors": clear_of_doors,
            "hall_left_in": left_in, "hall_ok": left_in >= p["bidset.code.stair.width_min_in"]}


# ---- The code's frame: 13R, the construction type, a fire alarm or not ----

def code_frame(apt: dict, p: dict) -> dict:
    """What the 2021 IBC (Pennsylvania's) asks of the building as a whole: 13R is allowed (903.3.1.2,
    with Pennsylvania's R-2 roof limit measured from the fire department's road); Type V-B is
    enough with 13R (Tables 504.3, 504.4, 506.2); a manual fire alarm system isn't required
    (907.2.9.1), so smoke alarms in each flat (907.2.11) and the sprinkler system's own alarms
    (903.4) are what there is."""
    c = "systems.fire_code."
    roof = next(x for x in apt["parts"] if x["kind"] == "roof")
    roof_ft = roof["hi_m"][2] / FT + p[c + "access_road_below_slab_ft"]
    footprint_ft2 = (apt["depth_m"] * apt["length_m"]) / FT ** 2
    height_ft = roof_ft
    top = max(f["floor"] for f in apt["flats"])
    alarm = (top - 1 >= p[c + "manual_alarm_storeys_above"]) or len(apt["flats"]) > p[c + "manual_alarm_max_units"]
    return {"roof_ft": roof_ft, "r13_ok": apt["storeys"] <= p[c + "r13_max_storeys"] and roof_ft < p[c + "r13_max_roof_ft"],
            "footprint_ft2": footprint_ft2, "vb_ok": apt["storeys"] <= p[c + "vb_s13r_storeys"]
            and height_ft <= p[c + "vb_s13r_height_ft"] and footprint_ft2 <= p[c + "vb_area_ft2"],
            "manual_alarm": alarm, "top_storeys_above_discharge": top - 1}


def smoke_alarms(apt: dict, p: dict) -> dict:
    """Each flat's smoke alarms (907.2.11.2): one in each bedroom and one outside the sleeping area
    (the hall), on one storey; photoelectric, so at least 6 ft from the range (907.2.11.3: the
    kitchen's nearest point taken for the range), interconnected (907.2.11.5) and on the building's
    wiring with a battery (907.2.11.6): step 5's sleeping-side lighting circuit."""
    c = "systems.fire_code."
    out = {}
    for f in apt["flats"]:
        rooms = by_flat(apt)[f["name"]]
        beds = [r for r in rooms if r["use"] == "bedroom"]
        hall = next(r for r in rooms if r["id"] == f"{f['name']}/hall")
        kitchen = next(r for r in rooms if r["use"] == "kitchen")
        hx, hy = (hall["lo_m"][0] + hall["hi_m"][0]) / 2, (hall["lo_m"][1] + hall["hi_m"][1]) / 2
        dx = max(kitchen["lo_m"][0] - hx, hx - kitchen["hi_m"][0], 0.0)
        dy = max(kitchen["lo_m"][1] - hy, hy - kitchen["hi_m"][1], 0.0)
        out[f["name"]] = {"alarms": len(beds) + 1, "places": [r["id"] for r in beds] + [hall["id"]],
                          "hall_to_kitchen_ft": math.hypot(dx, dy) / FT}
    worst = min(v["hall_to_kitchen_ft"] for v in out.values())
    return {"flats": out, "total": sum(v["alarms"] for v in out.values()), "cooking_ok": worst >= p[c + "smoke_from_cooking_ft"],
            "hall_to_kitchen_ft": worst}


# ---- Tables: the residential sprinkler's listing, CPVC pipe, the backflow assembly ----

def _rows(name: str) -> list[dict]:
    from .loads import _table

    return _table(name)


def listing(model: str = "TY2236") -> list[dict]:
    """A residential sprinkler's listed coverages (square, ft), flows (gpm) and pressures (psi),
    smallest first (`data/tyco_lfii_residential_sprinklers.csv`, Tyco's TFP403 and TFP412)."""
    rows = [r for r in _rows("tyco_lfii_residential_sprinklers.csv") if r["model"] == model
            and r["deflector_to_ceiling"] in ("1-1/4 to 4 in.", "4 to 6 in.")]
    return sorted(({"w": float(r["coverage_w_ft"]), "l": float(r["coverage_l_ft"]), "q": float(r["min_flow_gpm"]),
                    "p": float(r["min_pressure_psi"]), "k": float(r["K"])} for r in rows), key=lambda r: (r["l"], r["w"]))


def cpvc() -> dict[str, dict]:
    """CPVC sprinkler pipe (BlazeMaster, SDR 13.5): inside diameter and fittings' equivalent feet
    (`data/blazemaster_cpvc_sdr13_5.csv`)."""
    return {r["nominal_in"]: {"id": float(r["avg_ID_in"]), "tee_branch": float(r["tee_branch_ft"]), "elbow": float(r["elbow90_ft"]),
                              "tee_run": float(r["tee_run_ft"])} for r in _rows("blazemaster_cpvc_sdr13_5.csv")}


SIZES = ("3/4", "1", "1-1/4", "1-1/2", "2", "2-1/2", "3")
DROP_SIZE = "1"  # a residential sprinkler's drop from its branch line


def dcva_psi(gpm: float, size_in: str) -> float:
    """The double check valve assembly's loss at a flow, straight lines between the points read off
    Watts' LF007 chart (`data/watts_lf007_dcva_chartread.csv`, read by eye to about 0.5 psi)."""
    pts = sorted((float(r["flow_gpm"]), float(r["pressure_drop_psi_chartread"])) for r in _rows("watts_lf007_dcva_chartread.csv")
                 if r["size_in"] == size_in)
    for (q0, p0), (q1, p1) in zip(pts, pts[1:]):
        if q0 <= gpm <= q1:
            return p0 + (p1 - p0) * (gpm - q0) / (q1 - q0)
    raise ValueError(gpm)


# ---- The friction: Hazen-Williams ----

def hw_psi_ft(gpm: float, id_in: float, c: float) -> float:
    """Friction loss (psi per ft) by Hazen-Williams, as NFPA 13 has it: p = 4.52 Q^1.85 /
    (C^1.85 d^4.87)."""
    return 4.52 * gpm ** 1.85 / (c ** 1.85 * id_in ** 4.87)


def head_flow(p_node: float, k: float, drop_eq_ft: float, id_in: float, c: float) -> float:
    """A sprinkler's flow (gpm) on a drop of `drop_eq_ft` equivalent feet from a node at `p_node`:
    the Q at which its own pressure (Q/K)^2 and the drop's friction sum to the node's."""
    lo, hi = 0.0, k * math.sqrt(p_node)
    for _ in range(60):
        q = (lo + hi) / 2
        if (q / k) ** 2 + hw_psi_ft(q, id_in, c) * drop_eq_ft > p_node:
            hi = q
        else:
            lo = q
    return (lo + hi) / 2


# ---- 6c: the sprinklers ----

SPRINKLERED_OPEN = ("living", "study", "kitchen", "entry", "hall", "passage")  # one compartment, open to each other


def _cover(lx_ft: float, ly_ft: float, table: list[dict]) -> dict:
    """The fewest residential sprinklers that cover a rectangular room, each in an equal cell no
    longer than a listed square's side (so no more than half that from a wall); the listing's
    flow and pressure for the smallest square that holds the cell."""
    best = None
    for row in table:
        side = row["l"]
        nx, ny = max(1, math.ceil(lx_ft / side - 1e-9)), max(1, math.ceil(ly_ft / side - 1e-9))
        cell = max(lx_ft / nx, ly_ft / ny)
        use = next(r for r in table if r["l"] >= cell - 1e-9)
        cand = {"n": nx * ny, "nx": nx, "ny": ny, "cell_ft": (lx_ft / nx, ly_ft / ny), **use}
        if best is None or (cand["n"], cand["q"]) < (best["n"], best["q"]):
            best = cand
    return best


def layout(apt: dict, p: dict) -> dict:
    """Each flat's sprinklers (Tyco TY2236, residential pendent, K 4.9): every room but the bath
    (13R 6.6.2: none needed in a bathroom of 55 ft2 or less); the laundry closet included, its
    sprinkler intermediate-temperature (6.6.4: a closet with a washer or dryer; 6.2.3.3.4: a
    ventless dryer); the passage, a few square feet between the hall and the kitchen, covered by
    theirs. Each sprinkler at its cell's centre. Compartments: the open living area (living,
    study, kitchen, entry, hall, passage) is one; each bedroom and the closet another (doors)."""
    s = "systems.sprinkler."
    table = listing()
    out = {}
    for f in apt["flats"]:
        heads, comps = [], {}
        for r in by_flat(apt)[f["name"]]:
            use, key = r["use"], r["id"].split("/")[1]
            if use == "bath" and r["area_m2"] / FT ** 2 <= p[s + "bath_exempt_ft2"]:
                continue
            if key == "passage":
                continue
            lx, ly = (r["hi_m"][0] - r["lo_m"][0]) / FT, (r["hi_m"][1] - r["lo_m"][1]) / FT
            cov = _cover(lx, ly, table)
            comp = "open" if key in SPRINKLERED_OPEN else key
            for i in range(cov["nx"]):
                for j in range(cov["ny"]):
                    xy = (r["lo_m"][0] + (i + 0.5) * (r["hi_m"][0] - r["lo_m"][0]) / cov["nx"],
                          r["lo_m"][1] + (j + 0.5) * (r["hi_m"][1] - r["lo_m"][1]) / cov["ny"])
                    h = {"room": r["id"], "comp": comp, "xy": xy, "q": cov["q"], "p": cov["p"], "k": cov["k"], "l_ft": cov["l"],
                         "cell_ft2": cov["cell_ft"][0] * cov["cell_ft"][1], "cell_ft": list(cov["cell_ft"]),
                         "temp": "intermediate" if use == "utility" else "ordinary"}
                    heads.append(h)
                    comps.setdefault(comp, []).append(h)
        out[f["name"]] = {"heads": heads, "compartments": comps}
    return out


def stair_heads(apt: dict, p: dict) -> list[dict]:
    """The stair's quick-response sprinklers (13R 6.6.9.1: throughout an enclosed stairwell; 6.6.9.4:
    to NFPA 13 outside the flats; 6.2.2.1: quick response): each storey's footprint of the core at
    the light-hazard spacing (7.2.3.1(2), 225 ft2), at 0.1 gpm/ft2 of its share and at least 7 psi."""
    s = "systems.sprinkler."
    lo_y, hi_y = apt["stair"]["core_y_m"]
    core_ft2 = (max(x["hi_m"][0] for x in apt["parts"] if x["kind"] == "party_wall") - min(x["lo_m"][0] for x in apt["parts"] if x["kind"] == "party_wall")) * (hi_y - lo_y) / FT ** 2
    n = math.ceil(core_ft2 / p[s + "lh_spacing_ft2"])
    out = []
    for lv in apt["levels"]:
        for i in range(n):
            q = max(p[s + "qr_density"] * core_ft2 / n, p[s + "qr_k"] * math.sqrt(p[s + "min_head_psi"]))
            out.append({"storey": lv["storey"], "z_m": lv["elevation_m"] + p[s + "ceiling_m"], "q": q, "k": p[s + "qr_k"],
                        "cell_ft2": core_ft2 / n})
    return out


# ---- 6d: the hydraulics ----

def _path_back(nodes: list[dict], p: dict, c: float) -> tuple[float, float]:
    """Walk a path from its remote end to its source: `nodes[0]` the remote sprinkler; each node may
    carry a sprinkler (on a drop), each segment after it (to the next node upstream) a length,
    a pipe size and its fittings. The remote sprinkler at its listed pressure (and 13R's 7 psi
    floor); every other on the path flows what its node's pressure gives. Returns the pressure
    (psi) and flow (gpm) at the source end, before elevation."""
    s = "systems.sprinkler."
    pipe = cpvc()
    first = nodes[0]["head"]
    p_head = max(first["p"], p[s + "min_head_psi"], (first["q"] / first["k"]) ** 2)
    q = first["k"] * math.sqrt(p_head)
    drop = pipe[DROP_SIZE]
    pressure = p_head + hw_psi_ft(q, drop["id"], c) * (p[s + "drop_ft"] + drop["tee_branch"])
    for node in nodes:
        seg = node.get("seg")
        if seg is not None:
            d = pipe[seg["size"]]
            pressure += hw_psi_ft(q, d["id"], c) * (seg["ft"] + seg["elbows"] * d["elbow"] + seg["tee_runs"] * d["tee_run"]
                                                    + seg.get("tee_branches", 0) * d["tee_branch"])
        nxt = node.get("next_head")
        if nxt is not None:
            qh = head_flow(pressure, nxt["k"], p[s + "drop_ft"] + drop["tee_branch"], drop["id"], c)
            q += qh
    return pressure, q


def _manhattan_ft(a: tuple[float, float], b: tuple[float, float]) -> float:
    return (abs(a[0] - b[0]) + abs(a[1] - b[1])) / FT


def riser_xy(apt: dict) -> tuple[float, float]:
    """The sprinkler riser: in the stair (fire protection may pierce its enclosure, IBC 1023.5), at
    the back of each storey's hall against the flights, half way across the core."""
    hall = next(x for x in apt["stair"]["parts"] if x["id"] == "floor-2-hall")
    lo_y, hi_y = apt["stair"]["core_y_m"]
    return hall["hi_m"][0], (lo_y + hi_y) / 2


def compartment_demand(apt: dict, p: dict, flat: str, comp: str, sizes: dict) -> dict:
    """One compartment's design (13R 7.1.1.3.1: all its sprinklers up to four, those with the
    greatest demand): its sprinklers chained from the flat's door nearest-first, the last four the
    design; back along the chain, to the door, to the riser in the stair, down it, along to the
    riser assembly in the annex; the pressure and flow needed there, at the riser's base."""
    s = "systems.sprinkler."
    c = p[s + "c_cpvc"]
    lay = layout(apt, p)[flat]["compartments"][comp]
    door = next(d for d in apt["stair"]["doors"] if d.get("flat") == flat)
    entry = ((door["lo_m"][0] + door["hi_m"][0]) / 2, (door["lo_m"][1] + door["hi_m"][1]) / 2)
    chain, here, left = [], entry, list(lay)
    while left:
        nxt = min(left, key=lambda h: _manhattan_ft(here, h["xy"]))
        chain.append(nxt)
        left.remove(nxt)
        here = nxt["xy"]
    design = chain[-int(p[s + "design_heads_max"]):]
    # Nodes from the remote end: each design sprinkler, the chain's segments between them, then
    # the run to the flat's door (through the rest of the chain), the stair to the riser.
    nodes = []
    for i in range(len(design) - 1, -1, -1):
        h = design[i]
        prev = design[i - 1]["xy"] if i > 0 else entry
        ft = _manhattan_ft(h["xy"], prev)
        bends = 1 if (abs(h["xy"][0] - prev[0]) > 1e-6 and abs(h["xy"][1] - prev[1]) > 1e-6) else 0
        size = sizes["branch"] if i > 0 else sizes["feed"]
        node = {"head": h, "seg": {"ft": ft, "size": size, "elbows": bends, "tee_runs": 1}}
        if i > 0:
            node["next_head"] = design[i - 1]
        nodes.append(node)
    lvl = next(x for x in apt["levels"] if x["storey"] == next(f["floor"] for f in apt["flats"] if f["name"] == flat))
    rx = riser_xy(apt)
    nodes.append({"seg": {"ft": _manhattan_ft(entry, rx), "size": sizes["feed"], "elbows": 2, "tee_runs": 0, "tee_branches": 1}})
    p_floor, q = _path_back(nodes, p, c)
    first = design[-1]
    p_remote = max(first["p"], p[s + "min_head_psi"], (first["q"] / first["k"]) ** 2)
    z_head = lvl["elevation_m"] + p[s + "ceiling_m"]
    return {"flat": flat, "comp": comp, "heads": len(lay), "design": design, "q_gpm": q, "p_at_riser_floor_psi": p_floor,
            "p_remote_psi": p_remote, "branch_psi": p_floor - p_remote, "z_head_m": z_head, "remote_xy": first["xy"]}


def supply(p: dict, q: float, p_top: float, z_top_m: float, run: dict, sizes: dict) -> dict:
    """From the riser's tee at a storey to the street: down the riser, along to the riser
    assembly, through the backflow assembly (it is also the system's check and control valve,
    13R 6.8.5-6.8.6), out the underground service to the main; and the elevation from the main to
    the sprinkler. The pressure the street must give at that flow."""
    s, pl = "systems.sprinkler.", "systems.plumbing."
    c = p[s + "c_cpvc"]
    pipe = cpvc()
    rise = pipe[sizes["riser"]]
    riser_ft = z_top_m / FT
    main = pipe[sizes["main"]]
    friction = (hw_psi_ft(q, rise["id"], c) * (riser_ft + rise["elbow"])
                + hw_psi_ft(q, main["id"], c) * (run["main_ft"] + 3 * main["elbow"]))
    under = hw_psi_ft(q, p[s + "underground_id_in"], p[s + "c_underground"]) * (p[s + "underground_ft"] + p[s + "underground_el_ft"])
    backflow = dcva_psi(q, sizes["backflow"])
    head_ft = z_top_m / FT + p["systems.fire_code.access_road_below_slab_ft"] + p[pl + "main_depth_ft"]
    elevation = 0.433 * head_ft
    need = p_top + friction + under + backflow + elevation
    return {"riser_main_psi": friction, "underground_psi": under, "backflow_psi": backflow, "elevation_psi": elevation,
            "need_psi": need, "q_gpm": q}


def hydraulics(apt: dict, p: dict) -> dict:
    """Every compartment of every flat and the stair, each its own design: the one that asks the
    street for the most governs (the annex, beside the riser assembly, is checked in `design`). The pipe starts at the design's sizes (`SIZE_START`) and
    the governing run's largest friction is upsized until the street's pressure, less the margin
    for its seasonal swing (903.3.5), covers it."""
    s = "systems.sprinkler."
    sizes = dict(SIZE_START)
    target = p["systems.plumbing.street_psi"] - p[s + "margin_psi"]
    rx = riser_xy(apt)
    mech = next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/mechanical")
    run = {"main_ft": _manhattan_ft(((mech["lo_m"][0] + mech["hi_m"][0]) / 2, (mech["lo_m"][1] + mech["hi_m"][1]) / 2), rx)}
    for _ in range(12):
        cases = []
        for f in apt["flats"]:
            for comp in layout(apt, p)[f["name"]]["compartments"]:
                d = compartment_demand(apt, p, f["name"], comp, sizes)
                sup = supply(p, d["q_gpm"], d["p_at_riser_floor_psi"], d["z_head_m"], run, sizes)
                cases.append({**d, **sup, "kind": "flat"})
        st = stair_demand(apt, p, sizes)
        cases.append({**st, **supply(p, st["q_gpm"], st["p_at_riser_floor_psi"], st["z_head_m"], run, sizes), "kind": "stair"})
        worst = max(cases, key=lambda x: x["need_psi"])
        if worst["need_psi"] <= target:
            break
        # Upsize the part of the governing run that loses most, if it can grow.
        parts = {"branch": worst.get("branch_psi", 0.0), "riser": worst["riser_main_psi"]}
        key = max(parts, key=parts.get)
        grown = False
        for k in (("branch", "feed") if key == "branch" else ("riser", "main")):
            i = SIZES.index(sizes[k])
            if i + 1 < len(SIZES):
                sizes[k] = SIZES[i + 1]
                grown = True
        if not grown:
            break
    return {"cases": cases, "worst": worst, "sizes": sizes, "target_psi": target,
            "ok": worst["need_psi"] <= target, "water_gal": worst["q_gpm"] * p[s + "duration_min"]}


SIZE_START = {"branch": "1", "feed": "1-1/4", "riser": "2", "main": "2", "backflow": "2"}


def stair_demand(apt: dict, p: dict, sizes: dict) -> dict:
    """The stair's design, read the conservative way: every one of its sprinklers flowing (its
    total area is under NFPA 13's light-hazard design area; whether 13R 7.2.3.1's four-sprinkler
    compartment applies is the authority's call). Each storey's sprinklers on short arms from the
    riser; the top storey's the remote ones."""
    s = "systems.sprinkler."
    c = p[s + "c_cpvc"]
    pipe = cpvc()
    heads = stair_heads(apt, p)
    arm = pipe[sizes["branch"]]
    rise = pipe[sizes["riser"]]
    lo_y, hi_y = apt["stair"]["core_y_m"]
    arm_ft = (hi_y - lo_y) / 4 / FT + p[s + "drop_ft"]
    top = max(h["storey"] for h in heads)
    # The top storey's sprinklers at their least pressure; each storey below takes the pressure the
    # riser gives it: more by the storey's height, less by the riser's friction.
    p_head = max(p[s + "min_head_psi"], max((h["q"] / h["k"]) ** 2 for h in heads if h["storey"] == top))
    q_one = heads[0]["k"] * math.sqrt(p_head)
    per = sum(1 for h in heads if h["storey"] == top)
    pressure = p_head + hw_psi_ft(q_one, arm["id"], c) * (arm_ft + arm["tee_branch"] + arm["elbow"])
    q = q_one * per
    storey_ft = apt["storey_m"] / FT
    for st in range(top - 1, 0, -1):
        pressure += hw_psi_ft(q, rise["id"], c) * (storey_ft + rise["tee_run"]) + 0.433 * storey_ft
        for _ in range(per):
            q += head_flow(pressure, heads[0]["k"], arm_ft + arm["tee_branch"] + arm["elbow"], arm["id"], c)
    z_top = next(h["z_m"] for h in heads if h["storey"] == top)
    # The lower storeys' elevation is already in the pressure; the supply adds it from the lowest.
    z_low = next(h["z_m"] for h in heads if h["storey"] == 1)
    return {"heads": len(heads), "q_gpm": q, "p_at_riser_floor_psi": pressure, "z_head_m": z_low, "z_top_m": z_top,
            "flat": "stair", "comp": "stair", "per_storey": per, "p_remote_psi": p_head, "branch_psi": 0.0}


def annex_demand(apt: dict, p: dict) -> dict:
    """The annex's two rooms (13R 6.6.1: no omission covers mechanical or electrical rooms), one
    quick-response sprinkler each (both under 7.2.3.1's 130 ft2 for ordinary hazard), both
    flowing at the ordinary-hazard density, beside the riser assembly."""
    s = "systems.sprinkler."
    k = p[s + "qr_k"]
    q = 0.0
    p_need = 0.0
    for r in apt["rooms"]["rooms"]:
        if r["id"].startswith("annex/"):
            area = r["area_m2"] / FT ** 2
            p_h = max(p[s + "min_head_psi"], (p[s + "oh_density"] * area / k) ** 2)
            q += k * math.sqrt(p_h)
            p_need = max(p_need, p_h)
    return {"heads": 2, "q_gpm": q, "p_at_riser_floor_psi": p_need, "z_head_m": p[s + "ceiling_m"], "flat": "annex", "comp": "annex",
            "p_remote_psi": p_need, "branch_psi": 0.0}


# ---- The stair's temperature with no heater ----

def stair_temperature(apt: dict, p: dict, party_u: float | None = None, door_u: float | None = None) -> dict:
    """The stair's own heat balance at the design hour with no heater: warmth from the flats on
    its two sides (at room temperature, through the party walls and the flats' 1-hour doors) and
    from the annex behind it; loss through its front wall and its back wall above the annex, their
    windows and the entry door, its roof, its slab's exposed edge, and its air leakage at Phius's
    rate. Its temperature is where they meet; wet sprinkler pipe needs 40 F (13R 5.4.1)."""
    from .loads import CFM_M3H, RHO_CP_AIR
    from .house import BTU_FT, BTU_FT2

    s, e = "systems.sprinkler.", "pass3.envelope."
    party_u = p[s + "party_wall_u"] if party_u is None else party_u
    door_u = p[s + "fire_door_u"] if door_u is None else door_u
    lo_y, hi_y = apt["stair"]["core_y_m"]
    width = hi_y - lo_y
    height = apt["storey_m"] * apt["storeys"]
    length = max(x["hi_m"][0] for x in apt["parts"] if x["kind"] == "party_wall") - min(x["lo_m"][0] for x in apt["parts"] if x["kind"] == "party_wall")
    annex_h = max(x["hi_m"][2] for x in apt["rooms"]["annex"]["parts"] if x["kind"] == "annex_wall")
    stair_open = [o for o in apt["openings"] if o["id"].split("/")[0].endswith("-stair")]
    win = sum(o["width_m"] * o["height_m"] for o in stair_open if o["kind"] == "window")
    door = sum(o["width_m"] * o["height_m"] for o in stair_open if o["kind"] != "window")
    flat_doors = sum(d["width_m"] * d["height_m"] for d in apt["stair"]["doors"] if d.get("flat"))
    wall_u = p["systems.addendum_3.wall_u"] if apt.get("continuous_insulation_m", 0.0) > 0 else p[e + "wall_u"]
    out_walls = width * height + width * (height - annex_h) - win - door
    ua_out = (wall_u * BTU_FT2 * out_walls + apt["glass_u"] * BTU_FT2 * win + p[e + "door_u"] * BTU_FT2 * door
              + p[e + "ceiling_u"] * BTU_FT2 * width * length + p[e + "slab_f"] * BTU_FT * width)
    enclosure_ft2 = (out_walls + win + door + 2 * width * length) / FT ** 2
    leak_cfm = p["systems.phius.airtight_cfm50_ft2"] * enclosure_ft2 / p["pass3.air.n_factor"]
    ua_out += leak_cfm * CFM_M3H * RHO_CP_AIR
    ua_in = party_u * BTU_FT2 * (2 * length * height - flat_doors) + door_u * BTU_FT2 * flat_doors + wall_u * BTU_FT2 * width * annex_h
    t_in, t_out = p["pass3.loads.indoor_c"], p["systems.design.heating_c"]
    t = (ua_in * t_in + ua_out * t_out) / (ua_in + ua_out)
    return {"t_c": t, "t_f": t * 1.8 + 32, "ua_in_w_k": ua_in, "ua_out_w_k": ua_out, "ok": t * 1.8 + 32 >= p[s + "stair_min_f"]}


# ---- 6e: the alarms ----

def alarms(apt: dict, p: dict) -> dict:
    """The smoke alarms, and the sprinkler system's own: a waterflow switch and an exterior
    horn-strobe (903.4.2), tamper switches on its control valves (903.4: electrically supervised by
    a listed fire alarm control unit), the signals sent to a supervising station (903.4.1). The
    panel's battery by its maker's rule: 24 h standby then 5 min of alarm, over its 0.8 factor."""
    s = "systems.sprinkler."
    standby_h, alarm_h = p[s + "facp_standby_h"], p[s + "facp_alarm_min"] / 60.0
    need_ah = (p[s + "facp_standby_a"] * standby_h + (p[s + "facp_alarm_a"] + p[s + "nac_alarm_a"]) * alarm_h) / p[s + "battery_derate"]
    battery = max(p[s + "battery_min_ah"], math.ceil(need_ah))
    return {"smoke": smoke_alarms(apt, p), "need_ah": need_ah, "battery_ah": battery,
            "battery_ok": battery <= p[s + "battery_max_ah"], "tamper_switches": 2, "flow_switches": 1}


# ---- The road not taken: a shared domestic and fire main ----

SHARED_FIXTURES = ("Bathroom group with flush tank (lavatory + water closet + bathtub with shower)", "Kitchen sink",
                   "Dishwasher", "Washing machine")  # a flat's, as step 2 counts them


def shared_main(apt: dict, hyd: dict) -> dict:
    """What a shared domestic and fire main would carry (Jon kept the line separate, 2026-11-21):
    13R 9.3.1 adds the flats' domestic demand where the main serves both, at Table 9.3.2(b)'s flow
    for their fixture load (Table 9.3.2(a), private), interpolated (9.3.2.1)."""
    loads = {r["fixture"]: float(r["load_units"]) for r in _rows("nfpa13r_2019_fixture_loads.csv") if r["facility_class"] == "private"}
    units = len(apt["flats"]) * sum(loads[k] for k in SHARED_FIXTURES)
    pts = [(float(r["load_units"]), float(r["gpm_flush_tanks"])) for r in _rows("nfpa13r_2019_domestic_demand.csv")]
    gpm = next(q0 + (q1 - q0) * (units - u0) / (u1 - u0) for (u0, q0), (u1, q1) in zip(pts, pts[1:]) if u0 <= units <= u1)
    return {"load_units": units, "domestic_gpm": gpm, "total_gpm": hyd["worst"]["q_gpm"] + gpm,
            "flats_gpm": max(c["q_gpm"] for c in hyd["cases"] if c["kind"] == "flat") + gpm}


# ---- The step as data and as text ----

def fdc(apt: dict, p: dict) -> dict:
    """The fire department connection 13R asks (6.11.1: a building over 2,000 ft2 or of more than one
    storey), on the street side (IBC 912.2.1), with a check valve and an automatic drip (6.11.4)."""
    footprint = apt["depth_m"] * apt["length_m"] / FT ** 2
    return {"required": footprint > p["systems.sprinkler.fdc_area_ft2"] or apt["storeys"] > 1, "footprint_ft2": footprint}


def design(apt: dict, p: dict) -> dict:
    """Step 6 for the latest revision."""
    hyd = hydraulics(apt, p)
    ann = annex_demand(apt, p)
    mech = next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/mechanical")
    run = {"main_ft": 0.0}
    ann_sup = supply(p, ann["q_gpm"], ann["p_at_riser_floor_psi"], ann["z_head_m"], run, hyd["sizes"])
    lay = layout(apt, p)
    return {"frame": code_frame(apt, p), "single_exit": single_exit(apt, p), "enclosure": enclosure(apt, p),
            "roof": roof_access(apt, p), "layout": lay, "stair_heads": stair_heads(apt, p), "hydraulics": hyd,
            "annex": {**ann, **ann_sup}, "stair_temp": stair_temperature(apt, p), "alarms": alarms(apt, p), "fdc": fdc(apt, p),
            "shared_main": shared_main(apt, hyd),
            "mech_room": mech["id"]}


def usfa_example() -> dict:
    """The US Fire Administration's worked example ('Commercial Fire Sprinkler System Plans Review'
    student manual, May 2023, unit 7): a K 5.6 sprinkler flowing 15.5 gpm needs (15.5 / 5.6)^2 =
    7.66 psi; Hazen-Williams at 15.5 gpm and C 120 gives 0.081 psi/ft, and over 10.83 ft (a tee 5
    ft, an elbow 2 ft, a 3.83 ft drop) 0.87 psi. Its slide prints the bore as 1.087 in. (a
    thin-wall 1 in. pipe in its own table), but 0.081 is what 1 in. Schedule 40's 1.049 in. (the
    same table's) gives; 1.087 would give 0.068. The worked numbers are reproduced at 1.049."""
    per_ft = hw_psi_ft(15.5, 1.049, 120.0)
    return {"p_head": (15.5 / 5.6) ** 2, "psi_ft": per_ft, "psi": per_ft * 10.83}


def summary(apt: dict, p: dict) -> dict:
    """Step 6 for the latest revision (`apt`), with each known case's check, as data."""
    from .params import load_params

    s = "systems.sprinkler."
    d = design(apt, p)
    ex = usfa_example()
    table = listing() + listing("TY2334")
    k_worst = max(abs(r["k"] * math.sqrt(r["p"]) / r["q"] - 1) for r in table)
    dens_ok = all(r["q"] >= p[s + "min_density"] * r["w"] * r["l"] - 1e-9 for r in table)
    hyd, fr, se, rf, al, st = d["hydraulics"], d["frame"], d["single_exit"], d["roof"], d["alarms"], d["stair_temp"]
    lp = load_params()
    st_low = stair_temperature(apt, p, lp[s + "party_wall_u"].low, lp[s + "fire_door_u"].low)
    flats = [c for c in hyd["cases"] if c["kind"] == "flat"]
    design_ok = all(len(c["design"]) <= p[s + "design_heads_max"] and c["p_remote_psi"] >= p[s + "min_head_psi"] for c in flats)
    lay = d["layout"]
    baths = [r for f in apt["flats"] for r in by_flat(apt)[f["name"]] if r["use"] == "bath"]
    closet_ok = all(any(h["temp"] == "intermediate" for h in v["compartments"].get("utility", [])) for v in lay.values())
    worst = hyd["worst"]
    return {
        "revision": apt.get("revision"),
        "checks": [
            ("Hazen-Williams and Q = K sqrt(P) against the US Fire Administration's worked example: 7.66 psi; 0.081 psi/ft, 0.87 psi "
             "(its bore read as Schedule 40's 1.049 in.; it prints 1.087)",
             abs(ex["p_head"] - 7.66) < 0.005 and abs(ex["psi_ft"] - 0.081) < 0.0005 and abs(ex["psi"] - 0.87) < 0.01,
             f"{ex['p_head']:.2f} psi; {ex['psi_ft']:.4f} psi/ft, {ex['psi']:.3f} psi"),
            ("the residential sprinklers' listings hold to Q = K sqrt(P) and to 13R's 0.05 gpm/ft2 on every coverage",
             k_worst <= 0.01 and dens_ok, f"worst {k_worst:.1%} on {len(table)} rows"),
            ("one exit is allowed (IBC 2021 Table 1006.3.4(1)): three storeys, four flats a storey, travel at most 125 ft",
             se["ok"], f"{max(se['per_storey'].values())} flats a storey, at most {max(se['travel_ft'].values()):.0f} ft"),
            ("NFPA 13R is allowed (903.3.1.2, Pennsylvania's R-2 roof under 45 ft above the fire road); Type V-B is enough with it",
             fr["r13_ok"] and fr["vb_ok"], f"roof {fr['roof_ft']:.0f} ft up; {fr['footprint_ft2']:,.0f} ft2 a storey against 7,000"),
            ("no manual fire alarm system is required (907.2.9.1): no flat three storeys above the exit, 16 flats or fewer",
             not fr["manual_alarm"], f"top flats {fr['top_storeys_above_discharge']} storeys up, {len(apt['flats'])} flats"),
            ("every room sprinklered but baths of 55 ft2 or less (13R 6.6.2); each laundry closet's sprinkler intermediate-temperature",
             all(r["area_m2"] / FT ** 2 <= p[s + "bath_exempt_ft2"] for r in baths) and closet_ok,
             f"{sum(len(v['heads']) for v in lay.values())} in the flats, {len(d['stair_heads'])} in the stair, 2 in the annex"),
            ("every flat compartment's design at most four sprinklers, the remote one at 7 psi or its listing",
             design_ok, f"{len(flats)} compartments"),
            ("the street, less its seasonal margin, covers the governing design (placeholder: the hydrant test decides)",
             hyd["ok"] and d["annex"]["need_psi"] <= hyd["target_psi"],
             f"{worst['flat']} {worst['comp']}: {worst['q_gpm']:.0f} gpm at {worst['need_psi']:.1f} psi against {hyd['target_psi']:.0f}"),
            ("the stair stays above 40 F with no heater, so its pipe can be wet (13R 5.4.1)", st["ok"] and st_low["ok"],
             f"{st['t_f']:.0f} F at the design hour ({st_low['t_f']:.0f} F with the walls' low U)"),
            ("smoke alarms in every bedroom and outside them, each photoelectric one 6 ft or more from the range (907.2.11)",
             al["smoke"]["cooking_ok"], f"{al['smoke']['total']} alarms; the hall's {al['smoke']['hall_to_kitchen_ft']:.1f} ft from the kitchen"),
            ("the sprinkler monitoring panel's battery within the 8-18 Ah it takes (24 h standby, 5 min alarm)", al["battery_ok"],
             f"{al['need_ah']:.1f} Ah needed: {al['battery_ah']} Ah"),
            ("the roof hatch clear of the roof's edge by 10 ft (no guards), of the flats' doors, and the hall's width beside its ladder",
             not rf["guards"] and rf["clear_of_doors"] and rf["hall_ok"],
             f"{rf['edge_ft']:.1f} ft from the edge; {rf['hall_left_in']:.0f} in. of hall beside it"),
        ],
        "design": d,
    }


def report(s: dict) -> str:
    """Step 6 in plain text."""
    from .systems import report as checks

    d = s["design"]
    hyd, en, rf, al, st, se = d["hydraulics"], d["enclosure"], d["roof"], d["alarms"], d["stair_temp"], d["single_exit"]
    w = hyd["worst"]
    lines = [f"Pass 3g step 6: sprinklers and alarms ({s['revision']})", "", checks(s["checks"]), "",
             f"The one stair: four flats a storey, three storeys, at most {max(se['travel_ft'].values()):.0f} ft of travel (125 allowed), "
             "sprinklered (13R) and an escape window in every bedroom (step 1)."]
    lines += ["The stair's enclosure (1-hour): its wall with the annex becomes part of it; under 1023.7 the annex's walls within "
              "10 ft of the stair's unrated windows above it are 1-hour "
              f"({', '.join(x['id'] for x in en['rated_walls'])}, the first {en['rated_walls'][0]['rated_ft']:.0f} ft) and "
              + ", ".join(f"{x['id']} ({x['width_in']:.0f} in., {x['m'] / FT:.1f} ft away)" for x in en["protected_doors"])
              + " a 3/4-hour door."]
    lay = d["layout"]["3-front-left"]
    lines += ["", "Sprinklers (Tyco TY2236 residential pendent, K 4.9), each flat's by compartment: "
              + "; ".join(f"{c} {len(hs)}" for c, hs in lay["compartments"].items()) + "; none in the bath (44 ft2).",
              f"  The stair: {len(d['stair_heads'])} quick-response (K {d['stair_heads'][0]['k']:g}), two a storey; the annex: one in each room.",
              f"  Pipe: CPVC; branch lines {hyd['sizes']['branch']} in., each flat's feed {hyd['sizes']['feed']} in., the riser in the "
              f"stair and the main to the annex {hyd['sizes']['riser']} in.; a {hyd['sizes']['backflow']} in. double check assembly.",
              "  The designs, by what they ask of the street:"]
    for c in sorted(hyd["cases"], key=lambda x: -x["need_psi"])[:6]:
        lines.append(f"    {c['flat']:14s} {c['comp']:8s} {c['q_gpm']:5.1f} gpm, {c['need_psi']:5.1f} psi (the riser and main "
                     f"{c['riser_main_psi']:.1f}, backflow {c['backflow_psi']:.1f}, elevation {c['elevation_psi']:.1f})")
    lines.append(f"  Governing: {w['flat']} {w['comp']}, {w['q_gpm']:.0f} gpm at {w['need_psi']:.1f} psi; {hyd['water_gal']:,.0f} gal over 30 min. "
                 f"The street's 55 psi is a placeholder (the hydrant test).")
    lines += ["", f"The stair with no heater: {st['t_f']:.0f} F at the design hour (flats' side {st['ua_in_w_k']:.0f} W/K, outdoors "
              f"{st['ua_out_w_k']:.0f} W/K).",
              f"Alarms: {al['smoke']['total']} smoke alarms (three a flat); no building fire alarm required; the sprinkler system's flow "
              f"switch, {al['tamper_switches']} tamper switches, an exterior horn-strobe, a monitoring panel sending to a supervising "
              f"station on a {al['battery_ah']} Ah battery.",
              f"Roof hatch: {rf['area_ft2']:.1f} ft2 over the top storey's stair hall, {rf['edge_ft']:.1f} ft from the edge, a fixed ladder "
              f"({rf['hall_left_in']:.0f} in. of hall beside it).",
              f"Fire department connection: required ({d['fdc']['footprint_ft2']:,.0f} ft2, three storeys), on the street side.",
              f"A separate fire service (Jon's decision). A main shared with the taps would add the flats' domestic demand "
              f"(13R 9.3.1: {d['shared_main']['load_units']:.1f} fixture load units, {d['shared_main']['domestic_gpm']:.1f} gpm): "
              f"{d['shared_main']['total_gpm']:.0f} gpm under the stair's reading, {d['shared_main']['flats_gpm']:.0f} for the flats."]
    return "\n".join(lines)
