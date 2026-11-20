"""The walk-up's website (GitHub Pages): the plan room and the 3D viewer, as tools/viewer/build_site.py
builds them. Every link and every file the viewer loads must be in the built site, by a path
relative to the page (the site lives under /brownfield-compute/). The plan room's numbers must be
the model's: its counts and sizes are filled in from the files, and its description and sheet list,
written in the template, are held to the model and the PDF set here."""
import html
import importlib.util
import re
from pathlib import Path

import pytest

from brownfield import addendum, bidset, pdfset, viewer
from brownfield.params import load_params

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_site", ROOT / "tools" / "viewer" / "build_site.py")
build_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_site)

READY = viewer.status()
ready = pytest.mark.skipif(READY[0] != "ok", reason=f"viewer not ready: {READY[1]}")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    if READY[0] != "ok":
        pytest.skip(f"viewer not ready: {READY[1]}")
    out = tmp_path_factory.mktemp("site") / "brownfield-compute"
    build_site.build(out)
    return out


def _page(site):
    return (site / "index.html").read_text(encoding="utf-8")


def _links(text: str) -> list[str]:
    return re.findall(r'(?:href|src)="([^"]+)"', text)


@ready
def test_every_link_in_the_plan_room_is_in_the_site(site):
    page = _page(site)
    assert "{{" not in page
    local = [x for x in _links(page) if not x.startswith(("http://", "https://"))]
    assert local, "no links"
    for link in local:
        path = link.split("#")[0].split("?")[0]
        assert not path.startswith("/"), f"{link}: absolute, breaks under the site's prefix"
        assert (site / path).is_file(), link
    # The model is on the front page, embedded (the viewer hides its own notice and links there).
    assert '<iframe src="model.html?embed"' in page
    viewer_page = (site / "model.html").read_text(encoding="utf-8")
    assert 'has("embed")' in viewer_page and ".embed .notice" in viewer_page
    # ...and starts inert there, so the page scrolls past it until it is clicked.
    assert 'id="activate"' in viewer_page and "explore(false)" in viewer_page


@ready
def test_every_file_the_viewer_loads_or_links_is_in_the_site(site):
    page = (site / "model.html").read_text(encoding="utf-8")
    imports = re.search(r'<script type="importmap">\s*(\{.*?\})\s*</script>', page, re.S).group(1)
    paths = re.findall(r'"(\./[^"]+)"', imports)
    paths += re.findall(r'from "(\./[^"]+)"', page)
    paths += re.findall(r'file: "(\./[^"]+)"', page)
    paths.append(re.search(r'SetWasmPath\("(\./[^"]+)"', page).group(1) + "web-ifc.wasm")
    paths += [x for x in _links(page) if not x.startswith(("http://", "https://"))]
    assert len(paths) >= 8
    for p in paths:
        assert (site / p).is_file(), p
    assert not re.search(r'["(]/(vendor|models)/', page), "an absolute path"


@ready
def test_the_plan_room_counts_are_the_models(site):
    apt, _ = bidset.load()
    p = load_params()
    facts = {label: int(n.replace(",", "")) for n, label in
             re.findall(r'<div class="fact"><b>([\d,]+)</b><span>([^<]+)</span>', _page(site))}
    hazards = bidset.safety_glazing(apt, p)
    marks = bidset.types(apt, hazards)
    windows = [o for o in apt["openings"] if o["kind"] == "window"]
    w_types = sum(k[0] == "window" for k in marks)
    d_types = len(marks) - w_types
    assert facts[f"windows, in {w_types} types"] == len(windows)
    assert facts[f"doors, in {d_types} types"] == len(apt["openings"]) - len(windows)
    assert facts["openings the code calls for safety glass in"] == len(hazards)
    assert facts["addendum"] == 1


@ready
def test_the_plan_rooms_description_and_sheets_are_the_models(site):
    apt, _ = bidset.load()
    page = _page(site)
    ft = 0.3048
    desc = f"A {apt['storeys']}-storey walk-up, {apt['length_m'] / ft:g} x {apt['depth_m'] / ft:g} ft, with {len(apt['flats'])} flats"
    assert desc in page
    named = re.findall(r"\b(A-\d{3})\b", page)
    assert sorted(set(named)) == sorted([*pdfset.ELEVATIONS, pdfset.SCHEDULE])


@ready
def test_the_addendum_items_are_the_rfis(site):
    apt0, _ = bidset.load()
    apt1, _ = bidset.load("apartment-addendum-1.json")
    answer = addendum.words(apt0, apt1, load_params())["answer"]
    one, two = build_site.ITEMS.search(answer).groups()
    shown = html.unescape(re.search(r"Addendum 1 <small>([^<]+)</small>", _page(site)).group(1))
    assert shown == f"{one}; {two}"


def test_an_item_doesnt_stop_at_a_decimal_point():
    # The review's case: a width with a fraction of an inch.
    m = build_site.ITEMS.search('Item 1: tempered. Item 2: the doors narrow from 6\'-0" to 4\'-11.875", centred where they were.')
    assert m.groups() == ("tempered", 'the doors narrow from 6\'-0" to 4\'-11.875", centred where they were')


def test_it_wont_build_over_the_repository_or_a_folder_it_didnt_make(tmp_path):
    for bad in (ROOT, ROOT / "out", ROOT / "tools" / "viewer", ROOT / "docs"):
        with pytest.raises(SystemExit):
            build_site._safe_out(bad)
    stranger = tmp_path / "theirs"
    stranger.mkdir()
    (stranger / "notes.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(SystemExit):
        build_site._safe_out(stranger)
    build_site._safe_out(tmp_path / "new")  # a new folder is fine
    made = tmp_path / "made"
    made.mkdir()
    (made / build_site.MARKER).write_text("", encoding="utf-8")
    (made / "index.html").write_text("", encoding="utf-8")
    build_site._safe_out(made)  # one it made before is fine
