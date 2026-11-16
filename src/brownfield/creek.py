"""Pass 2e: what the campus's permitted discharge does to the creek's temperature.

The gas plant's cooling towers would send their blowdown to the creek (NPDES PA0005037, Outfall
027). This checks, from public numbers, how warm the creek gets once it is mixed, against
Pennsylvania's temperature criteria for the stream's designated use (25 Pa. Code 93.7), over the
gauged record and at the design low flow.

- Flows and water temperatures: USGS daily values (the Water Data OGC API), cached in .cache/.
- Design low flow Q7-10: the annual (climatic year, April-March) lowest 7-day mean flow, fitted by
  log-Pearson type III (method of moments on log10 flows, Wilson-Hilferty frequency factor), the
  10-year non-exceedance value; checked against USGS's published statistics.
- Mixing: fully mixed and steady, heat conserved (water's heat capacity taken as constant):

      T_mix = (Q_s T_s + Q_d T_d) / (Q_s + Q_d)

  with the stream's flow Q_s at the outfall scaled from a gauge by drainage area and reduced by any
  withdrawal upstream. Full mixing is the far-field answer; next to the outfall, before mixing,
  the plume is warmer (not modelled).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .http import fetch_json

DAILY = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items"
CFS_PER_MGD = 1.0 / 0.646317  # 1 MGD = 1.5472 cfs
STATS = {"00001": "max", "00002": "min", "00003": "mean"}


def f_to_c(f):
    return (np.asarray(f, dtype=float) - 32.0) * 5.0 / 9.0


def c_to_f(c):
    return np.asarray(c, dtype=float) * 9.0 / 5.0 + 32.0


def usgs_daily(site: str, param: str, start: str, end: str, approved_only: bool = True) -> pd.DataFrame:
    """Daily values of `param` (00060 discharge cfs, 00010 water temperature C) at a USGS site, one
    column per statistic (mean, max, min), indexed by date; approved values only unless asked
    (recent data are provisional and may be revised). Cached per page."""
    url = DAILY
    params = {"f": "json", "monitoring_location_id": f"USGS-{site}", "parameter_code": param,
              "time": f"{start}/{end}", "limit": 10000}
    rows = []
    while url:
        page = fetch_json(url, params, ttl_days=180)
        for feat in page.get("features", []):
            pr = feat["properties"]
            if pr.get("value") in (None, "") or (approved_only and pr.get("approval_status") != "Approved"):
                continue
            rows.append((pr["time"], STATS.get(pr.get("statistic_id"), pr.get("statistic_id")), float(pr["value"])))
        url = next((ln["href"] for ln in page.get("links", []) if ln.get("rel") == "next"), None)
        params = None  # the next link carries its own query
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["date", "stat", "value"])
    df["date"] = pd.to_datetime(df["date"])
    return df.pivot_table(index="date", columns="stat", values="value", aggfunc="mean").sort_index()


def annual_7day_min(q: pd.Series, min_days: int = 330) -> pd.Series:
    """Lowest 7-day mean flow in each climatic year (April 1 to March 31, named by its start),
    years with fewer than `min_days` days of record left out."""
    q = q.asfreq("D")
    q7 = q.rolling(7, min_periods=7).mean()
    year = q7.index.year - (q7.index.month < 4)
    counts = q.groupby(q.index.year - (q.index.month < 4)).count()
    lows = q7.groupby(year).min()
    return lows[counts.reindex(lows.index).fillna(0) >= min_days].dropna()


def lp3_quantile(x: np.ndarray, p: float) -> float:
    """The non-exceedance probability `p` quantile of log-Pearson type III fitted to x by moments
    of log10 x (Wilson-Hilferty frequency factor)."""
    from statistics import NormalDist

    y = np.log10(np.asarray(x, dtype=float))
    n = len(y)
    m, s = y.mean(), y.std(ddof=1)
    g = n * np.sum((y - m) ** 3) / ((n - 1) * (n - 2) * s ** 3)  # sample skew, bias-adjusted
    z = NormalDist().inv_cdf(p)
    k = z if abs(g) < 1e-6 else (2.0 / g) * ((1.0 + g * z / 6.0 - g * g / 36.0) ** 3 - 1.0)
    return float(10 ** (m + k * s))


def q7_10(q: pd.Series) -> float:
    lows = annual_7day_min(q)
    lows = lows[lows > 0]
    return lp3_quantile(lows.values, 0.1)


def mixed_temp(q_s, t_s, q_d, t_d):
    """Fully mixed temperature (same units as t_s, t_d) of stream flow q_s at t_s and discharge q_d
    at t_d (any one flow unit)."""
    q_s, q_d = np.asarray(q_s, dtype=float), np.asarray(q_d, dtype=float)
    return (q_s * np.asarray(t_s, dtype=float) + q_d * np.asarray(t_d, dtype=float)) / (q_s + q_d)


def heat_mbtu_day(q_d_mgd: float, t_d_f, t_s_f) -> np.ndarray:
    """Heat a discharge carries above the stream's temperature, million BTU a day (8.34 lb a
    gallon, 1 BTU per lb per F)."""
    return q_d_mgd * 1e6 * 8.34 * (np.asarray(t_d_f, dtype=float) - np.asarray(t_s_f, dtype=float)) / 1e6


# ---------------------------------------------------------------------------------------------
# DEP's Thermal Limits Spreadsheet (v1.0, April 2024), Case 2: an intake from outside the
# receiving stream, so temperature limits rather than heat limits. Its formulas, read from the
# workbook (MGD in, cfs at 1.547 a MGD):
#   F = max(0, D + C - E)                       discharge (D external intake, C stream intake, E consumed)
#   J = Q7-10 x multiplier                      the period's design stream flow
#   K = max(0, (J - 1.547 C) PMF)               stream flow the discharge mixes with
#   L = max(0, min(J + 1.547 (D - E), K + 1.547 F))   flow below the outfall
#   T = max(criterion, ambient + 1)             the target
#   limit = min(110, (L T - K ambient) / (1.547 F))

SPREADSHEET_CFS_PER_MGD = 1.547
SITES = {"blacklick": "03042000", "graceton": "03042500"}


def tls_table() -> pd.DataFrame:
    from . import DATA_DIR

    return pd.read_csv(DATA_DIR / "tls_tables.csv", comment="#")


def tls_limits(q710: float, ambient, criteria, multipliers, intake_ext: float, consumptive: float,
               intake_stream: float = 0.0, pmf: float = 1.0, cap: float = 110.0) -> pd.DataFrame:
    k_ = SPREADSHEET_CFS_PER_MGD
    a, c, m = (np.asarray(x, dtype=float) for x in (ambient, criteria, multipliers))
    f = max(0.0, intake_ext + intake_stream - consumptive)
    j = q710 * m
    k = np.maximum(0.0, (j - k_ * intake_stream) * pmf)
    lo = np.maximum(0.0, np.minimum(j + k_ * intake_ext - k_ * consumptive, k + k_ * f))
    t = np.maximum(c, a + 1.0)
    raw = (lo * t - k * a) / (k_ * f)
    return pd.DataFrame({"J": j, "K": k, "L": lo, "target": t, "raw": raw, "limit": np.minimum(cap, raw)})


def dep_limits(p: dict, ambient=None, q710: float | None = None) -> pd.DataFrame:
    """DEP's run as printed (TSF defaults, Q7-10 34 cfs), or with another ambient or Q7-10."""
    tb = tls_table()
    c = "creek.permit."
    out = tls_limits(p[c + "q710_cfs"] if q710 is None else q710, tb["amb_tsf"] if ambient is None else ambient,
                     tb["tsf"], tb["multiplier"], p[c + "intake_mgd"], p[c + "consumptive_mgd"], pmf=p[c + "pmf"],
                     cap=p["creek.effluent.cap_f"])
    out.insert(0, "period", tb["period"])
    return out


def period_index(dates: pd.DatetimeIndex) -> np.ndarray:
    """Which of the 19 periods (0-18) each date falls in."""
    tb = tls_table()
    md = dates.month * 100 + dates.day
    idx = np.full(len(dates), -1)
    for i, r in tb.iterrows():
        lo, hi = r.start_month * 100 + r.start_day, r.end_month * 100 + r.end_day
        idx[(md >= lo) & (md <= max(hi, lo))] = i
    idx[(dates.month == 2) & (dates.day == 29)] = 1
    return idx


def site_ambient(t_mean_c: pd.Series) -> pd.DataFrame:
    """Median (and 90th percentile) of the daily mean water temperature (F) in each period."""
    s = pd.Series(c_to_f(t_mean_c.values), index=t_mean_c.index).dropna()
    idx = period_index(s.index)
    g = s.groupby(idx)
    return pd.DataFrame({"median": g.median(), "p90": g.quantile(0.9), "days": g.count()}).reindex(range(19))


def record(start: str = "2013-10-01", end: str = "2026-10-31") -> pd.DataFrame:
    """Blacklick Creek at Josephine: daily mean flow (cfs) and daily mean and max water temperature
    (C), approved values on days with both."""
    q = usgs_daily(SITES["blacklick"], "00060", start, end)
    t = usgs_daily(SITES["blacklick"], "00010", start, end)
    df = pd.DataFrame({"q": q["mean"], "t_mean": t["mean"], "t_max": t["max"]}).dropna()
    return df


def daily_check(p: dict, df: pd.DataFrame, effluent_f, with_twolick: bool, temp: str = "t_mean") -> pd.DataFrame:
    """Day by day over the record: the creek fully mixed with the discharge at `effluent_f` (F; a
    number, or 19 values by period), against the target DEP's method sets for that day's own
    background: max(criterion, background + 1 F)."""
    c = "creek.permit."
    tb = tls_table()
    idx = period_index(df.index)
    q_s = df["q"].values * p[c + "blacklick_area_ratio"] + (p[c + "twolick_release_cfs"] if with_twolick else 0.0)
    q_d = p[c + "discharge_mgd"] * SPREADSHEET_CFS_PER_MGD
    t_s = c_to_f(df[temp].values)
    eff = np.asarray(effluent_f, dtype=float)
    t_d = eff[idx] if eff.ndim else np.full(len(df), float(eff))
    t_m = mixed_temp(q_s, t_s, q_d, t_d)
    crit = tb["tsf"].values[idx]
    return pd.DataFrame({"period": idx, "q_s": q_s, "t_s": t_s, "t_mix": t_m, "rise": t_m - t_s, "criterion": crit,
                         "over": t_m > np.maximum(crit, t_s + 1.0), "bg_over": t_s > crit}, index=df.index)


# ---------------------------------------------------------------------------------------------
# The report and the figure.

DEP_RUN = "DEP (defaults, 34 cfs)"


def analyse(p: dict) -> dict:
    tb = tls_table()
    df = record()
    amb = site_ambient(df["t_mean"])
    q_bl = q7_10(usgs_daily(SITES["blacklick"], "00060", "1950-01-01", "2026-10-31")["mean"])
    q_out = q_bl * p["creek.permit.blacklick_area_ratio"]
    runs = {DEP_RUN: dep_limits(p), "measured temperatures": dep_limits(p, ambient=amb["median"].values),
            "Blacklick's flow only": dep_limits(p, q710=q_out),
            "both": dep_limits(p, ambient=amb["median"].values, q710=q_out)}
    q_d = p["creek.permit.discharge_mgd"] * SPREADSHEET_CFS_PER_MGD
    hot = p["creek.effluent.max_daily_f"]
    step = q_d * (hot - tb["amb_tsf"].values) / runs[DEP_RUN]["L"].values
    checks = {}
    for label, eff in (("at DEP's limits", runs[DEP_RUN]["limit"].values), (f"at {hot:g} F", hot)):
        for tw in (True, False):
            checks[(label, tw)] = daily_check(p, df, eff, tw)
    return {"tb": tb, "df": df, "amb": amb, "q_bl": q_bl, "runs": runs, "step": step, "checks": checks}


def report(p: dict, a: dict) -> str:
    tb, runs, amb = a["tb"], a["runs"], a["amb"]
    hot = p["creek.effluent.max_daily_f"]
    lines = [f"**DEP's Outfall 027 temperature limits, reproduced and rerun** (instantaneous maximum, F; "
             f"the applicant projects {hot:g} F at most)", "",
             "| Period | Criterion (TSF) | DEP default creek temp | Measured median | " + " | ".join(runs) + " |",
             "|---|---|---|---|" + "---|" * len(runs)]
    for i, r in tb.iterrows():
        cells = []
        for v in runs.values():
            x = v["limit"].iloc[i]
            cells.append(f"**{x:.1f}**" if x < hot else f"{x:.1f}")
        lines.append(f"| {r.period} | {r.tsf} | {r.amb_tsf} | {amb['median'].iloc[i]:.1f} | " + " | ".join(cells) + " |")
    lines += ["", f"Bold: below the applicant's projected {hot:g} F. Measured: USGS 03042000 daily mean water temperature, "
              f"approved values {a['df'].index.min():%Y-%m-%d} to {a['df'].index.max():%Y-%m-%d} ({len(a['df']):,} days). "
              f"Blacklick's own Q7-10 from the gauge (log-Pearson III, climatic years 1952-2025): {a['q_bl']:.1f} cfs, "
              f"against DEP's 34 (23 + 11 from Two Lick Creek)."]
    lines += ["", f"**Switching on at once** (the discharge at {hot:g} F, DEP's design flow and default creek temperature): "
              "the creek rises " + ", ".join(f"{tb.period[i]} {a['step'][i]:.1f}" for i in range(19))
              + f" F; more than the 2 F an hour allowed in {(a['step'] > 2).sum()} of 19 periods."]
    lines += ["", "**Over the gauged record** (each day's own flow and temperature, fully mixed; 'over' = warmer than "
              "max(criterion, that day's creek + 1 F), the target DEP's method sets):", "",
              "| Discharge | Stream flow | Days over | July days over | Median rise | Largest rise |", "|---|---|---|---|---|---|"]
    for (label, tw), r in a["checks"].items():
        jul = r[r.period == 9]
        lines.append(f"| {label} | {'Blacklick + 11 cfs (DEP)' if tw else 'Blacklick only'} | {int(r.over.sum()):,} of {len(r):,} "
                     f"({r.over.mean():.0%}) | {int(jul.over.sum())} of {len(jul)} ({jul.over.mean():.0%}) | "
                     f"{r.rise.median():.1f} F | {r.rise.max():.1f} F |")
    bg = next(iter(a["checks"].values()))
    lines += ["", f"With no discharge at all the creek is above its criterion on {int(bg.bg_over.sum()):,} days "
              f"({bg.bg_over.mean():.0%}), {int(bg[bg.period == 9].bg_over.sum())} of {int((bg.period == 9).sum())} July days."]
    return "\n".join(lines)


def figure(p: dict, a: dict, path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .figures import GRID, INK, INK2, MUTED, SURFACE, _style

    tb, amb, runs = a["tb"], a["amb"], a["runs"]
    x = np.arange(19)
    labels = ["Jan", "Feb", "Mar", "Apr", "", "May", "", "Jun", "", "Jul", "Aug", "", "Sep", "", "Oct", "", "Nov", "", "Dec"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.4), dpi=150, facecolor=SURFACE)
    for ax in (ax1, ax2):
        _style(ax)
        ax.grid(True, axis="y", color=GRID, linewidth=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.5)
    ax1.step(x, tb["tsf"], where="mid", color=INK2, linewidth=1.1, linestyle=(0, (4, 3)), label="criterion (trout stocking)")
    ax1.plot(x, tb["amb_tsf"], color="#eb6834", linewidth=1.6, marker="o", markersize=3, label="DEP's default creek temperature")
    ax1.plot(x, amb["median"], color="#2a78d6", linewidth=1.6, marker="o", markersize=3, label="measured median (USGS, 2013-2024)")
    ax1.set_ylabel("creek temperature, F", color=INK2, fontsize=8.5)
    ax1.set_title("The creek before any discharge", fontsize=9, color=INK, loc="left")
    ax1.legend(loc="upper left", frameon=False, fontsize=7.5, labelcolor=INK2)
    hot = p["creek.effluent.max_daily_f"]
    ax2.plot(x, runs[DEP_RUN]["limit"], color="#2a78d6", linewidth=1.6, marker="o", markersize=3,
             label="DEP's limits (default temperatures, 34 cfs)")
    ax2.plot(x, runs["both"]["limit"], color="#eb6834", linewidth=1.6, marker="o", markersize=3,
             label="rerun: measured temperatures, Blacklick's flow")
    ax2.axhline(hot, color=INK2, linewidth=0.9, linestyle=(0, (4, 3)))
    ax2.text(4.5, hot + 1.0, f"applicant's projection, {hot:g} F", fontsize=7, color=INK2, ha="center")
    ax2.set_ylim(55, 115)
    ax2.set_ylabel("most the discharge may be, F", color=INK2, fontsize=8.5)
    ax2.set_title("Outfall 027's temperature limit", fontsize=9, color=INK, loc="left")
    ax2.legend(loc="lower left", frameon=False, fontsize=7.5, labelcolor=INK2)
    fig.suptitle("Blacklick Creek at Homer City: 6.84 million gallons a day of cooling tower blowdown (NPDES PA0005037 A-2)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.text(0.01, 0.01, "Limits by DEP's Thermal Limits Spreadsheet (reproduced to 0.1 F); 110 F is its ceiling. "
             "Semi-monthly periods, 25 Pa. Code 93.7.", fontsize=6.8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
