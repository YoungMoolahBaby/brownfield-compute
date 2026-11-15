"""Offline checks of pass 1's pieces against hand-worked cases."""

import numpy as np
import pandas as pd

from brownfield import climate, rank
from brownfield.params import check_params, load_params, values


def test_params_are_complete():
    assert check_params(load_params()) == []


def test_climate_stats_by_hand():
    # 365 days at a steady 8 C: 10 C below an 18 C base every day -> 3650 C day; no hot hours.
    s = climate.stats(np.full(8760, 8.0), base_c=18.0, limit_c=30.0)
    assert abs(s["hdd"] - 3650.0) < 1e-9 and s["hot_hours"] == 0 and s["mean_c"] == 8.0
    # 182 days at 35 C (4368 hours above 30 C, no heating), then 183 days at 8 C (1830 C day).
    t = np.concatenate([np.full(182 * 24, 35.0), np.full(183 * 24, 8.0)])
    s = climate.stats(t, base_c=18.0, limit_c=30.0)
    assert s["hot_hours"] == 4368 and abs(s["hdd"] - 1830.0) < 1e-9


def test_rank_directions():
    # Site a is better on every host component and needier on every help component than b.
    t = pd.DataFrame({
        "leaving_mw": [2000.0, 200.0], "sfha_share": [0.0, 0.8], "hot_hours": [10, 900],
        "coal_retiring_mw": [0.0, 0.0], "last_retired": [2025.0, 2016.0],
        "pop_change": [-0.10, 0.20], "income_vs_us": [0.6, 1.3], "hdd": [4000.0, 1000.0],
    }, index=["a", "b"])
    r = rank.rank(t, values(load_params()))
    assert r.loc["a", "host"] > r.loc["b", "host"] and r.loc["a", "help"] > r.loc["b", "help"]
    assert list(r.index) == ["a", "b"]


def test_missing_counts_as_median():
    t = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
    assert rank._pct(t["x"], True).iloc[1] == 0.5
