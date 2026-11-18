"""Pass 2f: the campus's water budget, from Two Lick Reservoir through the plant to the creeks.

HCR says the campus's water use stays "in line with the historical usage levels of the former coal
plant". This checks that against what the coal plant actually drew, and asks whether the reservoir
can carry the gas plant and the data centers through the droughts on record.

- **The coal plant as it ran:** EIA's thermoelectric cooling water data for plant 3122, monthly
  withdrawal and consumption, 2014-2023. `coal_history(refresh=True)` downloads EIA's yearly
  summary files to data/raw/water/ and writes the plant's rows to data/eia_cooling_3122.csv.
- **The gas plant:** what its own condensers evaporate at full output, by heat balance, with the
  towers' blowdown at their planned cycles of concentration n:

      Q_cond = (P / eta) (1 - eta - stack - other),   E = Q_cond f_evap / h_fg,   B = E / (n - 1)

  Against it, the station's water balance as filed with DEP (params/water.yaml `filed`, drawing
  D-352-1801): design maximums, with the intake's three pumps at 37.6 MGD and the data centers
  (the station's "tenant") on 1,400 gpm of makeup, 400 gpm of it returned.

- **The data centers:** pass 2's module models (scorecard.modules) at the scorecard's campus
  load, yearly averages.
- **Two Lick Creek's natural flow** at Graceton (USGS 03042500): as measured before the dam
  (regulation began in December 1968). After it, transferred from Blacklick Creek at Josephine
  (03042000, unregulated) by flow duration, month by month: the same exceedance probability in
  each month's flow-duration curve (QPPQ; Fennessey 1994, Archfield and Vogel 2010), fitted on
  the 1952-1968 overlap.
- **The reservoir:** a daily mass balance on its 74 mi2. It spills when full and loses evaporation
  from its surface. It releases at least R_min (a placeholder: what Indiana's water plant draws
  just below it), and more when the plant's draw D plus the consent order's 11 cfs P, kept over
  the low dam below the intake, exceeds the natural flow L of the 97 mi2 between the dam and the
  gauge:

      R = max(R_min, D + P - L),   S' = min(C, S + I - R - E)

  The intake sits below the gauge: the 316(b) report places it ~1 km downstream, and since 1969
  the gauge's mean flow is within ~1% of the reconstructed natural mean, consistent with that (a
  coal-plant-size withdrawal above it would be ~5-8% of the mean). Indiana's water plant draws just below
  the dam and returns most of it above the gauge through the borough's sewage plant: not counted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import DATA_DIR, RAW_DIR, creek
from .module import GAL, H_FG

AF_MG = 0.325851  # million US gallons in an acre-foot
MGD_PER_CFS = 0.646317
DAM = pd.Timestamp("1968-12-01")  # Two Lick Creek Reservoir regulates the gauge from here (USGS)
FIT = slice("1952-04-01", "1968-11-30")  # both gauges, before the dam
RECORD = slice("1952-04-01", "2025-03-31")  # climatic years 1952-2024
COAL_CSV = DATA_DIR / "eia_cooling_3122.csv"
EIA = "https://www.eia.gov/electricity/data/water/"
EIA_FILES = [f"archive/xls/cooling_summary_{y}.xlsx" for y in range(2014, 2021)] + \
    [f"archive/xls/Cooling_Boiler_Generator_Data_Summary_{y}.xlsx" for y in range(2021, 2024)]


# --- The coal plant as it ran -------------------------------------------------------------------

def coal_history(refresh: bool = False) -> pd.DataFrame:
    """Homer City Generating Station (EIA 3122), by month: net generation (MWh), water withdrawn and
    consumed (million gallons), steam capacity (MW)."""
    if COAL_CSV.exists() and not refresh:
        return pd.read_csv(COAL_CSV, comment="#")
    import warnings

    import requests

    raw = RAW_DIR / "water"
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in EIA_FILES:
        path = raw / f.rsplit("/", 1)[1]
        if not path.exists():
            r = requests.get(EIA + f, headers={"User-Agent": "brownfield-compute (public research)"}, timeout=300)
            r.raise_for_status()
            path.write_bytes(r.content)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            head = pd.read_excel(path, header=None, nrows=10, engine="openpyxl")
            hdr = next(i for i in range(10) if any("Plant" in str(v) for v in head.iloc[i].tolist()))
            df = pd.read_excel(path, header=hdr, engine="openpyxl")
        df.columns = [str(c).strip() for c in df.columns]
        rows.append(df[df["Plant Code"] == 3122])
    a = pd.concat(rows)
    cols = {"Year": "year", "Month": "month", "Summer Capacity of Steam Turbines (MW)": "mw",
            "Net Generation from Steam Turbines (MWh)": "net_mwh", "Water Withdrawal Volume (Million Gallons)": "withdrawn_mg",
            "Water Consumption Volume (Million Gallons)": "consumed_mg"}
    a = a[list(cols)].rename(columns=cols)
    a = a.apply(pd.to_numeric, errors="coerce").groupby(["year", "month"], as_index=False).agg(
        mw=("mw", "max"), net_mwh=("net_mwh", "sum"), withdrawn_mg=("withdrawn_mg", "sum"), consumed_mg=("consumed_mg", "sum"))
    head = ("# Homer City Generating Station (EIA plant 3122), by month, from EIA's thermoelectric cooling water data\n"
            "# (Water cooling by generator and boiler, summary files 2014-2023, https://www.eia.gov/electricity/data/water/).\n"
            "# mw: summer capacity of the steam turbines; net_mwh: their net generation; withdrawn_mg, consumed_mg: million US gallons.\n")
    COAL_CSV.write_text(head + a.to_csv(index=False), encoding="utf-8", newline="")
    return a


def coal_years(h: pd.DataFrame) -> pd.DataFrame:
    h = h.copy()
    h["days"] = pd.to_datetime(dict(year=h.year, month=h.month, day=1)).dt.days_in_month
    y = h.groupby("year").agg(mw=("mw", "max"), net=("net_mwh", "sum"), wd=("withdrawn_mg", "sum"), cons=("consumed_mg", "sum"),
                              days=("days", "sum"))
    y["share"] = y.net / (y.mw * 24 * y.days)
    y["drawn_mgd"], y["used_mgd"] = y.wd / y.days, y.cons / y.days
    y["gal_mwh"] = y.wd * 1e6 / y.net.where(y.net > 0)
    y["used_gal_mwh"] = y.cons * 1e6 / y.net.where(y.net > 0)
    return y


# --- Two Lick Creek's natural flow ---------------------------------------------------------------

def qppq_fit(target: pd.Series, source: pd.Series) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """Each calendar month's flow-duration curves (sorted log flows) of source and target over the days
    both were gauged."""
    both = pd.DataFrame({"t": target, "s": source}).dropna()
    both = both[(both.t > 0) & (both.s > 0)]
    return {m: (np.sort(np.log(g.s.values)), np.sort(np.log(g.t.values))) for m, g in both.groupby(both.index.month)}


def qppq(tab: dict, source: pd.Series) -> pd.Series:
    """The target's flow at the source's exceedance probability, month by month. Beyond the fitted
    range the log flows move one for one."""
    out = np.full(len(source), np.nan)
    month, v = source.index.month, source.values
    for m, (ls, lt) in tab.items():
        k = (month == m) & np.isfinite(v) & (v > 0)
        x = np.log(v[k])
        y = np.interp(np.interp(x, ls, np.linspace(0, 1, len(ls))), np.linspace(0, 1, len(lt)), lt)
        y = np.where(x < ls[0], lt[0] + x - ls[0], np.where(x > ls[-1], lt[-1] + x - ls[-1], y))
        out[k] = np.exp(y)
    return pd.Series(out, index=source.index)


def gauges() -> tuple[pd.Series, pd.Series]:
    g = creek.usgs_daily(creek.SITES["graceton"], "00060", "1951-09-01", "2025-09-30")["mean"].asfreq("D")
    b = creek.usgs_daily(creek.SITES["blacklick"], "00060", "1951-09-01", "2025-09-30")["mean"].asfreq("D")
    return g, b


def natural(g: pd.Series, b: pd.Series) -> pd.Series:
    """Two Lick Creek's natural daily flow at Graceton, cfs, over the record's climatic years: measured
    before the dam, transferred from Blacklick Creek after it (and for any day either is missing)."""
    t = qppq(qppq_fit(g[FIT], b[FIT]), b.interpolate(limit=10))
    n = t.copy()
    pre = (n.index < DAM) & g.reindex(n.index).notna().values
    n[pre] = g.reindex(n.index)[pre]
    return n[RECORD].interpolate(limit=10)


def checks(g: pd.Series, b: pd.Series, p: dict) -> dict:
    """The transfer on the record it can be checked against: in sample (1952-1968), split sample (fit
    to 1960, test after), and the gauge's mean since the dam; and what scaling by area would give."""
    t = qppq(qppq_fit(g[FIT], b[FIT]), b)
    cut = slice("1952-04-01", "1960-03-31"), slice("1960-04-01", "1968-11-30")
    t_cv = qppq(qppq_fit(g[cut[0]], b[cut[0]]), b)

    def low(s, days):
        r = s.asfreq("D").rolling(days, min_periods=days).mean()
        return r.groupby(r.index.year - (r.index.month < 4)).min().min()

    post = slice("1969-04-01", "2025-03-31")
    return {
        "q710_obs": creek.q7_10(g[FIT]), "q710_fit": creek.q7_10(t[FIT]),
        "q710_test_obs": creek.q7_10(g[cut[1]]), "q710_test": creek.q7_10(t_cv[cut[1]]),
        "low90_obs": low(g[FIT], 90), "low90_fit": low(t[FIT], 90),
        "low180_obs": low(g[FIT], 180), "low180_fit": low(t[FIT], 180),
        "mean_post_obs": g[post].mean(), "mean_post_nat": t[post].mean(),
        "q710_natural": creek.q7_10(natural(g, b)),
        "q710_area": creek.q7_10(b[FIT]) * p["water.gauges.graceton_mi2"] / p["water.gauges.blacklick_mi2"],
    }


# --- What each case draws -----------------------------------------------------------------------

def gas_condensers(p: dict) -> dict:
    """The gas plant's own condensers at its running output: heat to the towers, evaporation, and the
    draw with the towers' blowdown at their planned cycles of concentration (MGD)."""
    w = "water.gas."
    mw = p[w + "mw"] * p[w + "output_share"]
    q_mw = mw / p[w + "efficiency"] * (1.0 - p[w + "efficiency"] - p[w + "stack_loss_share"] - p[w + "other_loss_share"])
    evap = q_mw * 1e6 * p["pass2.conventional.evap_fraction"] / H_FG * 86400 / 1000 / GAL / 1e6
    blow = evap / (p[w + "cycles"] - 1.0)
    return {"mw": mw, "cond_mw": q_mw, "evap_mgd": evap, "blow_mgd": blow, "draw_mgd": evap + blow, "cycles": p[w + "cycles"]}


def filed(p: dict) -> dict:
    """The station's water balance as filed (drawing D-352-1801, design maximums, MGD), and what it
    implies at the towers' planned cycles of concentration."""
    f = "water.filed."
    mgd = {k[len(f):-4]: v * 1440 / 1e6 for k, v in p.items() if k.startswith(f) and k.endswith("_gpm")}
    split = mgd["screen_wash"] + mgd["tenant_makeup"] + mgd["towers_service"] + mgd["demin"]
    makeup = mgd["towers_service"] + mgd["tenant_return"]  # the towers' own makeup (HRSG blowdown left out)
    blow = makeup / p["water.gas.cycles"]
    evap = makeup - blow
    back = mgd["screen_wash"] + mgd["outfall_027"]
    tenant = mgd["tenant_makeup"] - mgd["tenant_return"]
    return {**mgd, "split": split, "makeup": makeup, "blow": blow, "evap": evap, "heat_mw": heat_for(evap, p),
            "returned": back + mgd["outfall_001"], "used": mgd["intake"] - back - mgd["outfall_001"],
            "used_july": mgd["intake"] - back - mgd["outfall_001_july"], "tenant_used": tenant, "tenant_heat_mw": heat_for(tenant, p)}


def heat_for(evap_mgd: float, p: dict) -> float:
    """MW of heat a wet tower rejects while evaporating `evap_mgd`."""
    return evap_mgd * 1e6 * GAL * 1000 / 86400 * H_FG / p["pass2.conventional.evap_fraction"] / 1e6


def cases(temp, rh, p: dict) -> list[dict]:
    """Each case's draw at the intake (a value per calendar month, MGD) and what it uses up."""
    from . import scorecard

    h = coal_history()
    y = coal_years(h)
    busy = int(y.drawn_mgd.idxmax())
    hm = h[h.year == busy].sort_values("month")
    days = pd.to_datetime(dict(year=hm.year, month=hm.month, day=1)).dt.days_in_month.values
    full_mw = y.loc[busy, "mw"]
    gc = gas_condensers(p)
    fb = filed(p)
    at = "full output" if p["water.gas.output_share"] >= 1 else f"{p['water.gas.output_share']:.0%} of full output"
    n = p["scorecard.campus_it_mw"] / p["pass2.module.it_mw"]
    d = scorecard.modules(temp, rh, p)["d"]
    mgd = lambda m3: m3 / GAL / 365 / 1e6 * n  # noqa: E731
    dc = {k: (mgd(d[k].withdrawn_m3), mgd(d[k].evaporated_m3)) for k in ("gn", "cloud", "ai", "old")}
    names = {"gn": "the good neighbour (dry coolers)", "cloud": "the cloud halls (outside air and pads)",
             "ai": "the AI halls (liquid and towers)", "old": "the old design (chillers and towers)"}
    flat = lambda x: np.full(12, x)  # noqa: E731
    out = [
        {"key": "coal_ran", "name": f"The coal plant as it ran in {busy}, its busiest recent year (EIA)",
         "draw": hm.withdrawn_mg.values / days, "used": hm.consumed_mg.sum() / days.sum(), "to": "Two Lick Creek"},
        {"key": "coal_full", "name": f"The coal plant at full output ({busy}'s gallons a MWh)",
         "draw": flat(y.loc[busy, "gal_mwh"] * full_mw * 24 / 1e6), "used": y.loc[busy, "used_gal_mwh"] * full_mw * 24 / 1e6,
         "to": "Two Lick Creek"},
        {"key": "coal_max", "name": "The coal plant's maximum intake rate (HCR's 14 gpm/MW)",
         "draw": flat(p["water.coal.max_gpm_per_mw"] * full_mw * 1440 / 1e6), "used": np.nan, "to": ""},
        {"key": "gas_max", "name": "The gas plant's maximum intake rate (HCR's 5.9 gpm/MW)",
         "draw": flat(p["water.gas.max_gpm_per_mw"] * p["water.gas.mw"] * 1440 / 1e6), "used": np.nan, "to": ""},
        {"key": "gas_own", "name": f"The gas plant's own condensers at {at} (heat balance)",
         "draw": flat(gc["draw_mgd"]), "used": gc["evap_mgd"], "to": "Blacklick Creek (Outfall 027)"},
        {"key": "filed", "name": "The station at its intake pumps' capacity, as filed (with the data centers' makeup)",
         "draw": flat(fb["intake"]), "used": fb["used"], "to": "both creeks (Outfalls 001, 002, 027)"},
        {"key": "gas_own+tenant", "name": "The gas plant's condensers, plus the data centers as filed (1,400 gpm in, 400 back)",
         "draw": flat(gc["draw_mgd"] + fb["tenant_used"]), "used": gc["evap_mgd"] + fb["tenant_used"], "to": "the creeks"},
    ]
    for k in ("gn", "cloud", "ai", "old"):
        out.append({"key": f"gas_own+{k}", "name": f"The gas plant's condensers, plus {names[k]}",
                    "draw": flat(gc["draw_mgd"] + dc[k][0]), "used": gc["evap_mgd"] + dc[k][1], "to": "the creeks"})
    for c in out:
        c["mean"] = float(np.average(c["draw"], weights=np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])))
    return out


# --- The reservoir ------------------------------------------------------------------------------

def evaporation(p: dict, index: pd.DatetimeIndex) -> np.ndarray:
    """MGD evaporated from the full reservoir's surface, by day."""
    r = "water.reservoir."
    year_mg = p[r + "evaporation_in_yr"] / 12.0 * p[r + "surface_acres"] * 43560 * 7.48052 / 1e6
    summer = (index.month >= 5) & (index.month <= 10)
    return np.where(summer, year_mg * p[r + "evaporation_may_oct_share"] / 184.0,
                    year_mg * (1 - p[r + "evaporation_may_oct_share"]) / 181.25)


def reservoir(p: dict, nat: pd.Series, draw: np.ndarray) -> dict:
    """Daily mass balance from full, with the plant's draw (MGD) given by calendar month (12 values) or
    by day. Returns storage, releases and shortfalls by day."""
    r = "water.reservoir."
    cap = p[r + "capacity_acft"] * AF_MG
    share = p[r + "drainage_mi2"] / p["water.gauges.graceton_mi2"]
    q = nat.values * MGD_PER_CFS
    inflow, local = q * share, q * (1 - share)
    evap = evaporation(p, nat.index).copy()  # what evaporates; capped below at what the pool holds
    draw = np.asarray(draw, dtype=float)
    draw = draw[nat.index.month - 1] if len(draw) == 12 else draw
    rmin = p[r + "min_release_cfs"] * MGD_PER_CFS
    pass_by = p[r + "pass_by_cfs"] * MGD_PER_CFS
    n = len(q)
    s_out, rel, short, spill = np.empty(n), np.empty(n), np.zeros(n), np.zeros(n)
    s = cap
    for t in range(n):
        need = max(rmin, draw[t] + pass_by - local[t])
        evap[t] = min(evap[t], s + inflow[t])
        avail = s + inflow[t] - evap[t]
        if avail >= need:
            rel[t] = need
            s = avail - need
            if s > cap:
                spill[t], s = s - cap, cap
        else:
            rel[t] = avail
            short[t] = need - rel[t]
            s = 0.0
        s_out[t] = s
    st = pd.Series(s_out / cap, index=nat.index)
    years = st.groupby(st.index.year - (st.index.month < 4)).min()
    since = st[st.index >= DAM]
    return {"storage": st, "release": rel, "short": short, "spill": spill, "inflow": inflow, "local": local, "evap": evap,
            "draw": draw, "cap_mg": cap, "lowest": float(st.min()), "when": st.idxmin(), "years_below_half": int((years < 0.5).sum()),
            "lowest_since_dam": float(since.min()) if len(since) else np.nan, "when_since_dam": since.idxmin() if len(since) else None,
            "short_days": int((short > 1e-9).sum()), "short_mg": float(short.sum()), "below_min_days": int((rel < rmin - 1e-9).sum()),
            "years": years}


def known_case(p: dict, nat: pd.Series) -> dict:
    """The reservoir with the coal plant's own monthly draws (EIA), over the months EIA reports, on that
    period's natural flows: it carried the plant then, so it must here."""
    h = coal_history()
    h = h[h.withdrawn_mg > 0]
    idx = nat["2014-01-01":"2023-06-30"].index
    m = pd.Series(h.withdrawn_mg.values / pd.to_datetime(dict(year=h.year, month=h.month, day=1)).dt.days_in_month.values,
                  index=pd.PeriodIndex([f"{a}-{b:02d}" for a, b in zip(h.year, h.month)], freq="M"))
    draw = m.reindex(idx.to_period("M")).fillna(0.0).values
    res = reservoir(p, nat[idx], draw)
    return {"lowest": res["lowest"], "when": res["when"], "short_days": res["short_days"]}


def analyse(temp, rh, params: dict) -> dict:
    from .params import values

    p = values(params)
    g, b = gauges()
    nat = natural(g, b)
    cs = cases(temp, rh, p)
    for c in cs:
        c["res"] = reservoir(p, nat, c["draw"])
    # Sensitivity on the cases that matter: a smaller usable pool, and 11 cfs kept at the reservoir's dam too.
    sens = {}
    for k in ("gas_own", "filed", "gas_own+tenant", "gas_own+ai"):
        c = next(c for c in cs if c["key"] == k)
        small = reservoir(dict(p, **{"water.reservoir.capacity_acft": params["water.reservoir.capacity_acft"].low}), nat, c["draw"])
        both = reservoir(dict(p, **{"water.reservoir.min_release_cfs": params["water.reservoir.min_release_cfs"].high}), nat, c["draw"])
        sens[k] = {"small": small, "both": both}
    return {"p": p, "nat": nat, "graceton": g, "checks": checks(g, b, p), "cases": cs, "sens": sens,
            "coal": coal_years(coal_history()), "gas": gas_condensers(p), "filed": filed(p), "known": known_case(p, nat)}


# --- Report and figure ---------------------------------------------------------------------------

# Where the intake and the gauge are: the 316(b) report (ASA, Feb 2026) p.3-3, 40 30' 45.22", -79 10' 58.79";
# USGS water data report 03042500, 40 31' 02", -79 10' 19".
INTAKE = (40 + 30 / 60 + 45.22 / 3600, -(79 + 10 / 60 + 58.79 / 3600))
GAUGE = (40 + 31 / 60 + 2 / 3600, -(79 + 10 / 60 + 19 / 3600))


def _km(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (*a, *b))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(h))


def _pct(x):
    return f"{x:.0%}"


def report(a: dict) -> str:
    p, k, gc = a["p"], a["checks"], a["gas"]
    cy = a["coal"][a["coal"].net > 0]
    cy = cy[cy.index < 2023]
    cs = {c["key"]: c for c in a["cases"]}
    fb = a["filed"]
    q710_mgd = k["q710_natural"] * MGD_PER_CFS
    rmin_mgd = p["water.reservoir.min_release_cfs"] * MGD_PER_CFS
    campus = p["scorecard.campus_it_mw"]
    L = ["**1. The coal plant as it ran** (EIA, plant 3122)", "",
         "| Year | Output, share of capacity | Drawn, MGD | Used up, MGD | Drawn, gal a MWh |", "|---|---|---|---|---|"]
    L += [f"| {yr} | {r.share:.0%} | {r.drawn_mgd:.1f} | {r.used_mgd:.1f} | {r.gal_mwh:,.0f} |" for yr, r in cy.iterrows()]
    h = coal_history()
    h = h.assign(mgd=h.withdrawn_mg / pd.to_datetime(dict(year=h.year, month=h.month, day=1)).dt.days_in_month)
    top = h.loc[h.mgd.idxmax()]
    L += ["", f"Its highest month: {top.mgd:.1f} MGD drawn ({int(top.month)}/{int(top.year)}). Its maximum intake rate, 14 gpm/MW "
          f"(HCR), is {cs['coal_max']['mean']:.1f} MGD.", ""]
    L += ["**2. The gas plant and the data centers**", "",
          f"- **The gas plant's own condensers** (heat balance, {gc['mw'] / p['water.gas.mw']:.0%} of full output): {gc['mw']:,.0f} MW at "
          f"{p['water.gas.efficiency']:.1%} efficiency sends {gc['cond_mw']:,.0f} MW of heat to its towers, which evaporate "
          f"{gc['evap_mgd']:.1f} MGD. At the towers' planned {gc['cycles']:.0f} cycles of concentration that is {gc['blow_mgd']:.1f} MGD of "
          f"blowdown and {gc['draw_mgd']:.1f} MGD drawn.",
          f"- **The station as filed** (drawing D-352-1801, design maximums): the intake's three pumps draw {fb['intake']:.1f} MGD. "
          f"{fb['towers_service']:.2f} MGD goes to the station's towers and service water, {fb['tenant_makeup']:.2f} MGD to the data "
          f"centers' cooling equipment ({fb['tenant_return']:.2f} MGD of it comes back to the towers), {fb['demin']:.2f} MGD to the "
          f"boilers and {fb['screen_wash']:.2f} MGD back to the creek as screen wash. The split adds to {fb['split']:.2f} MGD.",
          f"- **What the filed figures imply:** at {gc['cycles']:.0f} cycles, the towers' {fb['makeup']:.1f} MGD of makeup gives "
          f"{fb['blow']:.2f} MGD of blowdown (Outfall 027 is {fb['outfall_027']:.2f}) and {fb['evap']:.1f} MGD evaporated, enough to carry "
          f"~{fb['heat_mw']:,.0f} MW of heat against the condensers' {gc['cond_mw']:,.0f} MW. The filing fills the pumps' capacity: it is "
          f"the intake's ceiling, not the plant's expected use. DEP's permit inputs ({p['creek.permit.intake_mgd']:.0f} MGD drawn, "
          f"{p['creek.permit.consumptive_mgd']:.2f} not returned) sit just under that ceiling.",
          f"- **The data centers as filed** use up at most {fb['tenant_used']:.2f} MGD (1,400 gpm in, 400 back). Evaporated, that "
          f"carries ~{fb['tenant_heat_mw']:,.0f} MW of heat, {fb['tenant_heat_mw'] / campus:.0%} of a {campus:,.0f} MW campus's; the rest "
          f"would have to leave dry, through dry coolers or outside air.",
          f"- **Returned at design maximum:** {fb['outfall_027']:.2f} MGD to Blacklick Creek (Outfall 027), {fb['outfall_001']:.2f} MGD "
          f"to Two Lick Creek below the low dam (Outfall 001; {fb['outfall_001_july']:.2f} in July) and {fb['screen_wash']:.2f} MGD at "
          f"the intake. Not returned: {fb['used']:.1f} MGD ({fb['used_july']:.1f} in July). Part of Outfall 001 is treated landfill "
          f"leachate, not creek water, so slightly more creek water is used up.", ""]
    L += [f"**3. Each case against the reservoir** ({p['water.reservoir.capacity_acft']:,.0f} acre-ft, {a['cases'][0]['res']['cap_mg']:,.0f} "
          f"million gallons; daily, {a['nat'].index[0].year}-{a['nat'].index[-1].year}; Two Lick Creek's natural Q7-10 at Graceton "
          f"{k['q710_natural']:.1f} cfs, {q710_mgd:.1f} MGD)", "",
          "| Case | Drawn, MGD | Used up, MGD | Returned to | Reservoir at its lowest | Lowest since the dam (1969-) | Years it falls below half "
          f"| Days short | Of them, under {rmin_mgd:.1f} MGD at the dam (Indiana's draw) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c in a["cases"]:
        r = c["res"]
        used = "" if np.isnan(c["used"]) else f"{c['used']:.1f}"
        over = " *" if "+" in c["key"] and c["mean"] > fb["intake"] else ""
        L.append(f"| {c['name']}{over} | {c['mean']:.1f} | {used} | {c['to']} | {_pct(r['lowest'])} ({r['when']:%b %Y}) | "
                 f"{_pct(r['lowest_since_dam'])} ({r['when_since_dam']:%b %Y}) | {r['years_below_half']} | {r['short_days']:,} | "
                 f"{r['below_min_days']:,} |")
    L += ["", f"Days short: the reservoir is empty, and the plant's draw and the consent order's {p['water.reservoir.pass_by_cfs']:.0f} cfs over "
          f"the low dam below the intake can't both be met. Under {rmin_mgd:.1f} MGD at the dam: the reservoir can't pass even what "
          f"Indiana's water plant, just below it, draws. *: more than the intake's three pumps can draw ({fb['intake']:.1f} MGD); it "
          "would need a new intake."]
    L += ["", f"**4. The same, with a smaller usable pool and with {p['water.reservoir.pass_by_cfs']:.0f} cfs kept at the reservoir's dam too**", "",
          f"| Case | Central | Pool {a['p']['water.reservoir.capacity_acft']:,.0f} -> 13,000 acre-ft | 11 cfs also at the reservoir's dam |",
          "|---|---|---|---|"]
    for key, s in a["sens"].items():
        c, r = cs[key], cs[key]["res"]
        cell = lambda x: f"lowest {_pct(x['lowest'])}, {x['short_days']:,} days short"  # noqa: E731
        L.append(f"| {c['name']} | {cell(r)} | {cell(s['small'])} | {cell(s['both'])} |")
    kn = a["known"]
    L += ["", "**Checks**", "",
          f"- **The transfer, before the dam:** Q7-10 {k['q710_fit']:.1f} cfs against {k['q710_obs']:.1f} measured (USGS publishes 11.3); "
          f"the driest 90 days {k['low90_fit']:.1f} against {k['low90_obs']:.1f}; the driest 180 days {k['low180_fit']:.1f} against "
          f"{k['low180_obs']:.1f} cfs (the transfer is wetter in the longest droughts, so the reservoir results lean optimistic). "
          f"Scaling Blacklick's flow by area instead would give a Q7-10 of {k['q710_area']:.1f} cfs.",
          f"- **Split sample:** fitted to 1952-1960, it gives {k['q710_test']:.1f} cfs for 1960-1968 against {k['q710_test_obs']:.1f} measured.",
          f"- **Since the dam:** the gauge's mean, {k['mean_post_obs']:.1f} cfs, against the reconstructed natural {k['mean_post_nat']:.1f} "
          f"({k['mean_post_obs'] / k['mean_post_nat'] - 1:+.1%}). The reservoir moves water in time, not away; this is consistent with the "
          f"plant drawing below the gauge (the coal plant's ~5-8% of the mean would show above it). The 316(b) report places the intake "
          f"{_km(INTAKE, GAUGE):.1f} km south-west of the gauge, downstream.",
          f"- **The coal plant's own months (EIA, 2014-2023):** the reservoir's lowest is {_pct(kn['lowest'])} ({kn['when']:%b %Y}); it "
          f"carried the plant then, and the model agrees."]
    return "\n".join(L)


def figure(a: dict, path) -> None:
    import matplotlib.pyplot as plt

    from .figures import GRID, INK, INK2, MUTED, SERIES, SURFACE, _style

    cs = a["cases"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 9.2), dpi=150, facecolor=SURFACE, gridspec_kw={"height_ratios": [4, 3], "hspace": 0.32})
    for ax in (a1, a2):
        _style(ax)
    y = np.arange(len(cs))[::-1]
    draw = [c["mean"] for c in cs]
    used = [0.0 if np.isnan(c["used"]) else c["used"] for c in cs]
    a1.barh(y + 0.19, draw, height=0.36, color=SERIES[0], label="drawn at the intake")
    a1.barh(y - 0.19, used, height=0.36, color=SERIES[1], label="used up (evaporated)")
    a1.set_yticks(y, [c["name"] for c in cs], fontsize=7.5, color=INK2)
    a1.grid(axis="x", color=GRID, lw=0.6)
    a1.set_axisbelow(True)
    top = coal_history()
    top = (top.withdrawn_mg / pd.to_datetime(dict(year=top.year, month=top.month, day=1)).dt.days_in_month).max()
    q710 = a["checks"]["q710_natural"] * MGD_PER_CFS
    pumps = a["filed"]["intake"]
    for x, txt, ls, row in ((top, f"the coal plant's highest month, {top:.0f} MGD", (0, (4, 3)), 0.75),
                            (q710, f"Two Lick's natural Q7-10, {q710:.0f} MGD", (0, (1, 2)), 0.75),
                            (pumps, f"the intake's pumps, {pumps:.1f} MGD", "-", 0.75)):
        a1.axvline(x, color=INK2, lw=1.1, ls=ls)
        a1.annotate(txt, (x, y[0] + row), xytext=(3, 0), textcoords="offset points", fontsize=7, color=INK2, va="center",
                    annotation_clip=False)
    a1.set_xlabel("million gallons a day", color=INK2)
    a1.legend(loc="upper right", fontsize=8, frameon=False)
    a1.set_title("What each case draws from Two Lick Creek, and uses up", loc="left", fontsize=11, color=INK)
    # The worst drought for the intake at its ceiling, with the cases that show the spread.
    show = ["coal_ran", "gas_own", "gas_own+tenant", "filed", "gas_own+ai"]
    dep = next(c for c in cs if c["key"] == "filed")["res"]
    yr = dep["when"].year - (dep["when"].month < 4)
    win = slice(f"{yr}-05-01", f"{yr + 1}-03-31")
    for i, key in enumerate(show):
        c = next(c for c in cs if c["key"] == key)
        s = c["res"]["storage"][win]
        a2.plot(s.index, s.values * 100, color=SERIES[2 + i], lw=2, label=c["name"])
    a2.set_ylim(-3, 103)
    a2.set_ylabel("reservoir, % full", color=INK2)
    a2.grid(axis="y", color=GRID, lw=0.6)
    a2.legend(loc="upper left", bbox_to_anchor=(0.0, -0.1), ncol=2, fontsize=7, frameon=False)
    a2.set_title(f"Two Lick Creek Reservoir through {yr}'s drought (measured), the worst on the record", loc="left", fontsize=10, color=INK)
    fig.text(0.01, -0.03, "EIA thermoelectric cooling water data (plant 3122); HCG's filed water balance (NPDES renewal application, drawing "
             "D-352-1801); USGS 03042500 and 03042000 daily flows;\nreservoir 16,240 acre-ft (USGS). Data centers at 3,000 MW of IT "
             "(pass 2's models).", fontsize=6.5, color=MUTED)
    fig.savefig(path, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
