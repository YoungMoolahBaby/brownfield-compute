"""Pass 3g step 10e (D28): who gets the savings (`brownfield baseline`).

10b priced each walk-up up front and 10c its energy a year. 10e says who pays each dollar and who
keeps each saving. It adds no new prices of its own, only the rules for who pays.

- **Who pays what** (`payers`): the owner pays the construction (10b), the engineered design's extra
  fee and the house meter (its plant, pumps and own loads, net of PV). Each flat pays its own meter
  and, in the gas walk-up, its own gas account. The engineered flats also have meters for their heat
  and hot water. Two ways to use them:
  - **included:** the owner pays the heat and the hot water, inside the rent;
  - **billed:** each flat pays, at the owner's cost, for what its meters measure: the plant's share
    of the house meter (`plant_usd`, the meter's bill less its bill without the plant) and the data
    center's heat at its price.
- **A tax-credit flat** (pass 4's, `econ.flat`): the rent is capped at 30% of the 60% income limit,
  less the utility allowance for what the tenant pays. Each walk-up's cost, allowance and owner's
  bills move pass 4's gap per flat (`gap_change`). The allowance comes two ways:
  - by an energy consumption model (26 CFR 1.42-10(b)(4)(ii)(E)), which sees the design: it moves
    with the tenants' modelled bills;
  - by the housing authority's schedule (b)(4)(ii)(A), which sees only which utilities the tenant
    pays and by what fuel (`pha_change`).
  The heat and hot water are taken as included: 1.42-10(e) counts a submetered utility as the
  tenant's only if the owner buys it from a utility company, or it comes from a renewable source the
  rule names. A data center's heat is neither, as far as read, so a charge for it would be rent.
- **A market-rate flat:** the owner gets the premium back only through rent. A stated share of the
  tenants' saving (`split.rent_capture`) is taken to reach the rent, and the rent needed to carry the
  premium at pass 4's yield is set beside it.
- **The data center** (`heat_price`): what charging for its heat would move, at 10c's tie prices
  and at the price that would carry the heat network's share (pass 3 §4's annuity and upkeep).
"""

from __future__ import annotations

import json

from . import OUT_DIR
from .baseline import NAMES, WALKUPS
from .energy import NL

S = "baseline.split."
PLANT_USES = ("space heat", "hot water", "controls")  # the engineered plant's rows on the house meter
CREDITS = {"4%": 0.04, "9%": 0.09}
TC = {"4%": "tax-credit flat, 60% AMI, 4% credits", "9%": "tax-credit flat, 60% AMI, 9% credits"}
MARKET = "market-rate flat"


# ---- who pays what a year ----

def plant_usd(en: dict, p: dict, n: int) -> float:
    """The engineered plant's cost on the house meter a year (the building's): the meter's bill less
    what it would be without the plant's rows (its heat pump, swing element, pumps and controls), the
    house's own loads and the PV left on it. Without the plant the meter carries what the usual
    walk-ups' does, so its demand is theirs."""
    from .energy import costs

    rows = [r for r in en["ledger"] if not (r["walkup"] == "engineered" and r["meter"] == "house" and r["use"] in PLANT_USES)]
    dem = dict(en["demand"], engineered=en["demand"]["electric"])
    house = "the house meter, net of PV"
    return en["costs"]["engineered"]["usd"][house] - costs(rows, p, n, dem)["engineered"]["usd"][house]


def payers(en: dict, p: dict, n: int) -> dict:
    """Each walk-up's running cost a year a flat (USD), by who pays: `included` (the owner pays the
    heat and hot water) and, for the engineered design, `billed` (each flat pays its meters' share at
    the owner's cost). `heat_mwh` is the data center's heat a flat."""
    out = {}
    for w in WALKUPS:
        u = en["costs"][w]["usd"]
        tenant = u["flats' electricity"] + u["the flats' gas"]
        owner = u["the house meter, net of PV"] + u["the house's gas"] + u["the data center's heat"]
        out[w] = {"included": {"tenant": tenant / n, "owner": owner / n}, "total": en["costs"][w]["total"] / n}
    e = out["engineered"]
    meters = (plant_usd(en, p, n) + en["costs"]["engineered"]["usd"]["the data center's heat"]) / n
    e["billed"] = {"tenant": e["included"]["tenant"] + meters, "owner": e["included"]["owner"] - meters, "meters": meters}
    e["heat_mwh"] = en["costs"]["engineered"]["meters"]["heat"] / 1000 / n
    return out


# ---- up front ----

def up_front(pr: dict, n: int) -> dict:
    """What each walk-up's owner pays up front a flat beyond the usual electric walk-up's: its
    systems (10b) and, for the engineered design, the fee's extra. The heat network's share is
    beside it (`network`), the owner's only if the owner pays for it."""
    t = pr["totals"]
    out = {w: {"systems": (t[w]["total"] - t["electric"]["total"]) / n, "fee": pr["fee"]["extra_flat_usd"] if w == "engineered" else 0.0}
           for w in WALKUPS}
    for v in out.values():
        v["total"] = v["systems"] + v["fee"]
    out["network"] = {k: v["flat"] for k, v in pr["network"].items()}
    return out


# ---- pass 4's flat ----

def credit_share(p: dict, rate: float) -> float:
    """The share of a dollar of development cost that comes back as tax-credit equity (pass 4's
    `econ.flat`: eligible basis x the credit rate x 10 years x the price an investor pays)."""
    f = "pass4.finance."
    return p[f + "basis_share"] * rate * 10 * p[f + "credit_price"]


def gap_change(p: dict, d_tdc: float, d_ua_month: float, d_opex: float, d_market_rent_month: float = 0.0) -> dict:
    """Pass 4's gap per flat when a flat costs `d_tdc` more to build, its utility allowance is
    `d_ua_month` higher, its owner's bills `d_opex` a year higher, and (market-rate) its rent
    `d_market_rent_month` higher, against pass 4's flat as it stands (`econ.flat`)."""
    from .econ import flat

    c, r = "pass4.cost.", "pass4.rents."
    q = dict(p, **{c + "tdc_per_flat": p[c + "tdc_per_flat"] + d_tdc, r + "utility_allowance_usd": p[r + "utility_allowance_usd"] + d_ua_month,
                   r + "opex_usd": p[r + "opex_usd"] + d_opex, r + "market_rent_usd": p[r + "market_rent_usd"] + d_market_rent_month})
    base, now = flat(p), flat(q)
    return {k: now[k]["gap"] - base[k]["gap"] for k in base}


def closed_form(p: dict, d_tdc: float, d_ua_month: float, d_opex: float, d_market_rent_month: float = 0.0) -> dict:
    """The same change taken apart, while no floor in `econ.flat` binds: what the credits pay, what
    the change in rent carries as debt (or, market-rate, as value at the yield), and the gap."""
    from .econ import annuity

    f, r = "pass4.finance.", "pass4.rents."
    d_noi_tc = -d_ua_month * 12 * (1 - p[r + "vacancy"]) - d_opex
    debt = d_noi_tc / p[f + "dscr"] * annuity(p[f + "rate"], p[f + "term_yr"])
    out = {}
    for k, rate in CREDITS.items():
        eq = d_tdc * credit_share(p, rate)
        out[TC[k]] = {"credits": eq, "debt": debt, "gap": d_tdc - eq - debt}
    d_noi_m = d_market_rent_month * 12 * (1 - p[r + "vacancy"]) - d_opex
    worth = d_noi_m / p[f + "market_yield"]
    out[MARKET] = {"credits": 0.0, "debt": worth, "gap": d_tdc - worth}
    return out


def pha_change(p: dict, w: str) -> float:
    """The housing authority's allowance for walk-up `w` less the usual electric walk-up's (USD a
    month, a 2-bedroom): the schedule's lines for what each walk-up's tenant pays. The lines alike in
    every walk-up (cooling, cooking, other electric, the electric customer charge) cancel. The
    engineered design's and the central walk-up's hot water, and the engineered design's heat, are
    the owner's (included), so their lines drop out."""
    heat_hp, heat_gas = p[S + "pha_heat_hp_usd"], p[S + "pha_heat_gas_usd"]
    wh_e, wh_g, gas_c = p[S + "pha_wh_elec_usd"], p[S + "pha_wh_gas_usd"], p[S + "pha_gas_customer_usd"]
    return {"engineered": -heat_hp - wh_e, "electric": 0.0, "gas": heat_gas - heat_hp + wh_g - wh_e + gas_c, "central": -wh_e}[w]


def pha_against_model(en: dict, p: dict, n: int) -> dict:
    """The schedule's lines beside what 10c's model bills the usual flats for the same uses (USD a
    month, a flat): the electric flat's heat pump and tank at Penelec's residential price, the gas
    flat's furnace and heater at Peoples' (without the account's customer charge, a line of its own)."""
    from .cost import MCF_MWH

    t = "baseline.tariff."

    def kwh(w, use, meter):
        return sum(r["kwh"] for r in en["ledger"] if r["walkup"] == w and r["use"] == use and r["meter"] == meter) / n

    def elec(kwh_year):
        return kwh_year * p[t + "elec_res_usd_kwh"] / 12

    def gas(kwh_year):
        return kwh_year / 1000 / MCF_MWH * p[t + "gas_res_usd_mcf"] / 12

    return {"heating, heat pump": (p[S + "pha_heat_hp_usd"], elec(kwh("electric", "space heat", "flats"))),
            "water heating, electric": (p[S + "pha_wh_elec_usd"], elec(kwh("electric", "hot water", "flats"))),
            "heating, gas": (p[S + "pha_heat_gas_usd"], gas(kwh("gas", "space heat", "gas flats"))),
            "water heating, gas": (p[S + "pha_wh_gas_usd"], gas(kwh("gas", "hot water", "gas flats")))}


def tax_credit(p: dict, pay: dict, up: dict) -> dict:
    """Each walk-up's change in pass 4's gap per flat against the usual electric walk-up, the
    allowance both ways, the heat and hot water included."""
    out = {}
    e = pay["electric"]["included"]
    for w in WALKUPS:
        inc = pay[w]["included"]
        d_tenant = inc["tenant"] - e["tenant"]
        d_opex = inc["owner"] - e["owner"]
        ways = {"energy model": d_tenant / 12, "PHA schedule": pha_change(p, w)}
        out[w] = {"d_tdc": up[w]["total"], "d_opex": d_opex, "d_tenant_bills": d_tenant, "ways": {}}
        for way, d_ua in ways.items():
            g = gap_change(p, up[w]["total"], d_ua, d_opex)
            out[w]["ways"][way] = {"d_ua_month": d_ua, "gap": {k: g[TC[k]] for k in CREDITS},
                                   "parts": {k: closed_form(p, up[w]["total"], d_ua, d_opex)[TC[k]] for k in CREDITS},
                                   # the tenant's rent and bills together: the rent falls as the allowance rises
                                   "d_tenant_total": -d_ua * 12 + d_tenant}
    return out


def market(p: dict, pay: dict, up: dict) -> dict:
    """Each walk-up's change in pass 4's market-rate gap against the usual electric walk-up: the
    rent up by `rent_capture` of the tenants' saving (the engineered flats billed by their meters,
    as designed), and the rent that would carry the cost at pass 4's yield."""
    r, f = "pass4.rents.", "pass4.finance."
    s = p[S + "rent_capture"]
    e = pay["electric"]["included"]
    out = {}
    for w in WALKUPS:
        mine = pay[w]["billed"] if "billed" in pay[w] else pay[w]["included"]
        saving = e["tenant"] - mine["tenant"]
        d_opex = mine["owner"] - e["owner"]
        d_rent = s * saving / 12
        need = (up[w]["total"] * p[f + "market_yield"] + d_opex) / (12 * (1 - p[r + "vacancy"]))
        out[w] = {"tenant_saving": saving, "d_opex": d_opex, "d_rent_month": d_rent, "rent_needed_month": need,
                  "gap": gap_change(p, up[w]["total"], 0.0, d_opex, d_rent)[MARKET],
                  "gap_full_capture": gap_change(p, up[w]["total"], 0.0, d_opex, saving / 12)[MARKET]}
    return out


# ---- the data center's heat ----

def carry_usd_mwh(p: dict, network_flat: float, mwh: float) -> float:
    """The heat price that carries a flat's share of the heat network a year: its cost over pass 3's
    annuity (`cost.money`), its upkeep and its pumping (pass 3 §4's shares), over the heat a flat
    takes."""
    from .cost import annuity

    b = "pass3.block."
    year = network_flat / annuity(p["cost.money.discount"], p["cost.money.life_yr"]) + p[b + "om_share"] * network_flat \
        + p[b + "pump_share"] * mwh * p["cost.energy.elec_usd_mwh"]
    return year / mwh


def heat_price(p: dict, pay: dict, en: dict, up: dict) -> dict:
    """What charging for the data center's heat would move, a flat: at 10c's tie prices and at the
    prices that carry the network's share (base and dense). Who pays: the owner if the heat is
    included (a tax-credit flat), each flat by its heat meter if billed. In a tax-credit flat the
    owner's bills rise and pass 4's gap with them (the allowance doesn't move: the heat is the
    owner's)."""
    mwh = pay["engineered"]["heat_mwh"]
    prices = {f"ties with {w}": v for w, v in en["tie_usd_mwh"].items()}
    prices.update({f"carries the network ({k})": carry_usd_mwh(p, v, mwh) for k, v in up["network"].items()})
    out = {}
    for k, x in prices.items():
        g = gap_change(p, 0.0, 0.0, mwh * x)
        out[k] = {"usd_mwh": x, "usd_flat_year": mwh * x, "usd_building_year": mwh * x * en["flats"],
                  "tax_credit_gap": g[TC["4%"]]}
    return out


# ---- checks, the run, the report ----

def checks(r: dict, p: dict, en: dict) -> list[tuple[str, bool, str]]:
    from .block import per_home
    from .cost import annuity

    pay, tc = r["payers"], r["tax_credit"]
    worst = max(abs(v[c]["tenant"] + v[c]["owner"] - v["total"]) for v in pay.values() for c in ("included", "billed") if c in v)
    off = 0.0
    for v in tc.values():
        for x in v["ways"].values():
            for k in CREDITS:
                off = max(off, abs(x["gap"][k] - x["parts"][k]["gap"]))
    for w, v in r["market"].items():
        cf = closed_form(p, r["up_front"][w]["total"], 0.0, v["d_opex"], v["d_rent_month"])[MARKET]["gap"]
        off = max(off, abs(v["gap"] - cf))
    mwh = pay["engineered"]["heat_mwh"]
    tie_off = max(abs(pay["engineered"]["total"] + mwh * x - pay[w]["total"]) for w, x in en["tie_usd_mwh"].items())
    # The network's carrying price against pass 3 §4's own costing of it (`block.per_home`'s loop
    # home): the building's own parts (radiant floor, interface, booster, AC) at nothing, the whole
    # network share put on its main, the heat taken as space heat.
    lh, b = "pass3.loop_home.", "pass3.block."
    zero = dict(p, **{lh + "radiant_usd_ft2": 0.0, lh + "hiu_usd": 0.0, lh + "booster_usd": 0.0, lh + "ac_usd": 0.0,
                      b + "street_usd_m": 0.0, b + "plant_usd_kw": 0.0})
    af = annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    net_off = 0.0
    for v in r["up_front"]["network"].values():
        q = dict(zero, **{b + "main_usd_m": v * p[b + "homes"] / (p[b + "main_km"] * 1000)})
        theirs = per_home(q, mwh, 0.0, 0.0, 0.0, 1.0)["A"]
        net_off = max(net_off, abs(carry_usd_mwh(p, v, mwh) * mwh * af - theirs))
    e = pay["engineered"]
    return [
        ("every dollar of 10c's running cost has a payer, the heat and hot water included or billed", worst < 1e-6, f"worst ${worst:.2e} a flat"),
        ("billed at cost, the engineered owner pays no more for the house meter than the usual electric walk-up's owner (the same own loads, less PV)",
         e["billed"]["owner"] <= pay["electric"]["included"]["owner"] + 1e-9,
         f"${e['billed']['owner']:,.0f} against ${pay['electric']['included']['owner']:,.0f} a flat a year; the meters bill ${e['billed']['meters']:,.0f}"),
        ("pass 4's gap moves as its parts add up (the credits, the debt or value the rent carries; no floor binds)", off < 0.01, f"worst ${off:.2e}"),
        ("at 10c's tie prices, the engineered design's running cost meets each usual walk-up's", tie_off < 1e-6, f"worst ${tie_off:.2e} a flat"),
        ("the network's carrying price gives pass 3 §4's own cost of it over the years (`block.per_home`)", net_off < 1e-6,
         f"worst ${net_off:.2e} a flat"),
    ]


def run(pr: dict, en: dict, p: dict) -> dict:
    """10e on 10b's run (`pricing.run`) and 10c's (`energy.run`): who pays what, pass 4's gap each
    way, the heat's price; written to `out/pass3/savings.json` and `.md`."""
    n = en["flats"]
    pay = payers(en, p, n)
    up = up_front(pr, n)
    out = {"payers": pay, "up_front": up, "tax_credit": tax_credit(p, pay, up), "market": market(p, pay, up),
           "heat_price": heat_price(p, pay, en, up), "pha_against_model": pha_against_model(en, p, n), "flats": n}
    out["checks"] = checks(out, p, en)
    path = OUT_DIR / "pass3"
    (path / "savings.json").write_text(json.dumps(out, indent=1, default=float) + NL, encoding="utf-8")
    (path / "savings.md").write_text(report(out, p) + NL, encoding="utf-8")
    out["written"] = [path / "savings.json", path / "savings.md"]
    return out


def _row(label: str, vals) -> str:
    return f"{label:52s} " + " ".join(f"{v:>11s}" for v in vals)


def _usd(x: float) -> str:
    return f"{'-' if x < -0.5 else ''}${abs(x):,.0f}"


def report(r: dict, p: dict) -> str:
    from .systems import report as fmt

    pay, up, tc, mk, hp = r["payers"], r["up_front"], r["tax_credit"], r["market"], r["heat_price"]
    head = _row("", WALKUPS)
    e = pay["engineered"]
    lines = ["Pass 3g step 10e: who gets the savings", "", fmt(r["checks"]), "",
             "Up front, a flat, beyond the usual electric walk-up's (USD 2026; the owner's):", head,
             _row("the systems (10b)", [_usd(up[w]["systems"]) for w in WALKUPS]),
             _row("the fee's extra", [_usd(up[w]["fee"]) for w in WALKUPS]),
             _row("total", [_usd(up[w]["total"]) for w in WALKUPS]),
             "  beside it, the heat network's share (pass 3 §4), the owner's only if the owner pays it: "
             + "; ".join(f"{k} {_usd(v)}" for k, v in up["network"].items()),
             "", "A year, a flat (10c's running cost, the data center's heat free), by who pays:", head,
             _row("the tenant (own meter, own gas)", [_usd(pay[w]["included"]["tenant"]) for w in WALKUPS]),
             _row("the owner (house meter net of PV, house gas, heat)", [_usd(pay[w]["included"]["owner"]) for w in WALKUPS]),
             _row("total", [_usd(pay[w]["total"]) for w in WALKUPS]),
             f"  the engineered flats billed by their meters at the owner's cost: the tenant {_usd(e['billed']['tenant'])}, "
             f"the owner {_usd(e['billed']['owner'])} (the plant's share of the house meter {_usd(e['billed']['meters'])})",
             "", "A tax-credit flat (pass 4's; the heat and hot water the owner's): the change in its gap a flat against the usual electric walk-up's"]
    for way in ("energy model", "PHA schedule"):
        lines += [f"  the allowance by the {way}:", head,
                  _row("    the allowance, USD a month", [f"{tc[w]['ways'][way]['d_ua_month']:+,.0f}" for w in WALKUPS]),
                  _row("    the tenant's rent and bills, a year", [f"{tc[w]['ways'][way]['d_tenant_total']:+,.0f}" for w in WALKUPS])]
        for k in CREDITS:
            lines.append(_row(f"    the gap, {k} credits", [_usd(tc[w]["ways"][way]["gap"][k]) for w in WALKUPS]))
    for way in ("energy model", "PHA schedule"):
        x = tc["engineered"]["ways"][way]["parts"]
        lines.append(f"  the engineered design's {_usd(tc['engineered']['d_tdc'])} ({way}): the credits pay {_usd(x['4%']['credits'])} (4%) "
                     f"or {_usd(x['9%']['credits'])} (9%), the owner's higher net rent carries {_usd(x['4%']['debt'])} of debt, the gap takes the rest")
    lines.append("  the schedule's lines (Westmoreland County's, 2026) against what 10c's model bills, USD a month a flat: "
                 + "; ".join(f"{k} {a:,.0f} against {b:,.0f}" for k, (a, b) in r["pha_against_model"].items()))
    lines += ["", f"A market-rate flat: the rent up by {p[S + 'rent_capture']:.0%} of the tenant's saving (the engineered flats billed by their meters):", head,
              _row("  the tenant's saving a year", [_usd(mk[w]["tenant_saving"]) for w in WALKUPS]),
              _row("  the rent's rise, USD a month", [f"{mk[w]['d_rent_month']:+,.0f}" for w in WALKUPS]),
              _row("  the rent that would carry the cost, USD a month", [f"{mk[w]['rent_needed_month']:+,.0f}" for w in WALKUPS]),
              _row("  pass 4's market-rate gap", [_usd(mk[w]["gap"]) for w in WALKUPS]),
              _row("  the same if the rent took the whole saving", [_usd(mk[w]["gap_full_capture"]) for w in WALKUPS])]
    lines += ["", f"The data center's heat ({e['heat_mwh']:.2f} MWh a flat a year): what a price would move"]
    for k, v in hp.items():
        lines.append(f"  {k}: ${v['usd_mwh']:,.0f}/MWh, {_usd(v['usd_flat_year'])} a flat a year ({_usd(v['usd_building_year'])} the building); "
                     f"included, pass 4's tax-credit gap {_usd(v['tax_credit_gap'])} a flat")
    lines += ["", "The walk-ups: " + "; ".join(f"{w}, {NAMES[w]}" for w in WALKUPS)]
    return NL.join(lines)
