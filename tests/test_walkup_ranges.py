"""Pass 3g step 10f (D28): the ranges (`brownfield.ranges`). The synthetic tests never skip; the run on
the published model and the routes skips when they're absent."""
import numpy as np
import pytest

from brownfield import ranges as rg
from brownfield.baseline import WALKUPS
from brownfield.params import Param, draw, load_params, values


@pytest.fixture(scope="module")
def params():
    return load_params()


@pytest.fixture(scope="module")
def P(params):
    return values(params)


def _lines(cls: str, usd: float, qty: float = 1.0, walkups=("engineered",)) -> dict:
    return {"lines": [{"class": cls, "qty": {w: qty if w in walkups else 0.0 for w in WALKUPS},
                       "usd": {w: usd * qty if w in walkups else 0.0 for w in WALKUPS}}]}


def _p(**more) -> dict:
    p = {"cost.money.discount": 0.07, "cost.money.life_yr": 20.0, "systems.pv.dc_ac": 1.2, **{rg.U + k: 0.0 for k in rg.UPKEEP}}
    p.update(more)
    return p


def test_an_item_lasting_half_the_years_is_bought_again_once_at_mid_life():
    w = rg.wear(_lines("x", 1000.0), _p(**{rg.L + "x": 10.0}), 1)
    assert w["engineered"]["replace"] == pytest.approx(1000.0 / 1.07 ** 10)
    assert w["electric"]["replace"] == 0.0


def test_an_item_lasting_the_years_counted_or_longer_is_counted_once():
    for life in (20.0, 35.0):
        assert rg.wear(_lines("x", 1000.0), _p(**{rg.L + "x": life}), 1)["engineered"]["replace"] == 0.0
    assert rg.wear(_lines("x", 1000.0), _p(), 1)["engineered"]["replace"] == 0.0  # no life given: lasts


def test_a_shorter_life_costs_more_and_its_cost_spreads_without_a_cliff():
    f = [rg.wear(_lines("x", 1000.0), _p(**{rg.L + "x": life}), 1)["engineered"]["replace"] for life in (8.0, 12.0, 19.0, 19.99)]
    assert f[0] > f[1] > f[2] > f[3] > 0
    assert f[3] < 5.0  # a life just under the years counted adds almost nothing


def test_upkeep_is_per_unit_of_its_classes_and_a_flat():
    p = _p(**{rg.U + "erv_usd": 30.0, rg.U + "pv_usd_kwdc": 20.0})
    w = rg.wear(_lines("erv_broan_blp120", 1500.0, qty=12), p, 12)
    assert w["engineered"]["upkeep"] == pytest.approx(30.0)
    w = rg.wear(_lines("pv_kw", 3000.0, qty=6.0), p, 12)
    assert w["engineered"]["upkeep"] == pytest.approx(20.0 * 1.2 * 6.0 / 12)  # a kW AC is dc_ac kW DC


def test_the_sign_test_and_the_shares():
    s = {f"d life {w}{x}": {"p10": 5.0, "p50": 10.0, "p90": 20.0, "mean": 11.0}
         for w in rg.USUAL for x in ("", ", network dense", ", network base")}
    s["d life gas"] = {"p10": -5.0, "p50": 3.0, "p90": 8.0, "mean": 2.0}
    sg = rg.sign_test(s)
    assert sg["electric"]["holds"] and not sg["gas"]["holds"]
    mc = {f"d life {w}{x}": np.array([-1.0, 1.0, 2.0, 3.0]) for w in rg.USUAL for x in ("", ", network dense", ", network base")}
    mc.update({f"life {w}": np.array([10.0, 10.0, 10.0, 10.0]) for w in rg.USUAL})
    for x in ("life engineered", "life engineered, network dense", "life engineered, network base"):
        mc[x] = np.array([9.0, 11.0, 12.0, 13.0])
    sh = rg.shares(mc)
    assert sh["engineered cheaper"]["electric"]["alone"] == 0.25
    assert sh["cheapest"]["alone"]["engineered"] == 0.25 and sh["cheapest"]["alone"]["electric"] == 0.75  # ties go to the first


def test_the_draws_are_the_seeds():
    ps = {"a": Param("a", 1.0, 0.0, 2.0, "u", "low", "s"), "b": Param("b", 5.0, 5.0, 5.0, "u", "high", "s")}
    d1, d2 = draw(ps, 50, 7), draw(ps, 50, 7)
    assert np.array_equal(d1["a"], d2["a"]) and (d1["b"] == 5.0).all()
    assert not np.array_equal(draw(ps, 50, 8)["a"], d1["a"])


# ---- On the published model and the routes ----

@pytest.fixture(scope="module")
def made(P):
    from brownfield import baseline as bl, energy, pricing, routed, savings, systems

    if not bl.SERVICES.exists() or not (bl.RAW / "recs" / "recs2020_public_v7.csv").exists():
        pytest.skip("the services model isn't published, or RECS isn't downloaded")
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    r = bl.run(apt, P)
    pr = pricing.run(r, apt, P)
    en = energy.run(r, pr, apt, P)
    sv = savings.run(pr, en, P)
    fx = rg.prepare(r, apt, P)
    central, sp, hw = rg.evaluate(fx, P)
    return {"r": r, "pr": pr, "en": en, "sv": sv, "fx": fx, "central": central, "sp": sp, "hw": hw}


def test_at_the_centre_without_upkeep_10f_is_10b_10c_and_10e(made, P):
    worst = rg.parity(made["fx"], P, made["pr"], made["en"], made["sv"])
    assert max(worst.values()) < 1e-6


def test_the_years_add_up(made):
    c = made["central"]
    for w in WALKUPS:
        assert c[f"life {w}"] == pytest.approx(c[f"systems {w}"] + c[f"fee {w}"] + c[f"replace {w}"]
                                               + (c[f"energy {w}"] + c[f"upkeep {w}"]) * c["annuity"])
    for w in rg.USUAL:
        assert c[f"d life {w}"] == pytest.approx(c[f"d up {w}"] + c[f"d replace {w}"] + c[f"d year {w}"] * c["annuity"])
        assert c[f"d life {w}, network base"] - c[f"d life {w}"] == pytest.approx(c["network years base"])


def test_a_dearer_engineered_only_price_widens_the_difference_and_moves_no_usual_walk_up(made, P):
    k = "baseline.price.radiant_pex_0.5"
    q = dict(P, **{k: P[k] * 2})
    o, _, _ = rg.evaluate(made["fx"], q, made["sp"], made["hw"])
    c = made["central"]
    assert o["d life electric"] > c["d life electric"]
    assert all(o[f"life {w}"] == pytest.approx(c[f"life {w}"]) for w in rg.USUAL)


def test_the_draws_reproduce_whatever_the_workers(made, params):
    one = rg.monte_carlo(made["fx"], params, n=3, seed=5, workers=1)
    two = rg.monte_carlo(made["fx"], params, n=3, seed=5, workers=2)
    assert all(np.allclose(one[k], two[k], rtol=0, atol=1e-9) for k in one)
    other = rg.monte_carlo(made["fx"], params, n=3, seed=6, workers=1)
    assert not np.allclose(one["d life electric"], other["d life electric"])


def test_the_tornado_reruns_the_energy_only_for_what_it_reads(made, params, P):
    fx = made["fx"]
    reads = rg.energy_reads(fx, P)
    assert "baseline.energy.heat_set_f" in reads["space"] and "baseline.energy.occupants" in reads["hot_water"]
    assert "baseline.price.radiant_pex_0.5" not in reads["space"] | reads["hot_water"]
    some = {k: params[k] for k in ("baseline.energy.heat_set_f", "baseline.price.radiant_pex_0.5", "baseline.energy.occupants")}
    tor = rg.tornado(fx, some, P, ("d life electric",), made["sp"], made["hw"], reads)["d life electric"]
    got = {name: (lo, hi) for name, lo, hi in tor}
    for name in some:  # each end as a full run, the energy rerun, gives the same
        full = [rg.evaluate(fx, dict(P, **{name: x}))[0]["d life electric"] for x in (params[name].low, params[name].high)]
        assert got[name] == pytest.approx(tuple(full))
