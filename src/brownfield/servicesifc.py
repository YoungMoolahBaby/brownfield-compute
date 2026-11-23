"""Pass 3g step 7d (D28): the walk-up's services as IFC, and the schedules read back from it.

The services model is a file of its own beside the bid set's and the frame's (same storeys, same
origin), built from:
- **forge's routes** (7b, `out/pass3/routes.json`) as 7c reads them (`routed.Tree`): each run cut
  into its pieces between junctions, each piece a segment swept along the polyline forge routed
  (`IfcPipeSegment`, `IfcDuctSegment`, `IfcCableCarrierSegment` for the feeders' conduit,
  `IfcCableSegment` for the branch circuits' cable);
- **the sizes the designs give those pieces on the routes** (7c): the sprinklers' branch lines,
  feeds, riser and main; each duct piece Manual D sizes; the water and the loop's mains edge by
  edge; each circuit's wire and each feeder's conduit;
- **the fittings each material takes** where the route bends or branches (`fittings`): a fitting
  at each bend of CPVC, cast iron, PVC, duct and conduit; PEX bent on a support at its bends, with
  elbows only where 7c counted them; nothing for cable or the copper line sets, which are bent;
- **what 7a placed** for the routes to reach: the pinned verticals (stacks, vent stacks, risers,
  the line sets' and feeders' risers, the fire riser), the closet bends and standpipes, the
  equipment, and the fixtures on the plumbing walls; the sprinklers where 7b left them; a register
  or grille at each duct's outlet; the 12 water-level switches 7c found IMC 307.2.3 asks.

Each element carries `BF_Service` (its system, layer, run, piece, size, material and what the
schedules need) and is grouped into its `IfcDistributionSystem`. `check` reads the file back: every
piece once and where forge routed it (to 1 mm), every other element where 7a put it, schema valid
with express rules, and web-ifc's own geometry of each element where it should be. `schedules`
works the schedules from the file read back; the firestop schedule counts each penetration of a
rated assembly from the file's own geometry (`routecheck.penetration_hits`).

Not in it: the ports that connect one element to the next (IfcDistributionPort), the mechanical
room's wall-hung assemblies (the riser assembly, the backflow preventers, the plate exchangers,
the pumps, the mixing valve: the routes end at them, 7a gave them no boxes), the smoke alarms
(step 6 counts them by room; nothing places them), and the outlets and switches at the branch
circuits' ends.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import OUT_DIR

FT, IN = 0.3048, 0.0254
OUT = OUT_DIR / "pass3" / "services"
REVISION = "addendum-5"  # the frame the services are routed through (routing.FRAME); it keys their GlobalIds
# The addendum that issues this services model: Addendum 5 issued the first (services-addendum-5.ifc,
# published as it was); Addendum 7 (pass 3g step 9d) the revised one, each flat's hot-water loop and
# the plant's tanks and backup heater in it.
ISSUE = "addendum-7"
S = "systems.services."

# Each system: IfcDistributionSystem's type, its name, the viewer's layer.
SYSTEMS = {
    "sprinkler": ("FIREPROTECTION", "Sprinklers (NFPA 13R)", "sprinklers"),
    "cold": ("DOMESTICCOLDWATER", "Cold water", "plumbing"),
    "hot": ("DOMESTICHOTWATER", "Hot water and its return", "plumbing"),
    "drain": ("SEWAGE", "Drains", "plumbing"),
    "vent": ("VENT", "Vents", "plumbing"),
    "condensate": ("DRAINAGE", "The mini-splits' condensate", "hvac"),
    "loop": ("HEATING", "The building loop (radiant floors)", "hvac"),
    "ventilation": ("VENTILATION", "Ventilation (the ERVs)", "hvac"),
    "air": ("AIRCONDITIONING", "The mini-splits' ducts", "hvac"),
    "refrigerant": ("REFRIGERATION", "The mini-splits' line sets", "hvac"),
    "power": ("ELECTRICAL", "Feeders and branch circuits", "electrical"),
}
LAYERS = {"plumbing": "Plumbing", "hvac": "Heating, cooling and air", "electrical": "Wiring", "sprinklers": "Sprinklers"}

# The materials, as steps 3-6 and 7a chose them (each design's module says where from).
MATERIAL = {
    "cpvc": "CPVC sprinkler pipe, SDR 13.5 (BlazeMaster), solvent-cemented",  # fire.cpvc
    "pex": "PEX-a with cold-expansion fittings (Uponor ProPEX EP)",  # plumbing.ep_fittings
    "pex_pre": "PEX-a, pre-insulated under the slab (Uponor ProPEX EP fittings)",  # plumbing / hvac.routed_loop
    "cast_iron": "cast iron, no-hub",  # routing.closet_bend_od_in: step 4's stacks are cast iron
    "pvc": "PVC Schedule 40",  # routing.condensate_od_in
    "duct": "round galvanized steel duct",  # ducts.roughness_ft: galvanized; Field Controls' rigid-duct fittings
    "copper": "soft copper tube, each line insulated, with its control cable",  # routing.line_set_od_in
    "conduit": "rigid PVC conduit, Schedule 40, copper THHN/THWN-2",  # electrical.conduit_for
    "nm": "NM-B cable, copper",  # routing.nm_od_in
}


def nominal(x: float | str | None) -> str:
    """A nominal size in inches as the trade writes it: 0.75 -> '3/4', 1.25 -> '1-1/4'."""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    whole, frac = int(x + 1e-9), x - int(x + 1e-9)
    f = {0.0: "", 0.125: "1/8", 0.25: "1/4", 0.375: "3/8", 0.5: "1/2", 0.625: "5/8", 0.75: "3/4", 0.875: "7/8"}
    k = min(f, key=lambda v: abs(v - frac))
    if abs(k - frac) > 1e-6:
        return f"{x:g}"
    return f"{whole}-{f[k]}" if whole and f[k] else (str(whole) if whole else f[k])


@dataclass
class El:
    """One element of the services model, before it's written."""
    key: str
    cls: str
    pre: str
    name: str
    system: str
    geom: tuple  # ("sweep", points, diameter) or ("box", lo, hi)
    props: dict = field(default_factory=dict)
    obj: str | None = None  # ObjectType, for a USERDEFINED predefined type


# ---- A routed run's pieces ----

def piece_points(tree, n: int) -> list[list[float]]:
    return tree.piece(n)


def polyline_m(pts) -> float:
    return sum(math.dist(a, c) for a, c in zip(pts, pts[1:]))


def _bends_at(tree, n: int) -> list[tuple[list[float], list[float], list[float]]]:
    """The bends of edge `n` as forge routed them (each a vertex of its branch where the direction
    changes, as `Branch.turns` counts them): (the point before, the corner, the point after)."""
    e = tree.edges[n]
    br = tree.branches[e.branch]
    out = []
    for k in range(1, len(br.points) - 1):
        s = br.cum[k]
        if not (e.s0 - 1e-9 <= s < e.s1 - 1e-9 and s > 1e-9):
            continue
        a, b, c = br.points[k - 1], br.points[k], br.points[k + 1]
        u = np.subtract(b, a)
        v = np.subtract(c, b)
        if np.linalg.norm(np.cross(u, v)) > 1e-6 * max(1e-12, np.linalg.norm(u) * np.linalg.norm(v)):
            out.append((list(a), list(b), list(c)))
    return out


def _holes(tree, rec: dict, n: int) -> int:
    """forge's bores (holes through members) along edge `n`: those of its branch between its ends
    (the branch's last edge takes any at its very end)."""
    e = tree.edges[n]
    br = tree.branches[e.branch]
    last = e.s1 >= br.length - 1e-9
    at = [br.where(b["at"], 3)[1] for b in rec["branches"][e.branch].get("bores", [])]
    return sum(1 for s in at if e.s0 - 1e-6 <= s < e.s1 - 1e-6 or (last and s >= e.s1 - 1e-6))


# ---- What each run is, and the size of each piece ----

class Designs:
    """7c's designs on the routes, and what steps 3-6 and 7a fix, for the pieces' sizes."""

    def __init__(self, apt: dict, p: dict, routes, s7: dict) -> None:
        from . import plumbing
        from .plumbing import stacks as columns

        self.apt, self.p, self.routes, self.s7 = apt, p, routes, s7
        self.fire = s7["fire"]["sizes"]
        self.water = s7["water"]
        self.loop = s7["loop"]
        self.ducts = s7["ducts"]
        self.el = s7["electrical"]
        self.vents = s7["vents"]
        self.cols = columns(apt)
        self.drains = plumbing.drains_and_vents(apt, p)

    def loop_in(self, gpm: float) -> float:
        from .hvac import pipe_for_flow

        return pipe_for_flow(gpm, self.p)[0]

    def feeder(self, flat: str) -> dict:
        from .electrical import conduit_for

        f = self.el["feeders"][flat]
        c = conduit_for([f["size"]] * 3 + [f["egc"]], self.p)
        return {"trade": c["trade"], "text": f"{c['trade']} in. conduit, three {f['size']} AWG and a {f['egc']} AWG ground",
                "od_in": c["od_in"]}

    def circuit(self, flat: str, key: str) -> dict:
        return next(c for c in self.el["panels"][flat]["circuits"] if c["key"] == key)


def run_kind(req: dict) -> tuple[str, str, str, str]:
    """A run's (system, IFC class, predefined type, material)."""
    s, role = req["system"], req.get("role")
    if s == "sprinkler":
        return "sprinkler", "IfcPipeSegment", "RIGIDSEGMENT", "cpvc"
    if s == "water":
        return ("hot" if role == "hot-return" else role), "IfcPipeSegment", "FLEXIBLESEGMENT", "pex"
    if s == "main":
        k = req["kind"]
        return ("hot" if k == "hot-return" else "loop" if k.startswith("loop") else k), "IfcPipeSegment", "FLEXIBLESEGMENT", "pex_pre"
    if s == "hydronic":
        return "loop", "IfcPipeSegment", "FLEXIBLESEGMENT", "pex"
    if s in ("drain", "vent"):
        return s, "IfcPipeSegment", "RIGIDSEGMENT", "cast_iron"
    if s == "condensate":
        return "condensate", "IfcPipeSegment", "RIGIDSEGMENT", "pvc"
    if s == "duct":
        return ("air" if role == "ms-supply" else "ventilation"), "IfcDuctSegment", "RIGIDSEGMENT", "duct"
    if s == "line-set":
        return "refrigerant", "IfcPipeSegment", "FLEXIBLESEGMENT", "copper"
    if s == "feeder":
        return "power", "IfcCableCarrierSegment", "CONDUITSEGMENT", "conduit"
    if s == "cable":
        return "power", "IfcCableSegment", "CABLESEGMENT", "nm"
    raise ValueError(f"{req['id']}: no kind for system {s!r}")


def piece_size(req: dict, tree, n: int, D: Designs) -> tuple[float | str | None, str]:
    """A piece's nominal size (in., or a text), and where it comes from."""
    s, role, flat = req["system"], req.get("role"), req.get("flat")
    e = tree.edges[n]
    p = D.p
    if s == "sprinkler":
        if req["id"] == "fire/main":
            part = "main"
        elif req["id"].startswith("fire/stair/"):
            part = "branch" if all(t.startswith("stair/") for t in e.below) else "feed"
        else:
            part = "branch" if len(e.below) == 1 else "feed"
        return D.fire[part], f"7c's sprinkler {part}"
    if s == "water":
        if role == "hot-return":
            return D.water["loop"]["flat_return_in"], "the flat's loop's return (Addendum 7), at its share of the loop's flow"
        if role == "hot" and len(e.below) == 1:
            from .plumbing import fixture_hot_in

            return fixture_hot_in(e.below[0], p), "its fixture's own (Appendix E at that fixture's demand; 9c)"
        return D.water["paths"][role]["sizes"]["branch"], "step 4's branch, held on the routes (7c)"
    if s == "main":
        k = req["kind"]
        if k in ("cold", "hot"):
            return D.water["paths"][k]["sizes"]["main_edges"][n], "7c's main, edge by edge"
        if k == "hot-return":
            return D.water["loop"]["return_main_in"], "7c's return main"
        q = sum(D.loop["flats"][m]["gpm"] for c in e.below for m in D.cols[c])
        return D.loop_in(q), "7c's loop main, edge by edge (its flow's)"
    if s == "hydronic":
        return D.loop_in(D.loop["flats"][flat]["gpm"]), "7c's tail to the manifold"
    if s == "drain":
        return req["size_in"], "step 4's drain, as routed"
    if s == "vent":
        return D.vents["flats"][flat]["routed_in"], "7c's branch vent (IPC 906.2)"
    if s == "condensate":
        return _pvc_nominal(p["systems.routing.condensate_od_in"]), "7a's condensate"
    if s == "duct":
        d = D.ducts[flat]
        if role in ("erv-oa", "erv-ea"):
            key, what = ("erv_supply", "oa") if role == "erv-oa" else ("erv_exhaust", "ea")
            return next(c for c in d[key]["common"] if c["what"] == what)["in"], "7c's ERV duct to its wall cap"
        key = {"erv-supply": "erv_supply", "erv-exhaust": "erv_exhaust", "ms-supply": "ms"}[role]
        pieces = d[key]["pieces"]
        if len(pieces) != len(tree.edges):
            raise ValueError(f"{req['id']}: {len(pieces)} Manual D pieces for {len(tree.edges)} edges")
        size = pieces[n]["in"]
        return (size if size is not None else "plenum"), "7c's Manual D piece" if size is not None else "the supply plenum (7c)"
    if s == "line-set":
        return f"{nominal(p[S + 'line_set_liquid_in'])} and {nominal(p[S + 'line_set_gas_in'])}", "Fujitsu's line set"
    if s == "feeder":
        return D.feeder(flat)["trade"], "7c's feeder, its conduit by NEC Chapter 9"
    if s == "cable":
        return f"{D.circuit(flat, req['circuit'])['awg']} AWG", "7c's circuit"
    raise ValueError(req["id"])


def _pvc_nominal(od_in: float) -> str:
    """Schedule 40 PVC's trade size for its outside diameter (Wavin's sheet, `data/pvc_sched40_od.csv`:
    pipe and conduit share the iron-pipe sizes' diameters)."""
    from .electrical import _table_rows

    r = min(_table_rows("pvc_sched40_od.csv"), key=lambda r: abs(float(r["od_in"]) - od_in))
    if abs(float(r["od_in"]) - od_in) > 0.01:
        raise ValueError(f"no Schedule 40 size of {od_in} in. outside diameter")
    return r["trade_size"]


# ---- Fittings: what each material takes at a bend and where a branch leaves ----

def _dir(a, b) -> np.ndarray:
    v = np.subtract(b, a)
    return v / max(np.linalg.norm(v), 1e-12)


def _vertical(v) -> bool:
    return abs(v[2]) > 0.7


def dwv_bend(flow_in, flow_out) -> str:
    """A drain's bend by IPC 2021 Table 706.3, from its change in direction: horizontal to vertical
    takes a quarter bend; vertical to horizontal and horizontal to horizontal a long sweep, allowed in
    every direction (a quarter bend is allowed there only on a fixture drain of 2 in. or smaller, a
    short sweep vertical to horizontal also at 3 in. and up)."""
    if not _vertical(flow_in) and _vertical(flow_out):
        return "quarter bend (horizontal to vertical)"
    return "long sweep (" + ("vertical" if _vertical(flow_in) else "horizontal") + " to horizontal)"


def dwv_junction(branch_flow, run_dir) -> str:
    """Where a drain branch joins (IPC 2021 Table 706.3): into a vertical, from a horizontal, a
    sanitary tee; otherwise a combination wye and eighth bend (allowed in every direction)."""
    if _vertical(run_dir) and not _vertical(branch_flow):
        return "sanitary tee (horizontal to vertical)"
    return "combination wye and eighth bend"


def fittings(req: dict, tree, n: int, size, top_of_column: bool) -> list[dict]:
    """The fittings on edge `n`: each {kind, at (corner or junction), dirs (the two directions
    through it), size}. Where nothing is fitted, as on PEX's sweeps, the bend is counted on the
    piece instead (BF_Service Sweeps)."""
    s, role = req["system"], req.get("role")
    e = tree.edges[n]
    pts = piece_points(tree, n)
    out = []
    bends = _bends_at(tree, n)
    for a, b, c in bends:
        if s in ("cable", "line-set"):
            continue
        if s in ("water", "main", "hydronic"):
            continue  # a sweep on a bend support (7c), counted on the piece
        if s == "drain":
            # Flow runs toward the root: in along (c -> b), out along (b -> a).
            kind = dwv_bend(_dir(c, b), _dir(b, a))
        elif s == "vent":
            kind = "quarter bend"
        elif s == "duct":
            kind = "90° elbow"
        elif s == "feeder":
            kind = "90° elbow (factory)"
        else:
            kind = "90° elbow"
        out.append({"kind": kind, "at": b, "dirs": [_dir(a, b), _dir(b, c)]})
    if e.tee == "branch":
        j = pts[0]
        par = tree.branches[tree.branches[e.branch].parent]
        _, sp = par.where(j, 3)
        run_dir = _dir(par.point_at(max(0.0, sp - 0.05)), par.point_at(min(par.length, sp + 0.05)))
        out_dir = _dir(pts[0], pts[1]) if len(pts) > 1 else run_dir
        if s == "drain":
            kind = dwv_junction(-out_dir, run_dir)
        elif s == "duct":
            kind = "take-off"
        elif s in ("sprinkler", "water", "main", "vent", "condensate"):
            kind = "tee"
        else:
            kind = None
        if kind:
            out.append({"kind": kind, "at": j, "dirs": [run_dir, run_dir]})  # drawn along the run it sits on
    # PEX's elbows, where 7c counts them (plumbing.routed_paths, hvac.routed_loop): each fixture's
    # stub-out; where the main turns up into a riser; where the top flat's branch leaves the riser's
    # end; where a tail reaches its manifold.
    if s in ("water", "main", "hydronic"):
        if e.terminal is not None:
            out.append({"kind": "elbow", "at": pts[-1], "dirs": [_dir(pts[-2], pts[-1]), np.array([0.0, 0.0, 1.0])]})
        if e.up is None and top_of_column and s in ("water", "hydronic"):
            out.append({"kind": "elbow", "at": pts[0], "dirs": [np.array([0.0, 0.0, 1.0]), _dir(pts[0], pts[1])]})
    if s == "duct" and e.terminal is not None and role in ("ms-supply", "erv-exhaust"):
        out.append({"kind": "boot", "at": pts[-1], "dirs": [_dir(pts[-2], pts[-1]), _dir(pts[-2], pts[-1])]})
    for f in out:
        f["size"] = size
    return out


FITTING_CLASS = {"IfcPipeSegment": "IfcPipeFitting", "IfcDuctSegment": "IfcDuctFitting", "IfcCableCarrierSegment": "IfcCableCarrierFitting"}


def _fitting_pre(cls: str, kind: str) -> str:
    junction = kind.startswith(("tee", "take-off", "sanitary tee", "combination"))
    if cls == "IfcCableCarrierFitting":
        return "TEE" if junction else "BEND"
    if kind == "boot":
        return "TRANSITION"
    return "JUNCTION" if junction else "BEND"


def _fitting_geom(f: dict, d: float) -> list[list[float]]:
    """A fitting drawn as a short, fatter piece through its point along its two directions."""
    leg = max(d, 0.03)
    at = np.asarray(f["at"], float)
    u, v = (np.asarray(x, float) for x in f["dirs"])
    if np.linalg.norm(np.cross(u, v)) < 1e-6:
        return [list(at - u * leg), list(at + u * leg)]
    return [list(at - u * leg), list(at), list(at + v * leg)]


# ---- The model's elements ----

def storey_of(apt: dict, z: float) -> int:
    return int(min(max(math.floor(z / apt["storey_m"] + 1e-9) + 1, 1), apt["storeys"]))


def _centre_line(o: dict) -> tuple[list[float], list[float], float]:
    cx, cy = (o["lo"][0] + o["hi"][0]) / 2, (o["lo"][1] + o["hi"][1]) / 2
    return [cx, cy, o["lo"][2]], [cx, cy, o["hi"][2]], min(o["hi"][0] - o["lo"][0], o["hi"][1] - o["lo"][1])


def elements(apt: dict, p: dict, routes, s7: dict, placed: dict) -> list[El]:
    """Every element of the services model (`placed`: routing.placements)."""
    from .fire import layout, stair_heads
    from .routing import strip_soffits

    D = Designs(apt, p, routes, s7)
    out: list[El] = []
    tops = {max(names, key=lambda m: int(m.split("-", 1)[0])) for names in D.cols.values()}
    # -- The routed runs: a segment for each piece, the fittings on it.
    for rid in sorted(routes.recs):
        req, rec = routes.reqs[rid], routes.recs[rid]
        t = routes.tree(rid)
        system, cls, pre, mat = run_kind(req)
        for n, e in enumerate(t.edges):
            pts = piece_points(t, n)
            size, basis = piece_size(req, t, n, D)
            d = req["od_m"]
            sweeps = e.bends if req["system"] in ("water", "main", "hydronic") else 0
            props = {"System": system, "Layer": SYSTEMS[system][2], "Run": rid, "Piece": n, "Size": nominal(size), "SizeBasis": basis,
                     "Material": MATERIAL[mat], "OutsideDiameter": d, "Length": polyline_m(pts), "Bends": e.bends, "Sweeps": sweeps,
                     "Holes": _holes(t, rec, n), "Leaves": e.tee, "Terminal": e.terminal or "", "Flat": req.get("flat") or ""}
            if req["system"] == "cable":
                c = D.circuit(req["flat"], req["circuit"])
                props.update({"Circuit": req["circuit"], "Breaker": c["breaker_a"], "Poles": c["poles"]})
            if req["system"] == "feeder":
                props["Conductors"] = D.feeder(req["flat"])["text"]
            name = f"{rid} #{n}"
            out.append(El(f"run/{rid}/{n}", cls, pre, name, system, ("sweep", pts, d), props))
            fcls = FITTING_CLASS.get(cls)
            if not fcls:
                continue
            for k, f in enumerate(fittings(req, t, n, size, req.get("flat") in tops)):
                fp = {"System": system, "Layer": SYSTEMS[system][2], "Run": rid, "Piece": n, "Kind": f["kind"], "Size": nominal(size),
                      "Material": MATERIAL[mat], "Flat": req.get("flat") or ""}
                out.append(El(f"fit/{rid}/{n}/{k}", fcls, _fitting_pre(fcls, f["kind"]), f"{f['kind']}, {rid} #{n}", system,
                              ("sweep", _fitting_geom(f, d), d * 1.25), fp))
    # -- Each flat's balancing valve (Addendum 7), in its vanity: between the lavatory's hot stub and
    # its loop's return stub, in front of the wall, at the stubs' height.
    from .plumbing import LOOP_END

    L_, H_ = p["systems.hot_water.tbv_length_in"] * 0.0254, p["systems.hot_water.tbv_height_in"] * 0.0254
    for f in apt["flats"]:
        rid = f"plumbing/hot-return/{f['name']}"
        if rid not in routes.recs:
            continue
        hb = next(b for b in routes.tree(f"plumbing/hot/{f['name']}").branches if b.terminal == LOOP_END)
        rb = next(b for b in routes.tree(rid).branches if b.terminal == LOOP_END)
        fv = placed["fixtures"][f["name"]][LOOP_END]
        y = (hb.points[-1][1] + rb.points[-1][1]) / 2
        z = (hb.points[-1][2] + rb.points[-1][2]) / 2
        x0 = fv["x"] + fv["into"] * 0.0254
        x1 = x0 + fv["into"] * H_
        lo, hi = [min(x0, x1), y - L_ / 2, z - H_ / 2], [max(x0, x1), y + L_ / 2, z + H_ / 2]
        out.append(El(f"valve/{f['name']}/balancing", "IfcValve", "REGULATING", f"thermostatic balancing valve, {f['name']}", "hot",
                      ("box", lo, hi), {"System": "hot", "Layer": SYSTEMS["hot"][2], "Flat": f["name"], "Kind": "thermostatic balancing valve",
                                        "Size": nominal(D.water["loop"]["flat_return_in"]), "Model": "Caleffi ThermoSetter 116 series (basis of design)",
                                        "Setting": f"{p['systems.hot_water.tbv_set_f']:g} F", "Access": "the vanity's doors (IECC C404.6)"}))
    # -- The pinned verticals and fixed pieces 7a placed (the router's own boxes).
    w = D.water
    for o in routes.body["obstacles"]:
        oid, tail = o["id"], o["id"].split("/", 1)[1]
        col = oid.split("/", 1)[0]
        a, b, dia = _centre_line(o)
        base = {"Run": oid, "Piece": 0, "Flat": "", "OutsideDiameter": dia, "Length": b[2] - a[2], "Bends": 0, "Sweeps": 0, "Holes": 0}
        pinned = {
            "stack": ("drain", D.drains["stack_in"], "cast_iron", "drain stack"),
            "vent-stack": ("vent", p[S + "vent_stack_in"], "cast_iron", "vent stack (IPC 905.1)"),
            "hot": ("hot", w["paths"]["hot"]["sizes"]["riser"], "pex", "hot riser"),
            "hot-return": ("hot", w["loop"]["return_riser_in"], "pex", "hot-water return riser"),
            "cold": ("cold", w["paths"]["cold"]["sizes"]["riser"], "pex", "cold riser"),
            "loop-supply": ("loop", None, "pex", "building loop supply riser"),
            "loop-return": ("loop", None, "pex", "building loop return riser"),
        }
        if tail in pinned:
            system, size, mat, what = pinned[tail]
            if tail.startswith("loop"):
                size = D.loop["risers"][col]["pipe_in"]
            cls, pre = "IfcPipeSegment", ("RIGIDSEGMENT" if mat == "cast_iron" else "FLEXIBLESEGMENT")
            out.append(El(f"pinned/{oid}", cls, pre, f"{what}, {col}", system, ("sweep", [a, b], dia),
                          {"System": system, "Layer": SYSTEMS[system][2], **base, "Size": nominal(size), "Material": MATERIAL[mat],
                           "SizeBasis": "7c's riser" if mat == "pex" else "steps 4 and 7a"}))
        elif tail.startswith("line-set/"):
            flat = tail.split("/", 1)[1]
            size = f"{nominal(p[S + 'line_set_liquid_in'])} and {nominal(p[S + 'line_set_gas_in'])}"
            out.append(El(f"pinned/{oid}", "IfcPipeSegment", "FLEXIBLESEGMENT", f"line set riser, {flat}", "refrigerant", ("sweep", [a, b], dia),
                          {"System": "refrigerant", "Layer": "hvac", **base, "Flat": flat, "Size": size, "Material": MATERIAL["copper"],
                           "SizeBasis": "Fujitsu's line set"}))
        elif tail.startswith("feeder/"):
            flat = tail.split("/", 1)[1]
            fd = D.feeder(flat)
            out.append(El(f"pinned/{oid}", "IfcCableCarrierSegment", "CONDUITSEGMENT", f"feeder riser, {flat}", "power", ("sweep", [a, b], dia),
                          {"System": "power", "Layer": "electrical", **base, "Flat": flat, "Size": fd["trade"], "Material": MATERIAL["conduit"],
                           "Conductors": fd["text"], "SizeBasis": "7c's feeder, its conduit by NEC Chapter 9"}))
        elif oid == "stair/fire-riser":
            out.append(El(f"pinned/{oid}", "IfcPipeSegment", "RIGIDSEGMENT", "the sprinkler riser, in the stair", "sprinkler", ("sweep", [a, b], dia),
                          {"System": "sprinkler", "Layer": "sprinklers", **base, "Size": nominal(D.fire["riser"]), "Material": MATERIAL["cpvc"],
                           "SizeBasis": "7c's sprinkler riser"}))
        elif tail == "wc-bend":
            # The closet bend down from the water closet's flange at the floor and along its joist bay
            # to the stack (7a's box around it: its outlet's centre out from the wall, the stack's).
            wc = placed["fixtures"][col]["wc"]
            r_ = (o["hi"][1] - o["lo"][1]) / 2
            x_out = wc["x"] + wc["into"] * wc["out_m"]
            x_st = o["lo"][0] + r_ if abs(o["lo"][0] + r_ - x_out) > abs(o["hi"][0] - r_ - x_out) else o["hi"][0] - r_
            y, zc = (o["lo"][1] + o["hi"][1]) / 2, o["lo"][2] + r_
            pts = [[x_out, y, o["hi"][2]], [x_out, y, zc], [x_st, y, zc]]
            out.append(El(f"pinned/{oid}", "IfcPipeFitting", "BEND", f"closet bend, {col}", "drain", ("sweep", pts, 2 * r_),
                          {"System": "drain", "Layer": "plumbing", "Run": oid, "Kind": "closet bend", "Size": nominal(3.0), "Flat": col,
                           "Material": MATERIAL["cast_iron"], "OutsideDiameter": 2 * r_}))
        elif tail == "standpipe":
            out.append(El(f"pinned/{oid}", "IfcPipeSegment", "RIGIDSEGMENT", f"washer standpipe, {col}", "drain", ("sweep", [a, b], dia),
                          {"System": "drain", "Layer": "plumbing", **base, "Flat": col,
                           "Size": nominal(placed["fixtures"][col]["washer"]["drain_size"]), "Material": MATERIAL["cast_iron"],
                           "SizeBasis": "the washer's drain (7a)"}))
        elif oid == "stair/roof-ladder":
            continue  # the building's (Addendum 5), not a service
        else:
            out += _equipment(o, D, p)
    # -- Fixtures on the plumbing walls (7a), and each tub's drain down through the floor to where
    #    its routed drain starts in the space under it.
    out += _fixtures(apt, p, placed["fixtures"])
    for rid in sorted(k for k in routes.recs if k.endswith("/tub") and k.startswith("plumbing/drain/")):
        req, t = routes.reqs[rid], routes.tree(rid)
        flat = req["flat"]
        to = next(b.to for b in t.branches if b.terminal == "tub")
        top = placed["fixtures"][flat]["tub"]["floor_z"]
        size = placed["fixtures"][flat]["tub"]["drain_size"]
        out.append(El(f"drop/{flat}/tub", "IfcPipeSegment", "RIGIDSEGMENT", f"tub drain, {flat}", "drain",
                      ("sweep", [[to[0], to[1], top], list(to)], req["od_m"]),
                      {"System": "drain", "Layer": "plumbing", "Run": rid, "Piece": -1, "Flat": flat, "Size": nominal(size),
                       "SizeBasis": "the tub's drain (7a)", "Material": MATERIAL["cast_iron"], "OutsideDiameter": req["od_m"],
                       "Length": top - to[2], "Bends": 0, "Sweeps": 0, "Holes": 0}))
    # -- Sprinklers where 7b left them, with their listing (step 6).
    lay = layout(apt, p, strip_soffits(apt, p))
    stair = {h["storey"]: h for h in stair_heads(apt, p)}
    hd = p[S + "head_draw_in"] * IN
    for rid in sorted(k for k in routes.recs if k.startswith("fire/flat/") or k.startswith("fire/stair/")):
        t = routes.tree(rid)
        for b in t.branches:
            ref = b.terminal
            if ref.startswith("stair/"):
                storey = int(ref.split("/")[1])
                h = stair[storey]
                props = {"Model": "quick-response, K 5.6 (the model to choose)", "K": h["k"], "Room": "stair", "Compartment": "stair",
                         "Flat": "", "Storey": storey}
            elif "#" in ref:
                flat = rid.split("/")[-1]
                h = lay[flat]["heads"][int(ref.rsplit("#", 1)[1])]
                model = "Tyco TY2236, residential pendent" if h["l_ft"] <= 16 else "Tyco TY2334, residential pendent"
                props = {"Model": model, "K": h["k"], "Room": h["room"], "Compartment": h["comp"], "Flat": flat,
                         "Coverage": f"{h['l_ft']:g} x {h['l_ft']:g} ft", "Temperature": h["temp"]}
            else:
                continue
            at = list(b.to)
            out.append(El(f"head/{ref}", "IfcFireSuppressionTerminal", "SPRINKLER", f"sprinkler {ref}", "sprinkler",
                          ("sweep", [at, [at[0], at[1], at[2] - hd / 2]], hd),
                          {"System": "sprinkler", "Layer": "sprinklers", "Run": rid, **props}))
    # -- A register or grille at each duct's outlet; a wall cap at the ERVs' intake and exhaust.
    for rid in sorted(k for k in routes.recs if routes.reqs[k]["system"] == "duct"):
        req, t = routes.reqs[rid], routes.tree(rid)
        system = run_kind(req)[0]
        for b in t.branches:
            if b.terminal == "minisplit":
                continue  # the ERV's supply into the mini-split's return (Broan's kit), no outlet
            d = req["od_m"]
            at = np.asarray(b.to, float)
            lo, hi = at - [d / 2, d / 2, 0.0125], at + [d / 2, d / 2, 0.0125]
            role = req["role"]
            if role in ("erv-oa", "erv-ea"):
                pre, obj, what = "USERDEFINED", "wall cap", f"wall cap ({'intake' if role == 'erv-oa' else 'exhaust'})"
            elif role == "ms-supply":
                pre, obj, what = "REGISTER", None, "supply register"
            else:
                pre, obj, what = "GRILLE", None, "exhaust grille"
            out.append(El(f"air/{rid}/{b.terminal}", "IfcAirTerminal", pre, f"{what}, {b.terminal}", system, ("box", list(lo), list(hi)),
                          {"System": system, "Layer": "hvac", "Run": rid, "Flat": req["flat"], "Kind": what, "Size": nominal(d / IN)}, obj))
    # -- IMC 307.2.3 item 4 (7c): a water-level switch at each mini-split's drain, to its forced stop.
    sw = p[S + "switch_draw_in"] * IN
    for rid in sorted(k for k in routes.recs if k.startswith("hvac/condensate/")):
        t = routes.tree(rid)
        at = np.asarray(next(b.to for b in t.branches if b.terminal == "unit"), float)
        flat = routes.reqs[rid]["flat"]
        out.append(El(f"switch/{flat}", "IfcSensor", "LEVELSENSOR", f"water-level switch, {flat}", "condensate",
                      ("box", list(at - sw / 2), list(at + sw / 2)),
                      {"System": "condensate", "Layer": "hvac", "Run": rid, "Flat": flat,
                       "Kind": "UL 508 water-level switch to the unit's forced stop (IMC 307.2.3 item 4; Fujitsu function 46-02)"}))
    return out


def _equipment(o: dict, D: Designs, p: dict) -> list[El]:
    oid = o["id"]
    who, what = oid.split("/", 1)
    lo, hi = o["lo"], o["hi"]
    base = {"Run": oid, "Flat": who if who[0].isdigit() else ""}
    if what == "washer-dryer":
        mid = (lo[2] + hi[2]) / 2
        return [El(f"eq/{oid}/washer", "IfcElectricAppliance", "WASHINGMACHINE", f"washer, {who}", "drain", ("box", lo, [hi[0], hi[1], mid]),
                   {"System": "drain", "Layer": "plumbing", **base, "Kind": "washer (stacked under the dryer)"}),
                El(f"eq/{oid}/dryer", "IfcElectricAppliance", "TUMBLEDRYER", f"dryer, {who}", "power", ("box", [lo[0], lo[1], mid], hi),
                   {"System": "power", "Layer": "electrical", **base, "Kind": "dryer (stacked over the washer)"})]
    spec = {
        # The makers' models as the parameters' sources name them (routing.erv_l_in, ms_w_in, the
        # wiring's breakers, tank_dia_in, swing_dia_in, hp_w_in).
        "erv": ("IfcAirToAirHeatRecovery", "NOTDEFINED", None, "ventilation", "ERV (Broan EDGE BLP120E80NS-HW, step 3)"),
        "minisplit": ("IfcUnitaryEquipment", "SPLITSYSTEM", None, "air", "mini-split indoor unit, ducted (Fujitsu ARUH12KUAS, step 3)"),
        "outdoor-unit": ("IfcUnitaryEquipment", "SPLITSYSTEM", None, "refrigerant", "mini-split outdoor unit, on the roof"),
        "manifold": ("IfcPipeFitting", "USERDEFINED", "manifold", "loop", "radiant manifold in its cabinet"),
        "panel": ("IfcElectricDistributionBoard", "DISTRIBUTIONBOARD", None, "power",
                  "load centre (Square D QO130L125PG, step 5)"),
        "storage-tank-a": ("IfcTank", "STORAGE", None, "hot",
                           "hot-water storage tank ST-1A, the hot end of two in series (Lochinvar HP150G, basis of design; Addendum 7)"),
        "storage-tank-b": ("IfcTank", "STORAGE", None, "hot",
                           "hot-water storage tank ST-1B, the cold end of two in series (Lochinvar HP150G, basis of design; Addendum 7)"),
        "swing-tank": ("IfcTank", "STORAGE", None, "hot", "swing tank (step 4's basis of design, Bradford White)"),
        "backup-heater": ("IfcBoiler", "WATER", None, "hot",
                          "backup water heater BK-1, electric, on the heater circuit (A. O. Smith DRE-52-12, basis of design; step 9a, "
                          "Addendum 7)"),
        "heat-pump": ("IfcUnitaryEquipment", "USERDEFINED", "water-to-water heat pump", "hot",
                      "water-to-water heat pump (step 4's basis of design, ClimateMaster Tranquility SW036)"),
    }
    if what not in spec:
        raise ValueError(f"{oid}: no equipment of that kind")
    cls, pre, obj, system, kind = spec[what]
    if what == "minisplit":
        kind = kind.replace("step 3)", f"step 3's {D.ducts[who]['unit']})")
    return [El(f"eq/{oid}", cls, pre, f"{kind.split(' (')[0]}, {who}", system, ("box", lo, hi),
               {"System": system, "Layer": SYSTEMS[system][2], **base, "Kind": kind}, obj)]


def _fixtures(apt: dict, p: dict, fx: dict) -> list[El]:
    """The fixtures on each plumbing wall, as boxes off the wall's face (7a's centres; their sizes
    for the drawing are `systems.services`' placeholders where no fixture is chosen)."""
    r, d = "systems.routing.", "systems.design."
    sizes = {  # (width along the wall, depth off it, height), in.
        "wc": (p[S + "wc_w_in"], p[r + "wc_depth_in"], p[S + "wc_h_in"]),
        "lav": (p[S + "lav_w_in"], p[S + "lav_d_in"], p[S + "lav_h_in"]),
        "tub": (p[d + "tub_width_in"], p[d + "tub_length_in"], p[S + "tub_h_in"]),
        "sink": (p[r + "sink_base_in"], p[d + "counter_depth_in"], p[S + "counter_h_in"]),
        "dishwasher": (p[r + "dw_width_in"], p[d + "counter_depth_in"], p[S + "counter_h_in"]),
    }
    kinds = {"wc": ("IfcSanitaryTerminal", "TOILETPAN", "water closet"), "lav": ("IfcSanitaryTerminal", "WASHHANDBASIN", "lavatory"),
             "tub": ("IfcSanitaryTerminal", "BATH", "bathtub"), "sink": ("IfcSanitaryTerminal", "SINK", "kitchen sink"),
             "dishwasher": ("IfcElectricAppliance", "DISHWASHER", "dishwasher")}
    out = []
    for flat, fs in sorted(fx.items()):
        for k, (cls, pre, what) in kinds.items():
            f = fs[k]
            if f["y"] is None:
                continue
            w_, dp, h = (v * IN for v in sizes[k])
            x0, x1 = f["x"], f["x"] + f["into"] * dp
            lo = [min(x0, x1), f["y"] - w_ / 2, f["floor_z"]]
            hi = [max(x0, x1), f["y"] + w_ / 2, f["floor_z"] + h]
            out.append(El(f"fixture/{flat}/{k}", cls, pre, f"{what}, {flat}", "drain", ("box", lo, hi),
                          {"System": "drain", "Layer": "plumbing", "Run": f"{flat}/{k}", "Flat": flat, "Kind": what, "Room": f["room"],
                           "Drawn": "its size a placeholder for the drawing" if k in ("wc", "lav") else "its size from params"}))
    return out


# ---- The IFC ----

def _place_sweeps(f, ctx, product, points, diameter: float) -> None:
    """A pipe, duct or cable along its polyline (m, world): a disk of `diameter` swept along each
    straight run on its own (one item each, so no reader mitres a corner), placed from the first
    point."""
    import ifcopenshell.api.geometry as geometry

    pts = np.asarray(points, float)
    m = np.eye(4)
    m[:3, 3] = pts[0]
    geometry.edit_object_placement(f, product=product, matrix=m, is_si=True)
    rel = [f.createIfcCartesianPoint(tuple(float(v) for v in q - pts[0])) for q in pts]
    items = [f.createIfcSweptDiskSolid(f.createIfcPolyline([a, c]), diameter / 2, None, None, None) for a, c in zip(rel, rel[1:])]
    geometry.assign_representation(f, product=product, representation=f.createIfcShapeRepresentation(ctx, "Body", "AdvancedSweptSolid", items))


def write(els: list[El], apt: dict, path: Path, source: str) -> None:
    import ifcopenshell.api.aggregate as aggregate
    import ifcopenshell.api.context as context
    import ifcopenshell.api.geometry as geometry
    import ifcopenshell.api.project as project
    import ifcopenshell.api.pset as pset
    import ifcopenshell.api.spatial as spatial
    import ifcopenshell.api.system as system_api
    import ifcopenshell.api.unit as unit

    from . import bidset

    rev = REVISION
    f = project.create_file("IFC4")
    f.header.file_name.time_stamp = bidset.HEADER_TIME
    proj = bidset._make(f, "IfcProject", f"services/{rev}/project",
                        f"brownfield-compute: the walk-up's services ({ISSUE}, routed through {rev}'s frame)")
    unit.assign_unit(f, units=[unit.add_si_unit(f, unit_type=t) for t in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT", "PLANEANGLEUNIT")])
    model = context.add_context(f, context_type="Model")
    body = context.add_context(f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)
    site = bidset._make(f, "IfcSite", f"services/{rev}/site", "the walk-up's site (not georeferenced)")
    bldg = bidset._make(f, "IfcBuilding", f"services/{rev}/building", "12-flat walk-up: its services", Description=source)
    aggregate.assign_object(f, products=[site], relating_object=proj)
    aggregate.assign_object(f, products=[bldg], relating_object=site)
    geometry.edit_object_placement(f, product=site)
    geometry.edit_object_placement(f, product=bldg)
    storeys = {}
    for k in range(1, apt["storeys"] + 1):
        s = bidset._make(f, "IfcBuildingStorey", f"services/{rev}/storey/{k}", f"Level {k}")
        aggregate.assign_object(f, products=[s], relating_object=bldg)
        geometry.edit_object_placement(f, product=s)
        storeys[k] = s
    members: dict[str, list] = defaultdict(list)
    for el in els:
        attrs = {"PredefinedType": el.pre}
        if el.obj:
            attrs["ObjectType"] = el.obj
        e = bidset._make(f, el.cls, f"services/{rev}/{el.key}", el.name, **attrs)
        if el.geom[0] == "sweep":
            pts = el.geom[1]
            _place_sweeps(f, body, e, pts, el.geom[2])
            z = min(q[2] for q in pts)
        else:
            bidset._place_boxes(f, body, e, [(el.geom[1], el.geom[2])])
            z = el.geom[1][2]
        spatial.assign_container(f, products=[e], relating_structure=storeys[storey_of(apt, z)])
        ps = pset.add_pset(f, product=e, name="BF_Service")
        pset.edit_pset(f, pset=ps, properties={"Key": el.key, **{k: v for k, v in el.props.items() if v is not None}})
        members[el.system].append(e)
    for key, (pre, name, layer) in SYSTEMS.items():
        if not members[key]:
            continue
        s = system_api.add_system(f, ifc_class="IfcDistributionSystem")
        s.GlobalId = bidset.gid(f"services/{rev}/system/{key}")
        s.Name, s.PredefinedType, s.LongName = name, pre, LAYERS[layer]
        system_api.assign_system(f, products=members[key], system=s)
    bidset._derive_gids(f)
    bidset._sort_sets(f)
    path.parent.mkdir(parents=True, exist_ok=True)
    f.write(str(path))


def read_back(path: Path) -> list[dict]:
    """Every distribution element in the file: class, predefined type, name, BF_Service, its
    system's name, and its geometry from the file (a sweep's polyline in world coordinates, or a
    box)."""
    import ifcopenshell
    import ifcopenshell.util.element as util
    import ifcopenshell.util.placement as placement

    f = ifcopenshell.open(str(path))
    system_of = {}
    for rel in f.by_type("IfcRelAssignsToGroup"):
        if rel.RelatingGroup.is_a("IfcDistributionSystem"):
            for o in rel.RelatedObjects:
                system_of[o.id()] = rel.RelatingGroup.Name
    out = []
    for e in f.by_type("IfcDistributionElement"):
        m = placement.get_local_placement(e.ObjectPlacement)
        rec = {"cls": e.is_a(), "pre": e.PredefinedType, "name": e.Name, "gid": e.GlobalId, "obj": getattr(e, "ObjectType", None),
               "props": util.get_pset(e, "BF_Service") or {}, "group": system_of.get(e.id()),
               "storey": util.get_container(e).Name if util.get_container(e) else None}
        items = e.Representation.Representations[0].Items
        if items[0].is_a("IfcSweptDiskSolid"):
            loc = [list(items[0].Directrix.Points[0].Coordinates)] + [list(it.Directrix.Points[-1].Coordinates) for it in items]
            rec["sweep"] = [list((m @ np.array([*q, 1.0]))[:3]) for q in loc]
            rec["d"] = 2 * items[0].Radius
        else:
            rec["sweep"] = None
        out.append(rec)
    return out


def check(path: Path, els: list[El], routes, apt: dict, p: dict) -> list[tuple[str, bool, str]]:
    """The file read back against what it should hold."""
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.validate

    from . import bidset

    rb = read_back(path)
    by = {r["props"].get("Key"): r for r in rb}
    want = {e.key: e for e in els}
    names = Counter(r["props"].get("Key") for r in rb)
    res = [("every element once, and nothing else", set(names) == set(want) and all(n == 1 for n in names.values()),
            f"{len(rb)} in the file, {len(want)} expected")]
    # Every routed run whole and where forge has it: each piece's every vertex on forge's
    # polylines (or at the run's root or a terminal), and the run's pieces' length forge's
    # branches' plus the joins, tails and lead (from forge's own record).
    worst, gap, missing = 0.0, 0.0, []
    for rid, rec in routes.recs.items():
        req = routes.reqs[rid]
        # A branch of one point (a flat's loop's end on its tree already) is a vertex, not a line.
        polys = [np.asarray(b["points"], float) for b in rec["branches"] if len(b["points"]) > 1]
        extra = ([np.asarray(req["root"], float)] + [np.asarray(b["to"], float) for b in rec["branches"]]
                 + [np.asarray(b["points"][0], float) for b in rec["branches"] if len(b["points"]) == 1])
        pieces = [r for r in rb if r["props"].get("Run") == rid and r["props"].get("Key", "").startswith("run/")]
        if not pieces:
            missing.append(rid)
            continue
        got = 0.0
        for r in pieces:
            pts = np.asarray(r["sweep"], float)
            got += float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
            for q in pts:
                d = min(min(_seg_dist(q, P) for P in polys), min(float(np.linalg.norm(q - x)) for x in extra))
                worst = max(worst, d)
        t = routes.tree(rid)
        forge = sum(b["length_m"] for b in rec["branches"])
        joins = sum(math.dist(t.branches[i].points[0], t.branches[b.parent].point_at(b.at)) for i, b in enumerate(t.branches)
                    if b.parent is not None)
        tails = sum(b.tail_m for b in t.branches if len(b.points) > 1)  # a one-point branch has no piece to carry it (`Tree`)
        gap = max(gap, abs(got - (forge + joins + tails + t.lead_m)))
    res.append(("every routed run in the file, each piece where forge routed it (to 1 mm)", not missing and worst < 1e-3,
                f"{len(routes.recs)} runs; farthest vertex {worst * 1e3:.3f} mm" + (f"; missing {missing[:3]}" if missing else "")))
    res.append(("every run's pieces as long as forge's branches, their joins, tails and lead (to 1 mm)", gap < 1e-3,
                f"worst {gap * 1e3:.3f} mm"))
    # Everything else where 7a put it.
    off = 0.0
    for k, e in want.items():
        r = by.get(k)
        if r is None:
            continue
        if e.geom[0] == "sweep":
            off = max(off, float(np.abs(np.asarray(r["sweep"]) - np.asarray(e.geom[1])).max()))
    f = ifcopenshell.open(str(path))
    boxes = [x for x in f.by_type("IfcDistributionElement") if not x.Representation.Representations[0].Items[0].is_a("IfcSweptDiskSolid")]
    wb = bidset._world_boxes(f, boxes)
    for x in boxes:
        e = want.get(ifcopenshell.util.element.get_pset(x, "BF_Service", "Key"))
        if e is None:
            continue
        lo, hi = wb[x.GlobalId]
        off = max(off, float(np.abs(lo - np.asarray(e.geom[1])).max()), float(np.abs(hi - np.asarray(e.geom[2])).max()))
    res.append(("every element where it was placed (to 1 mm)", off < 1e-3, f"worst {off * 1e3:.4f} mm"))
    res.append(("every element in its system", all(r["group"] for r in rb), f"{len({r['group'] for r in rb})} systems"))
    log = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, log, express_rules=True)
    res.append(("schema validation (with express rules)", not log.statements, f"{len(log.statements)} issues"))
    return res


def _seg_dist(q: np.ndarray, P: np.ndarray) -> float:
    a, b = P[:-1], P[1:]
    ab = b - a
    l2 = np.einsum("ij,ij->i", ab, ab)
    t = np.clip(np.einsum("ij,ij->i", q - a, ab) / np.where(l2 > 0, l2, 1.0), 0.0, 1.0)
    return float(np.linalg.norm(a + t[:, None] * ab - q, axis=1).min())


def check_webifc(path: Path, els: list[El]) -> list[tuple[str, bool, str]]:
    """web-ifc's own geometry of each element (`tools/webifc/check.mjs`) where it should be: its box
    within the element's half-diameter of its points' box (a sweep) or on its box (to 1 mm)."""
    from .bidset import _ifc_axes, read_webifc

    rep = read_webifc(path)
    want = {e.key: e for e in els}
    got = [r for r in rep["elements"] if r["cls"] == "IFCDISTRIBUTIONELEMENT"]
    none, worst = [], 0.0
    for r in got:
        e = want.get((r["psets"].get("BF_Service") or {}).get("Key"))
        if e is None:
            continue
        if r["bbox"] is None:
            none.append(e.key)
            continue
        lo, hi = _ifc_axes(r["bbox"])
        if e.geom[0] == "sweep":
            pts = np.asarray(e.geom[1], float)
            slack = e.geom[2] / 2 + 1e-3
            worst = max(worst, float(np.clip(np.abs(lo - pts.min(0)) - slack, 0, None).max()),
                        float(np.clip(np.abs(hi - pts.max(0)) - slack, 0, None).max()))
        else:
            worst = max(worst, float(np.abs(lo - np.asarray(e.geom[1])).max()) - 1e-3, float(np.abs(hi - np.asarray(e.geom[2])).max()) - 1e-3)
    return [("web-ifc reads every element", len(got) == len(want), f"{len(got)} of {len(want)} ({rep['reader']})"),
            ("web-ifc draws every element where it should be", not none and worst <= 1e-9,
             f"{len(none)} with no mesh" + (f" ({none[:3]})" if none else "") + f"; worst {max(worst, 0) * 1e3:.3f} mm past")]


# ---- The schedules, from the file read back ----

FAMILY = {  # BF_Service's material -> the firestop schedule's penetrant family
    MATERIAL["cast_iron"]: "cast iron", MATERIAL["pex"]: "PEX", MATERIAL["pex_pre"]: "PEX", MATERIAL["copper"]: "copper line set",
    MATERIAL["conduit"]: "PVC conduit", MATERIAL["nm"]: "NM-B cable", MATERIAL["cpvc"]: "CPVC", MATERIAL["pvc"]: "PVC",
    MATERIAL["duct"]: "steel duct",
}
METALLIC = {"cast iron", "copper line set", "steel duct"}  # IBC 714.4.1's exception, 714.5.1's and 714.5.2's exception 1
FRACTIONS = {"1/8": 0.125, "1/4": 0.25, "3/8": 0.375, "1/2": 0.5, "5/8": 0.625, "3/4": 0.75, "7/8": 0.875}


def size_in(text: str) -> float | None:
    """A nominal size as the trade writes it, back to inches: '1-1/4' -> 1.25; None if it isn't one."""
    whole, _, frac = text.partition("-")
    try:
        if not frac:
            return FRACTIONS[whole] if whole in FRACTIONS else float(whole)
        return float(whole) + FRACTIONS[frac]
    except (KeyError, ValueError):
        return None


UNRATED = {"the roof": "the top storey's roof/ceiling, unrated in Type V-B (Table 601)",
           "the stair": "the stair's halls inside its 1-hour enclosure, which separate nothing"}


def penetration_rows(rb: list[dict], apt: dict) -> list[dict]:
    """Every crossing of an assembly's face by a routed piece or a riser, from the file's geometry
    (`routecheck.penetration_hits`), with what the firestop schedule needs of its penetrant."""
    from .routecheck import penetration_hits

    walls = [(w["lo_m"], w["hi_m"]) for w in apt["rooms"]["walls"]] + [(x["lo_m"], x["hi_m"]) for x in apt["parts"]
                                                                      if x["kind"] in ("party_wall", "exterior_wall")]
    segs, owner = [], []
    for r in rb:
        key = r["props"].get("Key", "")
        if r["sweep"] is None or not key.startswith(("run/", "pinned/", "drop/")):
            continue
        for a, c in zip(r["sweep"], r["sweep"][1:]):
            segs.append((a, c))
            owner.append(r)
    rows = []
    for h in penetration_hits(apt, segs):
        pr = owner[h["seg"]]["props"]
        fam = FAMILY.get(pr.get("Material"), pr.get("Material"))
        size = str(pr.get("Size", ""))
        n = size_in(size)
        # Insulated: a line set always; a PEX tube wider than its own CTS outside diameter (nominal + 1/8 in.).
        insulated = fam == "copper line set" or (fam == "PEX" and n is not None and pr.get("OutsideDiameter", 0) / IN > n + 0.125 + 0.05)
        x, y, z = h["at"]
        rows.append({"key": pr["Key"], "where": h["where"], "storey": h["storey"], "rated": h["rated"], "unrated": h["unrated"],
                     "system": pr.get("System"), "family": fam, "size": size, "insulated": insulated,
                     "od_in": round(pr.get("OutsideDiameter", 0) / IN, 2), "run": pr.get("Run"),
                     "in_wall": any(lo[0] - 1e-3 <= x <= hi[0] + 1e-3 and lo[1] - 1e-3 <= y <= hi[1] + 1e-3 for lo, hi in walls),
                     "tub": str(pr.get("Run", "")).endswith("/tub"), "x": round(x, 3), "y": round(y, 3), "z": round(z, 3)})
    return rows


OPENING = {
    "through": "through the floor/ceiling between flats, both faces (up a wall's cavity through its top plates and on through the floor)",
    "ceiling side": "into the floor/ceiling from below, up through a wall's top plates",
    "floor side": "into the floor/ceiling from above, through the subfloor",
    "membrane": "through the ceiling's membrane",
    "wall": "through a party or stair wall",
    "the roof": "through the top storey's ceiling (unrated)",
    "the stair": "through the stair's halls (unrated)",
}


def openings(rows: list[dict]) -> list[dict]:
    """The penetrations as openings, one firestop system each: an element's crossing of a floor and
    of the ceiling under it at the same place is one through-penetration of the floor/ceiling (both
    its faces); a crossing of one face alone is a membrane penetration of that face (IBC 714.5.2)."""
    by: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by[(r["key"], r["storey"])].append(r)
    out = []
    for _, rs in sorted(by.items()):
        floors = [r for r in rs if r["where"] == "floor"]
        ceil = [r for r in rs if r["where"] in ("top plate", "membrane")]
        used: set[int] = set()
        for f in floors:
            c = next((i for i, c in enumerate(ceil) if i not in used and math.hypot(c["x"] - f["x"], c["y"] - f["y"]) < 0.05), None)
            if c is not None:
                used.add(c)
                out.append(_opening("through", [f, ceil[c]]))
            else:
                out.append(_opening("floor side", [f]))
        for i, c in enumerate(ceil):
            if i not in used:
                out.append(_opening("ceiling side" if c["where"] == "top plate" else "membrane", [c]))
        out += [_opening("wall", [r]) for r in rs if r["where"] == "wall"]
    return out


def _opening(kind: str, faces: list[dict]) -> dict:
    r0 = faces[0]
    rated = any(f["rated"] for f in faces)
    if not rated:
        kind = next(f["unrated"] for f in faces if f["unrated"])
    in_wall = any(f["in_wall"] or f["where"] == "top plate" for f in faces)
    return {**{k: r0[k] for k in ("key", "storey", "system", "family", "size", "insulated", "od_in", "run", "x", "y")},
            "kind": kind, "rated": rated, "faces": "+".join(f["where"] for f in faces), "in_wall": in_wall, "tub": r0["tub"],
            **firestop_condition(kind, rated, r0["family"], in_wall, r0["tub"], r0["insulated"])}


def firestop_condition(kind: str, rated: bool, family: str, in_wall: bool, tub: bool, insulated: bool) -> dict:
    """What IBC 2021 714 asks of one opening (the code's text: data/raw/pass3g/raw/ibc9/ch7_all.txt;
    714.5.2's exception 7 as UpCodes prints it, data/raw/pass3g/firestop/UpCodes_PA-IBC2021_ch7_714.html)."""
    if not rated:
        return {"asks": "fireblocking kept whole around it (718.2.1.4)", "F": "", "T": "", "section": "718.2"}
    metal = family in METALLIC
    if kind == "wall":
        return {"asks": "a listed through-penetration firestop system, F 1 h (714.4.1.2)"
                + ("; or the annular space filled to the cotton-waste test (714.4.1 exception 2)" if metal else ""),
                "F": "1 h", "T": "", "section": "714.4.1.2"}
    if in_wall:
        t = "not required: in a wall's cavity (714.5.1.2 exception 1)"
    elif tub:
        t = "not required: a tub drain in the floor's space (714.5.1.2 exception 2)"
    else:
        t = "1 h"
    ins = "; the insulation through the assembly only where the listed system was tested with it (714.3)" if insulated else ""
    if kind == "through":
        asks = "a listed through-penetration firestop system (714.5.1.2)" + (
            "; or the annular space filled to the cotton-waste test (714.5.1 exception 1, openings at most 144 in.2 a 100 ft2)" if metal else "")
        return {"asks": asks + ins, "F": "1 h", "T": t, "section": "714.5.1.2"}
    if kind == "ceiling side":
        asks = ("a listed system for the penetration through the double top plates (714.5.2 exception 7, which lets the plates "
                "interrupt the ceiling where the wall is sheathed in Type X and the ceiling is tight to them)"
                + ("; or, read as a membrane penetration by ferrous or copper pipe, the annular space protected (714.5.2 exception 1)"
                   if metal else ""))
        return {"asks": asks + ins, "F": "1 h", "T": t, "section": "714.5.2"}
    # A face of its own: the open ceiling's membrane, or the subfloor.
    asks = ("the annular space protected (714.5.2 exception 1, openings at most 100 in.2 a 100 ft2)" if metal
            else "a listed membrane-penetration firestop system (714.5.2, 714.5.1.2)")
    return {"asks": asks + ins, "F": "1 h", "T": "" if metal else t, "section": "714.5.2"}


def firestop_schedule(ops: list[dict], listed: dict | None = None) -> list[dict]:
    """The openings by condition: the assembly and how it's penetrated, the penetrant's family and
    sizes, what the code asks, how many; with the listed system chosen for it (`listed`, by
    condition: `data/firestop_systems.csv`) and how well it fits."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in ops:
        groups[(r["kind"], r["family"], r["insulated"], r["asks"], r["T"])].append(r)
    out = []
    order = list(OPENING)
    for (kind, fam, ins, asks, t), rs in sorted(groups.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][1], kv[0][2], kv[0][4])):
        sizes = sorted({r["size"] for r in rs}, key=lambda s: (size_in(s) is None, size_in(s) or 0.0, s))
        cond = f"{kind}/{fam}{'/insulated' if ins else ''}"
        sys_ = (listed or {}).get(cond, {})
        out.append({"condition": cond, "opening": OPENING[kind], "penetrant": fam + (", insulated" if ins else ""),
                    "sizes": ", ".join(sizes), "count": len(rs), "F": rs[0]["F"], "T": t, "asks": asks,
                    "storeys": ", ".join(str(s) for s in sorted({r["storey"] for r in rs})),
                    "listed_system": sys_.get("system", ""), "fit": sys_.get("fit", ""), "note": sys_.get("note", ""),
                    "source": sys_.get("source", "")})
    return out


# The pull (forge `pull`) lands a feeder at most two of its 2 in. voxels (0.10 m) short of its riser's
# foot and steps the rest square, and its terminal snaps a few centimetres more: end pieces that
# short together are where the conduit's sweep up starts, not runs of their own.
SNAP_M = 0.16


def conduit_bends(rb: list[dict], p: dict) -> list[dict]:
    """NEC 352.26 on each feeder's conduit, meter to panel: the degrees it turns along its route (at
    any angle: forge runs it straight under the slab), and a quarter bend at each end where the run
    under the slab turns up (into the meter's wall and into its riser or the panel above), with no
    pull point between. Its straight runs are merged first; pieces at either end shorter than
    `SNAP_M` together are part of that end's sweep."""
    out = []
    for r in rb:
        if not r["props"].get("Key", "").startswith("run/electrical/feeder/"):
            continue
        pts = [np.asarray(q, float) for q in r["sweep"]]
        runs: list[list[np.ndarray]] = []  # [start, end] of each straight run
        for a, c in zip(pts, pts[1:]):
            if np.linalg.norm(c - a) < 1e-9:
                continue
            if runs and np.linalg.norm(np.cross(_dir(*runs[-1]), _dir(a, c))) < 1e-9 and float(_dir(*runs[-1]) @ _dir(a, c)) > 0:
                runs[-1][1] = c
            else:
                runs.append([a, c])
        for end in (0, -1):
            dropped = 0.0
            while len(runs) > 1 and dropped + np.linalg.norm(runs[end][1] - runs[end][0]) < SNAP_M:
                dropped += float(np.linalg.norm(runs[end][1] - runs[end][0]))
                runs.pop(end)
        segs = [_dir(a, c) for a, c in runs]
        along = sum(math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v))))) for u, v in zip(segs, segs[1:]))
        ends = (0 if _vertical(segs[0]) else 1) + (0 if _vertical(segs[-1]) else 1)
        deg = along + 90 * ends
        out.append({"flat": r["props"].get("Flat"), "bends": len(segs) - 1, "along_deg": round(along, 1), "end_bends": ends,
                    "degrees": round(deg, 1), "ok": deg <= p[S + "conduit_bends_max_deg"] + 0.05})
    return sorted(out, key=lambda x: x["flat"])


# Which rule asks a steel plate where a run passes near a wood member's edge, by its system: (rule,
# parameter, the members it covers: None for all). Cast iron (drains, vents) is exempt (IPC 305.6).
PLATE_RULE = {
    "cable": ("NEC 300.4(A)(1)", "nec_bore_edge_in", None),
    "feeder": ("NEC 300.4(A)(1)", "nec_bore_edge_in", None),
    "water": ("IPC 305.6", "ipc_shield_edge_in", None),
    "sprinkler": ("NFPA 13R 5.2.3.7", "nfpa13r_shield_edge_in", ("studs", "king studs", "jack studs", "cripples")),
    "condensate": ("IMC 305.5", "imc_shield_edge_in", None),
    "hydronic": ("IMC 305.5", "imc_shield_edge_in", None),
    "line-set": ("IMC 305.5", "imc_shield_edge_in", None),
}


def plates(routes, frame: dict, p: dict) -> list[dict]:
    """Every bore (forge's) where a run passes nearer a wood member's edge than its code allows: the
    hole's edge to the member's nearest face across its section (the faces a nail or screw comes
    through). Where forge put the hole doesn't bind the installer across a member's section, so each
    takes a steel plate only if a hole at the member's centre would still be too near (`plate`);
    the others are bored at the centre (the specification says so). A sleeve through concrete is no
    wood member."""
    members = {m["id"]: m for m in frame["members"]}
    out = []
    for rid, rec in sorted(routes.recs.items()):
        system = routes.reqs[rid]["system"]
        if system not in PLATE_RULE:
            continue
        rule, key, kinds = PLATE_RULE[system]
        limit = p[S + key] * IN
        for b in rec["branches"]:
            for h in b.get("bores", []):
                m = members.get(h["member"])
                if m is None or h["sleeve"] or (kinds and h["kind"] not in kinds):
                    continue
                lo = [min(x[0][i] for x in m["boxes"]) for i in range(3)]
                hi = [max(x[1][i] for x in m["boxes"]) for i in range(3)]
                c, a, d = h["at"], h["axis"], h["hole_m"]
                across = [i for i in range(3) if i != a and hi[i] - lo[i] < 0.4]
                if not across:
                    continue
                edge = min(min(c[i] - lo[i], hi[i] - c[i]) for i in across) - d / 2
                centred = min((hi[i] - lo[i]) / 2 for i in across) - d / 2
                if edge < limit - 1e-9:
                    out.append({"run": rid, "member": h["member"], "kind": h["kind"], "edge_in": round(edge / IN, 2),
                                "centred_edge_in": round(centred / IN, 2), "limit_in": p[S + key], "rule": rule,
                                "plate": ("1/16 in. steel" if rule.startswith("NEC") else "16 ga steel") if centred < limit - 1e-9 else
                                "none if bored at the member's centre"})
    return out


def schedules(rb: list[dict], routes, apt: dict, listed: dict | None = None, frame: dict | None = None,
              p: dict | None = None) -> dict[str, list[dict]]:
    """The schedules, every figure from the file read back but the holes (forge's bores; each
    piece's count of them is in BF_Service)."""
    lengths: dict[tuple, dict] = {}
    for r in rb:
        pr, key = r["props"], r["props"].get("Key", "")
        if r["sweep"] is None or not key.startswith(("run/", "pinned/", "drop/")) or r["cls"].endswith("Fitting"):
            continue
        k = (pr["System"], pr["Material"], str(pr["Size"]), r["cls"])
        row = lengths.setdefault(k, {"system": SYSTEMS[pr["System"]][1], "layer": LAYERS[pr["Layer"]], "class": r["cls"],
                                     "material": pr["Material"], "size_in": str(pr["Size"]), "pieces": 0, "m": 0.0, "bends": 0,
                                     "sweeps_on_supports": 0, "holes": 0})
        pts = np.asarray(r["sweep"], float)
        row["pieces"] += 1
        row["m"] += float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
        row["bends"] += int(pr.get("Bends", 0))
        row["sweeps_on_supports"] += int(pr.get("Sweeps", 0))
        row["holes"] += int(pr.get("Holes", 0))
    for row in lengths.values():
        row["ft"] = round(row["m"] / FT, 1)
        row["m"] = round(row["m"], 2)
    fits = Counter()
    for r in rb:
        if r["cls"].endswith("Fitting") and r["obj"] != "manifold":
            pr = r["props"]
            fits[(SYSTEMS[pr["System"]][1], pr["Material"], pr["Kind"], str(pr["Size"]))] += 1
    fittings_rows = [{"system": s, "material": m, "fitting": k, "size_in": z, "count": n} for (s, m, k, z), n in sorted(fits.items())]

    def rows(prefix: str, cols: list[str]) -> list[dict]:
        out = []
        for r in sorted(rb, key=lambda r: r["name"]):
            if not r["props"].get("Key", "").startswith(prefix):
                continue
            kind = r["obj"] if r["pre"] == "USERDEFINED" else (r["pre"] if r["pre"] != "NOTDEFINED" else "")
            out.append({"element": r["name"], "class": r["cls"] + (f" ({kind})" if kind else ""), "storey": r["storey"],
                        **{c: r["props"].get(c, "") for c in cols}})
        return out

    holes = []
    for rid, rec in sorted(routes.recs.items()):
        for b in rec["branches"]:
            for h in b.get("bores", []):
                holes.append({"run": rid, "member": h["member"], "kind": h["kind"], "hole_in": round(h["hole_m"] / IN, 3),
                              "allowed_in": "" if h["allowed_m"] is None else round(h["allowed_m"] / IN, 3),
                              "share": "" if not h["allowed_m"] else round(h["hole_m"] / h["allowed_m"], 3),
                              "from_support_ft": "" if h["from_support_m"] is None else round(h["from_support_m"] / FT, 2),
                              "sleeve": h["sleeve"]})
    pen = penetration_rows(rb, apt)
    ops = openings(pen)
    return {"lengths": sorted(lengths.values(), key=lambda x: (x["layer"], x["system"], x["material"], size_in(x["size_in"]) or 0.0)),
            "fittings": fittings_rows,
            "equipment": rows("eq/", ["Flat", "Kind"]),
            "fixtures": rows("fixture/", ["Flat", "Room", "Kind", "Drawn"]),
            "sprinklers": rows("head/", ["Flat", "Room", "Compartment", "Model", "K", "Coverage", "Temperature"]),
            "air_terminals": rows("air/", ["Flat", "Kind", "Size", "Run"]),
            "switches": rows("switch/", ["Flat", "Kind"]),
            "holes": holes,
            "plates": plates(routes, frame, p) if frame is not None else [],
            "penetrations": pen,
            "openings": ops,
            "firestop": firestop_schedule(ops, listed)}


def write_schedules(sch: dict[str, list[dict]], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, rows in sch.items():
        if not rows:
            continue
        path = out / f"{name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        written.append(path)
    return written


# ---- 7d as a run ----

LISTED = Path(__file__).resolve().parents[2] / "data" / "firestop_systems.csv"


def listed_systems() -> dict:
    """The listed firestop system chosen for each condition (`data/firestop_systems.csv`), if any."""
    if not LISTED.exists():
        return {}
    with open(LISTED, encoding="utf-8") as fh:
        return {r["condition"]: r for r in csv.DictReader(line for line in fh if not line.startswith("#"))}


def run(apt: dict, p: dict, out: Path = OUT, routes=None, s7: dict | None = None) -> dict:
    """Build the services model from the routes (and 7c's designs on them, `s7`, if already run),
    check it, and read its schedules back."""
    from . import routed, routing
    from .bidset import webifc_status
    from .routecheck import penetrations

    routes = routes or routed.load(apt, p)
    if routes is None:
        raise SystemExit("no routes yet: `brownfield routes --requests`, forge's `routes-json`, then `brownfield routes`")
    failed, runs = routed.run_checks(routes)
    if failed or not routes.fresh:
        return {"checks": runs + [("the services model built on the routes", False, "the routes aren't whole and fresh: run 7b again")]}
    s7 = s7 or routed.summary(apt, p, routes)
    if "incomplete" in s7:
        return {"checks": s7["checks"]}
    placed = routing.placements(apt, p)
    els = elements(apt, p, routes, s7, placed)
    path = out / f"services-{ISSUE}.ifc"
    write(els, apt, path, f"forge `routes-json` on {REVISION}'s frame (requests {routes.rt['requests_sha']}); sizes from 7c's designs")
    checks = check(path, els, routes, apt, p)
    why = webifc_status()
    checks += check_webifc(path, els) if why is None else [("web-ifc reads the services model", False, why)]
    rb = read_back(path)
    sch = schedules(rb, routes, apt, listed_systems(), placed["frame"], p)
    # The same count from forge's routes and the pinned verticals (7b's, `routecheck.penetrations`):
    # the file adds the closet bends and the tubs' drains, which 7a placed but forge didn't route.
    routed_only = [r for r in sch["penetrations"] if not r["key"].startswith("drop/") and not r["key"].endswith("/wc-bend")]
    pen_ifc = Counter((r["where"], r["rated"]) for r in routed_only)
    pen_forge = penetrations(apt, p, routes.body, routes.rt)
    same = all(pen_ifc[(w, True)] == pen_forge["rated"][w] and pen_ifc[(w, True)] + pen_ifc[(w, False)] == pen_forge[w]
               for w in ("floor", "top plate", "membrane", "wall"))
    extra = len(sch["penetrations"]) - len(routed_only)
    checks.append(("the penetrations counted from the file are forge's (7b's count from its routes)", same,
                   ", ".join(f"{w} {pen_ifc[(w, True)]} rated + {pen_ifc[(w, False)]}" for w in ("floor", "top plate", "membrane", "wall"))
                   + f"; and {extra} by the closet bends and tub drains"))
    bends = conduit_bends(rb, p)
    over = [f"{b['flat']} {b['degrees']:.0f}°" for b in bends if not b["ok"]]
    checks.append((f"every feeder's conduit within NEC 352.26's {p[S + 'conduit_bends_max_deg']:g}° of bends between pull points "
                   "(meter to panel, none between)", not over, ", ".join(over) or f"{len(bends)} feeders"))
    asked = [r for r in sch["firestop"] if r["F"] and "listed" in r["asks"].split(";")[0]]
    n = {k: sum(r["count"] for r in asked if r["fit"] == k) for k in ("fits", "fits if", "partial", "none")}
    unknown = [r["condition"] for r in asked if r["fit"] not in n]
    checks.append(("every rated opening whose code asks a listed firestop system has its route: a listed system as tested, or "
                   "where none fits, the maker's engineering judgment for the authority's approval (Jon, 2026-11-22); each "
                   "condition in data/firestop_systems.csv",
                   not unknown,
                   f"of {sum(r['count'] for r in asked)}: {n['fits']} listed, {n['fits if']} listed with a change the schedule gives, "
                   f"{n['partial'] + n['none']} by engineering judgment ({n['partial']} where a listing partly fits, {n['none']} where none "
                   "was found); the floor systems are tested in UL L500 floors, the walk-up's is AWC's WIJ-1.3"
                   + (f"; no entry for {unknown}" if unknown else "")))
    written = [path] + write_schedules(sch, out / "schedules")
    return {"checks": checks, "path": path, "written": written, "schedules": sch, "conduit_bends": bends,
            "counts": dict(Counter(r["cls"] for r in rb)), "elements": len(rb), "systems": sorted({r["group"] for r in rb if r["group"]})}


def report(s: dict) -> str:
    from .systems import report as checks

    lines = ["Pass 3g step 7d: the services as IFC, and their schedules", "", checks(s["checks"])]
    if "schedules" not in s:
        return "\n".join(lines)
    sch = s["schedules"]
    lines += ["", f"The model: {s['elements']:,} elements in {len(s['systems'])} systems ({s['path'].name})."]
    by_layer: dict[str, float] = defaultdict(float)
    for r in sch["lengths"]:
        by_layer[r["layer"]] += r["ft"]
    lines.append("  Lengths: " + "; ".join(f"{k} {v:,.0f} ft" for k, v in sorted(by_layer.items())))
    fit = Counter()
    for r in sch["fittings"]:
        fit[r["system"]] += r["count"]
    lines.append("  Fittings: " + "; ".join(f"{k} {v}" for k, v in sorted(fit.items())))
    lines.append(f"  Equipment {len(sch['equipment'])}, fixtures {len(sch['fixtures'])}, sprinklers {len(sch['sprinklers'])}, "
                 f"registers, grilles and wall caps {len(sch['air_terminals'])}, water-level switches {len(sch['switches'])}; "
                 f"holes through the frame {len(sch['holes']):,}")
    need = [r for r in sch["plates"] if not r["plate"].startswith("none")]
    by_rule = Counter(r["rule"] for r in need)
    lines.append(f"  Steel plates where a run passes near a member's edge: {len(need)} even bored at the centre ("
                 + ", ".join(f"{k} {v}" for k, v in sorted(by_rule.items())) + f"); {len(sch['plates']) - len(need)} more holes "
                 "drawn near an edge clear the codes bored at the centre")
    lines += ["", f"Firestop schedule (IBC 2021 714): {len(sch['openings'])} openings "
              f"({sum(1 for o in sch['openings'] if o['rated'])} through rated assemblies), by condition:"]
    for r in sch["firestop"]:
        unit = "" if "AWG" in r["sizes"] else " in."
        lines.append(f"  {r['count']:>4}  {r['opening']}; {r['penetrant']} ({r['sizes']}{unit}), storeys {r['storeys']}: "
                     f"{r['asks']}" + (f"; T {r['T']}" if r["T"] and r["F"] else ""))
        if r["listed_system"]:
            lines.append(f"          {r['listed_system']} ({r['fit']}): {r['note']}")
    lines += ["", "Feeder conduits, meter to panel (NEC 352.26): "
              + ", ".join(f"{b['flat']} {b['degrees']:.0f}°" for b in s["conduit_bends"])]
    return "\n".join(lines)


# ---- Publishing: the plan room's services model (D29's viewer layers) ----

PUBLISHED_SCHEDULES = ("lengths", "fittings", "equipment", "fixtures", "sprinklers", "air_terminals", "switches", "holes", "plates",
                       "openings", "firestop")
LABELS = {"lengths": "Pipe, duct, conduit and cable lengths, by system, material and size",
          "fittings": "Fittings, by system, kind and size", "equipment": "Equipment", "fixtures": "Plumbing fixtures",
          "sprinklers": "Sprinklers", "air_terminals": "Registers, grilles and wall caps",
          "switches": "Water-level switches (IMC 307.2.3)", "holes": "Holes bored through the frame",
          "plates": "Holes near a member's edge (steel plates)", "openings": "Every opening through an assembly",
          "firestop": "The firestop schedule, by condition (IBC 714)"}


def changes(old: Path, new: Path, tol: float = 1e-3) -> dict:
    """What a revised services model changed against the one before, by GlobalId (an element's key
    keeps it, `write`): those added; those deleted, with their names; and those changed in class,
    in their BF_Service properties (size, model, setting...) or in geometry (a run's path or
    diameter, a box's corners) by more than `tol` m. Counted by system, for the addendum's text."""
    import ifcopenshell

    from .bidset import _world_boxes

    r0 = {r["gid"]: r for r in read_back(old)}
    r1 = {r["gid"]: r for r in read_back(new)}
    f0, f1 = ifcopenshell.open(str(old)), ifcopenshell.open(str(new))
    b0 = _world_boxes(f0, [f0.by_guid(g) for g, r in r0.items() if r["sweep"] is None])
    b1 = _world_boxes(f1, [f1.by_guid(g) for g, r in r1.items() if r["sweep"] is None])

    def props(r: dict) -> dict:
        return {k: v for k, v in r["props"].items() if k != "id"}  # the pset's entity number in its file

    def same(g: str) -> bool:
        a, b = r0[g], r1[g]
        if a["cls"] != b["cls"] or a["pre"] != b["pre"] or props(a) != props(b) or (a["sweep"] is None) != (b["sweep"] is None):
            return False
        if a["sweep"] is not None:
            return (len(a["sweep"]) == len(b["sweep"]) and abs(a["d"] - b["d"]) <= tol
                    and float(np.abs(np.asarray(a["sweep"]) - np.asarray(b["sweep"])).max()) <= tol)
        return max(float(np.abs(b0[g][0] - b1[g][0]).max()), float(np.abs(b0[g][1] - b1[g][1]).max())) <= tol

    added = sorted(r1.keys() - r0.keys())
    deleted = sorted(r0.keys() - r1.keys())
    changed = sorted(g for g in r0.keys() & r1.keys() if not same(g))
    by: dict[str, dict[str, int]] = defaultdict(lambda: {"added": 0, "changed": 0, "deleted": 0})
    for k, gs, rs in (("added", added, r1), ("changed", changed, r1), ("deleted", deleted, r0)):
        for g in gs:
            by[rs[g]["props"].get("System") or "-"][k] += 1
    return {"before": old.name, "after": new.name, "n_before": len(r0), "n_after": len(r1), "added": added, "changed": changed,
            "deleted": [{"gid": g, "name": r0[g]["name"], "cls": r0[g]["cls"]} for g in deleted],
            "by_system": dict(sorted(by.items()))}


def publish(to: Path, issued: str, addendum: int) -> dict:
    """The services model as `ISSUE` issues it, and its schedules, into the published bid set
    (`to`), only from a run whose model checks all passed (`out/pass3/routes-7d.json`: the file
    whole, where forge routed it, schema valid, web-ifc's geometry where it should be). The
    design's own findings (a check of the code it doesn't yet meet) don't stop it: the manifest's
    note lists them. An earlier issue's model and schedules are left as published; what this one
    changed against the latest of them goes beside it (`changes-services-<issue>.json`, for the
    viewer to mark). Returns the manifest's `services` entry."""
    import shutil

    if f"addendum-{addendum}" != ISSUE:
        raise SystemExit(f"the services model is {ISSUE}'s, not Addendum {addendum}'s")
    rec = json.loads((OUT_DIR / "pass3" / "routes-7d.json").read_text(encoding="utf-8"))
    model_checks = [c for c in rec["checks"] if not c[0].startswith(("every feeder's conduit", "every rated opening whose code"))]
    bad = [c[0] for c in model_checks if not c[1]]
    if bad:
        raise SystemExit(f"won't publish the services model: {bad}")
    src = OUT / f"services-{ISSUE}.ifc"
    if rec.get("model") != src.name:
        raise SystemExit(f"routes-7d.json is the run of {rec.get('model')}, not {src.name}: `brownfield routes --ifc` again")
    before = sorted((q for q in to.glob("services-addendum-*.ifc") if q.name != src.name),
                    key=lambda q: int(q.stem.rsplit("-", 1)[1]))
    shutil.copyfile(src, to / src.name)
    sch = to / f"services-{ISSUE}"
    if sch.exists():
        shutil.rmtree(sch)
    sch.mkdir()
    for name in PUBLISHED_SCHEDULES:
        shutil.copyfile(OUT / "schedules" / f"{name}.csv", sch / f"{name}.csv")
    diff = None
    if before:
        diff = changes(before[-1], to / src.name)
        (to / f"changes-services-{ISSUE}.json").write_text(json.dumps(diff, indent=1) + "\n", encoding="utf-8")
    open_items = []
    over = [b for b in rec["conduit_bends"] if not b["ok"]]
    if over:
        open_items.append(f"{len(over)} feeder conduits over NEC 352.26's 360° of bends")
    judged = sum(r["count"] for r in rec["firestop"] if r["F"] and "listed" in r["asks"].split(";")[0] and r["fit"] in ("partial", "none"))
    if any(r["F"] and "listed" in r["asks"].split(";")[0] and not r["fit"] for r in rec["firestop"]):
        open_items.append("a rated opening's firestop condition with no entry in the table")
    layers = Counter()
    for r in read_back(src):
        layers[r["props"].get("Layer")] += 1
    return {"model": src.name, "frame": f"{REVISION.replace('-', ' ').title()}'s frame", "elements": rec["elements"],
            "layers": dict(sorted(layers.items())), "issued": issued,
            "files": [{"path": f"{sch.name}/{n}.csv", "label": LABELS[n]} for n in PUBLISHED_SCHEDULES],
            "status": f"Addendum {addendum}",
            "changes": f"changes-services-{ISSUE}.json" if diff else None,
            "changes_against": before[-1].name if before else None,
            "note": f"issued with Addendum {addendum}"
            + (f"; {judged} rated openings firestopped by the maker's engineering judgment" if judged else "")
            + ("; open: " + "; ".join(open_items) if open_items else "")}
