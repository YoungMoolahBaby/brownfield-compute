"""Pass 3c, the winter garden and the rooftop coolers: closed forms and hand-worked cases."""

import math

import numpy as np
import pytest

from brownfield import garden
from brownfield.params import load_params, values

P = values(load_params())
G = {"floor_m2": {"level1": 300.0, "level2": 100.0}, "glass_m2": {"level1": 120.0, "level2": 80.0},
     "height_m": {"level1": 3.0, "level2": 2.5}}


def test_heat_is_ua_times_degree_hours():
    # Constant 0 C for a year: heat = UA x set point x 8760 h, UA summed by hand.
    p = P
    h = "garden.heat."
    ua1 = p[h + "glass_u"] * 120 + p[h + "roof_u"] * ((300 - 100) + 300) + 0.33 * p[h + "ach"] * 300 * 3.0
    ua2 = p[h + "glass_u"] * 80 + p[h + "roof_u"] * 100 + 0.33 * p[h + "ach"] * 100 * 2.5
    out = garden.heat(G, np.zeros(8760), p, 15.0)
    assert out["ua_w_k"] == pytest.approx(ua1 + ua2)
    assert out["mwh"] == pytest.approx((ua1 + ua2) * 15.0 * 8760 / 1e6)


def test_floor_follows_en_1264():
    # q = 8.92 (floor - room)^1.1 W/m2: the surface temperature returned gives back the output.
    out = garden.heat(G, np.zeros(8760), P, 18.0)
    for f in out["floors"]:
        assert 8.92 * (f["surface_c"] - 18.0) ** 1.1 == pytest.approx(f["q_w_m2"])
        assert f["supply_c"] > f["surface_c"]


def test_uncracked_cantilever_by_hand():
    # Deep and short, so it never cracks (Ie = Ig): tip deflection = w L^4 / 8EI + P L^3 / 3EI.
    p = P
    c = "garden.cantilever."
    h, L = 2000.0, 1500.0
    out = garden.cantilever(p, span_m=L / 1000, depth_mm=h, as_mm2_m=2000.0)
    ec = 4700 * math.sqrt(p[c + "fc_mpa"])
    ig = 1000 * h ** 3 / 12
    w = 24e-6 * h * 1000 + p[c + "superimposed_kpa"] * 1e-3 * 1000
    tip = p[c + "parapet_kn_m"] * 1000
    assert out["ie"] == pytest.approx(ig)
    assert out["d_dead_mm"] == pytest.approx(w * L ** 4 / (8 * ec * ig) + tip * L ** 3 / (3 * ec * ig))
    assert out["lambda"] == pytest.approx(p[c + "creep_xi"])  # no compression steel given


def test_required_steel_carries_the_moment():
    # phi As fy (d - a/2) = Mu, with a = As fy / (0.85 f'c b), at the required steel.
    p = P
    c = "garden.cantilever."
    out = garden.cantilever(p)
    as_, d = out["as_mm2_m"], out["depth_mm"] - p[c + "cover_mm"]
    a = as_ * p[c + "fy_mpa"] / (0.85 * p[c + "fc_mpa"] * 1000)
    phi_mn = 0.9 * as_ * p[c + "fy_mpa"] * (d - a / 2) / 1e6
    assert phi_mn == pytest.approx(out["mu_knm"], rel=1e-6) or as_ == pytest.approx(0.0018 * 1000 * out["depth_mm"])


def test_shallow_tray_fails_deep_tray_passes():
    # The design finding: 600 mm sags past L/240 long-term, 900 mm doesn't.
    assert not garden.cantilever(P, depth_mm=600)["ok"]
    assert garden.cantilever(P, depth_mm=900)["ok"]


def test_parapet_below_the_sight_lines_changes_nothing():
    # A 0.1 m upstand sits below every fan-to-home line, so it isn't on the diffraction path.
    low = garden.rooftop_noise(P, parapet_m=0.1, distances=[200.0])
    edge = garden.rooftop_noise(P, parapet_m=0.0, distances=[200.0])
    assert low["levels"][0] == pytest.approx(edge["levels"][0], abs=0.05)


def test_higher_parapet_never_louder():
    lv = [garden.rooftop_noise(P, parapet_m=h, distances=[300.0])["levels"][0] for h in (0.0, 1.5, 3.0, 4.0)]
    assert all(b <= a + 1e-9 for a, b in zip(lv, lv[1:]))


def test_quieter_fans_shift_every_level():
    a = garden.rooftop_noise(P, fan_cut_db=0.0, distances=[100.0, 400.0])
    b = garden.rooftop_noise(P, fan_cut_db=6.0, distances=[100.0, 400.0])
    assert np.allclose(a["levels"] - b["levels"], 6.0)
