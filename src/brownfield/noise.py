"""Pass 2: sound at the nearest homes, by ISO 9613-2's outdoor propagation (A-weighted, the
standard's single-band method at 500 Hz).

    L_p = L_W - A_div - A_atm - A_gr - A_bar        (dB(A); D_c = 0, a source radiating freely)

- A_div = 20 lg(d / 1 m) + 11                          spherical spreading from a point
- A_atm = alpha d / 1000                               air absorption, alpha in dB/km
- A_gr  = 4.8 - (2 h_m / d)(17 + 300 / d), >= 0        ground, the standard's eq. (10)
- A_bar                                                a berm or wall, a design choice

The output that holds up without vendor data is the **sound power budget**: the most a module may
emit for a level L at a home d metres away. Each design's own sound power (fans x per-fan level)
rests on placeholders until vendor sound data is in hand; the levers (slow fans, berms) are
physics: fan sound power falls as 50 lg(speed ratio) (the fan law; half speed = -15 dB).
"""

from __future__ import annotations

import numpy as np


def a_div(d: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(d) + 11.0


def a_gr(d: np.ndarray, h_m: float) -> np.ndarray:
    return np.clip(4.8 - (2.0 * h_m / d) * (17.0 + 300.0 / d), 0.0, None)


def attenuation(d, alpha_db_km: float, h_m: float, barrier_db: float = 0.0):
    d = np.asarray(d, dtype=float)
    return a_div(d) + alpha_db_km * d / 1000.0 + a_gr(d, h_m) + barrier_db


def level_at(lw: float, d, p: dict, barrier_db: float = 0.0):
    """Sound pressure level (dB(A)) at distance d (m) from a source of sound power lw."""
    return lw - attenuation(d, p["pass2.noise.alpha_db_km"], p["pass2.noise.h_m"], barrier_db)


def budget(target_db: float, d, p: dict, barrier_db: float = 0.0):
    """Most sound power (dB(A)) a source may have for target_db at distance d."""
    return target_db + attenuation(d, p["pass2.noise.alpha_db_km"], p["pass2.noise.h_m"], barrier_db)


def fan_law_db(speed_ratio: float) -> float:
    """Change in a fan's sound power when its speed changes by speed_ratio."""
    return 50.0 * np.log10(speed_ratio)


def module_lw(design: str, heat_mw: float, p: dict) -> float:
    """Sound power of one module's heat rejection (dB(A)): n fans at a per-fan level, summed
    energetically (+10 lg n). Good neighbour: dry coolers oversized by a factor k, so k times the
    fans, each at 1/k of the speed (airflow and speed scale together)."""
    n = "pass2.noise."
    if design == "conventional":
        fans = heat_mw / p[n + "tower_mw_per_fan"]
        return p[n + "tower_fan_lw"] + 10.0 * np.log10(fans)
    k = p[n + "dry_oversize"]
    fans = k * heat_mw / p[n + "dry_mw_per_fan"]
    return p[n + "dry_fan_lw"] + fan_law_db(1.0 / k) + 10.0 * np.log10(fans)


def distance_for(target_db: float, lw: float, p: dict, barrier_db: float = 0.0) -> float:
    """Distance (m) beyond which the level falls below target_db (bisection on 10 m - 20 km)."""
    lo, hi = 10.0, 20_000.0
    if level_at(lw, hi, p, barrier_db) > target_db:
        return float("inf")
    for _ in range(60):
        mid = (lo * hi) ** 0.5
        if level_at(lw, mid, p, barrier_db) > target_db:
            lo = mid
        else:
            hi = mid
    return hi
