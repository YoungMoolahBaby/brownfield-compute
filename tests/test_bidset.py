"""Pass 3f (D27): the walk-up written out by forge as named parts for the bid set
(`cargo run --release -- apartment-json` in forge/, out/pass3/apartment.json), and the IFC
`brownfield bidset` writes from it."""
import copy
from collections import Counter, defaultdict

import ifcopenshell
import numpy as np
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


def test_the_stair_is_in_the_ifc(ifc):
    # Pass 3f step 8: an IfcStair a storey (1 and 2), each of its two flights, its landing and its
    # four handrails; the guard on its own on level 3.
    apt, _, p, path = ifc
    f = ifcopenshell.open(str(path))
    stairs = {s.Name: sorted(e.Name for e in ue.get_decomposition(s)) for s in f.by_type("IfcStair")}
    assert stairs == {
        f"stair-{k}": sorted([f"flight-{k}a", f"flight-{k}b", f"landing-{k}",
                              *(f"rail-{k}{s}-{side}" for s in "ab" for side in ("wall", "centre"))]) for k in (1, 2)}
    flight = next(e for e in f.by_type("IfcStairFlight") if e.Name == "flight-1b")
    assert (flight.NumberOfRisers, flight.NumberOfTreads) == (12, 11)
    assert (round(flight.RiserHeight / 0.0254, 6), round(flight.TreadLength / 0.0254, 6)) == (7.0, 11.0)
    guard = next(e for e in f.by_type("IfcRailing") if e.Name == "guard-3")
    assert guard.PredefinedType == "GUARDRAIL" and ue.get_container(guard).Name == "Level 3"


def test_the_check_catches_a_stair_out_of_line(ifc, tmp_path):
    # A missing flight, a step moved 5 mm, flat doors written with the wrong fire rating: each
    # fails its own check.
    apt, frame, p, path = ifc
    less = copy.deepcopy(apt)
    less["stair"]["flights"] = less["stair"]["flights"][1:]
    assert _results(path, less, p)["the stair's flights and railings, once, and nothing else"] is False
    moved = copy.deepcopy(apt)
    s = next(x for x in moved["stair"]["parts"] if x["id"] == "flight-2a-0")
    s["lo_m"][0] -= 0.005
    assert _results(path, moved, p)["every flight and the guard where forge has it"] is False
    q = dict(p)
    rating = p["bidset.code.exit_stair.door_rating_h"]
    q["bidset.code.exit_stair.door_rating_h"] = type(rating)(**{**vars(rating), "value": 0.75})
    wrong = tmp_path / "wrong-rating.ifc"
    bidset.write_ifc(apt, frame, q, wrong)
    assert _results(wrong, apt, p)["the flat doors 1 h fire doors, self-closing, and the stair walls rated 1 h"] is False


def test_the_ifc_is_the_same_every_export(ifc, tmp_path):
    apt, frame, p, path = ifc
    again = tmp_path / "again.ifc"
    bidset.write_ifc(apt, frame, p, again)
    # Byte for byte, header included: its time stamp is fixed, so no local time is published.
    assert again.read_bytes() == path.read_bytes()
    assert f"'{bidset.HEADER_TIME}'" in path.read_text(encoding="utf-8").splitlines()[3]


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
    # The windows the code calls for safety glazing in are their own type, W2; the flat doors
    # into the stair (pass 3f step 8) are D3.
    assert bidset.types(apt, bidset.safety_glazing(apt, p)) == {
        ("window", 0.9144, 1.2192, False): "W1", ("window", 0.9144, 1.2192, True): "W2",
        ("patio_door", 1.8288, 2.032, True): "D1", ("entry_door", 1.0668, 2.032, False): "D2",
        ("flat_door", 0.9144, 2.1336, False): "D3"}
    f = ifcopenshell.open(str(path))
    common = {t.Name: ue.get_psets(t)["Pset_WindowCommon" if t.is_a("IfcWindowType") else "Pset_DoorCommon"]
              for t in f.by_type("IfcWindowType") + f.by_type("IfcDoorType")}
    window_u, door_u = p["pass3.envelope.window_u"].value * BTU_FT2, p["pass3.envelope.door_u"].value * BTU_FT2
    u = {k: v.get("ThermalTransmittance") for k, v in common.items() if k != "D3"}
    assert u == pytest.approx({"W1": window_u, "W2": window_u, "D1": window_u, "D2": door_u})
    # A flat door is inside the envelope: no U-factor; a 1-hour fire door, self-closing.
    assert "ThermalTransmittance" not in common["D3"]
    assert (common["D3"]["FireRating"], common["D3"]["SelfClosing"], common["D3"]["IsExternal"]) == ("1 h", True, False)


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
    # Facades and spine bear the floors; the stair walls the roof over the stair; end walls and
    # the stair's partitions neither. The stair walls are the exit's 1-hour enclosure.
    path = ifc[3]
    f = ifcopenshell.open(str(path))
    psets = {w.Name: ue.get_psets(w)["Pset_WallCommon"] for w in f.by_type("IfcWall")}
    for name, ps in psets.items():
        assert ps["LoadBearing"] == (not name.startswith(("ext-left", "ext-right", "stair-centre", "stair-closure"))), name
        assert ps.get("FireRating") == ("1 h" if name.startswith(("stair-left", "stair-right")) else None), name


def test_the_check_catches_a_missing_part(ifc):
    apt, _, p, path = ifc
    extra = copy.deepcopy(apt)
    extra["parts"].append(dict(next(pt for pt in extra["parts"] if pt["kind"] == "roof"), id="roof-2"))
    assert _results(path, extra, p)["every wall, slab and roof of forge's model, the stair's floors, landings and "
                                    "partitions among them, once, and nothing else"] is False


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
    assert res["web-ifc's own geometry: every wall, slab, window, door, flight and the guard where forge has it"] is False
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
    assert res["web-ifc's own geometry: every wall, slab, window, door, flight and the guard where forge has it"] is False
    assert res["web-ifc: sizes exact"] is False
    assert res["web-ifc: glazing per flat equals pass 3b's flat_envelope"] is False


# ---- What a quote needs: safety glazing and the IDS (step 3) ----

def test_safety_glazing_by_the_layout(ifc):
    # Every patio door (2406.4.1), and the two windows beside each, whose edges are
    # 45 ft / 7 - 6 ft / 2 - 3 ft / 2 = 23.14 in from the door's: inside the 24 in arc, with sills
    # at 36 in, under 60 (2406.4.2). The 3 x 4 ft windows' sills are above 18 in over the floor,
    # so 2406.4.3 doesn't reach them, except the two back stair windows that rise from a landing
    # (pass 3f step 8): 12 ft2 of glass, its bottom at the landing, its top 48 in above it.
    apt, _, p, _ = ifc
    h = bidset.safety_glazing(apt, p)
    kinds = Counter(r.split(":")[0] for r in h.values())
    assert kinds == {"IBC 2018 2406.4.1": 12, "IBC 2018 2406.4.2": 24, "IBC 2018 2406.4.3": 2}
    assert {o: r.split(", ")[0] for o, r in h.items() if "2406.4.3" in r} == {
        "1-stair/back/0": "IBC 2018 2406.4.3: a large pane low over landing-1",
        "2-stair/back/0": "IBC 2018 2406.4.3: a large pane low over landing-2"}
    gap = 45 * 12 / 7 - 36 - 18
    assert all(f"{gap:.1f} in from the edge of door" in r for r in h.values() if "4.2" in r)
    doors = {o["id"] for o in apt["openings"] if o["kind"] == "patio_door"}
    assert doors <= set(h)


def test_a_landing_a_little_off_the_sill_still_makes_safety_glazing(ifc):
    # The review's case: landing 2 raised 2 mm, so the back window's glass starts just under it.
    # It is still a large pane low over a walking surface (2406.4.3).
    apt, _, p, _ = ifc
    raised = copy.deepcopy(apt)
    for part in raised["stair"]["parts"] + raised["parts"]:
        if part["id"] == "landing-2":
            part["lo_m"][2] += 0.002
            part["hi_m"][2] += 0.002
    assert "2406.4.3" in bidset.safety_glazing(raised, p)["2-stair/back/0"]


def test_the_stair_windows_under_2406_4_6_and_2406_4_7(ifc):
    # 2406.4.6: the back stair windows rise from the landings between flights, their bottom edge
    # 0 in above, 0 in away. The front ones and the level-3 back one have their bottom edge 60 in
    # or more above any tread or landing near them. 2406.4.7: the nearest glass is 103 in from a
    # bottom nosing, outside its 60 in arc.
    apt, _, p, _ = ifc
    h = bidset.safety_glazing(apt, p)
    six = {o for o, r in h.items() if "2406.4.6" in r}
    assert six == {"1-stair/back/0", "2-stair/back/0"}
    assert not any("2406.4.7" in r for r in h.values())
    assert bidset.sections_of(h["1-stair/back/0"]) == ["2406.4.3", "2406.4.6"]
    assert "; also IBC 2018 2406.4.6: its bottom edge 0 in above landing-1, 0 in from it" in h["1-stair/back/0"]
    # A flight turned to rise towards the front, its foot 33 in from the back windows: the
    # level-1 back window is within its bottom nosing's arc, 36 in above its landing.
    turned = copy.deepcopy(apt)
    fl = next(f for f in turned["stair"]["flights"] if f["id"] == "flight-1a")
    fl["dir"], fl["x_bottom_m"] = -1.0, (480 - 7 - 33) * 0.0254
    reason = bidset.safety_glazing(turned, p)["1-stair/back/0"]
    assert "IBC 2018 2406.4.7: 33 in from flight-1a's bottom nosing, 36 in above its landing" in reason


def test_2406_4_6_reach_alone_decides(ifc):
    # Without the landings, the level-1 back window's nearest stair surface is flight 1a's top tread:
    # its bottom edge 6 in above it, but 48 in away, so exempt (36 in or more). Slide that tread to
    # 22 in from the glass and it is caught.
    apt, _, p, _ = ifc
    bare = copy.deepcopy(apt)
    bare["stair"]["parts"] = [x for x in bare["stair"]["parts"] if x["kind"] != "landing"]
    bare["parts"] = [x for x in bare["parts"] if x["kind"] != "landing"]
    assert "1-stair/back/0" not in bidset.safety_glazing(bare, p)
    near = copy.deepcopy(bare)
    step = next(x for x in near["stair"]["parts"] if x["id"] == "flight-1a-4")
    shift = (473 - 22 - 425) * 0.0254
    step["lo_m"][0] += shift
    step["hi_m"][0] += shift
    assert "IBC 2018 2406.4.6: its bottom edge 6 in above flight-1a-4, 22 in from it" in bidset.safety_glazing(near, p)["1-stair/back/0"]


def test_2406_4_7_either_way_a_flight_runs(ifc):
    # The review's case: glass in a wall beside a flight's foot, straddling its bottom nosing, 12 in
    # above the floor. It is within the arc whichever way the flight rises.
    apt, _, p, _ = ifc
    fl = next(f for f in apt["stair"]["flights"] if f["id"] == "flight-1a")
    xb, y = fl["x_bottom_m"], fl["y0_m"]
    o = {"id": "test-window", "kind": "window", "glazed": True, "sill_m": 12 * 0.0254, "width_m": 0.4, "height_m": 1.2,
         "lo_m": [xb - 0.2, y - 0.254, 12 * 0.0254], "hi_m": [xb + 0.2, y, 12 * 0.0254 + 1.2], "outward": [0.0, -1.0, 0.0]}
    walls = np.array([[x["lo_m"], x["hi_m"]] for x in apt["parts"] if x["kind"] in bidset.WALL_KINDS])
    for way in (1.0, -1.0):
        turned = copy.deepcopy(apt)
        next(f for f in turned["stair"]["flights"] if f["id"] == "flight-1a")["dir"] = way
        assert any("2406.4.7" in r for r in bidset._by_the_stair(o, turned, p, walls)), way


def test_each_type_says_which_sections_call_for_its_glazing(ifc):
    _, _, _, path = ifc
    f = ifcopenshell.open(str(path))
    desc = {t.Name: t.Description for t in f.by_type("IfcWindowType") + f.by_type("IfcDoorType")}
    assert "Safety glazing: IBC 2018 2406.4.1 calls for it here." in desc["D1"]
    assert "Safety glazing: IBC 2018 2406.4.2, 2406.4.3 and 2406.4.6 call for it here." in desc["W2"]
    assert "Safety glazing" not in desc["W1"]


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
    assert len(want) == 58 and len(set(want)) == len(want)


def test_what_the_walk_up_carries(ifc, checklist):
    rows = bidset.run_ids(checklist[0], ifc[3])
    carried, fields = bidset.ids_carried(rows)
    assert fields == 34
    assert carried == ["type mark", "storey", "exterior or not", "unit width", "unit height",
                       "U-factor within the code's limit", "fire rating (doors into the stair)",
                       "self-closing (doors into the stair)", "in a wall", "the wall's construction (on exterior walls)"]


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
    assert (applies["safety/IFCWINDOW+hazard"], applies["safety/IFCDOOR+hazard"]) == (26, 12)  # 24 by the doors, 2 over landings
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
    assert applies["escape_height/IFCWINDOW+escape"] == 75  # W1's, not W2's 26



# ---- From the IFC alone: schedule, elevations, quantities (step 4) ----

@pytest.fixture(scope="module")
def drawings(ifc, tmp_path_factory):
    return bidset.write_drawings(ifc[3], tmp_path_factory.mktemp("drawings"))


def test_the_schedule_from_the_ifc_alone(drawings):
    s = {r["mark"]: r for r in drawings["schedule"]}
    assert {m: r["count"] for m, r in s.items()} == {"W1": 75, "W2": 26, "D1": 12, "D2": 1, "D3": 12}
    assert (s["W1"]["width"], s["W1"]["height"], s["D1"]["width"], s["D1"]["height"]) == ("3'-0\"", "4'-0\"", "6'-0\"", "6'-8\"")
    assert (s["W1"]["safety_glazing_required"], s["W2"]["safety_glazing_required"],
            s["D1"]["safety_glazing_required"]) == ("no", "yes (IBC 2018 2406.4.2, IBC 2018 2406.4.3, IBC 2018 2406.4.6)",
                                                    "yes (IBC 2018 2406.4.1)")
    # The flat doors: inside, a 1-hour fire door, self-closing, with no U-factor.
    assert (s["D3"]["is_external"], s["D3"]["fire_rating"], s["D3"]["self_closing"], s["D3"]["u_factor_w_m2k"]) == (
        "False", "1 h", "True", bidset.NOT_IN_MODEL)
    # What the model lacks shows as such, so a rep sees the gap; where a number comes from shows
    # too, so D2's placeholder U-factor reads as one, and our MasterFormat choice as judgement.
    assert all(r["operation"] == r["frame_material"] == r["shgc"] == bidset.NOT_IN_MODEL for r in s.values())
    assert s["D2"]["u_factor_source"] == "params pass3.envelope.door_u (placeholder)"
    assert all(r["masterformat"].endswith("(judgement)") for r in s.values())
    # Every field the IDS asks for has a column.
    for col in ("is_external", "safety_glazing", "clear_opening_area_ft2", "clear_opening_width", "clear_opening_height",
                "clear_opening_sill", "rough_opening", "design_pressure", "escape_window", "install_type"):
        assert col in s["W1"], col
    assert len(drawings["openings"]) == 126
    assert {p.name for p in drawings["written"]} == {"schedule.csv", "openings.csv", "quantities.csv",
                                                     *(f"elevation_{f}.svg" for f in bidset.FACES)}


def test_the_elevations_put_every_opening_where_forge_has_it(ifc, drawings):
    # Seen from outside, left to right: the front (x = 0) runs from y = length down to 0, the back
    # from y = 0 up, the left end (y = 0) from x = 0 (the front) up, the right end from x = depth
    # down. Written out here, not taken from bidset, so a mirrored drawing fails.
    apt = ifc[0]
    ops = {o["id"]: o for o in apt["openings"]}
    w, l = apt["depth_m"], apt["length_m"]
    centre = {"front": lambda a: l - a, "back": lambda a: a, "left": lambda a: a, "right": lambda a: w - a}
    seen = Counter()
    for face, el in drawings["elevations"].items():
        for r in el["rects"]:
            o = ops[r["name"]]
            assert o["face"] == face
            c = centre[face](o["along_m"])
            got = np.array([r["u0"], r["u1"], r["z0"], r["z1"]])
            want = [c - o["width_m"] / 2, c + o["width_m"] / 2, o["panel_lo_m"][2], o["panel_hi_m"][2]]
            assert np.abs(got - want).max() < 1e-3, r["name"]
            seen[r["name"]] += 1
    # Every opening in an outside wall, once; the flat doors, in the stair walls, on none.
    assert seen == Counter(o for o in ops if ops[o]["face"] != "stair")


def test_the_quantities_from_the_ifc_alone(ifc, drawings):
    apt = ifc[0]
    q = drawings["quantities"]
    w, l, h = apt["depth_m"], apt["length_m"], apt["storey_m"] * apt["storeys"]
    assert abs(q["total"]["gross_m2"] - 2 * (w + l) * h) < 1e-6
    outside = [o for o in apt["openings"] if o["face"] != "stair"]
    assert abs(q["total"]["openings_m2"] - sum(o["width_m"] * o["height_m"] for o in outside)) < 1e-6
    assert q["total"]["units"] == 114
    assert set(q["glazed_by_flat_m2"]) == {f["name"] for f in apt["flats"]}
    for f in apt["flats"]:
        assert abs(q["glazed_by_flat_m2"][f["name"]] - f["glazed_m2"]) < 1e-9


def test_the_elevation_svgs_are_well_formed(drawings):
    # The files as written: one titled rectangle per unit on that face.
    import xml.etree.ElementTree as ET

    ns = "{http://www.w3.org/2000/svg}"
    files = {p.stem.removeprefix("elevation_"): p for p in drawings["written"] if p.suffix == ".svg"}
    assert set(files) == set(bidset.FACES)
    for face, path in files.items():
        root = ET.parse(path).getroot()
        titled = [r for r in root.iter(ns + "rect") if r.find(ns + "title") is not None]
        assert len(titled) == len(drawings["elevations"][face]["rects"]) > 0, face


def test_the_drawings_read_an_odd_file_without_crashing(ifc, tmp_path):
    # A file from elsewhere may miss optional attributes or carry values the type doesn't: a
    # window without its width, a rough opening with only a width, a U-factor set on one window
    # over its type's, a material layer set, a storey name with an ampersand. All of it reads,
    # and differences show as "varies".
    import ifcopenshell.api.material as material
    import ifcopenshell.api.pset as pset

    f = ifcopenshell.open(str(ifc[3]))
    w1 = [w for w in f.by_type("IfcWindow") if ue.get_type(w).Name == "W1"]
    w1[0].OverallWidth = None
    w2 = next(t for t in f.by_type("IfcWindowType") if t.Name == "W2")
    ours = pset.add_pset(f, product=w2, name="BidSet_Unit")
    pset.edit_pset(f, pset=ours, properties={"RoughOpeningWidth": f.createIfcLengthMeasure(0.94)})
    own = pset.add_pset(f, product=w1[1], name="Pset_WindowCommon")
    pset.edit_pset(f, pset=own, properties={"ThermalTransmittance": 1.2})
    d2 = next(t for t in f.by_type("IfcDoorType") if t.Name == "D2")
    layers = material.add_material_set(f, name="steel door, insulated core", set_type="IfcMaterialLayerSet")
    material.add_layer(f, layer_set=layers, material=material.add_material(f, name="steel"))
    material.assign_material(f, products=[d2], material=layers)
    f.by_type("IfcBuildingStorey")[0].Name = "Level 1 & mezzanine"
    odd = tmp_path / "odd.ifc"
    f.write(str(odd))
    d = bidset.write_drawings(odd, tmp_path / "drawings")
    s = {r["mark"]: r for r in d["schedule"]}
    assert s["W1"]["width"].startswith("varies") and bidset.NOT_IN_MODEL in s["W1"]["width"]
    assert s["W2"]["rough_opening"] == f"3'-1\" x {bidset.NOT_IN_MODEL}"
    assert s["W1"]["u_factor_w_m2k"].startswith("varies") and "1.2" in s["W1"]["u_factor_w_m2k"]
    assert s["D2"]["frame_material"] == "steel door, insulated core"
    assert d["quantities"]["unsized"] == 1
    import xml.etree.ElementTree as ET
    for p in d["written"]:
        if p.suffix == ".svg":
            ET.parse(p)  # the ampersand is escaped


def test_the_drawings_leave_out_units_in_walls_that_arent_exterior(ifc, tmp_path):
    # A window or door in an interior wall isn't on any facade: mark one exterior wall interior,
    # and its units join the flat doors as "interior", on no elevation.
    import ifcopenshell.api.pset as pset

    f = ifcopenshell.open(str(ifc[3]))
    wall = next(w for w in f.by_type("IfcWall") if w.Name == "ext-front-2")
    hosted = sum(1 for e in list(f.by_type("IfcWindow")) + list(f.by_type("IfcDoor")) if bidset._host_wall(e) == wall)
    ps = next(r.RelatingPropertyDefinition for r in wall.IsDefinedBy if r.RelatingPropertyDefinition.Name == "Pset_WallCommon")
    pset.edit_pset(f, pset=ps, properties={"IsExternal": False})
    inner = tmp_path / "inner.ifc"
    f.write(str(inner))
    rb = bidset.read_back(inner)
    assert len(rb["units"]) == 126
    assert hosted > 0 and sum(u["face"] == "interior" for u in rb["units"]) == 12 + hosted
    assert sum(len(bidset.elevation(rb, face)["rects"]) for face in bidset.FACES) == 114 - hosted
