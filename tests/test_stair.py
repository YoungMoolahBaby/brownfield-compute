"""Pass 3f step 8 (D27): the walk-up's stair, halls and flat doors (forge `stair`, under `stair` in
out/pass3/apartment.json), checked against IBC 2018 by `brownfield.stair`. Every check passes on the
model. The tests below break the model in ways a check must catch: the review's cases (a column
on a tread, a low hall floor, a handrail across a door) and others."""
import copy
from collections import Counter

import numpy as np
import pytest

from brownfield import house, stair
from brownfield.params import load_params

IN = 0.0254


@pytest.fixture(scope="module")
def apt():
    return house.apartment()


@pytest.fixture(scope="module")
def params():
    return load_params()


def _failing(apt, params):
    return [label for label, ok, _ in stair.check(apt, params) if not ok]


def _part(apt, pid):
    return next(p for p in apt["stair"]["parts"] if p["id"] == pid)


def test_the_layout(apt):
    st = apt["stair"]
    # Two flights a storey between levels 1-3: 6 risers of 6 in up to the landing at the back
    # windows' sill, 12 of 7 in on to the next floor.
    assert [(f["id"], f["risers"], round(f["riser_m"] / IN, 4)) for f in st["flights"]] == [
        ("flight-1a", 6, 6.0), ("flight-1b", 12, 7.0), ("flight-2a", 6, 6.0), ("flight-2b", 12, 7.0)]
    # One door into every flat, from the stair; the existing openings untouched.
    assert sorted(d["flat"] for d in st["doors"]) == sorted(f["name"] for f in apt["flats"])
    assert len(apt["openings"]) == 114
    assert Counter(p["kind"] for p in st["parts"]) == {"step": 32, "landing": 2, "floor": 4, "stair_partition": 4, "guard": 1}


def test_every_check_passes(apt, params):
    res = stair.check(apt, params)
    assert len(res) == 17
    assert _failing(apt, params) == []


def test_headroom_known_values(apt):
    f1a, f1b = apt["stair"]["flights"][:2]
    # Over flight 1a: the level-2 hall floor's underside (120 - 12 in) above its first nosing (6 in).
    assert stair.headroom(apt, f1a)[0] == pytest.approx((108 - 6) * IN, abs=1e-5)
    # Over flight 1b: landing 2's underside (120 + 36 - 12 in) above its first nosing (36 + 7 in).
    assert stair.headroom(apt, f1b)[0] == pytest.approx((144 - 43) * IN, abs=1e-5)


def test_a_column_on_a_tread_fails_headroom(apt, params):
    broken = copy.deepcopy(apt)
    s = _part(broken, "flight-1b-5")
    broken["stair"]["parts"].append({"id": "column", "kind": "column", "storey": 1,
                                     "lo_m": [s["lo_m"][0], s["lo_m"][1], s["hi_m"][2]], "hi_m": [s["lo_m"][0] + 0.1, s["lo_m"][1] + 0.1, s["hi_m"][2] + 2.0]})
    assert _failing(broken, params) == ["headroom at least 80 in over every flight (1011.3)"]


def test_a_low_duct_fails_headroom(apt, params):
    broken = copy.deepcopy(apt)
    f = broken["stair"]["flights"][1]  # rises towards the front (-x) from the landing
    z = f["z0_m"] + 70 * IN
    broken["stair"]["parts"].append({"id": "duct", "kind": "duct", "storey": 1,
                                     "lo_m": [f["x_bottom_m"] - 0.3, f["y0_m"], z], "hi_m": [f["x_bottom_m"] - 0.1, f["y1_m"], z + 0.1]})
    assert _failing(broken, params) == ["headroom at least 80 in over every flight (1011.3)"]


def test_a_low_hall_floor_makes_a_tall_riser(apt, params):
    # The review's case: the hall in front of flight 2a 2 in low, so its first riser is 8 in.
    broken = copy.deepcopy(apt)
    for pid in ("floor-2-hall-a", "floor-2-hall"):
        p = _part(broken, pid)
        p["lo_m"][2] -= 2 * IN
        p["hi_m"][2] -= 2 * IN
    failing = _failing(broken, params)
    assert "risers 4-7 in, measured floor to floor (1011.5.2)" in failing
    assert "risers and treads within 0.375 in in each flight (1011.5.4)" in failing


def test_a_short_hall_fails_the_landing_depth(apt, params):
    # The level-2 hall cut back to 30 in in front of flight 2a's first riser, on side A.
    broken = copy.deepcopy(apt)
    a, h = _part(broken, "floor-2-hall-a"), _part(broken, "floor-2-hall")
    end = a["hi_m"][0]
    a["lo_m"][0] = end - 30 * IN
    h["hi_m"][0] = min(h["hi_m"][0], end - 30 * IN)
    broken["stair"]["parts"] = [p for p in broken["stair"]["parts"] if p["id"] != "floor-2-hall"] + [h]
    assert "the landing or floor at each end as deep as the flight is wide, up to 48 in (1011.6)" in _failing(broken, params)


def test_without_the_guard_the_open_edge_is_found(apt, params):
    broken = copy.deepcopy(apt)
    broken["stair"]["parts"] = [p for p in broken["stair"]["parts"] if p["kind"] != "guard"]
    assert "no open edge with a drop over 30 in without a guard (1015.2)" in _failing(broken, params)
    opens = [e for e in stair.edges(broken, params) if e["kind"] == "open" and e["drop"] > 30 * IN]
    assert {e["part"] for e in opens} == {"floor-3-hall-a"}


def test_an_uneven_step_fails_uniformity(apt, params):
    broken = copy.deepcopy(apt)
    _part(broken, "flight-1b-5")["hi_m"][2] += 0.5 * IN
    assert "risers and treads within 0.375 in in each flight (1011.5.4)" in _failing(broken, params)


def test_a_missing_handrail_and_a_narrow_door_fail(apt, params):
    broken = copy.deepcopy(apt)
    broken["stair"]["rails"] = [r for r in broken["stair"]["rails"] if r["id"] != "rail-2b-centre"]
    broken["stair"]["doors"][0]["width_m"] = 34 * IN
    failing = _failing(broken, params)
    assert "handrails on both sides of every flight (1011.11)" in failing
    assert "flat doors at least 32 x 80 in clear (1010.1.1)" in failing


def test_a_handrail_across_a_door_fails_its_landing(apt, params):
    # The review's case: the back-right door slid 10 in towards the stair, into the upper flight's
    # handrail extension.
    broken = copy.deepcopy(apt)
    d = next(x for x in broken["stair"]["doors"] if x["id"] == "2-back-right/stair/0")
    d["lo_m"][0] += 10 * IN
    d["hi_m"][0] += 10 * IN
    assert "a clear landing 44 in long and the door's width in front of every flat door (1010.1.6)" in _failing(broken, params)


def test_the_back_stair_windows_at_the_landings(apt, params):
    w = {x["window"]: x for x in stair.windows_by_walking(apt, params)}
    # The landing's top is the windows' sill: glazing at a walking surface (2406.4.3), and on
    # level 2 a sill 13 ft up (1015.8, if it opens).
    assert w["1-stair/back/0"]["safety_2406_4_3"] and not w["1-stair/back/0"]["fall_1015_8"]
    assert w["2-stair/back/0"]["safety_2406_4_3"] and w["2-stair/back/0"]["fall_1015_8"]
    assert not w["2-stair/front/0"]["safety_2406_4_3"] and not w["2-stair/front/0"]["fall_1015_8"]


def test_handrails_follow_the_nosing_line(apt):
    for r in apt["stair"]["rails"]:
        f = next(f for f in apt["stair"]["flights"] if f["id"] == r["flight"])
        p = np.array(r["points_m"])
        assert p[1][2] - f["z_top_m"] == pytest.approx(36 * IN, abs=1e-5)
        assert p[2][2] == pytest.approx(p[1][2], abs=1e-6)  # level past the top
