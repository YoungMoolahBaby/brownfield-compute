"""Pass 4: the economic base against published figures and hand-worked values."""

from brownfield import econ
from brownfield.params import load_params, values

PARAMS = load_params()
P = values(PARAMS)


def test_phfa_rent_from_income_limit():
    # A 2-bedroom's rent limit is 30% of the 3-person income limit, monthly: PHFA's 2026 table
    # for Indiana County gives $1,164 at 60% of $83,800.
    assert round(P["pass4.rents.lihtc_60_3p_usd"] * 0.30 / 12) == 1164


def test_hud_tdc_is_175_times_hcc():
    # HUD's 2024 walk-up limits: Johnstown 2 bedrooms HCC 161,169, TDC 282,045.
    assert abs(161169 * 1.75 - 282045) < 1.0


def test_demand_by_hand():
    d = econ.demand(P)
    j, w = P["pass4.demand.jobs"], P["pass4.demand.workers_per_household"]
    hh = (j * P["pass4.demand.movers_share"] + j * P["pass4.demand.induced_per_job"] * P["pass4.demand.induced_movers_share"]) / w
    assert abs(d["households"] - hh) < 1e-9
    assert abs(d["near_renters"] - hh * P["pass4.demand.renter_share"] * P["pass4.demand.near_campus_share"]) < 1e-9


def test_flat_by_hand():
    f = econ.flat(P)["tax-credit flat, 60% AMI, 4% credits"]
    rent = 46560 * 0.30 / 12 - P["pass4.rents.utility_allowance_usd"]
    noi = rent * 12 * (1 - P["pass4.rents.vacancy"]) - P["pass4.rents.opex_usd"]
    r, n = P["pass4.finance.rate"], P["pass4.finance.term_yr"]
    debt = noi / P["pass4.finance.dscr"] * (1 - (1 + r) ** -n) / r
    equity = P["pass4.cost.tdc_per_flat"] * P["pass4.finance.basis_share"] * 0.04 * 10 * P["pass4.finance.credit_price"]
    assert abs(f["gap"] - (P["pass4.cost.tdc_per_flat"] - debt - equity)) < 1e-6


def test_campus_tax_by_hand():
    t = econ.campus_tax(P)
    assessed = 39 * 225000 * P["pass4.money.dc_value_ft2"] * P["pass4.money.clr"]
    assert abs(t["total"] - assessed * 25.8989 / 1000) < 1.0
    f = econ.funding(P)
    assert abs(f["flats_a_year"] - t["total"] * P["pass4.money.housing_share"] / f["gap"]) < 1e-9
