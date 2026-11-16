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
    assert abs(r["A_minus_B"] - (r["A"] - r["B"])) < 1e-9
    # The break-even street price really ties the loop with the cheaper alternative.
    q = dict(P, **{b + "street_usd_m": r["street_breakeven_usd_m"]})
    assert abs(block.per_home(q, 8.0, 3.0, 5.0, 80.0, 20.0)["A_minus_best"]) < 1e-6


def _flat(name, floor, wall, glazed, ceiling, slab):
    return {"name": name, "floor": 1, "floor_m2": floor, "interior_volume_m3": floor * 2.74, "wall_gross_m2": wall + glazed,
            "wall_net_m2": wall, "glazed_m2": glazed, "door_m2": 0.0, "ceiling_m2": ceiling, "slab_perimeter_m": slab}


def test_flats_middle_floor_loses_least():
    # Same walls and windows; the ground flat adds a slab edge, the top flat a roof, the middle neither.
    apt = {"flats": [_flat("ground", 77.7, 47.8, 12.6, 0.0, 19.8), _flat("middle", 77.7, 47.8, 12.6, 0.0, 0.0),
                     _flat("top", 77.7, 47.8, 12.6, 83.6, 0.0)]}
    fh = house.flats_heat(apt, np.full(8760, 0.0), P)
    ua = {f["name"]: h["ua_w_k"] for f, h in fh["flats"]}
    assert ua["middle"] < min(ua["ground"], ua["top"])
    assert abs(ua["top"] - ua["middle"] - P["pass3.envelope.ceiling_u"] * house.BTU_FT2 * 83.6) < 1e-9
    assert abs(fh["mean"]["ua_w_k"] - sum(ua.values()) / 3) < 1e-9
    assert fh["mean"]["hardest_supply_c"] == max(h["supply_c"] for _, h in fh["flats"])


def test_recs_ratio_by_hand():
    # 9.1 / 828 against 44.0 / 1951 (EIA RECS 2020 CE3.1, HC10.14, HC10.15).
    rc = house.recs_check({"space_mwh": 10.0}, 100.0, {"space_mwh": 5.0, "floor_m2": 100.0})
    assert abs(rc["model"] - 0.5) < 1e-12
    assert abs(rc["recs_5plus"] - (9.1 / 828) / (44.0 / 1951)) < 1e-12
