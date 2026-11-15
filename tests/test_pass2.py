"""Pass 2 module model against hand-worked cases and published values."""

import numpy as np

from brownfield import module
from brownfield.params import load_params, values

P = values(load_params())


def test_tower_rule_of_thumb_is_thermodynamics():
    # "about 1% of circulation evaporates per 10 F of range" (0.85% with some heat sensible)
    assert 0.0090 < module.evaporation_per_10f() < 0.0100


def test_conventional_by_hand():
    # Steady 10 C year: towers reject IT x (1 + 1/COP) x (1 + fans); water = that heat x evap
    # fraction / h_fg, plus blowdown evap / (cycles - 1).
    t = np.full(8760, 10.0)
    r = module.conventional(t, P)
    it_mw = P["pass2.module.it_mw"] * P["pass2.module.load_factor"]
    heat = it_mw * (1 + 1 / P["pass2.conventional.chiller_cop"]) * (1 + P["pass2.fans.tower_kw_per_kw"])
    evap = heat * 1e6 * P["pass2.conventional.evap_fraction"] / module.H_FG * 3600 * 8760 / 1000
    assert abs(r.evaporated_m3 / evap - 1) < 1e-9
    assert abs(r.blowdown_m3 - evap / (P["pass2.conventional.cycles"] - 1)) < 1e-6
    assert abs(r.heat_out_mwh - heat * 8760) < 1e-6


def test_conventional_wue_in_published_range():
    # Published: 1.55 L/kWh (a colocation fleet, evaporative, 2024) to 2.8 (EPRI's water-cooled
    # chiller without economiser); RESEARCH.md. Our central case must land inside.
    r = module.conventional(np.full(8760, 10.0), P)
    assert 1.55 <= r.wue <= 2.8


def test_good_neighbour_balances():
    t = np.linspace(-15, 35, 8760)
    r = module.good_neighbour(t, P)
    assert r.withdrawn_m3 == 0.0
    # Delivered heat = source heat + heat pump work; the town gets at most what it asks for.
    assert abs(r.delivered_mwh - (r.heat_reused_mwh + r.heat_pump_mwh)) < 1e-6
    assert r.town_mwh <= r.town_demand_mwh + 1e-6
    assert abs(r.town_demand_mwh - P["pass2.town.homes"] * P["pass2.town.heat_per_home_mwh"]) < 1e-6


def test_cold_needs_no_trim():
    # Below supply - approach, the dry coolers carry both loops alone: cooling power = fans only.
    r = module.good_neighbour(np.full(8760, 0.0), P)
    assert r.trim_hours == 0


def test_heat_pump_cop_against_measured_unit():
    # IEA HPT Annex 57 (Danish case): water/water, -4.5 C source, 30/55 C sink, measured COP 3.58.
    # With no approaches that's 0.65 of Carnot; our central 0.55 with 5 K approaches must come out
    # below the measured unit (conservative), and the high end (0.65, no approach) must match it.
    ours = module.heat_pump_cop(-4.5, 55.0, P["pass2.good_neighbour.hp_approach_k"],
                                P["pass2.good_neighbour.hp_carnot_eff"])
    assert ours < 3.58
    assert abs(module.heat_pump_cop(-4.5, 55.0, 0.0, 0.65) - 3.58) < 0.05


def test_iso9613_closed_forms():
    from brownfield import noise
    # A_div at 1 km = 20 lg 1000 + 11 = 71 dB; ground term by hand at 200 m, h_m 1.5 m.
    assert abs(noise.a_div(1000.0) - 71.0) < 1e-9
    assert abs(noise.a_gr(200.0, 1.5) - (4.8 - (3.0 / 200.0) * (17.0 + 1.5))) < 1e-9
    # Budget and level are inverses.
    lw = noise.budget(40.0, 800.0, P)
    assert abs(noise.level_at(lw, 800.0, P) - 40.0) < 1e-9


def test_fan_law_matches_vendor_claim():
    from brownfield import noise
    # Guntner: EC fans at half airflow 15 dB(A) quieter; fan law 50 lg 0.5 = -15.05.
    assert abs(noise.fan_law_db(0.5) + 15.0) < 0.1


def test_cost_arithmetic():
    from brownfield import cost
    # 7% over 20 years: the textbook annuity factor 10.594.
    assert abs(cost.annuity(0.07, 20) - 10.594) < 1e-3
    # ~1,037 Btu per cubic foot: a thousand cubic feet is ~0.304 MWh.
    assert abs(cost.MCF_MWH - 0.3039) < 1e-3
    r = cost.ledgers(np.full(8760, 5.0), P)
    assert abs(r["capex_heat"] - (r["hp"] + r["main"] + r["network"] + r["homes"])) < 1e-3
    assert abs(r["npv_both"] - (r["npv_op"] + r["npv_heat"])) < 1e-3
    # Hydrogen by hand: backup kW x hours / (efficiency x 33.33 kWh/kg).
    kw = P["pass2.module.it_mw"] * P["pass2.backup.installed_per_it_mw"] * 1000
    kg = kw * P["cost.backup.h2_hours"] / (P["cost.backup.fuel_cell_eff"] * 33.33)
    assert abs(r["h2_t"] * 1000 - kg) < 1e-6


def test_wet_bulb_stull_example():
    from brownfield import climate
    # Stull (2011): 20 C at 50% RH has a wet bulb of 13.7 C.
    assert abs(float(climate.wet_bulb(np.array([20.0]), np.array([50.0]))[0]) - 13.7) < 0.1


def test_air_hall_dry_cold_year_uses_no_water():
    # Below the 27 C supply limit all year, the pads never run.
    r = module.air_hall(np.full(8760, 10.0), np.full(8760, 60.0), P)
    assert r.withdrawn_m3 == 0.0 and abs(r.pue - (1 + P["pass2.air_hall.ahu_kw_per_kw"])) < 1e-9


def test_vs_strong_arithmetic():
    from brownfield import cost
    t, rh = np.linspace(-10, 32, 8760), np.full(8760, 60.0)
    c = cost.vs_strong(t, rh, P)
    af = cost.annuity(P["cost.money.discount"], P["cost.money.life_yr"])
    assert abs(c["npv_vs_ai"] - (c["yearly_vs_ai"] * af - c["capex_vs_ai"])) < 1e-3
    assert abs(c["breakeven_vs_cloud"] - c["yearly_vs_cloud"] * af) < 1e-3
