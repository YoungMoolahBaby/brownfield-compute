"""Pass 3g step 10b (D28): both walk-ups priced item by item, and the fee (`brownfield.pricing`). The
synthetic tests never skip; the run on the published model and the routes skips when they're absent."""
import pytest

from brownfield import pricing as pc
from brownfield.baseline import WALKUPS
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def _it(id_, what, unit="ft", qty=None, system="cold", **more):
    return {"id": id_, "what": what, "unit": unit, "system": system, "qty": qty or {w: 1.0 for w in WALKUPS}, **more}


def test_each_item_finds_its_class_by_size():
    assert pc.classes_of(_it("fit | vent | cast iron, no-hub | quarter bend | 1-1/2", "cast iron, no-hub, quarter bend, 1-1/2 in.")) == \
        [("ci_fitting_small", 1.0)]  # 1-1/2 in. is small (a size parsed either way)
    assert pc.classes_of(_it("fit | drain | cast iron, no-hub | quarter bend | 4", "cast iron, no-hub, quarter bend, 4 in.")) == \
        [("ci_fitting_large", 1.0)]
    assert pc.classes_of(_it("run | drain | PVC DWV | 1-1/2 | x", "PVC DWV, Schedule 40 (the usual walk-up's), 1-1/2 in.: x", size="1-1/2")) == \
        [("pvc_dwv_1.5", 1.0)]
    assert pc.classes_of(_it("run | hot | m | 2 | main", "PEX-a, pre-insulated under the slab (Uponor), 2 in.: main", size="2")) == \
        [("pex_preins_large", 1.0)]
    assert pc._nps("1.5") == pc._nps("1-1/2") == 1.5
    # The fixtures and appliances aren't priced (every walk-up's alike); an item of no class is an error.
    assert pc.classes_of(_it("el | IfcSanitaryTerminal | water closet", "water closet", "each")) == []
    with pytest.raises(ValueError):
        pc.classes_of(_it("mystery | thing", "a thing"))


def test_a_feeder_is_its_conduit_and_its_copper(P):
    pr = "baseline.price."
    mat, h = pc.unit_cost("feeder_1", P)
    assert mat == pytest.approx(P[pr + "pvc_conduit_1"] + 3 * P[pr + "thhn_3"] + P[pr + "thhn_8"])
    assert h == P["baseline.hours.feeder_1"]


def test_a_book_price_is_taken_to_net_and_a_street_one_isnt(P):
    book = pc.book_classes()
    assert "climatemaster_sw036" in book and "duct_round_6" not in book
    half = dict(P, **{"baseline.markup.book_to_net": 0.5})
    assert pc.unit_cost("climatemaster_sw036", half)[0] == pytest.approx(0.5 * P["baseline.price.climatemaster_sw036"])
    assert pc.unit_cost("duct_round_6", half)[0] == pytest.approx(P["baseline.price.duct_round_6"])


def test_the_markups_fall_where_they_should(P):
    q = {w: 0.0 for w in WALKUPS}
    q["engineered"] = 10.0
    items = [_it("run | cold | PEX | 1 | the flats' branches", "PEX-a with cold-expansion fittings, 1 in.: the flats' branches", qty=q, size="1"),
             _it("water | domestic service", "domestic water service", "each", qty=dict(q, engineered=1.0))]
    pr = pc.price(items, P)
    by = {(x["id"], x["class"]): x for x in pr["lines"]}
    pex = by[("run | cold | PEX | 1 | the flats' branches", "pex_a_1")]
    mat, h = pc.unit_cost("pex_a_1", P)
    assert pex["unit_usd"] == pytest.approx((mat + h * pc.wage("plumber", P)) * (1 + pr["trade_op"]) * pr["builder"])
    tap = by[("water | domestic service", "tap_first")]  # a utility's charge: no markup at all
    assert tap["unit_usd"] == pytest.approx(P["baseline.price.tap_first"])
    assert pr["builder"] == pytest.approx((1 + 0.06 + 0.02 + 0.06) * 1.05)


def test_the_fee_is_a_share_of_the_mep_share(P):
    f = pc.fee(P)
    c = P["baseline.fee.hud_hcc_flat"] * P["baseline.fee.hcc_to_2026"] * 12
    assert f["construction_usd"] == pytest.approx(c)
    assert f["extra_usd"] == pytest.approx(P["baseline.fee.extra_of_mep"] * P["baseline.fee.mep_share"] * P["baseline.fee.ofm_pct"] * c)
    none = pc.fee(dict(P, **{"baseline.fee.extra_of_mep": 0.0}))
    assert none["extra_usd"] == 0.0 and none["phfa_fee_usd"] == f["phfa_fee_usd"]


# ---- On the published model and the routes ----

@pytest.fixture(scope="module")
def made(P):
    from brownfield import baseline as bl, routed, systems

    if not bl.SERVICES.exists() or not (bl.RAW / "recs" / "recs2020_public_v7.csv").exists():
        pytest.skip("the services model isn't published, or RECS isn't downloaded")
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    r = bl.run(apt, P)
    return r, pc.run(r, apt, P)


def test_every_check_passes(made):
    _, pr = made
    assert [label for label, ok, _ in pr["checks"] if not ok] == []


def test_what_every_walk_up_has_alike_cancels_and_the_purposes_add_up(made):
    _, pr = made
    bp = pc.by_purpose(pr)
    alike = bp["every walk-up's alike"]
    assert all(abs(alike[w] - alike["engineered"]) < 1e-6 for w in WALKUPS)
    for w in WALKUPS[1:]:
        diff = pr["totals"]["engineered"]["total"] - pr["totals"][w]["total"]
        assert sum(v["engineered"] - v[w] for v in bp.values()) == pytest.approx(diff)


def test_a_dearer_engineered_only_item_raises_the_difference_and_leaves_the_usual(made, P):
    r, pr = made
    dear = dict(P, **{"baseline.price.radiant_pex_0.5": P["baseline.price.radiant_pex_0.5"] * 2})
    pr2 = pc.price(r["items"], dear)
    assert pr2["totals"]["engineered"]["total"] > pr["totals"]["engineered"]["total"]
    for w in WALKUPS[1:]:
        assert pr2["totals"][w]["total"] == pytest.approx(pr["totals"][w]["total"])


def test_the_heat_network_is_cheaper_on_a_denser_block(made):
    _, pr = made
    nw = pr["network"]
    assert nw["dense"]["flat"] < nw["base"]["flat"] and nw["dense"]["street"] == nw["base"]["street"]
