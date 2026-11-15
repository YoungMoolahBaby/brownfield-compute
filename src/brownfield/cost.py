"""Pass 2b: what the good-neighbour features cost, and who pays and gains, per 100 MW module.

Two ledgers, because different people pay and gain:

- **The data center operator** (good neighbour minus conventional): oversized dry coolers, a
  smaller chiller plant, a berm, batteries instead of diesel; against the cooling electricity,
  water and generator upkeep it saves.
- **The heat business** (a utility, the town, or the operator): heat pumps, the main to Indiana
  borough, the town network and home connections; against heat sold at a discount to the gas it
  replaces, less the heat pumps' electricity and upkeep. The homes' savings are shown beside it.

Cooling hardware is priced only where the designs differ: industry sources say towers and
closed-circuit coolers of similar capacity cost about the same installed, so the dry coolers'
oversizing and the chiller plants are what change. Everything else comes from params/cost.yaml.
A Monte Carlo over every range gives the spread.
"""

from __future__ import annotations

import numpy as np

from . import module
from .module import GAL

MCF_MWH = 1.037 * 0.29307  # MWh per thousand cubic feet of natural gas (~1,037 Btu/cf, EIA)
H2_KWH_KG = 33.33  # lower heating value of hydrogen, kWh per kg


def annuity(rate: float, years: float) -> float:
    """Present value of $1 a year for `years` years at `rate`."""
    return (1 - (1 + rate) ** -years) / rate


def ledgers(temp: np.ndarray, p: dict) -> dict:
    a, g = module.conventional(temp, p), module.good_neighbour(temp, p)
    usd = p["cost.money.eur_usd"]
    af = annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    it = p["pass2.module.it_mw"]
    elec = p["cost.energy.elec_usd_mwh"]
    backup_mw = it * p["pass2.backup.installed_per_it_mw"]

    # The operator: capex of the good neighbour's features minus what the conventional design buys.
    k = p["pass2.noise.dry_oversize"]
    oversize = (k - 1) * it * 1.05 * 1000 * p["cost.cooling.dry_usd_kw"]  # heat to air at full load + fans
    chillers_conv = it * 1000 * p["cost.cooling.chiller_usd_kw"]
    chillers_gn = g.peak_trim_mw * 1000 * p["cost.cooling.chiller_usd_kw"]
    diesel = backup_mw * 1000 * p["cost.backup.diesel_usd_kw"]
    battery = backup_mw * 1000 * p["pass2.backup.battery_minutes"] / 60 * p["cost.backup.battery_usd_kwh"]
    capex_op = (oversize + chillers_gn + battery + p["cost.berm.usd"]) - (chillers_conv + diesel)
    saved_elec = (a.cooling_mwh - g.cooling_mwh) * elec
    saved_water = a.withdrawn_m3 / GAL / 1000 * p["cost.water.usd_per_kgal"]
    saved_diesel = backup_mw * 1000 * p["cost.backup.diesel_om_usd_kw_yr"]
    yearly_op = saved_elec + saved_water + saved_diesel

    # The heat business.
    hp = g.peak_delivered_mw * p["cost.heat.hp_eur_mw"] * 1e6 * usd
    main = p["cost.heat.main_km"] * 1000 * p["cost.heat.main_eur_m"] * usd
    network = g.town_mwh * p["cost.heat.network_eur_per_mwh_yr"] * usd
    homes = p["pass2.town.homes"] * p["cost.heat.connection_usd_home"]
    capex_heat = hp + main + network + homes
    avoided = p["cost.energy.res_gas_usd_mcf"] / (MCF_MWH * p["cost.energy.furnace_eff"])  # USD per MWh of heat
    price = avoided * (1 - p["cost.energy.heat_discount"])
    yearly_heat = g.delivered_mwh * price - g.heat_pump_mwh * elec - hp * p["cost.heat.hp_om_share"]
    home_saving = avoided * p["cost.energy.heat_discount"] * p["pass2.town.heat_per_home_mwh"]

    # The no-fossil option: hydrogen fuel cells for long outages (batteries still bridge).
    h2_kg = backup_mw * 1000 * p["cost.backup.h2_hours"] / (p["cost.backup.fuel_cell_eff"] * H2_KWH_KG)
    hydrogen = backup_mw * 1000 * p["cost.backup.fuel_cell_usd_kw"] + h2_kg * p["cost.backup.h2_storage_usd_kg"]

    # If the operator keeps its diesel anyway: only the cooling differences remain.
    capex_keep = oversize + chillers_gn + p["cost.berm.usd"] - chillers_conv
    npv_keep = (saved_elec + saved_water) * af - capex_keep
    npv_op = yearly_op * af - capex_op
    npv_heat = yearly_heat * af - capex_heat
    return {
        "npv_keep_diesel": npv_keep, "npv_both": npv_op + npv_heat,
        "capex_op": capex_op, "oversize": oversize, "chillers_conv": chillers_conv, "chillers_gn": chillers_gn,
        "diesel": diesel, "battery": battery, "berm": p["cost.berm.usd"],
        "saved_elec": saved_elec, "saved_water": saved_water, "saved_diesel": saved_diesel, "yearly_op": yearly_op,
        "npv_op": npv_op,
        "capex_heat": capex_heat, "hp": hp, "main": main, "network": network, "homes": homes,
        "avoided_usd_mwh": avoided, "price_usd_mwh": price, "yearly_heat": yearly_heat,
        "npv_heat": npv_heat, "home_saving": home_saving,
        "hydrogen": hydrogen, "h2_t": h2_kg / 1000, "peak_trim_mw": g.peak_trim_mw,
        "peak_hp_mw": g.peak_delivered_mw,
    }


def monte_carlo(temp: np.ndarray, params: dict, n: int, seed: int) -> dict[str, np.ndarray]:
    from .params import draw

    d = draw(params, n, seed)
    rows = [ledgers(temp, {k: float(v[i]) for k, v in d.items()}) for i in range(n)]
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}


# The worst corner for the good neighbour: every input at the end that hurts it.
WORST = {
    "pass2.conventional.chiller_cop": "high", "pass2.conventional.evap_fraction": "low",
    "pass2.conventional.cycles": "high", "pass2.fans.tower_kw_per_kw": "low",
    "pass2.fans.dry_kw_per_kw": "high", "pass2.good_neighbour.trim_cop": "low",
    "pass2.good_neighbour.approach_k": "high", "pass2.good_neighbour.liquid_fraction": "low",
    "pass2.good_neighbour.liquid_supply_c": "low", "pass2.good_neighbour.air_supply_c": "low",
    "pass2.good_neighbour.liquid_rise_k": "low", "pass2.good_neighbour.hp_carnot_eff": "low",
    "pass2.good_neighbour.hp_approach_k": "high", "cost.energy.elec_usd_mwh": "low",
    "cost.water.usd_per_kgal": "low", "cost.cooling.dry_usd_kw": "high", "cost.cooling.chiller_usd_kw": "high",
    "cost.backup.diesel_usd_kw": "low", "cost.backup.battery_usd_kwh": "high", "cost.backup.diesel_om_usd_kw_yr": "low",
    "pass2.backup.battery_minutes": "high", "cost.berm.usd": "high", "cost.money.discount": "high",
    "cost.money.life_yr": "low", "pass2.module.load_factor": "low", "pass2.noise.dry_oversize": "high",
}


def worst_corner(params: dict) -> dict:
    p = {k: v.value for k, v in params.items()}
    p.update({k: getattr(params[k], side) for k, side in WORST.items()})
    return p


def report(temp: np.ndarray, params: dict, n: int = 2000, seed: int = 7) -> str:
    """The cost results as Markdown: central case, Monte Carlo spread, worst corner."""
    p = {k: v.value for k, v in params.items()}
    c, w = ledgers(temp, p), ledgers(temp, worst_corner(params))
    mc = monte_carlo(temp, params, n, seed)
    M = 1e6

    def q(k):
        a = np.percentile(mc[k], [10, 50, 90]) / M
        return f"{a[0]:+,.0f} / {a[1]:+,.0f} / {a[2]:+,.0f}", f"{(mc[k] > 0).mean():.0%}"

    lines = [
        "| Per 100 MW module, million USD | Central |",
        "|---|---|",
        "| **Operator, good neighbour minus conventional** | |",
        f"| Dry coolers oversized | {c['oversize'] / M:+,.1f} |",
        f"| Trim chillers ({c['peak_trim_mw']:.0f} MW) instead of a full chiller plant | "
        f"{(c['chillers_gn'] - c['chillers_conv']) / M:+,.1f} |",
        f"| Batteries instead of diesel generators | {(c['battery'] - c['diesel']) / M:+,.1f} |",
        f"| Berm | {c['berm'] / M:+,.1f} |",
        f"| **Up-front difference** | **{c['capex_op'] / M:+,.1f}** |",
        f"| Cooling electricity saved, a year | {c['saved_elec'] / M:,.2f} |",
        f"| Water saved, a year | {c['saved_water'] / M:,.2f} |",
        f"| Generator upkeep saved, a year | {c['saved_diesel'] / M:,.2f} |",
        "| **Heat business** | |",
        f"| Heat pumps ({c['peak_hp_mw']:.0f} MW) | {c['hp'] / M:,.1f} |",
        f"| Main to Indiana borough | {c['main'] / M:,.1f} |",
        f"| Town network | {c['network'] / M:,.1f} |",
        f"| Home connections | {c['homes'] / M:,.1f} |",
        f"| **Up-front** | **{c['capex_heat'] / M:,.1f}** |",
        f"| Net heat income a year (sales at ${c['price_usd_mwh']:.0f}/MWh less pump power and upkeep) | "
        f"{c['yearly_heat'] / M:,.2f} |",
        f"| Each home saves, a year (USD) | {c['home_saving']:,.0f} |",
        "",
        "| 20-year value, million USD | Central | P10 / P50 / P90 | Positive in | Worst corner |",
        "|---|---|---|---|---|",
    ]
    for k, label in [("npv_op", "Operator, no diesel"), ("npv_keep_diesel", "Operator, keeps its diesel"),
                     ("npv_heat", "Heat business alone"), ("npv_both", "Operator + heat business")]:
        spread, pos = q(k)
        worst = f"{w[k] / M:+,.0f}" if k in ("npv_op", "npv_keep_diesel") else ""
        lines.append(f"| {label} | {c[k] / M:+,.0f} | {spread} | {pos} | {worst} |")
    h = np.percentile(mc["hydrogen"], [10, 50, 90]) / M
    lines += ["", f"Hydrogen instead of diesel for long outages: {c['hydrogen'] / M:,.0f} million USD central "
              f"({h[0]:,.0f}-{h[2]:,.0f} P10-P90; {c['h2_t']:,.0f} t of hydrogen stored), against "
              f"{c['diesel'] / M:,.0f} for diesel. Monte Carlo: {n:,} draws, seed {seed}."]
    return "\n".join(lines)


def vs_strong(temp: np.ndarray, rh: np.ndarray, p: dict) -> dict:
    """The good neighbour against the strongest conventional designs, cooling only (backup kept
    the same on both sides: dropping diesel is a choice either design can make).

    - vs liquid + towers (AI): the same loops; good neighbour adds dry cooler oversizing and a berm
      and differs in trim chillers; pays more electricity, saves the towers' water.
    - vs air + evaporative (cloud): cooling plants too different to price from public data, so
      the answer is a break-even: how much more the good neighbour's plant may cost up front for
      its energy and water savings to pay it back.
    """
    from . import module

    af = annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    elec, water = p["cost.energy.elec_usd_mwh"], p["cost.water.usd_per_kgal"]
    g = module.good_neighbour(temp, p)
    ai = module.liquid_towers(temp, rh, p)
    cloud = module.air_hall(temp, rh, p)
    it = p["pass2.module.it_mw"]
    oversize = (p["pass2.noise.dry_oversize"] - 1) * it * 1.05 * 1000 * p["cost.cooling.dry_usd_kw"]
    chillers = (g.peak_trim_mw - ai.peak_trim_mw) * 1000 * p["cost.cooling.chiller_usd_kw"]
    capex_ai = oversize + chillers + p["cost.berm.usd"]
    yearly_ai = (ai.cooling_mwh - g.cooling_mwh) * elec + ai.withdrawn_m3 / GAL / 1000 * water
    yearly_cloud = (cloud.cooling_mwh - g.cooling_mwh) * elec + cloud.withdrawn_m3 / GAL / 1000 * water
    return {
        "capex_vs_ai": capex_ai, "yearly_vs_ai": yearly_ai, "npv_vs_ai": yearly_ai * af - capex_ai,
        "extra_elec_vs_ai_mwh": g.cooling_mwh - ai.cooling_mwh, "water_saved_vs_ai_mgd": ai.withdrawn_m3 / GAL / 365 / 1e6,
        "yearly_vs_cloud": yearly_cloud, "breakeven_vs_cloud": yearly_cloud * af,
        "water_saved_vs_cloud_mgd": cloud.withdrawn_m3 / GAL / 365 / 1e6,
        "pue": {"conventional": module.conventional(temp, p).pue, "cloud": cloud.pue, "ai": ai.pue, "gn": g.pue},
        "wue": {"conventional": module.conventional(temp, p).wue, "cloud": cloud.wue, "ai": ai.wue},
    }


def strong_report(temp: np.ndarray, rh: np.ndarray, params: dict, n: int = 2000, seed: int = 7) -> str:
    """The good neighbour against the strongest conventional designs, as Markdown."""
    from .params import draw

    p = {k: v.value for k, v in params.items()}
    c, w = vs_strong(temp, rh, p), vs_strong(temp, rh, worst_corner(params))
    d = draw(params, n, seed)
    rows = [vs_strong(temp, rh, {k: float(v[i]) for k, v in d.items()}) for i in range(n)]
    M = 1e6

    def q(k):
        a = np.array([r[k] for r in rows])
        x = np.percentile(a, [10, 50, 90]) / M
        return f"{x[0]:+,.1f} / {x[1]:+,.1f} / {x[2]:+,.1f}", f"{(a > 0).mean():.0%}"

    pue, wue = c["pue"], c["wue"]
    s_ai, pos_ai = q("npv_vs_ai")
    s_cl, pos_cl = q("breakeven_vs_cloud")
    return "\n".join([
        "| Per 100 MW module | PUE (IT + cooling) | Water |",
        "|---|---|---|",
        f"| Old conventional (water-cooled chillers + towers) | {pue['conventional']:.3f} | {wue['conventional']:.2f} L/kWh |",
        f"| Strong cloud (outside air + evaporative pads) | {pue['cloud']:.3f} | {wue['cloud']:.3f} L/kWh |",
        f"| Strong AI (liquid loop + cooling towers) | {pue['ai']:.3f} | {wue['ai']:.2f} L/kWh |",
        f"| Good neighbour (liquid loop + dry coolers + heat pumps) | {pue['gn']:.3f} | none |",
        "",
        "| Good neighbour against | Central (million USD) | P10 / P50 / P90 | Good neighbour ahead in | Worst corner |",
        "|---|---|---|---|---|",
        f"| Strong AI, 20-year value (up front {c['capex_vs_ai'] / M:+,.1f}; a year {c['yearly_vs_ai'] / M:+,.2f}) | "
        f"{c['npv_vs_ai'] / M:+,.1f} | {s_ai} | {pos_ai} | {w['npv_vs_ai'] / M:+,.1f} |",
        f"| Strong cloud, most its cooling plant may cost extra up front and still break even | "
        f"{c['breakeven_vs_cloud'] / M:+,.1f} | {s_cl} | {pos_cl} | {w['breakeven_vs_cloud'] / M:+,.1f} |",
        "",
        f"Against the strong AI hall the good neighbour spends {c['extra_elec_vs_ai_mwh'] / 1e3:,.1f} GWh a year more "
        f"electricity and saves {c['water_saved_vs_ai_mgd']:.2f} million gallons of water a day. Backup is the same "
        f"on both sides here. Monte Carlo: {n:,} draws, seed {seed}.",
    ])


AI_CASES = [
    ("Today's AI racks: 40 C water, 80% load", {}),
    ("AI training: 40 C water, 95% load", {"pass2.module.load_factor": 0.95}),
    ("Chips that need colder water: 32 C, 95% load",
     {"pass2.module.load_factor": 0.95, "pass2.good_neighbour.liquid_supply_c": 32.0}),
    ("Chips that take warm water: 45 C, 95% load",
     {"pass2.module.load_factor": 0.95, "pass2.good_neighbour.liquid_supply_c": 45.0}),
]


def ai_report(temp: np.ndarray, rh: np.ndarray, params: dict) -> str:
    """The good neighbour on AI loads against the AI alternative (same liquid loop, cooling
    towers), central values: what changes with load and with the coolant temperature the chips
    accept. Towers cool toward the wet bulb, so a colder supply costs them little; dry coolers
    cool toward the dry bulb, so it costs them trim hours and the heat pumps a lower COP."""
    from . import module

    base = {k: v.value for k, v in params.items()}
    g_ = "pass2.good_neighbour."
    lines = ["| Case | Good neighbour PUE | AI towers PUE | Heat pump COP | Heat reused | Water saved, million gal/day "
             "| Good neighbour vs AI towers, 20 years, million USD | Electricity bill a year, million USD |",
             "|---|---|---|---|---|---|---|---|"]
    for name, ov in AI_CASES:
        p = dict(base, **ov)
        g, ai = module.good_neighbour(temp, p), module.liquid_towers(temp, rh, p)
        cop = module.heat_pump_cop(p[g_ + "liquid_supply_c"] + p[g_ + "liquid_rise_k"], p[g_ + "dh_supply_c"],
                                   p[g_ + "hp_approach_k"], p[g_ + "hp_carnot_eff"])
        c = vs_strong(temp, rh, p)
        bill = (g.it_mwh + g.cooling_mwh) * p["cost.energy.elec_usd_mwh"] / 1e6
        lines.append(f"| {name} | {g.pue:.3f} | {ai.pue:.3f} | {cop:.2f} | {g.heat_reused_mwh / g.heat_out_mwh:.0%} | "
                     f"{c['water_saved_vs_ai_mgd']:.2f} | {c['npv_vs_ai'] / 1e6:+,.1f} | {bill:,.0f} |")
    return "\n".join(lines)
