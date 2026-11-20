"""Pass 3f step 5 (D27): a made-up RFI and Addendum 1 run through the bid set as a reviewed
change (forge `apartment-json addendum-1`, out/pass3/apartment-addendum-1.json)."""
import json
from collections import Counter

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

from brownfield import OUT_DIR, addendum, bidset
from brownfield.params import load_params


@pytest.fixture(scope="module")
def revision(tmp_path_factory):
    p = load_params()
    apt0, frame = bidset.load()
    apt1, _ = bidset.load("apartment-addendum-1.json")
    d = tmp_path_factory.mktemp("addendum")
    base, rev = d / "base.ifc", d / "rev.ifc"
    bidset.write_ifc(apt0, frame, p, base)
    bidset.write_ifc(apt1, frame, p, rev, spec=addendum.SPEC)
    return {"p": p, "apt0": apt0, "apt1": apt1, "base": base, "rev": rev, "dir": d}


def test_forge_changes_only_the_patio_doors(revision):
    # The design change is forge's: the 12 patio doors 6'-0" -> 5'-0", centred where they were,
    # with everything that follows (the flats' glazing) recomputed there. Same ids, nothing else.
    a, b = revision["apt0"], revision["apt1"]
    assert (a["revision"], b["revision"]) == ("", "addendum-1")
    assert [o["id"] for o in a["openings"]] == [o["id"] for o in b["openings"]]
    moved = [(x, y) for x, y in zip(a["openings"], b["openings"]) if x != y]
    assert len(moved) == 12 and all(x["kind"] == "patio_door" for x, _ in moved)
    assert all(abs(y["width_m"] - 60 * 0.0254) < 1e-9 and y["along_m"] == x["along_m"] for x, y in moved)
    assert a["parts"] == b["parts"]
    # Each flat loses 1 ft x 6'-8" of patio door glass.
    for fa, fb in zip(a["flats"], b["flats"]):
        assert abs((fa["glazed_m2"] - fb["glazed_m2"]) - 0.3048 * 80 * 0.0254) < 1e-9


def test_the_code_check_follows_the_change(revision):
    # The windows beside each door are now 45 ft / 7 - 2.5 ft - 1.5 ft = 29.1 in from its edge,
    # outside the 24 in arc: only the doors themselves need safety glazing.
    p = revision["p"]
    h0, h1 = bidset.safety_glazing(revision["apt0"], p), bidset.safety_glazing(revision["apt1"], p)
    assert (len(h0), len(h1)) == (36, 12)
    assert all(r == "IBC 2018 2406.4.1: glazing in a door" for r in h1.values())


def test_the_diff_shows_exactly_what_the_addendum_changed(revision):
    # The 12 patio doors (narrower: attributes, geometry; tempered: properties; the 5'-0" door is
    # a new type), the 24 windows beside them (W2 -> W1), the 12 doors' openings, and the types:
    # D1 at 6'-0" and W2 withdrawn, D1 at 5'-0" new. Nothing else.
    d = addendum.element_diff(revision["base"], revision["rev"])
    assert d["added"] == [] and d["deleted"] == []
    how = Counter((v["cls"], tuple(v["changes"])) for v in d["changed"].values())
    assert how == {("IfcDoor", ("attributes", "geometry", "properties", "type")): 12, ("IfcWindow", ("properties", "type")): 24}
    patio = {o["id"] for o in revision["apt0"]["openings"] if o["kind"] == "patio_door"}
    assert set(d["openings_resized"]) == patio
    assert [x.split(" (")[0] for x in d["types"]["deleted"]] == ["D1", "W2"]
    assert [x.split(" (")[0] for x in d["types"]["added"]] == ["D1"] and d["types"]["changed"] == []
    # ifcdiff alone also flags elements whose only change is an entity number.
    assert d["ifcdiff_flagged"] > len(d["changed"])


def test_the_revision_must_be_the_base_plus_the_addendum(revision):
    p, a, b = revision["p"], revision["apt0"], revision["apt1"]
    assert addendum.check_revision(a, b, p) == []
    moved = json.loads(json.dumps(b))
    w = next(o for o in moved["openings"] if o["kind"] == "window")
    w["sill_m"] += 0.01
    assert any("changed" in e for e in addendum.check_revision(a, moved, p))
    assert addendum.check_revision(a, a, p)  # the base itself isn't the revision


def test_the_revision_passes_its_checks(revision):
    res = bidset.check(revision["rev"], revision["apt1"], revision["p"])
    assert all(ok for _, ok, _ in res), bidset.report(res)


def test_the_rfi_is_a_closed_bcf_topic_on_the_patio_doors(revision):
    import numpy as np
    from bcf.v3.bcfxml import BcfXml

    w = addendum.words(revision["apt0"], revision["apt1"], revision["p"])
    path = revision["dir"] / "rfi-001.bcf"
    guids = addendum.write_rfi(revision["base"], path, w)
    f = ifcopenshell.open(str(revision["base"]))
    assert guids == sorted(d.GlobalId for d in f.by_type("IfcDoor") if ue.get_type(d).Name == "D1")
    bcf = BcfXml.load(path)  # keep it: topics and viewpoints load from its zip as they're read
    (topic,) = bcf.topics.values()
    assert (topic.topic.title, topic.topic.topic_status) == (w["title"], "Closed")
    assert [c.comment for c in topic.comments] == [w["answer"]]
    assert topic.comments[0].date.to_datetime() > topic.topic.creation_date.to_datetime()
    (vp,) = topic.viewpoints.values()
    assert sorted(c.ifc_guid for c in vp.visualization_info.components.selection.component) == guids
    # The camera looks at the building: from outside the front, straight at its middle.
    cam = vp.visualization_info.perspective_camera
    eye = np.array([cam.camera_view_point.x, cam.camera_view_point.y, cam.camera_view_point.z])
    look = np.array([cam.camera_direction.x, cam.camera_direction.y, cam.camera_direction.z])
    apt = revision["apt0"]
    centre = np.array([apt["depth_m"], apt["length_m"], apt["storey_m"] * apt["storeys"]]) / 2
    assert eye[0] < 0 and look @ (centre - eye) / np.linalg.norm(centre - eye) > 0.999


def test_the_words_come_from_the_run(revision):
    # The RFI's numbers are the model's and the params', so a change to either shows in them.
    p, a, b = revision["p"], revision["apt0"], revision["apt1"]
    w = addendum.words(a, b, p)
    assert "23.1 in from a door's edge, inside 2406.4.2's 24 in arc" in w["question"]
    assert "6'-0\" to 5'-0\"" in w["answer"] and "type W2 is withdrawn; they are W1" in w["answer"]
    wide = dict(p)
    arc = p["bidset.code.safety_glazing.door_arc_in"]
    wide["bidset.code.safety_glazing.door_arc_in"] = type(arc)(**{**vars(arc), "value": 30.0, "high": 30.0})
    assert "24 of the windows beside them still need safety glazing" in addendum.words(a, b, wide)["answer"]


def test_schedule_changes_match_types_by_what_they_are():
    # W2 withdrawn from the middle: W3 becomes W2, and is reported as renumbered, not changed.
    row = lambda mark, w, safe, n: {"mark": mark, "kind": "window", "count": n, "width_mm": w, "height_mm": 1219.2,  # noqa: E731
                                    "safety_glazing_required": "yes (x)" if safe else "no"}
    old = [row("W1", 914.4, False, 10), row("W2", 914.4, True, 4), row("W3", 1219.2, False, 1)]
    new = [row("W1", 914.4, False, 14), row("W2", 1219.2, False, 1)]
    lines = addendum.schedule_changes(old, new)
    assert lines == ["W2: withdrawn (4 windows)", "W1 count: 10 -> 14", "W3 renumbered W2"]
    assert addendum.schedule_changes([row("W1", 1.0, False, 1)], [])[0] == "W1: withdrawn (1 window)"


def test_a_spec_adds_to_a_property_set_the_type_has(revision, tmp_path):
    # A spec naming Pset_WindowCommon adds to it rather than making a second with the same GlobalId.
    p, apt, (_, frame) = revision["p"], revision["apt0"], bidset.load()
    path = tmp_path / "spec.ifc"
    bidset.write_ifc(apt, frame, p, path, spec={"window": {"Pset_WindowCommon": {"FireExit": True}}})
    res = dict((label, ok) for label, ok, _ in bidset.check(path, apt, p))
    assert res["GlobalIds unique"]
    w1 = next(t for t in ifcopenshell.open(str(path)).by_type("IfcWindowType") if t.Name == "W1")
    assert [ps.Name for ps in w1.HasPropertySets].count("Pset_WindowCommon") == 1
    assert ue.get_psets(w1)["Pset_WindowCommon"]["FireExit"] is True


def test_the_schedule_moves_as_the_addendum_says(revision):
    d0 = bidset.write_drawings(revision["base"], revision["dir"] / "d0")
    d1 = bidset.write_drawings(revision["rev"], revision["dir"] / "d1")
    lines = addendum.schedule_changes(d0["schedule"], d1["schedule"])
    for want in ("W2: withdrawn (24 windows)", "W1 count: 77 -> 101", "D1 width: 6'-0\" -> 5'-0\"",
                 "D1 tempered: not in the model -> True", "D1 safety_glazing: not in the model -> tempered"):
        assert want in lines, want
