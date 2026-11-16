"""Pass 3d: winter food on the data center's warm water (D10).

Glasshouses beside the hall, heated straight off the liquid loop's return (~50 C, no heat pump),
lit where the sun falls short of the crop's daily light target. Hour by hour over the PVGIS
typical year at Homer City, per square metre of floor:

- Light: natural light inside = global horizontal irradiance x its PAR photon content x the
  cover's transmission. Lamps make up each day's shortfall against the crop's target, in the
  dimmest hours of its photoperiod.
- Heat: the cover's loss U x cover ratio x (set - outdoor), with the energy screen closed in the
  dark (its own U), plus air leakage, less the sensible share of the sun and the lamps. Never below
  zero: a surplus is vented.
- Supply: the liquid loop's heat, after pass 2's town network takes its share (pass 2's 10 ha
  placeholder greenhouse is replaced by these). Heating pipe sized for 50 C water caps what it can
  give in an hour; a buffer tank carries spare heat into the night; a gas boiler, running hotter
  water through the same pipe, covers the rest, reported.
- Yield: light received (capped where growers shade) x the crop's light use efficiency, checked
  against known lit and unlit yields.

The conventional case is the same houses on a gas boiler, with the same lamps. Pass 2's module.py
and its published numbers are unchanged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import module

AIR_W_M3K = 0.33  # W per m3/h of air per K (rho cp of air / 3600)
WATER_KWH_M3K = 1.163  # kWh per m3 of water per K
CROPS = ("lettuce", "tomato")
COVERS = ("glass", "poly")


def local(wx: dict, utc_offset: int) -> dict:
    """The typical year re-indexed to local standard time, so each block of 24 is a local day.
    (The few hours that wrap from 31 December to 1 January don't matter in a typical year.)"""
    return {k: np.roll(v, -utc_offset) if k != "hour_utc" else (np.roll(v, -utc_offset) + utc_offset) % 24
            for k, v in wx.items()}


def lamps(ghi: np.ndarray, p: dict, crop: str, cover: str) -> tuple[np.ndarray, np.ndarray]:
    """Hourly natural and lamp light inside (mol/m2 in each hour). Each day the lamps make up the
    shortfall against the crop's target in the dimmest hours of its photoperiod, centred on noon."""
    l = "food.light."
    nat = ghi * p[l + "par_per_w"] * p[l + "trans_" + cover] * 3600.0 / 1e6
    per_hour = p[l + "lamp_ppfd_" + crop] * 3600.0 / 1e6
    period = int(p[l + "photoperiod_" + crop])
    window = np.arange(12 - period // 2, 12 - period // 2 + period) % 24
    lamp = np.zeros_like(nat)
    for d in range(len(ghi) // 24):
        sl = slice(24 * d, 24 * d + 24)
        short = p[l + "dli_" + crop] - nat[sl].sum()
        if short <= 0:
            continue
        need = min(short / per_hour, float(period))
        hours = window[np.argsort(ghi[sl][window], kind="stable")]
        day = np.zeros(24)
        day[hours[: int(need)]] = 1.0
        if need % 1 and int(need) < period:
            day[hours[int(need)]] = need % 1
        lamp[sl] = day * per_hour
    return nat, lamp


def house(wx: dict, p: dict, crop: str, cover: str) -> dict:
    """Hourly heat demand and lamp power per m2 of floor (W/m2), and the light received."""
    l, h = "food.light.", "food.heat."
    ghi, temp = wx["ghi"], wx["t"]
    nat, lamp_mol = lamps(ghi, p, crop, cover)
    lamp_w = lamp_mol / (3600.0 / 1e6) / p[l + "led_umol_j"]
    lit = (ghi > 0) | (lamp_w > 0)
    set_c = np.where(lit, p[h + f"set_day_{crop}"], p[h + f"set_night_{crop}"])
    u_cover = np.where(ghi > 0, p[h + "u_" + cover], p[h + "u_" + cover + "_screen"])
    u = u_cover * p["pass2.greenhouse.cover_ratio"] + AIR_W_M3K * p[h + "ach"] * p[h + "height_m"]
    loss = u * (set_c - temp)
    gain = p[h + "sensible_share"] * (ghi * p[l + "trans_" + cover] + lamp_w)
    return {"heat_w": np.clip(loss - gain, 0.0, None), "lamp_w": lamp_w, "nat_mol": nat, "lamp_mol": lamp_mol, "set_c": set_c}


def yield_kg_m2(hs: dict, p: dict, crop: str) -> float:
    """A year's harvest per m2: the daily light received, capped where growers shade, x the crop's
    light use efficiency x the share of the year in crop."""
    y = "food.yield."
    daily = (hs["nat_mol"] + hs["lamp_mol"]).reshape(-1, 24).sum(axis=1)
    used = np.minimum(daily, p[y + "dli_cap_" + crop]).sum()
    return used * p[y + "lue_" + crop] * p[y + "in_crop_" + crop] / 1000.0


def dc_heat(temp: np.ndarray, p: dict) -> np.ndarray:
    """Heat on the liquid loop's return (MW) after pass 2's town network takes its share through
    the heat pumps (module.good_neighbour's own sums, without its placeholder greenhouse)."""
    g = "pass2.good_neighbour."
    liquid = p["pass2.module.it_mw"] * p["pass2.module.load_factor"] * p[g + "liquid_fraction"]
    cop = module.heat_pump_cop(p[g + "liquid_supply_c"] + p[g + "liquid_rise_k"], p[g + "dh_supply_c"],
                               p[g + "hp_approach_k"], p[g + "hp_carnot_eff"])
    town = module.town_demand(temp, p)
    return liquid - np.minimum(town * (cop - 1.0) / cop, liquid)


@dataclass
class Run:
    crop: str
    cover: str
    ha: float
    demand_mwh: float  # heat the houses need
    dc_mwh: float  # of it from the data center (directly and through the tank)
    backup_mwh: float  # from the gas boiler, in all
    backup_hours: int
    pipe_mwh: float  # of the boiler's, what 50 C water couldn't push through the pipe (more pipe would fix it)
    short_mwh: float  # of the boiler's, what the module didn't have to spare (the area's limit)
    lamp_mwh: float
    lamp_peak_mw: float
    food_t: float

    @property
    def backup_share(self) -> float:
        return self.backup_mwh / self.demand_mwh if self.demand_mwh else 0.0

    @property
    def short_share(self) -> float:
        return self.short_mwh / self.demand_mwh if self.demand_mwh else 0.0


def pipe_cap_w(hs: dict, p: dict) -> np.ndarray:
    """Most the heating pipe can give per m2 (W) on the loop's water: AHDB's 30 W/m2 per 10 K for
    standard rail, scaled by the pipe laid, at the mean of the loop's return and supply."""
    h, g = "food.heat.", "pass2.good_neighbour."
    mean_pipe = (p[g + "liquid_supply_c"] + p[g + "liquid_supply_c"] + p[g + "liquid_rise_k"]) / 2.0
    per_k = p[h + "pipe_w_m2_10k"] / 10.0 * p[h + "pipe_m_m2"] / 1.25
    return per_k * np.clip(mean_pipe - hs["set_c"], 0.0, None)


def simulate(hs: dict, avail: np.ndarray, p: dict, crop: str, cover: str, ha: float) -> Run:
    """The houses' heat against what the data center has spare, hour by hour, with the tank and the
    pipe's limit on 50 C water."""
    area = ha * 1e4
    demand = hs["heat_w"] * area / 1e6  # MW
    pipe = pipe_cap_w(hs, p) * area / 1e6  # MW the loop's water can put in through the pipe
    rise = p["pass2.good_neighbour.liquid_rise_k"]
    cap = p["food.heat.buffer_m3_ha"] * ha * WATER_KWH_M3K * rise / 1000.0  # MWh, stored 50 C down to 40 C
    store, dc, pipe_short, heat_short, short_hours = cap, 0.0, 0.0, 0.0, 0
    for need, have, lim in zip(demand, avail, pipe):
        want = min(need, lim)  # what the loop's water could deliver this hour
        if have >= want:
            got = want
            store = min(cap, store + have - want)
        else:
            draw = min(store, want - have)
            store -= draw
            got = have + draw
        dc += got
        pipe_short += need - want
        heat_short += want - got
        if need - got > 1e-9:
            short_hours += 1
    lamp_mw = hs["lamp_w"] * area / 1e6
    food = yield_kg_m2(hs, p, crop) * area / 1000.0
    return Run(crop, cover, ha, float(demand.sum()), dc, pipe_short + heat_short, short_hours, pipe_short, heat_short,
               float(lamp_mw.sum()), float(lamp_mw.max()), food)


def design_ha(hs: dict, avail: np.ndarray, p: dict, crop: str, cover: str) -> float:
    """The largest area (to 0.5 ha) whose heat the data center has to spare, but for a set share
    (the boiler's top-up where the pipe falls short on 50 C water is reported apart)."""
    lo, hi = 0.5, 400.0
    if simulate(hs, avail, p, crop, cover, lo).short_share > p["food.design.backup_max_share"]:
        return 0.0
    while hi - lo > 0.5:
        mid = (lo + hi) / 2
        if simulate(hs, avail, p, crop, cover, mid).short_share <= p["food.design.backup_max_share"]:
            lo = mid
        else:
            hi = mid
    return math.floor(lo * 2) / 2


# --- The houses' year, their money and carbon ----------------------------------------------------

def economics(run: Run, p: dict, cover: str) -> dict:
    """Per year, in USD: what the houses cost to build (annualised), to run and to heat, against
    what the food sells for; and the same houses heated by a gas boiler (the conventional case)."""
    from .cost import annuity

    c = "food.cost."
    area = run.ha * 1e4
    build = area * (p[c + "house_usd_m2"] + p["food.light.lamp_ppfd_" + run.crop] * p[c + "lamps_usd_per_umol_s"])
    yearly_build = build / annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    gas = p[c + "gas_usd_mwh"] / p[c + "boiler_eff"]  # USD per MWh of heat from the boiler
    lamps = run.lamp_mwh * p["cost.energy.elec_usd_mwh"]
    other = jobs(run, p) * p[c + "wage_usd_yr"]  # wages only: the margin leaves out every other running cost
    revenue = run.food_t * 1000.0 * p[c + "price_usd_kg_" + run.crop]
    heat_here = run.backup_mwh * gas
    heat_conv = run.demand_mwh * gas
    co2 = p["food.carbon.gas_kg_mwh"] / p[c + "boiler_eff"] / 1000.0  # t CO2 per MWh of boiler heat
    return {"build_usd": build, "build_usd_yr": yearly_build, "lamps_usd_yr": lamps, "wages_usd_yr": other,
            "heat_usd_yr": heat_here, "heat_conv_usd_yr": heat_conv, "revenue_usd_yr": revenue,
            "margin_usd_yr": revenue - yearly_build - lamps - other - heat_here,
            "margin_conv_usd_yr": revenue - yearly_build - lamps - other - heat_conv,
            "co2_t_yr": run.backup_mwh * co2, "co2_conv_t_yr": run.demand_mwh * co2}


def jobs(run: Run, p: dict) -> float:
    return run.ha * p["food.jobs.per_ha_" + run.crop]


def people_fed(run: Run, p: dict) -> float:
    """How many people's yearly lettuce (or fresh tomatoes) the harvest covers (USDA ERS)."""
    return run.food_t * 1000.0 / p["food.market.kg_person_" + run.crop]


def fusion_option(hs: dict, p: dict, crop: str, cover: str) -> dict:
    """Pass 5's option, not the plan: a stellarator on the site. Its power covers the lamps; its
    rejected heat, lifted by heat pumps to the houses' supply temperature, could carry more houses."""
    f = "food.fusion."
    net = p[f + "net_mwe"]
    thermal = net / p[f + "efficiency"]
    rejected = thermal - net
    g = "pass2.good_neighbour."
    cop = module.heat_pump_cop(p[f + "reject_c"], p["food.heat.supply_c"], p[g + "hp_approach_k"], p[g + "hp_carnot_eff"])
    usable = rejected * p[f + "usable_share"]
    delivered = usable * cop / (cop - 1.0)  # MW of heat at the houses' supply temperature
    avail = np.full(len(hs["heat_w"]), delivered)
    ha = design_ha(hs, avail, p, crop, cover)
    run = simulate(hs, avail, p, crop, cover, ha) if ha > 0 else None
    return {"net_mwe": net, "thermal_mw": thermal, "rejected_mw": rejected, "cop": cop, "delivered_mw": delivered,
            "hp_mw": delivered / cop, "ha": ha, "run": run}


# --- Known cases: the same model at Dutch growers' sites, against their published numbers ---------

WESTLAND = (52.00, 4.20, 1)  # lat, lon, UTC offset: the Netherlands' greenhouse district
LEAMINGTON = (42.05, -82.60, -5)  # Ontario's greenhouse district


def known_case(p: dict, wx_on: dict, wx_nl: dict) -> dict:
    """Tomatoes in glass, by this model: at Leamington, unlit and lit, against the Ontario growers'
    yield and heat (an independent check; the light use efficiency was set from Dutch yields); at
    Westland, lit over unlit, against the Dutch ratio. `wx_*` are local-time years."""
    out = {}
    for site, wx in (("on", wx_on), ("nl", wx_nl)):
        for lit in (False, True):
            q = dict(p) if lit else dict(p, **{"food.light.dli_tomato": 0.0})
            hs = house(wx, q, "tomato", "glass")
            out[(site, lit)] = {"kg_m2": yield_kg_m2(hs, q, "tomato"), "heat_mj_m2": hs["heat_w"].sum() * 3600 / 1e6,
                                "lamp_kwh_m2": hs["lamp_w"].sum() / 1000.0}
    k = "food.known."
    out["published"] = {key: (p[k + key], q_range(p, k + key)) for key in ("on_tomato_kg_m2", "on_tomato_heat_mj_m2", "lit_gain")}
    return out


_RANGES: dict = {}


def q_range(p: dict, key: str) -> tuple[float, float]:
    """A parameter's (low, high), registered by `set_ranges` (values() keeps only the central value)."""
    return _RANGES.get(key, (p[key], p[key]))


def set_ranges(params: dict) -> None:
    _RANGES.update({k: (v.low, v.high) for k, v in params.items() if k.startswith("food.")})


# --- The design and the report ------------------------------------------------------------------

DESIGN = ("tomato", "glass")  # the case drawn and reported first; the report says why


def analyse(p: dict, wx_site: dict, utc_offset: int = -5) -> dict:
    wx = local(wx_site, utc_offset)
    temp = wx["t"]
    avail = dc_heat(temp, p)
    gn = module.good_neighbour(temp, dict(p, **{"pass2.greenhouse.hectares": 0.0}))
    out = {"avail": avail, "heat_out_mwh": gn.heat_out_mwh, "it_mwh": gn.it_mwh, "cooling_mwh": gn.cooling_mwh,
           "town_hp_mwh": gn.heat_pump_mwh, "town_mwh": gn.town_mwh, "wx": wx, "cases": {}}
    for crop in CROPS:
        for cover in COVERS:
            hs = house(wx, p, crop, cover)
            ha = design_ha(hs, avail, p, crop, cover)
            run = simulate(hs, avail, p, crop, cover, ha)
            out["cases"][(crop, cover)] = {"hs": hs, "ha": ha, "run": run, "money": economics(run, p, cover)}
    crop, cover = DESIGN
    hs = out["cases"][DESIGN]["hs"]
    out["sweep"] = [simulate(hs, avail, p, crop, cover, ha) for ha in (5.0, 10.0, 25.0, 50.0, 100.0)]
    out["fusion"] = fusion_option(hs, p, crop, cover)
    return out


def monthly_dli(wx: dict, p: dict, cover: str) -> np.ndarray:
    """Mean daily light (mol/m2/day) outside and inside the cover, by month."""
    nat = wx["ghi"] * p["food.light.par_per_w"] * 3600.0 / 1e6
    days = nat.reshape(-1, 24).sum(axis=1)
    edges = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    out = np.array([days[edges[m]:edges[m + 1]].mean() for m in range(12)])
    return np.vstack([out, out * p["food.light.trans_" + cover]])


def report(p: dict, a: dict, known: dict | None = None) -> str:
    L = []
    heat_out = a["heat_out_mwh"]
    it_mw = p["pass2.module.it_mw"]
    L += ["**Light at Homer City** (PVGIS typical year; mol of growing light per m2 a day)", "",
          "| | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |", "|---|" + "---|" * 12]
    dli = monthly_dli(a["wx"], p, "glass")
    L.append("| Outside | " + " | ".join(f"{v:.0f}" for v in dli[0]) + " |")
    L.append("| Inside glass | " + " | ".join(f"{v:.0f}" for v in dli[1]) + " |")
    L += ["", f"Targets: lettuce {p['food.light.dli_lettuce']:g}, tomato {p['food.light.dli_tomato']:g} mol/m2/day.", ""]

    L += ["**The design point for each crop and cover**: the largest area whose heat one module has to spare, short by "
          f"no more than {p['food.design.backup_max_share']:.0%} of the houses' heat. Boiler: all its top-up (of which, where "
          "50 C water can't push enough through the pipe on the coldest nights).", "",
          "| Crop, cover | Area | Module heat used | Boiler (of it pipe-limited; hours) | Lamps a year | Lamps at peak | Food a year | "
          "People's yearly supply | Jobs | To build | Margin a year (on gas) | CO2 a year (on gas) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (crop, cover), c in a["cases"].items():
        r, m = c["run"], c["money"]
        L.append(f"| {crop}, {cover} | {r.ha:g} ha | {r.dc_mwh / heat_out:.0%} ({r.dc_mwh / 1e3:,.0f} GWh) | "
                 f"{r.backup_share:.1%} ({r.pipe_mwh / r.demand_mwh:.1%}; {r.backup_hours:,} h) | {r.lamp_mwh / 1e3:,.0f} GWh | {r.lamp_peak_mw:,.0f} MW "
                 f"({r.lamp_peak_mw / it_mw:.0%} of IT) | {r.food_t:,.0f} t | {people_fed(r, p):,.0f} | "
                 f"{jobs(r, p):,.0f} | ${m['build_usd'] / 1e6:,.0f}M | "
                 f"${m['margin_usd_yr'] / 1e6:,.1f}M (${m['margin_conv_usd_yr'] / 1e6:,.1f}M) | "
                 f"{m['co2_t_yr']:,.0f} t ({m['co2_conv_t_yr']:,.0f} t) |")

    crop, cover = DESIGN
    L += ["", f"**Area against heat** ({crop}, {cover})", "",
          "| Area | Heat the houses need | From the data center | Share of the module's heat | Boiler: pipe-limited | Boiler: module short | Lamps at peak |",
          "|---|---|---|---|---|---|---|"]
    for r in a["sweep"]:
        L.append(f"| {r.ha:g} ha | {r.demand_mwh / 1e3:,.0f} GWh | {r.dc_mwh / 1e3:,.0f} GWh | {r.dc_mwh / heat_out:.0%} | "
                 f"{r.pipe_mwh / r.demand_mwh:.0%} | {r.short_share:.0%} | {r.lamp_peak_mw:,.0f} MW |")

    r = a["cases"][DESIGN]["run"]
    L += ["", f"**Where every MW goes** (one module, a year; the design point, {r.ha:g} ha of {crop})", "",
          "| | GWh a year | Average MW |", "|---|---|---|"]
    rows = [("Computers (IT)", a["it_mwh"]), ("Cooling (trim chillers, fans, pumps)", a["cooling_mwh"]),
            ("Heat pumps for the town network (pass 2)", a["town_hp_mwh"]), ("Grow lights", r.lamp_mwh)]
    for name, mwh in rows:
        L.append(f"| {name} | {mwh / 1e3:,.0f} | {mwh / 8760:,.1f} |")
    total = sum(m for _, m in rows)
    L.append(f"| **Electricity in all** | **{total / 1e3:,.0f}** | **{total / 8760:,.1f}** |")
    L.append(f"| Heat to the town | {a['town_mwh'] / 1e3:,.0f} | {a['town_mwh'] / 8760:,.1f} |")
    L.append(f"| Heat to the food houses | {r.dc_mwh / 1e3:,.0f} | {r.dc_mwh / 8760:,.1f} |")
    let_go = heat_out - (a["town_mwh"] - a["town_hp_mwh"]) - r.dc_mwh
    L.append(f"| Heat still let go to the air | {let_go / 1e3:,.0f} | {let_go / 8760:,.1f} |")

    f = a["fusion"]
    L += ["", "**Pass 5's option, not the plan: a stellarator on the site** (Infinity Two class; design targets, `conf: low`)", "",
          f"- {f['net_mwe']:g} MW of electricity from {f['thermal_mw']:,.0f} MW of heat; {f['rejected_mw']:,.0f} MW let go at about "
          f"{p['food.fusion.reject_c']:g} C.",
          f"- The design point's lamps peak at {r.lamp_peak_mw:,.0f} MW: {r.lamp_peak_mw / f['net_mwe']:.0%} of its output.",
          f"- Heat pumps lifting {p['food.fusion.usable_share']:.0%} of its rejected heat to {p['food.heat.supply_c']:g} C (COP {f['cop']:.1f}, "
          f"{f['hp_mw']:,.0f} MW of electricity) would carry about {f['ha']:g} ha more of {crop} under the same rule."]
    if known:
        pub = known["published"]
        rng = lambda key, f: f"{pub[key][0]:{f}} ({pub[key][1][0]:{f}}-{pub[key][1][1]:{f}})"
        on0, on1, nl0, nl1 = known[("on", False)], known[("on", True)], known[("nl", False)], known[("nl", True)]
        L += ["", "**Known cases: tomatoes in glass, this model on PVGIS weather at the growers' own districts**", "",
              "| | This model | Published |", "|---|---|---|",
              f"| Leamington, Ontario: yield, kg/m2 a year (unlit / lit) | {on0['kg_m2']:.0f} / {on1['kg_m2']:.0f} | "
              f"{rng('on_tomato_kg_m2', 'g')} (8 growers, mostly unlit) |",
              f"| Leamington: heat, MJ/m2 a year (unlit) | {on0['heat_mj_m2']:,.0f} | {rng('on_tomato_heat_mj_m2', ',.0f')} |",
              f"| Westland, the Netherlands: lit over unlit yield | {nl1['kg_m2'] / nl0['kg_m2']:.2f} | {rng('lit_gain', '.2f')} |"]
    return "\n".join(L)


# --- The arboretum's species and the spec for forge ------------------------------------------------

SPECIES = [  # name, params key, form, water demand (setback class), autumn colour (rendering only)
    ("white oak", "white_oak", "round", "high", [0.56, 0.34, 0.17]),
    ("red oak", "red_oak", "round", "high", [0.55, 0.19, 0.10]),
    ("sugar maple", "sugar_maple", "round", "moderate", [0.84, 0.38, 0.12]),
    ("black cherry", "black_cherry", "round", "moderate", [0.78, 0.52, 0.18]),
    ("tulip poplar", "tulip_poplar", "oval", "moderate", [0.86, 0.70, 0.24]),
    ("sycamore", "sycamore", "oval", "moderate", [0.68, 0.58, 0.30]),
    ("eastern hemlock", "eastern_hemlock", "cone", "moderate", [0.15, 0.27, 0.19]),
    ("eastern white pine", "white_pine", "cone", "moderate", [0.22, 0.34, 0.25]),
]


def setback_m(p: dict, key: str, demand: str) -> float:
    """How far a species stands from any foundation: its mature height x its water-demand factor."""
    t = "food.trees."
    return p[t + "height_" + key] * p[t + "setback_" + demand]


def forge_spec(p: dict, a: dict) -> dict:
    crop, cover = DESIGN
    r = a["cases"][DESIGN]["run"]
    trees = [{"name": n, "height_m": p["food.trees.height_" + k] * p["food.trees.drawn_share"], "form": form, "colour": col,
              "setback_m": setback_m(p, k, dem), "count": int(p["food.trees.per_grove"])} for n, k, form, dem, col in SPECIES]
    return {"source": "brownfield food (pass 3d): the design point and the arboretum, for forge `garden`",
            "forge": {"ha": r.ha, "crop": crop, "cover": cover, "bay_m": 4.0, "gutter_m": 6.0, "roof_deg": 22.0, "trees": trees}}
