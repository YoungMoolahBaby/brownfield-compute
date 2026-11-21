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
    global horizontal irradiance `ghi` (W/m2), wind speed at 10 m `ws` (m/s), and `hour_utc` (0-23).
    PVGIS times are UTC."""
    lat, lon = round(lat, 3), round(lon, 3)
    path = CACHE_DIR / f"{lat:.3f}_{lon:.3f}_wx.json"
    if not path.exists() or "ws" not in json.loads(path.read_text()):
        resp = requests.get(PVGIS_TMY, params={"lat": lat, "lon": lon, "outputformat": "json", "usehorizon": 0},
                            headers={"User-Agent": USER_AGENT}, timeout=120)
        resp.raise_for_status()
        rows = resp.json()["outputs"]["tmy_hourly"]
        data = {"t": [round(float(r["T2m"]), 1) for r in rows], "rh": [round(float(r["RH"]), 1) for r in rows],
                "ghi": [round(float(r["G(h)"]), 1) for r in rows], "ws": [round(float(r["WS10m"]), 2) for r in rows],
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


# ---- The sun on a wall (pass 3g step 2, cooling) ----

PVGIS_SERIES = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"


def sun_position(lat: float, lon: float, doy: np.ndarray, hour_utc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The sun's altitude and azimuth (degrees; azimuth clockwise from north) at fractional UTC hours,
    by NOAA's "General Solar Position Calculations" (NOAA Global Monitoring Laboratory): the
    fractional year, the equation of time and the declination as Fourier series, then the hour
    angle and the zenith. Good to a few hundredths of a degree for the design of a building."""
    doy, h = np.asarray(doy, float), np.asarray(hour_utc, float)
    g = 2 * np.pi / 365 * (doy - 1 + (h - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g)
                       - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g)
            - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    tst = h * 60 + eqtime + 4 * lon  # true solar time, minutes (UTC, so no time zone)
    ha = np.radians(tst / 4 - 180)
    phi = np.radians(lat)
    cos_z = np.clip(np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(ha), -1, 1)
    zen = np.arccos(cos_z)
    # Azimuth from north, clockwise: from the hour angle's sign (afternoon west of south).
    cos_az = np.clip((np.sin(decl) - np.sin(phi) * cos_z) / (np.cos(phi) * np.maximum(np.sin(zen), 1e-9)), -1, 1)
    az = np.degrees(np.arccos(cos_az))
    az = np.where(ha > 0, 360 - az, az)
    return 90 - np.degrees(zen), az


def pvgis_vertical(lat: float, lon: float, year: int, aspect: float, angle: float = 90) -> pd.DataFrame:
    """PVGIS's own hourly series for one year on a plane `angle` degrees from horizontal (90, a wall;
    0, the ground) facing `aspect` (PVGIS's: 0 south, 90 west, -90 east, 180 north), with the beam,
    diffuse and reflected parts and the sun's height: the known case for `vertical_irradiance`.
    Cached."""
    lat, lon = round(lat, 3), round(lon, 3)
    path = CACHE_DIR / (f"{lat:.3f}_{lon:.3f}_v{year}_{int(aspect)}" + ("" if angle == 90 else f"_a{int(angle)}") + ".json")
    if not path.exists():
        resp = requests.get(PVGIS_SERIES, params={"lat": lat, "lon": lon, "startyear": year, "endyear": year, "angle": angle,
                                                  "aspect": aspect, "components": 1, "outputformat": "json",
                                                  "usehorizon": 0}, headers={"User-Agent": USER_AGENT}, timeout=120)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(resp.json()["outputs"]["hourly"]))
    return pd.DataFrame(json.loads(path.read_text()))


# PVGIS's aspects for walls facing south, west, north and east (its convention: 0 south, 90 west).
WALL_ASPECTS = {"S": 0, "W": 90, "N": 180, "E": -90}


def pvgis_walls(lat: float, lon: float, y0: int = 2005, y1: int = 2023) -> dict:
    """Every hour of `y0`-`y1` at the site, from PVGIS (ERA5 here: PVGIS 5.3 offers no satellite
    radiation for the Americas): the sunlight on a vertical wall facing each of S, W, N and E (beam,
    diffuse and reflected, W/m2, PVGIS's own transposition), the air temperature `t` (C) and the
    UTC time stamps (half past each hour). For the cooling loads (pass 3g step 2). Cached."""
    lat, lon = round(lat, 3), round(lon, 3)
    path = CACHE_DIR / f"{lat:.3f}_{lon:.3f}_walls_{y0}_{y1}.json"
    if not path.exists():
        data = {}
        for face, aspect in WALL_ASPECTS.items():
            resp = requests.get(PVGIS_SERIES, params={"lat": lat, "lon": lon, "startyear": y0, "endyear": y1, "angle": 90,
                                                      "aspect": aspect, "components": 1, "outputformat": "json",
                                                      "usehorizon": 0}, headers={"User-Agent": USER_AGENT}, timeout=600)
            resp.raise_for_status()
            rows = resp.json()["outputs"]["hourly"]
            data[face] = [round(r["Gb(i)"] + r["Gd(i)"] + r["Gr(i)"], 1) for r in rows]
            if "t" not in data:
                data["t"] = [r["T2m"] for r in rows]
                data["time"] = [r["time"] for r in rows]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    data = json.loads(path.read_text())
    return {k: (np.array(v, dtype=float) if k != "time" else v) for k, v in data.items()}
