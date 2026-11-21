"""Pass 3g step 6 (D28): sprinklers and alarms (`brownfield.fire`)."""
import pytest

from brownfield import fire, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


@pytest.fixture(scope="module")
def S(apt, P):
    return fire.summary(apt, P)


def _failing(apt, p):
    return [label for label, ok, _ in fire.summary(apt, p)["checks"] if not ok]


def test_hazen_williams_and_k_against_the_usfa_example():
    # USFA 'Commercial Fire Sprinkler System Plans Review' (2023): P = (15.5 / 5.6)^2 = 7.66 psi;
    # 15.5 gpm, C 120: 0.081 psi/ft, 0.87 psi over 10.83 ft (at Schedule 40's 1.049 in.).
    ex = fire.usfa_example()
    assert ex["p_head"] == pytest.approx(7.66, abs=0.005)
    assert ex["psi_ft"] == pytest.approx(0.081, abs=0.0005)
    assert ex["psi"] == pytest.approx(0.87, abs=0.01)
    # The bore the slide prints, 1.087 in., would not give it.
    assert fire.hw_psi_ft(15.5, 1.087, 120.0) == pytest.approx(0.068, abs=0.001)


def test_the_listing_is_k_times_root_p():
    for r in fire.listing() + fire.listing("TY2334"):
        assert r["k"] * r["p"] ** 0.5 == pytest.approx(r["q"], rel=0.01)


def test_every_step_6_check_passes(S):
    assert [label for label, ok, _ in S["checks"] if not ok] == []


def test_a_bigger_bathroom_would_need_a_sprinkler(apt, P):
    n = sum(len(v["heads"]) for v in fire.layout(apt, P).values())
    m = sum(len(v["heads"]) for v in fire.layout(apt, dict(P, **{"systems.sprinkler.bath_exempt_ft2": 40.0})).values())
    assert m == n + len(apt["flats"])


def test_one_inch_branches_would_ask_too_much_of_the_street(apt, P):
    mech = next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/mechanical")
    run = {"main_ft": fire._manhattan_ft(((mech["lo_m"][0] + mech["hi_m"][0]) / 2, (mech["lo_m"][1] + mech["hi_m"][1]) / 2),
                                         fire.riser_xy(apt))}
    d = fire.compartment_demand(apt, P, "3-front-left", "open", fire.SIZE_START)
    need = fire.supply(P, d["q_gpm"], d["p_at_riser_floor_psi"], d["z_head_m"], run, fire.SIZE_START)["need_psi"]
    assert need > P["systems.plumbing.street_psi"] - P["systems.sprinkler.margin_psi"]
    hyd = fire.hydraulics(apt, P)
    assert fire.SIZES.index(hyd["sizes"]["branch"]) > fire.SIZES.index(fire.SIZE_START["branch"])


def test_the_checks_catch_a_weak_street_a_cold_stair_and_a_hatch_at_the_edge(apt, P):
    assert any("the street" in x for x in _failing(apt, dict(P, **{"systems.plumbing.street_psi": 38.0})))
    cold = dict(P, **{"systems.sprinkler.party_wall_u": 0.004, "systems.sprinkler.fire_door_u": 0.01})
    assert not fire.stair_temperature(apt, cold)["ok"]
    assert any("roof hatch" in x for x in _failing(apt, dict(P, **{"systems.fire_code.hatch_margin_in": -24.0})))


def test_the_mechanical_rooms_door_sits_inside_1023_7s_reach(apt, P):
    en = fire.enclosure(apt, P)
    assert [d["id"] for d in en["protected_doors"]] == ["annex-mechanical/left/0"]
    assert {w["id"] for w in en["rated_walls"]} == {"annex-left", "annex-right"}


def test_no_manual_fire_alarm_but_a_fourth_storey_would_lose_the_single_exit(apt, P):
    assert not fire.code_frame(apt, P)["manual_alarm"]
    assert not fire.single_exit(apt, dict(P, **{"systems.fire_code.single_exit_max_storeys": 2}))["ok"]


def test_a_shared_main_would_add_13rs_domestic_demand(apt, P):
    # A flat: bathroom group 3.6 + kitchen sink 1.4 + dishwasher 1.4 + washer 1.4 = 7.8 load units
    # (13R Table 9.3.2(a), private); 12 flats 93.6; Table 9.3.2(b), flush tanks: 35 gpm at 70, 45 at 100.
    sm = fire.shared_main(apt, fire.hydraulics(apt, P))
    assert sm["load_units"] == pytest.approx(93.6)
    assert sm["domestic_gpm"] == pytest.approx(35 + 10 * (93.6 - 70) / 30)

