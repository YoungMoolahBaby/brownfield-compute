"""Pass 3g step 10 (D28): the usual walk-up, priced from sources, against the engineered design.

10a, what each walk-up has (`run`; no prices yet, those are 10b's):

- **The usual walk-up, from sources** (`usual_practice`). Census's Characteristics of New Housing
  2025 (new multifamily units completed in the Northeast: the heating system by its fuel) and
  EIA's RECS 2020 microdata (apartments built 2010-2020: whether the water heater is the flat's
  own, its fuel and size; the heating), with RECS's jackknife errors. The weights and the errors
  are checked against EIA's own published table (HC8.1).
- **Three usual walk-ups** beside the engineered design, on its layout and envelope:
  - *electric*: a heat pump (the same ducted mini-split) and a 50 gal electric water heater in
    each flat; the bath fan running as the flat's ventilation; the kitchen's hood vented outdoors;
  - *gas*: a gas furnace with a split air conditioner, and a gas water heater, in each flat;
  - *central*: heat pumps in the flats, and the hot water from a central gas water heater through
    the loops the energy code asks of any central system (C404.5). Set beside the engineered plant,
    it parts the code's cost from the plant's.
  Each has PVC drains and vents, the street's pressure (no reducing valve), no submeters, no PV,
  and the sprinklers on one shared service.
- **The item lists** (`items`):
  - every element of the published services model (Addendum 7's), in the walk-ups that have it;
  - the design's items the model doesn't hold: the radiant tubing and its topping, the plant's
    wall-hung equipment, the meters, the fire service's, the insulation, the air sealing and the
    tests;
  - each usual walk-up's own, by stated rules from the same layout.
- **Checks** (`checks`):
  - the model counted once: its lengths, fittings and elements reproduce its schedules;
  - every item traces to a model element, a design parameter or a stated rule;
  - the usual walk-ups work: each flat's heat pump carries its own heat at the code's leakage
    with no heat recovery; each flat's own hot pipe within IPC 607.2; each service on a main the
    meter stack offers (NEC 220.84, as the engineered design's).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np

from . import OUT_DIR, ROOT

RAW = ROOT / "data" / "raw" / "pass3g" / "step10"
PUBLISHED = ROOT / "docs" / "pass3" / "bidset"
SERVICES = PUBLISHED / "services-addendum-7.ifc"  # the services model in effect (Addendum 7's; Addendum 8 changed none)
DERIVED = ROOT / "data" / "baseline_usual_practice.csv"
FT, FT2 = 0.3048, 0.09290304

WALKUPS = ("engineered", "electric", "gas", "central")
NAMES = {"engineered": "the engineered design",
         "electric": "the usual walk-up, all electric: a heat pump and a water heater in each flat",
         "gas": "the usual walk-up, gas: a furnace, an air conditioner and a water heater in each flat",
         "central": "the usual walk-up, central hot water: a heat pump in each flat, a gas water heater for the building"}
ALL = WALKUPS
ENG = ("engineered",)
LOOPS = ("engineered", "central")  # a central plant's hot water, through each flat's loop (C404.5)
USUAL = ("electric", "gas", "central")
OWN_HEATER = ("electric", "gas")  # a water heater in each flat
HEAT_PUMPS = ("engineered", "electric", "central")  # the ducted mini-split in each flat

UA = "brownfield-compute (open research)"
CENSUS_URL = "https://www.census.gov/construction/chars/xls/{}.xls"
CENSUS_TABLES = ("mfu_heatfuelbysystem_cust", "mfu_heatingfuel_cust")
RECS_URL = "https://www.eia.gov/consumption/residential/data/2020/csv/recs2020_public_v7.csv"
HC81_URL = "https://www.eia.gov/consumption/residential/data/2020/hc/xls/HC%208.1.xlsx"


def _get(url: str, path: Path) -> Path:
    """A public file, downloaded once into data/raw (gitignored)."""
    if not path.exists():
        import requests

        with requests.get(url, headers={"User-Agent": UA}, timeout=600, stream=True) as r:
            r.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".part")
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
            tmp.replace(path)
    return path


# ---- 10a: the usual walk-up, from sources ----

def _num(x) -> float:
    """A Census cell: thousands of units; '(Z)' is fewer than 500, taken as none."""
    if isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x)):
        return float(x)
    return 0.0


def census_heating(region: str = "Northeast", year: int = 2025) -> dict:
    """New multifamily units completed (thousands), by heating system and fuel: Census CHARS's
    `mfu_heatfuelbysystem` (furnace, heat pump; hot water or steam, other or none, each by gas,
    electricity, oil and other), and the fuel table's totals to check them against."""
    import pandas as pd

    t = pd.read_excel(_get(CENSUS_URL.format(CENSUS_TABLES[0]), RAW / "census" / f"{CENSUS_TABLES[0]}.xls"), sheet_name=0,
                      header=None, engine="calamine")
    out, block = {}, 0
    systems = (("furnace", "heat_pump"), ("hot_water", "other"))
    for i in range(len(t)):
        if str(t.iat[i, 1]).strip() == region:
            row = next(j for j in range(i, i + 20) if str(t.iat[j, 0]).strip() == str(year))
            for k, name in enumerate(systems[block]):
                c = 1 + 4 * k
                out[name] = {"total": _num(t.iat[row, c]), "gas": _num(t.iat[row, c + 1]), "electricity": _num(t.iat[row, c + 2]),
                             "other": _num(t.iat[row, c + 3])}
            block += 1
            if block == 2:
                break
    f = pd.read_excel(_get(CENSUS_URL.format(CENSUS_TABLES[1]), RAW / "census" / f"{CENSUS_TABLES[1]}.xls"), sheet_name=0,
                      header=None, engine="calamine")
    fuel = None
    for i in range(len(f)):
        if str(f.iat[i, 1]).strip() == region:
            row = next(j for j in range(i, i + 70) if str(f.iat[j, 0]).strip() == str(year))
            fuel = {"total": _num(f.iat[row, 1]), "gas": _num(f.iat[row, 2]), "electricity": _num(f.iat[row, 3])}
            break
    return {"region": region, "year": year, "systems": out, "fuel": fuel,
            "source": "Census, Characteristics of New Housing (2025 data, published 2026-07-01), multifamily units completed: "
                      "mfu_heatfuelbysystem_cust.xls and mfu_heatingfuel_cust.xls"}


RECS_COLS = ["TYPEHUQ", "YEARMADERANGE", "REGIONC", "H2OAPT", "FUELH2O", "WHEATSIZ", "EQUIPM", "HEATAPT", "FUELHEAT", "NWEIGHT",
             *[f"NWEIGHT{i}" for i in range(1, 61)]]


def recs() -> "pd.DataFrame":  # noqa: F821
    import pandas as pd

    return pd.read_csv(_get(RECS_URL, RAW / "recs" / "recs2020_public_v7.csv"), usecols=RECS_COLS)


def _jk(g, mask) -> tuple[float, float]:
    """A weighted share and its standard error by RECS 2020's jackknife (JK1, 60 replicates: (R-1)/R
    times the squared deviations; it reproduces HC8.1's published errors, `recs_check`)."""
    w = g["NWEIGHT"]
    est = float((w * mask).sum() / w.sum())
    reps = np.array([(g[f"NWEIGHT{i}"] * mask).sum() / g[f"NWEIGHT{i}"].sum() for i in range(1, 61)])
    return est, float(np.sqrt(59 / 60 * ((reps - est) ** 2).sum()))


def recs_new_apartments(d, region: str | None = None) -> dict:
    """Apartments built 2010-2020 in buildings of 5 or more units (the walk-up's kind), in `region`
    or the US: the water heater, its fuel and size; the heating. Shares with their errors and the
    records behind them."""
    g = d[(d.TYPEHUQ == 5) & d.YEARMADERANGE.isin([8, 9])]
    if region:
        g = g[g.REGIONC == region.upper()]
    own, gas, elec = g.H2OAPT == 0, g.FUELH2O.isin([1, 2]), g.FUELH2O == 5
    rows = {
        "water heater the flat's own, electric": own & elec, "water heater the flat's own, gas": own & gas,
        "water heater shared, electric": (g.H2OAPT == 1) & elec, "water heater shared, gas": (g.H2OAPT == 1) & gas,
        "water heater 31-49 gal": g.WHEATSIZ == 2, "water heater 50 gal or more": g.WHEATSIZ == 3,
        "water heater 30 gal or less": g.WHEATSIZ == 1, "water heater tankless": g.WHEATSIZ == 4,
        "heating a central heat pump or mini-split": g.EQUIPM.isin([4, 13]), "heating a central furnace": g.EQUIPM == 3,
        "heating built-in electric (baseboard)": g.EQUIPM == 5, "heating shared": g.HEATAPT == 1,
    }
    return {"region": region or "US", "records": int(len(g)), "units_k": float(g.NWEIGHT.sum() / 1e3),
            "shares": {k: _jk(g, m) for k, m in rows.items()}}


def recs_check(d) -> dict:
    """The known case: the microdata's weights and jackknife against EIA's own HC8.1 (main water
    heater fuel, apartments in buildings of 5 or more units, millions and their RSEs)."""
    import pandas as pd

    x = pd.read_excel(_get(HC81_URL, RAW / "recs" / "HC8.1.xlsx"), sheet_name=None, header=None, engine="openpyxl")
    data, rse = x["data"], x["rse"]

    def first(t, label):
        return next(i for i in range(len(t)) if str(t.iat[i, 0]).strip() == label)

    a = d[d.TYPEHUQ == 5]
    out = {}
    for label, codes in (("Electricity", [5]), ("Natural gas", [1])):
        m = a.FUELH2O.isin(codes)
        est = float(a.NWEIGHT[m].sum())
        reps = np.array([a[f"NWEIGHT{i}"][m].sum() for i in range(1, 61)])
        se = float(np.sqrt(59 / 60 * ((reps - est) ** 2).sum()))
        out[label] = {"ours_m": est / 1e6, "eia_m": float(data.iat[first(data, label), 5]),
                      "ours_rse": 100 * se / est, "eia_rse": float(rse.iat[first(rse, label), 5])}
    return out


def usual_practice() -> dict:
    """Both sources, and the small derived table (`data/baseline_usual_practice.csv`) with them named."""
    d = recs()
    out = {"census": census_heating(), "recs_us": recs_new_apartments(d), "recs_ne": recs_new_apartments(d, "Northeast"),
           "recs_check": recs_check(d)}
    rows = ["source,region,measure,value,se,unit"]
    c = out["census"]
    for sys_, v in c["systems"].items():
        for fuel, n in v.items():
            rows.append(f"Census CHARS 2025 (mfu_heatfuelbysystem),{c['region']},{sys_} {fuel},{n:g},,thousand new multifamily units completed in {c['year']}")
    for key in ("recs_us", "recs_ne"):
        r = out[key]
        for k, (e, s) in r["shares"].items():
            rows.append(f"EIA RECS 2020 microdata (v7),{r['region']},{k},{100 * e:.1f},{100 * s:.1f},"
                        f"% of apartments in 5+ unit buildings built 2010-2020 ({r['records']} records)")
    DERIVED.write_text("\n".join(rows) + "\n", encoding="utf-8")
    out["derived"] = DERIVED
    return out


# ---- 10a: the item lists ----

def _role(run: str) -> str:
    """A run's role in the item lists: its id with the flat and the column taken out."""
    run = re.sub(r"\d-(front|back)-(left|right)", "*", run)
    return re.sub(r"^(front|back)-(left|right)", "*", run)


ROLE_WORDS = {  # how a run's role reads in the lists
    "*/cold": "risers", "*/hot": "risers", "*/hot-return": "return risers", "*/loop-supply": "supply risers",
    "*/loop-return": "return risers", "*/stack": "stacks", "*/vent-stack": "vent stacks", "*/standpipe": "washer standpipes",
    "main/cold": "main under the slab", "main/hot": "main under the slab", "main/hot-return": "return main under the slab",
    "main/loop-supply": "supply main under the slab", "main/loop-return": "return main under the slab",
    "plumbing/cold/*": "the flats' branches", "plumbing/hot/*": "the flats' branches", "plumbing/hot-return/*": "the flats' returns",
    "plumbing/drain/*/branch": "the flats' branches", "plumbing/drain/*/tub": "the tubs' drains", "plumbing/vent/*": "the flats' vents",
    "plumbing/building-drain": "the building drain", "hvac/loop-supply-tail/*": "the flats' supply tails",
    "hvac/loop-return-tail/*": "the flats' return tails", "hvac/condensate/*": "condensate", "hvac/ms-supply/*": "supply ducts",
    "hvac/erv-ea/*": "the ERVs' exhaust to outdoors", "hvac/erv-oa/*": "the ERVs' outdoor air", "hvac/erv-exhaust/*": "the ERVs' exhaust from the rooms",
    "hvac/erv-supply/*": "the ERVs' supply", "hvac/line-set/*": "line sets", "*/line-set/*": "line sets in the plumbing walls",
    "hvac/roof-line-set/*": "line sets on the roof", "electrical/feeder/*": "feeders", "*/feeder/*": "feeders in the plumbing walls",
    "fire/flat/*": "the flats' sprinkler pipe", "fire/main": "the sprinkler main", "stair/fire-riser": "the sprinkler riser",
    "fire/stair/1": "the stair's sprinkler pipe", "fire/stair/2": "the stair's sprinkler pipe", "fire/stair/3": "the stair's sprinkler pipe",
}


def walkups_of(props: dict) -> tuple[str, ...]:
    """Which walk-ups have a run of the services model (a segment or a fitting): the cold water, the
    sprinklers, the mini-splits' ducts, line sets and condensate in every one (the gas walk-up's
    air conditioner takes the same), the hot water's mains, risers, branches and returns in the
    walk-ups with a central plant, the building loop and the ERVs' ducts in the engineered design
    alone; the drains and vents as drawn in cast iron (the usual's twins in PVC are added apart);
    the wiring in every one but the ERVs' and the preheaters' circuits."""
    system, run = props.get("System"), props.get("Run", "")
    if system in ("cold", "sprinkler", "air", "refrigerant", "condensate"):
        return ALL
    if system == "hot":
        return LOOPS
    if system in ("loop", "ventilation", "drain", "vent"):
        return ENG
    if system == "power":
        return ENG if run.startswith("electrical/branch/") and run.split("/")[-1] in ("erv", "preheater") else ALL
    raise ValueError(f"no walk-ups for system {system!r} ({run})")


ELEMENT_WALKUPS = {  # an element of the model (not a run): which walk-ups have it, by its class and kind
    "IfcAirToAirHeatRecovery": ENG, "IfcElectricDistributionBoard": ALL, "IfcElectricAppliance": ALL, "IfcSanitaryTerminal": ALL,
    "IfcFireSuppressionTerminal": ALL, "IfcSensor": ALL, "IfcValve": LOOPS, "IfcTank": ENG, "IfcBoiler": ENG,
}


def _element_walkups(r: dict) -> tuple[str, ...]:
    p, cls = r["props"], r["cls"]
    kind = p.get("Kind", "")
    if cls == "IfcUnitaryEquipment":
        return HEAT_PUMPS if kind.startswith("mini-split") else ENG  # HP-1, the plant's heat pump
    if cls == "IfcAirTerminal":
        return ALL if p.get("System") == "air" else ENG  # the mini-splits' registers; the ERVs' grilles and caps
    if cls == "IfcPipeFitting" and "manifold" in kind:
        return ENG
    return ELEMENT_WALKUPS[cls]


def _q(walkups: tuple[str, ...], n: float) -> dict[str, float]:
    return {w: (n if w in walkups else 0.0) for w in WALKUPS}


def _add(items: dict, key: tuple, what: str, unit: str, qty: dict[str, float], basis: str, kind: str, system: str, **more) -> None:
    it = items.setdefault(key, {"id": " | ".join(str(k) for k in key), "system": system, "what": what, "unit": unit,
                                "qty": {w: 0.0 for w in WALKUPS}, "basis": basis, "kind": kind, **more})
    for w, n in qty.items():
        it["qty"][w] += n


def _size(s: str) -> str:
    return f"{s} in." if s and re.match(r"^[\d/ -]+$", str(s)) else str(s)


PVC_DWV = "PVC DWV, Schedule 40 (the usual walk-up's)"


def model_items(rb: list[dict]) -> tuple[dict, dict]:
    """Every element of the services model in the item lists: runs (ft) by system, material, size
    and role; fittings (each) by system, material, kind and size; the rest (each) by class and kind.
    The drains' and vents' cast iron gets its twin in PVC for the usual walk-ups, run for run.
    Returns the items and what was counted (to check against the schedules)."""
    items: dict = {}
    seen = {"ft": 0.0, "fittings": 0, "equipment": 0, "fixtures": 0, "sprinklers": 0, "air_terminals": 0, "switches": 0, "valves": 0,
            "rows": len(rb)}
    for r in rb:
        p, cls = r["props"], r["cls"]
        system, material, size = p.get("System"), p.get("Material", ""), str(p.get("Size", ""))
        if cls.endswith("Segment"):
            role = _role(p.get("Run", ""))
            ft = p["Length"] / FT
            seen["ft"] += ft
            words = ROLE_WORDS.get(role)
            if words is None and role.startswith("electrical/branch/"):
                words = "the ERVs' and preheaters' circuits" if role.split("/")[-1] in ("erv", "preheater") else "branch circuits"
            if words is None:
                raise ValueError(f"no words for {role}")
            key = ("run", system, material, size, words)
            _add(items, key, f"{material}, {_size(size)}: {words}", "ft", _q(walkups_of(p), ft),
                 f"the services model, {role}", "model", system, size=size, role=words, run=True)
            if system in ("drain", "vent"):
                _add(items, ("run", system, PVC_DWV, size, words), f"{PVC_DWV}, {_size(size)}: {words}", "ft", _q(USUAL, ft),
                     f"the services model's cast iron run for run (IPC 2021 Tables 702.1-702.4 list PVC DWV), {role}", "rule", system)
        elif cls.endswith("Fitting") and "manifold" not in p.get("Kind", ""):
            seen["fittings"] += 1
            kind = p.get("Kind", r["pre"])
            _add(items, ("fit", system, material, kind, size), f"{material}, {kind}, {_size(size)}", "each", _q(walkups_of(p), 1),
                 "the services model's fittings", "model", system)
            if system in ("drain", "vent"):
                _add(items, ("fit", system, PVC_DWV, kind, size), f"{PVC_DWV}, {kind}, {_size(size)}", "each", _q(USUAL, 1),
                     "the services model's cast iron fittings, one for one", "rule", system)
        else:
            k0 = p.get("Key", "").split("/")[0]
            group = {"eq": "equipment", "fixture": "fixtures", "head": "sprinklers", "switch": "switches", "valve": "valves"}.get(k0)
            group = "equipment" if "manifold" in p.get("Kind", "") else group or ("air_terminals" if cls == "IfcAirTerminal" else None)
            if group is None:
                raise ValueError(f"an element of no schedule: {p.get('Key')} ({cls})")
            seen[group] += 1
            kind = p.get("Kind") or p.get("Model") or r["name"]
            kind = re.sub(r",? ?\d-(front|back)-(left|right).*$", "", kind)
            if cls == "IfcFireSuppressionTerminal":
                kind = f"sprinkler, {p.get('Model', '')}"
            _add(items, ("el", cls, kind), kind, "each", _q(_element_walkups(r), 1), f"the services model, {cls}", "model", system or "")
    return items, seen


def flat_hot_rule(apt: dict, p: dict, routes) -> dict[str, dict]:
    """A flat's own water heater (the electric and gas walk-ups), by rule: in the utility closet on
    the plumbing wall, its outlet at the tank's top; a trunk along the wall at that height spanning
    the flat's hot fixtures (the engineered flat's hot terminals: lavatory, tub, sink, dishwasher,
    washer), and a drop to each. The trunk 3/4 in., the drops 1/2 in. (`baseline.usual`). The
    longest path is IPC 607.2's."""
    u = "baseline.usual."
    rooms = {x["id"]: x for x in apt["rooms"]["rooms"]}
    out = {}
    for f in apt["flats"]:
        n = f["name"]
        req = routes.reqs[f"plumbing/hot/{n}"]
        terms = {t["ref"]: t["xyz"] for t in req["terminals"]}
        util = rooms[f"{n}/utility"]
        wall_x = float(np.median([xyz[0] for xyz in terms.values()]))  # the fixtures' wall face
        y_h = (util["lo_m"][1] + util["hi_m"][1]) / 2
        z_h = util["lo_m"][2] + p[u + "heater_h_in"] * 0.0254  # the tank's top, above the flat's floor
        ys = [xyz[1] for xyz in terms.values()]
        trunk = max(ys + [y_h]) - min(ys + [y_h])
        drops = {k: abs(xyz[2] - z_h) + abs(xyz[0] - wall_x) for k, xyz in terms.items()}
        paths = {k: abs(xyz[1] - y_h) + drops[k] for k, xyz in terms.items()}
        far = max(paths, key=paths.get)
        out[n] = {"trunk_ft": trunk / FT, "drops_ft": sum(drops.values()) / FT, "longest_ft": paths[far] / FT, "farthest": far,
                  "heater_y_m": y_h}
    return out


def _per_flat(routes, prefix: str, flats: list[str]) -> dict[str, float]:
    """A run's routed length in each flat (ft), as a proxy for a usual walk-up's run of the same reach."""
    return {n: routes.tree(f"{prefix}/{n}").length_m / FT for n in flats}


def design_items(apt: dict, p: dict, s7: dict, its: list[dict]) -> dict:
    """The engineered design's items the services model doesn't hold, and those the walk-ups share
    or swap there, from the design's own parameters and runs."""
    from . import acceptance

    items: dict = {}
    sw = "systems."
    flats = len(apt["flats"])
    L = s7["loop"]
    # The radiant floors: their tubing (step 3's circuits, as 7c routes their tails) and the topping
    # that covers it on the upper floors (the ground floor's is in the slab, which every walk-up has),
    # and the heated slab's insulation under its whole area (PA IECC Table R402.1.3, note d).
    tubing = sum(x["circuits"] * x["circuit_ft"] for fl in L["flats"].values() for x in fl["rooms"])
    _add(items, ("radiant", "tubing"), "radiant tubing, PEX 1/2 in., in the floors (step 3's circuits)", "ft", _q(ENG, tubing),
         "hvac.substation's circuits (routed.summary's loop)", "design", "loop")
    upper = sum(f["floor_m2"] for f in apt["flats"] if f["floor"] > 1) / FT2
    _add(items, ("radiant", "topping"), f"gypsum topping {p['pass3.frame.topping_in']:g} in. over the upper flats' floors, "
         "the radiant tubing's cover", "ft2", _q(ENG, upper), "pass3.frame.topping_in; the flats' floors on storeys 2 and 3", "design", "loop")
    ground = sum(f["floor_m2"] for f in apt["flats"] if f["floor"] == 1) / FT2
    _add(items, ("radiant", "slab insulation"), "R-5 under the whole of the ground flats' heated slab (PA IECC Table R402.1.3, note d)",
         "ft2", _q(ENG, ground), "systems.addendum_3; the ground flats' floors", "design", "loop")
    _add(items, ("radiant", "heat meter"), "heat meter, each flat (Kamstrup MULTICAL 403, basis of design)", "each", _q(ENG, flats),
         "systems.heat_meter", "design", "loop")
    # The plant's wall-hung equipment and its points (P-601, M-602; eight never chosen, sequence.POINTS).
    for tag, what in (("HX-1", "plate exchanger, the data center's water to the heater circuit"),
                      ("HX-2", "plate exchanger, the data center's water to the building loop"),
                      ("P-1", "the building loop's circulator (Grundfos ALPHA2 15-55F)"), ("P-2", "the heater circuit's pump (to select)"),
                      ("V-1", "modulating valve through HX-1 (to select)"), ("V-2", "modulating valve through HX-2 (to select)"),
                      ("PC-1", "the plant controller (to select)"), ("TS-1/2/5, FS-1", "the plant's sensors and flow switch (to select)"),
                      ("ET", "expansion tanks, the building loop and the heater circuit")):
        _add(items, ("plant", tag), f"{tag}: {what}", "each", _q(ENG, 1), "P-601, M-602; sequence.POINTS", "design", "hot")
    for tag, what in (("P-3", "the hot water's recirculation pump (Grundfos ALPHA2 15-55SF)"), ("MV-1", "the master mixing valve (ASSE 1017)"),
                      ("ET-DHW", "the hot water's thermal expansion tank (IPC 607.3)")):
        _add(items, ("plant", tag), f"{tag}: {what}", "each", _q(LOOPS, 1), "P-601; sequence.POINTS (the central walk-up's the same)",
             "design", "hot")
    # The water service, the meters and the fire service (step 6: separate and supervised).
    _add(items, ("water", "submeters"), "hot and cold water submeters, each flat (Badger E-Series 3/4 in., basis of design)", "each",
         _q(ENG, 2 * flats), "systems.plumbing.submeter_psi_*", "design", "cold")
    _add(items, ("water", "prv"), "pressure-reducing valve, 2 in. (Watts LFN45B): 60 psi in the building, for quiet", "each", _q(ENG, 1),
         "systems.plumbing.max_static_psi", "design", "cold")
    _add(items, ("water", "domestic service"), "domestic water service, 2 in.: its tap, meter and double check "
         "valve assembly (Watts LF007)", "each", _q(ENG, 1), "systems.plumbing.tap_in; step 4", "design", "cold")
    _add(items, ("water", "domestic line"), "domestic service line, 2 in., from the main to the annex", "ft", _q(ENG, p[sw + "sprinkler.underground_ft"]),
         "systems.sprinkler.underground_ft (the same run as the fire service's; placeholder until the site plan)", "design", "cold")
    _add(items, ("fire", "underground"), f"underground water service, {p[sw + 'sprinkler.underground_id_in']:g} in. (the fire service; "
         "the usual walk-ups' one shared service)", "ft", _q(ALL, p[sw + "sprinkler.underground_ft"]),
         "systems.sprinkler.underground_ft and underground_id_in (placeholders until the authority and the site plan)", "design", "sprinkler")
    _add(items, ("fire", "service"), f"the fire service's tap and its double check valve assembly with two OS&Y valves "
         f"({p[sw + 'sprinkler.underground_id_in']:g} in.)", "each", _q(ENG, 1), "step 6: a separate fire service", "design", "sprinkler")
    _add(items, ("fire", "supervision"), "supervision: two tamper switches and the monitoring panel (Potter PFC-6006), to a "
         "supervising station", "each", _q(ENG, 1), "step 6 (IBC 903.4)", "design", "sprinkler")
    _add(items, ("fire", "alarm"), "waterflow switch and exterior horn-strobe (IBC 903.4.2)", "each", _q(ALL, 1), "step 6", "design", "sprinkler")
    _add(items, ("fire", "fdc"), "fire department connection with its check valve and automatic drip (NFPA 13R 6.11.1)", "each", _q(ALL, 1),
         "step 6", "design", "sprinkler")
    _add(items, ("fire", "combined service"), f"the shared service's tap, meter and backflow assembly ({p['baseline.usual.combined_service_in']:g} "
         "in.), the sprinklers and the flats on one main", "each", _q(USUAL, 1), "baseline.usual.combined_service_in (step 6's other way)",
         "rule", "sprinkler")
    # The ERVs' preheaters.
    _add(items, ("ventilation", "preheater"), "ERV preheater, 1 kW (Ouellet ODHR0501002)", "each", _q(ENG, flats), "systems.electrical.preheater_va",
         "design", "ventilation")
    # The roof's PV on the house panel (step 5; 9c's 120% rule).
    _add(items, ("electrical", "pv"), "PV on the roof, on the house panel", "kW AC", _q(ENG, s7["electrical"]["pv"]["house_ac_kw"]),
         "electrical.pv (routed.summary)", "design", "power")
    # The envelope's air sealing and its tests (Addendum 8): every walk-up tests each flat (the code's
    # R402.4.1.2, or Phius's compartment test); the engineered design also seals to Phius's limit and
    # tests the whole building.
    lk = acceptance.leakage(apt, p)
    _add(items, ("envelope", "air sealing"), f"air sealing to Phius's {lk['rate_cfm50_ft2']:g} cfm50/ft2, beyond the code's 3.0 ACH50",
         "ft2", _q(ENG, lk["area_ft2"]), "Addendum 8, E-1 (the gross enclosure)", "design", "envelope")
    _add(items, ("envelope", "whole-building test"), "blower door test, the whole building (Phius, multi-point, both ways)", "each",
         _q(ENG, 1), "Addendum 8, E-1", "design", "envelope")
    _add(items, ("envelope", "flat tests"), "blower door test, each flat (the code's, or Phius's compartment test)", "each", _q(ALL, flats),
         "IECC R402.4.1.2; Addendum 8, E-1", "design", "envelope")
    # The tests and inspections (01 45 00), each in the walk-ups it applies to: the codes' own where
    # the walk-up has what they test, the design's claims in the engineered design (and a central
    # plant's loops balanced in the central walk-up). E-1's are the envelope's, above; V-2 asks none.
    for it in its:
        if it["id"] in ("E-1", "V-2"):
            continue
        walk = TEST_WALKUPS.get(it["id"], ALL)
        n = {"P-4": {"engineered": 2.0}}.get(it["id"], {})  # the backflow assemblies: the domestic and the fire service's
        what = TEST_WORDS.get(it["id"], it["what"])
        _add(items, ("test", it["id"]), f"test {it['id']}: {what}", "each", {**_q(walk, 1), **n},
             f"acceptance.items ({it['basis']})", "design", "tests")
    # The house panel's circuits to the plant (the annex's wiring isn't in the services model).
    _add(items, ("electrical", "plant circuits"), "the house panel's circuits to the plant: HP-1, BK-1, ST-2's element, the pumps and PC-1",
         "lot", _q(ENG, 1), "electrical.house_loads (step 5; 9a)", "design", "power")
    _add(items, ("electrical", "central circuits"), "the house panel's circuits to the central heater and its pump", "lot",
         _q(("central",), 1), "the central walk-up's plant", "rule", "power")
    return items


TEST_WALKUPS = {  # 01 45 00's items that not every walk-up has (the rest are every walk-up's)
    "HW-1": LOOPS, "HW-2": LOOPS, "HW-3": LOOPS, "HW-4": LOOPS,  # IECC C404, a central plant's
    "HW-5": ENG, "H-1": ENG, "H-2": ENG, "H-3": ENG, "H-4": ENG,  # the plant and the building loop
}
TEST_WORDS = {  # where a test reads differently in the usual walk-ups
    "V-1": "each flat's ventilation flows (IECC R403.6.3: the engineered design's ERVs, the usual walk-ups' bath fans)",
}


def insulation_items(model: dict, p: dict) -> dict:
    """The pipe and duct insulation the specification asks of the model's runs: the hot water's
    (IECC C404.4, Table C403.12.3, any central plant's: 1 in. under 1-1/2 in., 1-1/2 in. at and over),
    the cold and the loop's risers (0.5 in.) and the ERVs' outdoor ducts (1.5 in.) in the engineered
    design. The mains under the slab come insulated."""
    items: dict = {}
    s, r = "systems.hot_water.", "systems.routing."

    def nps(size: str) -> float:
        whole, _, frac = size.partition("-")
        if "/" in whole:
            frac, whole = whole, "0"
        a, b = (frac.split("/") + ["1"])[:2] if frac else ("0", "1")
        return float(whole) + float(a) / float(b)

    for it in model.values():
        if not it.get("run") or "under the slab" in it["role"]:
            continue
        system, size, words = it["system"], it["size"], it["role"]
        if system == "hot":
            t = p[s + ("insulation_in_large" if nps(size) >= 1.5 else "insulation_in_small")]
            what, walk = f"insulation {t:g} in. on hot-water pipe, {size} in. ({words})", LOOPS
        elif system == "cold" and words == "risers":
            t, what, walk = p[r + "cold_insulation_in"], f"insulation {p[r + 'cold_insulation_in']:g} in. on the cold risers, {size} in.", ENG
        elif system == "loop" and "risers" in words:
            t, what, walk = p[r + "loop_insulation_in"], f"insulation {p[r + 'loop_insulation_in']:g} in. on the loop's {words}, {size} in.", ENG
        elif system == "ventilation" and words in ("the ERVs' exhaust to outdoors", "the ERVs' outdoor air"):
            t, what, walk = p[r + "oa_insulation_in"], f"insulation {p[r + 'oa_insulation_in']:g} in. on {words}, {size} in. duct", ENG
        else:
            continue
        n = max(it["qty"][w] for w in walk)
        _add(items, ("insulation", system, size, words), what, "ft", _q(walk, n), f"{it['id']}; the specification's thickness", "design", system)
    return items


def usual_items(apt: dict, p: dict, routes, rule: dict) -> dict:
    """Each usual walk-up's own, by stated rules from the same layout. Where a usual run has no
    route of its own, a routed run of the same reach stands in for its length, said so."""
    u = "baseline.usual."
    items: dict = {}
    names = [f["name"] for f in apt["flats"]]
    flats = len(names)
    dryer = _per_flat(routes, "electrical/branch", [f"{n}/dryer" for n in names])  # the utility closet's own circuit
    feeder = _per_flat(routes, "electrical/feeder", names)  # the meter wall to each flat
    ea = _per_flat(routes, "hvac/erv-ea", names)  # the utility closet's ceiling to the facade
    oa = _per_flat(routes, "hvac/erv-oa", names)
    # A water heater in each flat: its hot pipe by `flat_hot_rule`, its R-3 trunk (IECC R403.5.2), its
    # thermal expansion tank (IPC 607.3: the service passes a backflow preventer).
    trunk = sum(x["trunk_ft"] for x in rule.values())
    drops = sum(x["drops_ft"] for x in rule.values())
    pex = "PEX-a with cold-expansion fittings (Uponor ProPEX EP)"
    _add(items, ("own", "trunk"), f"{pex}, {p[u + 'trunk_in']:g} in.: each flat's hot trunk from its own heater", "ft", _q(OWN_HEATER, trunk),
         "flat_hot_rule", "rule", "hot")
    _add(items, ("own", "drops"), f"{pex}, {p[u + 'drop_in']:g} in.: each flat's hot fixtures' pipe from its trunk", "ft", _q(OWN_HEATER, drops),
         "flat_hot_rule", "rule", "hot")
    _add(items, ("own", "trunk insulation"), f"insulation {p[u + 'trunk_insulation_in']:g} in. (R-3) on each flat's hot trunk "
         "(IECC R403.5.2)", "ft", _q(OWN_HEATER, trunk), "flat_hot_rule", "rule", "hot")
    _add(items, ("own", "heater electric"), f"electric water heater, {p[u + 'heater_gal']:g} gal, {p[u + 'heater_va']:g} W at 208 V, in each flat's utility closet "
         "(A. O. Smith ENT-50, basis of design)", "each", _q(("electric",), flats), "baseline.usual.heater_* (RECS 2020; A. O. Smith)", "rule", "hot")
    _add(items, ("own", "heater gas"), f"gas water heater, {p[u + 'gas_heater_gal']:g} gal, power direct vent, in each flat's utility closet "
         "(Rheem PROG40-40N RH67 PDV, basis of design)", "each", _q(("gas",), flats), "baseline.usual.gas_heater_* (RECS 2020; Rheem)", "rule", "hot")
    _add(items, ("own", "expansion"), "thermal expansion tank on each flat's heater (IPC 607.3)", "each", _q(OWN_HEATER, flats),
         "IPC 2021 607.3", "rule", "hot")
    _add(items, ("own", "heater circuit"), "NM-B cable, copper, 10 AWG: each flat's water heater circuit (30 A, 208 V)", "ft",
         _q(("electric",), sum(dryer.values())), "its reach the dryer's routed circuit's, the same closet (a proxy)", "rule", "power")
    # Gas in the gas walk-up: a furnace with a split air conditioner in each flat, its gas, venting
    # and circuit; and gas to the central walk-up's plant.
    _add(items, ("gas", "furnace"), "gas furnace, 40,000 Btu/h, 97% AFUE, with its air conditioner's coil, in each flat (Goodman GR9S960403AN, basis of design)", "each", _q(("gas",), flats),
         "Census CHARS 2025 (Northeast: furnaces 37% of new multifamily units)", "rule", "air")
    _add(items, ("gas", "condenser"), "split air conditioner's outdoor unit, 1.5 ton, on the roof, each flat (Goodman GLXS4BA1810A, basis of design)", "each", _q(("gas",), flats),
         "in place of the mini-split's outdoor unit", "rule", "refrigerant")
    _add(items, ("gas", "furnace circuit"), "NM-B cable, copper, 14 AWG: each furnace's circuit (120 V)", "ft", _q(("gas",), sum(dryer.values())),
         "its reach the dryer's routed circuit's (a proxy)", "rule", "power")
    _add(items, ("gas", "vents"), "PVC vent and combustion-air pipe, 2 in., the furnace's and the heater's, to the facade", "ft",
         _q(("gas",), 2 * (sum(ea.values()) + sum(oa.values()))), "their reach the ERVs' ducts' to the facade (a proxy), two pipes each",
         "rule", "gas")
    _add(items, ("gas", "meters"), "gas meters, a bank by the meter wall, one a flat", "each", _q(("gas",), flats), "one a flat", "rule", "gas")
    _add(items, ("gas", "meter central"), "gas meter, the central plant's", "each", _q(("central",), 1), "one", "rule", "gas")
    _add(items, ("gas", "service"), "gas service from the street, its regulator", "each", _q(("gas", "central"), 1), "one", "rule", "gas")
    _add(items, ("gas", "lines"), "gas pipe from the meter bank to each flat", "ft", _q(("gas",), sum(feeder.values())),
         "its reach each flat's routed feeder's, from the meter wall (a proxy)", "rule", "gas")
    _add(items, ("gas", "branches"), "gas pipe in each flat, to its furnace and its heater", "ft", _q(("gas",), flats * p[u + "gas_branch_ft"]),
         "baseline.usual.gas_branch_ft", "rule", "gas")
    _add(items, ("central", "heater"), f"central gas water heater, {p[u + 'central_heater_kbtuh']:g} kBtu/h, {p[u + 'central_heater_gal']:g} gal, condensing, in the annex "
         "(A. O. Smith Cyclone FLEX BTH-120, basis of design)", "each", _q(("central",), 1),
         "RECS 2020 (a shared water heater in 65% of the Northeast's newer apartments in 5+ unit buildings)", "rule", "hot")
    _add(items, ("central", "vent"), "the central heater's vent and combustion air, through the annex's wall", "each", _q(("central",), 1),
         "one", "rule", "gas")
    # Ventilation, exhaust only: the bath fan running at the flat's rate, the kitchen's hood vented
    # outdoors, each in its own duct to a wall cap.
    _add(items, ("vent", "bath fan"), f"bath exhaust fan, continuous, {p[u + 'bath_fan_cfm']:g} cfm: the flat's ventilation (Panasonic FV-0511VQ1, basis of design)", "each",
         _q(USUAL, flats), "baseline.usual.bath_fan_cfm (IMC 2021 403.3.2)", "rule", "ventilation")
    _add(items, ("vent", "bath duct"), "round galvanized steel duct, 4 in.: the bath fan to the facade", "ft", _q(USUAL, sum(ea.values())),
         "its reach the ERV's exhaust to outdoors (a proxy)", "rule", "ventilation")
    _add(items, ("vent", "hood duct"), f"round galvanized steel duct, {p[u + 'hood_duct_in']:g} in.: the over-the-range microwave's hood vented to the facade (GE JVM3162)",
         "ft", _q(USUAL, sum(oa.values())), "its reach the ERV's outdoor air (a proxy)", "rule", "ventilation")
    _add(items, ("vent", "caps"), "wall caps, the bath fan's and the hood's", "each", _q(USUAL, 2 * flats), "two a flat", "rule", "ventilation")
    return items


# ---- 10a: the usual walk-ups work ----

USUAL_HOUSE = ("stair_lights", "annex_lights", "exterior_lights", "receptacles", "fire_alarm", "telecom")


def services(apt: dict, p: dict, s7: dict) -> dict:
    """Each walk-up's service by NEC 220.84, as the engineered design's (`electrical.service`): the
    flats' appliances as chosen, the larger of heating and cooling, and the house loads; the least
    main the meter stack offers. The usual walk-ups' flats lose the ERV, and the house its plant;
    each adds its own (`baseline.usual.*_va`)."""
    from .electrical import APPLIANCES, MAINS, appliance_va
    from .loads import nec_220_84

    e, h, u = "systems.electrical.", "systems.house.", "baseline.usual."
    ft2 = apt["flats"][0]["floor_m2"] / FT2
    eng = s7["electrical"]["service"]
    base = [appliance_va(p, k) for k in APPLIANCES if k != "erv"]
    flats = {"electric": (base + [p[u + "heater_va"]], p[e + "cooling_va"], p[e + "cooling_va"]),
             # the furnace's blower is its heating; with the cooling it runs with the outdoor unit
             "gas": (base + [p[u + "gas_heater_va"]], p[u + "furnace_va"], p[u + "ac_va"] + p[u + "furnace_va"]),
             "central": (base, p[e + "cooling_va"], p[e + "cooling_va"])}
    stair = len(apt["stair"]["flights"]) + 1
    out = {"engineered": {"amps": eng["amps"], "main_a": eng["main_a"], "house_a": eng["house"]["breaker_a"], "per_unit_va": eng["flats"]["per_unit_va"]}}
    for w, (appl, heat, cool) in flats.items():
        fl = nec_220_84(len(apt["flats"]), ft2, appl, heat, cool, p)
        house = 0.0
        for k in USUAL_HOUSE:
            va = stair * p[h + "stair_luminaire_w"] if k == "stair_lights" else p[h + f"{k}_va"]
            house += va * (p[h + "continuous_factor"] if k in ("stair_lights", "exterior_lights", "fire_alarm", "telecom") else 1.0)
        if w == "central":
            house += p[h + "recirc_pump_va"] * (1 + p[h + "largest_motor_extra"]) + p[u + "central_heater_va"]
        amps = (fl["calculated_va"] + house) / (math.sqrt(3) * 208.0)
        main = next(m[0] for m in MAINS if m[0] >= amps)
        out[w] = {"amps": amps, "main_a": main, "house_va": house, "per_unit_va": fl["per_unit_va"]}
    return out


def usual_case(apt: dict, p: dict) -> dict:
    """The usual walk-up's flats for `loads.room_heat`: the code's leakage, and the code's
    ventilation air (exhaust only, made up through the envelope) with no heat recovery; the same
    walls and glass as the engineered design."""
    from .loads import CFM_M3H, ventilation

    vent = ventilation(apt, p)
    flats = {}
    for f in apt["flats"]:
        flats[f["name"]] = {"infil_m3h": p["baseline.usual.ach50"] / p["pass3.air.n_factor"] * f["interior_volume_m3"],
                            "vent_m3h": vent[f["name"]]["imc_cfm"] * CFM_M3H, "recovery": 0.0,
                            **({"wall_u": p["systems.addendum_3.wall_u"]} if apt.get("continuous_insulation_m", 0.0) > 0.0 else {}),
                            **({"window_u": apt["glass_u"]} if apt.get("glass_u") is not None else {})}
    return {"flats": flats, "design_c": p["systems.design.heating_c"]}


def closet_check(apt: dict, p: dict) -> dict:
    """Each flat's own equipment side by side along its utility closet: the washer and dryer's stack
    (every walk-up), the electric walk-up's heater, the gas walk-up's furnace and heater; each as deep
    as the closet allows."""
    u, r = "baseline.usual.", "systems.routing."
    rooms = [x for x in apt["rooms"]["rooms"] if x["use"] == "utility"]
    long_in = min(max(x["hi_m"][0] - x["lo_m"][0], x["hi_m"][1] - x["lo_m"][1]) for x in rooms) / 0.0254
    deep_in = min(min(x["hi_m"][0] - x["lo_m"][0], x["hi_m"][1] - x["lo_m"][1]) for x in rooms) / 0.0254
    wd = p[r + "wd_stack_w_in"]
    pieces = {"electric": [wd, p[u + "heater_dia_in"]], "gas": [wd, p[u + "furnace_w_in"], p[u + "gas_heater_dia_in"]], "central": [wd]}
    out = {w: {"need_in": sum(x) + p[u + "closet_gap_in"] * (len(x) - 1), "pieces": len(x)} for w, x in pieces.items()}
    depth = max(p[r + "wd_stack_d_in"], p[u + "furnace_d_in"], p[u + "heater_dia_in"], p[u + "gas_heater_dia_in"])
    return {"long_in": long_in, "deep_in": deep_in, "depth_in": depth, "walkups": out,
            "ok": all(v["need_in"] <= long_in for v in out.values()) and depth <= deep_in}


def hood_check(apt: dict, p: dict, routes) -> dict:
    """The vented hood's duct against GE's 140 equivalent ft: its reach the ERV's outdoor air's (the
    proxy), its wall cap 40 ft and each of that route's bends 10."""
    u = "baseline.usual."
    out = {}
    for f in apt["flats"]:
        t = routes.tree(f"hvac/erv-oa/{f['name']}")
        out[f["name"]] = t.length_m / FT + 40.0 + 10.0 * sum(e.bends for e in t.edges)
    worst = max(out, key=out.get)
    return {"flats": out, "worst": worst, "ok": out[worst] <= p[u + "hood_max_eq_ft"]}


def central_check(p: dict, s7: dict) -> dict:
    """The central walk-up's gas heater against the design day's peak hour (Ecosizer's 'Stream'
    shape on the design's day, `plumbing.load_shape`): its recovery at the storage's rise and its
    usable storage, against the peak hour's draw at the storage's temperature and the loops' loss."""
    from .plumbing import RHO_CP, load_shape

    u, h = "baseline.usual.", "systems.hot_water."
    w = s7["water"]
    storage_f, supply_f, inlet_f = p[h + "storage_f"], p[h + "distribution_f"], w["inlet_f"]
    peak = w["day_gal"] * float(load_shape().max()) * (supply_f - inlet_f) / (storage_f - inlet_f)
    loss = w["loop"]["loss_btuh"] / (RHO_CP * (storage_f - inlet_f))
    give = p[u + "central_recovery_gph"] * 100.0 / (storage_f - inlet_f) + p[u + "central_usable"] * p[u + "central_heater_gal"]
    return {"peak_gal": peak, "loss_gph": loss, "give_gal": give, "ok": give >= peak + loss}


def heat_check(apt: dict, p: dict, s7: dict) -> dict:
    """Each usual flat's design heat (the code's leakage, no heat recovery) against its heat pump's
    capacity at the design dry bulb with its line set (`fallback.space_heat`, the same unit). The
    exhaust fan's air and the leakage are added (`room_ua`), an upper bound: an unbalanced fan and
    the envelope's leakage partly overlap, and how much needs a source (10c)."""
    from . import fallback, routing
    from .loads import room_heat

    sh = fallback.space_heat(apt, p, s7, routing.placements(apt, p))
    load = room_heat(apt, p, usual_case(apt, p))
    rows = {n: {"load_w": load[n]["design_w"], "capacity_w": sh["flats"][n]["capacity_w"], "engineered_w": sh["flats"][n]["load_w"]}
            for n in sh["flats"]}
    worst = min(rows, key=lambda n: rows[n]["capacity_w"] - rows[n]["load_w"])
    return {"flats": rows, "worst": worst, "ok": all(r["capacity_w"] >= r["load_w"] for r in rows.values()),
            "building_kw": sum(r["load_w"] for r in rows.values()) / 1e3, "engineered_kw": sum(r["engineered_w"] for r in rows.values()) / 1e3}


# ---- 10a: the run ----

def items(apt: dict, p: dict, s7: dict, routes, its: list[dict]) -> dict:
    from .servicesifc import read_back

    rb = read_back(SERVICES)
    model, seen = model_items(rb)
    rule = flat_hot_rule(apt, p, routes)
    out = {**model, **insulation_items(model, p), **design_items(apt, p, s7, its), **usual_items(apt, p, routes, rule)}
    return {"items": list(out.values()), "seen": seen, "rule": rule}


def checks(r: dict, p: dict) -> list[tuple[str, bool, str]]:
    import csv

    seen, its = r["seen"], r["items"]
    sched = PUBLISHED / "services-addendum-7"
    with open(sched / "lengths.csv", encoding="utf-8") as fh:
        sched_ft = sum(float(x["ft"]) for x in csv.DictReader(fh))
    with open(sched / "fittings.csv", encoding="utf-8") as fh:
        sched_fit = sum(int(x["count"]) for x in csv.DictReader(fh))
    sched_rows = {}
    for k, name in (("equipment", "equipment"), ("fixtures", "fixtures"), ("sprinklers", "sprinklers"), ("air_terminals", "air_terminals"),
                    ("switches", "switches")):
        with open(sched / f"{name}.csv", encoding="utf-8") as fh:
            sched_rows[k] = sum(1 for _ in csv.DictReader(fh))
    model = [it for it in its if it["kind"] == "model"]
    counted_ft = sum(it["qty"]["engineered"] for it in model if it["unit"] == "ft")
    counted_fit = sum(it["qty"]["engineered"] for it in model if it["id"].startswith("fit |"))
    untraced = [it["id"] for it in its if not it["basis"] or it["kind"] not in ("model", "design", "rule")]
    empty = [it["id"] for it in its if not any(it["qty"].values())]
    rc, hc, sv, rule = r["practice"]["recs_check"], r["heat"], r["services"], r["rule"]
    cl, hd, ce = r["closet"], r["hood"], r["central"]
    far = max(rule, key=lambda n: rule[n]["longest_ft"])
    c = r["practice"]["census"]
    sys_sum = {f: sum(v[f] for v in c["systems"].values()) for f in ("gas", "electricity")}
    return [
        ("the RECS microdata's weights reproduce EIA's HC8.1 (apartments in 5+ unit buildings, main water heater fuel)",
         all(abs(v["ours_m"] - v["eia_m"]) < 0.006 for v in rc.values()),
         "; ".join(f"{k} {v['ours_m']:.2f} M against {v['eia_m']:.2f}" for k, v in rc.items())),
        ("its jackknife reproduces HC8.1's published errors", all(abs(v["ours_rse"] - v["eia_rse"]) < 0.01 for v in rc.values()),
         "; ".join(f"{k} RSE {v['ours_rse']:.2f}% against {v['eia_rse']:.2f}" for k, v in rc.items())),
        ("Census's heating systems add up to its heating fuels (Northeast, 2025, thousands, rounded)",
         c["fuel"] is not None and all(abs(sys_sum[f] - c["fuel"][f]) <= 2 for f in sys_sum),
         f"gas {sys_sum['gas']:g} against {c['fuel']['gas']:g}, electricity {sys_sum['electricity']:g} against {c['fuel']['electricity']:g}"),
        ("the services model counted once: its runs' lengths are its schedule's", abs(counted_ft - sched_ft) < 0.5 and abs(seen["ft"] - sched_ft) < 0.5,
         f"{counted_ft:,.1f} ft against lengths.csv's {sched_ft:,.1f}"),
        ("its fittings and its elements are its schedules'", counted_fit == sched_fit == seen["fittings"]
         and all(seen[k] == n for k, n in sched_rows.items()),
         f"{counted_fit:,.0f} fittings against {sched_fit:,}; " + ", ".join(f"{k} {seen[k]} against {n}" for k, n in sched_rows.items())),
        ("every item traces to a model element, a design parameter or a stated rule, and has a quantity", not untraced and not empty,
         f"{len(its)} items" + (f"; untraced {untraced[:4]}" if untraced else "") + (f"; empty {empty[:4]}" if empty else "")),
        ("each usual flat's heat pump carries its own heat at the code's leakage with no heat recovery (the fan's air and the "
         "leakage added, an upper bound)", hc["ok"],
         f"least spare {hc['worst']}: {hc['flats'][hc['worst']]['capacity_w']:,.0f} W against {hc['flats'][hc['worst']]['load_w']:,.0f} "
         f"(the building at most {hc['building_kw']:.1f} kW against the engineered design's {hc['engineered_kw']:.1f})"),
        ("each usual flat's own hot pipe within IPC 607.2", rule[far]["longest_ft"] <= p["baseline.usual.ipc_607_2_ft"],
         f"longest {rule[far]['longest_ft']:.1f} ft ({far}, to its {rule[far]['farthest']}) against {p['baseline.usual.ipc_607_2_ft']:g}"),
        ("each walk-up's service on a main the meter stack offers (NEC 220.84)", all(v["amps"] <= v["main_a"] for v in sv.values()),
         "; ".join(f"{w} {v['amps']:.0f} A on {v['main_a']}" for w, v in sv.items())),
        ("each flat's own equipment fits along its utility closet", cl["ok"],
         "; ".join(f"{w} {v['need_in']:.1f} in." for w, v in cl["walkups"].items()) + f" along {cl['long_in']:.1f}; "
         f"{cl['depth_in']:g} in. deep in {cl['deep_in']:.1f}"),
        ("each flat's vented hood within GE's equivalent length", hd["ok"],
         f"worst {hd['worst']} {hd['flats'][hd['worst']]:.0f} ft against {p['baseline.usual.hood_max_eq_ft']:g}"),
        ("the central walk-up's gas heater covers the design day's peak hour and the loops' loss", ce["ok"],
         f"{ce['give_gal']:.0f} gal in its first hour against {ce['peak_gal']:.0f} drawn and {ce['loss_gph']:.0f} to the loops"),
    ]


def run(apt: dict | None = None, p: dict | None = None) -> dict:
    """10a: the usual walk-ups from sources, both item lists, their checks; written to
    `out/pass3/baseline.json` and `.md`."""
    from . import acceptance, routed, systems
    from .params import load_params, values

    p = p or values(load_params())
    apt = apt or systems.load(systems.latest_model())
    routes = routed.load(apt, p)
    if routes is None or not routes.fresh:
        raise SystemExit("no fresh routes for the latest model: `brownfield routes` first")
    s7 = routed.summary(apt, p, routes)
    its = acceptance.items(p, s7)
    r = items(apt, p, s7, routes, its)
    r["practice"] = usual_practice()
    r["heat"] = heat_check(apt, p, s7)
    r["closet"], r["hood"], r["central"] = closet_check(apt, p), hood_check(apt, p, routes), central_check(p, s7)
    r["services"] = services(apt, p, s7)
    for w, v in r["services"].items():  # each walk-up's service main (the meter stack's main module and its copper)
        r["items"].append({"id": f"electrical | service | {w}", "system": "power", "what": f"the service's main, {v['main_a']} A, and its copper "
                           "(NEC 220.84)", "unit": "each", "qty": _q((w,), 1), "basis": "baseline.services (electrical.service's method)",
                           "kind": "design" if w == "engineered" else "rule", "main_a": v["main_a"]})
    r["checks"] = checks(r, p)
    out = OUT_DIR / "pass3"
    (out / "baseline.json").write_text(json.dumps({k: r[k] for k in ("items", "heat", "services", "rule", "closet", "hood", "central", "checks")}, indent=1, default=str) + "\n",
                                       encoding="utf-8")
    (out / "baseline.md").write_text(report(r) + "\n", encoding="utf-8")
    r["written"] = [out / "baseline.json", out / "baseline.md", r["practice"]["derived"]]
    return r


def report(r: dict) -> str:
    from .systems import report as fmt

    c, ne, us = r["practice"]["census"], r["practice"]["recs_ne"], r["practice"]["recs_us"]
    tot = c["fuel"]["total"]
    lines = ["Pass 3g step 10a: the usual walk-up, and what each walk-up has", "", fmt(r["checks"]), "",
             f"New multifamily units completed in the {c['region']}, {c['year']} (Census CHARS; {tot:g} thousand):"]
    for s_, v in c["systems"].items():
        lines.append(f"  {s_.replace('_', ' ')}: {v['total']:g} thousand ({100 * v['total'] / tot:.0f}%): gas {v['gas']:g}, "
                     f"electricity {v['electricity']:g}, other {v['other']:g}")
    for g in (us, ne):
        lines += ["", f"Apartments in 5+ unit buildings built 2010-2020, {g['region']} (RECS 2020; {g['records']} records, "
                      f"{g['units_k']:,.0f} thousand units):"]
        lines += [f"  {k}: {100 * e:.1f}% (+-{100 * s:.1f})" for k, (e, s) in g["shares"].items()]
    lines += ["", "The walk-ups:", *(f"  {w}: {NAMES[w]}" for w in WALKUPS), "",
              f"{'item':96s} {'unit':6s} " + " ".join(f"{w:>11s}" for w in WALKUPS)]
    for it in sorted(r["items"], key=lambda x: (x["system"], x["id"])):
        q = it["qty"]
        lines.append(f"{it['what'][:96]:96s} {it['unit']:6s} " + " ".join(f"{q[w]:11,.1f}" if q[w] else f"{'-':>11s}" for w in WALKUPS))
    return "\n".join(lines)
