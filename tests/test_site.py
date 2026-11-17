"""D12, the modular site plan: geometry, rules and scores by hand."""

import math
from dataclasses import replace

import numpy as np
import pytest

from brownfield import site
from brownfield.params import load_params, values

P = values(load_params())
MODS = site.modules(P, P["site.greenhouse_ha"], site.homes_rect(P))


def test_gap_and_overlap_by_hand():
    a, b = (0.0, 10.0, 0.0, 10.0), (13.0, 20.0, 14.0, 20.0)
    assert site.gap(a, b) == pytest.approx(5.0)  # 3 across, 4 down
    assert not site.overlaps(a, b) and not site.overlaps(a, b, margin=4.0) and site.overlaps(a, b, margin=4.5)
    assert site.manhattan((0.0, 0.0), (3.0, -4.0)) == 7.0


def test_rotation_swaps_the_footprint():
    m = site.Module("x", 40.0, 10.0, 0.0, 0.0)
    assert m.rect == (-20.0, 20.0, -5.0, 5.0)
    assert replace(m, rot=90).rect == (-5.0, 5.0, -20.0, 20.0)


def test_the_current_layout_passes():
    assert site.rules(P, MODS) == []


def test_public_vehicles_kept_out_of_the_standoff_band():
    i = next(k for k, m in enumerate(MODS) if m.name == "mobility hub")
    hall = site.HALL
    moved = list(MODS)
    moved[i] = replace(MODS[i], x=(hall[0] + hall[1]) / 2, y=hall[2] - 10.0 - MODS[i].d / 2)  # just north of the hall
    assert any("stand-off" in r for r in site.rules(P, moved))


def test_homes_kept_beyond_the_noise_setback():
    for ring in site.RINGS:
        y = site.HALL[3] + 100.0 + (site.by(MODS, ring).rect[3] - site.by(MODS, ring).rect[2]) / 2  # its edge 100 m off
        assert any(f"{ring} inside the noise setback" in r for r in site.rules(P, _moved(ring, x=site.centre(site.HALL)[0], y=y)))


def test_moving_the_square_changes_only_the_walk_to_it():
    a = site.metrics(P, MODS, 1000.0)
    i = next(k for k, m in enumerate(MODS) if m.name == "square")
    moved = list(MODS)
    moved[i] = replace(MODS[i], x=MODS[i].x + 10.0)
    b = site.metrics(P, moved, 1000.0)
    assert b["walks"]["the square"] != a["walks"]["the square"]
    for k in a["walks"]:
        if k != "the square":
            assert b["walks"][k] == a["walks"][k]
    assert b["truck_km_yr"] == a["truck_km_yr"]


def test_proposals_pass_every_rule_and_differ_from_the_current_layout():
    props = site.optimise(P, MODS, 1000.0, n_starts=3, steps=300)
    assert props and all(site.rules(P, ms) == [] and not site.same(ms, MODS) for _, _, ms in props)
    assert [sc for sc, _, _ in props] == sorted(sc for sc, _, _ in props)


def _moved(name: str, **kw) -> list:
    i = next(k for k, m in enumerate(MODS) if m.name == name)
    out = list(MODS)
    out[i] = replace(MODS[i], **kw)
    return out


def test_the_homes_lie_between_the_hall_and_the_town():
    assert any("between the hall and the town" in r for r in site.rules(P, _moved("townhouses", y=site.HALL[2] - 400.0)))


def test_no_public_place_behind_the_hall():
    assert any("community center behind the hall" in r for r in site.rules(P, _moved("community center", y=site.HALL[2] - 200.0)))


def test_a_building_between_the_homes_and_the_winter_garden_blocks_the_view():
    g, f = site.by(MODS, "winter garden").rect, site.by(MODS, "flats").rect
    # On the line from the garden's middle to the nearest flats.
    gx, gy = site.centre(g)
    nx, ny = min(max(gx, f[0]), f[1]), min(max(gy, f[2]), f[3])
    between = _moved("remote delivery building", x=(gx + nx) / 2, y=(gy + ny) / 2)
    assert any("remote delivery building blocks the homes' view" in r for r in site.rules(P, between))
    # The garden's own host blocks it only if the view runs through the building.
    assert not any("community center blocks" in r for r in site.rules(P, MODS))


def test_the_winter_garden_stands_against_the_community_center_and_moves_with_it():
    c, g = site.by(MODS, "community center").rect, site.by(MODS, "winter garden").rect
    assert g[1] == pytest.approx(c[0]) and c[2] < (g[2] + g[3]) / 2 < c[3]  # on its west face, facing west
    moved = site.attach(_moved("community center", x=site.by(MODS, "community center").x + 100.0, y=site.by(MODS, "community center").y + 10.0))
    g2 = site.by(moved, "winter garden").rect
    assert (g2[0] - g[0], g2[2] - g[2]) == pytest.approx((100.0, 10.0))
    south = site.garden_on(replace(site.by(MODS, "winter garden"), faces=180), c)
    assert south.rect[2] == pytest.approx(c[3]) and south.rot == 0


def _grid(nx: int, ny: int) -> site.Grid:
    g = object.__new__(site.Grid)
    g.x0 = g.y0 = 0.0
    g.cell, g.nx, g.ny = 10.0, nx, ny
    g.X, g.Y = np.meshgrid((np.arange(nx) + 0.5) * 10.0, (np.arange(ny) + 0.5) * 10.0)
    return g


def test_routing_round_a_wall_by_hand():
    # A 100 x 30 m strip; a wall across the bottom two rows of column 5. Round it: two diagonals and
    # two straights up to the top row, two straights past the wall (no corner cutting), then two
    # diagonals and a straight down: 4 x 14.14 + 5 x 10 m.
    g = _grid(10, 3)
    wall = (g.X > 50) & (g.X < 60) & (g.Y < 20)
    (straight,) = g.paths(np.zeros_like(wall), np.ones(g.X.shape), (5.0, 5.0), [(95.0, 5.0)])
    (round_,) = g.paths(wall, np.ones(g.X.shape), (5.0, 5.0), [(95.0, 5.0)])
    assert g.length(straight) == pytest.approx(90.0)
    assert g.length(round_) == pytest.approx(10.0 * (4 * math.sqrt(2.0) + 5))


def test_a_road_goes_round_a_walk_when_the_detour_is_short_and_crosses_it_when_not():
    g = _grid(10, 3)
    walk = (g.X > 50) & (g.X < 60) & (g.Y < 20)  # a walk across the bottom two rows
    costly = np.ones(g.X.shape) + walk * 500.0 / 30.0  # a road that would go 500 m round
    (round_,) = g.paths(np.zeros_like(walk), costly, (5.0, 5.0), [(95.0, 5.0)])
    assert not walk.ravel()[round_].any()  # a 17 m detour beats crossing
    walk_all = (g.X > 50) & (g.X < 60)  # the walk now spans the strip: no way round
    (cross,) = g.paths(np.zeros_like(walk), np.ones(g.X.shape) + walk_all * 10.0, (5.0, 5.0), [(95.0, 5.0)])
    assert walk_all.ravel()[cross].sum() == 1  # straight across, once


def test_trucks_are_screened_where_they_come_in():
    gx = P["site.gate.x"]
    far = _moved("remote delivery building", x=gx - P["site.delivery_gate_m"] - 200.0)
    assert any("from the site entrance" in r for r in site.rules(P, far))


def test_capital_recovery_by_hand():
    # $1 over 2 years at 10%: 0.1 / (1 - 1.1^-2) = 0.5762
    assert site.crf(0.10, 2) == pytest.approx(0.1 / (1 - 1 / 1.21))
    assert site.crf(1e-9, 20) == pytest.approx(1 / 20, rel=1e-6)


def test_a_truck_road_goes_round_until_an_underpass_is_cheaper():
    # The detour that costs the trucks on a road as much a year as an underpass does.
    v = "site.value."
    trips = 1000.0
    d = site.truck_detour_m(P, trips)
    extra = trips * 2.0 * d / 1000.0 * P[v + "truck_usd_km"]
    assert extra == pytest.approx(P[v + "underpass_usd"] * site.crf(P[v + "discount"], P[v + "life_yr"]))
    assert site.truck_detour_m(P, 2 * trips) == pytest.approx(d / 2)  # twice the trucks, half the detour


def test_the_homes_rows_face_south():
    assert any("facing south" in r for r in site.rules(P, _moved("flats", rot=90)))


def test_the_score_is_the_sum_of_the_costs():
    m = site.metrics(P, MODS, 1000.0)
    c = site.costs(P, m)
    assert site.score(P, m) == pytest.approx(sum(c.values()) / 1000.0)
    # A minute more on the walk to the food court costs every resident's visits a year at the value of walking time.
    m2 = {**m, "walks": {**m["walks"], "the food court": (m["walks"]["the food court"][0] + 1.0, 0.0)}}
    m2["ring_walks"] = {k: {**v, "the food court": v["the food court"] + 1.0} for k, v in m["ring_walks"].items()}
    per = (sum(site.ring_people(P).values()) * P["site.visits.food_court_wk"] * 52 * 2 * P["site.value.walk_usd_h"] / 60.0)
    assert site.costs(P, m2)["residents' walks"] - c["residents' walks"] == pytest.approx(per)


def test_the_moat_holds_the_greenhouse_round_the_hall_and_leaves_the_ways_in_open():
    r = P["site.moat.road_m"]
    blocks = site.moat_blocks(P, P["site.greenhouse_ha"])
    assert sum((b[1] - b[0]) * (b[3] - b[2]) for b in blocks.values()) == pytest.approx(P["site.greenhouse_ha"] * 1e4)
    hall = site.HALL
    # The road ring: every block's nearest edge is the road's width off the hall.
    assert min(site.gap(b, hall) for b in blocks.values()) == pytest.approx(r)
    # The north blocks leave the covered crossing on the hall's centre line; the town-side blocks the mall.
    nw, ne = blocks["greenhouse north-west"], blocks["greenhouse north-east"]
    assert ne[0] - nw[1] == pytest.approx(P["site.moat.crossing_m"]) and nw[1] < site.centre(hall)[0] < ne[0]
    front = site.by(MODS, "hall front").rect
    for b in blocks.values():
        assert not site.overlaps(b, front)
    assert front[3] == pytest.approx(hall[3] + P["site.moat.south_m"])
    # The hall's trucks find their way in through the crossing.
    assert site.metrics(P, MODS, 1000.0, routed=True)["routes_ok"]


def test_glass_walls_of_touching_blocks_by_hand():
    # Two 10 x 10 blocks side by side: 40 + 40 - 2 x 10 shared.
    assert site.glass_walls_m([(0, 10, 0, 10), (10, 20, 0, 10)]) == pytest.approx(60.0)


def test_the_square_stands_on_the_halls_axis():
    assert not any("axis" in r for r in site.rules(P, MODS))
    assert any("square off the hall's axis" in r for r in site.rules(P, _moved("square", x=site.by(MODS, "square").x + 60.0)))
    assert any("square off the hall's axis" in r for r in site.rules(P, _moved("square", y=site.by(MODS, "square").y + 100.0)))


def test_the_rings_run_flats_townhouses_houses_out_from_the_square():
    assert not any("out of order" in r for r in site.rules(P, MODS))
    f, t = site.by(MODS, "flats"), site.by(MODS, "townhouses")
    swapped = _moved("flats", x=t.x, y=t.y)
    i = next(k for k, m in enumerate(swapped) if m.name == "townhouses")
    swapped[i] = replace(swapped[i], x=f.x, y=f.y)
    assert any("out of order" in r for r in site.rules(P, swapped))
