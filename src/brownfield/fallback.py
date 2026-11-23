"""Pass 3g step 9a (D28): when the data center's heat is gone.

The walk-up's heat and most of its hot water come from the data center's warm water: the radiant
floors through a plate exchanger (HX-2), the hot-water plant through a preheating exchanger (HX-1)
and a water-to-water heat pump whose own source is that water (HP-1). When it stops, for a repair,
an outage or for good, the building must still be heated and have hot water. Step 9a designs that:

- **The flats' heat:** each flat's ducted mini-split is a heat pump (Fujitsu ARUH12KUAS with its
  AOUH12KUBS1). Its heating capacity at the heating design dry bulb comes from Fujitsu's table
  (`data/fujitsu_aruh12_heating.csv`), corrected for its routed line set's length and the outdoor
  unit's height above it on the roof (`data/fujitsu_aouh12_heating_pipe_factors.csv`). It serves
  the same four rooms the radiant floors heat.
- **The hot water:** a backup electric heater on the plant's heater circuit after HP-1 (A. O.
  Smith DRE-52-12, 12.3 kW), its elements locked out unless the data center's heat is gone, so the
  237 gal of storage is heated as Ecosizer sized it. It must cover the plant's capacity.
- **The wiring** carries both (`electrical`): each flat's heat pump counted with its preheater,
  and the backup heater on the house panel, interlocked against HP-1 (220.60).

The control sequence that switches into this (9b) and its tests (9c) come next.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEATING = ROOT / "data" / "fujitsu_aruh12_heating.csv"
FACTORS = ROOT / "data" / "fujitsu_aouh12_heating_pipe_factors.csv"
FT, BTU_W = 0.3048, 3.412142
LB_GAL = 8.33  # lb of water a gallon (the recovery tables' basis: 1 kW = 4.1 gal at 100 F rise)


def _rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def heating_table() -> list[tuple[float, float, float]]:
    """(outdoor C, capacity kW, input kW), coldest first."""
    return sorted((float(r["outdoor_c"]), float(r["capacity_kw"]), float(r["input_kw"])) for r in _rows(HEATING))


def capacity_at(outdoor_c: float) -> tuple[float, float]:
    """The unit's heating capacity and input (kW) at an outdoor dry bulb, a straight line between
    the table's rows; outside them, an error (Fujitsu publishes nothing past its table)."""
    t = heating_table()
    for (t0, c0, i0), (t1, c1, i1) in zip(t, t[1:]):
        if t0 <= outdoor_c <= t1:
            k = (outdoor_c - t0) / (t1 - t0)
            return c0 + k * (c1 - c0), i0 + k * (i1 - i0)
    raise ValueError(f"{outdoor_c} C is off Fujitsu's heating table ({t[0][0]} to {t[-1][0]} C)")


def pipe_factor(length_m: float, height_m: float) -> float:
    """Fujitsu's heating correction for a line set's length and the indoor unit's height against
    the outdoor unit's (negative: the outdoor unit above), a straight line both ways between its
    published cells; a cell it leaves blank is never used."""
    rows = {float(r["height_m"]): {float(k[4:-1]): float(v) for k, v in r.items() if k.startswith("len_") and v} for r in _rows(FACTORS)}
    hs = sorted(rows)
    if not hs[0] <= height_m <= hs[-1]:
        raise ValueError(f"a height of {height_m:.1f} m is off Fujitsu's table")
    h0 = max(h for h in hs if h <= height_m)
    h1 = min(h for h in hs if h >= height_m)

    def along(h: float) -> float:
        pts = sorted(rows[h].items())
        for (l0, f0), (l1, f1) in zip(pts, pts[1:]):
            if l0 <= length_m <= l1:
                return f0 + (f1 - f0) * (length_m - l0) / (l1 - l0)
        raise ValueError(f"a {length_m:.1f} m line set at {h:g} m is off Fujitsu's table")

    f0, f1 = along(h0), along(h1)
    return f0 if h1 == h0 else f0 + (f1 - f0) * (height_m - h0) / (h1 - h0)


def recovery_gph(w: float, rise_f: float) -> float:
    """Gallons an hour an electric heater of `w` heats through `rise_f`: its heat over the water's."""
    return w * BTU_W / (LB_GAL * rise_f)


def space_heat(apt: dict, p: dict, s7: dict, placed: dict) -> dict:
    """Each flat on its mini-split at the heating design dry bulb, against its design heat."""
    units = {u["flat"]: u for u in placed["units"]}
    indoor = {e["id"].split("/")[0]: e for e in placed["equipment"] if e["id"].endswith("/minisplit")}
    cap, inp = capacity_at(p["systems.design.heating_c"])
    out = {}
    for n, fl in sorted(s7["loop"]["flats"].items()):
        line_m = s7["cooling"][n]["line_ft"] * FT
        height = indoor[n]["lo"][2] - units[n]["lo"][2]  # the indoor unit below the outdoor (negative)
        f = pipe_factor(line_m, height)
        out[n] = {"load_w": fl["w"], "capacity_w": cap * f * 1000, "input_w": inp * 1000, "factor": f, "line_m": line_m,
                  "height_m": height, "rooms": [r["id"].split("/")[-1] for r in fl["rooms"]]}
        out[n]["ok"] = out[n]["capacity_w"] >= out[n]["load_w"]
    return {"design_c": p["systems.design.heating_c"], "capacity_kw": cap, "input_kw": inp, "flats": out}


def hot_water(p: dict, s7: dict) -> dict:
    """The plant on its backup heater: the heater against the plant's capacity, and its recovery
    from the coldest inlet to storage."""
    w, h = s7["water"], "systems.hot_water."
    plant_w = w["primary"]["capacity_kbtuh"] * 1000 / BTU_W
    rise = p[h + "storage_f"] - w["inlet_f"]
    return {"plant_w": plant_w, "backup_w": p[h + "backup_w"], "ok": p[h + "backup_w"] >= plant_w, "rise_f": rise,
            "recovery_gph": recovery_gph(p[h + "backup_w"], rise), "storage_gal": w["primary"]["storage_gal"],
            "backup_gal": p[h + "backup_gal"], "day_gal": w["day_gal"]}


def checks(sh: dict, hw: dict, el: dict, p: dict) -> list[tuple[str, bool, str]]:
    house = el["service"]["house"]
    hp = next(r for r in house["rows"] if r["key"] == "dhw_heat_pump")
    bk = next(r for r in house["rows"] if r["key"] == "backup_heater")
    worst = min(sh["flats"].values(), key=lambda x: x["capacity_w"] - x["load_w"])
    worst_n = next(n for n, x in sh["flats"].items() if x is worst)
    known = recovery_gph(12300, 100)  # A. O. Smith's table: 12.3 kW, 100 F rise, 50 gal/h
    return [
        ("the recovery against A. O. Smith's own table (12.3 kW, a 100 F rise: 50 gal/h)", abs(known - 50) < 0.6, f"{known:.1f} gal/h"),
        ("Fujitsu's heating table read back at its own rows", abs(capacity_at(-15.0)[0] - 4.54) < 1e-9 and abs(pipe_factor(15, -7.5) - 0.926) < 1e-9,
         "-15 C 4.54 kW; 15 m at -7.5 m 0.926"),
        (f"every flat heated by its mini-split alone at the design dry bulb ({sh['design_c']:g} C), the line set's length and the "
         "outdoor unit's height counted", all(x["ok"] for x in sh["flats"].values()),
         f"least spare {worst_n}: {worst['capacity_w']:.0f} W against {worst['load_w']:.0f} (factor {worst['factor']:.3f})"),
        ("the plant's backup heater covers its capacity (Ecosizer's, over its run hours)", hw["ok"],
         f"{hw['backup_w'] / 1000:.1f} kW against {hw['plant_w'] / 1000:.2f}; {hw['recovery_gph']:.0f} gal/h through {hw['rise_f']:.0f} F"),
        ("the house panel's breaker covers its load, the backup heater and the heat pump interlocked (220.60)",
         house["breaker_a"] >= house["amps"] and not hp["counted"] and bk["counted"],
         f"{house['amps']:.1f} A on {house['breaker_a']:.0f} A (the backup {bk['calc_va']:,.0f} VA counted, the heat pump not)"),
        ("each flat's feeder covers its heat pump and preheater together", all(f["breaker_a"] >= f["amps"] for f in el["feeders"].values()),
         f"{max(f['amps'] for f in el['feeders'].values()):.1f} A at most on {min(f['breaker_a'] for f in el['feeders'].values()):.0f} A"),
        (f"every feeder within {p['systems.wiring.vd_feeder_max']:.0%} drop on its route",
         all(max(f["drop"]["ll"], f["drop"]["an"], f["drop"]["bn"]) <= p["systems.wiring.vd_feeder_max"] + 1e-12 for f in el["feeders"].values()),
         f"worst {max(max(f['drop']['ll'], f['drop']['an'], f['drop']['bn']) for f in el['feeders'].values()):.2%}"),
        ("the service carries it all on its main", el["service"]["amps"] <= el["service"]["main_a"],
         f"{el['service']['total_va']:,.0f} VA, {el['service']['amps']:.0f} A on {el['service']['main_a']} A"),
    ]


def run(apt: dict, p: dict) -> dict:
    from . import routed, routing

    routes = routed.load(apt, p)
    if routes is None or not routes.fresh:
        raise SystemExit("no fresh routes: `brownfield routes` first")
    s7 = routed.summary(apt, p, routes)
    if "incomplete" in s7:
        raise SystemExit(f"7c's designs didn't run: {s7['incomplete']}")
    placed = routing.placements(apt, p)
    sh, hw = space_heat(apt, p, s7, placed), hot_water(p, s7)
    el = s7["electrical"]
    return {"space": sh, "water": hw, "electrical": el, "checks": checks(sh, hw, el, p)}


def report(r: dict) -> str:
    from .systems import report as checks_report

    sh, hw, el = r["space"], r["water"], r["electrical"]
    house = el["service"]["house"]
    lines = ["Pass 3g step 9a: when the data center's heat is gone", "", checks_report(r["checks"]), "",
             f"The flats on their mini-splits at {sh['design_c']:g} C (Fujitsu: {sh['capacity_kw']:.2f} kW at 70 F indoor, drawing "
             f"{sh['input_kw']:.2f} kW, before the line set's correction):"]
    for n, x in sh["flats"].items():
        lines.append(f"  {n:14s} {x['load_w']:5.0f} W asked, {x['capacity_w']:5.0f} W given ({x['line_m'] / FT:.0f} ft of line, the outdoor "
                     f"unit {-x['height_m']:.1f} m above: x{x['factor']:.3f}); rooms {', '.join(x['rooms'])}")
    lines += ["", f"The hot water on the backup heater: {hw['backup_w'] / 1000:.1f} kW against the plant's {hw['plant_w'] / 1000:.2f} kW; "
                  f"{hw['recovery_gph']:.0f} gal/h from the coldest inlet to storage ({hw['rise_f']:.0f} F), into {hw['storage_gal']:.0f} gal "
                  f"of storage and its own {hw['backup_gal']:.0f}; the design day {hw['day_gal']:.0f} gal.",
              "", f"The house panel: {house['calculated_va']:,.0f} VA calculated, {house['amps']:.1f} A: a {house['breaker_a']:.0f} A position. "
                  f"The service: {el['service']['total_va']:,.0f} VA, {el['service']['amps']:.0f} A on its {el['service']['main_a']} A main. "
                  f"The PV the house panel takes under the 120% rule: {el['pv']['house_ac_kw']:.1f} kW AC."]
    return "\n".join(lines)
