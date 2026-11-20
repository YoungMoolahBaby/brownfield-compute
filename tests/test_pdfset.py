"""Pass 3f step 6 (D27): the bid set and Addendum 1 as PDFs only, and what each costs a bidder."""
import re
from collections import Counter

import pytest
from pypdf import PdfReader

from brownfield import addendum, bidset, pdfset
from brownfield.params import load_params


@pytest.fixture(scope="module")
def sets(tmp_path_factory):
    p = load_params()
    apt0, frame = bidset.load()
    apt1, _ = bidset.load("apartment-addendum-1.json")
    d = tmp_path_factory.mktemp("pdfset")
    base, rev = d / "base.ifc", d / "rev.ifc"
    bidset.write_ifc(apt0, frame, p, base)
    bidset.write_ifc(apt1, frame, p, rev, spec=addendum.SPEC)
    rb0, rb1 = bidset.read_back(base), bidset.read_back(rev)
    return {"rb0": rb0, "rb1": rb1, "p0": pdfset.places(rb0), "p1": pdfset.places(rb1), "dir": d}


def test_every_unit_and_schedule_cell_is_a_place(sets):
    p0 = sets["p0"]
    by_sheet = Counter(p.sheet for p in p0)
    assert {s: by_sheet[s] for s in pdfset.ELEVATIONS} == {"A-201": 45, "A-202": 45, "A-203": 24}
    assert by_sheet[pdfset.SCHEDULE] == 5 * len(pdfset.COLUMNS)  # W1, W2, D1, D2, D3


def test_the_addendum_changes_41_places_on_the_sheets(sets):
    # Front and back: the 6 patio doors (narrower) and the 12 windows beside them (W2 -> W1) on
    # each. The schedule: D1's width and glazing, W1's quantity, and W2's quantity and remarks:
    # W2 stays, for the 2 back stair windows over the landings (2406.4.3, pass 3f step 8).
    diff = pdfset.compare(sets["p0"], sets["p1"])
    counts = {s: (len(v["changed"]), len(v["added"]), len(v["removed"])) for s, v in diff.items()}
    assert counts == {"A-201": (18, 0, 0), "A-202": (18, 0, 0), "A-601": (5, 0, 0)}
    assert pdfset.count(diff) == 41
    cells = sorted(w for w, *_ in diff["A-601"]["changed"])
    assert cells == [("D1", "GLAZING"), ("D1", "WIDTH"), ("W1", "QTY"), ("W2", "QTY"), ("W2", "REMARKS")]


def test_the_pdfs_carry_the_tags_as_text(sets):
    # Read back as a takeoff tool would: the tags on the elevation sheets tally to the schedule.
    path = sets["dir"] / "bidset.pdf"
    order = pdfset.write_set(sets["rb0"], path)
    assert order == ["A-201", "A-202", "A-203", "A-601"]
    pages = PdfReader(str(path)).pages
    assert len(pages) == 4
    tags = Counter()
    for page, number in zip(pages, order):
        text = page.extract_text()
        assert number in text and "NOT FOR CONSTRUCTION" in text
        if number in pdfset.ELEVATIONS:
            tags.update(re.findall(r"\b([WD]\d+)\b", text))
    # The flat doors (D3) are on no elevation: the set has no floor plans, so a bidder reads
    # their count off the schedule alone.
    assert tags == {"W1": 75, "W2": 26, "D1": 12, "D2": 1}
    schedule = pages[order.index(pdfset.SCHEDULE)].extract_text()
    assert "D3 12" in schedule and "1 H FIRE DOOR, SELF-CLOSING" in schedule


def test_the_addendum_pdf_clouds_every_place_counted(sets):
    # A narrative page, then the revised sheets; one delta per place counted (41). No row is
    # withdrawn: W2 keeps the back stair windows.
    diff = pdfset.compare(sets["p0"], sets["p1"])
    path = sets["dir"] / "addendum-1.pdf"
    order = pdfset.write_set(sets["rb1"], path, revision="addendum-1", changes=diff,
                             narrative=["ADDENDUM 1", "Item 1 (data): tempered."], sheets=list(diff))
    assert order == ["ADD-1", "A-201", "A-202", "A-601"]
    texts = [pg.extract_text() for pg in PdfReader(str(path)).pages]
    assert "ADDENDUM 1" in texts[0] and len(texts) == 4
    assert "TEMPERED" in texts[3] and "DELETED" not in texts[3]
    assert [t.count(pdfset.DELTA) for t in texts] == [0, 18, 18, 5] and pdfset.count(diff) == 41


def test_an_addendum_that_touches_no_sheet_issues_only_its_narrative(sets, tmp_path):
    order = pdfset.write_set(sets["rb0"], tmp_path / "none.pdf", revision="addendum-9", changes={},
                             narrative=["ADDENDUM 9", "No sheets are revised by this addendum."], sheets=[])
    assert order == ["ADD-1"] and len(PdfReader(str(tmp_path / "none.pdf")).pages) == 1


def test_the_schedule_sheet_reads_as_a_us_set(sets):
    # U-factors in the unit NFRC rates them (Btu/h ft2 F) with SI after; the placeholder flagged;
    # laminated safety glazing shown as such, not as a dash.
    rows = {r["mark"]: r for r in bidset.schedule_rows(sets["rb0"])}
    cells = dict(zip(pdfset.COLUMNS, pdfset._schedule_cells(rows["W1"])))
    assert cells["U-FACTOR"] == "U-0.30 (1.70 W/m2K)" and cells["GLAZING"] == pdfset.DASH
    d2 = dict(zip(pdfset.COLUMNS, pdfset._schedule_cells(rows["D2"])))
    assert d2["U-FACTOR"].startswith("U-0.20") and "U-FACTOR TO BE CONFIRMED" in d2["REMARKS"]
    lam = dict(rows["D1"], safety_glazing="laminated")
    assert dict(zip(pdfset.COLUMNS, pdfset._schedule_cells(lam)))["GLAZING"] == "LAMINATED"


def test_a_moved_unit_counts_once():
    P = pdfset.Place
    old = [P("A-201", ("front", "w"), "W1", "W1 0.914 x 1.219 at 3.000, 0.914", (2.5, 3.5, 0.9, 2.1))]
    new = [P("A-201", ("front", "w"), "W1", "W1 0.914 x 1.219 at 3.500, 0.914", (3.0, 4.0, 0.9, 2.1))]
    assert pdfset.count(pdfset.compare(old, new)) == 1


def test_a_building_too_long_for_the_sheet_is_refused(sets, tmp_path):
    import copy

    long = copy.deepcopy(sets["rb0"])
    long["hi"][1] = long["lo"][1] + 40.0  # a 40 m front at 1/4" = 1'-0" runs into the title block
    with pytest.raises(ValueError, match="title block"):
        pdfset.write_set(long, tmp_path / "long.pdf", sheets=["A-201"])


def test_drawing_leaves_matplotlibs_settings_alone(sets, tmp_path):
    import matplotlib

    before = matplotlib.rcParams["pdf.fonttype"]
    pdfset.write_set(sets["rb0"], tmp_path / "set.pdf", sheets=["A-203"])
    assert matplotlib.rcParams["pdf.fonttype"] == before


def test_a_row_that_comes_or_goes_counts_once():
    P = pdfset.Place
    old = [P("A-601", ("W1", c), "W1", "x") for c in pdfset.COLUMNS] + [P("A-601", ("W2", c), "W2", "y") for c in pdfset.COLUMNS]
    new = [P("A-601", ("W1", c), "W1", "x") for c in pdfset.COLUMNS] + [P("A-601", ("W3", c), "W3", "z") for c in pdfset.COLUMNS]
    diff = pdfset.compare(old, new)
    assert (len(diff["A-601"]["removed"]), len(diff["A-601"]["added"]), len(diff["A-601"]["changed"])) == (1, 1, 0)


def test_the_pdfs_carry_no_creation_date(sets, tmp_path):
    pdfset.write_set(sets["rb0"], tmp_path / "set.pdf", sheets=["A-203"])
    assert "/CreationDate" not in (PdfReader(str(tmp_path / "set.pdf")).metadata or {})


def test_figures_are_closed_when_a_drawing_doesnt_fit(sets, tmp_path):
    import copy

    import matplotlib.pyplot as plt

    long = copy.deepcopy(sets["rb0"])
    long["hi"][1] = long["lo"][1] + 40.0
    before = len(plt.get_fignums())
    for draw in (lambda: pdfset.write_set(long, tmp_path / "long.pdf", sheets=["A-201"]),
                 lambda: pdfset.sheet_png(long, "A-201", tmp_path / "long.png")):
        with pytest.raises(ValueError):
            draw()
    assert len(plt.get_fignums()) == before


def test_the_report_figure_crop_holds_the_drawing(sets):
    # The crop takes the front elevation's width at 1/4" = 1'-0", its height and roof, and room
    # for its labels, inside the sheet's border and clear of the title block.
    x0, x1, y0, y1 = pdfset.elevation_crop(sets["rb1"], "front")
    el = bidset.elevation(sets["rb1"], "front")
    assert x1 - x0 >= el["width"] * pdfset.SCALE_IN_PER_M + 2.0
    assert y1 - y0 >= (max(r[3] for r in el["roofs"]) - el["z0"]) * pdfset.SCALE_IN_PER_M + 1.3
    assert x1 <= pdfset.SHEET_W - pdfset.BORDER - pdfset.TITLE_W and y1 <= pdfset.SHEET_H - pdfset.BORDER
