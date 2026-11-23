"""Pass 3g step 10a (D28): the usual walk-up from sources, and what each walk-up has
(`brownfield.baseline`). The synthetic tests never skip; those on the published model, the routes and
the downloaded sources skip when they're absent."""
import copy

import numpy as np
import pandas as pd
import pytest

from brownfield import baseline as bl
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def test_each_run_of_the_model_goes_to_the_walk_ups_that_have_it():
    w = bl.walkups_of
    assert w({"System": "cold", "Run": "plumbing/cold/1-front-left"}) == bl.ALL
    assert w({"System": "hot", "Run": "plumbing/hot-return/1-front-left"}) == bl.LOOPS  # a central plant's loops
    assert w({"System": "loop", "Run": "main/loop-supply"}) == bl.ENG
    assert w({"System": "ventilation", "Run": "hvac/erv-oa/1-front-left"}) == bl.ENG
    assert w({"System": "drain", "Run": "plumbing/drain/1-front-left/branch"}) == bl.ENG  # cast iron; the PVC twin apart
    assert w({"System": "power", "Run": "electrical/branch/1-front-left/preheater"}) == bl.ENG
    assert w({"System": "power", "Run": "electrical/branch/1-front-left/range"}) == bl.ALL
    with pytest.raises(ValueError):
        w({"System": "steam", "Run": "x"})


def test_the_jackknife_is_recs_jk1():
    # Equal weights; each replicate drops one record and reweights the rest by R/(R-1). The share's
    # error is then the textbook one, sqrt(p(1-p)/(n-1)) for n = R records, one dropped a replicate.
    n = 60
    mask = pd.Series([1] * 15 + [0] * 45)
    d = {"NWEIGHT": [1.0] * n}
    for i in range(1, 61):
        d[f"NWEIGHT{i}"] = [0.0 if j == i - 1 else n / (n - 1) for j in range(n)]
    est, se = bl._jk(pd.DataFrame(d), mask)
    assert est == pytest.approx(0.25)
    assert se == pytest.approx(np.sqrt(0.25 * 0.75 / (n - 1)), rel=1e-9)


def _seg(system, run, ft, size="1", material="m"):
    return {"cls": "IfcPipeSegment", "pre": None, "name": run, "props": {"System": system, "Run": run, "Length": ft * bl.FT,
                                                                        "Size": size, "Material": material, "Key": f"run/{run}/0"}}


def test_the_drains_cast_iron_gets_its_pvc_twin_and_nothing_is_lost():
    rb = [_seg("drain", "plumbing/building-drain", 100.0, "4", "cast iron, no-hub"), _seg("cold", "main/cold", 50.0, "1-1/2", "PEX"),
          {"cls": "IfcValve", "pre": None, "name": "tbv", "props": {"Key": "valve/1-front-left", "System": "hot", "Kind": "thermostatic balancing valve"}}]
    items, seen = bl.model_items(rb)
    assert seen["ft"] == pytest.approx(150.0) and seen["valves"] == 1
    by = {it["what"]: it["qty"] for it in items.values()}
    ci = by["cast iron, no-hub, 4 in.: the building drain"]
    pvc = by[f"{bl.PVC_DWV}, 4 in.: the building drain"]
    assert ci == {"engineered": 100.0, "electric": 0.0, "gas": 0.0, "central": 0.0}
    assert pvc == {"engineered": 0.0, "electric": 100.0, "gas": 100.0, "central": 100.0}
    assert by["thermostatic balancing valve"] == {"engineered": 1.0, "electric": 0.0, "gas": 0.0, "central": 1.0}
    # A run whose role has no words is an error, not a quiet item.
    with pytest.raises(ValueError):
        bl.model_items([_seg("cold", "somewhere/new", 1.0)])


def test_insulation_follows_the_specification_by_size(P):
    model, _ = bl.model_items([_seg("hot", "plumbing/hot/1-front-left", 10.0, "3/4", "PEX"), _seg("hot", "front-left/hot", 20.0, "1-1/2", "PEX"),
                               _seg("hot", "main/hot", 30.0, "2", "PEX")])
    ins = {it["what"]: it["qty"] for it in bl.insulation_items(model, P).values()}
    small, large = P["systems.hot_water.insulation_in_small"], P["systems.hot_water.insulation_in_large"]
    assert ins[f"insulation {small:g} in. on hot-water pipe, 3/4 in. (the flats' branches)"]["central"] == 10.0
    assert ins[f"insulation {large:g} in. on hot-water pipe, 1-1/2 in. (risers)"]["engineered"] == 20.0
    assert not any("under the slab" in k for k in ins)  # the mains come insulated


# ---- On the published model, the routes and the sources ----

@pytest.fixture(scope="module")
def made(P):
    from brownfield import routed, systems

    if not bl.SERVICES.exists():
        pytest.skip("the services model isn't published")
    if not (bl.RAW / "recs" / "recs2020_public_v7.csv").exists() or not (bl.RAW / "census").exists():
        pytest.skip("RECS's microdata or Census's tables aren't downloaded (`brownfield baseline` fetches them)")
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    return bl.run(apt, P)


def test_every_check_passes(made):
    assert [label for label, ok, _ in made["checks"] if not ok] == []


def test_a_lost_run_or_an_untraced_item_is_caught(made, P):
    bad = copy.deepcopy(made)
    run = next(it for it in bad["items"] if it.get("run"))
    run["qty"]["engineered"] -= 10.0
    bad["items"].append({**bad["items"][0], "id": "x", "basis": ""})
    failed = {label for label, ok, _ in bl.checks(bad, P) if not ok}
    assert "the services model counted once: its runs' lengths are its schedule's" in failed
    assert "every item traces to a model element, a design parameter or a stated rule, and has a quantity" in failed


def test_the_usual_flats_need_more_heat_and_the_heat_pump_still_carries_it(made):
    h = made["heat"]
    assert h["building_kw"] > 1.3 * h["engineered_kw"]  # the code's leakage, no heat recovery
    assert all(f["capacity_w"] >= f["load_w"] > f["engineered_w"] for f in h["flats"].values())


def test_the_usual_flats_own_hot_pipe_is_short_and_the_engineered_ones_loops_are_long(made):
    rule = made["rule"]
    assert max(x["longest_ft"] for x in rule.values()) < 25
    by = {it["id"]: it for it in made["items"]}
    trunk = by["own | trunk"]["qty"]
    loops = sum(it["qty"]["engineered"] for it in made["items"] if it.get("run") and it["system"] == "hot")
    assert trunk["electric"] > 0 and trunk["engineered"] == 0 and loops > 3 * (trunk["electric"] + by["own | drops"]["qty"]["electric"])


def test_the_census_and_recs_tables_read_as_published(made):
    c = made["practice"]["census"]
    assert c["fuel"]["total"] == 79 and c["systems"]["heat_pump"]["total"] == 34 and c["systems"]["furnace"]["total"] == 29
    ne = made["practice"]["recs_ne"]["shares"]
    shared = ne["water heater shared, electric"][0] + ne["water heater shared, gas"][0]
    assert shared > 0.5  # most newer Northeast apartments in 5+ unit buildings share a water heater


def test_each_usual_service_swaps_its_own_loads_in(made, P):
    s, u, e = made["services"], "baseline.usual.", "systems.electrical."
    # The gas walk-up's flat: the electric one's less its heater, plus the gas heater's fan; its
    # furnace's blower counted once, with the cooling (the larger), not as an appliance too.
    gas = s["electric"]["per_unit_va"] - P[u + "heater_va"] + P[u + "gas_heater_va"] - P[e + "cooling_va"] + P[u + "ac_va"] + P[u + "furnace_va"]
    assert s["gas"]["per_unit_va"] == pytest.approx(gas)
    assert s["central"]["per_unit_va"] == pytest.approx(s["electric"]["per_unit_va"] - P[u + "heater_va"])
    assert s["engineered"]["main_a"] == 600 and all(v["amps"] <= v["main_a"] for v in s.values())
