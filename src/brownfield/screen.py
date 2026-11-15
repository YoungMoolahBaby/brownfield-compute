"""Pass 1: the site screen. The plant list from EIA-860M, joined with the town (Census), the
climate (PVGIS) and the flood map (FEMA) at each site.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from . import climate, eia, flood, town

WORKERS = 4  # parallel requests per service: quick, and polite to public servers


def _each(fn, items, label):
    items = list(items)
    out = []
    with ThreadPoolExecutor(WORKERS) as ex:
        for i, r in enumerate(ex.map(fn, items), 1):
            out.append(r)
            if i % 50 == 0 or i == len(items):
                print(f"  {label}: {i}/{len(items)}", flush=True)
    return out


def plant_table(p: dict) -> pd.DataFrame:
    return eia.plants(eia.workbook(), retired_since=p["screen.coal.retired_since"],
                      retire_by=p["screen.coal.retire_by"], min_mw=p["screen.coal.min_mw"])


def enrich(t: pd.DataFrame, p: dict) -> pd.DataFrame:
    t = t.copy()
    pts = list(zip(t["lat"], t["lon"]))

    found = _each(lambda ll: town.county_of(*ll), pts, "county")
    t["fips"] = [f[0] if f else None for f in found]
    counties = town.county_table()
    t = t.join(counties, on="fips")
    t["income_vs_us"] = t["income"] / town.us_income()

    t = t.join(climate.site_climate(t[["lat", "lon"]], p["screen.climate.hdd_base_c"],
                                    p["screen.climate.dry_cooler_limit_c"]))

    half = p["screen.flood.half_m"]
    res = _each(lambda ll: flood.site(*ll, half), pts, "flood")
    t["sfha_share"] = [r[0] for r in res]
    t["flood_note"] = [r[1] for r in res]
    return t
