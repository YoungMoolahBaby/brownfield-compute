"""Pass 2d, the wall: ISO 9613-2's screening against a closed form and hand-worked cases."""

import numpy as np
import pytest

from brownfield import noise, wall
from brownfield.params import load_params, values

P = values(load_params())


@pytest.mark.parametrize("n", [0.1, 0.3, 1.0, 3.0])
def test_iso_barrier_matches_kurze_anderson(n):
    # With ground reflections handled separately (C2 = 40) and no meteorological correction,
    # ISO's D_z = 10 lg(3 + 20 N) is the familiar form of Maekawa's chart; Kurze and Anderson's
    # (1971) closed-form fit to the same measurements agrees within ~0.7 dB below ISO's 20 dB cap.
    lam = wall.wavelength()
    iso = wall.d_z(n * lam / 2, 1e3, 1e3, 2e3, c2=40.0, k_met=False)
    assert abs(iso - wall.kurze_anderson(n)) < 0.7


def test_cap():
    assert wall.d_z(50.0, 10.0, 10.0, 15.0, k_met=False) == 20.0
    assert wall.d_z(50.0, 10.0, 10.0, 15.0, e=1.0, k_met=False) == 25.0


def test_single_edge_by_hand():
    # Source 2 m up, receiver 2 m up, 100 m apart; a 5 m edge 10 m from the source.
    d_ss, e, d_sr, prof = wall.path((0.0, 2.0), (100.0, 2.0), [(10.0, 5.0)])
    assert e == 0.0
    assert d_ss == pytest.approx(np.hypot(10, 3))
    assert d_sr == pytest.approx(np.hypot(90, 3))
    assert prof - 100.0 == pytest.approx(np.hypot(10, 3) + np.hypot(90, 3) - 100)


def test_line_of_sight_clear_means_no_screening():
    # Edges below the line from source to receiver drop out of the tight path.
    d_ss, e, d_sr, prof = wall.path((0.0, 4.0), (100.0, 4.0), [(10.0, 3.0), (10.3, 3.0)])
    assert d_ss == 0.0 and prof == pytest.approx(100.0)
    s = wall.wall_screen(3.0, 3.5, 0.3)
    assert wall.insertion_loss(120.0, s, 20.0, 10.0, 4.0, 4.0, P) == pytest.approx(0.0, abs=1e-9)


def test_thin_wall_is_nearly_one_edge():
    lam = wall.wavelength()
    c3 = (1 + (5 * lam / 0.3) ** 2) / (1 / 3 + (5 * lam / 0.3) ** 2)
    assert 1.0 < c3 < 1.01


def test_screen_replaces_ground_effect():
    # One source right behind a wall: the excess attenuation is D_z, not D_z + A_gr.
    src, rcv = (-1.0, 4.0), (120.0, 4.0)
    s = wall.wall_screen(3.0, 6.0, 1e-6)
    d = 121.0
    d_ss, e, d_sr, prof = wall.path(src, rcv, list(s.edges))
    dz = wall.d_z(prof - d, d_ss, d_sr, d, e)
    a_gr = float(noise.a_gr(np.array(d), P["pass2.noise.h_m"]))
    grid = np.array([[src[0], 0.0]])
    il = (wall.level(100.0, rcv[0], wall.open_ground(), 1, 1, src[1], rcv[1], P, grid=grid)
          - wall.level(100.0, rcv[0], s, 1, 1, src[1], rcv[1], P, grid=grid))
    assert il == pytest.approx(dz - a_gr, abs=1e-6)


def test_screen_helps_most_near_it():
    # A deep yard behind an edge wall: insertion loss falls with distance and with yard depth.
    s = wall.wall_screen(3.0, 8.0, 0.35)
    near, far = (wall.insertion_loss(r, s, 100.0, 30.0, 4.0, 4.0, P) for r in (120.0, 700.0))
    assert near > far > 0
    deep = wall.insertion_loss(120.0, s, 30.0, 100.0, 4.0, 4.0, P)
    assert deep < near


# --- The wall's structure against published worked examples -------------------------------------

from brownfield import wallstruct as ws  # noqa: E402


def test_bia_45a_example_1_cantilever_section():
    # BIA TN 45A (1992) Design Example #1: M = 1000 ft-lb/ft, #5 at 32 in. (0.115 in2/ft), d = 3.815
    # in., n = 9.7 -> k 0.198, j 0.934, fs 29.3 ksi, fb 744 psi.
    s = ws.stresses(12_000, 0.115, 12, 3.815, 9.7)
    assert s["k"] == pytest.approx(0.198, abs=0.001)
    assert s["j"] == pytest.approx(0.934, abs=0.001)
    assert s["fs"] == pytest.approx(29_300, rel=0.002)
    assert s["fb"] == pytest.approx(744, rel=0.002)


def test_bia_45a_example_3_pier():
    # Example #3: M = 9000 ft-lb, As 0.307 in2, b 15.63 in., d 14.5 in. -> k 0.149, j 0.95,
    # fs 25.5 ksi, fb 458 psi.
    s = ws.stresses(108_000, 0.307, 15.63, 14.5, 9.7)
    assert s["k"] == pytest.approx(0.149, abs=0.002)
    assert s["fs"] == pytest.approx(25_500, rel=0.005)
    assert s["fb"] == pytest.approx(458, rel=0.015)


def test_tek_14_19b_moment_capacity():
    # CMHA TEK 14-19B Table 5b: No. 6 at 40 in., d 9.0 in., f'm 1500 psi -> 35,686 lb-in/ft (steel).
    assert ws.capacity(0.133, 12, 9.0, 21.5, 32_000, 0.45 * 1500) == pytest.approx(35_686, rel=0.003)


def test_asce_7_16_wall_wind_examples():
    # Caltrans Temporary Structures Manual App. A Ex. 1: qz 13.9 psf, F 11,910 lb.
    q = ws.qh_psf(93, 0.77, 0.85, 0.96)
    assert q == pytest.approx(13.9, abs=0.05)
    assert q * 0.85 * 1.6 * 630 == pytest.approx(11_910, rel=0.002)
    # MECA, a 6 ft wall at 120 mph, Exposure C: Kh 0.849, qh 26.6 psf.
    assert ws.kz_c(1.8) == pytest.approx(0.849, abs=0.001)
    assert ws.qh_psf(120, ws.kz_c(1.8), 0.85, 1.0) == pytest.approx(26.6, abs=0.05)


def test_shaft_depths_bracket_tek_14_15b():
    # TEK 14-15B Table 7 (w = 20 psf, 10 ft wall, 18 in. shaft, spans 10-20 ft): 7.0-9.5 ft. The IBC
    # pole formula with S1 = 300 psf/ft x 1.33 falls 0-0.8 ft short of it; without the 1/3 increase
    # it runs 0.4-0.5 ft deep. The project uses the deeper one (params/wall.yaml).
    published = [7.0, 7.5, 8.0, 8.5, 9.0, 9.5]
    for span, d_pub in zip((10, 12, 14, 16, 18, 20), published):
        lo = ws.embedment_ft(20 * span * 10, 5.0, 1.5, 300 * 1.33)
        hi = ws.embedment_ft(20 * span * 10, 5.0, 1.5, 300)
        assert lo - 0.01 <= d_pub <= hi + 0.01
        assert d_pub - lo < 0.8 and 0 < hi - d_pub < 0.6


def test_design_passes_its_own_checks():
    p = P
    fm = p["wall.masonry.fm_psi"]
    for cf in (p["wall.wind.cf_body"], p["wall.wind.cf_end"]):
        dz = ws.design(p, p["wall.design.perimeter_h_m"], cf)
        assert dz["panel"]["ok"] and dz["pier"]["ok"]
        for part in ("panel", "pier"):
            assert dz[part]["fs"] <= p["wall.masonry.fs_psi"]
            assert dz[part]["fb"] <= p["wall.masonry.fb_coef"] * fm


def test_bricks_per_m2_matches_bia():
    # BIA EPD11101 (2025): 73.81 modular brick per m2 at 3/8 in. joints.
    pm = ws.per_metre(P, 6.0, ws.design(P, 6.0, P["wall.wind.cf_body"]))
    assert pm["bricks_per_m2_wythe"] == pytest.approx(73.81, abs=0.01)


# --- The yard -------------------------------------------------------------------------------------

def test_yard_meets_the_well_rule_and_sizes_up():
    for layout in ("perimeter", "courts", "cells"):
        yd = wall.yard(P, layout)
        assert yd.units * P["wall.yard.unit_kw"] >= P["pass2.noise.dry_oversize"] * P["pass2.module.it_mw"] * 1.2e3
        assert wall.well_velocity(P, yd) <= P["wall.yard.well_v_max"]


def test_vendor_data_reproduce_pass2_sound_power():
    # Pass 2's module sound power (88 dB(A) a fan, 0.12 MW a fan, placeholders) against the makers'
    # data: ~86 dB(A) a fan (Kelvion unit 94 - 10 lg 6), 1,372 kW per 20 fans (EVAPCO).
    lw_pass2 = noise.module_lw("good neighbour", P["pass2.module.it_mw"] * 1.2, P)
    fans = P["pass2.noise.dry_oversize"] * P["pass2.module.it_mw"] * 1.2 / (1.372 / 20)
    lw_vendor = 86 + noise.fan_law_db(1 / P["pass2.noise.dry_oversize"]) + 10 * np.log10(fans)
    assert abs(lw_pass2 - lw_vendor) < 1.0


def test_courts_screen_one_way_cells_both():
    yd_c, yd_x = wall.yard(P, "courts"), wall.yard(P, "cells")
    hs, hr = P["wall.yard.fan_h_m"], P["wall.acoustics.ear_h_m"]
    il = {}
    for name, yd in (("courts", yd_c), ("cells", yd_x)):
        for direction in ("across", "along"):
            s, depth, width = wall.screen_for(P, yd, direction)
            il[name, direction] = wall.insertion_loss(300.0, s, width, depth, hs, hr, P)
    assert il["courts", "across"] > 3 * il["courts", "along"]
    assert il["cells", "along"] > 2 * il["courts", "along"]
