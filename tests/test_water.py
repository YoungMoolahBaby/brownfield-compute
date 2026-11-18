"""Pass 2f, the water budget: the flow transfer, the gas plant's heat balance, and the reservoir's mass balance."""

import numpy as np
import pandas as pd
import pytest

from brownfield import water
from brownfield.module import GAL, H_FG
from brownfield.params import load_params, values

P = values(load_params())


def test_qppq_onto_itself_is_the_identity():
    idx = pd.date_range("2000-01-01", periods=3 * 365, freq="D")
    q = pd.Series(np.exp(np.random.default_rng(1).normal(3, 1, len(idx))), index=idx)
    out = water.qppq(water.qppq_fit(q, q), q)
    assert np.allclose(out.values, q.values, rtol=1e-6)


def test_qppq_maps_a_scaled_source_back():
    idx = pd.date_range("2000-01-01", periods=2 * 365, freq="D")
    s = pd.Series(np.exp(np.random.default_rng(2).normal(3, 1, len(idx))), index=idx)
    t = 0.5 * s  # a target with half the flow every day
    assert np.allclose(water.qppq(water.qppq_fit(t, s), s).values, t.values, rtol=1e-6)


def test_gas_condensers_by_hand():
    g = water.gas_condensers(P)
    w = "water.gas."
    mw = P[w + "mw"] * P[w + "output_share"]
    fuel = mw / P[w + "efficiency"]
    cond = fuel * (1 - P[w + "efficiency"] - P[w + "stack_loss_share"] - P[w + "other_loss_share"])
    kg_s = cond * 1e6 * P["pass2.conventional.evap_fraction"] / H_FG
    mgd = kg_s * 86400 / 1000 / GAL / 1e6
    assert g["cond_mw"] == pytest.approx(cond)
    assert g["evap_mgd"] == pytest.approx(mgd)
    assert g["draw_mgd"] == pytest.approx(mgd + P["creek.permit.discharge_mgd"])
    # Inverting: the heat that evaporation carries is the condensers' heat.
    assert water.heat_for(g["evap_mgd"], P) == pytest.approx(cond)


def _flat(days, cfs):
    return pd.Series(np.full(days, float(cfs)), index=pd.date_range("2001-04-01", periods=days, freq="D"))


def test_reservoir_conserves_water():
    rng = np.random.default_rng(3)
    nat = pd.Series(np.exp(rng.normal(3.5, 1.2, 730)), index=pd.date_range("2001-04-01", periods=730, freq="D"))
    r = water.reservoir(P, nat, np.full(12, 40.0))
    s = r["storage"].values * r["cap_mg"]
    balance = r["cap_mg"] + np.cumsum(r["inflow"] - r["evap"] - r["release"] - r["spill"])
    assert np.allclose(s, balance, atol=1e-6)


def test_release_is_the_minimum_when_the_creek_covers_the_draw():
    r = water.reservoir(P, _flat(60, 500.0), np.full(12, 10.0))
    rmin = P["creek.permit.twolick_release_cfs"] * water.MGD_PER_CFS
    assert np.allclose(r["release"], rmin)
    assert r["lowest"] == pytest.approx(1.0)


def test_a_dry_spell_empties_a_reservoir_that_cannot_carry_the_draw():
    days = 400
    r = water.reservoir(P, _flat(days, 1.0), np.full(12, 60.0))
    need = 60.0 + P["water.reservoir.pass_by_cfs"] * water.MGD_PER_CFS
    # It runs dry about when the pool is spent on the draw net of the trickle in.
    expect = r["cap_mg"] / (need - 1.0 * water.MGD_PER_CFS * (1 - P["water.reservoir.drainage_mi2"] / P["water.gauges.graceton_mi2"]))
    first = int(np.argmax(r["short"] > 0))
    assert first == pytest.approx(expect, rel=0.1)
    assert r["lowest"] == 0.0 and r["below_min_days"] > 0


def test_coal_years_by_hand():
    h = pd.DataFrame({"year": [2014, 2014], "month": [1, 2], "mw": [1000.0, 1000.0], "net_mwh": [372000.0, 336000.0],
                      "withdrawn_mg": [310.0, 280.0], "consumed_mg": [155.0, 140.0]})
    y = water.coal_years(h).loc[2014]
    assert y.drawn_mgd == pytest.approx(590.0 / 59)
    assert y.share == pytest.approx(708000.0 / (1000 * 24 * 59))
    assert y.gal_mwh == pytest.approx(590e6 / 708000.0)
