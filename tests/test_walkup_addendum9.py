"""Addendum 9 (found in pass 3g step 10d, D28): the water pipes held off the frame (`baseline.pipe_isolation`,
section 22 05 29) and the ERV's sound, on G-001 reissued alone. The synthetic tests never skip; the run
on the model and the routes skips when they're absent."""
import math
from types import SimpleNamespace

import pytest

from brownfield import baseline as bl, servicesheets, systems
from brownfield.params import load_params, values

IN, FT = 0.0254, 0.3048
PEX = "PEX-a with cold-expansion fittings (Uponor ProPEX EP)"


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def _seg(rid: str, system: str, size: str, ft: float, holes: int, material: str = PEX) -> dict:
    return {"cls": "IfcPipeSegment", "props": {"Key": f"run/{rid}/0", "System": system, "Material": material, "Size": size,
                                              "Length": ft * FT, "Holes": holes}}


def _routes(bores: dict[str, list[tuple[float, float | None]]]) -> SimpleNamespace:
    """Routes whose runs bore these holes, (hole, allowed) in inches."""
    return SimpleNamespace(recs={rid: {"branches": [{"bores": [{"kind": "floor joists", "member": f"{rid}#{i}", "hole_m": h * IN,
                                                                 "allowed_m": None if a is None else a * IN} for i, (h, a) in enumerate(b)]}]}
                                 for rid, b in bores.items()})


def test_a_cold_hole_bored_for_its_insulation_takes_the_sleeve_and_a_bare_one_is_caught(P):
    rb = [_seg("plumbing/cold/1-a", "cold", "1", 10.0, 1)]
    # 1 in. PEX (1.125 in.) in 1/2 in. of insulation, the hole a 1/4 in. over: the sleeve (2.125) goes through as bored.
    fine = bl.pipe_isolation(rb, _routes({"plumbing/cold/1-a": [(2.375, 3.0)]}), P)
    assert not fine["bad"] and fine["holes"] == {"cold": 1, "hot": 0} and fine["cold_holes"] == 1
    bare = bl.pipe_isolation(rb, _routes({"plumbing/cold/1-a": [(1.375, 3.0)]}), P)
    assert len(bare["bad"]) == 1  # bored for the bare pipe: the sleeve can't pass


def test_a_hot_hole_takes_the_isolator_within_its_member_and_a_sleeve_would_overfill_it(P):
    rb = [_seg("plumbing/hot/1-a", "hot", "1", 5.0, 2), _seg("plumbing/hot-return/1-a", "hot", "1/2", 5.0, 1)]
    ok = bl.pipe_isolation(rb, _routes({"plumbing/hot/1-a": [(1.375, 2.0), (1.375, 3.0)], "plumbing/hot-return/1-a": [(0.875, 2.0)]}), P)
    assert not ok["bad"] and ok["isolators"] == {"1": 2, "1/2": 1}
    # The 1 in. pipe's isolator takes a 2 in. hole; the 1/2 in.'s, 1-3/8.
    need = {x["run"]: x["need_in"] for x in ok["fit"]}
    assert need["plumbing/hot/1-a"] == P["baseline.sleeves.isolator_hole_large_in"]
    assert need["plumbing/hot-return/1-a"] == P["baseline.sleeves.isolator_hole_small_in"]
    # A sleeve on the 1 in. pipe (2.125 in., and the hole's 1/4 in.) would overfill the 2 in. joist hole, not the 3 in. one.
    assert ok["sleeve_over"] == 1
    tight = bl.pipe_isolation(rb, _routes({"plumbing/hot/1-a": [(1.375, 1.75), (1.375, 3.0)], "plumbing/hot-return/1-a": [(0.875, 2.0)]}), P)
    assert [x["member"] for x in tight["bad"]] == ["plumbing/hot/1-a#0"]


def test_hangers_fill_the_spacing_the_holes_dont(P):
    s = P["baseline.sleeves.support_ft_small"]
    rb = [_seg("plumbing/cold/1-a", "cold", "1", 10.0, 1), _seg("plumbing/cold/1-b", "cold", "1", 10.0, 9),
          _seg("main/cold", "cold", "1-1/2", 30.0, 2, material="PEX-a, pre-insulated under the slab (Uponor ProPEX EP fittings)")]
    iso = bl.pipe_isolation(rb, _routes({}), P)
    assert iso["hangers"] == math.ceil(10.0 / s) - 1  # the second run's holes are close enough; the slab's main isn't counted
    assert iso["sleeves"] == iso["hangers"] + 10 and iso["ft"] == pytest.approx(20.0)


def test_g001_is_reissued_alone_by_addendum_9_and_sizes_read_as_the_trade_writes_them():
    rev, name = servicesheets.REVISED["G-001"]
    assert rev == "Addendum 9" and name == "services-sheet-g-001-addendum-9.pdf"
    assert servicesheets.REVISED["G-002"][0] == "Addendum 8"
    assert [servicesheets.inches(x) for x in (1.375, 2.0, 0.5, 2.125)] == ["1-3/8", "2", "1/2", "2-1/8"]
    assert systems.TITLES[9] and 9 in systems.ISSUED


def test_the_section_states_the_spacing_and_the_counts(P):
    iso = {"ft": 2417.0, "hangers": 348, "holes": {"cold": 308, "hot": 452}, "sleeve_over": 56, "sleeves": 656,
           "isolators": {"1": 132, "1/2": 170, "3/4": 150}}
    text = systems.section_22_05_29(P, iso)
    assert text.startswith("# 22 05 29")
    for s in ("2.67 ft (32 in.)", "Table 308.5", "1-3/8 in. for 1/2 and 3/4 in. pipe", "2 in. for 1 in. pipe", "656 sleeves",
              "452 isolators", "170 for 1/2 in. pipe, 150 for 3/4 in. pipe, 132 for 1 in. pipe", "overfill 56"):
        assert s in text, s


# ---- On the model and the routes ----

@pytest.fixture(scope="module")
def routes(P):
    from brownfield import routed

    if not bl.SERVICES.exists():
        pytest.skip("the services model isn't published")
    r = routed.load(systems.load(systems.latest_model()), P)
    if r is None or not r.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    return r


def test_every_hole_of_the_water_pipe_takes_its_sleeve_or_isolator(routes, P):
    from brownfield.servicesifc import read_back

    iso = bl.pipe_isolation(read_back(bl.SERVICES), routes, P)
    assert iso["fit"] and not iso["bad"]
    assert iso["cold_holes"] == iso["holes"]["cold"] and sum(iso["isolators"].values()) == iso["holes"]["hot"]
    assert iso["sleeve_over"] > 0  # why the hot pipe's holes take isolators
