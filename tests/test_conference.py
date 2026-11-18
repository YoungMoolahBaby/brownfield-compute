"""D17-D18, the conference of communities: shares, glass, windows, costs, and the layout, by hand."""

import math

import numpy as np
import pytest

from brownfield import conference as cf, neighbourhood as nb, rings
from brownfield.params import load_params, values

P = values(load_params())
C = "village.conference."
SITES = {"A": {"n": 12}, "B": {"n": 5}, "C": {"n": 7}}
TOWN = {"Homer City": {"xy": (0.0, 0.0), "people": 1000.0}, "Lucerne Mines": {"xy": (0.0, 1600.0), "people": 500.0},
        "Black Lick": {"xy": (0.0, -7000.0), "people": 250.0}, "Coral": {"xy": (2000.0, -1200.0), "people": 150.0},
        "Graceton": {"xy": (2300.0, -600.0), "people": 100.0}}


def test_each_sites_jobs_add_up():
    h = cf.site_homes(P, SITES)
    assert sum(v["jobs"] for v in h.values()) == pytest.approx(P["pass4.demand.jobs"])
    assert h["A"]["jobs"] / h["B"]["jobs"] == pytest.approx(12 / 5)


def test_the_glass_split_keeps_the_markets_area():
    h = cf.site_homes(P, SITES)
    g = cf.glass(P, h)
    assert sum(g.values()) == pytest.approx(P["site.greenhouse_ha"])


def test_every_town_grows_by_about_the_same_share():
    th = cf.town_homes(P, TOWN)
    c = rings.counts(P)
    assert sum(v["homes"] for v in th.values()) == c["flats"] + c["townhouses"] + c["houses"]
    assert sum(v["flats"] for v in th.values()) == c["flats"]
    for b in range(4):
        assert sum(v["flats_by_bed"][b] for v in th.values()) == c["flats_by_bed"][b]
    big = [v["growth"] for k, v in th.items() if TOWN[k]["people"] >= 250]
    assert max(big) - min(big) < 0.02  # rounding moves the smallest towns most
    assert th["Homer City"]["homes"] > th["Lucerne Mines"]["homes"] > th["Black Lick"]["homes"]


def test_window_share_by_hand():
    m = np.zeros((5, 5), bool)
    m[0:2, 0:2] = True
    s = cf.window_share(m, 1)
    assert s[0, 0] == pytest.approx(1.0)
    assert s[2, 2] == pytest.approx(1 / 9)
    assert s[4, 4] == pytest.approx(0.0)


def test_a_clubhouse_by_hand():
    q = dict(P, **{C + "clubhouse_ft2": 10000.0, C + "clubhouse_posts": 2.0, "village.community_center.rec_center_build_usd_ft2": 400.0,
                   "village.membership.day_h": 16.0, "village.membership.opex_per_fte": 100000.0})
    c = cf.clubhouse(q)
    assert c["build"] == pytest.approx(4.0e6)
    assert c["run"] == pytest.approx(2 * 16 * 365 / 2080 * 100000.0)


def test_the_clubhouse_rooms_make_its_floor_area():
    m2 = sum(P[C + k] for k in ("court_hall_m2", "cafe_m2", "fitness_m2", "workshop_m2", "support_m2"))
    assert m2 / 0.09290304 == pytest.approx(P[C + "clubhouse_ft2"], rel=0.01)
    # The court hall holds a high-school court (84 x 50 ft) with 3 m all round.
    assert P[C + "court_hall_m2"] == pytest.approx((25.6 + 6) * (15.2 + 6), rel=0.01)


def test_members_count_their_towns_and_the_clubhouse_rule():
    th = {k: {"homes": 10, "people": 25.0} for k in TOWN}
    m = cf.members(P, th, TOWN)
    hh = P["site.visits.persons_per_home"]
    r = m["Homer City and Lucerne Mines"]
    assert r["people"] == pytest.approx(1550.0)
    assert r["households"] == pytest.approx(1500.0 / hh + 20)
    assert r["club_town"] == "Homer City"
    run = cf.clubhouse(P)["run"]
    for v in m.values():
        assert v["clubhouse"] == (run / v["households"] <= P[C + "clubhouse_max_usd_household"])
    assert not m["Graceton and Coral"]["clubhouse"]


def test_walkups_share_the_flats():
    w = nb.walkups(P, [4, 24, 22, 5])
    ft2 = sum(n * P[f"village.rings.ft2_{b}"] for b, n in enumerate([4, 24, 22, 5]))
    assert len(w) == math.ceil(ft2 / P["village.rings.walkup_flats_ft2"])
    assert sum(n for n, _ in w) == 55
    assert all(16.0 <= wd <= P["village.rings.walkup_w_m"] for _, wd in w)
    assert nb.walkups(P, [0, 0, 0, 0]) == []


def test_a_lots_building_stands_inside_it_facing_the_street():
    lot = nb.Lot("flats", 100.0, 50.0, 0.0, 1.0, 42.0, 32.0, bw=30.48)
    b = nb.building(P, lot)
    assert lot.polygon().contains(b.polygon())
    # 6 m of front garden: the building's street face is 6 m short of the lot's.
    assert (lot.y + lot.d / 2) - (b.y + b.d / 2) == pytest.approx(6.0)


class _Flat:
    """A 10 m grid of clear land, on a plane rising `rise` m a metre to the north."""

    def __init__(self, n=200, rise=0.0):
        self.nx = self.ny = n
        self.dx = self.dy = 10.0
        y = (n / 2 - (np.arange(n) + 0.5)) * 10.0
        self.z = np.repeat((rise * y)[:, None], n, axis=1)

    def pix(self, x, y):
        return np.asarray(x, float) / 10.0 + self.nx / 2, self.ny / 2 - np.asarray(y, float) / 10.0


def _ground(rise=0.0):
    g = _Flat(rise=rise)
    return nb.Ground(g, np.ones((g.ny, g.nx), bool), np.zeros((g.ny, g.nx), bool))


def test_a_layout_on_open_flat_land_places_every_home_in_rings():
    h = {"flats_by_bed": [4, 24, 22, 5], "townhouses": 44, "houses": 10}
    q = nb.queue(P, h, club=True)
    lay = nb.try_layout(P, _ground(), q, (0.0, -300.0), (1.0, 0.0), (0.0, 1.0), "test")
    assert lay.missing() == 0 and not lay.blocked
    assert lay.homes() == {"flats": 55, "townhouses": 44, "houses": 10}
    polys = [l.polygon() for l in lay.lots]
    assert all(polys[i].intersection(polys[j]).area < 1e-6 for i in range(len(polys)) for j in range(i + 1, len(polys)))
    club = next(l for l in lay.lots if l.kind == "club")
    d = {k: np.mean([math.dist((l.x, l.y), (club.x, club.y)) for l in lay.lots if l.kind == k]) for k in nb.KINDS}
    assert d["flats"] < d["townhouses"] < d["houses"]  # rings outward from the clubhouse
    assert all(math.dist((l.x, l.y), (club.x, club.y)) <= P[C + "walk_m"] + l.w for l in lay.lots)


def test_steep_ground_takes_no_lots_and_a_plane_is_recovered():
    q = nb.queue(P, {"flats_by_bed": [0, 0, 0, 0], "townhouses": 3, "houses": 0}, club=False)
    # 0.4 m a metre: a townhouse's 11 m depth, running up the slope, falls 4.4 m, more than a storey.
    steep = nb.try_layout(P, _ground(rise=0.4), q, (0.0, -300.0), (1.0, 0.0), (0.0, 1.0), "test")
    assert steep.missing() == 3
    g = _ground(rise=0.05)
    lot = nb.Lot("houses", 0.0, 0.0, 0.0, 1.0, 20.0, 40.0)
    zc, su, so = nb.plane(lot, g)
    assert su == pytest.approx(0.0, abs=1e-6) and so == pytest.approx(0.05, abs=1e-6)


def test_the_loops_main_is_shared_by_the_towns_homes():
    from brownfield import climate, food, screen

    site = screen.plant_table(P).loc[3122]
    wx = food.local(climate.hourly_weather(site.lat, site.lon), -5)
    near = rings.loop_vs_heat_pump(P, wx["t"], "flats", 2, homes=100, main_km=0.5)
    far = rings.loop_vs_heat_pump(P, wx["t"], "flats", 2, homes=100, main_km=3.0)
    assert near["main"] == pytest.approx(500 * P["pass3.block.main_usd_m"] / 100)
    assert far["A"] - near["A"] == pytest.approx(far["main"] - near["main"], rel=0.2)  # the main, plus its upkeep
    assert far["A"] > far["B"]  # 3 km out, a flat heats itself
