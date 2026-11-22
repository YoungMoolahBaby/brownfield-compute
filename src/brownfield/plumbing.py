"""Pass 3g step 4 (D28): plumbing, designed from step 2's loads (`design`, `summary`).

**4a, hot water.** The cold water's temperature from the site's air (`mains_f`). One central
plant in the annex's mechanical room (Jon's decision), sized by Ecotope's Ecosizer method as its
engine computes it (EcosizerEngine, commit 7586430: `ecosizer_primary`, and `ecosizer_swing` for the
plant as built, a swing tank on the loop), held to the engine's own regression results; its heat
from the data center's return through a preheating exchanger, and a water-to-water heat pump
drawing on the same water after it (ClimateMaster's rating; step 5's revision). The recirculating
loop's loss from its pipes (`pipe_loss_btuh_ft`, held to NAIMA's table) and its flow at WHO's
temperatures.

**4b, cold and hot water.** IPC Appendix E's segmented loss method (`pressure_budget`, held to its
sample problem) from the building's reducing valve to the top floor's shower, every pipe the
smallest PEX within its velocity and the friction left (`pex_for`); and the pressure the street
must give.

**4c, drains and vents** (`drains_and_vents`): the stacks, their vents by Table 906.1.

**4d, noise** (`noise`): the stacks' material against CMHC's 33 dBA, the walls they face from the
model, and the supply pipes' measures relative to the usual building.
"""

from __future__ import annotations

import numpy as np

RHO_CP = 8.353535  # Btu per gallon F, EcosizerEngine constants.py `_RHO_CP`


def load_shape() -> np.ndarray:
    """The multifamily design day's hot water by hour, fractions of the day (Ecosizer's 'Stream',
    `data/ecosizer_multifamily_stream.csv`)."""
    from .loads import _table

    return np.array([float(r["fraction"]) for r in _table("ecosizer_multifamily_stream.csv")])


def _peak_starts(diff: np.ndarray) -> list[int]:
    """Hours where generation less demand turns from surplus to deficit (the day wrapping)."""
    return [i for i in range(len(diff)) if diff[i - 1] >= 0 and diff[i] < 0]


def strat_factor(supply_f: float, storage_f: float, inlet_f: float, on_fract: float, on_f: float,
                 slope: float) -> float:
    """Supply-temperature gallons a stratified tank gives per gallon, when its heater comes on with
    the aquastat at `on_fract` of its height reading `on_f`, the water above it warming at `slope`
    (F per percent of height) to the storage temperature; cold below. Ecosizer's
    `_calc_supply_temp_gal_from_100gal_tank` / 100."""
    on_pct, d = on_fract * 100.0, supply_f - inlet_f
    supply_h = max(on_pct + (supply_f - on_f) / slope, on_pct)
    storage_h = min(on_pct + (storage_f - on_f) / slope, 100.0)
    if supply_h >= 100.0:
        return 0.0
    s1, s2, a = supply_h - on_pct, storage_h - on_pct, on_f - inlet_f
    transition = (a * (s2 - s1) + slope * (s2 ** 2 - s1 ** 2) / 2.0) / d
    hot = max(0.0, 100.0 - storage_h) * (storage_f - inlet_f) / d
    return (transition + hot) / 100.0


def ecosizer_primary(day_gal: float, shape: np.ndarray, supply_f: float, storage_f: float, inlet_f: float,
                     run_hr: float = 16.0, aquastat: float = 0.5, on_f: float | None = None,
                     slope: float = 2.8, defrost: float = 1.0) -> dict:
    """The primary plant: the heating capacity (kBtu/h) that makes `day_gal` (at the supply
    temperature) in `run_hr`; the running volume (gal at supply) the storage must hold at the start
    of the worst peak; and the storage (gal at the storage temperature). The engine's defaults:
    16 h, the aquastat at half height firing at the supply temperature, 2.8 F per percent."""
    gen = day_gal / run_hr
    diff = gen - day_gal * shape
    tiled = np.tile(diff, 2)
    running = 0.0
    for i in _peak_starts(diff):
        cum = np.cumsum(tiled[i:])
        if (cum < 0).any():
            running = max(running, float(-cum[cum < 0].min()))
    f = strat_factor(supply_f, storage_f, inlet_f, aquastat, supply_f if on_f is None else on_f, slope)
    return {"capacity_kbtuh": gen * RHO_CP * (supply_f - inlet_f) / defrost / 1000, "gen_gph": gen,
            "running_gal": running, "strat_factor": f, "storage_gal": running / f,
            "minimum_gal": float(shape.max()) * day_gal / 2.0}


# Ecosizer's swing tank (EcosizerEngine SwingSystem.py, commit 7586430): its volume the smallest of
# these at least the loop's loss at 100 W a gallon and a minute's peak draw; its element turns on at
# the supply temperature and off 8 F above.
SWING_TABLE_GAL = (40, 50, 80, 100, 120, 160, 175, 240, 350, 400, 500, 600, 800, 1000, 1250)
SWING_W_PER_GAL = 100.0
SWING_DEADBAND_F = 8.0


def swing_sim(hw_min: np.ndarray, supply_f: float, storage_f: float, inlet_f: float, loss_btuh: float,
              tm_gal: float, tm_kbtuh: float, t0_f: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The swing tank alone, minute by minute (the engine's `_sim_just_swing` and
    `_run_one_swing_step`): the primary feeds it at the storage temperature as hot water is drawn
    (gallons at the supply temperature, `hw_min`, restated at the tank's temperature); the loop's
    loss cools it; its element warms it, on at the supply temperature and off 8 F above. Returns
    the tank's temperature, the element's running fraction and the draw on the primary, each
    minute."""
    n = len(hw_min)
    temps, run, primary = np.full(n, supply_f), np.zeros(n), np.zeros(n)
    temps[0], primary[0] = t0_f, hw_min[0]
    heating = False
    loss_dt = loss_btuh / 60.0 / (RHO_CP * tm_gal)
    elem_dt = tm_kbtuh * 1000.0 / 60.0 / (RHO_CP * tm_gal)
    for i in range(1, n):
        t = temps[i - 1]
        primary[i] = hw_min[i] * (supply_f - inlet_f) / (t - inlet_f) if t > inlet_f else hw_min[i]
        if primary[i] > 0:
            if tm_gal - primary[i] <= 0:
                raise ValueError(f"swing tank of {tm_gal:.0f} gal undersized for a minute's draw")
            t = (primary[i] * storage_f + t * (tm_gal - primary[i])) / tm_gal
        t -= loss_dt
        if heating:
            t += elem_dt
            run[i] = 1.0
            if t > supply_f + SWING_DEADBAND_F:
                over = min((t - (supply_f + SWING_DEADBAND_F)) / elem_dt, 1.0)
                t -= elem_dt * over
                run[i] = 1.0 - over
                heating = False
        elif t <= supply_f:
            missed = min((supply_f - t) / elem_dt, 1.0)
            t += elem_dt * missed
            run[i] = missed
            heating = True
        if t < supply_f:
            raise ValueError("the swing tank fell below the supply temperature: undersized")
        temps[i] = t
    return temps, run, primary


def ecosizer_swing(day_gal: float, shape: np.ndarray, supply_f: float, storage_f: float, inlet_f: float,
                   loss_btuh: float, run_hr: float = 16.0, aquastat: float = 0.5, slope: float = 2.8,
                   safety: float = 1.75, defrost: float = 1.0) -> dict:
    """A primary plant with a swing tank in series (Ecosizer's 'swing tank', as EcosizerEngine's
    SwingSystem sizes it): every draw passes through the swing tank, which the loop returns to; its
    element covers the loop's loss when no hot water is flowing through it.
    - The swing tank: the table's least volume over both the loop's loss at 100 W a gallon and the
      peak minute's draw; its element `safety` x the loss.
    - The running volume: for each peak start (and the hour after), the swing tank simulated over
      24 h; the primary's draw is what the swing tank can't give from its own heat; the worst
      cumulative deficit of the primary's generation (scaled to that draw) against it, restated at
      the supply temperature.
    - The capacity: the day's draw x that peak's share / `run_hr`, heated from the inlet to the
      storage temperature (the swing tank is fed at storage temperature)."""
    loss_need = loss_btuh / (SWING_W_PER_GAL * 3.412142)
    peak_min = day_gal * float(shape.max()) / 60.0
    tm_gal = float(min(v for v in SWING_TABLE_GAL if v >= max(loss_need, peak_min)))
    tm_kbtuh = safety * loss_btuh / 1000.0
    gen_norm = np.ones(24) / run_hr
    starts = _peak_starts(gen_norm - shape)
    running, eff = 0.0, 1.0
    for i in sorted(set(starts + [j + 1 for j in starts if j + 1 < 24])):
        hw = np.repeat(np.tile(shape, 2)[i:i + 24], 60) / 60.0 * day_gal
        _, _, primary = swing_sim(hw, supply_f, storage_f, inlet_f, loss_btuh, tm_gal, tm_kbtuh, supply_f + 0.1)
        mix = float(primary.sum()) / day_gal
        gen = np.repeat(np.tile(gen_norm, 2)[i:i + 24], 60) / 60.0 * day_gal * mix
        cum = np.cumsum(gen - primary)
        if (cum < 0).any() and -cum.min() > running:
            running, eff = float(-cum[cum < 0].min()), mix
    running *= (storage_f - inlet_f) / (supply_f - inlet_f)
    f = strat_factor(supply_f, storage_f, inlet_f, aquastat, supply_f, slope)
    return {"capacity_kbtuh": day_gal * eff / run_hr * RHO_CP * (storage_f - inlet_f) / defrost / 1000, "eff_mix": eff,
            "running_gal": running, "strat_factor": f, "storage_gal": running / f,
            "minimum_gal": float(shape.max()) * day_gal / 2.0, "tm_volume_gal": tm_gal, "tm_capacity_kbtuh": tm_kbtuh}


def swing_day(day_gal: float, shape: np.ndarray, supply_f: float, storage_f: float, inlet_f: float,
              loss_btuh: float, tm_gal: float, tm_kbtuh: float) -> dict:
    """The swing tank over the design day from midnight: how long its element runs and the heat it
    gives (kBtu), against the loop's loss over the day; the rest of the loss rides in on the
    primary's water, heated by the plant."""
    hw = np.repeat(shape, 60) / 60.0 * day_gal
    _, run, _ = swing_sim(hw, supply_f, storage_f, inlet_f, loss_btuh, tm_gal, tm_kbtuh, supply_f + 0.1)
    element = float(run.sum()) / 60.0 * tm_kbtuh
    return {"element_hr": float(run.sum()) / 60.0, "element_kbtu": element, "loss_kbtu": loss_btuh * 24 / 1000.0}


def recirc_loss_btuh(gpm: float, supply_f: float, return_f: float) -> float:
    """A recirculation loop's loss from its flow and its drop (Ecosizer's `get_recirc_loss_kbtuh`)."""
    return gpm * 60.0 * RHO_CP * (supply_f - return_f)


# ---- 4c, drains and vents; 4d, plumbing noise ----

def _rows(name: str) -> list[dict]:
    from .loads import _table

    return _table(name)


def tap_loss_psi(gpm: float, tap_in: float) -> float:
    """Loss through a tap or tee in the main (psi), IPC Table E103.3(4), straight lines between its
    rows."""
    col = f"t{tap_in:g}"
    pts = [(float(r["gpm"]), float(r[col])) for r in _rows("ipc2021_e103_3_4_taps.csv") if r.get(col)]
    if not pts[0][0] <= gpm <= pts[-1][0]:
        raise ValueError(f"{gpm:.0f} gpm is off Table E103.3(4) for a {tap_in:g} in. tap")
    return float(np.interp(gpm, [q for q, _ in pts], [v for _, v in pts]))


def stack_vent_in(dfu: float, developed_ft: float, stack_in: float = 3.0) -> float:
    """The least stack vent for a 3 in. stack (IPC 2021 Table 906.1): the first row carrying the
    stack's dfu, the smallest vent whose length allows `developed_ft`, and never under half the stack
    or 1-1/4 in. (906.1)."""
    if stack_in != 3.0:
        raise ValueError("only the 3 in. stack's rows of Table 906.1 are tabled here")
    row = next(r for r in _rows("ipc2021_906_1_vents_3in.csv") if float(r["dfu"]) >= dfu)
    for size in (1.25, 1.5, 2, 2.5, 3):
        cell = row[f"v{size:g}"]
        if cell and developed_ft <= float(cell) and size >= max(stack_in / 2, 1.25):
            return float(size)
    raise ValueError(f"no vent in Table 906.1 for {dfu:g} dfu over {developed_ft:.0f} ft")


def stacks(apt: dict) -> dict[str, list[str]]:
    """The drainage stacks: one in each column of flats (the same plumbing wall floor over floor),
    named by the ground floor's flat; each carries the flats above it."""
    from .systems import by_flat

    out: dict[str, list[str]] = {}
    for name in by_flat(apt):
        out.setdefault(name.split("-", 1)[1], []).append(name)
    return {k: sorted(v) for k, v in out.items()}


def wet_wall_rooms(apt: dict) -> dict[str, list[str]]:
    """Every plumbing wall and the rooms on its face, from the model's geometry."""
    R = apt["rooms"]
    out = {}
    for w in (w for w in R["walls"] if w["kind"] == "plumbing_wall"):
        lo, hi = w["lo_m"], w["hi_m"]
        thin = 0 if hi[0] - lo[0] < hi[1] - lo[1] else 1  # the wall's thickness runs along x (0) or y (1)
        along = 1 - thin
        faces = []
        for r in R["rooms"]:
            if r["storey"] != w["storey"]:
                continue
            a, b = r["lo_m"], r["hi_m"]
            if (abs(b[thin] - lo[thin]) < 0.02 or abs(a[thin] - hi[thin]) < 0.02) and \
                    min(b[along], hi[along]) - max(a[along], lo[along]) > 0.05:
                faces.append(r["use"])
        out[w["id"]] = faces
    return out


def drains_and_vents(apt: dict, p: dict) -> dict:
    """The drain stacks and their vents:
    - **stacks:** one in each column of flats, 3 in. (step 2: 27 dfu against Table 710.1(2)'s 48),
      each carried through the roof as its stack vent; no separate vent stack (IPC 904.2 asks one
      at five branch intervals; these have three);
    - **the stack vent's size** by Table 906.1 from the stack's dfu and the vent's developed length,
      the top floor's branch to the roof plus its extension above it;
    - **no frost closure** (903.2 asks 3 in. through the roof where the 97.5% winter design
      temperature is 0 F or less; the site's 99.6% is above it already).
    - **the building drain** below the slab, 4 in. (step 2)."""
    from .loads import water

    w = water(apt, p)
    pl = "systems.plumbing."
    roof_m = apt["storey_m"] * apt["storeys"]
    top_branch_m = apt["storey_m"] * (apt["storeys"] - 1)
    developed_ft = (roof_m - top_branch_m) / 0.3048 + p[pl + "vent_above_roof_in"] / 12
    vent = stack_vent_in(w["stack_dfu"], developed_ft, w["drains_in"]["stack"])
    t_99_6_f = p["systems.design.heating_c"] * 1.8 + 32
    return {"stacks": stacks(apt), "stack_in": w["drains_in"]["stack"], "stack_dfu": w["stack_dfu"],
            "vent_developed_ft": developed_ft, "stack_vent_min_in": vent, "frost_closure": t_99_6_f <= 0.0,
            "building_drain_in": w["drains_in"]["building drain, 1/8 in/ft"], "building_dfu": w["building_dfu"],
            "branch_intervals": apt["storeys"], "vent_stack_required": apt["storeys"] >= 5}


def noise(apt: dict, p: dict) -> dict:
    """Plumbing noise against CMHC's objective (a neighbour's plumbing at no more than
    `noise_limit_dba` Leq, Research Highlight 99-112):
    - **drains:** a 3 in. stack enclosed in 1/2 in. drywall, as CMHC Research Highlight 02-117
      measured it (MJM for CISPI: trade-sponsored), cast iron against PVC: the flats below take a
      neighbour's flush through their own plumbing wall, so the stack's material sets it;
    - **the rooms the stacks face:** only wet rooms, from the model;
    - **supply pipes:** Warnock and Morin's (NRC, 1990) measured effects, relative: plastic pipe
      against copper, closed-cell sleeves against rigid clamps, the supply pressure (p - 70)/12 dB."""
    n = "systems.noise."
    rooms = wet_wall_rooms(apt)
    wet = {"bath", "utility", "kitchen"}
    limit = p[n + "limit_dba"]
    drains = {m: p[n + f"stack_enclosed_{m}_dba"] for m in ("cast_iron", "pvc")}
    usual = p[n + "supply_copper_rigid_db"] + (p[n + "usual_pressure_psi"] - 70) / 12
    design = p[n + "supply_plastic_sleeved_db"] + (p["systems.plumbing.max_static_psi"] - 70) / 12
    return {"limit_dba": limit, "drain_dba": drains, "margin_db": {m: limit - v for m, v in drains.items()},
            "wet_walls_only": all(set(f) <= wet for f in rooms.values()), "faces": sorted({u for f in rooms.values() for u in f}),
            "supply_usual_db": usual, "supply_design_db": design}


# ---- 4b, cold and hot water: Appendix E's segmented loss method ----

def pressure_budget(main_psi: float, losses: dict[str, float]) -> dict:
    """IPC Appendix E, E103.3, lines A-J: the least pressure at the main, less every loss and the
    fixture's own need (lines B-H), leaves line J for pipe friction."""
    total = sum(losses.values())
    return {"main_psi": main_psi, "losses": losses, "total_psi": total, "friction_psi": main_psi - total}


def pex_for(gpm: float, max_fps: float, max_psi_100ft: float, t_c: float) -> tuple[float, float, float]:
    """The smallest SDR 9 PEX size whose velocity is at or under `max_fps` and friction at or under
    `max_psi_100ft` at `gpm`: (nominal in., ft/s, psi per 100 ft)."""
    from .hvac import FT, GPM, IN, PEX_SIZES_IN, pex_psi_per_100ft, sdr9_bore_in

    for n in PEX_SIZES_IN:
        d = sdr9_bore_in(n) * IN
        v = gpm * GPM / (np.pi * d * d / 4) / FT
        f = pex_psi_per_100ft(gpm, t_c, sdr9_bore_in(n))
        if v <= max_fps + 1e-9 and f <= max_psi_100ft + 1e-9:
            return n, v, f
    raise ValueError(f"{gpm:.1f} gpm needs PEX over 2 in.")


# ---- 4a, the cold water's temperature: the mains, from the site's air ----

def mains_f(p: dict) -> dict:
    """The water mains' temperature through the year (F), by Burch and Christensen's correlation as
    EnergyPlus implements it (Engineering Reference 26.1, 'Water Systems'; WeatherManager.cc; the
    Building America House Simulation Protocols, NREL/TP-550-49426, Eq. 26-27):
    T = (T_avg + 6) + ratio x (dT_max / 2) x sin(0.986 x (day - 15 - lag) - 90), F and degrees,
    ratio = 0.4 + 0.01 (T_avg - 44), lag = 35 - (T_avg - 44) days, floored at 32 F; T_avg the annual
    mean air and dT_max the spread of its monthly means, here from ERA5 at the site, 2005-2023 (as
    recorded: not the cooling design's shift). The design day takes its coldest."""
    from .loads import weather

    wx = weather(p)
    t_f = (np.asarray(wx["t"]) - wx["shift_k"]) * 1.8 + 32
    months = np.array([int(s[4:6]) for s in wx["time"]])
    monthly = np.array([t_f[months == m].mean() for m in range(1, 13)])
    t_avg, spread = float(t_f.mean()), float(monthly.max() - monthly.min())
    t = mains_correlation_f(t_avg, spread, np.arange(1, 366))
    return {"air_avg_f": t_avg, "air_monthly_spread_f": spread, "daily_f": t, "design_f": float(t.min()),
            "mean_f": float(t.mean())}


def mains_correlation_f(t_avg_f: float, spread_f: float, day: np.ndarray) -> np.ndarray:
    """Burch and Christensen's mains temperature (F) on Julian `day`, as EnergyPlus computes it."""
    ratio, lag = 0.4 + 0.01 * (t_avg_f - 44), 35 - 1.0 * (t_avg_f - 44)
    t = (t_avg_f + 6) + ratio * (spread_f / 2) * np.sin(np.radians(0.986 * (day - 15 - lag) - 90))
    return np.maximum(t, 32.0)


# ---- 4a, pipe heat loss ----

def pipe_loss_btuh_ft(od_in: float, ins_in: float, t_pipe_f: float, t_air_f: float, p: dict) -> float:
    """Heat lost from an insulated pipe per foot: conduction through the insulation (its
    conductivity, `insulation_k`) in series with the outer surface's film (`surface_h`); the pipe
    wall and the water's film left out."""
    h = "systems.hot_water."
    r1, r2 = od_in / 2 / 12, (od_in / 2 + ins_in) / 12
    k = p[h + "insulation_k"] / 12  # Btu/h ft F
    r_ins = np.log(r2 / r1) / (2 * np.pi * k) if ins_in > 0 else 0.0
    r_surf = 1 / (p[h + "surface_h"] * 2 * np.pi * r2)
    return float((t_pipe_f - t_air_f) / (r_ins + r_surf))


# ---- 4a-4b, the design ----

def _device_psi(gpm: float, pts: list[tuple[float, float]]) -> float:
    """A valve's or meter's loss at a flow: straight lines between its published points, and as
    the square of the flow from the nearest point outside them (a turbulent loss)."""
    pts = sorted(pts)
    if gpm <= pts[0][0]:
        return pts[0][1] * (gpm / pts[0][0]) ** 2
    if gpm >= pts[-1][0]:
        return pts[-1][1] * (gpm / pts[-1][0]) ** 2
    return float(np.interp(gpm, [q for q, _ in pts], [v for _, v in pts]))


def _xy(r: dict) -> tuple[float, float]:
    return (r["lo_m"][0] + r["hi_m"][0]) / 2, (r["lo_m"][1] + r["hi_m"][1]) / 2


def risers(apt: dict) -> dict[str, dict]:
    """Each stack's risers (cold, hot, hot return) in its plumbing wall, where the wall faces the
    bath: their plan position, and the flats they serve."""
    from .systems import by_flat

    walls = {w["id"].split("/")[0]: w for w in apt["rooms"]["walls"] if w["kind"] == "plumbing_wall"}
    out = {}
    for key, names in stacks(apt).items():
        w = walls[names[0]]
        bath = next(r for r in by_flat(apt)[names[0]] if r["use"] == "bath")
        thin = 0 if w["hi_m"][0] - w["lo_m"][0] < w["hi_m"][1] - w["lo_m"][1] else 1
        pos = list(_xy(bath))
        pos[thin] = (w["lo_m"][thin] + w["hi_m"][thin]) / 2
        out[key] = {"xy": tuple(pos), "flats": names}
    return out


def _sides(apt: dict, rs: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for key, r in rs.items():
        out.setdefault("left" if r["xy"][1] < apt["length_m"] / 2 else "right", []).append(key)
    return out


# ---- 7c: the water on its routes ----

def ep_fittings() -> dict[float, dict]:
    """Uponor's ProPEX EP fittings' equivalent feet of pipe, same-size (`data/uponor_propex_ep_fittings.csv`):
    a 90 degree elbow, a tee's run and its branch."""
    from .loads import _table

    return {float(r["size_in"]): {"elbow": float(r["elbow90_ft"]), "run": float(r["tee_through_ft"]), "branch": float(r["tee_branch_ft"])}
            for r in _table("uponor_propex_ep_fittings.csv")}


def _ft(tree, k: int) -> float:
    from .hvac import FT

    e = tree.edges[k]
    return (e.length + (tree.lead_m if e.up is None else 0.0)) / FT


def routed_loop(apt: dict, p: dict, routes, t_loop: float, t_in: float, air_f: float, ins, od) -> dict:
    """The recirculating loop's heat loss on its routes (7c): the hot and return mains under the slab
    (in ground at the mains' temperature) edge by edge, each the smallest PEX within its velocity for
    the flow it carries (the hot main the demand of the flats beyond it, the return its share of the
    loop's flow); and each column's hot and return risers in the heated building, from the main up
    to the top flat's tee. The returns' sizes and the loop's flow worked to agreement as in `design`."""
    from .hvac import FT
    from .loads import hunter_gpm, water

    pl, h = "systems.plumbing.", "systems.hot_water."
    w = water(apt, p)
    hot_per = w["per_flat"]["hot"]
    storeys = apt["storeys"]
    supply, ret_f = p[h + "distribution_f"], p[h + "return_min_f"]
    hot_c, ret_c = (supply - 32) / 1.8, (ret_f - 32) / 1.8
    cols = stacks(apt)
    hot_main, ret_main = routes.tree("main/hot"), routes.tree("main/hot-return")
    rise = {}
    for col, names in cols.items():
        top = max(routes.tree(f"plumbing/hot/{n}").root[2] for n in names)
        rise[col] = (top - hot_main.point(col)[2]) / FT
    n_hot = {k: pex_for(hunter_gpm(len(e.below) * storeys * hot_per), p[pl + "hot_fps"], 1e9, hot_c)[0] for k, e in enumerate(hot_main.edges)}
    n_rise = pex_for(hunter_gpm(storeys * hot_per), p[pl + "hot_fps"], 1e9, hot_c)[0]
    n_ret = {k: 0.5 for k in range(len(ret_main.edges))}
    n_ret_rise = 0.5
    for _ in range(4):
        loss = sum(_ft(hot_main, k) * pipe_loss_btuh_ft(od(n_hot[k]), ins(n_hot[k]), t_loop, t_in, p) for k in n_hot)
        loss += sum(_ft(ret_main, k) * pipe_loss_btuh_ft(od(n_ret[k]), ins(n_ret[k]), t_loop, t_in, p) for k in n_ret)
        loss += sum(L * (pipe_loss_btuh_ft(od(n_rise), ins(n_rise), t_loop, air_f, p) + pipe_loss_btuh_ft(od(n_ret_rise), ins(n_ret_rise), t_loop, air_f, p))
                    for L in rise.values())
        gpm = loss / (60 * RHO_CP * (supply - ret_f))
        new = {k: pex_for(gpm * len(e.below) / len(cols), p[pl + "return_fps"], 1e9, ret_c)[0] for k, e in enumerate(ret_main.edges)}
        new_rise = pex_for(gpm / len(cols), p[pl + "return_fps"], 1e9, ret_c)[0]
        if new == n_ret and new_rise == n_ret_rise:
            break
        n_ret, n_ret_rise = new, new_rise
    fps = max([pex_for(gpm * len(e.below) / len(cols), p[pl + "return_fps"], 1e9, ret_c)[1] for e in ret_main.edges]
              + [pex_for(gpm / len(cols), p[pl + "return_fps"], 1e9, ret_c)[1]])
    rows = [{"side": col, "main_ft": hot_main.path(col)["m"] / FT, "hot_main_in": max(n_hot.values()), "hot_riser_in": n_rise, "stacks": [col],
             "rise_ft": rise[col]} for col in cols]
    return {"loss": loss, "gpm": gpm, "rows": rows, "return_main_in": max(n_ret.values()), "return_riser_in": n_ret_rise, "return_fps": fps,
            "hot_main_in": n_hot, "hot_riser_in": n_rise, "main_ft": {"hot": hot_main.length_m / FT, "return": ret_main.length_m / FT},
            "rise_ft": rise}


PEX_SIZES = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)  # hvac.PEX_SIZES_IN


def _fps(gpm: float, n: float) -> float:
    from .hvac import FT, GPM, IN, sdr9_bore_in

    d = sdr9_bore_in(n) * IN
    return gpm * GPM / (np.pi * d * d / 4) / FT


def routed_paths(apt: dict, p: dict, routes, falloff: float, sub, tmv: float, start: dict, limit_psi: float,
                 all_elbows: bool = False) -> dict:
    """IPC Appendix E on the routes (7c), for every flat, cold and hot: from the building's reducing
    valve along the main under the slab to its column, up the riser (in pieces between the flats'
    tees, each carrying the flats above it) to the flat's tee, and along the flat's branch to its
    shower; each straight foot and each fitting's in place of the code's 50% for fittings:
    - **a sweep at each bend** of the route, the PEX bent on a bend support at six diameters' radius
      (PPI: elbows 'only when necessary, such as within tight cavities'), its loss as Crane's
      (`pex_sweep_el_d` diameters of pipe);
    - **an elbow** (Uponor's EP) where the main turns up into the riser, where the top flat's branch
      leaves the riser's end, and at each fixture's stub-out; **a tee's branch** where a branch leaves
      the riser or a pipe, **its run** where the pipe goes on past one (Uponor's EP tees).
    `all_elbows`: every bend an elbow instead (the bound). The budget starts at the lesser of the
    reducing valve's setting (less its falloff at the peak) and `limit_psi` (what the street gives
    at the peak past the meter, the tap, the backflow assembly and the lift: Appendix E's line A).
    The sizes: the flats' branches and the risers stay as routed (`start`, step 4's: they pass
    through the frame and the plumbing wall's cavity, the hot riser with 0.4 in. to spare), and
    the mains under the slab grow, each edge the larger of what its velocity asks and one size
    for all, the least that leaves every flat's shower its pressure. Only if no main will do,
    Appendix E's own way: every pipe the smallest PEX within its velocity and the tightest flat's
    friction rate (worked three times, the fittings' feet changing with the sizes)."""
    from .hvac import FT, pex_psi_per_100ft, sdr9_bore_in
    from .loads import hunter_gpm, water

    pl, h = "systems.plumbing.", "systems.hot_water."
    fit = ep_fittings()
    w = water(apt, p)
    per = w["per_flat"]
    storeys = apt["storeys"]
    cols = stacks(apt)
    lv = {x["storey"]: x["elevation_m"] for x in apt["levels"]}
    floor = {f["name"]: f["floor"] for f in apt["flats"]}
    out = {}
    for kind in ("cold", "hot"):
        t_c = ((p[h + "distribution_f"] if kind == "hot" else mains_f(p)["design_f"]) - 32) / 1.8
        main = routes.tree(f"main/{kind}")
        legs: dict[str, list[dict]] = {}
        for col, names in cols.items():
            tees = {n: routes.tree(f"plumbing/{kind}/{n}").root[2] for n in names}
            z_top = max(tees.values())
            for n in names:
                segs = []
                for k in main.path(col)["edges"]:
                    e = main.edges[k]
                    segs.append({"segment": "main", "key": ("main", k), "gpm": hunter_gpm(len(e.below) * storeys * per[kind]),
                                 "ft": _ft(main, k), "sweeps": e.bends, "elbows": 0, "tee": e.tee})
                z0 = main.point(col)[2]
                for i, z in enumerate(sorted(z_ for z_ in tees.values() if z_ <= tees[n] + 1e-9)):
                    above = sum(1 for z_ in tees.values() if z_ >= z - 1e-9)
                    segs.append({"segment": "riser", "key": ("riser", col), "gpm": hunter_gpm(above * per[kind]), "ft": (z - z0) / FT,
                                 "sweeps": 0, "elbows": 1 if i == 0 else 0, "tee": "run" if i > 0 else "none"})
                    z0 = z
                bt = routes.tree(f"plumbing/{kind}/{n}")
                es = bt.path("tub")["edges"]
                for j, k in enumerate(es):
                    e = bt.edges[k]
                    first = j == 0
                    segs.append({"segment": "branch", "key": ("branch",), "gpm": hunter_gpm(per[kind]), "ft": _ft(bt, k), "sweeps": e.bends,
                                 "elbows": (1 if first and tees[n] >= z_top - 1e-9 else 0) + (1 if j == len(es) - 1 else 0),
                                 "tee": ("branch" if tees[n] < z_top - 1e-9 else "none") if first else e.tee})
                legs[n] = segs
        budgets = {}
        for n in legs:
            static = (lv[floor[n]] / FT + p[pl + "valve_height_in"] / 12) * 0.433
            budgets[n] = pressure_budget(min(p[pl + "max_static_psi"] - falloff, limit_psi), {
                "the shower's valve (Table 604.3)": p[pl + "fixture_psi"],
                "up to the shower": static,
                "the flat's meter": sub(hunter_gpm(per[kind])),
                **({"the master mixing valve": tmv} if kind == "hot" else {}),
            })
        most: dict = {}
        for segs in legs.values():
            for sg in segs:
                most[sg["key"]] = max(most.get(sg["key"], 0.0), sg["gpm"])
        def el(sg: dict, n: float) -> float:
            if all_elbows:
                return (sg["sweeps"] + sg["elbows"]) * fit[n]["elbow"] + fit[n].get(sg["tee"], 0.0)
            return (sg["sweeps"] * p[pl + "pex_sweep_el_d"] * sdr9_bore_in(n) / 12 + sg["elbows"] * fit[n]["elbow"]
                    + fit[n].get(sg["tee"], 0.0))
        def spare(size: dict) -> float:
            return min(budgets[n]["friction_psi"] - sum(pex_psi_per_100ft(sg["gpm"], t_c, sdr9_bore_in(size[sg["key"]]))
                                                        * (sg["ft"] + el(sg, size[sg["key"]])) / 100 for sg in segs)
                       for n, segs in legs.items())

        vel = {k: pex_for(q, p[pl + f"{kind}_fps"], 1e9, t_c)[0] for k, q in most.items()}
        held = {k: max(start[kind][k[0]], vel[k]) for k in most if k[0] != "main"}
        size, how = None, "mains"
        for n_main in [n_ for n_ in PEX_SIZES if n_ >= start[kind]["main"] - 1e-9]:
            trial = {**held, **{k: max(n_main, vel[k]) for k in most if k[0] == "main"}}
            if spare(trial) >= 0:
                size = trial
                break
        if size is None:
            how = "every pipe"
            size = {k: start[kind][k[0]] for k in most}
            for _ in range(3):
                dev = {n: sum(sg["ft"] + el(sg, size[sg["key"]]) for sg in segs) for n, segs in legs.items()}
                rate = min(budgets[n]["friction_psi"] * 100 / dev[n] for n in legs)
                size = {k: pex_for(q, p[pl + f"{kind}_fps"], rate, t_c)[0] for k, q in most.items()}
        dev = {n: sum(sg["ft"] + el(sg, size[sg["key"]]) for sg in segs) for n, segs in legs.items()}
        rate = min(budgets[n]["friction_psi"] * 100 / dev[n] for n in legs)
        by_flat = {}
        for n, segs in legs.items():
            fr = 0.0
            rows = []
            for sg in segs:
                nn = size[sg["key"]]
                f = pex_psi_per_100ft(sg["gpm"], t_c, sdr9_bore_in(nn))
                eq = sg["ft"] + el(sg, nn)
                fr += f * eq / 100
                rows.append({**sg, "in": nn, "psi_100ft": f, "eq_ft": eq, "fps": _fps(sg["gpm"], nn)})
            by_flat[n] = {"friction_psi": fr, "spare_psi": budgets[n]["friction_psi"] - fr, "developed_ft": dev[n], "segments": rows,
                          "budget": budgets[n], "need_psi": budgets[n]["total_psi"] + fr}
        worst = min(by_flat, key=lambda n: by_flat[n]["spare_psi"])
        wv = by_flat[worst]
        # The worst flat's path, its pieces merged by what they are (the main, the riser, the branch).
        merged = []
        for what in ("main", "riser", "branch"):
            ss = [r for r in wv["segments"] if r["segment"] == what]
            merged.append({"segment": f"{what} ({len(ss)} pieces)", "gpm": max(r["gpm"] for r in ss), "ft": sum(r["ft"] for r in ss),
                           "eq_ft": sum(r["eq_ft"] for r in ss), "in": max(r["in"] for r in ss), "fps": max(r["fps"] for r in ss),
                           "psi_100ft": max(r["psi_100ft"] for r in ss)})
        out[kind] = {"budget": wv["budget"], "developed_ft": wv["developed_ft"], "rate_psi_100ft": rate, "segments": merged,
                     "friction_psi": wv["friction_psi"], "spare_psi": wv["spare_psi"], "flat": worst,
                     "by_flat": {n: v["spare_psi"] for n, v in by_flat.items()}, "need_psi": max(v["need_psi"] for v in by_flat.values()),
                     "sizes": {"main": max(v for k, v in size.items() if k[0] == "main"),
                               "main_edges": {k[1]: v for k, v in size.items() if k[0] == "main"},
                               "riser": max(v for k, v in size.items() if k[0] == "riser"), "branch": size[("branch",)]},
                     "fps_max": max(r["fps"] for v in by_flat.values() for r in v["segments"]), "grown": how,
                     "over_fps": [n for n, v in by_flat.items() if any(r["fps"] > p[pl + f"{kind}_fps"] + 1e-9 for r in v["segments"])]}
    return out


def routed_hot_lengths(apt: dict, routes) -> dict[str, float]:
    """IPC 607.2 on the routes: each flat's longest hot pipe (ft) from its riser (the recirculated
    loop) to a fixture, along its routed branch to the fixture's stub-out."""
    from .hvac import FT

    out = {}
    for f in apt["flats"]:
        t = routes.tree(f"plumbing/hot/{f['name']}")
        out[f["name"]] = max(t.path(x)["m"] for x in t.terminals()) / FT
    return out


def design(apt: dict, p: dict, routes=None) -> dict:
    """Step 4's water: the plant, the recirculating loop, and every pipe from the street to the
    highest shower, with what each part costs in pressure. With `routes` (7c), the loop's loss, the
    pressure paths and IPC 607.2 on the routed pipe (`routed_loop`, `routed_paths`,
    `routed_hot_lengths`); else on lengths taken square."""
    from .hvac import FT
    from .loads import hot_water, water
    from .systems import by_flat

    pl, h, g = "systems.plumbing.", "systems.hot_water.", "pass2.good_neighbour."
    m = mains_f(p)
    t_in = m["design_f"]
    w = water(apt, p)
    hw = hot_water(apt, p)
    demand = w["demand_gpm"]

    # The design day's gallons restated at the distribution temperature.
    supply, storage, ret_f = p[h + "distribution_f"], p[h + "storage_f"], p[h + "return_min_f"]
    day_gal = hw["day_gal"] * (p[h + "supply_f"] - t_in) / (supply - t_in)

    # -- the loop: supply mains below the slab to each side, risers up each stack, returns alongside
    mech = next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/mechanical")
    mc = _xy(mech)
    rs = risers(apt)
    rise_ft = apt["storey_m"] * (apt["storeys"] - 1) / FT
    air_f = p["pass3.loads.indoor_c"] * 1.8 + 32
    t_loop = (supply + ret_f) / 2
    ins = lambda n: p[h + ("insulation_in_large" if n >= 1.5 else "insulation_in_small")]  # noqa: E731
    od = lambda n: n + 0.125  # PEX is copper-tube size: OD = nominal + 1/8 in.  # noqa: E731
    hot_c, ret_c = (supply - 32) / 1.8, (ret_f - 32) / 1.8
    sides = _sides(apt, rs)
    n_main = pex_for(demand["half the building"]["hot"], p[pl + "hot_fps"], 1e9, hot_c)[0]
    n_rise = pex_for(demand["a stack (one flat a storey)"]["hot"], p[pl + "hot_fps"], 1e9, hot_c)[0]
    ret_main, ret_rise = 0.5, 0.5  # the returns, sized to the loop's flow below, then the loss again
    for _ in range(3):
        loss, rows = 0.0, []
        for side, keys in sides.items():
            main_ft = max(abs(rs[k]["xy"][0] - mc[0]) + abs(rs[k]["xy"][1] - mc[1]) for k in keys) / FT
            # The mains lie below the slab in ground at about the water mains' temperature; the
            # risers are in the heated building.
            loss += main_ft * (pipe_loss_btuh_ft(od(n_main), ins(n_main), t_loop, t_in, p)
                               + pipe_loss_btuh_ft(od(ret_main), ins(ret_main), t_loop, t_in, p))
            loss += len(keys) * rise_ft * (pipe_loss_btuh_ft(od(n_rise), ins(n_rise), t_loop, air_f, p)
                                           + pipe_loss_btuh_ft(od(ret_rise), ins(ret_rise), t_loop, air_f, p))
            rows.append({"side": side, "main_ft": main_ft, "hot_main_in": n_main, "hot_riser_in": n_rise, "stacks": keys})
        loop_gpm = loss / (60 * RHO_CP * (supply - ret_f))
        sized = (pex_for(loop_gpm / len(sides), p[pl + "return_fps"], 1e9, ret_c),
                 pex_for(loop_gpm / len(rs), p[pl + "return_fps"], 1e9, ret_c))
        if (sized[0][0], sized[1][0]) == (ret_main, ret_rise):
            break
        ret_main, ret_rise = sized[0][0], sized[1][0]
    ret_fps = max(sized[0][1], sized[1][1])
    square_loss, square_rows = loss, rows
    if routes is not None:
        rl = routed_loop(apt, p, routes, t_loop, t_in, air_f, ins, od)
        loss, loop_gpm, rows = rl["loss"], rl["gpm"], rl["rows"]
        ret_main, ret_rise, ret_fps = rl["return_main_in"], rl["return_riser_in"], rl["return_fps"]

    # -- the plant: Ecosizer's swing tank on the design day (Jon, 2026-11-21). The loop returns to the
    # swing tank, whose element covers its loss only when no hot water is passing through.
    prim = ecosizer_swing(day_gal, load_shape(), supply, storage, t_in, loss, p[h + "run_hr"], p[h + "aquastat_fract"],
                          p[h + "strat_slope_f_pct"], p[h + "tm_safety"])
    sday = swing_day(day_gal, load_shape(), supply, storage, t_in, loss, prim["tm_volume_gal"], prim["tm_capacity_kbtuh"])
    # A plate exchanger off the data center's return preheats on the heater's own circuit (no
    # lukewarm water stored); a water-to-water heat pump on the same circuit lifts it to storage.
    # The heat pump's heat comes from the same data center water after the exchanger, its flow
    # throttled so it leaves at the heat pump's source temperature (Jon, 2026-11-21): no unit is
    # rated on 122 F water.
    loop_c = p[g + "liquid_supply_c"] + p[g + "liquid_rise_k"]
    pre_f = (loop_c - p["systems.substation.approach_k"]) * 1.8 + 32
    share_pre = (pre_f - t_in) / (storage - t_in)
    cop, src_f = p[h + "hp_cop"], p[h + "hp_source_f"]
    dc_in_f = loop_c * 1.8 + 32
    # The plant's heat on the design day: the draw from the inlet to the supply temperature, and
    # the loop's loss less what the swing tank's element gives.
    day_kbtu = day_gal * RHO_CP * (supply - t_in) / 1000 + sday["loss_kbtu"] - sday["element_kbtu"]

    # -- the pressure: Appendix E's lines from the building's reducing valve to the top floor's shower
    top_ft = apt["storey_m"] * (apt["storeys"] - 1) / FT + p[pl + "valve_height_in"] / 12
    q_all = demand["the building"]["wsfu"]
    sub = lambda q: _device_psi(q, [(10, p[pl + "submeter_psi_10"]), (13, p[pl + "submeter_psi_13"])])  # noqa: E731
    tmv = _device_psi(demand["the building"]["hot"], [(26, p[pl + "tmv_psi_26"]), (40, p[pl + "tmv_psi_40"])])
    falloff = _device_psi(q_all, [(40, p[pl + "prv_falloff_psi_40"])])
    far = max(square_rows, key=lambda r_: r_["main_ft"])
    far_stack = far["stacks"][0]
    top_flat = rs[far_stack]["flats"][-1]
    bx = _xy(next(r_ for r_ in by_flat(apt)[top_flat] if r_["use"] == "bath"))
    branch_ft = (abs(bx[0] - rs[far_stack]["xy"][0]) + abs(bx[1] - rs[far_stack]["xy"][1])) / FT
    paths = {}
    for kind in ("cold", "hot"):
        t_c = ((supply if kind == "hot" else t_in) - 32) / 1.8
        segs = [("the main to the far side", demand["half the building"][kind], far["main_ft"]),
                ("the riser to the top floor", demand["a stack (one flat a storey)"][kind], top_ft),
                ("the top flat's branch to its shower", demand["a flat"][kind], branch_ft)]
        developed = sum(L for *_, L in segs) * p[pl + "fittings_factor"]
        budget = pressure_budget(p[pl + "max_static_psi"] - falloff, {
            "the shower's valve (Table 604.3)": p[pl + "fixture_psi"],
            "up to the top floor's shower": top_ft * 0.433,
            "the flat's meter": sub(demand["a flat"][kind]),
            **({"the master mixing valve": tmv} if kind == "hot" else {}),
        })
        rate = budget["friction_psi"] * 100 / developed
        sized, friction = [], 0.0
        for name, q, L in segs:
            n, v, f = pex_for(q, p[pl + f"{kind}_fps"], rate, t_c)
            friction += f * L * p[pl + "fittings_factor"] / 100
            sized.append({"segment": name, "gpm": q, "ft": L, "in": n, "fps": v, "psi_100ft": f})
        paths[kind] = {"budget": budget, "developed_ft": developed, "rate_psi_100ft": rate, "segments": sized,
                       "friction_psi": friction, "spare_psi": budget["friction_psi"] - friction}
    upstream = {"the main meter": _device_psi(q_all, [(40, p[pl + "meter_psi_40"])]),
                "the tap in the main (Table E103.3(4))": tap_loss_psi(q_all, p[pl + "tap_in"]),
                "the double check valve assembly": _device_psi(q_all, [(40, p[pl + "dcva_psi_40"])]),
                "up from the main": p[pl + "main_depth_ft"] * 0.433}
    limit = p[pl + "street_psi"] - sum(upstream.values())
    if routes is not None:
        start = {k: {"main": next(s_["in"] for s_ in paths[k]["segments"] if "main" in s_["segment"]),
                     "riser": next(s_["in"] for s_ in paths[k]["segments"] if "riser" in s_["segment"]),
                     "branch": next(s_["in"] for s_ in paths[k]["segments"] if "branch" in s_["segment"])} for k in paths}
        square_paths = paths
        paths = {}
        for k, v in routed_paths(apt, p, routes, falloff, sub, tmv, start, limit).items():
            paths[k] = v
        bound = routed_paths(apt, p, routes, falloff, sub, tmv, start, limit, all_elbows=True)
        for k in paths:
            paths[k]["all_elbows"] = {"spare_psi": bound[k]["spare_psi"], "sizes": bound[k]["sizes"], "developed_ft": bound[k]["developed_ft"]}
            paths[k]["square"] = {"spare_psi": square_paths[k]["spare_psi"], "developed_ft": square_paths[k]["developed_ft"]}
            paths[k]["start_sizes"] = start[k]
    # What the street must give at the peak with the reducing valve wide open: the worse path's
    # needs below the valve, and the meter, the tap, the backflow assembly and the main's depth.
    below = max(paths[k].get("need_psi", paths[k]["budget"]["total_psi"] + paths[k]["friction_psi"]) for k in paths)
    street_need = below + sum(upstream.values())

    # IPC 607.2: no hot pipe longer than 50 ft from the loop (the risers) to a fixture: the far
    # corner of each wet room, square, plus 4 ft up and down.
    longest = 0.0
    for key, r in rs.items():
        for name in r["flats"]:
            for room in by_flat(apt)[name]:
                if room["use"] in ("bath", "kitchen", "utility"):
                    a, b = room["lo_m"], room["hi_m"]
                    d = max(abs(x - r["xy"][0]) + abs(y - r["xy"][1]) for x in (a[0], b[0]) for y in (a[1], b[1]))
                    longest = max(longest, d / FT + 4.0)
    square_longest = longest
    if routes is not None:
        longest = max(routed_hot_lengths(apt, routes).values())
    return {"mains": m, "inlet_f": t_in, "day_gal": day_gal, "primary": prim,
            "heater": {"preheat_f": pre_f, "preheat_share": share_pre, "hp_cop": cop, "day_kbtu": day_kbtu,
                       "hp_kwh_day": day_kbtu * (1 - share_pre) / 3.412142 / cop,
                       "hp_heat_kwh_day": day_kbtu * (1 - share_pre) / 3.412142,
                       "loop_kwh_day": day_kbtu * share_pre / 3.412142,
                       "hp_kw": prim["capacity_kbtuh"] * (1 - share_pre) / 3.412142,
                       "preheat_kw": prim["capacity_kbtuh"] * share_pre / 3.412142,
                       "source_f": src_f, "dc_in_f": dc_in_f,
                       # the data center's flow per the heater circuit's, to leave the exchanger at src_f
                       "dc_per_circuit": (pre_f - t_in) / (dc_in_f - src_f) if dc_in_f > src_f else float("inf"),
                       "cold_end_k": (src_f - t_in) / 1.8,
                       "hp_capacity_ok": p[h + "hp_capacity_btuh"] / 1000 >= prim["capacity_kbtuh"] * (1 - share_pre)},
            "loop": {"loss_btuh": loss, "square_loss_btuh": square_loss, "w_per_flat": loss / 3.412142 / len(apt["flats"]), "gpm": loop_gpm,
                     "return_main_in": ret_main, "return_riser_in": ret_rise, "return_fps": ret_fps,
                     "sides": rows, "rise_ft": rise_ft},
            "tm": {"volume_gal": prim["tm_volume_gal"], "capacity_kbtuh": prim["tm_capacity_kbtuh"], **sday,
                   "kwh_day": sday["element_kbtu"] / 3.412142, "plant_share": 1 - sday["element_kbtu"] / sday["loss_kbtu"]},
            "paths": paths, "falloff_psi": falloff, "street_need_psi": street_need, "upstream": upstream,
            "street_ok": p[pl + "street_psi"] >= street_need, "longest_hot_ft": longest, "square_longest_hot_ft": square_longest,
            "risers": rs, "routed": routes is not None}


# ---- The step as data and as text ----

NAIMA_3_4_TYPE_M = {0.5: 10.35, 0.75: 8.30, 1.0: 7.21, 1.5: 5.91, 2.0: 5.18}  # Btuh/ft, NAIMA CI226 Table 3


def summary(apt: dict, p: dict) -> dict:
    """Step 4 for the latest revision (`apt`), with each known case's check, as data."""
    from .params import load_params

    h, pl = "systems.hot_water.", "systems.plumbing."
    d = design(apt, p)
    ht = d["heater"]
    dv = drains_and_vents(apt, p)
    nz = noise(apt, p)
    eco = ecosizer_primary(100 * 25, load_shape(), 120.0, 150.0, 55.0)
    sw = ecosizer_swing(100 * 25, load_shape(), 120.0, 150.0, 55.0, recirc_loss_btuh(5.0, 120.0, 110.0))
    naima = max(abs(pipe_loss_btuh_ft(0.875, t, 140, 75, p) / v - 1) for t, v in NAIMA_3_4_TYPE_M.items())
    sample = pressure_budget(55.0, {"B": 15.0, "C": 11.0, "D": tap_loss_psi(120, 2), "E": 21 * 0.43, "F": 9.0})
    segs = [s for path in d["paths"].values() for s in path["segments"]]
    over = [s["segment"] for k, path in d["paths"].items() for s in path["segments"] if s["fps"] > p[pl + f"{k}_fps"] + 1e-9]
    spread = load_params()[h + "recirc_w_per_flat"]  # Ecosizer's 25th and 75th percentiles, its low and high
    lo, hi = spread.low, spread.high
    return {
        "revision": apt.get("revision"),
        "checks": [
            ("Ecosizer against its engine's regression (100 people, 25 gpdpp, 120/150/55 F): 84.84 kBtu/h, 567.72 gal; "
             "with a swing tank on a 5 gpm loop at 110 F: 106.71 kBtu/h, 624.06 gal, an 80 gal tank, 43.86 kBtu/h",
             abs(eco["capacity_kbtuh"] / 84.84058984375 - 1) < 1e-6 and abs(eco["storage_gal"] / 567.7208360311284 - 1) < 1e-6
             and abs(sw["capacity_kbtuh"] / 106.70997942167497 - 1) < 1e-6 and abs(sw["storage_gal"] / 624.0605694309057 - 1) < 1e-6
             and sw["tm_volume_gal"] == 80 and abs(sw["tm_capacity_kbtuh"] - 43.85605875) < 1e-6,
             f"{eco['capacity_kbtuh']:.4f} kBtu/h, {eco['storage_gal']:.2f} gal; {sw['capacity_kbtuh']:.4f} kBtu/h, "
             f"{sw['storage_gal']:.2f} gal, {sw['tm_volume_gal']:.0f} gal, {sw['tm_capacity_kbtuh']:.4f}"),
            ("Appendix E's sample problem (E103.3.1): 9.36 psi left for friction", abs(sample["friction_psi"] - 9.36) < 1e-9,
             f"{sample['friction_psi']:.2f} psi"),
            ("pipe heat loss against NAIMA's table (3/4 in. copper, 140 F in 75 F, k 0.28): within 5%, never under",
             naima <= 0.05 and all(pipe_loss_btuh_ft(0.875, t, 140, 75, p) >= v for t, v in NAIMA_3_4_TYPE_M.items()),
             f"worst {naima:.1%}"),
            (f"the loop's loss within Ecosizer's spread of measured buildings ({lo:g}-{hi:g} W a flat)",
             lo - 1e-9 <= d["loop"]["w_per_flat"] <= hi + 1e-9, f"{d['loop']['w_per_flat']:.0f} W a flat"),
            ("hot water stored at 140 F and the loop back at 122 F or more (WHO, CDC)",
             p[h + "storage_f"] >= 140 and p[h + "return_min_f"] >= 122, f"{p[h + 'storage_f']:g} / {p[h + 'return_min_f']:g} F"),
            ("every pipe within its velocity (8 ft/s cold, 5 hot, 2 the return)",
             not over and d["loop"]["return_fps"] <= p[pl + "return_fps"] + 1e-9,
             f"{len(segs)} segments" + (f"; over: {over}" if over else "")),
            ("pressure to spare at the top floor's shower on both paths (Appendix E)",
             all(path["spare_psi"] >= 0 for path in d["paths"].values()),
             ", ".join(f"{k} {path['spare_psi']:.1f} psi" for k, path in d["paths"].items())),
            ("no hot pipe more than 50 ft from the loop to a fixture (IPC 2021 607.2)", d["longest_hot_ft"] <= 50,
             f"longest {d['longest_hot_ft']:.0f} ft"),
            ("the primary storage at least Ecosizer's floor (half the peak hour)", d["primary"]["storage_gal"] >= d["primary"]["minimum_gal"],
             f"{d['primary']['storage_gal']:.0f} gal against {d['primary']['minimum_gal']:.0f}"),
            ("the heat pump inside its maker's table: its source at most 80 F, which the preheat exchanger can cool the data "
             "center's water to; its rated output over its share of the plant",
             ht["source_f"] <= p[h + "hp_source_max_f"] and ht["cold_end_k"] >= p["systems.substation.approach_k"] and ht["hp_capacity_ok"],
             f"source {ht['source_f']:g} F ({ht['cold_end_k']:.1f} K over the inlet); {p[h + 'hp_capacity_btuh'] / 1000:.1f} "
             f"against {ht['hp_kw'] * 3.412142:.1f} kBtu/h"),
            ("stack vents per Table 906.1; no vent stack (three branch intervals); no frost closure (903.2)",
             dv["stack_vent_min_in"] <= dv["stack_in"] and not dv["vent_stack_required"] and not dv["frost_closure"],
             f"{dv['stack_vent_min_in']:g} in. over {dv['vent_developed_ft']:.0f} ft"),
            ("the stacks only in walls of wet rooms", nz["wet_walls_only"], ", ".join(nz["faces"])),
            ("cast-iron stacks under CMHC's 33 dBA for a neighbour's plumbing", nz["margin_db"]["cast_iron"] > 0,
             f"{nz['drain_dba']['cast_iron']:g} dBA, {nz['margin_db']['cast_iron']:g} dB to spare (PVC {nz['margin_db']['pvc']:g})"),
        ],
        "design": d, "drains": dv, "noise": nz,
    }


def report(s: dict) -> str:
    """Step 4 in plain text."""
    from .systems import report as checks

    d, dv, nz = s["design"], s["drains"], s["noise"]
    pr, ht, lp, tm, m = d["primary"], d["heater"], d["loop"], d["tm"], d["mains"]
    lines = [f"Pass 3g step 4: plumbing designed ({s['revision']})", "", checks(s["checks"]), "",
             f"The cold water: the mains at {m['design_f']:.1f} F on the coldest day, {m['mean_f']:.1f} F on average "
             f"(Burch and Christensen, from the site's air: {m['air_avg_f']:.1f} F a year, its monthly means {m['air_monthly_spread_f']:.1f} F apart).",
             "", f"The hot-water plant (design day {d['day_gal']:.0f} gal at 125 F): {pr['capacity_kbtuh']:.1f} kBtu/h "
             f"({pr['capacity_kbtuh'] / 3.412142:.1f} kW) and {pr['storage_gal']:.0f} gal stored at 140 F (Ecosizer; running "
             f"volume {pr['running_gal']:.0f} gal).",
             f"  The data center's return preheats to {ht['preheat_f']:.1f} F: {ht['preheat_share']:.0%} of the heat, "
             f"{ht['preheat_kw']:.1f} kW, {ht['loop_kwh_day']:.0f} kWh on the design day. A water-to-water heat pump lifts the "
             f"rest: {ht['hp_kw']:.1f} kW of heat, from the same water leaving the exchanger at {ht['source_f']:g} F "
             f"({ht['dc_per_circuit']:.2f} x the heater circuit's flow); COP {ht['hp_cop']:g} (ClimateMaster SW036's rating), "
             f"{ht['hp_heat_kwh_day']:.0f} kWh of heat for {ht['hp_kwh_day']:.1f} kWh.",
             f"  The loop: {lp['loss_btuh'] / 3.412142:.0f} W ({lp['w_per_flat']:.0f} a flat), {lp['gpm']:.2f} gpm to hold 125 F "
             f"out and 122 F back; returns {lp['return_main_in']:g} in. mains, {lp['return_riser_in']:g} in. risers (at most "
             f"{lp['return_fps']:.2f} ft/s). It returns to a {tm['volume_gal']:.0f} gal swing tank (Ecosizer) with a "
             f"{tm['capacity_kbtuh'] / 3.412142:.2f} kW element, which runs {tm['element_hr']:.1f} h on the design day: "
             f"{tm['kwh_day']:.1f} kWh, the plant carrying {tm['plant_share']:.0%} of the loop's {tm['loss_kbtu'] / 3.412142:.0f} kWh."]
    for side in lp["sides"]:
        lines.append(f"  {side['side']}: {side['main_ft']:.0f} ft of main, hot {side['hot_main_in']:g} in.; risers {side['hot_riser_in']:g} in. "
                     f"in stacks {', '.join(side['stacks'])}")
    lines += ["", f"The pressure (Appendix E), below a reducing valve at 60 psi static ({d['falloff_psi']:.1f} psi falloff at the peak):"]
    for k, path in d["paths"].items():
        b = path["budget"]
        lines.append(f"  {k}: {b['main_psi']:.1f} psi less " + ", ".join(f"{n} {v:.1f}" for n, v in b["losses"].items())
                     + f" leaves {b['friction_psi']:.1f} for friction over {path['developed_ft']:.0f} ft; friction "
                     f"{path['friction_psi']:.1f}, {path['spare_psi']:.1f} to spare")
        for sg in path["segments"]:
            lines.append(f"    {sg['segment']}: {sg['gpm']:.1f} gpm, {sg['in']:g} in. PEX, {sg['fps']:.1f} ft/s, "
                         f"{sg['psi_100ft']:.1f} psi/100 ft, {sg['ft']:.0f} ft")
    lines.append(f"  The street must give {d['street_need_psi']:.1f} psi at the peak: the above and "
                 + ", ".join(f"{n} {v:.2f}" for n, v in d["upstream"].items()) + ".")
    lines += ["", f"Drains: {len(dv['stacks'])} stacks of {dv['stack_in']:g} in. ({dv['stack_dfu']:g} dfu each), cast iron above the "
              f"slab; stack vents {dv['stack_vent_min_in']:g} in. at least ({dv['vent_developed_ft']:.0f} ft); building drain "
              f"{dv['building_drain_in']:g} in. ({dv['building_dfu']:g} dfu).",
              f"Noise: a neighbour's flush through a cast-iron stack {nz['drain_dba']['cast_iron']:g} dBA against "
              f"{nz['limit_dba']:g} (PVC {nz['drain_dba']['pvc']:g}); supply pipes sleeved, plastic, at 60 psi: "
              f"{nz['supply_usual_db'] - nz['supply_design_db']:.0f} dB under copper clamped rigidly at 80 psi (relative)."]
    return "\n".join(lines)
