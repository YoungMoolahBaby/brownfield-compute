"""Pass 4, the construction workforce: the schedule's arithmetic, beds and traffic, by hand."""

import numpy as np
import pandas as pd
import pytest

from brownfield import workforce as wf
from brownfield.params import load_params, values

P = values(load_params())
W = "workforce."
COUNTS = {"Rura": 5, "West": 7, "Harvey/Gaston": 5, "Bruner": 12, "Green": 5, "Helen": 5}


def test_each_site_is_on_site_for_its_buildings_times_their_years():
    t = wf.months(2026.0, 2040.0)
    sites = wf.aws(P, COUNTS, t)
    per, T = P[W + "workers_per_building"], P[W + "building_years"]
    for name, n in COUNTS.items():
        # Worker-months / 12 / workers a building = building-years on site.
        assert sites[name].sum() / 12 / per == pytest.approx(n * T, abs=1 / 12 * n)
        key = wf.SITES[name]
        assert sites[name][t < P[W + "start." + key] - 1e-9].sum() == 0
        assert sites[name][t >= P[W + "finish." + key] + 1 / 12].sum() == 0


def test_the_gas_plant_follows_its_reported_counts():
    g = wf.gas(P, np.array([2026.23, 2026.67, 2027.5, P[W + "gas_end"] + 0.1]))
    assert g[0] == pytest.approx(1000) and g[1] == pytest.approx(1800)
    assert g[2] == pytest.approx(P[W + "gas_plateau"])
    assert g[3] == 0.0


def test_beds_by_hand():
    h = pd.DataFrame([{"name": "Indiana County, Pennsylvania", "for_rent": 1000.0, "rental_vacancy": 0.10}])
    q = dict(P, **{W + "healthy_vacancy": 0.06, W + "hotel_rooms": 400.0, W + "hotel_share_crews": 0.5})
    b = wf.beds(q, h)
    # 10,000 rental homes in all; 600 vacant is balanced, so 400 spare; 200 hotel rooms.
    assert b["stock"] == pytest.approx(10000.0)
    assert b["spare_rentals"] == pytest.approx(400.0)
    assert b["units"] == pytest.approx(600.0)
    q2 = dict(q, **{W + "travel_share": 0.3, W + "workers_per_unit": 1.5})
    assert wf.need(q2, np.array([3000.0]))[0] == pytest.approx(600.0)


def test_the_shift_on_us_119_by_hand():
    q = dict(P, **{W + "vehicle_occupancy": 1.25, W + "arrive_hour_share": 0.8, W + "via_119_share": 0.5, W + "k_factor": 0.1,
                   W + "lane_capacity": 2000.0})
    r = wf.traffic(q, 2500.0, 6000.0)
    assert r["arrivals"] == pytest.approx(2500 / 1.25 * 0.8 * 0.5)
    assert r["base"] == pytest.approx(600.0)
    assert r["vc_after"] == pytest.approx((600 + 800) / 4000)
