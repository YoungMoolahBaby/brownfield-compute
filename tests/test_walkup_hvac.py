"""Pass 3g step 3 (D28): heating, cooling and ventilation designed (`brownfield.hvac`)."""
import pytest

from brownfield import hvac, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt3():
    return systems.load(systems.OUT_DIR / "pass3" / "apartment-addendum-3.json")


def test_the_floor_model_reproduces_rehau(P):
    # Its own calibration point exactly; the chart's reads (by eye, +/- 1 Btu/h ft2) asking at most
    # 2 F more water than the chart (the safe side) and never less.
    for (r, s, dt_f), btuh, model_f in hvac.chart_check(P):
        assert dt_f - 0.05 <= model_f <= dt_f + 2.0, (r, s, dt_f, btuh, model_f)


def test_friction_against_rehau_table_1a(P):
    # Turbulent flow (0.6 gpm and up in 1/2 in.): within 5% of REHAU's table at 60 F and 120 F. Below,
    # the table steps through the laminar-turbulent transition, and the model reads under it.
    for t_f, rows in hvac.REHAU_TABLE_1A.items():
        for gpm, psi in rows.items():
            if gpm >= 0.6:
                assert hvac.pex_psi_per_100ft(gpm, (t_f - 32) / 1.8, P["systems.radiant.bore_in"]) == pytest.approx(psi, rel=0.05)


def test_the_radiant_floors(apt3, P):
    rad = hvac.radiant(apt3, P)
    for name, f in rad.items():
        assert f["surface_over_limit"] == [] and f["too_long"] == []
        # Under the data center's 50 C return with the heat exchanger's approach to spare.
        assert f["supply_c"] <= 50 - P["systems.substation.approach_k"]
        for y in f["rooms"]:
            # Each loop's flow delivers its room's heat: m cp (supply - return) = W.
            m = y["gpm_per_circuit"] * y["circuits"] * hvac.GPM * hvac.water_props(30)[0]
            assert m * 4180 * (f["supply_c"] - y["return_c"]) == pytest.approx(y["w"], rel=0.02)
    # The ground floor's corner bedroom sets its flat's water, with its pipes at 4 in.
    g = rad["1-front-left"]
    assert g["index_room"] == "1-front-left/bed-1"
    assert next(y for y in g["rooms"] if y["id"] == g["index_room"])["spacing_in"] == 4


def test_hardwood_would_need_water_the_loop_cant_give(apt3, P):
    # Laminated hardwood (R-0.87) on the ground floor asks more than the data center's 50 C return
    # less the exchanger's approach: the covering is a design decision, not a finish to leave to the end.
    alt = hvac.radiant(apt3, P, alt_covering=True)
    assert alt["1-front-left"]["supply_c"] > 50 - P["systems.substation.approach_k"]


def test_sdr9_bore_matches_rehau(P):
    # The SDR 9 rule gives the 1/2 in. bore REHAU's velocity column implies.
    assert hvac.sdr9_bore_in(0.5) == pytest.approx(P["systems.radiant.bore_in"], abs=0.002)


def test_churchill_against_colebrook():
    # The closed form against Colebrook's implicit law over the pipes' and ducts' turbulent range
    # (relative roughness at most 0.001: a 4 in. galvanized duct is 0.0009). Rougher, at Re 5,000,
    # Churchill reads up to 3% high.
    for re in (5e3, 1e4, 1e5, 1e6):
        for rr in (1e-5, 1e-4, 1e-3):
            assert hvac.churchill_f(re, rr) == pytest.approx(hvac.colebrook_f(re, rr), rel=0.02)


def test_the_building_loop(apt3, P):
    s = hvac.substation(apt3, P)
    # The data center's 50 C return feeds the building with the exchanger's approach to spare.
    assert s["approach_ok"] and s["primary_in_c"] == pytest.approx(50.0)
    # Energy balances: the building's flow and drop carry its heat; the primary carries the same.
    rho = hvac.water_props(s["supply_c"] - 5)[0]
    assert s["gpm"] * hvac.GPM * rho * 4180 * (s["supply_c"] - s["return_c"]) == pytest.approx(s["w"], rel=1e-6)
    rho1 = hvac.water_props(s["primary_in_c"] - 5)[0]
    assert s["primary_gpm"] * hvac.GPM * rho1 * 4180 * (s["primary_in_c"] - s["primary_out_c"]) == pytest.approx(s["w"], rel=1e-6)
    # Every flat on the building's supply, each at or under it in need; each meter in its range.
    assert all(f["supply_c"] == s["supply_c"] >= f["need_c"] - 1e-9 for f in s["flats"].values())
    assert all(m["in_range"] for m in s["meters"].values())
    # Two risers of six flats, each under the velocity limit.
    assert sorted(len(r["flats"]) for r in s["risers"].values()) == [6, 6]
    assert all(r["fps"] <= P["systems.substation.max_velocity_fps"] for r in s["risers"].values())
    assert s["header_fps"] <= P["systems.substation.max_velocity_fps"]


def test_heat_meter_drop_at_its_rating(P):
    # Kamstrup's kv gives the data sheet's own 0.03 bar at qp.
    qp_gpm = P["systems.heat_meter.qp_m3h"] / 3600 / hvac.GPM
    assert hvac.heat_meter(qp_gpm, P)["psi"] * hvac.PSI / 1e5 == pytest.approx(0.03, abs=0.0005)


def test_the_erv_post_heater(apt3, P):
    # Without it, the ERV's air reaches the bedrooms well under PHI's 16.5 C at the design hour; the
    # coil lifts it there and carries the difference on the flat's manifold.
    from brownfield import loads
    t_out, t_in = P["systems.design.heating_c"], P["pass3.loads.indoor_c"]
    erv = loads.erv_sensible(P, t_out)
    assert t_out + erv * (t_in - t_out) < P["systems.erv.post_heat_c"] - 5
    case = loads.design_case(apt3, P, post_heat=True)
    for name, c in case["flats"].items():
        assert t_out + c["recovery"] * (t_in - t_out) == pytest.approx(P["systems.erv.post_heat_c"])
        cfm = c["vent_m3h"] / loads.CFM_M3H
        assert c["coil_w"] == pytest.approx(cfm * loads.CFM_M3H * loads.RHO_CP_AIR * (P["systems.erv.post_heat_c"] - (t_out + erv * (t_in - t_out))))
    rad = hvac.radiant(apt3, P)
    assert all(f["coil"]["w"] == pytest.approx(case["flats"][n]["coil_w"]) for n, f in rad.items())


def test_the_erv_between_hvis_tests(P):
    # A straight line between HVI's 32 F and -13 F tests, held beyond them.
    from brownfield import loads
    assert loads.erv_sensible(P, 0.0) == pytest.approx(P["systems.erv.sre_32f"])
    assert loads.erv_sensible(P, (-13 - 32) / 1.8) == pytest.approx(P["systems.erv.sre_m13f"])
    assert loads.erv_sensible(P, -40.0) == pytest.approx(P["systems.erv.sre_m13f"])


def test_cooling_unit_and_ducts(apt3, P):
    c = hvac.cooling_ducts(apt3, P)
    for name, x in c.items():
        assert x["covered"] and x["ducts"]["ok"]
        assert x["sensible_capacity_w"] >= x["sensible_w"]
        # The branches carry the unit's whole airflow.
        assert sum(b["cfm"] for b in x["ducts"]["branches"].values()) == pytest.approx(P[f"systems.{x['unit']}.cfm"])
    # Fujitsu's 75/63 rows at the design dry bulb, with no line-set loss at 25 ft (the rating's own).
    tot, sen = hvac.unit_capacity(P, "minisplit_12", 25.0)
    k = (P["systems.design.cooling_db_c"] * 1.8 + 32 - 86) / 9
    assert sen * 3.412142 == pytest.approx(9930 + k * (9550 - 9930))
    # The 12k can't carry the placeholder glass's load; the 18k can.
    worst = max(x["sensible_w"] for x in c.values())
    assert hvac.unit_capacity(P, "minisplit_12", 36.0)[1] < worst < hvac.unit_capacity(P, "minisplit_18", 36.0)[1]


def test_ventilation_ducts(apt3, P):
    v = hvac.ventilation_ducts(apt3, P)
    for x in v.values():
        assert x["in_range"]
        for side in ("supply", "exhaust"):
            d = x[side]
            assert d["ok"] and d["worst_inwc"] <= P["systems.erv.esp_inwc"]
            assert min(b["in"] for b in d["branches"].values()) >= 4  # none under the unit's ports
