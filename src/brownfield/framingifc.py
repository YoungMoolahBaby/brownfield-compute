"""The walk-up's wood frame as IFC (D29): the plan room's framing model and the viewer's framing layer.

Forge `framing-json` builds pass 3b's frame (out/pass3/frame.json, `brownfield frame`'s sizes) on a
revision's building and writes every member as boxes (out/pass3/framing-members-<revision>.json).
This writes them as an IFC4 model of their own, beside the bid set's (same storeys, same origin):

- studs, king and jack studs, cripples, plates and sills as IfcMember (STUD, PLATE);
- headers as IfcBeam (LINTEL), floor and roof joists and rim boards as IfcBeam (JOIST, BEAM);
- footings and stem walls as IfcFooting, the slab as IfcSlab (BASESLAB).

Each member carries what it is (BF_Member: kind, nominal size, storey). Forge's storey 0 (the
foundation) is placed on Level 1; floor and roof framing on top of a storey is in that storey, as
forge has it. `check` reads the file back: every member once, each where forge has it (to 1 mm),
schema valid.

Not in it: the flats' partitions and plumbing walls, and the service annex, which pass 3b's frame
doesn't have (D28 step 7 frames them).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import ifcopenshell
import ifcopenshell.api.aggregate as aggregate
import ifcopenshell.api.context as context
import ifcopenshell.api.project as project
import ifcopenshell.api.pset as pset
import ifcopenshell.api.spatial as spatial
import ifcopenshell.api.unit as unit
import ifcopenshell.validate

from . import OUT_DIR, bidset

# Forge's member kinds: (IFC class, predefined type).
CLASSES = {
    "studs": ("IfcMember", "STUD"), "king studs": ("IfcMember", "STUD"), "jack studs": ("IfcMember", "STUD"),
    "cripples": ("IfcMember", "STUD"), "plates": ("IfcMember", "PLATE"), "cap plates": ("IfcMember", "PLATE"),
    "rough sills": ("IfcMember", "PLATE"), "headers (plies)": ("IfcBeam", "LINTEL"), "rim boards": ("IfcBeam", "BEAM"),
    "floor joists": ("IfcBeam", "JOIST"), "roof joists": ("IfcBeam", "JOIST"), "footings": ("IfcFooting", "STRIP_FOOTING"),
    "stem walls": ("IfcFooting", "STRIP_FOOTING"), "slab": ("IfcSlab", "BASESLAB"),
}


def load(revision: str) -> dict:
    path = OUT_DIR / "pass3" / f"framing-members-{revision}.json"
    if not path.exists():
        raise SystemExit(f"no {path.relative_to(OUT_DIR.parent)}: run forge's `framing-json {revision} ...` first")
    return json.loads(path.read_text(encoding="utf-8"))


def write(frame: dict, path: Path) -> ifcopenshell.file:
    """The frame as IFC4, a file of its own (GlobalIds from each member's id; a fixed header time)."""
    rev = frame["revision"]
    f = project.create_file("IFC4")
    f.header.file_name.time_stamp = bidset.HEADER_TIME
    proj = bidset._make(f, "IfcProject", f"frame/{rev}/project", f"brownfield-compute: the walk-up's wood frame ({rev})")
    unit.assign_unit(f, units=[unit.add_si_unit(f, unit_type=t) for t in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT", "PLANEANGLEUNIT")])
    model = context.add_context(f, context_type="Model")
    body = context.add_context(f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)
    site = bidset._make(f, "IfcSite", f"frame/{rev}/site", "the walk-up's site (not georeferenced)")
    bldg = bidset._make(f, "IfcBuilding", f"frame/{rev}/building", "12-flat walk-up: its wood frame", Description=frame["source"])
    aggregate.assign_object(f, products=[site], relating_object=proj)
    aggregate.assign_object(f, products=[bldg], relating_object=site)
    import ifcopenshell.api.geometry as geometry

    geometry.edit_object_placement(f, product=site)
    geometry.edit_object_placement(f, product=bldg)
    storeys = {}
    levels = sorted({max(m["storey"], 1) for m in frame["members"]})
    for k in levels:
        s = bidset._make(f, "IfcBuildingStorey", f"frame/{rev}/storey/{k}", f"Level {k}")
        aggregate.assign_object(f, products=[s], relating_object=bldg)
        geometry.edit_object_placement(f, product=s)
        storeys[k] = s
    for mb in frame["members"]:
        cls, pre = CLASSES[mb["kind"]]
        e = bidset._make(f, cls, f"frame/{rev}/{mb['id']}", mb["id"], PredefinedType=pre)
        spatial.assign_container(f, products=[e], relating_structure=storeys[max(mb["storey"], 1)])
        bidset._place_boxes(f, body, e, [(lo, hi) for lo, hi in mb["boxes"]])
        ps = pset.add_pset(f, product=e, name="BF_Member")
        props = {"Id": mb["id"], "Kind": mb["kind"], "Storey": mb["storey"]}
        if mb["nominal"]:
            props["Nominal"] = mb["nominal"]
        pset.edit_pset(f, pset=ps, properties=props)
    bidset._derive_gids(f)
    bidset._sort_sets(f)
    path.parent.mkdir(parents=True, exist_ok=True)
    f.write(str(path))
    return f


def check(path: Path, frame: dict) -> list[tuple[str, bool, str]]:
    """Read the frame back: every member once and nothing else, each where forge has it (its boxes'
    extent, to 1 mm), and IfcOpenShell's schema validation."""
    f = ifcopenshell.open(str(path))
    want = {m["id"]: m for m in frame["members"]}
    got = [e for c in ("IfcMember", "IfcBeam", "IfcFooting", "IfcSlab") for e in f.by_type(c)]
    names = Counter(e.Name for e in got)
    res = [("every member of forge's frame once, and nothing else", set(names) == set(want) and all(n == 1 for n in names.values()),
            f"{len(got)} in the file, {len(want)} in forge's frame")]
    boxes = bidset._world_boxes(f, [e for e in got if e.Name in want])
    worst = 0.0
    for e in got:
        if e.Name not in want:
            continue
        b = np.array(want[e.Name]["boxes"], float)
        lo, hi = b[:, 0].min(0), b[:, 1].max(0)
        worst = max(worst, float(np.abs(boxes[e.GlobalId][0] - lo).max()), float(np.abs(boxes[e.GlobalId][1] - hi).max()))
    res.append(("every member where forge has it (to 1 mm)", worst < 1e-3, f"worst {worst * 1e3:.4f} mm"))
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, log, express_rules=True)
    res.append(("schema validation (with express rules)", not log.statements, f"{len(log.statements)} issues"))
    return res
