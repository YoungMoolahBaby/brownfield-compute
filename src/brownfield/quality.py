"""Pass 3g step 10h (D28): the quality walk-up the towns would build (`brownfield quality`).

D18 put the towns' new homes at their edges, 1-5 km from the data center's buildings, each on its
own heat pump: there the main to bring the data center's water costs $38,000-197,000 a home. The
engineered walk-up takes that water for its floors and its hot water, so as drawn it stands only
where the water reaches. 10g found what each of its choices buys and costs, and Jon set the aim:
"what we are going for is quality of life, anti enshittification". 10h keeps the choices that buy
quality and prices the walk-up the towns would build with them.

- **Kept** (`KEPT`): the ERVs, the airtightness to Phius, the cast iron, the water and fire services
  apart, the submeters, the water pipes held off the frame, the cold risers' insulation, and the
  design before bidding (the engineering's fee).
- **Dropped** (`DROPPED`): the floors and the plant (the data center's water, which the towns'
  edges don't get); the solar panels and the PRV (10g: no quality a tenant feels here, and neither
  pays). In their place, the usual all-electric walk-up's way: the mini-splits heat, and a 50 gal
  electric water heater in each flat.

Priced as 10g prices any walk-up by its choices (`choices.walkups`), over 10f's draws:
- the quality walk-up against the usual all-electric walk-up (the conventional design on the same
  site; its hot water the same), and against the central walk-up (one gas heater for the building;
  the cheapest usual walk-up in 10f's draws);
- each kept choice taken out of it alone, the usual walk-up's way in its place: its line where the
  heat it saves is the heat pump's, not the data center's free water;
- the data center's water (the floors and the plant) added back, with and without the heat
  network's share (pass 3 §4): what it would add where a walk-up could take it;
- the engineered design as drawn against it.
"""

from __future__ import annotations

import json
import math

import numpy as np

from . import OUT_DIR
from .choices import DC, FEE, FULL, KEYS, NAME, NONE, _usd, against_10f, diff, network_life, pays, walkups
from .energy import NL

KEPT = ("erv", "tight", "cast iron", "services", "submeters", "held off", "cold insulation")
DROPPED = {"radiant": "the data center's water: the towns' edges don't get it (D18)",
           "plant": "the data center's water: the towns' edges don't get it (D18)",
           "pv": "no quality a tenant feels, and it doesn't pay at 7% (10g)",
           "prv": "nothing at the street's 55 psi (10g); a site at the code's 80 psi would want it"}
QUALITY = frozenset(KEPT + (FEE,))
LINES = tuple(f"q out {k}" for k in KEPT + (FEE,))


def evaluate(fx: dict, p: dict, sp: dict | None = None, hw: dict | None = None) -> tuple[dict, dict, dict]:
    """10h on inputs `p` (`ranges.evaluate`'s signature, for its draws and tornado): the quality
    walk-up against the usual walk-ups, each kept choice taken out of it, and the data center's
    water added back; a flat, USD 2026. Returns (figures, sp, hw)."""
    walkup, sp, hw, a_T, nw = walkups(fx, p, sp, hw)
    full, none, central, q = walkup(FULL), walkup(NONE), walkup(NONE, "central"), walkup(QUALITY)
    o: dict[str, float] = {"annuity": a_T, "life engineered": full["life"], "life electric": none["life"],
                           "life central": central["life"], "life quality": q["life"]}
    o["feeders quality"] = q["feeders"]
    diff(o, "quality", q, none)
    diff(o, "quality, central", q, central)
    diff(o, "central", central, none)
    diff(o, "whole", full, none)
    for k in KEPT + (FEE,):
        diff(o, f"q out {k}", q, walkup(QUALITY - {k}))
    o["d life q interaction"] = o["d life quality"] - sum(o[f"d life {k}"] for k in LINES)
    qdc = walkup(QUALITY | DC)
    diff(o, "dc on quality", qdc, q)
    diff(o, "engineered over quality", full, q)
    for case, v in nw.items():
        o[f"d life dc on quality, network {case}"] = o["d life dc on quality"] + network_life(p, v, qdc["heat_mwh"], a_T)
        o[f"d life whole, network {case}"] = o["d life whole"] + network_life(p, v, full["heat_mwh"], a_T)
    return o, sp, hw


# ---- the wiring: the quality walk-up's flats have the ERV, its preheater and their own water heater ----

QUALITY_FLAT = (True, True, False)  # `choices.flat_kind(QUALITY)`
USUAL_FLATS = {"electric": (False, True, False), "central": (False, False, False)}


def wiring(r10: dict, fx: dict, p: dict, nec_note: float) -> dict:
    """The quality walk-up takes the all-electric walk-up's service main, and its flats carry both the
    ERV with its preheater (the engineered flats') and their own water heater (the usual flats'):
    - the main by NEC 220.84 (`electrical.service`'s way) on the all-electric walk-up's house loads
      (`baseline.services`);
    - each flat's feeder by 220.82, sized to the design's drop limit at that load
      (`choices.feeder_sizes`, as `walkups` prices it);
    - the same sizing at the engineered flats' load, which must give step 7's feeders;
    - the usual walk-ups' flats on the engineered design's feeders, within the NEC's informational
      note (`nec_note`, 3%): undesigned, they aren't held to the design's 2%."""
    from .baseline import FT2
    from .choices import ENGINEERED_FLAT, FEEDER_CLASS, feeder_sizes
    from .electrical import APPLIANCES, MAINS, appliance_va, conduit_for
    from .loads import nec_220_84

    e = "systems.electrical."
    apt = fx["apt"]
    appl = [appliance_va(p, k) - (p[e + "manifold_controls_va"] if k == "erv" else 0.0) for k in APPLIANCES] + [p["baseline.usual.heater_va"]]
    ft2 = apt["flats"][0]["floor_m2"] / FT2
    fl = nec_220_84(len(apt["flats"]), ft2, appl, p[e + "cooling_va"] + appliance_va(p, "preheater"), p[e + "cooling_va"], p)
    sv = r10["services"]["electric"]
    amps = (fl["calculated_va"] + sv["house_va"]) / (math.sqrt(3) * 208.0)
    q = fx["feeders"][QUALITY_FLAT]
    up = {k: v for k, v in q.items() if v["to"] != v["from"]}
    lax = dict(p, **{"systems.wiring.vd_feeder_max": nec_note})
    usual = {w: feeder_sizes(apt, lax, fx["s7"], kind) for w, kind in USUAL_FLATS.items()}
    return {"amps": amps, "main_a": next(m[0] for m in MAINS if m[0] >= amps), "electric_a": sv["main_a"], "feeders": q, "upsized": up,
            "priced": all(v["to"] in FEEDER_CLASS for v in up.values()),
            "conduits": {k: conduit_for([v["to"]] * 3 + ["8"], p)["trade"] for k, v in up.items()},
            "classes": {k: FEEDER_CLASS[v["to"]] for k, v in up.items() if v["to"] in FEEDER_CLASS},
            "engineered": fx["feeders"][ENGINEERED_FLAT], "usual": usual, "nec_note": nec_note, "vd_max": p["systems.wiring.vd_feeder_max"]}


CONDUIT = {"feeder_1": "1", "feeder_1.25": "1-1/4", "feeder_1.25_1awg": "1-1/4"}  # each feeder class's conduit (`pricing.CLASSES`)


def grounds(fx: dict) -> dict[str, list[dict]]:
    """NEC 250.122(B): conductors made larger than the least size with the ampacity (here, for the
    drop) take an equipment grounding conductor larger in proportion to their circular mils. The
    design sizes each feeder's by its breaker alone (Table 250.122, `electrical.egc_for`). Each
    feeder of the engineered design as issued, and of the quality walk-up, whose ground is short
    of it. Found by 10h; reported, not fixed (the bid set's feeders are Addendum 7's)."""
    from .choices import ENGINEERED_FLAT
    from .electrical import FEEDER_METAL, SIZES, _table_rows, ampacity, egc_for

    cmil = {r["size"]: float(r["cmil"]) for r in _table_rows("nec2020_ch9_table_8.csv")}
    out = {}
    for label, kind in (("engineered", ENGINEERED_FLAT), ("quality", QUALITY_FLAT)):
        rows = []
        for name, v in fx["feeders"][kind].items():
            least = next(sz for k, sz in enumerate(SIZES) if k >= SIZES.index("8") and ampacity(sz, FEEDER_METAL, 75) >= v["least_a"] - 1e-9)
            egc = egc_for(v["breaker_a"])
            need = cmil[egc] * cmil[v["to"]] / cmil[least]
            req = next(sz for sz in SIZES if sz in cmil and cmil[sz] >= need - 1e-6)
            if cmil[req] > cmil[egc]:
                rows.append({"flat": name, "size": v["to"], "least": least, "egc": egc, "needs": req, "ft": v["ft"]})
        out[label] = rows
    return out


# ---- what the quality walk-up keeps, and what it gives up (central, from the runs) ----

def buys(apt: dict, p: dict, en: dict, co: dict, central: dict) -> dict:
    """10g's facts (`choices.buys`) and the energy of each walk-up a flat a year."""
    from .choices import buys as facts

    b = facts(apt, p, en, co)
    b["kwh"] = {k: -central[f"d kwh {k}"] for k in ("quality", "q out erv", "q out tight", "dc on quality")}
    b["heat_mwh"] = central["d heat dc on quality"]
    return b


# ---- the run ----

def checks(r: dict) -> list[tuple[str, bool, str]]:
    from .ranges import PRECISION

    c, pc, tf, wr, g = r["central"], r["precision"], r["10f"], r["wiring"], r["10g"]
    fd, up = wr["feeders"].values(), wr["upsized"]
    worst_fd = max(fd, key=lambda x: x["amps"])
    eng = wr["engineered"].values()
    usual = [x for u in wr["usual"].values() for x in u.values()]
    return [
        ("the choices kept and dropped are 10g's, each once", sorted(KEPT + tuple(DROPPED)) == sorted(KEYS) and not set(KEPT) & set(DROPPED),
         f"{len(KEPT)} kept, {len(DROPPED)} dropped, of {len(KEYS)}"),
        ("the quality walk-up's flats (the ERV and its preheater, and their own water heater) keep the all-electric walk-up's main (NEC 220.84)",
         wr["main_a"] <= wr["electric_a"], f"{wr['amps']:.0f} A on {wr['electric_a']} A"),
        ("sized at the engineered flats' load, the feeders are step 7's: the same conductors and breakers",
         all(x["to"] == x["from"] and x["breaker_a"] == x["from_breaker_a"] for x in eng), f"{len(eng)} feeders"),
        ("the quality walk-up's feeders carry its flats on their breakers (220.82), each within its conductors' ampacity and the design's drop",
         all(x["breaker_a"] == x["from_breaker_a"] and x["amps"] <= x["ampacity"] and x["drop"] <= wr["vd_max"] + 1e-12 for x in fd),
         f"at most {worst_fd['amps']:.1f} A on {worst_fd['breaker_a']:.0f} A; drop at most {max(x['drop'] for x in fd):.2%}, the limit "
         f"{wr['vd_max']:.0%}; {len(up)} upsized: " + ", ".join(f"{k} {v['from']} to {v['to']} AWG" for k, v in up.items())),
        ("each feeder upsized has a priced class, and its conductors fit that class's conduit (Chapter 9)",
         wr["priced"] and all(CONDUIT[wr["classes"][k]] == t for k, t in wr["conduits"].items()),
         "; ".join(f"{k} in {t} in." for k, t in wr["conduits"].items()) or "none upsized"),
        (f"the usual walk-ups' flats on the engineered design's feeders, on their breakers and within the NEC's informational {wr['nec_note']:.0%}",
         all(x["to"] == x["from"] and x["breaker_a"] == x["from_breaker_a"] for x in usual),
         f"drop at most {max(x['drop'] for x in usual):.2%}, at most {max(x['amps'] for x in usual):.1f} A"),
        ("at every input's central value, the engineered design, the all-electric and the central walk-ups over the years counted are 10f's",
         r["parity"] < 1e-6, f"worst ${r['parity']:.2e} a flat"),
        ("draw for draw, they are 10f's (its saved draws)", tf["worst"] is not None and tf["worst"] < 1e-6,
         f"worst ${tf['worst']:.2e} a flat" if tf["worst"] is not None else tf["why"]),
        ("the fee (less the feeders its drop limit upsizes) and the choices that use no energy cost the same out of the quality walk-up "
         "as out of the engineered design (10g)", g["worst"] < 1e-6, f"worst ${g['worst']:.2e} a flat, {g['which']}"),
        ("the kept choices one at a time, the fee and their interaction add up to the quality walk-up's difference",
         abs(sum(c[f"d life {k}"] for k in LINES) + c["d life q interaction"] - c["d life quality"]) < 1e-6, "by construction, checked"),
        ("the draws reproduce: the first ones evaluated here, alone, give what the workers gave", r["repro"] < 1e-9, f"worst ${r['repro']:.2e} a flat"),
        (f"enough draws: each line's P10, P50 and P90 known to within {PRECISION:.1%} of its P10-P90 spread (the bootstrap's standard error)",
         pc["worst"] <= PRECISION, f"worst {pc['worst']:.1%} ({pc['which']})"),
        ("the tornado's centre is the central run", r["tornado_centre"] < 1e-9, f"worst ${r['tornado_centre']:.2e} a flat"),
    ]


NO_ENERGY = ("cast iron", "services", "submeters", "held off", "cold insulation", FEE)


def run(r10: dict, pr: dict, en: dict, co: dict, apt: dict, params: dict, n: int | None = None, seed: int | None = None,
        workers: int | None = None) -> dict:
    """10h on 10a-10d's runs: the quality walk-up centrally and over 10f's draws; written to
    `out/pass3/quality.json` and `.md`."""
    from . import choices, ranges
    from .params import values

    n = n or ranges.DRAWS
    seed = seed or ranges.SEED
    p = values(params)
    fx = choices.prepare(r10, apt, p)
    central, sp0, hw0 = evaluate(fx, p)
    ten, _, _ = ranges.evaluate(fx, p, sp0, hw0)
    parity = max(abs(central[k] - ten[k]) for k in ("life engineered", "life electric", "life central"))
    g10, _, _ = choices.evaluate(fx, p, sp0, hw0)
    gap = {k: abs(central[f"d life q out {k}"] - (central["feeders quality"] if k == FEE else 0.0) - g10[f"d life out {k}"]) for k in NO_ENERGY}
    mc = ranges.monte_carlo(fx, params, n, seed, workers, fn=evaluate)
    base, vary = ranges.draws(params, n, seed)
    alone = [evaluate(fx, dict(base, **{k: float(v[i]) for k, v in vary.items()}))[0] for i in range(min(n, 2))]
    repro = max(abs(alone[i][k] - mc[k][i]) for i in range(len(alone)) for k in mc)
    s = ranges.summary(mc)
    life = {k: v for k, v in mc.items() if k.startswith("d life ")}
    out = {"central": central, "summary": s, "pays": pays(mc), "lowest": {k: float(v.min()) for k, v in life.items()},
           "highest": {k: float(v.max()) for k, v in life.items()}, "draws": n, "seed": seed, "parity": parity,
           "10g": {"worst": max(gap.values()), "which": max(gap, key=gap.get)}, "repro": repro, "precision": ranges.precision(life),
           "10f": against_10f(mc), "buys": buys(apt, p, en, co, central), "wiring": wiring(r10, fx, p, params["systems.wiring.vd_feeder_max"].high),
           "grounds": grounds(fx), "flats": fx["n"],
           "varied": len(vary)}
    out["sign"] = {k.removeprefix("d life "): (s[k]["p10"] > 0) == (s[k]["p90"] > 0) for k in life}
    flips = tuple(f"d life {k}" for k, holds in out["sign"].items() if not holds)
    out["tornado"] = ranges.tornado(fx, params, p, flips, sp0, hw0, ranges.energy_reads(fx, p, only=choices.CASES), fn=evaluate) if flips else {}
    again, _, _ = evaluate(fx, p, sp0, hw0)
    out["tornado_centre"] = max(abs(again[k] - central[k]) for k in central)
    out["checks"] = checks(out)
    path = OUT_DIR / "pass3"
    (path / "quality.json").write_text(json.dumps(out, indent=1, default=float) + NL, encoding="utf-8")
    np.savez_compressed(path / "quality_draws.npz", **mc)
    (path / "quality.md").write_text(report(out, p) + NL, encoding="utf-8")
    out["mc"] = mc
    out["written"] = [path / "quality.json", path / "quality_draws.npz", path / "quality.md"]
    return out


# ---- the report ----

TOTALS = (("quality", "the quality walk-up, less the usual all-electric walk-up"),
          ("quality, central", "the quality walk-up, less the central walk-up (gas hot water, the cheapest usual)"),
          ("whole", "the engineered design as drawn, less the usual all-electric walk-up (10f)"),
          ("whole, network dense", "  with the heat network's share, dense (pass 3 §4)"),
          ("whole, network base", "  with the heat network's share, base"),
          ("engineered over quality", "the engineered design as drawn, less the quality walk-up"))
WATER = (("dc on quality", "the data center's water (the floors and the plant) added to the quality walk-up"),
         ("dc on quality, network dense", "  with the heat network's share, dense"),
         ("dc on quality, network base", "  with the heat network's share, base"))
OUT = tuple((f"q out {k}", NAME[k]) for k in KEPT) + (
    (f"q out {FEE}", "the design before bidding: its fee, and the feeders its 2% drop upsizes"),
    ("q interaction", "how the choices interact (the difference less the lines above)"))


def report(r: dict, p: dict) -> str:
    from .systems import report as fmt

    c, s, py, sg, b = r["central"], r["summary"], r["pays"], r["sign"], r["buys"]
    a_T = c["annuity"]
    lines = ["Pass 3g step 10h: the quality walk-up the towns would build", "", fmt(r["checks"]), "",
             "Kept, the choices that buy quality: " + "; ".join(NAME[k] for k in KEPT) + "; and the design before bidding.",
             "Dropped: " + "; ".join(f"{NAME[k]} ({why})" for k, why in DROPPED.items()) + ".",
             "In their place the usual all-electric walk-up's way: the mini-splits heat; a 50 gal electric water heater in each flat.", "",
             f"A flat, USD 2026, over {p['cost.money.life_yr']:g} years at {p['cost.money.discount']:.0%} (x{a_T:.2f} a year's cost). "
             f"{r['draws']:,} draws of {r['varied']} inputs (seed {r['seed']}, 10f's).", ""]
    w = max(len(label) for label in dict(TOTALS + WATER + OUT).values())
    lines.append(f"{'':{w}s} {'up front':>9s} {'a year':>7s} {'repl.':>7s} {'20 years':>9s} {'a month':>8s}  {'P50 (P10 to P90)':>28s} {'pays':>6s}")

    def row(k: str, label: str) -> str:
        x = s[f"d life {k}"]
        up = c.get(f"d up {k}")
        cols = (f"{_usd(up):>9s} {_usd(c[f'd year {k}']):>7s} {_usd(c[f'd replace {k}']):>7s}" if up is not None else f"{'':>9s} {'':>7s} {'':>7s}")
        band = f"{_usd(x['p50'])} ({_usd(x['p10'])} to {_usd(x['p90'])})"
        flag = "" if sg[k] else "  SIGN FLIPS"
        return f"{label:{w}s} {cols} {_usd(c[f'd life {k}']):>9s} {_usd(c[f'd life {k}'] / a_T / 12):>8s}  {band:>28s} {py[k]:6.1%}{flag}"

    for group in (TOTALS, WATER, OUT):
        lines += [row(k, label) for k, label in group] + [""]
    life = {k: c[f"life {k}"] for k in ("engineered", "quality", "electric", "central")}
    lines.append("Each walk-up over the years counted, central: " + "; ".join(f"{k} {_usd(v)}" for k, v in life.items()))
    kw = b["kwh"]
    e, u = b["bed_cfm"]["engineered"], b["bed_cfm"]["usual"]
    lines += ["", "What the quality walk-up keeps, against the usual all-electric walk-up:",
              f"  outdoor air to every bedroom, {e[0]:.1f}-{e[1]:.1f} cfm a person by duct at {b['erv_c']:.1f} C or more, against "
              f"{u[0]:.1f}-{u[1]:.1f} through the walls",
              f"  {b['ach50'][0]:.2f}-{b['ach50'][1]:.2f} ACH50, against {b['code_ach50']:g}",
              f"  a neighbour's flush at {b['drain_dba'][0]:g} dBA, against {b['drain_dba'][1]:g} (CMHC's limit {b['cmhc_dba']:g}); "
              f"supply pipes {b['supply_db']:.1f} dB quieter",
              "  the sprinklers on a service of their own, supervised; each flat billed for its own water; no condensation on the cold risers",
              f"  the tub's worst wait {b['tub_wait_s'][1]:.0f} s from the flat's own heater (the plant's {b['tub_wait_s'][0]:.0f} s)",
              f"  electricity: {abs(kw['quality']):,.0f} kWh a flat a year {'less' if kw['quality'] >= 0 else 'more'} than the usual walk-up; "
              f"the ERV {abs(kw['q out erv']):,.0f} kWh {'less' if kw['q out erv'] >= 0 else 'more'} than a bath fan, net of the heat "
              f"pump's heat it saves; the airtightness {abs(kw['q out tight']):,.0f} kWh {'less' if kw['q out tight'] >= 0 else 'more'}",
              "What it gives up, against the engineered design:",
              f"  floors at {b['floors_c'][0]:.1f}-{b['floors_c'][1]:.1f} C at the design hour; the outdoor units heat "
              f"{b['heat_h']['usual']:,.0f} h a year, against {b['heat_h']['engineered']:,.0f}",
              f"  {b['heat_mwh']:.1f} MWh of the data center's heat a flat a year, and {abs(kw['dc on quality']):,.0f} kWh of electricity "
              f"{'saved' if kw['dc on quality'] >= 0 else 'more'} with it"]
    for k, rows in r["tornado"].items():
        lines += ["", f"{k.removeprefix('d life ')} keeps no sign from P10 to P90. What moves it most (central {_usd(c[k])}; "
                      "each input low -> high, the rest central):"]
        lines += [f"  {name}: {_usd(lo)} -> {_usd(hi)}" for name, lo, hi in rows[:12]]
    wr = r["wiring"]
    lines += ["", f"The wiring: the quality walk-up's flats on the all-electric walk-up's house, {wr['amps']:.0f} A on its {wr['electric_a']} A main; "
                  f"each flat's feeder at most {max(x['amps'] for x in wr['feeders'].values()):.1f} A on its "
                  f"{min(x['breaker_a'] for x in wr['feeders'].values()):.0f} A breaker. Held to the design's {wr['vd_max']:.0%} drop, "
                  f"{len(wr['upsized'])} feeders go a size up: " + ", ".join(f"{k} ({v['ft']:.0f} ft) {v['from']} to {v['to']} AWG"
                                                                      for k, v in wr["upsized"].items())
              + f"; {_usd(c['feeders quality'])} a flat up front"]
    gr = r["grounds"]
    lines += ["", "Found, not fixed: NEC 250.122(B) takes a feeder's ground up in proportion when its conductors are made larger than the "
                  "least with the ampacity (here, for the drop). The design sizes the ground by the breaker alone, so:"]
    for label, rows in gr.items():
        lines.append(f"  {label}: " + ("; ".join(f"{x['flat']} ({x['ft']:.0f} ft), {x['size']} AWG where {x['least']} would carry it: "
                                                  f"its {x['egc']} AWG ground should be {x['needs']}" for x in rows) or "none"))
    lines += ["", "The lowest and highest draw of each line over the years counted:"]
    lines += [f"  {k}: {_usd(r['lowest'][f'd life {k}'])} to {_usd(r['highest'][f'd life {k}'])}" for k in sg]
    return NL.join(lines)


# ---- the figure ----

ROWS = (("central", "the central walk-up (gas hot water)"),
        ("quality", "the quality walk-up, on heat pumps"),
        ("whole", "the engineered design, as drawn"),
        ("whole, network dense", "  with the heat network's share, dense"),
        ("whole, network base", "  with the heat network's share, base"))


def figure(r: dict, path) -> None:
    """Each walk-up over 20 years, a flat, less the usual all-electric walk-up: the typical draw
    (P50) as a bar from zero, P10-P90 as a line. A static PNG for the report, light mode."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    from .figures import GRID, INK, INK2, MUTED, SERIES, SURFACE

    s, a_T = r["summary"], r["central"]["annuity"]
    keys = [k for k, _ in ROWS]
    ys = [0.0, 1.0, 2.0, 3.0, 4.0]
    lo = min(min(s[f"d life {k}"]["p10"] for k in keys), 0.0)
    hi = max(s[f"d life {k}"]["p90"] for k in keys)
    xmin, xmax = lo - 0.04 * (hi - lo), hi * 1.36
    dpi, bar_px, end_px = 150, 18, 4
    fig, ax = plt.subplots(figsize=(10, 3.9), dpi=dpi, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ys[-1] + 0.7, -0.7)
    fig.subplots_adjust(left=0.28, right=0.985, top=0.76, bottom=0.17)
    fig.canvas.draw()
    bb = ax.get_window_extent()
    px_x, px_y = bb.width / (xmax - xmin), bb.height / (ys[-1] + 1.4)
    h = bar_px / px_y
    for y, k in zip(ys, keys):
        x = s[f"d life {k}"]
        v = x["p50"]
        rx = min(end_px / px_x, abs(v) / 2) if v else 0.0
        color = SERIES[1] if k == "quality" else SERIES[0]
        ax.add_patch(FancyBboxPatch((min(0.0, v), y - h / 2), abs(v), h, boxstyle=f"round,pad=0,rounding_size={rx}", mutation_aspect=px_x / px_y,
                                    facecolor=color, edgecolor="none", zorder=2))
        ax.plot([x["p10"], x["p90"]], [y, y], color=INK, lw=1.1, zorder=4, solid_capstyle="butt")
        for e in (x["p10"], x["p90"]):
            ax.plot([e, e], [y - h * 0.32, y + h * 0.32], color=INK, lw=1.1, zorder=4)
        text = f"{_usd(v)}  ({_usd(v / a_T / 12)} a month)".replace("$", r"\$")
        ax.annotate(text, (max(v, x["p90"], 0.0), y), xytext=(8, 0), textcoords="offset points", ha="left", va="center", fontsize=7.5, color=INK2)
    ax.axvline(0, color=MUTED, lw=0.8, zorder=3)
    ax.set_yticks(ys, [label for _, label in ROWS], color=INK2, fontsize=8)
    step = next(t for t in (2000, 4000, 5000, 10000, 20000, 50000) if (xmax - xmin) / t <= 9)
    ticks = np.arange(np.ceil(xmin / step) * step, np.ceil(hi / step) * step + 1, step)  # none behind the labels
    ax.set_xticks(ticks, [_usd(t) for t in ticks])
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.94, "What a flat costs over 20 years more than the usual all-electric walk-up", fontsize=11, color=INK, ha="left")
    fig.text(0.01, 0.88, "The quality walk-up keeps the ERVs, the airtightness, the cast iron, the services apart, the submeters, the quiet pipes",
             fontsize=8, color=INK2, ha="left")
    fig.text(0.01, 0.83, f"and the design before bidding, on heat pumps. USD 2026; the bar is the typical of {r['draws']:,} draws, the line P10 to P90.",
             fontsize=8, color=INK2, ha="left")
    fig.text(0.01, 0.065, "A month: the 20-year cost spread over the 20 years at pass 3's 7%. The data center's heat free; the network's share is pass 3 §4's.",
             fontsize=6.5, color=MUTED, ha="left")
    fig.text(0.01, 0.025, "Prices: 10b. Energy: 10c. Lives and upkeep: 10f. Run: brownfield quality.", fontsize=6.5, color=MUTED, ha="left")
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
