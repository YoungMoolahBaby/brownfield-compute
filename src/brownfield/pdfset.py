"""Pass 3f step 6 (D27): the conventional side, the same bid set issued as PDFs only.

`brownfield pdfset` (after forge's `apartment-json` and `apartment-json addendum-1 <in>`) draws the
walk-up's bid set as an architect issues it, from the IFC: A-201 and A-202 the front and back
elevations, A-203 the two ends (1/4" = 1'-0" on 36 x 24 in sheets), and A-601 the window and door
schedule. Then Addendum 1 the same way: a narrative page, and the revised sheets with a revision
cloud and delta round every change, a withdrawn row or unit shown where it was.

What it measures is what a bidder with only the PDFs has to do:
- **to bid:** count every tag by eye on the elevations and read the schedule's rows;
- **for the addendum:** find every place on the sheets that changed (a unit's tag, size or
  position, a schedule cell, a row that comes or goes), against the data side, where the element
  diff lists them by GlobalId.

The IFCs are rebuilt here from forge's current model, and the revision is checked to be the base
plus the addendum, so the narrative, the sheets and the counts come from the same run. The sheets
are cleaner than a real set: no floor plans, sections, details, dimension strings or
specifications, where the same change shows up again, and every change here is clouded, which in
practice they aren't always. So the counts are a lower bound. A unit is matched across the two
sets by its id, which the sheets don't show; what a bidder sees is its tag, size and position.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import OUT_DIR, bidset

SHEET_W, SHEET_H = 36.0, 24.0  # in, ARCH D
BORDER, TITLE_W = 0.5, 4.0  # in: the border, and the title block's strip on the right
SCALE_IN_PER_M = 0.25 / 0.3048  # 1/4" = 1'-0"
ELEVATIONS = {"A-201": ("FRONT ELEVATION", ["front"]), "A-202": ("BACK ELEVATION", ["back"]),
              "A-203": ("END ELEVATIONS", ["left", "right"])}
SCHEDULE = "A-601"
COLUMNS = ["MARK", "QTY", "WIDTH", "HEIGHT", "OPERATION", "FRAME", "GLAZING", "U-FACTOR", "REMARKS"]
COLUMN_W = [0.9, 0.7, 1.0, 1.0, 1.5, 1.3, 1.3, 2.4, 5.2]  # in
ROW_H = 0.35  # in
DASH = "—"
DELTA = "△"


@dataclass(frozen=True)
class Place:
    """One thing on a sheet a bidder reads: which sheet, a key that matches it across two sets (a
    unit's face and id, or a schedule row and column; the bidder doesn't see it), its mark, what
    it shows, and for a unit where it is drawn (u0, u1, z0, z1, in m on its face)."""
    sheet: str
    key: tuple
    mark: str
    shows: str
    box: tuple | None = None


def _usable_right() -> float:
    return SHEET_W - BORDER - TITLE_W - 0.3


def _schedule_cells(row: dict) -> list[str]:
    """A schedule row as an architect's sheet shows it: blanks as a dash, not 'not in the model';
    U-factors in the US unit (Btu/h ft2 F, as NFRC rates them) with SI after."""
    def v(x):
        return DASH if x in (None, "", bidset.NOT_IN_MODEL) else str(x)

    sg = row.get("safety_glazing")
    if sg not in (None, "", bidset.NOT_IN_MODEL):
        glazing = str(sg).upper()
    elif str(row.get("tempered")) == "True":
        glazing = "TEMPERED"
    elif str(row.get("tempered", "")).startswith("varies"):
        glazing = str(row["tempered"]).upper()
    else:
        glazing = DASH
    try:  # the schedule carries it as text, e.g. "1.703", or "varies: ..."
        u = float(row.get("u_factor_w_m2k"))
        u_cell = f"U-{u / bidset.BTU_FT2:.2f} ({u:.2f} W/m2K)"
    except (TypeError, ValueError):
        u_cell = v(row.get("u_factor_w_m2k"))
    remarks = []
    if row["safety_glazing_required"] != "no":
        remarks.append("SAFETY GLAZING REQ'D, " + row["safety_glazing_required"].removeprefix("yes (").removesuffix(")"))
    if "placeholder" in str(row.get("u_factor_source", "")):
        remarks.append("U-FACTOR TO BE CONFIRMED")
    if row.get("fire_rating") not in (None, "", bidset.NOT_IN_MODEL):  # a flat door into the stair (pass 3f step 8)
        remarks.append(f"{str(row['fire_rating']).upper()} FIRE DOOR" + (", SELF-CLOSING" if str(row.get("self_closing")) == "True" else ""))
    return [row["mark"], str(row["count"]), v(row["width"]), v(row["height"]), v(row["operation"]).upper(),
            v(row["frame_material"]).upper(), glazing, u_cell, "; ".join(remarks) or DASH]


def places(rb: dict) -> list[Place]:
    """Everything on the sheets a bidder reads: each unit on an elevation (its tag, size and
    position) and each schedule cell."""
    out = []
    for sheet, (_, faces) in ELEVATIONS.items():
        for face in faces:
            for r in bidset.elevation(rb, face)["rects"]:
                c = (r["u0"] + r["u1"]) / 2
                out.append(Place(sheet, (face, r["name"]), r["mark"],
                                 f"{r['mark']} {r['u1'] - r['u0']:.3f} x {r['z1'] - r['z0']:.3f} at {c:.3f}, {r['z0']:.3f}",
                                 (r["u0"], r["u1"], r["z0"], r["z1"])))
    for row in bidset.schedule_rows(rb):
        for col, cell in zip(COLUMNS, _schedule_cells(row)):
            out.append(Place(SCHEDULE, (row["mark"], col), row["mark"], cell))
    return out


def compare(old: list[Place], new: list[Place]) -> dict:
    """The places that differ between two sets, by sheet: changed (the same thing, showing
    something else), added, removed, each as (key, old place or None, new place or None). A
    schedule row that comes or goes counts once, not per cell."""
    o = {(p.sheet, p.key): p for p in old}
    n = {(p.sheet, p.key): p for p in new}
    rows_o = {k[0] for (s, k) in o if s == SCHEDULE}
    rows_n = {k[0] for (s, k) in n if s == SCHEDULE}
    by_sheet: dict[str, dict] = {}

    def at(sheet):
        return by_sheet.setdefault(sheet, {"changed": [], "added": [], "removed": []})

    for sk in sorted(o.keys() | n.keys(), key=str):
        sheet, key = sk
        if sheet == SCHEDULE and (key[0] not in rows_o or key[0] not in rows_n):
            continue
        a, b = o.get(sk), n.get(sk)
        if a and b and a.shows != b.shows:
            at(sheet)["changed"].append((key, a, b))
        elif a and not b:
            at(sheet)["removed"].append((key, a, None))
        elif b and not a:
            at(sheet)["added"].append((key, None, b))
    for mark in sorted(rows_o - rows_n):
        at(SCHEDULE)["removed"].append(((mark, "row"), Place(SCHEDULE, (mark, "row"), mark, "row"), None))
    for mark in sorted(rows_n - rows_o):
        at(SCHEDULE)["added"].append(((mark, "row"), None, Place(SCHEDULE, (mark, "row"), mark, "row")))
    return dict(sorted(by_sheet.items()))


def count(diff: dict) -> int:
    return sum(len(v["changed"]) + len(v["added"]) + len(v["removed"]) for v in diff.values())


# ---- Drawing the sheets ----

def _figure():
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(SHEET_W, SHEET_H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SHEET_W)
    ax.set_ylim(0, SHEET_H)
    ax.axis("off")
    return fig, ax


def _title_block(ax, number: str, title: str, revision: str) -> None:
    from matplotlib.patches import Rectangle

    ax.add_patch(Rectangle((BORDER, BORDER), SHEET_W - 2 * BORDER, SHEET_H - 2 * BORDER, fill=False, lw=1.5))
    ax.add_patch(Rectangle((SHEET_W - BORDER - TITLE_W, BORDER), TITLE_W, SHEET_H - 2 * BORDER, fill=False, lw=1.0))
    x = SHEET_W - BORDER - TITLE_W + 0.2
    lines = [("brownfield-compute, pass 3f", 11), ("12-flat walk-up", 11), ("BID SET", 14), ("", 8),
             ("NOT FOR CONSTRUCTION", 12), ("a made-up bid set for a study,", 8), ("drawn from the bid set's IFC", 8), ("", 8),
             (f"revision: {revision or 'issued for bid'}", 9)]
    y = SHEET_H - 1.2
    for text, size in lines:
        ax.text(x, y, text, fontsize=size, va="top")
        y -= size / 72 * 1.8
    ax.text(x, 2.6, title, fontsize=13, va="top", weight="bold")
    ax.text(x, 1.6, number, fontsize=28, va="top", weight="bold")


def _cloud(ax, x0, y0, x1, y1, delta: str) -> None:
    from matplotlib.patches import FancyBboxPatch

    pad = 0.08
    ax.add_patch(FancyBboxPatch((x0 - pad, y0 - pad), x1 - x0 + 2 * pad, y1 - y0 + 2 * pad,
                                boxstyle="round,pad=0.02,rounding_size=0.12", fill=False, ec="#c00000", lw=1.2, ls=(0, (3, 2))))
    ax.text(x1 + pad + 0.05, y1 + pad, f"{DELTA}{delta}", fontsize=7, color="#c00000", va="bottom")


def _draw_elevation(ax, el: dict, x0: float, y0: float, label: str, clouded: set, removed: list, delta: str) -> None:
    """One facade. `clouded`: the (face, id) of units to cloud; `removed`: places withdrawn from
    this facade, shown dashed where they were, with a cloud."""
    from matplotlib.patches import Rectangle

    s = SCALE_IN_PER_M
    X = lambda u: x0 + u * s  # noqa: E731
    Y = lambda z: y0 + (z - el["z0"]) * s  # noqa: E731
    ax.add_patch(Rectangle((X(0), Y(el["z0"])), el["width"] * s, (el["z1"] - el["z0"]) * s, fill=False, lw=1.2))
    for r0, r1, z0, z1 in el["roofs"]:
        ax.add_patch(Rectangle((X(r0), Y(z0)), (r1 - r0) * s, (z1 - z0) * s, fill=True, fc="#888888", lw=0))
    ax.plot([X(0) - 0.5, X(el["width"]) + 0.5], [Y(0), Y(0)], color="black", lw=2)
    for z, name in el["levels"]:
        ax.plot([X(0), X(el["width"])], [Y(z), Y(z)], color="#777777", lw=0.5, ls=(0, (4, 3)))
        ax.text(X(el["width"]) + 0.15, Y(z), f"{name.upper()}  +{bidset._ftin(z)}", fontsize=7, va="center")
    for r in el["rects"]:
        ax.add_patch(Rectangle((X(r["u0"]), Y(r["z0"])), (r["u1"] - r["u0"]) * s, (r["z1"] - r["z0"]) * s,
                               fill=False, lw=0.8))
        ax.text(X((r["u0"] + r["u1"]) / 2), Y((r["z0"] + r["z1"]) / 2), r["mark"], fontsize=7, ha="center", va="center")
        if (el["face"], r["name"]) in clouded:
            _cloud(ax, X(r["u0"]), Y(r["z0"]), X(r["u1"]), Y(r["z1"]), delta)
    for p in removed:
        u0, u1, z0, z1 = p.box
        ax.add_patch(Rectangle((X(u0), Y(z0)), (u1 - u0) * s, (z1 - z0) * s, fill=False, lw=0.6, ls=(0, (2, 2))))
        ax.text(X((u0 + u1) / 2), Y((z0 + z1) / 2), f"{p.mark} REMOVED", fontsize=5, ha="center", va="center")
        _cloud(ax, X(u0), Y(z0), X(u1), Y(z1), delta)
    ax.text(x0, Y(el["z0"]) - 0.6, label, fontsize=12, weight="bold")
    ax.text(x0, Y(el["z0"]) - 0.85, "SCALE: 1/4\" = 1'-0\"", fontsize=8)


def _draw_schedule(ax, rows: list[dict], clouded: set, removed_rows: list[str], delta: str) -> None:
    """The schedule; `clouded` holds (mark, column) cells and (mark, 'row') rows to cloud, and
    `removed_rows` the marks withdrawn, shown struck through at the end, clouded."""
    x0, y = 1.5, SHEET_H - 2.5
    xs = [x0]
    for w in COLUMN_W:
        xs.append(xs[-1] + w)
    if xs[-1] > _usable_right():
        raise ValueError(f"the schedule is {xs[-1] - x0:.1f} in wide; it runs into the title block")
    needed = (len(rows) + len(removed_rows)) * ROW_H + 0.45
    if y - needed < BORDER + 0.5:
        raise ValueError(f"{len(rows) + len(removed_rows)} schedule rows don't fit on one sheet")
    ax.text(x0, y + 0.5, "WINDOW AND DOOR SCHEDULE", fontsize=14, weight="bold")
    for col, x in zip(COLUMNS, xs):
        ax.text(x + 0.05, y, col, fontsize=7, weight="bold", va="top")
    ax.plot([xs[0], xs[-1]], [y - 0.25, y - 0.25], color="black", lw=0.8)
    y -= 0.45
    for row in rows:
        for col, x, w, cell in zip(COLUMNS, xs, COLUMN_W, _schedule_cells(row)):
            ax.text(x + 0.05, y, cell, fontsize=7, va="top")
            if (row["mark"], col) in clouded:
                _cloud(ax, x, y - 0.18, x + w - 0.1, y + 0.02, delta)
        if (row["mark"], "row") in clouded:
            _cloud(ax, xs[0], y - 0.18, xs[-1] - 0.1, y + 0.02, delta)
        y -= ROW_H
    for mark in removed_rows:
        ax.text(xs[0] + 0.05, y, f"{mark}  DELETED", fontsize=7, va="top")
        ax.plot([xs[0], xs[2]], [y - 0.08, y - 0.08], color="black", lw=0.6)
        _cloud(ax, xs[0], y - 0.18, xs[-1] - 0.1, y + 0.02, delta)
        y -= ROW_H
    ax.plot([xs[0], xs[-1]], [y + 0.1, y + 0.1], color="black", lw=0.8)


def _draw_sheet(ax, rb: dict, number: str, revision: str, changes: dict) -> None:
    """One sheet, its title block and drawing, `changes` (from `compare`) clouded."""
    delta = revision.split("-")[-1] if revision else ""

    def keys(sheet, kinds):
        return {k for kind in kinds for k, *_ in changes.get(sheet, {}).get(kind, [])}

    if number == SCHEDULE:
        _title_block(ax, number, "WINDOW AND DOOR SCHEDULE", revision)
        removed_rows = [k[0] for k in keys(SCHEDULE, ["removed"]) if k[1] == "row"]
        _draw_schedule(ax, bidset.schedule_rows(rb), keys(SCHEDULE, ["changed", "added"]), sorted(removed_rows), delta)
        return
    title, faces = ELEVATIONS[number]
    _title_block(ax, number, title, revision)
    cl = keys(number, ["changed", "added"])
    gone = [a for _, a, _ in changes.get(number, {}).get("removed", [])]
    x, y = 1.5, SHEET_H - 9.5
    for face in faces:
        el = bidset.elevation(rb, face)
        if x + el["width"] * SCALE_IN_PER_M + 2.0 > _usable_right():
            raise ValueError(f"{number}: the {face} elevation runs into the title block at 1/4\" = 1'-0\"")
        _draw_elevation(ax, el, x, y, f"{face.upper()} ELEVATION", cl, [p for p in gone if p.key[0] == face], delta)
        x += el["width"] * SCALE_IN_PER_M + 3.0


def sheet_png(rb: dict, number: str, path: Path, revision: str = "", changes: dict | None = None,
              crop: tuple | None = None, dpi: int = 70) -> None:
    """One sheet as a PNG, optionally cropped to (x0, x1, y0, y1) in sheet inches, for a report."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = _figure()
    try:
        _draw_sheet(ax, rb, number, revision, changes or {})
        if crop:
            x0, x1, y0, y1 = crop
            ax.set_xlim(x0, x1)
            ax.set_ylim(y0, y1)
            fig.set_size_inches(x1 - x0, y1 - y0)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, facecolor="white")
    finally:
        plt.close(fig)


def elevation_crop(rb: dict, face: str) -> tuple:
    """The part of an elevation sheet one facade's drawing takes, with its labels and deltas (as
    `_draw_sheet` places the first facade on a sheet), for `sheet_png`."""
    el = bidset.elevation(rb, face)
    s = SCALE_IN_PER_M
    x0, y0 = 1.5, SHEET_H - 9.5
    top = max([el["z1"]] + [r[3] for r in el["roofs"]])
    return (x0 - 0.5, min(x0 + el["width"] * s + 3.0, SHEET_W - BORDER - TITLE_W),
            y0 - 1.3, min(y0 + (top - el["z0"]) * s + 0.6, SHEET_H - BORDER))


def write_set(rb: dict, path: Path, revision: str = "", changes: dict | None = None, narrative: list[str] | None = None,
              sheets: list[str] | None = None) -> list[str]:
    """The set as a PDF: an optional narrative page (an addendum), then the sheets (all if `sheets`
    is None, else those named), with `changes` (from `compare`) clouded. Returns the page names.
    No creation date, so the file carries no local time and repeats."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    changes = changes or {}
    order = [*ELEVATIONS, SCHEDULE] if sheets is None else list(sheets)
    path.parent.mkdir(parents=True, exist_ok=True)

    def page(pdf, draw):
        fig, ax = _figure()
        try:
            draw(ax)
            pdf.savefig(fig)
        finally:
            plt.close(fig)

    def narrative_page(ax):
        _title_block(ax, "ADD-1", "ADDENDUM", revision)
        y = SHEET_H - 2.0
        for line in narrative:
            ax.text(1.5, y, line, fontsize=11 if line.isupper() else 10, va="top", wrap=True,
                    weight="bold" if line.isupper() else "normal")
            y -= 0.42

    # TrueType text, so the PDF's text stays text, as a bidder's tools read it; only for these pages.
    with matplotlib.rc_context({"pdf.fonttype": 42}), PdfPages(
            path, metadata={"Title": f"walk-up bid set{(' ' + revision) if revision else ''}",
                            "Creator": "brownfield-compute pass 3f", "CreationDate": None}) as pdf:
        if narrative is not None:
            page(pdf, narrative_page)
        for number in order:
            page(pdf, lambda ax, n=number: _draw_sheet(ax, rb, n, revision, changes))
    return (["ADD-1"] if narrative is not None else []) + order


# ---- The comparison ----

DOCS = OUT_DIR.parent / "docs" / "pass3"


def publish(base: Path, rev: Path, rb0: dict, rb1: dict, r: dict, w: dict, narrative: list[str], params: dict,
            to: Path) -> list[Path]:
    """The pass report's figures and the bid set's files, for anyone to open without running
    anything, into `to` (docs/pass3), from the IFCs this run built and checked (`run` publishes
    only when every check passed):
    - the figures bidset_front.svg and bidset_addendum.png;
    - in bidset/: the IFC and its Addendum 1 revision, the IDS and its checklist on the model, the
      drawings and schedule of each, the RFI, the two PDF sets, the addendum's diff, and what the
      PDFs cost a bidder against the data."""
    import shutil

    from . import addendum

    pub = to / "bidset"
    pub.mkdir(parents=True, exist_ok=True)
    out = [pub / "apartment.ifc", pub / f"apartment-{addendum.REVISION}.ifc"]
    shutil.copyfile(base, out[0])
    shutil.copyfile(rev, out[1])
    doc = bidset.write_ids(params, pub / "bidset.ids")
    se = r["single_exit"]  # so the escape rows say how many are needed, as the report's table does
    (pub / "checklist.md").write_text(
        bidset.ids_report(bidset.run_ids(doc, base), (se["escape_needed_upper"], se["escape_needed_ground"])) + "\n",
        encoding="utf-8")
    d0 = bidset.write_drawings(base, pub / "drawings")
    d1 = bidset.write_drawings(rev, pub / f"drawings-{addendum.REVISION}")
    addendum.write_rfi(base, pub / "rfi-001.bcf", w)
    write_set(rb0, pub / "bidset.pdf")
    write_set(rb1, pub / f"{addendum.REVISION}.pdf", revision=addendum.REVISION, changes=r["diff"], narrative=narrative,
              sheets=r["revised_sheets"])
    diff_text = "\n".join(["What Addendum 1 changed, element by element (by GlobalId):",
                           *(f"  {x}" for x in addendum.diff_summary(r["data_diff"])), "",
                           "The schedule, where it moved:", *(f"  {x}" for x in r["schedule_changes"])])
    (pub / f"{addendum.REVISION}-diff.md").write_text(diff_text + "\n", encoding="utf-8")
    (pub / "conventional.md").write_text(report(r) + "\n", encoding="utf-8")
    shutil.copyfile(pub / "drawings" / "elevation_front.svg", to / "bidset_front.svg")
    sheet_png(rb1, "A-201", to / "bidset_addendum.png", revision=addendum.REVISION, changes=r["diff"],
              crop=elevation_crop(rb1, "front"))
    return [*out, pub / "bidset.ids", pub / "checklist.md", *d0["written"], *d1["written"], pub / "rfi-001.bcf",
            pub / "bidset.pdf", pub / f"{addendum.REVISION}.pdf", pub / f"{addendum.REVISION}-diff.md",
            pub / "conventional.md", to / "bidset_front.svg", to / "bidset_addendum.png"]


def run(params: dict, publish_to: Path | None = None) -> dict:
    """The bid set and Addendum 1 as PDFs, and what each costs a bidder with only the PDFs,
    against the data side.
    - The IFCs are rebuilt from forge's current model, and the revision is checked to be the base
      plus the addendum, so everything comes from one run.
    - Both IFCs are checked by both readers (`bidset.check`, `bidset.check_webifc`) and for a
      byte-for-byte repeat export.
    - With `publish_to` (docs/pass3 from the command line), the report's figures and files go
      there, but only if every check passed and the second reader ran."""
    from . import addendum

    apt0, frame = bidset.load()
    apt1, _ = bidset.load(f"apartment-{addendum.REVISION}.json")
    errs = addendum.check_revision(apt0, apt1, params)
    if errs:
        w_in = params["bidset.addendum_1.patio_door_width_in"].value
        raise SystemExit(f"out/pass3/apartment-{addendum.REVISION}.json isn't the base model with Addendum 1 ("
                         + "; ".join(errs) + f"): rerun forge `apartment-json` and `apartment-json {addendum.REVISION} {w_in:g}`")
    w = addendum.words(apt0, apt1, params)
    why = bidset.webifc_status()
    with tempfile.TemporaryDirectory() as tmp:
        base, rev = Path(tmp) / "base.ifc", Path(tmp) / "rev.ifc"
        bidset.write_ifc(apt0, frame, params, base)
        bidset.write_ifc(apt1, frame, params, rev, spec=addendum.SPEC)
        checks = []
        for label, path, apt, spec in (("base", base, apt0, None), ("Addendum 1", rev, apt1, addendum.SPEC)):
            again = Path(tmp) / f"again-{label[0]}.ifc"
            bidset.write_ifc(apt, frame, params, again, spec=spec)
            found = bidset.check(path, apt, params) + (bidset.check_webifc(path, apt, params) if why is None else [])
            found.append(("a second export is byte-for-byte the same file", again.read_bytes() == path.read_bytes(), ""))
            checks += [(f"{label}: {c}", ok, detail) for c, ok, detail in found]
        if why is not None:
            checks.append(("the second reader (web-ifc) ran", False, why))
        rb0, rb1 = bidset.read_back(base), bidset.read_back(rev)
        data = addendum.element_diff(base, rev)
        p0, p1 = places(rb0), places(rb1)
        diff = compare(p0, p1)
        revised = list(diff)
        narrative = ["ADDENDUM 1", "", *w["items"], "", f"In answer to {w['title'].split(':')[0]}.",
                     (f"Revised sheets, attached, changes clouded: {', '.join(revised)}." if revised
                      else "No sheets are revised by this addendum."),
                     "Bidders shall acknowledge receipt of this addendum on the bid form."]
        out_base = bidset.OUT / "pdf" / "bidset.pdf"
        out_add = addendum.OUT / "pdf" / "addendum-1.pdf"
        write_set(rb0, out_base)
        write_set(rb1, out_add, revision=addendum.REVISION, changes=diff, narrative=narrative, sheets=revised)
        on_elev = [p for p in p0 if p.sheet in ELEVATIONS]
        marks = sorted({p.mark for p in on_elev}, key=bidset._mark_key)
        r = {"base_pdf": out_base, "addendum_pdf": out_add,
             "tags_by_sheet": {s: sum(1 for p in on_elev if p.sheet == s) for s in ELEVATIONS},
             "tags_by_mark": {m: sum(1 for p in on_elev if p.mark == m) for m in marks},
             "schedule_rows": len(bidset.schedule_rows(rb0)), "units": len(bidset.opening_rows(rb0)),
             "diff": diff, "places_changed": count(diff),
             "revised_sheets": revised, "data_diff": data,
             "schedule_changes": addendum.schedule_changes(bidset.schedule_rows(rb0), bidset.schedule_rows(rb1)),
             "checks": checks, "publish_to": publish_to, "published": [],
             "single_exit": bidset.single_exit(apt0, params)}
        if publish_to is not None and all(ok for _, ok, _ in checks):
            r["published"] = publish(base, rev, rb0, rb1, r, w, narrative, params, publish_to)
    return r


def report(r: dict) -> str:
    d = r["data_diff"]
    units = sum(1 for v in d["changed"].values() if v["cls"] in ("IfcWindow", "IfcDoor"))
    others = len(d["changed"]) - units
    lines = ["To bid from the PDFs (bidset.pdf):",
             f"  count {sum(r['tags_by_sheet'].values())} tags by eye on {len(r['tags_by_sheet'])} elevation sheets "
             f"({', '.join(f'{s}: {n}' for s, n in r['tags_by_sheet'].items())}), tallied by mark "
             f"({', '.join(f'{m} {n}' for m, n in r['tags_by_mark'].items())}), and read the schedule's {r['schedule_rows']} rows;",
             f"  from the data: schedule.csv's {r['schedule_rows']} rows carry the counts, and openings.csv lists all "
             f"{r['units']} units, the {r['units'] - sum(r['tags_by_mark'].values())} on no elevation among them. "
             f"Nothing to count.", "",
             f"Addendum 1 from the PDFs (addendum-1.pdf: a narrative page and {len(r['revised_sheets'])} revised sheets):",
             f"  {r['places_changed']} places changed to find by eye, each clouded here:"]
    for sheet, v in r["diff"].items():
        lines.append(f"    {sheet}: {len(v['changed'])} changed, {len(v['added'])} added, {len(v['removed'])} removed")
    lines += [f"  from the data: the element diff lists {units} windows and doors"
              + (f" and {others} other elements" if others else "")
              + f", {len(d['openings_resized'])} openings and {sum(len(x) for x in d['types'].values())} types by "
              f"GlobalId, and the schedule {len(r['schedule_changes'])} changes; nothing to find.",
              "", "A lower bound: these sheets have no floor plans, sections, details, dimension strings or specifications, "
              "where the same change shows up again, and every change is clouded, which in practice they aren't always."]
    return "\n".join(lines)
