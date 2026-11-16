"""Pass 3b: the walk-up in concrete block bearing walls and precast hollow-core floors, on the
same plan as the wood frame.

- Floors and roof: 8 in. x 48 in. prestressed hollow-core planks spanning the same 19 ft from the
  facades to the spine, from a precaster's published table (Oldcastle Infrastructure, Elematic
  Hollowcore Plank Technical Guide 2019, "E8" x 48" Section with no topping": allowable live load
  by clear span, ACI 318-14, L/360; combined loads checked as (1.2/1.6) SDL + LL, as its note 4
  says). The radiant floor's gypsum topping goes on top, as on wood.
- Walls: 8 in. concrete masonry, unreinforced allowable stress design (TMS 402 Chapter 8, as taught
  in The Masonry Society's ASD course): Fa = 0.25 f'm [1 - (h/140r)^2] for h/r <= 99,
  Fb = f'm / 3, fa/Fa + fb/Fb <= 1, the floor's reaction applied at the face of its bearing. Wind
  across the facades is taken by vertical reinforcement in grouted cells, not checked here.
"""

from __future__ import annotations

from . import frame

# Oldcastle Elematic E8" x 48" untopped: allowable uniformly distributed live load (psf) by clear
# span 10-32 ft (plank self weight, 54 psf, already allowed for). Read from the guide's page 20.
PLANK_SELF_PSF = 54.0
PLANKS = {
    "2008805 (5 x 1/2 in. strands)": [441, 393, 354, 322, 294, 271, 250, 232, 209, 188, 170, 153, 139, 127, 116, 106, 98, 89, 83,
                                      76, 70, 63, None],
    "2008807 (7 x 1/2 in. strands)": [471, 421, 379, 345, 316, 290, 269, 250, 233, 218, 202, 183, 166, 152, 139, 127, 117, 107, 99,
                                      91, 85, 78, 72],
}
PLANK_SPANS_FT = list(range(10, 33))


def plank_capacity(design: str, clear_ft: float) -> float | None:
    """Allowable live load (psf) at the next tabulated clear span up."""
    i = next((k for k, s in enumerate(PLANK_SPANS_FT) if s >= clear_ft - 1e-9), None)
    return None if i is None else PLANKS[design][i]


def axial_allowable(fm: float, h_in: float, r_in: float) -> float:
    """TMS 402 ASD allowable axial stress (psi), unreinforced."""
    hr = h_in / r_in
    return 0.25 * fm * (1 - (hr / 140) ** 2) if hr <= 99 else 0.25 * fm * (70 / hr) ** 2


def known_cases() -> list[dict]:
    """The Masonry Society ASD course, example: a fully grouted 8 in. wall, f'm 2,000 psi,
    r = 2.20 in., h = 16.67 ft, An = 7.625 x 48 in. per 4 ft: Pa = 26,429 lb per foot."""
    pa = axial_allowable(2000, 16.67 * 12, 2.20) * 7.625 * 48 / 4
    return [{"case": "TMS ASD example: fully grouted 8 in. CMU, h 16.67 ft, Pa per ft", "table": 26429, "model": pa}]


def design(apt: dict, p: dict) -> dict:
    f, m = "pass3.frame.", "pass3.masonry."
    ld = frame.loads(p)
    m_in = 1000 / 25.4
    depth_in, storey_in, storeys = apt["depth_m"] * m_in, apt["storey_m"] * m_in, apt["storeys"]
    t_cmu = 7.625
    bearing = p[m + "plank_bearing_in"]
    # Planks run from the facade wall to the spine wall: clear span between the block walls' faces
    # (7-5/8 in. block at the facade and at the spine).
    clear_in = depth_in / 2 - t_cmu - t_cmu / 2
    plank_len_in = clear_in + 2 * bearing
    clear_ft = clear_in / 12
    # Superimposed dead load: the radiant topping, partitions, finishes (no ceiling below: the planks
    # are painted). The precaster's note 8 adds ~15 psf for service openings in preliminary design.
    sdl_floor = ld["topping"] + p[f + "partition_psf"] + p[m + "finishes_psf"]
    need_floor = 1.2 / 1.6 * sdl_floor + ld["floor_live"] + p[m + "openings_psf"]
    need_roof = 1.2 / 1.6 * p[m + "roof_sdl_psf"] + ld["roof_snow"]
    pick = lambda need: next(d for d in PLANKS if (c := plank_capacity(d, clear_ft)) and c >= need)
    floor_plank, roof_plank = pick(need_floor), pick(need_roof)

    # Walls: line loads per foot at the foot of each storey, D + L (and D + S); the floor reaction
    # at the top acts at the face of its bearing, e = t/2 - bearing/3 from the wall's centre.
    fm, an, r, sn = p[m + "fm_psi"], p[m + "an_in2_ft"], p[m + "r_in"], p[m + "sn_in3_ft"]
    wall_psf = p[m + "cmu_psf"]
    half = plank_len_in / 2 / 12
    floor_d = (PLANK_SELF_PSF + sdl_floor) * half
    floor_l = ld["floor_live"] * half
    roof_d = (PLANK_SELF_PSF + p[m + "roof_sdl_psf"]) * half
    roof_s = ld["roof_snow"] * half
    h = storey_in - 8.0  # clear height between the planks
    fa_allow = axial_allowable(fm, h, r)
    fb_allow = fm / 3
    e = t_cmu / 2 - bearing / 3
    walls = {}
    for storey in range(1, storeys + 1):
        above = storeys - storey
        top_d = roof_d if storey == storeys else floor_d
        top_l = roof_s if storey == storeys else floor_l
        rows = {}
        for wall, sides in (("facade", 1), ("spine", 2)):
            # Axial at the foot: everything above plus this storey's wall.
            p_ax = sides * (above * (floor_d + floor_l) + roof_d + roof_s) + (above + 1) * wall_psf * storey_in / 12
            # Moment at the top: the facade's floor sits at one face; the spine's two floors balance
            # except for live load on one side only.
            m_top = (top_d + top_l) * e if sides == 1 else top_l * e
            # Per foot of wall: An (in2/ft) and Sn (in3/ft); p_ax lb/ft, m_top lb-in/ft.
            fa = p_ax / an
            fb = m_top / sn
            rows[wall] = {"axial_plf": p_ax, "fa": fa, "fb": fb, "unity": fa / fa_allow + fb / fb_allow}
        walls[storey] = rows

    # Footings: everything down to the stem wall (now concrete block too), on the same soil.
    q = p[f + "soil_psf"]
    frost_ft = p[f + "frost_in"] / 12
    stem = 150 * (8 / 12) * (frost_ft + 8 / 12)
    facade = walls[1]["facade"]["axial_plf"] + stem
    spine = walls[1]["spine"]["axial_plf"]
    width = lambda line: line / (q - 150 * 12 / 12) * 12  # 12 in. thick footings under masonry
    return {"loads": ld, "clear_ft": clear_ft, "plank_len_in": plank_len_in, "bearing_in": bearing,
            "need_floor_psf": need_floor, "need_roof_psf": need_roof, "floor_plank": floor_plank, "roof_plank": roof_plank,
            "floor_cap_psf": plank_capacity(floor_plank, clear_ft), "roof_cap_psf": plank_capacity(roof_plank, clear_ft),
            "plank_kg": PLANK_SELF_PSF * 4 * plank_len_in / 12 * 0.453592, "fa_allow": fa_allow, "fb_allow": fb_allow,
            "h_over_r": h / r, "e_in": e, "walls": walls, "wall_psf": wall_psf,
            "footings": {"facade_plf": facade, "facade_width_in": width(facade), "spine_plf": spine, "spine_width_in": width(spine)},
            "block_lb": p[m + "block_lb"]}


def report(d: dict) -> str:
    lines = [
        f"Planks span {d['clear_ft']:.2f} ft clear (facade to spine), {d['plank_len_in'] / 12:.2f} ft long with "
        f"{d['bearing_in']:g} in. of bearing at each end; each weighs {d['plank_kg']:,.0f} kg (a crane lifts it).",
        "",
        "| Member | Chosen | Need | Allowed | Check |", "|---|---|---|---|---|",
        f"| Floor planks | 8 in. hollow-core, {d['floor_plank']} | {d['need_floor_psf']:.0f} psf | {d['floor_cap_psf']:.0f} psf | "
        f"{d['need_floor_psf'] / d['floor_cap_psf']:.0%} |",
        f"| Roof planks | 8 in. hollow-core, {d['roof_plank']} | {d['need_roof_psf']:.0f} psf | {d['roof_cap_psf']:.0f} psf | "
        f"{d['need_roof_psf'] / d['roof_cap_psf']:.0%} |",
    ]
    for k, v in d["walls"].items():
        for wall in ("facade", "spine"):
            w = v[wall]
            lines.append(f"| Storey {k} {wall} wall, 8 in. CMU | {w['axial_plf']:,.0f} plf | fa {w['fa']:.0f} psi, fb {w['fb']:.0f} psi | "
                         f"Fa {d['fa_allow']:.0f}, Fb {d['fb_allow']:.0f} psi | {w['unity']:.0%} |")
    fo = d["footings"]
    lines.append(f"| Footings, 12 in. thick | facades {fo['facade_width_in']:.0f} in. ({fo['facade_plf']:,.0f} plf), "
                 f"spine {fo['spine_width_in']:.0f} in. ({fo['spine_plf']:,.0f} plf) | | | |")
    lines.append("")
    lines.append(f"Walls h/r = {d['h_over_r']:.0f}; the floor's reaction acts {d['e_in']:.2f} in. off the wall's centre.")
    return "\n".join(lines)


def for_forge(d: dict, p: dict, apt: dict) -> dict:
    """forge's schedule for the block-and-plank building (mm)."""
    mm = 25.4
    plank_len = d["plank_len_in"] * mm
    plank_kg = d["plank_kg"]
    block_kg = p["pass3.masonry.block_lb"] * 0.453592
    block_box = (16 - 0.375) * (8 - 0.375) * 7.625 * mm ** 3 / 1e9  # m3, the unit's outline
    plank_box = 4 * 12 * mm * plank_len * 8 * mm / 1e9
    return {
        "source": "brownfield masonry (pass 3b): Oldcastle Elematic hollow-core table, TMS 402 ASD",
        "cmu_t_mm": 7.625 * mm, "course_mm": 8 * mm, "unit_mm": 16 * mm, "joint_mm": 0.375 * mm, "courses_below_plank": 14,
        "window_sill_mm": 40 * mm, "window_head_mm": 88 * mm, "door_head_mm": 80 * mm, "lintel_bearing_mm": 8 * mm,
        "plank_w_mm": 48 * mm, "plank_t_mm": 8 * mm, "bearing_mm": d["bearing_in"] * mm, "plank_len_mm": plank_len,
        "plank_kg": plank_kg, "plank_density": plank_kg / plank_box, "block_kg": block_kg, "block_density": block_kg / block_box,
        "lintel_density": 2300.0,
        "footings": {"facade_width_mm": max(d["footings"]["facade_width_in"], 12) * mm,
                     "spine_width_mm": max(d["footings"]["spine_width_in"], 12) * mm, "thickness_mm": 12 * mm},
        "floor_plank": d["floor_plank"], "roof_plank": d["roof_plank"],
    }
