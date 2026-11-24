"""Pass 3g step 10h (D28): the quality walk-up the towns would build (`brownfield.quality`), and the
feeders a designed walk-up sizes at its flats' load (`choices.feeder_sizes`). The synthetic tests
never skip; the run on the published model and the routes skips when they're absent."""
import numpy as np
import pytest

from brownfield import choices as ch
from brownfield import quality as qu
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def params():
    return load_params()


@pytest.fixture(scope="module")
def P(params):
    return values(params)


def test_the_quality_walkup_keeps_or_drops_each_of_10gs_choices_once():
    assert sorted(qu.KEPT + tuple(qu.DROPPED)) == sorted(ch.KEYS) and not set(qu.KEPT) & set(qu.DROPPED)
    assert set(qu.DROPPED) == {"radiant", "plant", "pv", "prv"} and ch.FEE in qu.QUALITY
    assert ch.config(qu.QUALITY) == {"case": "engineered", "heat": "hp", "hw": "electric", "pv": False}
    assert ch.flat_kind(qu.QUALITY) == qu.QUALITY_FLAT and ch.flat_kind(ch.FULL) == ch.ENGINEERED_FLAT
    assert ch.flat_kind(ch.NONE) == qu.USUAL_FLATS["electric"] and ch.flat_kind(ch.NONE, "central") == qu.USUAL_FLATS["central"]


def test_the_quality_flat_carries_more_than_either_walkups(P):
    ld = {k: ch.flat_load(P, 900.0, k)[0]["calculated_va"] for k in (qu.QUALITY_FLAT, ch.ENGINEERED_FLAT, qu.USUAL_FLATS["electric"])}
    assert ld[qu.QUALITY_FLAT] > ld[qu.USUAL_FLATS["electric"]] > ld[ch.ENGINEERED_FLAT]
    # the floors' manifold rides on the ERV's circuit: without the floors, the flat carries less
    assert ch.flat_load(P, 900.0, (True, False, False))[0]["calculated_va"] < ld[ch.ENGINEERED_FLAT]


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
    fx = ch.prepare(r, apt, P)
    central, sp, hw = qu.evaluate(fx, P)
    return {"r": r, "pr": pr, "fx": fx, "central": central, "sp": sp, "hw": hw}


def test_the_walkups_are_10fs_and_the_lines_add_up(made, P):
    from brownfield import ranges

    c = made["central"]
    ten, _, _ = ranges.evaluate(made["fx"], P, made["sp"], made["hw"])
    for k in ("life engineered", "life electric", "life central"):
        assert c[k] == pytest.approx(ten[k], abs=1e-6)
    assert sum(c[f"d life {k}"] for k in qu.LINES) + c["d life q interaction"] == pytest.approx(c["d life quality"])
    assert c["d life quality"] + c["d life engineered over quality"] == pytest.approx(c["d life whole"])
    for k in ("quality", "dc on quality") + qu.LINES:
        k = k.removeprefix("d life ")
        assert c[f"d life {k}"] == pytest.approx(c[f"d up {k}"] + c[f"d replace {k}"] + c[f"d year {k}"] * c["annuity"])


def test_the_choices_without_energy_cost_what_they_cost_in_10g(made, P):
    g, _, _ = ch.evaluate(made["fx"], P, made["sp"], made["hw"])
    c = made["central"]
    for k in ("cast iron", "services", "submeters", "held off", "cold insulation"):
        assert c[f"d life q out {k}"] == pytest.approx(g[f"d life out {k}"], abs=1e-6)
    assert c["d life q out engineering"] - c["feeders quality"] == pytest.approx(g["d life out engineering"], abs=1e-6)


def test_a_dearer_erv_moves_the_quality_walkup_not_the_water_added_to_it(made, P):
    k = "baseline.price.erv_broan_blp120"
    o, _, _ = qu.evaluate(made["fx"], dict(P, **{k: P[k] * 2}), made["sp"], made["hw"])
    c = made["central"]
    rise = o["d life quality"] - c["d life quality"]
    assert rise > 0 and o["d life q out erv"] - c["d life q out erv"] == pytest.approx(rise)
    assert o["d life dc on quality"] == pytest.approx(c["d life dc on quality"])


def test_priced_heat_leaves_the_quality_walkup_and_dearens_the_water(made, P):
    """The quality walk-up takes none of the data center's heat; priced, the water it would add costs it."""
    o, _, _ = qu.evaluate(made["fx"], dict(P, **{"baseline.energy.heat_usd_mwh": 100.0}), made["sp"], made["hw"])
    c = made["central"]
    assert o["d life quality"] == pytest.approx(c["d life quality"])
    assert o["d life dc on quality"] > c["d life dc on quality"]


def test_the_feeders_at_the_engineered_load_are_step_7s_and_the_quality_flats_upsize_some(made, P):
    fs = made["fx"]["feeders"]
    assert all(v["to"] == v["from"] and v["breaker_a"] == v["from_breaker_a"] for v in fs[ch.ENGINEERED_FLAT].values())
    up = [v for v in fs[qu.QUALITY_FLAT].values() if v["to"] != v["from"]]
    assert up and all(v["to"] in ch.FEEDER_CLASS for v in up)
    walkup, *_ = ch.walkups(made["fx"], P, made["sp"], made["hw"])
    # designed walk-ups with the flats' own heaters: the quality walk-up, and 10g's design without its plant
    assert made["central"]["feeders quality"] > 0 and walkup(ch.FULL - {"plant"})["feeders"] > 0


def test_undesigned_walkups_keep_the_engineered_feeders(made, P):
    """Without the fee nothing holds the design's 2%: the usual walk-ups, and the quality walk-up
    without its design, take the engineered design's feeders as they are."""
    walkup, *_ = ch.walkups(made["fx"], P, made["sp"], made["hw"])
    assert walkup(ch.NONE)["feeders"] == 0.0 and walkup(ch.NONE, "central")["feeders"] == 0.0
    assert walkup(qu.QUALITY - {ch.FEE})["feeders"] == 0.0 and walkup(qu.QUALITY)["feeders"] > 0.0
    assert walkup(ch.FULL)["feeders"] == 0.0  # the engineered flats' own load: step 7's feeders


def test_a_bigger_water_heater_breaks_the_wiring_check(made, P):
    """Broken on purpose: at 6 kW the quality flat outgrows its 100 A breaker, and the check says so."""
    q = dict(P, **{"baseline.usual.heater_va": 6000.0})
    big = ch.feeder_sizes(made["fx"]["apt"], q, made["fx"]["s7"], qu.QUALITY_FLAT)
    assert any(v["breaker_a"] > v["from_breaker_a"] for v in big.values())
    fx = dict(made["fx"], feeders={**made["fx"]["feeders"], qu.QUALITY_FLAT: big})
    wr = qu.wiring(made["r"], fx, P, 0.03)
    assert not all(x["breaker_a"] == x["from_breaker_a"] for x in wr["feeders"].values())


def test_the_grounds_short_of_250_122_b(made):
    """The engineered design's feeders upsized for the drop (2 AWG where 3 carries the load) keep the
    breaker's 8 AWG ground; 250.122(B) wants 6."""
    gr = qu.grounds(made["fx"])
    eng = {x["flat"]: x for x in gr["engineered"]}
    two = [n for n, v in made["fx"]["feeders"][ch.ENGINEERED_FLAT].items() if v["to"] == "2"]
    assert sorted(eng) == sorted(two) and all(x["egc"] == "8" and x["needs"] == "6" for x in eng.values())
    assert len(gr["quality"]) > len(gr["engineered"])


def test_the_draws_reproduce_whatever_the_workers(made, params):
    from brownfield import ranges

    one = ranges.monte_carlo(made["fx"], params, n=2, seed=5, workers=1, fn=qu.evaluate)
    two = ranges.monte_carlo(made["fx"], params, n=2, seed=5, workers=2, fn=qu.evaluate)
    assert all(np.allclose(one[k], two[k], rtol=0, atol=1e-9) for k in one)
