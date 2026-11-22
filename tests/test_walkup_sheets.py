"""Pass 3g step 8a (D28): the services drawn as sheets (`brownfield.servicesheets`)."""
import math

import numpy as np
import pytest

from brownfield import routed, servicesheets as ss, systems
from brownfield.params import load_params, values

PUBLISHED = [ss.BIDSET / f"{k}-{ss.REV}.ifc" for k in ("apartment", "services", "framing")]
BANDS = [(1, -math.inf, 2.74), (2, 2.74, 5.79), (3, 5.79, 9.14), ("roof", 9.14, math.inf)]


def _rec(system, run="", flat="", key="run/x/0", sweep=None):
    r = {"props": {"System": system, "Run": run, "Flat": flat, "Key": key}, "key": key, "sweep": sweep, "box": None, "cls": "IfcPipeSegment"}
    r["tag"] = ss.tag(r)
    return r


# ---- Synthetic: no files needed ----

def test_each_run_takes_its_systems_tag():
    assert [ss.tag(_rec(s, run)) for s, run in [
        ("cold", "plumbing/cold/1-front-left"), ("hot", "main/hot"), ("hot", "main/hot-return"), ("hot", "front-left/hot-return"),
        ("drain", "plumbing/drain/1-front-left/wc"), ("vent", "front-left/vent-stack"), ("condensate", "hvac/condensate/1-front-left"),
        ("loop", "main/loop-supply"), ("loop", "hvac/loop-return-tail/2-back-left"), ("ventilation", "hvac/erv-oa/1-front-left"),
        ("ventilation", "hvac/erv-ea/1-front-left"), ("ventilation", "hvac/erv-supply/1-front-left"),
        ("ventilation", "hvac/erv-exhaust/1-front-left"), ("air", "hvac/ms-supply/1-front-left"), ("refrigerant", "hvac/line-set/1-front-left"),
        ("power", "electrical/feeder/3-back-right"), ("power", "front-left/feeder/3-front-left"), ("power", "electrical/branch/1-front-left/range"),
        ("sprinkler", "fire/flat/1-front-left")]] == [
        "CW", "HW", "HWR", "HWR", "SAN", "V", "CD", "HS", "HR", "OA", "EA", "VS", "EX", "SA", "RL", "F", "F", "BC", "SP"]
    assert set(ss.TAGS) >= {"CW", "HW", "HWR", "SAN", "V", "CD", "HS", "HR", "OA", "EA", "VS", "EX", "SA", "RL", "F", "BC", "SP"}


def test_a_runs_tag_reads_as_the_trade_writes_it():
    r = _rec("refrigerant", "hvac/line-set/1-front-left")
    r["props"]["Size"] = "1/4 and 3/8"
    assert ss.label_text(r) == 'RL 1/4"+3/8"'
    r = _rec("power", "electrical/branch/1-front-left/range")
    r["props"].update({"Size": "8", "Circuit": "range"})
    assert ss.label_text(r) == "range 8 AWG"
    r = _rec("cold", "plumbing/cold/1-front-left")
    r["props"]["Size"] = "3/4"
    assert ss.label_text(r) == '3/4" CW'


def test_a_flats_runs_go_on_its_own_storeys_plan():
    # A level 1 flat's sprinkler pipe in the joist space above its ceiling, and a level 2 flat's
    # drain in the same joist space: each on its own flat's plan, not by the height alone.
    sprinkler = _rec("sprinkler", "fire/flat/1-front-left", flat="1-front-left")
    drain = _rec("drain", "plumbing/drain/2-front-left/wc", flat="2-front-left")
    assert ss.band_of(2.9, BANDS) == 2
    assert ss.level_of(sprinkler, 2.9, BANDS) == 1 and ss.level_of(drain, 2.9, BANDS) == 2
    # Under the ground slab: Level 1, whoever's it is (an upper flat's feeder); on the roof: the roof.
    feeder = _rec("power", "electrical/feeder/3-back-right", flat="3-back-right")
    assert ss.level_of(feeder, -0.3, BANDS) == 1
    line_set = _rec("refrigerant", "hvac/roof-line-set/1-front-left", flat="1-front-left")
    assert ss.level_of(line_set, 9.8, BANDS) == "roof"
    # A main or the stair's riser, with no flat: by the storey it's in.
    riser = _rec("sprinkler", "stair/fire-riser", key="pinned/stair/fire-riser")
    assert [ss.level_of(riser, z, BANDS) for z in (1.0, 4.0, 7.0)] == [1, 2, 3]


def test_a_pieces_straight_runs_and_risers():
    r = _rec("cold", sweep=[[0, 0, 0], [2, 0, 0], [2, 0, 3], [2, 1, 3.02]])
    parts = list(ss.segments(r))
    assert [v for _, _, v in parts] == [False, True, False]  # a 2% slope is still a run, not a riser
    r = _rec("cold", sweep=[[0, 0, 0], [0, 0, 0], [1, 0, 0]])
    assert len(list(ss.segments(r))) == 1  # a repeated point draws nothing


def test_the_plan_has_the_front_at_the_top_and_the_left_end_at_the_left():
    bld = {"lo": np.array([0.0, 0.0, 0.0]), "hi": np.array([12.0, 30.0, 9.5])}
    T = ss.PlanT(bld)
    (x0, y_front), (_, y_back) = T(0.0, 0.0), T(12.0, 0.0)
    (x_right, _) = T(0.0, 30.0)
    assert y_front > y_back and x_right > x0
    assert x_right - x0 == pytest.approx(30.0 * ss.S) and y_front - y_back == pytest.approx(12.0 * ss.S)
    # 1/4" = 1'-0": 48 ft of building is a foot of sheet.
    assert 48 * 0.3048 * ss.S == pytest.approx(12.0)


def test_labels_never_overlap_and_say_what_they_left_off():
    import matplotlib

    matplotlib.use("Agg")
    fig, ax = ss._figure()
    L = ss.Labels(ax)
    assert L.place("1-1/4\" CW", 10, 10)
    assert L.place("1-1/4\" CW", 10, 10)  # moved off the first
    for _ in range(10):
        L.place("1-1/4\" CW", 10, 10)
    a = L.boxes
    assert all(x1 <= c or x0 >= e or y1 <= d or y0 >= f for i, (x0, y0, x1, y1) in enumerate(a) for (c, d, e, f) in a[i + 1:])
    assert L.placed + L.skipped == 12 and L.skipped > 0
    import matplotlib.pyplot as plt
    plt.close(fig)


def test_the_set_is_indexed_once_each_by_discipline():
    sheets = ss.sheet_list()
    numbers = [n for n, _ in sheets]
    assert len(numbers) == len(set(numbers)) == 21
    assert numbers[0] == "G-001"
    assert [n.split("-")[0] for n in numbers] == sorted([n.split("-")[0] for n in numbers], key=["G", "P", "M", "E", "FP"].index)
    for trade in ("P", "M", "E", "FP"):
        assert {f"{trade}-101", f"{trade}-102", f"{trade}-103"} <= set(numbers)


# ---- On the published files ----

@pytest.fixture(scope="module")
def drawn(tmp_path_factory):
    if not all(p.exists() for p in PUBLISHED):
        pytest.skip("the published models aren't there (docs/pass3/bidset)")
    P = values(load_params())
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    ctx = ss.context(apt, P, routes=routes)
    path = tmp_path_factory.mktemp("sheets") / ss.PDF_NAME
    res = ss.write(ctx, path)
    return ctx, res, path


def test_every_element_is_on_a_sheet_and_the_pdf_reads_as_text(drawn):
    ctx, res, path = drawn
    assert [label for label, ok, _ in ss.checks(ctx, res, path) if not ok] == []


def test_each_trades_plan_draws_its_own_layer_and_the_elevations_every_trade(drawn):
    ctx, res, _ = drawn
    rb = {r["key"]: r for r in ctx["rb"]}
    # Every piece of every layer is somewhere: the plans and the walls between them.
    layers = {rb[k]["props"].get("Layer") for k in res["drawn"]}
    assert layers == {"plumbing", "hvac", "electrical", "sprinklers"}
    # Each storey's plans hold tags; most tags placed on every plan.
    for n, (placed, skipped) in res["tags"].items():
        assert placed > 0, n
        assert placed >= 0.6 * (placed + skipped), n


def test_the_sheets_repeat_byte_for_byte(drawn, tmp_path):
    ctx, _, _ = drawn
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    ss.write(ctx, a, ["E-601", "FP-601"])
    ss.write(ctx, b, ["E-601", "FP-601"])
    assert a.read_bytes() == b.read_bytes()
