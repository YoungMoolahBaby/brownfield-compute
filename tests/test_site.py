"""D12, the modular site plan: geometry, rules and scores by hand."""

from dataclasses import replace

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
    i = next(k for k, m in enumerate(MODS) if m.name == "parking: food court")
    hall = site.HALL
    moved = list(MODS)
    moved[i] = replace(MODS[i], x=(hall[0] + hall[1]) / 2, y=hall[2] - 10.0 - MODS[i].d / 2)  # just north of the hall
    assert any("stand-off" in r for r in site.rules(P, moved))


def test_homes_kept_beyond_the_noise_setback():
    i = next(k for k, m in enumerate(MODS) if m.name == "neighbourhood")
    moved = list(MODS)
    moved[i] = replace(MODS[i], y=MODS[i].y - 60.0)
    assert any("noise setback" in r for r in site.rules(P, moved))


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


def test_proposals_pass_every_rule_and_beat_or_match_the_current_layout():
    props = site.optimise(P, MODS, 1000.0, n_starts=3, steps=300)
    now = site.score(P, site.metrics(P, MODS, 1000.0))
    assert props and all(site.rules(P, ms) == [] for _, _, ms in props)
    assert props[0][0] <= now + 1e-9
