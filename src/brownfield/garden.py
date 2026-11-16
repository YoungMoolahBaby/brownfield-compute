"""Pass 3c: the winter garden's numbers (D9). Geometry from forge `garden` (out/pass3/garden.json).

- Heat: the two glass rooms' heat loss, hourly over the PVGIS typical year (UA x the hours below
  the set point), with no solar or internal gains (an upper bound), at a temperate and a warm set
  point; then the radiant stone floors at the design hour by EN 1264's characteristic
  q = 8.92 (floor - room)^1.1 W/m2 (floor surface <= 29 C) and pass 3's water-to-floor coefficient,
  against the data center loop's warm water.
- The cantilever: level 1's terrace as a reinforced concrete strip, ACI 318-19: strength
  (Mu <= phi As fy (d - a/2)), and deflection with the effective moment of inertia (Bischoff's
  form, 24.2.3.5) and the long-term multiplier lambda = xi / (1 + 50 rho').
- Sound: the bluff as one more screen in front of the cooler cells (pass 2d's ISO 9613-2 model).
"""

from __future__ import annotations

import json
import math

import numpy as np

from . import OUT_DIR

AIR_W_M3K = 0.33  # W per m3/h of air per K (rho cp of air / 3600)


def geometry() -> dict:
    return json.loads((OUT_DIR / "pass3" / "garden.json").read_text(encoding="utf-8"))["areas"]


def rooms(g: dict) -> list[dict]:
    """Each glass room's floor, glass, exposed roof and floor (m2) and volume (m3). Level 1's
    ceiling is level 2's floor where level 2's room sits on it; elsewhere a terrace (exposed).
    Both rooms stand on trays over the pool (exposed floors). North walls are the bluff (earth)."""
    f1, f2 = g["floor_m2"]["level1"], g["floor_m2"]["level2"]
    return [
        {"name": "level 1", "floor": f1, "glass": g["glass_m2"]["level1"], "roof": f1 - f2, "under": f1,
         "volume": f1 * g["height_m"]["level1"]},
        {"name": "level 2", "floor": f2, "glass": g["glass_m2"]["level2"], "roof": f2, "under": 0.0,
         "volume": f2 * g["height_m"]["level2"]},
    ]


def ua(room: dict, p: dict) -> float:
    h = "garden.heat."
    return (p[h + "glass_u"] * room["glass"] + p[h + "roof_u"] * (room["roof"] + room["under"])
            + AIR_W_M3K * p[h + "ach"] * room["volume"])


def heat(g: dict, temp: np.ndarray, p: dict, set_c: float) -> dict:
    rs = rooms(g)
    total_ua = sum(ua(r, p) for r in rs)
    hourly = total_ua * np.clip(set_c - temp, 0.0, None)
    design = p["pass3.loads.design_c"]
    r_ = "pass3.radiant."
    floors = []
    for r in rs:
        q = ua(r, p) * (set_c - design) / r["floor"]
        surface = set_c + (q / 8.92) ** (1 / 1.1)
        mean_water = set_c + q / p[r_ + "k_h"]
        floors.append({"name": r["name"], "q_w_m2": q, "surface_c": surface, "ok": surface <= p[r_ + "max_floor_c"],
                       "supply_c": mean_water + p[r_ + "dt_k"] / 2})
    return {"set_c": set_c, "ua_w_k": total_ua, "mwh": hourly.sum() / 1e6, "peak_kw": hourly.max() / 1e3,
            "design_kw": total_ua * (set_c - design) / 1e3, "floors": floors}


# --- The cantilever --------------------------------------------------------------------------------

def cantilever(p: dict, span_m: float | None = None, depth_mm: float | None = None, as_mm2_m: float | None = None) -> dict:
    """A 1 m strip of level 1's terrace: required top steel (or the steel given), and tip deflection
    now and long-term."""
    c = "garden.cantilever."
    L = (span_m if span_m is not None else p[c + "span_m"]) * 1000.0  # mm
    h = depth_mm if depth_mm is not None else p[c + "depth_mm"]
    b = 1000.0
    d = h - p[c + "cover_mm"]
    fc, fy = p[c + "fc_mpa"], p[c + "fy_mpa"]
    ec = 4700.0 * math.sqrt(fc)  # MPa
    es = 200_000.0
    n = es / ec
    dead = 24e-6 * h * b  # N/mm (24 kN/m3 self weight over a 1 m strip)
    sdl = p[c + "superimposed_kpa"] * 1e-3 * b  # kPa -> N/mm2 x b
    live = p[c + "live_kpa"] * 1e-3 * b
    tip = p[c + "parapet_kn_m"] * 1.0 * 1000.0  # N on the 1 m strip
    mu = (1.2 * (dead + sdl) + 1.6 * live) * L ** 2 / 2 + 1.2 * tip * L  # N mm
    phi = 0.9
    if as_mm2_m is None:
        # phi As fy (d - As fy / (1.7 fc b)) = Mu, the smaller root.
        a_, b_, c_ = phi * fy ** 2 / (1.7 * fc * b), -phi * fy * d, mu
        disc = b_ * b_ - 4 * a_ * c_
        as_req = (-b_ - math.sqrt(disc)) / (2 * a_) if disc >= 0 else float("nan")
        as_ = max(as_req, 0.0018 * b * h)  # ACI 318 minimum for slabs (Grade 60)
    else:
        as_ = as_mm2_m
    # Section properties.
    ig = b * h ** 3 / 12.0
    fr = 0.62 * math.sqrt(fc)
    mcr = fr * ig / (h / 2.0)
    rho_n = as_ * n / (b * d)
    kd = (math.sqrt(2 * rho_n + rho_n ** 2) - rho_n) * d
    icr = b * kd ** 3 / 3.0 + n * as_ * (d - kd) ** 2

    def ie(ma: float) -> float:
        if ma <= 2.0 / 3.0 * mcr:
            return ig
        return min(ig, icr / (1 - ((2.0 / 3.0 * mcr / ma) ** 2) * (1 - icr / ig)))

    def tip_deflection(w: float, pt: float, i: float) -> float:
        return w * L ** 4 / (8 * ec * i) + pt * L ** 3 / (3 * ec * i)

    m_d = (dead + sdl) * L ** 2 / 2 + tip * L
    m_all = (dead + sdl + live) * L ** 2 / 2 + tip * L
    i_all, i_d = ie(m_all), ie(m_d)
    d_dead = tip_deflection(dead + sdl, tip, i_d)
    d_all = tip_deflection(dead + sdl + live, tip, i_all)
    d_live = d_all - d_dead
    rho_comp = 0.0 if as_mm2_m is not None else 0.5 * as_ / (b * d)  # bottom bars: half the top steel
    lam = p[c + "creep_xi"] / (1 + 50 * rho_comp)
    sustained = d_dead + p[c + "sustained_live"] * d_live
    long_term = lam * sustained + d_live
    return {"span_mm": L, "depth_mm": h, "mu_knm": mu / 1e6, "as_mm2_m": as_, "mcr_knm": mcr / 1e6, "ma_knm": m_all / 1e6,
            "ig": ig, "icr": icr, "ie": i_all, "d_dead_mm": d_dead, "d_live_mm": d_live, "lambda": lam,
            "long_term_mm": long_term, "limit_mm": L / p[c + "limit_ratio"], "ok": long_term <= L / p[c + "limit_ratio"]}


# --- Sound: the bluff as one more screen ------------------------------------------------------------

def bluff_il(p: dict, distances=(120.0, 300.0, 700.0)) -> dict:
    """Insertion loss (dB) of walled cells alone, and with the bluff in front of them, homes facing
    across the rows (pass 2d's model)."""
    from . import wall

    yd = wall.yard(p, "cells")
    s, depth, width = wall.screen_for(p, yd, "across")
    a = "garden.acoustics."
    x0 = p["wall.yard.side_to_wall_m"] + wall.wall_thick(p) + p[a + "bluff_offset_m"]
    hb = p[a + "bluff_h_m"]
    with_bluff = wall.Screen("cells + bluff", tuple(sorted(s.edges + ((x0, hb), (x0 + p[a + "bluff_thick_m"], hb)))), s.footprint_m)
    hs, hr = p["wall.yard.fan_h_m"], p["wall.acoustics.ear_h_m"]
    return {r: (wall.insertion_loss(r, s, width, depth, hs, hr, p), wall.insertion_loss(r, with_bluff, width, depth, hs, hr, p))
            for r in distances}


def report(p: dict, temp: np.ndarray) -> str:
    g = geometry()
    lines = []
    rs = rooms(g)
    lines += ["**The glass rooms** (forge `garden`)", "", "| Room | Floor | Glass | Exposed roof + floor | Volume | UA |", "|---|---|---|---|---|---|"]
    for r in rs:
        lines.append(f"| {r['name']} | {r['floor']:.0f} m2 | {r['glass']:.0f} m2 | {r['roof'] + r['under']:.0f} m2 | {r['volume']:.0f} m3 | "
                     f"{ua(r, p):,.0f} W/K |")
    lines += ["", "**Heat** (PVGIS typical year at Homer City; no solar or internal gains, so an upper bound)", "",
              "| Held at | Heat a year | Design load | Floor output needed (level 1 / 2) | Floor surface | Water supply needed |",
              "|---|---|---|---|---|---|"]
    for set_c in (p["garden.heat.set_low_c"], p["garden.heat.set_high_c"]):
        h = heat(g, temp, p, set_c)
        f1, f2 = h["floors"]
        lines.append(f"| {set_c:g} C | {h['mwh']:,.0f} MWh | {h['design_kw']:,.0f} kW at {p['pass3.loads.design_c']:g} C | "
                     f"{f1['q_w_m2']:.0f} / {f2['q_w_m2']:.0f} W/m2 | {max(f1['surface_c'], f2['surface_c']):.1f} C (limit "
                     f"{p['pass3.radiant.max_floor_c']:g}) | {max(f1['supply_c'], f2['supply_c']):.1f} C |")
    warm = p["pass2.good_neighbour.liquid_supply_c"] + p["pass2.good_neighbour.liquid_rise_k"]
    lines += ["", f"The data center's warm water leaves the chips at about {warm:.0f} C (pass 2: {p['pass2.good_neighbour.liquid_supply_c']:g} C "
              f"supply + {p['pass2.good_neighbour.liquid_rise_k']:g} K)."]
    cv = cantilever(p)
    lines += ["", "**Level 1's cantilever** (a 1 m strip; ACI 318-19)", "",
              f"- {cv['span_mm'] / 1e3:.1f} m beyond the pier, {cv['depth_mm']:.0f} mm deep: factored moment {cv['mu_knm']:.0f} kN m per m; "
              f"top steel {cv['as_mm2_m']:,.0f} mm2 per m.",
              f"- Cracking moment {cv['mcr_knm']:.0f} kN m against {cv['ma_knm']:.0f} under full service load: effective stiffness "
              f"{cv['ie'] / cv['ig']:.0%} of the uncracked section.",
              f"- Tip deflection: {cv['d_dead_mm']:.1f} mm under dead load, {cv['d_live_mm']:.1f} mm more under full live load; long-term "
              f"(x {cv['lambda']:.2f} on the sustained part) {cv['long_term_mm']:.1f} mm against the L/{p['garden.cantilever.limit_ratio']:g} limit "
              f"{cv['limit_mm']:.0f} mm: {'within' if cv['ok'] else 'OVER'}."]
    il = bluff_il(p)
    lines += ["", "**Sound**: walled cells alone, then with the bluff in front (homes across the rows):", ""]
    lines += [f"- {r:,.0f} m: {a:.1f} dB -> {b:.1f} dB" for r, (a, b) in il.items()]
    return "\n".join(lines)
