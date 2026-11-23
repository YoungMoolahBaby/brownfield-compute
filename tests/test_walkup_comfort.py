"""Pass 3g step 10d (D28): noise and comfort, each walk-up side by side (`brownfield.comfort`). The
synthetic tests never skip; the run on the published model and the routes skips when they're absent."""
import math

import pytest

from brownfield import comfort as co
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def test_warnock_and_morins_pressure_term_is_their_5_db_from_40_to_100_psi():
    # NRCC-35548: 'increase linearly with pressure by about 5 dB when supply pressure was increased from 40 to 100 psi'.
    assert co.pressure_db(100) - co.pressure_db(40) == pytest.approx(5.0)
    assert co.pressure_db(70) == 0.0


def test_a_half_gallon_at_one_gpm_takes_thirty_seconds():
    assert co.wait_s(64.0, 1.0) == pytest.approx(30.0)
    assert co.wait_s(128.0, 2.0) == pytest.approx(30.0)
    assert co.wait_s(0.0, 2.2) == 0.0


def test_sound_power_spreads_over_half_a_sphere_to_1_m():
    # Lp = Lw - 10 lg(2 pi r2): 8 dB less at 1 m over a hard surface.
    assert co.lp_1m(74.0) == pytest.approx(74.0 - 10 * math.log10(2 * math.pi))
    assert co.lp_1m(74.0) == pytest.approx(66.0, abs=0.05)


def _box(rid, use, lo, hi):
    return {"id": rid, "use": use, "lo_m": list(lo), "hi_m": list(hi)}


def test_the_plant_room_finds_a_shared_wall_but_not_a_corner():
    mech = _box("annex/mechanical", "mechanical", (12.2, 13.8, 0.0), (15.8, 16.7, 2.7))
    wall = _box("1-a/bed-1", "bedroom", (8.0, 14.0, 0.0), (12.0, 16.0, 2.7))  # 0.2 m apart in x, overlapping in y and height
    corner = _box("1-b/living", "living", (8.0, 10.0, 0.0), (12.0, 13.6, 2.7))  # apart in both x and y
    above = _box("2-a/bed-1", "bedroom", (8.0, 14.0, 3.0), (12.0, 16.0, 5.7))  # apart in height
    apt = {"rooms": {"rooms": [mech, wall, corner, above]}, "ext_t_m": 0.2032, "party_t_m": 0.15}
    r = co.plant_room(apt)
    assert [s["room"] for s in r["shared"]] == ["1-a/bed-1"]
    assert r["shared"][0]["shared_m"] == pytest.approx(2.0)
    apt["rooms"]["rooms"] = [mech, corner, above]
    r = co.plant_room(apt)
    assert r["shared"] == [] and r["nearest"] == "1-b/living"
    assert r["nearest_m"] == pytest.approx(math.hypot(0.2, 0.2))


# ---- On the published model and the routes ----

@pytest.fixture(scope="module")
def made(P):
    from brownfield import baseline as bl, energy, pricing, routed, systems

    if not bl.SERVICES.exists() or not (bl.RAW / "recs" / "recs2020_public_v7.csv").exists():
        pytest.skip("the services model isn't published, or RECS isn't downloaded")
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    r = bl.run(apt, P)
    en = energy.run(r, pricing.run(r, apt, P), apt, P)
    return r, en, apt, co.run(r, en, apt, P)


def test_every_check_passes(made):
    *_, c = made
    assert [label for label, ok, _ in c["checks"] if not ok] == []


def test_the_reducing_valve_quiets_the_engineered_pipes_only_above_its_setting(made, P):
    *_, apt, _ = made
    n, valve = "systems.noise.", P["systems.plumbing.max_static_psi"]
    for street in (valve - 10, valve + 20):
        r = co.pipes(apt, dict(P, **{"systems.plumbing.street_psi": street}))
        assert r["supply_db"]["engineered"] == pytest.approx(P[n + "supply_plastic_sleeved_db"] + co.pressure_db(min(street, valve)))
        assert r["supply_db"]["electric"] == pytest.approx(P[n + "supply_plastic_rigid_db"] + co.pressure_db(street))
    assert r["drain_dba"]["engineered"] < r["drain_dba"]["electric"] <= r["limit_dba"]


def test_closing_the_door_takes_air_from_the_usual_bedrooms_and_none_from_the_ducts(made, P):
    *_, apt, c = made
    shut = co.bedrooms(apt, dict(P, **{"baseline.comfort.door_closed_drop": 0.5}))
    for rid, v in c["bedrooms"].items():
        assert v["usual_closed_cfm"] <= v["usual_open_cfm"]
        assert shut[rid]["usual_closed_cfm"] == pytest.approx(0.5 * v["usual_open_cfm"])
        assert shut[rid]["engineered_cfm"] == pytest.approx(v["engineered_cfm"])
    # Spread by exterior area, a usual flat's bedrooms get part of its air, never more than all of it.
    assert all(0 < v["usual_open_cfm"] < v["flat_usual_cfm"] for v in c["bedrooms"].values())


def test_more_fallback_hours_run_only_the_engineered_heat_pumps_longer(made, P):
    _, en, _, c = made
    more = co.machines(dict(P, **{"baseline.energy.fallback_h": P["baseline.energy.fallback_h"] + 500}), c["hours"], en)
    assert more["engineered"]["outdoor"]["heat_h"] > c["machines"]["engineered"]["outdoor"]["heat_h"]
    for w in ("electric", "gas", "central"):
        assert more[w] == c["machines"][w]


def test_the_central_walk_up_waits_as_the_engineered_design_and_the_own_heaters_alike(made):
    *_, c = made
    w = c["waits"]["by_walkup"]
    assert w["central"] == w["engineered"] and w["electric"] == w["gas"]
    assert w["engineered"]["lav"]["worst_oz"] == 0.0  # each flat's loop ends at its lavatory
