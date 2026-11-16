"""Pass 3d, winter food: the greenhouse balance, the lamps, the pipe and the supply by hand."""

import numpy as np
import pytest

from brownfield import food, module
from brownfield.params import load_params, values

P = values(load_params())
N = 24 * 10  # ten days


def wx(t=0.0, ghi=0.0):
    return {"t": np.full(N, t), "ghi": np.full(N, ghi), "rh": np.full(N, 70.0), "hour_utc": np.tile(np.arange(24), N // 24)}


def test_dark_house_is_u_times_area_times_dt():
    # No sun, no lamps, no leakage, the screen no better than the cover: heat = U x cover ratio x dT,
    # the same as pass 2's greenhouse_demand per m2 of floor.
    q = dict(P, **{"food.light.dli_tomato": 0.0, "food.heat.ach": 0.0, "food.heat.u_glass_screen": P["food.heat.u_glass"],
                   "food.heat.set_night_tomato": 18.0, "pass2.greenhouse.u_w_m2k": P["food.heat.u_glass"],
                   "pass2.greenhouse.set_c": 18.0, "pass2.greenhouse.hectares": 1e-4})
    hs = food.house(wx(-5.0), q, "tomato", "glass")
    assert hs["heat_w"][0] == pytest.approx(P["food.heat.u_glass"] * P["pass2.greenhouse.cover_ratio"] * 23.0)
    assert hs["heat_w"].sum() / 1e6 == pytest.approx(module.greenhouse_demand(np.full(N, -5.0), q).sum())


def test_lamps_make_up_the_dark_days_shortfall():
    # No sun: the lamps run target / (ppfd x 3600 / 1e6) hours a day, capped by the photoperiod.
    nat, lamp = food.lamps(np.zeros(N), P, "lettuce", "glass")
    per_hour = P["food.light.lamp_ppfd_lettuce"] * 3600 / 1e6
    hours = min(P["food.light.dli_lettuce"] / per_hour, P["food.light.photoperiod_lettuce"])
    assert lamp.reshape(-1, 24).sum(axis=1) == pytest.approx(np.full(N // 24, hours * per_hour))
    assert nat.sum() == 0.0


def test_bright_days_need_no_lamps():
    ghi = np.tile(np.r_[np.zeros(8), np.full(8, 700.0), np.zeros(8)], N // 24)
    _, lamp = food.lamps(ghi, P, "lettuce", "glass")
    assert lamp.sum() == 0.0


def test_pipe_capacity_by_hand():
    # AHDB: 30 W/m2 per 10 K for 1.25 m/m2 of pipe; here 2.5 m/m2 at a 45 C mean pipe against 18.5 C air.
    hs = {"set_c": np.array([18.5])}
    want = P["food.heat.pipe_w_m2_10k"] / 10 * P["food.heat.pipe_m_m2"] / 1.25 * (45.0 - 18.5)
    assert food.pipe_cap_w(hs, P)[0] == pytest.approx(want)


def test_supply_balances_and_never_exceeds_what_is_there():
    hs = food.house(wx(-10.0), P, "tomato", "glass")
    avail = np.full(N, 5.0)  # MW spare
    r = food.simulate(hs, avail, P, "tomato", "glass", 30.0)
    assert r.dc_mwh + r.backup_mwh == pytest.approx(r.demand_mwh)
    assert r.dc_mwh <= avail.sum() + P["food.heat.buffer_m3_ha"] * 30 * food.WATER_KWH_M3K * 10 / 1000 + 1e-6
    assert r.backup_mwh == pytest.approx(r.pipe_mwh + r.short_mwh)


def test_plenty_of_heat_leaves_only_the_pipe_limit():
    hs = food.house(wx(-15.0), P, "lettuce", "glass")
    r = food.simulate(hs, np.full(N, 1e6), P, "lettuce", "glass", 10.0)
    assert r.short_mwh == pytest.approx(0.0, abs=1e-9)
    over = np.clip(hs["heat_w"] - food.pipe_cap_w(hs, P), 0, None) * 1e5 / 1e6
    assert r.pipe_mwh == pytest.approx(over.sum())


def test_yield_is_light_times_efficiency():
    hs = {"nat_mol": np.full(N, 0.5), "lamp_mol": np.zeros(N)}  # 12 mol a day, under the cap
    want = 12.0 * (N // 24) * P["food.yield.lue_tomato"] * P["food.yield.in_crop_tomato"] / 1000
    assert food.yield_kg_m2(hs, P, "tomato") == pytest.approx(want)


def test_more_area_never_needs_less_boiler():
    hs = food.house(wx(-8.0, 0.0), P, "tomato", "glass")
    shares = [food.simulate(hs, np.full(N, 20.0), P, "tomato", "glass", ha).short_share for ha in (10, 40, 80, 160)]
    assert all(b >= a - 1e-12 for a, b in zip(shares, shares[1:]))
