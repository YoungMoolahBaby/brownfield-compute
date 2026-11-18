"""Pass 4b: the schools, the hospital and emergency services round the Homer City campus.

- **Where the tax goes** (`districts.py`, `econ.campus_tax`): about half the campus stands in Black
  Lick Township, which is in the River Valley School District (formerly Blairsville-Saltsburg), not
  Homer-Center.
- **The schools:** PDE's enrolment (October 1 counts, 2014-15 to 2025-26) for both districts; the
  newcomers' children (D18's homes, by the district each town is in); each district's 2023-24
  revenue and its market value / personal income aid ratio, recomputed with the campus's market
  value added (PDE's published formula and the floors in its own file).
  - **Uniformity:** a Pennsylvania district levies one millage on all its property, so the
    campus's value lowers the millage everyone pays for the same revenue. Residents' share of the
    school tax falls to their share of the district's market value.
- **The hospital:** car minutes (OSRM, free-flow, not ambulance) from each town and each AWS site
  to the emergency department in Indiana and the nearest adult trauma centres (data/hospitals.csv).
- **The build:** BLS construction injury and fatality rates on the workforce model's worker-years.
- **The fire service:** what each design stores on site: batteries (the good neighbour) or diesel
  generators (the others), from `scorecard.backup`.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from . import DATA_DIR, RAW_DIR

PDE = RAW_DIR / "pde"
ENROLL_CSV = DATA_DIR / "pde_enrollment_districts.csv"
HOSP_CSV = DATA_DIR / "hospitals.csv"
OSRM_CACHE = RAW_DIR / "care" / "osrm_table.json"
DISTRICTS = {128323303: "Homer-Center", 128321103: "River Valley"}
TIGER = {"Homer-Center School District": "Homer-Center", "Blairsville-Saltsburg School District": "River Valley"}
TOWNSHIP = {"Center township": "Homer-Center", "Black Lick township": "River Valley"}
GRADE_COLS = ["K4F", "K5F", "001", "002", "003", "004", "005", "006", "007", "008", "009", "010", "011", "012"]
PDE_ENROLL = "https://www.pa.gov/content/dam/copapwp-pagov/en/education/documents/data-and-reporting/enrollment/public-school/"
PDE_FIN = "https://www.pa.gov/content/dam/copapwp-pagov/en/education/documents/schools/grants-and-funding/school-finances/"
FILES = {"consolidated_1617_2526.xlsx": PDE_ENROLL + "enrollment%20public%20school%201617%20through%202526.xlsx",
         "enrollment_2014-15.xlsx": PDE_ENROLL + "enrollment%20public%20schools%202014-15.xlsx",
         "enrollment_2025-26.xlsx": PDE_ENROLL + "enrollment%20public%20schools%202025-2026.xlsx",
         "aidratio_2025-26.xlsx": PDE_FIN + "financial-data-elements/aid-ratios/finances%20aidratio%202025-2026.xlsx",
         "afr_revenues_2023-24.xlsx": PDE_FIN + "summary-of-afr-data/afr-data-summary-level/finances%20afr%20revenues%202023-2024.xlsx"}


def _file(name: str):
    path = PDE / name
    if not path.exists():
        import requests

        PDE.mkdir(parents=True, exist_ok=True)
        r = requests.get(FILES[name], headers={"User-Agent": "brownfield-compute (public research)"}, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def _sheet(name: str, sheet, header: int) -> pd.DataFrame:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d = pd.read_excel(_file(name), sheet, header=header, engine="openpyxl")
    d.columns = [str(c).replace("\n", " ").strip() for c in d.columns]
    if "AUN" in d.columns:
        d["AUN"] = pd.to_numeric(d["AUN"], errors="coerce")  # text in some years' files
    return d


# --- The schools ----------------------------------------------------------------------------------

def grades(lea: pd.DataFrame) -> pd.DataFrame:
    """One row per district from a PDE 'LEA' sheet: kindergarten (full- and half-day) and grades 1-12."""
    d = lea[lea["AUN"].isin(DISTRICTS)].copy()
    k = [c for c in d.columns if c.startswith("K5")]
    out = pd.DataFrame({"district": d["AUN"].map(DISTRICTS).values, "K": d[k].apply(pd.to_numeric, errors="coerce").sum(axis=1).values})
    for g in GRADE_COLS[2:]:
        out[f"g{int(g)}"] = pd.to_numeric(d[g], errors="coerce").values
    return out


def enrollment(refresh: bool = False) -> pd.DataFrame:
    """Both districts by school year: total enrolment, and by grade where PDE's yearly file was read."""
    if ENROLL_CSV.exists() and not refresh:
        return pd.read_csv(ENROLL_CSV, comment="#")
    c = _sheet("consolidated_1617_2526.xlsx", "10 Year LEA Enrollment", 5)
    c = c[c["AUN"].isin(DISTRICTS)]
    rows = []
    for _, r in c.iterrows():
        for col in [x for x in c.columns if x[:4].isdigit()]:
            rows.append({"district": DISTRICTS[int(r["AUN"])], "year": col, "total": float(r[col])})
    for name, year in (("enrollment_2014-15.xlsx", "2014-2015"), ("enrollment_2025-26.xlsx", "2025-2026")):
        g = grades(_sheet(name, "LEA", 4))
        lea = _sheet(name, "LEA", 4)
        tot = lea[lea["AUN"].isin(DISTRICTS)].set_index("AUN")["Total"]
        for _, r in g.iterrows():
            aun = next(a for a, n in DISTRICTS.items() if n == r["district"])
            row = next((x for x in rows if x["district"] == r["district"] and x["year"] == year), None)
            if row is None:
                row = {"district": r["district"], "year": year, "total": float(tot[aun])}
                rows.append(row)
            row.update({k: float(v) for k, v in r.items() if k != "district"})
    a = pd.DataFrame(rows).sort_values(["district", "year"]).reset_index(drop=True)
    head = ("# Homer-Center SD (AUN 128323303) and River Valley SD (AUN 128321103, formerly Blairsville-Saltsburg), October 1\n"
            "# enrolment from PDE: the 10-year LEA file (2015-16 to 2025-26) and the yearly LEA sheets for 2014-15 and 2025-26\n"
            "# (grades: K = full- and half-day kindergarten; pre-K left out). https://www.pa.gov/agencies/education/data-and-reporting/enrollment\n")
    ENROLL_CSV.write_text(head + a.to_csv(index=False), encoding="utf-8", newline="")
    return a


def aid_ratio(mv: float, pi: float, wadm: float, state_mv: float, state_pi: float, p: dict) -> dict[str, float]:
    """PDE's market value / personal income aid ratio, with the floors seen in its file. The
    methodology's truncations to four decimals are kept."""
    s = "services.schools."
    t4 = lambda x: math.floor(x * 1e4) / 1e4  # noqa: E731
    mv_ar = max(p[s + "ar_floor"], 1 - t4(0.5 * t4(math.floor(mv / wadm) / state_mv)))
    pi_ar = max(p[s + "ar_floor"], 1 - t4(0.5 * t4(math.floor(pi / wadm) / state_pi)))
    w = p[s + "mv_weight"]
    return {"mv_ar": mv_ar, "pi_ar": pi_ar, "mvpi_ar": max(p[s + "mvpi_floor"], t4(w * mv_ar) + t4((1 - w) * pi_ar))}


def state_per_wadm(ar: pd.DataFrame) -> tuple[float, float]:
    """The state's market value and personal income per WADM that PDE's ratios imply (districts above
    the floor)."""
    mv = ar[ar.mv_ar > 0.15]
    pi = ar[ar.pi_ar > 0.15]
    return float(np.median(mv.mv_wadm * 0.5 / (1 - mv.mv_ar))), float(np.median(pi.pi_wadm * 0.5 / (1 - pi.pi_ar)))


def money(p: dict) -> dict[str, dict]:
    """Each district's 2023-24 revenue against its share of the campus's school tax, its aid ratio
    before and after the campus's market value lands, and what the campus does to residents' share."""
    from . import econ

    ar = _sheet("aidratio_2025-26.xlsx", "SD", 0)
    ar.columns = ["fy", "aun", "name", "county", "mv", "pi", "wadm", "mv_wadm", "mv_ar", "pi_wadm", "pi_ar", "mvpi_ar"]
    s_mv, s_pi = state_per_wadm(ar)
    rev = _sheet("afr_revenues_2023-24.xlsx", 0, 0)
    tax = _sheet("afr_revenues_2023-24.xlsx", 2, 0)
    tx = econ.campus_tax(p)
    campus_mv = {"Homer-Center": tx["market_value"] * tx["share_center"], "River Valley": tx["market_value"] * tx["share_blacklick"]}
    campus_tax = {"Homer-Center": tx["school_homer_center"], "River Valley": tx["school_river_valley"]}
    out = {}
    for aun, name in DISTRICTS.items():
        a = ar[ar.aun == aun].iloc[0]
        rv = rev[rev["AUN"] == aun].iloc[0]
        t = tax[tax["AUN"] == aun].iloc[0]
        mv, re_tax = float(t["2023 STEB Market Value"]), float(t["Current and Interim Real Estate Taxes Collected"])
        state = float(rv["Total State Revenue 7000"])
        before = aid_ratio(float(a.mv), float(a.pi), float(a.wadm), s_mv, s_pi, p)
        after = aid_ratio(float(a.mv) + campus_mv[name], float(a.pi), float(a.wadm), s_mv, s_pi, p)
        share = mv / (mv + campus_mv[name])  # residents' (everything but the campus) share of the district's market value
        out[name] = {"revenue": float(rv["Total Revenue"]), "state": state, "local_taxes": float(rv["Local Taxes (6111-6400)"]),
                     "re_tax": re_tax, "mv": mv, "campus_mv": campus_mv[name], "campus_tax": campus_tax[name],
                     "ar_pde": float(a.mvpi_ar), "ar_before": before["mvpi_ar"], "ar_after": after["mvpi_ar"],
                     "residents_share": share,
                     "residents_same_spend": share * re_tax, "residents_all_state_lost": share * (re_tax + state)}
    return out


def newcomers(p: dict, layers: dict) -> dict[str, float]:
    """D18's newcomers' school-age children, by the school district each town stands in."""
    from . import conference as cf, districts, land
    from .homes import Local

    town = cf.towns(p, layers)
    th = cf.town_homes(p, town)
    loc = Local(*land.PLANT)
    sd = districts.polygons("school_districts", p)
    out = {n: 0.0 for n in DISTRICTS.values()}
    for k, t in town.items():
        x, y = t["xy"]
        name = districts.assign(np.array([loc.lon0 + x / loc.kx]), np.array([loc.lat0 + y / 111_320.0]), sd)[0]
        out[TIGER[name]] += th[k]["children"]
    return out


# --- The hospital and the drive -------------------------------------------------------------------

def hospitals() -> pd.DataFrame:
    return pd.read_csv(HOSP_CSV, comment="#")


def osrm_table(origins: dict[str, tuple[float, float]], dests: dict[str, tuple[float, float]], refresh: bool = False) -> dict:
    """Free-flow car minutes and km from each origin to each destination (lat, lon), by the public OSRM
    router's table service; cached."""
    key = json.dumps({"o": origins, "d": dests}, sort_keys=True)
    cache = json.loads(OSRM_CACHE.read_text(encoding="utf-8")) if OSRM_CACHE.exists() else {}
    if key not in cache or refresh:
        import requests

        pts = list(origins.values()) + list(dests.values())
        coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in pts)
        n = len(origins)
        r = requests.get(f"https://router.project-osrm.org/table/v1/driving/{coords}",
                         params={"sources": ";".join(map(str, range(n))), "destinations": ";".join(map(str, range(n, len(pts)))),
                                 "annotations": "duration,distance"},
                         headers={"User-Agent": "brownfield-compute (public research)"}, timeout=120)
        r.raise_for_status()
        cache[key] = r.json()
        OSRM_CACHE.parent.mkdir(parents=True, exist_ok=True)
        OSRM_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    t = cache[key]
    names_o, names_d = list(origins), list(dests)
    return {"minutes": pd.DataFrame(np.array(t["durations"], float) / 60, index=names_o, columns=names_d),
            "km": pd.DataFrame(np.array(t["distances"], float) / 1000, index=names_o, columns=names_d)}


def straight_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def origins(p: dict, layers: dict) -> dict[str, tuple[float, float]]:
    """Each town's middle and each AWS site's centre, (lat, lon)."""
    from shapely.geometry import shape

    from . import conference as cf, land
    from .homes import Local

    loc = Local(*land.PLANT)
    out = {}
    for k, t in cf.towns(p, layers).items():
        x, y = t["xy"]
        out[k] = (loc.lat0 + y / 111_320.0, loc.lon0 + x / loc.kx)
    g = json.loads((DATA_DIR / "aws_sites.geojson").read_text(encoding="utf-8"))
    for f in g["features"]:
        c = shape(f["geometry"]).centroid
        out[f"AWS {f['properties']['site']}"] = (c.y, c.x)
    return out


# --- The build and the fire service ---------------------------------------------------------------

def construction(p: dict, w: np.ndarray, t: np.ndarray) -> dict:
    """Worker-years on site (monthly series) and the injuries and deaths BLS's rates put on them."""
    c = "services.construction."
    dt = float(np.median(np.diff(t)))
    years = float(w.sum() * dt)
    peak_year = float(w.max())
    return {"worker_years": years, "injuries": years * p[c + "recordable_per_100_fte"] / 100,
            "deaths": years * p[c + "fatal_per_100k_fte"] / 1e5, "peak": peak_year,
            "injuries_peak_year": peak_year * p[c + "recordable_per_100_fte"] / 100}


def stores(p: dict) -> dict[str, dict]:
    """What each design keeps on site for backup, across the campus."""
    from . import scorecard

    n = p["scorecard.campus_it_mw"] / p["pass2.module.it_mw"]
    gn, conv = scorecard.backup("good neighbour", p), scorecard.backup("conventional", p)
    return {"good neighbour": {"battery_mwh": gn["battery_mwh"] * n, "gensets": 0},
            "the others": {"battery_mwh": 0.0, "gensets": conv["gensets"] * n}}


# --- Analysis, checks, report, figure ---------------------------------------------------------------

def checks(p: dict) -> dict:
    """Known case: PDE's 2025-26 aid ratios for both districts, recomputed from the file's own market
    value, income and WADM with the published formula."""
    ar = _sheet("aidratio_2025-26.xlsx", "SD", 0)
    ar.columns = ["fy", "aun", "name", "county", "mv", "pi", "wadm", "mv_wadm", "mv_ar", "pi_wadm", "pi_ar", "mvpi_ar"]
    s_mv, s_pi = state_per_wadm(ar)
    out = {}
    for aun, name in DISTRICTS.items():
        a = ar[ar.aun == aun].iloc[0]
        out[name] = (aid_ratio(float(a.mv), float(a.pi), float(a.wadm), s_mv, s_pi, p)["mvpi_ar"], float(a.mvpi_ar))
    return out


def analyse(params: dict) -> dict:
    from . import districts, econ, land, workforce as wf
    from .params import values

    p = values(params)
    layers = land.fetch_all(p)
    sites = land.aws_sites(p)
    land.site_counts(p, sites)
    t = wf.months()
    w = wf.total(p, {k: s["n"] for k, s in sites.items()}, t)
    o = origins(p, layers)
    h = hospitals()
    dest = {r["name"]: (r["lat"], r["lon"]) for _, r in h.iterrows()}
    return {"p": p, "split": districts.buildings(p), "tax": econ.campus_tax(p), "enroll": enrollment(), "money": money(p),
            "kids": newcomers(p, layers), "origins": o, "hosp": h, "drive": osrm_table(o, dest),
            "build": construction(p, w, t), "stores": stores(p), "checks": checks(p)}


def report(a: dict) -> str:
    p, tx, e, m, k = a["p"], a["tax"], a["enroll"], a["money"], a["kids"]
    G = int(p["services.schools.grades"])
    L = ["**1. Where the tax goes** (AWS's 39 buildings by township and school district; pass 4's tax at full build-out)", "",
         "| Site | Township | School district | Buildings |", "|---|---|---|---|"]
    for _, r in a["split"].iterrows():
        L.append(f"| {r.site} | {r.township} | {TIGER.get(r.school_district, r.school_district)} | {r.buildings:.1f} |")
    L += ["", f"Center Township and Homer-Center: {tx['share_center']:.0%} of the buildings; Black Lick Township and River Valley: "
          f"{tx['share_blacklick']:.0%}.", "",
          "| Taxing body | A year |", "|---|---|",
          f"| Indiana County | ${tx['county'] / 1e6:,.1f}M |", f"| Center Township | ${tx['township_center'] / 1e6:,.1f}M |",
          f"| Black Lick Township | ${tx['township_blacklick'] / 1e6:,.1f}M |",
          f"| Homer-Center School District | ${tx['school_homer_center'] / 1e6:,.1f}M |",
          f"| River Valley School District | ${tx['school_river_valley'] / 1e6:,.1f}M |",
          f"| **Total** | **${tx['total'] / 1e6:,.1f}M** |"]
    last, first = e[e.year == "2025-2026"].set_index("district"), e.groupby("district")
    L += ["", "**2. The schools** (PDE, October 1 enrolment; the newcomers' children from D18's homes)", "",
          "| District | 2025-26 | Most since 2014-15 (year) | Room against that | Pupils a grade now | Newcomers' children | A grade |",
          "|---|---|---|---|---|---|---|"]
    for name in DISTRICTS.values():
        g = first.get_group(name)
        top = g.loc[g.total.idxmax()]
        now = last.loc[name, "total"]
        L.append(f"| {name} | {now:,.0f} | {top.total:,.0f} ({top.year}) | {top.total - now:,.0f} | {now / G:,.0f} | {k[name]:,.0f} | "
                 f"{k[name] / G:.1f} |")
    L += ["", "**3. The money** (each district's 2023-24 revenue, PDE; its share of the campus's school tax at today's millage; "
          "the aid ratio recomputed with the campus's market value)", "",
          "| District | Revenue | State | Real estate tax | Campus's school tax | Aid ratio now (PDE) | With the campus | "
          "Everyone else's share of the market value | Their real estate tax, same spending | If all state aid were lost |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for name, x in m.items():
        L.append(f"| {name} | ${x['revenue'] / 1e6:,.1f}M | ${x['state'] / 1e6:,.1f}M | ${x['re_tax'] / 1e6:,.2f}M | "
                 f"${x['campus_tax'] / 1e6:,.1f}M | {x['ar_pde']:.4f} | {x['ar_after']:.4f} | {x['residents_share']:.0%} | "
                 f"${x['residents_same_spend'] / 1e6:,.2f}M ({x['residents_same_spend'] / x['re_tax'] - 1:+.0%}) | "
                 f"${x['residents_all_state_lost'] / 1e6:,.2f}M ({x['residents_all_state_lost'] / x['re_tax'] - 1:+.0%}) |")
    mins = a["drive"]["minutes"]
    h = a["hosp"]
    lvl = dict(zip(h.name, h.trauma_level))
    one = [n for n in mins.columns if lvl[n] in ("I", "II")]
    L += ["", "**4. The hospital** (car minutes, free-flow, by the public OSRM router; not an ambulance's)", "",
          "| From | Indiana Regional (ED, Level IV) | Nearest Level I or II trauma centre | Its minutes |", "|---|---|---|---|"]
    for o, r in mins.iterrows():
        near = r[one].idxmin()
        L.append(f"| {o} | {r['Indiana Regional Medical Center']:.0f} | {near} ({lvl[near]}) | {r[near]:.0f} |")
    b, st = a["build"], a["stores"]
    L += ["", "**5. The build and the fire service**", "",
          f"- **The build, 2026-2036:** {b['worker_years']:,.0f} worker-years on site (peak {b['peak']:,.0f}). At BLS's construction "
          f"rates that is ~{b['injuries']:,.0f} recorded injuries and illnesses and ~{b['deaths']:.1f} deaths over the decade; "
          f"~{b['injuries_peak_year']:,.0f} injuries in the peak year.",
          f"- **What the campus keeps for backup:** the good neighbour ~{st['good neighbour']['battery_mwh']:,.0f} MWh of batteries; the "
          f"other designs ~{st['the others']['gensets']:,.0f} diesel generators and their fuel."]
    c = a["checks"]
    L += ["", "**Checks**", "",
          "- **PDE's aid ratios recomputed** from the file's own market value, income and WADM with the published formula: "
          + "; ".join(f"{n} {v[0]:.4f} against PDE's {v[1]:.4f}" for n, v in c.items()) + ".",
          f"- **The drive:** Homer City to Indiana Regional is {mins.loc['Homer City', 'Indiana Regional Medical Center']:.0f} minutes and "
          f"{a['drive']['km'].loc['Homer City', 'Indiana Regional Medical Center']:.1f} km by road, "
          f"{straight_km(a['origins']['Homer City'], (h.lat[0], h.lon[0])):.1f} km in a straight line."]
    return "\n".join(L)


def figure(a: dict, path) -> None:
    import matplotlib.pyplot as plt

    from .figures import GRID, INK, INK2, MUTED, SERIES, SURFACE, _style

    e = a["enroll"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=150, facecolor=SURFACE, gridspec_kw={"width_ratios": [3, 2], "wspace": 0.35})
    for ax in (a1, a2):
        _style(ax)
    for i, name in enumerate(DISTRICTS.values()):
        g = e[e.district == name].sort_values("year")
        x = [int(y[:4]) for y in g.year]
        a1.plot(x, g.total, color=SERIES[i], lw=2)
        a1.annotate(f"{name}, {g.total.iloc[-1]:,.0f}", (x[-1], g.total.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                    fontsize=7.5, color=INK, va="center")
        a1.plot([x[-1] + 1], [g.total.iloc[-1] + a["kids"][name]], marker="o", ms=5, color=SERIES[i])
        a1.annotate(f"+{a['kids'][name]:,.0f} newcomers' children", (x[-1] + 1, g.total.iloc[-1] + a["kids"][name]), xytext=(4, 6),
                    textcoords="offset points", fontsize=7, color=INK2)
    a1.set_ylim(0, 1800)
    a1.set_xlim(2013.5, 2029.5)
    a1.grid(axis="y", color=GRID, lw=0.6)
    a1.set_title("Pupils, October 1 (PDE)", loc="left", fontsize=10, color=INK)
    a1.tick_params(colors=INK2, labelsize=7.5)
    m = a["money"]
    names = list(m)
    y = np.arange(len(names))
    a2.barh(y + 0.18, [m[n]["revenue"] / 1e6 for n in names], height=0.34, color=MUTED, label="whole budget, 2023-24")
    a2.barh(y - 0.18, [m[n]["campus_tax"] / 1e6 for n in names], height=0.34, color=SERIES[0], label="the campus's school tax")
    for i, n in enumerate(names):
        a2.annotate(f"${m[n]['revenue'] / 1e6:,.1f}M", (m[n]["revenue"] / 1e6, i + 0.18), xytext=(3, 0), textcoords="offset points",
                    fontsize=7, color=INK2, va="center")
        a2.annotate(f"${m[n]['campus_tax'] / 1e6:,.1f}M", (m[n]["campus_tax"] / 1e6, i - 0.18), xytext=(3, 0), textcoords="offset points",
                    fontsize=7, color=INK2, va="center")
    a2.set_yticks(y, names, fontsize=8, color=INK)
    a2.set_xlim(0, 48)
    a2.set_xlabel("million USD a year", color=INK2, fontsize=8)
    a2.legend(loc="upper left", bbox_to_anchor=(0, -0.2), fontsize=7, frameon=False, ncol=2)
    a2.set_title("The campus's school tax against each budget", loc="left", fontsize=10, color=INK)
    a2.tick_params(colors=INK2, labelsize=7.5)
    fig.text(0.01, -0.13, "PDE enrolment and Annual Financial Report data; the campus's tax at today's millage (pass 4, D26); "
             "newcomers' children from D18's homes.", fontsize=6.5, color=MUTED)
    fig.savefig(path, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
