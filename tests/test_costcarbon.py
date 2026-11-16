"""Pass 3b: embodied carbon and cost of the three structures, by hand on made-up quantities."""

from brownfield import costcarbon
from brownfield.params import load_params, values

PARAMS = load_params()
P = values(PARAMS)
Q = {
    "wood": {"sawn_m3": 10.0, "ijoist_m3": 2.0, "rim_m3": 1.0, "osb_m3": 5.0, "foundation_m3": 50.0, "wood_m3": 13.0},
    "steel": {"cfs_t": 8.0, "osb_m3": 5.0, "foundation_m3": 50.0},
    "masonry": {"block_kg": 21600.0, "wall_m2": 100.0, "lintel_m3": 1.0, "lintels": 4, "plank_m2": 200.0, "foundation_m3": 70.0},
    "areas": {"ext_wall_gross_m2": 300.0, "int_wall_m2": 200.0, "sheathing_m2": 250.0, "deck_m2": 200.0, "gfa_m2": 600.0},
}


def test_carbon_by_hand():
    c = "pass3.carbon."
    cb = costcarbon.carbon(Q, P)
    assert abs(cb["wood"]["sawn lumber"] - 10 * P[c + "lumber_kg_m3"]) < 1e-9
    assert abs(cb["steel"]["cold-formed steel"] - 8 * P[c + "cfs_kg_t"]) < 1e-9
    # Block: 21,600 kg of concrete at its density, times the per-m3 factor.
    assert abs(cb["masonry"]["concrete block"] - 21600 / P[c + "cmu_density_kg_m3"] * P[c + "cmu_kg_m3"]) < 1e-9
    plank = 200 * (P[c + "plank_concrete_m3_m2"] * P[c + "precast_kg_m3"] + P[c + "plank_strand_kg_m2"] * P[c + "steel_kg_t"] / 1e3)
    assert abs(cb["masonry"]["hollow-core planks"] - plank) < 1e-9
    assert abs(costcarbon.totals(cb)["wood"] - sum(cb["wood"].values())) < 1e-9


def test_cost_by_hand():
    c = "pass3.cost."
    cs = costcarbon.cost(Q, P)
    walls_ft2 = 500 * costcarbon.M2_FT2
    assert abs(cs["wood"]["wall framing"] - walls_ft2 * P[c + "wall_framing_usd_ft2"]) < 1e-6
    assert abs(cs["steel"]["wall framing"] - cs["wood"]["wall framing"] * P[c + "cfs_factor"]) < 1e-6
    assert abs(cs["masonry"]["hollow-core planks"] - 200 * costcarbon.M2_FT2 * P[c + "plank_usd_ft2"]) < 1e-6


def test_biogenic():
    # (13 + 5) m3 at G 0.42: 7,560 kg dry, half of it carbon, x 44/12.
    assert abs(costcarbon.biogenic_t(Q, 0.42) - 18 * 420 * 0.5 * 44 / 12 / 1e3) < 1e-9


def test_tornado_drops_shared_inputs():
    names = [r[0] for r in costcarbon.tornado(PARAMS, P, Q, costcarbon.cost, "steel", "wood", "pass3.cost.")]
    assert "sheathing_usd_ft2" not in names and "cfs_factor" in names
