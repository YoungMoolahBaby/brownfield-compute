"""American Community Survey 2019-2023 (5-year) tables for Indiana County, its municipalities and
Pennsylvania, from the Census Bureau's table-based summary file (bulk files on www2.census.gov; the
Census API needs a key). Each table file covers every geography in the country; we stream it and
keep the rows we want."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from . import RAW_DIR

BASE = "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF"
GEOS = f"{BASE}/documentation/Geos20235YR.txt"
USER_AGENT = "brownfield-compute (public research)"
DIR = RAW_DIR / "acs"

# Table: the estimate columns used (E = estimate).
TABLES = {
    "b01003": ["E001"],                                       # total population
    "b11001": ["E001"],                                       # households
    "b25002": ["E001", "E002", "E003"],                       # housing units: total, occupied, vacant
    "b25003": ["E002", "E003"],                               # owner, renter occupied
    "b25004": ["E002", "E003", "E004", "E005", "E006", "E008"],  # vacant: for rent, rented, for sale, sold, seasonal, other
    "b25064": ["E001"],                                       # median gross rent
    "b25119": ["E001", "E002", "E003"],                       # median household income: all, owners, renters
    "b25024": [f"E{i:03d}" for i in range(2, 12)],            # units in structure
    "b25034": [f"E{i:03d}" for i in range(2, 12)],            # year built, 2020+ ... 1939 or earlier
    "b25070": [f"E{i:03d}" for i in range(1, 12)],            # gross rent as a share of income
}


def _download(url: str, path: Path) -> Path:
    if not path.exists():
        with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=600, stream=True) as r:
            r.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
            tmp.replace(path)
    return path


def geographies(county: str = "Indiana County, Pennsylvania", state: str = "Pennsylvania") -> dict[str, str]:
    """GEO_ID -> name: the state, the county and the county's municipalities (county subdivisions)."""
    path = _download(GEOS, DIR / "Geos20235YR.txt")
    out = {}
    with open(path, encoding="utf-8-sig") as f:
        head = f.readline().rstrip("\n").split("|")
        i_sum, i_id, i_name = head.index("SUMLEVEL"), head.index("GEO_ID"), head.index("NAME")
        for line in f:
            c = line.rstrip("\n").split("|")
            if (c[i_sum] == "040" and c[i_name] == state) or (c[i_sum] in ("050", "060") and c[i_name].endswith(county)):
                out[c[i_id]] = c[i_name]
    return out


def table(name: str, geos: dict[str, str]) -> pd.DataFrame:
    path = _download(f"{BASE}/data/5YRData/acsdt5y2023-{name}.dat", DIR / f"acsdt5y2023-{name}.dat")
    rows = {}
    with open(path, encoding="utf-8-sig") as f:
        head = f.readline().rstrip("\n").split("|")
        cols = [head.index(f"{name.upper()}_{c}") for c in TABLES[name]]
        for line in f:
            gid = line[: line.find("|")]
            if gid in geos:
                c = line.rstrip("\n").split("|")
                rows[gid] = [pd.to_numeric(c[k], errors="coerce") for k in cols]
    return pd.DataFrame.from_dict(rows, orient="index", columns=[f"{name}_{c}" for c in TABLES[name]])


def housing(county: str = "Indiana County, Pennsylvania") -> pd.DataFrame:
    """Housing and income facts for the state, the county and each municipality."""
    geos = geographies(county)
    df = pd.concat([table(t, geos) for t in TABLES], axis=1)
    df.insert(0, "name", [geos[g] for g in df.index])
    out = pd.DataFrame({"name": df["name"]})
    out["population"] = df["b01003_E001"]
    out["households"] = df["b11001_E001"]
    out["housing_units"] = df["b25002_E001"]
    out["vacant"] = df["b25002_E003"]
    out["renters"] = df["b25003_E003"]
    out["for_rent"] = df["b25004_E002"]
    out["rental_vacancy"] = df["b25004_E002"] / (df["b25003_E003"] + df["b25004_E002"] + df["b25004_E003"])
    out["other_vacant"] = df["b25004_E008"]
    out["median_rent"] = df["b25064_E001"]
    out["median_income"] = df["b25119_E001"]
    out["renter_income"] = df["b25119_E003"]
    out["apartments_5plus"] = df[[f"b25024_E{i:03d}" for i in range(6, 10)]].sum(axis=1)
    out["built_2000_on"] = df[[f"b25034_E{i:03d}" for i in range(2, 5)]].sum(axis=1)
    out["built_pre_1960"] = df[[f"b25034_E{i:03d}" for i in range(9, 12)]].sum(axis=1)
    burdened = df[[f"b25070_E{i:03d}" for i in range(7, 11)]].sum(axis=1)
    out["rent_burdened"] = burdened / (df["b25070_E001"] - df["b25070_E011"])  # paying 30%+ of income, of those computed
    return out
