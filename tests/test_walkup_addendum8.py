"""Addendum 8 (found scoping pass 3g step 10, D28): E-1, the air-leakage tests, held to the leakage the
heat loads take (`acceptance.leakage`, `leakage_checks`, `loads.enclosure`), and why
(`systems.leaky_heat`)."""
import copy

import pytest

from brownfield import acceptance as ac, loads, servicesheets, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


def _e1(apt, P):
    lk = ac.leakage(apt, P)
    return [{"id": "E-1", "limits": {k: lk[k] for k in ("rate_cfm50_ft2", "area_ft2", "building_cfm50", "flat_cfm50_ft2")}}]


def test_the_test_holds_the_building_to_the_loads_leakage(apt, P):
    its = _e1(apt, P)
    assert all(ok for _, ok, _ in ac.leakage_checks(apt, P, its))
    lk = its[0]["limits"]
    assert lk["rate_cfm50_ft2"] == P["systems.phius.airtight_cfm50_ft2"] == 0.06
    assert lk["building_cfm50"] == pytest.approx(0.06 * lk["area_ft2"])


def test_addendum_7s_test_against_the_loads_is_caught(apt, P):
    # The loads at the code's 3.0 ACH50, which Addendum 7's E-1 passed: the test and the loads part.
    case = loads.design_case(apt, P, preheat=True)
    leaky = copy.deepcopy(case)
    for f in apt["flats"]:
        leaky["flats"][f["name"]]["infil_m3h"] = 3.0 / P["pass3.air.n_factor"] * f["interior_volume_m3"]
    first = ac.leakage_checks(apt, P, _e1(apt, P), case=leaky)[0]
    assert not first[1]
    # And a limit stated off the enclosure's.
    its = _e1(apt, P)
    its[0]["limits"]["building_cfm50"] *= 2
    assert not ac.leakage_checks(apt, P, its)[0][1]


def test_the_enclosure_adds_up_and_a_flat_off_it_is_caught(apt, P):
    e = loads.enclosure(apt)
    assert e["parts_main_m2"] == pytest.approx(e["main_m2"], rel=1e-9)
    # The annex is inside the envelope (Addendum 2): its walls, roof and floor add, the wall behind it goes.
    assert e["gross_m2"] == pytest.approx(e["main_m2"] + e["annex_m2"] - e["covered_m2"])
    bad = copy.deepcopy(apt)
    bad["flats"][0]["wall_gross_m2"] += 5.0
    second = ac.leakage_checks(bad, P, _e1(bad, P))[1]
    assert not second[1]


def test_the_old_test_would_pass_a_building_its_loop_isnt_sized_for(apt, P):
    h = systems.leaky_heat(apt, P)
    lo, hi = h["ach50"]
    assert 0.2 < lo <= hi < 1.0  # the loads' flats: well under the code's 3.0
    assert h["leaky_kw"] > 1.1 * h["design_kw"] and h["leaky_water_c"] > h["water_c"]


def test_g002_is_reissued_alone_by_addendum_8():
    rev, name = servicesheets.REVISED["G-002"]
    assert rev == "Addendum 8" and name == "services-sheet-g-002-addendum-8.pdf"
    assert set(servicesheets.REVISED) <= {n for n, _ in servicesheets.sheet_list()}
