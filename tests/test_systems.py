"""Pass 3b: light steel and masonry + precast against published tables and hand-worked values."""

from brownfield import masonry, steel
from brownfield.params import load_params, values
from brownfield.sfia import HEADERS, JOIST_SPANS, SECTIONS, STUD_AXIAL

P = values(load_params())


def test_sfia_parsed_values():
    # Spot checks against the guide's printed rows.
    s = SECTIONS[("1000S200-54", 50)]
    assert (s["ix"], s["ma"], s["mnd"], s["vag"], s["weight"]) == (10.77, 51.055, 77.888, 1661.0, 2.86)
    assert JOIST_SPANS[(10, 20)][("1000S200-54", 50)][:3] == [28 * 12 + 8, 26 * 12, 22 * 12 + 9]
    assert STUD_AXIAL[(5, "600S162-54", 50, 9, 16)] == 5.51 and STUD_AXIAL[(15, "600S162-54", 50, 9, 16)] == 5.07
    assert HEADERS[("600S162-54", 50)] == [3012.0, 1694.0, 1084.0, 753.0, 424.0, 250.0, 145.0]


def test_steel_spans_reproduced():
    for r in steel.known_cases():
        assert abs(r["model_in"] - r["table_in"]) < 1.0, r


def test_steel_stud_lookup_rounds_height_up():
    # 8.93 ft reads the 9 ft row.
    assert steel.stud_capacity(15, "600S162-54", 50, 8.93, 16) == 5070.0
    assert steel.stud_capacity(15, "600S162-54", 50, 9.0, 16) == 5070.0


def test_tms_example():
    r = masonry.known_cases()[0]
    assert abs(r["model"] / r["table"] - 1) < 0.002


def test_masonry_axial_formula():
    # h/r = 70: 0.25 f'm (1 - 0.25); above 99 the Euler-type branch.
    assert abs(masonry.axial_allowable(2000, 70 * 2.0, 2.0) - 500 * 0.75) < 1e-9
    assert abs(masonry.axial_allowable(2000, 120 * 2.0, 2.0) - 500 * (70 / 120) ** 2) < 1e-9


def test_plank_table_next_span_up():
    assert masonry.plank_capacity("2008805 (5 x 1/2 in. strands)", 19.0) == 188
    assert masonry.plank_capacity("2008805 (5 x 1/2 in. strands)", 19.2) == 170


def test_steel_designations():
    # 1200S250-54: 12.00 in. deep, 2.50 in. flanges; its track is 1200T125-54.
    assert steel.dims_mm("1200S250-54") == [2.5 * 25.4, 12.0 * 25.4]
    assert steel.track_for("600S162-43") == "600T125-43"
    assert abs(steel.weight("600S162-54") - 1.89) < 1e-12


def test_masonry_densities():
    from brownfield import house
    d = masonry.design(house.apartment(), P)
    f = masonry.for_forge(d, P, house.apartment())
    # A plank weighs 54 psf over its 4 ft width and its length; a block its unit weight.
    assert abs(f["plank_kg"] - 54 * 4 * d["plank_len_in"] / 12 * 0.453592) < 1e-6
    assert abs(f["block_kg"] - P["pass3.masonry.block_lb"] * 0.453592) < 1e-9
