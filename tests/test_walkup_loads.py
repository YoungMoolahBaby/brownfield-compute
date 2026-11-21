"""Pass 3g step 2 (D28): the walk-up's loads, room by room (`brownfield.loads`)."""
import copy

import numpy as np
import pytest

from brownfield import house, loads, systems
from brownfield.params import load_params, values

FT2 = 0.3048 ** 2


@pytest.fixture(scope="module")
def apt():
    return systems.load()


@pytest.fixture(scope="module")
def P():
    return values(load_params())


def test_rooms_sum_to_pass_3b_flat_by_flat(apt, P):
    ok, worst = loads.check_against_pass3b(apt, P)
    assert ok, worst


def test_every_opening_and_wall_is_shared_out(apt):
    # The rooms' glazing is the flat's (forge names every opening on a room), and the wall and
    # slab-edge shares of each flat sum to one.
    env = loads.room_envelopes(apt)
    for f in apt["flats"]:
        rows = env[f["name"]]
        assert sum(x["glazed_m2"] for x in rows) == pytest.approx(f["glazed_m2"], abs=1e-12)
        assert sum(x["wall_share"] for x in rows) == pytest.approx(1.0, abs=1e-12)
        assert sum(x["area_share"] for x in rows) == pytest.approx(1.0, abs=1e-12)


def test_exposure_follows_the_plan(apt):
    # Bed 1 is the corner room (facade and end wall), bed 2 the end wall only, the bath and the
    # kitchen inside; mirrored, the same in every flat.
    rooms = {r["id"]: r for r in apt["rooms"]["rooms"]}
    for flat in ("2-front-left", "1-back-right"):
        face, end = ("front" if "front" in flat else "back"), ("left" if flat.endswith("left") else "right")
        assert sorted(loads.exposure(apt, rooms[f"{flat}/bed-1"])) == sorted([face, end])
        assert list(loads.exposure(apt, rooms[f"{flat}/bed-2"])) == [end]
        assert loads.exposure(apt, rooms[f"{flat}/bath"]) == {} and loads.exposure(apt, rooms[f"{flat}/kitchen"]) == {}


def test_the_hardest_room_needs_warmer_water_than_the_flat_average(apt, P):
    # Pass 3b's case: the flat as a whole needs ~30 C water (pass 3b); room by room, the ground
    # floor's corner bedroom sets the manifold's supply higher.
    rh = loads.room_heat(apt, P)
    flat = house.heat(next(f for f in apt["flats"] if f["name"] == "1-front-left"), np.zeros(1), P)
    assert rh["1-front-left"]["hardest"] == "1-front-left/bed-1"
    assert rh["1-front-left"]["supply_c"] > flat["supply_c"] + 5
    assert rh["1-front-left"]["max_surface_c"] <= P["pass3.radiant.max_floor_c"]


def test_the_check_catches_a_lost_window(apt, P):
    bad = copy.deepcopy(apt)
    next(r for r in bad["rooms"]["rooms"] if r["id"] == "2-front-left/bed-1")["openings"] = []
    ok, worst = loads.check_against_pass3b(bad, P)
    assert not ok and worst > 1.0


def test_sun_on_a_wall_against_pvgis():
    # Known case: PVGIS's own hourly series (2020, the site) on vertical planes. NOAA's solar
    # position against PVGIS's sun height, and the beam on each wall by geometry against PVGIS's
    # beam on that plane (Gb(i)), from PVGIS's horizontal beam. Then why the cooling loads use
    # PVGIS's own series: the isotropic sky (Liu and Jordan: half the diffuse and half the ground's
    # reflection, albedo 0.2) reads the south and west walls' peak hours more than 5% low.
    import numpy as np
    import pandas as pd

    from brownfield import climate

    from brownfield.land import PLANT

    lat, lon = PLANT
    h = climate.pvgis_vertical(lat, lon, 2020, 0, angle=0)
    t = pd.to_datetime(h["time"], format="%Y%m%d:%H%M")
    alt, az = climate.sun_position(lat, lon, t.dt.day_of_year.values, (t.dt.hour + t.dt.minute / 60).values)
    up = h["H_sun"] > 5
    assert np.abs(alt - h["H_sun"])[up].max() < 0.3
    bn = np.where(h["H_sun"] > 1, h["Gb(i)"] / np.sin(np.radians(h["H_sun"])), 0)
    for aspect, facing in ((0, 180), (90, 270), (-90, 90), (180, 0)):
        v = climate.pvgis_vertical(lat, lon, 2020, aspect)
        beam = np.where(alt > 0, bn * np.clip(np.cos(np.radians(alt)) * np.cos(np.radians(az - facing)), 0, None), 0)
        assert beam.sum() == pytest.approx(v["Gb(i)"].sum(), rel=0.015)
        assert beam.max() == pytest.approx(v["Gb(i)"].max(), rel=0.05)
        iso = beam + 0.5 * h["Gd(i)"] + 0.5 * 0.2 * (h["Gb(i)"] + h["Gd(i)"])
        pv = v["Gb(i)"] + v["Gd(i)"] + v["Gr(i)"]
        if facing in (180, 270):  # south and west
            assert iso.max() < 0.95 * pv.max()


def test_ventilation_meets_the_code_and_phius(apt, P):
    v = loads.ventilation(apt, P)
    assert all(ok for _, ok, _ in loads.ventilation_checks(apt, P, v))
    x = v["2-front-left"]
    # IMC Eq. 4-9: 0.01 x 836 + 7.5 x 3 = 30.9 cfm; Phius 15 x 3 = 45; exhaust 25 + 20 = 45.
    assert x["imc_cfm"] == pytest.approx(0.01 * x["floor_ft2"] + 22.5)
    assert x["design_cfm"] == pytest.approx(45.0)
    assert {k.split("/")[1]: q for k, q in x["supply"].items()} == pytest.approx({"bed-1": 30.0, "bed-2": 15.0})
    assert {k.split("/")[1]: q for k, q in x["exhaust"].items()} == pytest.approx({"kitchen": 25.0, "bath": 20.0})


def test_ventilation_checks_catch_a_bedroom_without_air_and_an_imbalance(apt, P):
    v = copy.deepcopy(loads.ventilation(apt, P))
    v["3-back-left"]["supply"].pop("3-back-left/bed-2")
    v["3-back-left"]["supply"]["3-back-left/living"] = 15.0
    failing = [label for label, ok, _ in loads.ventilation_checks(apt, P, v) if not ok]
    assert any("every bedroom" in x for x in failing)
    v = copy.deepcopy(loads.ventilation(apt, P))
    v["1-front-right"]["exhaust"]["1-front-right/kitchen"] = 40.0
    assert any("balanced" in label for label, ok, _ in loads.ventilation_checks(apt, P, v) if not ok)


def test_the_engineered_design_needs_less_heat_and_cooler_water(apt, P):
    base = loads.room_heat(apt, P)
    drawn = loads.room_heat(apt, P, loads.design_case(apt, P))
    code = loads.room_heat(apt, P, loads.design_case(apt, P, P["systems.code.envelope.wall_u_max"]))
    for f in apt["flats"]:
        n = f["name"]
        assert drawn[n]["design_w"] < 0.75 * base[n]["design_w"]
        assert code[n]["design_w"] < drawn[n]["design_w"]
    # Its hardest rooms need cooler water than pass 3b's case once the ERV's supply is post-heated
    # to PHI's 16.5 C (step 3); with the ERV alone, the bedrooms take its cold air on their floors.
    post = loads.room_heat(apt, P, loads.design_case(apt, P, post_heat=True))
    for f in apt["flats"]:
        n = f["name"]
        assert post[n]["supply_c"] < base[n]["supply_c"]
        assert post[n]["supply_c"] < drawn[n]["supply_c"]
    # Ventilation heat lands only where the air is supplied: the bedrooms.
    rooms = {x["room"]["id"]: x for x in drawn["2-front-left"]["rooms"]}
    assert rooms["2-front-left/kitchen"]["ua_parts"]["ventilation"] == 0.0
    assert rooms["2-front-left/bed-1"]["ua_parts"]["ventilation"] > rooms["2-front-left/bed-2"]["ua_parts"]["ventilation"] > 0


# ---- 2c-2f: cooling, water, drainage, hot water, electrical ----

@pytest.fixture(scope="module")
def apt3():
    return systems.load(systems.OUT_DIR / "pass3" / "apartment-addendum-3.json")


@pytest.fixture(scope="module")
def cooling(apt3, P):
    return loads.cooling_design(apt3, P)


def test_cooling_design(cooling, apt3, P):
    # The weather is shifted up to meet ASHRAE's 0.4% dry bulb, not down.
    assert 0 < cooling["shift_k"] < 2
    for f in apt3["flats"]:
        q, worst = cooling["flats"][f["name"]]
        rooms = [cooling["rooms"][r["id"]][0] for r in apt3["rooms"]["rooms"] if r["flat"] == f["name"]]
        assert 2000 < q < 5000  # watts, about a ton
        assert sum(rooms) >= q - 1e-6  # rooms peak at different hours: their sum is at least the flat's
    # The long facade's living room is worst facing the sun: west (summer afternoons) or south (low
    # autumn sun on the glass), never north or east.
    assert all(cooling["rooms"][f"{k}-front-left/living"][1] in ("S", "W") for k in (1, 2, 3))
    assert cooling["latent"]["1-front-left"] > 0


def test_cooling_follows_the_sun(apt3, P):
    wx = loads.weather(P)
    shaded = dict(P, **{"systems.design.shgc": 0.0})
    sunny = loads.room_cooling(apt3, P, wx, 270)["2-front-left"]["flat"]
    dark = loads.room_cooling(apt3, shaded, wx, 270)["2-front-left"]["flat"]
    assert sunny.max() > dark.max() + 1000  # the glass's sun is most of the peak


def test_facing():
    # Front to the south: back north, and +y (the right end) 90 degrees clockwise, west.
    assert loads.facing(180) == {"front": "S", "back": "N", "right": "W", "left": "E"}


def test_holt_known_case(P):
    h = loads.holt_example(P)
    assert (h["connected_va"], round(h["calculated_va"]), round(h["amps_240_1ph"])) == (460800, 188928, 787)


def test_hunter_passes_through_its_rows():
    assert [loads.hunter_gpm(u) for u in (1, 20, 60, 70, 90, 100, 500)] == [3.0, 19.6, 32.0, 35.0, 41.0, 43.5, 124.0]
    assert loads.hunter_gpm(95) == pytest.approx(42.25)


def test_water_and_drains(apt3, P):
    w = loads.water(apt3, P)
    # A flat: bathroom group 3.6 + kitchen sink 1.4 + dishwasher 1.4 + washer 1.4 wsfu; 5 + 2 + 2 dfu.
    assert w["per_flat"]["wsfu"] == pytest.approx(7.8) and w["per_flat"]["dfu"] == 9
    assert w["demand_gpm"]["the building"]["wsfu"] == pytest.approx(loads.hunter_gpm(12 * 7.8))
    # 3 in. at least wherever a water closet drains; the building's 108 dfu needs 4 in.
    assert w["drains_in"]["flat branch"] == 3.0 and w["drains_in"]["stack"] == 3.0
    assert w["drains_in"]["building drain, 1/4 in/ft"] == 4.0 and loads.pipe_for(43, "drain_1_4") == 4.0
    assert loads.pipe_for(42, "drain_1_4") == 3.0


def test_hot_water_design_day(apt3, P):
    hw = loads.hot_water(apt3, P)
    assert hw["people"] == 36 and hw["day_gal"] == 900
    assert hw["peak_hour_gal"] == pytest.approx(900 * 0.151975684)
    # 8.34 lb a gallon, 70 F rise: 900 gallons is about 154 kWh.
    assert hw["day_kwh"] == pytest.approx(900 * 8.34 * 70 / 3412.142)


def test_electrical(apt3, P):
    el = loads.electrical(apt3, P)
    f = el["flat_feeder"]
    assert f["calculated_va"] == pytest.approx(10000 + 0.4 * (f["connected_less_hvac_va"] - 10000) + P["systems.electrical.cooling_va"])
    b = el["flats_220_84"]
    assert b["calculated_va"] == pytest.approx(0.41 * b["connected_va"]) and b["per_unit_va"] > f["connected_less_hvac_va"]
