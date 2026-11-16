"""Pass 3c: the winter garden's numbers (D9). Geometry from forge `garden` (out/pass3/garden.json).

- Heat: the two glass rooms' heat loss, hourly over the PVGIS typical year (UA x the hours below
  the set point), with no solar or internal gains (an upper bound), at a temperate and a warm set
  point; then the radiant stone floors at the design hour by EN 1264's characteristic
  q = 8.92 (floor - room)^1.1 W/m2 (floor surface <= 29 C) and pass 3's water-to-floor coefficient,
  against the data center loop's warm water.
- The cantilever: level 1's terrace as a reinforced concrete strip, ACI 318-19: strength
  (Mu <= phi As fy (d - a/2)), and deflection with the effective moment of inertia (Bischoff's
  form, 24.2.3.5) and the long-term multiplier lambda = xi / (1 + 50 rho').
- Sound: the coolers on the hall's roof behind its parapet, against pass 2d's walled cells on the
  ground (pass 2d's ISO 9613-2 model, scanned over distance).
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


# --- Sound: the coolers on the hall's roof -----------------------------------------------------------

def rooftop_screen(p: dict, parapet_m: float | None = None):
    """What a home on the ground sees between it and the roof's fans: the parapet's two top edges
    (unless it is zero), then the roof overhang's edge at deck height. x from the coolers' edge."""
    from . import wall

    a = "garden.acoustics."
    gap, deck, t = p["wall.yard.side_to_wall_m"], p[a + "deck_m"], p[a + "parapet_thick_m"]
    hp = p[a + "parapet_m"] if parapet_m is None else parapet_m
    edge = (gap + t + p[a + "overhang_m"], deck)
    if hp <= 0:
        return wall.Screen("roof edge only", (edge,), 0.0)
    return wall.Screen(f"{hp:g} m parapet", ((gap, deck + hp), (gap + t, deck + hp), edge), t)


def rooftop_noise(p: dict, parapet_m: float | None = None, fan_cut_db: float | None = None, distances=None,
                  h_r: float | None = None) -> dict:
    """Night level at homes (dB(A)) from the coolers on the roof, scanned over distance, because near a
    tall building the level rises before it falls. pass 2d's ISO 9613-2 model with the sources at deck +
    fan height and the ground term at the mean path height; the window `h_r` m up (default: pass 2d's
    ear height). The coolers stand at the makers' spacing with no walls between them (wall.py's
    `perimeter` yard)."""
    from . import noise, wall

    a = "garden.acoustics."
    s = rooftop_screen(p, parapet_m)
    yd = wall.yard(p, "perimeter")
    hs = p[a + "deck_m"] + p["wall.yard.fan_h_m"]
    hr = p["wall.acoustics.ear_h_m"] if h_r is None else h_r
    q = dict(p, **{"pass2.noise.h_m": (hs + hr) / 2})
    cut = p[a + "fan_cut_db"] if fan_cut_db is None else fan_cut_db
    lw = noise.module_lw("good neighbour", p["pass2.module.it_mw"] * 1.2, p) - cut
    rs = np.geomspace(10.0, 3000.0, 60) if distances is None else np.asarray(distances, dtype=float)
    lv = np.array([wall.level(lw, r, s, yd.length, yd.depth, hs, hr, q) for r in rs])
    target = p[a + "target_db"]
    over = rs[lv > target]
    return {"screen": s.name, "fan_cut_db": cut, "lw": lw, "r": rs, "levels": lv, "loudest_db": float(lv.max()),
            "at_m": float(rs[lv.argmax()]), "over_to_m": float(over.max()) if over.size else 0.0, "target": target}


def ground_cells(p: dict, fan_cut_db: float = 0.0, distances=None) -> list[dict]:
    """pass 2d's walled cells on the ground, scanned the same way, for comparison."""
    from . import noise, wall

    lw = noise.module_lw("good neighbour", p["pass2.module.it_mw"] * 1.2, p) - fan_cut_db
    hs, hr = p["wall.yard.fan_h_m"], p["wall.acoustics.ear_h_m"]
    rs = np.geomspace(10.0, 3000.0, 60) if distances is None else np.asarray(distances, dtype=float)
    yd = wall.yard(p, "cells")
    out = []
    for direction in ("across", "along"):
        s, depth, width = wall.screen_for(p, yd, direction)
        lv = np.array([wall.level(lw, r, s, width, depth, hs, hr, p) for r in rs])
        over = rs[lv > p["garden.acoustics.target_db"]]
        out.append({"direction": direction, "loudest_db": float(lv.max()), "at_m": float(rs[lv.argmax()]),
                    "over_to_m": float(over.max()) if over.size else 0.0})
    return out


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
    a = "garden.acoustics."
    lines += ["", f"**Sound at homes on the ground, at night** (pass 2d's ISO 9613-2 model; coolers on the {p[a + 'deck_m']:g} m roof "
              f"deck, homes facing across the rows; WHO night guideline {p[a + 'target_db']:g} dB(A))", "",
              "| Coolers | Fans | Loudest at any distance | Above the guideline out to |", "|---|---|---|---|"]
    for cut in (0.0, p[a + "fan_cut_db"]):
        fans = "as pass 2" if cut == 0 else f"low-noise (-{cut:g} dB)"
        for g in ground_cells(p, cut):
            far = f"{g['over_to_m']:.0f} m" if g["over_to_m"] > 0 else "nowhere"
            lines.append(f"| On the ground in walled cells (pass 2d), homes {g['direction']} the rows | {fans} | "
                         f"{g['loudest_db']:.1f} dB(A) at {g['at_m']:.0f} m | {far} |")
    for hp in (0.0, p[a + "parapet_m"]):
        for cut in (0.0, p[a + "fan_cut_db"]):
            r = rooftop_noise(p, parapet_m=hp, fan_cut_db=cut)
            fans = "as pass 2" if cut == 0 else f"low-noise (-{cut:g} dB)"
            far = f"{r['over_to_m']:.0f} m" if r["over_to_m"] > 0 else "nowhere"
            lines.append(f"| On the roof, {r['screen']} | {fans} | {r['loudest_db']:.1f} dB(A) at {r['at_m']:.0f} m | {far} |")
    return "\n".join(lines)
