"""Pass 3g step 3 (D28): heating, cooling and ventilation, designed from step 2's loads.

**3a, the radiant floors.** Each room's design heat (`loads.room_heat` on the engineered case with
the ERV's outdoor air preheated, `design_case(preheat=True)`) is delivered by ½ in. PEX in the
floor's 1.5 in. gypsum topping (the upper floors) or the slab (the ground floor), every circuit on
one manifold per flat in its utility closet:

- **The floor's output.** REHAU's Radiant Heating Systems Design Guide (855.601, 2017) works one
  case on its performance chart for this construction (Fig. 6.5: a 1.5 in. lightweight overpour,
  ½ in. pipe): 25 Btu/h ft2 at 6 in. spacing under a carpet of R-1.0, the mean water 62 F above the
  room. With EN 1264's surface relation (q = 8.92 (surface - room)^1.1, as pass 3 has it), that
  leaves the topping's own resistance from water to surface (`r_slab`). A room's mean water is
  then its output times that and its covering's resistance, plus the surface's rise. Checked
  against REHAU's chart, read by eye at 20 F (`CHART`); the model asks 4-9% warmer water than the
  chart, the safe side.
  - Pass 3 put the floor at 6 W/m2K from water to room (pass3.radiant.k_h, "judgement, to
    source"). This floor, bare, is about 4.
  - The ground floor's slab has no chart read here; it is taken as the topping.
- **Coverings** (REHAU Table 5.2): sheet linoleum or vinyl (R-0.26) in the living rooms, bedrooms
  and halls; ceramic tile (R-0.23) in the kitchen, bath and utility closet. Laminated hardwood
  (R-0.87) is the alternative the report prices in water temperature.
- **Loops:** 6 in. on centre (REHAU Table 6.2), 4 in. in rooms over `dense_above_w_m2`; the
  rooms under `shared_below_w_m2` share one circuit; each circuit no longer than 330 ft with its
  tails (Table 6.1), the tails twice the walk from the manifold.
- **The water.** One supply: the hardest room's mean water plus half the index loop's 10 F drop.
  Every other loop takes less flow, set at its balancing valve: the flow that, with the water
  cooling along the loop toward the room, delivers the room's heat.
- **Friction:** Darcy-Weisbach with Churchill's (1977) friction factor in SDR 9 PEX, water's
  viscosity by the Vogel equation; held to REHAU's pressure-loss table (855.681, Table 1A).

**3b, ventilation** (`ventilation_ducts`): one ERV a flat (`systems.erv`, Broan's, from HVI's
certified ratings), an electric preheater ahead of it (`loads.preheat_c`, `preheat_energy`) so it
never defrosts and its supply reaches PHI's 16.5 C, its ducts sized by ACCA Manual D's
friction-rate method (`size_paths`).

**3c, cooling** (`cooling_ducts`): one ducted mini-split a flat, the smallest of two Fujitsu units
(`systems.minisplit_12`, `_18`) that covers the flat at the design dry bulb, derated for its line
set to the roof (`unit_capacity`); its supply ducts by Manual D.

**3d, the building loop** (`substation`): a plate heat exchanger in the annex off the data
center's liquid loop, mains below the slab to two risers, a heat meter a flat (`heat_meter`,
Kamstrup's), the pump's head along the worst path.
"""

from __future__ import annotations

import math

from .loads import room_heat, design_case
from .systems import FT, FT2, IN, by_flat

GPM = 6.30902e-5  # m3/s per US gpm
PSI = 6894.757  # Pa
# REHAU 855.681 Table 1A, ½ in. RAUPEX, 100% water: psi per 100 ft at gpm, at 60 F and 120 F.
REHAU_TABLE_1A = {60: {0.1: 0.06, 0.2: 0.11, 0.3: 0.17, 0.4: 0.39, 0.5: 0.57, 0.6: 0.77, 0.7: 1.00, 0.8: 1.26, 0.9: 1.54, 1.0: 1.84},
                  120: {0.1: 0.03, 0.2: 0.10, 0.3: 0.19, 0.4: 0.31, 0.5: 0.46, 0.6: 0.62, 0.7: 0.81, 0.8: 1.03, 0.9: 1.26, 1.0: 1.52}}
# REHAU 855.601 Fig. 6.5 read by eye (+/- 1 Btu/h ft2): (covering R h ft2 F/Btu, spacing in, mean water
# above room F) -> Btu/h ft2. The worked example's point is exact, from the guide's text.
CHART = {(0.0, 6, 20): 14.5, (0.25, 6, 20): 11.8, (0.0, 4, 20): 17.4, (1.0, 6, 62): 25.0}
R_IP = 0.1761102  # m2K/W per h ft2 F/Btu
BTUH_FT2 = 3.154591  # W/m2 per Btu/h ft2


def water_props(t_c: float) -> tuple[float, float]:
    """Water's density (kg/m3, Kell 1975's fit) and dynamic viscosity (Pa s, the Vogel equation
    2.414e-5 x 10^(247.8 / (T - 140)), T in K), the usual closed forms."""
    rho = (999.83952 + 16.945176 * t_c - 7.9870401e-3 * t_c ** 2 - 46.170461e-6 * t_c ** 3 + 105.56302e-9 * t_c ** 4
           - 280.54253e-12 * t_c ** 5) / (1 + 16.879850e-3 * t_c)
    mu = 2.414e-5 * 10 ** (247.8 / (t_c + 273.15 - 140))
    return rho, mu


def churchill_f(re: float, rel_rough: float) -> float:
    """Darcy friction factor over laminar, transitional and turbulent flow, Churchill (1977),
    Chemical Engineering 84(24): 91-92."""
    a = (2.457 * math.log(1 / ((7 / re) ** 0.9 + 0.27 * rel_rough))) ** 16
    b = (37530 / re) ** 16
    return 8 * ((8 / re) ** 12 + 1 / (a + b) ** 1.5) ** (1 / 12)


def pex_psi_per_100ft(gpm: float, t_c: float, bore_in: float) -> float:
    """Friction in straight PEX (psi per 100 ft), Darcy-Weisbach, the pipe taken as hydraulically
    smooth: REHAU's Table 1A bears that out (`test_friction_against_rehau_table_1a`)."""
    if gpm <= 0:
        return 0.0
    d = bore_in * IN
    rho, mu = water_props(t_c)
    v = gpm * GPM / (math.pi * d * d / 4)
    re = rho * v * d / mu
    dp = churchill_f(re, 0.0) * (100 * FT / d) * rho * v * v / 2
    return dp / PSI


def _r_from(q_w_m2: float, dt_k: float, cover_si: float) -> float:
    """The resistance from water to surface (m2K/W) that an output, a mean water rise and a
    covering imply, with EN 1264's surface relation."""
    surface = (q_w_m2 / 8.92) ** (1 / 1.1)
    return dt_k / q_w_m2 - cover_si - surface / q_w_m2


def r_slab(p: dict, spacing_in: float | None = None) -> float:
    """The topping's resistance from water to surface (m2K/W) at a pipe spacing: at 6 in., from
    REHAU's worked example; at 4 in., the example's scaled by the chart's bare-floor reads at 4 and
    6 in. (`CHART`), so the 4 in. value keeps the example's margin."""
    r = "systems.radiant."
    six = _r_from(p[r + "rehau_example_btuh_ft2"] * BTUH_FT2, p[r + "rehau_example_dt_f"] / 1.8,
                  p[r + "rehau_example_cover_r"] * R_IP)
    spacing_in = p[r + "spacing_in"] if spacing_in is None else spacing_in
    if spacing_in == 6:
        return six
    if spacing_in == 4:
        chart = {s_: _r_from(CHART[(0.0, s_, 20)] * BTUH_FT2, 20 / 1.8, 0.0) for s_ in (4, 6)}
        return six * chart[4] / chart[6]
    raise ValueError(f"no chart read for {spacing_in} in. spacing")


def mean_water_rise(q_w_m2: float, cover_r_ip: float, p: dict, spacing_in: float | None = None) -> tuple[float, float]:
    """For an output q (W/m2) under a covering of R (h ft2 F/Btu), at a pipe spacing: the mean
    water's rise over the room (K) and the surface's (K)."""
    if q_w_m2 <= 0:
        return 0.0, 0.0
    surface = (q_w_m2 / 8.92) ** (1 / 1.1)
    return q_w_m2 * (r_slab(p, spacing_in) + cover_r_ip * R_IP) + surface, surface


def chart_check(p: dict) -> list[tuple[tuple, float, float]]:
    """The model against REHAU's chart: (point, the chart's output, the water the model asks for that
    output, as F above the room)."""
    out = []
    for (r, s, dt_f), btuh in CHART.items():
        rise, _ = mean_water_rise(btuh * BTUH_FT2, r, p, s)
        out.append(((r, s, dt_f), btuh, rise * 1.8))
    return out


def covering(use: str, p: dict, alt: bool = False) -> tuple[str, float, float]:
    """A room's floor covering: its name, its R (h ft2 F/Btu) and its surface limit (C): the lesser
    of the covering's (REHAU Table 5.2) and the comfort limit (pass3.radiant.max_floor_c)."""
    r = "systems.radiant."
    if use in ("kitchen", "bath", "utility"):
        name, key = "ceramic tile", "tile"
    elif alt:
        name, key = "laminated hardwood", "laminate"
    else:
        name, key = "sheet linoleum or vinyl", "linoleum"
    limit = min((p[r + f"{key}_max_f"] - 32) / 1.8, p["pass3.radiant.max_floor_c"])
    return name, p[r + f"{key}_r"], limit


def _loop_flow(q_w: float, ua_w_k: float, supply_rise_k: float, cp: float) -> float:
    """The mass flow (kg/s) at which a loop of conductance UA (W/K), its water entering
    `supply_rise_k` above the room and cooling toward it along the loop, delivers q_w."""
    if q_w <= 0:
        return 0.0
    if q_w >= ua_w_k * supply_rise_k:
        raise ValueError("the loop can't deliver its heat even at infinite flow")
    lo, hi = 1e-7, 10.0
    for _ in range(200):
        m = (lo * hi) ** 0.5
        delivered = m * cp * supply_rise_k * (1 - math.exp(-ua_w_k / (m * cp)))
        lo, hi = (m, hi) if delivered < q_w else (lo, m)
    return (lo * hi) ** 0.5


def radiant(apt: dict, p: dict, alt_covering: bool = False, supply_c: float | None = None) -> dict:
    """Every flat's radiant floor: each room's covering, output, mean water and surface; its
    circuits, their lengths, flows and friction; the flat's supply temperature (its own need, or
    `supply_c` if given and no lower), total flow and index circuit."""
    r = "systems.radiant."
    case = design_case(apt, p, preheat=True)
    heat = room_heat(apt, p, case)
    t_room = p["pass3.loads.indoor_c"]
    rooms_by = {r_["id"]: r_ for r_ in apt["rooms"]["rooms"]}
    out = {}
    for name, h in heat.items():
        util = next(r_ for r_ in by_flat(apt)[name] if r_["use"] == "utility")
        man = ((util["lo_m"][0] + util["hi_m"][0]) / 2, (util["lo_m"][1] + util["hi_m"][1]) / 2)
        # Zones: a room with real heat to make up gets its own circuits; the rooms that need little
        # (under shared_below_w_m2: halls, the passage, the wet rooms under the roof) share one,
        # run through them in series. Inside rooms with nothing to make up get none.
        own, low = [], []
        for x in h["rooms"]:
            if x["design_w"] <= 0:
                continue
            (low if x["floor_q_w_m2"] < p[r + "shared_below_w_m2"] else own).append([x])
        zones = own + ([sum(low, [])] if low else [])
        rooms = []
        for z in zones:
            zr = [rooms_by[x["room"]["id"]] for x in z]
            covs = [covering(room["use"], p, alt_covering) for room in zr]
            cov_r = max(c_[1] for c_ in covs)  # the most resistive covering on the circuit sets its water
            limit = min(c_[2] for c_ in covs)
            area = sum(x["heated_m2"] for x in z)
            w = sum(x["design_w"] for x in z)
            q = w / area
            spacing = p[r + "dense_spacing_in"] if q > p[r + "dense_above_w_m2"] else p[r + "spacing_in"]
            pipe_per_ft2 = 12 / spacing  # ft of pipe per ft2 (REHAU Table 6.3: 6 in. 2, 4 in. 3)
            rise, surface = mean_water_rise(q, cov_r, p, spacing)
            tail_ft = max(2 * (abs((room["lo_m"][0] + room["hi_m"][0]) / 2 - man[0])
                               + abs((room["lo_m"][1] + room["hi_m"][1]) / 2 - man[1])) / FT for room in zr)
            field_ft = area / FT2 * pipe_per_ft2
            n = max(1, math.ceil(field_ft / (p[r + "max_circuit_ft"] - tail_ft)))
            shared = len(z) > 1
            rooms.append({"id": f"{name}/shared" if shared else zr[0]["id"], "use": "shared" if shared else zr[0]["use"],
                          "serves": [room["id"] for room in zr],
                          "covering": " and ".join(sorted({c_[0] for c_ in covs})), "cover_r": cov_r, "q_w_m2": q,
                          "spacing_in": spacing, "w": w, "mean_rise_k": rise, "surface_c": t_room + surface,
                          "surface_limit_c": limit, "circuits": n, "circuit_ft": field_ft / n + tail_ft, "heated_m2": area})
        index = max(rooms, key=lambda y: y["mean_rise_k"])
        need_rise = index["mean_rise_k"] + p[r + "index_dt_f"] / 1.8 / 2
        if supply_c is not None and supply_c - t_room < need_rise - 1e-9:
            raise ValueError(f"{name} needs {t_room + need_rise:.1f} C, more than the {supply_c:.1f} C given")
        supply_rise = need_rise if supply_c is None else supply_c - t_room
        t_mean = t_room + supply_rise - p[r + "index_dt_f"] / 1.8 / 2
        rho, _ = water_props(t_mean)
        cp = 4180.0
        for y in rooms:
            ua = y["heated_m2"] * y["q_w_m2"] / y["mean_rise_k"] if y["mean_rise_k"] > 0 else 0.0
            m = _loop_flow(y["w"], ua, supply_rise, cp) if y["w"] > 0 else 0.0
            gpm = m / rho / GPM / y["circuits"]
            y.update({"gpm_per_circuit": gpm, "return_c": t_room + supply_rise - (y["w"] / (m * cp) if m else 0.0),
                      "psi": pex_psi_per_100ft(gpm, t_mean, p[r + "bore_in"]) * y["circuit_ft"] / 100})
        idx = max(rooms, key=lambda y: y["psi"])
        w = sum(y["w"] for y in rooms)
        m = sum(y["gpm_per_circuit"] * y["circuits"] for y in rooms) * GPM * rho
        erv = {"preheat_w": case["flats"][name]["preheat_w"], "supply_c": case["flats"][name]["supply_c"]}
        out[name] = {"rooms": rooms, "supply_c": t_room + supply_rise, "need_c": t_room + need_rise, "index_room": index["id"],
                     "w": w, "return_c": t_room + supply_rise - (w / (m * cp) if m else 0.0),
                     "circuits": sum(y["circuits"] for y in rooms), "erv": erv,
                     "gpm": sum(y["gpm_per_circuit"] * y["circuits"] for y in rooms),
                     "index_circuit": idx["id"], "index_psi": idx["psi"], "index_ft": idx["circuit_ft"],
                     "surface_over_limit": [y["id"] for y in rooms if y["surface_c"] > y["surface_limit_c"] + 1e-9],
                     "too_long": [y["id"] for y in rooms if y["circuit_ft"] > p[r + "max_circuit_ft"] + 1e-9]}
    return out


# ---- 3d, the building loop: the annex's heat exchanger, the mains and the risers ----

def sdr9_bore_in(nominal_in: float) -> float:
    """The bore (in.) of SDR 9 PEX of a copper-tube size: the outside diameter is the nominal plus
    1/8 in. and the wall a ninth of it (the dimension ratio), so 1/2 in. is 0.625 x 7/9 = 0.486 in.,
    as REHAU's velocities say (`bore_in`)."""
    return (nominal_in + 0.125) * 7 / 9


PEX_SIZES_IN = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


def pipe_for_flow(gpm: float, p: dict) -> tuple[float, float]:
    """The smallest SDR 9 PEX size whose velocity at `gpm` stays at or under the design limit:
    (nominal in., ft/s)."""
    for n in PEX_SIZES_IN:
        v = gpm * GPM / (math.pi * (sdr9_bore_in(n) * IN) ** 2 / 4) / FT
        if v <= p["systems.substation.max_velocity_fps"] + 1e-9:
            return n, v
    raise ValueError(f"{gpm:.1f} gpm needs a pipe over 2 in.")


def _centre(r: dict) -> tuple[float, ...]:
    return tuple((a + b) / 2 for a, b in zip(r["lo_m"], r["hi_m"]))


def stacks(apt: dict) -> dict[str, list[str]]:
    """The flats served by each riser: those whose utility closets share a plumbing wall (the
    same side of the stair), all floors."""
    utils = {name: next(r for r in rooms if r["use"] == "utility") for name, rooms in by_flat(apt).items()}
    mid = sum(_centre(u)[1] for u in utils.values()) / len(utils)
    out: dict[str, list[str]] = {}
    for name, u in utils.items():
        out.setdefault("left" if _centre(u)[1] < mid else "right", []).append(name)
    return out


def loop_pump_ft(gpm: float) -> float:
    """The building loop's pump (Grundfos ALPHA2 15-55F) at its highest fixed speed: its head (ft) at
    a flow, read off Grundfos's curve (`data/grundfos_alpha2_15_55_curve3.csv`), straight lines
    between the points."""
    from .loads import _table

    rows = [(float(r["gpm"]), float(r["ft"])) for r in _table("grundfos_alpha2_15_55_curve3.csv")]
    if not rows[0][0] <= gpm <= rows[-1][0]:
        raise ValueError(f"{gpm:.2f} gpm off the pump's curve ({rows[0][0]:g}-{rows[-1][0]:g})")
    for (q0, h0), (q1, h1) in zip(rows, rows[1:]):
        if gpm <= q1:
            return h0 + (h1 - h0) * (gpm - q0) / (q1 - q0)
    return rows[-1][1]


def routed_building_loop(apt: dict, p: dict, routes, flats: dict, t_c: float, meters: dict, riser_in: float = 0.0) -> dict:
    """The building loop on its routes (7c): a riser pair in each column's plumbing wall (7a: the
    spine between the front and back flats takes no pipe, so one pair a column, not one a side), its
    three flats' flow; the mains under the slab edge by edge, each carrying the flats beyond it, the
    smallest PEX within the velocity limit. The pump's head on each flat's path: the supply main to
    its column, up the riser (in pieces between the flats' tees, each carrying the flats above it)
    to its tee, its tail to the manifold, its meter and index circuit, and back the same way on the
    return. Fittings as `plumbing.routed_paths` counts them: a sweep at each bend, an elbow where the
    main turns up and at the manifold, a tee's branch or run at each junction (Uponor's EP). The
    risers no smaller than `riser_in` (`substation`: what the pump's curve asks)."""
    from .plumbing import ep_fittings, stacks as columns

    fit = ep_fittings()
    sweep = p["systems.plumbing.pex_sweep_el_d"]
    cols = columns(apt)
    out_risers, paths = {}, {}
    for kind in ("supply", "return"):
        main = routes.tree(f"main/loop-{kind}")
        for col, names in cols.items():
            q_col = sum(flats[n]["gpm"] for n in names)
            n_rise = max(pipe_for_flow(q_col, p)[0], riser_in)
            fps = q_col * GPM / (math.pi * (sdr9_bore_in(n_rise) * IN) ** 2 / 4) / FT
            tees = {n: routes.tree(f"hvac/loop-{kind}-tail/{n}").root[2] for n in names}
            z_top = max(tees.values())
            if kind == "supply":
                out_risers[col] = {"flats": sorted(names), "gpm": q_col, "pipe_in": n_rise, "fps": fps,
                                   "main_ft": main.path(col)["m"] / FT, "rise_ft": (z_top - main.point(col)[2]) / FT}
            for n in names:
                pieces = []
                for k in main.path(col)["edges"]:
                    e = main.edges[k]
                    q = sum(flats[m]["gpm"] for c in e.below for m in cols[c])
                    pieces.append((q, pipe_for_flow(q, p)[0], (e.length + (main.lead_m if e.up is None else 0.0)) / FT, e.bends, 0, e.tee))
                z0 = main.point(col)[2]
                for i, z in enumerate(sorted(z_ for z_ in tees.values() if z_ <= tees[n] + 1e-9)):
                    q = sum(flats[m]["gpm"] for m, z_ in tees.items() if z_ >= z - 1e-9)
                    pieces.append((q, n_rise, (z - z0) / FT, 0, 1 if i == 0 else 0, "run" if i > 0 else "none"))
                    z0 = z
                tail = routes.tree(f"hvac/loop-{kind}-tail/{n}")
                es = tail.path("manifold")["edges"]
                n_tail = pipe_for_flow(flats[n]["gpm"], p)[0]
                for j, k in enumerate(es):
                    e = tail.edges[k]
                    top = tees[n] >= z_top - 1e-9
                    pieces.append((flats[n]["gpm"], n_tail, (e.length + (tail.lead_m if e.up is None else 0.0)) / FT, e.bends,
                                   (1 if j == 0 and top else 0) + (1 if j == len(es) - 1 else 0),
                                   ("none" if top else "branch") if j == 0 else e.tee))
                psi = 0.0
                for q, nn, ft, sweeps, elbows, tee in pieces:
                    eq = ft + sweeps * sweep * sdr9_bore_in(nn) / 12 + elbows * fit[nn]["elbow"] + fit[nn].get(tee, 0.0)
                    psi += pex_psi_per_100ft(q, t_c, sdr9_bore_in(nn)) * eq / 100
                paths.setdefault(n, {})[kind] = {"psi": psi, "ft": sum(x[2] for x in pieces),
                                                 "largest_main_in": max(x[1] for x in pieces[:len(main.path(col)["edges"])])}
    head = {n: v["supply"]["psi"] + v["return"]["psi"] + meters[n]["psi"] + flats[n]["index_psi"] for n, v in paths.items()}
    worst = max(head, key=head.get)
    return {"risers": out_risers, "paths": paths, "head": head, "worst": worst}


def substation(apt: dict, p: dict, alt_covering: bool = False, routes=None) -> dict:
    """The building loop at design:
    - **the supply:** the hardest flat's need, held by the plate heat exchanger in the annex's
      mechanical room off the data center's liquid loop (its return, pass 2's supply plus rise),
      which must leave `approach_k` between them;
    - **every flat** on that supply, its loops balanced to it (`radiant`);
    - **the mains,** pre-insulated PEX below the slab from the mechanical room to each riser, and
      **the risers** up each plumbing wall, sized to the velocity limit; their lengths taken
      square (along the building's axes) from the mechanical room to the riser and up to the top
      floor, until step 7 routes them;
    - **the primary side:** the data center's water in at its return, out at the building's return
      plus the approach (counterflow)."""
    s_ = "systems.substation."
    g = "pass2.good_neighbour."
    t_primary = p[g + "liquid_supply_c"] + p[g + "liquid_rise_k"]
    own = radiant(apt, p, alt_covering)
    supply = max(f["need_c"] for f in own.values())
    flats = radiant(apt, p, alt_covering, supply_c=supply)
    rho, _ = water_props(supply - 5)
    cp = 4180.0
    w = sum(f["w"] for f in flats.values())
    gpm = sum(f["gpm"] for f in flats.values())
    t_return = supply - w / (gpm * GPM * rho * cp)
    mc = _centre(next(r for r in apt["rooms"]["rooms"] if r["id"] == "annex/mechanical"))
    risers = {}
    for side, names in stacks(apt).items():
        utils = [next(r for r in by_flat(apt)[n] if r["use"] == "utility") for n in names]
        foot = (sum(_centre(u)[0] for u in utils) / len(utils), sum(_centre(u)[1] for u in utils) / len(utils))
        main_m = abs(foot[0] - mc[0]) + abs(foot[1] - mc[1])
        rise_m = max(u["lo_m"][2] for u in utils)
        q = sum(flats[n]["gpm"] for n in names)
        size, fps = pipe_for_flow(q, p)
        risers[side] = {"flats": sorted(names), "gpm": q, "main_ft": main_m / FT, "rise_ft": rise_m / FT,
                        "pipe_in": size, "fps": fps,
                        "psi": pex_psi_per_100ft(q, supply - 5, sdr9_bore_in(size)) * 2 * (main_m + rise_m) / FT / 100}
    header, header_fps = pipe_for_flow(gpm, p)
    # Each flat's heat meter at its design flow; the pump's head along the worst path: its riser
    # (supply and return, at the riser's whole flow all the way: on the safe side), the flat's
    # meter and its index circuit. The exchanger's and the manifold valves' drops come with their
    # selection.
    meters = {n: heat_meter(f["gpm"], p) for n, f in flats.items()}
    side_of = {n: side for side, r in risers.items() for n in r["flats"]}
    path = {n: risers[side_of[n]]["psi"] + meters[n]["psi"] + f["index_psi"] for n, f in flats.items()}
    worst = max(path, key=path.get)
    square = {"risers": risers, "pump_psi": path[worst], "pump_path": worst}
    rl = None
    ft_of = lambda psi: psi * PSI / (rho * 9.80665) / FT  # noqa: E731
    curve = loop_pump_ft(gpm)
    margin = p[s_ + "pump_margin"]
    if routes is not None:
        # The risers grow a size at a time until the pump's highest fixed speed covers the worst
        # path with the margin in hand (9c: at the velocity limit's sizes alone it didn't).
        from .routed import grown

        start = max(max(r["pipe_in"] for r in risers.values()), grown(p).get("loop_riser_in", {}).get("loop", 0.0))
        for size in [n for n in PEX_SIZES_IN if n >= start]:
            rl = routed_building_loop(apt, p, routes, flats, supply - 5, meters, riser_in=size)
            if ft_of(rl["head"][rl["worst"]]) * (1 + margin) <= curve + 1e-9:
                break
        risers, path, worst = rl["risers"], rl["head"], rl["worst"]
        for r in risers.values():
            r["psi"] = max(rl["paths"][n]["supply"]["psi"] + rl["paths"][n]["return"]["psi"] for n in r["flats"])
    t_primary_out = t_return + p[s_ + "approach_k"]
    primary_gpm = w / (cp * (t_primary - t_primary_out)) / water_props(t_primary - 5)[0] / GPM
    return {"flats": flats, "supply_c": supply, "return_c": t_return, "w": w, "gpm": gpm, "risers": risers,
            "header_in": header, "header_fps": header_fps, "primary_in_c": t_primary, "primary_out_c": t_primary_out,
            "primary_gpm": primary_gpm, "margin_k": t_primary - supply, "meters": meters,
            "pump_psi": path[worst], "pump_ft": ft_of(path[worst]), "pump_path": worst,
            "pump_curve_ft": curve, "pump_ok": ft_of(path[worst]) * (1 + margin) <= curve + 1e-9,
            "riser_in": max(r["pipe_in"] for r in risers.values()),
            "approach_ok": t_primary - supply >= p[s_ + "approach_k"] - 1e-9, "square": square, "routed_loop": rl}


def heat_meter(gpm: float, p: dict) -> dict:
    """A flat's heat meter (`systems.heat_meter`, an ultrasonic meter of the smallest size) at a
    flow: the flow in l/h against the meter's least and greatest, and its drop from its kv (the
    flow in m3/h that loses 1 bar): dp = (q / kv)^2 bar."""
    h = "systems.heat_meter."
    q_m3h = gpm * GPM * 3600
    return {"l_h": q_m3h * 1000, "in_range": p[h + "qi_l_h"] <= q_m3h * 1000 <= p[h + "qs_m3h"] * 1000,
            "share_of_qp": q_m3h / p[h + "qp_m3h"], "psi": (q_m3h / p[h + "kv_m3h"]) ** 2 * 1e5 / PSI}


# ---- 3b and 3c, the air side: ducts ----

INWC = 248.84  # Pa per inch of water column
CFM = 4.719474e-4  # m3/s per cfm
DUCT_SIZES_IN = (4, 5, 6, 7, 8, 9, 10, 12)  # none under the ERV's own 4 in. ports


def air_props(p: dict, t_c: float = 21.0) -> tuple[float, float]:
    """Air's density (kg/m3, dry, at the site's station pressure) and viscosity (Pa s,
    Sutherland's law)."""
    t = t_c + 273.15
    rho = p["systems.design.station_pressure_pa"] / (287.055 * t)
    mu = 1.716e-5 * (t / 273.15) ** 1.5 * (273.15 + 110.4) / (t + 110.4)
    return rho, mu


def colebrook_f(re: float, rel_rough: float) -> float:
    """Darcy friction factor by Colebrook's (1939) implicit equation, solved by iteration: the law
    Churchill's closed form approximates in turbulent flow."""
    x = 0.02 ** -0.5
    for _ in range(100):
        x = -2 * math.log10(rel_rough / 3.7 + 2.51 * x / re)
    return 1 / (x * x)


def duct_inwc_per_100ft(cfm: float, d_in: float, p: dict) -> tuple[float, float]:
    """Friction in a round duct (in. w.c. per 100 ft, Darcy-Weisbach with Churchill's factor at the
    duct's roughness) and the velocity (ft/min)."""
    d = d_in * IN
    rho, mu = air_props(p)
    v = cfm * CFM / (math.pi * d * d / 4)
    re = rho * v * d / mu
    f = churchill_f(re, p["systems.ducts.roughness_ft"] * FT / d)
    return f * (100 * FT / d) * rho * v * v / 2 / INWC, v / FT * 60


def duct_size(cfm: float, fr_inwc_100ft: float, p: dict) -> tuple[int, float, float]:
    """The smallest round duct whose friction at `cfm` is no more than the friction rate:
    (in., in. w.c. per 100 ft, ft/min)."""
    for d in DUCT_SIZES_IN:
        fr, v = duct_inwc_per_100ft(cfm, d, p)
        if fr <= fr_inwc_100ft + 1e-12:
            return d, fr, v
    raise ValueError(f"{cfm:.0f} cfm needs a duct over {DUCT_SIZES_IN[-1]} in.")


def _square_ft(a: tuple, b: tuple) -> float:
    return (abs(a[0] - b[0]) + abs(a[1] - b[1])) / FT


def size_paths(unit_xy: tuple, branches: dict, esp: float, p: dict, common: tuple | None = None) -> dict:
    """ACCA Manual D's friction-rate method on one fan's ducts: the pressure the fan has for its
    ducts (its external static pressure at the design airflow, less a grille at each end) over the
    longest path's effective length gives the friction rate; every duct is the smallest round one
    at or under it. `branches`: name -> (cfm, (x, y) its outlet, m), each path's length taken square
    from the unit to its outlet, plus `fittings_el_ft`, until step 7 routes them. `common`: (cfm,
    ft, fittings ft) of a duct every path also runs through (an ERV's outdoor-air duct; a
    mini-split's return)."""
    d = "systems.ducts."
    g = p[d + "grille_inwc"]
    avail = esp - 2 * g
    rows = {k: {"cfm": q, "ft": _square_ft(unit_xy, xy)} for k, (q, xy) in branches.items()}
    c_cfm, c_ft, c_el = common if common else (0.0, 0.0, 0.0)
    tel = c_ft + c_el + max(r["ft"] for r in rows.values()) + p[d + "fittings_el_ft"]
    fr = avail * 100 / tel
    trunk = None
    if common:
        size, tfr, fpm = duct_size(c_cfm, fr, p)
        trunk = {"cfm": c_cfm, "ft": c_ft, "in": size, "fr": tfr, "fpm": fpm, "inwc": tfr * (c_ft + c_el) / 100}
    for r in rows.values():
        r["in"], r["fr"], r["fpm"] = duct_size(r["cfm"], fr, p)
        r["inwc"] = r["fr"] * (r["ft"] + p[d + "fittings_el_ft"]) / 100 + 2 * g + (trunk["inwc"] if trunk else 0.0)
    worst = max(r["inwc"] for r in rows.values())
    return {"esp": esp, "available": avail, "tel_ft": tel, "friction_rate": fr, "branches": rows, "common": trunk,
            "worst_inwc": worst, "ok": worst <= esp + 1e-9}


def tree_ducts(tree, cfm: dict[str, float], esp: float, p: dict, el: dict, common: list[dict] = (), cap: float | None = None,
               plenum_m: float = 0.0) -> dict:
    """Manual D's friction-rate method on a routed duct tree (7c): every piece of duct between two
    junctions carries the air of the outlets beyond it (`cfm`, by terminal), so where the router
    ran one room's duct off another's, that shared piece is a trunk, sized for both. Each path's
    effective length is its measured length and its fittings' equivalent lengths (`el`: an elbow at
    each bend; where it leaves a junction, a take-off, or a reducer where it runs on past one; a
    boot at its outlet), and the `common` ducts every path also runs through (each {ft, bends, el
    (its own fittings), cfm, in (a fixed size, or None)}); the longest sets the friction rate on
    the fan's pressure less a grille at each end, and each piece is the smallest round duct at or
    under it, but no larger than it was routed (`cap`, in.). Pieces within `plenum_m` of the root
    are the supply plenum on the unit's collar (no duct; what leaves them leaves by a take-off).
    Then each path's pressure at those sizes, against the fan's."""
    d = "systems.ducts."
    g = p[d + "grille_inwc"]
    avail = esp - 2 * g
    pieces = []
    for n, e in enumerate(tree.edges):
        ft = (e.length + (tree.lead_m if e.up is None else 0.0)) / FT
        reach = sum(tree.edges[k].length for k in _chain_to(tree, n)) + tree.lead_m
        fit = e.bends * el["elbow"] + {"branch": el["takeoff"], "run": el["reducer"]}.get(e.tee, 0.0) + (el["boot"] if e.terminal else 0.0)
        pieces.append({"ft": ft, "el_ft": fit, "cfm": sum(cfm[t] for t in e.below), "bends": e.bends, "tee": e.tee,
                       "terminal": e.terminal, "plenum": reach <= plenum_m + 1e-9 and not e.terminal})
    for n, e in enumerate(tree.edges):
        if e.up is not None and pieces[e.up]["plenum"] and e.tee == "run":
            pieces[n]["el_ft"] += el["takeoff"] - el["reducer"]
        elif e.tee == "root" and plenum_m > 0 and not pieces[n]["plenum"]:
            pieces[n]["el_ft"] += el["takeoff"]  # one duct out of the plenum before any junction: its starting collar
    com = [{**c_, "tel": c_["ft"] + c_["bends"] * el["elbow"] + c_["el"]} for c_ in common]
    com_tel = sum(c_["tel"] for c_ in com)
    paths = {t: tree.chain(t) for t in tree.terminals()}
    tel = {t: sum(pieces[k]["ft"] + pieces[k]["el_ft"] for k in ks if not pieces[k]["plenum"]) + com_tel for t, ks in paths.items()}
    fr = avail * 100 / max(tel.values())
    for pc in pieces:
        if pc["plenum"]:
            pc.update({"in": None, "fr": 0.0, "fpm": 0.0, "inwc": 0.0, "capped": False})
            continue
        size, _, _ = duct_size(pc["cfm"], fr, p)
        pc["capped"] = cap is not None and size > cap + 1e-9
        pc["in"] = min(size, cap) if cap is not None else size
        pc["fr"], pc["fpm"] = duct_inwc_per_100ft(pc["cfm"], pc["in"], p)
        pc["inwc"] = pc["fr"] * (pc["ft"] + pc["el_ft"]) / 100
    for c_ in com:
        if c_.get("in") is None:
            c_["in"], c_["fr"], c_["fpm"] = duct_size(c_["cfm"], fr, p)
        else:
            c_["fr"], c_["fpm"] = duct_inwc_per_100ft(c_["cfm"], c_["in"], p)
        c_["inwc"] = c_["fr"] * c_["tel"] / 100
    com_inwc = sum(c_["inwc"] for c_ in com)
    out = {t: {"cfm": cfm[t], "ft": sum(pieces[k]["ft"] for k in ks) + sum(c_["ft"] for c_ in com), "tel_ft": tel[t],
               "inwc": sum(pieces[k]["inwc"] for k in ks) + com_inwc + 2 * g, "in": pieces[ks[-1]]["in"]} for t, ks in paths.items()}
    worst = max(x["inwc"] for x in out.values())
    sized = [pc["in"] for pc in pieces if pc["in"] is not None]
    return {"esp": esp, "available": avail, "tel_ft": max(tel.values()), "friction_rate": fr, "pieces": pieces, "paths": out,
            "common": com, "worst_inwc": worst, "ok": worst <= esp + 1e-9, "largest_in": max(sized),
            "capped": sum(1 for pc in pieces if pc["capped"])}


def _chain_to(tree, n: int) -> list[int]:
    out = []
    m = n
    while m is not None:
        out.append(m)
        m = tree.edges[m].up
    return out


def least_esp(tree, cfm: dict[str, float], p: dict, el: dict, common: list[dict], cap: float, plenum_m: float, lo: float,
              hi: float, step: float) -> dict:
    """The mini-split's set static pressure for its ducts as routed: the least, from `lo` by `step`
    up to its maximum `hi`, at which Manual D's sizes (no larger than routed) carry every path
    within it (Fujitsu: 'According to the resistance of the connecting duct, perform the setting of
    the external static pressure'). The last tried if none does."""
    esp = lo
    while True:
        r = tree_ducts(tree, cfm, esp, p, el, common, cap, plenum_m)
        if r["ok"] or esp >= hi - 1e-9:
            return r
        esp = min(hi, round(esp + step, 6))


def routed_ducts(apt: dict, p: dict, routes) -> dict:
    """Step 3's ducts on the routes (7c), each flat's:
    - **the ERV's supply,** through the mini-split (Jon, 2026-11-21): from Broan's Tandem kit along
      the outdoor-air duct to the unit, then its supply duct to the mini-split's return, its whole
      airflow; the mini-split's fan carries it on to the rooms. Its pressure in the mini-split's
      return is taken as nothing (the return's suction would only help);
    - **the ERV's exhaust:** from the kitchen's and the bath's grilles through the exhaust tree to the
      unit, then the exhaust duct to the kit;
    - **the mini-split's supply tree** to its rooms from the plenum on its collar, and its return at
      the unit (no duct: a grille on the return box); its static pressure set to what they need.
    The outdoor-air and exhaust ducts stay at Broan's 5 in.; the rest is sized by `tree_ducts`, no
    larger than routed."""
    from .loads import ventilation

    d, m = "systems.ducts.", "systems.minisplit."
    erv_el = {"elbow": p[d + "erv_elbow_el_ft"], "takeoff": p[d + "erv_takeoff_el_ft"], "reducer": p[d + "reducer_el_ft"],
              "boot": p[d + "erv_boot_el_ft"]}
    ms_el = {"elbow": p[d + "ms_elbow_el_ft"], "takeoff": p[d + "ms_takeoff_el_ft"], "reducer": p[d + "reducer_el_ft"],
             "boot": p[d + "ms_boot_el_ft"]}
    vent = ventilation(apt, p)
    cool = cooling_ducts(apt, p)
    out = {}
    for name, v in vent.items():
        sup_cfm, exh = sum(v["supply"].values()), v["exhaust"]
        routed_in = {k: routes.reqs[f"hvac/{k}/{name}"]["od_m"] / IN for k in ("erv-supply", "erv-exhaust", "ms-supply")}

        def outdoor(kind: str, q: float) -> dict:
            t = routes.tree(f"hvac/erv-{kind}/{name}")
            # Broan's kit at the wall, and its 5-to-4 in. reducer at the unit (manual 2.8).
            return {"ft": t.length_m / FT, "bends": sum(e.bends for e in t.edges), "el": p[d + "termination_el_ft"] + p[d + "reducer_el_ft"],
                    "cfm": q, "in": p["systems.routing.oa_duct_in"], "what": kind}

        supply = tree_ducts(routes.tree(f"hvac/erv-supply/{name}"), {"minisplit": sup_cfm}, p["systems.erv.esp_inwc"], p, erv_el,
                            [outdoor("oa", sup_cfm)], routed_in["erv-supply"])
        ex_tree = routes.tree(f"hvac/erv-exhaust/{name}")
        exhaust = tree_ducts(ex_tree, {t: exh[t] for t in ex_tree.terminals()}, p["systems.erv.esp_inwc"], p, erv_el,
                             [outdoor("ea", sum(exh.values()))], routed_in["erv-exhaust"])
        c = cool[name]
        ms_tree = routes.tree(f"hvac/ms-supply/{name}")
        q = p[f"systems.{c['unit']}.cfm"]
        ms = least_esp(ms_tree, {t: c["ducts"]["branches"][t]["cfm"] for t in ms_tree.terminals()}, p, ms_el,
                       [{"ft": 0.0, "bends": 0, "el": p[d + "ms_return_el_ft"], "cfm": q, "in": None, "what": "return"}],
                       routed_in["ms-supply"], p[m + "plenum_in"] * IN, p[m + "esp_inwc"], p[f"systems.{c['unit']}.esp_max_inwc"],
                       p[m + "esp_step_inwc"])
        out[name] = {"erv_supply": supply, "erv_exhaust": exhaust, "ms": ms, "routed_in": routed_in, "unit": c["unit"],
                     "in_range": p["systems.erv.cfm_min"] <= v["design_cfm"] <= p["systems.erv.cfm_max"]}
    return out


def _xy(r: dict) -> tuple[float, float]:
    c = _centre(r)
    return c[0], c[1]


def outside_wall_ft(apt: dict, r: dict) -> float:
    """From a room's centre to the nearer long facade (the front at x = 0, the back at the depth),
    ft: an ERV's outdoor-air and exhaust ducts run there."""
    x = _centre(r)[0]
    return min(x, apt["depth_m"] - x) / FT


def preheat_energy(apt: dict, p: dict) -> dict:
    """The ERV preheater's electricity a year, a flat: every hour of 2005-2023's ERA5 air at the
    site (as recorded: not the cooling design's shift) under the setpoint, warmed to it at the
    flat's airflow; with the hours it runs."""
    import numpy as np

    from .loads import CFM_M3H, RHO_CP_AIR, preheat_c, ventilation, weather

    wx = weather(p)
    t = np.asarray(wx["t"]) - wx["shift_k"]
    years = len(t) / 8766.0
    cfm = max(v["design_cfm"] for v in ventilation(apt, p).values())
    under = np.clip(preheat_c(p) - t, 0.0, None)
    return {"kwh_year": float(under.sum()) * cfm * CFM_M3H * RHO_CP_AIR / 1000 / years,
            "hours_year": float((under > 0).sum()) / years, "setpoint_c": preheat_c(p), "cfm": cfm}


def ventilation_ducts(apt: dict, p: dict) -> dict:
    """Each flat's ERV (`systems.erv`, basis of design) in its utility closet's ceiling: its supply
    fan pulls outdoor air from the nearer long facade and supplies each bedroom its share
    (`loads.ventilation`); its exhaust fan draws from the kitchen and the bath and exhausts at the
    same facade. Each fan's ducts sized by `size_paths` to the pressure the unit holds across its
    airflow range (it runs at constant airflow)."""
    from .loads import ventilation
    vent = ventilation(apt, p)
    rooms_by = {r["id"]: r for r in apt["rooms"]["rooms"]}
    out = {}
    for name, v in vent.items():
        util = next(r for r in by_flat(apt)[name] if r["use"] == "utility")
        unit = _xy(util)
        wall_ft = outside_wall_ft(apt, util)
        el = p["systems.ducts.fittings_el_ft"]
        sides = {}
        for side, flows in (("supply", v["supply"]), ("exhaust", v["exhaust"])):
            cfm = sum(flows.values())
            sides[side] = size_paths(unit, {rid: (q, _xy(rooms_by[rid])) for rid, q in flows.items()},
                                     p["systems.erv.esp_inwc"], p, common=(cfm, wall_ft, el))
        out[name] = {"cfm": v["design_cfm"], "wall_ft": wall_ft, **sides,
                     "in_range": p["systems.erv.cfm_min"] <= v["design_cfm"] <= p["systems.erv.cfm_max"]}
    return out


def unit_capacity(p: dict, key: str, line_ft: float) -> tuple[float, float]:
    """A mini-split's (total, sensible) cooling capacity (W) at the design dry bulb, indoor 75/63 F:
    a straight line between its 86 F and 95 F rows, times its line-set factor at `line_ft` (a
    straight line between Fujitsu's lengths; none published under 16 ft)."""
    u = f"systems.{key}."
    t_f = p["systems.design.cooling_db_c"] * 1.8 + 32
    k = (t_f - 86) / (95 - 86)
    tot = p[u + "total_86f_btuh"] + k * (p[u + "total_95f_btuh"] - p[u + "total_86f_btuh"])
    sen = p[u + "sensible_86f_btuh"] + k * (p[u + "sensible_95f_btuh"] - p[u + "sensible_86f_btuh"])
    pts = sorted((int(k_[len(u + "line_factor_"):-2]), v) for k_, v in p.items() if k_.startswith(u + "line_factor_"))
    if not pts[0][0] <= line_ft <= pts[-1][0]:
        raise ValueError(f"a {line_ft:.0f} ft line set is off {key}'s table")
    f = next(f0 + (f1 - f0) * (line_ft - l0) / (l1 - l0) for (l0, f0), (l1, f1) in zip(pts, pts[1:]) if l0 <= line_ft <= l1)
    return tot * f / 3.412142, sen * f / 3.412142


def line_set_ft(apt: dict, hall: dict, p: dict) -> float:
    """From a flat's indoor unit (its hall ceiling) up a chase to the roof and across to its
    outdoor unit (ft), and never under the units' least line set (`line_min_ft`): a shorter run is
    made up to it."""
    roof_m = apt["storey_m"] * max(f["floor"] for f in apt["flats"])
    return max((roof_m - hall["hi_m"][2]) / FT + p["systems.minisplit.line_set_horizontal_ft"], p["systems.minisplit.line_min_ft"])


def line_set_m(routes, name: str) -> float:
    """A flat's line set as routed (m): the indoor unit to its riser, up the riser in the plumbing
    wall to the roof, across to the outdoor unit."""
    inner = routes.tree(f"hvac/line-set/{name}")
    roof = routes.tree(f"hvac/roof-line-set/{name}")
    return inner.length_m + (roof.root[2] - inner.root[2]) + roof.length_m


def routed_cooling(apt: dict, p: dict, routes) -> dict:
    """Each flat's mini-split on its routed line set (7c): its capacity at the design dry bulb,
    derated for the line's length by Fujitsu's table (`unit_capacity`; never under its 16 ft),
    against the flat's design sensible and total loads."""
    from .loads import cooling_design

    cool = cooling_design(apt, p)
    sq = cooling_ducts(apt, p, cool)
    out = {}
    for name, c in sq.items():
        line = max(line_set_m(routes, name) / FT, p["systems.minisplit.line_min_ft"])
        tot, sen = unit_capacity(p, c["unit"], line)
        out[name] = {"unit": c["unit"], "square_ft": c["line_ft"], "line_ft": line, "capacity_w": tot, "sensible_capacity_w": sen,
                     "covered": sen >= c["sensible_w"] and tot >= c["sensible_w"] + c["latent_w"],
                     "sensible_w": c["sensible_w"], "latent_w": c["latent_w"]}
    return out


def cooling_ducts(apt: dict, p: dict, cool: dict | None = None) -> dict:
    """Each flat's ducted mini-split: the smallest candidate (`systems.minisplit_12`, then
    `_18`, basis of design) whose sensible and total capacity at the design dry bulb, derated for
    its line set to the roof, cover the flat's design sensible and sensible-plus-latent loads
    (`loads.cooling_design`). Its indoor unit in a dropped ceiling over the flat's hall, a return
    grille beside it, a supply to every room whose design sensible load is at least
    `systems.minisplit.room_min_w`, its airflow the room's share of those rooms' loads at the
    unit's High fan; the ducts sized by `size_paths` to the unit's set external static pressure."""
    from .loads import cooling_design
    m = "systems.minisplit."
    cool = cool or cooling_design(apt, p)
    rooms_by = {r["id"]: r for r in apt["rooms"]["rooms"]}
    out = {}
    for name, rooms in by_flat(apt).items():
        hall = next(r for r in rooms if r["use"] == "hall")
        line = line_set_ft(apt, hall, p)
        sensible, latent = cool["flats"][name][0], cool["latent"][name]
        chosen = None
        for key in ("minisplit_12", "minisplit_18"):
            tot, sen = unit_capacity(p, key, line)
            if sen >= sensible and tot >= sensible + latent:
                chosen = key
                break
        key = chosen or "minisplit_18"
        tot, sen = unit_capacity(p, key, line)
        loads_w = {r["id"]: cool["rooms"][r["id"]][0] for r in rooms if r["id"] in cool["rooms"]}
        served = {rid: w for rid, w in loads_w.items() if w >= p[m + "room_min_w"]}
        total = sum(served.values())
        cfm = p[f"systems.{key}.cfm"]
        branches = {rid: (cfm * w / total, _xy(rooms_by[rid])) for rid, w in served.items()}
        ducts = size_paths(_xy(hall), branches, p[m + "esp_inwc"], p, common=(cfm, 0.0, p["systems.ducts.fittings_el_ft"]))
        out[name] = {"unit": key, "covered": chosen is not None, "line_ft": line, "ducts": ducts,
                     "sensible_w": sensible, "latent_w": latent, "capacity_w": tot, "sensible_capacity_w": sen,
                     "unserved_w": sum(w for rid, w in loads_w.items() if rid not in served)}
    return out


# ---- The step as data and as text ----

def summary(apt: dict, p: dict) -> dict:
    """Step 3 for the latest revision (`apt`), with each known case's check, as data."""
    sub = substation(apt, p)
    alt = radiant(apt, p, alt_covering=True)
    chart = chart_check(p)
    t1a = [(t, g, psi, pex_psi_per_100ft(g, (t - 32) / 1.8, p["systems.radiant.bore_in"]))
           for t, rows in REHAU_TABLE_1A.items() for g, psi in rows.items() if g >= 0.6]
    vent = ventilation_ducts(apt, p)
    cool = cooling_ducts(apt, p)
    worst_t1a = max(abs(m / psi - 1) for _, _, psi, m in t1a)
    meter_qp = heat_meter(p["systems.heat_meter.qp_m3h"] / 3600 / GPM, p)["psi"] * PSI / 1e5
    erv_in = min(f["erv"]["supply_c"] for f in sub["flats"].values())
    pre = preheat_energy(apt, p)
    return {
        "revision": apt.get("revision"),
        "checks": [
            ("the floor against REHAU's worked example and chart (Fig. 6.5): water asked within 0 to +2 F of the chart's",
             all(dt - 0.05 <= m <= dt + 2.0 for (_, _, dt), _, m in chart),
             "; ".join(f"R-{r:g} at {sp} in.: {q:g} Btu/h ft2 at {dt} F, the model {m:.1f} F" for (r, sp, dt), q, m in chart)),
            ("friction in 1/2 in. PEX against REHAU's Table 1A, 0.6-1.0 gpm, 60 and 120 F", worst_t1a <= 0.05, f"worst {worst_t1a:.1%}"),
            ("the heat meter's kv gives its data sheet's 0.03 bar at qp", abs(meter_qp - 0.03) < 5e-4, f"{meter_qp:.4f} bar"),
            ("every floor surface under its covering's and the comfort limit", not any(f["surface_over_limit"] for f in sub["flats"].values()), ""),
            ("every circuit at or under 330 ft (REHAU Table 6.1, 1/2 in.)", not any(f["too_long"] for f in sub["flats"].values()), ""),
            ("the building's supply under the data center's return less the exchanger's approach", sub["approach_ok"],
             f"{sub['supply_c']:.1f} C against {sub['primary_in_c']:.0f} - {p['systems.substation.approach_k']:g}"),
            (f"the building loop's pump covers its worst path at its highest fixed speed, {p['systems.substation.pump_margin']:.0%} in "
             "hand (Grundfos's curve)", sub["pump_ok"], f"{sub['pump_ft']:.1f} ft at {sub['gpm']:.2f} gpm against {sub['pump_curve_ft']:.1f}"),
            ("every flat's heat meter within its measuring range at design", all(m["in_range"] for m in sub["meters"].values()),
             f"{min(m['l_h'] for m in sub['meters'].values()):.0f}-{max(m['l_h'] for m in sub['meters'].values()):.0f} l/h"),
            ("every ERV's supply at or over PHI's minimum at the design hour, with no defrost (preheated to at least Broan's 0 C)",
             erv_in >= p["systems.erv.supply_min_c"] - 1e-9 and pre["setpoint_c"] >= p["systems.erv.preheat_min_c"],
             f"supply {erv_in:.1f} C; preheated to {pre['setpoint_c']:.1f} C"),
            ("every ERV path within its fan's pressure, its airflow within its range",
             all(v[s_]["ok"] and v["in_range"] for v in vent.values() for s_ in ("supply", "exhaust")), ""),
            ("every mini-split path within the unit's pressure", all(c["ducts"]["ok"] for c in cool.values()), ""),
            ("every flat's mini-split covers its design sensible and total loads, derated for its line set",
             all(c["covered"] for c in cool.values()),
             ", ".join(sorted({c["unit"] for c in cool.values()})) + f"; line sets {min(c['line_ft'] for c in cool.values()):.0f}-"
             f"{max(c['line_ft'] for c in cool.values()):.0f} ft"),
            ("the mini-split's set pressure inside its range",
             all(p[f"systems.{c['unit']}.esp_min_inwc"] <= p["systems.minisplit.esp_inwc"] <= p[f"systems.{c['unit']}.esp_max_inwc"]
                 for c in cool.values()), f"{p['systems.minisplit.esp_inwc']:g} in. w.c."),
        ],
        "substation": sub, "laminate_supply_c": {n: f["supply_c"] for n, f in alt.items()}, "preheat": pre,
        "ventilation_ducts": vent, "cooling": cool,
    }


def report(s: dict) -> str:
    """Step 3 in plain text."""
    from .systems import report as checks

    sub = s["substation"]
    lines = [f"Pass 3g step 3: heating, cooling and ventilation designed ({s['revision']})", "", checks(s["checks"]), "",
             f"The building loop at design: {sub['w'] / 1000:.1f} kW, {sub['supply_c']:.1f} C out and {sub['return_c']:.1f} C back, "
             f"{sub['gpm']:.2f} gpm on a {sub['header_in']:g} in. header ({sub['header_fps']:.1f} ft/s); the data center's water "
             f"{sub['primary_in_c']:.0f} -> {sub['primary_out_c']:.1f} C at {sub['primary_gpm']:.2f} gpm; the pump "
             f"{sub['pump_ft']:.1f} ft before the exchanger and valves (worst path {sub['pump_path']}); its highest fixed speed "
             f"gives {sub['pump_curve_ft']:.1f} ft at that flow (Grundfos's curve)."]
    for side, r in sub["risers"].items():
        lines.append(f"  {side} riser: {len(r['flats'])} flats, {r['gpm']:.2f} gpm, {r['pipe_in']:g} in. ({r['fps']:.1f} ft/s), "
                     f"{r['main_ft']:.0f} ft of main and {r['rise_ft']:.0f} ft up, {r['psi']:.2f} psi there and back")
    lines += ["", "The radiant floors (linoleum or vinyl; tile in the wet rooms), each flat on the building's supply:"]
    for n in sorted(sub["flats"], key=lambda n: (n[0], n)):
        f, m = sub["flats"][n], sub["meters"][n]
        lines.append(f"  {n:14s} needs {f['need_c']:.1f} C ({f['index_room'].split('/')[1]}); {f['w']:5.0f} W, {f['circuits']} circuits, "
                     f"{f['gpm']:.2f} gpm, back at {f['return_c']:.1f} C; meter {m['l_h']:.0f} l/h ({m['share_of_qp']:.0%} of qp)")
    ex = sub["flats"]["1-front-left"]
    lines.append("  1-front-left's circuits: " + "; ".join(
        f"{y['id'].split('/')[1]} {y['circuits']} x {y['circuit_ft']:.0f} ft at {y['spacing_in']:g} in., {y['gpm_per_circuit']:.3f} gpm"
        for y in ex["rooms"]))
    lines.append("  laminated hardwood instead would need: " + ", ".join(
        f"floor {k} {v:.1f} C" for k, v in sorted({n[0]: c for n, c in s["laminate_supply_c"].items()}.items())))
    v = s["ventilation_ducts"]["2-front-left"]
    pre, e = s["preheat"], sub["flats"]["2-front-left"]["erv"]
    lines += ["", f"Ventilation, 2-front-left: {v['cfm']:.0f} cfm; outdoor-air and exhaust ducts {v['wall_ft']:.0f} ft to the facade. "
              f"Its preheater: {e['preheat_w']:.0f} W at the design hour, to {pre['setpoint_c']:.1f} C, so the supply leaves at "
              f"{e['supply_c']:.1f} C; {pre['kwh_year']:.0f} kWh a year over {pre['hours_year']:.0f} hours (ERA5 2005-2023)."]
    for side in ("supply", "exhaust"):
        d = v[side]
        lines.append(f"  {side}: fan {d['esp']:.2f} in. w.c. at {sum(b['cfm'] for b in d['branches'].values()):.0f} cfm, friction rate "
                     f"{d['friction_rate']:.3f} in./100 ft; " + ", ".join(
                         f"{k.split('/')[1]} {b['cfm']:.0f} cfm {b['in']} in." for k, b in d["branches"].items())
                     + f"; outdoor duct {d['common']['in']} in.; worst path {d['worst_inwc']:.2f} in. w.c.")
    c = s["cooling"]["2-front-left"]
    d = c["ducts"]
    lines += ["", f"Cooling, 2-front-left: {c['unit']}, {c['line_ft']:.0f} ft of line set; design {c['sensible_w']:.0f} W sensible + "
              f"{c['latent_w']:.0f} W latent against its {c['sensible_capacity_w']:.0f} W sensible of {c['capacity_w']:.0f} W; "
              f"{d['esp']:.2f} in. w.c., friction rate "
              f"{d['friction_rate']:.3f} in./100 ft; " + ", ".join(
                  f"{k.split('/')[1]} {b['cfm']:.0f} cfm {b['in']} in. ({b['fpm']:.0f} fpm)" for k, b in d["branches"].items())
              + f"; return {d['common']['in']} in.; rooms left to the moving air {c['unserved_w']:.0f} W"]
    return "\n".join(lines)
