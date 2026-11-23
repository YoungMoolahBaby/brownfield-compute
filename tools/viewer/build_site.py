"""Build the walk-up's website (GitHub Pages): a plan room for its bid documents, and the 3D viewer.

    python3 tools/viewer/build_site.py [out dir]     (after `npm ci` in tools/viewer; default out/site)

Standard library only, so the Pages workflow (.github/workflows/pages.yml) runs it with the runner's
Python. The site (D27, D29):
- `index.html`: the plan room (tools/viewer/planroom.html), laid out as a builders exchange lays out
  a project: the project's header, an "Addenda (N, latest ...)" dropdown with each addendum's items
  and files, the bid documents as a tree of folders, and the model. What it shows is read from the
  published files: the addenda, their dates, items and files from `addenda.json` (written by
  `brownfield systems --ifc --publish`), the counts from the latest schedule, each file's size.
  The building's description and the sheet list are written in the template; tests/test_website.py
  holds them to the model and to the PDF set;
- `model.html`: the 3D viewer (tools/viewer/index.html);
- `vendor/`: only the files the viewer loads from the two pinned packages (tools/viewer's lock), with
  their licences;
- `models/`: the IFCs the viewer opens (the bid set, each addendum's, the framing and services models), the
  manifest and what each addendum changed;
- `files/`: the published bid set (docs/pass3/bidset), to download. The folders on the page are
  the page's; the files keep their published paths, so a link once given keeps working.

It replaces the output folder only if a previous build made it (it leaves a marker file there) or
it is empty, and never a folder holding the repository or its sources.
"""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIEWER = ROOT / "tools" / "viewer"
PUBLISHED = ROOT / "docs" / "pass3" / "bidset"
NODE = VIEWER / "node_modules"
DEFAULT_OUT = ROOT / "out" / "site"
MARKER = ".built-by-build-site"  # a dot file: the Pages artifact leaves it out
COPIES = {  # site path: source
    "model.html": VIEWER / "index.html",
    "vendor/web-ifc/web-ifc-api.js": NODE / "web-ifc" / "web-ifc-api.js",
    "vendor/web-ifc/web-ifc.wasm": NODE / "web-ifc" / "web-ifc.wasm",
    "vendor/web-ifc/LICENSE.md": NODE / "web-ifc" / "LICENSE.md",
    "vendor/three/build/three.module.min.js": NODE / "three" / "build" / "three.module.min.js",
    "vendor/three/examples/jsm/controls/OrbitControls.js": NODE / "three" / "examples" / "jsm" / "controls" / "OrbitControls.js",
    "vendor/three/LICENSE": NODE / "three" / "LICENSE",
    "models/apartment.ifc": PUBLISHED / "apartment.ifc",
    "models/apartment-addendum-1.ifc": PUBLISHED / "apartment-addendum-1.ifc",
}
MANIFEST = PUBLISHED / "addenda.json"
# When the bid documents themselves went out: first published with D27's report (git 8a9d200).
BID_ISSUED = "2026-11-19T23:29:07-08:00"
# The bid documents' folders (D29): (folder, [(published path, what it is)]).
BID_FOLDERS = [
    ("Drawings", [
        ("bidset.pdf", "Drawings: front and back elevations (A-201, A-202), the ends (A-203), the window and door schedule (A-601)"),
        ("drawings/elevation_front.svg", "Front elevation, drawn from the model"),
        ("drawings/elevation_back.svg", "Back elevation, drawn from the model"),
        ("drawings/elevation_left.svg", "Left end, drawn from the model"),
        ("drawings/elevation_right.svg", "Right end, drawn from the model"),
    ]),
    ("Model", [("apartment.ifc", "The model, IFC4: every wall, slab, stair, window and door, with its type and properties")]),
    ("Schedules", [
        ("drawings/schedule.csv", "Window and door schedule, one row per type"),
        ("drawings/openings.csv", "Every window and door: where it is, its size, whether it needs safety glass"),
        ("drawings/quantities.csv", "Quantities: wall and opening areas by facade"),
    ]),
    ("Requirements", [
        ("bidset.ids", "What a quote needs, as a machine-checkable list (buildingSMART IDS 1.0)"),
        ("checklist.md", "How much of it the model carries"),
    ]),
]
# An item ends at a full stop followed by a space or the end: not at the point in 4'-11.875".
ITEMS = re.compile(r"Item 1: (.+?)\.(?=\s|$)\s*Item 2: (.+?)\.(?=\s|$)")


def _size(path: Path) -> str:
    n = sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.is_dir() else path.stat().st_size
    kb = round(n / 1e3)
    return f"{n / 1e6:.1f} MB" if kb >= 1000 else f"{max(1, kb)} kB"


def when(iso: str, with_time: bool = True) -> str:
    """An issue date as an exchange shows it: Nov 21, 2026, 9:15 AM (UTC-8)."""
    t = datetime.fromisoformat(iso)
    off = t.utcoffset().total_seconds() / 3600 if t.utcoffset() is not None else 0
    day = f"{t:%b} {t.day}, {t.year}"
    if not with_time:
        return day
    return f"{day}, {t.hour % 12 or 12}:{t:%M} {'AM' if t.hour < 12 else 'PM'} (UTC{off:+g})".replace("+-", "-")


def counts(schedule: Path) -> dict[str, int]:
    """Windows and doors, their types, and the openings needing safety glass, from the schedule."""
    with schedule.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = {"windows": 0, "doors": 0, "window_types": 0, "door_types": 0, "safety": 0}
    for r in rows:
        if r["kind"] not in ("window", "door"):
            raise SystemExit(f"{schedule}: a row of kind {r['kind']!r}, neither window nor door")
        kind = r["kind"] + "s"
        out[kind] += int(r["count"])
        out[r["kind"] + "_types"] += 1
        out["safety"] += int(r["count"]) if r["safety_glazing_required"].startswith("yes") else 0
    return out


def addendum_items(bcf: Path) -> tuple[str, str]:
    """Addendum 1's two items, as the RFI's answer gives them (the BCF's comments, decoded)."""
    with zipfile.ZipFile(bcf) as z:
        texts = [el.text or "" for n in z.namelist() if n.endswith("markup.bcf")
                 for el in ET.fromstring(z.read(n)).iter() if el.tag.rsplit("}", 1)[-1] == "Comment"]
    for text in texts:
        m = ITEMS.search(text)
        if m:
            return m.group(1), m.group(2)
    raise SystemExit(f"{bcf}: no Item 1 and Item 2 in the RFI's answer")


def manifest() -> dict:
    """The published addenda (addenda.json), each checked to name only files that are published."""
    if not MANIFEST.exists():
        raise SystemExit(f"no {MANIFEST.relative_to(ROOT)}: run `uv run brownfield systems --ifc --publish`")
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = [f["path"] for a in m["addenda"] for f in a["files"] if not (PUBLISHED / f["path"]).exists()]
    missing += [p for a in m["addenda"] for p in (a["model"], a["changes"], a["rfi"]) if p and not (PUBLISHED / p).exists()]
    rnd = m.get("round") or {}
    missing += [x["path"] for x in rnd.get("files", []) + rnd.get("rfis", []) if not (PUBLISHED / x["path"]).exists()]
    if m.get("framing") and not (PUBLISHED / m["framing"]["model"]).exists():
        missing.append(m["framing"]["model"])
    s = m.get("services")
    if s:
        missing += [x for x in [s["model"], *(f["path"] for f in s["files"])] if not (PUBLISHED / x).exists()]
    if missing:
        raise SystemExit(f"addenda.json names files that aren't published: {missing}")
    return m


def _kind(path: str) -> str:
    return path.rsplit(".", 1)[-1].upper()


def _row(path: str, label: str, issued: str) -> str:
    e = html.escape
    name = path.rsplit("/", 1)[-1]
    dl = "" if path.endswith((".svg", ".md")) else " download" + (f'="{e(path.replace("/", "-"))}"' if "/" in path else "")
    return (f'<tr><td><span class="ft">{e(_kind(path))}</span> <a href="files/{e(path)}"{dl}>{e(label)}</a></td>'
            f'<td class="k">{e(name)}</td><td class="d">{e(when(issued, False))}</td><td class="s">{_size(PUBLISHED / path)}</td></tr>')


def _folder(name: str, rows: list[str], note: str = "", open_: bool = False) -> str:
    e = html.escape
    return (f'<details class="folder"{" open" if open_ else ""}><summary><span class="fold">{e(name)}</span>'
            f'<span class="n">{len(rows)} file{"s" if len(rows) != 1 else ""}{e(note)}</span></summary>'
            f'<table><tr><th>Document</th><th class="k">File</th><th class="d">Issued</th><th class="s">Size</th></tr>{"".join(rows)}</table></details>')


def tree(m: dict) -> str:
    """The bid documents as folders: the bid set's, each addendum's, the RFIs (the installers' comments
    shown among them), the framing model, the services model and its schedules, and the installers'
    round."""
    bid = "".join(_folder(name, [_row(p, label, BID_ISSUED) for p, label in files]) for name, files in BID_FOLDERS)
    adds = "".join(_folder(f"Addendum {a['number']:02d}: {a['title']}", [_row(f["path"], f["label"], a["issued"]) for f in a["files"]],
                           f" · issued {when(a['issued'], False)}") for a in reversed(m["addenda"]))
    rfis = [_row(a["rfi"], f"RFI {a['rfi'][4:7]}, answered by Addendum {a['number']} (BCF 3.0)", a["issued"])
            for a in m["addenda"] if a["rfi"]]
    rnd = m.get("round")
    rfis += [_row(x["path"], f"The installers' round: {x['label']}", x["issued"]) for x in (rnd or {}).get("rfis", [])]
    out = [f'<details class="folder top" open><summary><span class="fold">01 Bid documents</span>'
           f'<span class="n">issued {html.escape(when(BID_ISSUED, False))}</span></summary>{bid}</details>',
           f'<details class="folder top" open><summary><span class="fold">02 Addenda</span>'
           f'<span class="n">{len(m["addenda"])}</span></summary>{adds}</details>',
           f'<details class="folder top"><summary><span class="fold">03 RFIs</span><span class="n">{len(rfis)}</span></summary>'
           f'<table><tr><th>Document</th><th class="k">File</th><th class="d">Issued</th><th class="s">Size</th></tr>{"".join(rfis)}</table></details>']
    f = m.get("framing")
    if f:
        last = next(a for a in m["addenda"] if f"addendum-{a['number']}" == f["revision"])
        label = f"The wood frame, IFC4: {f['members']:,} members ({f['note']})"
        out.append(f'<details class="folder top"><summary><span class="fold">04 Framing model</span><span class="n">{html.escape(f.get("status", "reference"))}</span></summary>'
                   f'<table><tr><th>Document</th><th class="k">File</th><th class="d">Issued</th><th class="s">Size</th></tr>'
                   f'{_row(f["model"], label, last["issued"])}</table></details>')
    s = m.get("services")
    if s:
        rows = [_row(s["model"], f"The services, IFC4: {s['elements']:,} elements, routed through {s['frame']} ({s['note']})", s["issued"])]
        rows += [_row(x["path"], x["label"], s["issued"]) for x in s["files"]]
        out.append(f'<details class="folder top"><summary><span class="fold">05 Services model</span><span class="n">{html.escape(s.get("status", "preliminary"))}</span></summary>'
                   f'<table><tr><th>Document</th><th class="k">File</th><th class="d">Issued</th><th class="s">Size</th></tr>'
                   f'{"".join(rows)}</table></details>')
    if rnd:  # the installers' round (pass 3g step 8): the question forms and what came back
        out_rows = [_row(x["path"], x["label"], rnd["issued"]) for x in rnd["files"]]
        out.append("<details class=\"folder top\"><summary><span class=\"fold\">06 Installers' round</span>"
                   f'<span class="n">{html.escape(rnd["note"])}</span></summary>'
                   f'<table><tr><th>Document</th><th class="k">File</th><th class="d">Issued</th><th class="s">Size</th></tr>'
                   f'{"".join(out_rows)}</table></details>')
    return "".join(out)


def addenda(m: dict) -> tuple[str, str]:
    """The dropdown's summary line and its list, newest first."""
    e = html.escape
    latest = max(m["addenda"], key=lambda a: a["issued"])
    summary = f'Addenda ({len(m["addenda"])}) <span class="n">latest {e(when(latest["issued"]))}</span>'
    items = []
    for a in sorted(m["addenda"], key=lambda a: a["issued"], reverse=True):
        files = " · ".join(f'<a href="files/{e(f["path"])}">{e(f["path"].rsplit("/", 1)[-1])}</a>' for f in a["files"])
        # An addendum that changes no model (Addendum 6) has nothing to mark in 3D.
        seen = f' · <a href="model.html#addendum-{a["number"]}-changes">see what changed in 3D</a>' if a["model"] else ""
        items.append(
            f'<li><div class="ah"><b>Addendum {a["number"]:02d}</b> <span>{e(a["title"])}</span>'
            f'<span class="n">issued {e(when(a["issued"]))}</span></div>'
            f'<ol>{"".join(f"<li>{e(x)}</li>" for x in a["items"])}</ol>'
            f'<p class="af">{files}{seen}</p></li>')
    return summary, f'<ol class="addenda-list" reversed>{"".join(items)}</ol>'


def _safe_out(out: Path) -> None:
    """Refuse an output folder that holds the repository or its sources, or that something other
    than a previous build put files in."""
    out = out.resolve()
    for keep in (ROOT, VIEWER, PUBLISHED, ROOT / "out", ROOT / "docs", ROOT / ".git"):
        if out == keep or keep.is_relative_to(out):
            raise SystemExit(f"{out}: won't build into a folder that holds {keep}")
    if out.exists() and any(out.iterdir()) and not (out / MARKER).exists():
        raise SystemExit(f"{out}: not empty, and not made by this script; pick another folder")


def build(out: Path = DEFAULT_OUT) -> list[Path]:
    m = manifest()
    copies = dict(COPIES)
    for a in m["addenda"]:
        if not a["model"]:
            continue
        copies[f"models/{a['model']}"] = PUBLISHED / a["model"]
        if a["changes"]:
            copies[f"models/{a['changes']}"] = PUBLISHED / a["changes"]
    if m.get("framing"):
        copies[f"models/{m['framing']['model']}"] = PUBLISHED / m["framing"]["model"]
    if m.get("services"):
        copies[f"models/{m['services']['model']}"] = PUBLISHED / m["services"]["model"]
    copies["models/addenda.json"] = MANIFEST
    missing = [str(src) for src in copies.values() if not src.exists()]
    if missing:
        raise SystemExit("missing (run `npm ci --ignore-scripts` in tools/viewer, and publish the bid set): " + ", ".join(missing))
    _safe_out(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("made by tools/viewer/build_site.py; safe to delete\n", encoding="utf-8")
    written = []
    for rel, src in copies.items():
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        written.append(dst)
    shutil.copytree(PUBLISHED, out / "files")
    page = (VIEWER / "planroom.html").read_text(encoding="utf-8")
    page = re.sub(r"\{\{size:([^}]+)\}\}", lambda mm: _size(out / mm.group(1)), page)
    latest = max(m["addenda"], key=lambda a: a["number"])
    drawn = max((a for a in m["addenda"] if a["model"]), key=lambda a: a["number"])  # the latest with a model of its own
    c = counts(PUBLISHED / f"drawings-addendum-{drawn['number']}" / "schedule.csv")
    c["addenda"] = len(m["addenda"])
    page = re.sub(r"\{\{count:(\w+)\}\}", lambda mm: f"{c[mm.group(1)]:,}", page)
    summary, listing = addenda(m)
    page = (page.replace("{{addenda:summary}}", summary).replace("{{addenda:list}}", listing)
            .replace("{{documents:tree}}", tree(m)).replace("{{bid:issued}}", html.escape(when(BID_ISSUED)))
            .replace("{{addenda:latest}}", f"Addendum {latest['number']}")
            .replace("{{addenda:latest_model}}", f"Addendum {drawn['number']}")
            .replace("{{addenda:latest_model_n}}", str(drawn["number"])))
    if "{{" in page:
        raise SystemExit("planroom.html: a {{...}} left unfilled")
    (out / "index.html").write_text(page, encoding="utf-8")
    return written + [out / "index.html"]


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("usage: python3 tools/viewer/build_site.py [out dir]")
    out = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else DEFAULT_OUT
    build(out)
    files = [p for p in out.rglob("*") if p.is_file() and p.name != MARKER]
    print(f"built {out}: {len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.1f} MB")
