"""Pass 3g step 7b (D28): the services routed through the frame.

`brownfield routes --requests` writes `out/pass3/route-requests.json`: one request per service run,
its size, its root and terminals, and the zones it may run in, from 7a's placements
(`routing.placements`) and steps 3-6's sizes. forge's `routes-json` routes them through
Addendum 5's frame (`forge/src/routing.rs`: A* on a voxel grid, holes only where APA's chart and
IBC 2308 allow and APA's rules 6 and 11 keep them apart, drains falling and vents rising by their
slopes) and writes `out/pass3/routes.json`; `brownfield routes` reads it back and checks it
(`routecheck`).

The zones say where each kind of service may run:
- **a flat's ceiling cavity** (between the joists over it): sprinklers, branch circuits, the
  flat's water and vent headers, the manifold's tails, and the drains of the flat above; all but
  the verticals kept off the strip right over the plumbing wall (`over_wall`);
- **its soffits** (under the rated ceiling): the ERV's and mini-split's ducts, the line set, the
  condensate; joined across the partitions that stop under them;
- **the plumbing wall's stud cavity** (5/8 in. off the studs' faces, IBC 2308.5.10): only straight
  up and down, each in a stud bay that is a joist bay: the supplies from the ceiling, the vents to
  it, the drains through the floor into the cavity below;
- **under the slab** (2 in. voxels): the mains, feeders, fire main and building drain;
- **the stair's ceiling cavity:** the sprinkler riser's arms into the flats (IBC 1023.5);
- **the roof:** the line sets from their riser to the outdoor units.

The pinned services (7a's risers and stacks, the feeder conduits, the water closets' bends, the fire
riser) and the equipment are obstacles; a request may touch only what it is attached to.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from . import OUT_DIR
from .plumbing import LOOP_END  # where each flat's hot-water loop ends and its return starts (Addendum 7)
from .routing import FRAME, FT, IN, annex_drops, ceiling_z, column, placements, soffit_spans
from .systems import by_flat

# Each design's requests and routes: `designs.paths` (the network design's are out/pass3/route-requests.json
# and routes.json, as they always were).
R = "systems.routing."


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _box(lo, hi) -> dict:
    return {"lo": [min(a, b) for a, b in zip(lo, hi)], "hi": [max(a, b) for a, b in zip(lo, hi)]}


def _schedule() -> dict:
    return json.loads((OUT_DIR / "pass3" / "frame.json").read_text(encoding="utf-8"))


# ---- The zones ----

def flat_xy(apt: dict, name: str) -> tuple[list[float], list[float]]:
    """A flat's inside in plan: its rooms' and walls' extent (m)."""
    rs = by_flat(apt)[name] + [w for w in apt["rooms"]["walls"] if w["id"].startswith(name + "/")]
    return ([min(r["lo_m"][i] for r in rs) for i in range(2)], [max(r["hi_m"][i] for r in rs) for i in range(2)])


def storey_of(name: str) -> int:
    return int(name.split("-", 1)[0])


def cavity(apt: dict, name: str) -> dict:
    """The joists' space over a flat: its plan, from the joists' underside to their top."""
    s = _schedule()
    k = storey_of(name)
    z0 = ceiling_z(apt, k)
    depth = (s["floor_joist"] if k < apt["storeys"] else s["roof_joist"])["depth_mm"] / 1000
    lo, hi = flat_xy(apt, name)
    return _box([lo[0], lo[1], z0], [hi[0], hi[1], z0 + depth])


def below(apt: dict, name: str) -> str | None:
    """The flat under this one, or None on the ground floor."""
    k = storey_of(name)
    return f"{k - 1}-{column(name)}" if k > 1 else None


def slab_zone(apt: dict, p: dict) -> list[dict]:
    """Under the slab, inside the stem walls, the building's and the annex's, and through the
    building's back stem wall between them (a sleeve), at the trench depths."""
    z0, z1 = -p[R + "under_slab_bottom_in"] * IN, -p[R + "under_slab_top_in"] * IN
    stem = 8 * IN
    w, length = apt["depth_m"], apt["length_m"]
    annex = {x["id"]: x for x in apt["rooms"]["annex"]["parts"]}
    a0, a1 = annex["annex-left"]["lo_m"][1], annex["annex-right"]["hi_m"][1]
    ax1 = annex["annex-back"]["hi_m"][0]
    return [_box([stem, stem, z0], [w - stem, length - stem, z1]),
            _box([w - stem, a0 + stem, z0], [ax1 - stem, a1 - stem, z1])]


def wall_cavity(apt: dict, frame: dict, wall: dict, p: dict, z0: float | None = None, z1: float | None = None,
                y0: float | None = None, y1: float | None = None, edge: bool = True) -> dict:
    """A wall's stud cavity on its storey: its studs' depth less 5/8 in. each side (IBC 2308.5.10:
    a bored hole's edge 5/8 in. from the stud's), its length, from the floor to the joists over it
    (its plates included: crossed up through them). With `edge` False the studs' whole depth: for
    a pipe whose insulation stops at each member it passes (IECC C404.4), insulated in the bay and
    bare through the plates (cut plates strapped, IBC 2308.5.8); a stud it bores is still held to
    the 5/8 in. by `routecheck`."""
    from .routing import _bounds

    along = 1 if wall["hi_m"][1] - wall["lo_m"][1] > wall["hi_m"][0] - wall["lo_m"][0] else 0
    c = 1 - along
    studs = [_bounds(m) for m in frame["members"] if m["storey"] == wall["storey"] and m["kind"] == "studs"
             and wall["lo_m"][c] - 1e-6 <= _bounds(m)[0][c] and _bounds(m)[1][c] <= wall["hi_m"][c] + 1e-6
             and wall["lo_m"][along] - 1e-6 <= _bounds(m)[0][along] <= wall["hi_m"][along]]
    s0, s1 = studs[0][0][c], studs[0][1][c]
    e = p[R + "stud_edge_in"] * IN if edge else 0.0
    lo, hi = [0.0] * 3, [0.0] * 3
    lo[c], hi[c] = s0 + e, s1 - e
    lo[along], hi[along] = (wall["lo_m"][along] if y0 is None else y0), (wall["hi_m"][along] if y1 is None else y1)
    lo[2] = wall["lo_m"][2] if z0 is None else z0
    hi[2] = ceiling_z(apt, wall["storey"]) if z1 is None else z1
    return _box(lo, hi)


def soffit_zones(apt: dict, name: str, sf: list[dict]) -> list[dict]:
    """A flat's soffits, and the partitions' tops between them (the partitions stop under them)."""
    mine = [x for x in sf if x["flat"] == name]
    out = [_box(x["lo"], x["hi"]) for x in mine]
    z0, z1 = min(x["lo"][2] for x in mine), max(x["hi"][2] for x in mine)
    for w in (w for w in apt["rooms"]["walls"] if w["id"].startswith(name + "/") and w["kind"] == "partition"):
        along = 1 if w["hi_m"][1] - w["lo_m"][1] > w["hi_m"][0] - w["lo_m"][0] else 0
        for u0, u1 in soffit_spans(w, mine):
            lo, hi = list(w["lo_m"]), list(w["hi_m"])
            lo[along], hi[along], lo[2], hi[2] = u0, u1, z0, z1
            out.append(_box(lo, hi))
    return out


def over_wall(apt: dict, name: str, keep: list[tuple[float, float]]) -> list[dict]:
    """The joists' space directly over a flat's plumbing wall, less the spans `keep` (y0, y1): every
    vertical service in the wall comes up through it, so a run along the wall there would close
    the others' way. Each request takes it as blocks, all but the spans where it goes up or down."""
    from .routing import _free

    w = next(x for x in apt["rooms"]["walls"] if x["id"] == f"{name}/plumbing-wall")
    cv = cavity(apt, name)
    # Forge blocks every voxel a box touches, and opens a zone's voxels by their centres: each kept
    # span one voxel wider, so the zone's edge, not the block's, governs.
    e = 0.0254
    spans = _free([(w["lo_m"][1] - 0.15, w["hi_m"][1] + 0.15)], sorted((a - e, b + e) for a, b in keep))
    return [_box([w["lo_m"][0], a, cv["lo"][2]], [w["hi_m"][0], b, cv["hi"][2]]) for a, b in spans if b - a > 1e-4]


def wall_entry(wall_face_x: float, into: float, y: float, z0: float, z1: float, half: float, depth: float) -> dict:
    """A short way through a wall's room-side face (its gypsum) into its cavity, at y."""
    return _box([wall_face_x + into * 0.01, y - half, z0], [wall_face_x - into * depth, y + half, z1])


# ---- The requests ----

def requests(apt: dict, p: dict) -> dict:
    """Every run to route, with the rules and obstacles forge needs."""
    from .electrical import conduit_for, feeders, flat_circuits
    from .fire import cpvc, layout, riser_xy
    from .hvac import cooling_ducts, ventilation_ducts
    from .routing import load_frame

    frame = load_frame(apt, p)
    d = placements(apt, p)
    fx, vs, ch, sf, terms, units, eq, plant = (d[k] for k in ("fixtures", "verticals", "chase", "soffits", "terminations", "units",
                                                              "equipment", "plant"))
    sched = _schedule()
    roof_top = max(x["hi_m"][2] for x in apt["parts"] if x["kind"] == "roof")
    clear, hole = p[R + "riser_gap_in"] * IN, p[R + "hole_clear_in"] * IN
    v1, v2, vw = p[R + "voxel_in"] * IN, p[R + "slab_voxel_in"] * IN, p[R + "wall_voxel_in"] * IN
    vh, band = p[R + "hot_voxel_in"] * IN, p[R + "hot_band_in"] * IN
    wall_clear, cable_clear = p[R + "wall_clear_in"] * IN, p[R + "cable_clear_in"] * IN
    # Under the slab, each kind of service at its own depth: the ground floor's drains just under it,
    # the feeders, the mains, the building drain lowest (it falls to the sewer).
    zt, zb = -p[R + "under_slab_top_in"] * IN, -p[R + "under_slab_bottom_in"] * IN
    z_at = lambda f: zt + f * (zb - zt)  # noqa: E731
    z_drains, z_feed, z_mains, z_bldg = (z_at(p[R + k]) for k in ("slab_drains_at", "slab_feeders_at", "slab_mains_at", "slab_building_drain_at"))
    eqb = {e["id"]: e for e in eq}
    reqs = []
    # Step 7c's sizes, where the routed designs asked more than steps 3-6 (`routed.grow`): a flat's
    # vents a size up over 40 ft (IPC 906.2: 2 in., the vent stack's no-hub), the mains, the fire riser.
    from .routed import grown
    gs = grown(p)
    vent_od = lambda n: p[R + "vent_stack_od_in"] if gs.get("vent_in", {}).get(n, 1.5) >= 2.0 else p[R + "vent_od_in"]  # noqa: E731

    def fall(size_in: float) -> float:
        """A horizontal drain's least fall per unit run (IPC 2021 Table 704.1): 1/4 in./ft at
        2-1/2 in. and under, 1/8 at 3 to 6."""
        return p[R + ("drain_slope_small_in_ft" if size_in <= 2.5 else "drain_slope_large_in_ft")] / 12

    def add(id_, system, od_in, root, terminals, zones, attach=(), voxel=v1, square_ft=None, gap=None, **kw):
        reqs.append({"id": id_, "system": system, "od_m": od_in * IN, "clear_m": clear if gap is None else gap, "hole_clear_m": hole, "voxel_m": voxel,
                     "root": [round(v, 6) for v in root], "terminals": [{"ref": r, "xyz": [round(v, 6) for v in x]} for r, x in terminals],
                     "zones": zones, "attach": list(attach), "snap_m": p[R + "snap_in"] * IN, "square_ft": square_ft, **kw})

    obstacles = []
    pinned: dict[str, dict] = {}

    def block(id_, lo, hi):
        obstacles.append({"id": id_, **_box(lo, hi)})
        pinned[id_] = _box(lo, hi)

    def part_of(id_, z0=None, z1=None) -> list[dict]:
        """A pinned service's box between two heights: where a request may join it."""
        b = pinned[id_]
        return [_box([b["lo"][0], b["lo"][1], b["lo"][2] if z0 is None else z0], [b["hi"][0], b["hi"][1], b["hi"][2] if z1 is None else z1])]

    # The roof hatch's fixed ladder (Addendum 5), up through the top hall's ceiling: the stair's
    # sprinkler arm there keeps clear of it.
    if apt.get("roof_ladder"):
        block("stair/roof-ladder", apt["roof_ladder"]["lo_m"], apt["roof_ladder"]["hi_m"])

    # -- Pinned: 7a's vertical services, from under the slab up their column.
    top_tee = {}
    for col, v in vs.items():
        names = sorted((n for n in fx if column(n) == col), key=storey_of)
        for s_ in v:
            r_ = s_["od_in"] * IN / 2
            if s_["kind"] in ("drain", "vent"):
                z0, z1 = zt, roof_top + p["systems.plumbing.vent_above_roof_in"] * IN
            elif s_["kind"] == "line-set":
                flat = s_["id"].split("/", 2)[2]
                z0 = next(x for x in sf if x["id"] == f"{flat}/soffit-utility")["lo"][2]
                z1 = roof_top
            elif s_["kind"] == "hot-return":
                # Up through the top flat's plates into its joists' space, so the top flat's loop's
                # return joins it there as the floors below join theirs (Addendum 7).
                z0 = zt
                top = cavity(apt, names[-1])
                z1 = (top["lo"][2] + top["hi"][2]) / 2
                top_tee[s_["id"]] = z1
            else:
                z0 = zt
                z1 = ceiling_z(apt, storey_of(names[-1])) - p[R + "branch_drop_in"] * IN + 0.05
                top_tee[s_["id"]] = z1
            block(s_["id"], [s_["x"] - r_, s_["y"] - r_, z0], [s_["x"] + r_, s_["y"] + r_, z1])
    # The feeder conduits up the hall's partition.
    for col, c in ch.items():
        for k in c["conduits"]:
            flat = k["flat"]
            r_ = k["od_in"] * IN / 2
            pz = eqb[f"{flat}/panel"]["lo"][2]
            block(k["id"], [k["x"] - r_, k["y"] - r_, z_feed], [k["x"] + r_, k["y"] + r_, pz])
    # Each water closet's bend, along its joist bay to the stack (in the floor under it, or the slab's).
    stack = {col: next(s_ for s_ in v if s_["kind"] == "drain") for col, v in vs.items()}
    for name, f in fx.items():
        wc = f["wc"]
        x_out = wc["x"] + wc["into"] * wc["out_m"]
        st = stack[column(name)]
        b = below(apt, name)
        zc = (cavity(apt, b)["lo"][2] + cavity(apt, b)["hi"][2]) / 2 if b else z_drains
        r_ = p[R + "closet_bend_od_in"] * IN / 2
        block(f"{name}/wc-bend", [min(x_out, st["x"]) - r_, wc["y"] - r_, zc - r_], [max(x_out, st["x"]) + r_, wc["y"] + r_, wc["floor_z"]])
        # The washer's standpipe, in the wall from its trap up to the washer box (IPC 406.3: 2 in.):
        # the washer's vent stands beside it, the condensate drops into its box.
        wv = f["washer"]
        cw = wall_cavity(apt, frame, _pw(apt, name), p)
        r_ = p[R + "drain_od_washer_in"] * IN / 2
        block(f"{name}/standpipe", [(cw["lo"][0] + cw["hi"][0]) / 2 - r_, wv["y"] - r_, wv["floor_z"] + p[R + "washer_trap_in"] * IN],
              [(cw["lo"][0] + cw["hi"][0]) / 2 + r_, wv["y"] + r_, wv["floor_z"] + p[R + "washer_box_in"] * IN])
    # The sprinkler riser in the stair, just past the halls' floors.
    rx, ry = riser_xy(apt)
    fire_od = float(next(r["avg_OD_in"] for r in _cpvc_rows() if r["nominal_in"] == p_size(p, "riser")))
    riser_x = rx + fire_od * IN / 2 + clear
    top_cav = cavity(apt, f"{apt['storeys']}-front-left")["hi"][2]
    block("stair/fire-riser", [riser_x - fire_od * IN / 2, ry - fire_od * IN / 2, z_mains], [riser_x + fire_od * IN / 2, ry + fire_od * IN / 2, top_cav])
    # The equipment.
    for e in eq + plant + units:
        block(e["id"], e["lo"], e["hi"])

    # -- Sprinklers: the stair's arms into each flat, a storey at a time; each flat's tree.
    from .routing import strip_soffits
    lay = layout(apt, p, strip_soffits(apt, p))
    feed_od = float(next(r["avg_OD_in"] for r in _cpvc_rows() if r["nominal_in"] == p_size(p, "feed")))
    core = apt["stair"]["core_y_m"]
    stair_parts = {x["id"]: x for x in apt["stair"]["parts"]}
    roots = {}
    for name in by_flat(apt):
        door = next(x for x in apt["stair"]["doors"] if x.get("flat") == name)
        face = door["lo_m"][1] if door["lo_m"][1] < core[0] else door["hi_m"][1]  # the stair wall's flat side
        into = -1.0 if face <= core[0] else 1.0
        cv = cavity(apt, name)
        roots[name] = [(door["lo_m"][0] + door["hi_m"][0]) / 2, face + into * p[R + "fire_entry_in"] * IN, (cv["lo"][2] + cv["hi"][2]) / 2]
    for k in range(1, apt["storeys"] + 1):
        cv = cavity(apt, f"{k}-front-left")
        if k < apt["storeys"]:
            hall = stair_parts[f"floor-{k + 1}-hall"]
            x0, x1 = hall["lo_m"][0], riser_x + 0.15
        else:
            x0, x1 = 0.0, apt["depth_m"]
        zones = [_box([x0, core[0] - 0.4, cv["lo"][2]], [x1, core[1] + 0.4, cv["hi"][2]])]
        flats = [n for n in by_flat(apt) if storey_of(n) == k]
        for n in flats:
            rt = roots[n]
            zones.append(_box([rt[0] - 0.3, min(rt[1], core[0]), cv["lo"][2]], [rt[0] + 0.3, max(rt[1], core[1]), cv["hi"][2]]))
        # Its two quick-response sprinklers (step 6), at the quarters of the ceiling over the stair.
        reach = stair_parts[f"floor-{k + 1}-hall-a"]["hi_m"][0] if k < apt["storeys"] else apt["depth_m"]
        heads = [(f"stair/{k}/head-{i}", [x0 + (i + 0.5) * (reach - x0) / 2, (core[0] + core[1]) / 2, cv["lo"][2] + feed_od * IN / 2 + clear + 0.01])
                 for i in range(2)]
        add(f"fire/stair/{k}", "sprinkler", feed_od, [riser_x, ry, (cv["lo"][2] + cv["hi"][2]) / 2],
            [(n, roots[n]) for n in flats] + heads, zones, attach=["stair/fire-riser"], role="arm", storey=k)
    moved: dict[str, list] = {n: [] for n in lay}
    for name, L in lay.items():
        cv = cavity(apt, name)
        zones = [cv]
        mine = [x for x in sf if x["flat"] == name]
        terminals = []
        strips = [x_ for x_ in mine if "soffit-strip" in x_["id"]]
        xys = [clear_of_equipment(h, [e for e in eq if e.get("flat") == name], by_flat(apt)[name], p) for h in L["heads"]]
        cells = [([h["xy"][k] - h["cell_ft"][k] * FT / 2 for k in range(2)], [h["xy"][k] + h["cell_ft"][k] * FT / 2 for k in range(2)])
                 for h in L["heads"]]
        xys, cells = respace_off_strips(L["heads"], xys, cells, strips, by_flat(apt)[name], p)
        keep_out = [e for e in eq if e.get("flat") == name] + strips
        xys = spread_heads(L["heads"], xys, cells, keep_out, by_flat(apt)[name], p)
        for i, h in enumerate(L["heads"]):
            x, y = xys[i]
            moved[name].append({"head": i, "room": h["room"], "from": h["xy"], "to": (x, y), "l_ft": h["l_ft"], "cell": cells[i]})
            under = next((x_ for x_ in mine if x_["lo"][0] <= x <= x_["hi"][0] and x_["lo"][1] <= y <= x_["hi"][1]), None)
            if under:
                w = p[R + "drop_pass_in"] * IN
                zones.append(_box([x - w, y - w, under["lo"][2]], [x + w, y + w, cv["lo"][2] + 0.02]))
                terminals.append((f"{h['room']}#{i}", [x, y, under["lo"][2] + feed_od * IN / 2 + clear + 0.01]))
            else:
                terminals.append((f"{h['room']}#{i}", [x, y, cv["lo"][2] + feed_od * IN / 2 + clear + 0.01]))
        add(f"fire/flat/{name}", "sprinkler", feed_od, roots[name], terminals, zones, attach=[f"fire/stair/{storey_of(name)}"],
            role="flat", flat=name, blocks=over_wall(apt, name, []))
    # The fire main: from the riser assembly down through the annex's slab, under it into the stair,
    # to the riser's foot.
    main_od = float(next(r["avg_OD_in"] for r in _cpvc_rows() if r["nominal_in"] == p_size(p, "main")))
    fire_in = [*annex_drops(apt, p)["fire"], z_mains]
    add("fire/main", "sprinkler", main_od, fire_in, [("riser", [riser_x, ry, z_mains])], slab_zone(apt, p), attach=["stair/fire-riser"],
        voxel=v2, role="main")

    # -- Each flat's ducts in its soffits, its line set, condensate and the manifold's tails.
    from .hvac import pipe_for_flow, substation
    from .plumbing import design as pdesign
    from .routing import pex_od_in
    from .designs import floors
    vent = ventilation_ducts(apt, p)
    cool = cooling_ducts(apt, p)
    sub = substation(apt, p) if floors(p) else None  # the edge design has no building loop
    pd = pdesign(apt, p)
    for name in by_flat(apt):
        rooms = {r["id"].split("/")[1]: r for r in by_flat(apt)[name]}
        zones = soffit_zones(apt, name, sf)
        erv, ms = eqb[f"{name}/erv"], eqb[f"{name}/minisplit"]
        f = fx[name]
        into = f["wc"]["into"]
        # The ERV's ports: the outdoor pair on its end toward the closet's door, the indoor pair on the
        # end toward the plumbing wall (Broan: two 4 in. ports an end, 8-9/16 in. apart).
        door_end = erv["lo"][0] if into < 0 else erv["hi"][0]
        wall_end = erv["hi"][0] if into < 0 else erv["lo"][0]
        yc = (erv["lo"][1] + erv["hi"][1]) / 2
        zp = erv["hi"][2] - p[R + "erv_port_down_in"] * IN
        sep = p[R + "erv_port_sep_in"] * IN / 2
        out = into  # the door end lies the way into the rooms from the plumbing wall
        col = p[R + "erv_collar_in"] * IN
        port = {"oa": [door_end + out * col, yc - sep, zp], "ea": [door_end + out * col, yc + sep, zp],
                "supply": [wall_end - out * col, yc - sep, zp], "return": [wall_end - out * col, yc + sep, zp]}
        hall_soffit = next(x for x in sf if x["id"] == f"{name}/soffit-hall")
        zm = (hall_soffit["lo"][2] + hall_soffit["hi"][2]) / 2
        grille = _grilles(apt, name, rooms, zm, p, p[R + "grille_erv_at"])
        ms_grille = _grilles(apt, name, rooms, zm, p, p[R + "grille_ms_at"])
        v = vent[name]
        exh = [(rid, grille[rid.split("/")[1]]) for rid in v["exhaust"]["branches"]]
        # The fresh air into the mini-split's return, at its back (Jon, 2026-11-21: through the
        # mini-split; the hall can't hold both systems' ducts), and on through the mini-split's ducts
        # to every room it serves; its fan runs on at low speed with the ERV. Into the return, not
        # the side knockout: there it would cross the mini-split's supplies, with no room in the
        # soffit's 14 in. to pass over them.
        # The unit's back (its return) faces the passage, where the ERV's duct comes in; its supply
        # faces the bedrooms.
        liv_y0 = (rooms["living"]["lo_m"][1] + rooms["living"]["hi_m"][1]) / 2
        back_y = ms["hi"][1] + 0.03 if liv_y0 > (ms["lo"][1] + ms["hi"][1]) / 2 else ms["lo"][1] - 0.03
        # At the collar's end away from the living room's grille: the mini-split's duct to it passes
        # the unit's back on that grille's side.
        mid_x = (ms["lo"][0] + ms["hi"][0]) / 2
        dsz = max(r["in"] for r in v["supply"]["branches"].values())
        off = p[R + "ms_return_w_in"] * IN / 2 - dsz * IN / 2 - clear
        away = -1.0 if ms_grille["living"][0] > mid_x else 1.0
        knock = [mid_x + away * off, back_y, ms["lo"][2] + p[R + "ms_return_up_in"] * IN]
        dsz = max(r["in"] for r in v["supply"]["branches"].values())
        add(f"hvac/erv-supply/{name}", "duct", dsz, port["supply"], [("minisplit", knock)], zones, attach=[f"{name}/erv", f"{name}/minisplit"],
            flat=name, role="erv-supply", square_ft=v["supply"]["common"]["ft"] if v["supply"]["common"] else None)
        dsz = max(r["in"] for r in v["exhaust"]["branches"].values())
        add(f"hvac/erv-exhaust/{name}", "duct", dsz, port["return"], exh, zones, attach=[f"{name}/erv"], flat=name, role="erv-exhaust")
        t = next(x for x in terms if x["flat"] == name)
        strip = next(x for x in sf if x["id"] == f"{name}/soffit-strip")
        fx_in = strip["lo"][0] + 0.02 if t["face"] == "front" else strip["hi"][0] - 0.02
        oa_od = p[R + "oa_duct_in"] + 2 * p[R + "oa_insulation_in"]
        tand = p[R + "tandem_sep_in"] * IN / 2
        # The duct whose port is nearer the termination goes first: the other, routed first, would run
        # under its port on the way and close its drop out of it.
        oa_first = abs(port["oa"][1] - t["y"]) <= abs(port["ea"][1] - t["y"])
        prio = {"oa": 0 if oa_first else 1, "ea": 1 if oa_first else 0}
        dy = {"oa": -tand, "ea": tand}  # the kit's intake on its lower-y side, its exhaust on its upper
        zs = {"oa": zones, "ea": zones}
        bl: dict[str, list] = {"oa": [], "ea": []}
        turned = False
        leg = next((x for x in sf if x["id"] == f"{name}/soffit-strip-leg"), None)
        if leg:
            # Round the corner of the strip's leg (the middle storey's): the duct behind (its port
            # farther from the termination) passes the other's port on the leg's side, so it takes the
            # corner's inside lane, and goes first, kept off the other's drop out of its port. Two
            # 8 in. ducts can't cross in a 14 in. soffit; each keeps its own lane (`_lanes`).
            inside = -1.0 if (leg["lo"][1] + leg["hi"][1]) / 2 < t["y"] else 1.0  # the leg comes up from lower y
            inner, outer = ("ea", "oa") if oa_first else ("oa", "ea")
            if dy[inner] * inside < 0:  # its port on the kit's other side: the kit turns
                dy = {k: -v for k, v in dy.items()}
                turned = True
            zs = {inner: _lanes(zones, strip, leg, inside, t["face"] == "back", True),
                  outer: _lanes(zones, strip, leg, inside, t["face"] == "back", False)}
            prio = {inner: 0, outer: 1}
            q = port[outer]
            bl[inner] = [_box([q[0] - 0.05, q[1] - 0.05, strip["lo"][2]], [q[0] + 0.05, q[1] + 0.05, q[2] + 0.05])]
        add(f"hvac/erv-oa/{name}", "duct", oa_od, port["oa"], [("intake", [fx_in, t["y"] + dy["oa"], zm])], zs["oa"], attach=[f"{name}/erv"],
            flat=name, role="erv-oa", priority=prio["oa"], kit_turned=turned, blocks=bl["oa"])
        add(f"hvac/erv-ea/{name}", "duct", oa_od, port["ea"], [("exhaust", [fx_in, t["y"] + dy["ea"], zm])], zs["ea"], attach=[f"{name}/erv"],
            flat=name, role="erv-ea", priority=prio["ea"], kit_turned=turned, blocks=bl["ea"])
        # The mini-split: its supply collar toward the bedrooms (its back, the return, takes the
        # ERV's air from the passage's side); a duct to each room it serves.
        c = cool[name]
        liv_y = (rooms["living"]["lo_m"][1] + rooms["living"]["hi_m"][1]) / 2
        front = ms["lo"][1] if liv_y > (ms["lo"][1] + ms["hi"][1]) / 2 else ms["hi"][1]
        fwd = 1.0 if front == ms["hi"][1] else -1.0
        coll = [(ms["lo"][0] + ms["hi"][0]) / 2, front + fwd * 0.03, ms["lo"][2] + p[R + "ms_supply_up_in"] * IN]
        targets = [(rid, ms_grille[rid.split("/")[1]]) for rid in c["ducts"]["branches"]]
        msz = max(r["in"] for r in c["ducts"]["branches"].values())
        add(f"hvac/ms-supply/{name}", "duct", msz, coll, targets, zones, attach=[f"{name}/minisplit"], flat=name, role="ms-supply")
        # The line set: from the unit's piping side to its riser in the plumbing wall.
        ls = next(s_ for s_ in vs[column(name)] if s_["id"].endswith(f"line-set/{name}"))
        side = ms["piping_clear_to"]
        pipe_x = ms["hi"][0] if abs(side - ms["hi"][0]) < abs(side - ms["lo"][0]) else ms["lo"][0]
        sgn = 1.0 if pipe_x == ms["hi"][0] else -1.0
        back = front - fwd * p[R + "ms_pipe_back_in"] * IN
        util_s = next(x for x in sf if x["id"] == f"{name}/soffit-utility")
        lz = (util_s["lo"][2] + util_s["hi"][2]) / 2
        wz = [wall_cavity(apt, frame, _pw(apt, name), p, z0=util_s["lo"][2], z1=util_s["hi"][2], y0=ls["y"] - 0.15, y1=ls["y"] + 0.15),
              wall_entry(f["wc"]["x"], into, ls["y"], util_s["lo"][2], util_s["hi"][2], 0.12, 0.2)]
        add(f"hvac/line-set/{name}", "line-set", p[R + "line_set_od_in"], [ls["x"], ls["y"], lz],
            [("unit", [pipe_x + sgn * 0.04, back, ms["lo"][2] + p[R + "ms_pipe_up_in"] * IN])], zones + wz,
            attach=[f"{name}/minisplit", ls["id"]], flat=name, role="line-set", square_ft=c["line_ft"], gap=wall_clear)
        # The condensate: from the unit's drain port to the washer's standpipe (an indirect waste),
        # falling 1% (IMC 307.2.1) by gravity, in the soffits deepened under the unit for it.
        wy = f["washer"]["y"]
        wzone = [wall_cavity(apt, frame, _pw(apt, name), p, z0=f["washer"]["floor_z"] + p[R + "washer_box_in"] * IN - 0.1,
                             z1=util_s["hi"][2], y0=wy - 0.3, y1=wy + 0.3),
                 wall_entry(f["wc"]["x"], into, wy, util_s["lo"][2], util_s["hi"][2], 0.12, 0.2)]
        box_z = f["washer"]["floor_z"] + p[R + "washer_box_in"] * IN
        px = _pw_x(apt, frame, name, p)
        add(f"hvac/condensate/{name}", "condensate", p[R + "condensate_od_in"], [px, wy, box_z + 0.05],
            [("unit", [pipe_x + sgn * 0.03, back - 0.03, ms["lo"][2] + p[R + "ms_drain_up_in"] * IN])], zones + wzone,
            attach=[f"{name}/minisplit", f"hvac/line-set/{name}", f"{name}/standpipe"], flat=name, role="condensate", gap=wall_clear,
            goals=[_box([px - 0.03, wy - 0.03, box_z - 0.02], [px + 0.03, wy + 0.03, box_z + 0.15])],
            grade=-1, slope=p[R + "condensate_slope_in_ft"] / 12)
        # The radiant manifold's tails (the network design's): up from the loop's risers into the
        # ceiling (the risers stand side by side, so nothing passes along the wall beside them), over
        # to the closet, down the plumbing wall there, out of it beside the washer and along the
        # closet's floor to the cabinet.
        if sub is None:
            continue
        man = eqb[f"{name}/manifold"]
        wd = eqb[f"{name}/washer-dryer"]
        util = rooms["utility"]
        y_lo, y_hi = (util["lo_m"][1], wd["lo"][1] - clear) if man["lo"][1] <= util["lo_m"][1] + 0.01 else (wd["hi"][1] + clear, util["hi_m"][1])
        fz = f["wc"]["floor_z"]
        hz = fz + p[R + "tail_height_in"] * IN
        ceil_t = cavity(apt, name)
        col_w = p[R + "wall_column_in"] * IN
        tz = [_box([util["lo_m"][0], y_lo, fz + 0.05], [util["hi_m"][0], y_hi, hz + 0.1]),
              wall_cavity(apt, frame, _pw(apt, name), p, y0=y_lo, y1=y_hi),
              wall_entry(f["wc"]["x"], into, (y_lo + y_hi) / 2, fz + 0.05, hz + 0.1, (y_hi - y_lo) / 2, 0.2), ceil_t]
        mport_x = man["hi"][0] if into < 0 else man["lo"][0]
        loop_od = pex_od_in(pipe_for_flow(sub["flats"][name]["gpm"], p)[0], p[R + "tail_insulation_in"])
        for kind, dz in (("loop-supply", 0.18), ("loop-return", 0.08)):
            rs = next(s_ for s_ in vs[column(name)] if s_["kind"] == kind)
            top = storey_of(name) == max(storey_of(n) for n in fx if column(n) == column(name))
            add(f"hvac/{kind}-tail/{name}", "hydronic", loop_od, [rs["x"], rs["y"], ceiling_z(apt, storey_of(name)) - p[R + "branch_drop_in"] * IN],
                [("manifold", [mport_x - into * 0.03, (man["lo"][1] + man["hi"][1]) / 2, man["lo"][2] + dz])],
                tz + [wall_cavity(apt, frame, _pw(apt, name), p, y0=rs["y"] - col_w, y1=rs["y"] + col_w)],
                attach=[rs["id"], f"{name}/manifold", "hvac/loop-*"], flat=name, role=kind, gap=wall_clear,
                goals=part_of(rs["id"], fz + 0.3, ceil_t["lo"][2] if top else ceil_t["hi"][2]),
                blocks=over_wall(apt, name, [(rs["y"] - col_w, rs["y"] + col_w), (y_lo, y_hi)]))

    # -- Each flat's water, drains and vents in its plumbing wall: the flat's branches at step 4's
    # size for the top flat's (the largest).
    h = "systems.hot_water."
    ins = lambda n: p[h + ("insulation_in_large" if n >= 1.5 else "insulation_in_small")]  # noqa: E731
    branch = {k: next(s_["in"] for s_ in pd["paths"][k]["segments"] if "branch" in s_["segment"]) for k in ("cold", "hot")}
    for name, f in fx.items():
        pw = _pw(apt, name)
        cav = wall_cavity(apt, frame, pw, p)
        x = (cav["lo"][0] + cav["hi"][0]) / 2
        fz = f["wc"]["floor_z"]
        col = column(name)
        off = p[R + "stub_offset_in"] * IN
        ceil = cavity(apt, name)
        tee_z = ceiling_z(apt, storey_of(name)) - p[R + "branch_drop_in"] * IN
        # Where each fixture's vent and supplies go up and down the wall: a stud bay each, clear of
        # the column's stacks and risers.
        pins = [(s_["y"], s_["od_in"] * IN / 2) for s_ in vs[col] if s_["y"] is not None]
        free = wall_slots(apt, frame, pw, x, pins, wall_clear)
        r_sp = p[R + "drain_od_washer_in"] * IN / 2 + wall_clear
        taken: list[tuple[float, float]] = [(f["washer"]["y"] - r_sp, f["washer"]["y"] + r_sp)]  # its standpipe
        slot: dict[tuple[str, str], float] = {}
        hot_od, cold_od = pex_od_in(branch["hot"], p[R + "branch_insulation_in"]), pex_od_in(branch["cold"], p[R + "cold_insulation_in"])
        ret_n = max(pd["loop"]["flat_return_in"], gs.get("return_in", {}).get("flat", 0.0))
        ret_od = pex_od_in(ret_n, p[R + "branch_insulation_in"])
        # A slot as the router sees it: whole voxels (forge rounds a pipe's cross-section up to
        # 2r + 1 of them), and one more for where the grid's cells fall.
        cells = lambda half: (max(0, math.ceil((2 * half / v1 - 1) / 2 - 1e-9)) + 1) * v1  # noqa: E731
        for fk in ("wc", "tub", "lav", "sink", "washer", "dishwasher"):
            fv = f[fk]
            if fv["y"] is None:
                continue
            if fk != "dishwasher":
                slot[(fk, "vent")] = take_slot(free, fv["y"] + p[R + "vent_off_in"] * IN, cells(vent_od(name) * IN / 2 + wall_clear), taken, 0.0)
            for kind, od_, sgn in (("cold", cold_od, 1.0), ("hot", hot_od, -1.0)):
                if f"{kind}_in" in fv:
                    slot[(fk, kind)] = take_slot(free, fv["y"] + sgn * off, cells(od_ * IN / 2 + wall_clear), taken, 0.0)
            if fk == LOOP_END:
                # The flat's loop's return stub (Addendum 7), beside the hot one toward the fixture's
                # middle: the thermostatic balancing valve joins the two in the vanity.
                yh = slot[(fk, "hot")]
                toward = 1.0 if fv["y"] > yh else -1.0
                slot[(fk, "return")] = take_slot(free, yh + toward * off, cells(ret_od * IN / 2 + wall_clear), taken, 0.0)
        for kind, temp_od in (("cold", pex_od_in(branch["cold"], p[R + "cold_insulation_in"])), ("hot", pex_od_in(branch["hot"], p[R + "branch_insulation_in"]))):
            riser = next(s_ for s_ in vs[col] if s_["kind"] == kind)
            terms_ = []
            for fk, fv in f.items():
                key = f"{kind}_in"
                if key in fv and fv["y"] is not None:
                    terms_.append((fk, [x, slot[(fk, kind)], fz + fv[key] * IN]))
            # In the wall only straight up and down: a column at each fixture and at the riser; across
            # in the ceiling.
            col_w = p[R + "wall_column_in"] * IN
            bay = kind != "hot"  # the hot's insulation stops at the plates: the studs' whole depth (`wall_cavity`)
            cols = [wall_cavity(apt, frame, pw, p, y0=t_[1][1] - col_w, y1=t_[1][1] + col_w, edge=bay) for t_ in terms_]
            cols.append(wall_cavity(apt, frame, pw, p, y0=riser["y"] - col_w, y1=riser["y"] + col_w, edge=bay))
            # Below the top the riser goes on up through the ceiling cavity, and the branch tees off it
            # there (through the riser's own hole in the plates); at the top its tee is its end.
            top = storey_of(name) == max(storey_of(n) for n in fx if column(n) == col)
            extra, zone_ceil = {}, ceil
            if kind == "hot":
                # The flat's loop (IECC C404.5, Addendum 7) runs through its hot branch to the
                # lavatory, where its return starts (below), so every fixture is a short way off
                # circulating water. Its holes for the bare pipe: the insulation stops at each member
                # it passes (C404.4).
                extra = {"bore_m": pex_od_in(branch["hot"]) * IN, "voxel": vh}
                # On the finer voxel, in the joists' space along the wall (`hot_band_in`).
                zone_ceil = _box([max(ceil["lo"][0], x - band), ceil["lo"][1], ceil["lo"][2]],
                                 [min(ceil["hi"][0], x + band), ceil["hi"][1], ceil["hi"][2]])
            add(f"plumbing/{kind}/{name}", "water", temp_od, [riser["x"], riser["y"], tee_z], terms_, cols + [zone_ceil],
                attach=[riser["id"]], flat=name, role=kind, gap=wall_clear,
                goals=part_of(riser["id"], fz + 0.3, tee_z if top else ceil["hi"][2]),
                blocks=over_wall(apt, name, [(y_ - col_w, y_ + col_w) for y_ in [t_[1][1] for t_ in terms_] + [riser["y"]]]), **extra)
            if kind == "hot":
                # Its return: from its own stub under the lavatory (the thermostatic balancing valve
                # in the vanity joins it to the hot one, where it can be reached: C404.6), up the wall,
                # back through the joists' space to the return riser.
                rr = next(s_ for s_ in vs[col] if s_["kind"] == "hot-return")
                ys = slot[(LOOP_END, "return")]
                stub = [x, ys, fz + f[LOOP_END]["hot_in"] * IN]
                add(f"plumbing/hot-return/{name}", "water", ret_od, [rr["x"], rr["y"], tee_z], [(LOOP_END, stub)],
                    [wall_cavity(apt, frame, pw, p, y0=ys - col_w, y1=ys + col_w, edge=False),
                     wall_cavity(apt, frame, pw, p, y0=rr["y"] - col_w, y1=rr["y"] + col_w, edge=False), ceil],
                    attach=[rr["id"]], flat=name, role="hot-return", gap=wall_clear, bore_m=pex_od_in(ret_n) * IN,
                    after=f"plumbing/hot/{name}", size_in=ret_n,
                    goals=part_of(rr["id"], fz + 0.3, ceil["hi"][2]),
                    blocks=over_wall(apt, name, [(ys - col_w, ys + col_w), (rr["y"] - col_w, rr["y"] + col_w)]))
        st, vst = stack[col], next(s_ for s_ in vs[col] if s_["kind"] == "vent")
        # The lav's, sink's and washer's drains: down the wall from the trap, through the floor, along
        # the joists' space under it (or under the slab) to the stack; nothing runs along the wall,
        # where the supplies drop and the vents rise.
        b = below(apt, name)
        wet = [r for r in by_flat(apt)[name] if r["use"] in ("bath", "utility", "kitchen")]
        wx0, wx1 = min(min(r["lo_m"][0] for r in wet), cav["lo"][0]), max(max(r["hi_m"][0] for r in wet), cav["hi"][0])
        wy0, wy1 = min(r["lo_m"][1] for r in wet), max(r["hi_m"][1] for r in wet)
        if b:
            cb = cavity(apt, b)
            under_box = _box([wx0, wy0, cb["lo"][2]], [wx1, wy1, cb["hi"][2]])
            pass_z0, goal = cb["lo"][2], part_of(st["id"], cb["lo"][2], cb["hi"][2])
        else:
            under_box = _box([wx0, wy0, zb], [wx1, wy1, zt])
            pass_z0, goal = zt - 0.01, part_of(st["id"], zb, zt)
        # One horizontal branch for the three (IPC Table 710.1(2): 2 in. takes 6 dfu; they are 5), as
        # a plumber runs it: three pipes side by side close the joists' space to the flat below.
        down, terms_d, keep = [under_box], [], [(st["y"] - col_w, st["y"] + col_w)]
        for fk in ("lav", "sink", "washer"):
            fv = f[fk]
            dz = fz + fv["drain_in"] * IN
            down += [wall_cavity(apt, frame, pw, p, z0=fz, z1=dz + 0.05, y0=fv["y"] - 0.12, y1=fv["y"] + 0.12),
                     _box([cav["lo"][0], fv["y"] - 0.12, pass_z0], [cav["hi"][0], fv["y"] + 0.12, fz + 0.02])]
            terms_d.append((fk, [x, fv["y"], dz]))
            keep.append((fv["y"] - 0.12, fv["y"] + 0.12))
        add(f"plumbing/drain/{name}/branch", "drain", p[R + "drain_od_branch_in"], [st["x"], st["y"], (under_box["lo"][2] + under_box["hi"][2]) / 2],
            terms_d, down, attach=[st["id"], f"{name}/wc-bend", f"plumbing/drain/{name}/*", f"{name}/standpipe"], flat=name, role="drain",
            fixtures={fk: f[fk]["drain_size"] for fk in ("lav", "sink", "washer")}, size_in=p[R + "drain_branch_in"],
            gap=wall_clear, grade=-1, slope=fall(p[R + "drain_branch_in"]), goals=goal, voxel=v1, blocks=over_wall(apt, b, keep) if b else [])
        # The tub: under the floor, in the cavity below (or under the slab), to the stack's foot there.
        b = below(apt, name)
        bath = next(r for r in by_flat(apt)[name] if r["use"] == "bath")
        tub = f["tub"]
        tx = tub["x"] + tub["into"] * tub["out_m"]
        if b:
            cb = cavity(apt, b)
            zc = (cb["lo"][2] + cb["hi"][2]) / 2
            zone = [_box([min(bath["lo_m"][0], cav["lo"][0]), bath["lo_m"][1], cb["lo"][2]], [max(bath["hi_m"][0], cav["hi"][0]), bath["hi_m"][1], cb["hi"][2]])]
            add(f"plumbing/drain/{name}/tub", "drain", p[R + "drain_od_tub_in"], [st["x"], st["y"], zc], [("tub", [tx, tub["y"], zc])], zone,
                attach=[st["id"], f"{name}/wc-bend"], flat=name, role="drain", fixture="tub", size_in=1.5, gap=wall_clear, grade=-1, slope=fall(1.5),
                blocks=over_wall(apt, b, [(st["y"] - col_w, st["y"] + col_w)]))
        else:
            zone = [_box([min(bath["lo_m"][0], cav["lo"][0]), bath["lo_m"][1], -p[R + "under_slab_bottom_in"] * IN],
                         [max(bath["hi_m"][0], cav["hi"][0]), bath["hi_m"][1], -p[R + "under_slab_top_in"] * IN])]
            add(f"plumbing/drain/{name}/tub", "drain", p[R + "drain_od_tub_in"], [st["x"], st["y"], z_drains], [("tub", [tx, tub["y"], z_drains])], zone,
                attach=[st["id"], f"{name}/wc-bend"], flat=name, role="drain", fixture="tub", size_in=1.5, voxel=v1, gap=wall_clear, grade=-1,
                slope=fall(1.5))
        # Vents: each fixture's up the wall from its trap's arm into the ceiling, where they join one
        # another (a vent header) and the vent stack, 6 in. over the highest flood rim (IPC 905.4,
        # 905.5; 906.4 sizes a header of branch vents).
        vz = (ceil["lo"][2] + ceil["hi"][2]) / 2
        col_w = p[R + "wall_column_in"] * IN
        vterms, cols = [], [wall_cavity(apt, frame, pw, p, y0=vst["y"] - col_w, y1=vst["y"] + col_w)]
        for fk in ("wc", "tub", "lav", "sink", "washer"):
            fv = f[fk]
            low = fz + (fv["drain_in"] * IN if fv.get("drain_in") else p[R + "vent_low_in"] * IN) + p[R + "vent_up_in"] * IN
            vy = slot[(fk, "vent")]
            vterms.append((fk, [x, vy, low]))
            cols.append(wall_cavity(apt, frame, pw, p, y0=vy - col_w, y1=vy + col_w))
        add(f"plumbing/vent/{name}", "vent", vent_od(name), [vst["x"], vst["y"], vz], vterms, cols + [ceil],
            attach=[vst["id"], f"plumbing/drain/{name}/*", f"{name}/wc-bend"], flat=name, role="vent", gap=wall_clear, grade=1,
            slope=p[R + "vent_slope_in_ft"] / 12,
            goals=part_of(vst["id"], fz + p[R + "vent_conn_in"] * IN, ceil["hi"][2]),
            blocks=over_wall(apt, name, [(t_[1][1] - col_w, t_[1][1] + col_w) for t_ in vterms] + [(vst["y"] - col_w, vst["y"] + col_w)]))

    # -- Under the slab: the mains to each column's risers, the building drain, the feeders.
    root_plant = [*annex_drops(apt, p)["plant"], z_mains]
    main_in = {"cold": next(s_["in"] for s_ in pd["paths"]["cold"]["segments"] if "main" in s_["segment"]),
               "hot": next(s_["in"] for s_ in pd["paths"]["hot"]["segments"] if "main" in s_["segment"]),
               "hot-return": pd["loop"]["return_main_in"], **({"loop-supply": sub["header_in"], "loop-return": sub["header_in"]} if sub else {})}
    main_in = {k: max(v, gs.get("main_in", {}).get(k, 0.0)) for k, v in main_in.items()}
    # Each main at its own depth, so they cross under one another; each joins its risers' feet from
    # below (the risers stand 3-4 in. apart in the wall, too close for mains side by side).
    for kind, n in main_in.items():
        od = n + 0.125 + 2 * p[R + "underslab_jacket_in"]
        zk = z_at(p[R + f"slab_{kind.replace('-', '_')}_at"])
        feet = [s_ for v in vs.values() for s_ in v if s_["kind"] == kind]
        tt = [(s_["id"].split("/")[0], [s_["x"], s_["y"], zk]) for s_ in feet]
        add(f"main/{kind}", "main", od, [root_plant[0], root_plant[1], zk], tt, slab_zone(apt, p), attach=[s_["id"] for s_ in feet] + ["main/*"],
            voxel=v2, role="main", kind=kind)
    # The building drain: from the stacks' feet at its layer, the lowest, falling 1/8 in./ft to the
    # sewer's exit. Its fall (about 7 in. over its run) takes it below the perimeter footing's top,
    # level with the trench's bottom: it ends at the footing's inner edge at whatever depth its fall
    # gives, and leaves through the stem wall where the footing steps down under it (for the
    # structural engineer, as the spine footing's sleeves; the depth a site item, the lateral to the
    # street's sewer). Its trench deepened by that fall over the farthest stack's square run, and a
    # quarter more for its bends.
    exit_xy = [p[R + "sewer_exit_x_in"] * IN, p[R + "sewer_exit_y_ft"] * FT]
    foot = next(m for m in frame["members"] if m["kind"] == "footings"
                and min(b[0][0] for b in m["boxes"]) <= exit_xy[0] <= max(b[1][0] for b in m["boxes"])
                and min(b[0][1] for b in m["boxes"]) <= exit_xy[1] <= max(b[1][1] for b in m["boxes"]))
    edge = max(b[1][0] for b in foot["boxes"]) if exit_xy[0] < apt["depth_m"] / 2 else min(b[0][0] for b in foot["boxes"])
    inward = 1.0 if exit_xy[0] < apt["depth_m"] / 2 else -1.0
    bd = p[R + "drain_od_building_in"] * IN
    exit_ = [edge + inward * (bd / 2 + clear + v2), exit_xy[1], z_bldg]
    far = max(abs(s_["x"] - exit_[0]) + abs(s_["y"] - exit_[1]) for s_ in stack.values())
    deep = fall(4.0) * far * 1.25 + bd
    bz = [{**z_, "lo": [z_["lo"][0], z_["lo"][1], min(z_["lo"][2], z_bldg - deep)]} for z_ in slab_zone(apt, p)]
    out_box = _box([exit_[0] - v2, exit_[1] - 0.1, z_bldg - deep], [exit_[0] + v2, exit_[1] + 0.1, z_bldg])
    add("plumbing/building-drain", "drain", p[R + "drain_od_building_in"], exit_, [(col, [s_["x"], s_["y"], z_bldg]) for col, s_ in stack.items()],
        bz, attach=[s_["id"] for s_ in stack.values()] + ["*wc-bend", "plumbing/drain/1-*"], voxel=v2, role="building-drain",
        grade=-1, slope=fall(4.0), size_in=4.0, goals=[out_box], footing_top=max(b[1][2] for b in foot["boxes"]))
    fd = feeders(apt, p)
    annex = {x["id"]: x for x in apt["rooms"]["annex"]["parts"]}
    elec = next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/electrical")
    meter = [(elec["lo_m"][0] + elec["hi_m"][0]) / 2, annex["annex-right"]["hi_m"][1] + p[R + "meter_out_in"] * IN, z_feed]
    outside = _box([meter[0] - 0.6, annex["annex-right"]["lo_m"][1], -p[R + "under_slab_bottom_in"] * IN],
                   [meter[0] + 0.6, meter[1] + 0.15, -p[R + "under_slab_top_in"] * IN])
    for f_ in apt["flats"]:
        n = f_["name"]
        c = ch[column(n)]
        own = next((k for k in c["conduits"] if k["flat"] == n), None)
        y = own["y"] if own else c["panel_y"]
        cd = conduit_for([fd[n]["size"]] * 3 + [fd[n]["egc"]], p)
        add(f"electrical/feeder/{n}", "feeder", cd["od_in"], meter, [("riser", [c["x"], y, z_feed])], slab_zone(apt, p) + [outside],
            # It may touch the other feeders and its column's feeder risers: one trade's conduits, laid side by
            # side where they stub up into the partition.
            attach=["electrical/feeder/*", f"{column(n)}/feeder/*"], voxel=v2, flat=n, role="feeder", square_ft=fd[n]["ft"],
            # Straight at any angle (forge's `pull`): under the slab nothing holds a conduit to the
            # lattice, and NEC 352.26 counts its bends' degrees (D28 step 7e, Jon 2026-11-22).
            straight=True)

    # -- Each flat's branch circuits: up the panel's bay into the joists, to the far point of the rooms
    # each serves.
    for name in by_flat(apt):
        panel = eqb[f"{name}/panel"]
        c = ch[column(name)]
        cv = cavity(apt, name)
        pw = next(w for w in apt["rooms"]["walls"] if w["id"] == f"{name}/p4")
        bay = c["panel_bay"]
        col_zone = wall_cavity(apt, frame, pw, p, z0=panel["hi"][2], z1=cv["lo"][2] + 0.01, y0=bay[0], y1=bay[1])
        rooms = {r["id"].split("/")[1]: r for r in by_flat(apt)[name]}
        top = [c["x"], c["panel_y"], panel["hi"][2] + 0.04]
        for circ in flat_circuits(apt, p, name):
            if not circ["rooms"]:
                continue
            fx_, fy_ = _far_point(rooms, circ["rooms"], (c["x"], c["panel_y"]), p)
            add(f"electrical/branch/{name}/{circ['key']}", "cable", p[R + "nm_od_in"], top, [("far", [fx_, fy_, cv["lo"][2] + 0.03])],
                [col_zone, cv], attach=[f"{name}/panel", f"electrical/branch/{name}/*"], flat=name, role="branch", circuit=circ["key"],
                square_ft=circ["ft"], gap=cable_clear)

    # -- The line sets across the roof, from each riser's top to its outdoor unit.
    for u in units:
        ls = next(s_ for s_ in vs[u["column"]] if s_["id"].endswith(f"line-set/{u['flat']}"))
        zone = _box([min(ls["x"], u["lo"][0]) - 0.5, min(ls["y"], u["lo"][1]) - 0.5, roof_top],
                    [max(ls["x"], u["hi"][0]) + 0.5, max(ls["y"], u["hi"][1]) + 0.5, u["hi"][2]])
        end = u["lo"][1] if abs(u["lo"][1] - ls["y"]) < abs(u["hi"][1] - ls["y"]) else u["hi"][1]
        add(f"hvac/roof-line-set/{u['flat']}", "line-set", p[R + "line_set_od_in"], [ls["x"], ls["y"], roof_top + 0.05],
            [("unit", [(u["lo"][0] + u["hi"][0]) / 2, end + (0.05 if end == u["hi"][1] else -0.05), u["lo"][2] + 0.15])], [zone],
            attach=[ls["id"], u["id"]], flat=u["flat"], role="roof-line-set")

    rules = {
        "apa_table_m": [[a * IN, b * IN] for a, b in _apa_rows()], "apa_saf_m": p[R + "apa_saf_in"] * IN,
        "apa_min_edge_m": p[R + "apa_min_edge_in"] * IN, "apa_any_hole_m": p[R + "apa_any_hole_in"] * IN,
        "stud_nonbearing": p[R + "stud_hole_nonbearing"], "stud_bearing": p[R + "stud_hole_bearing"],
        "plate_nonbearing": p[R + "stud_hole_nonbearing"], "plate_bearing": p[R + "stud_hole_bearing"],
        "sawn_frac": p[R + "sawn_hole_frac"], "sawn_edge_m": p[R + "sawn_hole_edge_in"] * IN,
        "nonbearing": [_box(w["lo_m"], w["hi_m"]) for w in apt["rooms"]["walls"]]
        + [_box(x["lo_m"], x["hi_m"]) for x in apt["rooms"]["annex"]["parts"] if x["kind"] == "annex_partition"],
        "turn_cost_m": p[R + "turn_cost_ft"] * FT, "cross_cost_m": p[R + "cross_cost_ft"] * FT, "sleeve_cost_m": p[R + "sleeve_cost_ft"] * FT,
    }
    # The ERV's exhaust branches (to the bath's and kitchen's grilles) before its outdoor-air and
    # exhaust ducts, which then pass beside them: routed after, the pair can shut the kitchen's
    # grille between them (the middle storey's, round the strip's leg).
    order = {"arm": 0, "main": 1, "flat": 2, "erv-exhaust": 2.5, "erv-oa": 3, "erv-ea": 3, "ms-supply": 4, "condensate": 4.2, "erv-supply": 4.5, "drain": 6,
             "building-drain": 6, "vent": 7, "cold": 8, "hot": 8, "line-set": 9, "loop-supply": 11, "loop-return": 11,
             "hot-return": 8.5, "feeder": 13, "branch": 14, "roof-line-set": 15}
    reqs.sort(key=lambda r: (order.get(r.get("role", ""), 20), r.get("priority", 0), r["id"]))
    from .systems import latest_model
    body = {"schema": 1, "frame": str(FRAME.relative_to(OUT_DIR.parent)).replace("\\", "/"), "geometry_sha": _sha(latest_model()),
            "framing_sha": _sha(FRAME), "rules": rules, "obstacles": obstacles, "requests": reqs,
            "clash_voxel_m": p[R + "clash_voxel_in"] * IN, "clash_tol_m": p[R + "clash_tol_in"] * IN,
            "passes": int(p[R + "passes"])}
    body["requests_sha"] = hashlib.sha256(json.dumps(reqs, sort_keys=True).encode()).hexdigest()[:16]
    body["moved_heads"] = moved
    return body


def p_size(p: dict, part: str) -> str:
    """Step 6's sprinkler pipe sizes (the hydraulics' upsized ones), or 7c's where larger."""
    from .fire import SIZE_START, SIZES
    from .routed import grown

    step6 = _fire_sizes(p).get(part, SIZE_START[part])
    g = grown(p).get("fire", {}).get(part)
    return g if g and SIZES.index(g) > SIZES.index(step6) else step6


_FIRE: dict = {}  # step 6's sizes, by design (a process may work out both)


def _fire_sizes(p: dict) -> dict:
    from .designs import name

    d = name(p)
    if d not in _FIRE:
        from .fire import hydraulics
        from .systems import latest_model, load
        _FIRE[d] = hydraulics(load(latest_model()), p)["sizes"]
    return _FIRE[d]


def _cpvc_rows() -> list[dict]:
    from .loads import _table
    return _table("blazemaster_cpvc_sdr13_5.csv")


def _apa_rows() -> list[tuple[float, float]]:
    from .loads import _table
    return [(float(r["hole_in"]), float(r["min_dist_in"])) for r in _table("apa_z725e_table5_pri60_1178.csv")]


def _pw(apt: dict, name: str) -> dict:
    return next(w for w in apt["rooms"]["walls"] if w["id"] == f"{name}/plumbing-wall")


def _pw_x(apt: dict, frame: dict, name: str, p: dict) -> float:
    c = wall_cavity(apt, frame, _pw(apt, name), p)
    return (c["lo"][0] + c["hi"][0]) / 2


def _grilles(apt: dict, name: str, rooms: dict, z: float, p: dict, frac: float = 0.5) -> dict:
    """Where each room's duct ends in the soffits (m): a bedroom's at the hall's face of the partition
    between them (a high sidewall grille through it), the study's and the living room's at the
    hall's and the passage's open sides to them, the kitchen's and the bath's in the kitchen's and
    the utility closet's soffits (the bath's through the wall between them). `frac` places it along
    the side the rooms share, so two systems' grilles (the ERV's, the mini-split's) stand apart."""
    hall, pas, util, kit = rooms["hall"], rooms["passage"], rooms["utility"], rooms["kitchen"]
    ins = p[R + "grille_in_in"] * IN

    def toward(room: dict, frm: dict) -> list[float]:
        # The point inside `frm` (the soffit's room) nearest the shared side with `room`, at its middle.
        lo = [max(room["lo_m"][i], frm["lo_m"][i]) for i in range(2)]
        hi = [min(room["hi_m"][i], frm["hi_m"][i]) for i in range(2)]
        c = [(frm["lo_m"][i] + frm["hi_m"][i]) / 2 for i in range(2)]
        for i in range(2):
            if hi[i] - lo[i] < 0.2:  # the shared side is across this axis
                edge = frm["lo_m"][i] if abs(frm["lo_m"][i] - room["hi_m"][i]) < 0.2 else frm["hi_m"][i]
                c[i] = edge + (ins if edge == frm["lo_m"][i] else -ins)
                j = 1 - i
                s0, s1 = max(room["lo_m"][j], frm["lo_m"][j]), min(room["hi_m"][j], frm["hi_m"][j])
                c[j] = s0 + frac * (s1 - s0)
        return [c[0], c[1], z]

    return {"bed-1": toward(rooms["bed-1"], hall), "bed-2": toward(rooms["bed-2"], hall), "study": toward(rooms["study"], hall),
            "living": toward(rooms["living"], pas), "kitchen": [(kit["lo_m"][0] + kit["hi_m"][0]) / 2, (kit["lo_m"][1] + kit["hi_m"][1]) / 2, z],
            "bath": toward(rooms["bath"], util)}


def _far_point(rooms: dict, keys: list[str], xy: tuple[float, float], p: dict) -> tuple[float, float]:
    """A circuit's farthest point (step 5's: the corner of its rooms farthest from the panel,
    square), pulled into the room by `far_inset_in`."""
    best, at = -1.0, None
    for k in keys:
        r = rooms[k]
        for x in (r["lo_m"][0], r["hi_m"][0]):
            for y in (r["lo_m"][1], r["hi_m"][1]):
                d = abs(x - xy[0]) + abs(y - xy[1])
                if d > best:
                    best, at = d, (x, y, r)
    x, y, r = at
    i = p[R + "far_inset_in"] * IN
    return (x + i if x == r["lo_m"][0] else x - i, y + i if y == r["lo_m"][1] else y - i)


def clear_of_equipment(h: dict, eq: list[dict], rooms: list[dict], p: dict) -> tuple[float, float]:
    """A sprinkler at its room's cell centre (step 6) that falls under a piece of equipment (the
    mini-split in the hall's soffit) moves along the room's longer side just clear of it, by
    `head_clear_in`; else it stays."""
    x, y = h["xy"]
    room = next(r for r in rooms if r["id"] == h["room"])
    c = p[R + "head_clear_in"] * IN
    for e in eq:
        if e["lo"][0] - c < x < e["hi"][0] + c and e["lo"][1] - c < y < e["hi"][1] + c:
            along = 1 if room["hi_m"][1] - room["lo_m"][1] >= room["hi_m"][0] - room["lo_m"][0] else 0
            lo, hi = e["lo"][along] - c, e["hi"][along] + c
            pick = [v for v in (lo, hi) if room["lo_m"][along] < v < room["hi_m"][along]]
            v = min(pick, key=lambda v: abs(v - (x, y)[along]))
            x, y = (v, y) if along == 0 else (x, v)
    return x, y


def _row(h0: list[float], fixed: dict[int, float], a: float, b: float, L: float, smin: float) -> list[float] | None:
    """A row of sprinklers along one axis of a room [a, b]: positions nearest `h0` (sorted) with
    those in `fixed` set, the end ones within L/2 of the walls, neighbours at least `smin` and at
    most L apart (TY2236: 8 ft, and the coverage's side). None if there's no such row."""
    n = len(h0)
    lo = [a] * n
    hi = [b] * n
    lo[-1] = max(lo[-1], b - L / 2)
    hi[0] = min(hi[0], a + L / 2)
    for k, v in fixed.items():
        lo[k], hi[k] = max(lo[k], v), min(hi[k], v)

    def tighten() -> bool:
        for _ in range(n + 1):
            for i in range(1, n):
                lo[i] = max(lo[i], lo[i - 1] + smin)
                hi[i] = min(hi[i], hi[i - 1] + L)
            for i in range(n - 2, -1, -1):
                hi[i] = min(hi[i], hi[i + 1] - smin)
                lo[i] = max(lo[i], lo[i + 1] - L)
        return all(lo[i] <= hi[i] + 1e-9 for i in range(n))

    if not tighten():
        return None
    out = []
    for i in range(n):
        v = min(max(h0[i], lo[i]), hi[i])
        lo[i] = hi[i] = v
        if not tighten():
            return None
        out.append(v)
    return out


def respace_off_strips(heads: list[dict], xys: list[tuple[float, float]], cells: list, strips: list[dict], rooms: list[dict],
                       p: dict) -> tuple[list[tuple[float, float]], list]:
    """The sprinklers under the living room's strip soffit or its leg (the ERV's two ducts fill
    them, with no room for a drop beside them) move across it, `head_clear_in` past one side or
    the other, and the others in their row along that axis shift as little as keeps the row
    covering the room (TY2236's data sheet: 8 ft apart at least, at most the coverage's side, so
    each within half the side of the walls and of its neighbour's reach). Each head's cell along
    that axis is redrawn where its reach meets its neighbour's. Returns the new points and cells."""
    from itertools import product

    xys, cells = list(xys), [([*c[0]], [*c[1]]) for c in cells]
    c = p[R + "head_clear_in"] * IN
    smin = p[R + "head_min_spacing_ft"] * FT
    by_id = {r["id"]: r for r in rooms}
    for e in strips:
        across = 0 if e["hi"][0] - e["lo"][0] < e["hi"][1] - e["lo"][1] else 1
        other = 1 - across
        f0, f1 = e["lo"][across] - c, e["hi"][across] + c
        under = lambda xy: f0 < xy[across] < f1 and e["lo"][other] - c < xy[other] < e["hi"][other] + c  # noqa: E731
        if not any(under(xys[i]) for i in range(len(heads)) if heads[i]["room"] == e["room"]):
            continue
        room = by_id[e["room"]]
        a, b = room["lo_m"][across], room["hi_m"][across]
        rows: dict[float, list[int]] = {}
        for i, h in enumerate(heads):
            if h["room"] == e["room"]:
                rows.setdefault(round(xys[i][other], 3), []).append(i)
        for ids in rows.values():
            ids.sort(key=lambda i: xys[i][across])
            bad = [k for k, i in enumerate(ids) if under(xys[i])]
            if not bad:
                continue
            L = heads[ids[0]]["l_ft"] * FT
            h0 = [xys[i][across] for i in ids]
            best = None
            for pick in product((f0, f1), repeat=len(bad)):
                row = _row(h0, dict(zip(bad, pick)), a, b, L, smin)
                if row and not any(f0 < v < f1 for k, v in enumerate(row) if k not in bad):
                    cost = sum(abs(u - v) for u, v in zip(row, h0))
                    if best is None or cost < best[0]:
                        best = (cost, row)
            if best is None:
                continue  # left under it: the routes and the coverage check will say so
            row = best[1]
            for k, i in enumerate(ids):
                xy = list(xys[i])
                xy[across] = row[k]
                xys[i] = (xy[0], xy[1])
                lo_e = a if k == 0 else (max(row[k] - L / 2, row[k - 1]) + min(row[k - 1] + L / 2, row[k])) / 2
                hi_e = b if k == len(ids) - 1 else (max(row[k + 1] - L / 2, row[k]) + min(row[k] + L / 2, row[k + 1])) / 2
                cells[i][0][across], cells[i][1][across] = lo_e, hi_e
    return xys, cells


def spread_heads(heads: list[dict], xys: list[tuple[float, float]], cells: list, keep_out: list[dict], rooms: list[dict],
                 p: dict) -> list[tuple[float, float]]:
    """Two sprinklers in one compartment closer than `head_min_spacing_ft` (Tyco TFP403: 8 ft; step
    6's hall and study ones were 6.4 ft apart): one moves, the less far of the two, to the nearest
    point still covering its cell by its listed square, inside its room, clear of the keep-outs
    (equipment, the strip soffits) by `head_clear_in`, and 8 ft from every other in its
    compartment. Returns the new points (unchanged where none is found)."""
    xys = list(xys)
    smin = p[R + "head_min_spacing_ft"] * FT
    c = p[R + "head_clear_in"] * IN
    by_id = {r["id"]: r for r in rooms}
    step = 0.02

    def ok_at(i: int, q: tuple[float, float]) -> bool:
        if any(e["lo"][0] - c < q[0] < e["hi"][0] + c and e["lo"][1] - c < q[1] < e["hi"][1] + c for e in keep_out):
            return False
        return all(((q[0] - xys[j][0]) ** 2 + (q[1] - xys[j][1]) ** 2) ** 0.5 >= smin - 1e-9
                   for j in range(len(heads)) if j != i and heads[j]["comp"] == heads[i]["comp"])

    def options(i: int) -> list[tuple[float, float]]:
        L = heads[i]["l_ft"] * FT
        (lo, hi), r = cells[i], by_id[heads[i]["room"]]
        box = [(max(hi[k] - L / 2, r["lo_m"][k] + 0.1), min(lo[k] + L / 2, r["hi_m"][k] - 0.1)) for k in range(2)]
        if any(a > b + 1e-9 for a, b in box):
            return []
        nx, ny = (max(1, int((b - a) / step)) for a, b in box)
        pts = [(box[0][0] + (box[0][1] - box[0][0]) * u / nx, box[1][0] + (box[1][1] - box[1][0]) * v / ny)
               for u in range(nx + 1) for v in range(ny + 1)]
        return sorted((q for q in pts if ok_at(i, q)), key=lambda q: (q[0] - xys[i][0]) ** 2 + (q[1] - xys[i][1]) ** 2)

    for _ in range(3):
        moved = False
        for i in range(len(heads)):
            for j in range(i + 1, len(heads)):
                if heads[i]["comp"] != heads[j]["comp"]:
                    continue
                if ((xys[i][0] - xys[j][0]) ** 2 + (xys[i][1] - xys[j][1]) ** 2) ** 0.5 >= smin - 1e-9:
                    continue
                best = None
                for k in (i, j):
                    opt = options(k)
                    if opt:
                        d = ((opt[0][0] - xys[k][0]) ** 2 + (opt[0][1] - xys[k][1]) ** 2) ** 0.5
                        if best is None or d < best[0]:
                            best = (d, k, opt[0])
                if best:
                    xys[best[1]] = best[2]
                    moved = True
        if not moved:
            break
    return xys


def heads_covered(apt: dict, moved: dict) -> tuple[bool, float]:
    """Every moved sprinkler still covers its cell (step 6's layout: its room in equal cells, one
    sprinkler each) by its listed square: no point of the cell farther from it, along either side,
    than half the square's side. Returns (all covered, the farthest reach, ft)."""
    ok, worst = True, 0.0
    for name, ms in moved.items():
        for m in ms:
            if m["from"] == m["to"]:
                continue
            lo, hi = m["cell"]
            reach = max(max(abs(m["to"][i] - lo[i]), abs(hi[i] - m["to"][i])) for i in range(2)) / FT
            ok &= reach <= m["l_ft"] / 2 + 1e-9
            worst = max(worst, reach)
    return ok, worst


def joists_over(frame: dict, apt: dict, storey: int, x: float) -> list[tuple[float, float]]:
    """The joists over a storey (the floor above's, or the roof's) that pass over plan point x:
    each one's (y0, y1), sorted."""
    from .routing import _bounds, joists_under

    if storey < apt["storeys"]:
        return joists_under(frame, apt, storey + 1, x)
    out = []
    for m in frame["members"]:
        if m["kind"] == "roof joists" and m["storey"] == storey:
            lo, hi = _bounds(m)
            if hi[0] - lo[0] > hi[1] - lo[1] and lo[0] <= x <= hi[0]:
                out.append((lo[1], hi[1]))
    return sorted(out)


def wall_slots(apt: dict, frame: dict, wall: dict, x: float, pinned_ys: list[tuple[float, float]], gap: float) -> list[tuple[float, float]]:
    """A plumbing wall's free spans along it (m), for something going straight up it into the
    ceiling: its stud bays that are also bays between the joists over it, less its vertical
    services (centre, half width), a gap around each."""
    from .routing import _free, bays, studs_in

    st = studs_in(frame, wall["lo_m"], wall["hi_m"], wall["storey"])
    free = [(a[1] + gap, b[0] - gap) for a, b in zip(st, st[1:])]
    jb = [(a + gap, b - gap) for a, b in bays(joists_over(frame, apt, wall["storey"], x), wall["lo_m"][1], wall["hi_m"][1])]
    free = [(max(a, c), min(b, d)) for a, b in free for c, d in jb if min(b, d) > max(a, c)]
    return _free(free, [(y - h - gap, y + h + gap) for y, h in pinned_ys])


def take_slot(free: list[tuple[float, float]], y: float, half: float, taken: list[tuple[float, float]], gap: float) -> float:
    """The place nearest `y` where something `half` wide fits in `free`, clear of `taken`; it is
    added to `taken`."""
    from .routing import _free

    best = None
    for a, b in _free(free, [(t0 - gap, t1 + gap) for t0, t1 in taken]):
        lo, hi = a + half, b - half
        if lo <= hi + 1e-9:
            c = min(max(y, lo), hi)
            if best is None or abs(c - y) < abs(best - y):
                best = c
    if best is None:
        raise ValueError(f"no room in the wall for a {2 * half / IN:.2f} in. pipe near y = {y:.3f}")
    taken.append((best - half, best + half))
    return best


def _lanes(zones: list[dict], strip: dict, leg: dict, inside: float, facade_hi: bool, inner: bool) -> list[dict]:
    """A flat's zones with its strip soffit and the strip's leg cut to one duct's lane: the inner
    lane round the L's corner (`inside` -1 where the leg comes up from lower y), or the outer one.
    The inner lane: in from the kitchen's soffit across the leg's foot (its end over the kitchen),
    up the leg's half on the facade's side to the strip's middle, and along the strip's half on the
    corner's side from the leg's middle to the facade. The outer lane: in from the kitchen past
    that foot, up the leg's kitchen-side half, along the strip's other half. So the two ducts keep
    their order round the corner, and neither closes the other's way."""
    sm = (strip["lo"][1] + strip["hi"][1]) / 2
    lm = (leg["lo"][0] + leg["hi"][0]) / 2
    half = (leg["hi"][0] - leg["lo"][0]) / 2
    same = lambda a, b: all(abs(u - v) < 1e-6 for u, v in zip(a["lo"] + a["hi"], b["lo"] + b["hi"]))  # noqa: E731
    out = [z for z in zones if not same(z, strip) and not same(z, leg)]
    s_lo, s_hi, l_lo, l_hi = list(strip["lo"]), list(strip["hi"]), list(leg["lo"]), list(leg["hi"])
    corner_low = inside < 0  # the leg comes up from the kitchen at lower y; the corner's inside is low
    foot = (leg["lo"][1], leg["lo"][1] + half) if corner_low else (leg["hi"][1] - half, leg["hi"][1])
    if inner:
        s_lo[1], s_hi[1] = (s_lo[1], sm) if corner_low else (sm, s_hi[1])
        s_lo[0], s_hi[0] = (lm, s_hi[0]) if facade_hi else (s_lo[0], lm)
        l_lo[0], l_hi[0] = (lm, l_hi[0]) if facade_hi else (l_lo[0], lm)
        l_lo[1], l_hi[1] = (l_lo[1], sm) if corner_low else (sm, l_hi[1])
        out.append(_box([leg["lo"][0], foot[0], leg["lo"][2]], [leg["hi"][0], foot[1], leg["hi"][2]]))
    else:
        s_lo[1], s_hi[1] = (sm, s_hi[1]) if corner_low else (s_lo[1], sm)
        l_lo[0], l_hi[0] = (l_lo[0], lm) if facade_hi else (lm, l_hi[0])
        l_lo[1], l_hi[1] = (foot[1], l_hi[1]) if corner_low else (l_lo[1], foot[0])
    return out + [_box(s_lo, s_hi), _box(l_lo, l_hi)]


def write_requests(apt: dict, p: dict) -> Path:
    """The requests, to the design's own file (`designs.paths`), for forge's `routes-json`."""
    from .designs import paths

    path = paths(p)["requests"]
    path.parent.mkdir(parents=True, exist_ok=True)
    body = requests(apt, p)
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    return path
