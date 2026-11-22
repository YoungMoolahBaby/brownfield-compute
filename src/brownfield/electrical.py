"""Pass 3g step 5 (D28): electrical, designed from steps 2-4's loads (`design`, `summary`).

**5a, each flat's panel and circuits** (`panel_place`, `flat_circuits`, `flat_panel`). A load
centre in the hall, flush in the partition the hall shares with the bath, where the hall's width
gives the 36 in. of working space NEC 110.26(A) asks. Its circuits follow the rooms: the code's
required ones (210.11(C)'s kitchen, laundry and bathroom circuits; general lighting and
receptacles at 3 VA per ft2, 210.11(A)) and one for each appliance and piece of equipment steps 3
and 4 chose. Each one's breaker, conductor and protection (AFCI 210.12(A), GFCI 210.8), the
conductor upsized until its voltage drop is within the design limit; the legs balanced.

**5b, the feeders** (`routes`, `feeders`). From each flat's breaker under its meter, on the meter
stack outside the annex, under the slab to a riser in the partition behind the panel and up:
lengths taken square until step 7 routes them. Each feeder's load by 220.82; its conductor at
75 C (310.16) and upsized for voltage drop, computed by phasors on two phase conductors and the
neutral of a 208Y/120 V system (`feeder_drop`, held to the closed form 2 K I L / CM).

**5c, the house loads** (`house_loads`): the hot-water plant's heat pumps, the building loop's and
the recirculation's pumps, the stair's and the annex's lights, the receptacles the code asks for,
on the house meter and its panel.

**5d, the service** (`service`): 220.84 for the 12 flats, the house loads added at their own
calculation (Part III), on three phases; its conductors and main; the fault current at the meter
stack and at each flat's panel by Eaton Bussmann's point-to-point method (`point_to_point`, held
to its own worked example); the surge protector 230.67 asks; the grounding electrode.

**5e, the electrical room and the meter wall** (`room_fit`): the equipment along the walls, each
with the working space 110.26 asks, against the model's room and wall.

**5f, room for solar, and for chargers if ever wanted** (`pv`, `ev`): what the roof holds after
its fire pathways and the outdoor units, its yield from PVGIS, where it connects (705.12's 120%
rule). No chargers at the walk-up (D14 puts charging at the mobility hub, Jon 2026-11-21); what the
service would hold, as built and under load management (625.42).
"""

from __future__ import annotations

import cmath
import math

from .systems import FT, FT2, IN, by_flat

SIZES = ("14", "12", "10", "8", "6", "4", "3", "2", "1", "1/0", "2/0", "3/0", "4/0", "250", "300", "350", "400",
         "500", "600", "700", "750", "900", "1000")

# The design's choices that aren't numbers (each argued in docs/PLAN.md, D28 step 5):
FLAT_SYSTEM = "120/208"  # each flat on two phases and the neutral of the 208Y/120 V service
FEEDER_METAL, FEEDER_CONDUIT = "cu", "pvc"  # copper in PVC below the slab and up the risers
SERVICE_METAL = "cu"  # one set of copper from the transformer (FirstEnergy: no parallel sets)
MINISPLIT_PROTECTION = "GFCI"  # 210.8(F), outdoor outlets at a dwelling, in force unamended
PANEL_SPACES = (20, 24, 30, 32)  # Square D QO 125 A main-lug load centres (1100CT0501, 06/2026): QO120L125PG to QO132L125PG


def _rows(name: str) -> dict[str, dict]:
    from .loads import _table

    return {r["size"]: r for r in _table(name)}


# ---- Conductors: NEC 2020 Table 310.16, Chapter 9 Table 9, 240.4(D) ----

def ampacity(size: str, metal: str, temp_c: int) -> float:
    """A conductor's ampacity (A), not more than three current-carrying in a raceway or cable, at
    30 C ambient (Table 310.16, `data/nec2020_table_310_16.csv`). 0 where the table has none."""
    v = _rows("nec2020_table_310_16.csv")[size].get(f"{metal}_{temp_c}", "")
    return float(v) if v else 0.0


def protected_at(size: str, metal: str, temp_c: int, p: dict) -> float:
    """The largest overcurrent device a conductor may have (A): 240.4(D)'s limit for the small
    sizes, else its ampacity, rounded up to the next standard rating (240.4(B))."""
    small = p.get(f"systems.wiring.max_ocpd_{metal}_{size.replace('/', '_')}")
    if small is not None:
        return min(small, next_standard(ampacity(size, metal, temp_c), p))
    return next_standard(ampacity(size, metal, temp_c), p)


def next_standard(amps: float, p: dict) -> float:
    """The smallest standard rating (240.6(A)) at or above `amps`."""
    ratings = [float(r["amps"]) for r in _table_rows("nec2020_240_6_a.csv")]
    return next(r for r in ratings if r >= amps - 1e-9)


def _table_rows(name: str) -> list[dict]:
    from .loads import _table

    return _table(name)


def impedance(size: str, metal: str, conduit: str) -> complex:
    """A conductor's AC resistance and reactance (ohm per 1,000 ft, 75 C, 60 Hz) in `conduit`
    ('pvc' or 'steel'; nonmetallic cable taken as PVC): Chapter 9 Table 9
    (`data/nec2020_ch9_table_9.csv`)."""
    r = _rows("nec2020_ch9_table_9.csv")[size]
    return complex(float(r[f"r_{metal}_{conduit}"]), float(r[f"xl_{conduit}"]))


# ---- Voltage drop, by phasors ----

def phase_voltages(system: str) -> tuple[complex, complex]:
    """The two phase conductors' voltages to the neutral at the source: 120/208 V (two phases of a
    208Y/120 V wye) or 120/240 V (single-phase, centre-tapped)."""
    va = cmath.rect(120.0, 0.0)
    vb = cmath.rect(120.0, -2 * math.pi / 3) if system == "120/208" else cmath.rect(120.0, math.pi)
    return va, vb


def feeder_drop(z_kft: complex, ft: float, va_ll: float, va_a: float, va_b: float, pf: float = 1.0,
                system: str = "120/208", zn_kft: complex | None = None) -> dict:
    """The drop at the far end of a 3-wire circuit, two phase conductors and a neutral, `ft` long,
    each conductor `z_kft` (ohm per 1,000 ft; the neutral `zn_kft`, default the same): a load of
    `va_ll` across the phases and `va_a`, `va_b` from each phase to the neutral, at power factor
    `pf` (lagging), each drawing its current at the nominal voltage. Returns the fraction lost
    line to line and line to neutral on each leg, and the currents. On 120/208 V the neutral
    carries current even when the legs are balanced, and it costs the 120 V loads their voltage."""
    va, vb = phase_voltages(system)
    vab = va - vb
    phi = -math.acos(pf)
    i_ll = va_ll / abs(vab) * cmath.rect(1.0, cmath.phase(vab) + phi)
    i_a = va_a / 120.0 * cmath.rect(1.0, cmath.phase(va) + phi)
    i_b = va_b / 120.0 * cmath.rect(1.0, cmath.phase(vb) + phi)
    ia, ib, i_n = i_ll + i_a, -i_ll + i_b, i_a + i_b
    z, zn = z_kft * ft / 1000.0, (z_kft if zn_kft is None else zn_kft) * ft / 1000.0
    a, b, n = va - ia * z, vb - ib * z, i_n * zn
    return {"ll": 1 - abs(a - b) / abs(vab), "an": 1 - abs(a - n) / 120.0, "bn": 1 - abs(b - n) / 120.0,
            "ia": abs(ia), "ib": abs(ib), "in": abs(i_n)}


def two_wire_drop(z_kft: complex, ft: float, amps: float, volts: float, pf: float = 1.0) -> float:
    """A 2-wire circuit's drop as a fraction of `volts`: out and back, at `pf`."""
    phi = -math.acos(pf)
    return abs(2 * amps * cmath.rect(1.0, phi) * z_kft * ft / 1000.0) / volts


# ---- Fault current: Eaton Bussmann's point-to-point method ----

def transformer_isc(kva: float, volts_ll: float, z_pct: float, phases: int, tolerance: float) -> float:
    """The bolted fault at a transformer's secondary terminals (A), the primary taken as infinite:
    its full-load current times 100 / %Z, the impedance first multiplied by `tolerance` (0.9 for
    the worst case, as Bussmann's method asks)."""
    fla = kva * 1000.0 / (volts_ll * (math.sqrt(3) if phases == 3 else 1.0))
    return fla * 100.0 / (z_pct * tolerance)


def point_to_point(i_start: float, ft: float, c: float, sets: int, volts_ll: float, phases: int) -> float:
    """The bolted fault at the end of a run of `ft` feet of conductor whose C-value is `c`,
    `sets` in parallel, from a point with `i_start` available: f = 1.732 L I / (C n E) three-phase,
    2 L I / (C n E) single-phase line to line; M = 1 / (1 + f)."""
    f = (math.sqrt(3) if phases == 3 else 2.0) * ft * i_start / (c * sets * volts_ll)
    return i_start / (1.0 + f)


def c_value(size: str, metal: str, conduit: str) -> float:
    """Bussmann's C for three single conductors at 600 V (`data/bussmann_c_values.csv`); a size it
    doesn't list takes the next larger one's, which errs high on the fault."""
    rows = _rows("bussmann_c_values.csv")
    listed = next(s for s in SIZES[SIZES.index(size):] if s in rows)
    return float(rows[listed][f"{metal}_{conduit}"])


# ---- 5a: each flat's panel and circuits ----

def panel_place(apt: dict, name: str) -> dict:
    """The flat's load centre: flush in the partition between its hall and its bath, on the hall's
    side, midway along the length they share. Its working space is the hall's width in front and
    that length along it."""
    rooms = by_flat(apt)[name]
    hall = next(r for r in rooms if r["id"] == f"{name}/hall")
    bath = next(r for r in rooms if r["use"] == "bath")
    x = hall["hi_m"][0] if hall["hi_m"][0] <= bath["lo_m"][0] + 1e-6 else hall["lo_m"][0]
    y0, y1 = max(hall["lo_m"][1], bath["lo_m"][1]), min(hall["hi_m"][1], bath["hi_m"][1])
    return {"xy": (x, (y0 + y1) / 2), "depth_in": (hall["hi_m"][0] - hall["lo_m"][0]) / IN, "length_in": (y1 - y0) / IN,
            "floor_z": hall["lo_m"][2], "room": hall["id"], "behind": bath["id"]}


def _far_ft(apt: dict, xy: tuple[float, float], rooms: list[dict], p: dict) -> float:
    """From the panel to the farthest corner of `rooms`, square, up into the floor above's joists
    (or the ceiling) and down again, with the route's allowance: a branch circuit's length (ft)."""
    w = "systems.wiring."
    d = max(abs(x - xy[0]) + abs(y - xy[1]) for r in rooms for x in (r["lo_m"][0], r["hi_m"][0]) for y in (r["lo_m"][1], r["hi_m"][1]))
    return (d / FT + p[w + "branch_vertical_ft"]) * p[w + "route_slack"]


def flat_circuits(apt: dict, p: dict, name: str) -> list[dict]:
    """The flat's branch circuits: what each serves, its volts and poles, its load for the panel
    (VA, by Article 220's own values where the code gives one, else the nameplate), its breaker and
    protection, its length to the farthest outlet."""
    e, fp = "systems.electrical.", "systems.flat_panel."
    rooms = by_flat(apt)[name]
    flat = next(f for f in apt["flats"] if f["name"] == name)
    ft2 = flat["floor_m2"] / FT2
    by = {r["id"].split("/")[1]: r for r in rooms}
    general = p[e + "general_va_per_ft2"]
    lighting_va = p[fp + "lighting_w_ft2"] * ft2
    xy = panel_place(apt, name)["xy"]
    far = lambda keys: _far_ft(apt, xy, [by[k] for k in keys], p)  # noqa: E731
    ground = flat["floor"] == 1
    sleep = ["bed-1", "bed-2", "hall", "bath"]
    live = ["living", "study", "passage", "entry", "kitchen", "utility"]
    c = []

    def add(key, what, volts, poles, va, amps, prot, ft, kind, **kw):
        c.append({"key": key, "what": what, "volts": volts, "poles": poles, "va": va, "breaker_a": amps,
                  "protection": prot, "ft": ft, "kind": kind, **kw})

    # General lighting and receptacles (210.11(A)): lights on their own two circuits, the sleeping
    # side and the living side, so a tripped receptacle never darkens a room; the 3 VA per ft2 left
    # after the lights on the receptacle circuits, by floor area.
    rec_va = general * ft2 - lighting_va
    rec_keys = {"bed-1": ["bed-1"], "bed-2": ["bed-2"], "living": ["living"], "study, halls and entry": ["study", "hall", "passage", "entry"],
                "bath": ["bath"]}
    rec_ft2 = sum(by[k]["area_m2"] for ks in rec_keys.values() for k in ks)
    for side, keys in (("sleeping side", sleep), ("living side", live)):
        n = sum(by[k]["area_m2"] for k in keys) / sum(by[k]["area_m2"] for k in sleep + live)
        add(f"lights-{side.split()[0]}", f"lighting, the {side}" + (" and the smoke alarms" if side.startswith("sleeping") else ""),
            120, 1, lighting_va * n, p[fp + "lighting_a"], "AFCI", far(keys), "general", load_va=p[fp + "branch_vd_va"])
    for label, keys in rec_keys.items():
        va = rec_va * sum(by[k]["area_m2"] for k in keys) / rec_ft2
        if label == "bath":  # 210.11(C)(3): 20 A, the bathroom's receptacles only; GFCI, 210.8(A)(1)
            add("bath", "bathroom receptacles (210.11(C)(3))", 120, 1, va, 20, "GFCI", far(keys), "general", load_va=p[fp + "branch_vd_va"])
            continue
        extra = " and the patio's outdoor receptacle (210.52(E)(2), a GFCI receptacle)" if (label == "living" and ground) else ""
        add(f"rec-{label.split()[0].replace(',', '')}", f"receptacles, {label}{extra}", 120, 1, va, p[fp + "receptacle_a"], "AFCI",
            far(keys), "general", load_va=p[fp + "branch_vd_va"])
    # The circuits 210.11(C) requires, at 220.52's 1,500 VA each.
    for i in (1, 2):
        add(f"sa-{i}", f"kitchen small-appliance {i} (210.11(C)(1))", 120, 1, p[e + "small_appliance_va"] / 2, 20, "AFCI+GFCI",
            far(["kitchen"]), "small appliance", load_va=p[fp + "branch_vd_va"])
    add("laundry", "the laundry closet's receptacle (210.11(C)(2))", 120, 1, p[e + "laundry_va"], 20, "AFCI+GFCI",
        far(["utility"]), "laundry", load_va=p[fp + "branch_vd_va"])
    # Appliances and equipment, each on its own circuit at its maker's breaker. Every 120 V one is in
    # a room 210.12(A) lists (the kitchen, the laundry closet), so AFCI; GFCI where 210.8 reaches:
    # the dishwasher's outlet (210.8(D)) and the dryer's receptacle in the laundry area
    # (210.8(A)(10), 125 through 250 V). The range's receptacle doesn't serve the counter.
    for key, what, room, gfci in APPLIANCE_CIRCUITS:
        volts = p[e + f"{key}_v"]
        poles = 2 if volts > 120 else 1
        prot = "+".join(x for x in ("AFCI" if poles == 1 else "", "GFCI" if gfci else "") if x)
        add(key, what, volts, poles, appliance_va(p, key), p[e + f"{key}_breaker_a"], prot, far([room]), "appliance",
            load_va=appliance_va(p, key))
    # The mini-split's outdoor unit on the roof, at its minimum circuit ampacity and maximum breaker:
    # up the line set's chase from the hall to the roof and across to the unit.
    lvl = next(x for x in apt["levels"] if x["storey"] == flat["floor"])
    up_m = apt["storey_m"] * apt["storeys"] - lvl["elevation_m"] - p["systems.wiring.panel_mid_in"] * IN
    ms_ft = (up_m / FT + p["systems.minisplit.line_set_horizontal_ft"] + p["systems.wiring.branch_vertical_ft"] / 2) * p["systems.wiring.route_slack"]
    add("minisplit", "the mini-split's outdoor unit on the roof (its indoor unit fed from it)", 208, 2, p[e + "cooling_va"],
        p[e + "minisplit_breaker_a"], MINISPLIT_PROTECTION, ms_ft, "air conditioning", load_va=p[e + "cooling_va"])
    return c


def branch_size(circ: dict, p: dict) -> dict:
    """A branch circuit's conductor: the smallest copper NM (60 C, 334.80) its breaker protects,
    upsized until its drop at its design load (`load_va` at the far end) is within the limit."""
    w = "systems.wiring."
    size = next(s for s in SIZES if protected_at(s, "cu", 60, p) >= circ["breaker_a"])
    volts = 120.0 if circ["poles"] == 1 else 208.0
    amps = circ["load_va"] / volts
    i = SIZES.index(size)
    while True:
        drop = two_wire_drop(impedance(SIZES[i], "cu", "pvc"), circ["ft"], amps, volts, p[w + "pf"])
        if drop <= p[w + "vd_branch_max"] or SIZES[i] == "6":
            break
        i += 1
    return {**circ, "awg": SIZES[i], "min_awg": size, "drop": drop, "amps": amps}


def legs(circuits: list[dict]) -> dict:
    """The panel's two legs: each 2-pole load split between them, each 1-pole circuit to the
    lighter leg, heaviest first. Returns the VA on each and the circuits' legs."""
    a = b = 0.0
    out = []
    for c in sorted(circuits, key=lambda c: (-c["poles"], -c["va"])):
        if c["poles"] == 2:
            a, b = a + c["va"] / 2, b + c["va"] / 2
            out.append({**c, "leg": "A-B"})
        elif a <= b:
            a += c["va"]
            out.append({**c, "leg": "A"})
        else:
            b += c["va"]
            out.append({**c, "leg": "B"})
    return {"a_va": a, "b_va": b, "circuits": out}


def flat_load(p: dict, ft2: float) -> dict:
    """The flat's feeder load by 220.82 with the appliances as chosen: every one fastened in place
    or on its own circuit at its nameplate (220.82(B)(3)); and under 220.82(C) the larger of the
    mini-split at its minimum circuit ampacity and 65% of the ERV's preheater, which is fixed
    electric space heating (a duct heater, Article 424) and never runs with the cooling."""
    from .loads import nec_220_82

    appl = [appliance_va(p, k) for k in APPLIANCES]
    hvac = hvac_va(p, p["systems.electrical.heat_demand_220_82"])
    return {"appliances_va": dict(zip(APPLIANCES, appl)), "hvac_va": hvac, **nec_220_82(ft2, appl, hvac, p)}


def hvac_va(p: dict, heat_factor: float) -> float:
    """The flat's heating-or-cooling load: the larger of the air conditioning and the preheater at
    `heat_factor` (220.82(C)'s 65% of electric heat, as Holt's worked case takes it; 220.84(C)(5)
    compares them at 100%)."""
    e = "systems.electrical."
    return max(p[e + "cooling_va"], heat_factor * appliance_va(p, "preheater"))


def appliance_va(p: dict, key: str) -> float:
    """An appliance circuit's nameplate load (VA); the ERV's circuit also carries the radiant
    manifold's actuators and their transformer."""
    e = "systems.electrical."
    return p[e + f"{key}_va"] + (p[e + "manifold_controls_va"] if key == "erv" else 0.0)


APPLIANCE_CIRCUITS = (("range", "the induction range", "kitchen", False),
                      ("dishwasher", "the dishwasher", "kitchen", True),
                      ("refrigerator", "the refrigerator", "kitchen", False),
                      ("microwave", "the over-the-range microwave and recirculating hood", "kitchen", False),
                      ("washer", "the washer", "utility", True),
                      ("dryer", "the heat-pump dryer", "utility", True),
                      ("erv", "the ERV and the radiant manifold's controls", "utility", False),
                      ("preheater", "the ERV's preheater", "utility", False))
HEATING = ("preheater",)  # fixed electric space heating (Article 424): 220.82(C), 220.84(C)(5)
APPLIANCES = tuple(k for k, *_ in APPLIANCE_CIRCUITS if k not in HEATING)


def flat_panel(apt: dict, p: dict, name: str) -> dict:
    """One flat's panel: its circuits sized, its legs, its spaces against the load centre's."""
    fp = "systems.flat_panel."
    circuits = [branch_size(c, p) for c in flat_circuits(apt, p, name)]
    lg = legs(circuits)
    poles = sum(c["poles"] for c in circuits)
    need = math.ceil(poles * (1 + p[fp + "spare_fraction"]))
    spaces = next(s for s in PANEL_SPACES if s >= need)
    place = panel_place(apt, name)
    return {"place": place, "circuits": lg["circuits"], "a_va": lg["a_va"], "b_va": lg["b_va"],
            "imbalance": abs(lg["a_va"] - lg["b_va"]) / max(lg["a_va"], lg["b_va"]), "poles": poles, "spaces": spaces,
            "working_ok": place["depth_in"] >= p["systems.wiring.working_depth_in"] and place["length_in"] >= p["systems.wiring.working_width_in"]}


# ---- 5b: the meter stack and the feeders ----

def meter_stack(p: dict, flats: int) -> dict:
    """The meter stack (Square D EZ Meter-Pak, `systems.meter_stack`): a main ahead of the meters
    (FirstEnergy, past six meters; NEC 230.71's one disconnect; its rating from `service`), then columns of at most
    four 125 A positions, each meter with its flat's breaker; its sockets' heights from the
    column's own dimensions, its lowest socket at the design's height."""
    m = "systems.meter_stack."
    n = int(p[m + "positions_per_column"])
    positions = flats + 1 + int(p[m + "spare_positions"])
    columns = math.ceil(positions / n)
    pitch = (p[m + "column_height_in"] - p[m + "top_offset_in"] - p[m + "bottom_offset_in"]) / (n - 1)
    bottom = p[m + "bottom_socket_mid_in"]
    top = bottom + (n - 1) * pitch
    return {"positions": positions, "columns": columns, "per_column": n, "pitch_in": pitch, "bottom_mid_in": bottom,
            "top_mid_in": top, "mid_in": (bottom + top) / 2, "width_in": p[m + "main_width_in"] + columns * p[m + "column_width_in"],
            "fe_ok": (top <= p[m + "fe_top_max_in"] + 1e-9 and bottom >= p[m + "fe_bottom_min_in"] - 1e-9
                      and pitch >= p[m + "fe_spacing_min_in"] - 1e-9 and n <= 4)}


def meter_wall(apt: dict) -> dict:
    """Where the meter stack hangs: outdoors (FirstEnergy wants meters outdoors, and each tenant must
    reach the breaker on their own feeder, 240.24(B)), on the annex's long wall that has no door,
    centred on the electrical room behind it."""
    annex = {x["id"]: x for x in apt["rooms"]["annex"]["parts"]}
    wall = annex["annex-right"]
    elec = next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/electrical")
    doors = [d for d in apt["rooms"]["annex"]["doors"] if d["wall"] == "annex-right"]
    return {"wall": wall["id"], "length_in": (wall["hi_m"][0] - wall["lo_m"][0]) / IN, "doors": len(doors),
            "xy": ((elec["lo_m"][0] + elec["hi_m"][0]) / 2, wall["hi_m"][1])}


def routes(apt: dict, p: dict) -> dict:
    """Each flat's feeder length (ft): down from the meter stack's middle into the ground, square
    under the slab to the riser behind its panel, up to the panel, with the route's allowance."""
    w = "systems.wiring."
    m = meter_wall(apt)
    ms = meter_stack(p, len(apt["flats"]))
    out = {}
    for f in apt["flats"]:
        pl = panel_place(apt, f["name"])
        lvl = next(x for x in apt["levels"] if x["storey"] == f["floor"])
        horiz = abs(pl["xy"][0] - m["xy"][0]) + abs(pl["xy"][1] - m["xy"][1])
        down = ms["mid_in"] * IN + p[w + "under_slab_m"]
        up = p[w + "under_slab_m"] + lvl["elevation_m"] + p[w + "panel_mid_in"] * IN
        out[f["name"]] = {"ft": (horiz + down + up) / FT * p[w + "route_slack"], "riser_xy": pl["xy"], "floor": f["floor"]}
    return out


def split_load(p: dict, calculated_va: float, cooling_va: float) -> tuple[float, float]:
    """A flat's calculated load as phases see it: the air conditioning across them, the rest shared
    as the appliances are (those at 208 V across, the others to the neutral, half on each leg)."""
    e = "systems.electrical."
    connected = sum(appliance_va(p, k) for k in APPLIANCES)
    share_ll = sum(appliance_va(p, k) for k in APPLIANCES if p[e + f"{k}_v"] > 120) / connected
    general = calculated_va - cooling_va
    return general * share_ll + cooling_va, general * (1 - share_ll) / 2  # the HVAC term is the mini-split, across


def feeders(apt: dict, p: dict) -> dict:
    """Each flat's feeder: its 220.82 load and the leg current it draws; its breaker under the
    meter; copper at 75 C (110.14(C)(1): the load centre's lugs are rated for it; the tenant
    breakers' to confirm in the submittal), at least 83% of the
    breaker (310.12(B), which reaches a 120/208 V flat's feeder of 100-400 A) and the load, then
    larger until its drop at that load is within the limit; its equipment grounding conductor."""
    w = "systems.wiring."
    rt = routes(apt, p)
    out = {}
    for f in apt["flats"]:
        ld = flat_load(p, f["floor_m2"] / FT2)
        va_ll, va_ln = split_load(p, ld["calculated_va"], ld["hvac_va"])
        z0 = feeder_drop(complex(0.0, 0.0), 0.0, va_ll, va_ln, va_ln, p[w + "pf"], FLAT_SYSTEM)
        amps = max(z0["ia"], z0["ib"])
        breaker = max(next_standard(amps, p), p[w + "feeder_min_a"])
        least = max(amps, p[w + "feeder_83_fraction"] * breaker if 100 <= breaker <= 400 else breaker)
        i = next(k for k, sz in enumerate(SIZES) if k >= SIZES.index("8") and ampacity(sz, FEEDER_METAL, 75) >= least - 1e-9)
        first = SIZES[i]
        while True:
            d = feeder_drop(impedance(SIZES[i], FEEDER_METAL, FEEDER_CONDUIT), rt[f["name"]]["ft"], va_ll, va_ln, va_ln,
                            p[w + "pf"], FLAT_SYSTEM)
            if max(d["ll"], d["an"], d["bn"]) <= p[w + "vd_feeder_max"] + 1e-12:
                break
            i += 1
        out[f["name"]] = {"ft": rt[f["name"]]["ft"], "floor": f["floor"], "load": ld, "amps": amps, "breaker_a": breaker,
                          "least_a": least, "size": SIZES[i], "min_size": first, "ampacity": ampacity(SIZES[i], FEEDER_METAL, 75),
                          "drop": d, "va_ll": va_ll, "va_ln": va_ln, "egc": egc_for(breaker)}
    return out


def egc_for(ocpd_a: float) -> str:
    """The copper equipment grounding conductor for an overcurrent device's rating (Table 250.122,
    `data/nec2020_table_250_122.csv`)."""
    for r in _table_rows("nec2020_table_250_122.csv"):
        if ocpd_a <= float(r["ocpd_a"]) + 1e-9:
            return r["cu"]
    raise ValueError(ocpd_a)


def conduit_for(sizes: list[str], p: dict, kind: str = "THHN/THWN/THWN-2", sched: str = "40") -> dict:
    """The smallest rigid PVC conduit (Schedule `sched`) for these conductors: their areas from NEC
    Chapter 9 Table 5 against the conduit's from Table 4, at Table 1's fill (`systems.wiring.fill_*`:
    53% for one, 31% for two, 40% for more); its outside diameter from the maker's sheet
    (`data/pvc_sched40_od.csv`)."""
    area = {r["size"]: float(r["area_in2"]) for r in _table_rows("nec2020_ch9_table_5.csv") if r["type"] == kind}
    need = sum(area[s] for s in sizes)
    w = "systems.wiring."
    fill = {1: p[w + "fill_1"], 2: p[w + "fill_2"]}.get(len(sizes), p[w + "fill_over_2"])
    od = {r["trade_size"]: float(r["od_in"]) for r in _table_rows("pvc_sched40_od.csv")}
    for r in _table_rows("nec2020_ch9_table_4_pvc.csv"):
        if r["sched"] == sched and float(r["area_100_in2"]) * fill >= need - 1e-12:
            return {"trade": r["trade_size"], "od_in": od[r["trade_size"]], "fill": need / float(r["area_100_in2"]),
                    "conductors_in2": need}
    raise ValueError(f"{sizes} need more than 4 in. conduit")


# ---- 5c: the house loads ----

HOUSE_LOADS = (  # key, what, kind (motor / continuous / noncontinuous), across the phases (208 V)?
    ("dhw_heat_pump", "the hot-water plant's water-to-water heat pump (ClimateMaster SW036)", "motor", True),
    ("swing_element", "the swing tank's element (step 4's plant, Ecosizer's size)", "noncontinuous", True),
    ("loop_pump", "the building heating loop's pump (Grundfos ALPHA2 15-55F)", "motor", False),
    ("recirc_pump", "the hot-water recirculation pump (Grundfos ALPHA2 15-55SF)", "motor", False),
    ("controls", "the substation's and the plant's controls and the meters' reader", "continuous", False),
    ("stair_lights", "the stair's lights (Lithonia TSL9 with sensor and battery), one at each landing", "continuous", False),
    ("annex_lights", "the annex's lights", "noncontinuous", False),
    ("exterior_lights", "the entry's, the annex doors' and the meter wall's lights", "continuous", False),
    ("receptacles", "receptacles: each annex room, the roof (210.63), the meter wall (210.63(B)(1))", "noncontinuous", False),
    ("fire_alarm", "the fire alarm control unit (step 6)", "continuous", False),
    ("telecom", "the telecom backboard's equipment", "continuous", False),
)


def house_loads(apt: dict, p: dict) -> dict:
    """The house panel's loads (VA) and their calculation under Part III: motors at their
    nameplate with a share of the largest added (`largest_motor_extra`), continuous loads at
    `continuous_factor`, the rest at 100%. The stair has a luminaire at each landing: one a floor and one
    between each pair of flights. The house is on one meter position, 120/208 V like a flat."""
    from .plumbing import design as plant

    h, w = "systems.house.", "systems.wiring."
    stair_n = len(apt["stair"]["flights"]) + 1
    element_va = plant(apt, p)["tm"]["capacity_kbtuh"] * 1000.0 / 3.412142
    rows = []
    for k, what, kind, ll in HOUSE_LOADS:
        va = {"stair_lights": stair_n * p[h + "stair_luminaire_w"], "swing_element": element_va}.get(k) or p[h + f"{k}_va"]
        factor = p[h + "continuous_factor"] if kind == "continuous" else 1.0
        rows.append({"key": k, "what": what, "kind": kind, "ll": ll, "va": va, "calc_va": va * factor})
    largest = max(r["va"] for r in rows if r["kind"] == "motor")
    for r in rows:
        if r["kind"] == "motor" and r["va"] == largest:
            r["calc_va"] += p[h + "largest_motor_extra"] * largest
            break
    va_ll = sum(r["calc_va"] for r in rows if r["ll"])
    va_ln = sum(r["calc_va"] for r in rows if not r["ll"]) / 2
    z0 = feeder_drop(complex(0.0, 0.0), 0.0, va_ll, va_ln, va_ln, p[w + "pf"], FLAT_SYSTEM)
    amps = max(z0["ia"], z0["ib"])
    return {"rows": rows, "stair_luminaires": stair_n, "connected_va": sum(r["va"] for r in rows),
            "calculated_va": sum(r["calc_va"] for r in rows), "amps": amps, "breaker_a": next_standard(amps, p),
            "dhw_breaker_a": next_standard(p[h + "dhw_heat_pump_va"] / 208.0, p), "dhw_mocp_a": p[h + "dhw_heat_pump_mocp_a"]}


# ---- 5d: the service and its fault current ----

# The meter stack's main breaker modules (Square D Digest, Metering Equipment, 2019: 'Main Circuit
# Breakers (3-phase incoming and 3-phase outgoing)', 65 kA): rating (A), the line-side lugs'
# conductors a phase and the largest each takes. EZM3400CB '(1)1-600 or (2)1-250'; EZM3600CB and
# EZM3800CB '(3)3/0-500'. All 18.66 in. wide. No rating between 400 and 600.
MAINS = ((400, 2, "600"), (600, 3, "500"), (800, 3, "500"))


def service_conductors(amps: float, main: float, max_sets: int, largest: str, p: dict) -> tuple[int, str]:
    """The fewest parallel sets, and in them the smallest copper, whose 75 C ampacity together
    carries the load and which the main protects (240.4(B): the next standard rating above their
    ampacity); parallel sets 1/0 or larger (310.10(H), the usual least, not read here); none past the lugs' largest. A single set
    may not exceed the lugs' largest either."""
    for n in range(1, max_sets + 1):
        for sz in SIZES[SIZES.index("1/0") if n > 1 else 0:SIZES.index(largest) + 1]:
            a = n * ampacity(sz, SERVICE_METAL, 75)
            if a >= amps and next_standard(a, p) >= main:
                return n, sz
    raise ValueError((amps, main))


def service(apt: dict, p: dict) -> dict:
    """The 208Y/120 V service: the flats by 220.84 (12 units, Table 220.84's factor), each with the
    appliances as chosen, and the house loads added (220.84(B)); its current; the least main the
    meter stack offers that carries it; its copper in the fewest sets the main's lugs take
    (FirstEnergy: parallel sets to a meter stack need its approval); the flats four to each pair of
    phases; the grounding electrode conductor by the sets' equivalent area."""
    from .loads import nec_220_84

    e = "systems.electrical."
    ft2 = apt["flats"][0]["floor_m2"] / FT2
    flats = nec_220_84(len(apt["flats"]), ft2, [appliance_va(p, k) for k in APPLIANCES], appliance_va(p, "preheater"),
                       p[e + "cooling_va"], p)
    house = house_loads(apt, p)
    total = flats["calculated_va"] + house["calculated_va"]
    amps = total / (math.sqrt(3) * 208.0)
    main, max_sets, largest = next(m for m in MAINS if m[0] >= amps)
    sets, size = service_conductors(amps, main, max_sets, largest, p)
    cmil = {r["size"]: float(r["cmil"]) for r in _table_rows("nec2020_ch9_table_8.csv")}
    equivalent = next(s_ for s_ in SIZES if cmil.get(s_, 0.0) >= sets * cmil[size] - 1e-6)
    pairs = {pair: [f["name"] for k, f in enumerate(apt["flats"]) if ("AB", "BC", "CA")[k % 3] == pair] for pair in ("AB", "BC", "CA")}
    return {"flats": flats, "house": house, "total_va": total, "amps": amps, "main_a": main, "sets": sets, "size": size,
            "ampacity": sets * ampacity(size, SERVICE_METAL, 75), "pairs": pairs, "gec": gec_for(equivalent, SERVICE_METAL),
            "pad_ok": SIZES.index(size) <= SIZES.index(str(int(p["systems.service.pad_max_kcmil"]))) and sets <= p["systems.service.pad_max_sets"]}


def gec_for(size: str, metal: str) -> str:
    """The copper grounding electrode conductor for the service conductors (Table 250.66,
    `data/nec2020_table_250_66.csv`), to the metal water pipe or ground rods if any; to the
    footing's concrete-encased electrode, not over 4 AWG (250.66(B))."""
    k = SIZES.index(size)
    for r in _table_rows("nec2020_table_250_66.csv"):
        if k <= SIZES.index(r[f"max_{metal}"]):
            return r["gec_cu"]
    raise ValueError(size)


TENANT_BREAKERS = (("QO", 10), ("QO-VH", 22), ("QOH", 42))  # kA; Square D Digest, EZ Meter-Pak, Table 2.16


def faults(apt: dict, p: dict, fd: dict, svc: dict) -> dict:
    """The bolted fault at the meter stack (from the transformer's terminals through the service
    lateral, three-phase) and at each flat's panel (through its feeder, line to line: a two-phase
    fault is 0.866 of the three-phase one), by point-to-point; and the least tenant breaker whose
    interrupting rating covers the stack's fault."""
    s = "systems.service."
    i_tx = transformer_isc(p[s + "transformer_kva"], 208.0, p[s + "transformer_z_pct"], 3, p[s + "z_tolerance"])
    i_stack = point_to_point(i_tx, p[s + "lateral_ft"], c_value(svc["size"], SERVICE_METAL, "pvc"), svc["sets"], 208.0, 3)
    i_ll = i_stack * math.sqrt(3) / 2
    flats = {n: point_to_point(i_ll, f["ft"], c_value(f["size"], FEEDER_METAL, FEEDER_CONDUIT), 1, 208.0, 1) for n, f in fd.items()}
    tenant = next(((name, ka) for name, ka in TENANT_BREAKERS if ka * 1000 >= i_stack), None)
    return {"transformer_a": i_tx, "stack_a": i_stack, "stack_ll_a": i_ll, "flats_a": flats, "tenant_breaker": tenant}


# ---- 5e: the meter wall and the electrical room ----

def room_fit(apt: dict, p: dict) -> dict:
    """The meter stack and its neighbours in a row along the annex's outside wall, and the
    electrical room's equipment along its walls: a row needs the sum of its pieces' widths, and
    at least the 30 in. of working space 110.26(A)(2) asks (neighbours may share it); the room's
    depth, 36 in. of working space and the deepest piece."""
    w, r = "systems.wiring.", "systems.electrical_room."
    ms = meter_stack(p, len(apt["flats"]))
    need = lambda row: max(sum(x for _, x in row), p[w + "working_width_in"])  # noqa: E731
    outdoor = [("the meter stack and its main", ms["width_in"]),
               ("the PV system's lockable disconnect (FirstEnergy: by the meters)", p[r + "pv_disconnect_width_in"]),
               ("the surge protector at the main (230.67)", p[r + "spd_width_in"])]
    elec = next(x for x in apt["rooms"]["rooms"] if x["id"] == "annex/electrical")
    depth_in = (elec["hi_m"][0] - elec["lo_m"][0]) / IN
    long_in = (elec["hi_m"][1] - elec["lo_m"][1]) / IN
    inside = [("the house panel", p[r + "house_panel_width_in"]), ("space for a later panel", p[r + "spare_panel_width_in"]),
              ("the PV inverters (reserved)", p[r + "pv_inverter_width_in"])]
    side = [("the fire alarm control unit (step 6)", p[r + "facu_width_in"]), ("the telecom backboard", p[r + "telecom_width_in"])]
    return {"wall_in": meter_wall(apt)["length_in"], "outdoor": outdoor, "outdoor_need_in": need(outdoor),
            "partition_in": long_in, "inside": inside, "inside_need_in": need(inside),
            "side_in": depth_in, "side": side, "side_need_in": need(side), "room_depth_in": depth_in,
            "depth_need_in": p[w + "working_depth_in"] + p[r + "deepest_in"], "stack": ms}


# ---- 5f: room for solar and EV chargers ----

def pv(apt: dict, p: dict, house: dict) -> dict:
    """The array the flat roof holds: inside the perimeter pathway (IFC 2021 1205.3.1), less the
    outdoor units', the stack vents' and the roof hatch's zones, at the racks' ground coverage; its
    yield from PVGIS at the site; and how much of it the house panel takes under 705.12(B)(3)(2)'s
    120% rule (1.25 x the inverters' current + the bus's breaker <= 1.2 x the bus)."""
    from .climate import pvgis_pv
    from .land import PLANT
    from .plumbing import stacks

    v = "systems.pv."
    roof = next(x for x in apt["parts"] if x["kind"] == "roof")
    lx, ly = (roof["hi_m"][0] - roof["lo_m"][0]) / FT, (roof["hi_m"][1] - roof["lo_m"][1]) / FT
    edge = p[v + "perimeter_ft"]
    inside = (lx - 2 * edge) * (ly - 2 * edge)
    vents = len(stacks(apt))
    usable = inside - len(apt["flats"]) * p[v + "unit_zone_ft2"] - vents * p[v + "vent_zone_ft2"] - p[v + "hatch_zone_ft2"]
    modules = math.floor(usable * p[v + "gcr"] / p[v + "module_ft2"])
    kwp = modules * p[v + "module_w"] / 1000.0
    y = pvgis_pv(*PLANT, kwp, p[v + "tilt_deg"], 0, p[v + "loss_pct"])
    bus, main = p["systems.house_panel.bus_a"], house["breaker_a"]
    max_a = (p[v + "busbar_factor"] * bus - main) / p[v + "source_factor"]
    house_kw = max_a * 208.0 / 1000.0
    return {"roof_ft2": lx * ly, "inside_ft2": inside, "vents": vents, "usable_ft2": usable, "modules": modules, "kwp": kwp,
            "kwh_year": y["kwh_year"], "kwh_per_kwp": y["kwh_year"] / kwp, "ac_kw": kwp / p[v + "dc_ac"],
            "house_bus_a": bus, "house_main_a": main, "house_max_inverter_a": max_a, "house_ac_kw": house_kw}


def ev(p: dict, svc: dict) -> dict:
    """What the service leaves for chargers: its main less its calculated load. Each charger at
    7,200 VA (the 2023 NEC's least; the 2020 code sets none) and continuous (625.42), so 125%:
    how many it feeds unmanaged, or what each of one a flat gets under an energy management system
    holding them all to what's left (625.42)."""
    x = "systems.ev."
    spare_va = svc["main_a"] * math.sqrt(3) * 208.0 - svc["total_va"]
    cont = p["systems.house.continuous_factor"]
    each = p[x + "evse_va"] * cont
    return {"spare_va": spare_va, "unmanaged": max(0, math.floor(spare_va / each)), "chargers": int(p[x + "chargers"]),
            "managed_kw_each": max(spare_va, 0.0) / cont / p[x + "chargers"] / 1000.0}


# ---- The step as data and as text ----

REQUIRED = ("sa-1", "sa-2", "laundry", "bath")  # 210.11(C)(1)-(3)


def design(apt: dict, p: dict) -> dict:
    """Step 5's electrical for the latest revision: every flat's panel and feeder, the house loads,
    the service and its fault current, the meter wall and the electrical room, the roof's PV, the
    chargers' room."""
    from .loads import design_case

    w = "systems.wiring."
    panels = {f["name"]: flat_panel(apt, p, f["name"]) for f in apt["flats"]}
    fd = feeders(apt, p)
    svc = service(apt, p)
    # Each circuit's drop with its feeder's: 120 V circuits on the worse leg to neutral, 208 V ones
    # line to line. And the preheater's output at the voltage it gets, against the design hour.
    case = design_case(apt, p, preheat=True)["flats"]
    totals, heater = {}, {}
    for n, pn in panels.items():
        d = fd[n]["drop"]
        worst = 0.0
        for c in pn["circuits"]:
            t = c["drop"] + (max(d["an"], d["bn"]) if c["poles"] == 1 else d["ll"])
            worst = max(worst, t)
            if c["key"] == "preheater":
                v = c["volts"] * (1 - t)
                heater[n] = {"volts": v, "w": p["systems.electrical.preheater_va"] * (v / c["volts"]) ** 2,
                             "need_w": case[n]["preheat_w"]}
        totals[n] = worst
    return {"panels": panels, "feeders": fd, "service": svc, "faults": faults(apt, p, fd, svc), "room": room_fit(apt, p),
            "meter_wall": meter_wall(apt), "pv": pv(apt, p, svc["house"]), "ev": ev(p, svc), "total_drop": totals,
            "heater": heater, "vd_total_max": p[w + "vd_total_max"]}


def bussmann_examples(p: dict) -> dict:
    """Eaton Bussmann's own worked examples ('Short Circuit Current Calculations', SPD handbook):
    300 kVA, 2 %Z, 208 V, an infinite primary: 46,273 A at the terminals, 39,425 A after 20 ft of
    two 500 kcmil copper in steel conduit, 18,687 A after 20 ft more of 2 AWG (the handbook rounds
    f and M on the way: 18,670 unrounded); and 75 kVA, 1.4 %Z, 120/240 V single-phase, no tolerance:
    22,322 A, and 18,453 A line to line after 25 ft of 500 kcmil in steel."""
    i0 = transformer_isc(300.0, 208.0, 2.0, 3, 0.9)
    i1 = point_to_point(i0, 20.0, c_value("500", "cu", "steel"), 2, 208.0, 3)
    i2 = point_to_point(i1, 20.0, c_value("2", "cu", "steel"), 1, 208.0, 3)
    j0 = transformer_isc(75.0, 240.0, 1.4, 1, 1.0)
    j1 = point_to_point(j0, 25.0, c_value("500", "cu", "steel"), 1, 240.0, 1)
    return {"3ph": (i0, i1, i2), "1ph": (j0, j1)}


def summary(apt: dict, p: dict) -> dict:
    """Step 5 for the latest revision (`apt`), with each known case's check, as data."""
    from .loads import holt_example, nec_220_82

    w, m = "systems.wiring.", "systems.meter_stack."
    d = design(apt, p)
    holt = holt_example(p)
    # Holt's 1,500 ft2 house by 220.82 (EC&M, 2020-04-17, 'Based on the 2020 NEC'), its 220.82(C)
    # heat (heat pump 6,720 VA + 65% of 7 kW) given: 28,710 VA, 120 A at 240 V.
    case_a = nec_220_82(1500, [1200, 900, 6000, 3000, 4000, 4500], 6720 + 0.65 * 7000, p)
    bx = bussmann_examples(p)
    # The closed form: 12 AWG copper (Table 8, 1.98 ohm/kft), 16 A at 120 V over 100 ft: 2 K I L / CM.
    r12 = float(_rows("nec2020_ch9_table_8.csv")["12"]["r_cu"])
    vd = feeder_drop(complex(r12, 0.0), 100.0, 0.0, 16 * 120.0, 0.0, 1.0, "120/240")["an"] * 120.0
    t8 = _rows("nec2020_ch9_table_8.csv")
    ac_dc = max(abs(impedance(s, "cu", "pvc").real / float(t8[s]["r_cu"]) - 1) for s in SIZES[:SIZES.index("250") + 1])
    panels, fd, svc, fl, rm, ms = d["panels"], d["feeders"], d["service"], d["faults"], d["room"], d["room"]["stack"]
    circuits = [c for pn in panels.values() for c in pn["circuits"]]
    unprotected = [c["key"] for c in circuits if protected_at(c["awg"], "cu", 60, p) < c["breaker_a"]]
    missing = {n: [k for k in REQUIRED if k not in {c["key"] for c in pn["circuits"]}] for n, pn in panels.items()}
    over_branch = [c["key"] for c in circuits if c["drop"] > p[w + "vd_branch_max"] + 1e-12]
    over_feeder = [n for n, f in fd.items() if max(f["drop"]["ll"], f["drop"]["an"], f["drop"]["bn"]) > p[w + "vd_feeder_max"] + 1e-12
                   or f["ampacity"] < f["least_a"] - 1e-9]
    worst_total = max(d["total_drop"].values())
    heater_ok = all(h["w"] >= h["need_w"] for h in d["heater"].values())
    stack_ok = fl["stack_a"] <= p[m + "main_kaic"] * 1000 and fl["tenant_breaker"] is not None
    flat_fault = max(fl["flats_a"].values())
    return {
        "revision": apt.get("revision"),
        "checks": [
            ("NEC 220.84 against Holt's 12-unit example (EC&M 2009): 460,800 VA, 188,928 VA, 787 A",
             (holt["connected_va"], round(holt["calculated_va"]), round(holt["amps_240_1ph"])) == (460800, 188928, 787),
             f"{holt['connected_va']:,.0f} VA, {holt['calculated_va']:,.0f} VA"),
            ("NEC 220.82 against Holt's 1,500 ft2 house (EC&M 2020): 28,600 VA connected, 28,710 VA, 120 A at 240 V",
             round(case_a["connected_less_hvac_va"]) == 28600 and round(case_a["calculated_va"]) == 28710 and round(case_a["amps_240"]) == 120,
             f"{case_a['calculated_va']:,.0f} VA, {case_a['amps_240']:.1f} A"),
            ("point-to-point against Bussmann's examples: 46,273 / 39,425 / 18,687 A (3-phase, 208 V); 22,322 / 18,453 A (1-phase)",
             all(abs(a / b - 1) < 0.003 for a, b in zip(bx["3ph"] + bx["1ph"], (46273, 39425, 18687, 22322, 18453))),
             ", ".join(f"{a:,.0f}" for a in bx["3ph"] + bx["1ph"])),
            ("voltage drop by phasors against 2 K I L / CM (12 AWG, 16 A, 100 ft): 6.336 V", abs(vd - 2 * 16 * 100 * r12 / 1000) < 1e-9,
             f"{vd:.3f} V"),
            ("Table 9's AC resistance within 5% of Table 8's DC, copper 14 AWG-250 kcmil (the transcriptions agree)", ac_dc <= 0.05,
             f"worst {ac_dc:.1%}"),
            ("every flat's panel has 36 in. of working space and 30 in. of width in front of it (110.26(A))",
             all(pn["working_ok"] for pn in panels.values()),
             f"{min(pn['place']['depth_in'] for pn in panels.values()):.1f} in. deep"),
            ("every flat has 210.11(C)'s circuits: two small-appliance, laundry, bathroom", not any(missing.values()),
             "" if not any(missing.values()) else str({k: v for k, v in missing.items() if v})),
            ("every branch circuit's conductor protected by its breaker (240.4(D), NM at 60 C)", not unprotected, ", ".join(unprotected)),
            ("every branch circuit within 3% at its design load", not over_branch, ", ".join(sorted(set(over_branch)))),
            ("every feeder within 2% at its 220.82 load, its ampacity at least its load and 83% of its breaker (310.12(B))",
             not over_feeder, ", ".join(over_feeder)),
            ("feeder and branch together within 5% at every outlet", worst_total <= d["vd_total_max"] + 1e-12, f"worst {worst_total:.2%}"),
            ("every ERV preheater covers the design hour at the voltage it gets", heater_ok,
             f"least {min(h['w'] for h in d['heater'].values()):.0f} W against {max(h['need_w'] for h in d['heater'].values()):.0f} W"),
            ("every meter self-contained (125 A positions, FirstEnergy's limit 400 A); the service cables within what "
             "FirstEnergy's pad takes (1000 kcmil, 8 a phase); parallel sets need its approval",
             svc["pad_ok"] and 125 <= p["systems.service.self_contained_max_a"],
             f"{svc['total_va']:,.0f} VA, {svc['amps']:.0f} A: a {svc['main_a']:.0f} A main, {svc['sets']} x {svc['size']} kcmil"),
            ("the flats four to each pair of phases", all(len(v) == 4 for v in svc["pairs"].values()),
             ", ".join(f"{k} {len(v)}" for k, v in svc["pairs"].items())),
            ("the fault at the meter stack within its main's 65 kA and a tenant breaker's rating",
             stack_ok, f"{fl['stack_a']:,.0f} A" + (f": {fl['tenant_breaker'][0]} ({fl['tenant_breaker'][1]} kA)" if fl["tenant_breaker"] else "")),
            ("the fault at every flat's panel within its QO breakers' 10 kA", flat_fault <= p["systems.flat_panel.breaker_kaic"] * 1000,
             f"at most {flat_fault:,.0f} A"),
            ("the meter stack within FirstEnergy's heights and spacing, four positions high at most", ms["fe_ok"],
             f"sockets {ms['bottom_mid_in']:.0f}-{ms['top_mid_in']:.0f} in. up, {ms['pitch_in']:.1f} in. apart"),
            ("the meter wall and the electrical room hold their equipment with its working space",
             rm["outdoor_need_in"] <= rm["wall_in"] and rm["inside_need_in"] <= rm["partition_in"] and rm["side_need_in"] <= rm["side_in"]
             and rm["depth_need_in"] <= rm["room_depth_in"],
             f"wall {rm['outdoor_need_in']:.0f} of {rm['wall_in']:.0f} in.; room {rm['inside_need_in']:.0f} of {rm['partition_in']:.0f} in."),
            ("the plant's heat pump on the next standard breaker over its minimum circuit ampacity, within the maximum on its nameplate",
             svc["house"]["dhw_breaker_a"] <= svc["house"]["dhw_mocp_a"],
             f"MCA {p['systems.house.dhw_heat_pump_va'] / 208:.1f} A: a {svc['house']['dhw_breaker_a']:.0f} A breaker, its maximum "
             f"{svc['house']['dhw_mocp_a']:.0f} A"),
        ],
        "design": d,
    }


def report(s: dict) -> str:
    """Step 5 in plain text."""
    from .systems import report as checks

    d = s["design"]
    svc, fl, fd, rm, ms, pvr, evr = d["service"], d["faults"], d["feeders"], d["room"], d["room"]["stack"], d["pv"], d["ev"]
    pn = d["panels"]["3-front-left"]
    lines = [f"Pass 3g step 5: electrical designed ({s['revision']})", "", checks(s["checks"]), "",
             f"A flat's panel (3-front-left): a {pn['spaces']}-space QO load centre in the hall, {pn['poles']} poles used; legs "
             f"{pn['a_va']:,.0f} / {pn['b_va']:,.0f} VA ({pn['imbalance']:.0%} apart)."]
    for c in pn["circuits"]:
        lines.append(f"  {c['leg']:3s} {c['breaker_a']:3.0f} A {c['poles']}P {c['protection'] or '-':9s} {c['awg']:>3s} AWG "
                     f"{c['ft']:4.0f} ft {c['drop']:5.2%}  {c['what']} ({c['va']:,.0f} VA)")
    lines += ["", "Feeders (copper in PVC, 120/208 V from two phases and the neutral):"]
    for n, f in sorted(fd.items(), key=lambda kv: (kv[1]["floor"], kv[0])):
        dr = f["drop"]
        lines.append(f"  {n:14s} {f['ft']:5.0f} ft, {f['load']['calculated_va']:,.0f} VA (220.82), {f['amps']:.0f} A a leg; "
                     f"{f['breaker_a']:.0f} A breaker; {f['size']} AWG ({f['min_size']} by ampacity), EGC {f['egc']}; drop "
                     f"{max(dr['an'], dr['bn']):.2%} to neutral, {dr['ll']:.2%} across; fault {fl['flats_a'][n]:,.0f} A")
    h = svc["house"]
    lines += ["", f"House loads ({h['connected_va']:,.0f} VA connected, {h['calculated_va']:,.0f} VA calculated, {h['amps']:.0f} A a leg: "
              f"a {h['breaker_a']:.0f} A position):"]
    for r in h["rows"]:
        lines.append(f"  {r['va']:6,.0f} VA  {r['what']}")
    lines += ["", f"The service, 208Y/120 V: the flats {svc['flats']['connected_va']:,.0f} VA x {svc['flats']['factor']:g} = "
              f"{svc['flats']['calculated_va']:,.0f} VA (220.84), the house {h['calculated_va']:,.0f}; {svc['total_va']:,.0f} VA, "
              f"{svc['amps']:.0f} A; a {svc['main_a']:.0f} A main; {svc['sets']} set(s) of {svc['size']} kcmil copper "
              f"({svc['ampacity']:.0f} A); "
              f"grounding electrode conductor {svc['gec']} AWG (4 AWG to the footing's rebar).",
              f"  Fault: {fl['transformer_a']:,.0f} A at the transformer, {fl['stack_a']:,.0f} A at the meter stack "
              f"(placeholders: FirstEnergy gives the real one on request).",
              f"  Meter stack: {ms['positions']} positions in {ms['columns']} columns of {ms['per_column']} and the {svc['main_a']:.0f} A main, "
              f"{ms['width_in']:.0f} in. wide, sockets {ms['bottom_mid_in']:.0f}-{ms['top_mid_in']:.0f} in. up; on the annex's "
              f"outside wall ({rm['outdoor_need_in']:.0f} of {rm['wall_in']:.0f} in. with the PV disconnect and the surge protector).",
              "", f"Solar: the roof holds {pvr['modules']} modules, {pvr['kwp']:.1f} kWp ({pvr['usable_ft2']:,.0f} of {pvr['roof_ft2']:,.0f} ft2 "
              f"usable), {pvr['kwh_year'] / 1000:.1f} MWh a year (PVGIS, {pvr['kwh_per_kwp']:.0f} kWh/kWp). The house panel takes "
              f"{pvr['house_ac_kw']:.1f} kW AC of it under the 120% rule; the rest needs FirstEnergy's interconnection.",
              f"EV: no chargers at the walk-up; D14 puts charging at the site's mobility hub. If that changes, the service leaves "
              f"{evr['spare_va'] / 1000:.1f} kVA: {evr['unmanaged']} chargers at 7.2 kW unmanaged, or {evr['managed_kw_each']:.2f} kW "
              f"each for {evr['chargers']} under load management."]
    return "\n".join(lines)
