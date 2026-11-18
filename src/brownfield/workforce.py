"""Pass 4: the construction workforce at Homer City, 2026-2036, and what the towns must carry for it.

The developers' "10,000+ construction jobs" is a total over years, not a head count. This builds the
count month by month from what is on file:

- **The gas plant** (HCR, Kiewit): its reported head counts (1,000 in March 2026, 1,800 in September,
  ~2,000 by year-end), held through 2027 and wound down after first power (early 2028).
- **AWS's 39 data centers**: the filed schedule by site (Project Narrative, p. 2), each site's
  buildings started evenly across its window, each on site for `building_years` with
  `workers_per_building` (AWS's New Carlisle campus: ~145).

Then:
- **Who needs a bed**: the share from beyond a daily commute (`travel_share`), against the hotel rooms
  crews can hold and the rentals vacant above a balanced market's vacancy (ACS).
- **The region's own trades**: private construction employment within a daily commute (BLS QCEW).
- **The morning shift on US 119**: arrivals in the hour before the day shift against the highway's
  own peak hour and its capacity (PennDOT counts, the Highway Capacity Manual).

Uncertain inputs are drawn from their triangular ranges (`params.Param.sample`).
"""

from __future__ import annotations

import io
import math
import zipfile

import numpy as np
import pandas as pd
import requests

from . import RAW_DIR

W = "workforce."
SITES = {"Rura": "rura", "West": "west", "Harvey/Gaston": "harvey_gaston", "Bruner": "bruner", "Green": "green", "Helen": "helen"}
QCEW = "https://data.bls.gov/cew/data/api/{year}/a/area/{fips}.csv"
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_counties_national.zip"
UA = "brownfield-compute (public research)"
DIR = RAW_DIR / "qcew"


def months(t0: float = 2026.0, t1: float = 2037.0) -> np.ndarray:
    return np.arange(t0, t1, 1.0 / 12.0)


def aws(p: dict, counts: dict[str, int], t: np.ndarray) -> dict[str, np.ndarray]:
    """Workers on each AWS site each month: its buildings started evenly across its filed window (the
    last finishing at its completion), each on site for `building_years`."""
    T, per = p[W + "building_years"], p[W + "workers_per_building"]
    out = {}
    for name, key in SITES.items():
        a, b, n = p[W + "start." + key], p[W + "finish." + key], counts[name]
        act = np.zeros_like(t)
        for s in np.linspace(a, max(a, b - T), n):
            act += (t >= s) & (t < s + T)
        out[name] = act * per
    return out


def gas(p: dict, t: np.ndarray) -> np.ndarray:
    """The gas plant's crews: HCR's reported counts, its plateau through 2027, then down to none."""
    pl = p[W + "gas_plateau"]
    xs = [2025.5, 2026.23, 2026.67, 2027.0, 2027.92, max(2027.93, p[W + "gas_end"])]
    ys = [0.0, 1000.0, 1800.0, pl, pl, 0.0]
    return np.interp(t, xs, ys, left=0.0, right=0.0)


def total(p: dict, counts: dict[str, int], t: np.ndarray) -> np.ndarray:
    return gas(p, t) + sum(aws(p, counts, t).values())


# --- The region's own construction trades ------------------------------------------------------------

def _get(url: str, path) -> bytes:
    if not path.exists():
        r = requests.get(url, headers={"User-Agent": UA}, timeout=300)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path.read_bytes()


def counties_within(p: dict, lat0: float, lon0: float) -> list[tuple[str, str, float]]:
    """Counties whose centre lies within `commute_km` of the plant: (FIPS, name, km)."""
    z = zipfile.ZipFile(io.BytesIO(_get(GAZ, DIR / "gaz_counties.zip")))
    df = pd.read_csv(z.open(z.namelist()[0]), sep="\t", dtype={"GEOID": str})
    df.columns = [c.strip() for c in df.columns]
    kx = 111.32 * math.cos(math.radians(lat0))
    d = np.hypot((df["INTPTLONG"] - lon0) * kx, (df["INTPTLAT"] - lat0) * 111.32)
    near = df[d <= p[W + "commute_km"]].assign(km=d[d <= p[W + "commute_km"]])
    return [(r.GEOID, f"{r.NAME}, {r.USPS}", float(r.km)) for r in near.sort_values("km").itertuples()]


def construction_jobs(fips: str, year: int = 2024) -> float:
    """Private construction employment (NAICS 23), the year's average (BLS QCEW, open data)."""
    df = pd.read_csv(io.BytesIO(_get(QCEW.format(year=year, fips=fips), DIR / f"{fips}_{year}a.csv")), dtype=str)
    row = df[(df["own_code"] == "5") & (df["industry_code"] == "23")]
    return float(row["annual_avg_emplvl"].iloc[0]) if len(row) else 0.0


# --- Beds -----------------------------------------------------------------------------------------------

def beds(p: dict, housing: pd.DataFrame) -> dict:
    """Places crews from away can stay without squeezing the town: hotel rooms they can hold, and the
    county's rentals vacant above a balanced market's vacancy."""
    county = housing[housing["name"].str.startswith("Indiana County")].iloc[0]
    stock = county["for_rent"] / county["rental_vacancy"]
    spare = max(0.0, county["for_rent"] - p[W + "healthy_vacancy"] * stock)
    hotel = p[W + "hotel_rooms"] * p[W + "hotel_share_crews"]
    return {"for_rent": float(county["for_rent"]), "vacancy": float(county["rental_vacancy"]), "stock": float(stock),
            "spare_rentals": float(spare), "hotel": float(hotel), "units": float(spare + hotel)}


def need(p: dict, workers: np.ndarray) -> np.ndarray:
    """Hotel rooms or homes crews from away need."""
    return workers * p[W + "travel_share"] / p[W + "workers_per_unit"]


# --- The morning shift on US 119 -------------------------------------------------------------------------

def us119_aadt(layers: dict, lat0: float, lon0: float) -> float:
    """PennDOT's count on the US 119 carriageway nearest the plant (vehicles a day, one direction)."""
    from shapely.geometry import Point, shape

    from .homes import Local

    loc = Local(lat0, lon0)
    best = None
    for f in layers["state_roads"]:
        pr = f.get("properties") or {}
        if "STAPLETON" not in (pr.get("STREET_NAM") or "") or not pr.get("CUR_AADT") or not f.get("geometry"):
            continue
        d = loc.geom(shape(f["geometry"])).distance(Point(0, 0))
        if best is None or d < best[0]:
            best = (d, float(pr["CUR_AADT"]))
    return best[1] if best else float("nan")


def traffic(p: dict, workers: float, aadt_dir: float) -> dict:
    """The hour before the day shift: construction arrivals on US 119 against its peak hour and capacity
    (two lanes each way)."""
    arrive = workers / p[W + "vehicle_occupancy"] * p[W + "arrive_hour_share"] * p[W + "via_119_share"]
    base = aadt_dir * p[W + "k_factor"]
    cap = 2 * p[W + "lane_capacity"]
    return {"arrivals": arrive, "base": base, "capacity": cap, "vc_before": base / cap, "vc_after": (base + arrive) / cap}


# --- Uncertainty ------------------------------------------------------------------------------------------

DRAWN = ("building_years", "workers_per_building", "gas_plateau", "gas_end", "travel_share", "workers_per_unit", "hotel_rooms",
         "hotel_share_crews", "healthy_vacancy", "vehicle_occupancy", "arrive_hour_share", "via_119_share")


def monte_carlo(params: dict, counts: dict[str, int], housing: pd.DataFrame, aadt_dir: float, n: int = 2000, seed: int = 4) -> dict:
    """Peak workforce, peak units needed against the units available, and the shift's v/c, over draws."""
    from .params import values

    rng = np.random.default_rng(seed)
    p0 = values(params)
    draws = {k: params[W + k].sample(rng, n) for k in DRAWN}
    t = months()
    peak, short, vc, months_short = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    workers, needs = np.zeros((n, len(t))), np.zeros((n, len(t)))
    for i in range(n):
        q = dict(p0, **{W + k: float(v[i]) for k, v in draws.items()})
        w = total(q, counts, t)
        u = need(q, w)
        b = beds(q, housing)["units"]
        workers[i], needs[i] = w, u
        peak[i], short[i] = w.max(), u.max() - b
        months_short[i] = float((u > b).sum())
        vc[i] = traffic(q, w.max(), aadt_dir)["vc_after"]
    pct = lambda a: np.percentile(a, [10, 50, 90])
    sm = months_short[short > 0]
    return {"n": n, "peak": pct(peak), "short": pct(short), "p_short": float((short > 0).mean()),
            "months_short": float(np.median(sm)) if len(sm) else 0.0,
            "vc": pct(vc), "p_over": float((vc > 1.0).mean()),
            "workers_band": np.percentile(workers, [10, 90], axis=0), "need_band": np.percentile(needs, [10, 90], axis=0)}


# --- Report ------------------------------------------------------------------------------------------------

def report(p: dict, counts: dict, t: np.ndarray, sites_w: dict, gas_w: np.ndarray, b: dict, region: list, jobs: dict,
           near_rent: pd.DataFrame, tr: dict, mc: dict) -> str:
    w = gas_w + sum(sites_w.values())
    i = int(w.argmax())
    yr = lambda x: f"{int(x)}-{int(round((x % 1) * 12)) + 1:02d}"
    worker_years = w.sum() / 12.0
    u = need(p, w)
    short_months = int((u > b["units"]).sum())
    reg = sum(jobs.values())
    L = ["**The construction workforce, 2026-2036** (the gas plant's reported counts; AWS's filed schedule)", "",
         f"- Peak: **{w.max():,.0f} workers on site** in {yr(t[i])} ({gas_w[i]:,.0f} at the gas plant, {w[i] - gas_w[i]:,.0f} on AWS's sites); "
         f"{worker_years:,.0f} worker-years in all, 2026-2036.",
         "- By year (average workers on site):", "",
         "| Year | Gas plant | " + " | ".join(SITES) + " | All |", "|---" * (len(SITES) + 3) + "|"]
    for y in range(2026, 2037):
        m = (t >= y) & (t < y + 1)
        cells = [f"{gas_w[m].mean():,.0f}"] + [f"{sites_w[s][m].mean():,.0f}" for s in SITES] + [f"**{w[m].mean():,.0f}**"]
        L.append(f"| {y} | " + " | ".join(cells) + " |")
    L += ["", f"- Buildings: {', '.join(f'{s} {counts[s]}' for s in SITES)}; each on site ~{p[W + 'building_years']:g} years "
          f"with ~{p[W + 'workers_per_building']:.0f} workers.",
          "", "**The region's own trades** (private construction employment, 2024 average, BLS QCEW; counties whose centre is within "
          f"{p[W + 'commute_km']:.0f} km)", "",
          "| County | km | Construction jobs |", "|---|---|---|"]
    for fips, name, km in region:
        L.append(f"| {name} | {km:.0f} | {jobs[fips]:,.0f} |")
    L += [f"| **All** | | **{reg:,.0f}** |", "",
          f"- The peak is {w.max() / reg:.1%} of the construction workforce within a daily commute.",
          "", "**Beds for crews from away**", "",
          f"- At {p[W + 'travel_share']:.0%} from beyond a daily commute, {p[W + 'workers_per_unit']:g} to a room or home: "
          f"**{u.max():,.0f} rooms or homes** at the peak.",
          f"- Available without squeezing the town: {b['hotel']:,.0f} hotel rooms crews can hold ({p[W + 'hotel_share_crews']:.0%} of ~"
          f"{p[W + 'hotel_rooms']:,.0f}) and {b['spare_rentals']:,.0f} of Indiana County's {b['for_rent']:,.0f} vacant rentals (the county's "
          f"rental vacancy is {b['vacancy']:.1%}; a balanced market's is ~{p[W + 'healthy_vacancy']:.0%}): **{b['units']:,.0f}**.",
          f"- Months the need exceeds them (base case): {short_months}.",
          "- Where the vacant rentals are, and the towns next to the site:", "",
          "| Place | Renter homes | Vacant for rent | Median rent |", "|---|---|---|---|"]
    for _, r in near_rent.iterrows():
        L.append(f"| {r['name'].split(',')[0]} | {r['renters']:,.0f} | {r['for_rent']:,.0f} | ${r['median_rent']:,.0f} |")
    L += ["", f"**The morning shift on US 119** (the nearest carriageway: {tr['aadt']:,.0f} vehicles a day)", "",
          f"- At the peak, {tr['arrivals']:,.0f} construction vehicles in the hour before the day shift, on top of the road's own peak hour of "
          f"{tr['base']:,.0f}, against {tr['capacity']:,.0f} an hour for two lanes: volume to capacity {tr['vc_before']:.2f} before, "
          f"**{tr['vc_after']:.2f}** with the crews.",
          "", f"**Uncertainty** ({mc['n']:,} draws over the ranges in params/workforce.yaml; P10 / P50 / P90)", "",
          f"- Peak on site: {mc['peak'][0]:,.0f} / {mc['peak'][1]:,.0f} / {mc['peak'][2]:,.0f} workers.",
          f"- Rooms or homes needed at the peak minus those available: {mc['short'][0]:+,.0f} / {mc['short'][1]:+,.0f} / {mc['short'][2]:+,.0f}; "
          f"short at some point in {mc['p_short']:.0%} of draws; in those, for {mc['months_short']:.0f} months (median).",
          f"- US 119's volume to capacity in the shift hour: {mc['vc'][0]:.2f} / {mc['vc'][1]:.2f} / {mc['vc'][2]:.2f}; over capacity in "
          f"{mc['p_over']:.0%} of draws."]
    return "\n".join(L)
