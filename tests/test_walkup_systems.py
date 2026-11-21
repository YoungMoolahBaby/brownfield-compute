"""Pass 3g step 1 (D28): the walk-up's rooms, plumbing walls and service annex (forge `rooms`,
Addendum 2, under `rooms` in out/pass3/apartment-addendum-2.json), checked against IBC 2021 by
`brownfield.systems`. Every check passes on the model; the tests below break it in ways a check
must catch. (`test_systems.py` is pass 3b's structural systems, steel and masonry.)"""
import copy
import json

import pytest

from brownfield import systems
from brownfield.params import load_params, values

FT = 0.3048
IN = 0.0254


@pytest.fixture(scope="module")
def apt():
    return systems.load()


@pytest.fixture(scope="module")
def base():
    return json.loads(systems.BASE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def _failing(apt, base, P):
    return [label for label, ok, _ in systems.check(apt, base, P) if not ok]


def _room(apt, rid):
    return next(r for r in apt["rooms"]["rooms"] if r["id"] == rid)


def test_every_check_passes(apt, base, P):
    assert _failing(apt, base, P) == []


def test_the_layout(apt):
    R = apt["rooms"]
    assert apt["revision"] == "addendum-2"
    assert len(R["rooms"]) == 10 * 12 + 2 and len(R["walls"]) == 7 * 12 and len(R["annex"]["parts"]) == 6
    flats = systems.by_flat(apt)
    assert all(sum(r["use"] == "bedroom" for r in rs) == 2 for rs in flats.values())
    # Every flat alike: the front-left plan mirrored, so every flat's room areas are the same.
    areas = {n: sorted(round(r["area_m2"], 9) for r in rs) for n, rs in flats.items()}
    assert len({tuple(a) for a in areas.values()}) == 1
    # The typical flat, in ft2: bed 1, bed 2, living, kitchen, bath.
    a = {r["id"].split("/")[1]: r["area_m2"] / FT ** 2 for r in flats["2-front-left"]}
    assert [round(a[k], 1) for k in ("bed-1", "bed-2", "living", "kitchen", "bath")] == [112.9, 96.1, 273.8, 81.5, 43.5]


def test_escape_windows_are_named_and_need_casements(apt, P):
    esc = systems.escape_windows(apt, P)
    assert len(esc) == 24 and all(esc.values())
    ops = {o["id"]: o for o in apt["openings"]}
    for bed, w in esc.items():
        o = ops[w["id"]]
        assert o["flat"] == bed.split("/")[0] and o["kind"] == "window"  # in the bedroom's own flat
        assert w["side_hinged"] and not w["hung"] and not w["sliding"]
    # Bed 2 has the one end-wall window.
    assert esc["3-back-right/bed-2"]["id"].startswith("3-back-right/right/")


def test_a_smaller_bedroom_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    r = _room(bad, "2-back-right/bed-2")
    r["area_m2"] = 69.0 * FT ** 2
    assert any("70 ft2" in f for f in _failing(bad, base, P))


def test_a_narrow_bedroom_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    r = _room(bad, "3-front-left/bed-1")
    r["hi_m"][0] = r["lo_m"][0] + 6.9 * FT
    f = _failing(bad, base, P)
    assert any("7 ft in plan" in x for x in f)
    assert any("cover its floor" in x for x in f)  # and the flat is no longer covered


def test_a_narrow_hall_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    r = _room(bad, "1-back-left/hall")
    r["hi_m"][0] = r["lo_m"][0] + 35.0 * IN
    assert any("Table 1020.3" in x for x in _failing(bad, base, P))


def test_a_low_ceiling_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    r = _room(bad, "2-front-right/living")
    r["hi_m"][2] = r["lo_m"][2] + 89.0 * IN + P["systems.design.finished_floor_upper_in"] * IN
    assert any("1208.2" in x for x in _failing(bad, base, P))


def test_a_bedroom_without_a_window_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    _room(bad, "1-front-right/bed-2")["openings"] = []
    assert any("1031.3" in x for x in _failing(bad, base, P))


def test_a_hung_escape_window_would_not_do(apt, base, P):
    # Make every window taller, 52 in: a hung sash could then open 26 in, and the casement-only
    # finding no longer holds, so its check fails.
    bad = copy.deepcopy(apt)
    for o in bad["openings"]:
        if o["kind"] == "window":
            o["height_m"] = 52.0 * IN
    assert any("side-hinged" in x for x in _failing(bad, base, P))


def test_one_window_that_could_be_hung_breaks_the_finding(apt, base, P):
    # Only one bedroom's escape window made taller: the finding must hold for every one.
    bad = copy.deepcopy(apt)
    wid = systems.escape_windows(apt, P)["2-back-left/bed-2"]["id"]
    next(o for o in bad["openings"] if o["id"] == wid)["height_m"] = 52.0 * IN
    assert any("side-hinged" in x for x in _failing(bad, base, P))


def test_a_plumbing_wall_into_the_party_wall_fails(apt, base, P):
    # Pushed a full inch into the spine: the gap is negative, not 0.5 in.
    bad = copy.deepcopy(apt)
    w = next(w for w in bad["rooms"]["walls"] if w["id"] == "3-back-right/plumbing-wall")
    w["lo_m"][0] -= 1.5 * IN
    w["hi_m"][0] -= 1.5 * IN
    assert any("clear of the party wall" in x for x in _failing(bad, base, P))


def test_a_wet_room_out_of_stack_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    r = _room(bad, "3-back-left/bath")
    r["lo_m"][1] += 0.1
    r["hi_m"][1] += 0.1
    assert any("stack floor over floor" in x for x in _failing(bad, base, P))


def test_a_plumbing_wall_against_the_party_wall_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    w = next(w for w in bad["rooms"]["walls"] if w["id"] == "2-front-left/plumbing-wall")
    w["hi_m"][0] += 0.25 * IN
    assert any("clear of the party wall" in x for x in _failing(bad, base, P))


def test_any_other_change_to_the_building_fails(apt, base, P):
    bad = copy.deepcopy(apt)
    o = next(o for o in bad["openings"] if o["id"] == "2-front-left/front/0")
    o["width_m"] += 0.01
    assert any("Addendum 2 changes no opening" in x for x in _failing(bad, base, P))
    bad = copy.deepcopy(apt)
    bad["openings"] = [o for o in bad["openings"] if o["id"] != "3-back-left/back/2"]
    assert any("Addendum 2 changes no opening" in x for x in _failing(bad, base, P))


def test_the_annex_needs_its_doors(apt, base, P):
    bad = copy.deepcopy(apt)
    bad["rooms"]["annex"]["doors"] = bad["rooms"]["annex"]["doors"][:1]
    assert any("own outside door" in x for x in _failing(bad, base, P))
