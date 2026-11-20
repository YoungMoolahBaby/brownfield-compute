"""Pass 3f step 8 (D27): the walk-up's stair, halls and flat doors, checked against IBC 2018.

forge's `stair` module builds the stair into the walk-up's model (out/pass3/apartment.json,
under `stair`). This checks it against the code limits in params/bidset.yaml:
- `code.stair`: IBC 2018 1011 stairways, 1014 handrails and 1015 guards;
- `code.door`: 1010.1.1 and 1010.1.6, the flat doors' clear size and the landing in front of them;
- `code.window_fall`: 1015.8, low operable windows high above grade;
- `code.exit_stair`: 1023 and Table 716.1(2), reported for the doors, which 8b's IFC carries.

It measures the geometry rather than taking forge's word for it:
- **Risers and rise:** measured from the floor or landing found at each end of a flight, through
  its step boxes. Width is measured from the steps.
- **Headroom:** the lowest box above or through each flight's nosing line, over its full width,
  from one tread before the bottom riser to the top riser.
- **Edges:** every edge of every walking surface in the core is sorted into one of:
  - walled (barrier boxes cover it to guard height, windows cut out of the walls);
  - continuing (a walking surface within a riser of it carries on across the edge);
  - a window (the wall is there but a window is in it);
  - an open drop.

  A drop over 30 in within 36 in needs a guard. A window by a walking surface is reported under
  1015.8 and 2406.4.3.
"""

from __future__ import annotations

import numpy as np

IN = 0.0254
FT2 = 0.09290304
EPS = 1e-4  # m: what counts as touching (the JSON is rounded to the micrometre)
WALKING = {"floor", "landing", "ground_slab", "step"}
BARRIER = {"exterior_wall", "party_wall", "stair_partition", "guard", "floor", "roof"}


def _boxes(apt: dict) -> list[dict]:
    """Every box of the building and its stair, as numpy arrays, once each (the bid set's model,
    `bidset.load`, already has the stair's floors, landings and partitions among its parts)."""
    by_id = {p["id"]: p for p in apt["parts"] + apt["stair"]["parts"]}
    return [{"id": p["id"], "kind": p["kind"], "lo": np.array(p["lo_m"]), "hi": np.array(p["hi_m"])} for p in by_id.values()]


def _openings(apt: dict) -> list[dict]:
    """Every opening, the flat doors among them, once each."""
    by_id = {o["id"]: o for o in apt["openings"] + apt["stair"]["doors"]}
    return [{"id": o["id"], "lo": np.array(o["lo_m"]), "hi": np.array(o["hi_m"]), "o": o} for o in by_id.values()]


def _nose(f: dict):
    """The flight's nosing line, z as a function of x (extended past both ends)."""
    slope = f["riser_m"] / f["tread_m"]
    return lambda x: f["z0_m"] + f["riser_m"] + slope * (x - f["x_bottom_m"]) * f["dir"]


def _covers(b: dict, x: float, y0: float, y1: float) -> bool:
    return b["lo"][0] - EPS <= x <= b["hi"][0] + EPS and b["lo"][1] <= y0 + EPS and b["hi"][1] >= y1 - EPS


def ends(apt: dict, f: dict) -> tuple[dict | None, dict | None]:
    """The walking surfaces at a flight's foot and head: half a tread before the bottom riser, the
    highest surface below the first tread; half a tread past the top riser, the lowest above the
    last. Each must span the flight's full width."""
    boxes = _boxes(apt)
    own = set(f["steps"])
    steps = [b for b in boxes if b["id"] in own]
    first, last = min(s["hi"][2] for s in steps), max(s["hi"][2] for s in steps)
    xf = f["x_bottom_m"] - f["dir"] * f["tread_m"] / 2
    xh = f["x_top_m"] + f["dir"] * f["tread_m"] / 2
    walk = [b for b in boxes if b["kind"] in WALKING and b["id"] not in own]
    foot = [b for b in walk if _covers(b, xf, f["y0_m"], f["y1_m"]) and b["hi"][2] < first - EPS]
    head = [b for b in walk if _covers(b, xh, f["y0_m"], f["y1_m"]) and b["hi"][2] > last + EPS]
    return (max(foot, key=lambda b: b["hi"][2]) if foot else None,
            min(head, key=lambda b: b["hi"][2]) if head else None)


def run_out(apt: dict, x: float, away: float, z: float, y0: float, y1: float, need: float) -> float:
    """How far (m, up to `need`) a level walking surface at height `z` runs from `x` in direction
    `away` (+1 or -1) over the band y0-y1, across touching boxes."""
    boxes = [b for b in _boxes(apt) if b["kind"] in WALKING and abs(b["hi"][2] - z) < EPS]
    at = x
    while abs(at - x) < need - EPS:
        probe = at + away * 2 * EPS
        nxt = [b for b in boxes if _covers(b, probe, y0, y1)]
        if not nxt:
            break
        at = max(b["hi"][0] for b in nxt) if away > 0 else min(b["lo"][0] for b in nxt)
    return min(abs(at - x), need)


def headroom(apt: dict, f: dict) -> tuple[float, float | None]:
    """The least clearance (m) over flight `f`, measured vertically from its nosing line, and the x
    where it occurs. Anything rising through the line (a column on a tread) counts as no
    clearance. Sampled every 10 mm along x, and at every box's edge, from one tread before the
    bottom riser to the top riser, over the flight's width."""
    boxes = _boxes(apt)
    nose = _nose(f)
    own = set(f["steps"])
    x0, x1 = sorted((f["x_bottom_m"] - f["dir"] * f["tread_m"], f["x_top_m"]))
    edges_x = [e for b in boxes for e in (b["lo"][0], b["hi"][0]) if x0 <= e <= x1]
    xs = np.unique(np.concatenate([np.arange(x0, x1 + 0.005, 0.01), edges_x, [x0, x1]]))
    y0, y1 = f["y0_m"] + EPS, f["y1_m"] - EPS
    best: tuple[float, float | None] = (np.inf, None)
    for x in xs:
        z = nose(x)
        for b in boxes:
            if b["id"] in own or b["hi"][2] <= z + EPS:
                continue
            if b["lo"][0] - EPS <= x <= b["hi"][0] + EPS and b["lo"][1] < y1 and b["hi"][1] > y0:
                c = max(b["lo"][2] - z, 0.0)
                if c < best[0]:
                    best = (c, float(x))
    return best


def _covered(intervals: list[tuple[float, float]], a: float, b: float) -> bool:
    """Whether the union of `intervals` covers [a, b]."""
    reach = a
    for lo, hi in sorted(intervals):
        if lo > reach + EPS:
            return False
        reach = max(reach, hi)
        if reach >= b - EPS:
            return True
    return reach >= b - EPS


def _minus(iv: tuple[float, float], cuts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """An interval with the `cuts` taken out."""
    out = [iv]
    for c0, c1 in cuts:
        nxt = []
        for a, b in out:
            if c1 <= a or c0 >= b:
                nxt.append((a, b))
                continue
            if c0 > a:
                nxt.append((a, c0))
            if c1 < b:
                nxt.append((c1, b))
        out = nxt
    return out


def edges(apt: dict, params: dict) -> list[dict]:
    """Every edge of every walking surface in the core (hall floors, landings, steps), sampled every
    25 mm along it: walled, continuing, a window, or an open drop (its depth within reach)."""
    c = "bidset.code.stair."
    guard_h, reach = params[c + "guard_height_min_in"].value * IN, params[c + "guard_reach_in"].value * IN
    boxes = _boxes(apt)
    holes = _openings(apt)
    y0c, y1c = apt["stair"]["core_y_m"]
    rise = max(f["riser_m"] for f in apt["stair"]["flights"])
    walk = [b for b in boxes if b["kind"] in WALKING and b["kind"] != "ground_slab"
            and b["lo"][1] >= y0c - EPS and b["hi"][1] <= y1c + EPS]
    out = []
    for w in walk:
        zw = w["hi"][2]
        for axis in (0, 1):
            other = 1 - axis
            for side, at in ((-1, w["lo"][axis]), (1, w["hi"][axis])):
                for s in np.arange(w["lo"][other] + 0.0125, w["hi"][other], 0.025):
                    pt = np.zeros(2)
                    pt[axis], pt[other] = at, s

                    def touching(b):
                        return b is not w and b["lo"][axis] - EPS <= at <= b["hi"][axis] + EPS and b["lo"][other] - EPS <= s <= b["hi"][other] + EPS

                    near = [b for b in boxes if touching(b)]
                    here = [h for h in holes if touching(h)]
                    walls = [(b["lo"][2], b["hi"][2]) for b in near if b["kind"] in BARRIER]
                    cut = [p for iv in walls for p in _minus(iv, [(h["lo"][2], h["hi"][2]) for h in here])]
                    window = None
                    if _covered(cut, zw, zw + guard_h):
                        kind, drop = "walled", 0.0
                    elif any(b["kind"] in WALKING and abs(b["hi"][2] - zw) <= rise + EPS
                             and (b["hi"][axis] > at + EPS if side > 0 else b["lo"][axis] < at - EPS) for b in near):
                        kind, drop = "continuing", 0.0
                    elif here and _covered(walls, zw, zw + guard_h):
                        kind, drop = "window", 0.0
                        window = next(h["id"] for h in here if h["hi"][2] > zw and h["lo"][2] < zw + guard_h)
                    else:
                        lows = []
                        for d in np.arange(0.01, reach + 1e-9, 0.05):
                            q = pt.copy()
                            q[axis] += side * d
                            tops = [b["hi"][2] for b in boxes if b["kind"] in WALKING and b["lo"][0] - EPS <= q[0] <= b["hi"][0] + EPS
                                    and b["lo"][1] - EPS <= q[1] <= b["hi"][1] + EPS and b["hi"][2] < zw - EPS]
                            lows.append(zw - (max(tops) if tops else 0.0))
                        kind, drop = "open", max(lows)
                    out.append({"part": w["id"], "axis": "xy"[axis], "at": float(at), "s": float(s), "z": float(zw),
                                "kind": kind, "drop": float(drop), "window": window})
    return out


def windows_by_walking(apt: dict, params: dict, es: list[dict] | None = None) -> list[dict]:
    """Each window that a walking surface in the core runs up to, with what 1015.8 and 2406.4.3 make
    of it. Heights above grade are above the ground floor's level, since the model has no grade."""
    es = edges(apt, params) if es is None else es
    wf, sg = "bidset.code.window_fall.", "bidset.code.safety_glazing."
    v = lambda k: params[k].value  # noqa: E731
    by_id = {h["id"]: h["o"] for h in _openings(apt)}
    seen: dict[tuple[str, str], dict] = {}
    for e in es:
        if e["kind"] != "window":
            continue
        o = by_id[e["window"]]
        key = (o["id"], e["part"])
        if key in seen:
            continue
        sill = o["sill_m"] - e["z"]
        top = sill + o["height_m"]
        area = o["width_m"] * o["height_m"]
        seen[key] = {
            "window": o["id"], "surface": e["part"], "sill_above_surface_m": sill, "sill_above_ground_floor_m": o["sill_m"],
            "fall_1015_8": sill < v(wf + "sill_above_floor_max_in") * IN - EPS and o["sill_m"] > v(wf + "above_grade_min_in") * IN + EPS,
            "safety_2406_4_3": (area > v(sg + "window_area_ft2") * FT2 and sill < v(sg + "window_bottom_in") * IN
                                and top > v(sg + "window_top_in") * IN),
        }
    return list(seen.values())


def check(apt: dict, params: dict) -> list[tuple[str, bool, str]]:
    """The stair, its landings, handrails, guards and the flat doors against IBC 2018."""
    c, d = "bidset.code.stair.", "bidset.code.door."
    p = lambda k: params[k].value  # noqa: E731
    v = lambda k: params[k].value * IN  # noqa: E731
    st = apt["stair"]
    flights, rails, doors = st["flights"], st["rails"], st["doors"]
    boxes = {b["id"]: b for b in _boxes(apt)}
    res: list[tuple[str, bool, str]] = []

    def add(label, ok, detail):
        res.append((label, bool(ok), detail))

    inch = lambda m: f"{m / IN:.2f} in"  # noqa: E731
    # Each flight, measured: the surfaces at its ends, its risers, treads, width and rise.
    need = v(c + "landing_depth_max_needed_in")
    risers, treads, spread, widths, rises, missing, depths = [], [], [], [], [], [], []
    for f in flights:
        foot, head = ends(apt, f)
        steps = sorted((boxes[s] for s in f["steps"]), key=lambda b: b["hi"][2])
        widths.append(min(s["hi"][1] - s["lo"][1] for s in steps))
        ts = [s["hi"][0] - s["lo"][0] for s in steps]
        treads += ts
        if foot is None or head is None:
            missing.append(f"{f['id']} {'foot' if foot is None else 'head'}")
            continue
        rs = np.diff([foot["hi"][2]] + [s["hi"][2] for s in steps] + [head["hi"][2]])
        risers += list(rs)
        spread.append(max(rs.max() - rs.min(), max(ts) - min(ts)))
        rises.append(head["hi"][2] - foot["hi"][2])
        n = min(widths[-1], need)
        depths += [(f"{f['id']} foot", run_out(apt, f["x_bottom_m"], -f["dir"], foot["hi"][2], f["y0_m"], f["y1_m"], n), n),
                   (f"{f['id']} head", run_out(apt, f["x_top_m"], f["dir"], head["hi"][2], f["y0_m"], f["y1_m"], n), n)]
    add("a floor or landing across the full width at the foot and head of every flight (1011.6)", not missing,
        f"{2 * len(flights) - len(missing)} of {2 * len(flights)}" + (f"; none at {', '.join(missing)}" if missing else ""))
    if risers:
        add(f"risers {p(c + 'riser_min_in'):g}-{p(c + 'riser_max_in'):g} in, measured floor to floor (1011.5.2)",
            v(c + "riser_min_in") - EPS <= min(risers) and max(risers) <= v(c + "riser_max_in") + EPS,
            f"{len(risers)} risers, {inch(min(risers))} to {inch(max(risers))}")
        add(f"risers and treads within {p(c + 'uniformity_tol_in'):g} in in each flight (1011.5.4)",
            max(spread) <= v(c + "uniformity_tol_in") + EPS, f"the largest spread {inch(max(spread))}")
        add(f"each flight rises at most {p(c + 'flight_rise_max_in'):g} in (1011.8)", max(rises) <= v(c + "flight_rise_max_in") + EPS,
            f"the tallest {inch(max(rises))}")
        short = [x for x in depths if x[1] < x[2] - EPS]
        add(f"the landing or floor at each end as deep as the flight is wide, up to {p(c + 'landing_depth_max_needed_in'):g} in (1011.6)",
            not short, f"{len(depths)} ends, the shallowest {inch(min(x[1] for x in depths))}"
            + (f"; short: {', '.join(x[0] for x in short)}" if short else ""))
    add(f"treads at least {p(c + 'tread_min_in'):g} in (1011.5.2)", min(treads) >= v(c + "tread_min_in") - EPS,
        f"{len(treads)} treads, the shallowest {inch(min(treads))}")
    add(f"each flight at least {p(c + 'width_min_in'):g} in wide, measured on its steps (1011.2)",
        min(widths) >= v(c + "width_min_in") - EPS, f"{len(flights)} flights, the narrowest {inch(min(widths))}")
    hr = [(f["id"], *headroom(apt, f)) for f in flights]
    low = min(hr, key=lambda t: t[1])
    add(f"headroom at least {p(c + 'headroom_min_in'):g} in over every flight (1011.3)", low[1] >= v(c + "headroom_min_in") - EPS,
        f"the least {inch(low[1])}, over {low[0]}" + (f" at x = {low[2]:.3f} m" if low[2] is not None else " (nothing above)"))
    # Handrails: both sides of every flight, 34-38 in above the nosings, extended as 1014.6 asks,
    # within reach of every part of the width, projecting at most 4 1/2 in.
    by_flight: dict[str, list[dict]] = {}
    for r in rails:
        by_flight.setdefault(r["flight"], []).append(r)
    heights, ext_top, ext_bottom, reach, proj = [], [], [], [], []
    for f in flights:
        rs = by_flight.get(f["id"], [])
        nose = _nose(f)
        for r in rs:
            p0, p1, p2 = (np.array(q) for q in r["points_m"])
            heights += [p0[2] - nose(p0[0]), p1[2] - nose(p1[0])]
            ext_top.append(abs(p2[0] - p1[0]) if abs(p2[2] - p1[2]) < EPS else 0.0)
            ext_bottom.append(abs(p0[0] - f["x_bottom_m"]) if abs(p0[2] - nose(p0[0]) - (p1[2] - nose(p1[0]))) < EPS else 0.0)
            proj.append(min(abs(p0[1] - f["y0_m"]), abs(p0[1] - f["y1_m"])) + r["diameter_m"] / 2)
        ys = sorted(np.array(r["points_m"])[0][1] for r in rs)
        reach.append(max([ys[0] - f["y0_m"], f["y1_m"] - ys[-1]] + [(b - a) / 2 for a, b in zip(ys, ys[1:])]) if ys else np.inf)
    add("handrails on both sides of every flight (1011.11)", all(len(by_flight.get(f["id"], [])) >= 2 for f in flights),
        f"{len(rails)} handrails on {len(flights)} flights")
    add(f"handrails {p(c + 'handrail_height_min_in'):g}-{p(c + 'handrail_height_max_in'):g} in above the nosings (1014.2)",
        v(c + "handrail_height_min_in") - EPS <= min(heights) and max(heights) <= v(c + "handrail_height_max_in") + EPS,
        f"{inch(min(heights))} to {inch(max(heights))}")
    add(f"handrails extend {p(c + 'handrail_extension_in'):g} in level past the top riser and a tread past the bottom, sloping (1014.6)",
        min(ext_top) >= v(c + "handrail_extension_in") - EPS and min(ext_bottom) >= min(f["tread_m"] for f in flights) - EPS,
        f"top {inch(min(ext_top))}, bottom {inch(min(ext_bottom))}")
    add(f"every part of the width within {p(c + 'handrail_reach_max_in'):g} in of a handrail (1014.9)",
        max(reach) <= v(c + "handrail_reach_max_in") + EPS, f"the farthest {inch(max(reach))}")
    add(f"handrails project at most {p(c + 'handrail_projection_max_in'):g} in into the width (1014.8)",
        max(proj) <= v(c + "handrail_projection_max_in") + EPS, f"the most {inch(max(proj))}")
    # Guards: every open edge with more than a 30 in drop within 36 in has one (1015.2), at least
    # 42 in high (1015.3); the guard boxes are solid, so no sphere passes (1015.4).
    es = edges(apt, params)
    open_drops = [e for e in es if e["kind"] == "open" and e["drop"] > v(c + "guard_drop_in") + EPS]
    guards = [b for b in boxes.values() if b["kind"] == "guard"]
    count = {k: sum(e["kind"] == k for e in es) for k in ("walled", "continuing", "window", "open")}
    add(f"no open edge with a drop over {p(c + 'guard_drop_in'):g} in without a guard (1015.2)", not open_drops,
        f"{len(es)} edge samples: {count['walled']} walled or guarded, {count['continuing']} continuing into a stair or floor, "
        f"{count['window']} at a window, {count['open']} open"
        + (f" (the first at {open_drops[0]['part']}, {open_drops[0]['axis']} = {open_drops[0]['at']:.3f} m)" if open_drops else ""))
    add(f"guards at least {p(c + 'guard_height_min_in'):g} in high (1015.3)",
        all(g["hi"][2] - g["lo"][2] >= v(c + "guard_height_min_in") - EPS for g in guards),
        f"{len(guards)} guard{'s' if len(guards) != 1 else ''}, {', '.join(inch(g['hi'][2] - g['lo'][2]) for g in guards) or 'none'}")
    # The flat doors: clear size (1010.1.1), and a clear landing in front, 44 in long and the door's
    # width (1010.1.6), with no stair part in it and no handrail across it.
    loss = params["bidset.flat_door_clear_loss_in"].value * IN
    cw = min(x["width_m"] for x in doors) - loss
    ch = min(x["height_m"] for x in doors)
    add(f"flat doors at least {p(d + 'clear_width_min_in'):g} x {p(d + 'clear_height_min_in'):g} in clear (1010.1.1)",
        cw >= v(d + "clear_width_min_in") - EPS and ch >= v(d + "clear_height_min_in") - EPS,
        f"{len(doors)} doors, {inch(cw)} clear wide (the {inch(min(x['width_m'] for x in doors))} unit less "
        f"{params['bidset.flat_door_clear_loss_in'].value:g} in, a placeholder) and {inch(ch)} high")
    length = v(d + "landing_length_min_in")
    blocked = []
    for x in doors:
        lo, hi = np.array(x["lo_m"]), np.array(x["hi_m"])
        into = -np.array(x["outward"]) / np.linalg.norm(x["outward"])  # from the flat into the hall
        face = hi[1] if into[1] > 0 else lo[1]
        y0, y1 = sorted((face, face + into[1] * length))
        for b in boxes.values():
            if b["kind"] in WALKING and b["hi"][2] <= lo[2] + EPS:
                continue
            if b["lo"][0] < hi[0] - EPS and b["hi"][0] > lo[0] + EPS and b["lo"][1] < y1 - EPS and b["hi"][1] > y0 + EPS \
                    and b["lo"][2] < hi[2] - EPS and b["hi"][2] > lo[2] + EPS:
                blocked.append(f"{x['id']} ({b['id']})")
        for r in rails:
            pts = np.array(r["points_m"])
            for a, b in zip(pts, pts[1:]):
                if max(a[0], b[0]) > lo[0] + EPS and min(a[0], b[0]) < hi[0] - EPS and y0 < a[1] < y1 \
                        and max(a[2], b[2]) > lo[2] and min(a[2], b[2]) < hi[2]:
                    blocked.append(f"{x['id']} ({r['id']})")
    floorless = []
    for x in doors:
        lo, hi = np.array(x["lo_m"]), np.array(x["hi_m"])
        into = -np.array(x["outward"]) / np.linalg.norm(x["outward"])
        face = hi[1] if into[1] > 0 else lo[1]
        tops = [b for b in boxes.values() if b["kind"] in WALKING and abs(b["hi"][2] - lo[2]) < EPS
                and b["lo"][0] <= lo[0] + EPS and b["hi"][0] >= hi[0] - EPS
                and b["lo"][1] <= min(face, face + into[1] * length) + EPS and b["hi"][1] >= max(face, face + into[1] * length) - EPS]
        if not tops:
            floorless.append(x["id"])
    add(f"a clear landing {p(d + 'landing_length_min_in'):g} in long and the door's width in front of every flat door (1010.1.6)",
        not blocked and not floorless,
        f"{len(doors)} doors" + (f"; blocked: {', '.join(blocked)}" if blocked else "") + (f"; no floor: {', '.join(floorless)}" if floorless else ""))
    return res


def report(apt: dict, res: list[tuple[str, bool, str]], params: dict) -> str:
    rate = params["bidset.code.exit_stair.door_rating_h"].value
    lines = ["The stair, its halls and the flat doors against IBC 2018 (pass 3f step 8):"]
    lines += [f"  {'ok  ' if ok else 'FAIL'} {label}: {detail}" for label, ok, detail in res]
    for w in windows_by_walking(apt, params):
        notes = []
        if w["fall_1015_8"]:
            notes.append("if it opens, 1015.8 asks for a fall measure (an opening that stops a 4 in sphere, or an ASTM F2090 "
                         "device); the model doesn't say whether it opens")
        if w["safety_2406_4_3"]:
            notes.append("2406.4.3 makes it a hazardous location (safety glazing), measured from this surface")
        lines.append(f"  Window {w['window']} rises from {w['surface']}: sill {w['sill_above_surface_m'] / IN:.1f} in above it, "
                     f"{w['sill_above_ground_floor_m'] / IN:.0f} in above the ground floor"
                     + ("; " + "; ".join(notes) if notes else "") + ".")
    lines.append(f"  The flat doors swing into the flats (forge's design, not measured), so none opens onto the hall. The stair "
                 f"is the one exit, so its enclosure is a {params['bidset.code.exit_stair.enclosure_rating_h'].value:g}-hour fire "
                 f"barrier (1023.2), and each flat door is a {rate:g}-hour fire door assembly, self-closing and latching "
                 f"(Table 716.1(2), 716.2.6). The IFC carries both: FireRating on the flat doors' type (with SelfClosing) "
                 f"and on the stair walls.")
    return "\n".join(lines)
