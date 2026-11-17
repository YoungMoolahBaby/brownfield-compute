"""D18: each town's new homes laid out at its edge on the real ground, and what forge draws.

Jon, 2026-11-17: "draw the 3D homes and clubhouses". Before drawing, the steer: the new homes join the
towns for real, at their edges, on their streets (`conference.town_homes`). This lays each town's homes
out the way D16's rings do, on the land `land.analysis` leaves clear (`masks`):

- **The clubhouse first**, where the town has the member's: a 60 x 60 m lot on a public street, as
  near the town's middle as one fits (its court hall needs ~35 m of nearly level ground).
- **A spine street** leaves an existing local street at right angles, into the clear land nearest the
  town's middle. **Living streets** cross it parallel to the road, lots both sides, a green with big
  trees between back-to-back rows (D16's 15 m streets and 30 m greens).
- **Rings:** the lots fill outward from the spine's mouth, walk-ups first, then townhouses, then houses.
  A lot is kept where at least 95% of it is clear, it lies within a five-minute walk of the mouth, and
  the ground under its building falls no more than about a storey. What doesn't fit goes to a further
  cluster (up to three a town).
- **The ground** (`drawing`): each lot is graded to the plane that best fits it, its building on a
  level pad in that plane; outside the lots the ground blends back to the real one.

Positions are metres east and north of the old plant (`homes.Local`), as in `land`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

C = "village.conference."
R = "village.rings."
S = "village.site."
KINDS = ("flats", "townhouses", "houses")


@dataclass
class Lot:
    kind: str           # "club", "flats", "townhouses" or "houses"
    x: float            # the lot's middle
    y: float
    ox: float           # unit vector from the lot's middle toward its street
    oy: float
    w: float            # along the street
    d: float            # deep
    z: float = 0.0      # its level pad (m above sea level)
    flats: int = 0      # a walk-up's flats
    bw: float = 0.0     # a walk-up's width (fewer flats, a narrower building)

    def corners(self) -> list[tuple[float, float]]:
        tx, ty = -self.oy, self.ox
        hw, hd = self.w / 2, self.d / 2
        return [(self.x + sx * hw * tx + sy * hd * self.ox, self.y + sx * hw * ty + sy * hd * self.oy)
                for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    def polygon(self):
        from shapely.geometry import Polygon

        return Polygon(self.corners())


@dataclass
class Layout:
    town: str
    lots: list[Lot]
    streets: list[list[tuple[float, float]]]   # the living streets' centrelines
    spines: list[list[tuple[float, float]]]    # each spine, from its mouth on the existing road
    mouths: list[tuple[float, float]]
    rest: list = field(default_factory=list)   # what didn't fit (the queue's tail)
    blocked: bool = False                      # a spine would cross a building, a pond or a highway

    def centre(self) -> tuple[float, float]:
        xs = [l.x for l in self.lots if l.kind != "club"]
        ys = [l.y for l in self.lots if l.kind != "club"]
        return (float(np.mean(xs)), float(np.mean(ys))) if xs else self.mouths[0]

    def missing(self) -> int:
        return sum(nf if kind == "flats" else 1 for kind, nf, _ in self.rest)

    def merge(self, other: "Layout") -> None:
        self.lots += other.lots
        self.streets += other.streets
        self.spines += other.spines
        self.mouths += other.mouths
        self.rest = other.rest

    def homes(self) -> dict[str, int]:
        out = {k: 0 for k in KINDS}
        for l in self.lots:
            if l.kind == "flats":
                out["flats"] += l.flats
            elif l.kind in out:
                out[l.kind] += 1
        return out


def building(p: dict, lot: "Lot") -> "Lot":
    """The building on a lot, as a rectangle in the lot's frame: its width, depth and how far it stands
    back from the street (forge draws the same: `village.rs`'s walk-up 6 m back, townhouse 4 m, house
    8 m; the clubhouse ~34 x 35 m behind a 12 m plaza)."""
    from . import rings

    t = "village.townhouse."
    if lot.kind == "club":
        w, d, back = 34.0, 35.0, 12.0
    elif lot.kind == "flats":
        w, d, back = lot.bw or p[R + "walkup_w_m"], p[R + "walkup_d_m"], 6.0
    elif lot.kind == "townhouses":
        w, d, back = p[t + "width_gap"], p[t + "depth_m"], 4.0
    else:
        env = rings.house_env(p)
        w, d, back = env["width_m"] + p[t + "width_gap"], env["depth_m"], 8.0
    off = lot.d / 2 - back - d / 2  # from the lot's middle toward the street
    return Lot(lot.kind, lot.x + off * lot.ox, lot.y + off * lot.oy, lot.ox, lot.oy, w, d)


def lot_size(p: dict, kind: str) -> tuple[float, float]:
    from . import rings

    if kind == "club":
        return p[C + "clubhouse_lot_w_m"], p[C + "clubhouse_lot_d_m"]
    return rings.lot(p, kind)


def walkups(p: dict, flats_by_bed: list[int]) -> list[tuple[int, float]]:
    """A town's flats as walk-ups: how many (each up to D16's 9,450 ft2 of flats), and each one's flats
    and width (a walk-up with fewer flats is narrower, down to 16 m)."""
    from . import rings

    n = sum(flats_by_bed)
    if n == 0:
        return []
    ft2 = sum(k * p[R + f"ft2_{b}"] for b, k in enumerate(flats_by_bed))
    nw = math.ceil(ft2 / p[R + "walkup_flats_ft2"])
    per = rings._apportion(n, [1.0 / nw] * nw)
    w = max(16.0, p[R + "walkup_w_m"] * min(1.0, ft2 / nw / p[R + "walkup_flats_ft2"]))
    return [(k, w) for k in per]


def queue(p: dict, h: dict, club: bool) -> list[tuple[str, int, float]]:
    """The lots to place, in ring order: (kind, flats, walk-up width)."""
    q = [("club", 0, 0.0)] if club else []
    q += [("flats", k, w) for k, w in walkups(p, h["flats_by_bed"])]
    q += [("townhouses", 0, 0.0)] * h["townhouses"] + [("houses", 0, 0.0)] * h["houses"]
    return q


# --- Sampling the land -----------------------------------------------------------------------------

class Ground:
    """The 10 m grid's masks and ground levels, sampled at any local point."""

    def __init__(self, g, ok: np.ndarray, hard: np.ndarray):
        self.g, self.ok, self.hard = g, ok, hard

    def _rc(self, x, y):
        c, r = self.g.pix(x, y)
        return (np.clip(np.floor(r).astype(int), 0, self.g.ny - 1), np.clip(np.floor(c).astype(int), 0, self.g.nx - 1))

    def clear(self, x, y) -> np.ndarray:
        r, c = self._rc(x, y)
        return self.ok[r, c]

    def blocked(self, x, y) -> np.ndarray:
        r, c = self._rc(x, y)
        return self.hard[r, c]

    def z(self, x, y) -> np.ndarray:
        """Ground level, bilinear between cell centres."""
        c, r = self.g.pix(x, y)
        c, r = np.asarray(c) - 0.5, np.asarray(r) - 0.5
        c0 = np.clip(np.floor(c).astype(int), 0, self.g.nx - 2)
        r0 = np.clip(np.floor(r).astype(int), 0, self.g.ny - 2)
        fc, fr = np.clip(c - c0, 0, 1), np.clip(r - r0, 0, 1)
        z = self.g.z
        return ((1 - fr) * ((1 - fc) * z[r0, c0] + fc * z[r0, c0 + 1]) + fr * ((1 - fc) * z[r0 + 1, c0] + fc * z[r0 + 1, c0 + 1]))


def lattice(lot: Lot, step: float = 4.0) -> tuple[np.ndarray, np.ndarray]:
    """Points across a lot, `step` apart."""
    tx, ty = -lot.oy, lot.ox
    a = np.linspace(-lot.w / 2 + 1, lot.w / 2 - 1, max(2, int(lot.w / step) + 1))
    b = np.linspace(-lot.d / 2 + 1, lot.d / 2 - 1, max(2, int(lot.d / step) + 1))
    A, B = np.meshgrid(a, b)
    return lot.x + A * tx + B * lot.ox, lot.y + A * ty + B * lot.oy


def masks(p: dict, a: dict, sites: dict, blds: list, highways: list) -> tuple[np.ndarray, np.ndarray]:
    """Land a new lot may take (clear, under 15%, beyond the setback, off existing buildings, 30 m off
    the divided highways), and land a street may not cross (existing buildings, lakes and ponds, steep
    slopes, the highways)."""
    g = a["grid"]
    ok = a["buildable"] & ~a["flags"]["sloping (15-25%)"]
    d = g.distance(g.draw([s["footprint"] for s in sites.values()]), p[C + "setback_m"] + 10.0)
    ok &= d >= p[C + "setback_m"]
    near = g.draw([b.buffer(p[C + "building_clear_m"]) for b in blds])
    hw = g.draw([h.buffer(30.0) for h in highways])
    hard = g.draw(blds) | a["masks"]["lakes and ponds"] | a["masks"]["steep slopes"] | g.draw([h.buffer(12.0) for h in highways])
    return ok & ~near & ~hw, hard


# --- The layout ------------------------------------------------------------------------------------

def try_layout(p: dict, ground: Ground, q: list, R: tuple, t: tuple, n: tuple, town: str) -> Layout:
    """Lay the queue out from the spine's mouth at R (road tangent t, n into the land)."""
    sw, green = p[S + "street_w_m"], p[S + "green_w_m"]
    walk, fall = p[C + "walk_m"], p[C + "pad_fall_max_m"]
    clear0 = 10.0  # the existing road's half width and verge
    xy = lambda u, v: (R[0] + u * t[0] + v * n[0], R[1] + u * t[1] + v * n[1])
    lots: list[Lot] = []
    streets = []
    q = list(q)
    anchor_uv = (0.0, clear0)

    def fits(lot: Lot) -> bool:
        """Clear enough (95% of the lot; 90% of the clubhouse's, whose edges are lawn), within the walk,
        and level enough under its building (the gardens follow the ground)."""
        if math.dist((lot.x, lot.y), xy(*anchor_uv)) > walk + lot.w / 2:
            return False
        X, Y = lattice(lot)
        if ground.clear(X, Y).mean() < (0.9 if lot.kind == "club" else 0.95):
            return False
        z = ground.z(*lattice(building(p, lot), 2.0))
        if np.isnan(z).any() or z.max() - z.min() > fall:
            return False
        lot.z = float(np.median(z))
        return True

    # The clubhouse at the spine's mouth (or up to 30 m in), on whichever side of the spine it fits,
    # facing the road.
    club_side = 0
    if q and q[0][0] == "club":
        w, d = lot_size(p, "club")
        for push in (0.0, 15.0, 30.0):
            for side in (1, -1):
                c = xy(side * (sw / 2 + w / 2), clear0 + push + d / 2)
                lot = Lot("club", c[0], c[1], -n[0], -n[1], w, d)
                if fits(lot):
                    lots.append(lot)
                    anchor_uv = (side * (sw / 2 + w / 2), clear0 + push + d / 2)
                    club_side = side
                    break
            if club_side:
                break
        if not club_side:
            return Layout(town, [], [], [], [R], rest=q)
        q.pop(0)
        v = clear0 + push + d + sw / 2
    else:
        v = clear0 + lot_size(p, q[0][0])[1] + sw / 2 if q else clear0
    k = 0
    while q and v < walk + 60.0:
        depth = lot_size(p, q[0][0])[1]
        # Four arms from the spine: (side of the street: -1 near, +1 far) x (direction along it).
        arms = {(s, dirn): sw / 2 for s in (-1, 1) for dirn in (-1, 1)}
        if k == 0 and club_side:
            arms[(-1, club_side)] = sw / 2 + lot_size(p, "club")[0]
        gap = {a_: 0.0 for a_ in arms}   # metres skipped since the arm's last lot
        has = {a_: False for a_ in arms}
        dead = set()
        placed_u = []
        while q and len(dead) < 4:
            kind, nf, bw = q[0]
            w, d = lot_size(p, kind)
            if d > depth + 0.01:
                break  # a deeper lot starts a street of its own
            live = [a_ for a_ in arms if a_ not in dead]
            # The arm whose next lot stands nearest the mouth goes first: rings, not strips.
            def next_c(a_):
                s, dirn = a_
                return xy(dirn * (arms[a_] + w / 2), v + s * (sw / 2 + d / 2))
            arm = min(live, key=lambda a_: math.dist(next_c(a_), xy(*anchor_uv)))
            s, dirn = arm
            u = dirn * (arms[arm] + w / 2)
            cx, cy = xy(u, v + s * (sw / 2 + d / 2))
            if math.dist((cx, cy), xy(*anchor_uv)) > walk:
                dead.add(arm)
                continue
            if ground.blocked(*xy(dirn * arms[arm], v)).any():
                dead.add(arm)  # the street can't run on through a building or a pond
                continue
            lot = Lot(kind, cx, cy, -s * n[0], -s * n[1], w, d, flats=nf, bw=bw)
            if fits(lot):
                lots.append(lot)
                placed_u.append(u)
                arms[arm] += w
                gap[arm], has[arm] = 0.0, True
                q.pop(0)
            else:
                arms[arm] += 4.0
                gap[arm] += 4.0
                # A row stays a row: past a 12 m gap (40 m before its first lot) the arm ends.
                if gap[arm] > (12.0 if has[arm] else 40.0):
                    dead.add(arm)
        if placed_u:
            u0, u1 = min(placed_u) - 12.0, max(placed_u) + 12.0
            streets.append([xy(min(u0, -sw / 2), v), xy(max(u1, sw / 2), v)])
            k += 1
            nxt = lot_size(p, q[0][0])[1] if q else depth
            v += sw / 2 + depth + green + nxt + sw / 2
        else:
            v += 20.0  # nothing fitted along this line: try further in
    v_end = max([0.0] + [(l.x - R[0]) * n[0] + (l.y - R[1]) * n[1] for l in lots]) if lots else 0.0
    spine = [xy(0.0, 0.0), xy(0.0, v_end)]
    # The spine must not cross a building, a pond or a highway.
    S_ = np.linspace(clear0, v_end, max(2, int(v_end / 4)))
    blocked = bool(ground.blocked(np.array([xy(0, s_)[0] for s_ in S_]), np.array([xy(0, s_)[1] for s_ in S_])).any())
    return Layout(town, lots, streets, [spine], [R], rest=q, blocked=blocked)


def _highway(f: dict) -> bool:
    """US 119 and US 22 (divided highways) and their ramps: no street joins them except at a junction."""
    pr = f.get("properties") or {}
    name = (pr.get("STREET_NAM") or "").upper()
    return (pr.get("TRAF_RT_NO") or "").strip() == "US" or "JUGHANDLE" in name or "RAMP" in name


def _lines(feats: list, loc) -> list:
    from .land import local_geoms

    out = []
    for g in local_geoms(feats, loc):
        out += [part for part in getattr(g, "geoms", [g]) if part.geom_type == "LineString" and part.length > 20]
    return out


def _roads(layers: dict, highways: bool = False):
    """The public streets a new spine may join (not the divided highways), or with `highways` those."""
    from .homes import Local
    from .land import PLANT

    loc = Local(*PLANT)
    if highways:
        return _lines([f for f in layers["state_roads"] if _highway(f)], loc)
    return _lines([f for f in layers["state_roads"] if not _highway(f)] + layers["local_roads"], loc)


def _seeds(ground: Ground, target: tuple, roads: list, tries: int) -> list:
    """Clear cells with some room round them (a 90 m square at least 60% clear, not the scraps between
    houses), within 60 m of a public street, nearest `target` and 150 m apart; with that street."""
    from shapely.geometry import Point

    from .conference import window_share

    g = ground.g
    rows, cols = np.mgrid[0:g.ny, 0:g.nx]
    X, Y = g.xy(cols, rows)
    d = np.hypot(X - target[0], Y - target[1])
    cand = ground.ok & (d < 3000.0) & (window_share(ground.ok, 4) >= 0.6)
    xs, ys, ds = X[cand], Y[cand], d[cand]
    seeds, used = [], []
    for i in np.argsort(ds):
        pt = (float(xs[i]), float(ys[i]))
        if any(math.dist(pt, s) < 150.0 for s in used):
            continue
        near = min(roads, key=lambda r: r.distance(Point(pt)))
        if near.distance(Point(pt)) > 60.0:
            continue
        used.append(pt)
        seeds.append((pt, near))
        if len(seeds) >= tries:
            break
    return seeds


def search(p: dict, ground: Ground, target: tuple, q: list, roads: list, town: str, tries: int = 16,
           per_missing_m: float = 100.0) -> Layout | None:
    """The best layout from spine mouths along the streets nearest `target`: least distance from the
    neighbourhood's middle to the target, plus `per_missing_m` for each home that didn't fit (those go
    to a further cluster)."""
    from shapely.geometry import Point

    best, best_key = None, None
    for pt, road in _seeds(ground, target, roads, tries):
        s0 = road.project(Point(pt))
        for off in (0.0, -40.0, 40.0, -80.0, 80.0, -120.0, 120.0):
            s = s0 + off
            if not 15.0 <= s <= road.length - 15.0:
                continue
            Rp = road.interpolate(s)
            a_, b_ = road.interpolate(s - 10.0), road.interpolate(s + 10.0)
            tx, ty = b_.x - a_.x, b_.y - a_.y
            L = math.hypot(tx, ty)
            tt = (tx / L, ty / L)
            n = (-tt[1], tt[0])
            if (pt[0] - Rp.x) * n[0] + (pt[1] - Rp.y) * n[1] < 0:
                n = (-n[0], -n[1])
            lay = try_layout(p, ground, q, (Rp.x, Rp.y), tt, n, town)
            if lay.blocked or not lay.lots:
                continue
            key = math.dist(lay.centre(), target) + per_missing_m * lay.missing()
            if best_key is None or key < best_key:
                best, best_key = lay, key
    return best


def _take(ground: Ground, lay: Layout) -> None:
    """A layout's lots and streets are no longer free for the next one."""
    from shapely.geometry import LineString

    g = ground.g
    geoms = [l.polygon().buffer(5.0) for l in lay.lots]
    geoms += [LineString(s).buffer(10.0) for s in lay.streets + lay.spines if len(s) > 1 and LineString(s).length > 0]
    ground.ok = ground.ok & ~g.draw(geoms)


def lay_out(p: dict, ground: Ground, town_xy: tuple, homes: dict, club: bool, roads: list, town: str) -> Layout | None:
    """A town's clubhouse first, if it has the member's, on a public street as near the town's middle as
    it fits (a court hall needs some 35 m of nearly level ground). Then its new homes in up to three
    clusters, each as near the town's middle as the land left allows, the rings running outward from
    each spine's mouth."""
    out = None
    if club:
        c = search(p, ground, town_xy, [("club", 0, 0.0)], roads, town, tries=24, per_missing_m=1e6)
        if c is not None and not c.rest:
            _take(ground, c)
            out = c
    q = queue(p, homes, False)
    for _ in range(3):
        if not q:
            break
        lay = search(p, ground, town_xy, q, roads, town)
        if lay is None:
            break
        _take(ground, lay)
        if out is None:
            out = lay
        else:
            out.merge(lay)
        q = lay.rest
    if out is None:
        return None
    out.rest = q + ([("club", 0, 0.0)] if club and not any(l.kind == "club" for l in out.lots) else [])
    return out


def lay_out_all(p: dict, a: dict, sites: dict, layers: dict, blds: list, town: dict, th: dict, clubs: set) -> dict[str, Layout]:
    """Every town's layout, the most homes first; each takes its land from what the next may use."""
    ok, hard = masks(p, a, sites, blds, _roads(layers, highways=True))
    ground = Ground(a["grid"], ok, hard)
    roads = _roads(layers)
    out = {}
    for name in sorted(th, key=lambda k: -th[k]["homes"]):
        lay = lay_out(p, ground, town[name]["xy"], th[name], name in clubs, roads, name)
        if lay is not None:
            out[name] = lay
    return out


# --- What forge draws (D18) -----------------------------------------------------------------------

# The drawings: one region per member's homes (Graceton's and Coral's together), each an inner square
# at 2 m (the new homes, the town beside them, every tree) inside a 6 km square at the DEM's 10 m (the
# hills round it, the woods as a canopy).
REGIONS = {"homer_city": ("Homer City",), "lucerne_mines": ("Lucerne Mines",), "black_lick": ("Black Lick",),
           "graceton_coral": ("Graceton", "Coral")}
FOREST = (41, 42, 43, 90)


def aws_halls(p: dict) -> list:
    """AWS's buildings as drawn on the master plan: each orange block, in metres (approximate)."""
    from shapely.geometry import MultiPoint

    from . import land

    fit = land.Fit(*land.FIT)
    out = []
    for comp in land.components(land.colour_masks(land.master_plan())["buildings"], min_px=12):
        x, y = fit.xy(comp[:, 1].astype(float), comp[:, 0].astype(float))
        out.append(MultiPoint(list(zip(x, y))).minimum_rotated_rectangle)
    return out


class Cover:
    """NLCD classes sampled at local points."""

    def __init__(self, p: dict):
        from . import land
        from .homes import Local

        self.lc, (self.w, self.s, self.e, self.n) = land.landcover(p)
        self.loc = Local(*land.PLANT)

    def at(self, x, y) -> np.ndarray:
        lon = self.loc.lon0 + np.asarray(x, float) / self.loc.kx
        lat = self.loc.lat0 + np.asarray(y, float) / 111_320.0
        ny, nx = self.lc.shape
        c = np.clip(((lon - self.w) / (self.e - self.w) * nx).astype(int), 0, nx - 1)
        r = np.clip(((self.n - lat) / (self.n - self.s) * ny).astype(int), 0, ny - 1)
        return self.lc[r, c]


def _square(pts: list, pad: float, least: float) -> tuple[float, float, float]:
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    half = max(least / 2, (max(xs) - min(xs)) / 2 + pad, (max(ys) - min(ys)) / 2 + pad)
    return cx, cy, half


def plane(lot: Lot, ground: Ground) -> tuple[float, float, float]:
    """The plane that best fits the real ground across a lot: its level at the lot's middle and its
    slopes along the street and toward it (m a m)."""
    X, Y = lattice(lot, 3.0)
    z = ground.z(X, Y)
    tx, ty = -lot.oy, lot.ox
    a = (X - lot.x) * tx + (Y - lot.y) * ty
    b = (X - lot.x) * lot.ox + (Y - lot.y) * lot.oy
    A = np.c_[np.ones(a.size), a.ravel(), b.ravel()]
    zc, su, so = np.linalg.lstsq(A, z.ravel(), rcond=None)[0]
    return float(zc), float(su), float(so)


def _grade(lots: list, planes: list, X: np.ndarray, Y: np.ndarray, Z: np.ndarray, blend: float = 6.0) -> None:
    """Grade each lot to its plane (gardens follow it, the building stands on a level pad in it),
    blending back to the real ground over `blend` m outside the lot."""
    dx = X[0, 1] - X[0, 0]
    for lot, (zc, su, so) in zip(lots, planes):
        hw, hd = lot.w / 2, lot.d / 2
        r = math.hypot(hw, hd) + blend + 2 * dx
        c0, c1 = np.searchsorted(X[0], [lot.x - r, lot.x + r])
        r0, r1 = np.searchsorted(Y[:, 0], [lot.y - r, lot.y + r])
        if c1 <= c0 or r1 <= r0:
            continue
        xs, ys = X[r0:r1, c0:c1] - lot.x, Y[r0:r1, c0:c1] - lot.y
        tx, ty = -lot.oy, lot.ox
        a, b = xs * tx + ys * ty, xs * lot.ox + ys * lot.oy
        d = np.hypot(np.clip(np.abs(a) - hw, 0, None), np.clip(np.abs(b) - hd, 0, None))
        w = np.clip(1.0 - d / blend, 0.0, 1.0)
        zp = zc + su * np.clip(a, -hw, hw) + so * np.clip(b, -hd, hd)
        Z[r0:r1, c0:c1] = w * zp + (1 - w) * Z[r0:r1, c0:c1]


def _trees(rng, cover: Cover, X0: float, X1: float, Y0: float, Y1: float, avoid) -> list:
    """Trees where NLCD has woods (one in ~6.5 m) and yard trees in the towns' developed land (fewer),
    clear of buildings, roads and the new lots and streets (`avoid`, a prepared geometry)."""
    from shapely import contains_xy

    out = []
    for step, classes, keep in ((6.5, FOREST, 1.0), (22.0, (21, 22), 0.45)):
        gx = np.arange(X0 + step / 2, X1, step)
        gy = np.arange(Y0 + step / 2, Y1, step)
        GX, GY = np.meshgrid(gx, gy)
        GX = GX + rng.uniform(-0.4, 0.4, GX.shape) * step
        GY = GY + rng.uniform(-0.4, 0.4, GY.shape) * step
        cls = cover.at(GX, GY)
        m = np.isin(cls, classes) & (rng.uniform(0, 1, GX.shape) < keep)
        xs, ys, cs = GX[m], GY[m], cls[m]
        bad = contains_xy(avoid, xs, ys)
        for x, y, c in zip(xs[~bad], ys[~bad], cs[~bad]):
            conifer = c == 42 or (c == 43 and rng.uniform() < 0.4)
            h = rng.uniform(16.0, 26.0) if c in FOREST else rng.uniform(9.0, 16.0)
            out.append([round(float(x), 1), round(float(y), 1), round(float(h), 1), int(conifer)])
    return out


def _cameras(lays: list, town: dict, names: tuple, ground_z, z0: float) -> list[dict]:
    """Views: an aerial from beyond the new homes looking back over them to the town; for a town with
    the clubhouse, one from the road in front of it and one from above with its roof off."""
    lots = [l for lay in lays for l in lay.lots if l.kind != "club"]
    cx, cy = float(np.mean([l.x for l in lots])), float(np.mean([l.y for l in lots]))
    tx, ty = np.mean([town[n]["xy"][0] for n in names]), np.mean([town[n]["xy"][1] for n in names])
    ux, uy = cx - tx, cy - ty
    L = math.hypot(ux, uy) or 1.0
    ux, uy = ux / L, uy / L
    a = math.radians(30.0)
    vx, vy = ux * math.cos(a) - uy * math.sin(a), ux * math.sin(a) + uy * math.cos(a)
    span = max(math.dist((cx, cy), (l.x, l.y)) for l in lots) + 80.0
    dist = max(330.0, 1.25 * span)
    gz = float(ground_z(cx, cy)) - z0
    tgt = (cx - 0.25 * ux * span, cy - 0.25 * uy * span)
    out = [{"name": "aerial", "eye": [cx + vx * dist, cy + vy * dist, gz + 0.62 * dist],
            "target": [tgt[0], tgt[1], float(ground_z(*tgt)) - z0], "fov": 50.0}]
    for lay in lays:
        for c in (l for l in lay.lots if l.kind == "club"):
            # In the clubhouse's frame: a along the street (t), b toward it (o); the road's verge is at
            # b ~ 31-33 (the lot's front edge at 30, the road 10 m beyond it).
            at = lambda a_, b_: (c.x + a_ * -c.oy + b_ * c.ox, c.y + a_ * c.ox + b_ * c.oy)
            if "Homer City" in names:  # the same building in each town: drawn close once
                eye, tgt = at(-2.0, 33.0), at(-14.0, 12.0)
                out.append({"name": "clubhouse", "eye": [eye[0], eye[1], float(ground_z(*eye)) - z0 + 1.7],
                            "target": [tgt[0], tgt[1], c.z - z0 + 4.0], "fov": 70.0})
                up, mid = at(-24.0, 46.0), at(-11.0, -2.0)
                out.append({"name": "clubhouse_inside", "eye": [up[0], up[1], c.z - z0 + 52.0],
                            "target": [mid[0], mid[1], c.z - z0], "fov": 55.0})
            if math.dist((c.x, c.y), (cx, cy)) > 500.0:
                eye = at(-120.0, 150.0)
                out.append({"name": "clubhouse_aerial", "eye": [eye[0], eye[1], c.z - z0 + 95.0],
                            "target": [c.x, c.y, c.z - z0], "fov": 50.0})
    return out


def drawing(p: dict, a: dict, layers: dict, blds: list, heights: list, town: dict, lays: dict, out_dir) -> dict:
    """Write each region's drawing data for forge `conference`: `<region>.json` (the layout, roads,
    buildings, trees, AWS's halls, cameras) and the ground (`_inner.f32`/`.u8` at 2 m, `_outer` at
    10 m: heights above the region's lowest inner point, and NLCD classes; rows run north to south)."""
    import json

    import shapely
    from shapely.geometry import LineString, box as sbox
    from shapely.ops import unary_union

    from . import land
    from .homes import Local

    out_dir.mkdir(parents=True, exist_ok=True)
    g = a["grid"]
    ground = Ground(g, a["buildable"], a["buildable"])
    cover = Cover(p)
    loc = Local(*land.PLANT)
    roads = [(geom, 6.5) for geom in _lines(layers["local_roads"], loc)]
    roads += [(geom, 22.0 if _highway(f) else 9.0) for f in layers["state_roads"] for geom in _lines([f], loc)]
    halls = aws_halls(p)
    rng = np.random.default_rng(18)
    summary = {}
    for region, names in REGIONS.items():
        rl = [lays[n] for n in names if n in lays]
        if not rl:
            continue
        pts = [(l.x, l.y) for lay in rl for l in lay.lots] + [town[n]["xy"] for n in names]
        cx, cy, half = _square(pts, 320.0, 1100.0)
        X0, X1, Y0, Y1 = cx - half, cx + half, cy - half, cy + half
        step = 2.0
        xs = np.arange(X0, X1 + step / 2, step)
        ys = np.arange(Y1, Y0 - step / 2, -step)  # north to south
        X, Y = np.meshgrid(xs, ys)
        Zn = ground.z(X, Y)
        z0 = float(np.nanmin(Zn))
        lots = [l for lay in rl for l in lay.lots]
        planes = [plane(l, ground) for l in lots]
        Xs, Ys = np.meshgrid(xs, ys[::-1])  # south to north for the sorted search
        Zs = Zn[::-1].copy()
        _grade(lots, planes, Xs, Ys, Zs)
        Z = Zs[::-1]
        # Each building's pad: the plane's level under its middle (a walk-out storey takes up the fall).
        pads = []
        for l, (zc, su, so) in zip(lots, planes):
            bl = building(p, l)
            pads.append(zc + so * ((bl.x - l.x) * l.ox + (bl.y - l.y) * l.oy))
        cls = cover.at(X, Y)
        new = unary_union([l.polygon() for l in lots] + [LineString(s).buffer(7.5) for lay in rl for s in lay.streets + lay.spines
                                                          if LineString(s).length > 0])
        from shapely import contains_xy

        cls = np.where(contains_xy(new, X, Y), 200, cls).astype(np.uint8)  # 200: the new neighbourhood's lawns
        (out_dir / f"{region}_inner.f32").write_bytes((Z - z0).astype("<f4").tobytes())
        (out_dir / f"{region}_inner.u8").write_bytes(cls.tobytes())
        # The surroundings at 10 m.
        O = 3000.0
        oxs = np.arange(cx - O, cx + O + 5.0, 10.0)
        oys = np.arange(cy + O, cy - O - 5.0, -10.0)
        OX, OY = np.meshgrid(oxs, oys)
        OZ = ground.z(OX, OY)
        OZ = np.where(np.isnan(OZ), np.nanmin(OZ), OZ)
        (out_dir / f"{region}_outer.f32").write_bytes((OZ - z0).astype("<f4").tobytes())
        (out_dir / f"{region}_outer.u8").write_bytes(cover.at(OX, OY).astype(np.uint8).tobytes())
        inner = sbox(X0, Y0, X1, Y1)
        outer = sbox(cx - O, cy - O, cx + O, cy + O)
        near_i = [i for i, b in enumerate(blds) if b.intersects(inner.buffer(900.0))]
        near_b = [blds[i] for i in near_i]
        avoid = unary_union([new.buffer(2.0)] + [b.buffer(4.0) for b in near_b if b.intersects(inner)]
                                + [r.buffer(w / 2 + 4.0) for r, w in roads if r.intersects(inner)])
        shapely.prepare(avoid)
        trees = _trees(rng, cover, X0, X1, Y0, Y1, avoid)
        bjs = []
        for i in near_i:
            ext = list(blds[i].exterior.coords)[:-1]
            # Microsoft's height where it gives one (its median here is 3.7 m: it reads as the eaves), a
            # house's eaves (5 m) otherwise.
            h = heights[i] if heights[i] else 5.0
            bjs.append({"pts": [[round(x, 2), round(y, 2)] for x, y in ext], "h": round(float(min(max(h, 3.0), 14.0)), 1),
                        "z": round(float(np.nanmin(ground.z(np.array([q[0] for q in ext]), np.array([q[1] for q in ext])))) - z0, 2)})
        data = {
            "source": "brownfield conference (D18): each town's new homes on the real ground, for forge `conference`",
            "region": region, "towns": list(names), "z0": z0, "inner": {"x0": X0, "y1": Y1, "step": step, "nx": len(xs), "ny": len(ys)},
            "outer": {"x0": float(oxs[0]), "y1": float(oys[0]), "step": 10.0, "nx": len(oxs), "ny": len(oys)},
            "lots": [{"kind": l.kind, "x": l.x, "y": l.y, "ox": l.ox, "oy": l.oy, "w": l.w, "d": l.d, "pad": pz - z0,
                      "zc": pl[0] - z0, "su": pl[1], "so": pl[2], "flats": l.flats, "bw": l.bw}
                     for l, pl, pz in zip(lots, planes, pads)],
            "streets": [[list(q) for q in s] for lay in rl for s in lay.streets],
            "spines": [[list(q) for q in s] for lay in rl for s in lay.spines],
            "roads": [{"pts": [[round(x, 1), round(y, 1)] for x, y in r.coords], "w": w} for r, w in roads if r.intersects(outer)],
            "buildings": bjs,
            "trees": trees,
            "halls": [{"pts": [[round(x, 1), round(y, 1)] for x, y in list(h.exterior.coords)[:-1]],
                       "z": float(ground.z(h.centroid.x, h.centroid.y)) - z0, "h": 21.3} for h in halls if h.intersects(outer)],
            "cameras": _cameras(rl, town, names, ground.z, z0),
            "types": _types(p),
        }
        (out_dir / f"{region}.json").write_text(json.dumps(data), encoding="utf-8")
        summary[region] = {"lots": len(lots), "trees": len(trees), "buildings": len(bjs), "halls": len(data["halls"]),
                           "inner_m": 2 * half}
    return summary


def _types(p: dict) -> dict:
    """The homes' sizes forge needs (as `village.forge_spec`)."""
    from . import rings

    t = "village.townhouse."
    env = rings.house_env(p)
    return {"townhouse": {"w": p[t + "width_gap"], "d": p[t + "depth_m"], "storeys": int(p[t + "storeys"]), "storey_m": p[t + "storey_m"],
                          "garage_h": p[t + "garage_h_m"]},
            "flats": {"w": p[R + "walkup_w_m"], "d": p[R + "walkup_d_m"], "storeys": int(p[R + "walkup_storeys"]),
                      "storey_m": p[R + "walkup_storey_m"]},
            "house": {"w": env["width_m"], "d": env["depth_m"], "storeys": int(p[R + "house_storeys"]), "storey_m": p[R + "house_storey_m"],
                      "garage_w": p[t + "width_gap"], "garage_d": p[t + "depth_m"], "garage_h": p[t + "garage_h_m"]},
            "club": {"court_hall_m2": p[C + "court_hall_m2"], "clear_m": p[C + "court_clear_m"], "cafe_m2": p[C + "cafe_m2"],
                     "fitness_m2": p[C + "fitness_m2"], "workshop_m2": p[C + "workshop_m2"], "support_m2": p[C + "support_m2"]}}
