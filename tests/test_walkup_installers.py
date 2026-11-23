"""Pass 3g step 8c (D28): the installers' round's packets and its log (`brownfield.installers`).

Every comment here is synthetic, written into a temporary folder: nothing in these tests is an
installer's word, and nothing of it reaches the repo or the plan room."""
import json
from datetime import date

import pytest

from brownfield import installers as ins, servicesheets

IDS = {"P1", "P2", "M1", "E1", "F1", "C1", "C5"}
SHEETS = {n for n, _ in servicesheets.sheet_list()}


def _entry(**kw):
    e = {"id": "R-001", "trade": "plumber", "county": "TEST County", "received": date(2026, 12, 1), "via": "email",
         "about": ["P1"], "comment": "SYNTHETIC TEST ENTRY, not an installer's comment.", "publish": False, "status": "open"}
    e.update(kw)
    return e


def test_a_sound_log_has_no_problems():
    entries = [_entry(), _entry(id="R-002", trade="electrician", about=["E1", "E-602"], publish=True, status="answered",
                                answer="SYNTHETIC answer.", answered=date(2026, 12, 3))]
    assert ins.check_log(entries, IDS, SHEETS) == []


@pytest.mark.parametrize("change, says", [
    ({"trade": "roofer"}, "isn't one of the round's"),
    ({"about": ["P99"]}, "is no question, sheet"),
    ({"publish": "maybe"}, "publish must be yes or no"),
    ({"status": "answered"}, "needs its answer"),
    ({"status": "taken", "answer": "x", "answered": date(2026, 12, 2)}, "needs the addendum"),
    ({"comment": ""}, "no comment"),
    ({"received": "soon"}, "isn't a date"),
    ({"via": "fax"}, "isn't one of"),
])
def test_a_log_entry_missing_what_it_needs_is_named(change, says):
    problems = ins.check_log([_entry(**change)], IDS, SHEETS)
    assert any(says in p for p in problems), problems


def test_an_id_used_twice_is_named():
    assert any("used twice" in p for p in ins.check_log([_entry(), _entry()], IDS, SHEETS))


def test_only_a_comment_its_author_let_us_show_is_published(tmp_path):
    secret = "SYNTHETIC PRIVATE WORDS that must never be published."
    entries = [_entry(id="R-001", comment=secret, publish=False),
               _entry(id="R-002", trade="sprinkler contractor", about=["F1"], publish=True, status="taken", answer="SYNTHETIC answer.",
                      answered=date(2026, 12, 4), addendum=7)]
    forms = {}
    for t in ins.TRADES:
        f = tmp_path / "forms" / f"questions-{ins.SLUG[t]}.pdf"
        f.parent.mkdir(exist_ok=True)
        f.write_bytes(b"%PDF-1.4 synthetic")
        forms[t] = f
    out = tmp_path / "bidset" / "round"
    state = ins.publish(entries, forms, out)
    written = {p.name: p.read_bytes() for p in out.iterdir()}
    assert not any(secret.encode() in b for b in written.values())
    assert sorted(n for n in written if n.endswith(".bcf")) == ["r-002.bcf"]
    log = (out / "comments.md").read_text(encoding="utf-8")
    assert "Comments received: 2; shown here with their author's OK: 1." in log and "R-001" not in log
    assert "Taken in Addendum 7" in log
    assert [x["path"] for x in state["rfis"]] == ["round/r-002.bcf"]
    assert json.loads((out / "round.json").read_text(encoding="utf-8")) == state
    # The topic names a trade and a county, no person; its author is a role.
    import zipfile
    with zipfile.ZipFile(out / "r-002.bcf") as z:
        text = b"".join(z.read(n) for n in z.namelist()).decode("utf-8")
    assert "sprinkler@example.com" in text and "design@example.com" in text and "TEST County" in text
    # Published again, the same bytes: a rerun moves nothing in the plan room.
    first = (out / "r-002.bcf").read_bytes()
    ins.publish(entries, forms, out)
    assert (out / "r-002.bcf").read_bytes() == first


def test_a_comment_no_longer_to_be_shown_leaves_the_plan_room(tmp_path):
    forms = {}
    for t in ins.TRADES:
        f = tmp_path / f"questions-{ins.SLUG[t]}.pdf"
        f.write_bytes(b"%PDF-1.4 synthetic")
        forms[t] = f
    out = tmp_path / "round"
    ins.publish([_entry(publish=True)], forms, out)
    assert (out / "r-001.bcf").exists()
    ins.publish([_entry(publish=False)], forms, out)  # the author took it back
    assert not (out / "r-001.bcf").exists()


def test_the_letter_names_no_one_and_says_what_it_is():
    for t in ins.TRADES:
        text = " ".join(ins.letter_text(t))
        assert "not a job" in text and "made up" in text and ins.PLAN_ROOM in text
        assert "never your name" in text and "From:" not in text


def test_each_packet_holds_its_letter_questions_and_sheets(tmp_path):
    import pypdf

    sheets_pdf = ins.BIDSET / ins.SHEETS_PDF
    if not sheets_pdf.exists() or not all((ins.BIDSET / name).exists() for _, name in servicesheets.REVISED.values()):
        pytest.skip("the services sheets, or a sheet reissued alone, aren't published")
    pages = ins.sheet_pages(sheets_pdf)
    assert list(pages) == [n for n, _ in servicesheets.sheet_list()]
    form = tmp_path / "form.pdf"
    w = pypdf.PdfWriter()
    w.add_blank_page(612, 792)
    with open(form, "wb") as fh:
        w.write(fh)
    for t in ins.TRADES:
        k = ins.packet(t, form, tmp_path / "packets")
        r = pypdf.PdfReader(str(k["path"]))
        assert len(r.pages) == k["pages"] == 2 + len(ins.SHEETS[t])
        assert "would you look at its" in (r.pages[0].extract_text() or "")
        for i, n in enumerate(ins.SHEETS[t]):
            assert n in (r.pages[2 + i].extract_text() or ""), (t, n)
            # A sheet reissued alone comes from its addendum, the rest from the set as issued.
            rev = servicesheets.REVISED.get(n, (servicesheets.SHEETS_REV,))[0]
            assert f"revision: {rev}" in (r.pages[2 + i].extract_text() or ""), (t, n, rev)
