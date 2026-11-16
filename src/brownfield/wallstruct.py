"""Pass 2d: the wall's structure, a reinforced brick pier-and-panel wall under wind.

Wind, ASCE 7-16 chapter 29.3 (solid freestanding walls):

    q_h = 0.00256 K_z K_zt K_d K_e V^2   (psf, V in mph, at the wall's top; Exposure C)
    F   = q_h G C_f A_s                   (strength level; x 0.6 for allowable stress design)
    K_z = 2.01 (z / z_g)^(2/alpha), z >= 15 ft;  alpha = 9.5, z_g = 900 ft (Exposure C)

The wall: two wythes of modular brick with a grouted collar joint between them, spanning
sideways between reinforced brick piers (BIA Technical Note 45A's pier-and-panel system); the
panel's horizontal bars lie in the collar joint, the piers' vertical bars in their grouted cores;
each pier stands on a drilled concrete shaft, and a grade beam to the frost line carries the panels.

Masonry, TMS 402-16 allowable stress design for reinforced members (cracked, transformed section):

    rho n = A_s n / (b d);  k = sqrt(2 rho n + (rho n)^2) - rho n;  j = 1 - k/3
    f_s = M / (A_s j d) <= F_s;   f_b = 2 M / (j k b d^2) <= 0.45 f'm

Shafts: the IBC's non-constrained pole embedment (IBC 1807.3.2.1, as CMHA TEK 14-15B uses it):

    d = (A/2) [1 + sqrt(1 + 4.36 h / A)],  A = 2.34 P / (S_1 b),  S_1 at d/3

Checked against BIA TN 45A's worked examples, CMHA TEK 14-19B, Caltrans' and MECA's ASCE 7-16
wind examples (tests/test_wall.py).
"""

from __future__ import annotations

import math

FT, IN = 0.3048, 0.0254
# ASTM A615 bar areas (in^2) and weights (kg/m) by bar number.
BAR_AREA = {3: 0.11, 4: 0.20, 5: 0.31, 6: 0.44, 7: 0.60, 8: 0.79}
BAR_KG_M = {3: 0.560, 4: 0.994, 5: 1.552, 6: 2.235, 7: 3.042, 8: 3.973}


def kz_c(z_m: float, alpha: float = 9.5, zg_ft: float = 900.0) -> float:
    """Velocity pressure exposure coefficient, Exposure C (ASCE 7-16 Table 26.10-1's formula)."""
    return 2.01 * (max(z_m / FT, 15.0) / zg_ft) ** (2.0 / alpha)


def qh_psf(v_mph: float, kz: float, kd: float, ke: float, kzt: float = 1.0) -> float:
    return 0.00256 * kz * kzt * kd * ke * v_mph ** 2


def cracked(as_in2: float, b_in: float, d_in: float, n: float) -> tuple[float, float]:
    """(k, j) of a singly reinforced cracked section."""
    rn = as_in2 * n / (b_in * d_in)
    k = math.sqrt(2 * rn + rn * rn) - rn
    return k, 1 - k / 3


def stresses(m_lbin: float, as_in2: float, b_in: float, d_in: float, n: float) -> dict:
    k, j = cracked(as_in2, b_in, d_in, n)
    return {"k": k, "j": j, "fs": m_lbin / (as_in2 * j * d_in), "fb": 2 * m_lbin / (j * k * b_in * d_in ** 2)}


def capacity(as_in2: float, b_in: float, d_in: float, n: float, fs: float, fb: float) -> float:
    """Allowable moment (lb-in): the lesser of the steel's and the masonry's."""
    k, j = cracked(as_in2, b_in, d_in, n)
    return min(as_in2 * fs * j * d_in, 0.5 * fb * k * j * b_in * d_in ** 2)


def embedment_ft(p_lb: float, h_ft: float, b_ft: float, s1_psf_ft: float) -> float:
    """Depth (ft) of a non-constrained pole or shaft for lateral load P at h above grade, the soil's
    allowable lateral bearing S_1 taken at a third of the depth (fixed-point iteration)."""
    d = 6.0
    for _ in range(200):
        s1 = s1_psf_ft * d / 3.0
        a = 2.34 * p_lb / (s1 * b_ft)
        d_new = a / 2.0 * (1.0 + math.sqrt(1.0 + 4.36 * h_ft / a))
        if abs(d_new - d) < 1e-9:
            break
        d = 0.5 * (d + d_new)
    return d


def wind_psf(p: dict, h_m: float, cf: float) -> float:
    """Net design pressure (psf, allowable stress level) on a wall h_m tall."""
    w = "wall.wind."
    q = qh_psf(p[w + "v_mph"], kz_c(h_m), p[w + "kd"], p[w + "ke"])
    return p[w + "asd"] * max(q * p[w + "g"] * cf, 16.0)


def wall_t_in(p: dict) -> float:
    return 2 * p["wall.brick.unit_w_in"] + p["wall.brick.collar_in"]


def design(p: dict, h_m: float, cf: float) -> dict:
    """Panel bars, pier bars and shaft depth for a wall h_m tall under net force coefficient cf."""
    m, d = "wall.masonry.", "wall.design."
    fm = p[m + "fm_psi"]
    n = p[m + "es_psi"] / (p[m + "em_coef"] * fm)
    fs, fb = p[m + "fs_psi"], p[m + "fb_coef"] * fm
    w = wind_psf(p, h_m, cf)
    span = p[d + "pier_spacing_ft"]
    h_ft = h_m / FT
    t = wall_t_in(p)
    # Panel: spans between piers; bars at the collar joint's centre, spaced in 8 in. lifts.
    m_panel = w * span ** 2 / 8.0 * 12.0  # lb-in per ft of height
    panel = None
    for bar in (4, 5, 6):
        for s in (48, 40, 32, 24, 16, 8):
            a = BAR_AREA[bar] * 12.0 / s
            if capacity(a, 12.0, t / 2.0, n, fs, fb) >= m_panel:
                panel = {"bar": bar, "spacing_in": s, "ok": True, **stresses(m_panel, a, 12.0, t / 2.0, n)}
                break
        if panel:
            break
    if panel is None:  # nothing in the list carries it: the heaviest, flagged
        panel = {"bar": 6, "spacing_in": 8, "ok": False, **stresses(m_panel, BAR_AREA[6] * 1.5, 12.0, t / 2.0, n)}
    # Pier: a cantilever from the shaft; the resultant at `resultant` of the height.
    force = w * span * h_ft
    m_pier = force * p["wall.wind.resultant"] * h_ft * 12.0
    pd = p[d + "pier_d_in"] - p[m + "cover_in"]
    pier = None
    for count in (2, 3, 4, 5, 6):
        for bar in (5, 6, 7, 8):
            a = count * BAR_AREA[bar]
            if capacity(a, p[d + "pier_w_in"], pd, n, fs, fb) >= m_pier:
                pier = {"bars_per_face": count, "bar": bar, "ok": True, **stresses(m_pier, a, p[d + "pier_w_in"], pd, n)}
                break
        if pier:
            break
    if pier is None:  # the pier is too small for the wind: the heaviest, flagged
        pier = {"bars_per_face": 6, "bar": 8, "ok": False, **stresses(m_pier, 6 * BAR_AREA[8], p[d + "pier_w_in"], pd, n)}
    depth = embedment_ft(force, p["wall.wind.resultant"] * h_ft, p[d + "shaft_dia_in"] / 12.0,
                         p[m + "s1_psf_ft"] * p[m + "wind_soil_increase"])
    return {"h_m": h_m, "cf": cf, "w_psf": w, "panel_m_lbin": m_panel, "panel": panel, "pier_force_lb": force,
            "pier_m_lbin": m_pier, "pier": pier, "shaft_depth_ft": depth, "n": n}


def per_metre(p: dict, h_m: float, dz: dict) -> dict:
    """Materials per metre of wall h_m tall with design `dz`: brick (count), mortar, grout,
    concrete (m3), steel (kg)."""
    b, d, m = "wall.brick.", "wall.design.", "wall.masonry."
    span_m = p[d + "pier_spacing_ft"] * FT
    module = (p[b + "unit_l_in"] + p[b + "joint_in"]) * (p[b + "unit_h_in"] + p[b + "joint_in"]) * IN ** 2
    per_m2 = 1.0 / module  # bricks per m2 of one wythe's face
    wall_bricks = 2 * per_m2 * h_m
    t_m = wall_t_in(p) * IN
    # The pier beyond the wall's thickness: brick shell round a grouted core.
    pier_m3 = p[d + "pier_w_in"] * IN * (p[d + "pier_d_in"] * IN - t_m) * h_m
    unit_m3 = module * (p[b + "unit_w_in"] + p[b + "joint_in"]) * IN
    pier_bricks = pier_m3 * (1 - p[m + "pier_grout_share"]) / unit_m3
    bricks = wall_bricks + pier_bricks / span_m
    grout = p[b + "collar_in"] * IN * h_m + pier_m3 * p[m + "pier_grout_share"] / span_m
    shaft_m = dz["shaft_depth_ft"] * FT
    dia = p[d + "shaft_dia_in"] * IN
    concrete = (math.pi * dia ** 2 / 4 * shaft_m + p[d + "grade_beam_w_in"] * IN * p[d + "grade_beam_d_in"] * IN * max(span_m - dia, 0)) / span_m
    pan, pier = dz["panel"], dz["pier"]
    steel = (h_m / (pan["spacing_in"] * IN)) * BAR_KG_M[pan["bar"]]  # panel bars, per metre of wall
    steel += 2 * pier["bars_per_face"] * BAR_KG_M[pier["bar"]] * (h_m + shaft_m) / span_m  # both faces, into the shaft
    steel += p[m + "shaft_bars"] * BAR_KG_M[5] * shaft_m / span_m
    mortar = bricks * p[m + "mortar_m3_per_1000"] / 1000.0
    return {"bricks": bricks, "bricks_per_m2_wythe": per_m2, "mortar_m3": mortar, "grout_m3": grout, "concrete_m3": concrete,
            "steel_kg": steel, "thick_m": t_m, "pier_d_m": p[d + "pier_d_in"] * IN}
