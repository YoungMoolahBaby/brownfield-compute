"""Pass 3b: the walk-up's wood frame against published spans and hand-worked values."""

import math

from brownfield import frame
from brownfield.params import load_params, values

P = values(load_params())


def test_span_tables_reproduced():
    for r in frame.known_cases():
        if "SPF" in r["case"]:
            # SFPA 2013 spans, to the inch.
            assert 0 <= r["model_in"] - r["table_in"] < 1.0, r
        else:
            # APA nailed-only spans (table minus 12 in.), within 2%.
            assert abs(r["model_in"] - r["table_in"]) / r["table_in"] < 0.02, r


def test_flat_roof_snow():
    ld = frame.loads(P)
    assert abs(ld["roof_snow"] - 0.7 * 35) < 1e-9
    # Below 20 psf of flat-roof load the low-slope minimum takes over (pg > 20 psf).
    q = dict(P, **{"pass3.frame.ground_snow_psf": 25.0})
    assert frame.loads(q)["roof_snow"] == 20.0
    assert abs(ld["topping"] - 1.5 / 12 * 115) < 1e-9


def test_column_stability_factor():
    # NDS eq. 3.7-1 with FcE / Fc* = 1 and c = 0.8: 1.25 - sqrt(1.25^2 - 1.25).
    assert abs(frame.column_cp(1000.0, 1000.0) - (1.25 - math.sqrt(1.5625 - 1.25))) < 1e-12


def test_header_by_hand():
    # 3-2x8 SPF over 75 in., 300 + 400 plf: M = 700 x (75/12)^2 / 8 ft-lb against S = 3 x 1.5 x 7.25^2 / 6
    # and Fb' = 875 x 1.2 (C_F) x 1.15 (C_r, 3 plies) x 1.0 (C_D).
    r = frame.header(3, "2x8", 75.0, 300 / 12, 400 / 12, 1.0)
    m = 700 * (75 / 12) ** 2 / 8 * 12
    assert abs(r["bending"] - m / (3 * 1.5 * 7.25 ** 2 / 6) / (875 * 1.2 * 1.15)) < 1e-9
    assert abs(r["reaction_lb"] - 700 / 12 * 75 / 2) < 1e-9


def test_joist_deflection_by_hand():
    # A 2x12 SPF at 16 in. under 40 psf live: 5 w L^4 / 384 E I, w = 40 x 16 / 144 lb/in.
    L = 200.0
    r = frame.joist(("lumber", "SPF", "2x12"), 16, L, 10, 40, 1.0, 360, None)
    w = 40 * 16 / 144
    delta = 5 * w * L ** 4 / (384 * 1.4e6 * 1.5 * 11.25 ** 3 / 12)
    assert abs(r["deflection_live"] - delta / (L / 360)) < 1e-12


def test_wood_density():
    # NDS Supplement weight of wood: 62.4 [G / (1 + G 0.009 mc)] (1 + mc/100) lb/ft3, G 0.42 at 15%.
    lb_ft3 = 62.4 * 0.42 / (1 + 0.42 * 0.009 * 15) * 1.15
    assert abs(frame.wood_density(0.42, 15) - lb_ft3 * 16.0185) < 1e-9
    assert 450 < frame.wood_density(0.42, 15) < 465


def test_build_summary():
    from brownfield import build
    lifts = [{"storey": 1, "group": "facades", "length_m": 4.0, "kg": 200.0, "lift_lbf": 230.0, "framed_lift_lbf": 150.0,
              "crew": 5, "jack": False, "sheathed": True, "peak_servo_nm": 101.0, "statics_flat_nm": 100.0},
             {"storey": 1, "group": "facades", "length_m": 4.8, "kg": 260.0, "lift_lbf": 330.0, "framed_lift_lbf": 210.0,
              "crew": 7, "jack": True, "sheathed": True, "peak_servo_nm": 99.0, "statics_flat_nm": 100.0}]
    rows = build.lift_summary({"lifts": lifts})
    assert len(rows) == 1 and rows[0]["panels"] == 2 and rows[0]["crew"] == 7 and rows[0]["jacks"] == 1
    assert abs(build.sim_vs_statics({"lifts": lifts}) - 0.01) < 1e-12
