"""The town around a site, at county level: population trend and income (US Census Bureau).

County is coarse (a plant's town can shrink inside a growing county), but it is the finest level
with the same definitions everywhere; places come in the case-study pass. Bulk files, no API key
(the Census data API now requires one): population estimates and SAIPE income, downloaded into
data/raw/ on first use (~7 MB).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from . import RAW_DIR
from .http import USER_AGENT, fetch_json

GEOCODER = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
POPEST = "https://www2.census.gov/programs-surveys/popest/datasets"
FILES = {
    # Census 2010 count and estimates 2010-2020 (vintage 2020)
    "co-est2020-alldata.csv": f"{POPEST}/2010-2020/counties/totals/co-est2020-alldata.csv",
    # estimates 2020-2025 (vintage 2025)
    "co-est2025-alldata.csv": f"{POPEST}/2020-2025/counties/totals/co-est2025-alldata.csv",
    # Small Area Income and Poverty Estimates 2024 (released January 2026)
    "est24all.xls": "https://www2.census.gov/programs-surveys/saipe/datasets/2024/2024-state-and-county/est24all.xls",
}


def _file(name: str) -> Path:
    path = RAW_DIR / name
    if not path.exists():
        resp = requests.get(FILES[name], headers={"User-Agent": USER_AGENT}, timeout=300)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    return path


def county_of(lat: float, lon: float) -> tuple[str, str] | None:
    """(5-digit county FIPS, county name) containing a point, from the Census geocoder."""
    data = fetch_json(GEOCODER, params={"x": round(lon, 5), "y": round(lat, 5), "benchmark": "Public_AR_Current",
                                        "vintage": "Current_Current", "layers": "Counties", "format": "json"},
                      ttl_days=365)
    counties = data.get("result", {}).get("geographies", {}).get("Counties", [])
    if not counties:
        return None
    return counties[0]["GEOID"], counties[0]["NAME"]


def _popest(name: str, cols: list[str]) -> pd.DataFrame:
    d = pd.read_csv(_file(name), encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
    d = d[d["SUMLEV"] == 50]
    d.index = d["STATE"].str.zfill(2) + d["COUNTY"].str.zfill(3)
    # "X" marks a county that didn't exist at that date (e.g. Alaska's newer census areas).
    return d[cols].apply(pd.to_numeric, errors="coerce")


def county_table() -> pd.DataFrame:
    """Every county: population at Census 2010 and July 2025, change, median household income
    2024. Connecticut's counties became planning regions in 2022, so its change is missing."""
    t = pd.concat([
        _popest("co-est2020-alldata.csv", ["CENSUS2010POP"]).rename(columns={"CENSUS2010POP": "pop2010"}),
        _popest("co-est2025-alldata.csv", ["POPESTIMATE2025"]).rename(columns={"POPESTIMATE2025": "pop2025"}),
    ], axis=1)
    t["pop_change"] = t["pop2025"] / t["pop2010"] - 1.0
    s = pd.read_excel(_file("est24all.xls"), header=3, dtype={"State FIPS Code": str, "County FIPS Code": str})
    s = s[s["County FIPS Code"].str.zfill(3) != "000"]
    s.index = s["State FIPS Code"].str.zfill(2) + s["County FIPS Code"].str.zfill(3)
    t["income"] = pd.to_numeric(s["Median Household Income"], errors="coerce")
    return t


def us_income() -> float:
    """US median household income 2024 (SAIPE's national row)."""
    s = pd.read_excel(_file("est24all.xls"), header=3, dtype={"State FIPS Code": str, "County FIPS Code": str})
    return float(s[(s["State FIPS Code"].str.zfill(2) == "00")]["Median Household Income"].iloc[0])
