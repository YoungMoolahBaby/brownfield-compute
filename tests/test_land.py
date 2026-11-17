"""D17, the real land: the master plan's fit, slope, drawing and grouping by hand."""

import math

import numpy as np
import pytest

from brownfield import land
from brownfield.params import load_params, values

P = values(load_params())


def test_the_fit_moves_turns_and_scales_like_a_map():
    f = land.Fit(10.0, 0.0, 100.0, -50.0)
    # The sheet's centre lands on the shift; 10 px right is 100 m east; 10 px down is 100 m south.
    assert f.xy(f.cx, f.cy) == pytest.approx((100.0, -50.0))
    assert f.xy(f.cx + 10, f.cy) == pytest.approx((200.0, -50.0))
    assert f.xy(f.cx, f.cy + 10) == pytest.approx((100.0, -150.0))
    turned = land.Fit(10.0, math.pi / 2, 0.0, 0.0)  # a quarter turn: right on the sheet is north on the map
    assert turned.xy(turned.cx + 1, turned.cy) == pytest.approx((0.0, 10.0))


def test_slope_of_a_plane_by_hand():
    # A plane rising 1 m in 10 m east and 1 m in 20 m north: sqrt(0.1^2 + 0.05^2) = 11.18%.
    y, x = np.mgrid[0:20, 0:30]
    z = 0.1 * x * 10.0 - 0.05 * y * 10.0  # rows run south, so north is up the rows
    s = land.slope_pct(z, 10.0, 10.0)
    assert s[5:15, 5:25] == pytest.approx(100 * math.hypot(0.1, 0.05))


def test_components_group_touching_pixels():
    m = np.zeros((6, 6), bool)
    m[0:2, 0:2] = True  # four
    m[3:6, 4] = True    # three, apart
    m[2, 2] = True      # touches the first block's corner (8-way)
    comps = land.components(m, min_px=1)
    assert sorted(len(c) for c in comps) == [3, 5]


def test_drawing_a_square_covers_its_area():
    g = land.Grid(P)
    from shapely.geometry import box

    sq = box(-500.0, -500.0, 500.0, 500.0)  # 100 ha round the old plant
    assert g.draw([sq]).sum() * g.cell_ha == pytest.approx(100.0, rel=0.03)


def test_the_six_sites_share_the_filings_39_buildings():
    s = land.aws_sites(P)
    land.site_counts(P, s)
    assert sum(v["n"] for v in s.values()) == int(P["land.aws.buildings"])
    assert set(s) == {"Bruner", "Helen", "Green", "West", "Harvey/Gaston", "Rura"}
    # The drawn buildings come to about the filing's 39 footprints (within 15%).
    foot = P["land.aws.footprint_ft2"] * 0.09290304
    assert sum(v["building_m2"] for v in s.values()) / foot == pytest.approx(39, rel=0.15)


def test_the_permit_points_fall_in_their_sites():
    from shapely.geometry import Point

    from brownfield.homes import Local

    s = land.aws_sites(P)
    loc = Local(*land.PLANT)
    rura = Point(*loc.xy(-79.18379, 40.50361))
    west = Point(*loc.xy(-79.2042, 40.5088))
    assert s["Rura"]["footprint"].contains(rura)
    assert s["West"]["footprint"].distance(west) < 150.0  # the grading permit's centre, at the drawn buildings' edge


def test_the_two_point_start_lands_on_its_published_points():
    from brownfield.homes import Local

    f = land.two_point_start()
    loc = Local(*land.PLANT)
    for px, (lat, lon) in zip(land.START_PX, land.START_LL):
        assert f.xy(*px) == pytest.approx(loc.xy(lon, lat), abs=0.01)
