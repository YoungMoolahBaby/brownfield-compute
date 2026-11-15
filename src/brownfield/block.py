"""Pass 3, step 3: a block of new homes on the data center's warm loop, against each home heating
itself. Per dwelling, 20-year cost in today's dollars (capex + discounted running costs), cooling
included in every option so they compare like for like.

- **A, the loop**: radiant floor, a connection, a small booster heat pump for hot water, an air
  conditioner (a radiant slab can't cool), and a share of the street network, the main from the
  campus and the heat exchanger there. The data center's heat is counted as free; the cooler water
  coming back from the homes helps the data center a little, which isn't credited.
- **B, a heat pump**: a ducted cold-climate air-source heat pump (heats and cools) and a heat pump
  water heater.
- **C, gas**: a furnace with ducts, a gas water heater, a gas line, and an air conditioner.

Every dwelling uses the first house's heat (step 2); townhouses and apartments would use a little
less (shared walls), which narrows the running-cost gaps a bit and isn't modelled.
"""

from __future__ import annotations

import numpy as np

from .cost import MCF_MWH, annuity

DENSITIES = {"detached": "pass3.density.detached_m", "townhouse": "pass3.density.townhouse_m",
             "apartment": "pass3.density.apartment_m"}


def per_home(p: dict, space_mwh: float, dhw_mwh: float, design_kw: float, floor_m2: float, frontage_m: float) -> dict:
    af = annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    res, ind = p["pass3.prices.res_elec_usd_mwh"], p["cost.energy.elec_usd_mwh"]
    b, lh = "pass3.block.", "pass3.loop_home."
    floor_ft2 = floor_m2 / 0.09290304

    street = frontage_m * p[b + "street_usd_m"]
    main = p[b + "main_km"] * 1000 * p[b + "main_usd_m"] / p[b + "homes"]
    plant = p[b + "plant_usd_kw"] * design_kw
    network = street + main + plant
    a_capex = (p[lh + "radiant_usd_ft2"] * floor_ft2 + p[lh + "hiu_usd"] + p[lh + "booster_usd"] + p[lh + "ac_usd"]
               + network)
    a_year = (dhw_mwh / p[lh + "booster_cop"] * res + p[b + "pump_share"] * (space_mwh + dhw_mwh) * ind
              + p[b + "om_share"] * network)

    hp = "pass3.heat_pump_home."
    b_capex = p[hp + "ashp_usd"] + p[hp + "hpwh_usd"]
    b_year = (space_mwh / p[hp + "scop"] + dhw_mwh / p[hp + "hpwh_uef"]) * res

    g = "pass3.gas_home."
    c_capex = p[g + "furnace_usd"] + p[g + "gas_line_usd"] + p[g + "wh_usd"] + p[lh + "ac_usd"]
    gas_mwh = space_mwh / p[g + "furnace_eff"] + dhw_mwh / p[g + "wh_uef"]
    c_year = gas_mwh / MCF_MWH * p["cost.energy.res_gas_usd_mcf"] + 12 * p[g + "fixed_usd_month"]

    out = {"A_capex": a_capex, "A_year": a_year, "A": a_capex + a_year * af,
           "B_capex": b_capex, "B_year": b_year, "B": b_capex + b_year * af,
           "C_capex": c_capex, "C_year": c_year, "C": c_capex + c_year * af,
           "street": street, "main": main, "plant": plant, "network": network}
    best_other = min(out["B"], out["C"])
    out["A_minus_best"] = out["A"] - best_other
    # The street price per metre at which the loop ties with the cheaper alternative (the street
    # network's upkeep scales with it too, while the cheaper alternative stays put).
    out["street_breakeven_usd_m"] = p[b + "street_usd_m"] - out["A_minus_best"] / (frontage_m * (1 + p[b + "om_share"] * af))
    return out


def run(p: dict, h: dict, floor_m2: float) -> dict[str, dict]:
    return {name: per_home(p, h["space_mwh"], h["hot_water_mwh"], h["design_kw"], floor_m2, p[key])
            for name, key in DENSITIES.items()}


def monte_carlo(params: dict, house_fn, floor_m2: float, n: int = 2000, seed: int = 7) -> dict[str, np.ndarray]:
    """house_fn(p) -> the house's heat dict for that draw (its envelope inputs vary too)."""
    from .params import draw

    d = draw(params, n, seed)
    rows = {name: [] for name in DENSITIES}
    for i in range(n):
        p = {k: float(v[i]) for k, v in d.items()}
        res = run(p, house_fn(p), floor_m2)
        for name in DENSITIES:
            rows[name].append(res[name]["A_minus_best"])
    return {k: np.array(v) for k, v in rows.items()}


def report(central: dict[str, dict], mc: dict[str, np.ndarray], p: dict) -> str:
    lines = ["| Per dwelling, 20 years, USD | Detached | Townhouse | Apartment |", "|---|---|---|---|"]
    rows = [("A, the loop: up front", "A_capex"), ("  of it, the street network", "street"),
            ("  of it, the main from the campus", "main"), ("  of it, the exchanger at the data center", "plant"),
            ("A: running a year", "A_year"), ("**A, the loop: 20-year cost**", "A"),
            ("B, heat pump: up front", "B_capex"), ("B: running a year", "B_year"), ("**B, heat pump: 20-year cost**", "B"),
            ("C, gas: up front", "C_capex"), ("C: running a year", "C_year"), ("**C, gas: 20-year cost**", "C"),
            ("**The loop minus the cheaper of B and C**", "A_minus_best"),
            ("Street price per metre at which the loop ties", "street_breakeven_usd_m")]
    for label, k in rows:
        lines.append(f"| {label} | " + " | ".join(f"{central[d][k]:,.0f}" for d in DENSITIES) + " |")
    lines += ["", "| Monte Carlo (2,000 draws) | Detached | Townhouse | Apartment |", "|---|---|---|---|"]
    lines.append("| The loop minus the cheaper alternative, P10 / P50 / P90 | " + " | ".join(
        "{:+,.0f} / {:+,.0f} / {:+,.0f}".format(*np.percentile(mc[d], [10, 50, 90])) for d in DENSITIES) + " |")
    lines.append("| The loop cheapest in | " + " | ".join(f"{(mc[d] < 0).mean():.0%}" for d in DENSITIES) + " |")
    lines += ["", f"Street network at ${p['pass3.block.street_usd_m']:,.0f}/m; {p['pass3.block.homes']:,.0f} homes on "
              f"a {p['pass3.block.main_km']:g} km main; frontage per dwelling {p['pass3.density.detached_m']:g} / "
              f"{p['pass3.density.townhouse_m']:g} / {p['pass3.density.apartment_m']:g} m."]
    return "\n".join(lines)


GRID_HOMES = (100, 200, 500, 1000, 2000)
GRID_KM = (0.25, 0.5, 1.0, 1.5, 3.0)


def grid(p: dict, h: dict, floor_m2: float, density: str = "apartment") -> str:
    """The loop minus the cheaper alternative across block size and main length (central inputs)."""
    lines = [f"| {density.capitalize()}s: homes on the block | " + " | ".join(f"main {km:g} km" for km in GRID_KM) + " |",
             "|---|" + "---|" * len(GRID_KM)]
    for n in GRID_HOMES:
        cells = []
        for km in GRID_KM:
            q = dict(p, **{"pass3.block.homes": n, "pass3.block.main_km": km})
            v = run(q, h, floor_m2)[density]["A_minus_best"]
            cells.append(f"**{v:+,.0f}**" if v < 0 else f"{v:+,.0f}")
        lines.append(f"| {n:,} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
