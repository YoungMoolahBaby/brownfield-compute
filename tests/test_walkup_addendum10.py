"""Addendum 10 (found in pass 3g step 10h, D28): the feeders' grounds larger with their conductors (NEC
250.122(B), `electrical.egc_for`), every ground held to it (`electrical.short_grounds`), the feeders priced
with the grounds they carry, and the services model reissued with only those conductors changed. The
synthetic tests never skip; those on the routes and the models skip when they're absent."""
import pytest

from brownfield import electrical as el, pricing, servicesifc, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def _feeder(size, least, egc, breaker=100.0):
    return {"size": size, "min_size": least, "egc": egc, "breaker_a": breaker}


def _circuit(awg, least, breaker, key="c"):
    return {"key": key, "awg": awg, "min_awg": least, "breaker_a": breaker}


# ---- Synthetic: no files needed ----

def test_a_ground_grows_with_its_conductors_by_their_circular_mils():
    assert el.egc_for(100) == "8" and el.egc_for(100, "3", "3") == "8"  # Table 250.122 alone
    # 8 AWG's 16,510 cmil x 2 AWG's 66,360 / 3 AWG's 52,620 = 20,821: over 8, within 6 (26,240)
    assert el.egc_for(100, "2", "3") == "6"
    # x 1 AWG's 83,690 / 52,620 = 26,258: 18 cmil over 6 AWG, so 4
    assert el.egc_for(100, "1", "3") == "4"
    assert el.egc_for(15, "12", "14") == "12" and el.egc_for(40, "6", "8") == "8"


def test_nm_b_carries_a_ground_its_own_size_to_10_awg():
    assert [el.nmb_ground(s) for s in ("14", "12", "10", "8", "6")] == ["14", "12", "10", "10", "10"]


def test_a_short_ground_is_caught_feeder_or_branch_circuit():
    ok = {"feeders": {"a": _feeder("2", "3", "6"), "b": _feeder("3", "3", "8")},
          "panels": {"a": {"circuits": [_circuit("12", "14", 15), _circuit("8", "8", 40)]}}}
    assert el.short_grounds(ok) == []
    # Addendum 7's way: the breaker's ground on a feeder made larger for the drop.
    bad = {**ok, "feeders": {**ok["feeders"], "a": _feeder("2", "3", "8")}}
    assert el.short_grounds(bad) == ["a's feeder (2 AWG, ground 8)"]
    # A 30 A circuit made 8 AWG: 250.122(B) asks an 8 AWG ground, and NM-B 8/3 carries a 10.
    dryer = {**ok, "panels": {"a": {"circuits": [_circuit("8", "10", 30, "dryer")]}}}
    assert el.short_grounds(dryer) == ["a dryer (8 AWG NM-B, ground 10)"]


def test_the_feeders_are_priced_with_the_grounds_they_carry(P):
    assert "a 6 AWG ground" in pricing.CLASSES["feeder_1.25"][2] and "a 4 AWG ground" in pricing.CLASSES["feeder_1.25_1awg"][2]
    assert "a 8 AWG ground" in pricing.CLASSES["feeder_1"][2]
    eight = dict(P, **{"baseline.price.thhn_6_over_8": 1.0})
    more = pricing.installed("feeder_1.25", P) - pricing.installed("feeder_1.25", eight)
    assert more > 0
    assert pricing.installed("feeder_1", P) == pytest.approx(pricing.installed("feeder_1", eight))


def test_addendum_10_is_issued_with_the_services_model_and_two_sheets():
    from brownfield import servicesheets

    from brownfield import designs

    assert designs.ISSUE["network"] == "addendum-10" and servicesheets.SERVICES_REV == "addendum-10"
    assert servicesheets.REVISED["E-601"] == ("Addendum 10", "services-sheet-e-601-addendum-10.pdf")
    assert servicesheets.REVISED["G-001"] == ("Addendum 10", "services-sheet-g-001-addendum-10.pdf")
    assert systems.TITLES[10] and 10 in systems.ISSUED


# ---- On the routes, and the models built from them ----

@pytest.fixture(scope="module")
def s7(P):
    from brownfield import routed

    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    return routed.summary(apt, P, routes)


def test_the_three_feeders_made_larger_take_6_awg_grounds_and_none_is_short(s7):
    e = s7["electrical"]
    gr = systems.feeder_grounds(e)
    assert sorted(x["flat"] for x in gr) == ["2-front-left", "3-front-left", "3-front-right"]
    assert all(x["size"] == "2" and x["least"] == "3" and x["was"] == "8" and x["egc"] == "6" for x in gr)
    assert all(f["egc"] == "8" for n, f in e["feeders"].items() if f["size"] == f["min_size"])
    assert el.short_grounds(e) == []
    assert any("250.122(B)" in label and ok for label, ok, _ in s7["checks"])


def test_the_reissued_model_changes_only_those_feeders_conductors():
    from brownfield import designs

    old = systems.PUBLISHED / "services-addendum-7.ifc"
    new = designs.paths(designs.network(load_params()))["services"] / "services-addendum-10.ifc"
    if not old.exists() or not new.exists():
        pytest.skip("Addendum 7's published services model or Addendum 10's (`brownfield routes --ifc`) isn't there")
    d = servicesifc.changes(old, new)
    assert not d["added"] and not d["deleted"] and d["changed"] and set(d["by_system"]) == {"power"}
    r0 = {r["gid"]: r for r in servicesifc.read_back(old)}
    r1 = {r["gid"]: r for r in servicesifc.read_back(new)}
    flats = {r1[g]["props"]["Flat"] for g in d["changed"]}
    assert flats == {"2-front-left", "3-front-left", "3-front-right"}
    for g in d["changed"]:
        a, b = r0[g]["props"], r1[g]["props"]
        assert {k for k in set(a) | set(b) if k != "id" and a.get(k) != b.get(k)} == {"Conductors"}
        assert a["Conductors"].endswith("a 8 AWG ground") and b["Conductors"].endswith("a 6 AWG ground")
