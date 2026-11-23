"""Pass 3g step 9b (D28): the control sequence.

How the walk-up's services run, written as the sequence of operations a controls contractor builds
from and a commissioning agent tests against (step 9c), each system in its modes:

- **the hot-water plant:** normal, on the data center's heat (HX-1, then HP-1 on the same water),
  and the fallback when that heat is gone (the backup heater BK-1, step 9a);
- **the building loop:** the radiant floors on an outdoor reset off HX-2, and what happens when the
  data center's heat is gone (nothing at the plant: the flats' mini-splits take over);
- **each flat's mini-split:** set to heat a little below the floor's setpoint, so it runs only when
  the floor can't hold the room. Fujitsu's units take no outside mode signal (operation/stop and a
  forced stop only, the latter already the condensate switch's), so the takeover is each flat's
  setpoint, not a wire from the plant; the plant closes the loop's valve and stops its pump;
- **the ERV and its preheater; the fire protection's signals;**
- **the interlocks that are wired, not programmed:** above all BK-1 never with HP-1, which the
  house panel's size rests on (220.60).

Every setpoint is the design's own (`hot_water`, `erv`, `loads`, the designs on the routes) or one
of the sequence's few judgements (`controls`, each to set at commissioning). The plant's heater-
circuit pump, its two data-center valves, the flow switch and the controller are named here as
points; none is selected yet (7a placed none of the plant's wall-hung equipment).
"""

from __future__ import annotations

from .plumbing import SWING_DEADBAND_F


def f_of(c: float) -> float:
    return c * 9 / 5 + 32


def c_of(f: float) -> float:
    return (f - 32) * 5 / 9


def reset_c(p: dict, outdoor_c: float, supply_design_c: float) -> float:
    """The building loop's supply on its outdoor reset: a straight line from the room's temperature
    when it's that warm outdoors to the design supply at the heating design dry bulb, as the
    floor's heat falls with the difference indoors to out (REHAU's weather compensation). A
    starting curve, tuned at commissioning (9c)."""
    t_in, t_d = p["pass3.loads.indoor_c"], p["systems.design.heating_c"]
    return t_in + (supply_design_c - t_in) * max((t_in - outdoor_c) / (t_in - t_d), 0.0)


# The control points: tag, what, and whether the design has chosen it.
POINTS = [
    ("PC-1", "the plant controller (programmable, with an outdoor sensor, analog outputs and alarm notification)", "to select"),
    ("TS-1", "the data center's water entering the annex, its temperature", "to select"),
    ("FS-1", "the data center's water entering the annex, a flow switch", "to select"),
    ("V-1", "the data center's water through HX-1, a modulating valve", "to select"),
    ("P-2", "the heater circuit's pump: ST-1B's bottom (the storage's cold end) through HX-1, HP-1 and BK-1 to ST-1A's top", "to select"),
    ("TS-4", "the storage's aquastat, at Ecosizer's height in it", "with ST-1"),
    ("HP-1", "the water-to-water heat pump, its enable", "ClimateMaster Tranquility SW036 (basis of design)"),
    ("BK-1", "the backup heater's contactor, its own thermostats", "A. O. Smith DRE-52-12 (basis of design)"),
    ("ST-2", "the swing tank's element thermostat", "Bradford White RE340S6 (basis of design)"),
    ("MV-1", "the master mixing valve", "ASSE 1017"),
    ("P-3", "the recirculation pump, switched by PC-1", "Grundfos ALPHA2 15-55SF (basis of design)"),
    ("TS-5", "the hot-water return's temperature, at ST-2", "to select"),
    ("TBV", "each flat's thermostatic balancing valve, under its lavatory in the vanity, where its loop's return starts (self-acting; "
            "IECC C404.6: with access)",
     "Caleffi ThermoSetter 116 series, 1/2 in. (basis of design; Addendum 7)"),
    ("TS-3", "the outdoor air's temperature, shaded, out of the sun and the exhausts", "with PC-1"),
    ("V-2", "the data center's water through HX-2, a modulating valve", "to select"),
    ("P-1", "the building loop's circulator", "Grundfos ALPHA2 15-55F (basis of design)"),
    ("TS-2", "the building loop's supply leaving HX-2, its temperature", "to select"),
]


def aquastat_at(p: dict) -> str:
    """Where TS-4 goes: Ecosizer's aquastat height as a share of the storage's volume from its cold
    end, in the tanks in series (ST-1B the cold end, ST-1A the hot)."""
    n = int(p["systems.routing.tank_count"])
    names = [f"ST-1{c}" for c in "AB"[:n]][::-1]  # from the cold end
    x = p["systems.hot_water.aquastat_fract"] * n
    k = int(x + 1e-9)
    if abs(x - k) < 1e-9 and 0 < k < n:
        return f"where {names[k - 1]}'s top joins {names[k]}'s bottom"
    return f"at {x - k:.0%} of {names[min(k, n - 1)]}'s height"


def sequence(p: dict, s7: dict) -> list[dict]:
    """The sequence, system by system and mode by mode, each step with its figures."""
    h, c = "systems.hot_water.", "systems.controls."
    w, L = s7["water"], s7["loop"]
    t_store, t_out, t_back = p[h + "storage_f"], p[h + "distribution_f"], p[h + "return_min_f"]
    t_stop, t_tbv = p[c + "recirc_stop_f"], p[h + "tbv_set_f"]
    src = p[h + "hp_source_f"]
    t_in = p["pass3.loads.indoor_c"]
    sup = L["supply_c"]
    wwsd = p[c + "wwsd_c"]
    from .loads import preheat_c

    pre = preheat_c(p)
    from .plumbing import storage_held

    held = storage_held(p)
    reset = [(t, reset_c(p, t, sup)) for t in (p["systems.design.heating_c"], -10.0, 0.0, 10.0, wwsd)]
    return [
        {"system": "The hot-water plant (P-601)", "modes": [
            {"mode": "Normal: on the data center's heat", "steps": [
                f"P-2 starts when TS-4, at {p[h + 'aquastat_fract']:.0%} of the storage from its cold end ({aquastat_at(p)}), falls below "
                f"{t_store:g} F, and stops when it reaches {t_store:g} F (Ecosizer's primary aquastat): it runs only with the heating "
                "cycle (IECC C404.6.3).",
                f"With P-2, V-1 opens and modulates the data center's water through HX-1 so it leaves HX-1 at {src:g} F, the heat pump's "
                f"source (ClimateMaster's table goes to {p[h + 'hp_source_max_f']:g} F); HX-1 preheats the circuit to "
                f"{w['heater']['preheat_f']:.1f} F.",
                f"HP-1 runs with P-2 and lifts the circuit to {t_store:g} F into ST-1A's top; the storage's water moves from ST-1B to "
                "ST-1A as hot water is drawn (the tanks in series).",
                "BK-1's elements stay locked out (the interlock below).",
                f"ST-2's element switches on at {t_out:g} F and off at {t_out + SWING_DEADBAND_F:g} F (Ecosizer's swing tank).",
                f"MV-1 sends {t_out:g} F to the flats.",
                f"P-3 runs while TS-5 reads under {t_back:g} F and stops when it reaches {t_stop:g} F: off when the loop is at "
                "temperature (IECC C404.6.1).",
                f"Each flat's TBV, set at {t_tbv:g} F, throttles its flat's return as it nears that, so every flat's loop returns at "
                f"{t_back:g} F or more ({w['loop']['gpm']:.2f} gpm in all, {w['recirc']['flat_gpm']:.2f} a flat, at the design's loss).",
            ]},
            {"mode": "Fallback: the data center's heat gone (step 9a)", "steps": [
                f"Entered when TS-1 reads below {src:g} F, or FS-1 proves no flow, for {p[c + 'fallback_enter_min']:g} min.",
                "V-1 closes; HP-1 stops and is locked out; then BK-1's contactor is released.",
                f"BK-1's own thermostats hold {t_store:g} F at its outlet (set within its {p[h + 'backup_thermostat_min_f']:g}-"
                f"{p[h + 'backup_thermostat_max_f']:g} F range); P-2 runs on TS-4 as in normal, so ST-1's "
                f"{held:g} gal are heated as in normal running (Ecosizer asks {w['primary']['storage_gal']:.0f}).",
                f"Left when TS-1 is back at {src:g} F or more with flow for {p[c + 'fallback_exit_min']:g} min: BK-1 locked out first, "
                "then HP-1 enabled.",
            ]},
            {"mode": "Alarms, from PC-1 to the building's manager", "steps": [
                "the plant in or out of its fallback;",
                f"the storage at TS-4 below {t_out:g} F;",
                f"the hot-water return at TS-5 below {t_back:g} F (WHO: not less than 50 C) after P-3 has run "
                f"{p[c + 'loop_alarm_min']:g} min;",
                "HP-1's or BK-1's fault.",
            ]},
        ]},
        {"system": "The building loop: the radiant floors (M-601)", "modes": [
            {"mode": "Heating season", "steps": [
                f"P-1 runs while TS-3 reads below {wwsd:g} C ({f_of(wwsd):.0f} F) and stops above it.",
                "V-2 modulates the data center's water through HX-2 to hold TS-2 on the outdoor reset: "
                + "; ".join(f"{to:g} C out, {ts:.1f} C supply" for to, ts in reset)
                + f". At the heating design dry bulb it is the design's {sup:.1f} C; a straight line to the room's {t_in:g} C. "
                "A starting curve, tuned at commissioning.",
                "Each room's thermostat opens and closes its loops' actuators on the flat's manifold; each flat's heat meter counts.",
            ]},
            {"mode": "The data center's heat gone", "steps": [
                "While the plant is in its fallback (TS-1 or FS-1, above), V-2 closes and P-1 stops: the data center's water, cold or "
                "still, would only cool the floors. Each flat's mini-split takes the room (below).",
                f"PC-1 alarms when TS-2 stays {p[c + 'loop_alarm_k']:g} K under its reset target for {p[c + 'loop_alarm_min']:g} min.",
            ]},
        ]},
        {"system": "Each flat's mini-split (M-101 to M-103)", "modes": [
            {"mode": "Heating season", "steps": [
                f"Set to heat at {t_in - p[c + 'ms_offset_k']:g} C, {p[c + 'ms_offset_k']:g} K under the floor's {t_in:g} C: idle while the "
                "floor holds the room, it carries the flat when the floor can't (step 9a: at least twice the design heat).",
                "Fujitsu's units take no outside mode signal, so the setting is each flat's: the manager confirms it at the season's "
                "change and when the plant alarms.",
            ]},
            {"mode": "Cooling season", "steps": [f"Cooling at the tenant's setpoint (the design's {p['systems.design.cooling_indoor_f']:g} F)."]},
            {"mode": "Always", "steps": [
                "Its fan runs continuously at low speed while the ERV runs: the ERV's fresh air enters its return.",
                "Its static pressure is set to its ducts by Fujitsu's function setting (M-601).",
                "Its water-level switch stops it (Fujitsu function 46-02, forced stop; IMC 307.2.3).",
            ]},
        ]},
        {"system": "The ERV and its preheater (M-101 to M-103)", "modes": [
            {"mode": "Always", "steps": [
                "The ERV runs continuously at its design flows, supply and exhaust balanced (step 9c tests them).",
                f"The preheater holds the outdoor air leaving it at {pre:.1f} C ({f_of(pre):.1f} F), only with its airflow proved by its "
                "own sensor, and its over-temperature cut-out in the circuit.",
            ]},
        ]},
        {"system": "Fire protection (FP-601)", "modes": [
            {"mode": "Always", "steps": [
                "The waterflow switch: an alarm at the monitoring panel, the exterior horn-strobe, the supervising station.",
                "Each shutoff valve's tamper switch: a supervisory signal.",
            ]},
        ]},
    ]


INTERLOCKS = [
    ("BK-1 never with HP-1", "BK-1's contactor coil is wired through a normally closed contact of HP-1's enable relay: BK-1 can't "
     "energize while HP-1 is enabled. The house panel's size counts only the larger of the two (220.60) and rests on it."),
    ("the preheater with its airflow", "the preheater's own airflow sensor and over-temperature cut-out (Ouellet's) in its circuit."),
    ("each mini-split with its drain", "the water-level switch on Fujitsu's forced-stop input (function 46-02)."),
]


def checks(p: dict, s7: dict) -> list[tuple[str, bool, str]]:
    h, c = "systems.hot_water.", "systems.controls."
    sup, td, t_in = s7["loop"]["supply_c"], p["systems.design.heating_c"], p["pass3.loads.indoor_c"]
    curve = [reset_c(p, t, sup) for t in range(-25, 21)]
    from .loads import preheat_c

    house = s7["electrical"]["service"]["house"]
    hp = next(r for r in house["rows"] if r["key"] == "dhw_heat_pump")
    bk = next(r for r in house["rows"] if r["key"] == "backup_heater")
    return [
        ("the reset gives the design's supply at the heating design dry bulb, and the room's at the room's temperature",
         abs(reset_c(p, td, sup) - sup) < 1e-9 and abs(reset_c(p, t_in, sup) - t_in) < 1e-9, f"{sup:.1f} C at {td:g} C; {t_in:g} C at {t_in:g} C"),
        ("the reset never falls as it gets colder", all(a >= b for a, b in zip(curve, curve[1:])), "from -25 to 20 C"),
        (f"the loop still heats at the warm-weather shutdown ({p[c + 'wwsd_c']:g} C)", reset_c(p, p[c + "wwsd_c"], sup) > t_in,
         f"{reset_c(p, p[c + 'wwsd_c'], sup):.1f} C supply"),
        ("the heat pump's source setpoint within ClimateMaster's table", p[h + "hp_source_f"] <= p[h + "hp_source_max_f"],
         f"{p[h + 'hp_source_f']:g} F, the table to {p[h + 'hp_source_max_f']:g}"),
        ("BK-1's setpoint within its thermostats' range", p[h + "backup_thermostat_min_f"] <= p[h + "storage_f"] <= p[h + "backup_thermostat_max_f"],
         f"{p[h + 'storage_f']:g} F in {p[h + 'backup_thermostat_min_f']:g}-{p[h + 'backup_thermostat_max_f']:g}"),
        ("the swing tank's element switches on at the supply temperature, under the storage's", p[h + "distribution_f"] + SWING_DEADBAND_F < p[h + "storage_f"],
         f"{p[h + 'distribution_f']:g}-{p[h + 'distribution_f'] + SWING_DEADBAND_F:g} F under {p[h + 'storage_f']:g}"),
        ("the preheater's setpoint at least Broan's 0 C", preheat_c(p) >= p["systems.erv.preheat_min_c"], f"{preheat_c(p):.1f} C"),
        ("leaving the fallback takes longer than entering it (no cycling between the heaters)", p[c + "fallback_exit_min"] > p[c + "fallback_enter_min"],
         f"{p[c + 'fallback_enter_min']:g} min in, {p[c + 'fallback_exit_min']:g} out"),
        ("the house panel counts BK-1 and HP-1 as the interlock runs them: the larger, once", hp["counted"] != bk["counted"],
         f"{'BK-1' if bk['counted'] else 'HP-1'} counted"),
        ("the recirculation pump stops with the loop at temperature (IECC C404.6.1): its stop above the least return, under the supply",
         p[h + "return_min_f"] < p[c + "recirc_stop_f"] < p[h + "distribution_f"],
         f"runs under {p[h + 'return_min_f']:g} F, stops at {p[c + 'recirc_stop_f']:g}, the supply {p[h + 'distribution_f']:g}"),
        ("each flat's balancing valve set within its range, at or over the least return and under the supply",
         p[h + "tbv_min_f"] <= p[h + "tbv_set_f"] <= p[h + "tbv_max_f"] and p[h + "return_min_f"] <= p[h + "tbv_set_f"] < p[h + "distribution_f"],
         f"{p[h + 'tbv_set_f']:g} F in {p[h + 'tbv_min_f']:g}-{p[h + 'tbv_max_f']:g}"),
    ]


def markdown(seq: list[dict]) -> str:
    """The sequence as a specification section (for Addendum 7, step 9d)."""
    lines = ["# 23 09 93: Sequence of operations for the walk-up's services", "",
             "Made up, from the brownfield-compute study: not a real project, nothing is out to bid. Setpoints are the design's; "
             "those marked as judgement are set at commissioning.", ""]
    for i, s in enumerate(seq, 1):
        lines += [f"## {i}. {s['system']}", ""]
        for m in s["modes"]:
            lines += [f"**{m['mode']}.**", ""] + [f"- {x}" for x in m["steps"]] + [""]
    lines += [f"## {len(seq) + 1}. Interlocks, wired, not programmed", ""] + [f"- **{a}:** {b}" for a, b in INTERLOCKS] + [""]
    lines += [f"## {len(seq) + 2}. Control points", "", "| Tag | What | Chosen |", "|---|---|---|"]
    lines += [f"| {t} | {w} | {k} |" for t, w, k in POINTS]
    return "\n".join(lines) + "\n"


def run(apt: dict, p: dict) -> dict:
    from . import OUT_DIR, routed

    routes = routed.load(apt, p)
    if routes is None or not routes.fresh:
        raise SystemExit("no fresh routes: `brownfield routes` first")
    s7 = routed.summary(apt, p, routes)
    seq = sequence(p, s7)
    path = OUT_DIR / "pass3" / "sequence.md"
    path.write_text(markdown(seq), encoding="utf-8")
    return {"sequence": seq, "checks": checks(p, s7), "path": path}


def report(r: dict) -> str:
    from .systems import report as checks_report

    to_select = [t for t, _, k in POINTS if k == "to select"]
    return "\n".join(["Pass 3g step 9b: the control sequence", "", checks_report(r["checks"]), "",
                      f"{sum(len(m['steps']) for s in r['sequence'] for m in s['modes'])} steps in {len(r['sequence'])} systems, "
                      f"{len(INTERLOCKS)} wired interlocks, {len(POINTS)} control points ({len(to_select)} still to select: "
                      f"{', '.join(to_select)}). Written to {r['path'].name}."])
