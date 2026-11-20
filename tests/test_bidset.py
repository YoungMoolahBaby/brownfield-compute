"""Pass 3f (D27): the walk-up written out by forge as named parts for the bid set
(`cargo run --release -- apartment-json` in forge/, out/pass3/apartment.json)."""
from collections import Counter, defaultdict

from brownfield import house


def _apt():
    return house.apartment()


def test_openings_by_kind_and_storey():
    ops = _apt()["openings"]
    # By the layout (forge/src/apartment.rs): per flat and storey six windows and a patio door on
    # the long face, two windows in the end wall; the stair a window front and back, the entry
    # door in place of the front one on the ground floor.
    assert Counter(o["kind"] for o in ops) == {"window": 101, "patio_door": 12, "entry_door": 1}
    assert Counter(o["storey"] for o in ops) == {1: 38, 2: 38, 3: 38}
    assert sum(o["flat"] is None for o in ops) == 6


def test_ids_are_unique_and_name_space_face_and_index():
    ops = _apt()["openings"]
    assert len({o["id"] for o in ops}) == len(ops)
    for o in ops:
        space, face, index = o["id"].split("/")
        assert space == (o["flat"] or f"{o['storey']}-stair")
        assert face == o["face"]
        assert int(index) == o["index"]


def test_glazing_per_flat_matches_the_envelope():
    # Openings are put in flats by where they are (forge `flat_at`); the envelope's glazing comes
    # from a separate filter (`flat_openings`), the one the heat model has used since pass 3b.
    apt = _apt()
    glazed = defaultdict(float)
    for o in apt["openings"]:
        if o["glazed"] and o["flat"]:
            glazed[o["flat"]] += o["width_m"] * o["height_m"]
    assert set(glazed) == {f["name"] for f in apt["flats"]}
    for f in apt["flats"]:
        assert abs(glazed[f["name"]] - f["glazed_m2"]) < 1e-9


def test_openings_sit_in_their_walls_at_their_size():
    apt = _apt()
    parts = {p["id"]: p for p in apt["parts"]}
    for o in apt["openings"]:
        w = parts[o["wall"]]
        assert all(w["lo_m"][i] - 1e-6 <= o["lo_m"][i] and o["hi_m"][i] <= w["hi_m"][i] + 1e-6 for i in range(3))
        size = [hi - lo for lo, hi in zip(o["lo_m"], o["hi_m"])]
        along = 1 if o["face"] in ("front", "back") else 0
        assert abs(size[along] - o["width_m"]) < 1e-6
        assert abs(size[2] - o["height_m"]) < 1e-6
        assert abs(size[1 - along] - apt["ext_t_m"]) < 1e-6
        assert abs(o["lo_m"][2] - o["sill_m"]) < 1e-6


def test_wall_boxes_make_the_shell():
    apt = _apt()
    w, l, t, h = apt["depth_m"], apt["length_m"], apt["ext_t_m"], apt["storey_m"] * apt["storeys"]
    vol = sum((p["hi_m"][0] - p["lo_m"][0]) * (p["hi_m"][1] - p["lo_m"][1]) * (p["hi_m"][2] - p["lo_m"][2])
              for p in apt["parts"] if p["kind"] == "exterior_wall")
    assert abs(vol - (w * l - (w - 2 * t) * (l - 2 * t)) * h) < 1e-6
