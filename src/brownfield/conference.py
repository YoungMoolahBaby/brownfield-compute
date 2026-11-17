"""D17, step 2: the conference of communities on the real land. Jon, 2026-11-17: "communities that
are pulling heat and eating the food from the greenhouse ... like a conference of communities ...
your community can play the other community in your sport".

- **Homes by site.** Pass 4's newcomers who'd live near the campus (renting and buying, D16's rings)
  shared among AWS's six sites by their buildings (AWS: 50 staff a building a shift), in pass 4's
  base case and its high case.
- **Where they go.** On land with no constraint and under 15% slope (`land.analysis`), beyond the
  night-noise setback from every site and within a walk or a bike ride of their own, as close as
  that allows to the nearest existing town.
- **The glass.** The market sets how much greenhouse can be sold (pass 3d; `site.greenhouse_ha`), not
  the heat, so the campus's glass is shared among the sites by their homes and stands between each
  site and its community, as the community's food gate.
- **Third spaces.** A clubhouse in each community (a cafe, a court, a small gym, a workshop corner),
  and one arena for the conference (D16's community center: the rink, the big courts, the field),
  where the most people are. The leagues run between the communities and the towns already there.
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


def place(p: dict, a: dict, sites: dict, homes: dict, town: dict) -> dict[str, dict]:
    """Each community on flat, unconstrained land between the setback and the setback plus its reach
    from its own site, beyond the setback from every site, as near the nearest town as it can be,
    in one compact patch; communities don't share land."""
    g = a["grid"]
    rows, cols = np.mgrid[0:g.ny, 0:g.nx]
    X, Y = g.xy(cols, rows)
    ok = a["buildable"] & ~a["flags"]["sloping (15-25%)"]
    any_site = g.draw([s["footprint"] for s in sites.values()])
    d_any = g.distance(any_site, p[C + "setback_m"] + p[C + "reach_m"] + 100.0)
    ok &= d_any >= p[C + "setback_m"]
    taken = np.zeros(ok.shape, bool)
    out = {}
    tx = np.array([t["xy"] for t in town.values()])
    # The largest communities choose first.
    for name in sorted(sites, key=lambda k: -homes[k]["ha"]):
        own = g.distance(g.draw([sites[name]["footprint"]]), p[C + "setback_m"] + p[C + "reach_m"])
        cand = ok & ~taken & (own <= p[C + "setback_m"] + p[C + "reach_m"])
        if not cand.any():
            continue
        cx, cy = X[cand], Y[cand]
        dt = np.min(np.hypot(cx[:, None] - tx[None, :, 0], cy[:, None] - tx[None, :, 1]), axis=1)
        seed = int(np.argmin(dt))
        need = int(math.ceil(homes[name]["ha"] / g.cell_ha))
        order = np.argsort(np.hypot(cx - cx[seed], cy - cy[seed]))[:need]
        pick = np.zeros(cand.sum(), bool)
        pick[order] = True
        idx = np.flatnonzero(cand.ravel())[pick]
        taken.ravel()[idx] = True
        poly = cells_poly(g, idx, X, Y)
        near_town = min(town, key=lambda t: math.dist(town[t]["xy"], (poly.centroid.x, poly.centroid.y)))
        out[name] = {"poly": poly, "centre": (poly.centroid.x, poly.centroid.y), "town": near_town,
                     "town_m": math.dist(town[near_town]["xy"], (poly.centroid.x, poly.centroid.y)),
                     "site_m": float(own.ravel()[idx].min()), "undermined": float(a["flags"]["undermined"].ravel()[idx].mean())}
    return out


def glass(p: dict, homes: dict) -> dict[str, float]:
    """The campus's market-limited glass (ha) shared among the sites by their homes."""
    tot = sum(h["homes"] for h in homes.values())
    return {k: p["site.greenhouse_ha"] * h["homes"] / tot for k, h in homes.items()}


def arena(p: dict, a: dict, comm: dict, homes: dict, town: dict, sites: dict) -> tuple[float, float]:
    """The conference's arena: on flat, unconstrained land beyond the setback, nearest the middle of
    everyone (the communities' and the towns' people)."""
    w = [(c["centre"], homes[k]["people"]) for k, c in comm.items()] + [(t["xy"], t["people"]) for t in town.values()]
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


def report(p: dict, base: dict, high: dict, comm: dict, town: dict, gl: dict, ar: tuple) -> str:
    g = "village.growth_limits."
    L = ["**The conference of communities** (D17: a community at each of AWS's six sites, sized by its share of the jobs)", "",
         f"Homes keep {p[C + 'setback_m']:,.0f} m from AWS's buildings (pass 2's conventional cooling at night); each community stands "
         f"within {p[C + 'reach_m']:,.0f} m beyond that of its site, on flat land with no constraint, as near a town as it can be.", "",
         "| Site | Buildings | Jobs | Homes (base) | People | School children | Land | Homes (high case) | Glass | Nearest town |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for k, h in base.items():
        c = comm.get(k)
        where = f"{c['town']}, {c['town_m'] / 1000:.1f} km" if c else "no room found"
        L.append(f"| {k} | {h['buildings']} | {h['jobs']:.0f} | {h['homes']} ({h['flats']} flats, {h['townhouses']} townhouses, "
                 f"{h['houses']} houses) | {h['people']:.0f} | {h['children']:.0f} | {h['ha']:.1f} ha | {high[k]['homes']} | "
                 f"{gl[k]:.1f} ha | {where} |")
    hb, hh = sum(h["homes"] for h in base.values()), sum(h["homes"] for h in high.values())
    people = sum(h["people"] for h in base.values())
    kids = sum(h["children"] for h in base.values())
    tpeople = sum(t["people"] for t in town.values())
    cl = clubhouse(p)
    L += [f"| **All six** | **{sum(h['buildings'] for h in base.values())}** | **{sum(h['jobs'] for h in base.values()):,.0f}** | "
          f"**{hb}** | **{people:,.0f}** | **{kids:.0f}** | **{sum(h['ha'] for h in base.values()):.1f} ha** | **{hh}** | "
          f"**{sum(gl.values()):.1f} ha** | |", "",
          f"- The towns already there: " + ", ".join(f"{k} {t['people']:,.0f}" for k, t in town.items())
          + f": {tpeople:,.0f} people, against {people:,.0f} in the new communities (base case).",
          f"- Over old mines: " + ", ".join(f"{k} {c['undermined']:.0%}" for k, c in comm.items()) + " of each community's land.",
          f"- A clubhouse ({p[C + 'clubhouse_ft2']:,.0f} ft2) costs about ${cl['build'] / 1e6:,.1f}M to build and "
          f"${cl['run'] / 1e3:,.0f}k a year to run ({cl['fte']:.1f} full-time posts); six cost ${6 * cl['build'] / 1e6:,.0f}M and "
          f"${6 * cl['run'] / 1e6:,.1f}M a year: ${6 * cl['run'] / hb:,.0f} a home a year in the base case, ${6 * cl['run'] / hh:,.0f} "
          "in the high case.",
          f"- The arena (D16's community center, rink and field) stands at {ar[0] / 1000:.1f} km east, {ar[1] / 1000:.1f} km north of "
          "the old plant, nearest the middle of everyone.",
          f"- Limits: {hb} new homes in the base case and {hh} in the high case, against room for about "
          f"{p[g + 'sewer_spare_mgd'] * 1e6 / (p[g + 'sewer_avg_flow_mgd'] * 1e6 / p[g + 'sewer_residential_customers']):,.0f} on "
          f"Homer City's sewage plant; about {kids / 13:.0f} school children a grade in the base case against Homer-Center's "
          f"~{p[g + 'school_cohort_per_grade']:.0f}."]
    return "\n".join(L)


# The towns grouped as the conference's members, by where they stand: Homer City with Lucerne Mines just
# north of it; the villages by Route 119 south-east of the plant (Graceton, Coral); Black Lick to the south.
MEMBERS = {"Homer City and Lucerne Mines": ("Homer City", "Lucerne Mines"), "Graceton and Coral": ("Graceton", "Coral"),
           "Black Lick": ("Black Lick",)}


def members(p: dict, comm: dict, homes: dict, town: dict) -> dict[str, dict]:
    """The conference as the towns already there, each with the new homes that stand nearest it: their
    people, households and the cost a household of a clubhouse each."""
    hh_per = p["site.visits.persons_per_home"]
    out = {}
    cl = clubhouse(p)
    for m, names in MEMBERS.items():
        new = [k for k, c in comm.items() if c["town"] in names]
        people0 = sum(town[n]["people"] for n in names if n in town)
        new_people = sum(homes[k]["people"] for k in new)
        new_homes = sum(homes[k]["homes"] for k in new)
        households = people0 / hh_per + new_homes
        out[m] = {"towns": names, "sites": new, "people": people0 + new_people, "new_people": new_people, "new_homes": new_homes,
                  "households": households, "clubhouse_per_household": cl["run"] / households if households else math.inf}
    return out


def gates(p: dict, a: dict, sites: dict, comm: dict, gl: dict) -> dict:
    """Each site's share of the glass as a block on flat, dry land within 300 m of the site (`glass_ok`),
    grown from the side facing its community: its food gate."""
    g = a["grid"]
    rows, cols = np.mgrid[0:g.ny, 0:g.nx]
    X, Y = g.xy(cols, rows)
    ok = glass_ok(a)
    taken = np.zeros(ok.shape, bool)
    out = {}
    for name, c in comm.items():
        own = g.distance(g.draw([sites[name]["footprint"]]), 310.0)
        cand = ok & ~taken & (own <= 300.0)
        if not cand.any():
            continue
        cx, cy = X[cand], Y[cand]
        seed = int(np.argmin(np.hypot(cx - c["centre"][0], cy - c["centre"][1])))
        need = int(math.ceil(gl[name] * 1e4 / (g.cell_ha * 1e4)))
        order = np.argsort(np.hypot(cx - cx[seed], cy - cy[seed]))[:need]
        idx = np.flatnonzero(cand.ravel())[order]
        taken.ravel()[idx] = True
        out[name] = cells_poly(g, idx, X, Y)
    return out


def members_report(p: dict, mem: dict) -> str:
    cl = clubhouse(p)
    L = ["", "**The conference as the towns already there** (each community joins the town it stands nearest; one clubhouse a member)", "",
         "| Member | Towns | New homes from | People (new) | Households | A clubhouse's running cost a household a year |",
         "|---|---|---|---|---|---|"]
    for m, r in mem.items():
        L.append(f"| {m} | {', '.join(r['towns'])} | {', '.join(r['sites']) or 'none'} | {r['people']:,.0f} ({r['new_people']:,.0f}) | "
                 f"{r['households']:,.0f} | ${r['clubhouse_per_household']:,.0f} |")
    hh = sum(r["households"] for r in mem.values())
    L += ["", f"Three clubhouses cost ${3 * cl['run'] / 1e6:,.1f}M a year to run, ${3 * cl['run'] / hh:,.0f} a household across the "
          f"conference's {hh:,.0f} households, against ${6 * cl['run'] / 1e6:,.1f}M for six apart."]
    return "\n".join(L)
