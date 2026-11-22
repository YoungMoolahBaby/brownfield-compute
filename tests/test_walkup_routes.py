"""Pass 3g step 7 (D28): the services placed and routed through the frame (`brownfield.routing`)."""
import pytest

from brownfield import electrical, fire, routing, systems
from brownfield.params import load_params, values

IN = 0.0254
pytestmark = pytest.mark.skipif(not routing.FRAME.exists(), reason="forge's Addendum 5 frame not written (`brownfield routes` prints the command)")


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


@pytest.fixture(scope="module")
def S(apt, P):
    return routing.summary(apt, P)


def test_every_step_7a_check_passes(S):
    assert [label for label, ok, _ in S["checks"] if not ok] == []


def test_the_frame_is_built_on_step_6s_hatch_and_the_soffits(apt, P):
    h = fire.roof_access(apt, P)
    i = routing.inputs(apt, P)
    assert i["hatch_m"] == pytest.approx([*h["lo"], *h["hi"]], abs=1e-6)
    # Six a flat (hall, passage, utility, kitchen, the hall's reach over the bath, the living room's
    # strip), and the strip's leg on the middle storey, whose termination is a pier past the kitchen.
    assert len([s for s in i["soffits"] if not s["id"].endswith("leg")]) == 6 * len(apt["flats"])
    assert sorted(s["id"].split("/")[0] for s in i["soffits"] if s["id"].endswith("leg")) == sorted(f["name"] for f in apt["flats"] if f["floor"] == 2)


def test_conduit_fill_against_the_code_tables(P):
    # NEC Chapter 9: three 500 kcmil THHN (Table 5, 0.7073 in2 each) are 2.122 in2; at Table 1's 40%,
    # 2-1/2 in. Schedule 40 PVC holds 1.878 (Table 4), 3 in. 2.907: so 3 in. (ECM's Code Q&A, the same tables).
    assert electrical.conduit_for(["500"] * 3, P)["trade"] == "3"
    # One conductor may fill 53%, two 31%.
    assert electrical.conduit_for(["4/0"], P)["fill"] <= 0.53 and electrical.conduit_for(["4/0", "4/0"], P)["fill"] <= 0.31


def test_a_water_closet_off_its_bay_would_be_caught(apt, P, S):
    fr = routing.load_frame(apt, P)
    fx = {n: {k: dict(v) for k, v in f.items()} for n, f in S["design"]["fixtures"].items()}
    bad = fx["2-front-left"]["wc"]
    js = routing.joists_under(fr, apt, 2, bad["x"] + bad["into"] * bad["out_m"])
    bad["y"] = next((a + b) / 2 for a, b in js if a > bad["y"])  # on the next joist
    assert not routing.fixture_checks(apt, P, fr, fx)[0][1]


def test_the_terminations_need_fixed_windows(apt, P, S):
    t = [dict(x, fixed=[]) for x in S["design"]["terminations"]]
    assert not routing.termination_checks(apt, P, t)[1][1]
    assert len({f for x in S["design"]["terminations"] for f in x["fixed"]}) == 2 * len(apt["flats"])


def test_no_escape_window_is_fixed(apt, P, S):
    escape = {w["id"] for w in systems.escape_windows(apt, P).values() if w}
    fixed = {f for x in S["design"]["terminations"] for f in x["fixed"]}
    assert escape and not escape & fixed


# ---- 7b: forge's routes, and the checks on them ----

FT = 0.3048


def test_apas_chart_as_the_checks_read_it(P):
    from brownfield.routecheck import apa_allowed
    from brownfield.routes import _apa_rows

    rows = [(a * IN, b * IN) for a, b in _apa_rows()]
    saf, edge, anyh = P["systems.routing.apa_saf_in"] * IN, P["systems.routing.apa_min_edge_in"] * IN, P["systems.routing.apa_any_hole_in"] * IN
    full = 20 * FT
    # Table 5's PRI-60 11-7/8 in. row: 2 in. at 7 in., 3 at 21, 4 at 36, 6 at 69, 8-5/8 at 118; rule 9's 1-1/2 in. anywhere.
    for d_in, hole_in in ((0, 1.5), (6.9, 1.5), (7, 2), (21, 3), (36, 4), (69, 6), (118, 8.625)):
        assert apa_allowed(d_in * IN, full, rows, saf, edge, anyh) == pytest.approx(hole_in * IN)
    # Note e on a 10 ft span: 52 in. x 120/214 = 29.2 in. for 5 in., so 5 in. at 36 in., not 6 (69 x 0.56 = 38.7).
    assert apa_allowed(36 * IN, 10 * FT, rows, saf, edge, anyh) == pytest.approx(5 * IN)


def test_rule_6_and_the_grades_on_known_cases():
    from brownfield.routecheck import grade_miss, rule6

    d = 2 * IN
    # Two 2 in. holes across a web (along y): edges must be over 4 in. apart, so centres over 6 in.
    assert rule6([([0.0, 0.5, 0.15], d, 1), ([6.5 * IN, 0.5, 0.15], d, 1)]) > 0
    assert rule6([([0.0, 0.5, 0.15], d, 1), ([5.5 * IN, 0.5, 0.15], d, 1)]) < 0
    # Stacked in the web's plane counts the same way; apart along the bore axis doesn't count.
    assert rule6([([0.0, 0.5, 0.10], d, 1), ([0.0, 0.5, 0.10 + 5.5 * IN], d, 1)]) < 0
    assert rule6([([0.0, 0.5, 0.15], d, 1)]) is None
    s = 0.25 / 12
    # A drain going out from its stack must rise by its slope; a level one misses by slope x run.
    assert grade_miss([[0, 0, 0.0], [1.2, 0, s * 1.2], [1.2, 0, 0.5]], s, False) == pytest.approx(0, abs=1e-12)
    assert grade_miss([[0, 0, 0.0], [1.2, 0, 0.0]], s, False) == pytest.approx(s * 1.2)
    # A vent going out from its stack must fall by its slope; one rising misses by that and more.
    assert grade_miss([[0, 0, 0.5], [2.0, 0, 0.5 - s * 2.0], [2.0, 0, 0.0]], s, True) == pytest.approx(0, abs=1e-12)
    assert grade_miss([[0, 0, 0.5], [2.0, 0, 0.51]], s, True) == pytest.approx(0.01 + s * 2.0)


def test_a_clash_is_caught_and_an_attached_one_isnt():
    from brownfield.routecheck import clash_pairs

    def req(i, attach=()):
        return {"id": i, "od_m": 0.05, "clear_m": 0.0, "attach": list(attach), "system": "water"}

    body = {"requests": [req("a"), req("b"), req("c", ["a"])], "obstacles": [{"id": "x/riser", "lo": [0.9, -0.1, -0.1], "hi": [1.1, 0.1, 0.1]}],
            "clash_tol_m": 0.001}
    rt = {"routes": [{"id": "a", "branches": [{"points": [[0, 0, 0], [2, 0, 0]]}]},
                     {"id": "b", "branches": [{"points": [[0.5, -1, 0], [0.5, 1, 0]]}]},
                     {"id": "c", "branches": [{"points": [[1.5, -1, 0], [1.5, 1, 0]]}]}]}
    # a crosses b and runs through the pinned riser; c crosses a but is attached to it (a tee).
    assert clash_pairs(body, rt) == [("a", "b"), ("a", "x/riser")]


def test_a_row_of_sprinklers_shares_its_slack_off_the_strip():
    from brownfield.routes import _row

    # The middle storey's living room (2-back-left): 5.94 to 13.59 m along y, two sprinklers listed at
    # 14 ft; the upper one put 4 in. past the strip's far side (12.138 m). The lower must then be
    # within 14 ft of it and within 7 ft of its wall: 7.871 to 8.074 m, so it moves to 7.871.
    L, smin = 14 * FT, 8 * FT
    row = _row([7.855, 11.678], {1: 12.138}, 5.94, 13.59, L, smin)
    assert row[1] == pytest.approx(12.138) and row[0] == pytest.approx(12.138 - L)
    # Past the far side the slack runs out: no such row.
    assert _row([7.855, 11.678], {1: 12.5}, 5.94, 13.59, L, smin) is None


def test_the_two_ducts_round_the_legs_corner_in_lanes_that_dont_meet(apt, P):
    from brownfield.routes import _lanes, soffit_zones
    from brownfield.routing import soffits, terminations

    sf = soffits(apt, P, terminations(apt, P))
    for name in ("2-back-left", "2-front-right"):
        strip = next(x for x in sf if x["id"] == f"{name}/soffit-strip")
        leg = next(x for x in sf if x["id"] == f"{name}/soffit-strip-leg")
        t = next(x for x in terminations(apt, P) if x["flat"] == name)
        zones = soffit_zones(apt, name, sf)
        inside = -1.0 if (leg["lo"][1] + leg["hi"][1]) / 2 < t["y"] else 1.0
        a = _lanes(zones, strip, leg, inside, t["face"] == "back", True)[-3:]
        b = _lanes(zones, strip, leg, inside, t["face"] == "back", False)[-2:]
        for u in a:
            for v in b:
                assert any(min(u["hi"][i], v["hi"][i]) - max(u["lo"][i], v["lo"][i]) < 1e-6 for i in range(3)), (name, u, v)


ROUTED = pytest.mark.skipif(not __import__("brownfield.routecheck", fromlist=["ROUTES"]).ROUTES.exists(),
                            reason="forge's routes not written (`brownfield routes --requests`, then `cargo run --release -- routes-json` in forge/)")


@ROUTED
def test_every_step_7b_check_passes_on_forges_routes(apt, P):
    from brownfield import routecheck

    body, rt, sha = routecheck.load(apt, P)
    if rt.get("requests_sha") != sha:
        pytest.skip("forge's routes answer older requests: rerun `cargo run --release -- routes-json` in forge/")
    ch = routecheck.checks(apt, P, body, rt, routing.load_frame(apt, P), sha)
    assert [label for label, ok, _ in ch if not ok] == []
