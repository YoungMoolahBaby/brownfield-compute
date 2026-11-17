"""D16, the centre's running costs and memberships by hand."""

import pytest

from brownfield import center
from brownfield.params import load_params, values

P = values(load_params())
M = "village.membership."


def test_running_cost_by_hand():
    q = dict(P, **{M + "posts_day": 2, M + "posts_night": 1, M + "day_h": 16, M + "opex_per_fte": 100000.0})
    r = center.running(q)
    fte = (2 * 16 + 1 * 8) * 365 / 2080  # 7.02 posts
    assert r["fte"] == pytest.approx(fte)
    assert r["the building (staff, supplies, energy, upkeep)"] == pytest.approx(fte * 100000.0)


def test_break_even_fee_by_hand():
    cost = sum(v for k, v in center.running(P).items() if k != "fte")
    left = cost - sum(center.income(P).values())
    assert center.break_even(P, 5000) == pytest.approx(left / 5000 / 12)
    # More members, a lower fee.
    assert center.break_even(P, 10000) < center.break_even(P, 3000)


def test_league_income_by_hand():
    i = center.income(P)
    assert i["volleyball leagues"] == pytest.approx(P[M + "volleyball_teams"] * 590 * P[M + "seasons_yr"])
    assert i["ice rented by the hour"] == pytest.approx(P[M + "ice_hours_week"] * P[M + "ice_weeks"] * P[M + "ice_usd_h"])
