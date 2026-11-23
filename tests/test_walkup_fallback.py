"""Pass 3g step 9a (D28): when the data center's heat is gone (`brownfield.fallback`) and what it
does to the wiring (`electrical.hvac_va`, `electrical.house_loads`)."""
import pytest

from brownfield import electrical, fallback as fb, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


def test_the_backup_heaters_recovery_is_the_makers():
    # A. O. Smith AOSCE15300 p. 3, 12.3 kW: 50 gal/h at a 100 F rise, 101 at 50 F, 168 at 30 F.
    for rise, gph in ((100, 50), (50, 101), (30, 168)):
        assert fb.recovery_gph(12300, rise) == pytest.approx(gph, abs=0.6)


def test_fujitsus_heating_table_reads_back_and_goes_no_further():
    assert fb.capacity_at(-15.0) == pytest.approx((4.54, 2.25))
    assert fb.capacity_at(-20.6) == pytest.approx((4.09, 2.20))
    cap, _ = fb.capacity_at(-16.3)  # the heating design dry bulb, between its rows
    assert 4.09 < cap < 4.54 and cap == pytest.approx(4.54 - (4.54 - 4.09) * 1.3 / 5.6)
    with pytest.raises(ValueError):
        fb.capacity_at(-25.0)


def test_the_pipe_factor_is_fujitsus_and_never_a_blank_cell():
    assert fb.pipe_factor(15, -7.5) == pytest.approx(0.926)
    assert fb.pipe_factor(10, 0) == pytest.approx(0.981)
    assert fb.pipe_factor(12.5, -7.5) == pytest.approx((0.974 + 0.926) / 2)
    assert fb.pipe_factor(15, -6.25) == pytest.approx((0.928 + 0.926) / 2)
    with pytest.raises(ValueError):
        fb.pipe_factor(6, -10)  # the manual gives nothing under 10 m at 10 m of height
    with pytest.raises(ValueError):
        fb.pipe_factor(15, 5)  # the indoor unit above: not this building


def test_a_flats_heating_is_its_heat_pump_and_its_preheater(P):
    e = "systems.electrical."
    h82 = electrical.hvac_va(P, P[e + "heat_demand_220_82"])
    assert h82 == pytest.approx(P[e + "cooling_va"] + P[e + "heat_demand_220_82"] * P[e + "preheater_va"])
    assert h82 > P[e + "cooling_va"]  # step 5 had taken the cooling alone


def test_the_backup_heater_and_the_heat_pump_count_once(apt, P):
    h = electrical.house_loads(apt, P)
    rows = {r["key"]: r for r in h["rows"]}
    assert rows["backup_heater"]["counted"] and not rows["dhw_heat_pump"]["counted"]
    assert rows["dhw_heat_pump"]["calc_va"] == 0 and rows["backup_heater"]["calc_va"] == pytest.approx(12300 * 1.25)
    # A backup smaller than the heat pump: the heat pump counts, with its share of the largest motor.
    small = electrical.house_loads(apt, dict(P, **{"systems.hot_water.backup_w": 1000.0}))
    rs = {r["key"]: r for r in small["rows"]}
    assert rs["dhw_heat_pump"]["counted"] and not rs["backup_heater"]["counted"]
    assert rs["dhw_heat_pump"]["calc_va"] == pytest.approx(rs["dhw_heat_pump"]["va"] * (1 + P["systems.house.largest_motor_extra"]))
