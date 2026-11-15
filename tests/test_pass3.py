"""Pass 3: the first house's heat against hand-worked values."""

import numpy as np

from brownfield import house
from brownfield.params import load_params, values

P = values(load_params())
ENV = {"floor_m2": 100.0, "interior_volume_m3": 250.0, "wall_net_m2": 100.0, "glazed_m2": 10.0, "door_m2": 4.0,
       "ceiling_m2": 100.0, "slab_perimeter_m": 40.0}


def test_ua_by_hand():
    u = house.ua(ENV, P)
    assert abs(u["walls"] - 0.060 * 5.678263 * 100.0) < 1e-9
    # Infiltration: 3 ACH50 / 20 = 0.15 ACH of 250 m3 = 37.5 m3/h x 0.335 Wh/m3K.
    assert abs(u["infiltration"] - 37.5 * 1.2 * 1005 / 3600) < 1e-9
    # Ventilation, ASHRAE 62.2: 0.03 x 1076.4 ft2 + 7.5 x 3 = 54.79 cfm.
    cfm = 0.03 * 100.0 / 0.09290304 + 7.5 * 3
    assert abs(u["ventilation"] - cfm * 1.699011 * 1.2 * 1005 / 3600) < 1e-9


def test_radiant_floor_100_w_at_9k():
    # EN 1264 as cited: 9 K over the room is ~100 W/m2.
    assert abs(8.92 * 9 ** 1.1 - 100.0) < 0.5


def test_design_load_and_annual():
    h = house.heat(ENV, np.full(8760, 0.0), P)
    total = sum(house.ua(ENV, P).values())
    assert abs(h["design_kw"] - total * (20 - P["pass3.loads.design_c"]) / 1e3) < 1e-9
    balance = 20 - P["pass3.loads.internal_w"] / total
    assert abs(h["space_mwh"] - total * balance * 8760 / 1e6) < 1e-9


def test_block_by_hand():
    from brownfield import block
    from brownfield.cost import annuity
    r = block.per_home(P, 8.0, 3.0, 5.0, 80.0, 20.0)
    b = "pass3.block."
    assert abs(r["street"] - 20.0 * P[b + "street_usd_m"]) < 1e-9
    assert abs(r["main"] - P[b + "main_km"] * 1000 * P[b + "main_usd_m"] / P[b + "homes"]) < 1e-9
    af = annuity(P["cost.money.discount"], P["cost.money.life_yr"])
    assert abs(r["A"] - (r["A_capex"] + r["A_year"] * af)) < 1e-6
    # The break-even street price really ties the loop with the cheaper alternative.
    q = dict(P, **{b + "street_usd_m": r["street_breakeven_usd_m"]})
    assert abs(block.per_home(q, 8.0, 3.0, 5.0, 80.0, 20.0)["A_minus_best"]) < 1e-6
