"""Pass 2e, the creek: the low-flow statistic and the mixing balance against closed forms."""

from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest

from brownfield import creek


def test_lp3_with_no_skew_is_lognormal():
    # With zero skew of the logs, log-Pearson III is the lognormal: 10^(mean + z_p sd).
    y = np.array([-1.0, 0.0, 1.0, -0.5, 0.5])  # symmetric logs
    x = 10 ** (1.2 + 0.3 * y)
    m, s = np.log10(x).mean(), np.log10(x).std(ddof=1)
    assert creek.lp3_quantile(x, 0.1) == pytest.approx(10 ** (m + NormalDist().inv_cdf(0.1) * s), rel=1e-9)


def test_annual_7day_min_uses_climatic_years():
    # A flat 100 cfs with one dry week in August 2001 and one in February 2002: both fall in
    # climatic year 2001 (April 2001 - March 2002), whose minimum is the drier week.
    idx = pd.date_range("2000-04-01", "2003-03-31", freq="D")
    q = pd.Series(100.0, index=idx)
    q["2001-08-10":"2001-08-16"] = 20.0
    q["2002-02-10":"2002-02-16"] = 10.0
    lows = creek.annual_7day_min(q)
    assert list(lows.index) == [2000, 2001, 2002]
    assert lows[2001] == pytest.approx(10.0)
    assert lows[2000] == pytest.approx(100.0)


def test_mixing_conserves_heat():
    # 10 cfs at 20 C and 10 cfs at 40 C mix to 30 C; heat in = heat out.
    assert creek.mixed_temp(10, 20, 10, 40) == pytest.approx(30.0)
    qs, ts, qd, td = 23.0, 24.0, 10.5, 43.3
    tm = creek.mixed_temp(qs, ts, qd, td)
    assert qs * ts + qd * td == pytest.approx((qs + qd) * tm)


def test_units():
    assert creek.f_to_c(110) == pytest.approx(43.333, abs=1e-3)
    assert creek.c_to_f(creek.f_to_c(87.0)) == pytest.approx(87.0)
    assert 6.8 * creek.CFS_PER_MGD == pytest.approx(10.52, abs=0.01)
    # 1 MGD warmed 10 F carries 83.4 million BTU a day.
    assert creek.heat_mbtu_day(1.0, 70, 60) == pytest.approx(83.4)


# --- DEP's own calculation, reproduced (the known case) -------------------------------------------

from brownfield.params import load_params, values  # noqa: E402

P = values(load_params())


def test_dep_second_draft_limits_reproduce():
    # DEP fact sheet (second draft, Attachment 2) and draft permit p.42-43: Outfall 027's final
    # instantaneous maximum temperatures by period.
    published = [101.7, 96.2, 110, 110, 110, 110, 110, 110, 100.9, 79.5, 110, 110, 110, 110, 110, 110, 110, 96.3, 88.3]
    got = creek.dep_limits(P)["limit"].round(1).tolist()
    assert got == pytest.approx(published, abs=0.05)


def test_dep_first_draft_is_the_wwf_defaults():
    # The first draft (June 2026), which DEP said used the wrong default stream temperatures: a run
    # with the warm-water-fishery defaults reproduces it.
    first = {0: 91.4, 1: 96.2, 7: 98.9, 8: 81.6, 9: 81.5, 10: 107.0, 11: 110, 16: 109.4, 17: 91.1, 18: 80.6}
    got = creek.dep_limits(P, ambient=creek.tls_table()["amb_wwf"])["limit"].round(1)
    for i, v in first.items():
        assert got[i] == pytest.approx(v, abs=0.05)


def test_flows_in_dep_printout():
    # DEP's printed seasonal and downstream flows: January J 108.80, L 119.38; July 57.80, 68.38.
    d = creek.dep_limits(P)
    assert d["J"][0] == pytest.approx(108.8) and d["L"][0] == pytest.approx(119.38, abs=0.01)
    assert d["J"][9] == pytest.approx(57.8) and d["L"][9] == pytest.approx(68.38, abs=0.01)


def test_periods_cover_the_year():
    idx = creek.period_index(pd.date_range("2023-01-01", "2024-12-31", freq="D"))
    assert (idx >= 0).all() and set(idx) == set(range(19))


@pytest.mark.parametrize("site,y0,y1,published,tol", [
    ("03042000", 1952, 2008, 26.6, 0.03),  # USGS OFR 2011-1070, Blacklick Creek at Josephine
    ("03042500", 1969, 2008, 39.0, 0.03),  # same, Two Lick Creek at Graceton, regulated
    ("03042500", 1952, 1968, 11.3, 0.03),  # same, before the dams
])
def test_q710_matches_usgs(site, y0, y1, published, tol):
    try:
        q = creek.usgs_daily(site, "00060", "1950-01-01", "2010-03-31")["mean"]
    except Exception as e:  # offline and not cached
        pytest.skip(f"USGS data not available: {e}")
    lows = creek.annual_7day_min(q)
    lows = lows[(lows.index >= y0) & (lows.index <= y1) & (lows > 0)]
    assert creek.lp3_quantile(lows.values, 0.1) == pytest.approx(published, rel=tol)
