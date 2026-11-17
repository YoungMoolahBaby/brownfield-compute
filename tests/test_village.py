"""Pass 3e, the neighbourhood: townhouse heat, lots, walks, noise by floor and the heat balance by hand."""

import numpy as np
import pytest

from brownfield import house, village
from brownfield.params import load_params, values

P = values(load_params())
COLD = np.full(8760, -5.0)


def test_twin_walls_lose_no_heat_sideways_but_detached_houses_do():
    mid, end, gap = (village.townhouse_env(P, "twin"), village.townhouse_env(P, "twin", end=True),
                     village.townhouse_env(P, "gap"))
    t = "village.townhouse."
    h, n, d = P[t + "storey_m"], int(P[t + "storeys"]), P[t + "depth_m"]
    front_back = 2 * P[t + "width_twin"] * h * n
    assert mid["wall_net_m2"] + mid["glazed_m2"] + mid["door_m2"] == pytest.approx(front_back)
    assert end["wall_net_m2"] + end["glazed_m2"] + end["door_m2"] == pytest.approx(front_back + 2 * d * h * n)
    assert gap["glazed_m2"] > P[t + "glazing_front_back"] * 2 * P[t + "width_gap"] * h * n  # side windows too


@pytest.mark.parametrize("variant", village.VARIANTS)
def test_townhouse_heat_lies_between_pass3s_flat_and_house(variant):
    # Pass 3: the average flat ~51 kWh/m2 a year, the detached house ~106 (docs/pass3/README.md).
    from brownfield import climate, screen
    from brownfield.cli import HOMER_CITY

    s = screen.plant_table(P).loc[HOMER_CITY]
    env = village.townhouse_env(P, variant)
    h = village.townhouse_heat(env, climate.hourly_temp(s.lat, s.lon), P)
    assert 45 < h["house_mwh"] * 1e3 / env["floor_m2"] < 110


def test_floor_over_the_garage_by_hand():
    env = village.townhouse_env(P, "gap")
    h = village.townhouse_heat(env, COLD, P)
    t = "village.townhouse."
    want = P[t + "garage_floor_u"] * house.BTU_FT2 * env["garage_m2"] * (P["pass3.loads.indoor_c"] - P[t + "garage_c"])
    assert h["floor_over_garage_w"] == pytest.approx(want)


def test_lots_fill_phase1_clear_of_the_spine_and_behind_the_setback():
    s = "village.site."
    homes = village.lots(P, "gap")
    assert len(homes) == int(P[s + "phase1_homes"])
    assert all(abs(x - P[s + "square_x"]) > P[s + "spine_w_m"] / 2 for x, _ in homes)
    assert min(y for _, y in homes) >= village.HALL_FACE_Y + P[s + "home_setback_m"]


def test_walk_minutes_by_hand():
    s = "village.site."
    home = (P[s + "square_x"] + 30.0, P[s + "square_y"] + 120.0)
    w = village.walks(P, [home])
    assert w["the square"][0] == pytest.approx(150.0 / (P["village.walking.speed_hcm_sidewalk"] * 60))


def test_upper_windows_never_quieter_than_lower_ones():
    levels = [lv for _, lv in village.noise_by_floor(P, 150.0, 3.0)]
    assert all(b >= a - 1e-9 for a, b in zip(levels, levels[1:]))


def test_affordable_price_by_hand():
    m, f = "village.money.", "pass4.finance."
    pay = P["pass4.rents.ami_usd"] * P[m + "front_end"] / 12
    r, n = P[f + "rate"] / 12, P[f + "term_yr"] * 12
    want = pay * (1 - (1 + r) ** -n) / r / (1 - P[m + "down_payment"])
    assert village.home_cost(P)["afford_usd"] == pytest.approx(want)


def test_the_neighbourhood_comes_first_and_the_tomato_houses_shrink():
    from brownfield import climate, food, screen
    from brownfield.cli import HOMER_CITY

    s = screen.plant_table(P).loc[HOMER_CITY]
    wx = food.local(climate.hourly_weather(s.lat, s.lon), -5)
    b = village.balance(P, wx)
    assert b["short_mwh"] == pytest.approx(0.0)
    assert b["ha_after"] <= b["ha_before"]
    for r in b["months"]:
        used = r["homes"] + r["shared buildings"] + r["fields"] + r["market section"] + r["tomatoes"]
        assert used <= r["spare"] + 1e-6
        assert r["left"] == pytest.approx(r["spare"] - used, abs=1e-3)
