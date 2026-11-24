"""Pass 3g step 10g (D28): which of the engineered design's choices pay their way (`brownfield choices`).

10f set the engineered design against the usual walk-ups as a whole: over 20 years it costs about
$29,000 a flat more than the all-electric one. 10g takes that difference apart by choice.

- **Each choice taken out** of the engineered design, one at a time, the rest as designed, the
  all-electric walk-up's way in its place (`CHOICES`). What the 20-year cost falls by is what the
  choice costs net of what it saves. Its cost up front, its replacements and its upkeep are its
  lines' (10b's prices by `pricing.purpose`, 10f's `ranges.wear`). Its running cost is the energy
  model's with the choice's switch flipped (`energy.config_rows`): the flats' ventilation and
  leakage, where the space heat and the hot water come from, the PV.
- **The choices interact** where they share the heat. The ERVs and the airtightness save heat the
  floors take free from the data center; the house meter's rate class turns on the plant and the
  solar panels together. So the choices one at a time don't add up to the whole: the rest is its own line.
  Three of them are also measured added to the usual all-electric walk-up alone (`ADDED`), where
  the heat they save is the heat pump's.
- **The plant against central gas hot water** too, the cheapest usual walk-up's way (10f).
- **The two that take the data center's water,** the floors and the plant, taken out together:
  their controls go too, and the heat network's share (pass 3 §4) beside the systems.
- **The engineering's fee** on its own line: it buys the design, not a system.
- **What each buys** besides money, from 10c's and 10d's runs: decibels, outdoor air, floor
  temperatures, the heat used.

Then each figure's P10/P50/P90 over 10f's draws (the same seed and count, so draw for draw the same
inputs; the whole matches 10f's saved draws), the share of draws in which each choice pays, and
whether each keeps its sign from P10 to P90.
"""

from __future__ import annotations

import json

import numpy as np

from . import OUT_DIR
from .energy import NL

CASES = ("engineered", "engineered at the code's leakage", "usual", "usual at Phius's leakage")  # every `energy.cases`
GAS = "gas: its service lines, meters, piping and vents"
MAIN = "the electrical service's main"
# Each choice: its key, what it is, its lines' purpose (`pricing.purpose`), and the usual all-electric
# walk-up's way in its place.
CHOICES = (
    ("radiant", "the floors heated by the data center's water", "space heat from the data center's water",
     "the mini-splits heat, as they do in the fallback"),
    ("plant", "the hot-water plant and the flats' loops", "hot water: the plant and the loops, or each flat's heater",
     "a 50 gal electric water heater in each flat"),
    ("erv", "an ERV and its preheater in each flat", "ventilation: the ERVs, or the bath fans and hoods",
     "a bath fan running all year and a vented hood"),
    ("tight", "airtightness to Phius, and its tests", "airtightness to Phius", "the code's 3.0 ACH50"),
    ("pv", "solar panels on the house meter", "PV", "none"),  # the purpose keeps 10b's word
    ("cast iron", "cast-iron drains and vents", "drains and vents: cast iron, or PVC", "PVC"),
    ("services", "the water and fire services apart, the fire's supervised", "the water and fire services: apart and supervised, or one",
     "one service for both"),
    ("submeters", "a water submeter in each flat", "the flats' water submeters", "none"),
    ("held off", "the water pipes held off the frame (Addendum 9)", "the water pipes held off the frame, for quiet",
     "the pipes held rigid to the frame"),
    ("prv", "a pressure-reducing valve on the service", "the pressure-reducing valve, for quiet", "the street's pressure"),
    ("cold insulation", "the cold risers' insulation", "the cold risers' insulation, against condensation", "none"),
)
KEYS = tuple(c[0] for c in CHOICES)
NAME = {c[0]: c[1] for c in CHOICES}
OWNER = {c[2]: c[0] for c in CHOICES}  # a purpose's choice
ENERGY = ("radiant", "plant", "erv", "tight", "pv")  # the choices that flip a switch in `energy.CONFIGS`
ADDED = ("erv", "tight", "pv")  # also measured added to the usual walk-up
FEE = "engineering"
FULL = frozenset(KEYS + (FEE,))
NONE: frozenset = frozenset()
DC = frozenset(("radiant", "plant"))
ZERO = {"upkeep": 0.0, "replace": 0.0}
LEAKAGE = {(True, True): "engineered", (True, False): "engineered at the code's leakage",
           (False, True): "usual at Phius's leakage", (False, False): "usual"}  # (has the ERV, airtight)


def config(have: frozenset, hw_else: str = "electric") -> dict:
    """The energy model's switches (`energy.CONFIGS`'s shape) for a walk-up with the choices `have`;
    `hw_else` its hot water without the plant ("electric", or "central")."""
    return {"case": LEAKAGE[("erv" in have, "tight" in have)], "heat": "dc" if "radiant" in have else "hp",
            "hw": "plant" if "plant" in have else hw_else, "pv": "pv" in have}


def source(why: str, have: frozenset, hw_else: str = "electric") -> str:
    """Which walk-up's lines a purpose takes in a walk-up with the choices `have`: the engineered
    design's for a choice it has; the central walk-up's hot water and gas when that stands in for
    the plant; else the all-electric walk-up's (alike in the two where no choice owns it). The
    service's main is the central walk-up's 400 A only with neither the plant nor the ERVs: the
    flats' ERVs and preheaters on its house keep 600 A (`main_check`)."""
    c = OWNER.get(why)
    if c is not None and c in have:
        return "engineered"
    if hw_else != "electric" and "plant" not in have and (c == "plant" or why == GAS or (why == MAIN and "erv" not in have)):
        return hw_else
    return "electric"


def main_check(r10: dict) -> dict:
    """The main the plant's line against central gas keeps: the engineered flats by NEC 220.84
    (their ERVs and preheaters, `electrical.service`) on the central walk-up's house loads (10a's
    `baseline.services`), against the main the meter stack offers."""
    import math

    from .electrical import MAINS

    flats = r10["s7"]["electrical"]["service"]["flats"]["calculated_va"]
    amps = (flats + r10["services"]["central"]["house_va"]) / (math.sqrt(3) * 208.0)
    return {"amps": amps, "main_a": next(m[0] for m in MAINS if m[0] >= amps), "engineered_a": r10["services"]["engineered"]["main_a"],
            "central_a": r10["services"]["central"]["main_a"]}


# ---- the flats' feeders ----
# 10a gives every walk-up the engineered design's feeders (routed, sized at its flats' load: step 7).
# A walk-up designed before bidding (with the fee) holds the design's drop limit at its own flats'
# load: where they carry more (their own water heater), a feeder that would drop more is upsized as
# `electrical.feeders` sizes it, never down. Sized at the central inputs, as step 7 sizes the
# engineered design's: the draws price them, not resize them. The usual walk-ups keep the engineered
# design's (`quality.wiring` checks them within the NEC's informational 3%).
FEEDER_CLASS = {"3": "feeder_1", "2": "feeder_1.25", "1": "feeder_1.25_1awg"}  # by the conductors' size (`pricing.CLASSES`)
KINDS = tuple((erv, heater, radiant) for erv in (True, False) for heater in (True, False) for radiant in (True, False))
ENGINEERED_FLAT = (True, False, True)  # the ERV, no water heater of its own, the floors' manifold


def flat_kind(have: frozenset, hw_else: str = "electric") -> tuple[bool, bool, bool]:
    """What a walk-up's flats carry on their feeders: the ERV and its preheater, their own water
    heater, the floors' manifold controls (on the ERV's circuit)."""
    return "erv" in have, "plant" not in have and hw_else == "electric", "radiant" in have


def flat_load(p: dict, ft2: float, kind: tuple[bool, bool, bool]) -> tuple[dict, float]:
    """A flat's feeder load by 220.82 (`electrical.flat_load`'s way) for what it carries, and its
    heating-or-cooling load."""
    from .electrical import APPLIANCES, appliance_va, hvac_va
    from .loads import nec_220_82

    e = "systems.electrical."
    erv, heater, radiant = kind
    appl = [appliance_va(p, k) for k in APPLIANCES if k != "erv"]
    if erv:
        appl.append(p[e + "erv_va"] + (p[e + "manifold_controls_va"] if radiant else 0.0))
    if heater:
        appl.append(p["baseline.usual.heater_va"])
    hvac = hvac_va(p, p[e + "heat_demand_220_82"]) if erv else p[e + "cooling_va"]
    return nec_220_82(ft2, appl, hvac, p), hvac


def feeder_sizes(apt: dict, p: dict, s7: dict, kind: tuple[bool, bool, bool]) -> dict[str, dict]:
    """Each flat's feeder for flats that carry `kind`, as `electrical.feeders` sizes it (the breaker by
    the load; the conductors by the breaker's 83% and the load, then larger until the drop is within
    the design's limit), from the engineered design's size up, on its routed length."""
    from .baseline import FT2
    from .electrical import FEEDER_CONDUIT, FEEDER_METAL, FLAT_SYSTEM, SIZES, ampacity, feeder_drop, impedance, next_standard, split_load

    w = "systems.wiring."
    out = {}
    for f in apt["flats"]:
        fd = s7["electrical"]["feeders"][f["name"]]
        ld, hvac = flat_load(p, f["floor_m2"] / FT2, kind)
        va_ll, va_ln = split_load(p, ld["calculated_va"], hvac)
        z0 = feeder_drop(complex(0.0, 0.0), 0.0, va_ll, va_ln, va_ln, p[w + "pf"], FLAT_SYSTEM)
        amps = max(z0["ia"], z0["ib"])
        breaker = max(next_standard(amps, p), p[w + "feeder_min_a"])
        least = max(amps, p[w + "feeder_83_fraction"] * breaker if 100 <= breaker <= 400 else breaker)
        i = SIZES.index(fd["size"])
        while ampacity(SIZES[i], FEEDER_METAL, 75) < least - 1e-9:
            i += 1
        while True:
            d = feeder_drop(impedance(SIZES[i], FEEDER_METAL, FEEDER_CONDUIT), fd["ft"], va_ll, va_ln, va_ln, p[w + "pf"], FLAT_SYSTEM)
            if max(d["ll"], d["an"], d["bn"]) <= p[w + "vd_feeder_max"] + 1e-12:
                break
            i += 1
        out[f["name"]] = {"ft": fd["ft"], "from": fd["size"], "to": SIZES[i], "amps": amps, "breaker_a": breaker, "from_breaker_a": fd["breaker_a"],
                          "least_a": least, "ampacity": ampacity(SIZES[i], FEEDER_METAL, 75), "drop": max(d["ll"], d["an"], d["bn"])}
    return out


def prepare(r10: dict, apt: dict, p: dict) -> dict:
    """`ranges.prepare`'s, and each kind of flat's feeders at the central inputs `p` (`feeder_sizes`)."""
    from .ranges import prepare as fixed

    fx = fixed(r10, apt, p)
    fx["feeders"] = {kind: feeder_sizes(apt, p, fx["s7"], kind) for kind in KINDS}
    return fx


def upsizing(sizes: dict[str, dict], p: dict) -> float:
    """What upsizing the feeders `sizes` (`feeder_sizes`) adds, the building's (USD): each upsized
    feeder's length at its new class's installed price less its old's."""
    from .pricing import installed

    return sum((installed(FEEDER_CLASS[v["to"]], p) - installed(FEEDER_CLASS[v["from"]], p)) * v["ft"] for v in sizes.values() if v["to"] != v["from"])


def walkups(fx: dict, p: dict, sp: dict | None = None, hw: dict | None = None):
    """A walk-up by its choices on inputs `p`: `walkup(have, hw_else)` gives its cost a flat (up front,
    replacements, running and upkeep a year, and over the years counted) and its energy, memoized.
    Shared by 10g and 10h (`quality.py`). Returns (walkup, sp, hw, the annuity, the network shares)."""
    from . import energy, pricing
    from .cost import annuity
    from .ranges import wear

    apt, s7, n = fx["apt"], fx["s7"], fx["n"]
    pr = pricing.price(fx["items"], p)
    fee = pricing.fee(p, n)["extra_flat_usd"]
    nw = pricing.network_share(p, s7, n, fx["floor_m2"])
    sp = sp if sp is not None else energy.space(apt, p, fx["wx"], only=CASES)
    hw = hw if hw is not None else energy.hot_water(apt, p, s7)
    bp, wr = pricing.by_purpose(pr), wear(pr, p, n)
    a_T = annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    memo: dict = {}

    def walkup(have: frozenset, hw_else: str = "electric") -> dict:
        key = (have, hw_else)
        if key not in memo:
            cfg = config(have, hw_else)
            rows = energy.config_rows(apt, p, s7, sp, hw, cfg, "x")
            c = energy.costs(rows, p, n, {"x": energy.config_demand(apt, p, s7, cfg)}, walkups=("x",))["x"]
            up = rep = upk = 0.0
            for why, usd in bp.items():
                src = source(why, have, hw_else)
                up += usd[src] / n
                part = wr[src]["purpose"].get(why, ZERO)
                rep, upk = rep + part["replace"], upk + part["upkeep"]
            up += fee if FEE in have else 0.0
            feeders = upsizing(fx["feeders"][flat_kind(have, hw_else)], p) / n if FEE in have else 0.0
            up += feeders
            m = c["meters"]
            run = c["total"] / n
            memo[key] = {"up": up, "feeders": feeders, "replace": rep, "running": run, "upkeep": upk, "life": up + rep + (run + upk) * a_T,
                         "kwh": (m["flats"] + m["house"] + m["pv"]) / n, "heat_mwh": m["heat"] / 1000 / n,
                         "gas_kwh": (m["gas flats"] + m["gas house"]) / n}
        return memo[key]

    return walkup, sp, hw, a_T, nw


def diff(o: dict, label: str, a: dict, b: dict) -> None:
    """Walk-up `a` less walk-up `b` (`walkups`), into `o` under `label`."""
    o[f"d life {label}"] = a["life"] - b["life"]
    o[f"d up {label}"] = a["up"] - b["up"]
    o[f"d replace {label}"] = a["replace"] - b["replace"]
    o[f"d year {label}"] = (a["running"] + a["upkeep"]) - (b["running"] + b["upkeep"])
    o[f"d kwh {label}"] = a["kwh"] - b["kwh"]
    o[f"d heat {label}"] = a["heat_mwh"] - b["heat_mwh"]
    o[f"d gas {label}"] = a["gas_kwh"] - b["gas_kwh"]


def network_life(p: dict, share: dict, heat_mwh: float, a_T: float) -> float:
    """A flat's share of the heat network (`pricing.network_share`, one case) over the years counted:
    its capital, its upkeep and the network's pumping for the heat the flat takes."""
    b = "pass3.block."
    year = p[b + "om_share"] * share["flat"] + p[b + "pump_share"] * heat_mwh * p["cost.energy.elec_usd_mwh"]
    return share["flat"] + year * a_T


def evaluate(fx: dict, p: dict, sp: dict | None = None, hw: dict | None = None) -> tuple[dict, dict, dict]:
    """10g on inputs `p` (`ranges.evaluate`'s signature, for its draws and tornado): each choice's
    20-year cost taken out of the engineered design and, for `ADDED`, added to the usual walk-up; a
    flat, USD 2026. Returns (figures, sp, hw)."""
    walkup, sp, hw, a_T, nw = walkups(fx, p, sp, hw)
    o: dict[str, float] = {"annuity": a_T}
    full, none = walkup(FULL), walkup(NONE)
    o["life engineered"], o["life electric"], o["life central"] = full["life"], none["life"], walkup(NONE, "central")["life"]
    diff(o, "whole", full, none)
    for c in KEYS + (FEE,):
        diff(o, f"out {c}", full, walkup(FULL - {c}))
    o["feeders out plant"] = walkup(FULL - {"plant"})["feeders"]  # the feeders each flat's own heater would upsize
    diff(o, "out plant, central", full, walkup(FULL - {"plant"}, "central"))
    diff(o, "out dc", full, walkup(FULL - DC))
    for c in ADDED:
        diff(o, f"in {c}", walkup(frozenset({c})), none)
    o["d life interaction"] = o["d life whole"] - sum(o[f"d life out {c}"] for c in KEYS + (FEE,))
    for case, v in nw.items():
        o[f"d life out dc, network {case}"] = o["d life out dc"] + network_life(p, v, full["heat_mwh"], a_T)
    return o, sp, hw


# ---- what each choice buys besides money (central, from the runs) ----

def buys(apt: dict, p: dict, en: dict, co: dict) -> dict:
    """The facts each choice's line sets beside its cost: 10d's noise and comfort, the flats'
    leakage (ACH50) and the building's design heat under each of `energy.cases` (`loads.room_heat`:
    the floors are checked at the engineered design's, step 7, and at the code's leakage, Addendum
    8's scoping)."""
    from .energy import cases
    from .loads import CFM_M3H, room_heat

    cs = cases(apt, p)
    design_kw = {k: sum(v["design_w"] for v in room_heat(apt, p, case).values()) / 1e3 for k, (case, _) in cs.items()}
    eng = cs["engineered"][0]["flats"]
    ach = [eng[f["name"]]["infil_m3h"] * p["pass3.air.n_factor"] / CFM_M3H * 60 / (f["interior_volume_m3"] * 35.3147) for f in apt["flats"]]
    pi, b, hrs, fl, wa, wt = co["pipes"], co["bedrooms"], co["hours"], co["floors"], co["warm_air"], co["waits"]["by_walkup"]
    per = lambda k: [v[k] / v["occupants"] for v in b.values()]  # noqa: E731
    valve = p["systems.plumbing.max_static_psi"]
    from .comfort import pressure_db

    return {"design_kw": design_kw, "ach50": (min(ach), max(ach)), "code_ach50": p["baseline.usual.ach50"],
            "floors_c": (fl["min_c"], fl["max_c"]), "ashrae_c": fl["limits_c"], "erv_c": wa["erv_c"],
            "heat_h": {"engineered": p["baseline.energy.fallback_h"], "usual": hrs["usual"]["heat_h"]},
            "bed_cfm": {"engineered": (min(per("engineered_cfm")), max(per("engineered_cfm"))),
                        "usual": (min(per("usual_closed_cfm")), max(per("usual_open_cfm")))},
            "drain_dba": (pi["drain_dba"]["engineered"], pi["drain_dba"]["electric"]), "cmhc_dba": pi["limit_dba"],
            "supply_db": pi["supply_db"]["electric"] - pi["supply_db"]["engineered"], "street_psi": pi["street_psi"], "valve_psi": valve,
            "prv_db_street": pressure_db(pi["street_psi"]) - pressure_db(min(pi["street_psi"], valve)),
            "prv_db_most": pressure_db(pi["most_psi"]) - pressure_db(min(pi["most_psi"], valve)), "most_psi": pi["most_psi"],
            "tub_wait_s": (wt["engineered"]["tub"]["worst_s"], wt["electric"]["tub"]["worst_s"])}


# ---- the run ----

def pays(mc: dict[str, np.ndarray]) -> dict[str, float]:
    """The share of draws in which each line saves more than it costs over the years counted."""
    return {k.removeprefix("d life "): float((v < 0).mean()) for k, v in mc.items() if k.startswith("d life ")}


def against_10f(mc: dict[str, np.ndarray]) -> dict:
    """Draw for draw, the whole (the engineered design, the all-electric and central walk-ups over
    the years counted) against 10f's saved draws (`out/pass3/ranges_draws.npz`): the worst
    difference, USD a flat. None if 10f's draws are missing or another count."""
    path = OUT_DIR / "pass3" / "ranges_draws.npz"
    if not path.exists():
        return {"worst": None, "why": "10f's draws not found: run `brownfield baseline` first"}
    d = np.load(path)
    n = len(mc["life engineered"])
    if len(d["life engineered"]) != n:
        return {"worst": None, "why": f"10f ran {len(d['life engineered']):,} draws, these {n:,}"}
    return {"worst": float(max(np.abs(mc[k] - d[k]).max() for k in ("life engineered", "life electric", "life central"))), "why": ""}


def checks(r: dict) -> list[tuple[str, bool, str]]:
    from .ranges import PRECISION

    c, pc, tf, mn = r["central"], r["precision"], r["10f"], r["main"]
    unowned = r["unowned"]
    return [
        ("the plant's line against central gas keeps the engineered design's main: its flats' ERVs and preheaters on the central walk-up's house",
         mn["main_a"] == mn["engineered_a"], f"{mn['amps']:.0f} A on {mn['main_a']} A (the central walk-up's {mn['central_a']} A)"),
        ("every line's purpose is one choice's, or alike in the engineered and all-electric walk-ups",
         not unowned, "all" if not unowned else "; ".join(f"{k} ${v:,.0f} a flat" for k, v in unowned.items())),
        ("at every input's central value, the engineered design, the all-electric and the central walk-ups over the years counted are 10f's",
         r["parity"] < 1e-6, f"worst ${r['parity']:.2e} a flat"),
        ("draw for draw, the whole is 10f's (its saved draws)", tf["worst"] is not None and tf["worst"] < 1e-6,
         f"worst ${tf['worst']:.2e} a flat" if tf["worst"] is not None else tf["why"]),
        ("the choices one at a time, the fee and their interaction add up to the whole",
         abs(sum(c[f"d life out {k}"] for k in KEYS + (FEE,)) + c["d life interaction"] - c["d life whole"]) < 1e-6, "by construction, checked"),
        ("the draws reproduce: the first ones evaluated here, alone, give what the workers gave", r["repro"] < 1e-9, f"worst ${r['repro']:.2e} a flat"),
        (f"enough draws: each line's P10, P50 and P90 known to within {PRECISION:.1%} of its P10-P90 spread (the bootstrap's standard error)",
         pc["worst"] <= PRECISION, f"worst {pc['worst']:.1%} ({pc['which']})"),
        ("the tornado's centre is the central run", r["tornado_centre"] < 1e-9, f"worst ${r['tornado_centre']:.2e} a flat"),
    ]


def run(r10: dict, pr: dict, en: dict, co: dict, apt: dict, params: dict, n: int | None = None, seed: int | None = None,
        workers: int | None = None) -> dict:
    """10g on 10a-10d's runs: each choice centrally and over 10f's draws; written to
    `out/pass3/choices.json` and `.md`."""
    from . import pricing, ranges
    from .params import values

    n = n or ranges.DRAWS
    seed = seed or ranges.SEED
    p = values(params)
    fx = prepare(r10, apt, p)
    central, sp0, hw0 = evaluate(fx, p)
    ten, _, _ = ranges.evaluate(fx, p, sp0, hw0)
    parity = max(abs(central[k] - ten[k]) for k in ("life engineered", "life electric", "life central"))
    bp = pricing.by_purpose(pr)
    unowned = {k: (v["engineered"] - v["electric"]) / fx["n"] for k, v in bp.items() if k not in OWNER and abs(v["engineered"] - v["electric"]) > 1e-6}
    mc = ranges.monte_carlo(fx, params, n, seed, workers, fn=evaluate)
    base, vary = ranges.draws(params, n, seed)
    alone = [evaluate(fx, dict(base, **{k: float(v[i]) for k, v in vary.items()}))[0] for i in range(min(n, 2))]
    repro = max(abs(alone[i][k] - mc[k][i]) for i in range(len(alone)) for k in mc)
    s = ranges.summary(mc)
    life = {k: v for k, v in mc.items() if k.startswith("d life ")}
    out = {"central": central, "summary": s, "pays": pays(mc), "lowest": {k: float(v.min()) for k, v in life.items()},
           "highest": {k: float(v.max()) for k, v in life.items()}, "draws": n, "seed": seed, "parity": parity, "unowned": unowned,
           "repro": repro, "precision": ranges.precision(life), "10f": against_10f(mc), "buys": buys(apt, p, en, co),
           "flats": fx["n"], "varied": len(vary), "main": main_check(r10)}
    out["sign"] = {k.removeprefix("d life "): (s[k]["p10"] > 0) == (s[k]["p90"] > 0) for k in life}
    flips = tuple(f"d life {k}" for k, holds in out["sign"].items() if not holds)
    out["tornado"] = ranges.tornado(fx, params, p, flips, sp0, hw0, ranges.energy_reads(fx, p, only=CASES), fn=evaluate) if flips else {}
    again, _, _ = evaluate(fx, p, sp0, hw0)
    out["tornado_centre"] = max(abs(again[k] - central[k]) for k in central)
    out["checks"] = checks(out)
    path = OUT_DIR / "pass3"
    (path / "choices.json").write_text(json.dumps(out, indent=1, default=float) + NL, encoding="utf-8")
    np.savez_compressed(path / "choices_draws.npz", **mc)
    (path / "choices.md").write_text(report(out, p) + NL, encoding="utf-8")
    out["mc"] = mc
    out["written"] = [path / "choices.json", path / "choices_draws.npz", path / "choices.md"]
    return out


# ---- the report ----

def _usd(x: float) -> str:
    return f"{'-' if x < -0.5 else ''}${abs(x):,.0f}"


LINES = tuple((f"out {k}", NAME[k]) for k in KEYS) + (
    (f"out {FEE}", "the engineering's fee (the design before bidding)"),
    ("interaction", "how the choices interact (the whole less the lines above)"),
)
OTHER = (("whole", "the whole: the engineered design less the all-electric walk-up"),
         ("out plant, central", "the plant and loops, against one gas heater for the building (the central walk-up's way)"),
         ("out dc", "the two on the data center's water, the floors and the plant, together"),
         ("out dc, network dense", "  with the heat network's share, dense (pass 3 §4)"),
         ("out dc, network base", "  with the heat network's share, base"),
         *((f"in {k}", f"{NAME[k]}, added to the usual all-electric walk-up") for k in ADDED))


def what_it_buys(key: str, r: dict, p: dict) -> str:
    """A line's facts besides money, plain."""
    b, c = r["buys"], r["central"]
    kwh = lambda k: -c[f"d kwh {k}"]  # noqa: E731  the electricity a choice saves a flat a year

    def elec(k: str) -> str:
        v = kwh(k)
        return f"it saves {v:,.0f} kWh of electricity a year" if v >= 0 else f"it uses {-v:,.0f} kWh more electricity a year"
    dk = b["design_kw"]
    if key == "out radiant":
        return (f"floors at {b['floors_c'][0]:.1f}-{b['floors_c'][1]:.1f} C at the design hour (ASHRAE 55: {b['ashrae_c'][0]:g}-{b['ashrae_c'][1]:g}); "
                f"the outdoor units heat only in the fallback ({b['heat_h']['engineered']:,.0f} h a year, against {b['heat_h']['usual']:,.0f}); "
                f"{c['d heat out radiant']:.1f} MWh of the data center's heat a year, and {elec('out radiant')}, net of the floors' pump")
    if key == "out plant":
        return (f"{c['d heat out plant']:.1f} MWh of the data center's heat a year, and {elec('out plant')}, net of the plant's own; no heater in each "
                f"flat's closet, whose load would take {_usd(c['feeders out plant'])} a flat of larger feeders (10h). Against it: the tub's worst "
                f"wait {b['tub_wait_s'][0]:.0f} s, against {b['tub_wait_s'][1]:.0f} s from a flat's own heater")
    if key == "out erv":
        e, u = b["bed_cfm"]["engineered"], b["bed_cfm"]["usual"]
        return (f"outdoor air to every bedroom, {e[0]:.1f}-{e[1]:.1f} cfm a person by duct at {b['erv_c']:.1f} C or more, against {u[0]:.1f}-{u[1]:.1f} "
                f"through the walls at the outdoor temperature. With the floors on the data center's water, the heat it saves is free, "
                f"and {elec('out erv')}")
    if key == "out tight":
        code = dk["engineered at the code's leakage"]
        return (f"{b['ach50'][0]:.2f}-{b['ach50'][1]:.2f} ACH50, against {b['code_ach50']:g}; the floors' heat at the design hour "
                f"{dk['engineered']:.1f} kW for the building, against {code:.1f}; "
                f"the heat it saves is free here, and {elec('out tight')}")
    if key == "out pv":
        return f"{kwh('out pv'):,.0f} kWh a flat a year on the house meter"
    if key == "out cast iron":
        return f"a neighbour's flush at {b['drain_dba'][0]:g} dBA, against {b['drain_dba'][1]:g} (CMHC's limit {b['cmhc_dba']:g})"
    if key == "out services":
        return "the sprinklers' water on a service of its own, its valves supervised and its alarms sent to a monitoring station (903.4)"
    if key == "out submeters":
        return "each flat billed for the water it uses (the saving in use isn't modelled)"
    if key == "out held off":
        return f"supply pipes {b['supply_db']:.1f} dB quieter at the street's {b['street_psi']:g} psi"
    if key == "out prv":
        return (f"{b['prv_db_street']:.1f} dB at the street's {b['street_psi']:g} psi, under the valve's {b['valve_psi']:g}; "
                f"{b['prv_db_most']:.1f} dB if the street were at the code's {b['most_psi']:g}")
    if key == "out cold insulation":
        return "no condensation on the cold risers"
    if key == f"out {FEE}":
        return "the design exists before bidding; what it found is in the report"
    return ""


def report(r: dict, p: dict) -> str:
    from .systems import report as fmt

    c, s, py, sg = r["central"], r["summary"], r["pays"], r["sign"]
    a_T = c["annuity"]
    lines = ["Pass 3g step 10g: which of the engineered design's choices pay their way", "", fmt(r["checks"]), "",
             f"Each choice taken out of the engineered design, one at a time, the rest as designed, the all-electric walk-up's way in "
             f"its place. A flat, USD 2026, over {p['cost.money.life_yr']:g} years at {p['cost.money.discount']:.0%} (x{a_T:.2f} a year's cost). "
             f"Positive: the choice costs more than it saves. {r['draws']:,} draws of {r['varied']} inputs (seed {r['seed']}, 10f's).", ""]
    w = max(len(label) for label in dict(LINES + OTHER).values())
    head = f"{'':{w}s} {'up front':>9s} {'a year':>7s} {'repl.':>7s} {'20 years':>9s} {'a month':>8s}  {'P50 (P10 to P90)':>28s} {'pays':>6s}"
    lines.append(head)

    def row(k: str, label: str) -> str:
        x = s[f"d life {k}"]
        up = c.get(f"d up {k}")
        cols = (f"{_usd(up):>9s} {_usd(c[f'd year {k}']):>7s} {_usd(c[f'd replace {k}']):>7s}" if up is not None else f"{'':>9s} {'':>7s} {'':>7s}")
        band = f"{_usd(x['p50'])} ({_usd(x['p10'])} to {_usd(x['p90'])})"
        flag = "" if sg[k] else "  SIGN FLIPS"
        return f"{label:{w}s} {cols} {_usd(c[f'd life {k}']):>9s} {_usd(c[f'd life {k}'] / a_T / 12):>8s}  {band:>28s} {py[k]:6.1%}{flag}"

    for k, label in LINES:
        lines.append(row(k, label))
    lines.append("")
    for k, label in OTHER:
        lines.append(row(k, label))
    lines += ["", "What each buys besides money:"]
    lines += [f"  {label}: {what_it_buys(k, r, p)}" for k, label in LINES if what_it_buys(k, r, p)]
    dk = r["buys"]["design_kw"]
    lines += ["", "The building's heat at the design hour (loads.room_heat), kW: " + "; ".join(f"{k} {v:.1f}" for k, v in dk.items()),
              "  the floors are checked at the engineered design's (step 7) and at the code's leakage (Addendum 8's scoping); "
              "taken out, the ERVs would leave the floors more than either"]
    for k, rows in r["tornado"].items():
        lines += ["", f"{k.removeprefix('d life ')} keeps no sign from P10 to P90. What moves it most (central {_usd(c[k])}; "
                      "each input low -> high, the rest central):"]
        lines += [f"  {name}: {_usd(lo)} -> {_usd(hi)}" for name, lo, hi in rows[:12]]
    lines += ["", "The lowest and highest draw of each line over the years counted:"]
    lines += [f"  {k}: {_usd(r['lowest'][f'd life {k}'])} to {_usd(r['highest'][f'd life {k}'])}" for k in sg]
    return NL.join(lines)


# ---- the figure ----

def figure(r: dict, path) -> None:
    """Each choice's net cost over the years counted, a flat: the typical draw (P50) as a bar from
    zero, P10-P90 as a line; sorted, largest first; the fee and the interaction below. A static PNG
    for the report, light mode."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    from .figures import GRID, INK, INK2, MUTED, SERIES, SURFACE

    s = r["summary"]
    keys = sorted((f"out {k}" for k in KEYS), key=lambda k: -s[f"d life {k}"]["p50"]) + [f"out {FEE}", "interaction"]
    label = dict(LINES)
    short = {"out services": "the water and fire services apart", "interaction": "how the choices interact",
             f"out {FEE}": "the engineering's fee", "out held off": "the water pipes held off the frame"}
    ys = list(range(len(keys)))
    ys = [y + (0.6 if k in (f"out {FEE}", "interaction") else 0) for y, k in zip(ys, keys)]
    lo = min(min(s[f"d life {k}"]["p10"] for k in keys), 0.0)
    hi = max(s[f"d life {k}"]["p90"] for k in keys)
    xmin, xmax = lo - 0.04 * (hi - lo), hi * 1.32
    dpi, bar_px, end_px = 150, 16, 4
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=dpi, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ys[-1] + 0.7, -0.7)
    fig.subplots_adjust(left=0.31, right=0.985, top=0.835, bottom=0.12)
    fig.canvas.draw()
    bb = ax.get_window_extent()
    px_x, px_y = bb.width / (xmax - xmin), bb.height / (ys[-1] + 1.4)
    h = bar_px / px_y
    for y, k in zip(ys, keys):
        x = s[f"d life {k}"]
        v = x["p50"]
        rx = min(end_px / px_x, abs(v) / 2) if v else 0.0
        if abs(v) > 0:
            left = min(0.0, v)
            ax.add_patch(FancyBboxPatch((left, y - h / 2), abs(v), h, boxstyle=f"round,pad=0,rounding_size={rx}", mutation_aspect=px_x / px_y,
                                        facecolor=SERIES[0], edgecolor="none", zorder=2))
        if x["p90"] - x["p10"] > 1.0:
            ax.plot([x["p10"], x["p90"]], [y, y], color=INK, lw=1.1, zorder=4, solid_capstyle="butt")
            for e in (x["p10"], x["p90"]):
                ax.plot([e, e], [y - h * 0.32, y + h * 0.32], color=INK, lw=1.1, zorder=4)
        text = f"{_usd(v)}  ({_usd(v / r['central']['annuity'] / 12)} a month)".replace("$", r"\$")  # one $ each, not mathtext
        ax.annotate(text, (max(v, x["p90"], 0.0), y), xytext=(8, 0),
                    textcoords="offset points", ha="left", va="center", fontsize=7.5, color=INK2)
    ax.axvline(0, color=MUTED, lw=0.8, zorder=3)
    ax.set_yticks(ys, [short.get(k, label[k]) for k in keys], color=INK2, fontsize=8)
    step = 2000 if hi < 16000 else 4000
    ticks = np.arange(np.ceil(xmin / step) * step, xmax * 0.97, step)
    ax.set_xticks(ticks, [_usd(t) for t in ticks])
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.955, "What each of the engineered design's choices costs a flat over 20 years, net of what it saves", fontsize=11, color=INK, ha="left")
    fig.text(0.01, 0.915, "Each taken out of the design alone, the usual all-electric walk-up's way in its place. The data center's heat free.",
             fontsize=8, color=INK2, ha="left")
    fig.text(0.01, 0.88, f"USD 2026 a flat. The bar is the typical of {r['draws']:,} draws of every input with a range; the line is P10 to P90.",
             fontsize=8, color=INK2, ha="left")
    fig.text(0.01, 0.045, "A month: the 20-year cost spread over the 20 years at pass 3's 7%. Right of zero, the choice costs more than it saves.",
             fontsize=6.5, color=MUTED, ha="left")
    fig.text(0.01, 0.015, "Prices: 10b. Energy: 10c. Lives and upkeep: 10f. Run: brownfield choices.", fontsize=6.5, color=MUTED, ha="left")
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
