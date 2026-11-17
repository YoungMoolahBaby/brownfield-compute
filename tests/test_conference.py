"""D17, the conference of communities: shares, glass, windows and costs by hand."""

import numpy as np
import pytest

from brownfield import conference as cf, rings
from brownfield.params import load_params, values

P = values(load_params())
C = "village.conference."
SITES = {"A": {"n": 12}, "B": {"n": 5}, "C": {"n": 7}}


def test_each_sites_homes_add_up_to_the_newcomers():
    h = cf.site_homes(P, SITES)
    c = rings.counts(P)
    assert sum(v["homes"] for v in h.values()) == c["flats"] + c["townhouses"] + c["houses"]
    assert sum(v["flats"] for v in h.values()) == c["flats"]
    # A site with more buildings gets more homes and more of the jobs.
    assert h["A"]["homes"] > h["C"]["homes"] > h["B"]["homes"]
    assert sum(v["jobs"] for v in h.values()) == pytest.approx(P["pass4.demand.jobs"])


def test_the_glass_split_keeps_the_markets_area():
    h = cf.site_homes(P, SITES)
    g = cf.glass(P, h)
    assert sum(g.values()) == pytest.approx(P["site.greenhouse_ha"])
    assert g["A"] / g["B"] == pytest.approx(h["A"]["homes"] / h["B"]["homes"])


def test_window_share_by_hand():
    m = np.zeros((5, 5), bool)
    m[0:2, 0:2] = True  # four cells in the corner
    s = cf.window_share(m, 1)
    assert s[0, 0] == pytest.approx(1.0)       # its 2 x 2 window at the corner is all in
    assert s[2, 2] == pytest.approx(1 / 9)     # the middle's 3 x 3 window holds one
    assert s[4, 4] == pytest.approx(0.0)


def test_a_clubhouse_by_hand():
    q = dict(P, **{C + "clubhouse_ft2": 10000.0, C + "clubhouse_posts": 2.0, "village.community_center.rec_center_build_usd_ft2": 400.0,
                   "village.membership.day_h": 16.0, "village.membership.opex_per_fte": 100000.0})
    c = cf.clubhouse(q)
    assert c["build"] == pytest.approx(4.0e6)
    assert c["run"] == pytest.approx(2 * 16 * 365 / 2080 * 100000.0)


def test_members_count_the_towns_and_their_new_homes():
    homes = {"A": {"homes": 50, "people": 120.0}, "B": {"homes": 20, "people": 50.0}}
    comm = {"A": {"town": "Homer City"}, "B": {"town": "Black Lick"}}
    town = {"Homer City": {"people": 1000.0}, "Lucerne Mines": {"people": 500.0}, "Black Lick": {"people": 250.0}}
    m = cf.members(P, comm, homes, town)
    hh = P["site.visits.persons_per_home"]
    assert m["Homer City and Lucerne Mines"]["people"] == pytest.approx(1620.0)
    assert m["Homer City and Lucerne Mines"]["households"] == pytest.approx(1500.0 / hh + 50)
    assert m["Black Lick"]["new_homes"] == 20 and m["Graceton and Coral"]["new_homes"] == 0
