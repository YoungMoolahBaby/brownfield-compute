"""Pass 3b: the walk-up in light (cold-formed) steel, on the same plan as the wood frame.

Same bearing lines, loads and spacing as `frame.py`; the members are C-section studs and joists
and U-section tracks from the SFIA Technical Guide (AISI S100-07 edition, `sfia.py`):

- joists by their tabulated effective Ix, allowable moment Ma, distortional buckling moment Mnd
  (allowable Mnd / 1.67) and allowable shear Vag, the compression flange braced by the subfloor;
  checked first against the guide's own span tables (`known_cases`);
- studs by the guide's allowable axial loads for combined axial and lateral load (15 psf on the
  facades, which is the ASD wind 0.6 x 25 psf; 5 psf inside), at the next tabulated height;
- headers by the guide's allowable uniform loads for two-member headers, at the next
  tabulated span.
"""

from __future__ import annotations

from . import frame
from .sfia import HEADERS, JOIST_SPANS, SECTIONS, STUD_AXIAL

E_STEEL = 29.5e6  # psi, as AISI S100
OMEGA_D = 1.67    # distortional buckling safety factor (AISI S100-07 C3.1.4)


def section(name: str, fy: int) -> dict:
    return SECTIONS[(name, fy)]


def joist(name: str, fy: int, spacing_in: float, span_in: float, dead_psf: float, live_psf: float,
          live_limit: float, total_limit: float | None = 240.0) -> dict:
    """Utilisations of a simply supported C-joist under uniform dead + live load."""
    s = section(name, fy)
    w_d, w_l = frame.psf_to_pli(dead_psf, spacing_in), frame.psf_to_pli(live_psf, spacing_in)
    w = w_d + w_l
    L = span_in
    m_allow = min(s["ma"], s["mnd"] / OMEGA_D) * 1000  # in-lb
    defl = lambda q: 5 * q * L ** 4 / (384 * E_STEEL * s["ix"])
    out = {"bending": w * L * L / 8 / m_allow, "shear": w * L / 2 / s["vag"],
           "deflection_live": defl(w_l) / (L / live_limit)}
    if total_limit:
        out["deflection_total"] = (defl(w_d) + defl(w_l)) / (L / total_limit)
    out["max"] = max(out.values())
    return out


def known_cases(members=("800S162-54", "800S200-68", "1000S162-54", "1000S200-54", "1000S200-68", "1200S162-54",
                         "1200S200-68", "1200S250-97")) -> list[dict]:
    """The guide's single-span joist spans at 16 in., 10 psf dead + 40 psf live, L/360 and L/480,
    reproduced from its section properties (50 ksi)."""
    rows = []
    table = JOIST_SPANS[(10, 40)]
    for name in members:
        if (name, 50) not in table:
            continue
        for limit, col in ((360, 1), (480, 7)):
            got = frame.max_span(lambda L: joist(name, 50, 16, L, 10, 40, limit))
            rows.append({"case": f"{name} (50 ksi) joist, 16 in., 10/40 psf, L/{limit} (SFIA)",
                         "table_in": table[(name, 50)][col], "model_in": got})
    return rows


def joist_options() -> list[tuple[str, int]]:
    """Joists 8-12 in. deep, 54 mil and up, 50 ksi, lightest first."""
    opts = [(n, fy) for (n, fy) in SECTIONS if fy == 50 and n.split("S")[0] in ("800", "1000", "1200")
            and "S" in n and n.split("-")[1] in ("54", "68", "97")]
    return sorted(opts, key=lambda k: SECTIONS[k]["weight"])


def stud_capacity(lateral: int, name: str, fy: int, height_ft: float, spacing: int) -> float | None:
    """Allowable axial load per stud (lb) at the next tabulated height up."""
    heights = sorted({k[3] for k in STUD_AXIAL if k[0] == lateral and k[1] == name and k[2] == fy})
    h = next((x for x in heights if x >= height_ft - 1e-9), None)
    if h is None:
        return None
    v = STUD_AXIAL.get((lateral, name, fy, h, spacing))
    return None if v is None else v * 1000


def stud_options(series: tuple[str, ...]) -> list[tuple[str, int]]:
    opts = {(n, fy) for (_, n, fy, _, _) in STUD_AXIAL if n.rsplit("-", 1)[0] in series}
    return sorted(opts, key=lambda k: SECTIONS[k]["weight"] if k in SECTIONS else 99)


def header_capacity(name: str, fy: int, span_ft: float) -> float | None:
    spans = (3, 4, 5, 6, 8, 10, 12)
    i = next((k for k, s in enumerate(spans) if s >= span_ft - 1e-9), None)
    return None if i is None else HEADERS[(name, fy)][i]


def design(apt: dict, p: dict) -> dict:
    f = "pass3.frame."
    ld = frame.loads(p)
    m_in = 1000 / 25.4
    depth_in, storey_in, storeys = apt["depth_m"] * m_in, apt["storey_m"] * m_in, apt["storeys"]
    ext_t, party_t = apt["ext_t_m"] * m_in, apt["party_t_m"] * m_in
    span = depth_in / 2 - ext_t - party_t / 2 + 1.75
    sp = int(p[f + "spacing_in"])
    live_lim = p[f + "floor_live_defl"]

    def first(options, check):
        for o in options:
            r = check(o)
            if r["max"] <= 1.0:
                return o, r
        raise ValueError("nothing passes")

    floor, floor_r = first(joist_options(), lambda o: joist(o[0], o[1], sp, span, ld["floor_dead"], ld["floor_live"], live_lim))
    roof, roof_r = first(joist_options(), lambda o: max(
        (joist(o[0], o[1], sp, span, ld["roof_dead"], ld["roof_snow"], 240, 180),
         joist(o[0], o[1], sp, span, ld["roof_dead"], ld["roof_live"], 240, 180)), key=lambda r: r["max"]))
    joist_depth = int(floor[0].split("S")[0]) / 100
    floor_depth = joist_depth + 23 / 32
    track = 1.25 + 0.1  # in., the tracks' flanges wrap the stud ends; ~1/8 in. of web below and above
    stud_len = storey_in - floor_depth - 2 * 0.06  # studs run between the tracks' webs
    height_ft = stud_len / 12
    half = span / 2 / 12
    floor_d, floor_l = ld["floor_dead"] * half, ld["floor_live"] * half
    roof_d, roof_s, roof_lr = ld["roof_dead"] * half, ld["roof_snow"] * half, ld["roof_live"] * half
    wall_d = ld["wall_dead"] * storey_in / 12

    def axial(storey: int) -> float:
        """Largest gravity line load (plf) at the foot of a stud on `storey`, one side of joists."""
        above = storeys - storey
        d = above * floor_d + roof_d + above * wall_d
        return max(d + above * floor_l, d + roof_s, d + roof_lr, d + 0.75 * above * floor_l + 0.75 * roof_s)

    studs = {}
    for storey in range(1, storeys + 1):
        plf = axial(storey)
        row = {}
        for wall, lateral, series in (("exterior", 15, ("600S162", "600S200")), ("spine_row", 5, ("362S162", "362S200", "600S162"))):
            pick = None
            for (n, fy) in stud_options(series):
                cap = stud_capacity(lateral, n, fy, height_ft, sp)
                if cap and plf * sp / 12 <= cap:
                    pick = (n, fy, cap)
                    break
            row[wall] = {"name": pick[0], "fy": pick[1], "util": plf * sp / 12 / pick[2], "axial_lb": plf * sp / 12,
                         "weight": SECTIONS[(pick[0], pick[1])]["weight"]}
        studs[storey] = row

    headers = {}
    for storey in range(1, storeys + 1):
        top = storey == storeys
        w = (roof_d + roof_s if top else floor_d + floor_l) + wall_d * 0.1
        for wm in sorted({round(x, 3) for x in apt["facade_opening_widths_m"]}):
            span_ft = (wm * m_in + 3.0) / 12
            opts = sorted(HEADERS, key=lambda k: SECTIONS[k]["weight"] if k in SECTIONS else 99)
            pick = next((k for k in opts if k[0].startswith("600S") and (c := header_capacity(k[0], k[1], span_ft)) and c >= w), None)
            headers[(storey, wm)] = {"name": pick[0], "fy": pick[1], "util": w / header_capacity(pick[0], pick[1], span_ft)}

    # Footings as for the wood frame (the floors weigh the same; the walls are lighter or alike).
    q = p[f + "soil_psf"]
    frost_ft = p[f + "frost_in"] / 12
    stem = 150 * (8 / 12) * (frost_ft + 8 / 12)
    facade = (storeys - 1) * (floor_d + floor_l) + roof_d + max(roof_s, roof_lr) + storeys * wall_d + stem
    spine = 2 * ((storeys - 1) * (floor_d + floor_l) + roof_d + max(roof_s, roof_lr)) + storeys * wall_d
    width = lambda line: line / (q - 150 * 8 / 12) * 12
    return {"loads": ld, "span_in": span, "spacing_in": sp, "floor_joist": floor, "floor_util": floor_r,
            "roof_joist": roof, "roof_util": roof_r, "floor_depth_in": floor_depth, "stud_len_in": stud_len,
            "studs": studs, "headers": headers, "track_in": track,
            "footings": {"facade_plf": facade, "facade_width_in": width(facade), "spine_plf": spine, "spine_width_in": width(spine)}}


def report(d: dict) -> str:
    fj, rj = d["floor_joist"], d["roof_joist"]
    lines = [
        f"Joist span {d['span_in'] / 12:.2f} ft (design), {d['spacing_in']} in. apart; studs {d['stud_len_in']:.1f} in. long.",
        "",
        "| Member | Chosen (SFIA designation, Fy) | lb/ft | Highest check |", "|---|---|---|---|",
        f"| Floor joists | {fj[0]}, {fj[1]} ksi | {SECTIONS[fj]['weight']:.2f} | {d['floor_util']['max']:.0%} "
        f"({', '.join(f'{k} {v:.0%}' for k, v in d['floor_util'].items() if k != 'max')}) |",
        f"| Roof joists | {rj[0]}, {rj[1]} ksi | {SECTIONS[rj]['weight']:.2f} | {d['roof_util']['max']:.0%} |",
    ]
    for k, v in d["studs"].items():
        for wall, label in (("exterior", "facade studs (15 psf wind)"), ("spine_row", "spine studs, each row")):
            s = v[wall]
            lines.append(f"| Storey {k} {label} | {s['name']}, {s['fy']} ksi | {s['weight']:.2f} | {s['util']:.0%} of the table's "
                         f"allowable ({s['axial_lb']:,.0f} lb a stud) |")
    for (storey, wm), v in d["headers"].items():
        lines.append(f"| Storey {storey} header over a {wm / 0.3048:.1f} ft opening | two {v['name']}, {v['fy']} ksi | "
                     f"{2 * SECTIONS[(v['name'], v['fy'])]['weight']:.2f} | {v['util']:.0%} |")
    fo = d["footings"]
    lines.append(f"| Footings | facades {max(fo['facade_width_in'], 12):.0f} in., spine {max(fo['spine_width_in'], 12):.0f} in. | | |")
    return "\n".join(lines)


LB_FT_TO_KG_M = 1.48816


def dims_mm(name: str) -> list[float]:
    """[flange, depth] in mm from an SFIA designation (1200S250-54: 12.00 in. deep, 2.50 in. flange)."""
    base = name.split("-")[0]
    k = "S" if "S" in base else "T"
    depth, flange = base.split(k)
    return [int(flange) / 100 * 25.4, int(depth) / 100 * 25.4]


def track_for(stud: str) -> str:
    """The track that takes a stud: same depth, 1-1/4 in. flanges, same thickness where listed."""
    depth, mils = stud.split("S")[0], stud.split("-")[1]
    for m in (mils, "43", "54", "33", "68"):
        if (f"{depth}T125-{m}", 33) in SECTIONS or (f"{depth}T125-{m}", 50) in SECTIONS:
            return f"{depth}T125-{m}"
    raise KeyError(stud)


def weight(name: str) -> float:
    return next(SECTIONS[(name, fy)]["weight"] for fy in (50, 33) if (name, fy) in SECTIONS)


def for_forge(d: dict, p: dict, apt: dict) -> dict:
    """forge's schedule for the steel frame, in the wood schedule's shape (mm)."""
    mm = 25.4
    storey = apt["storey_m"] * 1000
    plate = 1.25 * mm  # the tracks' flanges
    fj, rj = d["floor_joist"][0], d["roof_joist"][0]
    floor_depth = dims_mm(fj)[1] + 23 / 32 * mm
    names = {fj, rj, "362S162-33"}
    studs = {}
    for k, v in d["studs"].items():
        studs[str(k)] = {"exterior": {"size": v["exterior"]["name"], "spacing_mm": d["spacing_in"] * mm},
                         "spine_row": {"size": v["spine_row"]["name"], "spacing_mm": d["spacing_in"] * mm}}
        names |= {v["exterior"]["name"], v["spine_row"]["name"]}
    headers = [{"storey": s, "opening_m": w, "plies": 2, "size": v["name"], "jacks": 1} for (s, w), v in d["headers"].items()]
    names |= {h["size"] for h in headers}
    tracks = {n: track_for(n) for n in names if "S" in n.split("-")[0] and n not in (fj, rj)}
    rim = track_for(fj)
    names |= set(tracks.values()) | {rim}
    joist = lambda n: {"kind": "lumber", "name": n, "width_mm": dims_mm(n)[0], "depth_mm": dims_mm(n)[1]}
    return {
        "source": "brownfield steel (pass 3b): SFIA Technical Guide (AISI S100-07), ASCE 7-16 loads",
        "spacing_mm": d["spacing_in"] * mm, "stud_length_mm": storey - floor_depth - 2 * plate,
        "floor_joist": joist(fj), "roof_joist": joist(rj), "subfloor_mm": 23 / 32 * mm,
        "studs": studs, "headers": headers, "sizes_mm": {n: dims_mm(n) for n in names},
        "footings": {"facade_width_mm": max(d["footings"]["facade_width_in"], 12) * mm,
                     "spine_width_mm": max(d["footings"]["spine_width_in"], 12) * mm, "thickness_mm": 8 * mm},
        "build": frame.build_params(p),
        "dims": {"system": "steel", "ply_mm": 1.625 * mm, "plate_mm": plate, "rim_mm": plate, "cap": False},
        "track_for": tracks, "rim_name": rim, "stair_stud": "362S162-33",
        "linear_kg_m": {n: weight(n) * LB_FT_TO_KG_M for n in names},
    }
