"""Pass 3g step 10d (D28): noise and comfort, each walk-up side by side (`brownfield baseline`).

Only what a maker publishes, a study measured, a standard sets, or the model computes from them;
no scores and no weights. The four walk-ups (10a) share the envelope, the layout and the people.

- **Noise:**
  - a neighbour's flush through a drain stack (CMHC's measurements, `plumbing.noise`): cast iron
    in the engineered design, PVC in the usual walk-ups;
  - the supply pipes (Warnock and Morin's relative levels): sleeved, behind the engineered
    design's reducing valve; clamped rigidly at the street's pressure in the usual walk-ups;
  - the fan that runs all year in each flat: the ERV, or the bath fan;
  - the heat pumps' indoor and outdoor units, and the gas walk-up's furnace and air conditioner:
    their makers' levels, and the hours a year each runs, from 10c's hourly model (`hours`);
  - the plant: what its makers publish, and whether a flat's room shares its walls.
- **Comfort:**
  - outdoor air to each bedroom: the ERV's ducted supply, or what leaks in through the bedroom's
    own walls under the bath fan (leakage by exterior area, as `loads.room_ua` spreads it), less
    with the door closed (WSU's field study, `comfort.door_closed_drop`);
  - the air that heats in winter: none in the engineered flats (the floors heat, and the ERV
    supplies at PHI's 16.5 C), the mini-split's or the furnace's warm air in the usual ones;
  - the floors' surfaces at the design hour, against ASHRAE 55;
  - the hot water's wait at each fixture: the water in its pipe (C404.5's table) over its flow
    (the federal most, so the least wait).
"""

from __future__ import annotations

import json
import math

import numpy as np

from . import OUT_DIR
from .baseline import NAMES, USUAL, WALKUPS
from .energy import BTU_KWH, FACINGS, NL
from .loads import CFM_M3H, RHO_CP_AIR

C = "baseline.comfort."
FIXTURES = ("lav", "sink", "tub", "dishwasher", "washer")
FLOW = {"lav": "lav_gpm", "sink": "sink_gpm", "tub": "shower_gpm"}  # the fixtures someone stands at, waiting
OZ_GAL = 128.0
YEAR_H = 8766.0


def pressure_db(psi: float) -> float:
    """Warnock and Morin's (NRC, 1990) correction of a supply pipe's noise for its pressure (dB)."""
    return (psi - 70.0) / 12.0


def lp_1m(lw_dba: float) -> float:
    """A source's sound pressure 1 m away over a hard surface (dBA), from its sound power: half a
    sphere's spreading, Lp = Lw - 10 lg(2 pi r2). A far-field rule, so rough this close."""
    return lw_dba - 10.0 * math.log10(2.0 * math.pi)


def wait_s(oz: float, gpm: float) -> float:
    """The seconds a fixture runs before its pipe's water is through, at its flow."""
    return oz / OZ_GAL / gpm * 60.0


# ---- noise ----

def pipes(apt: dict, p: dict) -> dict:
    """The drains (CMHC's dBA, a neighbour's flush through a stack enclosed in drywall) and the
    supply pipes (Warnock and Morin's relative dB), each walk-up's: at the street's pressure and at
    the code's most without a reducing valve. The engineered design's valve holds its pipes at
    `plumbing.max_static_psi` when the street gives more."""
    from .plumbing import noise

    nz, n = noise(apt, p), "systems.noise."
    valve = p["systems.plumbing.max_static_psi"]

    def supply(psi: float) -> dict:
        return {"engineered": p[n + "supply_plastic_sleeved_db"] + pressure_db(min(psi, valve)),
                **{w: p[n + "supply_plastic_rigid_db"] + pressure_db(psi) for w in USUAL}}

    street, most = p["systems.plumbing.street_psi"], p[n + "usual_pressure_psi"]
    return {"limit_dba": nz["limit_dba"], "wet_walls_only": nz["wet_walls_only"],
            "drain_dba": {"engineered": nz["drain_dba"]["cast_iron"], **{w: nz["drain_dba"]["pvc"] for w in USUAL}},
            "street_psi": street, "most_psi": most, "supply_db": supply(street), "supply_db_most": supply(most)}


def hours(apt: dict, p: dict) -> dict:
    """A flat's hours a year needing heat and needing cooling, each hour alone (10c's model, the
    four facings and the flats averaged): the engineered flats and the usual ones. Cooling only on
    days that need no heat on balance, as 10c counts it, and only in hours that don't need heat
    (`both_h`: the hours 10c's cooling leaves the slab edge out of, so that they need both; counted
    as heating). Each hour alone, so an upper bound on a unit's running hours: a day's mass
    carries some of them (`energy.mass`)."""
    from .energy import cases, flat_parts, flat_series, year_hours

    wx = year_hours(p)
    out = {}
    for key, (case, erv) in cases(apt, p).items():
        if key not in ("engineered", "usual"):
            continue
        parts = flat_parts(apt, p, case)
        heat = cool = both = 0.0
        for az in FACINGS:
            for part in parts.values():
                loss, gain, _ = flat_series(part, wx, p, az, erv)
                L, G = np.asarray(loss).reshape(wx["days"], 24), np.asarray(gain).reshape(wx["days"], 24)
                h, c = L > 0, (G > 0) & (L.sum(1) <= 0)[:, None]
                heat, cool, both = heat + float(h.sum()), cool + float((c & ~h).sum()), both + float((h & c).sum())
        k = wx["years"] * len(FACINGS) * len(parts)
        out[key] = {"heat_h": heat / k, "cool_h": cool / k, "both_h": both / k}
    return out


def machines(p: dict, hrs: dict, en: dict) -> dict:
    """The machines that run in a flat or on the roof for it, each walk-up's: what each is, its
    makers' level (None where none is published) and its hours a year. Inverter heat pumps run
    whenever their flat needs them (`hours`); the gas walk-up's single-stage furnace and air
    conditioner run their output's share of the year (10c's heat and cooling over their capacity).
    The engineered flats' mini-splits heat only in the fallback (`energy.fallback_h`, a placeholder),
    so their hours there are at most that."""
    e, n = "baseline.energy.", en["flats"]
    eng, usual = hrs["engineered"], hrs["usual"]
    fb = p[e + "fallback_h"]
    b = en["space"]["usual"]["building"]
    furnace_h = b["heat_kwh"] / n / (p[e + "furnace_out_btuh"] / BTU_KWH)
    ac_h = b["cool_kwh"] / n / (p[C + "ac_btuh"] / BTU_KWH)
    indoor = (p[C + "ms_indoor_dba_quiet"], p[C + "ms_indoor_dba_high"])
    outdoor = (p[C + "ms_outdoor_cool_dba"], p[C + "ms_outdoor_heat_dba"])
    erv = {"what": "the ERV (Broan EDGE BLP120E80NS-HW), in the utility closet's ceiling, ducted to the bedrooms, kitchen and bath",
           "sone": None, "hours": YEAR_H}
    fan = {"what": "the bath fan (Panasonic FV-0511VQ1) at 50 cfm", "sone": p[C + "bath_fan_sone"], "hours": YEAR_H}

    def ms(heat_h: float, cool_h: float, why: str) -> dict:
        return {"indoor": {"what": "the mini-split's ducted indoor unit (Fujitsu ARUH12KUAS)", "dba": indoor,
                           "heat_h": heat_h, "cool_h": cool_h, "why": why},
                "outdoor": {"what": "its outdoor unit on the roof (Fujitsu AOUH12KUBS1), at 1 m", "dba": outdoor,
                            "heat_h": heat_h, "cool_h": cool_h}}

    out = {"engineered": {"fan": erv, **ms(min(fb, eng["heat_h"]), eng["cool_h"], "cooling; heating only in the fallback")},
           "gas": {"fan": fan,
                   "indoor": {"what": "the gas furnace's blower (Goodman GR9S960403AN), heating and cooling", "dba": None,
                              "heat_h": furnace_h, "cool_h": ac_h, "why": "single-stage: its output's share of the year"},
                   "outdoor": {"what": "the air conditioner's outdoor unit (Goodman GLXS4BA1810A), at 1 m",
                               "dba": (lp_1m(p[C + "ac_lw_dba"]),) * 2, "lw_dba": p[C + "ac_lw_dba"], "heat_h": 0.0, "cool_h": ac_h}}}
    for w in ("electric", "central"):
        out[w] = {"fan": fan, **ms(usual["heat_h"], usual["cool_h"], "heating and cooling")}
    return {w: out[w] for w in WALKUPS}


def plant_room(apt: dict) -> dict:
    """The rooms of the flats that share a wall with the annex's mechanical room (HP-1, the tanks,
    P-1 and P-2; the central walk-up's gas heater): faces no more than a wall's thickness apart,
    overlapping along the wall and in height. And the nearest flat room's distance."""
    rooms = apt["rooms"]["rooms"]
    mech = next(r for r in rooms if r["use"] == "mechanical")
    wall = max(apt["ext_t_m"], apt["party_t_m"]) + 0.05
    shared, near = [], []
    for r in rooms:
        if r["id"].split("/")[0] == mech["id"].split("/")[0]:
            continue
        gap = [max(mech["lo_m"][i] - r["hi_m"][i], r["lo_m"][i] - mech["hi_m"][i]) for i in range(3)]  # > 0 apart, < 0 overlapping
        for i, j in ((0, 1), (1, 0)):
            if 0.0 <= gap[i] <= wall and gap[j] < 0 and gap[2] < 0:
                shared.append({"room": r["id"], "shared_m": min(mech["hi_m"][j], r["hi_m"][j]) - max(mech["lo_m"][j], r["lo_m"][j])})
        near.append((math.hypot(*(max(g, 0.0) for g in gap)), r["id"]))
    d, nearest = min(near)
    return {"room": mech["id"], "shared": shared, "nearest": nearest, "nearest_m": d}


# ---- comfort ----

def bedrooms(apt: dict, p: dict) -> dict:
    """Each bedroom's outdoor air (cfm), the annual average:
    - **engineered:** the ERV's ducted supply (`loads.ventilation`), plus its share of the flat's
      natural leakage at Phius's tightness;
    - **usual:** none by duct. The bath fan's air and the leakage (`baseline.usual_case`, LBNL's
      sub-additivity) all come in through the envelope, spread by each room's exterior area as
      `loads.room_ua` spreads leakage; with the door closed, `door_closed_drop` less (WSU's median)."""
    from .baseline import usual_case
    from .loads import design_case, room_envelopes, ventilation

    eng, usual, vent = design_case(apt, p, preheat=True), usual_case(apt, p), ventilation(apt, p)
    bed1, drop = p["systems.design.bed_1_occupants"], p[C + "door_closed_drop"]
    out = {}
    for name, rows in room_envelopes(apt).items():
        ext = {x["room"]["id"]: x["wall_gross_m2"] + x["ceiling_m2"] for x in rows}
        tot = sum(ext.values())
        u, e = usual["flats"][name], eng["flats"][name]
        q_usual = (u["infil_m3h"] + u["vent_m3h"]) / CFM_M3H
        for x in rows:
            rid = x["room"]["id"]
            if x["room"]["use"] != "bedroom":
                continue
            share = ext[rid] / tot
            duct = vent[name]["supply"].get(rid, 0.0)
            out[rid] = {"occupants": bed1 if rid.endswith("/bed-1") else 1.0, "share": share, "duct_cfm": duct,
                        "engineered_cfm": duct + e["infil_m3h"] / CFM_M3H * share,
                        "usual_open_cfm": q_usual * share, "usual_closed_cfm": q_usual * share * (1 - drop), "flat_usual_cfm": q_usual}
    return out


def warm_air(p: dict, r10: dict) -> dict:
    """The air that heats a flat at the design hour: the usual flats' mini-splits carrying each
    flat's design heat (10a, `baseline.heat_check`) at their Quiet and High airflows; the gas
    furnace at its rated temperature rise over RECS's set point; the engineered flats' ERV supply
    (they heat by their floors); and the outdoor air as it leaks in."""
    t_in = p["pass3.loads.indoor_c"]
    ms = {}
    for n, v in r10["heat"]["flats"].items():
        ms[n] = {s: t_in + v["load_w"] / (p[C + f"ms_cfm_{s}"] * CFM_M3H * RHO_CP_AIR) for s in ("quiet", "high")}
    t_set = (p["baseline.energy.heat_set_f"] - 32) / 1.8
    furnace = tuple(t_set + p[C + f"furnace_rise_{k}_f"] / 1.8 for k in ("min", "max"))
    erv = min(f["erv"]["supply_c"] for f in r10["s7"]["loop"]["flats"].values())
    return {"minisplit": ms, "minisplit_range": (min(v["high"] for v in ms.values()), max(v["quiet"] for v in ms.values())),
            "furnace": furnace, "erv_c": erv, "outdoor_c": p["systems.design.heating_c"], "room_c": t_in}


def floors(p: dict, r10: dict) -> dict:
    """The engineered flats' heated floors at the design hour (`hvac.radiant` on the routes, step 7)
    against ASHRAE 55's range. The usual flats' floors aren't heated."""
    rooms = [x for f in r10["s7"]["loop"]["flats"].values() for x in f["rooms"]]
    lo, hi = min(rooms, key=lambda x: x["surface_c"]), max(rooms, key=lambda x: x["surface_c"])
    return {"rooms": len(rooms), "min_c": lo["surface_c"], "min_room": lo["id"], "max_c": hi["surface_c"], "max_room": hi["id"],
            "limits_c": (p[C + "ashrae55_floor_min_c"], p[C + "ashrae55_floor_max_c"])}


def waits(p: dict, r10: dict) -> dict:
    """Each hot fixture's pipe (fl oz, IECC Table C404.5.2.1's PEX) and, where someone waits at it,
    the seconds at its flow: the worst flat's and the mean. The engineered flats' (and the central
    walk-up's, the same loops) from each flat's loop (step 9, on the routes; the lavatory is the
    loop's end); a flat's own heater's from 10a's rule (`baseline.flat_hot_rule`)."""
    from .loads import hunter_gpm
    from .plumbing import FIXTURE_HOT_WSFU, _fps, tube_oz_ft

    u = "baseline.usual."
    t_oz, d_oz = tube_oz_ft(p[u + "trunk_in"]), tube_oz_ft(p[u + "drop_in"])
    own_fps = {x: _fps(hunter_gpm(p["systems.plumbing." + k]), p[u + "drop_in"]) for x, k in FIXTURE_HOT_WSFU.items()}
    own = {n: {k: v["trunk_ft"] * t_oz + v["drop_ft"] * d_oz for k, v in f["fixtures"].items()} for n, f in r10["rule"].items()}
    loop = {n: {"lav": 0.0, **d} for n, d in r10["s7"]["water"]["c404"]["by_flat"].items()}
    by = {"engineered": loop, "electric": own, "gas": own, "central": loop}
    out = {}
    for w, d in by.items():
        out[w] = {}
        for x in FIXTURES:
            vals = [f[x] for f in d.values() if x in f]
            row = {"worst_oz": max(vals), "mean_oz": sum(vals) / len(vals)}
            if x in FLOW:
                gpm = p[C + FLOW[x]]
                row.update(gpm=gpm, worst_s=wait_s(row["worst_oz"], gpm), mean_s=wait_s(row["mean_oz"], gpm))
            out[w][x] = row
    return {"by_walkup": out, "own": own, "loop": loop, "limit_oz": p["systems.hot_water.c404_volume_oz"], "own_fps": own_fps}


# ---- checks, the run, the report ----

def checks(r: dict, p: dict, r10: dict, en: dict) -> list[tuple[str, bool, str]]:
    res = []
    add = lambda label, ok, detail: res.append((label, bool(ok), detail))  # noqa: E731
    five = pressure_db(100) - pressure_db(40)
    add("Warnock and Morin's pressure term gives their 5 dB from 40 to 100 psi", abs(five - 5.0) < 1e-9, f"{five:.2f} dB")
    worst = max(v for f in r["waits"]["loop"].values() for v in f.values())
    c404 = r10["s7"]["water"]["c404"]["worst"]["oz"]
    add("the engineered flats' worst hot fixture is step 9's under C404.5", abs(worst - c404) < 1e-9, f"{worst:.1f} fl oz")
    rule = r10["rule"]
    off = max(abs(max(v["trunk_ft"] + v["drop_ft"] for v in f["fixtures"].values()) - f["longest_ft"]) for f in rule.values())
    add("each usual flat's farthest fixture is 10a's IPC 607.2 path", off < 1e-9, f"{max(f['longest_ft'] for f in rule.values()):.1f} ft at most")
    beds = r["bedrooms"]
    per = min(v["duct_cfm"] / v["occupants"] for v in beds.values())
    add("every engineered bedroom gets Phius's 15 cfm a person by duct", per >= p["systems.phius.supply_cfm_per_person"] - 1e-9,
        f"{len(beds)} bedrooms, {per:.1f} cfm a person at least")
    f, (lo, hi) = r["floors"], r["floors"]["limits_c"]
    add("every heated floor within ASHRAE 55's range at the design hour", lo <= f["min_c"] and f["max_c"] <= hi,
        f"{f['min_c']:.1f}-{f['max_c']:.1f} C against {lo:g}-{hi:g}")
    add("the ERV's supply at the design hour at least PHI's 16.5 C", r["warm_air"]["erv_c"] >= p["systems.erv.supply_min_c"] - 1e-9,
        f"{r['warm_air']['erv_c']:.1f} C")
    pr = r["plant_room"]
    add("no flat's room shares a wall with the plant room", not pr["shared"],
        f"the nearest, {pr['nearest']}, {pr['nearest_m']:.2f} m away" + (f"; shared: {pr['shared']}" if pr["shared"] else ""))
    h = r["hours"]
    ok = all(v["heat_h"] + v["cool_h"] <= YEAR_H for v in h.values())
    add("a flat's hours heating and cooling fit in the year", ok,
        "; ".join(f"{k} {v['heat_h']:,.0f} h heating, {v['cool_h']:,.0f} cooling" for k, v in h.items()))
    m, e = r["machines"]["gas"]["indoor"], "baseline.energy."
    blower = m["heat_h"] * p[e + "furnace_fan_w"] / 1000
    ledger = sum(x["kwh"] for x in en["ledger"] if x["walkup"] == "gas" and x["use"] == "space heat" and x["meter"] == "flats") / en["flats"]
    add("the furnace's hours give 10c's blower energy", abs(blower - ledger) < 1e-6, f"{m['heat_h']:,.0f} h, {blower:.1f} kWh a flat")
    return res


def run(r10: dict, en: dict, apt: dict, p: dict) -> dict:
    """10d on 10a's run (`baseline.run`) and 10c's (`energy.run`): noise and comfort, each walk-up
    side by side; written to `out/pass3/comfort.json` and `.md`."""
    hrs = hours(apt, p)
    out = {"pipes": pipes(apt, p), "hours": hrs, "machines": machines(p, hrs, en), "plant_room": plant_room(apt),
           "bedrooms": bedrooms(apt, p), "warm_air": warm_air(p, r10), "floors": floors(p, r10), "waits": waits(p, r10)}
    out["checks"] = checks(out, p, r10, en)
    path = OUT_DIR / "pass3"
    keep = {k: v for k, v in out.items() if k != "waits"}
    keep["waits"] = out["waits"]["by_walkup"]
    (path / "comfort.json").write_text(json.dumps(keep, indent=1, default=float) + NL, encoding="utf-8")
    (path / "comfort.md").write_text(report(out, p) + NL, encoding="utf-8")
    out["written"] = [path / "comfort.json", path / "comfort.md"]
    return out


def _row(label: str, vals) -> str:
    return f"{label:44s} " + " ".join(f"{v:>12s}" for v in vals)


def report(r: dict, p: dict) -> str:
    from .systems import report as fmt

    pi, m, b, wa, fl, wt = r["pipes"], r["machines"], r["bedrooms"], r["warm_air"], r["floors"], r["waits"]["by_walkup"]
    head = _row("", WALKUPS)
    lines = ["Pass 3g step 10d: noise and comfort, each walk-up side by side", "", fmt(r["checks"]), "", "Noise:", head,
             _row("a neighbour's flush through a stack, dBA", [f"{pi['drain_dba'][w]:g}" for w in WALKUPS]),
             f"  CMHC's limit for a neighbour's plumbing {pi['limit_dba']:g} dBA; cast iron in the engineered design, PVC in the usual",
             _row(f"supply pipes, dB (relative), {pi['street_psi']:g} psi street", [f"{pi['supply_db'][w]:.1f}" for w in WALKUPS]),
             _row(f"  at the code's most without a valve, {pi['most_psi']:g} psi", [f"{pi['supply_db_most'][w]:.1f}" for w in WALKUPS]),
             _row("the fan running all year in a flat, sone", ["not published" if m[w]["fan"]["sone"] is None else f"{m[w]['fan']['sone']:g}"
                                                               for w in WALKUPS])]
    for part, label in (("indoor", "indoor unit or blower"), ("outdoor", "outdoor unit")):
        lines.append(_row(f"{label}, dBA", ["not published" if m[w][part]["dba"] is None else
                                            "-".join(f"{x:.0f}" for x in sorted(set(m[w][part]["dba"]))) for w in WALKUPS]))
        lines.append(_row("  hours a year heating", [f"{m[w][part]['heat_h']:,.0f}" for w in WALKUPS]))
        lines.append(_row("  hours a year cooling", [f"{m[w][part]['cool_h']:,.0f}" for w in WALKUPS]))
    g = m["gas"]["outdoor"]
    lines += [f"  the gas walk-up's air conditioner: Goodman's {g['lw_dba']:g} dBA is sound power; {g['dba'][0]:.0f} at 1 m by half a sphere's spreading (rough)",
              f"  the engineered flats' mini-splits heat only in the fallback, at most {p['baseline.energy.fallback_h']:g} h a year (a placeholder)",
              "  the heat pumps' hours each hour alone, so at most; the cooling hours with the windows shut all year, as 10c has them"]
    pr = r["plant_room"]
    lines += [f"The plant ({pr['room']}): HP-1's maker publishes no sound level; the circulators under {p[C + 'circulator_dba']:g} dBA. "
              f"Flat rooms sharing its walls: {len(pr['shared'])}; the nearest, {pr['nearest']}, {pr['nearest_m']:.2f} m away."]
    lines += ["", "Comfort:", "Outdoor air to each bedroom, cfm a person (the year's average; min-max over the bedrooms):"]
    per = lambda k: [v[k] / v["occupants"] for v in b.values()]  # noqa: E731
    lines += [f"  engineered, by duct and at 16.5 C or more: {min(per('engineered_cfm')):.1f}-{max(per('engineered_cfm')):.1f} "
              f"(the duct alone {min(per('duct_cfm')):.1f}-{max(per('duct_cfm')):.1f})",
              f"  usual, through the bedroom's own walls at the outdoor temperature: {min(per('usual_open_cfm')):.1f}-{max(per('usual_open_cfm')):.1f} "
              f"door open, {min(per('usual_closed_cfm')):.1f}-{max(per('usual_closed_cfm')):.1f} door closed",
              f"  (a usual flat's whole outdoor air {min(v['flat_usual_cfm'] for v in b.values()):.1f} cfm; Phius asks "
              f"{p['systems.phius.supply_cfm_per_person']:g} a person, to every bedroom)"]
    lo, hi = wa["minisplit_range"]
    lines += ["", f"The air that heats, at the design hour ({wa['outdoor_c']:g} C outdoors, {wa['room_c']:g} C in):",
              f"  engineered: none (the floors heat); the ERV's supply {wa['erv_c']:.1f} C",
              f"  electric and central: the mini-split's {lo:.0f}-{hi:.0f} C from the ceiling's ducts (High to Quiet fan, each flat's design heat)",
              f"  gas: the furnace's {wa['furnace'][0]:.0f}-{wa['furnace'][1]:.0f} C (its rated rise over {p['baseline.energy.heat_set_f']:g} F)",
              f"  the usual flats' outdoor air comes in through the envelope at {wa['outdoor_c']:g} C"]
    lines += ["", f"Floors at the design hour: the engineered flats' {fl['rooms']} heated rooms {fl['min_c']:.1f}-{fl['max_c']:.1f} C "
                  f"against ASHRAE 55's {fl['limits_c'][0]:g}-{fl['limits_c'][1]:g}; the usual flats' floors aren't heated."]
    lines += ["", "The hot water's wait, the worst flat's (fl oz; seconds at the federal most flow):", head]
    for x in FIXTURES:
        lines.append(_row(f"  {x}", [f"{wt[w][x]['worst_oz']:.0f}" + (f" / {wt[w][x]['worst_s']:.0f} s" if "worst_s" in wt[w][x] else "")
                                     for w in WALKUPS]))
    lines.append("  the mean flat's, seconds: " + "; ".join(f"{w} " + ", ".join(f"{x} {wt[w][x]['mean_s']:.0f}" for x in FLOW) for w in WALKUPS))
    lines += [f"  the engineered design is held to C404.5's {r['waits']['limit_oz']:g} fl oz; its lavatories are on their loops; "
              f"its fixtures' own pipes sized for quiet ({p['systems.plumbing.hot_fps']:g} ft/s), a flat's own heater's drops "
              f"{p['baseline.usual.drop_in']:g} in. (10a's rule), at most {max(r['waits']['own_fps'].values()):.1f} ft/s at a fixture's demand",
              "", "The walk-ups: " + "; ".join(f"{w}, {NAMES[w]}" for w in WALKUPS)]
    return NL.join(lines)
