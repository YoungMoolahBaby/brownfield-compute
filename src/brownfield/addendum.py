"""Pass 3f step 5 (D27): a change to the bid set run the way a pull request is.

An RFI is the issue, Addendum 1 the change, and `brownfield addendum` the CI step:

- **The RFI** (made up): the schedule gives the patio doors no glass, though IBC 2018 2406.4.1
  makes glazing in a door a hazardous location; and the windows beside them sit inside
  2406.4.2's arc. It is written as a BCF 3.0 topic pointing at the doors by GlobalId
  (`rfi-001.bcf`), with the answer as a comment, closed.
- **Addendum 1** (made up) answers it with one data change and one size change:
  1. the patio doors' glazing is tempered (`SPEC`, written onto the patio door types);
  2. the patio doors narrow to `bidset.addendum_1.patio_door_width_in` (params), centred where
     they were, made in forge (`apartment-json addendum-1 <in>`), so the windows beside them
     clear the arc.
- **The CI step:** the revised model is checked to be the base plus exactly that, exported,
  diffed against the bid set (units, openings and types), checked by both readers and the IDS,
  and its schedule, elevations and quantities regenerated, with what changed in each listed.

The RFI's and the addendum's words are built from the model, the params and the code check, so
they can't drift from the run. ifcdiff 0.9.0 compares property sets with their entity numbers in
them and stops at the first relationship that differs, so it does only the attributes and
geometry here; type, storey and properties are compared directly.
"""

from __future__ import annotations

import re
import tempfile
import uuid
from collections import Counter
from datetime import timedelta
from pathlib import Path

import numpy as np
import ifcopenshell
import ifcopenshell.util.element

from . import bidset

REVISION = "addendum-1"
OUT = bidset.OUT / REVISION
# Item 1, as properties on every patio door type.
SPEC = {"patio_door": {"BidSet_Unit": {"SafetyGlazing": "tempered"},
                       "Pset_DoorWindowGlazingType": {"IsTempered": True}}}
AUTHORS = {"asked": "bidder@example.com", "answered": "architect@example.com"}  # roles, made up


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# ---- The revision is the base plus the addendum, and nothing else ----

def check_revision(apt0: dict, apt1: dict, params: dict) -> list[str]:
    """Why the revision isn't the base model with Addendum 1 applied (empty when it is): the same
    parts and openings, the patio doors alone at the params width, centred where they were."""
    width = params["bidset.addendum_1.patio_door_width_in"].value * bidset.IN
    errs = []
    if apt1.get("revision") != REVISION:
        errs.append(f"its revision is {apt1.get('revision')!r}, not {REVISION!r}")
    if apt0["parts"] != apt1["parts"]:
        errs.append("its walls, slabs or roof differ from the base")
    ids0, ids1 = [o["id"] for o in apt0["openings"]], [o["id"] for o in apt1["openings"]]
    if ids0 != ids1:
        errs.append("its openings aren't the base's")
        return errs
    for a, b in zip(apt0["openings"], apt1["openings"]):
        if a["kind"] == "patio_door":
            if abs(b["width_m"] - width) > 1e-6 or b["along_m"] != a["along_m"] or b["sill_m"] != a["sill_m"]:
                errs.append(f"{a['id']} isn't {width / bidset.IN:g} in wide where it was")
        elif a != b:
            errs.append(f"{a['id']} changed, and the addendum changes only the patio doors")
    return errs[:5]


# ---- The words, from the model, the params and the code check ----

def words(apt0: dict, apt1: dict, params: dict) -> dict:
    """The RFI's question, the answer and the addendum's items, from what the run finds."""
    c = "bidset.code.safety_glazing."
    arc, bottom = params[c + "door_arc_in"].value, params[c + "door_bottom_in"].value
    h0, h1 = bidset.safety_glazing(apt0, params), bidset.safety_glazing(apt1, params)
    m0, m1 = bidset.types(apt0, h0), bidset.types(apt1, h1)
    door = next(o for o in apt0["openings"] if o["kind"] == "patio_door")
    door1 = next(o for o in apt1["openings"] if o["id"] == door["id"])
    dmark = bidset.mark_of(door, m0, h0)
    beside = [o for o in apt0["openings"] if "2406.4.2" in h0.get(o["id"], "")]
    gaps = [float(g) for o in beside for g in re.findall(r"2406\.4\.2: ([0-9.]+) in", h0[o["id"]])]
    wmarks0 = sorted({bidset.mark_of(o, m0, h0) for o in beside})
    wmarks1 = sorted({bidset.mark_of(next(x for x in apt1["openings"] if x["id"] == o["id"]), m1, h1) for o in beside})
    still = sum(1 for o in beside if o["id"] in h1)
    w0, w1 = bidset._ftin(door["width_m"]), bidset._ftin(door1["width_m"])
    question = (f"The schedule gives the patio doors ({dmark}) no glass. IBC 2018 2406.4.1 makes glazing in a door a "
                f"hazardous location: tempered or laminated? And the {len(beside)} windows beside them "
                f"({', '.join(wmarks0)}) are {min(gaps):.1f} in from a door's edge, inside 2406.4.2's {arc:g} in arc with "
                f"sills under {bottom:g} in: do they take safety glazing too, or can the doors narrow?")
    answer = (f"Answered by Addendum 1. Item 1: the patio doors' glazing is tempered. Item 2: the patio doors narrow from "
              f"{w0} to {w1}, centred where they were. "
              + (f"The windows beside them then clear the {arc:g} in arc and take ordinary glazing "
                 f"(type {', '.join(sorted(set(wmarks0) - set(wmarks1)))} is withdrawn; they are {', '.join(wmarks1)})."
                 if still == 0 else f"{still} of the windows beside them still need safety glazing."))
    return {"title": f"RFI 001: what glass goes in the patio doors ({dmark})?", "question": question, "answer": answer,
            "items": [f"Item 1 (data): the patio doors ({dmark}) are glazed with tempered glass (IBC 2018 2406.4.1).",
                      f"Item 2 (size): the patio doors narrow from {w0} to {w1} wide, centred where they were."]}


# ---- The RFI as BCF ----

def write_rfi(base_ifc: Path, path: Path, w: dict) -> list[str]:
    """The RFI as a BCF 3.0 topic: the question; a viewpoint selecting every patio door by
    GlobalId, the camera in front of the building looking at it; and the answer as a comment a
    day later, the topic closed. Returns the GlobalIds it points at."""
    from bcf.v3 import model as mdl
    from bcf.v3.bcfxml import BcfXml

    f = ifcopenshell.open(str(base_ifc))
    doors = [d for d in f.by_type("IfcDoor")
             if (ifcopenshell.util.element.get_pset(d, "BF_Opening") or {}).get("Kind") == "patio_door"]
    guids = sorted(d.GlobalId for d in doors)
    ext = mdl.Extensions(topic_types=mdl.ExtensionsTopicTypes(topic_type=["Request for information"]),
                         topic_statuses=mdl.ExtensionsTopicStatuses(topic_status=["Open", "Closed"]),
                         users=mdl.ExtensionsUsers(user=sorted(AUTHORS.values())))
    bcf = BcfXml.create_new("brownfield-compute pass 3f: the walk-up's bid set", extensions=ext)
    topic = bcf.add_topic(w["title"], w["question"], AUTHORS["asked"], "Request for information", "Open")
    # The camera: in front of the front facade (x < 0), raised, looking at the building's middle.
    rb = bidset.read_back(base_ifc)
    centre = (rb["lo"] + rb["hi"]) / 2
    eye = np.array([rb["lo"][0] - 2.0 * (rb["hi"][1] - rb["lo"][1]), centre[1], rb["hi"][2] * 1.5])
    look = (centre - eye) / np.linalg.norm(centre - eye)
    up = np.cross(np.cross(look, [0.0, 0.0, 1.0]), look)
    up /= np.linalg.norm(up)
    vih = topic.add_viewpoint_from_point_and_guids(centre, *guids)
    cam = vih.visualization_info.perspective_camera
    cam.camera_view_point = mdl.Point(x=float(eye[0]), y=float(eye[1]), z=float(eye[2]))
    cam.camera_direction = mdl.Direction(x=float(look[0]), y=float(look[1]), z=float(look[2]))
    cam.camera_up_vector = mdl.Direction(x=float(up[0]), y=float(up[1]), z=float(up[2]))
    from xsdata.models.datatype import XmlDateTime

    asked = topic.topic.creation_date
    answered = XmlDateTime.from_datetime(asked.to_datetime() + timedelta(days=1))
    comments = topic.comments or []
    comments.append(mdl.Comment(guid=str(uuid.uuid4()), date=answered, author=AUTHORS["answered"], comment=w["answer"]))
    topic.comments = comments
    topic.topic.topic_status = "Closed"
    topic.topic.modified_date, topic.topic.modified_author = answered, AUTHORS["answered"]
    path.parent.mkdir(parents=True, exist_ok=True)
    bcf.save(path)
    return guids


# ---- The diff ----

def _strip_ids(x):
    """A property set as get_psets gives it, without the entity numbers ('id') in it."""
    if isinstance(x, dict):
        return {k: _strip_ids(v) for k, v in x.items() if k != "id"}
    return x


def element_diff(old: Path, new: Path) -> dict:
    """What changed, by GlobalId:
    - **units and other elements** (not openings): added, deleted, and for each changed one which
      of attributes, geometry (ifcdiff), type, storey and properties (compared here: ifcdiff stops
      at the first relationship that differs, and its properties carry entity numbers);
    - **openings** (the holes in the walls): those whose box in the world moved or resized;
    - **types**: added, deleted, and changed in name, description or properties.
    Also how many elements ifcdiff alone flags."""
    from ifcdiff import IfcDiff

    f0, f1 = ifcopenshell.open(str(old)), ifcopenshell.open(str(new))
    d = IfcDiff(f0, f1, relationships=["attributes", "geometry"], is_shallow=False)
    raw = IfcDiff(f0, f1, relationships=["attributes", "geometry", "type", "container", "property"], is_shallow=False)
    d.diff()
    raw.diff()
    changed = {g: {k.removesuffix("_changed") for k in v} for g, v in d.change_register.items()}

    def gid(x):
        return x.GlobalId if x is not None else None

    elems0 = {e.GlobalId: e for e in f0.by_type("IfcElement") if not e.is_a("IfcFeatureElement")}
    elems1 = {e.GlobalId: e for e in f1.by_type("IfcElement") if not e.is_a("IfcFeatureElement")}
    for g in elems0.keys() & elems1.keys():
        e0, e1 = elems0[g], elems1[g]
        if gid(ifcopenshell.util.element.get_type(e0)) != gid(ifcopenshell.util.element.get_type(e1)):
            changed.setdefault(g, set()).add("type")
        if gid(ifcopenshell.util.element.get_container(e0)) != gid(ifcopenshell.util.element.get_container(e1)):
            changed.setdefault(g, set()).add("storey")
        if _strip_ids(ifcopenshell.util.element.get_psets(e0)) != _strip_ids(ifcopenshell.util.element.get_psets(e1)):
            changed.setdefault(g, set()).add("properties")

    voids0 = {v.GlobalId: v for v in f0.by_type("IfcOpeningElement")}
    voids1 = {v.GlobalId: v for v in f1.by_type("IfcOpeningElement")}
    common = sorted(voids0.keys() & voids1.keys())
    b0 = bidset._world_boxes(f0, [voids0[g] for g in common])
    b1 = bidset._world_boxes(f1, [voids1[g] for g in common])
    moved = [voids0[g].Name for g in common
             if max(np.abs(b0[g][0] - b1[g][0]).max(), np.abs(b0[g][1] - b1[g][1]).max()) > 1e-6]

    def tdesc(t):
        return {"name": t.Name, "description": t.Description,
                "op": getattr(t, "OperationType", None), "psets": _strip_ids(ifcopenshell.util.element.get_psets(t))}

    t0 = {t.GlobalId: t for t in f0.by_type("IfcTypeObject")}
    t1 = {t.GlobalId: t for t in f1.by_type("IfcTypeObject")}
    types = {"added": sorted(f"{t1[g].Name} ({t1[g].Description})" for g in t1.keys() - t0.keys()),
             "deleted": sorted(f"{t0[g].Name} ({t0[g].Description})" for g in t0.keys() - t1.keys()),
             "changed": sorted(t0[g].Name for g in t0.keys() & t1.keys() if tdesc(t0[g]) != tdesc(t1[g]))}
    return {"added": sorted(elems1.keys() - elems0.keys()), "deleted": sorted(elems0.keys() - elems1.keys()),
            "changed": {g: {"name": elems0[g].Name, "cls": elems0[g].is_a(), "changes": sorted(v)}
                        for g, v in sorted(changed.items(), key=lambda kv: elems0[kv[0]].Name or kv[0])},
            "openings_resized": sorted(moved), "types": types, "ifcdiff_flagged": len(raw.change_register)}


def diff_summary(diff: dict) -> list[str]:
    """The diff in a few lines: elements by class and how they changed, openings, types."""
    groups = Counter((v["cls"], ", ".join(v["changes"])) for v in diff["changed"].values())
    lines = [f"{_plural(n, cls.removeprefix('Ifc').lower())}: {how}" for (cls, how), n in sorted(groups.items())]
    lines.append(f"{_plural(len(diff['openings_resized']), 'opening')} in the walls resized or moved")
    t = diff["types"]
    lines += [f"type withdrawn: {x}" for x in t["deleted"]] + [f"type new: {x}" for x in t["added"]]
    lines += [f"type changed: {x}" for x in t["changed"]]
    lines.append(f"{len(diff['added'])} elements added, {len(diff['deleted'])} deleted, {len(diff['changed'])} changed; "
                 f"no other element, opening or type changed (ifcdiff alone flags {diff['ifcdiff_flagged']}: the rest "
                 "only because entity numbers moved)")
    return lines


def schedule_changes(old: list[dict], new: list[dict]) -> list[str]:
    """What changed in the schedule. Types are matched on what they are (kind, size, safety
    glazing), since marks are numbered by position; a type matched that way under another mark
    is reported as renumbered, and a mark left on each side with no match is taken as resized."""
    def key(r):
        return (r["kind"], str(r["width_mm"]), str(r["height_mm"]), r["safety_glazing_required"] != "no")

    ok, nk = {key(r): r for r in old}, {key(r): r for r in new}
    pairs = [(ok[k], nk[k]) for k in ok if k in nk]
    left_o = [ok[k] for k in ok if k not in nk]
    left_n = {nk[k]["mark"]: nk[k] for k in nk if k not in ok}
    for r in list(left_o):
        if r["mark"] in left_n:
            pairs.append((r, left_n.pop(r["mark"])))
            left_o.remove(r)
    lines = [f"{r['mark']}: withdrawn ({_plural(r['count'], r['kind'])})" for r in left_o]
    lines += [f"{r['mark']}: new ({_plural(r['count'], r['kind'])})" for r in left_n.values()]
    for a, b in pairs:
        if a["mark"] != b["mark"]:
            lines.append(f"{a['mark']} renumbered {b['mark']}")
        for col in dict.fromkeys([*a, *b]):
            if col != "mark" and str(a.get(col)) != str(b.get(col)):
                lines.append(f"{b['mark']} {col}: {a.get(col, '(none)')} -> {b.get(col, '(none)')}")
    return lines


# ---- The CI step ----

def run(params: dict) -> dict:
    """The bid set as it stands, Addendum 1 applied, the RFI, the diff, both readers and the IDS
    on the revision, and the drawings regenerated, with what changed. Written to `OUT`, base
    copy included; the main bid set's files are left alone."""
    apt0, frame = bidset.load()
    apt1, _ = bidset.load(f"apartment-{REVISION}.json")
    width_in = params["bidset.addendum_1.patio_door_width_in"].value
    errs = check_revision(apt0, apt1, params)
    if errs:
        raise SystemExit(f"out/pass3/apartment-{REVISION}.json isn't the base model with Addendum 1 ("
                         + "; ".join(errs) + f"): rerun forge `cargo run --release -- apartment-json` and "
                         f"`cargo run --release -- apartment-json {REVISION} {width_in:g}`")
    w = words(apt0, apt1, params)
    base, rev = OUT / "base.ifc", OUT / "apartment.ifc"
    bidset.write_ifc(apt0, frame, params, base)
    bidset.write_ifc(apt1, frame, params, rev, spec=SPEC)
    guids = write_rfi(base, OUT / "rfi-001.bcf", w)
    diff = element_diff(base, rev)

    checks = bidset.check(rev, apt1, params)
    with tempfile.TemporaryDirectory() as tmp:
        again = Path(tmp) / "apartment.ifc"
        bidset.write_ifc(apt1, frame, params, again, spec=SPEC)
        checks.append(("a second export is the same file (header aside)", bidset.body_text(again) == bidset.body_text(rev),
                       f"{len(bidset.body_text(rev)):,} lines"))
    why = bidset.webifc_status()
    second = bidset.check_webifc(rev, apt1, params) if why is None else []
    doc = bidset.write_ids(params, OUT / "bidset.ids")
    ids0, ids1 = bidset.run_ids(doc, base), bidset.run_ids(doc, rev)
    ids_changes = [f"{b['name']}: {a['passed']} of {a['applicable']} -> {b['passed']} of {b['applicable']}"
                   for a, b in zip(ids0, ids1) if (a["passed"], a["applicable"]) != (b["passed"], b["applicable"])]
    with tempfile.TemporaryDirectory() as tmp:
        d0 = bidset.write_drawings(base, Path(tmp))
    d1 = bidset.write_drawings(rev, OUT / "drawings")
    h0, h1 = bidset.safety_glazing(apt0, params), bidset.safety_glazing(apt1, params)
    return {"words": w, "rfi_guids": guids, "diff": diff, "checks": checks, "second": second, "second_status": why,
            "ids_changes": ids_changes, "schedule_changes": schedule_changes(d0["schedule"], d1["schedule"]),
            "hazards": (len(h0), len(h1)), "quantities": (d0["quantities"]["total"], d1["quantities"]["total"]),
            "base": base, "rev": rev, "written": [OUT / "rfi-001.bcf", OUT / "bidset.ids", base, rev, *d1["written"]]}


def report(r: dict) -> str:
    """Addendum 1 as a reviewed change, in plain text."""
    w, (q0, q1) = r["words"], r["quantities"]
    second = (r["second"] if r["second_status"] is None else
              [("the second reader (web-ifc) ran", False, f"it didn't: {r['second_status']}")])
    lines = [w["title"], f"  asked: {w['question']}", f"  points at {_plural(len(r['rfi_guids']), 'patio door')} by GlobalId",
             f"  answered: {w['answer']}", "", "Addendum 1:", *(f"  {i}" for i in w["items"]), "",
             "What changed:", *(f"  {x}" for x in diff_summary(r["diff"])), "",
             "Checks on the revision:", *(f"  {x}" for x in bidset.report(r["checks"] + second).splitlines()), "",
             f"Safety glazing (IBC 2018 2406.4.1-2406.4.3): {r['hazards'][0]} -> {r['hazards'][1]} openings.", "",
             "The checklist (IDS), where it moved:", *(f"  {x}" for x in r["ids_changes"]), "",
             "The schedule, where it moved:", *(f"  {x}" for x in r["schedule_changes"]), "",
             f"Openings in the exterior walls: {q0['openings_m2']:.1f} -> {q1['openings_m2']:.1f} m2 "
             f"({q0['openings_m2'] / bidset.FT2:,.0f} -> {q1['openings_m2'] / bidset.FT2:,.0f} ft2)."]
    return "\n".join(lines)
