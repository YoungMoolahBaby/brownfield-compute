"""Pass 3g step 10f (D28): the ranges (`brownfield baseline`).

10b-10e gave each walk-up's figures with every input at its central value. 10f draws every input
that has a range, all at once (`params.draw`: triangular low/value/high, independent, a fixed seed),
and runs 10b's prices, 10c's energy and 10e's split again for each draw (`evaluate`). 10a's lists
are held: they are the design's quantities, not inputs. Where 10a and 10c read the same input (the
envelope's U-values, the code's leakage), the draw moves 10c's energy and not 10a's quantities.

What it gives, a flat:
- **each walk-up over the years counted** (`cost.money.life_yr`, 20; pass 3's frame): its systems
  and the fee's extra up front; the replacements of what wears out sooner (`baseline.life`: an item
  that lasts L years costs its price spread over its own L years, every year, `wear`); and each
  year's running cost (10c) and upkeep (`baseline.upkeep`) at pass 3's discount rate as an annuity;
- the engineered design **with its share of the heat network** (pass 3 §4), base and dense: the
  share up front, its upkeep and pumping a year;
- **the engineered design less each usual walk-up:** up front, a year, over the years counted;
- **10e's split under the draw:** pass 4's gap per flat each way, the market-rate gap and the rent
  that would carry the cost, the heat prices that tie. The owner's upkeep and replacements are in
  the owner's costs here (10e left them out).

Then P10/P50/P90 of each, the share of draws in which each walk-up costs least, the sign test (does
the engineered design's 20-year difference against each usual walk-up keep its sign from P10 to
P90?) and a tornado (`tornado`: each input from its low to its high, the rest central).
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import OUT_DIR
from .baseline import NAMES, USUAL, WALKUPS
from .energy import NL

DRAWS = 4000
SEED = 2610  # pass 3g, step 10f
SPACE_CASES = ("engineered", "usual")  # the two `energy.ledger` reads; the case between them is 10c's split only
L, U = "baseline.life.", "baseline.upkeep."
# An upkeep param (USD a unit a year): the price classes it's a unit of (their quantities in 10b's
# lines), and the param that scales a unit, if any.
UPKEEP: dict[str, tuple[tuple[str, ...], str | None]] = {
    "heat_pump_usd": (("minisplit_fujitsu_12_ducted",), None),
    "furnace_usd": (("furnace_goodman_40k",), None),
    "ac_usd": (("ac_goodman_15ton",), None),
    "electric_heater_usd": (("aosmith_ent50",), None),
    "gas_heater_usd": (("rheem_prog40_pdv",), None),
    "central_heater_usd": (("aosmith_bth120",), None),
    "erv_usd": (("erv_broan_blp120",), None),
    "hp_wtw_usd": (("climatemaster_sw036",), None),
    "tank_usd": (("lochinvar_hp150g", "bradford_re340s6", "aosmith_dre52"), None),
    "backflow_test_usd": (("domestic_service", "fire_service", "combined_service"), None),
    "pv_usd_kwdc": (("pv_kw",), "systems.pv.dc_ac"),
}
TC_KEYS = ("4%", "9%")
WAYS = ("energy model", "PHA schedule")


# ---- one set of inputs ----

def prepare(r10: dict, apt: dict, p: dict) -> dict:
    """What every draw holds fixed: the model, 10a's lists and its summary of the routes, the
    weather's hours."""
    from .energy import year_hours

    n = len(apt["flats"])
    return {"apt": apt, "items": r10["items"], "s7": r10["s7"], "n": n,
            "floor_m2": sum(f["floor_m2"] for f in apt["flats"]) / n, "wx": year_hours(p)}


def wear(pr: dict, p: dict, n: int) -> dict:
    """Each walk-up's upkeep a year and its replacements over the years counted (present value), a
    flat. An item that lasts L years, fewer than the years counted T, costs its 10b price spread
    over its own L years as an annuity, every year of the T: its price x (annuity(T) / annuity(L)
    - 1) beyond the first. (When L divides T this is each replacement at its year, discounted.)
    What lasts T years or more is counted once, as pass 3 counts all equipment."""
    from .cost import annuity

    r, T = p["cost.money.discount"], p["cost.money.life_yr"]
    a_T = annuity(r, T)
    lives = {k.removeprefix(L): p[k] for k in p if k.startswith(L)}
    qty: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    out = {w: {"upkeep": 0.0, "replace": 0.0, "by": defaultdict(float)} for w in WALKUPS}
    for ln in pr["lines"]:
        for w in WALKUPS:
            qty[ln["class"]][w] += ln["qty"][w]
        life = lives.get(ln["class"])
        if life is not None and life < T:
            f = a_T / annuity(r, life) - 1
            for w in WALKUPS:
                out[w]["replace"] += ln["usd"][w] * f / n
                out[w]["by"][f"replace {ln['class']}"] += ln["usd"][w] * f / n
    for key, (classes, scale) in UPKEEP.items():
        k = 1.0 if scale is None else p[scale]
        for w in WALKUPS:
            v = p[U + key] * k * sum(qty[c][w] for c in classes) / n
            out[w]["upkeep"] += v
            out[w]["by"][f"upkeep {key}"] += v
    for w in WALKUPS:
        out[w]["by"] = dict(out[w]["by"])
    return out


def evaluate(fx: dict, p: dict, sp: dict | None = None, hw: dict | None = None) -> tuple[dict, dict, dict]:
    """10b, 10c and 10e on inputs `p`, with the upkeep and replacements: every figure 10f ranges,
    a flat (USD 2026). `sp` and `hw` reuse a run of `energy.space` and `energy.hot_water` (the
    tornado's, when the input moved isn't one they read). Returns (figures, sp, hw)."""
    from . import energy, pricing, savings
    from .cost import annuity

    apt, s7, n = fx["apt"], fx["s7"], fx["n"]
    pr = pricing.price(fx["items"], p)
    pr["fee"] = pricing.fee(p, n)
    pr["network"] = pricing.network_share(p, s7, n, fx["floor_m2"])
    sp = sp if sp is not None else energy.space(apt, p, fx["wx"], only=SPACE_CASES)
    hw = hw if hw is not None else energy.hot_water(apt, p, s7)
    rows = energy.ledger(apt, p, s7, sp, hw)
    dem = energy.house_demand(apt, p, s7, hw)
    c = energy.costs(rows, p, n, dem)
    en = {"ledger": rows, "costs": c, "demand": dem, "flats": n, "tie_usd_mwh": energy.tie_price(c)}
    pay = savings.payers(en, p, n)
    up = savings.up_front(pr, n)
    wr = wear(pr, p, n)
    a_T = annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    t = pr["totals"]
    o: dict[str, float] = {"annuity": a_T}
    for w in WALKUPS:
        o[f"systems {w}"] = t[w]["total"] / n
        o[f"fee {w}"] = up[w]["fee"]
        o[f"energy {w}"] = pay[w]["total"]
        o[f"upkeep {w}"] = wr[w]["upkeep"]
        o[f"replace {w}"] = wr[w]["replace"]
        o[f"energy years {w}"], o[f"upkeep years {w}"] = o[f"energy {w}"] * a_T, o[f"upkeep {w}"] * a_T  # the years', valued now
        o[f"life {w}"] = o[f"systems {w}"] + o[f"fee {w}"] + o[f"replace {w}"] + o[f"energy years {w}"] + o[f"upkeep years {w}"]
    mwh = pay["engineered"]["heat_mwh"]
    b = "pass3.block."
    for case, v in pr["network"].items():
        year = p[b + "om_share"] * v["flat"] + p[b + "pump_share"] * mwh * p["cost.energy.elec_usd_mwh"]
        o[f"network {case}"] = v["flat"]
        o[f"network year {case}"] = year
        o[f"network years {case}"] = v["flat"] + year * a_T
        o[f"life engineered, network {case}"] = o["life engineered"] + o[f"network years {case}"]
        o[f"heat carry {case}"] = savings.carry_usd_mwh(p, v["flat"], mwh)
    for w in USUAL:
        o[f"d up {w}"] = (o["systems engineered"] + o["fee engineered"]) - (o[f"systems {w}"] + o[f"fee {w}"])
        o[f"d year {w}"] = (o["energy engineered"] + o["upkeep engineered"]) - (o[f"energy {w}"] + o[f"upkeep {w}"])
        o[f"d replace {w}"] = o["replace engineered"] - o[f"replace {w}"]
        o[f"d life {w}"] = o["life engineered"] - o[f"life {w}"]
        for case in pr["network"]:
            o[f"d life {w}, network {case}"] = o[f"life engineered, network {case}"] - o[f"life {w}"]
        o[f"heat tie {w}"] = en["tie_usd_mwh"][w]
    # 10e under the draw, the owner's upkeep and replacements (a year, as an annuity) in the owner's costs.
    pay2 = {w: {**v, **{k: dict(v[k], owner=v[k]["owner"] + wr[w]["upkeep"] + wr[w]["replace"] / a_T)
                        for k in ("included", "billed") if k in v}} for w, v in pay.items()}
    tc = savings.tax_credit(p, pay2, up)["engineered"]["ways"]
    for way in WAYS:
        for k in TC_KEYS:
            o[f"gap {k}, {way}"] = tc[way]["gap"][k]
        o[f"allowance, {way}"] = tc[way]["d_ua_month"]
    mk = savings.market(p, pay2, up)["engineered"]
    o["market gap"], o["market rent needed"], o["tenant saving"] = mk["gap"], mk["rent_needed_month"], mk["tenant_saving"]
    return o, sp, hw


# ---- the draws ----

_FX: dict | None = None
_BASE: dict | None = None


def _init(fx: dict, base: dict) -> None:
    global _FX, _BASE
    _FX, _BASE = fx, base


def _work(cols: dict[str, np.ndarray]) -> list[dict]:
    """A worker's share of the draws: each draw's inputs over the central ones, evaluated."""
    out = []
    for i in range(len(next(iter(cols.values())))):
        p = dict(_BASE)
        p.update({k: float(v[i]) for k, v in cols.items()})
        out.append(evaluate(_FX, p)[0])
    return out


def draws(params: dict, n: int, seed: int) -> tuple[dict, dict[str, np.ndarray]]:
    """The central inputs and the draws of every input that varies (`params.draw`)."""
    from .params import draw, values

    d = draw(params, n, seed)
    return values(params), {k: d[k] for k in sorted(params) if params[k].varies}


def monte_carlo(fx: dict, params: dict, n: int = DRAWS, seed: int = SEED, workers: int | None = None) -> dict[str, np.ndarray]:
    """`n` draws evaluated, split over `workers` processes (one: in this one). The result is the
    same for any number of workers: the draws are made here, by `seed`, and kept in order."""
    base, vary = draws(params, n, seed)
    workers = workers or max(1, min((os.cpu_count() or 2) - 2, 10))
    size = max(1, -(-n // (workers * 4)))
    chunks = [{k: v[a:a + size] for k, v in vary.items()} for a in range(0, n, size)]
    if workers == 1:
        _init(fx, base)
        done = [_work(ch) for ch in chunks]
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(fx, base)) as ex:
            done = list(ex.map(_work, chunks))
    rows = [r for ch in done for r in ch]
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}


def summary(mc: dict[str, np.ndarray]) -> dict[str, dict[str, float]]:
    return {k: {"p10": float(np.percentile(v, 10)), "p50": float(np.percentile(v, 50)), "p90": float(np.percentile(v, 90)),
                "mean": float(v.mean())} for k, v in mc.items()}


def shares(mc: dict[str, np.ndarray]) -> dict:
    """The share of draws in which the engineered design costs less than each usual walk-up over
    the years counted (without and with its network share), and in which each walk-up costs least."""
    out = {"engineered cheaper": {}, "cheapest": {}}
    for w in USUAL:
        out["engineered cheaper"][w] = {k: float((mc[f"d life {w}{s}"] < 0).mean())
                                        for k, s in (("alone", ""), ("network base", ", network base"), ("network dense", ", network dense"))}
    for label, eng in (("alone", "life engineered"), ("network dense", "life engineered, network dense"),
                       ("network base", "life engineered, network base")):
        stack = np.vstack([mc[eng]] + [mc[f"life {w}"] for w in USUAL])
        least = np.argmin(stack, axis=0)
        out["cheapest"][label] = {w: float((least == i).mean()) for i, w in enumerate(WALKUPS)}
    return out


def sign_test(s: dict) -> dict:
    """Does the engineered design's difference over the years counted keep its sign from P10 to
    P90, against each usual walk-up (alone, and with the network share)? 10f's question: if not, a
    private cross-check (PLAN D28 step 10)."""
    out = {}
    for w in USUAL:
        for suffix in ("", ", network dense", ", network base"):
            x = s[f"d life {w}{suffix}"]
            out[f"{w}{suffix}"] = {"p10": x["p10"], "p90": x["p90"], "holds": (x["p10"] > 0) == (x["p90"] > 0)}
    return out


# ---- the tornado ----

class _Reads(dict):
    """Inputs that records which of them were read (each stage reads `p` directly: no copies)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.seen: set[str] = set()

    def __getitem__(self, k):
        self.seen.add(k)
        return super().__getitem__(k)


def energy_reads(fx: dict, p: dict) -> dict[str, set[str]]:
    """The inputs `energy.space` and `energy.hot_water` read (the slow stages), so the tornado reruns
    them only for those."""
    from . import energy

    a, b = _Reads(p), _Reads(p)
    energy.space(fx["apt"], a, fx["wx"], only=SPACE_CASES)
    energy.hot_water(fx["apt"], b, fx["s7"])
    return {"space": a.seen, "hot_water": b.seen}


def tornado(fx: dict, params: dict, p: dict, keys: tuple[str, ...], sp0: dict, hw0: dict, reads: dict) -> dict[str, list]:
    """How far each figure in `keys` moves as each input goes from its low to its high, the rest
    central; largest swing first. Inputs that move none of them by a dollar are left out."""
    rows: dict[str, list] = {k: [] for k in keys}
    for name in sorted(params):
        v = params[name]
        if not v.varies:
            continue
        ends = []
        for x in (v.low, v.high):
            q = dict(p, **{name: x})
            sp = None if name in reads["space"] else sp0
            hw = None if name in reads["hot_water"] else hw0
            ends.append(evaluate(fx, q, sp, hw)[0])
        for k in keys:
            lo, hi = ends[0][k], ends[1][k]
            if abs(hi - lo) >= 1.0:
                rows[k].append((name, lo, hi))
    return {k: sorted(v, key=lambda r: -abs(r[2] - r[1])) for k, v in rows.items()}


# ---- checks, the run, the report ----

def parity(fx: dict, p: dict, pr: dict, en: dict, sv: dict) -> dict:
    """The run at every input's central value, with no upkeep and nothing replaced, against 10b's,
    10c's and 10e's own runs: the worst difference (USD a flat) in the systems, the running costs and
    pass 4's gaps."""
    q = dict(p, **{k: 0.0 for k in p if k.startswith(U)}, **{k: 1e9 for k in p if k.startswith(L)})
    o, _, _ = evaluate(fx, q)
    n = fx["n"]
    worst = {"systems": max(abs(o[f"systems {w}"] - pr["totals"][w]["total"] / n) for w in WALKUPS),
             "running": max(abs(o[f"energy {w}"] - en["costs"][w]["total"] / n) for w in WALKUPS),
             "gap": max(abs(o[f"gap {k}, {way}"] - sv["tax_credit"]["engineered"]["ways"][way]["gap"][k]) for way in WAYS for k in TC_KEYS)}
    worst["market"] = abs(o["market gap"] - sv["market"]["engineered"]["gap"])
    return worst


def checks(r: dict) -> list[tuple[str, bool, str]]:
    pa, rp, hv = r["parity"], r["repro"], r["halves"]
    return [
        ("at every input's central value, with no upkeep and nothing replaced, 10f's run gives 10b's systems, 10c's running costs and 10e's gaps",
         max(pa.values()) < 1e-6, "; ".join(f"{k} worst ${v:.2e} a flat" for k, v in pa.items())),
        ("the draws reproduce: the first ones evaluated here, alone, give what the workers gave", rp < 1e-9, f"worst ${rp:.2e} a flat"),
        ("enough draws: each half of them gives the 20-year differences' P10, P50 and P90 within 5% of their P10-P90 spread",
         hv["worst"] <= 0.05, f"worst {hv['worst']:.1%} ({hv['which']})"),
        ("the tornado's centre is the central run", r["tornado_centre"] < 1e-9, f"worst ${r['tornado_centre']:.2e} a flat"),
    ]


TORNADO_KEYS = tuple(f"d life {w}" for w in USUAL)


def run(r10: dict, pr: dict, en: dict, sv: dict, apt: dict, params: dict, n: int = DRAWS, seed: int = SEED,
        workers: int | None = None) -> dict:
    """10f on 10a-10e's runs: the Monte Carlo, the sign test, the tornado; written to
    `out/pass3/ranges.json` and `.md`."""
    from .params import values
    from .pricing import price

    p = values(params)
    fx = prepare(r10, apt, p)
    central, sp0, hw0 = evaluate(fx, p)
    mc = monte_carlo(fx, params, n, seed, workers)
    base, vary = draws(params, n, seed)  # the same draws: each input's come in a block of n
    alone = []
    for i in range(min(n, 2)):
        q = dict(base, **{k: float(v[i]) for k, v in vary.items()})
        alone.append(evaluate(fx, q)[0])
    repro = max(abs(alone[i][k] - mc[k][i]) for i in range(len(alone)) for k in mc)
    s = summary(mc)
    half = n // 2
    worst, which = 0.0, ""
    for k in [k for k in mc if k.startswith("d life")]:
        spread = max(s[k]["p90"] - s[k]["p10"], 1.0)
        for q in (10, 50, 90):
            d = abs(np.percentile(mc[k][:half], q) - np.percentile(mc[k][half:], q)) / spread
            if d > worst:
                worst, which = d, f"{k}, P{q}"
    reads = energy_reads(fx, p)
    tor = tornado(fx, params, p, TORNADO_KEYS, sp0, hw0, reads)
    again, _, _ = evaluate(fx, p, sp0, hw0)
    out = {"central": central, "summary": s, "shares": shares(mc), "sign": sign_test(s), "tornado": tor, "draws": n, "seed": seed,
           "parity": parity(fx, p, pr, en, sv), "repro": repro, "halves": {"worst": worst, "which": which},
           "tornado_centre": max(abs(again[k] - central[k]) for k in central), "varied": len(vary), "flats": fx["n"],
           "wear": wear(price(fx["items"], p), p, fx["n"])}
    out["checks"] = checks(out)
    path = OUT_DIR / "pass3"
    (path / "ranges.json").write_text(json.dumps(out, indent=1, default=float) + NL, encoding="utf-8")
    np.savez_compressed(path / "ranges_draws.npz", **mc)
    (path / "ranges.md").write_text(report(out, p) + NL, encoding="utf-8")
    out["mc"] = mc
    out["written"] = [path / "ranges.json", path / "ranges_draws.npz", path / "ranges.md"]
    return out


def _usd(x: float) -> str:
    return f"{'-' if x < -0.5 else ''}${abs(x):,.0f}"


def _band(x: dict) -> str:
    return f"{_usd(x['p50'])} ({_usd(x['p10'])} to {_usd(x['p90'])})"


def report(r: dict, p: dict) -> str:
    from .systems import report as fmt

    c, s, sh, sg, tor = r["central"], r["summary"], r["shares"], r["sign"], r["tornado"]
    head = f"{'':44s} " + " ".join(f"{w:>24s}" for w in WALKUPS)
    T = p["cost.money.life_yr"]
    lines = ["Pass 3g step 10f: the ranges", "", fmt(r["checks"]), "",
             f"{r['draws']:,} draws of the {r['varied']} inputs with a range (seed {r['seed']}); each figure P50 (P10 to P90), a flat, USD 2026.",
             f"Over the years counted: {T:g} at {p['cost.money.discount']:.0%} (pass 3's; drawn from "
             f"{s['annuity']['p10']:.2f} to {s['annuity']['p90']:.2f} years' worth of a year's cost, P10 to P90).", "", head]
    for label, key in (("the systems (10b)", "systems"), ("the fee's extra", "fee"), ("replacements, present value", "replace"),
                       ("running cost a year (10c)", "energy"), ("upkeep a year", "upkeep"), ("over the years counted", "life")):
        lines.append(f"{label:44s} " + " ".join(f"{_band(s[f'{key} {w}']):>24s}" for w in WALKUPS))
    for case in ("dense", "base"):
        lines.append(f"  the engineered design with its network share ({case}): {_band(s[f'life engineered, network {case}'])}")
    lines += ["", "The engineered design less each usual walk-up:", f"{'':44s} " + " ".join(f"{w:>24s}" for w in USUAL)]
    for label, key in (("up front", "d up"), ("a year", "d year"), ("replacements", "d replace"), ("over the years counted", "d life"),
                       ("  with the network share, dense", "d life {}, network dense"), ("  with the network share, base", "d life {}, network base")):
        keys = [key.format(w) if "{}" in key else f"{key} {w}" for w in USUAL]
        lines.append(f"{label:44s} " + " ".join(f"{_band(s[k]):>24s}" for k in keys))
    lines += ["", "The sign test (the difference over the years counted, P10 and P90):"]
    lines += [f"  against {k}: {_usd(v['p10'])} to {_usd(v['p90'])}: {'holds' if v['holds'] else 'DOES NOT HOLD'}" for k, v in sg.items()]
    lines += ["", "Share of draws in which the engineered design costs less over the years counted:"]
    lines += [f"  than {w}: " + ", ".join(f"{k} {v:.1%}" for k, v in x.items()) for w, x in sh["engineered cheaper"].items()]
    lines += ["", "Share of draws in which each walk-up costs least:"]
    lines += [f"  the engineered design {k}: " + ", ".join(f"{w} {v:.1%}" for w, v in x.items()) for k, x in sh["cheapest"].items()]
    lines += ["", "10e under the draw (the engineered design against the usual electric walk-up; the owner's upkeep and replacements counted):"]
    for way in WAYS:
        lines.append(f"  pass 4's gap, allowance by the {way}: " + "; ".join(f"{k} credits {_band(s[f'gap {k}, {way}'])}" for k in TC_KEYS))
    lines += [f"  market-rate: the gap {_band(s['market gap'])}; the rent that would carry it {_band(s['market rent needed'])} a month; "
              f"the tenant's saving {_band(s['tenant saving'])} a year",
              "  the heat price that ties (USD/MWh): " + "; ".join(f"{w} {_band(s[f'heat tie {w}'])}".replace("$", "") for w in USUAL),
              "  the heat price that carries the network (USD/MWh): " + "; ".join(f"{k} {_band(s[f'heat carry {k}'])}".replace("$", "")
                                                                               for k in ("dense", "base"))]
    for k, rows in tor.items():
        w = k.removeprefix("d life ")
        lines += ["", f"What moves the engineered design less {w} over the years counted most (central {_usd(c[k])}; each input low -> high, the rest central):"]
        lines += [f"  {name}: {_usd(lo)} -> {_usd(hi)}" for name, lo, hi in rows[:12]]
    lines += ["", "The walk-ups: " + "; ".join(f"{w}, {NAMES[w]}" for w in WALKUPS)]
    return NL.join(lines)


# ---- the figure ----

PARTS = (("systems", "the systems, up front (10b)"), ("fee", "the fee's extra"), ("replace", "replacements"),
         ("energy years", "running cost (10c)"), ("upkeep years", "upkeep"), ("network years", "the heat network's share (pass 3 §4)"))
ROWS = (("engineered", "The engineered design", None), ("electric", "Usual: all electric", None), ("gas", "Usual: gas", None),
        ("central", "Usual: central hot water", None), ("engineered", "Engineered + network, dense", "dense"),
        ("engineered", "Engineered + network, base", "base"))


def figure(r: dict, path) -> None:
    """Each walk-up's cost a flat over the years counted, stacked by part, each part at its average
    over the draws (so the parts add to the average total), with P10-P90 of the draws on each total.
    A static PNG for the report, light mode."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    from .figures import GRID, INK, INK2, MUTED, SERIES, SURFACE

    s = r["summary"]
    ys = [0, 1, 2, 3, 4.5, 5.5]
    dpi, bar_px, gap_px, end_px = 150, 22, 2, 4
    fig, ax = plt.subplots(figsize=(10, 4.4), dpi=dpi, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for sp_ in ax.spines.values():
        sp_.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    total = {i: f"life {w}" if case is None else f"life engineered, network {case}" for i, (w, _, case) in enumerate(ROWS)}
    xmax = max(s[k]["p90"] for k in total.values()) * 1.36
    ax.set_xlim(0, xmax)
    ax.set_ylim(ys[-1] + 0.6, -0.6)
    fig.subplots_adjust(left=0.215, right=0.985, top=0.775, bottom=0.15)
    fig.canvas.draw()
    bb = ax.get_window_extent()
    px_x, px_y = bb.width / xmax, bb.height / (ys[-1] + 1.2)
    h = bar_px / px_y
    for i, (y, (w, label, case)) in enumerate(zip(ys, ROWS)):
        vals = {"systems": s[f"systems {w}"]["mean"], "fee": s[f"fee {w}"]["mean"], "replace": s[f"replace {w}"]["mean"],
                "energy years": s[f"energy years {w}"]["mean"], "upkeep years": s[f"upkeep years {w}"]["mean"],
                "network years": 0.0 if case is None else s[f"network years {case}"]["mean"]}
        segs = [(k, v) for k, v in vals.items() if v > 0]
        x0 = 0.0
        for j, (k, v) in enumerate(segs):
            colour = SERIES[[q[0] for q in PARTS].index(k)]
            if j == len(segs) - 1:  # the data end rounded; its left end hidden under the segment before
                rx = end_px / px_x
                ax.add_patch(FancyBboxPatch((x0 - rx, y - h / 2), v + rx, h, boxstyle=f"round,pad=0,rounding_size={rx}",
                                            mutation_aspect=px_x / px_y, facecolor=colour, edgecolor="none", zorder=1))
            else:
                ax.add_patch(Rectangle((x0, y - h / 2), v, h, facecolor=colour, edgecolor="none", zorder=2))
            if j:  # the surface gap between segments
                ax.add_patch(Rectangle((x0 - gap_px / 2 / px_x, y - h / 2 - 0.01), gap_px / px_x, h + 0.02, facecolor=SURFACE,
                                       edgecolor="none", zorder=3))
            x0 += v
        band = s[total[i]]
        ax.plot([band["p10"], band["p90"]], [y, y], color=INK, lw=1.2, zorder=4, solid_capstyle="butt")
        for x in (band["p10"], band["p90"]):
            ax.plot([x, x], [y - h * 0.32, y + h * 0.32], color=INK, lw=1.2, zorder=4)
        ax.annotate(f"${x0 / 1e3:,.0f}k  (P10-P90 ${band['p10'] / 1e3:,.0f}k-${band['p90'] / 1e3:,.0f}k)",
                    (max(x0, band["p90"]), y), xytext=(8, 0), textcoords="offset points", ha="left", va="center", fontsize=8, color=INK2)
    ax.set_yticks(ys, [lab for _, lab, _ in ROWS], color=INK2, fontsize=8.5)
    ticks = np.arange(0, xmax * 0.97, 20000)
    ax.set_xticks(ticks, [f"${t / 1e3:,.0f}k" for t in ticks])
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.95, "A flat's building systems over 20 years: the engineered design and the usual walk-ups", fontsize=11, color=INK, ha="left")
    fig.text(0.01, 0.905, f"USD 2026 a flat, the average of {r['draws']:,} draws of every input with a range; the line is P10 to P90. "
             "The data center's heat free.", fontsize=8, color=INK2, ha="left")
    handles = [Rectangle((0, 0), 1, 1, facecolor=SERIES[i], edgecolor="none") for i in range(len(PARTS))]
    fig.legend(handles, [lab for _, lab in PARTS], loc="upper left", bbox_to_anchor=(0.005, 0.885), ncol=6, frameon=False, fontsize=7.5,
               handlelength=1.0, handleheight=0.8, columnspacing=1.2, labelcolor=INK2)
    fig.text(0.01, 0.045, "Running cost and upkeep over the years at pass 3's 7%; replacements of what wears out sooner. The network share: "
             "pass 3 §4's block, dense (1,000 flats, 0.5 km main) or base (200 homes, 1.5 km).", fontsize=6.5, color=MUTED, ha="left")
    fig.text(0.01, 0.012, "Prices: 10b (list prices, BLS wages, PHFA's markups). Energy: 10c (ERA5 2005-2023; Penelec's and Peoples' tariffs). "
             "Run: brownfield baseline.", fontsize=6.5, color=MUTED, ha="left")
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
