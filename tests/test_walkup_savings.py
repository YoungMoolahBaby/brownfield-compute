"""Pass 3g step 10e (D28): who gets the savings (`brownfield.savings`). The synthetic tests never
skip; the run on the published model and the routes skips when they're absent."""
import pytest

from brownfield import savings as sv
from brownfield.econ import annuity
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def test_a_dollar_of_cost_adds_to_the_tax_credit_gap_what_the_credits_dont_pay(P):
    g = sv.gap_change(P, 1000.0, 0.0, 0.0)
    f = "pass4.finance."
    four = P[f + "basis_share"] * 0.04 * 10 * P[f + "credit_price"]
    assert g[sv.TC["4%"]] == pytest.approx(1000.0 * (1 - four))
    assert g[sv.TC["9%"]] == pytest.approx(1000.0 * (1 - four * 9 / 4))
    assert g[sv.MARKET] == pytest.approx(1000.0)  # no credits on a market-rate flat


def test_a_lower_allowance_raises_the_rent_and_the_debt_it_carries(P):
    # $10 a month less allowance: $10 more rent, less vacancy, over the coverage, as a mortgage.
    f, r = "pass4.finance.", "pass4.rents."
    debt = 10 * 12 * (1 - P[r + "vacancy"]) / P[f + "dscr"] * annuity(P[f + "rate"], P[f + "term_yr"])
    g = sv.gap_change(P, 0.0, -10.0, 0.0)
    assert g[sv.TC["4%"]] == pytest.approx(-debt) and g[sv.TC["9%"]] == pytest.approx(-debt)
    assert g[sv.MARKET] == pytest.approx(0.0)  # the allowance is the tax-credit rent's only
    # The owner paying $114 a year more takes the same debt away as $10 a month less rent would.
    more = sv.gap_change(P, 0.0, 0.0, 10 * 12 * (1 - P[r + "vacancy"]))
    assert more[sv.TC["4%"]] == pytest.approx(debt)
    assert more[sv.MARKET] == pytest.approx(10 * 12 * (1 - P[r + "vacancy"]) / P[f + "market_yield"])


def test_the_parts_add_up_to_the_gap(P):
    for args in ((5000.0, -20.0, 300.0, 0.0), (0.0, 15.0, -50.0, 40.0)):
        g, cf = sv.gap_change(P, *args), sv.closed_form(P, *args)
        for k, v in cf.items():
            assert v["gap"] == pytest.approx(g[k])
            assert v["gap"] == pytest.approx(args[0] - v["credits"] - v["debt"])


def test_the_pha_schedule_sees_only_who_pays_and_by_what_fuel(P):
    q = dict(P, **{sv.S + "pha_heat_hp_usd": 30.0, sv.S + "pha_heat_gas_usd": 40.0, sv.S + "pha_wh_elec_usd": 25.0,
                   sv.S + "pha_wh_gas_usd": 12.0, sv.S + "pha_gas_customer_usd": 17.0})
    assert sv.pha_change(q, "electric") == 0.0
    assert sv.pha_change(q, "engineered") == pytest.approx(-55.0)  # the heat and hot water the owner's
    assert sv.pha_change(q, "central") == pytest.approx(-25.0)  # the hot water the owner's
    assert sv.pha_change(q, "gas") == pytest.approx(40 - 30 + 12 - 25 + 17)
    dearer = dict(q, **{sv.S + "pha_heat_hp_usd": 50.0})
    assert sv.pha_change(dearer, "central") == sv.pha_change(q, "central")  # its tenants heat with the same heat pump


def test_a_network_that_costs_nothing_is_carried_by_its_pumping_alone(P):
    b = "pass3.block."
    assert sv.carry_usd_mwh(P, 0.0, 3.9) == pytest.approx(P[b + "pump_share"] * P["cost.energy.elec_usd_mwh"])
    assert sv.carry_usd_mwh(P, 10000.0, 3.9) > sv.carry_usd_mwh(P, 2000.0, 3.9)
    assert sv.carry_usd_mwh(P, 10000.0, 7.8) == pytest.approx(sv.carry_usd_mwh(P, 10000.0, 3.9) / 2
                                                              + P[b + "pump_share"] * P["cost.energy.elec_usd_mwh"] / 2)


# ---- On the published model and the routes ----

@pytest.fixture(scope="module")
def made(P):
    from brownfield import baseline as bl, energy, pricing, routed, systems

    if not bl.SERVICES.exists() or not (bl.RAW / "recs" / "recs2020_public_v7.csv").exists():
        pytest.skip("the services model isn't published, or RECS isn't downloaded")
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    r = bl.run(apt, P)
    pr = pricing.run(r, apt, P)
    en = energy.run(r, pr, apt, P)
    return pr, en, sv.run(pr, en, P)


def test_every_check_passes(made):
    *_, s = made
    assert [label for label, ok, _ in s["checks"] if not ok] == []


def test_billing_by_the_meters_moves_dollars_between_payers_not_the_total(made):
    *_, s = made
    e = s["payers"]["engineered"]
    assert e["billed"]["tenant"] + e["billed"]["owner"] == pytest.approx(e["included"]["tenant"] + e["included"]["owner"])
    assert e["billed"]["meters"] > 0 and e["billed"]["tenant"] > e["included"]["tenant"]


def test_an_allowance_by_energy_model_leaves_each_tenant_where_they_were(made):
    *_, s = made
    for v in s["tax_credit"].values():
        assert v["ways"]["energy model"]["d_tenant_total"] == pytest.approx(0.0, abs=1e-9)


def test_the_rent_capture_moves_only_the_market_rate_gap(made, P):
    *_, s = made
    q = dict(P, **{sv.S + "rent_capture": 0.0})
    none = sv.market(q, s["payers"], s["up_front"])
    half = sv.market(dict(P, **{sv.S + "rent_capture": 0.5}), s["payers"], s["up_front"])
    for w, v in none.items():
        # With no capture the market-rate gap takes the whole cost, and the owner's bills over the yield.
        assert v["gap"] == pytest.approx(s["up_front"][w]["total"] + v["d_opex"] / P["pass4.finance.market_yield"])
        if v["tenant_saving"] > 0:
            assert v["gap"] > half[w]["gap"] > v["gap_full_capture"]
    assert sv.tax_credit(q, s["payers"], s["up_front"]) == s["tax_credit"]


def test_charging_for_the_heat_moves_the_included_tax_credit_gap_by_its_bill(made, P):
    *_, s = made
    f = "pass4.finance."
    for v in s["heat_price"].values():
        assert v["tax_credit_gap"] == pytest.approx(v["usd_flat_year"] / P[f + "dscr"] * annuity(P[f + "rate"], P[f + "term_yr"]))
