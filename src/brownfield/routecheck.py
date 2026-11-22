"""Pass 3g step 7b's checks on forge's routes (`out/pass3/routes.json`), worked again here from the
frame, the requests and the code's own numbers rather than taken from forge's records:

- every run routed, and the routes answer the requests as they stand now;
- no two services clash (forge's check, and the boxes overlapped again here);
- every hole in an I-joist's web within APA Z725E's Table 5 at its distance from the support, its
  rule 6 (edges more than twice the larger hole apart) and rule 11 (three maximum-size holes a
  span); in a stud within IBC 2308.5.10 (40% or 60% of its depth, 5/8 in. to its edges); every cut
  plate tied (2308.5.8); a sawn joist's within 2308.4.2.4;
- every drain falling toward its stack by IPC Table 704.1's slope (the condensate by IMC 307.2.1's),
  every vent graded back to its drain (IPC 905.2);
- no duct through a rated ceiling (so no ceiling radiation dampers, IBC 717.6.2); every penetration
  of a rated floor or wall counted for its firestop (714); the sleeves through the footings listed;
- the sprinklers moved off equipment and the soffit strips still covering their cells, at least
  8 ft apart in each compartment (Tyco TFP403).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import OUT_DIR
from .routing import FT, IN, ceiling_z

R = "systems.routing."
ROUTES = OUT_DIR / "pass3" / "routes.json"


def _attached(req: dict, owner: str) -> bool:
    """forge's `Request::attached`: its own solids, an id, a family by a trailing `*` or a leading one."""
    if owner == req["id"]:
        return True
    for a in req.get("attach", []):
        if a.endswith("*"):
            if owner.startswith(a[:-1]):
                return True
        elif a.startswith("*"):
            if owner.endswith(a[1:]):
                return True
        elif a == owner:
            return True
    return False


def _boxes(points: list, half: float, piece: float = 0.25) -> list[tuple[list, list]]:
    """A branch's runs as boxes: the pipe and its clearance across, end to end along; a sloped run in
    pieces of `piece` m, each to its own heights."""
    out = []
    for a, c in zip(points, points[1:]):
        run = max(range(3), key=lambda i: abs(c[i] - a[i]))
        n = max(1, int(np.ceil(abs(c[run] - a[run]) / piece))) if run != 2 and abs(c[2] - a[2]) > 1e-9 else 1
        for k in range(n):
            p0 = [a[i] + (c[i] - a[i]) * k / n for i in range(3)]
            p1 = [a[i] + (c[i] - a[i]) * (k + 1) / n for i in range(3)]
            e = [0.0 if i == run else half for i in range(3)]
            out.append(([min(p0[i], p1[i]) - e[i] for i in range(3)], [max(p0[i], p1[i]) + e[i] for i in range(3)]))
    return out


def clash_pairs(body: dict, rt: dict) -> list[tuple[str, str]]:
    """Every pair of services whose boxes overlap by more than the tolerance on all three axes: a
    routed one against another or against a pinned one, unless one is attached to the other (as
    forge compares them; two pinned ones were placed and checked in 7a)."""
    reqs = {r["id"]: r for r in body["requests"]}
    lo, hi, own = [], [], []
    for rec in rt["routes"]:
        r = reqs[rec["id"]]
        half = r["od_m"] / 2 + r.get("clear_m", 0.0)
        for b in rec.get("branches", []):
            for a, c in _boxes(b["points"], half):
                lo.append(a)
                hi.append(c)
                own.append(rec["id"])
    n_routed = len(own)
    for o in body["obstacles"]:
        if "/" in o["id"]:
            lo.append(o["lo"])
            hi.append(o["hi"])
            own.append(o["id"])
    lo, hi = np.array(lo), np.array(hi)
    tol = body["clash_tol_m"]
    found = set()
    for s in range(0, n_routed, 400):
        e = min(s + 400, n_routed)
        a_lo, a_hi = lo[s:e, None, :], hi[s:e, None, :]
        ov = (np.minimum(a_hi, hi[None]) - np.maximum(a_lo, lo[None]) > tol).all(axis=2)
        for i, j in zip(*np.nonzero(ov)):
            o1, o2 = own[s + i], own[j]
            if o1 == o2 or (o1, o2) in found or (o2, o1) in found:
                continue
            if _attached(reqs[o1], o2) or (o2 in reqs and _attached(reqs[o2], o1)):
                continue
            found.add((o1, o2))
    return sorted(tuple(sorted(x)) for x in found)


def _bounds(m: dict) -> tuple[list, list]:
    return ([min(b[0][i] for b in m["boxes"]) for i in range(3)], [max(b[1][i] for b in m["boxes"]) for i in range(3)])


def _faces(m: dict, caps: list[tuple[list, list]]) -> tuple[int, float, float]:
    """An I-joist's axis and its supports' inside faces: the cap plates crossing under its ends."""
    lo, hi = _bounds(m)
    ax = 0 if hi[0] - lo[0] > hi[1] - lo[1] else 1
    o = 1 - ax

    def under(end: float, low: bool) -> float | None:
        best = None
        for a, b in caps:
            if abs(b[2] - lo[2]) < 3e-3 and a[o] < hi[o] and b[o] > lo[o] and a[ax] <= end + 1e-6 and b[ax] >= end - 1e-6 and b[ax] - a[ax] < 0.4:
                v = b[ax] if low else a[ax]
                best = v if best is None else (max(best, v) if low else min(best, v))
        return best

    f0 = under(lo[ax] + 0.01, True)
    f1 = under(hi[ax] - 0.01, False)
    return ax, (lo[ax] + 0.0381 if f0 is None else f0), (hi[ax] - 0.0381 if f1 is None else f1)


def apa_allowed(d: float, span: float, rows: list[tuple[float, float]], saf: float, min_edge: float, any_hole: float) -> float:
    """APA Z725E Table 5 (m): the largest round hole whose least distance from the support's face
    to its centre is no more than `d`; on a span shorter than the chart's SAF (note e) each
    distance shrinks by span/SAF, but never under `min_edge` to the hole's edge; rule 9's small hole
    anywhere."""
    k = min(span / saf, 1.0)
    best = any_hole
    for hole, dist in rows:
        need = max(dist * k, min_edge + hole / 2) if k < 1 else dist
        if need <= d + 1e-9:
            best = max(best, hole)
    return best


def rule6(hs: list[tuple[list, float, int]]) -> float | None:
    """APA's rule 6 in one joist's web: the least, over every pair of its holes (centre, diameter,
    the axis they run along), of their edges' distance in the web's plane less twice the larger
    hole (m; it must be over 0). None for fewer than two holes."""
    least = None
    for i in range(len(hs)):
        for j in range(i + 1, len(hs)):
            (c1, d1, a1), (c2, d2, _) = hs[i][:3], hs[j][:3]
            dist = sum((c1[k] - c2[k]) ** 2 for k in range(3) if k != a1) ** 0.5
            margin = (dist - d1 / 2 - d2 / 2) - 2 * max(d1, d2)
            least = margin if least is None else min(least, margin)
    return least


def grade_miss(points: list, slope: float, rises: bool) -> float:
    """How far a branch's points (from where it joins, out to its fixture) miss their grade (m):
    a drain's must rise by at least `slope` of each level run going out (it falls to its stack); a
    vent's (`rises`) must fall by that much going out, never rise."""
    worst = 0.0
    for a, c in zip(points, points[1:]):
        dh = abs(c[0] - a[0]) + abs(c[1] - a[1])
        dz = c[2] - a[2]
        worst = max(worst, (dz + slope * dh) if rises else (slope * dh - dz))
    return worst


def checks(apt: dict, p: dict, body: dict, rt: dict, frame: dict, fresh_sha: str | None = None) -> list[tuple[str, bool, str]]:
    from .fire import layout
    from .routes import _apa_rows, heads_covered

    out: list[tuple[str, bool, str]] = []
    reqs = {r["id"]: r for r in body["requests"]}
    routes = rt["routes"]
    if fresh_sha is not None:
        out.append(("forge's routes answer the requests as they stand (their hash)", rt.get("requests_sha") == fresh_sha,
                    f"routes {rt.get('requests_sha')}, requests {fresh_sha}"))
    bad = [r["id"] for r in routes if not r.get("ok")]
    out.append((f"every run routed through the frame ({len(routes)})", not bad, f"{len(routes) - len(bad)} routed" + (f"; not: {', '.join(bad[:6])}" if bad else "")))
    out.append(("no two services clash (forge)", not rt["clashes"], f"{len(rt['clashes'])} pairs"))
    pairs = clash_pairs(body, rt)
    out.append(("no two services clash (their boxes overlapped again here)", not pairs, f"{len(pairs)} pairs" + (f": {pairs[:3]}" if pairs else "")))

    # -- Holes.
    members = {m["id"]: m for m in frame["members"]}
    caps = [b for m in frame["members"] if m["kind"] == "cap plates" for b in [(bb[0], bb[1]) for bb in m["boxes"]]]
    rows = [(a * IN, b * IN) for a, b in _apa_rows()]
    saf, min_edge, any_hole = p[R + "apa_saf_in"] * IN, p[R + "apa_min_edge_in"] * IN, p[R + "apa_any_hole_in"] * IN
    nonbearing = [(b["lo"], b["hi"]) for b in body["rules"]["nonbearing"]]
    inside = lambda c, lo, hi: all(lo[i] - 1e-6 <= c[i] <= hi[i] + 1e-6 for i in range(3))  # noqa: E731
    faces: dict[str, tuple] = {}
    holes: dict[str, list] = {}
    worst_apa, n_apa, worst_stud, worst_edge, n_stud, ties, worst_plate, worst_sawn, n_sawn = 0.0, 0, 0.0, None, 0, 0, 0.0, 0.0, 0
    sleeves: dict[str, int] = {}
    for rec in routes:
        for b in rec.get("branches", []):
            for bo in b.get("bores", []):
                m = members[bo["member"]]
                c, d = bo["at"], bo["hole_m"]
                kind = m["kind"]
                lo, hi = _bounds(m)
                if bo.get("sleeve"):
                    sleeves[kind] = sleeves.get(kind, 0) + 1
                if kind in ("floor joists", "roof joists") and len(m["boxes"]) == 3:
                    if m["id"] not in faces:
                        faces[m["id"]] = _faces(m, caps)
                    ax, f0, f1 = faces[m["id"]]
                    dist = min(c[ax] - f0, f1 - c[ax])
                    allowed = apa_allowed(dist, f1 - f0, rows, saf, min_edge, any_hole) if dist >= 0 else 0.0
                    worst_apa = max(worst_apa, d / allowed if allowed > 0 else 9.9)
                    n_apa += 1
                    holes.setdefault(m["id"], []).append((c, d, bo["axis"], allowed))
                elif kind in ("floor joists", "roof joists"):
                    depth = hi[2] - lo[2]
                    edge = min(c[2] - d / 2 - lo[2], hi[2] - (c[2] + d / 2))
                    worst_sawn = max(worst_sawn, d / (depth / 3), (2 * IN) / max(edge, 1e-9))
                    n_sawn += 1
                elif kind == "studs":
                    dax = 0 if hi[0] - lo[0] > hi[1] - lo[1] else 1
                    frac = p[R + "stud_hole_nonbearing"] if any(inside([(lo[i] + hi[i]) / 2 for i in range(3)], a, z) for a, z in nonbearing) \
                        else p[R + "stud_hole_bearing"]
                    worst_stud = max(worst_stud, d / (frac * (hi[dax] - lo[dax])))
                    e = min(c[dax] - lo[dax], hi[dax] - c[dax]) - d / 2
                    worst_edge = e if worst_edge is None else min(worst_edge, e)
                    n_stud += 1
                elif kind in ("plates", "cap plates"):
                    ties += 1
                    wax = 0 if hi[0] - lo[0] < hi[1] - lo[1] else 1
                    frac = p[R + "stud_hole_nonbearing"] if any(inside([(lo[i] + hi[i]) / 2 for i in range(3)], a, z) for a, z in nonbearing) \
                        else p[R + "stud_hole_bearing"]
                    worst_plate = max(worst_plate, d / (frac * (hi[wax] - lo[wax])))
    out.append((f"every hole in an I-joist's web within APA Table 5 at its distance from the support ({n_apa} holes)", worst_apa <= 1 + 1e-9,
                f"largest {worst_apa:.0%} of what the chart allows there"))
    least_gap, worst_pair, over11 = None, None, []
    sizes = sorted({h for h, _ in rows} | {any_hole})
    for mid, hs in holes.items():
        m6 = rule6(hs)
        if m6 is not None and (least_gap is None or m6 < least_gap):
            least_gap, worst_pair = m6, mid
        # Rule 11: a maximum-size hole needs its location's row (a smaller row wouldn't take it).
        n_max = sum(1 for _, d, _, allowed in hs if d > max([s for s in sizes if s < allowed - 1e-9], default=0.0) + 1e-9)
        if n_max > 3:
            over11.append((mid, n_max))
    out.append(("APA rule 6: adjacent holes' edges more than twice the larger hole apart, in every joist", least_gap is None or least_gap > 0,
                "no joist with two holes" if least_gap is None else f"least {least_gap / IN:+.2f} in. past it ({worst_pair})"))
    out.append(("APA rule 11: at most three maximum-size holes a span", not over11,
                f"{len(holes)} joists bored" + (f"; over: {over11[:3]}" if over11 else "")))
    out.append((f"every hole in a stud within IBC 2308.5.10: 40% of its depth (60% in a nonbearing wall), 5/8 in. to its edges ({n_stud} holes)",
                worst_stud <= 1 + 1e-9 and (worst_edge is None or worst_edge >= p[R + "stud_edge_in"] * IN - 1e-6),
                f"largest {worst_stud:.0%} of its limit; least edge {(worst_edge or 0) / IN:.2f} in."))
    out.append(("every cut plate tied across with a 16 ga strap (IBC 2308.5.8), its hole within the stud's limit", worst_plate <= 1 + 1e-9,
                f"{ties} ties; largest hole {worst_plate:.0%} of its limit"))
    out.append((f"every hole in a sawn joist within IBC 2308.4.2.4: a third of its depth, 2 in. from its edges ({n_sawn} holes)", worst_sawn <= 1 + 1e-9,
                f"worst {worst_sawn:.0%} of its limit" if n_sawn else "none"))
    # IBC 2308.5.8: a partition holding pipes that runs along the floor joists under it needs them
    # doubled and spaced for the pipes. Each pinned vertical's wall, against the joists' direction.
    joist_along = {}
    for m in frame["members"]:
        if m["kind"] == "floor joists" and m["storey"] not in joist_along:
            lo, hi = _bounds(m)
            joist_along[m["storey"]] = 0 if hi[0] - lo[0] > hi[1] - lo[1] else 1
    parallel, held = set(), set()
    for o in body["obstacles"]:
        if "/" not in o["id"] or o["hi"][2] - o["lo"][2] < apt["storey_m"] * 0.5:
            continue
        c = [(o["lo"][i] + o["hi"][i]) / 2 for i in range(2)]
        for w in apt["rooms"]["walls"]:
            if all(w["lo_m"][i] - 1e-3 <= c[i] <= w["hi_m"][i] + 1e-3 for i in range(2)) and w["lo_m"][2] < o["hi"][2] and w["hi_m"][2] > o["lo"][2]:
                held.add(w["id"])
                along = 0 if w["hi_m"][0] - w["lo_m"][0] > w["hi_m"][1] - w["lo_m"][1] else 1
                if joist_along.get(w["storey"]) == along:
                    parallel.add(w["id"])
    out.append(("every wall holding a vertical service runs across the floor joists under it (else IBC 2308.5.8 doubles them)", not parallel,
                f"{len(held)} walls" + (f"; along them: {sorted(parallel)[:4]}" if parallel else "")))
    out.append(("the sleeves through the footings, the slab and the stem walls listed (for the structural engineer)", True,
                ", ".join(f"{n} through {k}" for k, n in sorted(sleeves.items())) or "none"))

    # -- Grades.
    worst_fall, n_drain, worst_vent, n_vent = 0.0, 0, 0.0, 0
    for rec in routes:
        r = reqs[rec["id"]]
        for b in rec.get("branches", []):
            if r["system"] in ("drain", "condensate"):
                worst_fall = max(worst_fall, grade_miss(b["points"], r.get("slope", 0.0), False))
                n_drain += 1
            elif r["system"] == "vent":
                worst_vent = max(worst_vent, grade_miss(b["points"], p[R + "vent_slope_in_ft"] / 12, True))
                n_vent += 1
    out.append(("every drain falls toward its stack by IPC Table 704.1's slope (1/4 in./ft to 2-1/2 in., 1/8 above), the condensate by IMC 307.2.1's 1%",
                worst_fall <= 1e-6, f"{n_drain} branches; worst {worst_fall * 1000:.1f} mm short"))
    out.append(("every vent rises toward its vent stack by 1/8 in./ft, graded back to its drain (IPC 905.2)", worst_vent <= 1e-6,
                f"{n_vent} branches; worst {worst_vent * 1000:.1f} mm short"))

    # -- Rated assemblies.
    top = {}
    for rec in routes:
        r = reqs[rec["id"]]
        if r["system"] != "duct" or not r.get("flat"):
            continue
        k = int(r["flat"].split("-")[0])
        z = max(pt[2] for b in rec.get("branches", []) for pt in b["points"]) if rec.get("branches") else -1e9
        top[r["flat"]] = max(top.get(r["flat"], -1e9), z + r["od_m"] / 2 - (ceiling_z(apt, k) - p[R + "ceiling_assembly_in"] * IN))
    worst_top = max(top.values(), default=-1.0)
    out.append(("no duct through a rated ceiling: every flat's ducts in its soffits (no ceiling radiation dampers, IBC 717.6.2)", worst_top <= 1e-6,
                f"highest duct {-worst_top / IN:.1f} in. under the ceiling"))
    pen = penetrations(apt, p, body, rt)
    out.append(("every penetration of a rated floor or wall counted for its firestop system (IBC 714.5)", True,
                f"{pen['floor']} through the floors, {pen['top plate']} up through walls' top plates into the floors, "
                f"{pen['membrane']} through the ceilings' membrane, {pen['wall']} through the party and stair walls"))

    # -- Sprinklers.
    ok, worst = heads_covered(apt, body["moved_heads"])
    moved = sum(1 for ms in body["moved_heads"].values() for m in ms if m["from"] != m["to"])
    out.append((f"every sprinkler moved off equipment or a strip soffit still covers its cell ({moved} moved)", ok, f"farthest reach {worst:.2f} ft"))
    lay = layout(apt, p)
    least = None
    for name, ms in body["moved_heads"].items():
        comp = [h["comp"] for h in lay[name]["heads"]]
        pts = [m["to"] for m in ms]
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                if comp[i] == comp[j]:
                    d = ((pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2) ** 0.5
                    least = d if least is None else min(least, d)
    out.append(("sprinklers at least 8 ft apart in each compartment (Tyco TFP403)", least is None or least >= p[R + "head_min_spacing_ft"] * FT - 1e-6,
                f"least {least / FT:.1f} ft" if least else "one a compartment"))
    return out


def penetrations(apt: dict, p: dict, body: dict, rt: dict) -> dict:
    """The rated assemblies' penetrations: through each floor between flats (its subfloor, z at the
    floor); through each ceiling's plane (the joists' underside), at a wall's top plates or through
    the open ceiling's membrane; and through the party and stair walls, carried up through the
    joists' space over them to the floor above. By the routed runs and the pinned verticals (stacks,
    risers, line sets, feeders). Each takes a listed through-penetration firestop system (IBC
    714.5.1) or a membrane one (714.5.2)."""
    reqs = {r["id"]: r for r in body["requests"]}
    floors = [k * apt["storey_m"] for k in range(1, apt["storeys"])]
    membranes = [ceiling_z(apt, k) for k in range(1, apt["storeys"] + 1)]
    walls = []
    for x in apt["parts"]:
        if x["kind"] == "party_wall":
            k = round(x["lo_m"][2] / apt["storey_m"]) + 1
            walls.append((x["lo_m"], [x["hi_m"][0], x["hi_m"][1], k * apt["storey_m"]]))
    plates = [(w["lo_m"], w["hi_m"]) for w in apt["rooms"]["walls"]] + [(x["lo_m"], x["hi_m"]) for x in apt["parts"]
                                                                       if x["kind"] in ("party_wall", "exterior_wall")]
    rows: dict[tuple[str, str, float], int] = {}

    def add(where: str, system: str, od: float) -> None:
        key = (where, system, round(od / IN, 2))
        rows[key] = rows.get(key, 0) + 1

    def crosses(a: float, b: float, z: float) -> bool:
        return min(a, b) < z < max(a, b)

    segs = []
    for rec in rt["routes"]:
        r = reqs[rec["id"]]
        for b in rec.get("branches", []):
            for a, c in zip(b["points"], b["points"][1:]):
                segs.append((r["system"], r["od_m"], a, c))
    for o in body["obstacles"]:
        if "/" in o["id"] and o["hi"][2] - o["lo"][2] > apt["storey_m"] * 0.5:
            c = [(o["lo"][i] + o["hi"][i]) / 2 for i in range(2)]
            segs.append(("pinned", o["hi"][0] - o["lo"][0], [*c, o["lo"][2]], [*c, o["hi"][2]]))
    for system, od, a, c in segs:
        if not (0 < a[0] < apt["depth_m"] and 0 < a[1] < apt["length_m"]):
            continue
        for z in floors:
            if crosses(a[2], c[2], z):
                add("floor", system, od)
        for z in membranes:
            if crosses(a[2], c[2], z):
                on_wall = any(lo[0] - 1e-3 <= a[0] <= hi[0] + 1e-3 and lo[1] - 1e-3 <= a[1] <= hi[1] + 1e-3 and lo[2] < z <= hi[2] + 0.4
                              for lo, hi in plates)
                add("top plate" if on_wall else "membrane", system, od)
        for lo, hi in walls:
            mid = [(a[i] + c[i]) / 2 for i in range(3)]
            for ax in (0, 1):
                if hi[ax] - lo[ax] < 0.5 and crosses(a[ax], c[ax], (lo[ax] + hi[ax]) / 2) \
                        and all(lo[i] <= mid[i] <= hi[i] for i in range(3) if i != ax):
                    add("wall", system, od)
    tot = {w: sum(n for (k, _, _), n in rows.items() if k == w) for w in ("floor", "top plate", "membrane", "wall")}
    return {**tot, "rows": [{"where": k, "system": s, "od_in": d, "n": n} for (k, s, d), n in sorted(rows.items())]}


def quantities(body: dict, rt: dict) -> list[dict]:
    """The routed lengths by system and outside diameter (m), with their bends and holes."""
    reqs = {r["id"]: r for r in body["requests"]}
    q: dict[tuple[str, float], dict] = {}
    for rec in rt["routes"]:
        r = reqs[rec["id"]]
        key = (r["system"], round(r["od_m"] / IN, 3))
        row = q.setdefault(key, {"system": key[0], "od_in": key[1], "m": 0.0, "bends": 0, "holes": 0, "runs": 0})
        row["runs"] += 1
        for b in rec.get("branches", []):
            row["m"] += b["length_m"]
            row["bends"] += b["bends"]
            row["holes"] += len(b.get("bores", []))
    return sorted(q.values(), key=lambda x: (x["system"], x["od_in"]))


def load(apt: dict, p: dict) -> tuple[dict, dict | None, str]:
    """The requests as they stand (worked out afresh), and forge's routes if it has run: (requests,
    routes or None, the requests' hash)."""
    from .routes import requests

    body = requests(apt, p)
    rt = json.loads(ROUTES.read_text(encoding="utf-8")) if Path(ROUTES).exists() else None
    return body, rt, body["requests_sha"]
