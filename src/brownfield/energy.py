"""Pass 3g step 10c (D28): each walk-up's energy a year, and what it costs (`brownfield baseline`).

The four walk-ups (10a) share the envelope, the weather, the people and the appliances; only their
systems differ. The weather is every hour of 2005-2023 at the site: ERA5's air as recorded (not the
cooling design's shift) and PVGIS's sun on each wall.

- **Space heat**, each flat hour by hour (`flat_series`). Its walls, glass, roof, slab edge and
  leakage (`loads.room_ua`) lose heat to the outdoor air. Against that come the sun through its
  glass (Addendum 4's SHGC) and the IECC reference design's internal gains. `energy.mass` sets how
  much of a day's surplus carries to its other hours: 0 is each hour alone, 1 the day as a whole.
  No site plan fixes the building's facing, so each of the four is run and averaged. The cases:
  - **the engineered design:** balanced; the ERV recovers heat hour by hour after its preheater
    (`erv_sre`, `loads.preheat_c`); Phius's leakage, which Addendum 8's test holds;
  - **the usual walk-ups:** the bath fan exhausts all year, its air made up through the envelope;
    the code's 3.0 ACH50 leakage; the two combined by LBNL's sub-additivity (`loads.subadditive`,
    `baseline.usual_case`);
  - **between the two:** the engineered design at the code's leakage, so the ERV's share of the
    saving and the airtightness's each have a line.
- **Cooling:** the same model at 75 F, on the days that need no heat; at the mini-split's SEER2,
  or the gas walk-up's air conditioner's. Sensible heat only.
- **Hot water:** each flat's gallons a day by FSEC's model (`fsec_gpd`), on the mains' temperature
  by day (`plumbing.mains_f`). Then:
  - a flat's own heater by its UEF (the electric and gas walk-ups);
  - the central gas heater by its thermal efficiency, with the loops' loss and its tank's;
  - the engineered plant month by month (`plant_day`). Ecosizer's swing tank on the month's
    average day (`plumbing.swing_day`) gives its element's share of the loops' loss. The rest, the
    draw and the tanks' loss, comes from HX-1 on the data center's water and from HP-1 lifting it
    at its COP.
- **Fans, pumps and controls:** the ERV at HVI's watts, the bath fan at Panasonic's, the furnace's
  blower at Goodman's, the circulators at their design duties (`pump_w`).
- **PV** on the house meter: PVGIS's yield for the array the house panel takes.
- **The fallback** (`energy.fallback_h`): those hours' heat on the mini-splits and the plant on
  BK-1, spread over the year like the heat.

The prices are in `baseline.tariff`. The data center's heat is priced at `energy.heat_usd_mwh`
(free in the base case). 10c also gives the heat price at which the engineered design's running
cost meets each usual walk-up's.
"""

from __future__ import annotations

import json
import math

import numpy as np

from . import OUT_DIR
from .baseline import NAMES, WALKUPS
from .loads import RHO_CP_AIR

BTU_KWH = 3412.142
FACINGS = (0, 90, 180, 270)
UTC_TO_LOCAL = 5  # h: PVGIS's stamps are UTC; the site keeps Eastern Standard Time
GPM_FT_W = 0.18852  # W of water power per gpm per ft of head (8.34 lb/gal x 60 / 33,000 hp ft-lb/min x 745.7 W/hp)
HW_HOURS = 8760.0  # h: the hot water's year, the mains' 365 days
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
NL = chr(10)


# ---- the weather and each flat's parts ----

def year_hours(p: dict) -> dict:
    """The site's hours trimmed to whole local days: the air (C, as recorded), each wall's sun
    (W/m2, keyed by compass point), the number of days and of years."""
    from .loads import weather

    wx = weather(p)
    n = (len(wx["t"]) - UTC_TO_LOCAL) // 24 * 24
    cut = slice(UTC_TO_LOCAL, UTC_TO_LOCAL + n)
    out = {k: np.asarray(wx[k], dtype=float)[cut] for k in ("N", "E", "S", "W")}
    out["t"] = (np.asarray(wx["t"], dtype=float) - wx["shift_k"])[cut]
    out["days"], out["years"] = n // 24, n / 24 / 365.25
    return out


def erv_sre(p: dict, t_c):
    """`loads.erv_sensible` on an array: HVI's two tests of the ERV, a straight line between them."""
    t_f = np.asarray(t_c, dtype=float) * 1.8 + 32
    hi, lo = p["systems.erv.sre_32f"], p["systems.erv.sre_m13f"]
    return lo + (hi - lo) * np.clip((t_f + 13) / 45, 0.0, 1.0)


def flat_parts(apt: dict, p: dict, case: dict) -> dict:
    """Each flat's steady parts under `case` (`loads.room_heat`'s shape): its envelope's W/K by part
    (`loads.room_ua`, the ventilation left to `flat_series`), its ventilation (m3/h), its glass by
    face (m2 x SHGC) and its internal gains (W, the IECC reference design's IGain)."""
    from .loads import room_envelopes, room_ua
    from .systems import FT2

    flats = {f["name"]: f for f in apt["flats"]}
    ops = {o["id"]: o for o in apt["openings"]}
    shgc = apt.get("glass_shgc", p["systems.design.shgc"])
    d = "systems.design."
    out = {}
    for name, rows in room_envelopes(apt).items():
        f, c = flats[name], case["flats"][name]
        rooms = room_ua(f, rows, p, {**c, "vent_m3h": 0.0, "recovery": 0.0})
        ua = {k: sum(x["ua_parts"][k] for x in rooms) for k in rooms[0]["ua_parts"]}
        glass: dict[str, float] = {}
        for x in rows:
            for oid in x["room"]["openings"]:
                o = ops[oid]
                if o["glazed"]:
                    glass[o["face"]] = glass.get(o["face"], 0.0) + shgc * o["width_m"] * o["height_m"]
        nbr = sum(x["room"]["use"] == "bedroom" for x in rows)
        igain = (p[d + "igain_btu_day"] + p[d + "igain_btu_day_per_ft2"] * f["floor_m2"] / FT2
                 + p[d + "igain_btu_day_per_bedroom"] * nbr) / 24 / 3.412142
        out[name] = {"ua": ua, "vent_m3h": c["vent_m3h"], "glass": glass, "igain_w": igain, "floor_m2": f["floor_m2"]}
    return out


def flat_series(part: dict, wx: dict, p: dict, az: int, erv: bool, gains: bool = True, t_in: float | None = None):
    """A flat's hours, the front facing `az`: the heat it needs at the heating set point (W,
    negative a surplus), the heat to remove at the cooling set point (W, negative none), and its ERV
    preheater's power (W). The set points are RECS's households' (`energy.heat_set_f`,
    `cool_set_f`); `t_in` sets the heating one instead (the design hour's check). With `erv`, the
    outdoor air is warmed to `loads.preheat_c` and then the ERV recovers `erv_sre` of the rest;
    without, the fan's air comes in at the outdoor temperature."""
    from .loads import facing, preheat_c

    t = wx["t"]
    e = "baseline.energy."
    t_in = (p[e + "heat_set_f"] - 32) / 1.8 if t_in is None else t_in
    t_cool = (p[e + "cool_set_f"] - 32) / 1.8
    fd = facing(az)
    gain = sum(g * wx[fd[face]] for face, g in part["glass"].items()) + part["igain_w"] if gains else 0.0
    ua = part["ua"]
    h_heat = sum(v for k, v in ua.items() if k != "ventilation")
    h_cool = h_heat - ua["slab edge"]  # as `loads.room_cooling`: the slab edge against the cooler ground left out
    q = part["vent_m3h"] * RHO_CP_AIR  # W/K
    if erv:
        core = np.maximum(t, preheat_c(p))
        vent_heat = q * (t_in - (core + erv_sre(p, core) * (t_in - core)))
        pre_w = q * (core - t)
        vent_cool = q * (t + erv_sre(p, t) * (t_cool - t) - t_cool)
    else:
        vent_heat, pre_w, vent_cool = q * (t_in - t), np.zeros_like(t), q * (t - t_cool)
    return h_heat * (t_in - t) + vent_heat - gain, h_cool * (t - t_cool) + vent_cool + gain, pre_w


def season(loss, gain, days: int, mass: float) -> tuple[np.ndarray, np.ndarray]:
    """Each day's heat and cooling (Wh): hour by hour (each hour's surplus lost) blended with the
    day as a whole (its surplus carried within it) by `mass`. Cooling only on days that need no
    heat on balance."""
    L, G = np.asarray(loss).reshape(days, 24), np.asarray(gain).reshape(days, 24)
    heat = (1 - mass) * np.clip(L, 0, None).sum(1) + mass * np.clip(L.sum(1), 0, None)
    cool = (1 - mass) * np.clip(G, 0, None).sum(1) + mass * np.clip(G.sum(1), 0, None)
    return heat, np.where(L.sum(1) <= 0, cool, 0.0)


def cases(apt: dict, p: dict) -> dict:
    """The three envelopes of air: the engineered design (Phius's leakage, the ERV and its
    preheater), the same at the code's leakage (balanced, so the leakage adds), and the usual
    walk-ups (the bath fan and the code's leakage, sub-additive). Each (case, has an ERV)."""
    from .baseline import usual_case
    from .loads import design_case

    eng, usual = design_case(apt, p, preheat=True), usual_case(apt, p)
    code = {"flats": {n: {**c, "infil_m3h": usual["flats"][n]["natural_m3h"]} for n, c in eng["flats"].items()}}
    return {"engineered": (eng, True), "engineered at the code's leakage": (code, True), "usual": (usual, False)}


def space(apt: dict, p: dict, wx: dict) -> dict:
    """Each case's year, a flat and the building: the heat delivered, the cooling removed, the
    preheater's electricity (kWh); the hours the building needs heat (the loop pump's); and, for the
    usual walk-ups, Fujitsu's full-capacity COP weighted by the year's heat (a floor on the
    seasonal COP taken)."""
    from .fallback import heating_table

    tab = heating_table()
    cop = np.interp(wx["t"], [r[0] for r in tab], [r[1] / r[2] for r in tab])
    m = p["baseline.energy.mass"]
    out = {}
    for key, (case, erv) in cases(apt, p).items():
        parts = flat_parts(apt, p, case)
        flats = {n: {"heat_kwh": 0.0, "cool_kwh": 0.0, "pre_kwh": 0.0} for n in parts}
        on_h, wq, wi = 0.0, 0.0, 0.0
        for az in FACINGS:
            bld = np.zeros_like(wx["t"])
            for n, part in parts.items():
                loss, gain, pre = flat_series(part, wx, p, az, erv)
                heat, cool = season(loss, gain, wx["days"], m)
                k = 1e3 * wx["years"] * len(FACINGS)
                flats[n]["heat_kwh"] += float(heat.sum()) / k
                flats[n]["cool_kwh"] += float(cool.sum()) / k
                flats[n]["pre_kwh"] += float(pre.sum()) / k
                bld += loss
            on_h += float((bld > 0).sum()) / wx["years"] / len(FACINGS)
            pos = np.clip(bld, 0, None)
            wq, wi = wq + float(pos.sum()), wi + float((pos / cop).sum())
        tot = {k: sum(v[k] for v in flats.values()) for k in ("heat_kwh", "cool_kwh", "pre_kwh")}
        out[key] = {"flats": flats, "building": tot, "heat_on_h": on_h, "table_cop": wq / wi, "parts": parts}
    return out


def design_hour_check(apt: dict, p: dict) -> float:
    """The hourly model at the heating design hour, no sun and no gains, against `loads.room_heat`'s
    design heat of the engineered design with its preheater: the worst flat's difference (W)."""
    from .loads import design_case, room_heat

    case = design_case(apt, p, preheat=True)
    want = room_heat(apt, p, case)
    wx = {"t": np.array([p["systems.design.heating_c"]]), **{k: np.zeros(1) for k in ("N", "E", "S", "W")}}
    worst = 0.0
    for n, part in flat_parts(apt, p, case).items():
        loss, _, _ = flat_series(part, wx, p, 180, True, gains=False, t_in=p["pass3.loads.indoor_c"])
        worst = max(worst, abs(float(loss[0]) - want[n]["design_w"]))
    return worst


# ---- hot water ----

def fsec_gpd(p: dict, occupants: float, mains_f):
    """A flat's hot water a day (gal at the tap's temperature), FSEC-PF-464-15's Eq. 11:
    22 x occupants x Fmix for showers, baths and faucets, Fmix = 1 - (Tset - Tmix)/(Tset - Tmains);
    with its clothes washer (gal a cycle x (123 + 61 occupants)/365, Eq. 2) and dishwasher (gal a
    cycle x (91 + 30 occupants)/365, Eq. 3)."""
    e = "baseline.energy."
    tset, tmix = p["systems.hot_water.supply_f"], p[e + "tmix_f"]
    fmix = 1 - (tset - tmix) / (tset - np.asarray(mains_f, dtype=float))
    cw = p[e + "cw_gal_cycle"] * (123 + 61 * occupants) / 365
    dw = p[e + "dw_gal_cycle"] * (91 + 30 * occupants) / 365
    return p[e + "fixture_gpd_per_occ"] * occupants * fmix + cw + dw


def tank_loss_w(dia_in: float, h_in: float, water_f: float, p: dict) -> float:
    """A tank's standby loss (W): its shell (sides, top and bottom) through `energy.tank_r` to the
    plant room."""
    e = "baseline.energy."
    a = math.pi * dia_in / 12 * h_in / 12 + 2 * math.pi * (dia_in / 24) ** 2
    return a * (water_f - (p[e + "plant_room_c"] * 1.8 + 32)) / p[e + "tank_r"] / 3.412142


def pump_w(gpm: float, ft: float, p: dict) -> float:
    """A circulator's power at its duty (W): water power over `energy.pump_eff`."""
    return gpm * ft * GPM_FT_W / p["baseline.energy.pump_eff"]


def plant_day(p: dict, s7: dict, day_gal: float, inlet_f: float, loss_btuh: float, tm_kbtuh: float, standby_btuh: float) -> dict:
    """The engineered plant on one day (kBtu, kWh): the draw (`day_gal` at the tap's temperature)
    restated at the distribution temperature, Ecosizer's swing tank on it (its element's heat), and
    the rest from the primary: HX-1's share on the data center's water (to its preheat temperature)
    and HP-1's at its COP, whose own source is that water."""
    from .plumbing import RHO_CP, load_shape, swing_day

    h = "systems.hot_water."
    tap, dist, storage = p[h + "supply_f"], p[h + "distribution_f"], p[h + "storage_f"]
    hx = s7["water"]["heater"]
    gal = day_gal * (tap - inlet_f) / (dist - inlet_f)
    sday = swing_day(gal, load_shape(), dist, storage, inlet_f, loss_btuh, s7["water"]["tm"]["volume_gal"], tm_kbtuh)
    draw = day_gal * RHO_CP * (tap - inlet_f) / 1000
    plant = draw + sday["loss_kbtu"] - sday["element_kbtu"] + standby_btuh * 24 / 1000
    share = (hx["preheat_f"] - inlet_f) / (storage - inlet_f)
    cop = p[h + "hp_cop"]
    return {"draw_kbtu": draw, "element_kbtu": sday["element_kbtu"], "plant_kbtu": plant, "preheat_share": share,
            "hp_kwh": plant * (1 - share) / cop * 1000 / BTU_KWH, "element_kwh": sday["element_kbtu"] * 1000 / BTU_KWH,
            "dc_kwh": (plant * share + plant * (1 - share) * (cop - 1) / cop) * 1000 / BTU_KWH,
            "plant_kwh": plant * 1000 / BTU_KWH}


def hot_water(apt: dict, p: dict, s7: dict) -> dict:
    """Each walk-up's hot water a year: each flat's use (gal, kWh of heat at the tap), its own
    heaters' energy, the central heater's, the engineered plant's month by month."""
    from .plumbing import RHO_CP, mains_f

    e, h, hs, rt = "baseline.energy.", "systems.hot_water.", "systems.house.", "systems.routing."
    n = len(apt["flats"])
    tm = mains_f(p)["daily_f"]
    gpd = fsec_gpd(p, p[e + "occupants"], tm)
    flat_btu = gpd * RHO_CP * (p[h + "supply_f"] - tm)  # each day's heat at the tap, a flat
    flat_kwh = float(flat_btu.sum()) / BTU_KWH
    loop_btuh = s7["water"]["loop"]["loss_btuh"]
    storage, dist = p[h + "storage_f"], p[h + "distribution_f"]

    # The engineered plant: the primary's tanks (ST-1A and ST-1B, and BK-1 on its circuit) at the
    # storage temperature; the swing tank at the distribution temperature, its loss on its element.
    primary_w = p[rt + "tank_count"] * tank_loss_w(p[rt + "tank_dia_in"], p[rt + "tank_h_in"], storage, p) \
        + tank_loss_w(p[rt + "backup_dia_in"], p[rt + "backup_h_in"], storage, p)
    swing_w = tank_loss_w(p[rt + "swing_dia_in"], p[rt + "swing_h_in"], dist, p)
    tm_kbtuh = p[hs + "swing_element_va"] * 3.412142 / 1000  # its element as built
    months, d0 = [], 0
    for days in MONTH_DAYS:
        sl = slice(d0, d0 + days)
        d0 += days
        day = plant_day(p, s7, n * float(gpd[sl].mean()), float(tm[sl].mean()), loop_btuh + swing_w * 3.412142, tm_kbtuh,
                        primary_w * 3.412142)
        months.append({k: v * days for k, v in day.items() if k not in ("preheat_share",)} | {"days": days})
    eng = {k: sum(mo[k] for mo in months) for k in months[0]}
    cap = s7["water"]["primary"]["capacity_kbtuh"]
    p2_h = eng["plant_kbtu"] / cap  # the heater circuit's pump, while the primary heats
    central_w = tank_loss_w(p[e + "central_dia_in"], p[e + "central_h_in"], storage, p)
    central_gas = (n * flat_kwh + (loop_btuh / 3.412142 + central_w) * HW_HOURS / 1000) / p[e + "central_te"]
    own_gas = flat_kwh / p[e + "gas_heater_uef"]
    rc = s7["water"]["recirc"]
    return {"gpd": float(gpd.mean()), "gpd_min": float(gpd.min()), "gpd_max": float(gpd.max()), "flat_kwh": flat_kwh,
            "mains_mean_f": float(tm.mean()), "loop_w": loop_btuh / 3.412142,
            "electric_kwh": flat_kwh / p[e + "heater_uef"], "own_gas_kwh": own_gas,
            "own_gas_fan_kwh": own_gas * BTU_KWH / p[e + "gas_heater_in_btuh"] * p[e + "gas_heater_fan_w"] / 1000,
            "central_gas_kwh": central_gas, "central_tank_w": central_w,
            "central_fan_kwh": central_gas * BTU_KWH / (p["baseline.usual.central_heater_kbtuh"] * 1000) * p[e + "gas_heater_fan_w"] / 1000,
            "recirc_kwh": pump_w(rc["gpm"], rc["ft"], p) * HW_HOURS / 1000, "recirc_w": pump_w(rc["gpm"], rc["ft"], p),
            "plant": eng, "months": months, "primary_tanks_w": primary_w, "swing_tank_w": swing_w,
            "p2_kwh": pump_w(p[e + "p2_gpm"], p[e + "p2_head_ft"], p) * p2_h / 1000, "p2_h": p2_h}


def plant_design_check(p: dict, s7: dict) -> dict:
    """`plant_day` on step 4's design day (its gallons and coldest inlet, Ecosizer's element, no
    tanks' loss) against step 4's own figures: HP-1's electricity and the swing element's heat."""
    w = s7["water"]
    h = "systems.hot_water."
    day_tap = w["day_gal"] * (p[h + "distribution_f"] - w["inlet_f"]) / (p[h + "supply_f"] - w["inlet_f"])
    d = plant_day(p, s7, day_tap, w["inlet_f"], w["loop"]["loss_btuh"], w["tm"]["capacity_kbtuh"], 0.0)
    return {"hp_kwh": d["hp_kwh"], "want_hp_kwh": w["heater"]["hp_kwh_day"], "element_kbtu": d["element_kbtu"],
            "want_element_kbtu": w["tm"]["element_kbtu"]}


# ---- each walk-up's meters ----

def ledger(apt: dict, p: dict, s7: dict, sp: dict, hw: dict) -> list[dict]:
    """Every walk-up's energy a year by end use and meter, the building's: `flats` (the flats' own
    electric meters), `house` (the house meter, before PV), `pv` (on the house meter), `gas flats`,
    `gas house` (kWh of gas), `heat` (kWh from the data center). The flats' lights, appliances and
    plugs, alike in every walk-up, are left out. The house's continuous loads (its lights, the fire
    alarm, the telecom backboard; `house_own_w`) are alike too but kept in: they set the house
    meter's rate class with the rest."""
    e, sx = "baseline.energy.", "systems.erv."
    n = len(apt["flats"])
    fb = p[e + "fallback_h"] / 8766.0
    scop, s19, sac = p[e + "hp_scop"], p[e + "seer2_minisplit"], p[e + "seer2_ac"]
    eng, usual = sp["engineered"], sp["usual"]
    from .loads import ventilation

    erv_w = sum(v["design_cfm"] for v in ventilation(apt, p).values()) * p[sx + "watts_49cfm"] / 49.0  # HVI's 28 W at 49 cfm, by each flat's airflow
    fan_w = n * p["baseline.usual.bath_fan_w"]
    loop = s7["loop"]
    pl = hw["plant"]
    pv = s7["electrical"]["pv"]
    pv_kwh = pv["house_ac_kw"] * p["systems.pv.dc_ac"] * pv["kwh_per_kwp"]
    rows = []

    def add(w, use, meter, kwh):
        rows.append({"walkup": w, "use": use, "meter": meter, "kwh": float(kwh)})

    # The engineered design.
    add("engineered", "space heat", "heat", (1 - fb) * eng["building"]["heat_kwh"])
    add("engineered", "space heat", "flats", fb * eng["building"]["heat_kwh"] / scop)  # the fallback, on the mini-splits
    add("engineered", "space heat", "house", pump_w(loop["gpm"], loop["pump_ft"], p) * eng["heat_on_h"] / 1000)  # P-1
    add("engineered", "ventilation", "flats", erv_w * 8766 / 1000 + eng["building"]["pre_kwh"])
    add("engineered", "cooling", "flats", eng["building"]["cool_kwh"] * BTU_KWH / s19 / 1000)
    add("engineered", "hot water", "house", (1 - fb) * pl["hp_kwh"] + fb * pl["plant_kwh"] + pl["element_kwh"]
        + hw["recirc_kwh"] + hw["p2_kwh"])
    add("engineered", "hot water", "heat", (1 - fb) * pl["dc_kwh"])
    add("engineered", "controls", "house", p[e + "controls_w"] * 8766 / 1000)
    add("engineered", "pv", "pv", -pv_kwh)
    # The usual walk-ups.
    for w in ("electric", "central"):
        add(w, "space heat", "flats", usual["building"]["heat_kwh"] / scop)
        add(w, "cooling", "flats", usual["building"]["cool_kwh"] * BTU_KWH / s19 / 1000)
        add(w, "ventilation", "flats", fan_w * 8766 / 1000)
    add("electric", "hot water", "flats", n * hw["electric_kwh"])
    add("central", "hot water", "gas house", hw["central_gas_kwh"])
    add("central", "hot water", "house", hw["recirc_kwh"] + hw["central_fan_kwh"])
    heat_g = usual["building"]["heat_kwh"]
    add("gas", "space heat", "gas flats", heat_g / p[e + "furnace_afue"])
    add("gas", "space heat", "flats", heat_g * BTU_KWH / p[e + "furnace_out_btuh"] * p[e + "furnace_fan_w"] / 1000)
    add("gas", "cooling", "flats", usual["building"]["cool_kwh"] * BTU_KWH / sac / 1000)
    add("gas", "ventilation", "flats", fan_w * 8766 / 1000)
    add("gas", "hot water", "gas flats", n * hw["own_gas_kwh"])
    add("gas", "hot water", "flats", n * hw["own_gas_fan_kwh"])
    own = house_own_w(apt, p) * 8766 / 1000
    for w in WALKUPS:
        add(w, "the house's own", "house", own)
    return rows


def house_own_w(apt: dict, p: dict) -> float:
    """The house panel's continuous loads, alike in every walk-up (W): the stair's luminaires (one at
    each landing, `electrical.house_loads`), the exterior lights, the fire alarm, the telecom
    backboard. The annex's lights and the receptacles, used now and then, are left out."""
    h = "systems.house."
    return (len(apt["stair"]["flights"]) + 1) * p[h + "stair_luminaire_w"] + p[h + "exterior_lights_va"] + p[h + "fire_alarm_va"] \
        + p[h + "telecom_va"]


def house_demand(apt: dict, p: dict, s7: dict, hw: dict) -> dict:
    """Each walk-up's house meter at its most (kW), for a demand charge: what runs together in a
    normal month, and in the month the data center's heat is gone. The engineered design's: HP-1 at
    its rated input with the swing element, the pumps, the controls and the house's own loads; in
    the fallback BK-1 in HP-1's place. The central walk-up's: its pump and its heater's blower."""
    e, hs = "baseline.energy.", "systems.house."
    own = house_own_w(apt, p)
    loop, rc = s7["loop"], s7["water"]["recirc"]
    pumps = pump_w(loop["gpm"], loop["pump_ft"], p) + pump_w(rc["gpm"], rc["ft"], p) + pump_w(p[e + "p2_gpm"], p[e + "p2_head_ft"], p)
    base = p[hs + "swing_element_va"] + pumps + p[e + "controls_w"] + own
    central = pump_w(rc["gpm"], rc["ft"], p) + p[e + "gas_heater_fan_w"] + own
    return {"engineered": {"normal_kw": (base + p[e + "hp1_input_w"]) / 1000, "fallback_kw": (base + p["systems.hot_water.backup_w"]) / 1000},
            "electric": {"normal_kw": own / 1000, "fallback_kw": own / 1000}, "gas": {"normal_kw": own / 1000, "fallback_kw": own / 1000},
            "central": {"normal_kw": central / 1000, "fallback_kw": central / 1000}}


def costs(rows: list[dict], p: dict, flats: int, demand: dict | None = None) -> dict:
    """Each walk-up's running cost a year (USD, the building's) by meter:
    - the flats' electricity at Penelec's residential price;
    - the house meter on GS-Small, or on GS-Medium if it takes more than GS-Small's 1,500 kWh a
      month on average (before PV): GS-Medium's lower energy price, its demand charge (`demand`;
      a fallback month's peak held at half for the next eleven by its ratchet), its customer charge;
      PV credited at the meter's energy price up to its use, any excess over the year at the price
      to compare (52 Pa. Code 75.13);
    - gas by the Mcf: each flat's own account (Peoples RS) or the central heater's (SGS, its customer
      charge by its tier);
    - the data center's heat at `energy.heat_usd_mwh`."""
    from .cost import MCF_MWH

    t = "baseline.tariff."
    fallback = p["baseline.energy.fallback_h"] > 0
    out = {}
    for w in WALKUPS:
        m = {k: sum(r["kwh"] for r in rows if r["walkup"] == w and r["meter"] == k)
             for k in ("flats", "house", "pv", "gas flats", "gas house", "heat")}
        net = m["house"] + m["pv"]
        gsm = m["house"] / 12 > p[t + "gss_limit_kwh_month"]
        rate = p[t + "house_gsm_usd_kwh"] if gsm else p[t + "house_gss_usd_kwh"]
        energy = net * rate if net >= 0 else net * p[t + "pv_excess_usd_kwh"]
        d = (demand or {}).get(w, {"normal_kw": 0.0, "fallback_kw": 0.0})
        kw_months = 11 * max(d["normal_kw"], 0.5 * d["fallback_kw"]) + d["fallback_kw"] if fallback else 12 * d["normal_kw"]
        house = energy + (kw_months * p[t + "house_gsm_usd_kw"] if gsm else 0.0) \
            + 12 * p[t + ("house_gsm_customer_usd_month" if gsm else "house_gss_customer_usd_month")]
        mcf_f, mcf_h = m["gas flats"] / 1000 / MCF_MWH, m["gas house"] / 1000 / MCF_MWH
        gas_f = mcf_f * p[t + "gas_res_usd_mcf"] + (flats * 12 * p[t + "gas_res_customer_usd_month"] if mcf_f else 0.0)
        tier = "gas_com_customer_large_usd_month" if mcf_h >= p[t + "gas_com_tier_mcf"] else "gas_com_customer_small_usd_month"
        gas_h = mcf_h * p[t + "gas_com_usd_mcf"] + (12 * p[t + tier] if mcf_h else 0.0)
        heat = m["heat"] / 1000 * p["baseline.energy.heat_usd_mwh"]
        lines = {"flats' electricity": m["flats"] * p[t + "elec_res_usd_kwh"], "the house meter, net of PV": house,
                 "the flats' gas": gas_f, "the house's gas": gas_h, "the data center's heat": heat}
        out[w] = {"meters": m, "usd": lines, "total": sum(lines.values()), "net_house_kwh": net, "house_class": "GS-Medium" if gsm else "GS-Small",
                  "billing_kw_months": kw_months if gsm else 0.0, "gas_mcf": mcf_f + mcf_h}
    return out


def tie_price(c: dict) -> dict:
    """The price of the data center's heat (USD/MWh) at which the engineered design's running cost
    equals each usual walk-up's, its other costs as they are."""
    e = c["engineered"]
    mwh = e["meters"]["heat"] / 1000
    rest = e["total"] - e["usd"]["the data center's heat"]
    return {w: (c[w]["total"] - rest) / mwh for w in WALKUPS[1:]}


# ---- the known cases ----

def recs_cases(apt: dict, p: dict, sp: dict, hw: dict, wx: dict) -> dict:
    """The model's flats against RECS 2020's households (apartments in buildings of 5 or more
    units), ratio of means with the jackknife's error:
    - a flat's own electric water heater, kWh per occupant (2-bedroom flats);
    - a flat's own gas water heater, kBtu per occupant;
    - the usual flats' space heat, Wh delivered per ft2 per heating degree day (65 F), against
      RECS's flats in climate zones 4A and 5A built 2000 or later: those heated by their own heat
      pump (its electricity times the stock's seasonal COP, `check.recs_stock_hp_cop`) and those by
      their own gas furnace (its gas times the stock's AFUE, `check.recs_stock_afue`). RECS gives
      the energy bought, not the heat; its households' equipment is older than the model's, so the
      heat is what can be compared."""
    import pandas as pd

    from .baseline import RAW, RECS_URL, _get
    from .systems import FT2

    cols = ["TYPEHUQ", "YEARMADERANGE", "H2OAPT", "FUELH2O", "EQUIPM", "HEATAPT", "FUELHEAT", "BEDROOMS", "IECC_climate_code",
            "NHSLDMEM", "TOTSQFT_EN", "HDD65", "KWHWTH", "BTUNGWTH", "KWHSPH", "BTUNGSPH", "NWEIGHT", *[f"NWEIGHT{i}" for i in range(1, 61)]]
    d = pd.read_csv(_get(RECS_URL, RAW / "recs" / "recs2020_public_v7.csv"), usecols=cols)
    a = d[d.TYPEHUQ == 5]

    def ratio(g, num, den):
        def r(wcol):
            return float((g[wcol] * g[num]).sum() / (g[wcol] * g[den]).sum())
        est = r("NWEIGHT")
        reps = np.array([r(f"NWEIGHT{i}") for i in range(1, 61)])
        return {"recs": est, "se": float(np.sqrt(59 / 60 * ((reps - est) ** 2).sum())), "records": int(len(g))}

    cold = a.IECC_climate_code.isin(["4A", "5A"]) & (a.YEARMADERANGE >= 7)
    a = a.assign(SQFT_HDD=a.TOTSQFT_EN * a.HDD65)
    occ = p["baseline.energy.occupants"]
    t_f = wx["t"].reshape(wx["days"], 24).mean(1) * 1.8 + 32
    hdd = float(np.clip(65 - t_f, 0, None).sum()) / wx["years"]
    ft2 = sum(f["floor_m2"] for f in apt["flats"]) / FT2
    heat = sp["usual"]["building"]["heat_kwh"] * 1000 / (ft2 * hdd)  # Wh of heat per ft2 per degree day
    ck = "baseline.check."

    def heat_of(g, col, per_wh):
        r = ratio(g, col, "SQFT_HDD")
        return {"recs": r["recs"] * per_wh, "se": r["se"] * per_wh, "records": r["records"]}

    out = {
        "own electric water heater, kWh per occupant": (hw["electric_kwh"] / occ,
                                                        ratio(a[(a.H2OAPT == 0) & (a.FUELH2O == 5) & (a.BEDROOMS == 2)], "KWHWTH", "NHSLDMEM")),
        "own gas water heater, kBtu per occupant": (hw["own_gas_kwh"] * BTU_KWH / 1000 / occ,
                                                    ratio(a[(a.H2OAPT == 0) & (a.FUELH2O == 1)], "BTUNGWTH", "NHSLDMEM")),
        "space heat, Wh per ft2 per degree day, against heat-pump flats (4A/5A, built 2000+)": (
            heat, heat_of(a[cold & a.EQUIPM.isin([4, 13]) & (a.HEATAPT == 0)], "KWHSPH", 1000 * p[ck + "recs_stock_hp_cop"])),
        "space heat, Wh per ft2 per degree day, against gas-furnace flats (4A/5A, built 2000+)": (
            heat, heat_of(a[cold & (a.EQUIPM == 3) & (a.FUELHEAT == 1) & (a.HEATAPT == 0)], "BTUNGSPH",
                          1000 / BTU_KWH * 1000 * p[ck + "recs_stock_afue"])),
    }
    return {"cases": {k: {"model": m, **r} for k, (m, r) in out.items()}, "hdd65": hdd}


def checks(r: dict, p: dict) -> list[tuple[str, bool, str]]:
    e = "baseline.energy."
    f = p["baseline.check.recs_energy_factor"]
    pc, sp = r["plant_check"], r["space"]
    res = [
        ("the hourly model at the design hour, no sun and no gains, reproduces each flat's design heat (`loads.room_heat`)",
         r["design_hour_w"] < 1e-6, f"worst {r['design_hour_w']:.2e} W"),
        ("its preheater's year reproduces hvac.preheat_energy's (the largest flat's airflow)",
         abs(r["preheat"]["ours"] - r["preheat"]["hvac"]) <= 0.01 * r["preheat"]["hvac"],
         f"{r['preheat']['ours']:.1f} kWh against {r['preheat']['hvac']:.1f}"),
        ("the plant on step 4's design day reproduces its HP-1 electricity and its swing element's heat",
         abs(pc["hp_kwh"] - pc["want_hp_kwh"]) <= 1e-6 * pc["want_hp_kwh"] and abs(pc["element_kbtu"] - pc["want_element_kbtu"]) <= 1e-6 * pc["want_element_kbtu"],
         f"HP-1 {pc['hp_kwh']:.3f} kWh against {pc['want_hp_kwh']:.3f}; element {pc['element_kbtu']:.2f} kBtu against {pc['want_element_kbtu']:.2f}"),
        ("Fujitsu's table at full capacity, weighted by the usual flats' year, is under the seasonal COP taken (HSPF2's)",
         sp["usual"]["table_cop"] <= p[e + "hp_scop"], f"{sp['usual']['table_cop']:.2f} against {p[e + 'hp_scop']:.2f}"),
        ("the plant's primary covers no more of the loops' loss a year than Ecotope's ~50 W an apartment (the swing element the rest)",
         r["primary_tm_w"] <= p["baseline.check.ecotope_primary_tm_w"],
         f"{r['primary_tm_w']:.0f} W a flat of {(r['hot_water']['loop_w'] + r['hot_water']['swing_tank_w']) / r['flats']:.0f}"),
    ]
    for k, v in r["recs"]["cases"].items():
        res.append((f"RECS 2020, apartments in 5+ unit buildings: {k}, within a factor of {f:g}",
                    1 / f <= v["model"] / v["recs"] <= f,
                    f"model {v['model']:,.2f} against RECS {v['recs']:,.2f} (+-{v['se']:,.2f}, {v['records']} records)"))
    return res


def run(r10: dict, pr: dict, apt: dict, p: dict) -> dict:
    """10c on 10a's run (`baseline.run`) and 10b's (`pricing.run`): every walk-up's energy and its
    running cost a year; written to `out/pass3/energy.json` and `.md`."""
    from .hvac import preheat_energy
    from .loads import ventilation

    s7 = r10["s7"]
    wx = year_hours(p)
    sp = space(apt, p, wx)
    hw = hot_water(apt, p, s7)
    rows = ledger(apt, p, s7, sp, hw)
    n = len(apt["flats"])
    dem = house_demand(apt, p, s7, hw)
    c = costs(rows, p, n, dem)
    big = max(ventilation(apt, p).items(), key=lambda kv: kv[1]["design_cfm"])[0]
    out = {"space": sp, "hot_water": hw, "ledger": rows, "costs": c, "demand": dem, "tie_usd_mwh": tie_price(c), "flats": n,
           "design_hour_w": design_hour_check(apt, p), "plant_check": plant_design_check(p, s7),
           "preheat": {"ours": sp["engineered"]["flats"][big]["pre_kwh"], "hvac": preheat_energy(apt, p)["kwh_year"]},
           "recs": recs_cases(apt, p, sp, hw, wx), "years": wx["years"],
           "primary_tm_w": ((hw["loop_w"] + hw["swing_tank_w"]) * HW_HOURS / 1000 - hw["plant"]["element_kwh"]) * 1000 / HW_HOURS / n}
    nw, b = pr["network"], "pass3.block."
    dc_mwh = c["engineered"]["meters"]["heat"] / 1000 / n
    out["network"] = {k: {"upkeep_usd": p[b + "om_share"] * v["flat"],
                          "pumping_usd": p[b + "pump_share"] * dc_mwh * p["cost.energy.elec_usd_mwh"]} for k, v in nw.items()}
    out["split"] = {k: sp[k]["building"]["heat_kwh"] / n for k in sp}
    out["checks"] = checks(out, p)
    path = OUT_DIR / "pass3"
    keep = {k: out[k] for k in ("ledger", "costs", "demand", "tie_usd_mwh", "network", "split", "recs", "checks", "plant_check", "preheat")}
    keep["space"] = {k: {kk: vv for kk, vv in v.items() if kk != "parts"} for k, v in sp.items()}
    keep["hot_water"] = {k: v for k, v in hw.items() if k != "months"}
    (path / "energy.json").write_text(json.dumps(keep, indent=1, default=float) + NL, encoding="utf-8")
    (path / "energy.md").write_text(report(out, p) + NL, encoding="utf-8")
    out["written"] = [path / "energy.json", path / "energy.md"]
    return out


USES = ("space heat", "cooling", "hot water", "ventilation", "controls", "the house's own", "pv")


def report(r: dict, p: dict) -> str:
    from .systems import report as fmt

    n, c, sp, hw = r["flats"], r["costs"], r["space"], r["hot_water"]
    lines = ["Pass 3g step 10c: each walk-up's energy and running cost a year", "", fmt(r["checks"]), "",
             f"Weather: ERA5 at the site, {r['years']:.1f} years (2005-2023), as recorded; {r['recs']['hdd65']:,.0f} heating degree days (65 F) a year.",
             "", "A flat's space heat a year (kWh of heat delivered; the four facings averaged):"]
    for k, v in sp.items():
        lines.append(f"  {k}: {v['building']['heat_kwh'] / n:,.0f} (cooling removed {v['building']['cool_kwh'] / n:,.0f})")
    s = r["split"]
    code = s["engineered at the code's leakage"]
    lines.append(f"  the saving over the usual flats' {s['usual']:,.0f}: the ERV's {s['usual'] - code:,.0f}, "
                 f"the airtightness's {code - s['engineered']:,.0f}")
    lines += ["", f"Hot water: {hw['gpd']:.1f} gal a day a flat at the tap ({hw['gpd_min']:.1f}-{hw['gpd_max']:.1f} through the year; "
                  f"FSEC, {p['baseline.energy.occupants']:g} people), {hw['flat_kwh']:,.0f} kWh of heat a flat a year; the loops lose {hw['loop_w']:,.0f} W.",
              f"  The engineered plant a year: HP-1 {hw['plant']['hp_kwh']:,.0f} kWh, the swing element {hw['plant']['element_kwh']:,.0f}, "
              f"the data center's heat {hw['plant']['dc_kwh']:,.0f}; tanks' loss {hw['primary_tanks_w'] + hw['swing_tank_w']:.0f} W."]
    lines += ["", "A flat's energy a year by end use (kWh; gas as kWh of gas; heat from the data center apart):",
              f"{'':34s} " + " ".join(f"{w:>11s}" for w in WALKUPS)]
    for use in USES:
        for meter in ("flats", "house", "pv", "gas flats", "gas house", "heat"):
            vals = [sum(x["kwh"] for x in r["ledger"] if x["walkup"] == w and x["use"] == use and x["meter"] == meter) / n for w in WALKUPS]
            if any(abs(v) > 1e-9 for v in vals):
                lines.append(f"{use + ', ' + meter:34s} " + " ".join(f"{v:11,.0f}" for v in vals))
    lines += ["", "A flat's running cost a year (USD 2026):", f"{'':30s} " + " ".join(f"{w:>11s}" for w in WALKUPS)]
    for k in c["engineered"]["usd"]:
        lines.append(f"{k:30s} " + " ".join(f"{c[w]['usd'][k] / n:11,.0f}" for w in WALKUPS))
    lines.append(f"{'total':30s} " + " ".join(f"{c[w]['total'] / n:11,.0f}" for w in WALKUPS))
    lines.append(f"{'the house meter on':30s} " + " ".join(f"{c[w]['house_class']:>11s}" for w in WALKUPS))
    e = c["engineered"]
    if e["house_class"] == "GS-Medium":
        d = r["demand"]["engineered"]
        lines.append(f"  the engineered house meter's demand: {d['normal_kw']:.1f} kW a normal month, {d['fallback_kw']:.1f} with BK-1; "
                     f"{e['billing_kw_months']:.0f} kW-months billed a year")
    lines += ["", "The data center's heat price at which the engineered design's running cost meets each usual walk-up's (USD/MWh):"]
    lines += [f"  {w}: {v:,.0f}" for w, v in r["tie_usd_mwh"].items()]
    lines += ["", "Beside the building: the heat network's running cost, a flat a year (pass 3's block model, its upkeep and pumping):"]
    lines += [f"  {k}: upkeep ${v['upkeep_usd']:,.0f}, pumping ${v['pumping_usd']:,.0f}" for k, v in r["network"].items()]
    lines += ["", "The walk-ups: " + "; ".join(f"{w}, {NAMES[w]}" for w in WALKUPS)]
    return NL.join(lines)
