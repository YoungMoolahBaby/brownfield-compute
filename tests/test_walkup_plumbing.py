"""Pass 3g step 4 (D28): plumbing designed (`brownfield.plumbing`)."""
import numpy as np
import pytest

from brownfield import plumbing, systems
from brownfield.params import load_params, values


def test_ecosizer_reproduces_its_engines_regression():
    # EcosizerEngine's test_ecosizer_engine_regression.py, 'primary_no_recirc': 100 people at 25 gal
    # a day, 120 F supply, 150 F storage, 55 F inlet, the engine's defaults; expected 84.84058984375
    # kBtu/h and 567.7208360311284 gal (to 1e-6).
    r = plumbing.ecosizer_primary(100 * 25, plumbing.load_shape(), 120.0, 150.0, 55.0)
    assert r["capacity_kbtuh"] == pytest.approx(84.84058984375, rel=1e-6)
    assert r["storage_gal"] == pytest.approx(567.7208360311284, rel=1e-6)
    # 'parallel_loop': a 5 gpm loop returning at 110 F; expected 187.5 gal and 43.85605875 kBtu/h.
    loss = plumbing.recirc_loss_btuh(5.0, 120.0, 110.0)
    tm = plumbing.ecosizer_parallel_tm(loss, 120.0, 128.0)
    assert tm["volume_gal"] == pytest.approx(187.5, rel=1e-6)
    assert tm["capacity_kbtuh"] == pytest.approx(43.85605875, rel=1e-6)


def test_the_load_shape_is_a_day():
    s = plumbing.load_shape()
    assert len(s) == 24 and s.sum() == pytest.approx(1.0, abs=1e-6)


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


def test_appendix_e_sample_problem():
    # IPC Appendix E, E103.3.1: 55 psi at the main less 15 (a flushometer), 11 (the meter), 1.61 (the 2 in.
    # tap at the table's 120 gpm row), 21 ft x 0.43 and 9 (the backflow preventer) leaves 9.36 psi.
    b = plumbing.pressure_budget(55.0, {"B": 15.0, "C": 11.0, "D": plumbing.tap_loss_psi(120, 2), "E": 21 * 0.43, "F": 9.0})
    assert b["total_psi"] == pytest.approx(45.64) and b["friction_psi"] == pytest.approx(9.36)


def test_pipe_heat_loss_against_naima(P):
    # NAIMA CI226 Table 3: 3/4 in. Type M copper at 140 F in 75 F air, elastomeric insulation (k 0.28).
    assert plumbing.pipe_loss_btuh_ft(0.875, 0.0, 140, 75, P) == pytest.approx(29.64, rel=0.001)
    for t, v in plumbing.NAIMA_3_4_TYPE_M.items():
        q = plumbing.pipe_loss_btuh_ft(0.875, t, 140, 75, P)
        assert v <= q <= v * 1.05, (t, v, q)


def test_mains_correlation_keeps_its_form():
    # Unfloored, its year averages the air's mean plus EnergyPlus's 6 F, and swings by ratio x the
    # spread of the monthly means.
    t = plumbing.mains_correlation_f(50.0, 40.0, np.arange(1, 366))
    assert t.mean() == pytest.approx(56.0, abs=0.05)
    assert (t.max() - t.min()) / 2 == pytest.approx((0.4 + 0.01 * 6) * 20, rel=0.01)


def test_every_step_4_check_passes(apt, P):
    s = plumbing.summary(apt, P)
    assert [label for label, ok, _ in s["checks"] if not ok] == []


def test_the_street_pressure_it_needs(apt, P):
    # Under the pressure the design states it needs, the shower would starve: the check turns false.
    d = plumbing.design(apt, P)
    assert d["street_ok"] and d["street_need_psi"] < P["systems.plumbing.street_psi"]
    low = dict(P, **{"systems.plumbing.street_psi": d["street_need_psi"] - 1})
    assert not plumbing.design(apt, low)["street_ok"]


def test_pvc_stacks_would_leave_nothing(apt, P):
    n = plumbing.noise(apt, P)
    assert n["margin_db"]["cast_iron"] > 0 >= n["margin_db"]["pvc"]
    assert n["wet_walls_only"]


def test_vent_table():
    assert plumbing.stack_vent_in(27, 11.0) == 1.5
    assert plumbing.stack_vent_in(27, 40.0) == 2.0  # past 1-1/2 in.'s 27 ft at 53 dfu
    assert plumbing.stack_vent_in(27, 500.0) == 3.0
