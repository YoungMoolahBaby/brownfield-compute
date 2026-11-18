"""Pass 4b: the tax split, PDE's aid ratio, the schools' parsing, the drive cache and the build's injuries."""

import numpy as np
import pandas as pd
import pytest

from brownfield import districts, econ, services
from brownfield.params import load_params, values

P = values(load_params())
M = "pass4.money."


def test_the_campus_tax_by_hand_on_a_50_50_split():
    tx = econ.campus_tax(P, split=(0.5, 0.5))
    assessed = P[M + "dc_buildings"] * P[M + "dc_ft2_each"] * P[M + "dc_value_ft2"] * P[M + "clr"]
    assert tx["school_homer_center"] == pytest.approx(assessed * 0.5 * P[M + "mills_school"] / 1000)
    assert tx["school_river_valley"] == pytest.approx(assessed * 0.5 * P[M + "mills_school_rivervalley"] / 1000)
    assert tx["township"] == pytest.approx(assessed * 0.5 * (P[M + "mills_township"] + P[M + "mills_township_blacklick"]) / 1000)
    assert tx["total"] == pytest.approx(tx["county"] + tx["township"] + tx["school"])
    # All on Center's side is pass 4's old figure.
    old = econ.campus_tax(P, split=(1.0, 0.0))
    assert old["total"] == pytest.approx(assessed * (P[M + "mills_county"] + P[M + "mills_township"] + P[M + "mills_school"]) / 1000)


def test_the_building_split_covers_all_39_and_each_site_once():
    df = districts.buildings(P)
    assert df.buildings.sum() == pytest.approx(39.0, abs=0.01)
    assert (df.groupby("site").pixel_share.sum() - 1).abs().max() < 1e-3
    sh = districts.shares(P)["township"]
    assert sum(sh.values()) == pytest.approx(1.0)


def test_split_assigns_pixels_by_polygon():
    from shapely.geometry import box

    towns = [("West", box(0, 0, 1, 1)), ("East", box(1, 0, 2, 1))]
    schools = [("A", box(0, 0, 2, 1))]
    sites = {"S": {"n": 10, "building_xy": np.array([[0.5, 0.5], [0.6, 0.5], [0.7, 0.5], [1.5, 0.5]])}}
    df = districts.split(sites, towns, schools, lambda x, y: (x, y))
    got = df.set_index("township").buildings.to_dict()
    assert got == {"West": pytest.approx(7.5), "East": pytest.approx(2.5)}


def test_aid_ratio_by_hand_and_its_floors():
    # A district at the state's own market value and income per WADM: both ratios 0.5, combined 0.5.
    r = services.aid_ratio(500_000.0 * 1000, 250_000.0 * 1000, 1000.0, 500_000.0, 250_000.0, P)
    assert r == {"mv_ar": 0.5, "pi_ar": 0.5, "mvpi_ar": 0.5}
    # Ten times the state's market value per WADM: the market value ratio floors at 0.10.
    r = services.aid_ratio(5_000_000.0 * 1000, 250_000.0 * 1000, 1000.0, 500_000.0, 250_000.0, P)
    assert r["mv_ar"] == 0.10 and r["mvpi_ar"] == pytest.approx(0.6 * 0.10 + 0.4 * 0.5)


def test_grades_reads_a_pde_lea_sheet():
    lea = pd.DataFrame({"AUN": [128323303, 999], "K5A": [2, 0], "K5P": [3, 0], "K5F": [50, 0],
                        **{f"{g:03d}": [60 + g, 0] for g in range(1, 13)}})
    g = services.grades(lea)
    assert list(g.district) == ["Homer-Center"]
    assert g.K.iloc[0] == 55 and g.g12.iloc[0] == 72


def test_construction_injuries_by_hand():
    t = np.arange(0, 2, 1 / 12)
    w = np.full(len(t), 1200.0)
    b = services.construction(P, w, t)
    assert b["worker_years"] == pytest.approx(2400.0)
    assert b["injuries"] == pytest.approx(2400 * 2.3 / 100)
    assert b["deaths"] == pytest.approx(2400 * 9.6 / 1e5)


def test_osrm_reads_its_cache(tmp_path, monkeypatch):
    import json

    o, d = {"A": (40.5, -79.2)}, {"H": (40.6, -79.15)}
    key = json.dumps({"o": o, "d": d}, sort_keys=True)
    cache = tmp_path / "osrm.json"
    cache.write_text(json.dumps({key: {"durations": [[600.0]], "distances": [[9100.0]]}}), encoding="utf-8")
    monkeypatch.setattr(services, "OSRM_CACHE", cache)
    t = services.osrm_table(o, d)
    assert t["minutes"].loc["A", "H"] == pytest.approx(10.0) and t["km"].loc["A", "H"] == pytest.approx(9.1)
