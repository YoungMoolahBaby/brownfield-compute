"""Pass 3g (D28): the walk-up's systems, designed before anyone bids.

Step 1, the rooms. Forge `rooms` lays out every flat's rooms, partitions and plumbing wall, and the
service annex behind the stair, as Addendum 2 (Addendum 1 plus the rooms and the annex, and the
stair window the annex covers removed): `cargo run --release -- apartment-json addendum-2 60` in
forge/ writes out/pass3/apartment-addendum-2.json. This checks them against IBC 2021, the edition
Pennsylvania enforces (params/systems.yaml `code`):

- **Room sizes (1208):** habitable rooms at least 7 ft in plan and 70 ft2, one room a flat of
  120 ft2, ceilings 7 ft 6 in (7 ft in baths, kitchens, laundry and a flat's corridors).
- **The hall (Table 1020.3):** 36 in clear within a dwelling unit.
- **The kitchen (1208.1):** 36 in clear past the counter on the plumbing wall.
- **Escape openings (1031):** every bedroom gets one, named on the window. A window's net clear
  opening depends on how it opens, which the model doesn't say (D27). The rough opening bounds it:
  a hung sash opens at most half the height, a slider at most half the width, so a 3 x 4 ft window
  can serve only if it is side-hinged (a casement). The check says which.
- **The layout's own promises:** the rooms, walls and the plumbing wall's air gap cover each flat's
  floor exactly, measured against pass 3b's `flat_envelope` (an independent number); wet rooms
  stack floor over floor and sit back to back across the spine; Addendum 2 changes nothing in the
  building but the one stair window.

A study nook open to the living room is part of that room, not a room of its own: at 6.3 ft deep
it would fail 1208.1 if it had a door. That reading is ours, and the report says so.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from . import OUT_DIR

REVISION = "addendum-2"
PATH = OUT_DIR / "pass3" / "apartment-addendum-2.json"
BASE = OUT_DIR / "pass3" / "apartment-addendum-1.json"
FT = 0.3048
IN = 0.0254
FT2 = FT ** 2
EPS = 1e-6
HABITABLE = ("bedroom", "living")  # the study nook is open to the living room (see above)
WET = ("bath", "utility", "kitchen")


def load(path: Path = PATH) -> dict:
    if not path.exists():
        raise SystemExit(f"no {path.relative_to(OUT_DIR.parent)}: run `cargo run --release -- apartment-json "
                         f"{REVISION} 60` in forge/ first")
    apt = json.loads(path.read_text(encoding="utf-8"))
    if "rooms" not in apt:
        raise SystemExit(f"{path.name} has no rooms: it isn't Addendum 2")
    return apt


def _dx(r: dict) -> float:
    return r["hi_m"][0] - r["lo_m"][0]


def _dy(r: dict) -> float:
    return r["hi_m"][1] - r["lo_m"][1]


def by_flat(apt: dict) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in apt["rooms"]["rooms"]:
        if r["flat"]:
            out[r["flat"]].append(r)
    return dict(out)


def ceiling_in(apt: dict, r: dict, P: dict) -> float:
    """A room's ceiling height above the finished floor (in): its box, less the radiant topping on
    the upper floors."""
    h = (r["hi_m"][2] - r["lo_m"][2]) / IN
    return h - (P["systems.design.finished_floor_upper_in"] if r["storey"] > 1 else 0.0)


def escape_options(apt: dict, r: dict, P: dict) -> list[dict]:
    """A bedroom's windows, each with what its rough opening allows (in, ft2) and which ways of
    opening could give 1031's net clear opening."""
    ops = {o["id"]: o for o in apt["openings"]}
    c = "systems.code.escape."
    floor = P["systems.design.finished_floor_upper_in"] if r["storey"] > 1 else 0.0
    out = []
    for oid in r["openings"]:
        o = ops[oid]
        if o["kind"] != "window":
            continue
        # To a millionth of an inch: metres to inches leaves float noise (48.00000000000001).
        w, h = round(o["width_m"] / IN, 6), round(o["height_m"] / IN, 6)
        sill = round(o["sill_above_floor_m"] / IN - floor, 6)
        # Bounds on the net clear opening by how the window opens. A frame (and a hung or sliding
        # window's meeting rail) always takes some, so the clear opening is strictly less than the
        # bound and its sill strictly higher: a bound that only equals a limit fails it.
        fits = lambda cw, ch: cw * ch / 144.0 > P[c + "net_clear_ft2"] and ch > P[c + "min_height_in"] and cw > P[c + "min_width_in"]
        out.append({
            "id": oid, "width_in": w, "height_in": h, "sill_in": sill,
            "rough_ok": fits(w, h) and sill < P[c + "max_sill_in"],
            "side_hinged": fits(w, h), "hung": fits(w, h / 2.0), "sliding": fits(w / 2.0, h),
        })
    return out


def escape_windows(apt: dict, P: dict) -> dict[str, dict]:
    """Each bedroom's escape window: the first of its windows whose rough opening clears 1031, and
    the ways of opening that could."""
    out = {}
    for r in apt["rooms"]["rooms"]:
        if r["use"] != "bedroom":
            continue
        ok = [w for w in escape_options(apt, r, P) if w["rough_ok"]]
        out[r["id"]] = ok[0] if ok else None
    return out


def _covered(rooms: list[dict], walls: list[dict]) -> float:
    return sum(_dx(x) * _dy(x) for x in rooms + walls)


def check(apt: dict, base: dict, P: dict) -> list[tuple[str, bool, str]]:
    res = []
    add = lambda label, ok, detail: res.append((label, bool(ok), detail))
    c = "systems.code."
    R = apt["rooms"]
    rooms, walls = R["rooms"], R["walls"]
    flats = by_flat(apt)

    # Addendum 2 is Addendum 1 plus the rooms and the annex, less the one stair window.
    gone = sorted({o["id"] for o in base["openings"]} - {o["id"] for o in apt["openings"]})
    added = sorted({o["id"] for o in apt["openings"]} - {o["id"] for o in base["openings"]})
    same = [o for o in apt["openings"] if o["id"] in {b["id"] for b in base["openings"]}]
    unchanged = all(o == next(b for b in base["openings"] if b["id"] == o["id"]) for o in same)
    add("Addendum 2 changes no opening but the stair window behind the annex",
        apt.get("revision") == REVISION and gone == ["1-stair/back/0"] and not added and unchanged
        and apt["parts"] == base["parts"] and apt["stair"] == base["stair"],
        f"removed {gone or 'none'}, added {added or 'none'}; parts and stair {'unchanged' if apt['parts'] == base['parts'] and apt['stair'] == base['stair'] else 'CHANGED'}")

    ids = [r["id"] for r in rooms] + [w["id"] for w in walls]
    add("every room and wall has its own id", len(ids) == len(set(ids)), f"{len(rooms)} rooms, {len(walls)} walls")

    # Coverage against pass 3b's envelope: rooms, walls and the plumbing wall's gap sum to the floor.
    gap_t = R["plumbing_gap_m"]
    worst = 0.0
    for f in apt["flats"]:
        name = f["name"]
        mine_w = [w for w in walls if w["id"].startswith(name + "/")]
        pw = next(w for w in mine_w if w["kind"] == "plumbing_wall")
        gap = gap_t * max(_dx(pw), _dy(pw))  # the air gap runs the plumbing wall's length
        worst = max(worst, abs(_covered(flats[name], mine_w) + gap - f["floor_m2"]))
    add("each flat's rooms and walls cover its floor (pass 3b's flat_envelope)", worst < 1e-6,
        f"worst difference {worst * 1e6:.3f} mm2 over {len(apt['flats'])} flats")

    # 1208.1 and 1208.3: habitable rooms.
    hab = [r for r in rooms if r["use"] in HABITABLE]
    narrow = [(r["id"], min(_dx(r), _dy(r)) / FT) for r in hab]
    lo = min(narrow, key=lambda t: t[1])
    add(f"habitable rooms at least {P[c + 'room.min_dimension_ft']:g} ft in plan (IBC 2021 1208.1)",
        lo[1] >= P[c + "room.min_dimension_ft"] - EPS, f"narrowest {lo[0]} at {lo[1]:.2f} ft")
    small = min(((r["id"], r["area_m2"] / FT2) for r in hab), key=lambda t: t[1])
    add(f"habitable rooms at least {P[c + 'room.habitable_min_ft2']:g} ft2 (1208.3)",
        small[1] >= P[c + "room.habitable_min_ft2"] - EPS, f"smallest {small[0]} at {small[1]:.1f} ft2")
    biggest = {n: max(r["area_m2"] for r in rs) / FT2 for n, rs in flats.items()}
    add(f"every flat has a room of at least {P[c + 'room.one_room_min_ft2']:g} ft2 (1208.3)",
        min(biggest.values()) >= P[c + "room.one_room_min_ft2"], f"the least flat's largest room {min(biggest.values()):.0f} ft2")

    # 1208.2: ceilings.
    serv = ("bath", "kitchen", "utility", "hall")
    low_hab = min((ceiling_in(apt, r, P), r["id"]) for r in rooms if r["flat"] and r["use"] not in serv)
    low_srv = min((ceiling_in(apt, r, P), r["id"]) for r in rooms if r["flat"] and r["use"] in serv)
    add(f"ceilings at least {P[c + 'room.min_ceiling_habitable_in']:g} in, {P[c + 'room.min_ceiling_service_in']:g} in in baths, "
        "kitchens, laundry and a flat's halls (1208.2)",
        low_hab[0] >= P[c + "room.min_ceiling_habitable_in"] and low_srv[0] >= P[c + "room.min_ceiling_service_in"],
        f"lowest {low_hab[0]:.1f} in ({low_hab[1]}), {low_srv[0]:.1f} in ({low_srv[1]}); no soffits yet (steps 3-4)")

    # Table 1020.3: the hall.
    halls = [(r["id"], min(_dx(r), _dy(r)) / IN) for r in rooms if r["flat"] and r["id"].endswith("/hall")]
    h = min(halls, key=lambda t: t[1])
    add(f"each flat's hall at least {P[c + 'corridor.within_unit_min_in']:g} in clear (IBC 2021 Table 1020.3)",
        h[1] >= P[c + "corridor.within_unit_min_in"] - EPS, f"narrowest {h[0]} at {h[1]:.1f} in")

    # 1208.1: the kitchen, a counter along the plumbing wall and the passage in front of it.
    k = min(((r["id"], _dx(r) / IN - P["systems.design.counter_depth_in"]) for r in rooms if r["use"] == "kitchen"),
            key=lambda t: t[1])
    add(f"each kitchen {P[c + 'room.kitchen_passage_in']:g} in clear past a {P['systems.design.counter_depth_in']:g} in counter (1208.1)",
        k[1] >= P[c + "room.kitchen_passage_in"], f"least {k[1]:.1f} in ({k[0]})")

    # 1031: escape openings.
    esc = escape_windows(apt, P)
    missing = [b for b, w in esc.items() if w is None]
    add("every bedroom has a window whose rough opening clears IBC 2021 1031.3 (5.7 ft2, 24 x 20 in, sill 44 in)",
        not missing and len(esc) == 2 * len(apt["flats"]), f"{len(esc)} bedrooms, {len(missing)} without" + (f": {missing}" if missing else ""))
    # The finding holds for every escape window, not on average: one that could serve hung or
    # sliding breaks it.
    found = [w for w in esc.values() if w]
    casement_only = all(w["side_hinged"] and not w["hung"] and not w["sliding"] for w in found)
    add("each escape window can clear 1031 only side-hinged (a casement): hung or sliding, it can't",
        bool(found) and casement_only,
        "half its height or half its width falls short of 1031.3.2; the window schedule must say casement for these")

    # The wet rooms stack and sit back to back.
    def plan(r):
        return (round(r["lo_m"][0], 6), round(r["lo_m"][1], 6), round(r["hi_m"][0], 6), round(r["hi_m"][1], 6))
    wet = {r["id"]: r for r in rooms if r["use"] in WET}
    stacked = all(plan(wet[f"{k}-{side}/{u}"]) == plan(wet[f"1-{side}/{u}"])
                  for k in (2, 3) for side in ("front-left", "front-right", "back-left", "back-right") for u in WET)
    D = apt["depth_m"]
    back = all(abs((D - wet[f"{k}-front-{s}/{u}"]["hi_m"][0]) - wet[f"{k}-back-{s}/{u}"]["lo_m"][0]) < EPS
               for k in (1, 2, 3) for s in ("left", "right") for u in WET)
    add("wet rooms stack floor over floor and sit back to back across the spine", stacked and back,
        f"{len(wet)} wet rooms: bath, utility closet and kitchen in every flat")

    # The plumbing wall stands clear of the party wall.
    spine = [p for p in apt["parts"] if p["id"].startswith("spine-")]
    # The gap across x between each plumbing wall and the spine wall alongside it (same storey,
    # overlapping in y), signed: negative where the two overlap.
    clear = min(max(s["lo_m"][0] - w["hi_m"][0], w["lo_m"][0] - s["hi_m"][0])
                for w in walls if w["kind"] == "plumbing_wall" for s in spine
                if s["storey"] == w["storey"] and s["lo_m"][1] < w["hi_m"][1] and w["lo_m"][1] < s["hi_m"][1])
    add("every plumbing wall stands clear of the party wall", clear >= gap_t - EPS,
        f"least gap {clear / IN:.2f} in")

    # The annex: two rooms, a door each, opening out.
    annex = [r for r in rooms if not r["flat"]]
    doors = R["annex"]["doors"]
    add("the annex has its two rooms, each with its own outside door",
        sorted(r["use"] for r in annex) == ["electrical", "mechanical"]
        and all(any(d["room"] == r["id"] for d in doors) for r in annex) and all(d["swing"] == "out" for d in doors),
        "; ".join(f"{r['id']} {r['area_m2'] / FT2:.0f} ft2" for r in annex) + "; sizes provisional until steps 4-5")
    return res


def typical_flat(apt: dict, P: dict, flat: str = "2-front-left") -> list[dict]:
    """The rows of one flat's room schedule."""
    esc = escape_windows(apt, P)
    rows = []
    for r in by_flat(apt)[flat]:
        rows.append({
            "room": r["id"].split("/")[1], "use": r["use"],
            "x_ft": _dx(r) / FT, "y_ft": _dy(r) / FT, "area_ft2": r["area_m2"] / FT2,
            "ceiling_in": ceiling_in(apt, r, P), "openings": r["openings"],
            "escape": esc[r["id"]]["id"] if r["id"] in esc and esc[r["id"]] else "",
        })
    return rows


def report(res: list[tuple[str, bool, str]]) -> str:
    return "\n".join(f"{'ok  ' if ok else 'FAIL'} {label}: {detail}" for label, ok, detail in res)


# ---- The plan sheet ----

USE_COLOR = {"bedroom": "#cfe0f3", "living": "#f3e6c8", "study": "#f3e6c8", "kitchen": "#bfe3d0", "bath": "#bfe3d0",
             "utility": "#bfe3d0", "hall": "#ecebe6", "entry": "#ecebe6", "mechanical": "#f6d2c4", "electrical": "#f2e3a0"}


def plan_figure(apt: dict, P: dict, path: Path, storey: int = 1) -> None:
    """The ground floor as built in Addendum 2: walls, the rooms by use, the plumbing walls, the
    openings (escape windows marked) and the annex; one flat's rooms labelled with their areas."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    from .figures import INK, INK2, MUTED, SURFACE

    def box(ax, lo, hi, **kw):
        # Plan: the building's length (y) across, its depth (x) down, in feet.
        ax.add_patch(Rectangle((lo[1] / FT, lo[0] / FT), (hi[1] - lo[1]) / FT, (hi[0] - lo[0]) / FT, **kw))

    R = apt["rooms"]
    esc = {w["id"] for w in escape_windows(apt, P).values() if w}
    fig, ax = plt.subplots(figsize=(11, 7.4), dpi=150, facecolor=SURFACE)
    for r in R["rooms"]:
        if r["storey"] == storey:
            box(ax, r["lo_m"], r["hi_m"], fc=USE_COLOR[r["use"]], ec="none")
    walls = [p for p in apt["parts"] if p["storey"] == storey and "wall" in p["kind"]]
    walls += [p for p in apt["stair"]["parts"] if p["storey"] == storey and "wall" in p["kind"]]
    for p in walls + [p for p in R["annex"]["parts"] if "wall" in p["kind"] or "partition" in p["kind"]]:
        box(ax, p["lo_m"], p["hi_m"], fc=INK, ec="none")
    for w in R["walls"]:
        if w["storey"] == storey:
            box(ax, w["lo_m"], w["hi_m"], fc="#1a7f5a" if w["kind"] == "plumbing_wall" else INK2, ec="none")
    doors = apt["stair"]["doors"] + R["annex"]["doors"]
    for o in apt["openings"] + doors:
        if o["storey"] != storey:
            continue
        c = "#d1495b" if o["id"] in esc else {"window": "#2a78d6", "patio_door": "#eb6834"}.get(o["kind"], "#8a5a2b")
        box(ax, o["lo_m"], o["hi_m"], fc=c, ec="none")
    for r in R["rooms"]:
        if r["storey"] == storey and (r["flat"] == f"{storey}-front-left" or not r["flat"]) and r["use"] not in ("hall",):
            cx, cy = (r["lo_m"][1] + r["hi_m"][1]) / 2 / FT, (r["lo_m"][0] + r["hi_m"][0]) / 2 / FT
            name = r["id"].split("/")[1].replace("-", " ")
            ax.text(cx, cy, f"{name}\n{r['area_m2'] / FT2:.0f} ft²", ha="center", va="center", fontsize=6.5, color=INK)
    sx = apt["stair"]["core_y_m"]
    ax.text((sx[0] + sx[1]) / 2 / FT, 14, "stair", ha="center", va="center", fontsize=7, color=MUTED, rotation=90)
    ax.set_xlim(-2, 102)
    ax.set_ylim(62, -2)
    ax.set_aspect("equal")
    ax.set_facecolor(SURFACE)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=7, length=0)
    ax.set_xlabel("ft along the building", fontsize=7.5, color=MUTED)
    ax.set_ylabel("ft from the front", fontsize=7.5, color=MUTED)
    ax.set_title("The walk-up's ground floor in Addendum 2: rooms, plumbing walls (green) and the service annex",
                 fontsize=9.5, color=INK, loc="left")
    fig.text(0.01, 0.015, "Blue: windows; red: each bedroom's escape window (a casement); orange: patio doors; brown: doors. "
             "Blue rooms sleep, cream live, green are wet (bath, utility, kitchen) and stack on every floor; the annex's mechanical "
             "and plumbing room (pink) and electrical room (yellow). Forge `rooms`, pass 3g step 1.",
             fontsize=6.5, color=INK2, wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
