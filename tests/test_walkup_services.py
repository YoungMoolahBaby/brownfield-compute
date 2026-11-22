"""Pass 3g step 7d (D28): the services as IFC and their schedules (`brownfield.servicesifc`)."""
import math

import numpy as np
import pytest

from brownfield import routing, servicesifc as sv, systems
from brownfield.params import load_params, values
from brownfield.routecheck import ROUTES, penetration_hits

IN = 0.0254


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


def _tree(branches, system="sprinkler", slope=0.0, root=(0.0, 0.0, 0.0)):
    from brownfield.routed import Tree

    req = {"id": "t", "system": system, "root": list(root), "snap_m": 0.05, "goals": [], "slope": slope, "od_m": 0.03}
    rec = {"ok": True, "branches": [{"terminal": t, "points": [list(q) for q in pts], "to": list(to or pts[-1]), "bores": []}
                                    for t, pts, to in branches]}
    return req, Tree(req, rec)


def test_a_tree_cut_into_pieces_keeps_every_metre_once():
    # A trunk to `a` with a bend, `b` teeing off it 2 m out, `a`'s terminal 5 cm past its last cell.
    req, t = _tree([("a", [(0, 0, 0), (4, 0, 0), (4, 3, 0)], (4, 3.05, 0)), ("b", [(2, 0, 0), (2, -2, 0)], None)])
    pieces = [t.piece(n) for n in range(len(t.edges))]
    assert [round(sv.polyline_m(q), 9) for q in pieces] == [round(e.length, 9) for e in t.edges]
    assert sum(sv.polyline_m(q) for q in pieces) == pytest.approx(t.length_m)
    # Each piece starts where the last ended or where it tees off.
    assert pieces[1][0] == pieces[0][-1] and pieces[2][0] == pytest.approx([2, 0, 0])
    # The bend is on the trunk's second piece, at the corner forge routed.
    assert [b[1] for n in range(3) for b in sv._bends_at(t, n)] == [[4.0, 0.0, 0.0]]


def test_each_material_takes_its_fittings():
    branches = [("a", [(0, 0, 0), (4, 0, 0), (4, 3, 0)], None), ("b", [(2, 0, 0), (2, -2, 0)], None)]
    kinds = {}
    for system in ("sprinkler", "water", "duct", "cable", "line-set"):
        req, t = _tree(branches, system)
        req["role"] = "ms-supply" if system == "duct" else "cold"
        kinds[system] = sorted(f["kind"] for n in range(len(t.edges)) for f in sv.fittings(req, t, n, 1.0, False))
    # CPVC: an elbow at the bend, a tee where b leaves.
    assert kinds["sprinkler"] == ["90° elbow", "tee"]
    # PEX bends on a support (counted on the piece), a tee, and an elbow at each fixture's stub-out.
    assert kinds["water"] == ["elbow", "elbow", "tee"]
    # A duct: an elbow, a take-off, a boot at each outlet; cable and soft copper: nothing.
    assert kinds["duct"] == ["90° elbow", "boot", "boot", "take-off"]
    assert kinds["cable"] == [] and kinds["line-set"] == []


def test_a_drains_fittings_follow_ipc_table_706_3():
    down, along = np.array([0, 0, -1.0]), np.array([1.0, 0, 0])
    assert sv.dwv_bend(along, down).startswith("quarter bend")  # horizontal to vertical
    assert sv.dwv_bend(down, along).startswith("long sweep")  # vertical to horizontal
    assert sv.dwv_bend(along, np.array([0, 1.0, 0])).startswith("long sweep")  # horizontal to horizontal
    assert sv.dwv_junction(along, down).startswith("sanitary tee")  # a branch into a stack
    assert sv.dwv_junction(along, along).startswith("combination wye")


def test_the_firestop_rules_of_ibc_714():
    # Through a floor/ceiling in a wall's cavity: listed, F 1 h, T waived (714.5.1.2 exception 1).
    c = sv.firestop_condition("through", True, "PEX", True, False, True)
    assert c["F"] == "1 h" and c["T"].startswith("not required") and "714.3" in c["asks"]
    # Plastic through the open ceiling: F and T 1 h; iron there needs only its annular space protected.
    assert sv.firestop_condition("membrane", True, "CPVC", False, False, False)["T"] == "1 h"
    assert sv.firestop_condition("membrane", True, "cast iron", False, False, False)["asks"].startswith("the annular space")
    # A tub drain in the floor's space needs no T (exception 2); a wall asks F only; unrated, fireblocking.
    assert "exception 2" in sv.firestop_condition("floor side", True, "PVC", False, True, False)["T"]
    assert sv.firestop_condition("wall", True, "CPVC", False, False, False)["T"] == ""
    assert sv.firestop_condition("the roof", False, "CPVC", False, False, False)["asks"].startswith("fireblocking")


def test_a_riser_through_a_floor_is_one_opening_and_the_top_storeys_ceiling_is_unrated(apt):
    # A vertical in a plumbing wall from the ground to the roof: it crosses each floor and the
    # ceiling under it (two faces, one through-penetration each), and the top storey's ceiling.
    w = next(x for x in apt["rooms"]["walls"] if x["id"].endswith("/plumbing-wall"))
    x, y = (w["lo_m"][0] + w["hi_m"][0]) / 2, (w["lo_m"][1] + w["hi_m"][1]) / 2
    hits = penetration_hits(apt, [([x, y, 0.1], [x, y, apt["storeys"] * apt["storey_m"] + 0.3])])
    rows = [{"key": "r", "where": h["where"], "storey": h["storey"], "rated": h["rated"], "unrated": h["unrated"], "system": "cold",
             "family": "PEX", "size": "1", "insulated": False, "od_in": 1.1, "run": "r", "in_wall": True, "tub": False,
             "x": h["at"][0], "y": h["at"][1], "z": h["at"][2]} for h in hits]
    ops = sv.openings(rows)
    assert sorted(o["kind"] for o in ops) == ["the roof"] + ["through"] * (apt["storeys"] - 1)


def test_feeder_bends_count_the_turns_up_at_each_end(P):
    # Under the slab with one square bend, turning up at both ends: 270 degrees; with three, 450
    # (over 352.26's 360); straight with one 30 degree turn, 210. A 3 cm jog where it snapped to its
    # terminal is no bend.
    def feeder(pts):
        return {"props": {"Key": f"run/electrical/feeder/{len(pts)}/0", "Flat": str(len(pts))}, "sweep": pts}
    square = [[0, 0, -0.4], [1, 0, -0.4], [1, 1, -0.4], [2, 1, -0.4], [2, 2, -0.4]]
    skew = [[0, 0, -0.4], [2, 0, -0.4], [2 + 3 ** 0.5, 1, -0.4], [2 + 3 ** 0.5 + 0.02, 1.02, -0.42]]
    got = {b["flat"]: b for b in sv.conduit_bends([feeder(square[:3]), feeder(square), feeder(skew)], P)}
    assert [got[k]["degrees"] for k in ("3", "5", "4")] == pytest.approx([270, 450, 210])
    assert [got[k]["ok"] for k in ("3", "5", "4")] == [True, False, True]


def test_nominal_sizes_as_the_trade_writes_them():
    assert [sv.nominal(x) for x in (0.5, 0.75, 1.0, 1.25, 2.5, 4.0)] == ["1/2", "3/4", "1", "1-1/4", "2-1/2", "4"]
    assert [sv.size_in(s) for s in ("1/2", "1-1/4", "3", "12 AWG")] == [0.5, 1.25, 3.0, None]


ROUTED = pytest.mark.skipif(not ROUTES.exists() or not routing.FRAME.exists(),
                            reason="no forge routes yet (`brownfield routes --requests`, forge's `routes-json`)")


@ROUTED
def test_the_services_model_holds_every_route_where_forge_has_it(apt, P, tmp_path):
    from brownfield import routed

    routes = routed.load(apt, P)
    if not routes.fresh:
        pytest.skip(f"routes stale: {routes.why}")
    s = sv.run(apt, P, out=tmp_path)
    assert [label for label, ok, _ in s["checks"] if not ok] == []
    # Every routed run's length is in the lengths schedule, read back from the file.
    sch = s["schedules"]
    routed_m = sum(routes.tree(k).length_m for k in routes.recs)
    assert sum(r["m"] for r in sch["lengths"] if r["class"] != "IfcPipeFitting") >= routed_m - 1.0
    # Every sprinkler and every water-level switch is in the model.
    assert len(sch["sprinklers"]) == sum(len(routes.tree(k).terminals()) - (4 if k.startswith("fire/stair/") else 0)
                                         for k in routes.recs if k.startswith(("fire/flat/", "fire/stair/")))
    assert len(sch["switches"]) == len(apt["flats"])
    assert math.isclose(sum(o["rated"] for o in sch["openings"]), sum(r["count"] for r in sch["firestop"] if r["F"]))
