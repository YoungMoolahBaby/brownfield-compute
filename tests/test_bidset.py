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


def _results(path, apt, p):
    return {label.split(" (")[0]: ok for label, ok, _ in bidset.check(path, apt, p)}


def test_the_ifc_holds_to_forges_model(ifc):
    apt, _, p, path = ifc
    res = bidset.check(path, apt, p)
    assert all(ok for _, ok, _ in res), bidset.report(res)


def test_the_ifc_is_the_same_every_export(ifc, tmp_path):
    apt, frame, p, path = ifc
    again = tmp_path / "again.ifc"
    bidset.write_ifc(apt, frame, p, again)
    assert bidset.body_text(again) == bidset.body_text(path)


def test_the_check_catches_a_window_moved_or_resized(ifc):
    apt, _, p, path = ifc
    moved = copy.deepcopy(apt)
    o = moved["openings"][0]
    o["panel_lo_m"][2] += 0.005
    o["panel_hi_m"][2] += 0.005
    assert _results(path, moved, p)["every wall, slab, window and door where forge has it"] is False
    resized = copy.deepcopy(apt)
    resized["openings"][0]["width_m"] += 0.001
    assert _results(path, resized, p)["sizes exact"] is False


def test_types_and_their_u_factors(ifc):
    apt, _, p, path = ifc
    # The windows the code calls for safety glazing in are their own type, W2.
    assert bidset.types(apt, bidset.safety_glazing(apt, p)) == {
        ("window", 0.9144, 1.2192, False): "W1", ("window", 0.9144, 1.2192, True): "W2",
        ("patio_door", 1.8288, 2.032, True): "D1", ("entry_door", 1.0668, 2.032, False): "D2"}
    f = ifcopenshell.open(str(path))
    u = {t.Name: ue.get_psets(t)["Pset_WindowCommon" if t.is_a("IfcWindowType") else "Pset_DoorCommon"]["ThermalTransmittance"]
         for t in f.by_type("IfcWindowType") + f.by_type("IfcDoorType")}
    window_u, door_u = p["pass3.envelope.window_u"].value * BTU_FT2, p["pass3.envelope.door_u"].value * BTU_FT2
    assert u == pytest.approx({"W1": window_u, "W2": window_u, "D1": window_u, "D2": door_u})


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
    apt, _, p, path = ifc
    extra = copy.deepcopy(apt)
    extra["parts"].append(dict(extra["parts"][-1], id="roof-2"))
    assert _results(path, extra, p)["every wall, slab and roof of forge's model, once, and nothing else"] is False


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


# ---- The second reader, web-ifc ----

webifc = pytest.mark.skipif(not bidset.webifc_ready(), reason=f"second reader not ready: {bidset.webifc_status()}")


@webifc
def test_web_ifc_reads_the_same_building(ifc):
    apt, _, p, path = ifc
    res = bidset.check_webifc(path, apt, p)
    assert all(ok for _, ok, _ in res), bidset.report(res)


@webifc
def test_web_ifc_check_catches_a_moved_window_and_a_wrong_sill(ifc):
    apt, _, p, path = ifc
    moved = copy.deepcopy(apt)
    o = moved["openings"][7]
    o["panel_lo_m"][2] += 0.005
    o["panel_hi_m"][2] += 0.005
    o["sill_above_floor_m"] += 0.005
    res = {label.split(" (")[0]: ok for label, ok, _ in bidset.check_webifc(path, moved, p)}
    assert res["web-ifc's own geometry: every wall, slab, window and door where forge has it"] is False
    assert res["web-ifc: every unit's id, kind, flat, face, index and sill height"] is False


@webifc
def test_web_ifc_check_fails_on_an_empty_mesh_or_a_missing_size(ifc, monkeypatch):
    # The review's cases: a mesh with no vertices (JSON null, so NaN) and a unit with no width
    # must fail their checks, not pass or crash.
    apt, _, p, path = ifc
    real = bidset.read_webifc

    def broken(pth):
        w = real(pth)
        wall = next(e for e in w["elements"] if e["cls"] == "IFCWALL")
        wall["bbox"] = [[None, None, None], [None, None, None]]
        unit = next(e for e in w["elements"] if e["cls"] == "IFCWINDOW")
        unit["width"] = None
        return w

    monkeypatch.setattr(bidset, "read_webifc", broken)
    res = {label.split(" (")[0]: ok for label, ok, _ in bidset.check_webifc(path, apt, p)}
    assert res["web-ifc's own geometry: every wall, slab, window and door where forge has it"] is False
    assert res["web-ifc: sizes exact"] is False
    assert res["web-ifc: glazing per flat equals pass 3b's flat_envelope"] is False


# ---- What a quote needs: safety glazing and the IDS (step 3) ----

def test_safety_glazing_by_the_layout(ifc):
    # Every patio door (2406.4.1), and the two windows beside each, whose edges are
    # 45 ft / 7 - 6 ft / 2 - 3 ft / 2 = 23.14 in from the door's: inside the 24 in arc, with sills
    # at 36 in, under 60 (2406.4.2). The 3 x 4 ft windows' sills are above 18 in, so 2406.4.3 doesn't
    # reach them.
    apt, _, p, _ = ifc
    h = bidset.safety_glazing(apt, p)
    kinds = Counter(r.split(":")[0] for r in h.values())
    assert kinds == {"IBC 2018 2406.4.1": 12, "IBC 2018 2406.4.2": 24}
    gap = 45 * 12 / 7 - 36 - 18
    assert all(f"{gap:.1f} in from the edge of door" in r for r in h.values() if "4.2" in r)
    doors = {o["id"] for o in apt["openings"] if o["kind"] == "patio_door"}
    assert doors <= set(h)


@pytest.fixture(scope="module")
def checklist(ifc, tmp_path_factory):
    _, _, p, _ = ifc
    path = tmp_path_factory.mktemp("ids") / "bidset.ids"
    return bidset.write_ids(p, path), path


def test_the_ids_is_valid_and_reads_back(ifc, checklist):
    # Read back from the file, every specification carries the identifier it was written with.
    doc, path = checklist
    want = [f"{f['key']}/{on}" for f in bidset.ids_fields(ifc[2]) for on in f["on"]]
    assert [s.identifier for s in doc.specifications] == want
    assert len(want) == 56 and len(set(want)) == len(want)


def test_what_the_walk_up_carries(ifc, checklist):
    rows = bidset.run_ids(checklist[0], ifc[3])
    carried, fields = bidset.ids_carried(rows)
    assert fields == 32
    assert carried == ["type mark", "storey", "exterior or not", "unit width", "unit height",
                       "U-factor within the code's limit", "in a wall", "the wall's construction (on exterior walls)"]


def _complete(path, out):
    """A copy of the bid set with every field a quote needs filled in (made-up values), to show
    the IDS passes a model that has them."""
    import ifcopenshell.api.classification as classification
    import ifcopenshell.api.material as material
    import ifcopenshell.api.pset as pset

    f = ifcopenshell.open(str(path))
    mf = f.by_type("IfcClassification")[0]
    vinyl = material.add_material(f, name="vinyl")
    for t in f.by_type("IfcWindowType") + f.by_type("IfcDoorType"):
        window = t.is_a("IfcWindowType")
        material.assign_material(f, products=[t], material=vinyl)
        classification.add_reference(f, products=[t], identification="08 53 13" if window else "08 32 13",
                                     name="made up for the test", classification=mf)
        if not window:
            t.OperationType = "SLIDING_TO_LEFT"
        common = next(ps for ps in t.HasPropertySets if ps.Name in ("Pset_WindowCommon", "Pset_DoorCommon"))
        pset.edit_pset(f, pset=common, properties={"WindLoadRating": "LC-PG50", **({"FireExit": True} if window else {})})
        glass = pset.add_pset(f, product=t, name="Pset_DoorWindowGlazingType")
        pset.edit_pset(f, pset=glass, properties={"IsCoated": True, "FillGas": "argon", "IsTempered": True,
                                                  "SolarHeatGainTransmittance": 0.3})
        ours = pset.add_pset(f, product=t, name="BidSet_Unit")
        label = f.createIfcLabel
        pset.edit_pset(f, pset=ours, properties={
            "RoughOpeningWidth": f.createIfcLengthMeasure(1.0), "RoughOpeningHeight": f.createIfcLengthMeasure(1.3),
            "Operation": label("casement"), "FrameColourInside": label("white"), "FrameColourOutside": label("bronze"),
            "ObscureGlass": False, "Screen": True, "Grilles": label("none"), "HardwareFinish": label("white"),
            "InstallType": label("nail fin"), "SafetyGlazing": label("tempered"),
            # A casement's clear opening, comfortably over IBC 2018 1030's minimums.
            "ClearOpeningArea": f.createIfcAreaMeasure(0.80), "ClearOpeningWidth": f.createIfcLengthMeasure(0.80),
            "ClearOpeningHeight": f.createIfcLengthMeasure(1.10), "ClearOpeningSillHeight": f.createIfcLengthMeasure(0.95)})
    f.write(str(out))
    return f


def test_the_ids_passes_a_complete_model_and_fails_a_broken_one(ifc, checklist, tmp_path):
    doc, ids_path = checklist
    full = tmp_path / "complete.ifc"
    f = _complete(ifc[3], full)
    rows = bidset.run_ids(doc, full)
    assert all(r["status"] for r in rows), [r["id"] for r in rows if not r["status"]]
    # And every one applies to something (a specification that applies to nothing passes).
    assert all(r["applicable"] > 0 for r in rows), [r["id"] for r in rows if not r["applicable"]]
    applies = {r["id"]: r["applicable"] for r in rows}
    assert (applies["safety/IFCWINDOW+hazard"], applies["safety/IFCDOOR+hazard"]) == (24, 12)
    w = f.by_type("IfcWindow")[0]
    w.OverallWidth = None
    broken = tmp_path / "broken.ifc"
    f.write(str(broken))
    failed = [r["id"] for r in bidset.run_ids(bidset.read_ids(ids_path), broken) if not r["status"]]
    assert failed == ["width/IFCWINDOW"]


def test_safety_glazing_finds_a_sidelite_tight_against_a_door(ifc):
    # Edge to edge with the entry door: the gap is zero, or -1e-15 to rounding, and still counts.
    apt, _, p, _ = ifc
    a = copy.deepcopy(apt)
    door = next(o for o in a["openings"] if o["kind"] == "entry_door")
    w = 18 * 0.0254
    side = dict(door, id="1-stair/front/sidelite", kind="window", glazed=True, width_m=w,
                along_m=door["along_m"] + door["width_m"] / 2 + w / 2)
    side["lo_m"] = [door["lo_m"][0], door["hi_m"][1], door["lo_m"][2]]
    side["hi_m"] = [door["hi_m"][0], door["hi_m"][1] + w, door["hi_m"][2]]
    a["openings"].append(side)
    assert "2406.4.2: 0.0 in" in bidset.safety_glazing(a, p)[side["id"]]


def test_safety_glazing_looks_round_a_corner(ifc):
    # A window in the end wall within the arc of a door at the corner of the facade is flagged,
    # and the reason says exception 4 turns on the door's handing.
    apt, _, p, _ = ifc
    a = copy.deepcopy(apt)
    win = next(o for o in a["openings"] if o["face"] == "left" and o["storey"] == 1)
    door = next(o for o in a["openings"] if o["kind"] == "patio_door" and o["storey"] == 1 and o["face"] == "front")
    door["lo_m"][1], door["hi_m"][1] = 0.2, 0.2 + door["width_m"]  # slid to the corner
    win["lo_m"][0], win["hi_m"][0] = 0.3, 0.3 + win["width_m"]     # and the window to it
    reason = bidset.safety_glazing(a, p).get(win["id"], "")
    assert "round the corner" in reason and "handing" in reason



def test_one_stair_fits_the_table_but_the_model_misses_footnote_a(ifc):
    # IBC 2018 Table 1006.3.3(1): 3 storeys, 4 flats a storey; the common path bounded by a flat
    # corner to corner (45 + 20 = 65 ft) and, on the ground floor, the back flats' far corner to
    # the front door in the middle of its 7 in wall (40 ft - 3.5 in + 50 ft). It fits, but
    # footnote a wants escape windows in every
    # bedroom (2 a flat, pass 4's flats: 16 upstairs, 8 on the ground floor), and none is marked.
    apt, _, p, _ = ifc
    se = bidset.single_exit(apt, p)
    assert (se["storeys"], se["units_per_storey"], se["fits_table"]) == (3, 4, True)
    assert (round(se["path_to_stair_ft"], 6), round(se["path_to_entry_ft"], 6)) == (65.0, round(90 - 3.5 / 12, 6))
    assert (se["escape_needed_upper"], se["escape_needed_ground"], se["meets_footnote_a"]) == (16, 8, False)
    assert bidset.single_exit(apt, p, marked=16)["meets_footnote_a"] is True
    assert "does NOT meet it yet" in bidset.single_exit_report(se, p)


def test_one_stair_fails_the_table_past_each_limit(ifc):
    apt, _, p, _ = ifc
    four = copy.deepcopy(apt)
    four["storeys"] = 4
    five = copy.deepcopy(apt)
    five["flats"].append(dict(five["flats"][0], name="2-extra"))
    five["flats"][-1]["floor"] = 2
    far = copy.deepcopy(apt)
    far["flat_len_m"] = 130 * 0.3048  # a flat 130 ft long: past 125 ft of common path
    for a in (four, five, far):
        assert bidset.single_exit(a, p)["fits_table"] is False


def test_escape_counts_round_up(ifc):
    apt, _, p, _ = ifc
    q = dict(p)
    q["bidset.flat_bedrooms"] = type(p["bidset.flat_bedrooms"])(**{**vars(p["bidset.flat_bedrooms"]), "value": 1.7})
    se = bidset.single_exit(apt, q)
    assert (se["escape_needed_upper"], se["escape_needed_ground"]) == (14, 7)  # 13.6 and 6.8, up


def test_an_escape_window_too_short_to_clear_24_inches_fails(ifc, checklist, tmp_path):
    # A double-hung 3 x 4 ft opens about half its height, under 1030.2.1's 24 in: marked as an
    # escape window, it fails the clear height (and the area), and nothing else. Windows marked as
    # not escape windows (W2 here) are left out of the escape sizes.
    import ifcopenshell.api.pset as pset

    doc, _ = checklist
    full = tmp_path / "complete.ifc"
    f = _complete(ifc[3], full)
    for t in f.by_type("IfcWindowType"):
        ours = next(ps for ps in t.HasPropertySets if ps.Name == "BidSet_Unit")
        pset.edit_pset(f, pset=ours, properties={"ClearOpeningHeight": f.createIfcLengthMeasure(0.55),
                                                 "ClearOpeningArea": f.createIfcAreaMeasure(0.45)})
        if t.Name == "W2":  # not an escape window: left out of the escape sizes
            common = next(ps for ps in t.HasPropertySets if ps.Name == "Pset_WindowCommon")
            pset.edit_pset(f, pset=common, properties={"FireExit": False})
    short = tmp_path / "short.ifc"
    f.write(str(short))
    rows = bidset.run_ids(doc, short)
    failed = sorted(r["id"] for r in rows if not r["status"])
    assert failed == ["escape_area/IFCWINDOW+escape", "escape_height/IFCWINDOW+escape"]
    applies = {r["id"]: r["applicable"] for r in rows}
    assert applies["escape_height/IFCWINDOW+escape"] == 77  # W1's, not W2's 24
