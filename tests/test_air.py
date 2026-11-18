"""Pass 2g, the air: EIA's plant rows, the permitted rates, each design's share and the diesel tests."""

import numpy as np
import pandas as pd
import pytest

from brownfield import air, scorecard
from brownfield.params import load_params, values

P = values(load_params())


def test_plant_totals_sum_the_selected_columns_not_the_repeated_plant_level_ones():
    # Two rows of one plant (coal and gas): the plant-level column repeats the plant's total on each row.
    co2 = pd.DataFrame({"Generation (kWh)": [9e9, 1e9], "Tons of CO2 Emissions": [9e6, 0.5e6]})
    so2 = pd.DataFrame({"CEMS Reported Plant Level SO2 Emissions (Tons)": [5000.0, 5000.0],
                        "Selected SO2 Emissions (Tons)": [4990.0, 10.0]})
    nox = pd.DataFrame({"CEMS Reported Plant Level NOx Emissions (Tons)": [3000.0, 3000.0],
                        "Selected NOx Emissions (Tons)": [2900.0, 100.0]})
    t = air.plant_totals({"CO2": co2, "SO2": so2, "NOx": nox})
    assert t == {"gen_mwh": 1e7, "so2": 5000.0, "nox": 3000.0, "co2": 9.5e6}


def test_permitted_rates_by_hand():
    g = air.gas(P)
    mwh = P["air.gas.full_mw"] * 8760
    assert g["mwh"] == pytest.approx(mwh)
    assert g["lb_mwh"]["nox"] == pytest.approx(P["air.gas.nox_tpy"] * 2000 / mwh)
    assert g["lb_mwh"]["co2e"] == pytest.approx(17_551_454 * 2000 / (4678 * 8760))


def test_each_design_takes_its_share_of_the_caps_and_only_diesel_designs_test():
    temp, rh = np.full(8760, 10.0), np.full(8760, 70.0)  # a mild humid synthetic year, as in test_scorecard_campus
    ds = air.designs(temp, rh, P)
    g = air.gas(P)
    n = P["scorecard.campus_it_mw"] / P["pass2.module.it_mw"]
    d = scorecard.modules(temp, rh, P)["d"]
    for k, x in ds.items():
        assert x["mwh"] == pytest.approx(d[k].it_mwh * d[k].pue * n)
        assert x["nox"] == pytest.approx(x["mwh"] / g["mwh"] * P["air.gas.nox_tpy"])
    assert ds["gn"]["gensets"] == 0 and ds["gn"]["diesel_nox_t2"] == 0
    # The diesel tests: Tier 4 against Tier 2 is the ratio of the standards; the tons are short tons.
    old = ds["old"]
    assert old["diesel_nox_t4"] / old["diesel_nox_t2"] == pytest.approx(0.67 / P["pass2.backup.nox_g_kwh"])
    bk = scorecard.backup("conventional", P)
    assert old["diesel_nox_t2"] == pytest.approx(bk["nox_t"] * n / 0.907185)


def test_the_so2_check_by_hand():
    coal = pd.DataFrame({"year": [2021, 2022], "gen_mwh": [1.0, 1.0], "so2": [4736.0, 4185.0], "nox": [3144.0, 2472.0], "co2": [1.0, 1.0]})
    k = air.checks(coal, P)
    assert k["so2_2122"] == pytest.approx(4460.5)
    assert k["ratio"] == pytest.approx(4460.5 / 4460.6)
