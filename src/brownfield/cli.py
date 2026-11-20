"""`uv run brownfield <command>`

- `check`: the parameter files, and the known cases in the site screen.
- `sites [--limit N]`: pass 1, the site screen, written to out/pass1/sites.csv.
- `rank`: pass 1's ranking of out/pass1/sites.csv on two axes, host and help.
- `module`: pass 2, one 100 MW module at Homer City, conventional vs good neighbour.
- `cost`: pass 2b, what the good-neighbour features cost, and who pays and gains.
- `homes`: the homes around the Homer City campus and their distance to it (county parcels).
- `sensitivity`: which inputs move pass 2's results most (one at a time, low to high).
- `house`: pass 3, the first house's heat (envelope from forge's CortenForge model) and its radiant
  floor on the data center's warm water.
- `block`: pass 3, a block of new homes on the warm loop against each home heating itself.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from . import OUT_DIR, eia, rank, screen
from .params import check_params, load_params, values


def cmd_check(_args) -> int:
    ok = True
    params = load_params()
    problems = check_params(params)
    for msg in problems:
        print(f"FAIL params: {msg}")
    ok &= not problems
    print(f"params: {'ok' if not problems else f'{len(problems)} problems'}")

    t = screen.plant_table(values(params))
    for (name, state), hit in eia.find_known(t).items():
        if hit.empty:
            print(f"FAIL known case {name}, {state}: not in the plant list")
            ok = False
        else:
            r = hit.iloc[0]
            print(f"ok   known case {name}, {state}: {r.plant}, {r.leaving_mw:.0f} MW leaving, {r.status}")
    sites = OUT_DIR / "pass1" / "sites.csv"
    if sites.exists():
        ok &= _known_cases_rank(rank.rank(pd.read_csv(sites, index_col=0), values(params)), values(params))
    else:
        print("skip known-case ranking: run `brownfield sites` first")
    ok &= _water_checks(values(params))
    ok &= _air_checks(values(params))
    ok &= _services_checks(values(params))
    print("check:", "passed" if ok else "FAILED")
    return 0 if ok else 1


def _water_checks(p) -> bool:
    """Pass 2f on the record it can be checked against: the flow transfer before the dam (USGS publishes
    a Q7-10 of 11.3 cfs at Graceton for 1952-1968), and the reservoir under the coal plant's own draws."""
    from . import water

    g, b = water.gauges()
    k = water.checks(g, b, p)
    kn = water.known_case(p, water.natural(g, b))
    tests = [(abs(k["q710_fit"] / 11.3 - 1) < 0.1, f"Two Lick's pre-dam Q7-10 from Blacklick {k['q710_fit']:.1f} cfs vs USGS 11.3"),
             (abs(k["q710_test"] / k["q710_test_obs"] - 1) < 0.15, f"split sample 1960-1968: {k['q710_test']:.1f} vs {k['q710_test_obs']:.1f} cfs"),
             (kn["short_days"] == 0, f"the reservoir carries the coal plant's own draws 2014-2023 (lowest {kn['lowest']:.0%})")]
    for good, msg in tests:
        print(f"{'ok  ' if good else 'FAIL'} water: {msg}")
    return all(good for good, _ in tests)


def _air_checks(p) -> bool:
    """Pass 2g on the record: EIA's SO2 for the coal plant's last two years against the CEMS baseline
    in the gas plant's air permit application (4,460.6 tons a year)."""
    from . import air

    k = air.checks(air.coal_history(), p)
    good = abs(k["ratio"] - 1) < 0.01
    print(f"{'ok  ' if good else 'FAIL'} air: the coal plant's SO2 2021-22 from EIA {k['so2_2122']:,.1f} tons a year vs the application's "
          f"{k['so2_app']:,.1f}")
    return good


def _services_checks(p) -> bool:
    """Pass 4b on the record: PDE's 2025-26 aid ratios for both districts recomputed with the published
    formula, and the 2026 millage totals for the campus's two sides (the county's sheet)."""
    from . import services

    ok = True
    for name, (ours, pde) in services.checks(p).items():
        good = abs(ours - pde) < 0.002
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} services: {name}'s aid ratio {ours:.4f} vs PDE's {pde:.4f}")
    m = "pass4.money."
    for side, total, mills in (("Center Township", 25.899, p[m + "mills_county"] + p[m + "mills_township"] + p[m + "mills_school"]),
                               ("Black Lick Township (River Valley)", 23.786,
                                p[m + "mills_county"] + p[m + "mills_township_blacklick"] + p[m + "mills_school_rivervalley"])):
        good = abs(mills - total) < 0.001
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} services: {side} millage {mills:.3f} vs the county's sheet {total:.3f}")
    return ok


def _known_cases_rank(r, p) -> bool:
    ok = True
    need = p["screen.rank.known_case_min_pct"]
    for (name, state), hit in eia.find_known(r).items():
        if hit.empty:
            continue
        x = hit.iloc[0]
        place = int((r["host"] > x.host).sum()) + 1
        good = x.host_pct >= need
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} known case {name}, {state}: host rank {place} of {len(r)} "
              f"(percentile {x.host_pct:.2f}, need {need:.2f})")
    return ok


def cmd_rank(_args) -> int:
    p = values(load_params())
    r = rank.rank(pd.read_csv(OUT_DIR / "pass1" / "sites.csv", index_col=0), p)
    r.to_csv(OUT_DIR / "pass1" / "ranked.csv", float_format="%.4f")
    show = ["plant", "state", "status", "leaving_mw", "host", "help", "host_grid", "host_flood", "host_heat",
            "host_fresh", "help_shrinking", "help_income", "help_heat_use"]
    print("top 20, host:")
    print(r[show].head(20).round(2).to_string())
    both = r[(r["host_pct"] >= 0.75) & (r["help_pct"] >= 0.75)]
    print(f"\n{len(both)} sites in the top quarter on both axes:")
    print(both[show].round(2).to_string())
    print()
    _known_cases_rank(r, p)

    from . import ROOT, figures  # matplotlib only when drawing

    known = pd.concat([hit.head(1) for hit in eia.find_known(r).values()])
    strongest = both.assign(score=both["host"] + both["help"]).sort_values("score", ascending=False).head(6)
    labels = pd.concat([strongest, known]).drop_duplicates(subset=["plant", "state"])
    labels = labels.assign(label=[f"{x.plant}, {x.state}" for x in labels.itertuples()])
    docs = ROOT / "docs" / "pass1"
    docs.mkdir(parents=True, exist_ok=True)
    figures.site_map(r, labels, docs / "map.png")
    figures.host_help(r, labels, docs / "host_help.png")
    print(f"figures in {docs}")
    return 0


HOMER_CITY = 3122  # EIA plant id
NL = chr(10)


def cmd_module(_args) -> int:
    from . import climate, module

    p = values(load_params())
    t = screen.plant_table(p)
    site = t.loc[HOMER_CITY]
    temp = climate.hourly_temp(site.lat, site.lon)
    print(f"{site.plant}, {site.state} ({site.lat:.4f}, {site.lon:.4f}): typical year mean {temp.mean():.1f} C, "
          f"{(temp > 30).sum()} h above 30 C, min {temp.min():.1f} C, max {temp.max():.1f} C")
    a, b = module.conventional(temp, p), module.good_neighbour(temp, p)
    print(module.table([a, b]))
    print(f"\ntown demand {b.town_demand_mwh / 1e3:,.0f} GWh/yr ({p['pass2.town.homes']:,.0f} homes), "
          f"greenhouse demand {b.greenhouse_demand_mwh / 1e3:,.0f} GWh/yr ({p['pass2.greenhouse.hectares']:g} ha), "
          f"trim hours {b.trim_hours}")
    from . import scorecard

    card, _ = scorecard.build(temp, p)
    print("\nscorecard:")
    print(card)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "module.md").write_text(module.table([a, b]) + "\n", encoding="utf-8")
    (out / "scorecard.md").write_text(card + "\n", encoding="utf-8")
    return 0


def cmd_cost(_args) -> int:
    from . import climate, cost

    params = load_params()
    site = screen.plant_table(values(params)).loc[HOMER_CITY]
    md = cost.report(climate.hourly_temp(site.lat, site.lon), params)
    print(md)
    t, rh = climate.hourly_temp_rh(site.lat, site.lon)
    strong = cost.strong_report(t, rh, params)
    print("\nAgainst the strongest conventional designs:\n")
    print(strong)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "cost.md").write_text(md + "\n", encoding="utf-8")
    (out / "cost_strong.md").write_text(strong + "\n", encoding="utf-8")
    ai = cost.ai_report(t, rh, params)
    print("\nOn AI loads, against the AI alternative (liquid + towers):\n")
    print(ai)
    (out / "cost_ai.md").write_text(ai + "\n", encoding="utf-8")
    return 0


def cmd_homes(_args) -> int:
    from . import ROOT, figures, homes

    p = values(load_params())
    site = screen.plant_table(p).loc[HOMER_CITY]
    campus, acres, hs = homes.campus_and_homes(site.lat, site.lon, p["pass2.homes.campus_radius_m"],
                                               p["pass2.homes.strip_m"])
    lines = [f"Campus (the plant owner's land within {p['pass2.homes.campus_radius_m'] / 1000:g} km of the plant): "
             f"{acres:,.0f} acres; {len(hs):,} homes around it.", "",
             "| Distance from the campus edge | Homes |", "|---|---|"]
    lines += [f"| within {e:,} m | {n:,} |" for e, n in homes.bands(hs)]
    near = sorted(h[3] for h in hs)[:5]
    lines += ["", f"Nearest homes: {', '.join(f'{d:.0f}' for d in near)} m from the edge."]
    md = "\n".join(lines)
    print(md)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "homes.md").write_text(md + "\n", encoding="utf-8")
    figures.homes_map(campus, hs, ROOT / "docs" / "pass2" / "homes.png")
    return 0


def cmd_sensitivity(_args) -> int:
    from . import climate, cost

    params = load_params()
    site = screen.plant_table(values(params)).loc[HOMER_CITY]
    t, rh = climate.hourly_temp_rh(site.lat, site.lon)
    md = cost.tornado_report(cost.tornado(t, rh, params), params)
    print(md)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "sensitivity.md").write_text(md + "\n", encoding="utf-8")
    return 0


def cmd_house(_args) -> int:
    from . import climate, house

    p = values(load_params())
    site = screen.plant_table(p).loc[HOMER_CITY]
    env = house.envelope()
    h = house.heat(env, climate.hourly_temp(site.lat, site.lon), p)
    md = house.report(env, h, p["pass2.good_neighbour.liquid_supply_c"])
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "heat.md").write_text(md + NL, encoding="utf-8")
    if (out / "apartment.json").exists():
        fh = house.flats_heat(house.apartment(), climate.hourly_temp(site.lat, site.lon), p)
        md2 = house.flats_report(fh)
        rc = house.recs_check(h, env["floor_m2"], fh["mean"])
        md2 += (NL + NL + f"Known case: space heat per square metre, the average flat against the house, "
                f"{rc['model']:.2f}; RECS 2020, apartments in buildings of 5+ units against detached homes, "
                f"{rc['recs_5plus']:.2f} (2-4 units {rc['recs_2_4']:.2f}, older stock); national averages.")
        print(NL + "The walk-up's flats:" + NL + NL + md2)
        (out / "flats.md").write_text(md2 + NL, encoding="utf-8")
    return 0


def cmd_block(_args) -> int:
    import numpy as np

    from . import block, climate, house

    params = load_params()
    p = values(params)
    site = screen.plant_table(p).loc[HOMER_CITY]
    env = house.envelope()
    t = climate.hourly_temp(site.lat, site.lon)
    h = house.heat(env, t, p)
    apt = house.apartment() if (OUT_DIR / "pass3" / "apartment.json").exists() else None
    flat_fn = (lambda q: house.flats_heat(apt, t, q)["mean"]) if apt else None
    flat = flat_fn(p) if flat_fn else None
    mc = block.monte_carlo(params, lambda q: house.heat(env, t, q), env["floor_m2"], flat_fn=flat_fn)
    md = block.report(block.run(p, h, env["floor_m2"], flat), mc, p)
    if flat:
        md += (NL + NL + f"Apartments use the average flat of forge's walk-up ({flat['floor_m2']:.1f} m2, "
               f"{flat['space_mwh']:.2f} MWh of space heat a year); houses and townhouses the first house.")
    md += NL + NL + "What it takes (negative = the loop is cheapest):" + NL + NL + block.grid(p, h, env["floor_m2"], flat=flat)
    # The dense case beside the campus, with every input varying.
    dense = {k: v for k, v in params.items()}
    from .params import Param

    for name, val in (("pass3.block.homes", 1000.0), ("pass3.block.main_km", 0.5)):
        old = params[name]
        dense[name] = Param(name, val, val, val, old.unit, old.conf, old.source, old.note)
    mcd = block.monte_carlo(dense, lambda q: house.heat(env, t, q), env["floor_m2"], flat_fn=flat_fn)["apartment"]
    q10, q50, q90 = np.percentile(mcd, [10, 50, 90])
    md += (NL + NL + f"1,000 apartments on a 0.5 km main, every other input varying (2,000 draws): the loop minus the "
           f"cheaper alternative P10 / P50 / P90 {q10:+,.0f} / {q50:+,.0f} / {q90:+,.0f} USD per dwelling; "
           f"the loop cheapest in {(mcd < 0).mean():.0%}.")
    # An all-electric neighbourhood (no gas line): the loop against the heat pump only.
    md += (NL + NL + "Against the heat pump only (an all-electric neighbourhood, no gas):" + NL + NL
           + block.grid(p, h, env["floor_m2"], flat=flat, key="A_minus_B"))
    mce = block.monte_carlo(dense, lambda q: house.heat(env, t, q), env["floor_m2"], flat_fn=flat_fn, key="A_minus_B")["apartment"]
    e10, e50, e90 = np.percentile(mce, [10, 50, 90])
    md += (NL + NL + f"1,000 apartments on a 0.5 km main against the heat pump, every other input varying: P10 / P50 / P90 "
           f"{e10:+,.0f} / {e50:+,.0f} / {e90:+,.0f} USD per dwelling; the loop cheaper in {(mce < 0).mean():.0%}.")
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "block.md").write_text(md + NL, encoding="utf-8")
    return 0


def cmd_frame(_args) -> int:
    import json

    from . import frame, house

    params = load_params()
    p = values(params)
    apt = house.apartment()
    known = frame.known_cases()
    d = frame.design(apt, p)
    # Every load at the top of its range at once, the soil at its weakest.
    worst = dict(p)
    for k, v in params.items():
        if k.startswith("pass3.frame.") and k not in ("pass3.frame.spacing_in", "pass3.frame.floor_live_defl"):
            worst[k] = v.low if k == "pass3.frame.soil_psf" else v.high
    w = frame.design(apt, worst)
    md = ("Published spans, reproduced with the sizing code:" + NL + NL + frame.known_report(known) + NL + NL
          + frame.report(d) + NL + NL + "Every load at the top of its range at once:" + NL + NL + frame.report(w))
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "frame.md").write_text(md + NL, encoding="utf-8")
    (out / "frame.json").write_text(json.dumps(frame.for_forge(d, p), indent=2) + NL, encoding="utf-8")
    print(NL + f"wrote {out / 'frame.json'} (forge `framing` builds it)")
    return 0


def cmd_build(args) -> int:
    from . import ROOT, build

    system = args.system
    sfx = build.SUFFIX[system]
    b = build.load(system)
    md = build.masonry_report(b) if system == "masonry" else build.report(b)
    print(md)
    out = OUT_DIR / "pass3"
    (out / f"build{sfx}.md").write_text(md + NL, encoding="utf-8")
    n = build.gif(out / f"build_frames{sfx}", ROOT / "docs" / "pass3" / f"build{sfx}.gif")
    print(NL + f"docs/pass3/build{sfx}.gif: {n} frames")
    return 0


def cmd_compare(_args) -> int:
    from . import compare

    md = compare.report(compare.gather())
    print(md)
    (OUT_DIR / "pass3" / "compare.md").write_text(md + NL, encoding="utf-8")
    return 0


def cmd_steel(_args) -> int:
    import json

    from . import frame, house, steel

    p = values(load_params())
    apt = house.apartment()
    d = steel.design(apt, p)
    md = ("SFIA joist spans, reproduced from the section properties:" + NL + NL
          + frame.known_report(steel.known_cases()) + NL + NL + steel.report(d))
    print(md)
    out = OUT_DIR / "pass3"
    (out / "steel.md").write_text(md + NL, encoding="utf-8")
    (out / "steel.json").write_text(json.dumps(steel.for_forge(d, p, apt), indent=2) + NL, encoding="utf-8")
    print(NL + f"wrote {out / 'steel.json'} (forge `framing steel` builds it)")
    return 0


def cmd_masonry(_args) -> int:
    import json

    from . import house, masonry

    p = values(load_params())
    apt = house.apartment()
    d = masonry.design(apt, p)
    k = masonry.known_cases()[0]
    md = (f"Known case: {k['case']}: {k['table']:,} lb, this code {k['model']:,.0f} lb ({k['model'] / k['table'] - 1:+.2%})."
          + NL + NL + masonry.report(d))
    print(md)
    out = OUT_DIR / "pass3"
    (out / "masonry.md").write_text(md + NL, encoding="utf-8")
    (out / "masonry.json").write_text(json.dumps(masonry.for_forge(d, p, apt), indent=2) + NL, encoding="utf-8")
    print(NL + f"wrote {out / 'masonry.json'} (forge `masonry` builds it)")
    return 0


def cmd_costcarbon(_args) -> int:
    from . import costcarbon

    params = load_params()
    p = values(params)
    md = costcarbon.report(costcarbon.quantities(), p, params)
    print(md)
    (OUT_DIR / "pass3" / "costcarbon.md").write_text(md + NL, encoding="utf-8")
    return 0


def cmd_wall(_args) -> int:
    import json

    from . import ROOT, build, wall

    params = load_params()
    p = values(params)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "wall.json").write_text(json.dumps(wall.forge_spec(p), indent=2) + NL, encoding="utf-8")
    forge_path = out / "wall_forge.json"
    forge = json.loads(forge_path.read_text(encoding="utf-8")) if forge_path.exists() else None
    md = wall.report(p, params, forge)
    print(md)
    (out / "wall.md").write_text(md + NL, encoding="utf-8")
    docs = ROOT / "docs" / "pass2"
    wall.figure(p, docs / "wall_noise.png")
    frames = out / "wall_frames"
    if frames.exists() and any(frames.glob("f*.png")):
        n = build.gif(frames, docs / "wall_build.gif", ms=320)
        print(NL + f"docs/pass2/wall_build.gif: {n} frames")
    print("wrote out/pass2/wall.json (forge `wall` reads it), out/pass2/wall.md, docs/pass2/wall_noise.png"
          + ("" if forge else "; run forge `wall` then this again for the CortenForge results"))
    return 0


def cmd_creek(_args) -> int:
    from . import ROOT, climate, creek, module

    params = load_params()
    p = values(params)
    a = creek.analyse(p)
    md = creek.report(p, a)
    # The comparison: a conventional module's own tower blowdown, which the good neighbour doesn't have.
    site = screen.plant_table(p).loc[HOMER_CITY]
    conv = module.conventional(climate.hourly_temp(site.lat, site.lon), p)
    bd = conv.blowdown_m3 / module.GAL / 365 / 1e6
    md += NL + NL + (f"Per 100 MW data center module (pass 2): a conventional module's cooling towers blow down "
                     f"{bd:.2f} million gallons a day on average; the good neighbour (dry coolers) none.")
    print(md)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "creek.md").write_text(md + NL, encoding="utf-8")
    creek.figure(p, a, ROOT / "docs" / "pass2" / "creek.png")
    print(NL + "wrote out/pass2/creek.md, docs/pass2/creek.png")
    return 0


def cmd_garden(_args) -> int:
    from . import climate, garden

    p = values(load_params())
    site = screen.plant_table(p).loc[HOMER_CITY]
    md = garden.report(p, climate.hourly_temp(site.lat, site.lon), climate.hourly_weather(site.lat, site.lon))
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "garden.md").write_text(md + NL, encoding="utf-8")
    print(NL + "wrote out/pass3/garden.md (geometry from forge `garden`)")
    return 0


def cmd_food(_args) -> int:
    import json

    from . import climate, food

    params = load_params()
    p = values(params)
    food.set_ranges(params)
    site = screen.plant_table(p).loc[HOMER_CITY]
    a = food.analyse(p, climate.hourly_weather(site.lat, site.lon))
    wx_on = food.local(climate.hourly_weather(*food.LEAMINGTON[:2]), food.LEAMINGTON[2])
    wx_nl = food.local(climate.hourly_weather(*food.WESTLAND[:2]), food.WESTLAND[2])
    md = food.report(p, a, food.known_case(p, wx_on, wx_nl))
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "food.md").write_text(md + NL, encoding="utf-8")
    (out / "food.json").write_text(json.dumps(food.forge_spec(p, a), indent=2) + NL, encoding="utf-8")
    print(NL + "wrote out/pass3/food.md, out/pass3/food.json (forge `garden` reads it)")
    return 0


def cmd_village(_args) -> int:
    from . import center, climate, food, rings, village

    params = load_params()
    p = values(params)
    village.set_ranges(params)
    site = screen.plant_table(p).loc[HOMER_CITY]
    wx = food.local(climate.hourly_weather(site.lat, site.lon), -5)
    md = rings.report(p, wx) + NL + NL + village.report(p, wx) + NL + NL + center.report(p)
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "village.md").write_text(md + NL, encoding="utf-8")
    import json

    (out / "village.json").write_text(json.dumps(village.forge_spec(p), indent=2) + NL, encoding="utf-8")
    print(NL + "wrote out/pass3/village.md, out/pass3/village.json (forge `garden` reads it)")
    return 0


def cmd_conference(_args) -> int:
    """D17-D18: the conference of communities on the real land, each town's new homes laid out at its
    edge, and the drawing data for forge `conference`."""
    import math

    from shapely.geometry import Polygon

    from . import ROOT, conference as cf, figures, land, neighbourhood as nb
    from .homes import Local

    params = load_params()
    p = values(params)
    layers = land.fetch_all(p)
    sites = land.aws_sites(p)
    land.site_counts(p, sites)
    a = land.analysis(p, layers, sites)
    loc = Local(*land.PLANT)
    raw = land.buildings(p)
    blds = [Polygon([loc.xy(lo, la) for lo, la in b["lonlat"]]) for b in raw]
    blds = [b if b.is_valid else b.buffer(0) for b in blds]
    town = cf.towns(p, layers)
    sites_h = cf.site_homes(p, sites)
    base, high = cf.town_homes(p, town), cf.town_homes(cf.high_case(p, params), town)
    mem = cf.members(p, base, town)
    lays = nb.lay_out_all(p, a, sites, layers, blds, town, base, cf.club_towns(mem))
    where = {k: lay.centre() for k, lay in lays.items()}
    gl = cf.glass(p, sites_h)
    ar = cf.arena(p, a, where, base, town, sites)
    toward = {s: min(where.values(), key=lambda xy: math.dist(xy, sites[s]["centre"])) for s in sites}
    gates = cf.gates(p, a, sites, toward, gl)
    from . import climate, food

    site = screen.plant_table(p).loc[HOMER_CITY]
    wx = food.local(climate.hourly_weather(site.lat, site.lon), -5)
    md = (cf.report(p, sites_h, base, high, town, lays, gl, ar, a) + NL + cf.clubs_report(p, lays, town) + NL
          + cf.members_report(p, mem) + NL + cf.heat_report(p, cf.heat(p, wx, base, lays, sites)))
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "conference.md").write_text(md + NL, encoding="utf-8")
    figures.conference_map(a, sites, layers, land.power_block(), lays, gates, ar, ROOT / "docs" / "pass3" / "conference.png")
    summary = nb.drawing(p, a, layers, blds, [b["height"] for b in raw], town, lays, out / "conference")
    print(NL + "drawing data: " + ", ".join(f"{k} ({v['lots']} lots, {v['trees']:,} trees, {v['buildings']:,} buildings)" for k, v in summary.items()))
    print("wrote out/pass3/conference.md, docs/pass3/conference.png, out/pass3/conference/ (draw with forge `conference`)")
    return 0


def cmd_scorecard(_args) -> int:
    """The scorecard as the design now stands: a module against three conventional designs, the campus,
    and the towns (docs/SCORECARD.md)."""
    from . import climate, scorecard

    params = load_params()
    p = values(params)
    site = screen.plant_table(p).loc[HOMER_CITY]
    temp, rh = climate.hourly_temp_rh(site.lat, site.lon)
    md, _ = scorecard.campus(temp, rh, params)
    print(md)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "scorecard.md").write_text(md + NL, encoding="utf-8")
    print(NL + "wrote out/scorecard.md")
    return 0


def cmd_bidset(args) -> int:
    from . import bidset

    import tempfile
    from pathlib import Path

    if args.setup_reader:
        return bidset.setup_webifc()
    apt, frame = bidset.load()
    params = load_params()
    path = bidset.OUT / "apartment.ifc"
    bidset.write_ifc(apt, frame, params, path)
    print(f"wrote {path.relative_to(OUT_DIR.parent)} ({path.stat().st_size / 1e3:.0f} kB)")
    res = bidset.check(path, apt, params)
    with tempfile.TemporaryDirectory() as tmp:
        again = Path(tmp) / "apartment.ifc"
        bidset.write_ifc(apt, frame, params, again)
        res.append(("a second export is the same file (header aside)", bidset.body_text(again) == bidset.body_text(path),
                    f"{len(bidset.body_text(path)):,} lines"))
    print(bidset.report(res))

    # What a quote needs (step 3): the IDS, and how much of it the model carries. It needs only
    # IfcOpenShell, so it runs whether or not the second reader can. Fields the model lacks are
    # the finding, not a failed run.
    ids_path = bidset.OUT / "bidset.ids"
    rows = bidset.run_ids(bidset.write_ids(params, ids_path), path)
    marked = next((r["applicable"] for r in rows if r["id"].startswith("escape_area/")), 0)
    se = bidset.single_exit(apt, params, marked)
    table = bidset.ids_report(rows, (se["escape_needed_upper"], se["escape_needed_ground"]))
    carried, fields = bidset.ids_carried(rows)
    hazards = bidset.safety_glazing(apt, params)
    summary = (f"The model carries {len(carried)} of the {fields} fields a quote needs ({', '.join(carried)}). "
               f"IBC 2018 2406.4.1-2406.4.3 call for safety glazing in {len(hazards)} of the {len(apt['openings'])} "
               f"openings (2406.4.4-2406.4.7, stairs and wet areas among them, not assessed).")
    summary += NL + NL + bidset.single_exit_report(se, params)
    print(NL + f"wrote {ids_path.relative_to(OUT_DIR.parent)} ({len(rows)} specifications)" + NL + table + NL + NL + summary)
    (bidset.OUT / "checklist.md").write_text(table + NL + NL + summary + NL, encoding="utf-8")

    why = bidset.webifc_status()
    if why:
        # Two readers are the check; with one, say so and fail, so nobody takes it for both.
        print(NL + f"FAIL the second reader (web-ifc) didn't run: {why}")
        return 1
    second = bidset.check_webifc(path, apt, params)
    print(NL + bidset.report(second))
    return 0 if all(ok for _, ok, _ in res + second) else 1


def cmd_services(_args) -> int:
    """Pass 4b: where the campus's tax goes, the schools, the hospital and emergency services."""
    from . import ROOT, services

    a = services.analyse(load_params())
    md = services.report(a)
    print(md)
    out = OUT_DIR / "pass4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "services.md").write_text(md + NL, encoding="utf-8")
    services.figure(a, ROOT / "docs" / "pass4" / "services.png")
    print(NL + "wrote out/pass4/services.md, docs/pass4/services.png")
    return 0


def cmd_air(_args) -> int:
    """Pass 2g: the gas plant's permitted air emissions against the coal plant's, and what each design adds."""
    from . import ROOT, air, climate

    params = load_params()
    site = screen.plant_table(values(params)).loc[HOMER_CITY]
    temp, rh = climate.hourly_temp_rh(site.lat, site.lon)
    a = air.analyse(temp, rh, params)
    md = air.report(a)
    print(md)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "air.md").write_text(md + NL, encoding="utf-8")
    air.figure(a, ROOT / "docs" / "pass2" / "air.png")
    print(NL + "wrote out/pass2/air.md, docs/pass2/air.png")
    return 0


def cmd_water(_args) -> int:
    """Pass 2f: the campus's water budget, from Two Lick Reservoir through the plant to the creeks."""
    from . import ROOT, climate, water

    params = load_params()
    site = screen.plant_table(values(params)).loc[HOMER_CITY]
    temp, rh = climate.hourly_temp_rh(site.lat, site.lon)
    a = water.analyse(temp, rh, params)
    md = water.report(a)
    print(md)
    out = OUT_DIR / "pass2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "water.md").write_text(md + NL, encoding="utf-8")
    water.figure(a, ROOT / "docs" / "pass2" / "water.png")
    print(NL + "wrote out/pass2/water.md, docs/pass2/water.png")
    return 0


def cmd_workforce(_args) -> int:
    """Pass 4: the construction workforce 2026-2036: on site by month, beds for crews from away, the
    morning shift on US 119."""
    from . import ROOT, acs, figures, land, workforce as wf

    params = load_params()
    p = values(params)
    sites = land.aws_sites(p)
    land.site_counts(p, sites)
    counts = {k: s["n"] for k, s in sites.items()}
    t = wf.months()
    sites_w, gas_w = wf.aws(p, counts, t), wf.gas(p, t)
    region = wf.counties_within(p, *land.PLANT)
    jobs = {f: wf.construction_jobs(f) for f, _, _ in region}
    housing = acs.housing()
    b = wf.beds(p, housing)
    near = housing[housing["name"].str.match(r"(Homer City borough|Center township|Black Lick township|Indiana borough|White township|"
                                             r"Blairsville borough),")]
    aadt = wf.us119_aadt({"state_roads": land.features("state_roads", land.box(p))}, *land.PLANT)
    w = gas_w + sum(sites_w.values())
    tr = dict(wf.traffic(p, w.max(), aadt), aadt=aadt)
    mc = wf.monte_carlo(params, counts, housing, aadt)
    md = wf.report(p, counts, t, sites_w, gas_w, b, region, jobs, near, tr, mc)
    print(md)
    out = OUT_DIR / "pass4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "workforce.md").write_text(md + NL, encoding="utf-8")
    figures.workforce_chart(t, gas_w, sites_w, wf.need(p, w), mc["need_band"], b["units"], ROOT / "docs" / "pass4" / "workforce.png")
    print(NL + "wrote out/pass4/workforce.md, docs/pass4/workforce.png")
    return 0


def cmd_land(_args) -> int:
    """D17: the real land round the plant and AWS's six sites."""
    import json

    from . import ROOT, figures, land

    p = values(load_params())
    layers = land.fetch_all(p)
    sites = land.aws_sites(p)
    land.site_counts(p, sites)
    a = land.analysis(p, layers, sites)
    md = land.report(p, a, sites)
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "land.md").write_text(md + NL, encoding="utf-8")
    (ROOT / "data" / "aws_sites.geojson").write_text(json.dumps(land.sites_geojson(sites), indent=1) + NL, encoding="utf-8")
    figures.land_map(a, sites, layers, land.power_block(), ROOT / "docs" / "pass3" / "land.png")
    print(NL + "wrote out/pass3/land.md, data/aws_sites.geojson, docs/pass3/land.png")
    return 0


def cmd_site(_args) -> int:
    import json

    from . import site

    p = values(load_params())
    food_t = p["site.food_t_yr"]
    mods = site.modules(p, p["site.greenhouse_ha"], site.homes_rect(p))
    m = site.metrics(p, mods, food_t, routed=True)
    proposals = site.optimise(p, mods, food_t)
    deep = site.depths(p, mods, food_t) if site.moat_on(p) else None
    md = site.report(p, mods, m, proposals, deep)
    print(md)
    out = OUT_DIR / "pass3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "site.md").write_text(md + NL, encoding="utf-8")
    sp = site.spec(p, mods, m, proposals)
    (out / "site.json").write_text(json.dumps(sp, indent=2) + NL, encoding="utf-8")
    from . import ROOT, figures

    docs = ROOT / "docs" / "pass3"
    docs.mkdir(parents=True, exist_ok=True)
    figures.site_plans(sp, docs / "site_plans.png")
    print(NL + "wrote out/pass3/site.md, out/pass3/site.json, docs/pass3/site_plans.png")
    return 0


def cmd_economy(_args) -> int:
    from . import acs, econ

    params = load_params()
    p = values(params)
    md = econ.report(p, params, acs.housing()) + NL + econ.sensitivity(params, p)
    print(md)
    out = OUT_DIR / "pass4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "economy.md").write_text(md + NL, encoding="utf-8")
    return 0


def cmd_sites(args) -> int:
    p = values(load_params())
    t = screen.plant_table(p)
    print(f"{len(t)} coal plant sites, {t['leaving_mw'].sum() / 1000:.1f} GW of coal leaving")
    print(t.groupby("status")["leaving_mw"].agg(["count", "sum"]).round(0).to_string())
    if args.limit:
        t = t.head(args.limit)
    t = screen.enrich(t, p)
    out = OUT_DIR / "pass1"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "sites.csv", float_format="%.4f")
    cols = ["plant", "state", "status", "leaving_mw", "pop_change", "income_vs_us", "hdd", "hot_hours",
            "sfha_share"]
    print(t[cols].head(25).round(2).to_string())
    print(f"\nwrote {out / 'sites.csv'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="brownfield")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check", help="parameters and known cases")
    sub.add_parser("rank", help="pass 1: rank the screened sites")
    sub.add_parser("module", help="pass 2: one module at Homer City, two designs")
    sub.add_parser("cost", help="pass 2b: costs, who pays and gains")
    sub.add_parser("homes", help="homes around the Homer City campus")
    sub.add_parser("sensitivity", help="which inputs move pass 2 most")
    sub.add_parser("house", help="pass 3: the first house's heat and radiant floor")
    sub.add_parser("block", help="pass 3: a block of new homes on the warm loop")
    sub.add_parser("frame", help="pass 3b: the walk-up's wood frame, sized")
    bp = sub.add_parser("build", help="pass 3b: the build sequence (after forge `build [steel|masonry]`)")
    bp.add_argument("system", nargs="?", default="wood", choices=["wood", "steel", "masonry"])
    sub.add_parser("compare", help="pass 3b: wood, light steel and block + precast side by side")
    sub.add_parser("costcarbon", help="pass 3b: embodied carbon and cost of the three structures")
    sub.add_parser("economy", help="pass 4: demand, a flat's economics, the campus's property tax")
    sub.add_parser("site", help="D12: the modular site plan: rules, scores, and proposed layouts")
    sub.add_parser("land", help="D17: the real land round the plant (public map services) and AWS's six sites")
    sub.add_parser("scorecard", help="the scorecard as the design now stands: four designs, the campus, the towns")
    sub.add_parser("water", help="pass 2f: the campus's water budget, from Two Lick Reservoir through the plant to the creeks")
    sub.add_parser("services", help="pass 4b: where the campus's tax goes, the schools, the hospital and emergency services")
    sub.add_parser("air", help="pass 2g: the gas plant's permitted air emissions against the coal plant's, and what each design adds")
    sub.add_parser("workforce", help="pass 4: the construction workforce 2026-2036, beds for crews from away, the shift on US 119")
    sub.add_parser("conference", help="D17-D18: the conference of communities on the real land, each town's new homes laid out, and forge's drawing data")
    sub.add_parser("village", help="pass 3e: the neighbourhood at the campus edge: townhouses, heat by month, noise, walks, money, growth")
    bs = sub.add_parser("bidset", help="pass 3f: the walk-up as a bid set in IFC4, written from forge's model and checked against it by two readers")
    bs.add_argument("--setup-reader", action="store_true", help="install the second reader, web-ifc (tools/webifc, npm ci with the dev group's Node)")
    sub.add_parser("food", help="pass 3d: winter food houses on the data center's warm water, and the arboretum")
    sub.add_parser("garden", help="pass 3c: the winter garden's heat, its cantilever, the rooftop coolers' noise (after forge `garden`)")
    sub.add_parser("creek", help="pass 2e: the gas plant blowdown against Blacklick Creek temperature criteria")
    sub.add_parser("wall", help="pass 2d: the wall in front of the coolers (then forge `wall`, then this again)")
    sub.add_parser("steel", help="pass 3b: the walk-up in light steel, sized")
    sub.add_parser("masonry", help="pass 3b: the walk-up in block and precast planks, sized")
    s = sub.add_parser("sites", help="pass 1: the site screen")
    s.add_argument("--limit", type=int, default=0, help="only the N largest sites (for testing)")
    args = ap.parse_args(argv)
    cmd = {"check": cmd_check, "sites": cmd_sites, "rank": cmd_rank, "module": cmd_module, "cost": cmd_cost, "homes": cmd_homes, "sensitivity": cmd_sensitivity, "house": cmd_house, "block": cmd_block, "frame": cmd_frame, "build": cmd_build, "steel": cmd_steel, "masonry": cmd_masonry, "compare": cmd_compare, "costcarbon": cmd_costcarbon, "economy": cmd_economy, "wall": cmd_wall, "creek": cmd_creek, "garden": cmd_garden, "food": cmd_food, "village": cmd_village, "site": cmd_site, "land": cmd_land, "conference": cmd_conference, "workforce": cmd_workforce, "scorecard": cmd_scorecard, "water": cmd_water, "air": cmd_air, "services": cmd_services, "bidset": cmd_bidset}.get(args.cmd or "check")
    return cmd(args)


if __name__ == "__main__":
    sys.exit(main())
