"""D16, the rings of homes: who lives where, and each type's checks by hand."""

import math

import pytest

from brownfield import econ, rings, village
from brownfield.params import load_params, values

P = values(load_params())
R = "village.rings."


def test_apportion_keeps_the_total():
    assert rings._apportion(10, [0.25, 0.25, 0.5]) == [3, 2, 5]  # 2.5 / 2.5 / 5: the spare one to the first tie
    assert sum(rings._apportion(121, [0.08, 0.43, 0.39, 0.09])) == 121


def test_counts_by_hand():
    d = econ.demand(P)
    c = rings.counts(P)
    owners = d["households"] * (1 - P["pass4.demand.renter_share"]) * P[R + "owners_near_share"]
    assert c["flats"] == round(d["near_renters"])
    assert c["townhouses"] + c["houses"] == round(owners)
    assert c["houses"] == round(round(owners) * P[R + "owners_4bed_share"])
    ft2 = sum(n * P[R + f"ft2_{b}"] for b, n in enumerate(c["flats_by_bed"]))
    assert c["walkups"] == math.ceil(ft2 / P[R + "walkup_flats_ft2"])


def test_tax_credit_rents_by_hand():
    # PHFA's 60% limit for 3 people is 90% of the 4-person limit; a 1-bed is set at 1.5 people (the mean of
    # the 1- and 2-person factors, 70% and 80%), a 2-bed at 3.
    four = P["pass4.rents.lihtc_60_3p_usd"] / 0.9
    ua = P["pass4.rents.utility_allowance_usd"]
    assert rings.lihtc_rent(P, 2) == pytest.approx(P["pass4.rents.lihtc_60_3p_usd"] * 0.30 / 12 - ua)
    assert rings.lihtc_rent(P, 1) == pytest.approx(four * 0.75 * 0.30 / 12 - ua)
    assert rings.lihtc_rent(P, 0) == pytest.approx(four * 0.70 * 0.30 / 12 - ua)


def test_the_house_envelope_adds_up():
    env = rings.house_env(P)
    n, h = int(P[R + "house_storeys"]), P[R + "house_storey_m"]
    assert env["floor_m2"] == pytest.approx(P["village.housing_cost.median_new_sf_floor_area"] * rings.FT2_M2)
    walls = 2 * (env["width_m"] + env["depth_m"]) * h * n
    assert env["wall_net_m2"] + env["glazed_m2"] + env["door_m2"] == pytest.approx(walls)
    assert env["ceiling_m2"] * n == pytest.approx(env["floor_m2"])


def test_window_heights_and_noise_rise_with_the_storeys():
    assert rings.windows(P, "flats") == pytest.approx([1.5, 1.5 + P[R + "walkup_storey_m"], 1.5 + 2 * P[R + "walkup_storey_m"]])
    assert rings.night_db(P, "flats", 150.0, 3.0) >= rings.night_db(P, "houses", 150.0, 3.0)


def test_children_by_hand():
    c = rings.counts(P)
    f = c["flats_by_bed"]
    k = rings.children(P, c)
    assert k["flats"] == pytest.approx((f[0] + f[1]) * 0.127 + f[2] * 0.368 + f[3] * 0.995)
    assert k["houses"] == pytest.approx(c["houses"] * 1.044)


def test_a_townhouse_to_buy_matches_the_neighbourhoods_own_sum():
    o = rings.owner_money(P, "townhouses")
    h = village.home_cost(P)
    assert o["build"] == pytest.approx(h["build_usd"])
    assert o["afford"]["county median"] == pytest.approx(h["afford_usd"])


def test_houses_join_the_loop_only_if_it_beats_a_heat_pump():
    import numpy as np

    temp = np.full(8760, 0.0)
    r = rings.houses_on_loop(P, temp)
    assert r["loop"] == (r["A"] < r["B"])
    # With the operator paying the pipes the loop costs a household less than with its share in.
    assert r["A_operator"] < r["A"]
