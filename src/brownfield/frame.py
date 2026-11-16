"""Pass 3b, step 3: the walk-up's wood frame, sized.

Light-frame (platform) wood construction, sized by allowable stress design:

- sawn lumber by the 2018 NDS (bending fb <= Fb', shear fv <= Fv', deflection; columns by the
  Ylinen curve, NDS 3.7.1; axial plus bending, NDS 3.9.2), design values from the NDS
  Supplement (Spruce-Pine-Fir No.1/No.2; Southern Pine No.2, 2013 values);
- I-joists by their published design properties (APA PRI-400, Form Z725 Table 7);
- loads by ASCE 7-16: the ASD combinations of 2.4.1, flat-roof snow pf = 0.7 Ce Ct Is pg (7.3).

Units inside: inches, pounds, psi; loads come in as psf and leave as pounds per inch of member.
The joists span front to back, from the facades to the spine wall between the front and back
flats, so the facades and the spine are the bearing walls and the end and stair walls aren't.

Before it sizes anything, `known_cases` reproduces published span tables with the same code.
"""

from __future__ import annotations

import math

# ---- Design values ----------------------------------------------------------------------------

# Dressed sizes (in.): thickness, depth.
SIZES = {"2x4": (1.5, 3.5), "2x6": (1.5, 5.5), "2x8": (1.5, 7.25), "2x10": (1.5, 9.25), "2x12": (1.5, 11.25)}

# NDS Supplement Table 4A, Spruce-Pine-Fir No.1/No.2 (2012 values, unchanged in 2018), via SFPA
# "No.2 Design Value Comparisons by Species" (2013), whose size-adjusted values (2x4-2x12: Fb 1315 /
# 1140 / 1050 / 965 / 875, Fc 1325 / 1265 / 1210 / 1150 / 1150) give back these base values and
# size factors. Emin from NDS Appendix D: E (1 - 1.645 x 0.25) 1.03 / 1.66 = 511,000 -> 510,000.
SPF = {"Fb": 875, "Fv": 135, "Fc_perp": 425, "Fc": 1150, "E": 1.4e6, "Emin": 510_000,
       "CF_b": {"2x4": 1.5, "2x6": 1.3, "2x8": 1.2, "2x10": 1.1, "2x12": 1.0},
       "CF_c": {"2x4": 1.15, "2x6": 1.1, "2x8": 1.05, "2x10": 1.0, "2x12": 1.0}}
# Southern Pine No.2, SPIB values effective 2013-06-01 (same SFPA comparison): size-specific, no C_F.
SP = {"Fb": {"2x4": 1100, "2x6": 1000, "2x8": 925, "2x10": 800, "2x12": 750}, "Fv": 175, "Fc_perp": 565,
      "Fc": {"2x4": 1450, "2x6": 1400, "2x8": 1350, "2x10": 1300, "2x12": 1250}, "E": 1.4e6, "Emin": 510_000}

# APA Performance Rated I-Joists, Form Z725E (2012), Table 7: EI (lb-in2), M (lb-ft), V (lb),
# K (lb, shear deflection), and the end reaction on 1-3/4 in. of bearing without stiffeners (lb).
PRI = {
    ("11-7/8", "PRI-20"): (225e6, 3265, 1420, 6.18e6, 1700), ("11-7/8", "PRI-30"): (271e6, 4170, 1420, 6.18e6, 1905),
    ("11-7/8", "PRI-40"): (313e6, 3545, 1420, 6.18e6, 2500), ("11-7/8", "PRI-50"): (316e6, 4915, 1420, 6.18e6, 2040),
    ("11-7/8", "PRI-60"): (371e6, 4900, 1420, 6.18e6, 2500), ("11-7/8", "PRI-70"): (416e6, 6595, 1420, 6.18e6, 2335),
    ("11-7/8", "PRI-80"): (518e6, 6940, 1420, 6.18e6, 2760), ("11-7/8", "PRI-90"): (571e6, 8770, 1925, 6.18e6, 3355),
    ("14", "PRI-40"): (459e6, 4270, 1710, 7.28e6, 2500), ("14", "PRI-50"): (463e6, 5860, 1710, 7.28e6, 2040),
    ("14", "PRI-60"): (544e6, 5895, 1710, 7.28e6, 2500), ("14", "PRI-70"): (609e6, 7865, 1710, 7.28e6, 2335),
    ("14", "PRI-80"): (756e6, 8360, 1710, 7.28e6, 3020), ("14", "PRI-90"): (832e6, 10460, 2125, 7.28e6, 3355),
}
PRI_DEPTH = {"11-7/8": 11.875, "14": 14.0}

# APA Z725E Table 1, simple spans, 40 psf live + 10 psf dead, L/480, glue-nailed: 11-7/8 in. and
# 14 in. series at 16 in. o.c. Nailed-only floors: 12 in. less (footnote b).
PRI_TABLE1_16OC = {
    ("11-7/8", "PRI-20"): 17 * 12 + 8, ("11-7/8", "PRI-30"): 18 * 12 + 7, ("11-7/8", "PRI-40"): 19 * 12 + 4,
    ("11-7/8", "PRI-50"): 19 * 12 + 5, ("11-7/8", "PRI-60"): 20 * 12 + 3, ("11-7/8", "PRI-70"): 20 * 12 + 11,
    ("11-7/8", "PRI-80"): 22 * 12 + 4, ("11-7/8", "PRI-90"): 22 * 12 + 11,
    ("14", "PRI-40"): 21 * 12 + 11, ("14", "PRI-50"): 22 * 12 + 0, ("14", "PRI-60"): 23 * 12 + 0,
    ("14", "PRI-70"): 23 * 12 + 9, ("14", "PRI-80"): 25 * 12 + 4, ("14", "PRI-90"): 26 * 12 + 0,
}

# Total-load deflection is held to the IBC limit under D + L as applied (IBC 2018 Table 1604.3);
# NDS 3.5.2's creep factor estimates long-term sag and isn't stacked on that limit.
C_D = {"D": 0.9, "L": 1.0, "S": 1.15, "Lr": 1.25, "W": 1.6}  # NDS Table 2.3.2 load duration


def psf_to_pli(psf: float, spacing_in: float) -> float:
    """Load per inch of a member spaced `spacing_in` apart."""
    return psf * spacing_in / 144.0


# ---- Members ----------------------------------------------------------------------------------

def lumber_props(species: str, size: str) -> dict:
    b, d = SIZES[size]
    if species == "SPF":
        fb, fc = SPF["Fb"] * SPF["CF_b"][size], SPF["Fc"] * SPF["CF_c"][size]
        v = SPF
    else:
        fb, fc = SP["Fb"][size], SP["Fc"][size]
        v = SP
    return {"b": b, "d": d, "A": b * d, "S": b * d * d / 6, "I": b * d ** 3 / 12, "Fb": fb, "Fc": fc,
            "Fv": v["Fv"], "Fc_perp": v["Fc_perp"], "E": v["E"], "Emin": v["Emin"]}


def joist(member: tuple, spacing_in: float, span_in: float, dead_psf: float, live_psf: float, cd: float,
          live_limit: float, total_limit: float | None = 240.0, repetitive: bool = True,
          shear_at_d: bool = True) -> dict:
    """Utilisations of a simply supported joist under uniform dead + live (or snow) load.
    member = ("lumber", species, size) or ("ijoist", depth, series)."""
    w_d, w_l = psf_to_pli(dead_psf, spacing_in), psf_to_pli(live_psf, spacing_in)
    w = w_d + w_l
    L = span_in
    m = w * L * L / 8  # in-lb
    if member[0] == "lumber":
        p = lumber_props(member[1], member[2])
        fb_allow = p["Fb"] * cd * (1.15 if repetitive else 1.0)
        v = w * (L / 2 - (p["d"] if shear_at_d else 0.0))
        bending, shear = m / p["S"] / fb_allow, 1.5 * v / p["A"] / (p["Fv"] * cd)
        ei, k = p["E"] * p["I"], math.inf
        bearing = (w * L / 2) / (p["Fc_perp"] * p["b"] * 1.5)  # on 1.5 in. of plate
    else:
        ei, m_allow, v_allow, k, er = PRI[(member[1], member[2])]
        bending, shear = m / (m_allow * 12 * cd), (w * L / 2) / (v_allow * cd)
        bearing = (w * L / 2) / (er * cd)
    defl = lambda q: 5 * q * L ** 4 / (384 * ei) + q * L * L / k
    out = {"bending": bending, "shear": shear, "bearing": bearing,
           "deflection_live": defl(w_l) / (L / live_limit)}
    if total_limit:
        out["deflection_total"] = (defl(w_d) + defl(w_l)) / (L / total_limit)
    out["max"] = max(out.values())
    return out


def max_span(check, lo: float = 24.0, hi: float = 720.0) -> float:
    """Longest span (in.) at which check(span)['max'] <= 1 (bisection)."""
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if check(mid)["max"] <= 1.0 else (lo, mid)
    return lo


def column_cp(fc_star: float, fce: float, c: float = 0.8) -> float:
    """NDS 3.7.1, the column stability factor (sawn lumber c = 0.8)."""
    r = fce / fc_star
    a = (1 + r) / (2 * c)
    return a - math.sqrt(a * a - r / c)


def stud(species: str, size: str, spacing_in: float, le_in: float, axial_lb: float, wind_psf: float,
         cd: float) -> dict:
    """A wall stud, braced on its weak axis by the sheathing, under axial load and (for exterior
    walls) wind across it; NDS 3.7.1 and 3.9.2 (eq. 3.9-3)."""
    p = lumber_props(species, size)
    fce = 0.822 * p["Emin"] / (le_in / p["d"]) ** 2
    fc_star = p["Fc"] * cd
    fc_allow = fc_star * column_cp(fc_star, fce)
    fc = axial_lb / p["A"]
    w = psf_to_pli(wind_psf, spacing_in)
    fb = w * le_in ** 2 / 8 / p["S"]
    fb_allow = p["Fb"] * cd * 1.15  # repetitive members
    combined = (fc / fc_allow) ** 2 + (fb / (fb_allow * (1 - fc / fce)) if fb else 0.0)
    # The stud bearing on its plate, away from the plate's end: NDS 3.10.4 bearing area factor
    # Cb = (lb + 0.375) / lb for lb = 1.5 in.
    plate = fc / (p["Fc_perp"] * (1.5 + 0.375) / 1.5)
    return {"axial": fc / fc_allow, "combined": combined, "plate_bearing": plate,
            "max": max(fc / fc_allow, combined, plate), "fc_allow": fc_allow, "slenderness": le_in / p["d"]}


def header(plies: int, size: str, span_in: float, w_dead: float, w_live: float, cd: float,
           species: str = "SPF") -> dict:
    """A built-up header of `plies` sawn members (pli loads); C_r only for 3 or more plies
    (NDS 4.3.9 needs 3 members joined by a load-distributing element)."""
    p = lumber_props(species, size)
    w = w_dead + w_live
    L = span_in
    m = w * L * L / 8
    s, a, i = p["S"] * plies, p["A"] * plies, p["I"] * plies
    cr = 1.15 if plies >= 3 else 1.0
    v = w * (L / 2 - p["d"])
    defl = lambda q: 5 * q * L ** 4 / (384 * p["E"] * i)
    out = {"bending": m / s / (p["Fb"] * cd * cr), "shear": 1.5 * max(v, 0) / a / (p["Fv"] * cd),
           "deflection_live": defl(w_live) / (L / 360), "deflection_total": (defl(w_dead) + defl(w_live)) / (L / 240)}
    out["max"] = max(out.values())
    out["reaction_lb"] = w * L / 2
    return out


# ---- Known cases ------------------------------------------------------------------------------

def known_cases() -> list[dict]:
    """Published span tables, reproduced with this module's own checks."""
    rows = []
    # SFPA Maximum Span Comparisons by Species (2013), SPF No.1/No.2 floor joists at 16 in.,
    # 10 psf dead, L/360 live (tables check strength and live-load deflection only).
    for size, live, table in (("2x10", 30, 17 * 12 + 2), ("2x12", 40, 17 * 12 + 10)):
        s = max_span(lambda L: joist(("lumber", "SPF", size), 16, L, 10, live, 1.0, 360, None))
        rows.append({"case": f"SPF No.2 {size} floor joist, 16 in., {live}/10 psf, L/360 (SFPA 2013)",
                     "table_in": table, "model_in": s})
    # APA Z725E Table 1, I-joists at 16 in., 40/10 psf, L/480: the table assumes glued sheathing
    # (composite); nailed-only spans are 12 in. less, and that is what a bare joist should give.
    for (depth, series), table in PRI_TABLE1_16OC.items():
        s = max_span(lambda L: joist(("ijoist", depth, series), 16, L, 10, 40, 1.0, 480, None))
        rows.append({"case": f"I-joist {depth} {series}, 16 in., 40/10 psf, L/480, nailed (APA Z725E)",
                     "table_in": table - 12, "model_in": s})
    return rows


# ---- The walk-up's frame ----------------------------------------------------------------------

def loads(p: dict) -> dict[str, float]:
    """Area loads (psf) and the flat roof's snow (ASCE 7-16 7.3: pf = 0.7 Ce Ct Is pg, not less
    than the low-slope minimum pm = 20 Is when pg > 20 psf)."""
    f = "pass3.frame."
    pg = p[f + "ground_snow_psf"]
    pf = 0.7 * p[f + "snow_ce"] * p[f + "snow_ct"] * pg
    pm = 20.0 if pg > 20 else pg
    topping = p[f + "topping_in"] / 12 * p[f + "topping_pcf"]
    return {
        "floor_dead": p[f + "floor_dead_psf"] + p[f + "partition_psf"] + topping, "topping": topping,
        "floor_dead_no_topping": p[f + "floor_dead_psf"] + p[f + "partition_psf"],
        "floor_live": p[f + "floor_live_psf"], "roof_dead": p[f + "roof_dead_psf"],
        "roof_snow": max(pf, pm), "roof_live": p[f + "roof_live_psf"], "wall_dead": p[f + "wall_dead_psf"],
        "wind": p[f + "wall_wind_psf"],
    }


def joist_options() -> list[tuple]:
    """Candidates, roughly cheapest first: sawn lumber, then I-joists by depth and series."""
    opts = [("lumber", sp, sz) for sp in ("SPF", "SP") for sz in ("2x10", "2x12")]
    opts += [("ijoist", d, s) for (d, s) in PRI]
    return opts


def member_name(m: tuple) -> str:
    return f"{m[1]} No.2 {m[2]}" if m[0] == "lumber" else f"{m[2]} I-joist, {m[1]} in."


def member_depth(m: tuple) -> float:
    return SIZES[m[2]][1] if m[0] == "lumber" else PRI_DEPTH[m[1]]


def first_passing(options, check) -> tuple:
    for o in options:
        r = check(o)
        if r["max"] <= 1.0:
            return o, r
    raise ValueError("nothing passes")


def design(apt: dict, p: dict) -> dict:
    """Size the walk-up's wood frame. apt = forge's out/pass3/apartment.json."""
    f = "pass3.frame."
    ld = loads(p)
    m_in = 1000 / 25.4
    depth_in = apt["depth_m"] * m_in
    ext_t, party_t = apt["ext_t_m"] * m_in, apt["party_t_m"] * m_in
    storey_in = apt["storey_m"] * m_in
    storeys = apt["storeys"]
    clear = depth_in / 2 - ext_t - party_t / 2  # facade to spine
    span = clear + 1.75  # NDS 3.2.1: face to face plus half the required bearing at each end
    sp = p[f + "spacing_in"]
    live_lim = p[f + "floor_live_defl"]

    # Floor joists: D + L (C_D 1.0); with and without the radiant floor's gypsum topping.
    floor_check = lambda o, dead: joist(o, sp, span, dead, ld["floor_live"], C_D["L"], live_lim, 240)
    floor, floor_r = first_passing(joist_options(), lambda o: floor_check(o, ld["floor_dead"]))
    floor_alternatives = [o for o in joist_options() if floor_check(o, ld["floor_dead"])["max"] <= 1.0]
    bare, bare_r = first_passing(joist_options(), lambda o: floor_check(o, ld["floor_dead_no_topping"]))
    # Roof joists: D + S (C_D 1.15) and D + Lr (1.25); IBC Table 1604.3: L/240 for snow under a
    # gypsum ceiling, L/180 total.
    def roof_check(o):
        a = joist(o, sp, span, ld["roof_dead"], ld["roof_snow"], C_D["S"], 240, 180)
        b = joist(o, sp, span, ld["roof_dead"], ld["roof_live"], C_D["Lr"], 240, 180)
        return a if a["max"] >= b["max"] else b
    roof, roof_r = first_passing(joist_options(), roof_check)

    floor_depth = member_depth(floor) + 23 / 32  # joists and the subfloor the walls stand on
    le = storey_in - floor_depth - 3 * 1.5  # bottom plate and double top plate
    half = span / 2 / 12  # ft of floor each bearing wall line carries, per side
    # Line loads (plf) a bearing wall carries at each level from one side's joists.
    floor_d, floor_l = ld["floor_dead"] * half, ld["floor_live"] * half
    roof_d, roof_s, roof_lr = ld["roof_dead"] * half, ld["roof_snow"] * half, ld["roof_live"] * half
    wall_d = ld["wall_dead"] * storey_in / 12  # plf per storey of wall

    def axial_cases(storey: int, sides: int) -> list[tuple[float, float, float]]:
        """(plf axial, wind psf, C_D) for the ASD combinations (ASCE 7-16 2.4.1) at the foot of a
        stud on `storey` (1 = ground), carrying `sides` sides of joists."""
        floors_above = storeys - storey  # floor levels this storey's studs hold up (the roof aside)
        d = sides * (floors_above * floor_d + roof_d) + (storeys - storey) * wall_d
        l, s, lr = sides * floors_above * floor_l, sides * roof_s, sides * roof_lr
        w = ld["wind"] * 0.6
        return [(d, 0, C_D["D"]), (d + l, 0, C_D["L"]), (d + s, 0, C_D["S"]), (d + lr, 0, C_D["Lr"]),
                (d + 0.75 * l + 0.75 * s, 0, C_D["S"]), (d, w, C_D["W"]),
                (d + 0.75 * l + 0.75 * s, 0.75 * w, C_D["W"])]

    def stud_check(size, spacing, storey, sides, exterior):
        worst = None
        for plf, wind, cd in axial_cases(storey, sides):
            r = stud("SPF", size, spacing, le, plf * spacing / 12, wind if exterior else 0.0, cd)
            if worst is None or r["max"] > worst["max"]:
                worst = r | {"axial_lb": plf * spacing / 12, "cd": cd, "wind_psf": wind if exterior else 0.0}
        return worst

    studs = {}
    for storey in range(1, storeys + 1):
        # Facades: 2x6 for the code's R-20 cavity; spacing with the joists (in-line framing).
        ext = [(("2x6", s), stud_check("2x6", s, storey, 1, True)) for s in (sp, 12)]
        # The spine: two rows of studs (a double-stud party wall), each carrying one side's joists.
        spine = [(("2x4", s), stud_check("2x4", s, storey, 1, False)) for s in (sp, 12)]
        spine += [(("2x6", s), stud_check("2x6", s, storey, 1, False)) for s in (sp, 12)]
        studs[storey] = {"exterior": next(o for o in ext if o[1]["max"] <= 1.0),
                         "spine_row": next(o for o in spine if o[1]["max"] <= 1.0),
                         "exterior_24": stud_check("2x6", 24, storey, 1, True)}

    # Headers in the facades: a header holds up the one level above it (the floor, or the roof on
    # the top storey); the levels higher still come down the studs beside the opening, which
    # stack. Span: rough opening + 3 in.
    headers = {}
    opening_widths = sorted({round(w, 3) for w in apt["facade_opening_widths_m"]})
    for storey in range(1, storeys + 1):
        top = storey == storeys
        wd = (roof_d if top else floor_d) + wall_d * 0.1  # plus the bit of wall over the opening
        wl = roof_s if top else floor_l
        cd = C_D["S"] if top else C_D["L"]
        for wm in opening_widths:
            L = wm * m_in + 3.0
            opts = [(n, s) for s in ("2x6", "2x8", "2x10", "2x12") for n in (2, 3)]
            pick = next(((n, s), r) for (n, s) in opts
                        if (r := header(n, s, L, wd / 12, wl / 12, cd))["max"] <= 1.0)
            (n, s), r = pick
            jack_cap = SPF["Fc_perp"] * 1.5 * min(5.5, n * 1.5)  # header on one jack, at the header's end (Cb = 1)
            headers[(storey, round(wm, 3))] = {"plies": n, "size": s, "span_in": L, "util": r,
                                               "jacks": max(1, math.ceil(r["reaction_lb"] / jack_cap))}

    # Footings (IBC Table 1806.2 presumptive soil pressure): facades and spine on their own
    # footings; a stem wall to frost depth under the facades.
    q = p[f + "soil_psf"]
    frost_ft = p[f + "frost_in"] / 12
    stem = 150 * (8 / 12) * (frost_ft + 8 / 12)  # 8 in. concrete wall from the footing to 8 in. above grade
    facade_line = sum((floor_d + floor_l) for _ in range(storeys - 1)) + roof_d + max(roof_s, roof_lr) + storeys * wall_d + stem
    spine_line = 2 * (sum((floor_d + floor_l) for _ in range(storeys - 1)) + roof_d + max(roof_s, roof_lr)) + storeys * wall_d
    footing = lambda line: line / (q - 150 * 8 / 12)  # ft, net of the footing's own weight
    return {
        "loads": ld, "span_in": span, "clear_in": clear, "spacing_in": sp, "stud_le_in": le,
        "floor_joist": floor, "floor_util": floor_r, "floor_alternatives": floor_alternatives, "floor_joist_without_topping": bare, "bare_util": bare_r,
        "roof_joist": roof, "roof_util": roof_r, "floor_depth_in": floor_depth,
        "studs": studs, "headers": headers,
        "footings": {"facade_plf": facade_line, "facade_width_in": footing(facade_line) * 12,
                     "spine_plf": spine_line, "spine_width_in": footing(spine_line) * 12, "soil_psf": q,
                     "ibc_prescriptive_width_in": 18},
    }


def wood_density(g: float, mc: float) -> float:
    """Weight of wood (kg/m3) at moisture content mc (%) from its specific gravity: the NDS
    Supplement's 62.4 [G / (1 + G 0.009 mc)] (1 + mc / 100) lb/ft3."""
    return 62.4 * g / (1 + g * 0.009 * mc) * (1 + mc / 100) * 16.0185


def build_params(p: dict) -> dict:
    """What forge `build` needs (SI, mm)."""
    b = "pass3.build."
    return {"wood_density_kgm3": wood_density(p[b + "wood_g"], p[b + "wood_mc"]),
            "osb_kgm2": p[b + "osb_psf"] * 4.88243, "crew_lift_lbf": p[b + "crew_lift_lbf"],
            "crew_max": p[b + "crew_max"], "panel_max_mm": p[b + "panel_max_ft"] * 304.8}


def for_forge(d: dict, p: dict | None = None) -> dict:
    """The members forge builds (sizes in mm), and the build's settings."""
    mm = 25.4
    def joist_geom(m):
        if m[0] == "lumber":
            b, dd = SIZES[m[2]]
            return {"kind": "lumber", "name": member_name(m), "width_mm": b * mm, "depth_mm": dd * mm}
        # Display geometry only: typical PRI flanges 1-1/2 x 2-5/16 in., 3/8 in. web (not in Table 7).
        return {"kind": "ijoist", "name": member_name(m), "width_mm": 2.3125 * mm, "depth_mm": PRI_DEPTH[m[1]] * mm,
                "flange_mm": 1.5 * mm, "web_mm": 0.375 * mm}
    return {
        "source": "brownfield frame (pass 3b): NDS 2018 ASD, APA PRI-400, ASCE 7-16 loads",
        "spacing_mm": d["spacing_in"] * mm, "stud_length_mm": d["stud_le_in"] * mm,
        "floor_joist": joist_geom(d["floor_joist"]), "roof_joist": joist_geom(d["roof_joist"]),
        "subfloor_mm": 23 / 32 * mm,
        "studs": {str(k): {"exterior": {"size": v["exterior"][0][0], "spacing_mm": v["exterior"][0][1] * mm},
                           "spine_row": {"size": v["spine_row"][0][0], "spacing_mm": v["spine_row"][0][1] * mm}}
                  for k, v in d["studs"].items()},
        "headers": [{"storey": k[0], "opening_m": k[1], "plies": v["plies"], "size": v["size"], "jacks": v["jacks"]}
                    for k, v in d["headers"].items()],
        "sizes_mm": {k: [b * mm, dd * mm] for k, (b, dd) in SIZES.items()},
        "footings": {"facade_width_mm": max(d["footings"]["facade_width_in"], 12) * mm,
                     "spine_width_mm": max(d["footings"]["spine_width_in"], 12) * mm, "thickness_mm": 8 * mm},
        "build": build_params(p) if p else {},
    }


def report(d: dict) -> str:
    ld = d["loads"]
    u = lambda r: ", ".join(f"{k} {v:.0%}" for k, v in r.items() if k not in ("max", "fc_allow", "slenderness",
                                                                                  "axial_lb", "cd", "wind_psf", "reaction_lb"))
    lines = [
        f"Joist span {d['clear_in'] / 12:.2f} ft clear (facade to spine), {d['span_in']:.1f} in. design span; "
        f"members {d['spacing_in']:g} in. apart.",
        "",
        "| Loads | psf |", "|---|---|",
        f"| Floor dead (structure, ceiling, finishes, partitions) | {ld['floor_dead_no_topping']:.1f} |",
        f"| + the radiant floor's gypsum topping | {ld['topping']:.1f} |",
        f"| Floor live (dwelling units) | {ld['floor_live']:.0f} |",
        f"| Roof dead | {ld['roof_dead']:.0f} |",
        f"| Roof snow (flat roof, 0.7 Ce Ct Is pg) | {ld['roof_snow']:.1f} |",
        f"| Wind on the facades (components and cladding, strength level) | {ld['wind']:.0f} |",
        "",
        "| Member | Chosen | Highest check |", "|---|---|---|",
        f"| Floor joists | {member_name(d['floor_joist'])} at {d['spacing_in']:g} in. | {d['floor_util']['max']:.0%} ({u(d['floor_util'])}) |",
        f"| Floor joists: everything else that passes | " + ", ".join(member_name(o) for o in d['floor_alternatives'][1:]) + " | |",
        f"| Floor joists, without the topping | {member_name(d['floor_joist_without_topping'])} | {d['bare_util']['max']:.0%} |",
        f"| Roof joists | {member_name(d['roof_joist'])} at {d['spacing_in']:g} in. | {d['roof_util']['max']:.0%} ({u(d['roof_util'])}) |",
    ]
    for k, v in d["studs"].items():
        (es, esp), er = v["exterior"]
        (ss, ssp), sr = v["spine_row"]
        lines.append(f"| Storey {k} facade studs ({d['stud_le_in']:.1f} in. long) | {es} at {esp:g} in. | "
                     f"{er['max']:.0%} (axial {er['axial']:.0%}, with wind {er['combined']:.0%}); at 24 in.: {v['exterior_24']['max']:.0%} |")
        lines.append(f"| Storey {k} spine studs, each row | {ss} at {ssp:g} in. | {sr['max']:.0%} (axial {sr['axial']:.0%}) |")
    for (storey, wm), v in d["headers"].items():
        lines.append(f"| Storey {storey} header over a {wm / 0.3048:.1f} ft opening | {v['plies']}-{v['size']}, "
                     f"{v['jacks']} jack stud(s) a side | {v['util']['max']:.0%} |")
    fo = d["footings"]
    lines.append(f"| Facade footing ({fo['facade_plf']:,.0f} plf on {fo['soil_psf']:,.0f} psf soil) | "
                 f"{max(fo['facade_width_in'], 12):.0f} in. wide (IBC prescriptive: 18 in.) | |")
    lines.append(f"| Spine footing ({fo['spine_plf']:,.0f} plf) | {max(fo['spine_width_in'], 12):.0f} in. wide | |")
    return "\n".join(lines)


def known_report(rows: list[dict]) -> str:
    lines = ["| Published span | Table | This code | Difference |", "|---|---|---|---|"]
    for r in rows:
        t, m = r["table_in"], r["model_in"]
        lines.append(f"| {r['case']} | {t // 12:.0f}'-{t % 12:.0f}\" | {m // 12:.0f}'-{m % 12:.1f}\" | {m - t:+.1f} in. |")
    return "\n".join(lines)
