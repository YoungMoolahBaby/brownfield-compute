"""Pass 3g step 2 (D28): the walk-up's loads, room by room.

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
            "windows": p[e + "window_u"] * BTU_FT2 * x["glazed_m2"],
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

def design_case(apt: dict, p: dict, wall_u: float | None = None) -> dict:
    """The engineered design for `room_heat`: the flats' balanced ventilation with heat recovery
    (`ventilation`, the ERV's sensible recovery a placeholder until step 3), air leakage at Phius's
    0.06 cfm50 per ft2 of each flat's share of the gross enclosure (its outside walls, its roof,
    its floor on the ground) over pass 3's n-factor, the 2025 ASHRAE heating design temperature for
    Indiana County, and the walls at `wall_u` (default: as drawn: Addendum 3's continuous insulation
    where the model has it, `systems.addendum_3.wall_u`, else pass 3's)."""
    if wall_u is None and apt.get("continuous_insulation_m", 0.0) > 0.0:
        wall_u = p["systems.addendum_3.wall_u"]
    vent = ventilation(apt, p)
    flats = {}
    for f in apt["flats"]:
        v = vent[f["name"]]
        ground = f["floor"] == 1
        footprint = f["ceiling_m2"] or (apt["flat_len_m"] * apt["depth_m"] / 2)  # a flat's outline (m2)
        enclosure_ft2 = (f["wall_gross_m2"] + f["ceiling_m2"] + (footprint if ground else 0.0)) / FT2
        cfm50 = p["systems.phius.airtight_cfm50_ft2"] * enclosure_ft2
        flats[f["name"]] = {
            "infil_m3h": cfm50 / p["pass3.air.n_factor"] * CFM_M3H, "vent_m3h": v["design_cfm"] * CFM_M3H,
            "recovery": p["systems.design.erv_sensible_eff"],
            "supply_share": {rid: q / v["design_cfm"] for rid, q in v["supply"].items()},
            **({"wall_u": wall_u} if wall_u is not None else {}),
        }
    return {"flats": flats, "design_c": p["systems.design.heating_c"]}
