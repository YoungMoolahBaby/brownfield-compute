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


def types(apt: dict) -> dict[tuple, str]:
    """Type marks by (kind, width, height): windows W1, W2... by size, then doors D1, D2... by
    kind (patio, entry) and size."""
    sizes = sorted({(KINDS.index(o["kind"]), o["width_m"], o["height_m"]) for o in apt["openings"]})
    marks, n = {}, Counter()
    for k, w, h in sizes:
        letter = "W" if KINDS[k] == "window" else "D"
        n[letter] += 1
        marks[(KINDS[k], w, h)] = f"{letter}{n[letter]}"
    return marks


def mark_of(o: dict, marks: dict) -> str:
    return marks[(o["kind"], o["width_m"], o["height_m"])]


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

    # Window and door types.
    marks = types(apt)
    type_of = {}
    for (kind, w, h), mark in sorted(marks.items(), key=lambda kv: kv[1]):
        cls = "IfcWindowType" if kind == "window" else "IfcDoorType"
        attrs = {"PredefinedType": "WINDOW" if kind == "window" else "DOOR"}
        e = _make(f, cls, f"type/{mark}", mark, **attrs,
                  Description=f"{NAMES[kind]}, {w / IN:g} x {h / IN:g} in.")
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
        mark = mark_of(o, marks)
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
            "SillHeightAboveFloor": f.createIfcLengthMeasure(o["sill_above_floor_m"])})

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


def check(path: Path, apt: dict) -> list[tuple[str, bool, str]]:
    """Read the IFC back and hold it to forge's model: every part, opening and unit there and
    nothing else, counts and types, sizes, every element where forge has it (to 1 mm), no clashes,
    glazing per flat against pass 3b, unique GlobalIds, and IfcOpenShell's schema validation with
    the express rules. A mismatch is reported as a failure, not raised."""
    f = ifcopenshell.open(str(path))
    res = []
    ops = {o["id"]: o for o in apt["openings"]}
    parts = {pt["id"]: pt for pt in apt["parts"]}
    marks = types(apt)
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
    want = Counter(mark_of(o, marks) for o in ops.values())
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
    marks = types(apt)
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
    res.append(("web-ifc: windows and doors by type", got == Counter(mark_of(o, marks) for o in ops.values()),
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
