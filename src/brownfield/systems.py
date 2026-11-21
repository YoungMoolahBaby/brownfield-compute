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
        raise SystemExit(f"no {path.relative_to(OUT_DIR.parent)}: run forge's `apartment-json "
                         f"{path.stem.removeprefix('apartment-')} ...` first (60 for Addendum 1's patio doors; Addendum 3 "
                         "also takes params/systems.yaml's addendum_3.ci_in)")
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
    """The rooms against the code, after the revision's own check against the one before it
    (`base`): Addendum 2 against Addendum 1, 3 against 2, 4 against 3, by `apt`'s revision."""
    head = {"addendum-3": check_addendum_3, "addendum-4": check_addendum_4}.get(
        apt.get("revision"), lambda a, b, _: check_addendum_2(a, b))(apt, base, P)
    return head + room_checks(apt, P)


def check_addendum_2(apt: dict, base: dict) -> list[tuple[str, bool, str]]:
    """Addendum 2 is Addendum 1 (`base`) plus the rooms and the annex, less the one stair window."""
    res = []
    add = lambda label, ok, detail: res.append((label, bool(ok), detail))
    gone = sorted({o["id"] for o in base["openings"]} - {o["id"] for o in apt["openings"]})
    added = sorted({o["id"] for o in apt["openings"]} - {o["id"] for o in base["openings"]})
    same = [o for o in apt["openings"] if o["id"] in {b["id"] for b in base["openings"]}]
    unchanged = all(o == next(b for b in base["openings"] if b["id"] == o["id"]) for o in same)
    add("Addendum 2 changes no opening but the stair window behind the annex",
        apt.get("revision") == REVISION and gone == ["1-stair/back/0"] and not added and unchanged
        and apt["parts"] == base["parts"] and apt["stair"] == base["stair"],
        f"removed {gone or 'none'}, added {added or 'none'}; parts and stair {'unchanged' if apt['parts'] == base['parts'] and apt['stair'] == base['stair'] else 'CHANGED'}")
    return res


def check_addendum_3(apt: dict, base: dict, P: dict) -> list[tuple[str, bool, str]]:
    """Addendum 3 is Addendum 2 (`base`) with the exterior walls (the annex's with them) thickened
    inward by their continuous insulation and nothing else: the building's outside, every opening
    (where it is along its wall, its size, its sill) and the rooms' plan unchanged but where they
    meet an outside wall."""
    res = []
    add = lambda label, ok, detail: res.append((label, bool(ok), detail))  # noqa: E731
    ci = P["systems.addendum_3.ci_in"] * IN
    grown = apt["ext_t_m"] - base["ext_t_m"]
    keys = ("id", "kind", "storey", "flat", "face", "index", "width_m", "height_m", "sill_m", "along_m")
    same_openings = [{k: o[k] for k in keys} for o in apt["openings"]] == [{k: o[k] for k in keys} for o in base["openings"]]
    outer = all(abs(a[k][i] - b[k][i]) < EPS for a, b in zip(apt["parts"], base["parts"]) if a["kind"] == "exterior_wall"
                for k, i in (("lo_m", 0), ("lo_m", 1), ("hi_m", 0), ("hi_m", 1)) if
                (k == "lo_m" and abs(b[k][i]) < EPS) or (k == "hi_m" and abs(b[k][i] - (apt["depth_m"] if i == 0 else apt["length_m"])) < EPS))
    add("Addendum 3 thickens the exterior walls by their continuous insulation, inward, and changes no opening",
        apt.get("revision") == "addendum-3" and abs(grown - ci) < EPS and abs(apt.get("continuous_insulation_m", 0) - ci) < EPS
        and same_openings and outer and (apt["depth_m"], apt["length_m"]) == (base["depth_m"], base["length_m"]),
        f"walls {base['ext_t_m'] / IN:g} -> {apt['ext_t_m'] / IN:g} in (continuous insulation {ci / IN:g} in); "
        f"outside {apt['length_m'] / FT:g} x {apt['depth_m'] / FT:g} ft unchanged; openings {'unchanged' if same_openings else 'CHANGED'}")
    return res


def addendum_4(apt3: dict, P: dict) -> dict:
    """Addendum 4's model: Addendum 3's building with its glass specified: `glass_shgc`, the most
    solar heat gain the windows and patio doors may have (`systems.addendum_4.shgc_max`), and
    `glass_u`, their most U-factor (`window_u_max`, ENERGY STAR's Northern zone). Nothing is drawn
    differently, so it is made here, not in forge."""
    out = dict(apt3)
    out["revision"] = "addendum-4"
    out["glass_shgc"] = P["systems.addendum_4.shgc_max"]
    out["glass_u"] = P["systems.addendum_4.window_u_max"]
    out["source"] = apt3.get("source", "") + "; Addendum 4: the glass (brownfield systems)"
    return out


def write_addendum_4(P: dict) -> Path | None:
    """out/pass3/apartment-addendum-4.json from Addendum 3's, if forge has written that."""
    src = OUT_DIR / "pass3" / "apartment-addendum-3.json"
    if not src.exists():
        return None
    path = OUT_DIR / "pass3" / "apartment-addendum-4.json"
    path.write_text(json.dumps(addendum_4(json.loads(src.read_text(encoding="utf-8")), P), indent=1) + "\n", encoding="utf-8")
    return path


def latest_model() -> Path:
    """The latest revision's model that has been written: Addendum 4's, else 3's."""
    for rev in ("addendum-4", "addendum-3"):
        path = OUT_DIR / "pass3" / f"apartment-{rev}.json"
        if path.exists():
            return path
    return PATH


def check_addendum_4(apt: dict, base: dict, P: dict) -> list[tuple[str, bool, str]]:
    """Addendum 4 is Addendum 3 (`base`) with the glass specified, and nothing else."""
    keys = ("revision", "glass_shgc", "glass_u", "source")
    rest = {k: v for k, v in apt.items() if k not in keys}
    rest0 = {k: v for k, v in base.items() if k not in keys}
    a = "systems.addendum_4."
    ok = (apt.get("revision") == "addendum-4" and abs(apt.get("glass_shgc", -1) - P[a + "shgc_max"]) < 1e-12
          and abs(apt.get("glass_u", -1) - P[a + "window_u_max"]) < 1e-12 and rest == rest0)
    return [("Addendum 4 specifies the glass and changes nothing drawn", ok,
             f"SHGC at most {apt.get('glass_shgc')}, U at most {apt.get('glass_u')}; "
             f"the building {'unchanged' if rest == rest0 else 'CHANGED'}")]


def room_checks(apt: dict, P: dict) -> list[tuple[str, bool, str]]:
    """The rooms against IBC 2021 and the layout's own promises (see the module's docstring)."""
    res = []
    add = lambda label, ok, detail: res.append((label, bool(ok), detail))  # noqa: E731
    c = "systems.code."
    R = apt["rooms"]
    rooms, walls = R["rooms"], R["walls"]
    flats = by_flat(apt)

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
    rev = (apt.get("revision") or "").replace("addendum-", "Addendum ")
    ax.set_title(f"The walk-up's ground floor in {rev}: rooms, plumbing walls (green) and the service annex",
                 fontsize=9.5, color=INK, loc="left")
    fig.text(0.01, 0.015, "Blue: windows; red: each bedroom's escape window (a casement); orange: patio doors; brown: doors. "
             "Blue rooms sleep, cream live, green are wet (bath, utility, kitchen) and stack on every floor; the annex's mechanical "
             "and plumbing room (pink) and electrical room (yellow). Forge `rooms`, pass 3g step 1.",
             fontsize=6.5, color=INK2, wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


# ---- Addenda 2 and 3 in the bid set: the IFC, checked and diffed against the addendum before ----

# {revision: (the model before it, its own model)}, under out/pass3/.
REVISIONS = {"addendum-2": ("apartment-addendum-1.json", "apartment-addendum-2.json"),
             "addendum-3": ("apartment-addendum-2.json", "apartment-addendum-3.json"),
             "addendum-4": ("apartment-addendum-3.json", "apartment-addendum-4.json")}
IFC_OUT = OUT_DIR / "pass3" / "bidset" / REVISION
# RFI 002 (made up), which Addendum 3 answers: asked when the walls' shortfall was confirmed
# (08:45 Pacific, D28), answered when Addendum 3 went out (ISSUED[3]). UTC, as BCF keeps it.
RFI_002_ASKED = "2026-11-21T16:45:00"
RFI_002_ANSWER_AFTER_MIN = 30
# When each addendum went out (D29): Addendum 1 when it was first published (git 8a9d200), Addendum
# 2 when it was produced and checked (git 2f6623f), Addenda 3 and 4 when they were published (4 with
# ENERGY STAR's glass, before it went out).
ISSUED = {1: "2026-11-19T23:29:07-08:00", 2: "2026-11-21T08:43:25-08:00", 3: "2026-11-21T09:15:00-08:00",
          4: "2026-11-21T11:41:33-08:00"}
TITLES = {1: "The patio doors: their glass and their width",
          2: "The rooms, the plumbing walls and the service annex",
          3: "The envelope to Pennsylvania's 2021 energy code",
          4: "The glass: ENERGY STAR's Northern zone, at a solar heat gain that sizes the cooling"}
PUBLISHED = OUT_DIR.parent / "docs" / "pass3" / "bidset"


def ifc_out(revision: str) -> Path:
    return OUT_DIR / "pass3" / "bidset" / revision


def rfi_002_words(apt_before: dict, params: dict) -> dict:
    """RFI 002 and Addendum 3's items, from the params (the code's numbers, the insulation chosen)."""
    v = lambda k: params[k].value  # noqa: E731
    e, a = "systems.code.envelope.", "systems.addendum_3."
    drawn = v("pass3.envelope.wall_u")
    question = (f"The exterior wall type is 2x6 studs with R-{v(a + 'cavity_r'):g} in the cavities, U-{drawn:.3f}: the 2018 IECC's "
                f"zone 5 wall. Pennsylvania's UCC took up the 2021 IECC on 2026-01-01 (55 Pa.B. 7701). Its zone 5 frame wall "
                f"is U-{v(e + 'wall_u_max'):.3f} (R-23, 13 + 7.5 or 20 + 3.8), and a heated slab needs R-{v(e + 'heated_slab_under_r'):g} "
                "under its full area besides its edge insulation. The ground floor's slab carries the radiant tubing. Which "
                "code do we price to?")
    items = [
        f"Item 1 (walls): the exterior walls, and the service annex's, take R-{v(a + 'ci_r'):g} continuous insulation "
        f"({v(a + 'ci_in'):g} in. of board outboard of the sheathing) over the R-{v(a + 'cavity_r'):g} cavities: U-{v(a + 'wall_u'):.3f}, "
        f"the 2021 IECC's (Table R402.1.3, 20 + 3.8). The walls thicken inward from "
        f"{apt_before['ext_t_m'] / IN:g} to {apt_before['ext_t_m'] / IN + v(a + 'ci_in'):g} in.; the building's outside stays "
        f"{apt_before['length_m'] / FT:g} x {apt_before['depth_m'] / FT:g} ft, so the rooms along the outside walls lose "
        f"{v(a + 'ci_in'):g} in. and the stair, set against the back wall, moves with it.",
        f"Item 2 (slabs): the ground floor's heated slab sits on R-{v(a + 'slab_under_r'):g} under its full area, with "
        f"R-{v(a + 'slab_edge_r'):g} at its edge to {v(a + 'slab_edge_depth_ft'):g} ft; the annex's slab takes the same edge "
        "insulation (Table R402.1.3 and its footnote d).",
        "The windows (U-0.30) and the roof (R-49) already meet the 2021 code: no change.",
    ]
    return {"title": "RFI 002: which energy code do the exterior walls meet?", "question": question,
            "answer": "Answered by Addendum 3: the 2021 IECC, as Pennsylvania adopts it. " + " ".join(items[:2]),
            "items": items}


def ifc_run(params: dict, revision: str = REVISION) -> dict:
    """An addendum as a reviewed change, as `brownfield addendum` ran Addendum 1: its model checked
    first (`check`: the revision itself, then the rooms); then the model before it and the addendum
    written as IFC (Addendum 1's tempered patio doors carried on), the element diff between them,
    both readers and the IDS on the addendum, a second export compared byte for byte, and the
    schedule, elevations and quantities regenerated, with what changed in each. Addendum 3 also
    writes RFI 002 (BCF), which it answers. Written to `ifc_out(revision)`; the published bid set
    is left alone."""
    import tempfile

    from . import addendum, bidset, stair
    from .params import values

    before, mine = REVISIONS[revision]
    raw1 = json.loads((OUT_DIR / "pass3" / before).read_text(encoding="utf-8"))
    raw2 = load(OUT_DIR / "pass3" / mine)
    failing = [label for label, ok, _ in check(raw2, raw1, values(params)) if not ok]
    if failing:
        raise SystemExit(f"{revision}'s model fails its checks (run `brownfield systems`): " + "; ".join(failing))
    apt1, frame = bidset.load(before)
    apt2, _ = bidset.load(mine)
    out = ifc_out(revision)
    base, rev = out / "base.ifc", out / "apartment.ifc"
    bidset.write_ifc(apt1, frame, params, base, spec=addendum.SPEC)
    bidset.write_ifc(apt2, frame, params, rev, spec=addendum.SPEC)
    words, rfi = None, []
    if revision == "addendum-3":
        import ifcopenshell
        import ifcopenshell.util.element
        from datetime import timedelta

        words = rfi_002_words(raw1, params)
        f0 = ifcopenshell.open(str(base))
        walls = sorted(w.GlobalId for w in f0.by_type("IfcWall")
                       if (ifcopenshell.util.element.get_pset(w, "Pset_WallCommon") or {}).get("IsExternal"))
        rfi = addendum.write_rfi(base, out / "rfi-002.bcf", words, guids=walls, asked=RFI_002_ASKED,
                                 answered_after=timedelta(minutes=RFI_002_ANSWER_AFTER_MIN), key="rfi-002")
    if revision == "addendum-4":
        words = addendum_4_words(params)
    diff = addendum.element_diff(base, rev)
    checks = bidset.check(rev, apt2, params)
    with tempfile.TemporaryDirectory() as tmp:
        again = Path(tmp) / "apartment.ifc"
        bidset.write_ifc(apt2, frame, params, again, spec=addendum.SPEC)
        checks.append(("a second export is byte-for-byte the same file", again.read_bytes() == rev.read_bytes(),
                       f"{len(bidset.body_text(rev)):,} lines"))
    why = bidset.webifc_status()
    second = bidset.check_webifc(rev, apt2, params) if why is None else []
    doc = bidset.write_ids(params, out / "bidset.ids")
    ids1, ids2 = bidset.run_ids(doc, base), bidset.run_ids(doc, rev)
    ids_changes = [f"{b['name']}: {a['passed']} of {a['applicable']} -> {b['passed']} of {b['applicable']}"
                   for a, b in zip(ids1, ids2) if (a["passed"], a["applicable"]) != (b["passed"], b["applicable"])]
    with tempfile.TemporaryDirectory() as tmp:
        d1 = bidset.write_drawings(base, Path(tmp))
    d2 = bidset.write_drawings(rev, out / "drawings")
    h1, h2 = bidset.safety_glazing(apt1, params), bidset.safety_glazing(apt2, params)
    st = stair.check(apt2, params)
    R = raw2["rooms"]
    return {
        "revision": revision, "words": words, "rfi_guids": rfi,
        "diff": diff, "checks": checks, "second": second, "second_status": why, "ids_changes": ids_changes,
        "schedule_changes": addendum.schedule_changes(d1["schedule"], d2["schedule"]),
        "hazards": (len(h1), len(h2)), "removed": sorted(set(h1) - set(h2)),
        "quantities": (d1["quantities"]["total"], d2["quantities"]["total"]),
        "stair": (sum(ok for _, ok, _ in st), len(st)),
        "rooms": len(R["rooms"]), "partitions": sum(w["kind"] == "partition" for w in R["walls"]),
        "plumbing_walls": sum(w["kind"] == "plumbing_wall" for w in R["walls"]),
        "annex_marks": {u["name"]: u["mark"] for u in d2["read"]["units"] if u["face"] == "annex"},
        "escapes": len(bidset.escape_windows(raw2, params)),
        "escape_marks": sorted({u["mark"] for u in d2["read"]["units"]
                                if (u["psets"].get("Pset_WindowCommon") or {}).get("FireExit") is True}),
        "written": [out / "bidset.ids", base, rev, *([out / "rfi-002.bcf"] if rfi else []), *d2["written"]],
    }


def ifc_report(r: dict) -> str:
    """An addendum as a reviewed change, in plain text."""
    from . import addendum, bidset

    (q1, q2), (h1, h2) = r["quantities"], r["hazards"]
    second = (r["second"] if r["second_status"] is None else
              [("the second reader (web-ifc) ran", False, f"it didn't: {r['second_status']}")])
    if r["revision"] == "addendum-3":
        w = r["words"]
        head = [w["title"], f"  asked: {w['question']}", f"  points at {len(r['rfi_guids'])} exterior walls by GlobalId",
                f"  answered: {w['answer']}", "",
                "Addendum 3 (made up, pass 3g, D28): the envelope to Pennsylvania's 2021 energy code", "",
                *(f"  {x}" for x in w["items"]),
                f"  The stair's checks after the move: {r['stair'][0]} of {r['stair'][1]} pass."]
        before = "Addendum 2"
    elif r["revision"] == "addendum-4":
        head = ["Addendum 4 (made up, pass 3g step 3c, D28): the glass: ENERGY STAR's Northern zone, at a solar heat gain "
                "that sizes the cooling", "",
                *(f"  {x}" for x in r["words"]["items"])]
        before = "Addendum 3"
    else:
        head = ["Addendum 2 (made up, pass 3g step 1, D28): the rooms, the plumbing walls and the service annex", "",
                *(f"  {x}" for x in addendum_2_items(r))]
        before = "Addendum 1"
    lines = [*head, "",
             f"What changed (against {before}):", *(f"  {x}" for x in addendum.diff_summary(r["diff"])), "",
             "Checks on the revision:", *(f"  {x}" for x in bidset.report(r["checks"] + second).splitlines()), "",
             "The checklist (IDS), where it moved:", *(f"  {x}" for x in r["ids_changes"] or ["(nowhere)"]), "",
             "The schedule, where it moved:", *(f"  {x}" for x in r["schedule_changes"] or ["(nowhere)"]), "",
             f"Openings in the exterior walls (the annex's doors aside): {q1['openings_m2']:.1f} -> {q2['openings_m2']:.1f} m2 "
             f"({q1['openings_m2'] / bidset.FT2:,.0f} -> {q2['openings_m2'] / bidset.FT2:,.0f} ft2)."]
    return "\n".join(lines)


def addendum_4_words(params: dict) -> dict:
    """Addendum 4's items, from the params (the glass's limits, the units it lets serve)."""
    v = lambda k: params[k].value  # noqa: E731
    a = "systems.addendum_4."
    return {"items": [
        f"Item 1 (glass): every window and patio door is rated, whole unit, at a U-factor of at most {v(a + 'window_u_max'):.2f} "
        f"Btu/h ft2 F (NFRC 100; the code asks {v('pass3.envelope.window_u'):.2f}), a solar heat gain coefficient from "
        f"{v(a + 'shgc_min'):.2f} to {v(a + 'shgc_max'):.2f} (NFRC 200) and air leakage of at most {v(a + 'air_leakage_cfm_ft2'):g} "
        "cfm/ft2: ENERGY STAR v7's Northern zone, which all of western Pennsylvania is in. The window and door schedule now "
        "carries the U-factor and the SHGC (Pset_DoorWindowGlazingType.SolarHeatGainTransmittance).",
        f"Why: the flats' cooling (step 3c). The schedule gave no SHGC, and the cooling design had assumed "
        f"{v('systems.design.shgc'):g}: at that, no 1-ton unit covers a flat; at this glass one does. The winter sun the "
        "glass gives up is heat the data center's loop supplies anyway.",
        "Why the U-factor: ENERGY STAR, chosen beyond the code; it lowers the flats' heat, and the water their floors need.",
        "No drawing changes; no opening moves or resizes.",
    ]}


def addendum_2_items(r: dict) -> list[str]:
    """Addendum 2's items, from its run (`ifc_run`)."""
    (h1, h2) = r["hazards"]
    am = r["annex_marks"]
    mech, elec = am.get("annex-mechanical/left/0", "(missing)"), am.get("annex-electrical/back/0", "(missing)")
    return [
            f"1. Every room as a space (IfcSpace), {r['rooms']} in all: its use, the openings in its walls and its net "
            "floor area, from forge `rooms` (pass 3g step 1).",
            f"2. The flats' walls: {r['partitions']} partitions and {r['plumbing_walls']} plumbing walls (IFC's PLUMBINGWALL), "
            "each plumbing wall 1/2 in. clear of the party wall.",
            f"3. The service annex behind the stair: its walls, slab and roof; a mechanical and plumbing room (door {mech}) "
            f"and an electrical room (door {elec}), each with its own outside door.",
            f"4. The ground floor's back stair window removed ({', '.join(r['removed']) or 'none'} was safety glazed): the "
            f"annex covers it. Safety glazing goes {h1} -> {h2} openings.",
            f"5. Each bedroom's escape window named ({r['escapes']}): its own type ({', '.join(r['escape_marks'])}), side-hinged "
            "(a casement), since hung or sliding a window of their size can't clear IBC 2021 1031; every window now says "
            "whether it is one (Pset_WindowCommon.FireExit).",
    ]


# ---- Publishing the addenda (D29): the plan room's files ----

def changes(old: Path, new: Path) -> dict:
    """What an addendum changed, for the viewer to mark: the elements added and changed by
    GlobalId, those deleted with their names, and the rooms resized, by name (`element_diff`)."""
    import ifcopenshell

    from . import addendum

    d = addendum.element_diff(old, new)
    f0 = ifcopenshell.open(str(old))
    gone = [{"gid": g, "name": f0.by_guid(g).Name, "cls": f0.by_guid(g).is_a()} for g in d["deleted"]]
    return {"added": d["added"], "changed": sorted(d["changed"]), "deleted": gone,
            "rooms_resized": d["spaces"]["resized"], "rooms_added": d["spaces"]["added"],
            "rooms_added_names": d["spaces"]["added_names"],
            "openings_resized": d["openings_resized"]}


def publish(params: dict, runs: dict[str, dict], to: Path = PUBLISHED) -> list[Path]:
    """Addenda 2 and 3 into the published bid set, with the manifest the plan room and the viewer
    read (`addenda.json`) and what each addendum changed (`changes-addendum-N.json`), Addendum 1's
    included. Only from runs whose every check passed (both readers'), and only Addenda 2 and 3's
    own files are written; the bid set and Addendum 1's files are left as they are."""
    import shutil

    from . import addendum, bidset

    for rev in ("addendum-2", "addendum-3", "addendum-4"):
        r = runs.get(rev)
        if r is None or r["second_status"] or not all(ok for _, ok, _ in r["checks"] + r["second"]):
            raise SystemExit(f"won't publish: {rev} didn't run, or a check failed")
    written = []
    for n in (2, 3, 4):
        rev, out = f"addendum-{n}", ifc_out(f"addendum-{n}")
        for src, dst in ((out / "apartment.ifc", to / f"apartment-{rev}.ifc"), (out / f"{rev}.md", to / f"{rev}.md")):
            shutil.copyfile(src, dst)
            written.append(dst)
        if (to / f"drawings-{rev}").exists():
            shutil.rmtree(to / f"drawings-{rev}")
        shutil.copytree(out / "drawings", to / f"drawings-{rev}")
        written.append(to / f"drawings-{rev}")
    shutil.copyfile(ifc_out("addendum-3") / "rfi-002.bcf", to / "rfi-002.bcf")
    written.append(to / "rfi-002.bcf")
    models = {0: "apartment.ifc", **{n: f"apartment-addendum-{n}.ifc" for n in (1, 2, 3, 4)}}
    for n in (1, 2, 3, 4):
        path = to / f"changes-addendum-{n}.json"
        path.write_text(json.dumps(changes(to / models[n - 1], to / models[n]), indent=1) + "\n", encoding="utf-8")
        written.append(path)
    # The frame of the latest addendum's building (forge `framing-json addendum-3 ...`), checked.
    from . import framingifc

    frame = framingifc.load("addendum-3")
    fpath = ifc_out("addendum-3") / "framing.ifc"
    framingifc.write(frame, fpath)
    bad = [label for label, ok, _ in framingifc.check(fpath, frame) if not ok]
    if bad:
        raise SystemExit(f"won't publish the frame: {bad}")
    shutil.copyfile(fpath, to / "framing-addendum-3.ifc")
    written.append(to / "framing-addendum-3.ifc")
    apt0, _ = bidset.load()
    apt1, _ = bidset.load("apartment-addendum-1.json")
    items = {1: addendum.words(apt0, apt1, params)["items"], 2: addendum_2_items(runs["addendum-2"]),
             3: runs["addendum-3"]["words"]["items"], 4: runs["addendum-4"]["words"]["items"]}
    files = {
        1: [("addendum-1.pdf", "The addendum: its narrative and the revised sheets, changes clouded"),
            ("addendum-1-diff.md", "What changed, element by element"),
            ("apartment-addendum-1.ifc", "The revised model, IFC4"),
            ("drawings-addendum-1/schedule.csv", "The revised window and door schedule"),
            ("rfi-001.bcf", "RFI 001, the question it answers (BCF 3.0)")],
        2: [("addendum-2.md", "The addendum: its items, what changed and the checks"),
            ("apartment-addendum-2.ifc", "The revised model, IFC4, with the rooms"),
            ("drawings-addendum-2/schedule.csv", "The revised window and door schedule"),
            ("drawings-addendum-2/openings.csv", "Every window and door")],
        3: [("addendum-3.md", "The addendum: its items, what changed and the checks"),
            ("apartment-addendum-3.ifc", "The revised model, IFC4"),
            ("drawings-addendum-3/schedule.csv", "The window and door schedule (unchanged)"),
            ("rfi-002.bcf", "RFI 002, the question it answers (BCF 3.0)")],
        4: [("addendum-4.md", "The addendum: its item, what changed and the checks"),
            ("apartment-addendum-4.ifc", "The revised model, IFC4, the glass's U-factor and SHGC on its types"),
            ("drawings-addendum-4/schedule.csv", "The revised window and door schedule, with the glass's U-factor and SHGC")],
    }
    manifest = {"note": "Made up, from the brownfield-compute study: not a real project, nothing is out to bid.",
                "framing": {"model": "framing-addendum-3.ifc", "revision": "addendum-3", "members": len(frame["members"]),
                            "note": "pass 3b's wood frame on Addendum 3's building; the flats' partitions and plumbing "
                                    "walls and the service annex aren't framed yet (D28 step 7)"},
                "addenda": [{"number": n, "title": TITLES[n], "issued": ISSUED[n], "items": items[n],
                             "model": models[n], "changes": f"changes-addendum-{n}.json",
                             "rfi": {1: "rfi-001.bcf", 2: None, 3: "rfi-002.bcf", 4: None}[n],
                             "files": [{"path": f, "label": label} for f, label in files[n]]} for n in (1, 2, 3, 4)]}
    path = to / "addenda.json"
    path.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    written.append(path)
    missing = [f["path"] for a in manifest["addenda"] for f in a["files"] if not (to / f["path"]).exists()]
    if missing:
        raise SystemExit(f"addenda.json names files that aren't published: {missing}")
    return written
