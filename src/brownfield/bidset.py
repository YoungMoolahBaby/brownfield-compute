"""Pass 3f (D27): the walk-up as a bid set, written as data.

`brownfield bidset` reads forge's model of the walk-up (out/pass3/apartment.json, from
`cargo run --release -- apartment-json` in forge/) and its frame (out/pass3/frame.json, from
`brownfield frame`), and writes it as IFC4 (ISO 16739-1:2018), `out/pass3/bidset/apartment.ifc`:

- the site, the building, three storeys;
- every wall a storey at a time (exterior, spine and stair), the ground slab, the floor systems
  and the roof, each a box as forge has it, with wall types from the frame's stud schedule;
- every window and door, typed (W1, D1, D2), in an opening that voids its wall, with its U-factor
  (the number the heat model uses), a MasterFormat section, and its id, flat, face and sill height.

GlobalIds come from the stable ids forge gives every part and opening, so writing the same model
twice gives the same file (the header's timestamp aside), and a changed model differs only where
it changed. Then `check` reads the file back and holds it to forge's model (see `check`).
"""

from __future__ import annotations

import json
import math
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import ifcopenshell
import ifcopenshell.api.aggregate as aggregate
import ifcopenshell.api.classification as classification
import ifcopenshell.api.context as context
import ifcopenshell.api.feature as feature
import ifcopenshell.api.geometry as geometry
import ifcopenshell.api.project as project
import ifcopenshell.api.pset as pset
import ifcopenshell.api.root as root
import ifcopenshell.api.spatial as spatial
import ifcopenshell.api.type as itype
import ifcopenshell.api.unit as unit
import ifcopenshell.geom
import ifcopenshell.guid
import ifcopenshell.util.classification
import ifcopenshell.util.element
import ifcopenshell.validate

from . import OUT_DIR
from .house import BTU_FT2

OUT = OUT_DIR / "pass3" / "bidset"
# Fixed for this project, so every GlobalId is the same from one export to the next.
NAMESPACE = uuid.UUID("dc59612f-bccb-4cb2-84de-d82f843790d2")
IN = 0.0254

# The order types are numbered in (W1..., then D1, D2...).
KINDS = ("window", "patio_door", "entry_door")
# CSI MasterFormat 2020, Division 08 Openings. Level 2 where it doesn't presume what the model
# doesn't know: a window's level-3 section (08 51 aluminum, 08 52 wood, 08 53 plastic, 08 54
# composite) is its frame material; a patio door is 08 10 00 if it swings, 08 32 00 (sliding glass
# doors) if it slides, so it gets only the division until its operation is chosen.
MASTERFORMAT = {
    "window": ("08 50 00", "Windows"),
    "patio_door": ("08 00 00", "Openings"),
    "entry_door": ("08 10 00", "Doors and Frames"),
}
# Written into each reference, so the file says these are our choice, not a specifier's.
MASTERFORMAT_WHY = {
    "window": "judgement (brownfield-compute pass 3f): level 2 until the frame material is chosen",
    "patio_door": "judgement (brownfield-compute pass 3f): the division only, until it is chosen to swing (08 10 00) or slide (08 32 00)",
    "entry_door": "judgement (brownfield-compute pass 3f): level 2 until the door and frame material are chosen",
}
# The U-factor each kind takes from params/pass3.yaml: glazed units are fenestration.
U_PARAM = {"window": "pass3.envelope.window_u", "patio_door": "pass3.envelope.window_u",
           "entry_door": "pass3.envelope.door_u"}
NAMES = {"window": "Window", "patio_door": "Patio door", "entry_door": "Entry door"}


def gid(key: str) -> str:
    return ifcopenshell.guid.compress(uuid.uuid5(NAMESPACE, key).hex)


def read_json(name: str, how: str) -> dict:
    path = OUT_DIR / "pass3" / name
    if not path.exists():
        raise SystemExit(f"no out/pass3/{name}: {how} first")
    return json.loads(path.read_text(encoding="utf-8"))


def load() -> tuple[dict, dict]:
    apt = read_json("apartment.json", "run `cargo run --release -- apartment-json` in forge/")
    ops, parts = apt.get("openings") or [{}], {pt["id"] for pt in apt.get("parts", [])}
    # The shape this module reads: openings with their panels, each in its own storey's wall.
    if "panel_lo_m" not in ops[0] or ops[0].get("wall") not in parts:
        raise SystemExit("out/pass3/apartment.json is from an older forge: rerun `cargo run --release -- apartment-json` in forge/")
    return apt, read_json("frame.json", "run `uv run brownfield frame`")


def types(apt: dict, hazards=()) -> dict[tuple, str]:
    """Type marks by (kind, width, height, safety glazing): windows W1, W2... by size and then
    by safety glazing, then doors D1, D2... by kind (patio, entry), size and the same. A unit the
    code says must be safety glazed (`hazards`, from `safety_glazing`) is its own type, so a
    schedule priced by type can't miss it."""
    sizes = sorted({(KINDS.index(o["kind"]), o["width_m"], o["height_m"], o["id"] in hazards) for o in apt["openings"]})
    marks, n = {}, Counter()
    for k, w, h, safe in sizes:
        letter = "W" if KINDS[k] == "window" else "D"
        n[letter] += 1
        marks[(KINDS[k], w, h, safe)] = f"{letter}{n[letter]}"
    return marks


def mark_of(o: dict, marks: dict, hazards=()) -> str:
    return marks[(o["kind"], o["width_m"], o["height_m"], o["id"] in hazards)]


def _inches(mm: float) -> str:
    return f"{mm / 25.4:g}"


def wall_types(frame: dict) -> dict[str, dict]:
    """The wall types (one per distinct framing) and which walls take them: {part id prefix and
    storey: type}. From the stud schedule `brownfield frame` sized (pass 3b): facades and end walls
    one row of exterior studs; the spine two rows (a double-stud party wall); the stair walls two
    rows of 2x4 at the frame's spacing (forge `framing`)."""
    by_wall, kinds = {}, {}
    for storey, s in frame["studs"].items():
        ext, spine = s["exterior"], s["spine_row"]
        for prefix, (kind, size, spacing, rows) in {
            "ext": ("exterior", ext["size"], ext["spacing_mm"], 1),
            "spine": ("party", spine["size"], spine["spacing_mm"], 2),
            "stair": ("stair", frame.get("stair_stud", "2x4"), frame["spacing_mm"], 2),  # forge's default too
        }.items():
            name = f"{kind} wall, {'double ' if rows == 2 else ''}{size} wood studs at {_inches(spacing)} in."
            kinds.setdefault(name, {"name": name, "kind": kind, "size": size, "spacing_mm": spacing, "rows": rows})
            by_wall[(prefix, int(storey))] = name
    return {"types": kinds, "by_wall": by_wall}


# ---- Writing the IFC ----

def _box_rep(f, ctx, dx: float, dy: float, dz: float):
    """A box from the local origin, dx by dy by dz (m): a rectangle extruded up."""
    prof = f.createIfcRectangleProfileDef(
        "AREA", None, f.createIfcAxis2Placement2D(f.createIfcCartesianPoint((dx / 2, dy / 2)), None), dx, dy)
    solid = f.createIfcExtrudedAreaSolid(
        prof, f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0.0, 0.0, 0.0)), None, None),
        f.createIfcDirection((0.0, 0.0, 1.0)), dz)
    return f.createIfcShapeRepresentation(ctx, "Body", "SweptSolid", [solid])


def _face_axes(outward) -> np.ndarray:
    """An opening's local axes: x along the face, left to right as seen from outside; y into the
    building; z up (right-handed: x = y cross z)."""
    y = -np.asarray(outward, float)
    z = np.array([0.0, 0.0, 1.0])
    return np.array([np.cross(y, z), y, z])


def _place_box(f, ctx, product, lo, hi, axes=np.eye(3)) -> None:
    """Place a product at the box lo..hi (m, world), its local axes `axes` (rows: x, y, z)."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    dims = [abs(float((hi - lo) @ a)) for a in axes]
    origin = (lo + hi) / 2 - sum(a * d / 2 for a, d in zip(axes, dims))
    m = np.eye(4)
    m[:3, :3] = axes.T
    m[:3, 3] = origin
    geometry.edit_object_placement(f, product=product, matrix=m, is_si=True)
    geometry.assign_representation(f, product=product, representation=_box_rep(f, ctx, *dims))


def _make(f, cls: str, key: str, name: str | None = None, **attrs):
    e = root.create_entity(f, cls, name=name or key)
    e.GlobalId = gid(key)
    for k, v in attrs.items():
        setattr(e, k, v)
    return e


def _derive_gids(f) -> None:
    """Property sets and relationships get random GlobalIds from the API: derive each from what
    it joins, so they are as stable as the elements. A relationship is keyed on its relating side,
    plus the related element when there is only one (a void, a filling): so a storey's containment
    or a type's occurrences keep their GlobalId when an addendum adds or removes a window."""
    for ps in f.by_type("IfcPropertySet"):
        owner = next((r.RelatedObjects[0].GlobalId for r in f.get_inverse(ps) if r.is_a("IfcRelDefinesByProperties")), None)
        if owner is None:
            owner = next(t.GlobalId for t in f.by_type("IfcTypeObject") if ps in (t.HasPropertySets or ()))
        ps.GlobalId = gid(f"pset/{owner}/{ps.Name}")
    for rel in f.by_type("IfcRelationship"):
        key = []
        for name, v in rel.get_info(recursive=False).items():
            if not isinstance(v, ifcopenshell.entity_instance):
                continue  # attributes, and one-to-many related sets
            if v.is_a("IfcRoot"):
                key.append(f"{name}={v.GlobalId}")
            elif name.startswith("Relating"):  # e.g. a classification reference
                key.append(f"{name}={v.is_a()}:{getattr(v, 'Identification', None) or v.id()}")
        rel.GlobalId = gid(f"rel/{rel.is_a()}/{'/'.join(key)}")


def _sort_sets(f) -> None:
    """IFC SETs (a relationship's related objects, the unit assignment) have no order, and the API
    writes them in one that changes from run to run: sort each by GlobalId, or by entity number
    (which follows the order things were made in, and so is the same every run)."""
    def key(x):
        return (0, x.GlobalId, 0) if x.is_a("IfcRoot") else (1, "", x.id())

    schema = ifcopenshell.ifcopenshell_wrapper.schema_by_name(f.schema)
    for e in f:
        decl = schema.declaration_by_name(e.is_a())
        for i, attr in enumerate(decl.all_attributes()):
            agg = attr.type_of_attribute().as_aggregation_type()
            v = e[i]
            if (agg and agg.type_of_aggregation_string() == "set" and isinstance(v, tuple) and len(v) > 1
                    and all(isinstance(x, ifcopenshell.entity_instance) for x in v)):
                e[i] = tuple(sorted(v, key=key))


def _note_source(ps, prop: str, param) -> None:
    """Say where a property's number comes from, in the property's own Description: the params
    name, its confidence and its source (so a placeholder reads as one in the file)."""
    for q in ps.HasProperties:
        if q.Name == prop:
            q.Description = f"params {param.name} ({param.conf}): {param.value:g} {param.unit}; {param.source}"


def write_ifc(apt: dict, frame: dict, params: dict, path: Path) -> ifcopenshell.file:
    """params: `load_params()`'s Param objects, so each number can carry its source."""
    f = project.create_file("IFC4")
    proj = _make(f, "IfcProject", "project", "brownfield-compute pass 3f: the walk-up's bid set")
    si = {t: unit.add_si_unit(f, unit_type=t) for t in
          ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT", "PLANEANGLEUNIT", "POWERUNIT", "THERMODYNAMICTEMPERATUREUNIT")}
    u_unit = unit.add_derived_unit(f, unit_type="THERMALTRANSMITTANCEUNIT", userdefinedtype=None,
                                   attributes={si["POWERUNIT"]: 1, si["LENGTHUNIT"]: -2, si["THERMODYNAMICTEMPERATUREUNIT"]: -1})
    unit.assign_unit(f, units=[*si.values(), u_unit])
    model = context.add_context(f, context_type="Model")
    body = context.add_context(f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)

    site = _make(f, "IfcSite", "site", "the walk-up's site (not georeferenced)")
    bldg = _make(f, "IfcBuilding", "building", "12-flat walk-up",
                 Description=apt["source"])
    aggregate.assign_object(f, products=[site], relating_object=proj)
    aggregate.assign_object(f, products=[bldg], relating_object=site)
    geometry.edit_object_placement(f, product=site)
    geometry.edit_object_placement(f, product=bldg)
    storeys = {}
    for lv in apt["levels"]:
        k = lv["storey"]
        s = _make(f, "IfcBuildingStorey", f"storey/{k}", f"Level {k}", Elevation=lv["elevation_m"])
        aggregate.assign_object(f, products=[s], relating_object=bldg)
        m = np.eye(4)
        m[2, 3] = lv["elevation_m"]
        geometry.edit_object_placement(f, product=s, matrix=m, is_si=True)
        storeys[k] = s

    mf = classification.add_classification(f, classification="MasterFormat")
    mf.Edition, mf.Source = "2020", "Construction Specifications Institute"

    # Wall types, then walls, slabs and the roof.
    wt = wall_types(frame)
    wall_type = {}
    for name, t in wt["types"].items():
        e = _make(f, "IfcWallType", f"walltype/{name}", name, PredefinedType="STANDARD",
                  Description=f"{t['rows']} row{'s' if t['rows'] > 1 else ''} of {t['size']} studs at "
                              f"{t['spacing_mm']:.1f} mm (brownfield frame, pass 3b)")
        # What a window or door installer needs to know about the wall it goes in (pass 3f step 3).
        ps = pset.add_pset(f, product=e, name="BidSet_Wall")
        pset.edit_pset(f, pset=ps, properties={"Construction": name})
        wall_type[name] = e
    walls = {}
    for part in apt["parts"]:
        k = part["storey"]
        if part["kind"].endswith("_wall"):
            prefix = part["id"].split("-")[0]
            external = part["kind"] == "exterior_wall"
            e = _make(f, "IfcWall", f"part/{part['id']}", part["id"], PredefinedType="STANDARD")
            itype.assign_type(f, related_objects=[e], relating_type=wall_type[wt["by_wall"][(prefix, k)]],
                              should_map_representations=False)
            face = part["id"].split("-")[1]
            # As forge `framing` builds it: the facades and the spine bear the floors and the roof;
            # the stair walls bear the roof over the stair (its joists span between them), and the
            # stair walls below carry those above; the end walls bear neither.
            bearing = (external and face in ("front", "back")) or prefix in ("spine", "stair")
            ps = pset.add_pset(f, product=e, name="Pset_WallCommon")
            pset.edit_pset(f, pset=ps, properties={"IsExternal": external, "LoadBearing": bearing})
            walls[part["id"]] = e
        else:
            predefined = {"ground_slab": "BASESLAB", "floor": "FLOOR", "roof": "ROOF"}[part["kind"]]
            e = _make(f, "IfcSlab", f"part/{part['id']}", part["id"], PredefinedType=predefined)
            ps = pset.add_pset(f, product=e, name="Pset_SlabCommon")
            pset.edit_pset(f, pset=ps, properties={"IsExternal": part["kind"] != "floor",
                                                   "LoadBearing": True})
        spatial.assign_container(f, products=[e], relating_structure=storeys[k])
        _place_box(f, body, e, part["lo_m"], part["hi_m"])

    # Window and door types: by size, and by whether the code calls for safety glazing.
    hazards = safety_glazing(apt, params)
    marks = types(apt, hazards)
    type_of = {}
    for (kind, w, h, safe), mark in sorted(marks.items(), key=lambda kv: kv[1]):
        cls = "IfcWindowType" if kind == "window" else "IfcDoorType"
        attrs = {"PredefinedType": "WINDOW" if kind == "window" else "DOOR"}
        e = _make(f, cls, f"type/{mark}", mark, **attrs,
                  Description=f"{NAMES[kind]}, {w / IN:g} x {h / IN:g} in."
                              + (" Safety glazing: IBC 2018 2406.4.1-2406.4.3 call for it here." if safe else ""))
        ps = pset.add_pset(f, product=e, name="Pset_WindowCommon" if kind == "window" else "Pset_DoorCommon")
        u = params[U_PARAM[kind]]
        pset.edit_pset(f, pset=ps, properties={"Reference": mark, "IsExternal": True,
                                               "ThermalTransmittance": u.value * BTU_FT2})
        _note_source(ps, "ThermalTransmittance", u)
        code, title = MASTERFORMAT[kind]
        ref = classification.add_reference(f, products=[e], identification=code, name=title, classification=mf)
        ref.Description = MASTERFORMAT_WHY[kind]
        type_of[mark] = e

    # Every opening: the void in its wall, and the window or door that fills it.
    for o in apt["openings"]:
        axes = _face_axes(o["outward"])
        mark = mark_of(o, marks, hazards)
        void = _make(f, "IfcOpeningElement", f"opening/{o['id']}", o["id"], PredefinedType="OPENING")
        feature.add_feature(f, feature=void, element=walls[o["wall"]])
        _place_box(f, body, void, o["lo_m"], o["hi_m"], axes)
        window = o["kind"] == "window"
        e = _make(f, "IfcWindow" if window else "IfcDoor", f"element/{o['id']}", o["id"], Tag=o["id"],
                  PredefinedType="WINDOW" if window else "DOOR",
                  OverallWidth=o["width_m"], OverallHeight=o["height_m"])
        spatial.assign_container(f, products=[e], relating_structure=storeys[o["storey"]])
        feature.add_filling(f, opening=void, element=e)
        itype.assign_type(f, related_objects=[e], relating_type=type_of[mark], should_map_representations=False)
        _place_box(f, body, e, o["panel_lo_m"], o["panel_hi_m"], axes)
        ps = pset.add_pset(f, product=e, name="BF_Opening")
        pset.edit_pset(f, pset=ps, properties={
            "Id": o["id"], "Kind": o["kind"], "Glazed": o["glazed"], "Flat": o["flat"] or f"{o['storey']}-stair",
            "Face": o["face"], "Index": o["index"],
            # Typed as a length, so it carries the project's metre.
            "SillHeightAboveFloor": f.createIfcLengthMeasure(o["sill_above_floor_m"]),
            # Our reading of IBC 2018 2406.4.1-2406.4.3 from the geometry (`safety_glazing`).
            "SafetyGlazingRequired": o["id"] in hazards,
            "SafetyGlazingReason": hazards.get(o["id"], NO_HAZARD)})

    _derive_gids(f)
    _sort_sets(f)
    path.parent.mkdir(parents=True, exist_ok=True)
    f.write(str(path))
    return f


# ---- Reading it back ----

def _world_boxes(f, elements) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Each element's world bounding box (m) from IfcOpenShell's own geometry, openings not cut
    (so a wall reads as its whole box)."""
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    s.set("disable-opening-subtractions", True)
    out = {}
    for e in elements:
        v = np.array(ifcopenshell.geom.create_shape(s, e).geometry.verts).reshape(-1, 3)
        out[e.GlobalId] = (v.min(0), v.max(0))
    return out


def _overlap(a, b) -> float:
    return float(np.prod(np.clip(np.minimum(a[1], b[1]) - np.maximum(a[0], b[0]), 0.0, None)))


def body_text(path: Path) -> list[str]:
    """The file's entities, without the header (whose timestamp changes every export)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[lines.index("DATA;"):]


def check(path: Path, apt: dict, params: dict) -> list[tuple[str, bool, str]]:
    """Read the IFC back and hold it to forge's model: every part, opening and unit there and
    nothing else, counts and types, sizes, every element where forge has it (to 1 mm), no clashes,
    glazing per flat against pass 3b, unique GlobalIds, and IfcOpenShell's schema validation with
    the express rules. A mismatch is reported as a failure, not raised."""
    f = ifcopenshell.open(str(path))
    res = []
    ops = {o["id"]: o for o in apt["openings"]}
    parts = {pt["id"]: pt for pt in apt["parts"]}
    hazards = safety_glazing(apt, params)
    marks = types(apt, hazards)
    fills = f.by_type("IfcWindow") + f.by_type("IfcDoor")
    built = f.by_type("IfcWall") + f.by_type("IfcSlab")
    voids = f.by_type("IfcOpeningElement")

    def same(label, got, want):
        names = Counter(e.Name for e in got)
        missing, extra = sorted(set(want) - set(names)), sorted(set(names) - set(want))
        twice = sorted(n for n, c in names.items() if c > 1)
        detail = f"{len(got)} in the file, {len(want)} in forge's model"
        for what, v in (("missing", missing), ("not in forge's model", extra), ("twice", twice)):
            if v:
                detail += f"; {len(v)} {what}, first {v[0]}"
        res.append((label, not (missing or extra or twice), detail))

    same("every wall, slab and roof of forge's model, once, and nothing else", built, parts)
    same("every opening, once, and nothing else", voids, ops)
    same("every window and door, once, and nothing else", fills, ops)
    built = [e for e in built if e.Name in parts]
    voids = [e for e in voids if e.Name in ops]
    fills = [e for e in fills if e.Name in ops]

    def type_name(e):
        t = ifcopenshell.util.element.get_type(e)
        return t.Name if t else None

    got = Counter(type_name(e) for e in fills)
    want = Counter(mark_of(o, marks, hazards) for o in ops.values())
    res.append(("windows and doors by type", got == want, ", ".join(f"{k} {v}" for k, v in sorted(got.items(), key=str))))
    bad = [e.Name for e in fills if abs(e.OverallWidth - ops[e.Name]["width_m"]) > 1e-9
           or abs(e.OverallHeight - ops[e.Name]["height_m"]) > 1e-9]
    res.append(("sizes exact", not bad, f"{len(fills) - len(bad)} of {len(fills)}"))

    tol = 1e-3
    boxes = _world_boxes(f, built + fills + voids)

    def off(e, lo, hi) -> float:
        got = boxes[e.GlobalId]
        return max(float(np.abs(got[0] - lo).max()), float(np.abs(got[1] - hi).max()))

    worst = max([off(e, parts[e.Name]["lo_m"], parts[e.Name]["hi_m"]) for e in built]
                + [off(e, ops[e.Name]["panel_lo_m"], ops[e.Name]["panel_hi_m"]) for e in fills], default=0.0)
    res.append((f"every wall, slab, window and door where forge has it (to {tol * 1e3:g} mm)", worst < tol,
                f"worst {worst * 1e3:.4f} mm"))
    worst_void = max((off(v, ops[v.Name]["lo_m"], ops[v.Name]["hi_m"]) for v in voids), default=0.0)
    res.append((f"every opening where forge has it (to {tol * 1e3:g} mm)", worst_void < tol, f"worst {worst_void * 1e3:.4f} mm"))
    host = {v.Name: v.VoidsElements[0].RelatingBuildingElement.Name if v.VoidsElements else None for v in voids}
    wrong = [n for n, w in host.items() if w != ops[n]["wall"]]
    filled = {e.Name: e.FillsVoids[0].RelatingOpeningElement.Name if e.FillsVoids else None for e in fills}
    unfilled = [n for n in ops if filled.get(n) != n]
    res.append(("every opening voids its own wall and holds its own window or door", not wrong and not unfilled,
                f"{len(voids)} openings, {len(wrong) + len(unfilled)} wrong"))

    clashes = [(a.Name, b.Name) for i, a in enumerate(built) for b in built[i + 1:]
               if _overlap(boxes[a.GlobalId], boxes[b.GlobalId]) > 1e-9]
    res.append(("no clashes between walls, slabs and roof", not clashes,
                f"{len(built)} elements, {len(clashes)} clashes" + (f", first {clashes[0]}" if clashes else "")))

    glazed = defaultdict(float)
    for e in fills:
        props = ifcopenshell.util.element.get_pset(e, "BF_Opening") or {}
        if props.get("Glazed") and not str(props.get("Flat", "")).endswith("stair"):
            glazed[props["Flat"]] += e.OverallWidth * e.OverallHeight
    flats = {fl["name"]: fl["glazed_m2"] for fl in apt["flats"]}
    worst_glazing = max((abs(glazed.get(n, 0.0) - g) for n, g in flats.items()), default=0.0)
    res.append(("glazing per flat equals pass 3b's flat_envelope", worst_glazing < 1e-9 and set(glazed) == set(flats),
                f"{len(glazed)} flats glazed of {len(flats)}, worst {worst_glazing:.2e} m2"))

    ids = [e.GlobalId for e in f.by_type("IfcRoot")]
    res.append(("GlobalIds unique", len(ids) == len(set(ids)), f"{len(ids)}"))
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, log, express_rules=True)
    res.append(("schema validation (with express rules)", not log.statements,
                f"{len(log.statements)} issues" + (f": {str(log.statements[0])[:160]}" if log.statements else "")))
    return res


def report(res: list[tuple[str, bool, str]]) -> str:
    return "\n".join(f"{'ok  ' if ok else 'FAIL'} {label}: {detail}" for label, ok, detail in res)


# ---- Safety glazing (IBC 2018 2406.4.1-2406.4.3), from forge's geometry ----

FT2 = 0.3048 ** 2
TOL_M = 1e-9  # edges that touch, to rounding
NO_HAZARD = "none found under IBC 2018 2406.4.1-2406.4.3 (2406.4.4-2406.4.7 not assessed)"


def _plan_gap(a: dict, b: dict) -> float:
    """The plan distance (m) between two openings' boxes: along the face for two in one wall,
    corner to corner for two in walls that meet."""
    d = [max(0.0, b["lo_m"][i] - a["hi_m"][i], a["lo_m"][i] - b["hi_m"][i]) for i in (0, 1)]
    return float(np.hypot(*d))


def safety_glazing(apt: dict, params: dict) -> dict[str, str]:
    """The openings whose glazing IBC 2018 2406.4.1-2406.4.3 make a hazardous location (so it must
    be safety glazing), each with the reason, from forge's geometry and params/bidset.yaml:

    - 2406.4.1: glazing in a door (the patio doors);
    - 2406.4.2: glazing within the arc of a closed door's vertical edge, measured in plan on the
      same storey (along the wall, or round a corner), with its bottom edge under the height above
      the floor. Exceptions 1-3 (decorative glazing, a wall between, a closet door) don't fit
      this building. Exception 4 (on the latch side of, and perpendicular to, a door in an R-2
      unit) needs the door's handing, which the model doesn't carry, so glazing round a corner
      is flagged and the reason says so;
    - 2406.4.3: a pane over the area, its bottom edge under and top edge over the heights, and a
      walking surface within the distance. The unit's whole glass stands in for its largest pane
      (the model has no panes), and the floor inside, which meets the wall, is the walking surface.

    Not assessed: 2406.4.4 (guards and railings), 2406.4.5 (wet areas), 2406.4.6 and 2406.4.7
    (beside stairs and landings, and at the bottom of a stair). The model has no stair flights or
    landings, so the stair windows wait for them.
    """
    c = "bidset.code.safety_glazing."
    arc, door_bottom = params[c + "door_arc_in"].value * IN, params[c + "door_bottom_in"].value * IN
    area, w_bottom, w_top, walk = (params[c + "window_area_ft2"].value * FT2, params[c + "window_bottom_in"].value * IN,
                                   params[c + "window_top_in"].value * IN, params[c + "window_walk_in"].value * IN)
    floor_from_glass = 0.0  # the floor inside runs to the wall
    ops = apt["openings"]
    doors = [d for d in ops if d["kind"] != "window"]
    out = {}
    for o in ops:
        if not o["glazed"]:
            continue
        if o["kind"] != "window":
            out[o["id"]] = "IBC 2018 2406.4.1: glazing in a door"
            continue
        for d in doors:
            if d["storey"] != o["storey"]:
                continue
            gap = _plan_gap(o, d)
            if gap <= arc + TOL_M and o["sill_above_floor_m"] < door_bottom:
                where = ("" if d["wall"] == o["wall"] else
                         ", round the corner (exception 4 may apply on the door's latch side; the model has no handing)")
                out[o["id"]] = (f"IBC 2018 2406.4.2: {gap / IN:.1f} in from the edge of door {d['id']}{where}, "
                                f"bottom edge {o['sill_above_floor_m'] / IN:.0f} in above the floor")
                break
        bottom, top = o["sill_above_floor_m"], o["sill_above_floor_m"] + o["height_m"]
        if (o["id"] not in out and o["width_m"] * o["height_m"] > area and bottom < w_bottom and top > w_top
                and floor_from_glass <= walk):
            out[o["id"]] = "IBC 2018 2406.4.3: a large pane low in the wall"
    return out


# ---- One stair: IBC 2018 1006.3.3 and Table 1006.3.3(1), and so escape windows (1030) ----

def single_exit(apt: dict, params: dict, marked: int = 0) -> dict:
    """Whether the walk-up's one stair fits IBC 2018 1006.3.3 item 1 and Table 1006.3.3(1) (R-2
    dwelling units), what that brings with it, and how far the model is from it. `marked` is the
    number of windows the model marks as escape windows.

    - **The table** allows one exit on the first to third storey above grade, with at most 4
      dwelling units a storey and at most 125 ft of common path of egress travel. Its footnote a
      holds it to buildings sprinklered throughout (903.3.1.1 or 903.3.1.2) and given escape
      openings by section 1030. So `fits_table` is only half of it: `meets_footnote_a` asks
      whether the model has the escape windows. Sprinklers aren't in the model at all.
    - **Common path:** bounded by straight lines, interior walls not modelled. On every storey, a
      flat corner to its far corner (length plus width), where the flat's door to the stair is
      the exit. On the ground floor, if the stair hall there is exit access and not part of the
      stair's enclosure, the walk runs on to the front entry door: the farthest flat corner to that
      door, by x plus y.
    - **Escape windows:** a storey with one exit brings 1030.1 item 1, an escape opening in every
      sleeping room. Exception 2 (a door from the room straight to a yard or an exterior exit
      balcony) is for rooms the model doesn't have. That is certain on the upper storeys, whose
      only way out is the stair. The ground floor too, unless its flats' patio doors to the yard
      count as a second way out; the model and this reading leave that open. Counts round up.
    """
    c = "bidset.code.single_exit."
    per_storey = Counter(fl["floor"] for fl in apt["flats"])
    units = max(per_storey.values())
    storeys = apt["storeys"]
    ft = 0.3048
    to_stair_ft = (apt["flat_len_m"] + apt["depth_m"] / 2) / ft
    entry = next((o for o in apt["openings"] if o["kind"] == "entry_door"), None)
    to_entry_ft = None
    if entry is not None:
        ex, ey = (entry["lo_m"][0] + entry["hi_m"][0]) / 2, entry["along_m"]
        corners = []
        for fl in (fl for fl in apt["flats"] if fl["floor"] == 1):
            name = fl["name"]
            x0, x1 = (0.0, apt["depth_m"] / 2) if "-front-" in name else (apt["depth_m"] / 2, apt["depth_m"])
            y0, y1 = (0.0, apt["flat_len_m"]) if name.endswith("-left") else (apt["length_m"] - apt["flat_len_m"], apt["length_m"])
            corners += [abs(x - ex) + abs(y - ey) for x in (x0, x1) for y in (y0, y1)]
        to_entry_ft = max(corners) / ft if corners else None
    path_ft = max(to_stair_ft, to_entry_ft or 0.0)
    fits = (storeys <= params[c + "r2_max_storey"].value and units <= params[c + "r2_max_units"].value
            and path_ft <= params[c + "r2_max_common_path_ft"].value)
    bedrooms = params["bidset.flat_bedrooms"].value
    upper = sum(n for k, n in per_storey.items() if k > 1)
    need_upper = math.ceil(upper * bedrooms)
    need_ground = math.ceil(per_storey.get(1, 0) * bedrooms)
    return {"storeys": storeys, "units_per_storey": units, "path_to_stair_ft": to_stair_ft, "path_to_entry_ft": to_entry_ft,
            "fits_table": fits, "escape_needed_upper": need_upper, "escape_needed_ground": need_ground,
            "escape_marked": marked, "meets_footnote_a": fits and marked >= need_upper}


def single_exit_report(se: dict, params: dict) -> str:
    """The single-stair finding in a few sentences, saying plainly how far the model is from it."""
    c, e = "bidset.code.single_exit.", "bidset.code.escape."
    v = lambda k: params[k].value  # noqa: E731
    path = f"~{se['path_to_stair_ft']:.0f} ft from a flat's far corner to its door to the stair"
    if se["path_to_entry_ft"] is not None:
        path += (f", or ~{se['path_to_entry_ft']:.0f} ft on to the front door on the ground floor if its stair hall is "
                 "exit access")
    head = (f"One stair: IBC 2018 Table 1006.3.3(1) allows a single exit on the first {v(c + 'r2_max_storey'):g} storeys "
            f"with at most {v(c + 'r2_max_units'):g} dwelling units a storey and {v(c + 'r2_max_common_path_ft'):g} ft of "
            f"common path. The walk-up has {se['storeys']} storeys and {se['units_per_storey']} flats a storey; its "
            f"common path is bounded by {path} (straight lines; interior walls not modelled).")
    if not se["fits_table"]:
        return head + " So one stair does NOT fit the table: the walk-up needs a second exit."
    return (head + " It fits the table, but the table's footnote a allows it only in a building sprinklered throughout "
            "(903.3.1.1 or 903.3.1.2) and given escape openings (1030): an escape window in every sleeping room, "
            f"{se['escape_needed_upper']} on the upper storeys and {se['escape_needed_ground']} more on the ground floor "
            "unless its patio doors count as a second way out. Each must clear "
            f"{v(e + 'min_area_ft2'):g} ft2, {v(e + 'min_height_in'):g} in high and {v(e + 'min_width_in'):g} in wide in "
            f"normal operation, its bottom no more than {v(e + 'max_sill_in'):g} in up. "
            + ("The model meets that for the escape windows. " if se["meets_footnote_a"] else
               f"The model does NOT meet it yet: it marks {se['escape_marked']} escape windows of at least "
               f"{se['escape_needed_upper']} needed, has no rooms to say which windows serve bedrooms, ")
            + "and has no sprinkler system in it.")


# ---- The IDS: what a bid set's windows and doors must carry ----

UNIT_PSET = {"IFCWINDOW": "Pset_WindowCommon", "IFCDOOR": "Pset_DoorCommon"}
GLAZING = "Pset_DoorWindowGlazingType"
OPERATIONS = ["casement", "awning", "hopper", "double-hung", "single-hung", "horizontal slider", "fixed", "tilt-turn"]
SAFETY_GLAZING = ["tempered", "laminated"]


def _down(x: float) -> float:
    """x rounded down to 0.0001, after clearing float noise (24 in is 0.6096 m, not 0.6095)."""
    return math.floor(round(x * 1e4, 6)) / 1e4


def _up(x: float) -> float:
    return math.ceil(round(x * 1e4, 6)) / 1e4


def ids_fields(params: dict) -> list[dict]:
    """The fields a quote needs (Jon, 2026-11-19, and D27's list), each as an IDS requirement:
    which classes it applies to, whether it is a standard IFC property or one of ours (BidSet_),
    and the facet. Standard where IFC4 has the property; ours where it doesn't."""
    from ifctester import ids

    def prop(ps, name, value=None, dt=None):
        return lambda cls: ids.Property(propertySet=ps(cls) if callable(ps) else ps, baseName=name, value=value, dataType=dt)

    def const(facet):
        return lambda cls: facet()

    # The code's U-0.30 in W/m2K, rounded up to 3 decimals: a unit rated U-0.30 and written
    # rounded (1.7035) still passes, and nothing over 0.3001 does.
    u_max = math.ceil(params["bidset.code.fenestration_u_max"].value * BTU_FT2 * 1e3) / 1e3
    # Escape windows (IBC 2018 1030), in metres, to 0.1 mm (0.0001 m2): a unit that meets the code
    # and is written rounded still passes. That leans to the supplier, by under 0.1 mm.
    e = "bidset.code.escape."
    esc_area = _down(params[e + "min_area_ft2"].value * FT2)
    esc_width = _down(params[e + "min_width_in"].value * IN)
    esc_height = _down(params[e + "min_height_in"].value * IN)
    esc_sill = _up(params[e + "max_sill_in"].value * IN)
    door_ops = [x for x in ifcopenshell.ifcopenshell_wrapper.schema_by_name("IFC4")
                .declaration_by_name("IfcDoorTypeOperationEnum").enumeration_items() if x not in ("USERDEFINED", "NOTDEFINED")]
    both, windows, glazed = ("IFCWINDOW", "IFCDOOR"), ("IFCWINDOW",), ("IFCWINDOW", "IFCDOOR+glazed")
    unit = lambda cls: UNIT_PSET[cls]  # noqa: E731
    return [
        dict(key="type", label="type mark", on=both, std=True, facet=prop(unit, "Reference")),
        dict(key="storey", label="storey", on=both, std=True,
             facet=const(lambda: ids.PartOf(name="IFCBUILDINGSTOREY", relation="IFCRELCONTAINEDINSPATIALSTRUCTURE"))),
        dict(key="external", label="exterior or not", on=both, std=True, facet=prop(unit, "IsExternal")),
        dict(key="width", label="unit width", on=both, std=True, facet=const(lambda: ids.Attribute(name="OverallWidth"))),
        dict(key="height", label="unit height", on=both, std=True, facet=const(lambda: ids.Attribute(name="OverallHeight"))),
        dict(key="ro_width", label="rough opening width", on=both, std=False,
             note="IFC's opening element is the hole in the model; this is the size to frame",
             facet=prop("BidSet_Unit", "RoughOpeningWidth", dt="IFCLENGTHMEASURE")),
        dict(key="ro_height", label="rough opening height", on=both, std=False,
             note="IFC's opening element is the hole in the model; this is the size to frame",
             facet=prop("BidSet_Unit", "RoughOpeningHeight", dt="IFCLENGTHMEASURE")),
        dict(key="operation", label="operation", on=windows, std=False,
             note="in a supplier's words; IFC4 describes a panel's operation in IfcWindowPanelProperties, in panel terms",
             facet=prop("BidSet_Unit", "Operation", ids.Restriction(options={"enumeration": OPERATIONS}), "IFCLABEL")),
        dict(key="door_operation", label="operation (on the door type)", on=("IFCDOORTYPE",), std=True,
             facet=const(lambda: ids.Attribute(name="OperationType", value=ids.Restriction(options={"enumeration": door_ops})))),
        dict(key="material", label="frame material", on=both, std=True, facet=const(lambda: ids.Material())),
        dict(key="colour_in", label="frame colour inside", on=both, std=False, note="IFC's styles colour a drawing, not a product", facet=prop("BidSet_Unit", "FrameColourInside", dt="IFCLABEL")),
        dict(key="colour_out", label="frame colour outside", on=both, std=False, note="IFC's styles colour a drawing, not a product", facet=prop("BidSet_Unit", "FrameColourOutside", dt="IFCLABEL")),
        dict(key="low_e", label="glass: low-e coating (yes or no)", on=glazed, std=True, facet=prop(GLAZING, "IsCoated", dt="IFCBOOLEAN")),
        dict(key="gas", label="glass: gas fill", on=glazed, std=True, facet=prop(GLAZING, "FillGas", dt="IFCLABEL")),
        dict(key="tempered", label="glass: tempered (yes or no)", on=glazed, std=True, facet=prop(GLAZING, "IsTempered", dt="IFCBOOLEAN")),
        dict(key="obscure", label="glass: obscure (yes or no)", on=glazed, std=False, facet=prop("BidSet_Unit", "ObscureGlass", dt="IFCBOOLEAN")),
        dict(key="u", label="U-factor within the code's limit", on=glazed, std=True,
             facet=prop(unit, "ThermalTransmittance", ids.Restriction(options={"maxInclusive": u_max}, base="double"),
                        "IFCTHERMALTRANSMITTANCEMEASURE")),
        dict(key="shgc", label="SHGC", on=glazed, std=True, facet=prop(GLAZING, "SolarHeatGainTransmittance", dt="IFCNORMALISEDRATIOMEASURE")),
        dict(key="grade", label="performance grade (design pressure)", on=both, std=True,
             facet=prop(unit, "WindLoadRating", ids.Restriction(options={"pattern": "(R|LC|CW|AW)-PG[0-9]+.*"}), "IFCLABEL")),
        dict(key="escape", label="escape window (yes or no)", on=windows, std=True, facet=prop("Pset_WindowCommon", "FireExit", dt="IFCBOOLEAN")),
        # On a window marked as an escape window, IBC 2018 1030.2-1030.3 (params). IFC4 has no
        # net clear opening; it is "the result of normal operation of the opening" (1030.2.1).
        dict(key="escape_area", label="escape window: clear opening area", on=("IFCWINDOW+escape",), std=False,
             note="IFC4 has no net clear opening",
             facet=prop("BidSet_Unit", "ClearOpeningArea", ids.Restriction(options={"minInclusive": esc_area}, base="double"), "IFCAREAMEASURE")),
        dict(key="escape_width", label="escape window: clear opening width", on=("IFCWINDOW+escape",), std=False,
             note="IFC4 has no net clear opening",
             facet=prop("BidSet_Unit", "ClearOpeningWidth", ids.Restriction(options={"minInclusive": esc_width}, base="double"), "IFCLENGTHMEASURE")),
        dict(key="escape_height", label="escape window: clear opening height", on=("IFCWINDOW+escape",), std=False,
             note="IFC4 has no net clear opening",
             facet=prop("BidSet_Unit", "ClearOpeningHeight", ids.Restriction(options={"minInclusive": esc_height}, base="double"), "IFCLENGTHMEASURE")),
        dict(key="escape_sill", label="escape window: bottom of the clear opening above the floor", on=("IFCWINDOW+escape",), std=False,
             note="IFC4 has no net clear opening",
             facet=prop("BidSet_Unit", "ClearOpeningSillHeight", ids.Restriction(options={"maxInclusive": esc_sill}, base="double"), "IFCLENGTHMEASURE")),
        dict(key="screen", label="screen (yes or no)", on=glazed, std=False, facet=prop("BidSet_Unit", "Screen", dt="IFCBOOLEAN")),
        dict(key="grilles", label="grilles", on=glazed, std=False, facet=prop("BidSet_Unit", "Grilles", dt="IFCLABEL")),
        dict(key="hardware", label="hardware finish", on=both, std=False, facet=prop("BidSet_Unit", "HardwareFinish", dt="IFCLABEL")),
        dict(key="install", label="install type", on=both, std=False, facet=prop("BidSet_Unit", "InstallType", dt="IFCLABEL")),
        dict(key="in_wall", label="in a wall", on=both, std=True,
             facet=const(lambda: ids.PartOf(name="IFCWALL", relation="IFCRELVOIDSELEMENT IFCRELFILLSELEMENT"))),
        dict(key="wall_construction", label="the wall's construction (on exterior walls)", on=("IFCWALL+external",), std=False,
             facet=prop("BidSet_Wall", "Construction", dt="IFCLABEL")),
        dict(key="masterformat", label="MasterFormat section, level 3", on=both, std=True,
             facet=const(lambda: ids.Classification(system="MasterFormat",
                                                    value=ids.Restriction(options={"pattern": "08 [0-9][1-9] [0-9]{2}"})))),
        dict(key="safety", label="safety glazing where IBC 2018 2406.4.1-2406.4.3 call for it", on=("IFCWINDOW+hazard", "IFCDOOR+hazard"),
             std=False, note="IFC4 has IsTempered and IsLaminated as two yes-or-noes; this names the one that meets the code", facet=prop("BidSet_Unit", "SafetyGlazing", ids.Restriction(options={"enumeration": SAFETY_GLAZING}), "IFCLABEL")),
    ]


def _applicability(on: str):
    """The entity a field applies to, and any filter: '+glazed', '+hazard' (BF_Opening flags),
    '+escape' (a window marked as an escape window) or '+external' (a wall's Pset_WallCommon)."""
    from ifctester import ids

    cls, _, only = on.partition("+")
    facets = [ids.Entity(name=cls)]
    if only == "glazed":
        facets.append(ids.Property(propertySet="BF_Opening", baseName="Glazed", value="TRUE", dataType="IFCBOOLEAN"))
    elif only == "hazard":
        facets.append(ids.Property(propertySet="BF_Opening", baseName="SafetyGlazingRequired", value="TRUE", dataType="IFCBOOLEAN"))
    elif only == "escape":
        facets.append(ids.Property(propertySet="Pset_WindowCommon", baseName="FireExit", value="TRUE", dataType="IFCBOOLEAN"))
    elif only == "external":
        facets.append(ids.Property(propertySet="Pset_WallCommon", baseName="IsExternal", value="TRUE", dataType="IFCBOOLEAN"))
    return cls, facets


def write_ids(params: dict, path: Path):
    """The IDS (buildingSMART IDS 1.0) for a bid set's windows and doors: one specification per
    field and class, so the results read as a checklist. Written to `path` and read back against
    the IDS schema."""
    from ifctester import ids

    doc = ids.Ids(title="Windows and doors in a bid set (brownfield-compute pass 3f)", version="0.1",
                  description="What a supplier needs to price a window or door, as requirements an IFC model can be "
                              "checked against. Properties named BidSet_ are ours, where IFC4 has no standard one.",
                  purpose="bidding", milestone="bid set")
    for fld in ids_fields(params):
        for on in fld["on"]:
            cls, facets = _applicability(on)
            spec = ids.Specification(name=f"{fld['label']} ({cls.lower().removeprefix('ifc')})", ifcVersion=["IFC4"],
                                     identifier=f"{fld['key']}/{on}",
                                     description=("IFC4 standard" if fld["std"] else
                                                  f"BidSet_ (ours: {fld.get('note', 'IFC4 has no property for it')})"))
            spec.applicability.extend(facets)
            spec.requirements.append(fld["facet"](cls))
            doc.specifications.append(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.to_xml(str(path))
    return read_ids(path)


def read_ids(path: Path):
    """The IDS read back from its file, checked against the IDS schema. ifctester 0.9.0 doesn't
    read a specification's `identifier` back, so it is restored from the XML, in order."""
    import xml.etree.ElementTree as ET

    from ifctester import ids

    doc = ids.open(str(path), validate=True)
    tags = [e for e in ET.parse(path).getroot().iter() if e.tag.rsplit("}", 1)[-1] == "specification"]
    if len(tags) != len(doc.specifications):
        raise ValueError(f"{path}: {len(tags)} specifications in the XML, {len(doc.specifications)} read")
    for spec, tag in zip(doc.specifications, tags):
        spec.identifier = tag.get("identifier")
    return doc


def run_ids(doc, ifc_path: Path) -> list[dict]:
    """Each specification's result on the file: how many elements it applies to and how many pass."""
    f = ifcopenshell.open(str(ifc_path))
    doc.validate(f)
    return [{"id": s.identifier, "name": s.name, "standard": s.description.startswith("IFC4"),
             "applicable": len(s.applicable_entities), "passed": len(s.passed_entities), "status": bool(s.status)}
            for s in doc.specifications]


def ids_carried(rows: list[dict]) -> tuple[list[str], int]:
    """The fields the model carries (every specification of the field passes, on at least one
    element), by label, and how many fields there are."""
    by = defaultdict(list)
    for r in rows:
        by[r["id"].split("/", 1)[0]].append(r)
    carried = [rs[0]["name"].rsplit(" (", 1)[0] for rs in by.values()
               if all(r["status"] for r in rs) and sum(r["applicable"] for r in rs) > 0]
    return carried, len(by)


def ids_report(rows: list[dict], escape_needed: tuple[int, int] | None = None) -> str:
    """The checklist: per field, how many pass of those it applies to, for windows, doors, and
    (for the two fields that sit elsewhere) the door types or the exterior walls. An escape
    window's sizes apply only to windows marked as escape windows; with `escape_needed` (upper
    storeys, ground floor, from `single_exit`), a row that applies to none says how many are
    needed, so it can't read as a pass."""
    fields: dict[str, dict] = {}
    for r in rows:
        key, on = r["id"].split("/", 1)
        d = fields.setdefault(key, {"name": r["name"].rsplit(" (", 1)[0], "std": r["standard"]})
        d[on.split("+")[0]] = r

    def cell(r, what=""):
        if not r:
            return ""
        if escape_needed and r["id"].startswith("escape_") and r["applicable"] == 0:
            up, ground = escape_needed
            return f"none marked; {up} needed ({up + ground} with the ground floor)"
        return f"{r['passed']} of {r['applicable']}{what}"

    lines = ["| Field | Where | Windows | Doors | Door types or walls |", "|---|---|---|---|---|"]
    for d in fields.values():
        other = (cell(d.get("IFCDOORTYPE"), " door types") if "IFCDOORTYPE" in d
                 else cell(d.get("IFCWALL"), " exterior walls") if "IFCWALL" in d else "")
        lines.append(f"| {d['name']} | {'IFC4' if d['std'] else 'BidSet_'} | {cell(d.get('IFCWINDOW'))} | "
                     f"{cell(d.get('IFCDOOR'))} | {other} |")
    return "\n".join(lines)


# ---- From the IFC alone: schedule, elevations, quantities (step 4) ----
#
# Everything here reads the IFC file and nothing else (not forge's JSON), to show the file is
# enough to price and draw from. The tests hold what comes out to forge's model. Optional IFC
# attributes may be missing in a file from elsewhere: they read as "not in the model", never as
# a crash.

FACES = ("front", "back", "left", "right")
NOT_IN_MODEL = "not in the model"


def _host_wall(e):
    """The wall a window or door sits in: the one voided by the opening it fills."""
    for fill in e.FillsVoids or ():
        for void in fill.RelatingOpeningElement.VoidsElements or ():
            return void.RelatingBuildingElement
    return None


def _material_name(mat) -> str | None:
    """A material's name, whatever kind of IFC material it is."""
    if mat is None:
        return None
    for attr in ("Name", "LayerSetName", "ProfileSetName"):
        if getattr(mat, attr, None):
            return getattr(mat, attr)
    if mat.is_a("IfcMaterialList"):
        return ", ".join(m.Name for m in mat.Materials if m.Name) or None
    if mat.is_a("IfcMaterialLayerSetUsage"):
        return _material_name(mat.ForLayerSet)
    if mat.is_a("IfcMaterialLayerSet"):
        return ", ".join(lay.Material.Name for lay in mat.MaterialLayers if lay.Material and lay.Material.Name) or None
    return None


def _property_note(e, t, pset_name: str, prop: str) -> str | None:
    """The Description of a property (where our files say a number's source), on the unit if it
    has the property, else on its type."""
    sets = [r.RelatingPropertyDefinition for r in getattr(e, "IsDefinedBy", ()) or () if r.is_a("IfcRelDefinesByProperties")]
    sets += list((t.HasPropertySets or ()) if t is not None else ())
    for ps in sets:
        if ps.is_a("IfcPropertySet") and ps.Name == pset_name:
            for q in ps.HasProperties or ():
                if q.Name == prop:
                    return q.Description
    return None


def read_back(path: Path) -> dict:
    """What the drawings need, read from the IFC: storeys, the building's extent (its exterior
    walls), the roofs, and every window and door in an exterior wall, each with its type, size,
    place and properties (its own over its type's, as IFC has it)."""
    f = ifcopenshell.open(str(path))
    ext = [w for w in f.by_type("IfcWall") if (ifcopenshell.util.element.get_pset(w, "Pset_WallCommon") or {}).get("IsExternal")]
    ext_ids = {w.id() for w in ext}
    units = [e for e in list(f.by_type("IfcWindow")) + list(f.by_type("IfcDoor"))
             if (h := _host_wall(e)) is not None and h.id() in ext_ids]
    roofs = [s for s in f.by_type("IfcSlab") if s.PredefinedType == "ROOF"]
    boxes = _world_boxes(f, ext + units + roofs)
    lo = np.min([boxes[w.GlobalId][0] for w in ext], axis=0)
    hi = np.max([boxes[w.GlobalId][1] for w in ext], axis=0)
    out = {"storeys": sorted(((s.Elevation or 0.0), s.Name or "(unnamed storey)") for s in f.by_type("IfcBuildingStorey")),
           "lo": lo, "hi": hi, "roofs": [boxes[r.GlobalId] for r in roofs], "units": [], "types": {}}
    for e in units:
        t = ifcopenshell.util.element.get_type(e)
        mark = t.Name if t is not None and t.Name else "(no type)"
        box = boxes[e.GlobalId]
        container = ifcopenshell.util.element.get_container(e)
        out["units"].append({
            "name": e.Name or e.GlobalId, "cls": e.is_a(), "mark": mark, "width": e.OverallWidth, "height": e.OverallHeight,
            "lo": box[0], "hi": box[1], "face": _face_of(box, lo, hi),
            "storey": container.Name if container is not None else "(no storey)",
            "storey_z": (container.Elevation or 0.0) if container is not None and container.is_a("IfcBuildingStorey") else 0.0,
            "props": ifcopenshell.util.element.get_pset(e, "BF_Opening") or {},
            "psets": ifcopenshell.util.element.get_psets(e),  # its own over its type's
            "operation": getattr(e, "OperationType", None) or (getattr(t, "OperationType", None) if t is not None else None),
            "material": _material_name(ifcopenshell.util.element.get_material(e)),
            "u_note": _property_note(e, t, "Pset_WindowCommon" if e.is_a("IfcWindow") else "Pset_DoorCommon", "ThermalTransmittance"),
        })
        if mark not in out["types"]:
            refs = []
            if t is not None:
                for r in ifcopenshell.util.classification.get_references(t):
                    system = ifcopenshell.util.classification.get_classification(r)
                    if system is not None and system.Name == "MasterFormat":
                        refs.append((r.Identification or "", r.Name or "", r.Description or ""))
            out["types"][mark] = {"cls": t.is_a() if t is not None else None,
                                  "description": (t.Description if t is not None else None) or "", "refs": sorted(refs)}
    return out


def _face_of(b, lo, hi) -> str:
    """The facade a unit is in: the building side its centre is nearest to."""
    c = (np.asarray(b[0]) + np.asarray(b[1])) / 2
    d = {"front": c[0] - lo[0], "back": hi[0] - c[0], "left": c[1] - lo[1], "right": hi[1] - c[1]}
    return min(d, key=d.get)


def _along(face: str, lo, hi, x: float, y: float) -> float:
    """Distance along a facade, left to right as seen from outside it (m)."""
    return {"front": hi[1] - y, "back": y - lo[1], "left": x - lo[0], "right": hi[0] - x}[face]


def elevation(rb: dict, face: str) -> dict:
    """A facade seen from outside: its width, the walls' bottom and top, the roofs' edges, the
    storey levels, and each unit as a rectangle (u0, u1 along; z0, z1 up), with its mark."""
    lo, hi = rb["lo"], rb["hi"]
    width = float(hi[1] - lo[1]) if face in ("front", "back") else float(hi[0] - lo[0])
    rects = []
    for u in (u for u in rb["units"] if u["face"] == face):
        a = sorted([_along(face, lo, hi, u["lo"][0], u["lo"][1]), _along(face, lo, hi, u["hi"][0], u["hi"][1])])
        rects.append({"name": u["name"], "mark": u["mark"], "cls": u["cls"], "u0": float(a[0]), "u1": float(a[1]),
                      "z0": float(u["lo"][2]), "z1": float(u["hi"][2]), "glazed": bool(u["props"].get("Glazed")),
                      "safety": bool(u["props"].get("SafetyGlazingRequired"))})
    roofs = []
    for r_lo, r_hi in rb["roofs"]:
        a = sorted([_along(face, lo, hi, r_lo[0], r_lo[1]), _along(face, lo, hi, r_hi[0], r_hi[1])])
        roofs.append((float(a[0]), float(a[1]), float(r_lo[2]), float(r_hi[2])))
    return {"face": face, "width": width, "z0": float(lo[2]), "z1": float(hi[2]), "levels": rb["storeys"], "roofs": roofs,
            "rects": sorted(rects, key=lambda r: (r["z0"], r["u0"]))}


def _ftin(m) -> str:
    if m is None:
        return NOT_IN_MODEL
    inches = round(m / IN * 8) / 8
    ft, rest = divmod(inches, 12)
    return f"{int(ft)}'-{rest:g}\""


def elevation_svg(el: dict, scale: float = 40.0) -> str:
    """The elevation as SVG: 1 m = `scale` px. Wall, roof edges, storey levels (dashed), each window
    and door with its mark, safety-glazed units outlined heavier, and a legend. Text from the IFC
    is XML-escaped."""
    from xml.sax.saxutils import escape

    pad, right, head, foot = 60.0, 120.0, 50.0, 90.0  # right: room for the level labels
    u_min = min([0.0] + [r[0] for r in el["roofs"]])
    u_max = max([el["width"]] + [r[1] for r in el["roofs"]])
    top = max([el["z1"]] + [r[3] for r in el["roofs"]])
    bottom = min(el["z0"], 0.0)
    w, h = (u_max - u_min) * scale + pad + right, (top - bottom) * scale + head + foot
    X = lambda u: pad + (u - u_min) * scale  # noqa: E731
    Y = lambda z: head + (top - z) * scale  # noqa: E731
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.1f} {h:.1f}" '
           'font-family="Helvetica, Arial, sans-serif">',
           f'<rect x="0" y="0" width="{w:.1f}" height="{h:.1f}" fill="#ffffff"/>',
           f'<text x="{pad:.1f}" y="24" font-size="16" fill="#222">{escape(el["face"].capitalize())} elevation, seen from outside</text>',
           f'<text x="{pad:.1f}" y="40" font-size="11" fill="#555">Drawn from apartment.ifc alone. 1 m = {scale:g} px. '
           f'{el["width"]:.2f} m ({escape(_ftin(el["width"]))}) wide.</text>',
           f'<rect x="{X(0):.1f}" y="{Y(el["z1"]):.1f}" width="{el["width"] * scale:.1f}" '
           f'height="{(el["z1"] - el["z0"]) * scale:.1f}" fill="#efe9df" stroke="#444" stroke-width="1.5"/>']
    for r in el["roofs"]:
        out.append(f'<rect x="{X(r[0]):.1f}" y="{Y(r[3]):.1f}" width="{(r[1] - r[0]) * scale:.1f}" '
                   f'height="{(r[3] - r[2]) * scale:.1f}" fill="#555"/>')
    out.append(f'<line x1="{X(u_min) - 20:.1f}" y1="{Y(0):.1f}" x2="{X(u_max) + 20:.1f}" y2="{Y(0):.1f}" stroke="#222" stroke-width="2"/>')
    for z, name in el["levels"]:
        out.append(f'<line x1="{X(0):.1f}" y1="{Y(z):.1f}" x2="{X(el["width"]):.1f}" y2="{Y(z):.1f}" stroke="#999" '
                   'stroke-dasharray="6 4" stroke-width="0.8"/>')
        out.append(f'<text x="{X(el["width"]) + 6:.1f}" y="{Y(z) - 3:.1f}" font-size="10" fill="#555">{escape(name)} '
                   f'+{escape(_ftin(z))}</text>')
    for r in el["rects"]:
        fill = "#bcd7ee" if r["glazed"] else "#8b6a4f"
        stroke, sw = ("#b00020", 2.2) if r["safety"] else ("#333", 1.0)
        out.append(f'<rect x="{X(r["u0"]):.1f}" y="{Y(r["z1"]):.1f}" width="{(r["u1"] - r["u0"]) * scale:.1f}" '
                   f'height="{(r["z1"] - r["z0"]) * scale:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}">'
                   f'<title>{escape(str(r["name"]))}: {escape(str(r["mark"]))}</title></rect>')
        out.append(f'<text x="{X((r["u0"] + r["u1"]) / 2):.1f}" y="{Y((r["z0"] + r["z1"]) / 2) + 4:.1f}" font-size="10" '
                   f'text-anchor="middle" fill="#111">{escape(str(r["mark"]))}</text>')
    marks = sorted({r["mark"] for r in el["rects"]}, key=_mark_key)
    safe = sorted({r["mark"] for r in el["rects"] if r["safety"]}, key=_mark_key)
    ly = Y(min(el["z0"], 0.0)) + 30
    out.append(f'<text x="{pad:.1f}" y="{ly:.1f}" font-size="11" fill="#222">Marks: {escape(", ".join(marks))}. '
               f'{len(el["rects"])} units on this face.</text>')
    if safe:
        out.append(f'<rect x="{pad:.1f}" y="{ly + 12:.1f}" width="14" height="10" fill="#bcd7ee" stroke="#b00020" stroke-width="2.2"/>'
                   f'<text x="{pad + 20:.1f}" y="{ly + 21:.1f}" font-size="11" fill="#222">Safety glazing: IBC 2018 '
                   f'2406.4.1-2406.4.3 call for it ({escape(", ".join(safe))}).</text>')
    out.append("</svg>")
    return "\n".join(out)


def _mark_key(mark: str):
    """W before D, then by number: W2 before W10."""
    digits = "".join(ch for ch in mark if ch.isdigit())
    return (mark[:1] != "W", mark[:1], int(digits) if digits else 0, mark)


def _common(values) -> str:
    """One value if every unit agrees, else 'varies: ...' (so a schedule never hides a difference)."""
    vals = sorted({str(v) for v in values})
    return vals[0] if len(vals) == 1 else "varies: " + "; ".join(vals)


def schedule_rows(rb: dict) -> list[dict]:
    """The window and door schedule, one row per type mark: every field the IDS asks for, each
    from the units' own properties over their type's, or 'not in the model'. Where the units of a
    mark differ (a size, a property), the cell says 'varies' and lists them. Each U-factor carries
    its source as the file gives it, so a placeholder reads as one."""
    by_mark = defaultdict(list)
    for u in rb["units"]:
        by_mark[u["mark"]].append(u)
    glass, ours = "Pset_DoorWindowGlazingType", "BidSet_Unit"
    rows = []
    for mark in sorted(by_mark, key=_mark_key):
        us, t = by_mark[mark], rb["types"].get(mark, {})
        window = us[0]["cls"] == "IfcWindow"
        common = "Pset_WindowCommon" if window else "Pset_DoorCommon"

        def val(pset, prop, fmt=lambda v: v):
            return _common(NOT_IN_MODEL if (v := (u["psets"].get(pset) or {}).get(prop)) is None else fmt(v) for u in us)

        def length(pset, prop):
            return val(pset, prop, _ftin)

        def ro(u):
            p = u["psets"].get(ours) or {}
            w, h = p.get("RoughOpeningWidth"), p.get("RoughOpeningHeight")
            return NOT_IN_MODEL if w is None and h is None else f"{_ftin(w)} x {_ftin(h)}"

        reasons = sorted({u["props"].get("SafetyGlazingReason", "").split(":")[0] for u in us if u["props"].get("SafetyGlazingRequired")})
        refs = t.get("refs", [])
        rows.append({
            "mark": mark, "kind": "window" if window else "door", "count": len(us),
            "per_storey": "; ".join(f"{name}: {n}" for (_, name), n in sorted(Counter((u["storey_z"], u["storey"]) for u in us).items())),
            "width": _common(_ftin(u["width"]) for u in us), "height": _common(_ftin(u["height"]) for u in us),
            "width_mm": _common(NOT_IN_MODEL if u["width"] is None else round(u["width"] * 1e3, 1) for u in us),
            "height_mm": _common(NOT_IN_MODEL if u["height"] is None else round(u["height"] * 1e3, 1) for u in us),
            "description": t.get("description", ""),
            "is_external": val(common, "IsExternal"),
            "rough_opening": _common(ro(u) for u in us),
            "operation": _common((u["operation"] if u["operation"] not in (None, "NOTDEFINED") else NOT_IN_MODEL) for u in us)
            if not window else val(ours, "Operation"),
            "frame_material": _common(u["material"] or NOT_IN_MODEL for u in us),
            "frame_colour_inside": val(ours, "FrameColourInside"), "frame_colour_outside": val(ours, "FrameColourOutside"),
            "low_e": val(glass, "IsCoated"), "gas_fill": val(glass, "FillGas"), "tempered": val(glass, "IsTempered"),
            "obscure": val(ours, "ObscureGlass"),
            "safety_glazing_required": "yes (" + ", ".join(reasons) + ")" if reasons else "no",
            "safety_glazing": val(ours, "SafetyGlazing"),
            "u_factor_w_m2k": val(common, "ThermalTransmittance", lambda v: round(v, 3)),
            "u_factor_source": _common((u["u_note"] or "").split(":")[0] or NOT_IN_MODEL for u in us),
            "shgc": val(glass, "SolarHeatGainTransmittance"),
            "design_pressure": val(common, "WindLoadRating"),
            "escape_window": val("Pset_WindowCommon", "FireExit") if window else "",
            "clear_opening_area_ft2": val(ours, "ClearOpeningArea", lambda v: round(v / FT2, 2)) if window else "",
            "clear_opening_width": length(ours, "ClearOpeningWidth") if window else "",
            "clear_opening_height": length(ours, "ClearOpeningHeight") if window else "",
            "clear_opening_sill": length(ours, "ClearOpeningSillHeight") if window else "",
            "screen": val(ours, "Screen"), "grilles": val(ours, "Grilles"),
            "hardware_finish": val(ours, "HardwareFinish"), "install_type": val(ours, "InstallType"),
            "masterformat": "; ".join(f"{c} {n}" + (" (judgement)" if d.startswith("judgement") else "") for c, n, d in refs)
            or NOT_IN_MODEL,
        })
    return rows


def opening_rows(rb: dict) -> list[dict]:
    """Every window and door: id, mark, storey, flat, face, size, sill, and safety glazing."""
    rows = []
    for u in sorted(rb["units"], key=lambda u: str(u["name"])):
        p = u["props"]
        rows.append({"id": u["name"], "mark": u["mark"], "storey": u["storey"], "flat": p.get("Flat", ""),
                     "face": u["face"], "width": _ftin(u["width"]), "height": _ftin(u["height"]),
                     "sill_above_floor": _ftin(p.get("SillHeightAboveFloor")),
                     "safety_glazing": p.get("SafetyGlazingReason", "") if p.get("SafetyGlazingRequired") else "no"})
    return rows


def quantities_from_ifc(rb: dict) -> dict:
    """Areas from the IFC alone (m2): each facade's wall, gross (its width by the walls' height),
    its openings (drawn, from the geometry), and net; and the glazing in each flat (BF_Opening.Flat,
    from each unit's overall size; a unit without one is counted in `unsized`)."""
    faces = {}
    for face in FACES:
        el = elevation(rb, face)
        gross = el["width"] * (el["z1"] - el["z0"])
        openings = sum((r["u1"] - r["u0"]) * (r["z1"] - r["z0"]) for r in el["rects"])
        faces[face] = {"gross_m2": gross, "openings_m2": openings, "net_m2": gross - openings, "units": len(el["rects"])}
    glazed, unsized = defaultdict(float), 0
    for u in rb["units"]:
        p = u["props"]
        if p.get("Glazed") and not str(p.get("Flat", "")).endswith("stair"):
            if u["width"] is None or u["height"] is None:
                unsized += 1
                continue
            glazed[p["Flat"]] += u["width"] * u["height"]
    total = {k: sum(f[k] for f in faces.values()) for k in ("gross_m2", "openings_m2", "net_m2", "units")}
    lo, hi = rb["lo"], rb["hi"]
    return {"faces": faces, "total": total, "glazed_by_flat_m2": dict(sorted(glazed.items())), "unsized": unsized,
            "extent_m": [float(hi[i] - lo[i]) for i in range(3)]}


def write_drawings(path: Path, out: Path) -> dict:
    """The schedule (CSV), the openings list (CSV), four elevations (SVG) and the quantities (CSV),
    all from the IFC at `path`, into `out`. Returns what was read and written."""
    import csv

    rb = read_back(path)
    out.mkdir(parents=True, exist_ok=True)
    written = []

    def write_csv(name, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        written.append(out / name)

    sched, units = schedule_rows(rb), opening_rows(rb)
    write_csv("schedule.csv", sched)
    write_csv("openings.csv", units)
    els = {face: elevation(rb, face) for face in FACES}
    for face, el in els.items():
        (out / f"elevation_{face}.svg").write_text(elevation_svg(el), encoding="utf-8")
        written.append(out / f"elevation_{face}.svg")
    q = quantities_from_ifc(rb)
    qrows = [{"facade": face, "units": v["units"], "gross_m2": round(v["gross_m2"], 3), "openings_m2": round(v["openings_m2"], 3),
              "net_m2": round(v["net_m2"], 3), "gross_ft2": round(v["gross_m2"] / FT2, 1),
              "openings_ft2": round(v["openings_m2"] / FT2, 1), "net_ft2": round(v["net_m2"] / FT2, 1)}
             for face, v in [*q["faces"].items(), ("all", q["total"])]]
    write_csv("quantities.csv", qrows)
    return {"read": rb, "schedule": sched, "openings": units, "elevations": els, "quantities": q, "written": written}


# ---- A second, independent reader: That Open's web-ifc (tools/webifc) ----

WEBIFC = Path(__file__).resolve().parents[2] / "tools" / "webifc"
NODE_TIMEOUT_S = 300  # the reader takes a few seconds; a hang shouldn't block a run for ever


def _node_wheel():
    """The `nodejs_wheel` module from the `webifc` dependency group, or None without it."""
    import importlib.util

    if importlib.util.find_spec("nodejs_wheel") is None:
        return None
    import nodejs_wheel

    return nodejs_wheel


def webifc_locked() -> str | None:
    """The web-ifc version tools/webifc/package-lock.json pins."""
    lock = WEBIFC / "package-lock.json"
    if not lock.exists():
        return None
    return json.loads(lock.read_text(encoding="utf-8"))["packages"].get("node_modules/web-ifc", {}).get("version")


def webifc_installed() -> str | None:
    pkg = WEBIFC / "node_modules" / "web-ifc" / "package.json"
    return json.loads(pkg.read_text(encoding="utf-8"))["version"] if pkg.exists() else None


def webifc_status() -> str | None:
    """None when the second reader can run; otherwise why it can't, and what to do."""
    if _node_wheel() is None:
        return "no Node: the `webifc` dependency group isn't installed (`uv sync --group webifc`)"
    have, want = webifc_installed(), webifc_locked()
    if have is None:
        return "web-ifc isn't installed: run `uv run brownfield bidset --setup-reader` once"
    if have != want:
        return f"web-ifc {have} is installed but the lock pins {want}: rerun `uv run brownfield bidset --setup-reader`"
    return None


def webifc_ready() -> bool:
    return webifc_status() is None


def setup_webifc() -> int:
    """Install web-ifc from tools/webifc's lock file (npm ci, install scripts off), with the Node
    the `webifc` dependency group brings."""
    node = _node_wheel()
    if node is None:
        print("no Node: install the `webifc` dependency group first (`uv sync --group webifc`)")
        return 1
    return node.npm(["ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=str(WEBIFC))


def read_webifc(path: Path) -> dict:
    """What web-ifc finds in the file (tools/webifc/check.mjs), as it reports it. The report comes
    back through a file; whatever web-ifc logs on its own (stdout, stderr) is passed on, and is in
    the error if the reader fails."""
    import subprocess
    import tempfile

    node = _node_wheel()
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "webifc.json"
        try:
            run = node.node([str(WEBIFC / "check.mjs"), str(path), str(report)], return_completed_process=True,
                            capture_output=True, text=True, encoding="utf-8", timeout=NODE_TIMEOUT_S)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"web-ifc reader timed out after {NODE_TIMEOUT_S} s") from e
        logged = (run.stdout + run.stderr).strip()
        if run.returncode != 0 or not report.exists():
            raise RuntimeError(f"web-ifc reader failed ({run.returncode}): {logged[-2000:]}")
        if logged:
            print(f"web-ifc said: {logged[-2000:]}")
        out = json.loads(report.read_text(encoding="utf-8"))
    out["logged"] = logged
    return out


def _ifc_axes(b) -> tuple[np.ndarray, np.ndarray]:
    """web-ifc's y-up box back to the file's z-up axes: (x, y, z) = (wx, -wz, wy)."""
    lo, hi = np.asarray(b[0], float), np.asarray(b[1], float)
    return np.array([lo[0], -hi[2], lo[1]]), np.array([hi[0], -lo[2], hi[1]])


def _num(x) -> float:
    """A number web-ifc reported, or NaN for a missing one (so any comparison with it fails)."""
    return float("nan") if x is None else float(x)


def check_webifc(path: Path, apt: dict, params: dict) -> list[tuple[str, bool, str]]:
    """Hold what web-ifc reads to forge's model, as `check` does with IfcOpenShell: its version is
    the one the lock pins; every element once by class (with subclasses) and name; types, sizes,
    storeys, voids and fillings; every BF_Opening property; the types' U-factors; every box from
    web-ifc's own geometry (to 1 mm); and glazing per flat. A mismatch is a failure, not raised."""
    w = read_webifc(path)
    locked = webifc_locked()
    res = [("web-ifc reads it, at the version the lock pins",
            w.get("schema") == "IFC4" and w.get("reader") == f"web-ifc {locked}",
            f"{w.get('reader')} (lock: {locked}), {w.get('schema')}")]
    ops = {o["id"]: o for o in apt["openings"]}
    parts = {pt["id"]: pt for pt in apt["parts"]}
    hazards = safety_glazing(apt, params)
    marks = types(apt, hazards)
    by = defaultdict(list)
    for e in w["elements"]:
        if e["name"] is None:
            e["name"] = f"<unnamed {e['globalId']}>"
        by[e["cls"]].append(e)
    want = {"IFCWALL": {n for n, pt in parts.items() if pt["kind"].endswith("_wall")},
            "IFCSLAB": {n for n, pt in parts.items() if not pt["kind"].endswith("_wall")},
            "IFCOPENINGELEMENT": set(ops),
            "IFCWINDOW": {n for n, o in ops.items() if o["kind"] == "window"},
            "IFCDOOR": {n for n, o in ops.items() if o["kind"] != "window"}}
    bad = {c: sorted(set(e["name"] for e in by[c]) ^ want[c]) for c in want}
    twice = [c for c in want if len(by[c]) != len({e["name"] for e in by[c]})]
    res.append(("web-ifc: every element of forge's model, once, by class, and nothing else",
                not any(bad.values()) and not twice,
                ", ".join(f"{c} {len(by[c])}" for c in want) + "".join(f"; {c} off: {v[:2]}" for c, v in bad.items() if v)))

    units = [e for c in ("IFCWINDOW", "IFCDOOR") for e in by[c] if e["name"] in ops]
    got = Counter(e["type"] for e in units)
    res.append(("web-ifc: windows and doors by type", got == Counter(mark_of(o, marks, hazards) for o in ops.values()),
                ", ".join(f"{k} {v}" for k, v in sorted(got.items(), key=str))))
    wrong = [e["name"] for e in units if not (abs(_num(e["width"]) - ops[e["name"]]["width_m"]) <= 1e-9
                                              and abs(_num(e["height"]) - ops[e["name"]]["height_m"]) <= 1e-9)]
    res.append(("web-ifc: sizes exact", not wrong, f"{len(units) - len(wrong)} of {len(units)}"))
    storey = [e["name"] for e in units if e["storey"] != f"Level {ops[e['name']]['storey']}"]
    storey += [e["name"] for c in ("IFCWALL", "IFCSLAB") for e in by[c]
               if e["name"] in parts and e["storey"] != f"Level {parts[e['name']]['storey']}"]
    res.append(("web-ifc: every element in its storey", not storey, f"{len(storey)} wrong"))
    hosts = [e["name"] for e in by["IFCOPENINGELEMENT"] if e["name"] in ops and e["voids"] != ops[e["name"]]["wall"]]
    hosts += [e["name"] for e in units if e["fills"] != e["name"]]
    res.append(("web-ifc: every opening voids its own wall and holds its own unit", not hosts, f"{len(hosts)} wrong"))

    def props_match(got: dict | None, o: dict) -> bool:
        if not got:
            return False
        exact = {"Id": o["id"], "Kind": o["kind"], "Glazed": o["glazed"], "Flat": o["flat"] or f"{o['storey']}-stair",
                 "Face": o["face"], "Index": o["index"]}
        return (all(got.get(k) == v for k, v in exact.items())
                and abs(_num(got.get("SillHeightAboveFloor")) - o["sill_above_floor_m"]) <= 1e-9)

    props = [e["name"] for e in units if not props_match(e["psets"].get("BF_Opening"), ops[e["name"]])]
    res.append(("web-ifc: every unit's id, kind, flat, face, index and sill height", not props, f"{len(props)} differ"))
    tps = {t["name"]: t["psets"] for t in w["types"]}
    u_off = []
    for (kind, *_), mark in marks.items():
        ps = tps.get(mark, {}).get("Pset_WindowCommon" if kind == "window" else "Pset_DoorCommon", {})
        if not abs(_num(ps.get("ThermalTransmittance")) - params[U_PARAM[kind]].value * BTU_FT2) <= 1e-9:
            u_off.append(mark)
    res.append(("web-ifc: each type's U-factor is its params value", not u_off, f"{len(marks) - len(u_off)} of {len(marks)}"))

    tol, worst, missing = 1e-3, 0.0, []
    for c in ("IFCWALL", "IFCSLAB", "IFCWINDOW", "IFCDOOR"):
        for e in by[c]:
            if e["name"] not in (parts if c in ("IFCWALL", "IFCSLAB") else ops):
                continue
            box = None if e["bbox"] is None else _ifc_axes(e["bbox"])
            if box is None or not (np.isfinite(box[0]).all() and np.isfinite(box[1]).all()):
                missing.append(e["name"])  # no mesh, or an empty one
                continue
            src = parts[e["name"]] if c in ("IFCWALL", "IFCSLAB") else ops[e["name"]]
            want_lo, want_hi = ((src["lo_m"], src["hi_m"]) if c in ("IFCWALL", "IFCSLAB")
                                else (src["panel_lo_m"], src["panel_hi_m"]))
            worst = max(worst, float(np.abs(box[0] - want_lo).max()), float(np.abs(box[1] - want_hi).max()))
    res.append((f"web-ifc's own geometry: every wall, slab, window and door where forge has it (to {tol * 1e3:g} mm)",
                worst < tol and not missing,
                f"worst {worst * 1e3:.4f} mm" + (f"; {len(missing)} without a mesh, first {missing[0]}" if missing else "")))

    glazed, unsized = defaultdict(float), 0
    for e in units:
        p = e["psets"].get("BF_Opening") or {}
        if p.get("Glazed") and not str(p.get("Flat", "")).endswith("stair"):
            if e["width"] is None or e["height"] is None:
                unsized += 1
                continue
            glazed[p["Flat"]] += e["width"] * e["height"]
    flats = {fl["name"]: fl["glazed_m2"] for fl in apt["flats"]}
    off = max((abs(glazed.get(n, 0.0) - g) for n, g in flats.items()), default=0.0)
    res.append(("web-ifc: glazing per flat equals pass 3b's flat_envelope",
                off < 1e-9 and set(glazed) == set(flats) and not unsized,
                f"{len(glazed)} flats glazed of {len(flats)}, worst {off:.2e} m2"
                + (f"; {unsized} glazed units without a size" if unsized else "")))
    return res
