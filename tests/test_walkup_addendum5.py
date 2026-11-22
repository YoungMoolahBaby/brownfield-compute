"""Pass 3g step 7e (D28): Addendum 5's building, the fire items and the roof hatch (`systems.addendum_5`)."""
import json

import pytest

from brownfield import OUT_DIR, systems
from brownfield.params import load_params, values

A4 = OUT_DIR / "pass3" / "apartment-addendum-4.json"
pytestmark = pytest.mark.skipif(not A4.exists(), reason="no Addendum 4 model (`brownfield systems`)")


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def pair(P):
    a4 = json.loads(A4.read_text(encoding="utf-8"))
    return a4, systems.addendum_5(a4, P)


def test_addendum_5_changes_only_what_it_says(pair, P):
    a4, a5 = pair
    assert [label for label, ok, _ in systems.check_addendum_5(a5, a4, P) if not ok] == []
    # Addendum 4's model is left as it was.
    assert "roof_ladder" not in a4 and all("fire_rating_h" not in x for x in a4["parts"])


def test_the_annex_walls_and_door_near_the_stair_are_rated(pair, P):
    _, a5 = pair
    c = "systems.fire_code."
    rated = {x["id"]: x["fire_rating_h"] for x in a5["rooms"]["annex"]["parts"] if x.get("fire_rating_h")}
    assert rated == {"annex-left": P[c + "exterior_wall_hr"], "annex-right": P[c + "exterior_wall_hr"]}
    doors = {x["id"]: x["fire_rating_h"] for x in a5["rooms"]["annex"]["doors"] if x.get("fire_rating_h")}
    assert doors == {"annex-mechanical/left/0": P[c + "opening_protective_hr"]}


def test_the_back_wall_is_cut_at_the_stair_and_its_windows_keep_their_places(pair):
    a4, a5 = pair
    before = next(x for x in a4["parts"] if x["id"] == "ext-back-1")
    pieces = [x for x in a5["parts"] if x["id"].startswith("ext-back-1")]
    assert [x["id"] for x in pieces] == ["ext-back-1", "ext-back-1-stair", "ext-back-1-end"]
    assert pieces[0]["lo_m"] == before["lo_m"] and pieces[-1]["hi_m"] == before["hi_m"]
    assert all(abs(a["hi_m"][1] - b["lo_m"][1]) < 1e-12 for a, b in zip(pieces, pieces[1:]))
    assert pieces[1].get("fire_rating_h") == 1
    for o in a5["openings"]:
        if o["wall"].startswith("ext-back-1"):
            w = next(x for x in pieces if x["id"] == o["wall"])
            assert w["lo_m"][1] <= o["lo_m"][1] and o["hi_m"][1] <= w["hi_m"][1], o["id"]


def test_the_roof_hatch_is_an_opening_in_the_roof_over_the_stairs_top_hall(pair, P):
    _, a5 = pair
    c = "systems.fire_code."
    h = next(o for o in a5["openings"] if o["kind"] == "roof_hatch")
    roof = next(x for x in a5["parts"] if x["kind"] == "roof")
    hall = next(x for x in a5["stair"]["parts"] if x["id"] == f"floor-{a5['storeys']}-hall")
    assert h["wall"] == "roof" and h["lo_m"][2] == roof["lo_m"][2] and h["hi_m"][2] == roof["hi_m"][2]
    assert round(h["width_m"] / 0.0254, 6) == P[c + "hatch_l_in"] and round(h["height_m"] / 0.0254, 6) == P[c + "hatch_w_in"]
    assert hall["lo_m"][1] <= h["lo_m"][1] and h["hi_m"][1] <= hall["hi_m"][1]
    lad = a5["roof_ladder"]
    assert round((lad["hi_m"][0] - lad["lo_m"][0]) / 0.0254, 6) == P[c + "ladder_w_in"]
    assert h["lo_m"][0] <= lad["lo_m"][0] and lad["hi_m"][0] <= h["hi_m"][0] and lad["hi_m"][2] == roof["hi_m"][2]
