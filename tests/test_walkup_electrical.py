"""Pass 3g step 5 (D28): electrical designed (`brownfield.electrical`)."""
import pytest

from brownfield import electrical as el
from brownfield import systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


@pytest.fixture(scope="module")
def S(apt, P):
    return el.summary(apt, P)


def _failing(apt, p):
    return [label for label, ok, _ in el.summary(apt, p)["checks"] if not ok]


def test_point_to_point_reproduces_bussmanns_examples():
    # Eaton Bussmann's SPD handbook, 'Short Circuit Current Calculations': 300 kVA, 2 %Z, 208 V, an
    # infinite primary (46,273 A), then 20 ft of 2 x 500 kcmil Cu in steel (39,425 A), then 20 ft
    # of 2 AWG (18,687 A; the handbook rounds f and M: 18,670 unrounded); and 75 kVA, 1.4 %Z,
    # 120/240 V (22,322 A), 25 ft of 500 kcmil line to line (18,453 A).
    b = el.bussmann_examples({})
    for got, want in zip(b["3ph"] + b["1ph"], (46273, 39425, 18687, 22322, 18453)):
        assert got == pytest.approx(want, rel=0.003)


def test_220_82_reproduces_holts_house(P):
    from brownfield.loads import nec_220_82

    # Holt, EC&M 2020-04-17: 1,500 ft2, the appliances, 220.82(C) = 6,720 + 65% of 7 kW.
    r = nec_220_82(1500, [1200, 900, 6000, 3000, 4000, 4500], 6720 + 0.65 * 7000, P)
    assert r["connected_less_hvac_va"] == pytest.approx(28600)
    assert r["calculated_va"] == pytest.approx(28710)
    assert r["amps_240"] == pytest.approx(119.6, abs=0.05)


def test_the_phasor_drop_is_the_closed_form_and_the_208_neutral_carries_current():
    # A 2-wire 120 V load: 2 K I L / CM exactly (12 AWG, Table 8, 16 A, 100 ft).
    d = el.feeder_drop(complex(1.98, 0.0), 100.0, 0.0, 16 * 120.0, 0.0, 1.0, "120/240")
    assert d["an"] * 120 == pytest.approx(2 * 16 * 100 * 1.98 / 1000, rel=1e-12)
    # Balanced 120 V loads on a 120/240 feeder: no neutral current. On two phases of a 208Y/120
    # wye: the neutral carries as much as either phase, and the 120 V loads lose more voltage.
    z = complex(0.25, 0.047)
    split = el.feeder_drop(z, 100.0, 0.0, 4800.0, 4800.0, 1.0, "120/240")
    wye = el.feeder_drop(z, 100.0, 0.0, 4800.0, 4800.0, 1.0, "120/208")
    assert split["in"] == pytest.approx(0.0, abs=1e-9)
    assert wye["in"] == pytest.approx(wye["ia"], rel=1e-9) and wye["an"] > split["an"]


def test_every_step_5_check_passes(S):
    assert [label for label, ok, _ in S["checks"] if not ok] == []


def test_a_flat_missing_a_required_circuit_is_caught(apt, P, monkeypatch):
    real = el.flat_circuits
    monkeypatch.setattr(el, "flat_circuits", lambda a, p, n, *k: [c for c in real(a, p, n, *k) if c["key"] != "bath"])
    assert any("210.11(C)" in label for label in _failing(apt, P))


def test_the_500_w_preheater_would_fall_short_at_the_design_hour(apt, P):
    # Ouellet's 500 W model gives 470 W after a 3% drop against the design hour's 482 W.
    assert any("preheater" in label for label in _failing(apt, dict(P, **{"systems.electrical.preheater_va": 500.0})))


def test_a_longer_feeder_gets_bigger_copper_and_stays_within_its_drop(apt, P):
    long = dict(P, **{"systems.wiring.route_slack": 2.0})
    base, more = el.feeders(apt, P), el.feeders(apt, long)
    n = "3-front-left"
    assert el.SIZES.index(more[n]["size"]) > el.SIZES.index(base[n]["size"])
    assert max(more[n]["drop"]["an"], more[n]["drop"]["bn"], more[n]["drop"]["ll"]) <= P["systems.wiring.vd_feeder_max"] + 1e-12


def test_the_main_is_the_least_the_stack_offers(apt, P):
    s = el.service(apt, P)
    # 413 A: no main between 400 and 600 A, and the 600 A main's lugs take 500 kcmil at most, so two sets.
    assert 400 < s["amps"] < 600 and s["main_a"] == 600 and s["sets"] == 2
    assert s["sets"] * el.ampacity(s["size"], "cu", 75) >= s["amps"]
    small = dict(P, **{"systems.electrical.range_va": 6000.0})
    t = el.service(apt, small)
    assert t["amps"] < 400 and t["main_a"] == 400 and t["sets"] == 1


def test_the_checks_catch_a_low_meter_and_a_weak_panel(apt, P):
    assert any("FirstEnergy's heights" in x for x in _failing(apt, dict(P, **{"systems.meter_stack.bottom_socket_mid_in": 24.0})))
    assert any("flat's panel within" in x for x in _failing(apt, dict(P, **{"systems.flat_panel.breaker_kaic": 4.0})))


def test_the_roof_array_is_what_the_pathways_leave(apt, P, S):
    from brownfield.plumbing import stacks

    pv = S["design"]["pv"]
    zones = 12 * P["systems.pv.unit_zone_ft2"] + len(stacks(apt)) * P["systems.pv.vent_zone_ft2"] + P["systems.pv.hatch_zone_ft2"]
    assert pv["usable_ft2"] == pytest.approx(pv["inside_ft2"] - zones)
    assert pv["modules"] * P["systems.pv.module_ft2"] <= pv["usable_ft2"] * P["systems.pv.gcr"]
    assert 1000 < pv["kwh_per_kwp"] < 1400  # western Pennsylvania, 10 degrees south (PVGIS)
