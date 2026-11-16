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
    print("check:", "passed" if ok else "FAILED")
    return 0 if ok else 1


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
    s = sub.add_parser("sites", help="pass 1: the site screen")
    s.add_argument("--limit", type=int, default=0, help="only the N largest sites (for testing)")
    args = ap.parse_args(argv)
    cmd = {"check": cmd_check, "sites": cmd_sites, "rank": cmd_rank, "module": cmd_module, "cost": cmd_cost, "homes": cmd_homes, "sensitivity": cmd_sensitivity, "house": cmd_house, "block": cmd_block}.get(args.cmd or "check")
    return cmd(args)


if __name__ == "__main__":
    sys.exit(main())
