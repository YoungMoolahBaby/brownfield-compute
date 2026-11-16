"""Climate at a site from a PVGIS typical meteorological year (EU JRC; ERA5 in North America).

Two numbers matter for a liquid-cooled data center: the hours too hot for dry coolers alone (so
water or chillers are needed), and the heating degree days (how much waste heat a town could
use). The hourly temperatures are cached in .cache/climate/ (~44 kB a site); the stats are
recomputed on every run, so changing a threshold needs no re-download.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import requests

from . import ROOT
from .http import USER_AGENT

PVGIS_TMY = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
CACHE_DIR = ROOT / ".cache" / "climate"


def hourly_temp(lat: float, lon: float) -> np.ndarray:
    """8760 hourly air temperatures (C, 2 m) of the typical year, cached."""
    lat, lon = round(lat, 3), round(lon, 3)
    path = CACHE_DIR / f"{lat:.3f}_{lon:.3f}.json"
    if path.exists():
        return np.array(json.loads(path.read_text()), dtype=float)
    resp = requests.get(PVGIS_TMY, params={"lat": lat, "lon": lon, "outputformat": "json", "usehorizon": 0},
                        headers={"User-Agent": USER_AGENT}, timeout=120)
    resp.raise_for_status()
    temp = [round(float(r["T2m"]), 1) for r in resp.json()["outputs"]["tmy_hourly"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(temp))
    return np.array(temp, dtype=float)


def stats(temp: np.ndarray, base_c: float, limit_c: float) -> dict:
    """Mean, 99th percentile, heating degree days (C day, daily means against `base_c`), and the
    hours above `limit_c`."""
    daily = temp[: len(temp) // 24 * 24].reshape(-1, 24).mean(axis=1)
    return {
        "mean_c": float(temp.mean()),
        "p99_c": float(np.percentile(temp, 99)),
        "hdd": float(np.clip(base_c - daily, 0, None).sum()),
        "hot_hours": int((temp > limit_c).sum()),
    }


def site_climate(sites: pd.DataFrame, base_c: float, limit_c: float) -> pd.DataFrame:
    """Climate stats for every site (index plant_id, columns lat, lon)."""
    rows = {pid: stats(hourly_temp(r.lat, r.lon), base_c, limit_c) for pid, r in sites.iterrows()}
    return pd.DataFrame.from_dict(rows, orient="index")


def hourly_temp_rh(lat: float, lon: float) -> tuple[np.ndarray, np.ndarray]:
    """8760 hourly air temperatures (C) and relative humidities (%) of the typical year, cached."""
    lat, lon = round(lat, 3), round(lon, 3)
    path = CACHE_DIR / f"{lat:.3f}_{lon:.3f}_rh.json"
    if not path.exists():
        resp = requests.get(PVGIS_TMY, params={"lat": lat, "lon": lon, "outputformat": "json", "usehorizon": 0},
                            headers={"User-Agent": USER_AGENT}, timeout=120)
        resp.raise_for_status()
        rows = resp.json()["outputs"]["tmy_hourly"]
        data = {"t": [round(float(r["T2m"]), 1) for r in rows], "rh": [round(float(r["RH"]), 1) for r in rows]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    data = json.loads(path.read_text())
    return np.array(data["t"], dtype=float), np.array(data["rh"], dtype=float)


def hourly_weather(lat: float, lon: float) -> dict[str, np.ndarray]:
    """8760 hours of the typical year, cached: air temperature `t` (C), relative humidity `rh` (%),
    global horizontal irradiance `ghi` (W/m2), and `hour_utc` (0-23). PVGIS times are UTC."""
    lat, lon = round(lat, 3), round(lon, 3)
    path = CACHE_DIR / f"{lat:.3f}_{lon:.3f}_wx.json"
    if not path.exists():
        resp = requests.get(PVGIS_TMY, params={"lat": lat, "lon": lon, "outputformat": "json", "usehorizon": 0},
                            headers={"User-Agent": USER_AGENT}, timeout=120)
        resp.raise_for_status()
        rows = resp.json()["outputs"]["tmy_hourly"]
        data = {"t": [round(float(r["T2m"]), 1) for r in rows], "rh": [round(float(r["RH"]), 1) for r in rows],
                "ghi": [round(float(r["G(h)"]), 1) for r in rows],
                "hour_utc": [int(r["time(UTC)"][9:11]) for r in rows]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    data = json.loads(path.read_text())
    return {k: np.array(v, dtype=int if k == "hour_utc" else float) for k, v in data.items()}


def wet_bulb(t: np.ndarray, rh: np.ndarray) -> np.ndarray:
    """Wet-bulb temperature (C) from air temperature (C) and relative humidity (%), Stull (2011),
    J. Appl. Meteor. Climatol. 50: within ~0.3 K for RH 5-99% and -20 to 50 C at sea-level pressure."""
    rh = np.clip(rh, 5.0, 99.0)
    return (t * np.arctan(0.151977 * np.sqrt(rh + 8.313659)) + np.arctan(t + rh) - np.arctan(rh - 1.676331)
            + 0.00391838 * rh ** 1.5 * np.arctan(0.023101 * rh) - 4.686035)
