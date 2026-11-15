"""Coal plant sites from EIA-860M, the monthly US generator inventory.

One row per plant: how much coal capacity retired (and when), how much is set to retire, what
still runs there, and where it is. The coal capacity that leaves a site is a proxy for the grid
connection left behind (pass 1 research: whether the interconnection rights survive).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from . import RAW_DIR

# Pinned release, so a run is reproducible: September 2026 data, released 2026-10-23.
RELEASE = ("september", 2026)
BASE = "https://www.eia.gov/electricity/data/eia860m"
USER_AGENT = "brownfield-compute site screen"

# Coal, by EIA's technology names and energy source codes (Form EIA-860 instructions): anthracite,
# bituminous, lignite, subbituminous, refined coal, waste coal, coal-derived synthesis gas.
COAL_TECH = {"Conventional Steam Coal", "Coal Integrated Gasification Combined Cycle"}
COAL_FUEL = {"ANT", "BIT", "LIG", "SUB", "RC", "WC", "SGC"}

# Retired coal sites real developers have already chosen for a new use (RESEARCH.md): the screen
# must find them. (plant name contains, state). Not Naughton, WY (TerraPower's Natrium is next
# door): EIA lists its units 1-2 as coal with no planned retirement and unit 3 converted to gas,
# and a conversion isn't coal leaving the site.
KNOWN_CASES = [("Bull Run", "TN"), ("Homer City", "PA")]


def workbook(release: tuple[str, int] = RELEASE) -> Path:
    """The EIA-860M workbook, downloaded into data/raw/ on first use (~14 MB)."""
    month, year = release
    name = f"{month}_generator{year}.xlsx"
    path = RAW_DIR / name
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    for sub in ("xls", "archive/xls"):  # recent months sit in xls/, older ones in archive/
        resp = requests.get(f"{BASE}/{sub}/{name}", headers={"User-Agent": USER_AGENT}, timeout=300)
        if resp.ok and resp.content[:2] == b"PK":
            path.write_bytes(resp.content)
            return path
    raise RuntimeError(f"EIA-860M {name} not found under {BASE}")


def read_sheet(path: Path, sheet: str) -> pd.DataFrame:
    """A generator sheet: header on row 3, notes at the bottom dropped, numbers as numbers."""
    d = pd.read_excel(path, sheet, header=2)
    d = d[d["Plant ID"].notna() & d["Generator ID"].notna()].copy()
    d["Plant ID"] = d["Plant ID"].astype(int)
    for col in ("Nameplate Capacity (MW)", "Latitude", "Longitude", "Retirement Year", "Planned Retirement Year"):
        if col in d:
            d[col] = pd.to_numeric(d[col], errors="coerce")
    d["coal"] = d["Technology"].isin(COAL_TECH) | d["Energy Source Code"].isin(COAL_FUEL)
    return d


def plants(path: Path, retired_since: float, retire_by: float, min_mw: float) -> pd.DataFrame:
    """Coal plant sites with at least `min_mw` of coal retired since `retired_since` or set to
    retire by `retire_by`, largest first."""
    op = read_sheet(path, "Operating")
    ret = read_sheet(path, "Retired")
    mw = "Nameplate Capacity (MW)"

    def by_plant(rows: pd.DataFrame, col: str) -> pd.Series:
        return rows.groupby("Plant ID")[mw].sum().rename(col)

    coal_ret = ret[ret["coal"]]
    coal_op = op[op["coal"]]
    planned = coal_op["Planned Retirement Year"]
    parts = [
        by_plant(coal_ret[coal_ret["Retirement Year"] >= retired_since], "coal_retired_mw"),
        by_plant(coal_ret[coal_ret["Retirement Year"] < retired_since], "coal_retired_before_mw"),
        by_plant(coal_op[planned <= retire_by], "coal_retiring_mw"),
        by_plant(coal_op[~(planned <= retire_by)], "coal_staying_mw"),
        by_plant(op[~op["coal"]], "other_operating_mw"),
        coal_ret.groupby("Plant ID")["Retirement Year"].max().rename("last_retired"),
        coal_op[planned <= retire_by].groupby("Plant ID")["Planned Retirement Year"].max().rename("last_planned"),
    ]
    t = pd.concat(parts, axis=1).fillna({c: 0.0 for c in ("coal_retired_mw", "coal_retired_before_mw",
                                                          "coal_retiring_mw", "coal_staying_mw",
                                                          "other_operating_mw")})
    t["leaving_mw"] = t["coal_retired_mw"] + t["coal_retiring_mw"]
    t = t[t["leaving_mw"] >= min_mw]

    # Name, place and owner from the plant's coal rows (operating first: the current owner).
    info_cols = ["Plant Name", "Plant State", "County", "Entity Name", "Balancing Authority Code",
                 "Sector", "Latitude", "Longitude"]
    info = pd.concat([coal_op, coal_ret]).drop_duplicates("Plant ID").set_index("Plant ID")[info_cols]
    t = t.join(info, how="left")
    t["status"] = [
        "retired" if r.coal_retiring_mw == 0 and r.coal_staying_mw == 0
        else "partly staying" if r.coal_staying_mw > 0
        else "retiring"
        for r in t.itertuples()
    ]
    t = t.rename(columns={"Plant Name": "plant", "Plant State": "state", "County": "county",
                          "Entity Name": "owner", "Balancing Authority Code": "ba", "Sector": "sector",
                          "Latitude": "lat", "Longitude": "lon"})
    t.index.name = "plant_id"
    cols = ["plant", "state", "county", "owner", "ba", "sector", "status", "leaving_mw",
            "coal_retired_mw", "coal_retiring_mw", "coal_staying_mw", "coal_retired_before_mw",
            "other_operating_mw", "last_retired", "last_planned", "lat", "lon"]
    return t[cols].sort_values("leaving_mw", ascending=False)


def find_known(t: pd.DataFrame, cases=KNOWN_CASES) -> dict[tuple[str, str], pd.DataFrame]:
    """Rows of `t` matching each known case by name and state (empty frame if missing)."""
    out = {}
    for name, state in cases:
        hit = t[(t["state"] == state) & t["plant"].str.contains(name, case=False, na=False)]
        out[(name, state)] = hit
    return out
