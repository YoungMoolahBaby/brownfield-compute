"""Pass 3g step 9c (D28): the energy code's hot-water rules the design missed, fixed for Addendum 7:
each flat's own loop (IECC C404.5), its insulation (C404.4), the pump stopped at temperature
(C404.6.1) (`plumbing.flat_loop`, `dead_legs`, `routed_volumes`, `recirc_head`)."""
import math

import pytest

from brownfield import plumbing, routed, systems
from brownfield.params import load_params, values
from brownfield.routed import Routes

FT = 0.3048


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def test_table_c404_5_2_1_as_read(P):
    assert plumbing.tube_oz_ft(1.0) == 3.91 and plumbing.tube_oz_ft(0.5) == 1.18  # PEX CTS SDR 9
    assert plumbing.tube_oz_ft(1.0, "copper_l") == 5.49 and plumbing.tube_oz_ft(2.0, "cpvc_sch40") == 21.88
    with pytest.raises(ValueError):
        plumbing.tube_oz_ft(0.375, "cpvc_cts_sdr11")  # N/A in the table
    assert P["systems.hot_water.c404_volume_oz"] == 0.5 * 128  # half a gallon, 128 oz to the gallon (the table's footnote)


def _flat(sink_at: float, sink_leg: float) -> Routes:
    """One flat's hot branch: a 6 m trunk from the riser to the lavatory, where the loop ends; the tub
    off it 1 m short of that, the sink off it `sink_at` m out on a `sink_leg` m leg; its return back
    alongside from its own stub 0.1 m from the lavatory's."""
    end = plumbing.LOOP_END
    hot = {"id": "plumbing/hot/x", "root": [0.0, 0.0, 0.0], "snap_m": 0.05, "goals": [], "slope": 0.0}
    ret = {"id": "plumbing/hot-return/x", "root": [0.0, 0.1, 0.0], "snap_m": 0.05, "goals": [], "slope": 0.0}
    rec_hot = {"id": hot["id"], "ok": True, "branches": [
        {"terminal": end, "points": [[0, 0, 0], [6, 0, 0]], "to": [6, 0, 0]},
        {"terminal": "tub", "points": [[5, 0, 0], [5, 0, -1]], "to": [5, 0, -1]},
        {"terminal": "sink", "points": [[sink_at, 0, 0], [sink_at, 0, -sink_leg]], "to": [sink_at, 0, -sink_leg]}]}
    rec_ret = {"id": ret["id"], "ok": True, "branches": [{"terminal": end, "points": [[0, 0.1, 0], [6, 0.1, 0]], "to": [6, 0.1, 0]}]}
    return Routes({"requests": [hot, ret]}, {"routes": [rec_hot, rec_ret]}, True)


def test_each_hot_fixtures_own_pipe_takes_its_own_size(P):
    # Appendix E for one fixture: Table E103.3(2)'s units, Table E103.3(3)'s demand (3.0 gpm at 1
    # wsfu), the smallest PEX within 5 ft/s: the tub's 3 gpm needs 3/4 in., the lavatory's 1.5 fits 1/2.
    assert plumbing.fixture_hot_in("tub", P) == 0.75 and plumbing.fixture_hot_in("lav", P) == 0.5
    t = _flat(2.0, 2.0).tree("plumbing/hot/x")
    sizes = plumbing.hot_edge_sizes(t, 1.0, P)
    for k, e in enumerate(t.edges):
        assert sizes[k] == (plumbing.fixture_hot_in(e.below[0], P) if len(e.below) == 1 else 1.0)


def test_a_flats_loop_leaves_each_fixture_only_its_own_leg(P):
    r = _flat(2.0, 2.0)
    fl = plumbing.flat_loop(r, "x", P)
    assert fl["hot_m"] == pytest.approx(6.0) and fl["return_m"] == pytest.approx(6.0)
    assert fl["joint_m"] == pytest.approx(0.1 + P["systems.hot_water.tbv_length_in"] * 0.0254)  # the stubs apart, and the valve
    legs = plumbing.dead_legs(r, "x")
    assert sorted(legs) == ["sink", "tub"]
    assert sum(m for m, _ in legs["sink"]) == pytest.approx(2.0) and sum(m for m, _ in legs["tub"]) == pytest.approx(1.0)
    oz = plumbing.tube_oz_ft(plumbing.fixture_hot_in("sink", P))
    v = plumbing.routed_volumes({"flats": [{"name": "x"}]}, P, r, 1.0)
    assert v["by_flat"]["x"]["sink"] == pytest.approx(2.0 / FT * oz) and not v["over"]
    # The same flat with its sink 9 m down off the trunk: over the half gallon even at its own size.
    v = plumbing.routed_volumes({"flats": [{"name": "x"}]}, P, _flat(2.0, 9.0), 1.0)
    assert v["worst"]["fixture"] == "sink" and v["worst"]["oz"] == pytest.approx(9.0 / FT * oz) and v["over"] == [("x", "sink")]
    # IPC 607.2 from the flat's loop: the longest leg, not the way from the riser.
    assert plumbing.routed_hot_lengths({"flats": [{"name": "x"}]}, r)["x"] == pytest.approx(2.0 / FT)


def test_the_building_loops_pump_curve_as_read(P):
    from brownfield import hvac

    # Grundfos's own figures: the leaflet's "max. 19 ft", and the 15-55SF sheet's rated 10.7 gpm at
    # 8.202 ft, which the curve read off the leaflet passes within 3%.
    assert hvac.loop_pump_ft(0.5) == pytest.approx(19.0, abs=0.2)
    assert hvac.loop_pump_ft(P["systems.hot_water.recirc_rated_gpm"]) == pytest.approx(P["systems.hot_water.recirc_rated_ft"], rel=0.03)
    q = [0.5] + list(range(1, 22))
    assert all(hvac.loop_pump_ft(a) > hvac.loop_pump_ft(b) for a, b in zip(q, q[1:]))  # falls with flow
    with pytest.raises(ValueError):
        hvac.loop_pump_ft(25.0)


def test_the_pumps_head_counts_each_flats_valve_by_its_cv(P):
    h = "systems.hot_water."
    cv = P[h + "tbv_cv_design"]
    zero = dict.fromkeys(("main_ft", "rise_ft", "flat_ft", "flat_return_ft", "return_rise_ft", "return_main_ft"), 0.0)
    size = dict.fromkeys(("main", "riser", "flat", "flat_return", "return_riser", "return_main"), 1.0)
    # Twelve flats at the valve's Cv each: 1 psi across each valve (Cv is the gpm at 1 psi).
    r = plumbing.recirc_head(P, 12 * cv, 4, 12, zero, size, 51.7, 50.0)
    assert r["parts"]["tbv"] == pytest.approx(1.0) and r["flat_gpm"] == pytest.approx(cv)
    assert all(r["parts"][k] == 0.0 for k in size)
    assert r["ft"] == pytest.approx((1.0 + r["parts"]["mixing_valve"]) / 0.433)
    # Past the pump's rated point it fails: four times the flow, sixteen times the valve's loss.
    assert not plumbing.recirc_head(P, 48 * cv, 4, 12, zero, size, 51.7, 50.0)["ok"]


def test_the_flats_branches_take_the_codes_insulation(P):
    # C404.4 by Table C403.12.3 (105-140 F, under 1-1/2 in.): 1.0 in., as the risers' ASHRAE figure.
    assert P["systems.routing.branch_insulation_in"] == P["systems.hot_water.insulation_in_small"] == 1.0


@pytest.fixture(scope="module")
def made(P):
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    return apt, routes, routed.summary(apt, P, routes)


def test_every_flat_has_its_loop_and_every_fixture_is_within_half_a_gallon(made, P):
    apt, routes, s7 = made
    w = s7["water"]
    assert set(w["loop"]["flats"]) == {f["name"] for f in apt["flats"]}
    assert not w["c404"]["over"] and w["c404"]["worst"]["oz"] <= P["systems.hot_water.c404_volume_oz"]
    assert w["longest_hot_ft"] <= 50
    for f in apt["flats"]:
        fl = plumbing.flat_loop(routes, f["name"], P)
        # The two stubs under the lavatory within a vanity's width, the valve between them.
        assert fl["joint_m"] - P["systems.hot_water.tbv_length_in"] * 0.0254 < 0.5 and fl["hot_m"] > 0 and fl["return_m"] > 0
        assert all(m > 0 for legs in plumbing.dead_legs(routes, f["name"]).values() for m, _ in legs)


def test_the_loops_checks_pass_on_the_routes(made):
    _, _, s7 = made
    names = ("IECC C404.5.2", "the recirculation pump holds", "risers' and mains' routed loss", "IPC 607.2", "building loop's pump covers")
    rows = [(label, ok, detail) for label, ok, detail in s7["checks"] if any(n in label for n in names)]
    assert len(rows) == len(names) and all(ok for _, ok, _ in rows), rows
