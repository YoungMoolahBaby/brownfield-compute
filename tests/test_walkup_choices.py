"""Pass 3g step 10g (D28): which of the design's choices pay their way (`brownfield.choices`). The
synthetic tests never skip; the run on the published model and the routes skips when they're absent."""
import numpy as np
import pytest

from brownfield import choices as ch
from brownfield import energy
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def params():
    return load_params()


@pytest.fixture(scope="module")
def P(params):
    return values(params)


def test_the_whole_design_and_none_of_it_are_10cs_walkups():
    assert ch.config(ch.FULL) == energy.CONFIGS["engineered"]
    assert ch.config(ch.NONE) == energy.CONFIGS["electric"]
    assert ch.config(ch.NONE, "central") == energy.CONFIGS["central"]
    assert {ch.config(frozenset(x))["case"] for x in ((), ("erv",), ("tight",), ("erv", "tight"))} == set(ch.CASES)
    assert ch.config(ch.FULL - {"plant"}, "central")["hw"] == "central" and ch.config(ch.FULL - {"radiant"})["heat"] == "hp"


def test_a_purpose_takes_the_lines_of_the_walkup_that_has_it():
    plant = "hot water: the plant and the loops, or each flat's heater"
    assert ch.source(plant, ch.FULL) == "engineered"
    assert ch.source(plant, ch.FULL - {"plant"}) == "electric"
    assert ch.source(plant, ch.FULL - {"plant"}, "central") == "central" and ch.source(ch.GAS, ch.FULL - {"plant"}, "central") == "central"
    assert ch.source(ch.GAS, ch.FULL, "central") == "electric"  # the plant kept: no gas
    assert ch.source("every walk-up's alike", ch.FULL) == "electric"
    # the main: the central walk-up's 400 A only without the plant and the ERVs (their preheaters keep 600 A)
    assert ch.source(ch.MAIN, ch.FULL - {"plant"}, "central") == "electric"
    assert ch.source(ch.MAIN, ch.NONE, "central") == "central"


def test_every_choice_owns_one_purpose_and_the_fee_is_apart():
    assert len(ch.OWNER) == len(ch.CHOICES) == len(set(ch.KEYS))
    assert set(ch.ENERGY) <= set(ch.KEYS) and set(ch.ADDED) <= set(ch.ENERGY) and ch.FEE not in ch.KEYS


def test_the_share_of_draws_in_which_a_line_pays():
    mc = {"d life out x": np.array([-1.0, 2.0, 3.0, -4.0]), "d life whole": np.ones(4), "life engineered": -np.ones(4)}
    assert ch.pays(mc) == {"out x": 0.5, "whole": 0.0}


# ---- On the published model and the routes ----

@pytest.fixture(scope="module")
def made(P):
    from brownfield import baseline as bl, pricing, ranges, routed, systems

    if not bl.SERVICES.exists() or not (bl.RAW / "recs" / "recs2020_public_v7.csv").exists():
        pytest.skip("the services model isn't published, or RECS isn't downloaded")
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    r = bl.run(apt, P)
    pr = pricing.run(r, apt, P)
    fx = ch.prepare(r, apt, P)
    central, sp, hw = ch.evaluate(fx, P)
    return {"r": r, "pr": pr, "fx": fx, "central": central, "sp": sp, "hw": hw}


def test_the_whole_is_10fs_and_the_lines_add_up_to_it(made, P):
    from brownfield import ranges

    c = made["central"]
    ten, _, _ = ranges.evaluate(made["fx"], P, made["sp"], made["hw"])
    for k in ("life engineered", "life electric", "life central"):
        assert c[k] == pytest.approx(ten[k], abs=1e-6)
    assert c["d life whole"] == pytest.approx(ten["d life electric"], abs=1e-6)
    assert sum(c[f"d life out {k}"] for k in ch.KEYS + (ch.FEE,)) + c["d life interaction"] == pytest.approx(c["d life whole"])
    for k in ch.KEYS + ("whole",):
        assert c[f"d life out {k}" if k != "whole" else "d life whole"] == pytest.approx(
            c[f"d up out {k}" if k != "whole" else "d up whole"] + c[f"d replace out {k}" if k != "whole" else "d replace whole"]
            + c[f"d year out {k}" if k != "whole" else "d year whole"] * c["annuity"])


def test_every_line_belongs_to_a_choice_or_is_alike(made):
    from brownfield import pricing

    for why, v in pricing.by_purpose(made["pr"]).items():
        assert why in ch.OWNER or v["engineered"] == pytest.approx(v["electric"]), why


def test_a_choice_without_energy_is_its_own_cost_taken_out_or_added(made):
    c = made["central"]
    for k in ("cast iron", "submeters", "held off", "prv", "cold insulation"):
        assert c[f"d year out {k}"] == 0.0 and c[f"d kwh out {k}"] == 0.0
        assert c[f"d life out {k}"] == pytest.approx(c[f"d up out {k}"] + c[f"d replace out {k}"])


def test_a_dearer_price_moves_only_its_choice(made, P):
    k = "baseline.price.radiant_pex_0.5"
    o, _, _ = ch.evaluate(made["fx"], dict(P, **{k: P[k] * 2}), made["sp"], made["hw"])
    c = made["central"]
    assert o["d life out radiant"] > c["d life out radiant"] and o["d life whole"] > c["d life whole"]
    for x in ("cast iron", "erv", "plant", "pv", "tight"):
        assert o[f"d life out {x}"] == pytest.approx(c[f"d life out {x}"])


def test_with_the_heat_priced_the_erv_and_the_airtightness_save_it(made, P):
    """The interaction: with the floors on the data center's water, the heat the ERVs and the
    airtightness save is free; priced, taking either out costs it."""
    q = dict(P, **{"baseline.energy.heat_usd_mwh": 100.0})
    o, _, _ = ch.evaluate(made["fx"], q, made["sp"], made["hw"])
    c = made["central"]
    assert o["d life out erv"] < c["d life out erv"] and o["d life out tight"] < c["d life out tight"]
    assert o["d life out radiant"] > c["d life out radiant"]  # the floors now buy the heat they bring
    assert o["d life in erv"] == pytest.approx(c["d life in erv"])  # the usual walk-up takes none


def test_the_fourth_case_lies_between(made):
    s = {k: v["building"]["heat_kwh"] for k, v in made["sp"].items()}
    assert s["usual"] > s["usual at Phius's leakage"] > s["engineered"]
    assert s["usual"] > s["engineered at the code's leakage"] > s["engineered"]


def test_the_plant_against_gas_keeps_the_600_a_main(made):
    m = ch.main_check(made["r"])
    assert m["central_a"] < m["amps"] and m["main_a"] == m["engineered_a"]


def test_the_draws_reproduce_whatever_the_workers(made, params):
    from brownfield import ranges

    one = ranges.monte_carlo(made["fx"], params, n=2, seed=5, workers=1, fn=ch.evaluate)
    two = ranges.monte_carlo(made["fx"], params, n=2, seed=5, workers=2, fn=ch.evaluate)
    assert all(np.allclose(one[k], two[k], rtol=0, atol=1e-9) for k in one)
