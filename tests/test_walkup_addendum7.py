"""Pass 3g step 9d (D28): Addendum 7's plant, the storage tanks and the backup heater in the mechanical
room (`routing.annex_equipment`, `equipment_checks`, `plumbing.storage_held`, `sequence.aquastat_at`),
and what the revised services model changed (`servicesifc.changes`)."""
import pytest

from brownfield import plumbing, routing, sequence, servicesifc, systems
from brownfield.params import load_params, values

R = "systems.routing."


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def apt():
    return systems.load(systems.latest_model())


def _plant_checks(apt, p):
    d = routing.placements(apt, p)
    return {label: (ok, detail) for label, ok, detail in routing.equipment_checks(apt, p, d["equipment"], d["plant"], d["soffits"])
            if "plant" in label}


def test_the_room_takes_the_two_tanks_and_the_backup_heater(apt, P):
    ch = _plant_checks(apt, P)
    assert len(ch) == 3 and all(ok for ok, _ in ch.values()), ch
    plant = {e["id"]: e for e in routing.annex_equipment(apt, P)}
    assert set(plant) == {"annex/storage-tank-a", "annex/storage-tank-b", "annex/heat-pump", "annex/swing-tank", "annex/backup-heater"}
    # ST-1A, the hot end, in the corner; ST-1B in front of it along the same wall.
    a, b = plant["annex/storage-tank-a"], plant["annex/storage-tank-b"]
    assert a["hi"][0] == pytest.approx(b["hi"][0]) and a["lo"][1] > b["hi"][1]


def test_the_single_tank_that_would_hold_it_doesnt_fit_the_room(apt, P):
    # Lochinvar's next single tank over 255 gal, the HP500G: 49 in. across, 97-5/16 in. high. It's
    # wider than the 42 in. door, and its diagonal (109 in.) is over the 108 in. ceiling.
    one = dict(P, **{R + "tank_count": 1, R + "tank_dia_in": 49.0, R + "tank_h_in": 97.3125})
    ok, detail = _plant_checks(apt, one)["each piece of the plant through the mechanical room's door and stood up under its ceiling"]
    assert not ok and "wider than the door" in detail and "on its diagonal" in detail


def test_the_drops_are_kept_out_of_the_heaters_working_space(apt, P):
    # At the old 24 in. off the wall the plant's drop was in front of the backup heater.
    old = dict(P, **{R + "plant_drop_x_in": 24.0})
    ok, detail = _plant_checks(apt, old)["the plant's and the fire service's drops through the slab clear of every piece and its service space"]
    assert not ok and "backup-heater (its service space)" in detail


def test_the_storage_is_held_now_and_wasnt_by_the_one_tank(apt, P):
    sq = plumbing.design(apt, P)
    assert plumbing.storage_held(P) == 300 >= sq["primary"]["storage_gal"]
    # Addendum 5's HP250G alone falls short of the plant with each flat's loop (9c).
    assert plumbing.storage_held(dict(P, **{R + "tank_count": 1, R + "tank_gal": 250})) < sq["primary"]["storage_gal"]
    checks = {label: ok for label, ok, _ in plumbing.summary(apt, P)["checks"]}
    assert checks["the storage tanks hold the storage Ecosizer asks"]


def test_the_aquastat_is_where_ecosizer_puts_it_in_the_tanks(P):
    h = "systems.hot_water."
    assert sequence.aquastat_at(P) == "where ST-1B's top joins ST-1A's bottom"  # half the storage, two equal tanks
    assert sequence.aquastat_at(dict(P, **{h + "aquastat_fract": 0.25})) == "at 50% of ST-1B's height"
    assert sequence.aquastat_at(dict(P, **{R + "tank_count": 1})) == "at 50% of ST-1A's height"


@pytest.fixture(scope="module")
def diff():
    old, new = systems.PUBLISHED / "services-addendum-5.ifc", servicesifc.OUT / f"services-{servicesifc.ISSUE}.ifc"
    if not old.exists() or not new.exists():
        pytest.skip("Addendum 5's published services model or Addendum 7's (`brownfield routes --ifc`) isn't there")
    return servicesifc.changes(old, new)


def test_the_services_diff_finds_what_addendum_7_added(diff):
    assert diff["n_after"] - diff["n_before"] == len(diff["added"]) - len(diff["deleted"])
    # Addendum 5's one storage tank went; Addendum 7's two and the backup heater came, and a
    # balancing valve in each flat.
    assert "hot-water storage tank, annex" in [d["name"] for d in diff["deleted"]]
    assert diff["by_system"]["hot"]["added"] >= 12 + 3
    # Nothing the addendum doesn't touch is marked: the sprinklers and the ducts are as they were.
    assert "sprinkler" not in diff["by_system"] and "ventilation" not in diff["by_system"] and "air" not in diff["by_system"]
    # The same file against itself: nothing.
    same = servicesifc.changes(servicesifc.OUT / f"services-{servicesifc.ISSUE}.ifc", servicesifc.OUT / f"services-{servicesifc.ISSUE}.ifc")
    assert not same["added"] and not same["changed"] and not same["deleted"]
