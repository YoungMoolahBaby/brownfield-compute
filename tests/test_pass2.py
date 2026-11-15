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
