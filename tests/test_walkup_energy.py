"""Pass 3g step 10c (D28): each walk-up's energy and running cost a year (`brownfield.energy`). The
synthetic tests never skip; the run on the published model and the routes skips when they're absent."""
import math

import numpy as np
import pytest

from brownfield import energy as en
from brownfield.baseline import WALKUPS
from brownfield.loads import erv_sensible, subadditive
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def test_a_balanced_fan_adds_to_the_leakage_and_an_exhaust_fan_partly_overlaps_it():
    assert subadditive(50.0, 0.0, 20.0, 2 / 3) == pytest.approx(70.0)  # balanced: simple addition
    assert subadditive(50.0, 50.0, 20.0, 2 / 3) == pytest.approx(50.0 + 20.0 * math.exp(-2 / 3 * 50 / 20))  # Hurel et al., Table 4
    assert subadditive(500.0, 500.0, 20.0, 2 / 3) == pytest.approx(500.0, abs=1e-5)  # a large fan is the whole flow
    assert 50.0 < subadditive(50.0, 50.0, 20.0, 2 / 3) < 70.0  # sub-additive


def test_fsec_reproduces_its_own_worked_example(P):
    # FSEC-PF-464-15 Eq. 12: three occupants, Fmix 0.68, a standard washer and dishwasher: '52.3 gpd'.
    q = dict(P, **{"baseline.energy.cw_gal_cycle": 4.0, "baseline.energy.dw_gal_cycle": 8.0})
    tset, tmix = P["systems.hot_water.supply_f"], P["baseline.energy.tmix_f"]
    mains = tset - (tset - tmix) / (1 - 0.68)  # the inlet that gives Fmix 0.68
    assert float(en.fsec_gpd(q, 3.0, mains)) == pytest.approx(52.3, abs=0.15)
    # Colder water, more of it hot.
    assert float(en.fsec_gpd(P, 2.39, 45.0)) > float(en.fsec_gpd(P, 2.39, 65.0))


def test_the_erv_on_an_array_is_the_loads_ervs(P):
    ts = np.array([-30.0, -25.0, -10.0, 0.0, 5.0, 30.0])
    assert np.allclose(en.erv_sre(P, ts), [erv_sensible(P, float(t)) for t in ts])


def test_mass_carries_a_days_surplus_and_cooling_waits_for_a_day_without_heat():
    loss = np.array([100.0] * 12 + [-50.0] * 12 + [-10.0] * 24)  # a day needing heat on balance, then a warm one
    gain = np.array([0.0] * 24 + [20.0] * 24)
    h0, c0 = en.season(loss, gain, 2, 0.0)
    h1, c1 = en.season(loss, gain, 2, 1.0)
    assert h0[0] == pytest.approx(1200.0) and h1[0] == pytest.approx(600.0)  # each hour alone; the day as a whole
    assert h0[1] == h1[1] == 0.0
    assert c0[0] == c1[0] == 0.0 and c0[1] == pytest.approx(480.0)


def test_a_tanks_loss_and_a_pumps_power_from_first_principles(P):
    q = dict(P, **{"baseline.energy.tank_r": 10.0, "baseline.energy.plant_room_c": 20.0, "baseline.energy.pump_eff": 1.0})
    a = math.pi * 2 * 4 + 2 * math.pi * 1.0  # a 24 in. by 48 in. tank: its sides, top and bottom (ft2)
    assert en.tank_loss_w(24, 48, 140.0, q) == pytest.approx(a * (140 - 68) / 10 / 3.412142)
    assert en.pump_w(1.0, 1.0, q) == pytest.approx(0.18852)  # 1 gpm against 1 ft of water


def _rows(P):
    rows = []
    for w in WALKUPS:
        rows.append({"walkup": w, "use": "space heat", "meter": "flats", "kwh": 1000.0})
    rows += [{"walkup": "engineered", "use": "hot water", "meter": "house", "kwh": 500.0},
             {"walkup": "engineered", "use": "pv", "meter": "pv", "kwh": -800.0},
             {"walkup": "engineered", "use": "space heat", "meter": "heat", "kwh": 4000.0},
             {"walkup": "gas", "use": "hot water", "meter": "gas flats", "kwh": 2000.0},
             {"walkup": "central", "use": "hot water", "meter": "gas house", "kwh": 2000.0}]
    return rows


def test_pv_beyond_the_house_meters_use_is_credited_at_the_excess_price_and_gas_accounts_cost_only_where_there_is_gas(P):
    t = "baseline.tariff."
    c = en.costs(_rows(P), P, 12)
    assert c["engineered"]["usd"]["the house meter, net of PV"] == pytest.approx(-300.0 * P[t + "pv_excess_usd_kwh"]
                                                                                + 12 * P[t + "house_gss_customer_usd_month"])
    assert c["electric"]["usd"]["the flats' gas"] == 0.0 and c["electric"]["usd"]["the house's gas"] == 0.0
    assert c["gas"]["usd"]["the flats' gas"] > 12 * 12 * P[t + "gas_res_customer_usd_month"]
    assert c["central"]["usd"]["the house's gas"] > 12 * P[t + "gas_com_customer_small_usd_month"]


def test_at_the_tie_price_the_engineered_design_costs_what_each_usual_walk_up_does(P):
    rows = _rows(P)
    c = en.costs(rows, P, 12)
    for w, price in en.tie_price(c).items():
        c2 = en.costs(rows, dict(P, **{"baseline.energy.heat_usd_mwh": price}), 12)
        assert c2["engineered"]["total"] == pytest.approx(c2[w]["total"])


# ---- On the published model and the routes ----

@pytest.fixture(scope="module")
def made(P):
    from brownfield import baseline as bl, pricing, routed, systems

    if not bl.SERVICES.exists() or not (bl.RAW / "recs" / "recs2020_public_v7.csv").exists():
        pytest.skip("the services model isn't published, or RECS isn't downloaded")
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    r = bl.run(apt, P)
    pr = pricing.run(r, apt, P)
    return r, pr, apt, en.run(r, pr, apt, P)


def test_every_check_passes(made):
    *_, e = made
    assert [label for label, ok, _ in e["checks"] if not ok] == []


def test_the_erv_and_the_airtightness_each_save_heat(made):
    *_, e = made
    s = e["split"]
    assert s["usual"] > s["engineered at the code's leakage"] > s["engineered"] > 0


def test_more_fallback_hours_cost_the_engineered_design_more_and_leave_the_usual_alone(made, P):
    r, pr, apt, e = made
    more = dict(P, **{"baseline.energy.fallback_h": P["baseline.energy.fallback_h"] + 500})
    rows = en.ledger(apt, more, r["s7"], e["space"], e["hot_water"])
    c = en.costs(rows, more, e["flats"], e["demand"])
    assert c["engineered"]["total"] > e["costs"]["engineered"]["total"]
    for w in WALKUPS[1:]:
        assert c[w]["total"] == pytest.approx(e["costs"][w]["total"])


def test_a_house_meter_past_gs_smalls_limit_pays_gs_mediums_demand(P):
    t = "baseline.tariff."
    big = [{"walkup": w, "use": "x", "meter": "house", "kwh": 12 * (P[t + "gss_limit_kwh_month"] + 1)} for w in WALKUPS]
    dem = {w: {"normal_kw": 5.0, "fallback_kw": 20.0} for w in WALKUPS}
    none = dict(P, **{"baseline.energy.fallback_h": 0.0})
    c = en.costs(big, none, 12, dem)
    assert c["electric"]["house_class"] == "GS-Medium" and c["electric"]["billing_kw_months"] == pytest.approx(60.0)
    c = en.costs(big, P, 12, dem)  # a fallback month's 20 kW held at half by the ratchet for the next eleven
    assert c["electric"]["billing_kw_months"] == pytest.approx(11 * 10.0 + 20.0)
    small = [dict(r, kwh=12 * (P[t + "gss_limit_kwh_month"] - 1)) for r in big]
    assert en.costs(small, P, 12, dem)["electric"]["house_class"] == "GS-Small"


def test_the_hot_water_is_the_same_at_every_tap(made):
    *_, e = made
    hw, n = e["hot_water"], e["flats"]
    # Each walk-up heats the same water: its own heaters' energy at least the heat at the taps.
    assert hw["electric_kwh"] >= hw["flat_kwh"] and hw["own_gas_kwh"] >= hw["flat_kwh"]
    assert hw["central_gas_kwh"] >= n * hw["flat_kwh"] and hw["plant"]["plant_kwh"] + hw["plant"]["element_kwh"] >= n * hw["flat_kwh"]
