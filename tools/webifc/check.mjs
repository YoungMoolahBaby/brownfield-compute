// Pass 3f (D27): read the walk-up's IFC with That Open's web-ifc, a parser and geometry kernel
// independent of IfcOpenShell (which wrote the file), and write what it finds as JSON to a file
// (not stdout, where web-ifc logs its own messages). `brownfield bidset` compares it with forge's
// model (bidset.check_webifc); nothing is judged here.
//
//   uv run python -m nodejs_wheel tools/webifc/check.mjs out/pass3/bidset/apartment.ifc report.json
//
// Every element (walls, slabs, openings, windows, doors) with its class, name, GlobalId, type,
// storey, overall size, the wall it voids or the opening it fills, its property sets, and its
// bounding box from web-ifc's own meshes (none for openings, which web-ifc cuts, not draws, nor
// for a mesh with no vertices). Each class is read with its subclasses, as IfcOpenShell's by_type.
// Coordinates are as web-ifc gives them: its meshes are y-up, so `axes` says so for the reader.

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const WebIFC = require("web-ifc");
const here = path.dirname(fileURLToPath(import.meta.url));
const version = JSON.parse(fs.readFileSync(path.join(here, "node_modules/web-ifc/package.json"), "utf8")).version;

const [file, report] = process.argv.slice(2);
if (!file || !report) {
  console.error("usage: check.mjs <file.ifc> <report.json>");
  process.exit(2);
}

const api = new WebIFC.IfcAPI();
await api.Init(undefined, true);
// OpenModel returns -1 for a file it can't open, or throws (a file with no IFC header).
let model = -1, why = "";
try {
  model = api.OpenModel(new Uint8Array(fs.readFileSync(file)), { COORDINATE_TO_ORIGIN: false });
} catch (err) {
  why = `: ${err.message}`;
}
if (model < 0) {
  console.error(`web-ifc could not open ${file}${why}`);
  process.exit(3);
}

const ids = (type) => {
  const v = api.GetLineIDsWithType(model, type, true);
  return Array.from({ length: v.size() }, (_, i) => v.get(i));
};
const line = (id) => api.GetLine(model, id, false);
const val = (x) => (x === null || x === undefined ? null : typeof x === "object" && "value" in x ? x.value : x);
const refs = (x) => (Array.isArray(x) ? x : x ? [x] : []).map((r) => r.value);

// Property sets: name -> {property: value}, from the set's single values.
function psetOf(id) {
  const ps = line(id);
  const props = {};
  for (const q of refs(ps.HasProperties)) {
    const p = line(q);
    props[val(p.Name)] = val(p.NominalValue);
  }
  return [val(ps.Name), props];
}

const kinds = {
  IFCWALL: WebIFC.IFCWALL, IFCSLAB: WebIFC.IFCSLAB, IFCOPENINGELEMENT: WebIFC.IFCOPENINGELEMENT,
  IFCWINDOW: WebIFC.IFCWINDOW, IFCDOOR: WebIFC.IFCDOOR,
};
const el = new Map(); // expressID -> record
for (const [cls, type] of Object.entries(kinds)) {
  for (const id of ids(type)) {
    const e = line(id);
    el.set(id, {
      cls, ifcClass: api.GetNameFromTypeCode(api.GetLineType(model, id)), name: val(e.Name), globalId: val(e.GlobalId),
      width: val(e.OverallWidth) ?? null, height: val(e.OverallHeight) ?? null,
      type: null, storey: null, voids: null, fills: null, psets: {}, bbox: null,
    });
  }
}
const name = (id) => val(line(id).Name);

for (const id of ids(WebIFC.IFCRELDEFINESBYTYPE)) {
  const r = line(id);
  for (const o of refs(r.RelatedObjects)) if (el.has(o)) el.get(o).type = name(r.RelatingType.value);
}
for (const id of ids(WebIFC.IFCRELCONTAINEDINSPATIALSTRUCTURE)) {
  const r = line(id);
  for (const o of refs(r.RelatedElements)) if (el.has(o)) el.get(o).storey = name(r.RelatingStructure.value);
}
for (const id of ids(WebIFC.IFCRELVOIDSELEMENT)) {
  const r = line(id);
  const o = r.RelatedOpeningElement.value;
  if (el.has(o)) el.get(o).voids = name(r.RelatingBuildingElement.value);
}
for (const id of ids(WebIFC.IFCRELFILLSELEMENT)) {
  const r = line(id);
  const o = r.RelatedBuildingElement.value;
  if (el.has(o)) el.get(o).fills = name(r.RelatingOpeningElement.value);
}
for (const id of ids(WebIFC.IFCRELDEFINESBYPROPERTIES)) {
  const r = line(id);
  const [n, props] = psetOf(r.RelatingPropertyDefinition.value);
  for (const o of refs(r.RelatedObjects)) if (el.has(o)) el.get(o).psets[n] = props;
}

const types = [];
for (const type of [WebIFC.IFCWINDOWTYPE, WebIFC.IFCDOORTYPE, WebIFC.IFCWALLTYPE]) {
  for (const id of ids(type)) {
    const t = line(id);
    types.push({ name: val(t.Name), psets: Object.fromEntries(refs(t.HasPropertySets).map(psetOf)) });
  }
}

// Bounding boxes from web-ifc's meshes: each placed geometry's vertices (x, y, z, nx, ny, nz)
// through its column-major 4x4 transformation.
api.StreamAllMeshes(model, (mesh) => {
  const rec = el.get(mesh.expressID);
  if (!rec) return;
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  let seen = 0;
  for (let g = 0; g < mesh.geometries.size(); g++) {
    const pg = mesh.geometries.get(g);
    const geom = api.GetGeometry(model, pg.geometryExpressID);
    const v = api.GetVertexArray(geom.GetVertexData(), geom.GetVertexDataSize());
    const m = pg.flatTransformation;
    for (let i = 0; i < v.length; i += 6) {
      seen++;
      const [x, y, z] = [v[i], v[i + 1], v[i + 2]];
      const w = [m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13], m[2] * x + m[6] * y + m[10] * z + m[14]];
      for (let k = 0; k < 3; k++) {
        lo[k] = Math.min(lo[k], w[k]);
        hi[k] = Math.max(hi[k], w[k]);
      }
    }
    geom.delete();
  }
  rec.bbox = seen ? [lo, hi] : null;
});

const counts = {};
for (const r of el.values()) counts[r.cls] = (counts[r.cls] ?? 0) + 1;
const out = {
  reader: `web-ifc ${version}`, schema: api.GetModelSchema(model), axes: "y-up (web-ifc's meshes)",
  coordination_matrix: api.GetCoordinationMatrix(model), counts, types, elements: [...el.values()],
};
api.CloseModel(model);
fs.writeFileSync(report, JSON.stringify(out));
