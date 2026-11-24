"""Pass 3g step 8b (D28): the installers' round's question sheets (`brownfield.questions`)."""
import re

import pytest

from brownfield import questions as qn, routed, servicesheets, systems
from brownfield.params import load_params, values


def test_the_study_s_own_references_are_kept_off_the_forms():
    assert qn.for_the_reader("Read the safe way until the authority says (step 6).") == "Read the safe way until the authority says."
    assert qn.for_the_reader("an open question of the study (D27).") == "an open question of the study."
    assert qn.for_the_reader("NEC 210.8(F) and 13R 7.2.3.1 (the stair)") == "NEC 210.8(F) and 13R 7.2.3.1 (the stair)"


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    P = values(load_params())
    apt = systems.load(systems.latest_model())
    routes = routed.load(apt, P)
    if routes is None or not routes.fresh:
        pytest.skip("no fresh routes (`brownfield routes`)")
    from brownfield.designs import issue

    if not (qn.BIDSET / f"services-{issue(P)}" / "holes.csv").exists():
        pytest.skip("the services schedules aren't published")
    s7 = routed.summary(apt, P, routes)
    return P, s7, qn.run(apt, P, out=tmp_path_factory.mktemp("round"), s7=s7)


def test_each_trade_has_its_questions_and_the_common_ones(made):
    _, _, r = made
    qs = r["questions"]
    assert set(qs) == {"P", "M", "E", "FP", "common"}
    ids = [q["id"] for t in qs for q in qs[t]]
    assert len(ids) == len(set(ids))
    assert [q["id"] for q in qs["common"]] == ["C1", "C2", "C3", "C4", "C5", "C6"]  # C6, the consent, last
    for t in qn.TRADES:
        assert len(qs[t]) >= 5, t
        text = r["md"].read_text(encoding="utf-8")
        assert f"for the {qn.TRADES[t]}" in text


def test_the_figures_are_the_designs(made):
    P, s7, r = made
    qs = {q["id"]: q for t in r["questions"] for q in r["questions"][t]}
    w = s7["fire"]["worst"]
    assert f"{w['need_psi']:.1f} of the {s7['fire']['target_psi']:.0f} psi" in qs["F1"]["ask"]
    assert f"{s7['water']['street_need_psi']:.1f} psi" in qs["P7"]["ask"]
    house = s7["electrical"]["service"]["house"]
    assert f"{house['breaker_a']:.0f} A" in qs["E7"]["ask"]
    # Nothing left unfilled, and every sheet a question points at is in the set.
    numbers = {n for n, _ in servicesheets.sheet_list()}
    for q in qs.values():
        assert "{" not in q["ask"] + q["see"] + q["why"], q["id"]
        for ref in re.findall(r"\b(?:G|P|M|E|FP)-\d{3}\b", q["see"]):
            assert ref in numbers, (q["id"], ref)


def test_the_forms_read_as_text_without_the_study_s_references(made):
    import pypdf

    _, _, r = made
    for t, path in r["pdfs"].items():
        text = "".join(pg.extract_text() or "" for pg in pypdf.PdfReader(str(path)).pages)
        assert "not a real project" in text and f"questions for the {qn.TRADES[t]}" in text
        assert not qn.STUDY_REF.search(text), t
        assert r["pages"][t] == len(pypdf.PdfReader(str(path)).pages)
