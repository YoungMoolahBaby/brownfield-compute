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


def test_the_frame_is_built_on_step_6s_hatch(apt, P):
    h = fire.roof_access(apt, P)
    words = routing.hatch_command(apt, P).split()
    assert [float(x) * IN for x in words[-4:]] == pytest.approx([*h["lo"], *h["hi"]], abs=1e-6)


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
