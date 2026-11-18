"""The scorecard as the design now stands: the current good neighbour's glass share, and the four module
designs on a synthetic year."""

import numpy as np
import pytest

from brownfield import scorecard
from brownfield.params import load_params, values

P = values(load_params())


def test_the_current_design_heats_only_its_share_of_the_glass():
    q = scorecard.current(P)
    n = P["scorecard.campus_it_mw"] / P["pass2.module.it_mw"]
    assert q["pass2.town.homes"] == 0.0
    assert q["pass2.greenhouse.hectares"] * n == pytest.approx(P["site.greenhouse_ha"])


def test_four_designs_on_a_mild_humid_year():
    temp, rh = np.full(8760, 10.0), np.full(8760, 70.0)
    m = scorecard.modules(temp, rh, P)
    d = m["d"]
    assert d["gn"].withdrawn_m3 == 0.0
    assert d["old"].withdrawn_m3 > d["ai"].withdrawn_m3 > d["cloud"].withdrawn_m3 >= 0.0
    assert d["old"].pue > max(d["cloud"].pue, d["ai"].pue, d["gn"].pue) > 1.0
    # Its heat goes only to the glass, a small share of what it rejects.
    assert 0.0 < d["gn"].delivered_mwh / d["gn"].heat_out_mwh < 0.1
