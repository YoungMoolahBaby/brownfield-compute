"""The scorecard (docs/SCORECARD.md).

- `build`: pass 2's, one 100 MW module, the old conventional design against the good neighbour.
- `campus` (2026-11-17): the whole of it at Homer City as it now stands.
  - **The data center, a module:** against the three conventional designs (old water-cooled, the
    strong cloud hall, the strong AI hall); the good neighbour's heat now goes to the glass only
    (D16-D18: the homes heat themselves).
  - **The campus:** AWS's 39 buildings at `scorecard.campus_it_mw`.
  - **The towns:** what is the same whichever design is built (jobs, tax, the crews), and what the
    good-neighbour deal adds (homes, third places), with what each costs and who pays.
"""

from __future__ import annotations

import calendar

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
            "good neighbour": noise.distance_for(target, lw["good neighbour"], p)}
    # Honest corner: dry coolers at minimum size (k = 1). Screens: pass 2d's yard and ISO 9613-2
    # barrier geometry (wall.py), measured from the yard's edge.
    lw_min = noise.module_lw("good neighbour", peak_heat, dict(p, **{"pass2.noise.dry_oversize": 1.0}))
    from . import wall

    ac = {(r["layout"], r["direction"]): r["dist"] for r in wall.acoustics(p)}
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
        (f"Distance to {target:.0f} dB(A) at night (the module as a point, no screen)", "m",
         f"{dist['conventional']:,.0f}", f"{dist['good neighbour']:,.0f}"),
        ("  from the cooler yard's edge, 6 m berm round it (pass 2d)", "m", "", f"{ac[('berm', 'across')]:,.0f}"),
        ("  from the yard's edge, walled cells (pass 2d), across / along the rows", "m", "",
         f"{ac[('cells', 'across')]:,.0f} / {ac[('cells', 'along')]:,.0f}"),
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


# --- The campus and the towns (2026-11-17) ----------------------------------------------------------

def current(p: dict) -> dict:
    """The good neighbour as the design now stands: no town heat network (the new homes heat themselves,
    D18) and the campus's market-sized glass (`site.greenhouse_ha`) shared among its modules."""
    n = p["scorecard.campus_it_mw"] / p["pass2.module.it_mw"]
    return dict(p, **{"pass2.town.homes": 0.0, "pass2.greenhouse.hectares": p["site.greenhouse_ha"] / n})


def modules(temp, rh, p: dict) -> dict:
    """One module of each design, and the costs between them (cooling and backup; 20 years)."""
    from . import cost, module

    q = current(p)
    d = {"old": module.conventional(temp, q), "cloud": module.air_hall(temp, rh, q), "ai": module.liquid_towers(temp, rh, q),
         "gn": module.good_neighbour(temp, q)}
    return {"d": d, "vs": cost.vs_strong(temp, rh, q), "old": cost.ledgers(temp, q)}


def campus(temp, rh, params: dict) -> tuple[str, dict]:
    from . import acs, center, conference as cf, cost, econ, land, rings, wall, workforce as wf
    from .params import values

    p = values(params)
    n = p["scorecard.campus_it_mw"] / p["pass2.module.it_mw"]
    m = modules(temp, rh, p)
    d, vs, old = m["d"], m["vs"], m["old"]
    mgd = lambda r: r.withdrawn_m3 / GAL / 365 / 1e6
    peak_heat = p["pass2.module.it_mw"] * 1.2  # heat to reject at full IT load, as in `build`
    target = p["pass2.noise.target_night_db"]
    towers = noise.distance_for(target, noise.module_lw("conventional", peak_heat, p), p)
    ac = {(r["layout"], r["direction"]): r["dist"] for r in wall.acoustics(p)}
    bk = backup("conventional", p)
    gn = d["gn"]
    share = gn.delivered_mwh / gn.heat_out_mwh
    ai_year = vs["npv_vs_ai"] / cost.annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    ai_bill = d["ai"].it_mwh * d["ai"].pue * p["cost.energy.elec_usd_mwh"]  # IT + cooling
    L = ["**1. The data center: one 100 MW module, four designs** (the typical year at the plant; cooling only, electrical losses left out)", "",
         "| Per module | Old conventional (chillers + towers) | Strong cloud (outside air + pads) | Strong AI (liquid + towers) | Good neighbour |",
         "|---|---|---|---|---|",
         "| Water withdrawn, million gal/day | " + " | ".join(f"{mgd(d[k]):.2f}" for k in ("old", "cloud", "ai")) + " | 0 |",
         "| PUE (IT + cooling) | " + " | ".join(f"{d[k].pue:.3f}" for k in ("old", "cloud", "ai", "gn")) + " |",
         f"| Night sound: 40 dB(A) at | ~{towers:,.0f} m (towers) | not modelled (fans on the halls) | ~{towers:,.0f} m (towers) | "
         f"{ac[('cells', 'across')]:,.0f}-{ac[('cells', 'along')]:,.0f} m from its walled cooler yard |",
         f"| Diesel generators (tested {p['pass2.backup.test_hours']:g} h a year each) | {bk['gensets']} | {bk['gensets']} | {bk['gensets']} | "
         f"0 (batteries to the gas plant) |",
         f"| NOx from generator tests, t a year | {bk['nox_t']:.1f} | {bk['nox_t']:.1f} | {bk['nox_t']:.1f} | 0 |",
         f"| Heat put to use | none | none | none | {gn.delivered_mwh / 1e3:,.1f} GWh a year to its share of the glass "
         f"({p['site.greenhouse_ha'] / n:.2f} ha): {share:.1%} of its heat |",
         f"| The good neighbour over 20 years, million USD (+ means it's cheaper) | {old['npv_keep_diesel'] / 1e6:+,.1f} keeping diesel "
         f"({old['npv_op'] / 1e6:+,.1f} dropping it) | {vs['breakeven_vs_cloud'] / 1e6:+,.1f}: its plant must cost that much less to "
         f"break even | {vs['npv_vs_ai'] / 1e6:+,.1f} | |",
         f"| The same against the AI hall, as a sum each year, million USD | | | {ai_year / 1e6:+,.1f} ({ai_year / ai_bill:+.1%} of the AI "
         f"hall's power bill at ${p['cost.energy.elec_usd_mwh']:g}/MWh; {ai_year * n / 1e6:+,.0f} across the campus) | |",
         ""]
    # The campus.
    keep = lambda x: f"{x:,.0f}"
    L += [f"**2. The campus: AWS's 39 buildings at ~{p['scorecard.campus_it_mw']:,.0f} MW of IT ({n:.0f} modules; AWS states no load, "
          f"range {params['scorecard.campus_it_mw'].low:,.0f}-{params['scorecard.campus_it_mw'].high:,.0f} MW)**", "",
          "| The campus | Old conventional | Strong cloud | Strong AI | Good neighbour |", "|---|---|---|---|---|",
          "| Water withdrawn, million gal/day | " + " | ".join(f"{mgd(d[k]) * n:,.1f}" for k in ("old", "cloud", "ai")) + " | 0 |",
          "| Of it, blowdown to the creeks, million gal/day | " + " | ".join(f"{d[k].blowdown_m3 / GAL / 365 / 1e6 * n:,.1f}" for k in ("old", "cloud", "ai"))
          + " | 0 |",
          "| Cooling electricity, GWh a year | " + " | ".join(keep(d[k].cooling_mwh / 1e3 * n) for k in ("old", "cloud", "ai", "gn")) + " |",
          f"| Diesel generators | {keep(bk['gensets'] * n)} | {keep(bk['gensets'] * n)} | {keep(bk['gensets'] * n)} | 0 |",
          f"| NOx from their tests, t a year | {bk['nox_t'] * n:,.0f} | {bk['nox_t'] * n:,.0f} | {bk['nox_t'] * n:,.0f} | 0 |",
          f"| Heat put to use | none | none | none | {gn.delivered_mwh * n / 1e3:,.0f} GWh a year, the {p['site.greenhouse_ha']:g} ha of glass |",
          f"| Greenhouse jobs | 0 | 0 | 0 | {p['site.greenhouse_ha'] * p['pass2.jobs.greenhouse_per_ha']:,.0f} |", ""]
    # The towns.
    layers = {k: land.features(k, land.box(p)) for k in ("places", "cdps", "state_roads")}
    town = cf.towns(p, layers)
    th, hi = cf.town_homes(p, town), cf.town_homes(cf.high_case(p, params), town)
    mem = cf.members(p, th, town)
    cl = cf.clubhouse(p)
    n_club = sum(r["clubhouse"] for r in mem.values())
    hh = sum(r["households"] for r in mem.values())
    homes, homes_hi = sum(v["homes"] for v in th.values()), sum(v["homes"] for v in hi.values())
    growth = sum(v["people"] for v in th.values()) / sum(t_["people"] for t_ in town.values())
    c = rings.counts(p)
    fm = rings.flat_money(p)
    gaps = {k: sum(fm[b][k]["gap"] * c["flats_by_bed"][b] for b in range(4))
            for k in ("market-rate flat", "tax-credit flat, 60% AMI, 4% credits", "tax-credit flat, 60% AMI, 9% credits")}
    tax = econ.campus_tax(p)
    run = center.running(p)
    arena_cost = sum(v for k, v in run.items() if k != "fte")
    g = "village.growth_limits."
    sewer = p[g + "sewer_spare_mgd"] * 1e6 / (p[g + "sewer_avg_flow_mgd"] * 1e6 / p[g + "sewer_residential_customers"])
    kids = sum(v["children"] for v in th.values())
    sites = land.aws_sites(p)
    land.site_counts(p, sites)
    counts = {k: s_["n"] for k, s_ in sites.items()}
    tm = wf.months()
    w = wf.total(p, counts, tm)
    housing = acs.housing()
    aadt = wf.us119_aadt(layers, *land.PLANT)
    mc = wf.monte_carlo(params, counts, housing, aadt)
    tr = wf.traffic(p, w.max(), aadt)
    t_peak = tm[int(w.argmax())]
    when = f"{calendar.month_name[int(round((t_peak % 1) * 12)) + 1]} {int(t_peak)}"
    people = sum(t_["people"] for t_ in town.values())
    L += [f"**3. The towns** ({', '.join(town)}: {people:,.0f} people)", "",
          "| | Whichever design is built | What the good-neighbour deal adds |", "|---|---|---|",
          f"| Permanent jobs | AWS: 1,500-2,000 at $80,000-100,000 (its filing) | {p['site.greenhouse_ha'] * p['pass2.jobs.greenhouse_per_ha']:,.0f} "
          f"in the glass |",
          f"| Property tax at build-out | ${tax['total'] / 1e6:,.0f}M a year (school ${tax['school'] / 1e6:,.0f}M, county ${tax['county'] / 1e6:,.0f}M, "
          f"townships ${tax['township'] / 1e6:,.0f}M); AWS seeks no abatement | a set share into a housing fund and the trust |",
          f"| Construction, 2026-2036 | peak ~{w.max():,.0f} on site in {when} ({mc['peak'][0]:,.0f}-{mc['peak'][2]:,.0f}); beds for crews "
          f"from away short in {mc['p_short']:.0%} of draws; US 119 at {tr['vc_after']:.2f} of capacity in the shift hour | "
          "a crew housing plan, protection for the towns' renters, park-and-ride (pass 4) |",
          f"| New homes | none planned | {homes} (high case {homes_hi}) at the towns' edges, each town growing ~{growth:.0%}: "
          f"{c['flats']} flats, {c['townhouses']} townhouses, {c['houses']} houses; every one on its own heat pump |",
          f"| The flats' funding gap | | ${gaps['market-rate flat'] / 1e6:,.1f}M at market rents, "
          f"${gaps['tax-credit flat, 60% AMI, 4% credits'] / 1e6:,.1f}M with 4% tax credits, "
          f"${gaps['tax-credit flat, 60% AMI, 9% credits'] / 1e6:,.1f}M with 9%; from the housing fund |",
          f"| Third places | | {n_club} clubhouses (${n_club * cl['build'] / 1e6:,.1f}M to build, ${n_club * cl['run'] / 1e6:,.2f}M a year: "
          f"${n_club * cl['run'] / hh:,.0f} a household) and the arena (${arena_cost / 1e6:,.2f}M a year to run, less leagues and memberships) |",
          f"| Limits | | {homes} homes against room for ~{sewer:,.0f} on Homer City's sewage plant; ~{kids / 13:.0f} children a grade "
          f"against Homer-Center's ~{p[g + 'school_cohort_per_grade']:.0f} |"]
    return "\n".join(L), {"n": n, "modules": m, "tax": tax, "homes": homes, "mc": mc}
