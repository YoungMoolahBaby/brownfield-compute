"""Build the walk-up's website (GitHub Pages): a plan room for its bid documents, and the 3D viewer.

    python3 tools/viewer/build_site.py [out dir]     (after `npm ci` in tools/viewer; default out/site)

Standard library only, so the Pages workflow (.github/workflows/pages.yml) runs it with the runner's
Python. The site:
- `index.html`: the plan room (tools/viewer/planroom.html). Its counts, the file sizes and the
  number of addenda are filled in from the published files, and Addendum 1's items from the
  published RFI. The building's description and the sheet list are written in the template;
  tests/test_website.py holds them to the model and to the PDF set;
- `model.html`: the 3D viewer (tools/viewer/index.html);
- `vendor/`: only the files the viewer loads from the two pinned packages (tools/viewer's lock), with
  their licences;
- `models/`: the two IFCs the viewer opens;
- `files/`: the published bid set (docs/pass3/bidset), to download.

It replaces the output folder only if a previous build made it (it leaves a marker file there) or
it is empty, and never a folder holding the repository or its sources.
"""

from __future__ import annotations

import csv
import html
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
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
# An item ends at a full stop followed by a space or the end: not at the point in 4'-11.875".
ITEMS = re.compile(r"Item 1: (.+?)\.(?=\s|$)\s*Item 2: (.+?)\.(?=\s|$)")


def _size(path: Path) -> str:
    kb = round(path.stat().st_size / 1e3)
    return f"{path.stat().st_size / 1e6:.1f} MB" if kb >= 1000 else f"{max(1, kb)} kB"


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
    missing = [str(src) for src in COPIES.values() if not src.exists()]
    if missing:
        raise SystemExit("missing (run `npm ci --ignore-scripts` in tools/viewer, and publish the bid set): " + ", ".join(missing))
    _safe_out(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / MARKER).write_text("made by tools/viewer/build_site.py; safe to delete\n", encoding="utf-8")
    written = []
    for rel, src in COPIES.items():
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        written.append(dst)
    shutil.copytree(PUBLISHED, out / "files")
    page = (VIEWER / "planroom.html").read_text(encoding="utf-8")
    page = re.sub(r"\{\{size:([^}]+)\}\}", lambda m: _size(out / m.group(1)), page)
    c = counts(PUBLISHED / "drawings" / "schedule.csv")
    c["addenda"] = len(list(PUBLISHED.glob("addendum-*.pdf")))
    page = re.sub(r"\{\{count:(\w+)\}\}", lambda m: f"{c[m.group(1)]:,}", page)
    one, two = addendum_items(PUBLISHED / "rfi-001.bcf")
    page = page.replace("{{addendum:items}}", f"{html.escape(one)}; {html.escape(two)}")
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
