"""Pass 3g step 8 (D28): Addendum 6's design changes, the fire service's shutoff valves and the
swing tank's element in the house load (`fire.valves_psi`, `electrical.house_loads`)."""
import pytest

from brownfield import electrical, fire, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


def test_the_two_shutoff_valves_are_a_foot_of_steel_pipe_each(P):
    # By hand: NFPA 13's chart gives a 2 in. gate valve 1 ft of Schedule 40 steel (2.067 in., C 120);
    # Hazen-Williams for two of them at 56 gpm.
    q = 56.0
    by_hand = 2 * 1.0 * 4.52 * q ** 1.85 / (120 ** 1.85 * 2.067 ** 4.87)
    assert fire.valves_psi(q, "2", P) == pytest.approx(by_hand, rel=1e-12)
    assert 0.06 < by_hand < 0.07
    # The chart's figure is a 2 in. valve's: another size is refused, not guessed.
    with pytest.raises(ValueError):
        fire.valves_psi(q, "3", P)


def test_the_supply_counts_the_valves_in_what_the_street_must_give(P):
    run = {"main_ft": 40.0}
    s = fire.supply(P, 55.0, 20.0, 9.0, run, fire.SIZE_START)
    parts = 20.0 + s["riser_main_psi"] + s["underground_psi"] + s["backflow_psi"] + s["valves_psi"] + s["elevation_psi"]
    assert s["need_psi"] == pytest.approx(parts)
    assert s["valves_psi"] == pytest.approx(fire.valves_psi(55.0, fire.SIZE_START["backflow"], P))


def test_the_swing_element_is_its_nameplate_and_continuous_by_its_hours(apt, P):
    # Addendum 6 took the element's nameplate (then 2.0 kW); Addendum 7's flats' loops raised it.
    h = electrical.house_loads(apt, P)
    row = next(r for r in h["rows"] if r["key"] == "swing_element")
    va = P["systems.house.swing_element_va"]
    assert row["va"] == va
    # Its design day's heat takes it more than 3 h: continuous, at 125%.
    assert h["element_h"] >= P["systems.house.continuous_h"]
    assert row["kind"] == "continuous" and row["calc_va"] == pytest.approx(va * P["systems.house.continuous_factor"])
    assert h["breaker_a"] >= h["amps"]
    # Were the rule 10 h, the same element would count at 100%, and the house load fall by its 25%.
    assert h["element_h"] < 10
    q = dict(P, **{"systems.house.continuous_h": 10.0})
    h10 = electrical.house_loads(apt, q)
    row10 = next(r for r in h10["rows"] if r["key"] == "swing_element")
    assert row10["kind"] == "noncontinuous" and row10["calc_va"] == va
    assert h["calculated_va"] - h10["calculated_va"] == pytest.approx(va * (P["systems.house.continuous_factor"] - 1))


def test_addendum_6_changes_no_model(P):
    # It's drawn on Addendum 5's models, the latest; it has no model of its own.
    assert systems.latest_model().name == "apartment-addendum-5.json"
    assert 6 in systems.TITLES
