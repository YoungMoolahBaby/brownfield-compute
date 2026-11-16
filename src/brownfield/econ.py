"""Pass 4: the economic base. Who would live in flats beside the Homer City campus, what a flat
costs and what households here can pay, and whether the campus's own money could close the gap.

1. **Demand**: AWS's permanent staff and the other local jobs they bring, the share who move in,
   households, renters, and the share who'd choose Homer City and Center Township.
2. **A flat's economics**: HUD's total development cost for a 2-bedroom walk-up against three ways to
   pay for it: tax-credit flats at 60% of the area median income (4% credits, non-competitive; 9%
   credits, competitive and scarce) and market-rate flats. Gap = cost - what the rent carries as a
   mortgage - tax-credit equity.
3. **The campus's property tax** at full build-out (AWS says it won't seek abatements), by taxing
   body, and how many flats a share of it would close the gap on each year.
"""

from __future__ import annotations

import numpy as np

D, C, R, F, M = "pass4.demand.", "pass4.cost.", "pass4.rents.", "pass4.finance.", "pass4.money."


def demand(p: dict) -> dict[str, float]:
    """Households moving in for the campus's jobs, and the renters among them who'd live nearby;
    'direct' are AWS staff (market-rate incomes), 'induced' the other local jobs (local wages)."""
    j, w, r, q = p[D + "jobs"], p[D + "workers_per_household"], p[D + "renter_share"], p[D + "near_campus_share"]
    direct_hh = j * p[D + "movers_share"] / w
    induced_hh = j * p[D + "induced_per_job"] * p[D + "induced_movers_share"] / w
    return {"jobs": j, "induced_jobs": j * p[D + "induced_per_job"], "direct_households": direct_hh,
            "induced_households": induced_hh, "households": direct_hh + induced_hh,
            "near_direct": direct_hh * r * q, "near_induced": induced_hh * r * q,
            "near_renters": (direct_hh + induced_hh) * r * q}


def annuity(rate: float, years: float) -> float:
    return (1 - (1 + rate) ** -years) / rate


def flat(p: dict) -> dict[str, dict[str, float]]:
    """Per flat: rent, net operating income, the mortgage it carries, tax-credit equity, the gap."""
    tdc = p[C + "tdc_per_flat"]
    lihtc_rent = p[R + "lihtc_60_3p_usd"] * 0.30 / 12 - p[R + "utility_allowance_usd"]
    debt = lambda noi: max(0.0, noi / p[F + "dscr"] * annuity(p[F + "rate"], p[F + "term_yr"]))
    noi = lambda rent: rent * 12 * (1 - p[R + "vacancy"]) - p[R + "opex_usd"]
    credits = lambda rate: tdc * p[F + "basis_share"] * rate * 10 * p[F + "credit_price"]
    out = {}
    for name, rent, equity in (("tax-credit flat, 60% AMI, 4% credits", lihtc_rent, credits(0.04)),
                               ("tax-credit flat, 60% AMI, 9% credits", lihtc_rent, credits(0.09))):
        n = noi(rent)
        out[name] = {"rent": rent, "noi": n, "debt": debt(n), "equity": equity, "gap": max(0.0, tdc - debt(n) - equity)}
    n = noi(p[R + "market_rent_usd"])
    worth = n / p[F + "market_yield"]  # what a developer can spend and still earn its yield
    out["market-rate flat"] = {"rent": p[R + "market_rent_usd"], "noi": n, "debt": 0.0, "equity": worth,
                               "gap": max(0.0, tdc - worth)}
    return out


def campus_tax(p: dict) -> dict[str, float]:
    """The campus's real-property tax a year at full build-out, by taxing body (USD)."""
    value = p[M + "dc_buildings"] * p[M + "dc_ft2_each"] * p[M + "dc_value_ft2"]
    assessed = value * p[M + "clr"]
    out = {"market_value": value, "assessed": assessed}
    for body in ("county", "township", "school"):
        out[body] = assessed * p[M + f"mills_{body}"] / 1000
    out["total"] = out["county"] + out["township"] + out["school"]
    return out


def funding(p: dict) -> dict[str, float]:
    """A share of the campus's tax into housing: tax-credit flats (4% credits) closed a year."""
    tax = campus_tax(p)["total"]
    fund = tax * p[M + "housing_share"]
    gap = flat(p)["tax-credit flat, 60% AMI, 4% credits"]["gap"]
    return {"fund": fund, "gap": gap, "flats_a_year": fund / gap if gap > 0 else float("inf")}


def monte_carlo(params: dict, n: int = 4000, seed: int = 21) -> dict[str, np.ndarray]:
    from .params import draw

    d = draw({k: v for k, v in params.items() if k.startswith("pass4.")}, n, seed)
    keys = ("near_renters", "near_direct", "near_induced", "gap_4", "gap_9", "gap_market", "tax", "flats_a_year")
    out = {k: np.empty(n) for k in keys}
    for i in range(n):
        p = {k: float(v[i]) for k, v in d.items()}
        dm, fl, tx, fu = demand(p), flat(p), campus_tax(p), funding(p)
        out["near_renters"][i], out["near_direct"][i], out["near_induced"][i] = dm["near_renters"], dm["near_direct"], dm["near_induced"]
        out["gap_4"][i] = fl["tax-credit flat, 60% AMI, 4% credits"]["gap"]
        out["gap_9"][i] = fl["tax-credit flat, 60% AMI, 9% credits"]["gap"]
        out["gap_market"][i] = fl["market-rate flat"]["gap"]
        out["tax"][i], out["flats_a_year"][i] = tx["total"], fu["flats_a_year"]
    return out


def report(p: dict, params: dict, housing=None) -> str:
    dm, fl, tx, fu = demand(p), flat(p), campus_tax(p), funding(p)
    mc = monte_carlo(params)
    pct = lambda a: "{:,.0f} / {:,.0f} / {:,.0f}".format(*np.percentile(a, [10, 50, 90]))
    lines = ["**1. Who would move in**", "",
             "| | Central | P10 / P50 / P90 |", "|---|---|---|",
             f"| AWS permanent staff (2036) | {dm['jobs']:,.0f} | |",
             f"| Other local jobs they bring | {dm['induced_jobs']:,.0f} | |",
             f"| Households moving in | {dm['households']:,.0f} ({dm['direct_households']:,.0f} AWS, {dm['induced_households']:,.0f} others) | |",
             f"| **Renters among them who'd live in Homer City or Center Township** | **{dm['near_renters']:,.0f}** | {pct(mc['near_renters'])} |",
             f"| of them AWS staff (market-rate incomes) | {dm['near_direct']:,.0f} | {pct(mc['near_direct'])} |",
             f"| of them in other local jobs (local wages) | {dm['near_induced']:,.0f} | {pct(mc['near_induced'])} |"]
    if housing is not None:
        hc = housing[housing["name"].str.startswith(("Homer City borough", "Center township"))]
        burdened = (hc["renters"] * hc["rent_burdened"]).sum()
        lines += ["", f"Already here (ACS 2019-2023): Homer City and Center Township have {hc['renters'].sum():,.0f} renter households, "
                      f"{hc['for_rent'].sum():,.0f} homes for rent, {hc['apartments_5plus'].sum():,.0f} flats in buildings of 5 or more, "
                      f"and ~{burdened:,.0f} renter households paying 30% or more of their income in rent."]
    lines += ["", "**2. What a flat costs, and what pays for it** (2-bedroom, per flat)", "",
              "| | Rent a month | Net operating income | Mortgage it carries | Tax-credit equity (market: value) | Gap | Gap P10 / P50 / P90 |",
              "|---|---|---|---|---|---|---|"]
    keys = {"tax-credit flat, 60% AMI, 4% credits": "gap_4", "tax-credit flat, 60% AMI, 9% credits": "gap_9", "market-rate flat": "gap_market"}
    for name, v in fl.items():
        lines.append(f"| {name} | ${v['rent']:,.0f} | ${v['noi']:,.0f} | ${v['debt']:,.0f} | ${v['equity']:,.0f} | **${v['gap']:,.0f}** | "
                     f"${pct(mc[keys[name]]).replace(' / ', ' / $')} |")
    lines += ["", f"Total development cost ${p[C + 'tdc_per_flat']:,.0f} a flat (HUD's 2024 walk-up limit for Johnstown, raised to 2026); "
                  f"the construction share ${p[C + 'hcc_per_flat']:,.0f}.",
              "", "**3. The campus's property tax at full build-out**", "",
              f"{p[M + 'dc_buildings']:.0f} buildings x {p[M + 'dc_ft2_each']:,.0f} sq ft at ${p[M + 'dc_value_ft2']:,.0f}/sq ft = "
              f"${tx['market_value'] / 1e9:,.1f}B market value, x {p[M + 'clr']:.3f} = ${tx['assessed'] / 1e9:,.2f}B assessed:", "",
              "| Taxing body | Mills | A year |", "|---|---|---|",
              f"| Indiana County | {p[M + 'mills_county']:.3f} | ${tx['county'] / 1e6:,.1f}M |",
              f"| Center Township | {p[M + 'mills_township']:.3f} | ${tx['township'] / 1e6:,.1f}M |",
              f"| Homer-Center School District | {p[M + 'mills_school']:.4f} | ${tx['school'] / 1e6:,.1f}M |",
              f"| **Total** | {p[M + 'mills_county'] + p[M + 'mills_township'] + p[M + 'mills_school']:.3f} | **${tx['total'] / 1e6:,.1f}M** "
              f"(P10 / P50 / P90 ${pct(mc['tax'] / 1e6).replace(' / ', 'M / $')}M) |",
              "", f"With {p[M + 'housing_share']:.0%} of it put into housing: ${fu['fund'] / 1e6:,.1f}M a year closes the gap on "
                  f"**{fu['flats_a_year']:,.0f} tax-credit flats a year** (4% credits), P10 / P50 / P90 {pct(mc['flats_a_year'])}."]
    # What it would take: a market-rate flat for each AWS household who'd live nearby (their incomes
    # are above the tax-credit limits), a tax-credit flat for each other newcomer, and one for each
    # renter household already paying 30% or more of its income.
    if housing is not None:
        need = dm["near_direct"] * fl["market-rate flat"]["gap"] + dm["near_induced"] * fl["tax-credit flat, 60% AMI, 4% credits"]["gap"]
        extra = burdened * fl["tax-credit flat, 60% AMI, 4% credits"]["gap"]
        lines += ["", f"What it would take: gap funding of ${need / 1e6:,.1f}M for every newcomer household who'd rent nearby "
                      f"({dm['near_direct']:,.0f} market-rate flats for AWS staff, {dm['near_induced']:,.0f} tax-credit flats), "
                      f"{need / tx['total']:.0%} of one year of the campus's tax; ${(need + extra) / 1e6:,.1f}M with a tax-credit flat "
                      f"for each of the ~{burdened:,.0f} rent-burdened households already here, {(need + extra) / tx['total']:.0%} of one year."]
    return "\n".join(lines)


def tornado(params: dict, p: dict, metric, top: int = 5) -> list[tuple[str, float, float]]:
    """How far `metric(p)` moves as each pass 4 input goes from its low to its high end."""
    rows = []
    for k, v in params.items():
        if not k.startswith("pass4.") or v.low == v.high:
            continue
        lo, hi = metric(dict(p, **{k: v.low})), metric(dict(p, **{k: v.high}))
        if abs(hi - lo) > 1e-9:
            rows.append((k.removeprefix("pass4."), lo, hi))
    return sorted(rows, key=lambda r: -abs(r[2] - r[1]))[:top]


def sensitivity(params: dict, p: dict) -> str:
    lines = []
    for title, metric, fmt in (
        ("Renters who'd live near the campus", lambda q: demand(q)["near_renters"], "{:,.0f}"),
        ("Gap on a tax-credit flat (4% credits)", lambda q: flat(q)["tax-credit flat, 60% AMI, 4% credits"]["gap"], "${:,.0f}"),
        ("The campus's property tax a year", lambda q: campus_tax(q)["total"] / 1e6, "${:,.1f}M"),
    ):
        lines += ["", f"What moves it most: {title.lower()} (each input low -> high):", ""]
        lines += [f"- {k}: {fmt.format(lo)} -> {fmt.format(hi)}" for k, lo, hi in tornado(params, p, metric)]
    return "\n".join(lines)
