"""D17-D18: the conference of communities on the real land. Jon, 2026-11-17: "communities that are
pulling heat and eating the food from the greenhouse ... like a conference of communities ... your
community can play the other community in your sport"; then "draw the 3D homes and clubhouses".

- **The jobs by site.** AWS's six sites share pass 4's jobs by their buildings (AWS: 50 staff a
  building a shift), and the campus's glass by the same shares: each site's food gate (`gates`).
- **The homes by town (D18).** D17 put each site's homes beside it, which left Bruner's 74 in the woods
  3 km from Homer City. The newcomers instead join the towns already there in proportion to their
  people (`town_homes`), so every town grows by the same share and none is doubled; each town's homes
  are laid out at its edge on the real ground (`neighbourhood`).
- **Third spaces.** A clubhouse (a cafe, a court, a fitness room, a workshop) for each member that can
  run one for under `clubhouse_max_usd_household` a household a year; one arena for the conference
  (D16's community center: the rink, the big courts, the field), where the most people are. The
  leagues run between the members.
"""

from __future__ import annotations

import math

import numpy as np

C = "village.conference."
TOWNS = {"Homer City": "homer_city", "Black Lick": "black_lick", "Lucerne Mines": "lucerne_mines", "Coral": "coral",
         "Graceton": "graceton"}
KINDS = ("flats", "townhouses", "houses")
DEMAND_HIGH = ("pass4.demand.jobs", "pass4.demand.movers_share", "pass4.demand.induced_per_job", "pass4.demand.induced_movers_share")


def high_case(p: dict, params: dict) -> dict:
    """Pass 4's demand inputs at their high ends (more jobs, more of them filled by movers)."""
    return dict(p, **{k: params[k].high for k in DEMAND_HIGH})


def area_per_home(p: dict) -> dict[str, float]:
    """m2 of land a home takes in each ring, streets and greens in (D16's layouts)."""
    from . import rings

    c = rings.counts(p)
    out = {}
    for k in KINDS:
        r = rings.rect(p, k)
        out[k] = (r[1] - r[0]) * (r[3] - r[2]) / (c["flats"] if k == "flats" else c[k])
    return out


def site_homes(p: dict, sites: dict) -> dict[str, dict]:
    """Each site's share of the homes, by type, its people and school children, and the land it takes."""
    from . import rings

    c = rings.counts(p)
    n = {k: s["n"] for k, s in sites.items()}
    tot = sum(n.values())
    names = list(sites)
    share = [n[k] / tot for k in names]
    per = {kind: rings._apportion(c["flats"] if kind == "flats" else c[kind], share) for kind in KINDS}
    flat_beds = [rings._apportion(nb, share) for nb in c["flats_by_bed"]]
    apm = area_per_home(p)
    out = {}
    for i, k in enumerate(names):
        cc = dict(c, flats_by_bed=[fb[i] for fb in flat_beds], flats=per["flats"][i], townhouses=per["townhouses"][i], houses=per["houses"][i])
        homes = cc["flats"] + cc["townhouses"] + cc["houses"]
        out[k] = {"homes": homes, **{kind: cc[kind] for kind in KINDS}, "people": sum(rings.persons(p, cc).values()),
                  "children": sum(rings.children(p, cc).values()), "ha": sum(cc[kind] * apm[kind] for kind in KINDS) / 1e4,
                  "jobs": p["pass4.demand.jobs"] * n[k] / tot, "buildings": n[k]}
    return out


def town_homes(p: dict, town: dict) -> dict[str, dict]:
    """D18: the newcomers shared among the towns by their people, so every town grows by the same
    share and none is doubled; each town's homes by type (D16's mix), people and school children."""
    from . import rings

    c = rings.counts(p)
    names = list(town)
    tot = sum(town[k]["people"] for k in names)
    share = [town[k]["people"] / tot for k in names]
    flat_beds = [rings._apportion(nb, share) for nb in c["flats_by_bed"]]
    per = {kind: rings._apportion(c[kind], share) for kind in ("townhouses", "houses")}
    apm = area_per_home(p)
    out = {}
    for i, k in enumerate(names):
        fb = [b[i] for b in flat_beds]
        cc = dict(c, flats_by_bed=fb, flats=sum(fb), townhouses=per["townhouses"][i], houses=per["houses"][i])
        homes = cc["flats"] + cc["townhouses"] + cc["houses"]
        people = sum(rings.persons(p, cc).values())
        out[k] = {"homes": homes, "flats_by_bed": fb, **{kind: cc[kind] for kind in KINDS}, "people": people,
                  "children": sum(rings.children(p, cc).values()), "ha": sum(cc[kind] * apm[kind] for kind in KINDS) / 1e4,
                  "growth": people / town[k]["people"]}
    return out


def towns(p: dict, layers: dict) -> dict[str, dict]:
    """The towns already there, their middles (m from the plant) and people."""
    from shapely.geometry import shape

    from .homes import Local
    from .land import PLANT

    loc = Local(*PLANT)
    out = {}
    for key in ("places", "cdps"):
        for f in layers[key]:
            name = f["properties"]["BASENAME"]
            if name in TOWNS:
                c = loc.geom(shape(f["geometry"])).representative_point()
                out[name] = {"xy": (c.x, c.y), "people": p[C + "town_pop_" + TOWNS[name]]}
    return out


def cells_poly(g, idx: np.ndarray, X: np.ndarray, Y: np.ndarray):
    """The chosen cells as one outline (each cell its own square, joined), so the area is the cells'."""
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union

    hx, hy = g.dx / 2 + 0.01, g.dy / 2 + 0.01
    xs, ys = X.ravel()[idx], Y.ravel()[idx]
    return unary_union([sbox(x - hx, y - hy, x + hx, y + hy) for x, y in zip(xs, ys)]).simplify(1.0)


def window_share(mask: np.ndarray, half: int) -> np.ndarray:
    """The share of cells in each cell's (2 half + 1) square that are in the mask (summed-area table)."""
    s = np.pad(mask.astype(float), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ny, nx = mask.shape
    r0, r1 = np.clip(np.arange(ny) - half, 0, ny), np.clip(np.arange(ny) + half + 1, 0, ny)
    c0, c1 = np.clip(np.arange(nx) - half, 0, nx), np.clip(np.arange(nx) + half + 1, 0, nx)
    tot = s[r1][:, c1] - s[r0][:, c1] - s[r1][:, c0] + s[r0][:, c0]
    area = (r1 - r0)[:, None] * (c1 - c0)[None, :]
    return tot / area


def glass_ok(a: dict) -> np.ndarray:
    """Land glass can stand on: flat, dry, not steep, and not on homes, the power block or a site (the
    wells' setbacks are for homes, not glasshouses)."""
    m = a["masks"]
    bad = np.zeros(a["buildable"].shape, bool)
    for k in ("steep slopes", "flood zone", "wetlands", "streams", "lakes and ponds", "coal refuse", "abandoned mine land",
              "transmission lines", "existing homes", "AWS's sites", "the power block"):
        bad |= m[k]
    return ~bad & ~a["flags"]["sloping (15-25%)"] & ~np.isnan(a["grid"].z)


def glass(p: dict, homes: dict) -> dict[str, float]:
    """The campus's market-limited glass (ha) shared among the sites by their homes."""
    tot = sum(h["homes"] for h in homes.values())
    return {k: p["site.greenhouse_ha"] * h["homes"] / tot for k, h in homes.items()}


def arena(p: dict, a: dict, where: dict, th: dict, town: dict, sites: dict) -> tuple[float, float]:
    """The conference's arena: on flat, unconstrained land beyond the setback, nearest the middle of
    everyone (each town's people where they are, and its newcomers at their new homes, `where`)."""
    w = [(where[k], th[k]["people"]) for k in where] + [(t["xy"], t["people"]) for t in town.values()]
    mx = sum(xy[0] * n for xy, n in w) / sum(n for _, n in w)
    my = sum(xy[1] * n for xy, n in w) / sum(n for _, n in w)
    g = a["grid"]
    rows, cols = np.mgrid[0:g.ny, 0:g.nx]
    X, Y = g.xy(cols, rows)
    ok = a["buildable"] & ~a["flags"]["sloping (15-25%)"]
    ok &= g.distance(g.draw([s["footprint"] for s in sites.values()]), p[C + "setback_m"] + 10.0) >= p[C + "setback_m"]
    # Room for the centre, the rink, the field and the car park: a 300 m square mostly buildable and flat.
    ok &= window_share(ok, int(150.0 / g.dx)) >= 0.8
    d = np.where(ok, np.hypot(X - mx, Y - my), np.inf)
    i = int(np.argmin(d))
    return float(X.ravel()[i]), float(Y.ravel()[i])


def clubhouse(p: dict) -> dict[str, float]:
    """A clubhouse to build and to run a year."""
    build = p[C + "clubhouse_ft2"] * p["village.community_center.rec_center_build_usd_ft2"]
    fte = p[C + "clubhouse_posts"] * p["village.membership.day_h"] * 365.0 / p["village.membership.fte_h"]
    return {"build": build, "run": fte * p["village.membership.opex_per_fte"], "fte": fte}


def report(p: dict, sites_h: dict, base: dict, high: dict, town: dict, lays: dict, gl: dict, ar: tuple, a: dict) -> str:
    """The jobs and glass by site; the homes by town, where they stand and what they need."""
    import math as _m

    g = "village.growth_limits."
    L = ["**The jobs and the glass, by AWS's site**", "",
         "| Site | Buildings | Jobs | Glass (its food gate) |", "|---|---|---|---|"]
    for k, h in sites_h.items():
        L.append(f"| {k} | {h['buildings']} | {h['jobs']:.0f} | {gl[k]:.1f} ha |")
    L += [f"| **All six** | **{sum(h['buildings'] for h in sites_h.values())}** | **{sum(h['jobs'] for h in sites_h.values()):,.0f}** | "
          f"**{sum(gl.values()):.1f} ha** |", "",
          "**The new homes, by town** (D18: shared by the towns' people, so each grows by the same share; laid out at its edge)", "",
          "| Town | People now | New homes (base) | People | School children | Growth | Homes (high case) | Lots | Clusters | "
          "From the town's middle | Over old mines |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    grid = a["grid"]
    for k, h in base.items():
        lay = lays.get(k)
        homes_lots = [l for l in lay.lots if l.kind != "club"] if lay else []
        if homes_lots:
            cx, cy = lay.centre()
            d = _m.dist((cx, cy), town[k]["xy"])
            und = grid.draw([l.polygon() for l in homes_lots]) & a["flags"]["undermined"]
            under = und.sum() / max(1, grid.draw([l.polygon() for l in homes_lots]).sum())
            where, mines, n = f"{d / 1000:.1f} km", f"{under:.0%}", len(lay.mouths) - (1 if any(l.kind == "club" for l in lay.lots) else 0)
        else:
            where, mines, n = "not placed", "", 0
        mix = ", ".join(f"{h[kd]} {kd if h[kd] != 1 else kd[:-1]}" for kd in KINDS)
        L.append(f"| {k} | {town[k]['people']:,.0f} | {h['homes']} ({mix}) | "
                 f"{h['people']:.0f} | {h['children']:.0f} | {h['growth']:.0%} | {high[k]['homes']} | {len(homes_lots)} | {n} | {where} | {mines} |")
    hb, hh = sum(h["homes"] for h in base.values()), sum(h["homes"] for h in high.values())
    people = sum(h["people"] for h in base.values())
    kids = sum(h["children"] for h in base.values())
    tpeople = sum(t["people"] for t in town.values())
    missing = {k: lay.missing() for k, lay in lays.items() if lay.missing()}
    L += [f"| **All five** | **{tpeople:,.0f}** | **{hb}** | **{people:,.0f}** | **{kids:.0f}** | **{people / tpeople:.0%}** | **{hh}** | | | | |", "",
          "- Every home placed." if not missing else f"- Not placed: {missing}.",
          f"- Homes keep {p[C + 'setback_m']:,.0f} m from AWS's buildings (pass 2's conventional cooling at night), {p[C + 'building_clear_m']:.0f} m "
          f"from existing buildings and 30 m from US 119 and US 22; each lot is at least 95% clear land, within a {p[C + 'walk_m']:.0f} m walk "
          f"of its spine's mouth, and its building's ground falls no more than {p[C + 'pad_fall_max_m']:.1f} m.",
          f"- The arena (D16's community center, rink and field) stands at {ar[0] / 1000:.1f} km east, {ar[1] / 1000:.1f} km north of "
          "the old plant, nearest the middle of everyone.",
          f"- Limits: {hb} new homes in the base case and {hh} in the high case, against room for about "
          f"{p[g + 'sewer_spare_mgd'] * 1e6 / (p[g + 'sewer_avg_flow_mgd'] * 1e6 / p[g + 'sewer_residential_customers']):,.0f} on "
          f"Homer City's sewage plant; about {kids / 13:.0f} school children a grade in the base case against Homer-Center's "
          f"~{p[g + 'school_cohort_per_grade']:.0f}."]
    return "\n".join(L)


def clubs_report(p: dict, lays: dict, town: dict) -> str:
    """Where each clubhouse stands."""
    import math as _m

    L = []
    for k, lay in lays.items():
        for c in (l for l in lay.lots if l.kind == "club"):
            d = _m.dist((c.x, c.y), town[k]["xy"])
            near = _m.dist((c.x, c.y), lay.centre())
            L.append(f"- {k}'s clubhouse stands {d:,.0f} m from the town's middle and {near:,.0f} m from the middle of its new homes.")
    return "\n".join(L)


# The towns grouped as the conference's members, by where they stand: Homer City with Lucerne Mines just
# north of it; the villages by Route 119 south-east of the plant (Graceton, Coral); Black Lick to the south.
MEMBERS = {"Homer City and Lucerne Mines": ("Homer City", "Lucerne Mines"), "Graceton and Coral": ("Graceton", "Coral"),
           "Black Lick": ("Black Lick",)}


def members(p: dict, th: dict, town: dict) -> dict[str, dict]:
    """The conference as the towns already there, each with its new homes (`town_homes`): people,
    households, and a clubhouse where it costs a household no more than `clubhouse_max_usd_household`
    a year to run (in its largest town); a member without one plays at the arena."""
    hh_per = p["site.visits.persons_per_home"]
    out = {}
    cl = clubhouse(p)
    for m, names in MEMBERS.items():
        names = tuple(n for n in names if n in town)
        people0 = sum(town[n]["people"] for n in names)
        new_people = sum(th[n]["people"] for n in names)
        new_homes = sum(th[n]["homes"] for n in names)
        households = people0 / hh_per + new_homes
        per = cl["run"] / households if households else math.inf
        out[m] = {"towns": names, "people": people0 + new_people, "new_people": new_people, "new_homes": new_homes,
                  "households": households, "clubhouse_per_household": per,
                  "clubhouse": per <= p[C + "clubhouse_max_usd_household"],
                  "club_town": max(names, key=lambda n: town[n]["people"]) if names else None}
    return out


def club_towns(mem: dict) -> set[str]:
    return {r["club_town"] for r in mem.values() if r["clubhouse"]}


def gates(p: dict, a: dict, sites: dict, toward: dict, gl: dict) -> dict:
    """Each site's share of the glass as a block on flat, dry land within 300 m of the site (`glass_ok`),
    grown from the side facing `toward` (the nearest town's new homes): its food gate."""
    g = a["grid"]
    rows, cols = np.mgrid[0:g.ny, 0:g.nx]
    X, Y = g.xy(cols, rows)
    ok = glass_ok(a)
    taken = np.zeros(ok.shape, bool)
    out = {}
    for name, xy in toward.items():
        own = g.distance(g.draw([sites[name]["footprint"]]), 310.0)
        cand = ok & ~taken & (own <= 300.0)
        if not cand.any():
            continue
        cx, cy = X[cand], Y[cand]
        seed = int(np.argmin(np.hypot(cx - xy[0], cy - xy[1])))
        need = int(math.ceil(gl[name] * 1e4 / (g.cell_ha * 1e4)))
        order = np.argsort(np.hypot(cx - cx[seed], cy - cy[seed]))[:need]
        idx = np.flatnonzero(cand.ravel())[order]
        taken.ravel()[idx] = True
        out[name] = cells_poly(g, idx, X, Y)
    return out


def members_report(p: dict, mem: dict) -> str:
    cl = clubhouse(p)
    L = ["", "**The conference as the towns already there** (D18: the new homes shared among the towns by their people; "
         f"a clubhouse where it costs a household under ${p[C + 'clubhouse_max_usd_household']:,.0f} a year to run)", "",
         "| Member | Towns | New homes | People (newcomers) | Households | A clubhouse's running cost a household a year | Home ground |",
         "|---|---|---|---|---|---|---|"]
    for m, r in mem.items():
        home = f"its clubhouse, in {r['club_town']}" if r["clubhouse"] else "the arena"
        L.append(f"| {m} | {', '.join(r['towns'])} | {r['new_homes']} | {r['people']:,.0f} ({r['new_people']:,.0f}) | "
                 f"{r['households']:,.0f} | ${r['clubhouse_per_household']:,.0f} | {home} |")
    hh = sum(r["households"] for r in mem.values())
    n = sum(r["clubhouse"] for r in mem.values())
    L += ["", f"{n} clubhouses cost ${n * cl['build'] / 1e6:,.1f}M to build and ${n * cl['run'] / 1e6:,.2f}M a year to run: "
          f"${n * cl['run'] / hh:,.0f} a household across the conference's {hh:,.0f} households."]
    return "\n".join(L)


def heat(p: dict, wx: dict, th: dict, lays: dict, sites: dict) -> dict[str, dict]:
    """D18: each town's new homes on a warm loop from AWS's nearest building, against their own heat
    pumps (pass 3's comparison, `rings.loop_vs_heat_pump`, 20 years a home). The main is the straight
    line from the nearest site's drawn development to the homes' middle: the shortest it could be."""
    from shapely.geometry import Point

    from . import rings

    out = {}
    for k, lay in lays.items():
        n = th[k]["homes"]
        if not n:
            continue
        km = min(s["footprint"].distance(Point(lay.centre())) for s in sites.values()) / 1000.0
        row = {"homes": n, "main_km": km}
        for kind, b in (("flats", 2), ("townhouses", 2)):
            r = rings.loop_vs_heat_pump(p, wx["t"], kind, b, homes=n, main_km=km)
            row[kind] = {"loop": r["A"], "operator": r["A_operator"], "heat_pump": r["B"], "main": r["main"]}
        out[k] = row
    return out


def heat_report(p: dict, h: dict) -> str:
    L = ["", "**Heat for the new homes** (D18: a warm loop from AWS's nearest building, against each home's own heat pump; "
         f"pass 3's comparison, {p['cost.money.life_yr']:g} years a home)", "",
         "| Town | New homes | Main, at the least | Two-bed flat: loop | its own heat pump | Townhouse: loop | its own heat pump |",
         "|---|---|---|---|---|---|---|"]
    for k, r in h.items():
        f, t = r["flats"], r["townhouses"]
        L.append(f"| {k} | {r['homes']} | {r['main_km']:.1f} km | ${f['loop']:,.0f} | ${f['heat_pump']:,.0f} | ${t['loop']:,.0f} | "
                 f"${t['heat_pump']:,.0f} |")
    lo = min(r["flats"]["main"] for r in h.values())
    hi = max(r["flats"]["main"] for r in h.values())
    k0 = min(r["main_km"] for r in h.values())
    k1 = max(r["main_km"] for r in h.values())
    L += ["", f"The main alone comes to ${lo:,.0f}-{hi:,.0f} a home: at the towns' edges, {k0:.1f}-{k1:.1f} km from AWS's buildings, every "
          "new home heats itself with a heat pump. The loop's heat belongs to the food gates' glass at the sites."]
    return "\n".join(L)
