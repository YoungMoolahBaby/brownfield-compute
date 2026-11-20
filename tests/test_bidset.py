"""Pass 3f (D27): the walk-up written out by forge as named parts for the bid set
(`cargo run --release -- apartment-json` in forge/, out/pass3/apartment.json), and the IFC
`brownfield bidset` writes from it."""
import copy
from collections import Counter, defaultdict

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

from brownfield import bidset, house
from brownfield.house import BTU_FT2
from brownfield.params import load_params


def _apt():
    return house.apartment()


def test_openings_by_kind_and_storey():
    ops = _apt()["openings"]
    # By the layout (forge/src/apartment.rs): per flat and storey six windows and a patio door on
    # the long face, two windows in the end wall; the stair a window front and back, the entry
    # door in place of the front one on the ground floor.
    assert Counter(o["kind"] for o in ops) == {"window": 101, "patio_door": 12, "entry_door": 1}
    assert Counter(o["storey"] for o in ops) == {1: 38, 2: 38, 3: 38}
    assert sum(o["flat"] is None for o in ops) == 6


def test_ids_are_unique_and_name_space_face_and_index():
    ops = _apt()["openings"]
    assert len({o["id"] for o in ops}) == len(ops)
    for o in ops:
        space, face, index = o["id"].split("/")
        assert space == (o["flat"] or f"{o['storey']}-stair")
        assert face == o["face"]
        assert int(index) == o["index"]


def test_glazing_per_flat_matches_the_envelope():
    # Openings are put in flats by where they are (forge `flat_at`); the envelope's glazing comes
    # from a separate filter (`flat_openings`), the one the heat model has used since pass 3b.
    apt = _apt()
    glazed = defaultdict(float)
    for o in apt["openings"]:
        if o["glazed"] and o["flat"]:
            glazed[o["flat"]] += o["width_m"] * o["height_m"]
    assert set(glazed) == {f["name"] for f in apt["flats"]}
    for f in apt["flats"]:
        assert abs(glazed[f["name"]] - f["glazed_m2"]) < 1e-9


def test_openings_sit_in_their_walls_at_their_size():
    apt = _apt()
    parts = {p["id"]: p for p in apt["parts"]}
    for o in apt["openings"]:
        w = parts[o["wall"]]
        assert all(w["lo_m"][i] - 1e-6 <= o["lo_m"][i] and o["hi_m"][i] <= w["hi_m"][i] + 1e-6 for i in range(3))
        size = [hi - lo for lo, hi in zip(o["lo_m"], o["hi_m"])]
        along = 1 if o["face"] in ("front", "back") else 0
        assert abs(size[along] - o["width_m"]) < 1e-6
        assert abs(size[2] - o["height_m"]) < 1e-6
        assert abs(size[1 - along] - apt["ext_t_m"]) < 1e-6
        assert abs(o["lo_m"][2] - o["sill_m"]) < 1e-6


def test_wall_boxes_make_the_shell():
    apt = _apt()
    w, l, t, h = apt["depth_m"], apt["length_m"], apt["ext_t_m"], apt["storey_m"] * apt["storeys"]
    vol = sum((p["hi_m"][0] - p["lo_m"][0]) * (p["hi_m"][1] - p["lo_m"][1]) * (p["hi_m"][2] - p["lo_m"][2])
              for p in apt["parts"] if p["kind"] == "exterior_wall")
    assert abs(vol - (w * l - (w - 2 * t) * (l - 2 * t)) * h) < 1e-6


def test_part_ids_are_unique_and_walls_are_per_storey():
    parts = _apt()["parts"]
    assert len({p["id"] for p in parts}) == len(parts)
    walls = [p for p in parts if p["kind"].endswith("_wall")]
    assert Counter(p["storey"] for p in walls) == {1: 8, 2: 8, 3: 8}
    for p in walls:
        assert p["id"].endswith(f"-{p['storey']}")


# ---- The IFC ----

@pytest.fixture(scope="module")
def ifc(tmp_path_factory):
    apt, frame = bidset.load()
    params = load_params()
    path = tmp_path_factory.mktemp("bidset") / "apartment.ifc"
    bidset.write_ifc(apt, frame, params, path)
    return apt, frame, params, path


def _results(path, apt):
    return {label.split(" (")[0]: ok for label, ok, _ in bidset.check(path, apt)}


def test_the_ifc_holds_to_forges_model(ifc):
    apt, _, _, path = ifc
    res = bidset.check(path, apt)
    assert all(ok for _, ok, _ in res), bidset.report(res)


def test_the_ifc_is_the_same_every_export(ifc, tmp_path):
    apt, frame, p, path = ifc
    again = tmp_path / "again.ifc"
    bidset.write_ifc(apt, frame, p, again)
    assert bidset.body_text(again) == bidset.body_text(path)


def test_the_check_catches_a_window_moved_or_resized(ifc):
    apt, _, _, path = ifc
    moved = copy.deepcopy(apt)
    o = moved["openings"][0]
    o["panel_lo_m"][2] += 0.005
    o["panel_hi_m"][2] += 0.005
    assert _results(path, moved)["every wall, slab, window and door where forge has it"] is False
    resized = copy.deepcopy(apt)
    resized["openings"][0]["width_m"] += 0.001
    assert _results(path, resized)["sizes exact"] is False


def test_types_and_their_u_factors(ifc):
    apt, _, p, path = ifc
    assert bidset.types(apt) == {("window", 0.9144, 1.2192): "W1", ("patio_door", 1.8288, 2.032): "D1",
                                 ("entry_door", 1.0668, 2.032): "D2"}
    f = ifcopenshell.open(str(path))
    u = {t.Name: ue.get_psets(t)["Pset_WindowCommon" if t.is_a("IfcWindowType") else "Pset_DoorCommon"]["ThermalTransmittance"]
         for t in f.by_type("IfcWindowType") + f.by_type("IfcDoorType")}
    window_u, door_u = p["pass3.envelope.window_u"].value * BTU_FT2, p["pass3.envelope.door_u"].value * BTU_FT2
    assert u == pytest.approx({"W1": window_u, "D1": window_u, "D2": door_u})


def test_each_u_factor_says_where_it_comes_from(ifc):
    # D2's comes from a placeholder (params/pass3.yaml door_u), and the file has to say so.
    _, _, p, path = ifc
    f = ifcopenshell.open(str(path))
    notes = {t.Name: q.Description for t in f.by_type("IfcWindowType") + f.by_type("IfcDoorType")
             for ps in t.HasPropertySets for q in ps.HasProperties if q.Name == "ThermalTransmittance"}
    assert notes["D2"].startswith("params pass3.envelope.door_u (placeholder)")
    assert notes["W1"].startswith(f"params pass3.envelope.window_u ({p['pass3.envelope.window_u'].conf})")
    refs = [r for r in f.by_type("IfcClassificationReference")]
    assert refs and all(r.Description.startswith("judgement") for r in refs)


def test_bearing_walls_follow_the_frame(ifc):
    # Facades and spine bear the floors; the stair walls the roof over the stair; end walls neither.
    path = ifc[3]
    f = ifcopenshell.open(str(path))
    bearing = {w.Name: ue.get_psets(w)["Pset_WallCommon"]["LoadBearing"] for w in f.by_type("IfcWall")}
    for name, b in bearing.items():
        assert b == (not name.startswith(("ext-left", "ext-right"))), name


def test_the_check_catches_a_missing_part(ifc):
    apt, _, _, path = ifc
    extra = copy.deepcopy(apt)
    extra["parts"].append(dict(extra["parts"][-1], id="roof-2"))
    assert _results(path, extra)["every wall, slab and roof of forge's model, once, and nothing else"] is False


def test_an_addendum_changes_only_what_it_changes(ifc, tmp_path):
    # Drop one window: only its own records go; the storey's containment, its type's occurrences
    # and every other GlobalId stay.
    apt, frame, p, path = ifc
    less = copy.deepcopy(apt)
    gone = less["openings"].pop(40)["id"]
    after = tmp_path / "less.ifc"
    bidset.write_ifc(less, frame, p, after)
    f0, f1 = ifcopenshell.open(str(path)), ifcopenshell.open(str(after))
    g0, g1 = {e.GlobalId: e for e in f0.by_type("IfcRoot")}, {e.GlobalId for e in f1.by_type("IfcRoot")}
    assert g1 <= set(g0)
    removed = sorted(f"{g0[g].is_a()}" for g in set(g0) - g1)
    assert removed == sorted(["IfcWindow", "IfcOpeningElement", "IfcPropertySet", "IfcRelDefinesByProperties",
                              "IfcRelVoidsElement", "IfcRelFillsElement"]), (gone, removed)
