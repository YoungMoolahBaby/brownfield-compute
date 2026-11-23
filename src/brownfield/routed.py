"""Pass 3g step 7c (D28): forge's routes read back as trees, for steps 3-6 to size and check on.

forge (`routes-json`) writes each run as branches, grown one at a time: each from a point on what
the run had routed so far (its root, a goal box such as a riser, or an earlier branch) out to one
terminal, as a polyline of straight runs. Here each run becomes a tree of edges between its
junctions (where a branch tees off another), each edge with its length, its bends and the
terminals beyond it, so a design can walk from any terminal back to its root:
- **a length:** the polylines' lengths, the short piece from a branch's last cell to its terminal,
  and, on a drain or a vent, the drop (or rise) where a branch joins its trunk (the branch has
  fallen less than the trunk where they meet; forge keeps that, `run_at`);
- **its fittings:** each bend an elbow; at each junction, a tee: its branch where the path turns
  off the run it leaves, its run where the path goes on past another branch.

`load` says whether the routes answer the requests as they stand (the hashes forge echoes); a stale
or missing route is never used in silence (`Routes.why`).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from . import OUT_DIR

REQUESTS = OUT_DIR / "pass3" / "route-requests.json"
ROUTES = OUT_DIR / "pass3" / "routes.json"
# The sizes 7c asked beyond steps 3-6's, kept in git: the router's result depends on the order sizes
# grew in, so the requests are reproducible from these, not from rerunning the cycle afresh.
GROWN = Path(__file__).resolve().parents[2] / "data" / "route_sizes.json"
JOIN_TOL_M = 0.02  # a branch's first point within this of its parent's polyline (in plan, on a graded run)


def _seg(p: list[float], a: list[float], c: list[float], dims: int) -> tuple[float, float]:
    """The distance from `p` to the segment a-c over the first `dims` axes, and how far along it."""
    ax = [c[i] - a[i] for i in range(dims)]
    l2 = sum(x * x for x in ax)
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, sum((p[i] - a[i]) * ax[i] for i in range(dims)) / l2))
    return math.dist(p[:dims], [a[i] + t * ax[i] for i in range(dims)]), t * math.dist(a, c)


@dataclass
class Branch:
    terminal: str
    points: list[list[float]]
    to: list[float]
    parent: int | None = None
    at: float = 0.0  # arc length along the parent where it tees off
    join_m: float = 0.0  # the drop (or rise) into the parent, on a graded run
    cum: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cum = [0.0]
        for a, c in zip(self.points, self.points[1:]):
            self.cum.append(self.cum[-1] + math.dist(a, c))

    @property
    def length(self) -> float:
        return self.cum[-1]

    @property
    def tail_m(self) -> float:
        """From the last cell's centre to the terminal itself."""
        return math.dist(self.points[-1], self.to)

    def where(self, p: list[float], dims: int) -> tuple[float, float]:
        """The nearest point of the polyline to `p` (over `dims` axes): (distance, arc length)."""
        best = (math.inf, 0.0)
        for k, (a, c) in enumerate(zip(self.points, self.points[1:])):
            d, s = _seg(p, a, c, dims)
            if d < best[0] - 1e-12:
                best = (d, self.cum[k] + s)
        return best

    def turns(self, s0: float, s1: float) -> int:
        """The polyline's bends (where its direction changes) at arc lengths in [s0, s1), not
        counting its first point."""
        n = 0
        for k in range(1, len(self.points) - 1):
            s = self.cum[k]
            if not (s0 - 1e-9 <= s < s1 - 1e-9 and s > 1e-9):
                continue
            a, b, c = self.points[k - 1], self.points[k], self.points[k + 1]
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - b[i] for i in range(3)]
            cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            if math.hypot(*cross) > 1e-6 * max(1e-12, math.hypot(*u) * math.hypot(*v)):
                n += 1
        return n

    def point_at(self, s: float) -> list[float]:
        for k, (a, c) in enumerate(zip(self.points, self.points[1:])):
            if s <= self.cum[k + 1] + 1e-12 or k == len(self.points) - 2:
                L = self.cum[k + 1] - self.cum[k]
                t = 0.0 if L == 0 else min(1.0, max(0.0, (s - self.cum[k]) / L))
                return [a[i] + t * (c[i] - a[i]) for i in range(3)]
        return list(self.points[-1])


@dataclass
class Edge:
    """A piece of one branch between two junctions (or a junction and its terminal)."""
    branch: int
    s0: float
    s1: float
    length: float
    bends: int
    up: int | None  # the edge it hangs from (None at the root)
    tee: str  # how it leaves `up`: "run" (on along the same branch), "branch" (a tee's side), "root"
    terminal: str | None = None  # the terminal at its far end, if any
    below: list[str] = field(default_factory=list)  # every terminal beyond it
    a: list[float] = field(default_factory=list)  # its two ends (m)
    b: list[float] = field(default_factory=list)


class Tree:
    """One run's routed tree (forge's record `rec` for request `req`)."""

    def __init__(self, req: dict, rec: dict) -> None:
        self.req, self.rec, self.id = req, rec, req["id"]
        graded = bool(req.get("slope"))
        self.branches: list[Branch] = []
        self.far: list[str] = []
        for i, b in enumerate(rec.get("branches", [])):
            br = Branch(b["terminal"], [list(map(float, q)) for q in b["points"]], list(map(float, b["to"])))
            # Its parent: the earlier branch it touches; on a graded run, failing that, the one it
            # meets in plan, above or below it by the fall each has run. (Where it starts on a
            # vertical piece of its trunk it touches it, and joins it there: in plan alone it would
            # join at that piece's top and count the piece twice.)
            best = self._nearest(br.points[0], 3)
            if best is None and graded:
                best = self._nearest(br.points[0], 2)
            if best is not None:
                br.parent, br.at = best[1], best[2]
                if graded:
                    br.join_m = abs(br.points[0][2] - self.branches[best[1]].point_at(best[2])[2])
            elif i > 0 and not self._at_source(br.points[0]):
                self.far.append(br.terminal)
            self.branches.append(br)
        self.lead_m = math.dist(self.branches[0].points[0], req["root"]) if self.branches and self._at_root(self.branches[0].points[0]) else 0.0
        self._edges()

    def _nearest(self, p: list[float], dims: int) -> tuple[float, int, float] | None:
        """The earlier branch within JOIN_TOL_M of `p` over `dims` axes, the nearest: (distance,
        branch, arc length along it)."""
        best = None
        for j, pb in enumerate(self.branches):
            d, s = pb.where(p, dims)
            if best is None or d < best[0] - 1e-12:
                best = (d, j, s)
        return best if best is not None and best[0] <= JOIN_TOL_M else None

    def _at_root(self, p: list[float]) -> bool:
        return math.dist(p, self.req["root"]) <= self.req.get("snap_m", 0.2) + 1e-6

    def _at_source(self, p: list[float]) -> bool:
        """At the root or in one of the goal boxes (a riser it tees off)."""
        if self._at_root(p):
            return True
        return any(all(g["lo"][k] - 0.03 <= p[k] <= g["hi"][k] + 0.03 for k in range(3)) for g in self.req.get("goals") or [])

    def _edges(self) -> None:
        cuts: dict[int, set[float]] = {i: {0.0, b.length} for i, b in enumerate(self.branches)}
        for b in self.branches:
            if b.parent is not None:
                cuts[b.parent].add(b.at)
        self.edges: list[Edge] = []
        first: dict[int, int] = {}  # a branch's first edge
        at_cut: dict[tuple[int, float], int] = {}  # the edge ending at a branch's cut
        for i, b in enumerate(self.branches):
            ss = sorted(cuts[i])
            ss = [s for k, s in enumerate(ss) if k == 0 or s - ss[k - 1] > 1e-6]
            prev = None
            for k, (s0, s1) in enumerate(zip(ss, ss[1:])):
                L = s1 - s0
                if k == 0:
                    L += b.join_m
                last = k == len(ss) - 2
                if last:
                    L += b.tail_m
                if b.parent is None and k == 0:
                    up, tee = None, "root"
                elif k == 0:
                    up, tee = self._edge_at(b.parent, b.at, at_cut, first), "branch"
                else:
                    up, tee = prev, "run"
                self.edges.append(Edge(i, s0, s1, L, b.turns(s0, s1), up, tee, b.terminal if last else None,
                                       a=b.point_at(s0), b=b.point_at(s1)))
                n = len(self.edges) - 1
                if k == 0:
                    first[i] = n
                at_cut[(i, round(s1, 6))] = n
                prev = n
        self._at_cut, self._first = at_cut, first
        # The terminals beyond each edge.
        for n, e in enumerate(self.edges):
            if e.terminal is not None:
                m: int | None = n
                while m is not None:
                    self.edges[m].below.append(e.terminal)
                    m = self.edges[m].up

    def _edge_at(self, i: int, s: float, at_cut: dict, first: dict) -> int | None:
        """The edge of branch `i` that ends at its cut `s` (where a later branch tees off); at its
        very start, the edge it in turn hangs from."""
        if s <= 1e-6:
            b = self.branches[i]
            return None if b.parent is None else self._edge_at(b.parent, b.at, at_cut, first)
        key = (i, round(s, 6))
        if key in at_cut:
            return at_cut[key]
        # Cuts are made before the edges; the nearest one.
        cands = [(abs(k[1] - s), v) for k, v in at_cut.items() if k[0] == i]
        return min(cands)[1]

    # ---- what the designs ask ----

    @property
    def ok(self) -> bool:
        return bool(self.rec.get("ok")) and not self.far

    @property
    def length_m(self) -> float:
        return self.lead_m + sum(e.length for e in self.edges)

    def terminals(self) -> list[str]:
        return [e.terminal for e in self.edges if e.terminal is not None]

    def chain(self, terminal: str) -> list[int]:
        """The edges from the root out to a terminal, in order. A terminal forge reached on the tree
        already (its branch of no length, as a flat's loop's end can be) ends the edge its parent was
        cut at there."""
        n = next((k for k, e in enumerate(self.edges) if e.terminal == terminal), None)
        if n is None:
            b = next(b for b in self.branches if b.terminal == terminal)
            if b.parent is None:
                return []
            n = self._edge_at(b.parent, b.at, self._at_cut, self._first)
        out = []
        m: int | None = n
        while m is not None:
            out.append(m)
            m = self.edges[m].up
        return out[::-1]

    def path(self, terminal: str) -> dict:
        """From the root to a terminal: its length (m), its bends, and the tees it passes (on their
        branch, where it turns off; on their run, where it goes on past another branch)."""
        es = self.chain(terminal)
        tee_branch = sum(1 for k in es if self.edges[k].tee == "branch")
        tee_run = sum(1 for k in es if self.edges[k].tee == "run")
        return {"m": self.lead_m + sum(self.edges[k].length for k in es), "bends": sum(self.edges[k].bends for k in es),
                "tee_branch": tee_branch, "tee_run": tee_run, "edges": es}

    def point(self, terminal: str) -> list[float]:
        return next(b.to for b in self.branches if b.terminal == terminal)

    @property
    def root(self) -> list[float]:
        return self.branches[0].points[0] if self.branches else self.req["root"]

    def piece(self, n: int) -> list[list[float]]:
        """Edge `n` as a polyline (m): its part of forge's branch, from where it leaves its trunk (the
        trunk's point: on a drain or a vent, the drop or rise into it) or the run's root, to its
        terminal if it ends at one. Its length is the edge's, but for a join off a level run, where
        forge's branch starts within JOIN_TOL_M of its trunk and the gap isn't counted."""
        e = self.edges[n]
        br = self.branches[e.branch]
        pts = [br.point_at(e.s0)]
        pts += [list(br.points[k]) for k in range(1, len(br.points) - 1) if e.s0 + 1e-9 < br.cum[k] < e.s1 - 1e-9]
        pts.append(br.point_at(e.s1))
        if e.s0 <= 1e-9:
            if br.parent is not None:
                pts.insert(0, self.branches[br.parent].point_at(br.at))
            elif e.branch == 0 and self.lead_m > 0:
                pts.insert(0, list(map(float, self.req["root"])))
        if e.terminal is not None:
            pts.append(list(br.to))
        out = [pts[0]]
        for q in pts[1:]:
            if math.dist(q, out[-1]) > 1e-7:
                out.append(q)
        return out


@dataclass
class Routes:
    body: dict
    rt: dict | None
    fresh: bool
    why: str = ""

    def __post_init__(self) -> None:
        self.reqs = {r["id"]: r for r in self.body["requests"]}
        self.recs = {r["id"]: r for r in (self.rt or {}).get("routes", [])}
        self._trees: dict[str, Tree] = {}

    def tree(self, id_: str) -> Tree:
        if id_ not in self._trees:
            self._trees[id_] = Tree(self.reqs[id_], self.recs[id_])
        return self._trees[id_]

    def ids(self, prefix: str) -> list[str]:
        return [k for k in self.recs if k.startswith(prefix)]

    def pinned(self, id_: str) -> dict:
        """A pinned service's box (a riser, a stack, a conduit)."""
        return next(o for o in self.body["obstacles"] if o["id"] == id_)

    @property
    def status(self) -> str:
        n = len(self.recs)
        ok = sum(1 for r in self.recs.values() if r.get("ok"))
        return f"routed {ok} of {n}" + ("" if self.fresh else f" (stale: {self.why})")


def load(apt: dict, p: dict, body: dict | None = None) -> Routes | None:
    """forge's routes with the requests they answer: fresh only if forge routed exactly these
    requests (worked out afresh from the model and the parameters unless `body` is given) on this
    model and frame. None if forge hasn't run."""
    from .routes import requests

    if not ROUTES.exists():
        return None
    body = body or requests(apt, p)
    rt = json.loads(Path(ROUTES).read_text(encoding="utf-8"))
    why = []
    for k in ("requests_sha", "geometry_sha", "framing_sha"):
        if rt.get(k) != body.get(k):
            why.append(k.replace("_sha", ""))
    return Routes(body, rt, not why, ", ".join(f"{w} changed" for w in why))


# ---- The sizes the routes asked (7c), back into the requests ----

SOURCE = ("brownfield routes (pass 3g step 7c, src/brownfield/routed.py `grow`): the nominal sizes (in.) steps 3-6's designs "
          "asked on forge's routes beyond what they were routed at; `brownfield routes --requests` routes at them. Only for the "
          "model and frame whose hashes are `basis`.")


def _basis() -> dict:
    from .routes import _sha
    from .routing import FRAME
    from .systems import latest_model

    return {"geometry_sha": _sha(latest_model()), "framing_sha": _sha(FRAME)}


def grown() -> dict:
    """The sizes step 7c's designs asked of the routes beyond steps 3-6's (`data/route_sizes.json`):
    {fire: {part: nominal}, vent_in: {flat: nominal}, main_in: {kind: nominal}, return_in: {"flat": nominal},
    loop_riser_in: {"loop": nominal}}, for `routes.requests`
    to route at. Only for this model and frame; empty if none or another's."""
    if not GROWN.exists():
        return {}
    g = json.loads(GROWN.read_text(encoding="utf-8"))
    return g if g.get("basis") == _basis() else {}


def grow(asks: dict) -> dict:
    """Merge 7c's asks into the grown sizes (they only grow) and write them if anything grew. Returns
    what grew (empty if nothing)."""
    from .fire import SIZES

    g = grown()
    out = {"source": SOURCE, "basis": _basis(), "fire": dict(g.get("fire", {})), "vent_in": dict(g.get("vent_in", {})),
           "main_in": dict(g.get("main_in", {})), "return_in": dict(g.get("return_in", {})),
           "loop_riser_in": dict(g.get("loop_riser_in", {}))}
    new = {}
    for part, size in asks.get("fire", {}).items():
        if part not in out["fire"] or SIZES.index(size) > SIZES.index(out["fire"][part]):
            out["fire"][part] = new.setdefault("fire", {})[part] = size
    for key in ("vent_in", "main_in", "return_in", "loop_riser_in"):
        for k, v in asks.get(key, {}).items():
            if v > out[key].get(k, 0.0) + 1e-9:
                out[key][k] = new.setdefault(key, {})[k] = v
    if new:
        GROWN.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return new


# ---- Step 7c: steps 3-6 on the routes ----

def vents(apt: dict, p: dict, routes) -> dict:
    """The vents on their routes (IPC 2021):
    - **each flat's branch vents** (906.3: from the farthest vent connection to the vent stack): over
      40 ft, a nominal size larger over the whole of it (906.2); 1-1/2 in. otherwise, half the 3 in.
      branch its water closet asks (906.2, 906.4);
    - **each column's vent stack** (906.1: from its connection at the stack's base to the open
      air): by Table 906.1 on the stack's fixture units."""
    from .loads import water
    from .plumbing import stack_vent_in

    w = water(apt, p)
    g = grown().get("vent_in", {})
    flats = {}
    for f in apt["flats"]:
        t = routes.tree(f"plumbing/vent/{f['name']}")
        longest = max(t.path(x)["m"] for x in t.terminals()) / FT_
        need = 1.5 + (0.5 if longest > p["systems.routing.vent_upsize_ft"] else 0.0)
        flats[f["name"]] = {"longest_ft": longest, "need_in": need, "routed_in": g.get(f["name"], 1.5), "whole": t.ok}
    stacks = {}
    for o in routes.body["obstacles"]:
        if o["id"].endswith("/vent-stack"):
            ft = (o["hi"][2] - o["lo"][2]) / FT_
            stacks[o["id"]] = {"developed_ft": ft, "need_in": stack_vent_in(w["stack_dfu"], ft, w["drains_in"]["stack"])}
    return {"flats": flats, "stacks": stacks, "stack_dfu": w["stack_dfu"],
            "stack_od_in": p["systems.routing.vent_stack_od_in"]}


def obstructions(apt: dict, p: dict, body: dict) -> dict:
    """The sprinklers against the living rooms' strip soffits (continuous obstructions at the
    ceiling, 14 in. deep): each strip no wider than 4 ft (TFP490 Figure 2); the floor on each side
    of its centreline covered by the sprinklers on that side alone, where 7b left them (13R
    6.4.6.3.6.4; within half its listed square of a sprinkler on its side, both ways, sampled every
    `step` m); and the floor under each strip's leg, which runs along a wall, within 13R
    6.4.6.3.3.1's 15 ft2 of shadow a sprinkler."""
    from .fire import layout
    from .routing import soffits, strip_soffits, terminations

    strips = strip_soffits(apt, p)
    lay = layout(apt, p, strips)
    legs = [x for x in soffits(apt, p, terminations(apt, p)) if x["id"].endswith("/soffit-strip-leg")]
    step = 0.05
    widest, gaps, crossed = 0.0, [], []
    for st in strips:
        name = st["flat"]
        a = 0 if st["hi"][0] - st["lo"][0] < st["hi"][1] - st["lo"][1] else 1
        widest = max(widest, st["hi"][a] - st["lo"][a])
        mid = (st["lo"][a] + st["hi"][a]) / 2
        heads = [(h, m["to"]) for h, m in zip(lay[name]["heads"], body["moved_heads"][name]) if h["room"] == st["room"]]
        sides = {}
        for h, xy in heads:
            sides.setdefault(tuple(map(tuple, h["side"])), []).append((h, xy))
            if (xy[a] - mid) * ((h["side"][0][a] + h["side"][1][a]) / 2 - mid) <= 0:
                crossed.append(f"{name} {h['room']}")
        for (lo, hi), hs in sides.items():
            nx, ny = (max(1, int((hi[k] - lo[k]) / step)) for k in range(2))
            for i in range(nx + 1):
                for j in range(ny + 1):
                    q = (lo[0] + (hi[0] - lo[0]) * i / nx, lo[1] + (hi[1] - lo[1]) * j / ny)
                    if not any(abs(q[0] - xy[0]) <= h["l_ft"] * FT_ / 2 + 1e-6 and abs(q[1] - xy[1]) <= h["l_ft"] * FT_ / 2 + 1e-6
                               for h, xy in hs):
                        gaps.append((name, q))
    leg_ft2 = max(((x["hi"][0] - x["lo"][0]) * (x["hi"][1] - x["lo"][1]) / FT_ ** 2 for x in legs), default=0.0)
    return {"strips": len(strips), "widest_ft": widest / FT_, "gaps": gaps, "crossed": crossed, "leg_ft2": leg_ft2, "legs": len(legs),
            "ok": widest <= p["systems.sprinkler.obstruction_max_w_ft"] * FT_ + 1e-9 and not gaps and not crossed
            and leg_ft2 <= p["systems.sprinkler.shadow_ft2"] + 1e-9}


FT_ = 0.3048


def asks(apt: dict, p: dict, routes, fire_h: dict, water: dict, vt: dict, sub_riser_in: float | None = None) -> dict:
    """What the routed designs ask beyond what was routed: a pipe larger than its request's."""
    from .fire import SIZES
    from .routes import p_size

    out: dict = {}
    for part, size in fire_h["sizes"].items():
        if SIZES.index(size) > SIZES.index(p_size(p, part)):
            out.setdefault("fire", {})[part] = size
    for name, v in vt["flats"].items():
        if v["need_in"] > v["routed_in"] + 1e-9:
            out.setdefault("vent_in", {})[name] = v["need_in"]
    jacket = 2 * p["systems.routing.underslab_jacket_in"]
    used = {k: routes.reqs[f"main/{k}"]["od_m"] / 0.0254 - jacket - 0.125 for k in ("cold", "hot", "hot-return")}
    want = {"cold": water["paths"]["cold"]["sizes"]["main"], "hot": water["paths"]["hot"]["sizes"]["main"],
            "hot-return": water["loop"]["return_main_in"]}
    for k, v in want.items():
        if v > used[k] + 1e-6:
            out.setdefault("main_in", {})[k] = v
    # The building loop's risers, if the pump's curve asks them larger than 7a placed them.
    from .routing import default_sizes
    if sub_riser_in is not None and sub_riser_in > default_sizes(apt, p)["loop"] + 1e-9:
        out.setdefault("loop_riser_in", {})["loop"] = sub_riser_in
    # Each flat's loop's return (Addendum 7), routed at one size for all.
    rets = [r["size_in"] for rid, r in routes.reqs.items() if rid.startswith("plumbing/hot-return/")]
    if rets and water["loop"]["flat_return_in"] > min(rets) + 1e-9:
        out.setdefault("return_in", {})["flat"] = water["loop"]["flat_return_in"]
    return out


class Incomplete(Exception):
    """A design reads a run forge didn't finish."""


def run_checks(routes: Routes) -> tuple[dict[str, list[str]], list]:
    """The runs themselves: each routed, answering the requests as they stand, and read back whole.
    Also the failed runs, by id, with the outlets each failed at."""
    failed = {k: [f["ref"] for f in r.get("failed", [])] for k, r in routes.recs.items() if not r.get("ok")}
    return failed, [
        ("every run routed, answering the requests as they stand (forge routed exactly these)", routes.fresh and not failed,
         routes.status + "".join(f"; {k} failed: " + ", ".join(v) for k, v in failed.items())),
        ("every tree read back whole: each branch joins its trunk, a riser or its root",
         all(not routes.tree(k).far for k in routes.recs), f"{len(routes.recs)} runs"),
    ]


def summary(apt: dict, p: dict, routes: Routes) -> dict:
    """Step 7c: steps 3-6 on the routes, each beside its square figures, with their checks. Where a
    run failed, or the routes answer older requests, and a design can't read what it needs, that
    is said as a failing check beside the runs' own (the designs that could run are not run apart:
    one report, whole). With every run routed and fresh, an error is a bug, and raised."""
    failed, runs = run_checks(routes)
    try:
        return _designs(apt, p, routes, runs)
    except (Incomplete, KeyError, StopIteration, ValueError, IndexError) as e:
        if not failed and routes.fresh:
            raise
        why = f"a design reads a run forge didn't finish or routed for older requests ({type(e).__name__}: {e})"
        return {"checks": runs + [("steps 3-6 run on the routes", False, why)], "asks": {}, "incomplete": why,
                "stale": [] if routes.fresh else [routes.why]}


def _designs(apt: dict, p: dict, routes: Routes, runs: list) -> dict:
    from . import electrical, fire, hvac, plumbing
    from .routecheck import penetrations

    sq_fire = fire.hydraulics(apt, p)
    fh = fire.routed_hydraulics(apt, p, routes)
    ducts = hvac.routed_ducts(apt, p, routes)
    cool = hvac.routed_cooling(apt, p, routes)
    sq_sub, sub = hvac.substation(apt, p), hvac.substation(apt, p, routes=routes)
    sq_water, water = plumbing.design(apt, p), plumbing.design(apt, p, routes)
    sq_el, el = electrical.design(apt, p), electrical.design(apt, p, routes)
    vt = vents(apt, p, routes)
    ob = obstructions(apt, p, routes.body)
    pen = penetrations(apt, p, routes.body, routes.rt)
    want = asks(apt, p, routes, fh, water, vt, sub["riser_in"])
    pl, w, h = "systems.plumbing.", "systems.wiring.", "systems.hot_water."
    c4, rc = water["c404"], water["recirc"]
    erv_ok = all(d[k]["ok"] for d in ducts.values() for k in ("erv_supply", "erv_exhaust"))
    ms_ok = all(d["ms"]["ok"] for d in ducts.values())
    esp = [d["ms"]["esp"] for d in ducts.values()]
    circuits = [c for pn in el["panels"].values() for c in pn["circuits"]]
    over_branch = [f"{n} {c['key']}" for n, pn in el["panels"].items() for c in pn["circuits"] if c["drop"] > p[w + "vd_branch_max"] + 1e-12]
    over_feeder = [n for n, f in el["feeders"].items() if max(f["drop"]["ll"], f["drop"]["an"], f["drop"]["bn"]) > p[w + "vd_feeder_max"] + 1e-12]
    from .params import load_params
    spread = load_params()["systems.hot_water.recirc_w_per_flat"]
    over_fps = [f"{k} {n}" for k in ("cold", "hot") for n in water["paths"][k]["over_fps"]]
    stale = [] if routes.fresh else [routes.why]
    sp, units = "systems.sprinkler.", {d["unit"] for d in ducts.values()}
    lim = {"erv_esp": p["systems.erv.esp_inwc"], "ms_esp": p["systems.minisplit.esp_inwc"],
           "ms_lo": min(p[f"systems.{u}.esp_min_inwc"] for u in units), "ms_hi": max(p[f"systems.{u}.esp_max_inwc"] for u in units),
           "strip_ft": p[sp + "obstruction_max_w_ft"], "shadow_ft2": p[sp + "shadow_ft2"], "vent_ft": p["systems.routing.vent_upsize_ft"],
           "fps": {k: p[pl + f"{k}_fps"] for k in ("cold", "hot", "return")},
           "vd": {k: p[w + f"vd_{k}_max"] for k in ("branch", "feeder", "total")}}
    checks = runs + [
        ("the street, less its margin, covers every sprinkler design on the routed pipe (13R 7.1.1.3.1: each compartment's "
         "worst four; the stair's six)", fh["ok"],
         f"{fh['worst']['flat']} {fh['worst']['comp']}: {fh['worst']['q_gpm']:.0f} gpm at {fh['worst']['need_psi']:.1f} psi "
         f"against {fh['target_psi']:.0f}"),
        (f"the sprinklers on each side of every strip soffit cover that side (13R 6.4.6.3.6.4; TFP490 Figure 2: up to "
         f"{lim['strip_ft']:g} ft wide); the floor under each leg within 13R's {lim['shadow_ft2']:g} ft2 of shadow (6.4.6.3.3.1)", ob["ok"],
         f"{ob['strips']} strips, widest {ob['widest_ft']:.1f} ft, {len(ob['gaps'])} uncovered points, {len(ob['crossed'])} across; "
         f"legs {ob['leg_ft2']:.1f} ft2"),
        (f"every ERV path on its routes within its fan's {lim['erv_esp']:g} in. w.c. (Manual D's friction rate, Field Controls' "
         "fittings), no duct larger than routed", erv_ok,
         f"worst {max(d[k]['worst_inwc'] for d in ducts.values() for k in ('erv_supply', 'erv_exhaust')):.3f} in. w.c."),
        (f"every mini-split path within a static pressure the unit can be set to (Fujitsu: {lim['ms_lo']:.2f}-{lim['ms_hi']:.2f} "
         "in. w.c.), no duct larger than routed (Southwark's Manual D-style fittings)", ms_ok, f"set {min(esp):.2f}-{max(esp):.2f} in. w.c."),
        ("every mini-split covers its flat's design loads on its routed line set (Fujitsu's derating)",
         all(c["covered"] for c in cool.values()),
         f"line sets {min(c['line_ft'] for c in cool.values()):.0f}-{max(c['line_ft'] for c in cool.values()):.0f} ft"),
        ("the building loop's risers (a pair a column) and mains within the velocity limit, no main larger than routed",
         all(r["fps"] <= p["systems.substation.max_velocity_fps"] + 1e-9 for r in sub["risers"].values())
         and max(v[k]["largest_main_in"] for v in sub["routed_loop"]["paths"].values() for k in ("supply", "return")) <= sub["header_in"] + 1e-9,
         f"pump {sub['pump_ft']:.1f} ft (square {sq_sub['pump_ft']:.1f}), worst {sub['pump_path']}"),
        (f"the building loop's pump covers its worst routed path at its highest fixed speed, {p['systems.substation.pump_margin']:.0%} in hand "
         "(Grundfos's ALPHA2 15-55 curve III, read off its leaflet)", sub["pump_ok"],
         f"{sub['pump_ft']:.1f} ft needed at {sub['gpm']:.2f} gpm against {sub['pump_curve_ft']:.1f}; risers {sub['riser_in']:g} in."),
        ("pressure to spare at every flat's shower on the routed pipe, cold and hot (Appendix E; PEX sweeps, Uponor's "
         "fittings), within the street's at the peak", all(v >= 0 for k in ("cold", "hot") for v in water["paths"][k]["by_flat"].values())
         and water["street_ok"],
         f"least: cold {water['paths']['cold']['spare_psi']:.1f} psi ({water['paths']['cold']['flat']}), hot "
         f"{water['paths']['hot']['spare_psi']:.1f} ({water['paths']['hot']['flat']}); street {water['street_need_psi']:.1f} of "
         f"{p[pl + 'street_psi']:.0f}"),
        (f"every water pipe within its velocity ({lim['fps']['cold']:g} ft/s cold, {lim['fps']['hot']:g} hot, {lim['fps']['return']:g} "
         "the return)", not over_fps and water["loop"]["return_fps"] <= p[pl + "return_fps"] + 1e-9, ", ".join(over_fps)),
        ("no hot pipe more than 50 ft from circulating water (each flat's loop, Addendum 7) to a fixture, on the routes (IPC 607.2)",
         water["longest_hot_ft"] <= 50, f"longest {water['longest_hot_ft']:.1f} ft (square, from the risers: {water['square_longest_hot_ft']:.1f})"),
        (f"no more than {c4['limit_oz']:g} fl oz (half a gallon) in any hot fixture's pipe off its flat's loop, on the routes (IECC C404.5.2, "
         f"Table C404.5.2.1's PEX; each fixture's own pipe at its own size, {', '.join(f'{k} {v:g}' for k, v in c4['own_in'].items())} in.)", not c4["over"],
         f"worst {c4['worst']['oz']:.0f} fl oz ({c4['worst']['flat']}, {c4['worst']['fixture']})"),
        (f"the risers' and mains' routed loss within Ecosizer's spread ({spread.low:g}-{spread.high:g} W a flat); the flats' own loops "
         "(C404.5) on top", spread.low - 1e-9 <= water["loop"]["riser_mains_w_per_flat"] <= spread.high + 1e-9,
         f"{water['loop']['riser_mains_w_per_flat']:.0f} W a flat; with the flats' loops {water['loop']['w_per_flat']:.0f}"),
        (f"the recirculation pump holds the loop's flow round its index circuit, within its rated {p[h + 'recirc_rated_gpm']:g} gpm at "
         f"{p[h + 'recirc_rated_ft']:g} ft; each flat's balancing valve within its {p[h + 'tbv_max_dp_psi']:g} psi",
         rc["ok"] and rc["tbv_ok"], f"{rc['gpm']:.2f} gpm at {rc['ft']:.1f} ft ({rc['index']}); valve {rc['tbv_psi']:.2f} psi at {rc['flat_gpm']:.2f} gpm"),
        (f"every branch vent routed, within {lim['vent_ft']:g} ft or a size up over its whole length (IPC 906.2); each vent stack "
         "by Table 906.1",
         all(v["routed_in"] >= v["need_in"] - 1e-9 and v["whole"] for v in vt["flats"].values())
         and all(s_["need_in"] <= 2.0 for s_ in vt["stacks"].values()),
         f"longest {max(v['longest_ft'] for v in vt['flats'].values()):.1f} ft; vent stacks "
         f"{max(s_['developed_ft'] for s_ in vt['stacks'].values()):.0f} ft, {max(s_['need_in'] for s_ in vt['stacks'].values()):g} in. asked, 2 in. placed"),
        (f"every branch circuit within {lim['vd']['branch']:.0%} and every feeder within {lim['vd']['feeder']:.0%} on its route",
         not over_branch and not over_feeder, ", ".join(over_branch + over_feeder)),
        (f"feeder and branch together within {lim['vd']['total']:.0%} at every outlet, on the routes",
         max(el["total_drop"].values()) <= el["vd_total_max"] + 1e-12,
         f"worst {max(el['total_drop'].values()):.2%} (square {max(sq_el['total_drop'].values()):.2%})"),
        ("nothing routed smaller than the routed designs ask", not want, str(want) if want else ""),
    ]
    sq_vent = hvac.ventilation_ducts(apt, p)
    sq_cool = hvac.cooling_ducts(apt, p)
    tel = lambda xs: f"{min(xs):.0f}-{max(xs):.0f}"  # noqa: E731
    return {"checks": checks, "fire": fh, "square_fire": sq_fire, "ducts": ducts, "cooling": cool, "loop": sub, "square_loop": sq_sub,
            "square_erv_tel": tel([v[k]["tel_ft"] for v in sq_vent.values() for k in ("supply", "exhaust")]),
            "square_ms_tel": tel([c["ducts"]["tel_ft"] for c in sq_cool.values()]),
            "water": water, "square_water": sq_water, "electrical": el, "square_electrical": sq_el, "vents": vt, "obstructions": ob,
            "penetrations": pen, "asks": want, "circuits": len(circuits), "stale": stale, "limits": lim}


def report(s: dict) -> str:
    """Step 7c in plain text: the checks, then each system square against routed."""
    from .systems import report as checks

    if "incomplete" in s:
        return "\n".join(["Pass 3g step 7c: steps 3-6 on the routes", "", checks(s["checks"])])
    lim = s["limits"]
    fs, fh = s["square_fire"], s["fire"]
    sw, w = s["square_water"], s["water"]
    sl, lp = s["square_loop"], s["loop"]
    se, el = s["square_electrical"], s["electrical"]
    d, cool, vt, ob, pen = s["ducts"], s["cooling"], s["vents"], s["obstructions"], s["penetrations"]
    rng = lambda xs, f="{:.0f}": f"{f.format(min(xs))}-{f.format(max(xs))}"  # noqa: E731
    lines = ["Pass 3g step 7c: steps 3-6 on the routes", "", checks(s["checks"]), "",
             "Square (step 3-6's lengths) against routed (7b's), by system:"]
    ws, wr = fs["worst"], fh["worst"]
    lines.append(f"  Sprinklers: governing {ws['flat']} {ws['comp']} {ws['q_gpm']:.0f} gpm at {ws['need_psi']:.1f} psi -> "
                 f"{wr['flat']} {wr['comp']} {wr['q_gpm']:.0f} gpm at {wr['need_psi']:.1f} psi (street less margin {fh['target_psi']:.0f}); "
                 f"pipe " + ", ".join(f"{k} {v}" for k, v in fh["sizes"].items()) + " in."
                 + (f"; grew from 7b's: " + ", ".join(f"{k} {a} -> {b}" for k, (a, b) in fh["grew"].items()) if fh["grew"] else ""))
    lines.append(f"  The ERVs: effective length {rng([x[k]['tel_ft'] for x in d.values() for k in ('erv_supply', 'erv_exhaust')])} ft "
                 f"(square {s['square_erv_tel']}), worst path {max(x[k]['worst_inwc'] for x in d.values() for k in ('erv_supply', 'erv_exhaust')):.3f} "
                 f"of {lim['erv_esp']:g} in. w.c.")
    held = sorted({x["routed_in"]["ms-supply"] for x in d.values()})
    lines.append(f"  The mini-splits: effective length {rng([x['ms']['tel_ft'] for x in d.values()])} ft (square {s['square_ms_tel']}); "
                 f"set static pressure {rng([x['ms']['esp'] for x in d.values()], '{:.2f}')} in. w.c. (step 3: {lim['ms_esp']:.2f}); "
                 f"{sum(x['ms']['capped'] for x in d.values())} pieces held at their routed "
                 + "/".join(f"{v:g}" for v in held) + " in.")
    lines.append(f"  Line sets: {rng([c['square_ft'] for c in cool.values()])} ft -> {rng([c['line_ft'] for c in cool.values()])} ft; "
                 f"least capacity left {min(c['sensible_capacity_w'] - c['sensible_w'] for c in cool.values()):.0f} W sensible")
    lines.append(f"  The building loop: pump {sl['pump_ft']:.1f} -> {lp['pump_ft']:.1f} ft ({lp['pump_path']}); risers "
                 + ", ".join(f"{k} {r_['pipe_in']:g} in." for k, r_ in lp["risers"].items()))
    lines.append(f"  The hot-water loop: {sw['loop']['loss_btuh'] / 3.412142:.0f} -> {w['loop']['loss_btuh'] / 3.412142:.0f} W "
                 f"({w['loop']['w_per_flat']:.0f} a flat, {w['loop']['flats_loss_btuh'] / 3.412142:.0f} W of it in the flats' own loops); "
                 f"returns {w['loop']['return_main_in']:g} in. mains, {w['loop']['return_riser_in']:g} in. risers, "
                 f"{w['loop']['flat_return_in']:g} in. in each flat; {w['loop']['gpm']:.2f} gpm, the pump {w['recirc']['ft']:.1f} ft")
    c4 = w["c404"]
    lines.append(f"  Off each flat's loop (C404.5): worst {c4['worst']['oz']:.0f} of {c4['limit_oz']:g} fl oz ({c4['worst']['flat']}, "
                 f"{c4['worst']['fixture']})")
    for k in ("cold", "hot"):
        a, b = sw["paths"][k], w["paths"][k]
        lines.append(f"  {k.capitalize()} water: developed {a['developed_ft']:.0f} -> {b['developed_ft']:.0f} ft, spare {a['spare_psi']:.1f} -> "
                     f"{b['spare_psi']:.1f} psi ({b['flat']}); every bend an elbow instead: {b['all_elbows']['spare_psi']:.1f} psi with "
                     f"{b['all_elbows']['sizes']['main']:g}/{b['all_elbows']['sizes']['riser']:g}/{b['all_elbows']['sizes']['branch']:g} in.")
    lines.append(f"  The street at the peak: {sw['street_need_psi']:.1f} -> {w['street_need_psi']:.1f} psi; hot pipe to a fixture "
                 f"{sw['longest_hot_ft']:.1f} -> {w['longest_hot_ft']:.1f} ft (607.2: 50)")
    fd0, fd1 = se["feeders"], el["feeders"]
    smaller = sorted(n for n in fd1 if fd1[n]["size"] != fd0[n]["size"])
    lines.append(f"  Feeders: {rng([f['ft'] for f in fd0.values()])} -> {rng([f['ft'] for f in fd1.values()])} ft"
                 + (f"; {len(smaller)} a size smaller" if smaller else "")
                 + f"; worst outlet {max(se['total_drop'].values()):.2%} -> {max(el['total_drop'].values()):.2%} ({lim['vd']['total']:.0%})")
    lines.append(f"  Vents: longest branch vent {max(v['longest_ft'] for v in vt['flats'].values()):.1f} ft"
                 + f"; a size up, over {lim['vent_ft']:g} ft (906.2): " + (", ".join(sorted(n for n, v in vt["flats"].items() if v["routed_in"] >= 2.0)) or "none")
                 + f"; vent stacks {max(x['developed_ft'] for x in vt['stacks'].values()):.0f} ft, Table 906.1 asks "
                 f"{max(x['need_in'] for x in vt['stacks'].values()):g} in. for {vt['stack_dfu']:g} dfu")
    lines.append(f"  Strip soffits: {ob['strips']}, each side's floor covered by its own sprinklers; the legs' floor {ob['leg_ft2']:.1f} ft2 "
                 f"of shadow each ({lim['shadow_ft2']:g} allowed)")
    lines.append(f"  The membrane: {pen['rated']['membrane']} penetrations of the rated ceilings (of {pen['membrane']} through any: the "
                 "top storey's roof/ceiling, unrated in Type V-B, and the stair's halls), the sprinklers' CPVC drops into the soffits among them: "
                 "no exception of IBC 714.5.2 covers CPVC (1 is metal pipe; 5 a sprinkler's own annular space), so each takes a listed "
                 "membrane-penetration firestop system (714.5.1.2, F and T 1 hour): 7d's firestop schedule")
    lines.append("  The mini-splits over finished ceilings (IMC 307.2.3): item 4, a UL 508 water-level switch in each unit's drain "
                 f"pan or primary drain, wired to its forced-stop input (Fujitsu: function 46-02, a dry contact): {len(d)}, for 7d's schedule")
    if s["asks"]:
        lines += ["", "To route again at: " + json.dumps(s["asks"])]
    return "\n".join(lines)
