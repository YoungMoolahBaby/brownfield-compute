"""Pass 2g: the air. The gas plant's permitted emissions against what the coal plant actually emitted,
what DEP's modelling puts at the worst point off the site, and what each data center design adds.

- **The coal plant as it ran:** EIA's "Emissions by plant" files (CO2, SO2 and NOx for every US plant,
  2013-2023). `coal_history(refresh=True)` downloads them to data/raw/air/ and writes plant 3122's
  yearly totals to data/eia_emissions_3122.csv. The files repeat plant-level columns on each of a
  plant's rows, so only the "Selected" columns (apportioned to the rows) are summed.
- **The gas plant as permitted:** Plan Approval 32-00457A's facility-wide caps (short tons a year,
  12-month rolling, startups included). A cap over a year at full output is the permitted rate per
  MWh: rate = cap / (MW x 8,760 h).
- **What reaches the ground:** DEP's summaries of the air quality and inhalation risk modelling
  (params/air.yaml). Only PM10 and PM2.5 were modelled against the standards: NOx and CO "netted out"
  against the coal plant's retirement, so no NO2 or ozone modelling was required.
- **The data centers:** each design's energy (pass 2's modules at the scorecard's campus load, IT x
  PUE) at the gas plant's permitted rates, and the diesel tests of the designs that keep generators
  (scorecard.backup), at EPA Tier 2 and Tier 4.

Tons here are US short tons (2,000 lb), as in DEP's permit.
"""

from __future__ import annotations

import pandas as pd

from . import DATA_DIR, RAW_DIR

PLANT = 3122
YEARS = range(2013, 2024)
HOURS = 8760
COAL_CSV = DATA_DIR / "eia_emissions_3122.csv"
EIA = "https://www.eia.gov/electricity/data/emissions/archive/xls/"
POLLUTANTS = ("so2", "nox", "co2")
SELECTED = {"so2": "Selected SO2 Emissions (Tons)", "nox": "Selected NOx Emissions (Tons)", "co2": "Tons of CO2 Emissions"}
SHEET = {"so2": "SO2", "nox": "NOx", "co2": "CO2"}
NAMES = {"old": "the old design (chillers and towers)", "cloud": "the cloud halls (outside air and pads)",
         "ai": "the AI halls (liquid and towers)", "gn": "the good neighbour (dry coolers, batteries)"}


# --- The coal plant as it ran -------------------------------------------------------------------

def plant_totals(sheets: dict[str, pd.DataFrame]) -> dict:
    """One plant's year from EIA's three sheets (its rows only): generation (MWh) and tons of SO2, NOx
    and CO2. Sums the per-row "Selected" columns; the plant-level columns repeat on each row."""
    return {"gen_mwh": float(pd.to_numeric(sheets["CO2"]["Generation (kWh)"]).sum()) / 1000,
            **{k: float(pd.to_numeric(sheets[SHEET[k]][c]).sum()) for k, c in SELECTED.items()}}


def coal_history(refresh: bool = False) -> pd.DataFrame:
    """Homer City Generating Station (EIA 3122), by year: generation (MWh) and tons of SO2, NOx, CO2."""
    if COAL_CSV.exists() and not refresh:
        return pd.read_csv(COAL_CSV, comment="#")
    import warnings

    import requests

    raw = RAW_DIR / "air"
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for y in YEARS:
        path = raw / f"emissions{y}.xlsx"
        if not path.exists():
            r = requests.get(f"{EIA}emissions{y}.xlsx", headers={"User-Agent": "brownfield-compute (public research)"}, timeout=300)
            r.raise_for_status()
            path.write_bytes(r.content)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            x = pd.ExcelFile(path, engine="openpyxl")
            sheets = {}
            for s in ("CO2", "SO2", "NOx"):
                d = pd.read_excel(x, s, header=1)
                d.columns = [str(c).replace("\n", " ").strip() for c in d.columns]
                sheets[s] = d[d["Plant Code"] == PLANT]
        rows.append({"year": y, **plant_totals(sheets)})
    a = pd.DataFrame(rows)
    head = ("# Homer City Generating Station (EIA plant 3122), by year, from EIA's 'Emissions by plant' files\n"
            "# (https://www.eia.gov/electricity/data/emissions/, emissions2013-2023.xlsx): gen_mwh is generation;\n"
            "# so2 and nox are the 'Selected' emissions (CEMS where reported), co2 'Tons of CO2 Emissions'; US short tons.\n")
    COAL_CSV.write_text(head + a.round(1).to_csv(index=False), encoding="utf-8", newline="")
    return a


# --- The gas plant as permitted -----------------------------------------------------------------

def gas(p: dict) -> dict:
    """The facility-wide caps (tons a year) and the permitted rates at full output (lb a MWh; CO2e in
    tons a MWh)."""
    g = "air.gas."
    mwh = p[g + "full_mw"] * HOURS
    caps = {k: p[f"{g}{k}_tpy"] for k in ("nox", "sox", "pm25", "co", "voc", "co2e", "haps")}
    return {"mwh": mwh, "caps": caps, "lb_mwh": {k: v * 2000 / mwh for k, v in caps.items()}}


# --- What each data center design adds ------------------------------------------------------------

def designs(temp, rh, p: dict) -> dict:
    """Each design at the campus load: energy a year (MWh, IT x PUE), its share of the gas plant's
    full output, the plant's emissions at the permitted rates for that share (tons), and the diesel
    tests (tons of NOx at Tier 2 and Tier 4, tons of PM)."""
    from . import scorecard

    gp = gas(p)
    n = p["scorecard.campus_it_mw"] / p["pass2.module.it_mw"]
    d = scorecard.modules(temp, rh, p)["d"]
    st = p["air.units.short_ton_t"]
    out = {}
    for k in ("old", "cloud", "ai", "gn"):
        mwh = d[k].it_mwh * d[k].pue * n
        share = mwh / gp["mwh"]
        bk = scorecard.backup("good neighbour" if k == "gn" else "conventional", p)
        b = "pass2.backup."
        test_mwh = bk["gensets"] * n * p[b + "gen_mw"] * p[b + "test_load"] * p[b + "test_hours"]
        out[k] = {"name": NAMES[k], "pue": d[k].pue, "mwh": mwh, "share": share,
                  **{k2: share * v for k2, v in gp["caps"].items()},
                  "gensets": bk["gensets"] * n, "test_mwh": test_mwh,
                  "diesel_nox_t2": test_mwh * p[b + "nox_g_kwh"] / 1000 / st,
                  "diesel_nox_t4": test_mwh * p["air.diesel.tier4_nox_g_kwh"] / 1000 / st,
                  "diesel_pm_t2": test_mwh * p["air.diesel.tier2_pm_g_kwh"] / 1000 / st,
                  "diesel_pm_t4": test_mwh * p["air.diesel.tier4_pm_g_kwh"] / 1000 / st}
    return out


# --- Checks and analysis --------------------------------------------------------------------------

def checks(coal: pd.DataFrame, p: dict) -> dict:
    """EIA's SO2 for 2021-2022 against the coal plant's CEMS baseline in the gas plant's application."""
    c = coal.set_index("year")
    so2 = c.loc[[2021, 2022], "so2"].mean()
    return {"so2_2122": so2, "so2_app": p["air.baseline.so2_tpy"], "ratio": so2 / p["air.baseline.so2_tpy"],
            "nox_2122": c.loc[[2021, 2022], "nox"].mean(), "nox_credited": p["air.baseline.nox_tpy"]}


def analyse(temp, rh, params: dict) -> dict:
    from .params import values

    p = values(params)
    coal = coal_history()
    return {"p": p, "coal": coal, "gas": gas(p), "designs": designs(temp, rh, p), "checks": checks(coal, p)}


# --- Report and figure ------------------------------------------------------------------------------

def _change(new, old):
    x = new / old - 1
    if x >= 9.5:
        return f"{new / old:.0f}x"
    return f"{x:+.{2 if x < -0.995 else 1 if x < -0.95 else 0}%}"


def report(a: dict) -> str:
    p, gp, k = a["p"], a["gas"], a["checks"]
    c = a["coal"].set_index("year")
    c = c[c.gen_mwh > 0]
    lb = lambda t, mwh: t * 2000 / mwh  # noqa: E731
    L = ["**1. The coal plant as it ran** (EIA, plant 3122; tons a year, and lb a MWh)", "",
         "| Year | Generation, TWh | SO2, tons | NOx, tons | CO2, million tons | SO2, lb/MWh | NOx, lb/MWh | CO2, lb/MWh |",
         "|---|---|---|---|---|---|---|---|"]
    L += [f"| {y} | {r.gen_mwh / 1e6:.2f} | {r.so2:,.0f} | {r.nox:,.0f} | {r.co2 / 1e6:.2f} | {lb(r.so2, r.gen_mwh):.2f} | "
          f"{lb(r.nox, r.gen_mwh):.2f} | {lb(r.co2, r.gen_mwh):,.0f} |" for y, r in c.iterrows()]
    busy = int(c.gen_mwh.idxmax())
    b = c.loc[busy]
    base = c.loc[[2021, 2022]].mean()
    cap = gp["caps"]
    L += ["", f"**2. The gas plant as permitted** ({p['air.gas.full_mw']:,.0f} MW; caps in tons a year; rates at full output all year, "
          f"{gp['mwh'] / 1e6:.1f} TWh)", "",
          f"| Pollutant | Gas plant's cap | Its rate, lb/MWh | Coal plant {busy} | Coal plant 2021-22 | Cap against {busy} | "
          f"Rate against {busy} |", "|---|---|---|---|---|---|---|"]
    for key, name, coal_key in (("sox", "SO2", "so2"), ("nox", "NOx", "nox"), ("co2e", "CO2 (CO2e for the gas plant)", "co2")):
        L.append(f"| {name} | {cap[key]:,.0f} | {gp['lb_mwh'][key]:,.3g} | {b[coal_key]:,.0f} | {base[coal_key]:,.0f} | "
                 f"{_change(cap[key], b[coal_key])} | {_change(gp['lb_mwh'][key], lb(b[coal_key], b.gen_mwh))} |")
    L.append(f"| PM2.5 | {cap['pm25']:,.0f} | {gp['lb_mwh']['pm25']:.3f} | (not in EIA) | {p['air.baseline.pm25_tpy']:,.0f} "
             "(application) | | |")
    L += ["", f"CO {cap['co']:,.0f}, VOC {cap['voc']:,.0f} and hazardous air pollutants {cap['haps']:,.1f} tons a year are also capped."]
    m = "air.modelled."
    rows = (("PM2.5, annual", "pm25_annual"), ("PM2.5, 24-hour", "pm25_24h"), ("PM10, 24-hour", "pm10_24h"))
    L += ["", "**3. What reaches the ground** (DEP's review of the modelling: the worst point off the site, ug/m3)", "",
          "| | The plant | Background (monitored) | Total | Standard | Total, share of the standard |", "|---|---|---|---|---|---|"]
    for name, key in rows:
        pl, bg, std = p[f"{m}{key}_ugm3"], p[f"{m}{key}_background_ugm3"], p[f"{m}{key}_naaqs_ugm3"]
        L.append(f"| {name} | {pl:.2f} | {bg:g} | {pl + bg:.2f} | {std:g} | {(pl + bg) / std:.0%} |")
    r = "air.risk."
    L += ["", f"Risk (DEP's review of the inhalation risk assessment): lifetime cancer risk {p[r + 'cancer_mei']:g} in a million at the "
          f"most exposed point and {p[r + 'cancer_homes']:g} at the most exposed home or school, against DEP's benchmark of "
          f"{p[r + 'cancer_benchmark']:g}; chronic hazard index {p[r + 'chronic_hi_mei']:g} against {p[r + 'chronic_benchmark']:g}; the "
          f"highest short-term hazard {p[r + 'acute_hq_max']:.2f} of its limit (cadmium). No NO2 or ozone was modelled: NOx netted out."]
    ds = a["designs"]
    gn = ds["gn"]
    L += ["", f"**4. What each data center design adds** (the campus at {p['scorecard.campus_it_mw']:,.0f} MW of IT; the gas plant's "
          "emissions at its permitted rates for the energy each design draws; diesel tests at "
          f"{p['pass2.backup.test_hours']:g} h a year)", "",
          "| Design | PUE | Energy, TWh a year | Share of the plant's full output | NOx from the gas plant, tons | PM2.5 from the gas plant, tons | "
          "CO2e, million tons | Diesel generators | Their NOx, Tier 2 / Tier 4, tons | Diesel NOx against the gas plant's |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for key in ("old", "cloud", "ai", "gn"):
        x = ds[key]
        dn = "0" if x["gensets"] == 0 else f"{x['diesel_nox_t2']:,.0f} / {x['diesel_nox_t4']:,.0f}"
        vs = "-" if x["gensets"] == 0 else f"+{x['diesel_nox_t2'] / x['nox']:.0%} / +{x['diesel_nox_t4'] / x['nox']:.0%}"
        L.append(f"| {x['name']} | {x['pue']:.3f} | {x['mwh'] / 1e6:.1f} | {x['share']:.0%} | {x['nox']:,.0f} | {x['pm25']:,.0f} | "
                 f"{x['co2e'] / 1e6:.1f} | {x['gensets']:,.0f} | {dn} | {vs} |")
    old = ds["old"]
    L += ["", f"Against the old design, the good neighbour's lower PUE saves {old['nox'] - gn['nox']:,.0f} tons of NOx, "
          f"{old['pm25'] - gn['pm25']:,.0f} of PM2.5 and {(old['co2e'] - gn['co2e']) / 1e6:.1f} million of CO2e a year at the gas plant; "
          f"dropping diesel saves {old['diesel_nox_t2']:,.0f} tons of NOx (Tier 2) or {old['diesel_nox_t4']:,.0f} (Tier 4). Tier 2 caps NOx "
          "and hydrocarbons together, so its figure is an upper bound for NOx; the gas plant's are its permitted rates, also upper bounds."]
    L += ["", "**Checks**", "",
          f"- **The coal plant's SO2, 2021-22:** EIA gives {k['so2_2122']:,.1f} tons a year against the application's CEMS baseline of "
          f"{k['so2_app']:,.1f} ({k['so2_2122'] - k['so2_app']:+.1f}).",
          f"- **Its NOx, 2021-22:** EIA gives {k['nox_2122']:,.0f} tons a year. The netting credits {k['nox_credited']:,.0f}, discounted to what "
          "the coal plant could have emitted under the federal NOx rules (application, Table 3-9)."]
    return "\n".join(L)


def figure(a: dict, path) -> None:
    import matplotlib.pyplot as plt

    from .figures import GRID, INK, INK2, MUTED, SERIES, SURFACE, _style

    from matplotlib.ticker import FuncFormatter, NullFormatter

    p, cap = a["p"], a["gas"]["caps"]
    c = a["coal"]
    c = c[c.gen_mwh > 0]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.4), dpi=150, facecolor=SURFACE, gridspec_kw={"hspace": 0.42, "wspace": 0.28})
    panels = (("so2", "sox", "SO2, tons a year (log scale)", (50, 3e5)), ("nox", "nox", "NOx, tons a year (log scale)", (300, 4e4)),
              ("co2", "co2e", "CO2, million tons a year", None))
    box = {"fc": SURFACE, "ec": "none", "pad": 1.5}
    for ax, (ck, gk, title, lim) in zip(axes.flat, panels):
        _style(ax)
        scale = 1 if lim else 1e6
        bottom = lim[0] if lim else 0
        ax.bar(c.year, c[ck] / scale - bottom, bottom=bottom, width=0.7, color=SERIES[1])
        ax.axhline(cap[gk] / scale, color=SERIES[0], lw=2)
        ax.annotate(f"the gas plant's cap, {cap[gk] / scale:,.{0 if lim else 1}f}", (c.year.max() + 0.45, cap[gk] / scale), xytext=(0, 4),
                    textcoords="offset points", fontsize=7.5, color=INK, ha="right", va="bottom", bbox=box)
        if lim:
            ax.set_yscale("log")
            ax.set_ylim(*lim)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.yaxis.set_minor_formatter(NullFormatter())
        ax.set_xlim(c.year.min() - 0.6, c.year.max() + 0.6)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(colors=INK2, labelsize=7.5)
    axes.flat[0].annotate("the coal plant as it ran (EIA)", (c.year.min() - 0.35, c.so2.iloc[0]), xytext=(0, 4), textcoords="offset points",
                          fontsize=7.5, color=INK, va="bottom", bbox=box)
    ax = axes.flat[3]
    _style(ax)
    m = "air.modelled."
    bg, pl, std = p[m + "pm25_annual_background_ugm3"], p[m + "pm25_annual_ugm3"], p[m + "pm25_annual_naaqs_ugm3"]
    ax.barh([0], [bg], height=0.36, color=MUTED)
    ax.barh([0], [pl], left=[bg + 0.04], height=0.36, color=SERIES[0])
    ax.annotate(f"background (monitored), {bg:g}", (bg / 2, 0), fontsize=7.5, color=SURFACE, ha="center", va="center")
    ax.annotate(f"the gas plant at its worst point, +{pl:.2f}", (bg + 0.04 + pl, 0.18), xytext=(0, 6), textcoords="offset points",
                fontsize=7.5, color=INK, ha="right", va="bottom")
    ax.axvline(std, color=INK, lw=1.5)
    ax.annotate(f"standard, {std:g}", (std, -0.18), xytext=(-4, 0), textcoords="offset points", fontsize=7.5, color=INK, ha="right", va="top")
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 0.6)
    ax.set_yticks([])
    ax.set_xlabel("annual PM2.5, ug/m3", color=INK2, fontsize=8)
    ax.tick_params(colors=INK2, labelsize=7.5)
    ax.set_title("Fine particles at the worst point off the site", loc="left", fontsize=10, color=INK)
    fig.text(0.01, 0.0, "EIA emissions by plant (3122), 2013-2023; Plan Approval 32-00457A facility caps (short tons); DEP's PSD modelling "
             "summary, Table 10 (2025-11-17).", fontsize=6.5, color=MUTED)
    fig.savefig(path, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
