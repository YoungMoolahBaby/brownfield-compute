"""Pass 3b: embodied carbon (cradle to gate, A1-A3) and installed cost of the walk-up's three
structures, from the quantities in their CortenForge models.

What's counted is the structure: framing or block and planks, sheathing and subfloor (framed
systems), the ceilings the floors need underneath (rated gypsum under framed floors, a skim and
paint under planks), and the foundation. What's the same in all three is left out (the radiant
floor's gypsum topping, finishes, windows, services), and so is the exterior wall's insulation and
cladding, which differs (block has no stud cavity to fill) but isn't structure.

Carbon factors are industry averages from the Carbon Leadership Forum's North American Material
Baselines (via Washington's proposed code table); the planks are estimated from their concrete and
strand. Carbon stored in the wood is reported beside the A1-A3 total, not netted against it. Costs
are installed unit costs from public but mostly consumer-grade sources: low confidence, wide
ranges; the Monte Carlo and the tornado say which of them decide the ranking.
"""

from __future__ import annotations

import json

import numpy as np

from . import OUT_DIR

M2_FT2 = 10.7639
SYSTEMS = ("wood", "steel", "masonry")


def _read(name: str) -> dict:
    path = OUT_DIR / "pass3" / name
    if not path.exists():
        raise SystemExit(f"no {path}: run forge `framing`, `framing steel` and `masonry` first")
    return json.loads(path.read_text(encoding="utf-8"))


def quantities() -> dict:
    """Material quantities of the three structures, from the models."""
    apt = _read("apartment.json")
    wf, sf, mm = _read("framing.json"), _read("framing_steel.json"), _read("masonry_model.json")
    kind = {r["kind"]: r for r in wf["by_kind"]}
    sawn = sum(kind[k]["m3"] for k in ("studs", "king studs", "jack studs", "cripples", "plates", "cap plates",
                                       "rough sills", "headers (plies)", "roof joists"))
    L, D, H = apt["length_m"], apt["depth_m"], apt["storey_m"] * apt["storeys"]
    glazing = sum(f["glazed_m2"] for f in apt["flats"])
    ext_gross = 2 * (L + D) * H
    # The framed walls inside: two rows each for the spine and the stair walls, every storey.
    fl, t, p = apt["flat_len_m"], apt["ext_t_m"], apt["party_t_m"]
    spine_row = fl - t - p / 2  # the end wall's face to the stair wall's face
    stair_row = D - 2 * t
    int_walls = (4 * spine_row + 4 * stair_row) * H
    deck = mm["plank_m2"]  # floors and roof, the same area whichever system carries it
    sheathing = ext_gross - glazing - 6.0  # the stair core's door and windows ~6 m2
    return {
        "wood": {"sawn_m3": sawn, "ijoist_m3": kind["floor joists"]["m3"], "rim_m3": kind["rim boards"]["m3"],
                 "osb_m3": sheathing * 0.0111 + deck * 0.0183, "foundation_m3": wf["concrete_m3"],
                 "wood_m3": wf["wood_m3"]},
        "steel": {"cfs_t": sf["steel_kg"] / 1e3, "osb_m3": sheathing * 0.0111 + deck * 0.0183, "foundation_m3": sf["concrete_m3"]},
        "masonry": {"block_kg": mm["block_t"] * 1e3, "wall_m2": mm["blocks_full_equivalent"] * 0.4064 * 0.2032,
                    "lintel_m3": mm["lintel_t"] / 2.3, "lintels": mm["lintels"], "plank_m2": mm["plank_m2"],
                    "foundation_m3": mm["foundation_concrete_m3"]},
        "areas": {"ext_wall_gross_m2": ext_gross, "int_wall_m2": int_walls, "sheathing_m2": sheathing, "deck_m2": deck,
                  "gfa_m2": L * D * apt["storeys"]},
    }


def carbon(q: dict, p: dict) -> dict[str, dict[str, float]]:
    """kg CO2e (A1-A3) by system and part."""
    c = "pass3.carbon."
    w, s, m = q["wood"], q["steel"], q["masonry"]
    cmu_concrete_m3 = m["block_kg"] / p[c + "cmu_density_kg_m3"]
    return {
        "wood": {"sawn lumber": w["sawn_m3"] * p[c + "lumber_kg_m3"], "I-joists": w["ijoist_m3"] * p[c + "ijoist_kg_m3"],
                 "rim boards": w["rim_m3"] * p[c + "rim_kg_m3"], "OSB sheathing and subfloor": w["osb_m3"] * p[c + "osb_kg_m3"],
                 "foundation": w["foundation_m3"] * p[c + "readymix_kg_m3"]},
        "steel": {"cold-formed steel": s["cfs_t"] * p[c + "cfs_kg_t"], "OSB sheathing and subfloor": s["osb_m3"] * p[c + "osb_kg_m3"],
                  "foundation": s["foundation_m3"] * p[c + "readymix_kg_m3"]},
        "masonry": {"concrete block": cmu_concrete_m3 * p[c + "cmu_kg_m3"],
                    "grout and reinforcement": m["wall_m2"] * (p[c + "grout_m3_m2"] * p[c + "readymix_kg_m3"]
                                                               + p[c + "wall_rebar_kg_m2"] * p[c + "steel_kg_t"] / 1e3),
                    "hollow-core planks": m["plank_m2"] * (p[c + "plank_concrete_m3_m2"] * p[c + "precast_kg_m3"]
                                                           + p[c + "plank_strand_kg_m2"] * p[c + "steel_kg_t"] / 1e3),
                    "lintels": m["lintel_m3"] * p[c + "precast_kg_m3"],
                    "foundation": m["foundation_m3"] * p[c + "readymix_kg_m3"]},
    }


def biogenic_t(q: dict, wood_g: float) -> float:
    """CO2 held in the wood (t): dry mass x ~50% carbon x 44/12, for the wood system's wood
    (lumber, I-joists, rims, OSB, all taken at the lumber's specific gravity)."""
    w = q["wood"]
    dry_kg = (w["wood_m3"] + w["osb_m3"]) * wood_g * 1000
    return dry_kg * 0.5 * 44 / 12 / 1e3


def cost(q: dict, p: dict) -> dict[str, dict[str, float]]:
    """USD by system and part."""
    c = "pass3.cost."
    a = q["areas"]
    walls_ft2 = (a["ext_wall_gross_m2"] + a["int_wall_m2"]) * M2_FT2
    sheath_ft2 = a["sheathing_m2"] * M2_FT2
    deck_ft2 = a["deck_m2"] * M2_FT2
    m = q["masonry"]
    lintel_ft = m["lintel_m3"] / (0.1937 * 0.1937) / 0.3048  # the lintels' total length
    found = lambda sys: q[sys]["foundation_m3"] * p[c + "concrete_usd_m3"]
    wood_walls = walls_ft2 * p[c + "wall_framing_usd_ft2"]
    wood_deck = deck_ft2 * p[c + "deck_framing_usd_ft2"]
    return {
        "wood": {"wall framing": wood_walls, "floor and roof framing": wood_deck, "wall sheathing": sheath_ft2 * p[c + "sheathing_usd_ft2"],
                 "rated ceilings": deck_ft2 * p[c + "ceiling_framed_usd_ft2"], "foundation": found("wood")},
        "steel": {"wall framing": wood_walls * p[c + "cfs_factor"], "floor and roof framing": wood_deck * p[c + "cfs_factor"],
                  "wall sheathing": sheath_ft2 * p[c + "sheathing_usd_ft2"], "rated ceilings": deck_ft2 * p[c + "ceiling_framed_usd_ft2"],
                  "foundation": found("steel")},
        "masonry": {"block walls": m["wall_m2"] * M2_FT2 * p[c + "cmu_usd_ft2"], "lintels": lintel_ft * p[c + "lintel_usd_ft"],
                    "hollow-core planks": m["plank_m2"] * M2_FT2 * p[c + "plank_usd_ft2"],
                    "plank ceilings": m["plank_m2"] * M2_FT2 * p[c + "ceiling_plank_usd_ft2"], "foundation": found("masonry")},
    }


def totals(parts: dict[str, dict[str, float]]) -> dict[str, float]:
    return {s: sum(v.values()) for s, v in parts.items()}


def monte_carlo(params: dict, q: dict, n: int = 4000, seed: int = 11) -> dict[str, dict[str, np.ndarray]]:
    from .params import draw

    d = draw(params, n, seed)
    out = {"cost": {s: np.empty(n) for s in SYSTEMS}, "carbon": {s: np.empty(n) for s in SYSTEMS}}
    for i in range(n):
        p = {k: float(v[i]) for k, v in d.items()}
        for name, fn in (("cost", cost), ("carbon", carbon)):
            for s, v in totals(fn(q, p)).items():
                out[name][s][i] = v
    return out


def tornado(params: dict, p: dict, q: dict, fn, a: str, b: str, prefix: str) -> list[tuple[str, float, float]]:
    """How far `fn`'s gap between systems `a` and `b` moves as each input under `prefix` goes from
    its low to its high end, the rest central; largest swing first."""
    base = lambda pp: totals(fn(q, pp))[a] - totals(fn(q, pp))[b]
    rows = []
    for k, v in params.items():
        if not k.startswith(prefix) or v.low is None or v.high is None or v.low == v.high:
            continue
        lo, hi = base(dict(p, **{k: v.low})), base(dict(p, **{k: v.high}))
        if abs(hi - lo) > 1.0:  # inputs both systems share in full don't move the gap
            rows.append((k.removeprefix(prefix), lo, hi))
    return sorted(rows, key=lambda r: -abs(r[2] - r[1]))


def report(q: dict, p: dict, params: dict) -> str:
    cb, cs = carbon(q, p), cost(q, p)
    tc, ts = totals(cb), totals(cs)
    mc = monte_carlo(params, q)
    gfa_m2 = q["areas"]["gfa_m2"]  # the building's gross floor area, stair included
    flats = 12
    names = {"wood": "Wood frame", "steel": "Light steel", "masonry": "Block + precast"}
    lines = ["**Embodied carbon, cradle to gate (A1-A3), of the structure**", "",
             "| | " + " | ".join(names[s] for s in SYSTEMS) + " |", "|---|---|---|---|"]
    parts = sorted({k for s in SYSTEMS for k in cb[s]}, key=lambda k: (k == "foundation", k))
    for k in parts:
        lines.append(f"| {k} | " + " | ".join(f"{cb[s][k] / 1e3:,.1f} t" if k in cb[s] else "" for s in SYSTEMS) + " |")
    lines.append("| **total** | " + " | ".join(f"**{tc[s] / 1e3:,.0f} t**" for s in SYSTEMS) + " |")
    lines.append("| per flat | " + " | ".join(f"{tc[s] / 1e3 / flats:,.1f} t" for s in SYSTEMS) + " |")
    lines.append("| per m2 of floor area | " + " | ".join(f"{tc[s] / gfa_m2:,.0f} kg" for s in SYSTEMS) + " |")
    lines.append("| P10 / P90 (Monte Carlo) | " + " | ".join(
        "{:,.0f} / {:,.0f} t".format(*np.percentile(mc["carbon"][s], [10, 90]) / 1e3) for s in SYSTEMS) + " |")
    lines += ["", f"Carbon held in the wood frame's wood (not counted above): ~{biogenic_t(q, p['pass3.build.wood_g']):,.0f} t CO2.", "",
              "**Installed cost of the structure (low confidence)**", "",
              "| | " + " | ".join(names[s] for s in SYSTEMS) + " |", "|---|---|---|---|"]
    parts = sorted({k for s in SYSTEMS for k in cs[s]}, key=lambda k: (k == "foundation", k))
    for k in parts:
        lines.append(f"| {k} | " + " | ".join(f"${cs[s][k] / 1e3:,.0f}k" if k in cs[s] else "" for s in SYSTEMS) + " |")
    lines.append("| **total** | " + " | ".join(f"**${ts[s] / 1e6:,.2f}M**" for s in SYSTEMS) + " |")
    lines.append("| per flat | " + " | ".join(f"${ts[s] / flats / 1e3:,.0f}k" for s in SYSTEMS) + " |")
    lines.append("| per sq ft of floor area | " + " | ".join(f"${ts[s] / (gfa_m2 * M2_FT2):,.0f}" for s in SYSTEMS) + " |")
    lines.append("| P10 / P90 (Monte Carlo) | " + " | ".join(
        "${:,.2f}M / ${:,.2f}M".format(*np.percentile(mc["cost"][s], [10, 90]) / 1e6) for s in SYSTEMS) + " |")
    cheapest = np.argmin(np.vstack([mc["cost"][s] for s in SYSTEMS]), axis=0)
    lowest_c = np.argmin(np.vstack([mc["carbon"][s] for s in SYSTEMS]), axis=0)
    lines += ["", "| In the Monte Carlo (4,000 draws) | " + " | ".join(names[s] for s in SYSTEMS) + " |", "|---|---|---|---|",
              "| cheapest in | " + " | ".join(f"{(cheapest == i).mean():.0%}" for i in range(3)) + " |",
              "| lowest carbon in | " + " | ".join(f"{(lowest_c == i).mean():.0%}" for i in range(3)) + " |"]
    framing = sum(cs["wood"][k] for k in ("wall framing", "floor and roof framing", "wall sheathing"))
    lines += ["", f"Known case: the wood frame's framing (walls, floors, roof, sheathing) comes to "
              f"${framing / (flats * 900):,.1f} per sq ft of flat (12 x 900 sq ft); NAHB's 2024 Cost of Constructing a Home puts "
              f"single-family framing (incl. roof trusses and sheathing) at $70,982 for 2,647 sq ft = $26.8."]
    for (a, b) in (("steel", "wood"), ("masonry", "wood")):
        rows = tornado(params, p, q, cost, a, b, "pass3.cost.")[:4]
        lines += ["", f"What moves {names[a].lower()} minus {names[b].lower()} in cost most (each input low -> high):", ""]
        lines += [f"- {k}: ${lo / 1e3:+,.0f}k -> ${hi / 1e3:+,.0f}k" for k, lo, hi in rows]
    return "\n".join(lines)
