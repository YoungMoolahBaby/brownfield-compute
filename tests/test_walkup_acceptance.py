"""Pass 3g step 9c (D28): the tests and inspections (`brownfield.acceptance`)."""
import pytest

from brownfield import acceptance as ac, routed, systems
from brownfield.params import load_params, values


@pytest.fixture(scope="module")
def P():
    return values(load_params())


@pytest.fixture(scope="module")
def made(P):
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    s7 = routed.summary(apt, P, routes)
    return s7, ac.items(P, s7)


def test_every_quotation_is_the_codes_own_words(made, P):
    s7, its = made
    if not all(path.exists() for path, _ in ac.SRC.values()):
        pytest.skip("the saved code texts aren't on disk (data/raw is gitignored)")
    assert [label for label, ok, _ in ac.checks(P, s7, its) if not ok] == []
    # A quotation the code doesn't say is caught.
    bad = [dict(its[0], quotes=[("IPC", "This pressure shall be held for not less than 60 minutes")])] + its[1:]
    first = ac.checks(P, s7, bad)[0]
    assert not first[1] and "P-1" in first[2]


def test_the_schedule_takes_its_figures_from_the_design(made, P):
    s7, its = made
    by = {it["id"]: it for it in its}
    c4, w, L = s7["water"]["c404"], s7["water"], s7["loop"]
    assert f"the design's worst {c4['worst']['oz']:.0f}" in by["HW-2"]["passes"]
    assert f"{w['loop']['gpm']:.2f} gpm in all" in by["HW-3"]["passes"]
    assert f"{L['pump_ft']:.1f} ft at the worst flat" in by["H-3"]["passes"] and f"{L['pump_curve_ft']:.1f} ft" in by["H-3"]["passes"]
    # E-1 (Addendum 8): the whole building at Phius's rate on its enclosure, each flat at the compartment limit.
    lim = by["E-1"]["limits"]
    assert f"at most {lim['building_cfm50']:,.0f} cfm at 50 Pa" in by["E-1"]["passes"]
    assert f"{P['systems.phius.compartment_cfm50_ft2']:.2f} cfm50 per ft2 of its own shell" in by["E-1"]["passes"]
    assert "air changes" not in by["E-1"]["passes"]
    assert f"{P['systems.plumbing.max_static_psi']:g} psi" in by["P-3"]["passes"]
    # Every code-based item quotes its code; every other rests on the design or the sequence, named.
    for it in its:
        assert it["quotes"] or "design" in it["basis"] or "sequence" in it["basis"], it["id"]


def test_the_written_section_holds_every_item(made, P):
    _, its = made
    md = ac.markdown(P, its)
    for it in its:
        assert f"| {it['id']} |" in md
    assert md.count('"') >= 2 * sum(len(it["quotes"]) for it in its)
