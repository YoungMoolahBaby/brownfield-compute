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
