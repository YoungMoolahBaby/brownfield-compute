"""Pass 3g step 9b (D28): the control sequence (`brownfield.sequence`)."""
import pytest

from brownfield import routed, sequence as sq, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def test_the_reset_runs_from_the_room_to_the_design_supply(P):
    sup = 40.2
    td, t_in = P["systems.design.heating_c"], P["pass3.loads.indoor_c"]
    assert sq.reset_c(P, td, sup) == pytest.approx(sup)
    assert sq.reset_c(P, t_in, sup) == pytest.approx(t_in)
    mid = (td + t_in) / 2
    assert sq.reset_c(P, mid, sup) == pytest.approx((sup + t_in) / 2)  # a straight line
    assert sq.reset_c(P, 30.0, sup) == pytest.approx(t_in)  # never under the room


@pytest.fixture(scope="module")
def made(P):
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    s7 = routed.summary(apt, P, routes)
    return s7, sq.sequence(P, s7)


def test_the_sequences_checks_pass(made, P):
    s7, _ = made
    assert [label for label, ok, _ in sq.checks(P, s7) if not ok] == []


def test_the_plant_hands_over_between_its_heaters_one_at_a_time(made):
    _, seq = made
    plant = next(s for s in seq if s["system"].startswith("The hot-water plant"))
    fb = next(m for m in plant["modes"] if m["mode"].startswith("Fallback"))
    text = " ".join(fb["steps"])
    # Into the fallback: HP-1 locked out before BK-1 released; out of it: BK-1 locked out first.
    assert text.index("HP-1 stops and is locked out") < text.index("BK-1's contactor is released")
    assert text.index("BK-1 locked out first") < text.index("then HP-1 enabled")
    assert any("BK-1" in a and "HP-1" in a for a, _ in sq.INTERLOCKS)


def test_the_written_sequence_names_every_point_and_interlock(made):
    _, seq = made
    md = sq.markdown(seq)
    for tag, _, _ in sq.POINTS:
        assert f"| {tag} |" in md
    for a, _ in sq.INTERLOCKS:
        assert a in md
    assert "{" not in md and "}" not in md
