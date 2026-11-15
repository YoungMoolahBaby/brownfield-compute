"""Pass 2's scorecard: one module at the site, conventional vs good neighbour, every measure in
docs/SCORECARD.md that pass 2 can fill. Water and heat come from module.py, sound from noise.py,
backup and jobs from their parameters.
"""

from __future__ import annotations

from . import module, noise
from .module import GAL


def backup(design: str, p: dict) -> dict:
    b = "pass2.backup."
    installed = p["pass2.module.it_mw"] * p[b + "installed_per_it_mw"]
    if design == "good neighbour":
        return {"gensets": 0, "diesel_hours": 0.0, "nox_t": 0.0,
                "battery_mwh": installed * p[b + "battery_minutes"] / 60.0}
    n = int(-(-installed // p[b + "gen_mw"]))
    mwh = n * p[b + "gen_mw"] * p[b + "test_load"] * p[b + "test_hours"]
    return {"gensets": n, "diesel_hours": n * p[b + "test_hours"], "nox_t": mwh * 1000 * p[b + "nox_g_kwh"] / 1e6,
            "battery_mwh": 0.0}


def build(temp, p: dict) -> tuple[str, dict]:
    a, g = module.conventional(temp, p), module.good_neighbour(temp, p)
    target = p["pass2.noise.target_night_db"]
    peak_heat = p["pass2.module.it_mw"] * 1.2  # heat to reject at full IT load, both designs
    lw = {"conventional": noise.module_lw("conventional", peak_heat, p),
          "good neighbour": noise.module_lw("good neighbour", peak_heat, p)}
    dist = {"conventional": noise.distance_for(target, lw["conventional"], p),
            "good neighbour": noise.distance_for(target, lw["good neighbour"], p, p["pass2.noise.barrier_db"])}
    # Honest corners: dry coolers at minimum size (k = 1) and without the berm.
    lw_min = noise.module_lw("good neighbour", peak_heat, dict(p, **{"pass2.noise.dry_oversize": 1.0}))
    dist_noberm = noise.distance_for(target, lw["good neighbour"], p)
    bk = {d: backup(d, p) for d in lw}
    gh_ha = p["pass2.greenhouse.hectares"]
    rows = [
        ("Water withdrawn", "million US gal/day", f"{a.withdrawn_m3 / GAL / 365 / 1e6:.2f}", "0"),
        ("Water consumed (evaporated)", "million m3/yr", f"{a.evaporated_m3 / 1e6:.2f}", "0"),
        ("WUE", "L/kWh IT", f"{a.wue:.2f}", "0"),
        ("PUE (IT + cooling)", "", f"{a.pue:.3f}", f"{g.pue:.3f}"),
        ("Heat put to use", "GWh/yr", "0", f"{g.delivered_mwh / 1e3:,.0f}"),
        ("Heat put to use", "share of heat out", "0%", f"{g.heat_reused_mwh / g.heat_out_mwh:.0%}"),
        ("Homes heated", "homes", "0", f"{g.town_mwh / p['pass2.town.heat_per_home_mwh']:,.0f}"),
        ("Sound power of heat rejection", "dB(A)", f"{lw['conventional']:.0f}", f"{lw['good neighbour']:.0f}"),
        ("  dry coolers at minimum size instead (fans at full speed)", "dB(A)", "", f"{lw_min:.0f}"),
        (f"Distance to {target:.0f} dB(A) at night", "m",
         f"{dist['conventional']:,.0f}", f"{dist['good neighbour']:,.0f} (with berm)"),
        ("  without the berm", "m", "", f"{dist_noberm:,.0f}"),
        ("Diesel generators", "units", f"{bk['conventional']['gensets']}", "0"),
        ("Diesel test hours", "engine-hours/yr", f"{bk['conventional']['diesel_hours']:,.0f}", "0"),
        ("NOx from tests", "t/yr", f"{bk['conventional']['nox_t']:.1f}", "0"),
        ("Batteries", "MWh", "-", f"{bk['good neighbour']['battery_mwh']:,.0f}"),
        ("Jobs, data center", "per AWS building", f"{p['pass2.jobs.per_aws_building']:.0f}",
         f"{p['pass2.jobs.per_aws_building']:.0f}"),
        ("Jobs, greenhouses", "jobs", "0", f"{gh_ha * p['pass2.jobs.greenhouse_per_ha']:.0f} ({gh_ha:g} ha)"),
    ]
    md = ["| Per 100 MW module | Unit | Conventional | Good neighbour |", "|---|---|---|---|"]
    md += [f"| {m} | {u} | {c} | {gn} |" for m, u, c, gn in rows]
    return "\n".join(md), {"lw": lw, "dist": dist, "backup": bk}
