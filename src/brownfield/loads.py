"""Pass 3g step 2 (D28): the walk-up's loads, room by room (`brownfield loads`).

- **2a, heat** (below, at length);
- **2b, ventilation** (`ventilation`): IMC 2021 Equation 4-9 and its exhaust table, Phius 2024;
- **2c, cooling** (`room_cooling`, `cooling_design`): every hour of 2005-2023 with PVGIS's sun on
  each wall, at ASHRAE's 0.4% level;
- **2d, water and drainage** (`water`): IPC 2021 Appendix E (Hunter) and Tables 709.1, 710.1;
- **2e, hot water** (`hot_water`): the central plant's design day, by Ecotope's Ecosizer method;
- **2f, electrical** (`electrical`): NEC 2020 220.82 for a flat and 220.84 for the flats, held to
  Holt's 12-unit example.

Each section's sources are in params/systems.yaml and data/.

**2a, heat.** Pass 3b sized each flat's heat as a whole (`house.ua` on forge's `flat_envelope`).
The systems are laid out room by room (forge `rooms`, Addendum 2), so this splits each flat's
envelope among its rooms by what each touches:

- **exterior walls and the slab edge:** by the room's length along the flat's outside walls;
- **windows and the patio door:** the room's own (forge names them on the room);
- **the roof over a top-floor flat:** by floor area;
- **air leakage:** by exterior area (walls and roof);
- **ventilation:** to the rooms the fresh air is supplied to. With an exhaust-only or unknown
  system (pass 3b's case) it comes in everywhere, so by floor area.

Party walls and floors between flats lose nothing, and every room is held at the same indoor
temperature, as pass 3b had it. **The check:** in pass 3b's own case, the rooms of every flat sum to
`house.ua` exactly, part by part.

The radiant floor is then sized per room: the room's design load over its *heated* floor (the
kitchen's cabinets along the plumbing wall and the bath's tub take no tubing), the water a loop
needs for that output, and the floor's surface temperature. One manifold serves a flat, so the
flat's supply water is its hardest room's; the others take less flow. Pass 3b's own floor model and
limits (`pass3.radiant`) are used unchanged.
"""

from __future__ import annotations

from . import house
from .house import BTU_FT, BTU_FT2, RHO_CP_AIR
from .systems import FT, FT2, IN, by_flat

CFM_M3H = 1.699011  # m3/h per cfm
TOL = 1e-6  # m: a room's face on a wall's face


def exposure(apt: dict, r: dict) -> dict[str, float]:
    """A room's length (m) along each outside wall of its flat: the facade ('front' or 'back')
    and the end wall ('left' or 'right'). Interior rooms have none."""
    e, D, L = apt["ext_t_m"], apt["depth_m"], apt["length_m"]
    out = {}
    if abs(r["lo_m"][0] - e) < TOL:
        out["front"] = r["hi_m"][1] - r["lo_m"][1]
    if abs(r["hi_m"][0] - (D - e)) < TOL:
        out["back"] = r["hi_m"][1] - r["lo_m"][1]
    if abs(r["lo_m"][1] - e) < TOL:
        out["left"] = r["hi_m"][0] - r["lo_m"][0]
    if abs(r["hi_m"][1] - (L - e)) < TOL:
        out["right"] = r["hi_m"][0] - r["lo_m"][0]
    return out


def room_envelopes(apt: dict) -> dict[str, list[dict]]:
    """Each flat's rooms, each with its share of the flat's envelope (m, m2), in pass 3b's shape."""
    flats = {f["name"]: f for f in apt["flats"]}
    ops = {o["id"]: o for o in apt["openings"]}
    out = {}
    for name, rooms in by_flat(apt).items():
        f = flats[name]
        ext = {r["id"]: sum(exposure(apt, r).values()) for r in rooms}
        tot_ext, tot_area = sum(ext.values()), sum(r["area_m2"] for r in rooms)
        rows = []
        for r in rooms:
            share = ext[r["id"]] / tot_ext
            glazed = sum(ops[o]["width_m"] * ops[o]["height_m"] for o in r["openings"] if ops[o]["glazed"])
            gross = f["wall_gross_m2"] * share
            rows.append({"room": r, "exposure": exposure(apt, r), "wall_share": share, "area_share": r["area_m2"] / tot_area,
                         "wall_gross_m2": gross, "glazed_m2": glazed, "wall_net_m2": gross - glazed,
                         "ceiling_m2": f["ceiling_m2"] * r["area_m2"] / tot_area,
                         "slab_perimeter_m": f["slab_perimeter_m"] * share})
        out[name] = rows
    return out


def flat_air(f: dict, p: dict, case: dict) -> tuple[float, float]:
    """A flat's natural infiltration and its ventilation air reaching the rooms untempered (m3/h).
    `case`: {"ach50", "n_factor"} or {"infil_m3h"} for leakage; {"vent_m3h", "recovery"} or None
    (pass 3b's: ASHRAE 62.2-2016's rate with no heat recovery, `house.ua`'s own)."""
    a = "pass3.air."
    infil = case["infil_m3h"] if "infil_m3h" in case else case["ach50"] / case["n_factor"] * f["interior_volume_m3"]
    if case.get("vent_m3h") is None:
        floor_ft2 = f["floor_m2"] / 0.09290304
        vent = (0.03 * floor_ft2 + 7.5 * (p[a + "bedrooms"] + 1)) * CFM_M3H * (1 - p[a + "hrv_eff"])
    else:
        vent = case["vent_m3h"] * (1 - case["recovery"])
    return infil, vent


def room_ua(f: dict, rows: list[dict], p: dict, case: dict) -> list[dict]:
    """Each room's heat loss coefficient by part (W/K). Leakage by exterior area; ventilation by the
    case's supply shares ({room id: share}), or by floor area when it has none."""
    e = "pass3.envelope."
    infil, vent = flat_air(f, p, case)
    ext_area = {x["room"]["id"]: x["wall_gross_m2"] + x["ceiling_m2"] for x in rows}
    tot_ext = sum(ext_area.values())
    supply = case.get("supply_share") or {x["room"]["id"]: x["area_share"] for x in rows}
    wall_u = case.get("wall_u", p[e + "wall_u"])
    out = []
    for x in rows:
        rid = x["room"]["id"]
        parts = {
            "walls": wall_u * BTU_FT2 * x["wall_net_m2"],
            "windows": case.get("window_u", p[e + "window_u"]) * BTU_FT2 * x["glazed_m2"],
            "doors": 0.0,  # a flat's door opens into the stair, inside the envelope
            "ceiling": p[e + "ceiling_u"] * BTU_FT2 * x["ceiling_m2"],
            "slab edge": p[e + "slab_f"] * BTU_FT * x["slab_perimeter_m"],
            "infiltration": infil * ext_area[rid] / tot_ext * RHO_CP_AIR,
            "ventilation": vent * supply.get(rid, 0.0) * RHO_CP_AIR,
        }
        out.append({**x, "ua_parts": parts, "ua_w_k": sum(parts.values())})
    return out


def heated_area(apt: dict, r: dict, p: dict) -> float:
    """A room's floor that takes tubing (m2): less the kitchen's cabinets along the plumbing wall
    and the bath's tub."""
    a = r["area_m2"]
    if r["use"] == "kitchen":
        a -= p["systems.design.counter_depth_in"] * IN * (r["hi_m"][1] - r["lo_m"][1])
    elif r["use"] == "bath":
        a -= p["systems.design.tub_length_in"] * p["systems.design.tub_width_in"] * IN * IN
    return a


def room_heat(apt: dict, p: dict, case: dict | None = None) -> dict:
    """The design heat load of every room and the radiant floor it needs; per flat, the hardest
    room and the water the manifold must supply. `case` None is pass 3b's (the check)."""
    case = case or {"ach50": p["pass3.air.ach50"], "n_factor": p["pass3.air.n_factor"]}
    r = "pass3.radiant."
    dt = p["pass3.loads.indoor_c"] - case.get("design_c", p["pass3.loads.design_c"])
    flats = {f["name"]: f for f in apt["flats"]}
    out = {}
    for name, rows in room_envelopes(apt).items():
        rooms = room_ua(flats[name], rows, p, case["flats"][name] if "flats" in case else case)
        for x in rooms:
            w = x["ua_w_k"] * dt
            area = heated_area(apt, x["room"], p)
            q = w / area if area > 0 else 0.0
            x.update({"design_w": w, "heated_m2": area, "floor_q_w_m2": q,
                      "floor_surface_c": p["pass3.loads.indoor_c"] + (q / 8.92) ** (1 / 1.1) if q > 0 else p["pass3.loads.indoor_c"],
                      "supply_c": p["pass3.loads.indoor_c"] + q / p[r + "k_h"] + p[r + "dt_k"] / 2 if q > 0 else None})
        need = [x for x in rooms if x["supply_c"] is not None]
        hardest = max(need, key=lambda x: x["supply_c"])
        out[name] = {"rooms": rooms, "design_w": sum(x["design_w"] for x in rooms), "ua_w_k": sum(x["ua_w_k"] for x in rooms),
                     "hardest": hardest["room"]["id"], "supply_c": hardest["supply_c"],
                     "max_surface_c": max(x["floor_surface_c"] for x in rooms)}
    return out


def check_against_pass3b(apt: dict, p: dict) -> tuple[bool, float]:
    """Pass 3b's case: every flat's rooms sum to `house.ua` of the flat, part by part (W/K)."""
    rh = room_heat(apt, p)
    worst = 0.0
    for f in apt["flats"]:
        want = house.ua(f, p)
        got = {k: sum(x["ua_parts"][k] for x in rh[f["name"]]["rooms"]) for k in want}
        worst = max(worst, max(abs(got[k] - want[k]) for k in want))
    return worst < 1e-9, worst


# ---- 2b, ventilation: each flat's air, room by room ----

def ventilation(apt: dict, p: dict) -> dict[str, dict]:
    """Each flat's ventilation (cfm), designed balanced with heat recovery:

    - **the code's floor (IMC 2021 403.3.2.1, Equation 4-9):** 0.01 cfm per ft2 plus 7.5 per
      bedroom-plus-one, continuous;
    - **the code's exhaust (Table 403.3.2.3):** 25 cfm continuous from the kitchen, 20 from the
      bath;
    - **Phius (2024 Guidebook 1.3.4.2):** 15 cfm per occupant supplied, with outdoor air to every
      bedroom; occupants are bedrooms + 1; the flat's rate is the larger of the supply and the
      exhaust requirement; supply and exhaust within 10%.

    Supply goes to the bedrooms by their occupants, any more to the living room; air passes from
    there through the hall and the living room to the kitchen and the bath, which exhaust it. The
    utility closet takes any exhaust beyond those two."""
    c, ph = "systems.code.vent.", "systems.phius."
    out = {}
    for name, rooms in by_flat(apt).items():
        f = next(x for x in apt["flats"] if x["name"] == name)
        beds = [r for r in rooms if r["use"] == "bedroom"]
        nbr = max(len(beds), 1)
        floor_ft2 = f["floor_m2"] / FT2
        occupants = nbr + p[ph + "extra_occupants"]
        imc = p[c + "area_cfm_per_ft2"] * floor_ft2 + p[c + "per_occupant_cfm"] * (nbr + 1)
        exhaust_req = p[c + "kitchen_cfm"] + p[c + "bath_cfm"]
        supply_req = p[ph + "supply_cfm_per_person"] * occupants
        design = max(imc, exhaust_req, supply_req)
        # Supply: each bedroom by its occupants (the larger bedroom has bed_1_occupants), the rest to
        # the living room.
        occ = {r["id"]: (p["systems.design.bed_1_occupants"] if r["id"].endswith("/bed-1") else 1.0) for r in beds}
        scale = occupants / sum(occ.values())
        supply = {rid: p[ph + "supply_cfm_per_person"] * n * scale for rid, n in occ.items()}
        living = next(r["id"] for r in rooms if r["use"] == "living")
        supply[living] = supply.get(living, 0.0) + design - sum(supply.values())
        kitchen = next(r["id"] for r in rooms if r["use"] == "kitchen")
        bath = next(r["id"] for r in rooms if r["use"] == "bath")
        utility = next(r["id"] for r in rooms if r["use"] == "utility")
        exhaust = {kitchen: p[c + "kitchen_cfm"], bath: p[c + "bath_cfm"]}
        exhaust[utility] = design - sum(exhaust.values())
        out[name] = {"floor_ft2": floor_ft2, "bedrooms": nbr, "occupants": occupants, "imc_cfm": imc,
                     "exhaust_req_cfm": exhaust_req, "supply_req_cfm": supply_req, "design_cfm": design,
                     "supply": {k: v for k, v in supply.items() if v > 1e-9},
                     "exhaust": {k: v for k, v in exhaust.items() if v > 1e-9}}
    return out


def ventilation_checks(apt: dict, p: dict, vent: dict) -> list[tuple[str, bool, str]]:
    res = []
    add = lambda label, ok, detail: res.append((label, bool(ok), detail))  # noqa: E731
    beds = {name: [r["id"] for r in rooms if r["use"] == "bedroom"] for name, rooms in by_flat(apt).items()}
    worst_imc = min(v["design_cfm"] - v["imc_cfm"] for v in vent.values())
    add("each flat's ventilation at least the IMC's (2021 403.3.2.1, Equation 4-9)", worst_imc >= -1e-9,
        f"design {min(v['design_cfm'] for v in vent.values()):.1f} cfm against at most {max(v['imc_cfm'] for v in vent.values()):.1f}")
    c = "systems.code.vent."
    low_ex = [n for n, v in vent.items() if not any(r.endswith("/kitchen") and q >= p[c + "kitchen_cfm"] - 1e-9 for r, q in v["exhaust"].items())
              or not any(r.endswith("/bath") and q >= p[c + "bath_cfm"] - 1e-9 for r, q in v["exhaust"].items())]
    add("each kitchen and bath exhausts the IMC's continuous rate (Table 403.3.2.3)", not low_ex,
        f"{p[c + 'kitchen_cfm']:g} and {p[c + 'bath_cfm']:g} cfm" + (f"; short: {low_ex}" if low_ex else ""))
    no_air = [b for n, v in vent.items() for b in beds[n] if v["supply"].get(b, 0.0) <= 0]
    add("outdoor air supplied to every bedroom (Phius 1.3.4.2)", not no_air, f"{sum(len(b) for b in beds.values())} bedrooms, {len(no_air)} without")
    ph = "systems.phius."
    short = [n for n, v in vent.items() if sum(v["supply"].values()) < p[ph + "supply_cfm_per_person"] * v["occupants"] - 1e-9]
    add("at least 15 cfm per occupant supplied, occupants bedrooms + 1 (Phius)", not short,
        f"{min(sum(v['supply'].values()) / v['occupants'] for v in vent.values()):.1f} cfm per occupant")
    off = max(abs(sum(v["supply"].values()) - sum(v["exhaust"].values())) / max(sum(v["supply"].values()), 1e-9) for v in vent.values())
    add("supply and exhaust balanced within 10% (Phius 1.3.4.2)", off <= p[ph + "balance"], f"worst {off:.1%}")
    return res


# ---- The engineered design's case ----

def erv_sensible(p: dict, t_c: float) -> float:
    """The ERV's sensible recovery at an outdoor temperature: a straight line between HVI's two
    tests of the unit (`systems.erv`, 32 F and -13 F, the latter over its defrost cycles), held at
    their values beyond them."""
    t_f = t_c * 1.8 + 32
    hi, lo = p["systems.erv.sre_32f"], p["systems.erv.sre_m13f"]
    return lo + (hi - lo) * min(max((t_f + 13) / 45, 0.0), 1.0)


def preheat_c(p: dict) -> float:
    """The setpoint of the electric preheater ahead of each ERV: at least Broan's 0 C, below which
    the unit defrosts by stopping its supply fan, and warm enough that the ERV's supply reaches
    PHI's minimum (`supply_min_c`) at the recovery HVI measured at 32 F."""
    sre, t_in = p["systems.erv.sre_32f"], p["pass3.loads.indoor_c"]
    return max(p["systems.erv.preheat_min_c"], (p["systems.erv.supply_min_c"] - sre * t_in) / (1 - sre))


def design_case(apt: dict, p: dict, wall_u: float | None = None, preheat: bool = False) -> dict:
    """The engineered design for `room_heat`: the flats' balanced ventilation with heat recovery
    (`ventilation`, the ERV's sensible recovery at the design temperature, `erv_sensible`), air leakage at Phius's
    0.06 cfm50 per ft2 of each flat's share of the gross enclosure (its outside walls, its roof,
    its floor on the ground) over pass 3's n-factor, the 2025 ASHRAE heating design temperature for
    Indiana County, and the walls at `wall_u` (default: as drawn: Addendum 3's continuous insulation
    where the model has it, `systems.addendum_3.wall_u`, else pass 3's), the windows at Addendum 4's
    U-factor where the model has it (`glass_u`), else pass 3's.

    With `preheat` (step 3's design), an electric heater warms the outdoor air ahead of the ERV to
    `preheat_c`: the ERV never defrosts, so it stays balanced, and its supply reaches PHI's minimum;
    the rooms see only what is left, and each flat's case carries the heater's power (`preheat_w`).
    """
    if wall_u is None and apt.get("continuous_insulation_m", 0.0) > 0.0:
        wall_u = p["systems.addendum_3.wall_u"]
    vent = ventilation(apt, p)
    t_out, t_in = p["systems.design.heating_c"], p["pass3.loads.indoor_c"]
    t_core = max(t_out, preheat_c(p)) if preheat else t_out  # the air entering the ERV
    supply_c = t_core + erv_sensible(p, t_core) * (t_in - t_core)
    recovery = (supply_c - t_out) / (t_in - t_out)  # what the rooms see, as a recovery from outdoors
    flats = {}
    for f in apt["flats"]:
        v = vent[f["name"]]
        ground = f["floor"] == 1
        footprint = f["ceiling_m2"] or (apt["flat_len_m"] * apt["depth_m"] / 2)  # a flat's outline (m2)
        enclosure_ft2 = (f["wall_gross_m2"] + f["ceiling_m2"] + (footprint if ground else 0.0)) / FT2
        cfm50 = p["systems.phius.airtight_cfm50_ft2"] * enclosure_ft2
        flats[f["name"]] = {
            "infil_m3h": cfm50 / p["pass3.air.n_factor"] * CFM_M3H, "vent_m3h": v["design_cfm"] * CFM_M3H,
            "recovery": recovery,
            "supply_c": supply_c, "preheat_w": v["design_cfm"] * CFM_M3H * RHO_CP_AIR * (t_core - t_out),
            "supply_share": {rid: q / v["design_cfm"] for rid, q in v["supply"].items()},
            **({"wall_u": wall_u} if wall_u is not None else {}),
            **({"window_u": apt["glass_u"]} if apt.get("glass_u") is not None else {}),  # Addendum 4's glass
        }
    return {"flats": flats, "design_c": p["systems.design.heating_c"]}


# ---- 2c, cooling: each room's sensible load, hour by hour ----

FACES = ("front", "back", "left", "right")
COMPASS = {0: "N", 90: "E", 180: "S", 270: "W"}


def facing(front_az: int) -> dict[str, str]:
    """Which way each face looks when the front faces `front_az` (degrees clockwise from north).
    In the model's frame (x from the front to the back, y along, z up, right-handed) +x is the back
    and +y lies 90 degrees clockwise of the front's outward normal: the right end."""
    return {"front": COMPASS[front_az % 360], "back": COMPASS[(front_az + 180) % 360],
            "right": COMPASS[(front_az + 90) % 360], "left": COMPASS[(front_az + 270) % 360]}


def sat_pressure_pa(t_c):
    """Saturation vapour pressure over water (Pa), the Magnus form of Alduchov and Eskridge (1996),
    J. Appl. Meteor. 35: 601-609."""
    import numpy as np

    return 610.94 * np.exp(17.625 * np.asarray(t_c) / (np.asarray(t_c) + 243.04))


def humidity_ratio(db_c: float, wb_c: float, p_pa: float) -> float:
    """kg of water per kg of dry air from dry and wet bulb at pressure `p_pa`: the psychrometric
    relation of the ASHRAE Handbook - Fundamentals ch. 1 (SI), with `sat_pressure_pa`."""
    ws = 0.621945 * sat_pressure_pa(wb_c) / (p_pa - sat_pressure_pa(wb_c))
    return float(((2501 - 2.326 * wb_c) * ws - 1.006 * (db_c - wb_c)) / (2501 + 1.86 * db_c - 4.186 * wb_c))


def weather(p: dict, site: tuple[float, float] | None = None) -> dict:
    """PVGIS's 2005-2023 hours at the site (ERA5: the air and the sun on each wall), the air shifted
    so its 0.4% hour meets ASHRAE's 2025 0.4% cooling dry bulb for Indiana County: ERA5 smooths
    the hottest hours (`systems.design.cooling_db_c`)."""
    import numpy as np

    from . import climate
    from .land import PLANT  # the plant's coordinates (EIA-860), pass 1

    w = climate.pvgis_walls(*(site or PLANT))
    shift = p["systems.design.cooling_db_c"] - float(np.percentile(w["t"], 99.6))
    return {**w, "t": w["t"] + shift, "shift_k": shift}


def room_cooling(apt: dict, p: dict, wx: dict | None = None, front_az: int = 180) -> dict:
    """Every room's sensible cooling load (W), every hour of `wx`, with the front facing `front_az`:
    - conduction through its walls, windows and roof share at the hour's air temperature (the slab
      edge, against the cooler ground, left out);
    - sun through its windows and patio door: glazed area x SHGC x the hour's sunlight on that wall
      (PVGIS's own transposition, beam, sky and ground), no shading counted;
    - leakage and its ventilation supply, the ERV's sensible recovery on the air it supplies;
    - internal gains, the IECC reference design's IGain for the flat spread by floor area, as a
      steady rate.
    Indoors at the IECC's 75 F. Room by room and the flat's sum, both hour by hour."""
    import numpy as np

    wx = wx or weather(p)
    t_in = (p["systems.design.cooling_indoor_f"] - 32) / 1.8
    case = design_case(apt, p)
    flats = {f["name"]: f for f in apt["flats"]}
    ops = {o["id"]: o for o in apt["openings"]}
    face_dir = facing(front_az)
    shgc = apt.get("glass_shgc", p["systems.design.shgc"])  # Addendum 4's glass, else the placeholder
    dt = wx["t"] - t_in
    out = {}
    for name, rows in room_envelopes(apt).items():
        f, c = flats[name], case["flats"][name]
        parts = room_ua(f, rows, p, c)
        nbr = sum(r["room"]["use"] == "bedroom" for r in rows)
        igain_w = (p["systems.design.igain_btu_day"] + p["systems.design.igain_btu_day_per_ft2"] * f["floor_m2"] / FT2
                   + p["systems.design.igain_btu_day_per_bedroom"] * nbr) / 24 / 3.412142
        rooms = {}
        for x in parts:
            r, ua = x["room"], x["ua_parts"]
            cond = (ua["walls"] + ua["windows"] + ua["ceiling"]) * dt
            air = (ua["infiltration"] + ua["ventilation"]) * dt  # recovery already in the ventilation part
            sun = np.zeros_like(dt)
            for oid in r["openings"]:
                o = ops[oid]
                if o["glazed"]:
                    sun = sun + shgc * o["width_m"] * o["height_m"] * wx[face_dir[o["face"]]]
            rooms[r["id"]] = cond + air + sun + igain_w * x["area_share"]
        out[name] = {"rooms": rooms, "flat": sum(rooms.values())}
    return out


def cooling_design(apt: dict, p: dict, pct: float = 99.6) -> dict:
    """The design sensible cooling load, the hour exceeded 0.4% of the time (ASHRAE's design
    level), for every room and every flat, the worst of the four ways the building could face; and
    the outdoor air's latent load at ASHRAE's 0.4% dry bulb and coincident wet bulb."""
    import numpy as np

    wx = weather(p)
    rooms, flats = {}, {}
    for az in (0, 90, 180, 270):
        rc = room_cooling(apt, p, wx, az)
        for name, v in rc.items():
            q = float(np.percentile(v["flat"], pct))
            if q > flats.get(name, (-1, None))[0]:
                flats[name] = (q, COMPASS[az])
            for rid, series in v["rooms"].items():
                q = float(np.percentile(series, pct))
                if q > rooms.get(rid, (-1, None))[0]:
                    rooms[rid] = (q, COMPASS[az])
    # Latent, the outdoor air: leakage plus ventilation, the ERV's moisture recovery on the latter.
    P = p["systems.design.station_pressure_pa"]
    t_in = (p["systems.design.cooling_indoor_f"] - 32) / 1.8
    w_out = humidity_ratio(p["systems.design.cooling_db_c"], p["systems.design.cooling_wb_c"], P)
    pw_in = p["systems.design.cooling_indoor_rh"] * float(sat_pressure_pa(t_in))
    w_in = 0.621945 * pw_in / (P - pw_in)
    case = design_case(apt, p)
    rho = P / (287.055 * (t_in + 273.15))  # dry air at the indoor temperature, kg/m3
    latent = {}
    for name, c in case["flats"].items():
        m3s = (c["infil_m3h"] + c["vent_m3h"] * (1 - p["systems.erv.nmt_95f"])) / 3600
        latent[name] = m3s * rho * max(w_out - w_in, 0.0) * 2.45e6
    return {"rooms": rooms, "flats": flats, "latent": latent, "shift_k": wx["shift_k"], "w_out": w_out, "w_in": w_in}


# ---- 2d, water and drainage ----

def _table(name: str) -> list[dict]:
    import csv

    from . import ROOT

    with (ROOT / "data" / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def hunter_gpm(wsfu: float) -> float:
    """Demand (gpm) for a load in water supply fixture units, flush tanks: IPC 2021 Table E103.3(3)
    (data/ipc2021_hunter_flush_tank.csv), straight lines between its rows."""
    rows = [(float(r["wsfu"]), float(r["gpm"])) for r in _table("ipc2021_hunter_flush_tank.csv")]
    if wsfu <= rows[0][0]:
        return rows[0][1] * wsfu / rows[0][0]
    for (u0, q0), (u1, q1) in zip(rows, rows[1:]):
        if wsfu <= u1:
            return q0 + (q1 - q0) * (wsfu - u0) / (u1 - u0)
    raise ValueError(f"{wsfu} wsfu: past the table")


def pipe_for(dfu: float, column: str, least: float = 3.0) -> float:
    """The smallest pipe (in.) whose column in IPC 2021 Table 710.1(1)/(2) (data/ipc2021_drains.csv)
    takes `dfu`, no smaller than `least` (a drain serving a water closet: 3 in., 710.1(1))."""
    for r in _table("ipc2021_drains.csv"):
        if float(r["size_in"]) >= least and r[column] and float(r[column]) >= dfu:
            return float(r["size_in"])
    raise ValueError(f"{dfu} dfu: no pipe in {column}")


def water(apt: dict, p: dict) -> dict:
    """Each flat's fixtures (a bathroom group in its bath; a kitchen sink and a dishwasher in its
    kitchen; a clothes washer in its utility closet), their water supply fixture units (IPC 2021
    Table E103.3(2)) and drainage fixture units (Table 709.1); the demand (Table E103.3(3)) of a
    flat, a stack of flats (one over another), half the building (the stair splits it) and the
    building, total, cold and hot; and the drains: each flat's branch, each stack, the building
    drain at 1/8 and 1/4 in. per ft (Tables 710.1(1)-(2), 3 in. at least)."""
    pl = "systems.plumbing."
    flats = by_flat(apt)
    per = {}
    for name, rooms in flats.items():
        uses = [r["use"] for r in rooms]
        n_bath, n_kitchen, n_washer = uses.count("bath"), uses.count("kitchen"), uses.count("utility")
        cold = n_bath * p[pl + "wsfu_bath_group_cold"] + n_kitchen * p[pl + "wsfu_kitchen_sink_each"] + n_washer * p[pl + "wsfu_washer_each"]
        hot = (n_bath * p[pl + "wsfu_bath_group_hot"] + n_kitchen * (p[pl + "wsfu_kitchen_sink_each"] + p[pl + "wsfu_dishwasher"])
               + n_washer * p[pl + "wsfu_washer_each"])
        total = (n_bath * p[pl + "wsfu_bath_group"] + n_kitchen * (p[pl + "wsfu_kitchen_sink"] + p[pl + "wsfu_dishwasher"])
                 + n_washer * p[pl + "wsfu_washer"])
        dfu = n_bath * p[pl + "dfu_bath_group"] + n_kitchen * p[pl + "dfu_kitchen"] + n_washer * p[pl + "dfu_washer"]
        per[name] = {"wsfu": total, "cold": cold, "hot": hot, "dfu": dfu}
    flat = next(iter(per.values()))
    if any(v != flat for v in per.values()):
        raise ValueError("the flats' fixtures differ: size them one by one")
    storeys = apt["storeys"]
    groups = {"a flat": 1, "a stack (one flat a storey)": storeys, "half the building": len(per) // 2, "the building": len(per)}
    demand = {g: {k: hunter_gpm(n * flat[k]) for k in ("wsfu", "cold", "hot")} for g, n in groups.items()}
    stack_dfu = storeys * flat["dfu"]
    drains = {
        "flat branch": pipe_for(flat["dfu"], "branch"),
        "stack": max(pipe_for(stack_dfu, "stack_3_intervals"), pipe_for(flat["dfu"], "stack_one_interval")),
        "half-building drain, 1/8 in/ft": pipe_for(len(per) // 2 * flat["dfu"], "drain_1_8"),
        "building drain, 1/8 in/ft": pipe_for(len(per) * flat["dfu"], "drain_1_8"),
        "building drain, 1/4 in/ft": pipe_for(len(per) * flat["dfu"], "drain_1_4"),
    }
    return {"per_flat": flat, "groups": groups, "demand_gpm": demand, "stack_dfu": stack_dfu,
            "building_dfu": len(per) * flat["dfu"], "drains_in": drains}


# ---- 2e, hot water: the central plant's design day ----

def hot_water(apt: dict, p: dict) -> dict:
    """The design day for the central heat-pump water heater, by Ecotope's Ecosizer method: people
    x the 98th-percentile day's gallons per person at 120 F, its busiest hour's share (the
    Ecosizer engine's multifamily load shape), the heat to raise it from the cold inlet, and the
    recirculation loop's loss per flat. The cold inlet is the mains' coldest day by Burch and
    Christensen's correlation (`plumbing.mains_f`). Sizing the plant is step 4 (`plumbing.design`)."""
    from .plumbing import mains_f

    h = "systems.hot_water."
    n = len(apt["flats"])
    people = n * p[h + "occupants_per_flat"]
    day_gal = people * p[h + "gpd_per_person"]
    peak_gal = day_gal * p[h + "peak_hour_fraction"]
    inlet_f = mains_f(p)["design_f"]
    dT_f = p[h + "supply_f"] - inlet_f
    btu_per_gal = 8.34 * dT_f  # lb per gallon x F
    return {"flats": n, "people": people, "day_gal": day_gal, "peak_hour_gal": peak_gal,
            "day_kwh": day_gal * btu_per_gal / 3412.142, "peak_hour_kw": peak_gal * btu_per_gal / 3412.142,
            "recirc_kw": n * p[h + "recirc_w_per_flat"] / 1e3, "inlet_f": inlet_f}


# ---- 2f, electrical: NEC 2020 Article 220 ----

def nec_220_84(units: int, ft2: float, appliances_va: list[float], heat_va: float, cooling_va: float,
               p: dict, factor: float | None = None) -> dict:
    """The optional calculation for a multifamily building (220.84), as Holt works it: per unit,
    3 VA per ft2, two small-appliance circuits and the laundry circuit, every appliance's nameplate,
    and the larger of space heating and air conditioning; times the units; times Table 220.84's
    factor (`factor`, else the 12-unit 0.41 from params). House loads are added apart (Part III)."""
    e = "systems.electrical."
    general = ft2 * p[e + "general_va_per_ft2"] + p[e + "small_appliance_va"] + p[e + "laundry_va"]
    per_unit = general + sum(appliances_va) + max(heat_va, cooling_va)
    connected = units * per_unit
    f = p[e + "demand_factor_12_units"] if factor is None else factor
    return {"per_unit_va": per_unit, "connected_va": connected, "factor": f, "calculated_va": connected * f,
            "amps_240_1ph": connected * f / 240.0, "amps_208_3ph": connected * f / (208.0 * 3 ** 0.5)}


def nec_220_82(ft2: float, appliances_va: list[float], cooling_va: float, p: dict) -> dict:
    """One flat's feeder by the optional dwelling calculation (220.82): its load less heating and
    cooling, the first 10 kVA at 100% and the rest at 40%; then air conditioning at 100%."""
    e = "systems.electrical."
    general = ft2 * p[e + "general_va_per_ft2"] + p[e + "small_appliance_va"] + p[e + "laundry_va"] + sum(appliances_va)
    calc = min(general, 10000.0) + 0.4 * max(general - 10000.0, 0.0) + cooling_va
    return {"connected_less_hvac_va": general, "calculated_va": calc, "amps_240": calc / 240.0}


def holt_example(p: dict) -> dict:
    """The known case (Holt, EC&M 2009): 12 units of 1,500 ft2, each with a 1.5 kVA dishwasher,
    a 4.0 kVA water heater, a 4.5 kVA dryer and a 14.4 kVA range (the washer on the laundry
    circuit), 3.91 kVA of air conditioning against 5.0 kVA of heat: 460,800 VA connected,
    188,928 VA calculated, 787 A at 240 V."""
    return nec_220_84(12, 1500, [1500, 4000, 4500, 14400], 5000, 3910, p)


def electrical(apt: dict, p: dict) -> dict:
    """The flats' load: each flat's feeder (220.82), and the flats together for the service (220.84).
    The flats have no electric space heat (the radiant floors run on the warm loop) and a heat pump
    for cooling; no water heater (the plant is central, a house load). The appliances are step 5's
    (`electrical.APPLIANCES`, at their 208 V nameplates); step 5 adds the house loads."""
    from .electrical import APPLIANCES, appliance_va, hvac_va

    e = "systems.electrical."
    ft2 = apt["flats"][0]["floor_m2"] / FT2
    appliances = [appliance_va(p, k) for k in APPLIANCES]
    return {"flat_ft2": ft2, "flat_feeder": nec_220_82(ft2, appliances, hvac_va(p, 0.65), p),
            "flats_220_84": nec_220_84(len(apt["flats"]), ft2, appliances, appliance_va(p, "preheater"), p[e + "cooling_va"], p)}


# ---- The step's summary ----

def summary(apt: dict, p: dict) -> dict:
    """Step 2's loads for the latest revision (`apt`), with each known case's check, as data."""
    ok3b, worst3b = check_against_pass3b(apt, p)
    base = room_heat(apt, p)
    design = room_heat(apt, p, design_case(apt, p))
    vent = ventilation(apt, p)
    cool = cooling_design(apt, p)
    holt = holt_example(p)
    return {
        "revision": apt.get("revision"),
        "checks": [
            ("rooms sum to pass 3b's flats (house.ua), part by part", ok3b, f"worst {worst3b:.1e} W/K"),
            *ventilation_checks(apt, p, vent),
            ("NEC 220.84 against Holt's 12-unit example (EC&M 2009): 460,800 VA, 188,928 VA, 787 A",
             (holt["connected_va"], round(holt["calculated_va"]), round(holt["amps_240_1ph"])) == (460800, 188928, 787),
             f"{holt['connected_va']:,.0f} VA, {holt['calculated_va']:,.0f} VA, {holt['amps_240_1ph']:.0f} A"),
            ("Hunter's curve (IPC E103.3(3)) through its own rows", [hunter_gpm(u) for u in (1, 20, 100)] == [3.0, 19.6, 43.5], "1, 20, 100 wsfu"),
        ],
        "heat": {n: {"design_w": design[n]["design_w"], "pass3b_case_w": base[n]["design_w"], "hardest": design[n]["hardest"],
                     "supply_c": design[n]["supply_c"], "pass3b_case_supply_c": base[n]["supply_c"],
                     "rooms": {x["room"]["id"]: {"w": x["design_w"], "w_m2": x["floor_q_w_m2"], "supply_c": x["supply_c"]}
                               for x in design[n]["rooms"]}} for n in design},
        "ventilation": vent,
        "cooling": {"flats": cool["flats"], "rooms": cool["rooms"], "latent_w": cool["latent"], "era5_shift_k": cool["shift_k"]},
        "water": water(apt, p),
        "hot_water": hot_water(apt, p),
        "electrical": electrical(apt, p),
    }


def report(s: dict) -> str:
    """Step 2 in plain text."""
    from .systems import report as checks

    heat, cool, w, hw, el = s["heat"], s["cooling"], s["water"], s["hot_water"], s["electrical"]
    lines = [f"Pass 3g step 2: the walk-up's loads, room by room ({s['revision']})", "", checks(s["checks"]), "",
             "Heat (design, -16.3 C), engineered design (ERV, Phius airtightness) against pass 3b's case:"]
    for n in sorted(heat, key=lambda n: (n[0], n)):
        h = heat[n]
        lines.append(f"  {n:14s} {h['design_w']:5.0f} W (pass 3b's case {h['pass3b_case_w']:5.0f}); the floor water "
                     f"{h['supply_c']:.1f} C, set by {h['hardest'].split('/')[1]} ({h['pass3b_case_supply_c']:.1f} C)")
    v = next(iter(s["ventilation"].values()))
    lines += ["", f"Ventilation, each flat: {v['design_cfm']:.0f} cfm balanced (IMC {v['imc_cfm']:.1f}; Phius {v['supply_req_cfm']:.0f} supplied; "
              f"exhaust {v['exhaust_req_cfm']:.0f}); supply " + ", ".join(f"{k.split('/')[1]} {q:.0f}" for k, q in v["supply"].items())
              + "; exhaust " + ", ".join(f"{k.split('/')[1]} {q:.0f}" for k, q in v["exhaust"].items()) + " cfm", "",
              f"Cooling (0.4% hour of 2005-2023, ERA5 shifted {cool['era5_shift_k']:+.2f} K to ASHRAE's 30.9 C; worst of four facings):"]
    for n in sorted(cool["flats"], key=lambda n: (n[0], n)):
        q, d = cool["flats"][n]
        lines.append(f"  {n:14s} {q:5.0f} W sensible ({q * 3.412142 / 12000:.2f} ton), worst facing {d}; outdoor air latent {cool['latent_w'][n]:.0f} W")
    r = {k.split("/")[1]: v for k, v in cool["rooms"].items() if k.startswith("2-front-left/")}
    lines.append("  rooms of 2-front-left: " + ", ".join(f"{k} {q:.0f} W ({d})" for k, (q, d) in r.items()))
    pf = w["per_flat"]
    lines += ["", f"Water: a flat {pf['wsfu']:.1f} wsfu (cold {pf['cold']:.1f}, hot {pf['hot']:.1f}), {pf['dfu']:.0f} dfu. Demand (Hunter, IPC E103.3(3)):"]
    for g, d in w["demand_gpm"].items():
        lines.append(f"  {g:28s} {d['wsfu']:5.1f} gpm (cold {d['cold']:.1f}, hot {d['hot']:.1f})")
    lines.append("  drains (IPC 710.1): " + ", ".join(f"{k} {v:g} in." for k, v in w["drains_in"].items())
                 + f"; a stack {w['stack_dfu']:.0f} dfu, the building {w['building_dfu']:.0f}")
    lines += ["", f"Hot water, the design day (Ecosizer): {hw['people']:.0f} people, {hw['day_gal']:.0f} gal at 120 F, the busiest hour "
              f"{hw['peak_hour_gal']:.0f} gal ({hw['peak_hour_kw']:.1f} kW of heat); {hw['day_kwh']:.0f} kWh a day; recirculation "
              f"{hw['recirc_kw']:.1f} kW", ""]
    f, b = el["flat_feeder"], el["flats_220_84"]
    lines += [f"Electrical (NEC 2020 Article 220; step 5's appliances): a flat's feeder (220.82) {f['calculated_va']:,.0f} VA, "
              f"{f['amps_240']:.0f} A at 240 V; the 12 flats (220.84) {b['connected_va']:,.0f} VA connected x {b['factor']:g} = "
              f"{b['calculated_va']:,.0f} VA, {b['amps_240_1ph']:.0f} A at 120/240 V or {b['amps_208_3ph']:.0f} A at 208Y/120 V, "
              "before house loads (step 5: `brownfield electrical`)."]
    return "\n".join(lines)
