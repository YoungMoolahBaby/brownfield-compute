"""Pass 3g step 7 (D28): the walk-up's services in the model, routed through its frame.

Steps 3-6 sized every pipe, duct, conductor and sprinkler line, but took each length square (along
the axes, through nothing). Step 7 places what the routes connect and routes them through the
wood frame forge builds, only where the frame's rules allow a hole.

**7a, what the routes connect and the frame they go through** (this part):

- **The frame:** forge `framing-json addendum-5` frames the flats' partitions and plumbing walls,
  the annex and the stair halls' floors, and the roof hatch's opening, onto the shell
  (`out/pass3/framing-members-addendum-5.json`). `hatch_command` prints the command, with the
  hatch where step 6 put it (`fire.roof_access`).
- **The fixtures** on each plumbing wall (`fixtures`): the bath's tub across its end, then the
  water closet and the lavatory along the wall at IPC 2021 405.3.1's clearances (15 in. from a
  fixture's centre to a side wall, 30 in. between fixtures, 21 in. in front); the kitchen's sink
  and dishwasher; the utility closet's washer box.
- **Each water closet in a joist bay.** The floor joists span from the facade to the spine, so they
  bear on the spine just behind the plumbing wall: a hole through them there breaks the maker's
  chart (APA Z725E Table 5: a 2 in. hole at least 7 in. from the support, a 4 in. hole 3 ft). So
  the closet bend runs along the joists, in one bay, to the stack in the same bay of the plumbing
  wall: the water closet's centre is set where its bend clears the bay's flanges, within the
  clearances above. The ground floor's water closets stand under the upper floors' (one stack a
  column).
- **The vertical services** (`vertical_services`): each column's stack, vent stack, risers and line
  sets along its plumbing wall, each in a stud bay that is a joist bay on every floor; the feeders
  up the hall's partition beside the panel (`feeder_chase`).
- **The soffits, the ERVs' wall terminations and the roof's outdoor units** (`soffits`,
  `terminations`, `roof_units`), and **the equipment** in the flats and the mechanical room
  (`flat_equipment`, `annex_equipment`), each with its maker's service space.

Frame and units as the model's (metres; x across the depth from the front facade, y along the
length, z up from the top of the ground slab).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import OUT_DIR
from .systems import by_flat

FT = 0.3048
IN = 0.0254
FRAME = OUT_DIR / "pass3" / "framing-members-addendum-5.json"
INPUTS = OUT_DIR / "pass3" / "addendum-5-inputs.json"
R = "systems.routing."


# ---- The frame forge builds ----

def hatch_command(apt: dict, p: dict) -> str:
    """forge's command for Addendum 5's frame: Addendum 3's building (the patio doors' width and the
    continuous insulation from params), with the roof hatch and the soffits from `INPUTS`."""
    return (f"cargo run --release -- framing-json addendum-5 {p['bidset.addendum_1.patio_door_width_in']:g} "
            f"{p['systems.addendum_3.ci_in']:g}")


def inputs(apt: dict, p: dict) -> dict:
    """What forge needs from here to frame Addendum 5: the roof hatch's plan box where step 6 put it
    (`fire.roof_access`) and the soffits the partitions stop under (`soffits`), m."""
    from .fire import roof_access

    h = roof_access(apt, p)
    sf = soffits(apt, p, terminations(apt, p))
    return {"source": "brownfield routes (pass 3g step 7a): for forge's framing-json addendum-5",
            "hatch_m": [round(v, 6) for v in (*h["lo"], *h["hi"])],
            "soffits": [{"id": x["id"], "lo": [round(v, 6) for v in x["lo"]], "hi": [round(v, 6) for v in x["hi"]]} for x in sf]}


def load_frame(apt: dict, p: dict, path: Path = FRAME) -> dict:
    """forge's Addendum 5 frame (every member as boxes, m), built from this module's `inputs`: the
    inputs are (re)written first, and a frame older than them is refused."""
    want = json.dumps(inputs(apt, p), indent=1) + "\n"
    if not INPUTS.exists() or INPUTS.read_text(encoding="utf-8") != want:
        INPUTS.write_text(want, encoding="utf-8")
    how = f"run `{hatch_command(apt, p)}` in forge/ (it reads {INPUTS.relative_to(OUT_DIR.parent)})"
    if not path.exists():
        raise SystemExit(f"no {path.relative_to(OUT_DIR.parent)}: {how}")
    if path.stat().st_mtime < INPUTS.stat().st_mtime:
        raise SystemExit(f"{path.relative_to(OUT_DIR.parent)} is older than its inputs: {how}")
    return json.loads(path.read_text(encoding="utf-8"))


def _bounds(m: dict) -> tuple[list[float], list[float]]:
    lo = [min(b[0][i] for b in m["boxes"]) for i in range(3)]
    hi = [max(b[1][i] for b in m["boxes"]) for i in range(3)]
    return lo, hi


def joists_under(frame: dict, apt: dict, storey: int, x: float) -> list[tuple[float, float]]:
    """The floor joists under storey `storey` (2 or more) that pass under plan point x (along x):
    each one's (y0, y1), its widest part (the flanges), sorted along y."""
    out = []
    for m in frame["members"]:
        if m["kind"] != "floor joists" or m["storey"] != storey - 1:
            continue
        lo, hi = _bounds(m)
        if hi[0] - lo[0] > hi[1] - lo[1] and lo[0] <= x <= hi[0]:
            out.append((lo[1], hi[1]))
    return sorted(out)


def bays(joists: list[tuple[float, float]], y0: float, y1: float) -> list[tuple[float, float]]:
    """The clear spaces between consecutive joists that overlap y0..y1."""
    return [(a[1], b[0]) for a, b in zip(joists, joists[1:]) if b[0] > y0 and a[1] < y1]


def studs_in(frame: dict, box_lo: list[float], box_hi: list[float], storey: int) -> list[tuple[float, float]]:
    """The studs (any stud kind) standing inside a wall's box on its storey: their extent along the
    wall, sorted."""
    along = 1 if box_hi[1] - box_lo[1] > box_hi[0] - box_lo[0] else 0
    thin = 1 - along
    out = []
    for m in frame["members"]:
        if m["storey"] != storey or m["kind"] not in ("studs", "king studs", "jack studs", "cripples"):
            continue
        lo, hi = _bounds(m)
        if lo[thin] >= box_lo[thin] - 1e-6 and hi[thin] <= box_hi[thin] + 1e-6 and box_lo[along] - 1e-6 <= lo[along] and hi[along] <= box_hi[along] + 1e-6:
            out.append((lo[along], hi[along]))
    return sorted(set(out))


# ---- 7a: the fixtures ----

def column(name: str) -> str:
    """A flat's column of flats (one plumbing wall, one stack): its name without the storey."""
    return name.split("-", 1)[1]


def wall_face(apt: dict, name: str) -> tuple[float, float]:
    """The plumbing wall's room-side face (x) and the way from it into the rooms (-1 or +1)."""
    w = next(x for x in apt["rooms"]["walls"] if x["id"] == f"{name}/plumbing-wall")
    spine = apt["depth_m"] / 2
    return (w["lo_m"][0], -1.0) if w["hi_m"][0] <= spine else (w["hi_m"][0], 1.0)


def _wc_y(bath: dict, tub_at_low: bool, bays_: list[tuple[float, float]], p: dict) -> tuple[float, float, float]:
    """Where the water closet's centre may go along the bath's wet wall (y), given the tub at one
    end: from the tub's edge plus the side clearance to the far wall less the lavatory's spacing and
    its side clearance (405.3.1); and inside a joist bay with its closet bend clear of the flanges.
    Returns (y, the range's low, high): y in the bay where the water closet can sit nearest the
    bay's centre, or None if no bay holds it."""
    side, gap = p[R + "fixture_side_in"] * IN, p[R + "fixture_spacing_in"] * IN
    tub = p["systems.design.tub_width_in"] * IN
    y0, y1 = bath["lo_m"][1], bath["hi_m"][1]
    if tub_at_low:
        lo, hi = y0 + tub + side, y1 - side - gap
    else:
        lo, hi = y0 + side + gap, y1 - tub - side
    half = (p[R + "closet_bend_od_in"] / 2 + p[R + "bend_clear_in"]) * IN
    cands = []
    for b0, b1 in bays_:
        a, b = max(lo, b0 + half), min(hi, b1 - half)
        if a <= b + 1e-9:
            c = min(max((b0 + b1) / 2, a), b)
            cands.append((round(abs(c - (b0 + b1) / 2), 9), c))
    return (min(cands)[1] if cands else None), lo, hi


def fixtures(apt: dict, p: dict, frame: dict) -> dict[str, dict]:
    """Each flat's plumbing fixtures on its plumbing wall, by column: the water closet's centre set
    from the second floor's joists (the upper floors share them; the ground floor's stands under
    theirs). Each fixture: its room, its centre on the wall face (x, y), the heights of its
    supplies and drain, and its drain's size."""
    rooms = by_flat(apt)
    cols: dict[str, float] = {}
    out = {}
    for name in sorted(rooms, key=lambda n: (column(n), n)):
        by = {r["use"]: r for r in rooms[name] if r["use"] in ("bath", "kitchen", "utility")}
        bath, kit, util = by["bath"], by["kitchen"], by["utility"]
        face, into = wall_face(apt, name)
        # The tub at the bath's end against the bedroom (away from the utility closet), as the
        # plan's other flats mirror it.
        tub_at_low = bath["lo_m"][1] < util["lo_m"][1]
        col = column(name)
        if col not in cols:
            js = joists_under(frame, apt, 2, face - into * p[R + "wc_rough_in_in"] * IN)
            y, lo, hi = _wc_y(bath, tub_at_low, bays(js, bath["lo_m"][1], bath["hi_m"][1]), p)
            if y is None:
                raise ValueError(f"{col}: no joist bay holds the water closet between {lo:.3f} and {hi:.3f} m")
            cols[col] = y
        wc_y = cols[col]
        side, gap = p[R + "fixture_side_in"] * IN, p[R + "fixture_spacing_in"] * IN
        tub = p["systems.design.tub_width_in"] * IN
        # The lavatory: as far from the water closet as its own side clearance lets it.
        far = bath["hi_m"][1] - side if tub_at_low else bath["lo_m"][1] + side
        lav_y = far if abs(far - wc_y) >= gap - 1e-9 else None
        tub_y = bath["lo_m"][1] + tub / 2 if tub_at_low else bath["hi_m"][1] - tub / 2
        sink_y = (kit["lo_m"][1] + kit["hi_m"][1]) / 2
        toward_util = -1.0 if util["lo_m"][1] < kit["lo_m"][1] else 1.0
        dw_y = sink_y + toward_util * (p[R + "sink_base_in"] / 2 + p[R + "dw_width_in"] / 2) * IN
        washer_y = (util["lo_m"][1] + util["hi_m"][1]) / 2
        z0 = bath["lo_m"][2] + (p["systems.design.finished_floor_upper_in"] * IN if bath["storey"] > 1 else 0.0)
        fx = {
            "wc": {"room": bath["id"], "y": wc_y, "cold_in": p[R + "wc_supply_in"], "drain_in": None, "drain_size": 3.0,
                   "out_m": p[R + "wc_rough_in_in"] * IN},
            "lav": {"room": bath["id"], "y": lav_y, "cold_in": p[R + "lav_supply_in"], "hot_in": p[R + "lav_supply_in"],
                    "drain_in": p[R + "lav_drain_in"], "drain_size": 1.25},
            "tub": {"room": bath["id"], "y": tub_y, "cold_in": p[R + "tub_valve_in"], "hot_in": p[R + "tub_valve_in"],
                    "drain_in": None, "drain_size": 1.5, "out_m": p[R + "tub_drain_out_in"] * IN},
            "sink": {"room": kit["id"], "y": sink_y, "cold_in": p[R + "sink_supply_in"], "hot_in": p[R + "sink_supply_in"],
                     "drain_in": p[R + "sink_drain_in"], "drain_size": 1.5},
            "dishwasher": {"room": kit["id"], "y": dw_y, "hot_in": p[R + "sink_supply_in"], "drain_in": None, "drain_size": None,
                           "to": "sink"},
            "washer": {"room": util["id"], "y": washer_y, "cold_in": p[R + "washer_box_in"], "hot_in": p[R + "washer_box_in"],
                       "drain_in": p[R + "washer_trap_in"], "drain_size": 2.0},
        }
        for f in fx.values():
            f["x"] = face
            f["into"] = into
            f["floor_z"] = z0
        out[name] = fx
    return out


def _free(intervals: list[tuple[float, float]], taken: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """`intervals` less every `taken` span."""
    out = list(intervals)
    for t0, t1 in taken:
        nxt = []
        for a, b in out:
            if t1 <= a or t0 >= b:
                nxt.append((a, b))
                continue
            if t0 > a:
                nxt.append((a, t0))
            if t1 < b:
                nxt.append((t1, b))
        out = nxt
    return out


def pex_od_in(nominal: float, insulation_in: float = 0.0) -> float:
    """PEX is copper-tube size: OD = nominal + 1/8 in., and its insulation both sides."""
    return nominal + 0.125 + 2 * insulation_in


def vertical_services(apt: dict, p: dict, frame: dict, fx: dict, sizes: dict | None = None) -> dict[str, list[dict]]:
    """Each column's vertical services, placed along its plumbing wall, the same on every storey:
    each in a stud bay (between the wall's studs) that is also a joist bay on every upper floor, so
    it passes the floors between joists, never through one. In order: the drain stack in the water
    closet's joist bay (its closet bend runs along that bay); the vent stack beside it (each
    floor's dry vent must reach one, IPC 2021 905.1); then the hot, hot-return and cold risers, the
    heating loop's supply and return and the line sets of the column's three mini-splits, packed at
    the wall's far end from the stack, past the last fixture. A riser fills the 2x6 cavity floor to
    ceiling, so nothing runs along the wall past it: with the risers at the end, every fixture lies
    between them and the stack and its drain and vent run along the wall to the stacks unhindered,
    and the water branches leave their risers upward into the ceiling and drop to the fixtures (7b).
    The washer box's bay is kept clear. `sizes` (in., nominal) default to steps 3-4's: {cold, hot,
    return, loop}."""
    h = "systems.hot_water."
    sizes = sizes or default_sizes(apt, p)
    ins = lambda n: p[h + ("insulation_in_large" if n >= 1.5 else "insulation_in_small")]  # noqa: E731
    gap = p[R + "riser_gap_in"] * IN
    order = [("stack", "drain", p[R + "closet_bend_od_in"]),
             ("vent-stack", "vent", p[R + "vent_stack_od_in"]),
             ("hot", "hot", pex_od_in(sizes["hot"], ins(sizes["hot"]))),
             ("hot-return", "hot-return", pex_od_in(sizes["return"], ins(sizes["return"]))),
             ("cold", "cold", pex_od_in(sizes["cold"], p[R + "cold_insulation_in"])),
             ("loop-supply", "loop-supply", pex_od_in(sizes["loop"], p[R + "loop_insulation_in"])),
             ("loop-return", "loop-return", pex_od_in(sizes["loop"], p[R + "loop_insulation_in"]))]
    out = {}
    for col in sorted({column(n) for n in fx}):
        names = sorted(n for n in fx if column(n) == col)
        first = names[0]
        order_c = order + [(f"line-set/{n}", "line-set", p[R + "line_set_od_in"]) for n in names]
        w = next(x for x in apt["rooms"]["walls"] if x["id"] == f"{first}/plumbing-wall")
        studs = studs_in(frame, w["lo_m"], w["hi_m"], 1)
        cav = (min(a for a, _ in studs), max(b for _, b in studs))
        stud_bays = [(a[1], b[0]) for a, b in zip(studs, studs[1:])]
        # The studs' depth across the wall: the cavity a pipe must fit in.
        sx = [m for m in frame["members"] if m["storey"] == 1 and m["kind"] == "studs"]
        x0, x1 = w["lo_m"][0], w["hi_m"][0]
        dx = next(_bounds(m) for m in sx if _bounds(m)[0][0] >= x0 - 1e-6 and _bounds(m)[1][0] <= x1 + 1e-6
                  and cav[0] - 1e-6 <= _bounds(m)[0][1] <= cav[1])
        cx, depth = (dx[0][0] + dx[1][0]) / 2, dx[1][0] - dx[0][0]
        free = stud_bays
        for s in range(2, apt["storeys"] + 1):
            js = joists_under(frame, apt, s, cx)
            jb = bays(js, cav[0], cav[1])
            free = [(max(a, c), min(b, d)) for a, b in free for c, d in jb if min(b, d) > max(a, c)]
        wy = fx[first]["washer"]["y"]
        hw = (p[R + "washer_box_w_in"] / 2) * IN + gap
        free = _free(free, [(wy - hw, wy + hw)])
        wc_y = fx[first]["wc"]["y"]
        far_end = cav[1] if abs(cav[1] - wc_y) > abs(cav[0] - wc_y) else cav[0]
        near_end = cav[0] if far_end == cav[1] else cav[1]
        placed, taken = [], []
        for key, kind, od in order_c:
            r_ = od * IN / 2
            # The vent stack beside the drain stack on its far side from the fixtures, so their
            # drains reach the drain stack along the wall; their vents reach the vent stack over the
            # ceiling (7b).
            target = wc_y if kind == "drain" else (placed[0]["y"] - (0.15 if near_end < wc_y else -0.15) if kind == "vent" else far_end)
            best = None
            for a, b in _free(free, taken):
                lo_, hi_ = a + r_ + gap, b - r_ - gap
                if lo_ > hi_ + 1e-9:
                    continue
                y = min(max(target, lo_), hi_)
                if best is None or abs(y - target) < abs(best - target) - 1e-12:
                    best = y
            if best is None or od * IN > depth - 2 * p[R + "cavity_clear_in"] * IN:
                placed.append({"id": f"{col}/{key}", "kind": kind, "od_in": od, "x": cx, "y": None})
                continue
            placed.append({"id": f"{col}/{key}", "kind": kind, "od_in": od, "x": cx, "y": best})
            taken.append((best - r_, best + r_))
        out[col] = placed
    return out


def default_sizes(apt: dict, p: dict) -> dict:
    """The risers' nominal sizes (in.) as steps 3-4 chose them: the cold and hot risers from the
    pressure path, the return riser from the loop, the heating loop's riser."""
    from .hvac import substation
    from .plumbing import design

    d = design(apt, p)
    seg = {k: next(s["in"] for s in d["paths"][k]["segments"] if "riser" in s["segment"]) for k in ("cold", "hot")}
    from .routed import grown

    loop = max(max(r["pipe_in"] for r in substation(apt, p)["risers"].values()), grown().get("loop_riser_in", {}).get("loop", 0.0))
    return {"cold": seg["cold"], "hot": seg["hot"], "return": d["loop"]["return_riser_in"], "loop": loop}


def vertical_checks(apt: dict, p: dict, frame: dict, fx: dict, vs: dict) -> list[tuple[str, bool, str]]:
    """Every vertical service placed in its plumbing wall, and each stack in its water closet's
    joist bay."""
    missing = [s["id"] for v in vs.values() for s in v if s["y"] is None]
    off = []
    half = (p[R + "closet_bend_od_in"] / 2) * IN
    for col, v in vs.items():
        stack = next(s for s in v if s["kind"] == "drain")
        first = sorted(n for n in fx if column(n) == col)[0]
        bath = next(r for r in by_flat(apt)[first] if r["use"] == "bath")
        wc = fx[first]["wc"]["y"]
        for s in range(2, apt["storeys"] + 1):
            bay = next(((a, b) for a, b in bays(joists_under(frame, apt, s, stack["x"]), bath["lo_m"][1] - 1, bath["hi_m"][1] + 1) if a <= wc <= b), None)
            if stack["y"] is None or bay is None or not (bay[0] + half <= stack["y"] <= bay[1] - half):
                off.append(f"{col} (floor {s})")
    n = sum(len(v) for v in vs.values())
    return [("every column's vertical services in its plumbing wall, each in a stud bay that is a joist bay on every floor",
             not missing, ", ".join(missing) or f"{n} in 4 walls"),
            ("every drain stack in its water closet's joist bay", not off, ", ".join(off) or "all four")]


def soffit_spans(wall: dict, sf: list[dict]) -> list[tuple[float, float]]:
    """Where along a partition (its length's spans) a soffit runs over it or on both its sides: where
    forge stops it at the soffit (`framing::under_soffits`, the same rule)."""
    along = 1 if wall["hi_m"][1] - wall["lo_m"][1] > wall["hi_m"][0] - wall["lo_m"][0] else 0
    c = 1 - along
    lo, hi = wall["lo_m"], wall["hi_m"]
    out = []
    near = lambda a, b: abs(a - b) < 1e-3  # noqa: E731
    for x in sf:
        u0, u1 = max(x["lo"][along], lo[along]), min(x["hi"][along], hi[along])
        if u1 - u0 < 1e-3:
            continue
        if x["lo"][c] < hi[c] - 1e-3 and x["hi"][c] > lo[c] + 1e-3:
            out.append((u0, u1))
        elif near(x["hi"][c], lo[c]):
            for y in sf:
                if near(y["lo"][c], hi[c]):
                    w0, w1 = max(u0, y["lo"][along]), min(u1, y["hi"][along])
                    if w1 - w0 > 1e-3:
                        out.append((w0, w1))
    return out


def feeder_chase(apt: dict, p: dict, frame: dict, sf: list[dict]) -> dict[str, dict]:
    """Each column's panels and feeder conduits in the partition between hall and bath (step 5's
    place, `electrical.panel_place`):
    - **the panel** in the stud bay nearest step 5's point that is a whole bay (a load centre's box
      wants one) and has no soffit over it: NEC 2020 110.26(E) keeps the space above a panel's
      footprint, to 6 ft above it or the structural ceiling, for the electrical installation, and a
      soffit there carries ducts and pipes;
    - **the conduits of the flats above** (NEC Chapter 9 fill, `electrical.conduit_for`) up
      neighbouring bays that are joist bays on every floor, the same on every storey. The ground
      floor's feeder comes up under its own panel."""
    from .electrical import conduit_for, feeders, panel_place

    fd = feeders(apt, p)
    gap = p[R + "riser_gap_in"] * IN
    box = p[R + "panel_box_w_in"] * IN
    out = {}
    for col in sorted({column(f["name"]) for f in apt["flats"]}):
        names = sorted((f["name"] for f in apt["flats"] if column(f["name"]) == col), key=lambda n: int(n.split("-", 1)[0]))
        first = names[0]
        wall = next(x for x in apt["rooms"]["walls"] if x["id"] == f"{first}/p4")
        studs = studs_in(frame, wall["lo_m"], wall["hi_m"], 1)
        stud_bays = [(a[1], b[0]) for a, b in zip(studs, studs[1:])]
        place = panel_place(apt, first)
        y_step5 = place["xy"][1]
        covered = soffit_spans(wall, [x for x in sf if x["flat"] == first])
        fits = [(abs((a + b) / 2 - y_step5), (a + b) / 2, (a, b)) for a, b in stud_bays if b - a >= box - 1e-9
                and not any(u0 < b and u1 > a for u0, u1 in covered)]
        _, y_panel, pbay = min(fits) if fits else (None, None, (0.0, 0.0))
        cx = (wall["lo_m"][0] + wall["hi_m"][0]) / 2
        free = [bay for bay in stud_bays if bay != pbay]
        for s in range(2, apt["storeys"] + 1):
            jb = bays(joists_under(frame, apt, s, cx), wall["lo_m"][1], wall["hi_m"][1])
            free = [(max(a, c), min(b, d)) for a, b in free for c, d in jb if min(b, d) > max(a, c)]
        conduits, taken = [], []
        for n in names[1:]:
            f = fd[n]
            c = conduit_for([f["size"]] * 3 + [f["egc"]], p)
            r_ = c["od_in"] * IN / 2
            best = None
            for a, b in _free(free, taken):
                lo_, hi_ = a + r_ + gap, b - r_ - gap
                if lo_ <= hi_ + 1e-9:
                    y = min(max(y_panel, lo_), hi_)
                    if best is None or abs(y - y_panel) < abs(best - y_panel):
                        best = y
            conduits.append({"id": f"{col}/feeder/{n}", "flat": n, "x": cx, "y": best, **c})
            if best is not None:
                taken.append((best - r_, best + r_))
        out[col] = {"panel_y": y_panel, "panel_bay": pbay, "step5_y": y_step5, "x": cx, "conduits": conduits, "covered": covered,
                    "own": {n: conduit_for([fd[n]["size"]] * 3 + [fd[n]["egc"]], p) for n in names}}
    return out


def chase_checks(apt: dict, p: dict, ch: dict) -> list[tuple[str, bool, str]]:
    """Every panel in a stud bay as wide as its box; every upper flat's conduit placed, inside the
    partition's studs."""
    box = p[R + "panel_box_w_in"] * IN
    placed = all(c["panel_y"] is not None and c["panel_bay"][1] - c["panel_bay"][0] >= box - 1e-9 for c in ch.values())
    moved = max((abs(c["panel_y"] - c["step5_y"]) for c in ch.values() if c["panel_y"] is not None), default=0.0)
    missing = [k["id"] for c in ch.values() for k in c["conduits"] if k["y"] is None]
    sched = json.loads((OUT_DIR / "pass3" / "frame.json").read_text(encoding="utf-8"))
    depth = sched["sizes_mm"]["2x4"][1] / 25.4  # the partition's studs (pass 3b's schedule)
    fat = max(k["od_in"] for c in ch.values() for k in c["conduits"])
    dedicated = all(not any(u0 < c["panel_bay"][1] and u1 > c["panel_bay"][0] for u0, u1 in c["covered"]) for c in ch.values())
    # Its working space (110.26(A)), in the hall it faces: 30 in. wide about the panel, 36 in. deep.
    w = "systems.wiring."
    room_ok, least = True, None
    for col, c in ch.items():
        for f in (f for f in apt["flats"] if column(f["name"]) == col):
            hall = next(r for r in apt["rooms"]["rooms"] if r["id"] == f"{f['name']}/hall")
            half = p[w + "working_width_in"] * IN / 2
            deep = hall["hi_m"][0] - hall["lo_m"][0]
            room_ok &= hall["lo_m"][1] - 1e-6 <= c["panel_y"] - half and c["panel_y"] + half <= hall["hi_m"][1] + 1e-6
            least = deep if least is None else min(least, deep)
    room_ok &= least >= p[w + "working_depth_in"] * IN - 1e-9
    return [("every panel in a whole stud bay of its partition", placed, f"moved at most {moved / IN:.1f} in. from step 5's point"),
            ("no soffit over any panel's footprint: its dedicated space (NEC 2020 110.26(E)) free of ducts and pipes", dedicated, ""),
            ("every moved panel still faces its hall with 110.26(A)'s working space: 30 in. wide, 36 in. deep", room_ok,
             f"the halls {least / IN:.1f} in. deep"),
            ("every upper flat's feeder conduit up its column's partition, in a stud bay that is a joist bay on every floor",
             not missing and fat <= depth - 2 * p[R + "cavity_clear_in"], ", ".join(missing) or f"{sum(len(c['conduits']) for c in ch.values())} conduits, at most {fat:g} in. in the 2x4's 3.5 in.")]


# ---- 7a: the soffits, the ERV's wall terminations, the roof's outdoor units ----

def ceiling_z(apt: dict, storey: int) -> float:
    """The underside of the joists over a storey (floor or roof, m): the next floor less the
    subfloor and the floor joist (pass 3b's schedule, `out/pass3/frame.json`); the roof joists sit
    on the same plates. The ceiling assembly (resilient channel and gypsum, `ceiling_assembly_in`)
    hangs under it."""
    sched = json.loads((OUT_DIR / "pass3" / "frame.json").read_text(encoding="utf-8"))
    return storey * apt["storey_m"] - (sched["subfloor_mm"] + sched["floor_joist"]["depth_mm"]) / 1000


def soffits(apt: dict, p: dict, terms: list[dict]) -> list[dict]:
    """Each flat's soffits, framed under the rated ceiling so no duct pierces it (IBC 2021 717.6.2
    would ask a ceiling radiation damper at every register through it): over the hall (the
    mini-split's indoor unit), the passage, the utility closet (the ERV) and the kitchen, and a
    strip across the living room from the kitchen to the flat's ERV termination (`terminations`)
    for its two 5 in. ducts (a furred ceiling over less than a third of the room, 1208.2.1), with
    a leg to the kitchen's where the termination is past its end. Each is a box (m) `soffit_in`
    deep under the ceiling's finish; the hall's, the passage's and the closet's
    `condensate_soffit_drop_in` deeper, for the mini-split's condensate."""
    by_t = {t["flat"]: t for t in terms}
    out = []
    for name, rooms in by_flat(apt).items():
        by = {r["id"].split("/")[1]: r for r in rooms}
        storey = by["hall"]["storey"]
        top = ceiling_z(apt, storey) - p[R + "ceiling_assembly_in"] * IN
        z0 = top - p[R + "soffit_in"] * IN
        # The hall's, the passage's and the closet's soffits go `condensate_soffit_drop_in` deeper,
        # under the mini-split and the ERV (both hung from the top): room for the mini-split's
        # condensate to fall by gravity, 1%, to the washer's standpipe (Jon, 2026-11-21: gravity
        # first; its drain port is 1-1/8 in. above the unit's bottom).
        zd = z0 - p[R + "condensate_soffit_drop_in"] * IN
        for key in ("hall", "passage", "utility", "kitchen"):
            r = by[key]
            out.append({"id": f"{name}/soffit-{key}", "flat": name, "room": r["id"], "lo": [r["lo_m"][0], r["lo_m"][1], z0 if key == "kitchen" else zd],
                        "hi": [r["hi_m"][0], r["hi_m"][1], top]})
        # The hall's soffit reaches past the hall over the partition and the bath, along the
        # mini-split, by what its width and its two side spaces need beyond the hall's width.
        hall = by["hall"]
        need = (p[R + "ms_w_in"] + p[R + "ms_side_other_in"] + p[R + "ms_side_piping_in"]) * IN - (hall["hi_m"][0] - hall["lo_m"][0])
        if need > 0:
            into = -1.0 if hall["hi_m"][0] <= apt["depth_m"] / 2 else 1.0  # the bath is toward the spine
            edge = hall["hi_m"][0] if into < 0 else hall["lo_m"][0]
            uy, half = (hall["lo_m"][1] + hall["hi_m"][1]) / 2, p[R + "ms_d_in"] * IN / 2 + p[R + "riser_gap_in"] * IN
            out.append({"id": f"{name}/soffit-hall-reach", "flat": name, "room": by["bath"]["id"],
                        "lo": [min(edge, edge - into * need), uy - half, zd], "hi": [max(edge, edge - into * need), uy + half, top]})
        liv, kit = by["living"], by["kitchen"]
        w = p[R + "furdown_w_in"] * IN
        y = by_t[name]["y"]
        lo_x, hi_x = (liv["lo_m"][0], kit["lo_m"][0]) if liv["lo_m"][0] < kit["lo_m"][0] else (kit["hi_m"][0], liv["hi_m"][0])
        out.append({"id": f"{name}/soffit-strip", "flat": name, "room": liv["id"], "lo": [lo_x, y - w / 2, z0], "hi": [hi_x, y + w / 2, top]})
        # Where the termination is past the kitchen's end (the middle storey's, a pier along), a leg
        # along the kitchen's side of the living room joins the strip to the kitchen's soffit.
        ky0, ky1 = kit["lo_m"][1], kit["hi_m"][1]
        lx0, lx1 = (hi_x - w, hi_x) if liv["lo_m"][0] < kit["lo_m"][0] else (lo_x, lo_x + w)
        if y + w / 2 > ky1:
            out.append({"id": f"{name}/soffit-strip-leg", "flat": name, "room": liv["id"], "lo": [lx0, ky1 - w, z0], "hi": [lx1, y + w / 2, top]})
        elif y - w / 2 < ky0:
            out.append({"id": f"{name}/soffit-strip-leg", "flat": name, "room": liv["id"], "lo": [lx0, y - w / 2, z0], "hi": [lx1, ky0 + w, top]})
    return out


def strip_soffits(apt: dict, p: dict) -> list[dict]:
    """The living rooms' strip soffits (not their legs, which run along a wall): continuous
    obstructions at the ceiling to the sprinklers' spray (step 7c)."""
    return [x for x in soffits(apt, p, terminations(apt, p)) if x["id"].endswith("/soffit-strip")]


def soffit_checks(apt: dict, p: dict, frame: dict, sf: list[dict]) -> list[tuple[str, bool, str]]:
    """What's left under each soffit against IBC 2021 1208.2 (7 ft in a dwelling's corridors,
    kitchens and laundries; a furred ceiling 7 ft, over at most a third of a room, 1208.2.1), and
    the mini-split's indoor unit inside its soffit."""
    rooms = {r["id"]: r for r in apt["rooms"]["rooms"]}
    least, furred = None, {}
    for s in sf:
        r = rooms[s["room"]]
        floor = r["lo_m"][2] + (p["systems.design.finished_floor_upper_in"] * IN if r["storey"] > 1 else 0.0)
        h = s["lo"][2] - floor
        least = h if least is None else min(least, h)
        if "strip" in s["id"]:
            # The strip and its leg overlap by their corner: the leg's area less the overlap.
            a = (s["hi"][0] - s["lo"][0]) * (s["hi"][1] - s["lo"][1])
            if s["id"].endswith("leg"):
                st = next(x for x in sf if x["id"] == s["id"][: -len("-leg")])
                ox = max(0.0, min(s["hi"][0], st["hi"][0]) - max(s["lo"][0], st["lo"][0]))
                oy = max(0.0, min(s["hi"][1], st["hi"][1]) - max(s["lo"][1], st["lo"][1]))
                a -= ox * oy
            furred[r["id"]] = furred.get(r["id"], 0.0) + a
    worst_share = max((a / rooms[k]["area_m2"] for k, a in furred.items()), default=0.0)
    unit_h = p[R + "minisplit_h_in"]
    fits = p[R + "soffit_in"] >= unit_h + p[R + "unit_hanger_in"]
    need = p["systems.code.room.min_ceiling_service_in"] * IN
    return [("every soffit leaves 7 ft under it (IBC 2021 1208.2, 1208.2.1)", least >= need - 1e-9,
             f"least {least / IN:.1f} in."),
            ("the living room's strip under a third of the room (1208.2.1)", worst_share < 1 / 3, f"at most {worst_share:.1%}"),
            ("the mini-split's indoor unit fits its soffit with its hangers", fits,
             f"{unit_h:g} + {p[R + 'unit_hanger_in']:g} in. in {p[R + 'soffit_in']:g}")]


def terminations(apt: dict, p: dict) -> list[dict]:
    """Each flat's ERV wall termination: one factory-built intake and exhaust combination (Broan's
    Tandem transition kit, which its manual names for the BLP120, with 5 in. ducts), so the intake
    needs no separation from its own exhaust (IMC 2021 401.4 item 3).
    - **Where:** on the flat's long facade, in the living room's wall, at the middle of a pier
      between two windows, at the soffits' mid-height. No pier on the facade is wide enough to keep
      3 ft from every opening (Broan's distance for an exhaust in a multifamily building, from
      operable openings), so the two windows either side are specified fixed (`fixed`): an
      Addendum 5 item.
    - **Which pier:** of those between two windows (none beside the patio door), the one nearest
      the kitchen; the middle storey's the next one along, so no intake is within 10 ft of another flat's exhaust
      (401.4 item 3, 3 ft below it otherwise; the storeys are exactly 10 ft apart)."""
    out = []
    for name, rooms in by_flat(apt).items():
        by = {r["id"].split("/")[1]: r for r in rooms}
        liv, kit = by["living"], by["kitchen"]
        storey = liv["storey"]
        front = liv["lo_m"][0] < apt["depth_m"] / 2
        face = "front" if front else "back"
        ops = sorted((o for o in apt["openings"] if o["flat"] == name and o["face"] == face
                      and liv["lo_m"][1] - 1e-6 <= (o["lo_m"][1] + o["hi_m"][1]) / 2 <= liv["hi_m"][1] + 1e-6),
                     key=lambda o: o["lo_m"][1])
        piers = []
        for a, b in zip(ops, ops[1:]):
            if a["kind"] == "window" and b["kind"] == "window":
                piers.append(((a["hi_m"][1] + b["lo_m"][1]) / 2, a, b))
        kc = (kit["lo_m"][1] + kit["hi_m"][1]) / 2
        piers.sort(key=lambda t: abs(t[0] - kc))
        y, a, b = piers[(storey + 1) % 2 if len(piers) > 1 else 0]
        top = ceiling_z(apt, storey) - p[R + "ceiling_assembly_in"] * IN
        z = top - p[R + "soffit_in"] * IN / 2
        out.append({"id": f"{name}/erv-termination", "flat": name, "x": 0.0 if front else apt["depth_m"], "y": y, "z": z,
                    "face": face, "fixed": [a["id"], b["id"]]})
    return out


def termination_checks(apt: dict, p: dict, terms: list[dict]) -> list[tuple[str, bool, str]]:
    """The terminations against IMC 2021 401.4 (an intake 10 ft from another flat's exhaust, or 3 ft
    below it) and Broan's manual for multifamily buildings (the exhaust 3 ft from an operable
    opening, 18 in. above the ground); the windows `terminations` specifies fixed don't count."""
    worst_pair, worst_open = None, None
    fixed = {f for t in terms for f in t["fixed"]}
    for a in terms:
        for b in terms:
            if a is b:
                continue
            d = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2 + (a["z"] - b["z"]) ** 2) ** 0.5
            below = b["z"] - a["z"]  # a's intake below b's exhaust
            ok = d > 10 * FT + 1e-9 or below >= 3 * FT - 1e-9
            if not ok:
                worst_pair = (a["id"], b["id"], d / FT)
        for o in apt["openings"]:
            if o["face"] != a["face"] or o["id"] in fixed:
                continue
            lo, hi = o["lo_m"], o["hi_m"]
            dy = max(lo[1] - a["y"], 0.0, a["y"] - hi[1])
            dz = max(lo[2] - a["z"], 0.0, a["z"] - hi[2])
            d = (dy ** 2 + dz ** 2) ** 0.5
            worst_open = d if worst_open is None else min(worst_open, d)
    return [("every ERV intake 10 ft from another flat's exhaust or 3 ft below it (IMC 2021 401.4)", worst_pair is None,
             "none closer" if worst_pair is None else f"{worst_pair[0]} and {worst_pair[1]}: {worst_pair[2]:.1f} ft"),
            ("every ERV termination 3 ft from any operable window or door (Broan, multifamily)", worst_open >= p[R + "termination_clear_ft"] * FT - 1e-9,
             f"least {worst_open / FT:.1f} ft"),
            ("every termination 18 in. above the ground (Broan)", min(t["z"] for t in terms) >= 18 * IN, f"lowest {min(t['z'] for t in terms) / FT:.1f} ft up")]


def roof_units(apt: dict, p: dict, vs: dict) -> list[dict]:
    """The 12 outdoor units on the roof (Fujitsu AOUH12KUBS1): each column's three side by side
    along y (Fujitsu: at most three in a row, 10 in. between them), centred on the column's line
    sets, their backs to the spine and the column across it (4 in. behind each), their fronts open
    to the facade (24 in.), on a stand `stand_in` high for the snow (Fujitsu's caution)."""
    h, w, d = (p[R + k] for k in ("ou_h_in", "ou_w_in", "ou_d_in"))
    roof = next(x for x in apt["parts"] if x["kind"] == "roof")
    z0 = roof["hi_m"][2] + p[R + "stand_in"] * IN
    cx = apt["depth_m"] / 2
    out = []
    for col, v in vs.items():
        ls = [s for s in v if s["kind"] == "line-set" and s["y"] is not None]
        yc = sum(s["y"] for s in ls) / len(ls)
        front = col.startswith("front")
        rear = cx - p[R + "ou_rear_in"] * IN if front else cx + p[R + "ou_rear_in"] * IN
        x0, x1 = (rear - d * IN, rear) if front else (rear, rear + d * IN)
        n = len(ls)
        span = n * w * IN + (n - 1) * p[R + "ou_between_in"] * IN
        for i, s in enumerate(sorted(ls, key=lambda s: s["id"])):
            y0 = yc - span / 2 + i * (w + p[R + "ou_between_in"]) * IN
            out.append({"id": f"{s['id'].split('/', 2)[2]}/outdoor-unit", "flat": s["id"].split("/", 2)[2], "column": col,
                        "lo": [x0, y0, z0], "hi": [x1, y0 + w * IN, z0 + h * IN], "front": "-x" if front else "+x"})
    return out


def roof_checks(apt: dict, p: dict, units: list[dict]) -> list[tuple[str, bool, str]]:
    """The units clear of each other at Fujitsu's spacing, inside the roof's perimeter pathway (IFC
    2021 1205.3.1, the PV design's), clear of the hatch's 4 ft path, with their fronts' 24 in."""
    from .fire import roof_access
    roof = next(x for x in apt["parts"] if x["kind"] == "roof")
    edge = p["systems.pv.perimeter_ft"] * FT
    inside = all(u["lo"][0] >= roof["lo_m"][0] + edge and u["hi"][0] <= roof["hi_m"][0] - edge and u["lo"][1] >= roof["lo_m"][1] + edge
                 and u["hi"][1] <= roof["hi_m"][1] - edge for u in units)
    gap = min((max(b["lo"][1] - a["hi"][1], a["lo"][1] - b["hi"][1]) for a in units for b in units
               if a is not b and a["column"] == b["column"]), default=1.0)
    hatch = roof_access(apt, p)
    path = p[R + "hatch_path_ft"] * FT
    clear_hatch = all(u["hi"][0] < hatch["lo"][0] - path or u["lo"][0] > hatch["hi"][0] + path or u["hi"][1] < hatch["lo"][1] - path
                      or u["lo"][1] > hatch["hi"][1] + path for u in units)
    fr = p[R + "ou_front_in"] * IN
    zones = [{"lo": [u["lo"][0] - fr, u["lo"][1], u["lo"][2]] if u["front"] == "-x" else [u["hi"][0], u["lo"][1], u["lo"][2]],
              "hi": [u["lo"][0], u["hi"][1], u["hi"][2]] if u["front"] == "-x" else [u["hi"][0] + fr, u["hi"][1], u["hi"][2]], "of": u["id"]}
             for u in units]
    blocked = [z["of"] for z in zones for u in units if u["id"] != z["of"] and _overlap(z, u)]
    return [("12 outdoor units, three to a column, 10 in. apart (Fujitsu's installation space)",
             len(units) == len(apt["flats"]) and gap >= p[R + "ou_between_in"] * IN - 1e-9, f"{len(units)} units, least {gap / IN:.1f} in. apart"),
            ("the outdoor units inside the roof's perimeter pathway (IFC 2021 1205.3.1)", inside, f"{p['systems.pv.perimeter_ft']:g} ft from the edge"),
            ("the outdoor units clear of the hatch's 4 ft path (IFC 2021 1205.3.2)", clear_hatch, ""),
            ("24 in. open in front of every outdoor unit (Fujitsu)", not blocked, ", ".join(blocked))]


def fixture_checks(apt: dict, p: dict, frame: dict, fx: dict) -> list[tuple[str, bool, str]]:
    """The fixtures against 405.3.1 and the frame: every water closet in a joist bay with its bend
    clear of the flanges on every upper floor; the lavatory 30 in. from it and 15 in. from the wall;
    the water closet's 21 in. in front; the tub inside the bath."""
    res = []
    side, gap, front = (p[R + k] * IN for k in ("fixture_side_in", "fixture_spacing_in", "wc_front_in"))
    half = (p[R + "closet_bend_od_in"] / 2 + p[R + "bend_clear_in"]) * IN
    bad_bay, bad_405 = [], []
    worst_front = None
    for name, f in fx.items():
        bath = next(r for r in by_flat(apt)[name] if r["use"] == "bath")
        if f["lav"]["y"] is None or abs(f["lav"]["y"] - f["wc"]["y"]) < gap - 1e-9:
            bad_405.append(name)
        for k in ("wc", "lav"):
            y = f[k]["y"]
            if y is not None and min(y - bath["lo_m"][1], bath["hi_m"][1] - y) < side - 1e-9:
                bad_405.append(f"{name} {k}")
        x_bend = f["wc"]["x"] + f["wc"]["into"] * f["wc"]["out_m"]
        room = bath["hi_m"][0] - bath["lo_m"][0]
        clear = room - p[R + "wc_depth_in"] * IN
        if p["systems.design.tub_length_in"] * IN > room + 1e-9:
            bad_405.append(f"{name} tub")
        worst_front = clear if worst_front is None else min(worst_front, clear)
        storey = bath["storey"]
        for s in range(max(storey, 2), apt["storeys"] + 1):
            js = joists_under(frame, apt, s, x_bend)
            if not any(b0 + half - 1e-9 <= f["wc"]["y"] <= b1 - half + 1e-9 for b0, b1 in bays(js, bath["lo_m"][1], bath["hi_m"][1])):
                bad_bay.append(f"{name} (floor {s})")
    res.append(("every water closet's bend inside one joist bay, clear of its flanges (APA Z725E: no hole by the support)",
                not bad_bay, ", ".join(bad_bay) or f"{len(fx)} water closets, {p[R + 'closet_bend_od_in']:g} in. bends"))
    res.append(("the bath's fixtures at IPC 405.3.1's clearances (15 in. to a side wall, 30 in. apart), the tub across it",
                not bad_405, ", ".join(bad_405) or "all"))
    res.append(("21 in. clear in front of every water closet (405.3.1)", worst_front >= front - 1e-9,
                f"least {worst_front / IN:.1f} in."))
    return res


def frame_checks(apt: dict, p: dict, frame: dict) -> list[tuple[str, bool, str]]:
    """Addendum 5's frame against Addendum 3's (the shell, as published) and against the rooms: the
    shell's members all there but the roof joists the hatch cuts; every partition and plumbing wall
    framed within IBC Table 2308.5.1; no member inside the hatch's opening, doubled trimmers either
    side of it and a doubled header."""
    from .fire import roof_access

    base = OUT_DIR / "pass3" / "framing-members-addendum-3.json"
    res = []
    if base.exists():
        old = json.loads(base.read_text(encoding="utf-8"))["members"]
        new = {(m["kind"], m["storey"], json.dumps(m["boxes"])) for m in frame["members"]}
        h = roof_access(apt, p)
        gone = [m for m in old if (m["kind"], m["storey"], json.dumps(m["boxes"])) not in new]
        cut = all(m["kind"] == "roof joists" and _bounds(m)[1][0] > h["lo"][0] - 0.1 and _bounds(m)[0][0] < h["hi"][0] + 0.1 for m in gone)
        res.append(("Addendum 5's frame keeps Addendum 3's shell, but for the roof joists the hatch cuts", cut,
                    f"{len(old) - len(gone)} of {len(old)} kept; {len(gone)} roof joists cut; {len(frame['members'])} members in all"))
    worst, tallest = 0.0, 0.0
    for w in apt["rooms"]["walls"]:
        st = studs_in(frame, w["lo_m"], w["hi_m"], w["storey"])
        worst = max([worst] + [b[0] - a[0] for a, b in zip(st, st[1:])])
        tallest = max(tallest, w["hi_m"][2] - w["lo_m"][2])
    res.append(("every partition and plumbing wall framed within IBC Table 2308.5.1 (nonbearing: 24 in. on centre, 14 ft unsupported)",
                worst <= p[R + "nonbearing_stud_max_in"] * IN + 1e-6 and tallest <= p[R + "nonbearing_height_max_ft"] * FT,
                f"{len(apt['rooms']['walls'])} walls on a 16 in. layout, the end bays up to {worst / IN:.1f} in.; {tallest / FT:.1f} ft high"))
    h = roof_access(apt, p)
    inside = [m["id"] for m in frame["members"] if m["storey"] == apt["storeys"] and m["kind"] in ("roof joists", "headers (plies)")
              and any(b[0][0] < h["hi"][0] - 1e-6 and b[1][0] > h["lo"][0] + 1e-6 and b[0][1] < h["hi"][1] - 1e-6 and b[1][1] > h["lo"][1] + 1e-6
                      for b in m["boxes"])]
    ply = 1.5 * IN
    roofs = [_bounds(m) for m in frame["members"] if m["kind"] == "roof joists" and m["storey"] == apt["storeys"]]
    left = sum(1 for lo, hi in roofs if h["lo"][0] - 2 * ply - 1e-4 <= lo[0] and hi[0] <= h["lo"][0] + 1e-4)
    right = sum(1 for lo, hi in roofs if h["hi"][0] - 1e-4 <= lo[0] and hi[0] <= h["hi"][0] + 2 * ply + 1e-4)
    headers = sum(1 for m in frame["members"] if m["kind"] == "headers (plies)" and m["storey"] == apt["storeys"]
                  and abs(_bounds(m)[0][1] - h["hi"][1]) < 2 * ply + 1e-4 and abs(_bounds(m)[0][0] - h["lo"][0]) < 1e-4)
    res.append(("the roof hatch's opening clear of framing, doubled trimmers either side and a doubled header",
                not inside and left == 2 and right == 2 and headers == 2,
                ", ".join(inside) or f"{h['area_ft2']:.1f} ft2 clear"))
    return res


# ---- 7a: the equipment ----

def _box(id_: str, kind: str, lo: list[float], hi: list[float], **kw) -> dict:
    return {"id": id_, "kind": kind, "lo": [min(a, b) for a, b in zip(lo, hi)], "hi": [max(a, b) for a, b in zip(lo, hi)], **kw}


def flat_equipment(apt: dict, p: dict, frame: dict, fx: dict, ch: dict, sf: list[dict]) -> list[dict]:
    """Each flat's equipment as boxes (m):
    - **the washer and dryer** stacked against the plumbing wall in the utility closet, on its box;
    - **the ERV** in the closet's soffit over its free floor (between the door's wall and the
      stack, so its access door opens over floor), its length along the closet;
    - **the radiant manifold's cabinet** on the closet's wall to the bath, by the door, 16 in. up;
    - **the mini-split's indoor unit** in the hall's soffit, its airflow along the hall, its
      non-piping side 6 in. off the hall's far wall; the 12 in. it wants on its piping side reaches
      past the hall over the partition (step 7b frames that partition to the soffit there);
    - **the load centre** flush in the hall's partition at the panel's bay (`feeder_chase`)."""
    sp = {s["id"]: s for s in sf}
    hang = p[R + "unit_hanger_in"] * IN
    out = []
    for name, rooms in by_flat(apt).items():
        by = {r["id"].split("/")[1]: r for r in rooms}
        f = fx[name]
        face, into = f["wc"]["x"], f["wc"]["into"]
        util, hall = by["utility"], by["hall"]
        z0 = f["wc"]["floor_z"]
        # The washer and dryer.
        w, d, h = (p[R + k] * IN for k in ("wd_stack_w_in", "wd_stack_d_in", "wd_stack_h_in"))
        wy = f["washer"]["y"]
        out.append(_box(f"{name}/washer-dryer", "appliance", [face + into * d, wy - w / 2, z0], [face, wy + w / 2, z0 + h], flat=name))
        # The ERV: over the floor between the closet's door wall and the stack's front.
        far = util["lo_m"][0] if into < 0 else util["hi_m"][0]
        front = face + into * d
        L, W, H = (p[R + k] * IN for k in ("erv_l_in", "erv_w_in", "erv_h_in"))
        xc = (far + front) / 2
        yc = (util["lo_m"][1] + util["hi_m"][1]) / 2
        s = sp[f"{name}/soffit-utility"]
        out.append(_box(f"{name}/erv", "erv", [xc - L / 2, yc - W / 2, s["hi"][2] - H], [xc + L / 2, yc + W / 2, s["hi"][2]], flat=name))
        # The manifold cabinet: on the closet's wall to the bath, by the door's wall.
        bath = by["bath"]
        wall_y = util["lo_m"][1] if bath["hi_m"][1] <= util["lo_m"][1] + 1e-6 else util["hi_m"][1]
        toward = 1.0 if wall_y == util["lo_m"][1] else -1.0
        cw, chh, cd = (p[R + k] * IN for k in ("manifold_cab_w_in", "manifold_cab_h_in", "manifold_cab_d_in"))
        x0 = far - into * p[R + "wall_gap_in"] * IN
        zc0 = z0 + p[R + "manifold_floor_in"] * IN
        out.append(_box(f"{name}/manifold", "manifold", [x0, wall_y, zc0], [x0 - into * cw, wall_y + toward * cd, zc0 + chh], flat=name))
        # The mini-split's indoor unit, hung in the hall's soffit.
        hs = sp[f"{name}/soffit-hall"]
        mw, md, mh = (p[R + k] * IN for k in ("ms_w_in", "ms_d_in", "minisplit_h_in"))
        hall_far = hall["lo_m"][0] if into < 0 else hall["hi_m"][0]
        ux0 = hall_far - into * p[R + "ms_side_other_in"] * IN
        uy = (hall["lo_m"][1] + hall["hi_m"][1]) / 2
        top = hs["hi"][2] - hang
        out.append(_box(f"{name}/minisplit", "minisplit", [ux0, uy - md / 2, top - mh], [ux0 - into * mw, uy + md / 2, top], flat=name,
                        piping_clear_to=ux0 - into * (mw + p[R + "ms_side_piping_in"] * IN)))
        # The load centre, flush in the hall's side of its partition.
        c = ch[column(name)]
        pw = next(x for x in apt["rooms"]["walls"] if x["id"] == f"{name}/p4")
        on_lo = abs(pw["lo_m"][0] - hall["hi_m"][0]) < 1e-6
        hall_face = pw["lo_m"][0] if on_lo else pw["hi_m"][0]
        sign = 1.0 if on_lo else -1.0
        bw, bh, bd = (p[R + k] * IN for k in ("panel_box_w_in", "panel_box_h_in", "panel_box_d_in"))
        zc = z0 + p["systems.wiring.panel_mid_in"] * IN
        out.append(_box(f"{name}/panel", "panel", [hall_face, c["panel_y"] - bw / 2, zc - bh / 2],
                        [hall_face + sign * bd, c["panel_y"] + bw / 2, zc + bh / 2], flat=name))
    return out


def annex_equipment(apt: dict, p: dict) -> list[dict]:
    """The mechanical room's floor-standing plant (m), laid out against its walls:
    - **the storage tank** in the corner of the far wall and the partition, its anodes' 36 in.
      toward the room;
    - **the heat pump** against the partition by the door's wall, its front (connections, 36 in.
      of service) toward the room;
    - **the swing tank** against the partition between them, its 24 in. in front.
    The fire and domestic services' assemblies, the plate exchangers, pumps and mixing valve hang
    on the walls above the floor (7b routes to them)."""
    mech = next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/mechanical")
    (_, y0, z0), (x1, y1, _) = mech["lo_m"], mech["hi_m"]
    g = p[R + "wall_gap_in"] * IN
    D, Ht = p[R + "tank_dia_in"] * IN, p[R + "tank_h_in"] * IN
    tank = _box("annex/storage-tank", "tank", [x1 - g - D, y1 - g - D, z0], [x1 - g, y1 - g, z0 + Ht],
                service=[[x1 - g - D - p[R + "tank_anode_in"] * IN, y1 - g - D, z0], [x1 - g - D, y1 - g, z0 + Ht]])
    hw, hd, hh = (p[R + k] * IN for k in ("hp_w_in", "hp_d_in", "hp_h_in"))
    hp = _box("annex/heat-pump", "heat_pump", [x1 - g - hd, y0 + g, z0], [x1 - g, y0 + g + hw, z0 + hh],
              service=[[x1 - g - hd - p[R + "hp_service_in"] * IN, y0 + g, z0], [x1 - g - hd, y0 + g + hw, z0 + hh]])
    sd, sh = p[R + "swing_dia_in"] * IN, p[R + "swing_h_in"] * IN
    ym = (hp["hi"][1] + tank["lo"][1]) / 2
    swing = _box("annex/swing-tank", "tank", [x1 - g - sd, ym - sd / 2, z0], [x1 - g, ym + sd / 2, z0 + sh],
                 service=[[x1 - g - sd - p[R + "swing_front_in"] * IN, ym - sd / 2, z0], [x1 - g - sd, ym + sd / 2, z0 + sh]])
    return [tank, hp, swing]


def _overlap(a: dict, b: dict, tol: float = 1e-6) -> bool:
    return all(min(a["hi"][i], b["hi"][i]) - max(a["lo"][i], b["lo"][i]) > tol for i in range(3))


def equipment_checks(apt: dict, p: dict, eq: list[dict], plant: list[dict], sf: list[dict]) -> list[tuple[str, bool, str]]:
    """The equipment where it can be served: each ERV over open floor with its access door, each
    mini-split inside its soffit's depth, no two pieces overlapping; the plant inside its room with
    each piece's service space clear of the others and of the door's way in."""
    rooms = {r["id"]: r for r in apt["rooms"]["rooms"]}
    by: dict[str, dict] = {}
    for e in eq:
        by.setdefault(e["flat"], {})[e["kind"]] = e
    bad_erv, bad_ms, clash = [], [], []
    door_l = p[R + "erv_door_l_in"] * IN
    for name, k in by.items():
        erv, wd = k["erv"], k["appliance"]
        over = min(erv["hi"][0], wd["hi"][0]) - max(erv["lo"][0], wd["lo"][0])
        util = rooms[f"{name}/utility"]
        free_floor = (util["hi_m"][0] - util["lo_m"][0]) - (wd["hi"][0] - wd["lo"][0])
        if over > 1e-6 or free_floor < door_l - 1e-9:
            bad_erv.append(name)
        s = next(x for x in sf if x["id"] == f"{name}/soffit-hall")
        if k["minisplit"]["lo"][2] < s["lo"][2] - 1e-6:
            bad_ms.append(name)
        vals = list(k.values())
        clash += [f"{a['id']} / {b['id']}" for i, a in enumerate(vals) for b in vals[i + 1:] if _overlap(a, b)]
    mech = rooms["annex/mechanical"]
    inside = all(all(mech["lo_m"][i] - 1e-6 <= e["lo"][i] and e["hi"][i] <= mech["hi_m"][i] + 1e-6 for i in range(3)) for e in plant)
    svc = [f"{a['id']} / {b['id']}" for a in plant for b in plant if a is not b and _overlap({"lo": a["service"][0], "hi": a["service"][1]}, b)]
    door = next(d for d in apt["rooms"]["annex"]["doors"] if d["room"] == "annex/mechanical")
    way = {"lo": [door["lo_m"][0], mech["lo_m"][1], 0.0], "hi": [door["hi_m"][0], mech["lo_m"][1] + p["systems.wiring.working_depth_in"] * IN, 2.0]}
    blocked = [e["id"] for e in plant if _overlap(e, way)]
    over_wall = max(abs(k["minisplit"]["piping_clear_to"] - (rooms[f"{n}/hall"]["hi_m"][0] if k["minisplit"]["piping_clear_to"] > rooms[f"{n}/hall"]["hi_m"][0]
                    else rooms[f"{n}/hall"]["lo_m"][0])) for n, k in by.items())
    return [("every ERV over open floor in its closet, with room for its 20 x 30 in. access door under it (Broan)", not bad_erv,
             ", ".join(bad_erv) or f"{len(by)} closets"),
            ("every mini-split's indoor unit inside its hall's soffit", not bad_ms,
             ", ".join(bad_ms) or f"its 12 in. piping side reaches {over_wall / IN:.1f} in. past the hall (the partition framed to the soffit, 7b)"),
            ("no two pieces of a flat's equipment overlap", not clash, ", ".join(clash[:4])),
            ("the plant inside the mechanical room, each piece's service space clear of the rest and the door's way in clear",
             inside and not svc and not blocked, "; ".join(svc + blocked) or "storage tank, heat pump, swing tank")]


# ---- 7a as data and as text ----

def placements(apt: dict, p: dict) -> dict:
    """Everything 7a places, from forge's Addendum 5 frame."""
    frame = load_frame(apt, p)
    fx = fixtures(apt, p, frame)
    vs = vertical_services(apt, p, frame, fx)
    terms = terminations(apt, p)
    sf = soffits(apt, p, terms)
    ch = feeder_chase(apt, p, frame, sf)
    units = roof_units(apt, p, vs)
    eq = flat_equipment(apt, p, frame, fx, ch, sf)
    plant = annex_equipment(apt, p)
    return {"frame": frame, "fixtures": fx, "verticals": vs, "chase": ch, "terminations": terms, "soffits": sf, "units": units,
            "equipment": eq, "plant": plant}


def summary(apt: dict, p: dict) -> dict:
    """7a's checks and what it placed (the frame left out: forge's file has it)."""
    d = placements(apt, p)
    fr = d.pop("frame")
    checks = (frame_checks(apt, p, fr) + fixture_checks(apt, p, fr, d["fixtures"]) + vertical_checks(apt, p, fr, d["fixtures"], d["verticals"])
              + chase_checks(apt, p, d["chase"]) + soffit_checks(apt, p, fr, d["soffits"]) + termination_checks(apt, p, d["terminations"])
              + roof_checks(apt, p, d["units"]) + equipment_checks(apt, p, d["equipment"], d["plant"], d["soffits"]))
    return {"revision": apt["revision"], "frame_members": len(fr["members"]), "checks": checks, "design": d,
            "hatch_command": hatch_command(apt, p), "tub_half_in": p["systems.design.tub_width_in"] / 2}


def report(s: dict) -> str:
    """7a in plain text."""
    from .systems import report as checks

    d = s["design"]
    fl = d["fixtures"]["2-front-left"]
    vs = d["verticals"]["front-left"]
    ch = d["chase"]["front-left"]
    fixed = sorted({f for t in d["terminations"] for f in t["fixed"]})
    lines = [f"Pass 3g step 7a: what the routes connect, and the frame they go through ({s['revision']})", "", checks(s["checks"]), "",
             f"The frame: forge's Addendum 5, {s['frame_members']:,} members (`{s['hatch_command']}`): the shell, and the flats' "
             "partitions and plumbing walls, the annex, the stair halls' floors and the roof hatch's opening framed.",
             f"Each bath (2-front-left): the tub across its end; the water closet's centre "
             f"{abs(fl['wc']['y'] - fl['tub']['y']) / IN - s['tub_half_in']:.1f} in. from the tub (15 at least), set in a joist bay so its "
             f"bend runs along it to the stack in the same bay; the lavatory {abs(fl['lav']['y'] - fl['wc']['y']) / IN:.1f} in. on (30 at least).",
             "Each plumbing wall (front-left): " + "; ".join(f"{x['id'].split('/', 1)[1]} {x['od_in']:.2f} in. at y {x['y']:.3f} m" for x in vs) + ".",
             f"The feeders (front-left): the panel moved {abs(ch['panel_y'] - ch['step5_y']) / IN:.1f} in. into a whole stud bay; "
             + ", ".join(f"{k['flat']}'s {k['trade']} in. conduit" for k in ch["conduits"]) + " up the bays beside it.",
             f"The ERVs: a Tandem termination each on the long facade between two living-room windows; {len(fixed)} windows "
             "specified fixed so the exhaust is 3 ft from every operable opening (Addendum 5).",
             f"The roof: {len(d['units'])} outdoor units, three a column, back to back across the spine."]
    return "\n".join(lines)
