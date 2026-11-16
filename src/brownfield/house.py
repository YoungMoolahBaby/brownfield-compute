"""Pass 3: the first house's heat. The envelope's areas come from the CortenForge model
(`forge` mode `house` writes out/pass3/house.json); the assemblies, air and loads from
params/pass3.yaml.

    UA = sum(U A) + F P + (infiltration + ventilation) rho c_p          (W/K)
    design load = UA (indoor - design)
    annual heat = UA x degree-hours below the balance point, indoor - gains / UA

and whether a radiant floor can carry the design load on the data center's warm water:

    floor output q = 8.92 (floor surface - room)^1.1 W/m2, floor surface <= 29 C   (EN 1264, as cited)
    mean water - room = q / K_H                                                    (system characteristic)
"""

from __future__ import annotations

import json

import numpy as np

from . import OUT_DIR

BTU_FT2 = 5.678263  # W/m2K per Btu/(h ft2 F)
BTU_FT = 1.730735  # W/mK per Btu/(h ft F)
RHO_CP_AIR = 1.2 * 1005.0 / 3600.0  # Wh per m3 K (0.335)


def envelope() -> dict:
    path = OUT_DIR / "pass3" / "house.json"
    if not path.exists():
        raise SystemExit("no out/pass3/house.json: run `cargo run --release -- house` in forge/ first")
    return json.loads(path.read_text(encoding="utf-8"))


def ua(env: dict, p: dict) -> dict[str, float]:
    """Heat loss coefficient by part (W/K)."""
    e, a = "pass3.envelope.", "pass3.air."
    floor_ft2 = env["floor_m2"] / 0.09290304
    vent_cfm = 0.03 * floor_ft2 + 7.5 * (p[a + "bedrooms"] + 1)  # ASHRAE 62.2-2016 whole-house rate
    vent_m3h = vent_cfm * 1.699011 * (1 - p[a + "hrv_eff"])
    infil_m3h = p[a + "ach50"] / p[a + "n_factor"] * env["interior_volume_m3"]
    return {
        "walls": p[e + "wall_u"] * BTU_FT2 * env["wall_net_m2"],
        "windows": p[e + "window_u"] * BTU_FT2 * env["glazed_m2"],
        "doors": p[e + "door_u"] * BTU_FT2 * env["door_m2"],
        "ceiling": p[e + "ceiling_u"] * BTU_FT2 * env["ceiling_m2"],
        "slab edge": p[e + "slab_f"] * BTU_FT * env["slab_perimeter_m"],
        "infiltration": infil_m3h * RHO_CP_AIR,
        "ventilation": vent_m3h * RHO_CP_AIR,
    }


def heat(env: dict, temp: np.ndarray, p: dict) -> dict:
    parts = ua(env, p)
    total = sum(parts.values())
    indoor = p["pass3.loads.indoor_c"]
    balance = indoor - p["pass3.loads.internal_w"] / total
    hourly_w = total * np.clip(balance - temp, 0, None)
    design_w = total * (indoor - p["pass3.loads.design_c"])
    floor_q = design_w / env["floor_m2"]

    # The radiant floor at the design hour.
    r = "pass3.radiant."
    surface_rise = (floor_q / 8.92) ** (1 / 1.1)
    mean_water = indoor + floor_q / p[r + "k_h"]
    supply = mean_water + p[r + "dt_k"] / 2
    return {
        "ua_parts": parts, "ua_w_k": total, "balance_c": balance,
        "design_kw": design_w / 1e3, "space_mwh": hourly_w.sum() / 1e6,
        "hot_water_mwh": p["pass3.loads.hot_water_mwh"],
        "floor_q_w_m2": floor_q, "floor_surface_c": indoor + surface_rise,
        "floor_ok": indoor + surface_rise <= p[r + "max_floor_c"],
        "supply_c": supply, "return_c": supply - p[r + "dt_k"], "peak_hourly_kw": hourly_w.max() / 1e3,
    }


def report(env: dict, h: dict, dc_supply_c: float) -> str:
    lines = [
        f"The house: {env['width_m']:.2f} x {env['length_m']:.2f} m outside ({env['floor_m2']:.1f} m2 of floor), "
        f"{env['glazed_m2']:.1f} m2 of glazing, {env['door_m2']:.1f} m2 of doors (CortenForge model, forge `house`).",
        "",
        "| Heat loss | W/K | Share |",
        "|---|---|---|",
    ]
    for k, v in h["ua_parts"].items():
        lines.append(f"| {k} | {v:.1f} | {v / h['ua_w_k']:.0%} |")
    lines += [
        f"| **total UA** | **{h['ua_w_k']:.1f}** | |",
        "",
        "| Result | Value |",
        "|---|---|",
        f"| Design load (at the design temperature) | {h['design_kw']:.1f} kW |",
        f"| Biggest hour in the typical year | {h['peak_hourly_kw']:.1f} kW |",
        f"| Balance point (heat needed below) | {h['balance_c']:.1f} C |",
        f"| Space heat a year | {h['space_mwh']:.1f} MWh |",
        f"| Hot water a year | {h['hot_water_mwh']:.1f} MWh |",
        f"| Floor output needed at design | {h['floor_q_w_m2']:.0f} W/m2 |",
        f"| Floor surface at design (limit 29 C) | {h['floor_surface_c']:.1f} C |",
        f"| Water the floor needs at design, supply / return | {h['supply_c']:.1f} / {h['return_c']:.1f} C |",
        f"| The data center's liquid loop: supply / return | {dc_supply_c:.0f} / {dc_supply_c + 10:.0f} C |",
    ]
    return "\n".join(lines)


def apartment() -> dict:
    """forge's 12-flat walk-up (out/pass3/apartment.json)."""
    path = OUT_DIR / "pass3" / "apartment.json"
    if not path.exists():
        raise SystemExit("no out/pass3/apartment.json: run `cargo run --release -- apartment` in forge/ first")
    return json.loads(path.read_text(encoding="utf-8"))


def flats_heat(apt: dict, temp: np.ndarray, p: dict) -> dict:
    """Every flat's heat (party walls and floors between flats lose nothing), and the average flat
    in the shape `heat` returns, for the block model."""
    rows = [(f, heat(f, temp, p)) for f in apt["flats"]]
    n = len(rows)
    mean = {k: sum(h[k] for _, h in rows) / n for k in ("ua_w_k", "design_kw", "space_mwh", "hot_water_mwh",
                                                         "floor_q_w_m2", "supply_c")}
    mean["floor_m2"] = sum(f["floor_m2"] for f, _ in rows) / n
    mean["hardest_supply_c"] = max(h["supply_c"] for _, h in rows)
    return {"flats": rows, "mean": mean}


# Known case: the US housing survey, space heat per household and heated floor area by type.
RECS_2020 = {
    "detached_mmbtu": 44.0,     # EIA RECS 2020 Table CE3.1, single-family detached, space heating, million Btu per household
    "apt5_mmbtu": 9.1,          # same table, apartments in buildings with 5 or more units
    "apt2_4_mmbtu": 22.6,       # same table, apartments in buildings with 2-4 units
    "single_family_ft2": 1951,  # RECS 2020 Table HC10.14, single-family homes, heated square feet (mean)
    "apartment_ft2": 828,       # RECS 2020 Table HC10.15, apartment units, heated square feet (mean)
}


def recs_check(house_h: dict, house_floor_m2: float, flat: dict) -> dict:
    """Space heat per floor area, a flat against the house, beside the same ratio in RECS 2020
    (national, all climates and ages; single-family area includes attached homes)."""
    r = RECS_2020
    sf = r["detached_mmbtu"] / r["single_family_ft2"]
    return {"model": (flat["space_mwh"] / flat["floor_m2"]) / (house_h["space_mwh"] / house_floor_m2),
            "recs_5plus": (r["apt5_mmbtu"] / r["apartment_ft2"]) / sf,
            "recs_2_4": (r["apt2_4_mmbtu"] / r["apartment_ft2"]) / sf}


def flats_report(fh: dict) -> str:
    lines = ["| Flat | Floor m2 | UA W/K | Design kW | Space heat MWh/yr | Floor W/m2 | Water needed C |",
             "|---|---|---|---|---|---|---|"]
    for f, h in fh["flats"]:
        lines.append(f"| {f['name']} | {f['floor_m2']:.1f} | {h['ua_w_k']:.1f} | {h['design_kw']:.2f} | "
                     f"{h['space_mwh']:.2f} | {h['floor_q_w_m2']:.0f} | {h['supply_c']:.1f} |")
    m = fh["mean"]
    lines.append(f"| **average flat** | {m['floor_m2']:.1f} | {m['ua_w_k']:.1f} | {m['design_kw']:.2f} | "
                 f"{m['space_mwh']:.2f} | {m['floor_q_w_m2']:.0f} | {m['supply_c']:.1f} |")
    return "\n".join(lines)
