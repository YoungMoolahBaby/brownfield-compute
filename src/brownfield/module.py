"""Pass 2: one data center module, two designs, hour by hour over the site's typical year.

- **Conventional**: water-cooled. Chillers move the IT heat to evaporative cooling towers, which
  reject it (plus the chillers' own work) by evaporating water; blowdown keeps the minerals down.
- **Good neighbour**: direct-to-chip liquid cooling on a warm-water loop (W40), the rest on an
  air-side chilled loop; dry coolers reject heat without water, small chillers trim the hottest
  hours (power, not water); heat pumps lift the liquid loop's heat to district heating for a town
  and to greenhouses.

Same weather, same IT load. Units: MW, MWh, kg, m3; temperatures in C. All the numbers come from
params/pass2.yaml. Simplifications are stated where they are made.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

H_FG = 2.43e6  # J/kg, latent heat of vaporisation of water near 30 C (steam tables)
CP_WATER = 4186.0  # J/(kg K)
KELVIN = 273.15
GAL = 3.785411784e-3  # m3 per US gallon


@dataclass
class Result:
    name: str
    it_mwh: float
    cooling_mwh: float  # chillers or trim chillers, plus fans and pumps
    heat_pump_mwh: float  # electricity to lift heat for the town and greenhouses
    evaporated_m3: float
    blowdown_m3: float
    heat_out_mwh: float  # all heat leaving the site
    heat_reused_mwh: float  # data center heat taken by the heat pumps
    delivered_mwh: float  # heat delivered to the town and greenhouses (source + pump work)
    town_mwh: float
    greenhouse_mwh: float
    town_demand_mwh: float
    greenhouse_demand_mwh: float
    trim_hours: int

    @property
    def withdrawn_m3(self) -> float:
        return self.evaporated_m3 + self.blowdown_m3

    @property
    def wue(self) -> float:
        """Water withdrawn per kWh of IT energy (L/kWh), the usual site WUE."""
        return self.withdrawn_m3 * 1000.0 / (self.it_mwh * 1000.0)

    @property
    def pue(self) -> float:
        """(IT + cooling) / IT; heat pump power is for selling heat and is reported apart."""
        return (self.it_mwh + self.cooling_mwh) / self.it_mwh


def evaporation_per_10f() -> float:
    """Share of circulating water evaporated per 10 F of tower range if all heat left as vapour:
    c_p dT / h_fg. The rules of thumb say 0.85-1% (RESEARCH.md)."""
    return CP_WATER * (10.0 / 1.8) / H_FG


def heat_pump_cop(source_c: float, supply_c: float, approach_k: float, carnot_eff: float) -> float:
    """COP of a heat pump lifting heat from water at source_c to water at supply_c: a share of the
    Carnot COP between evaporating (source - approach) and condensing (supply + approach)."""
    cond = supply_c + approach_k + KELVIN
    evap = source_c - approach_k + KELVIN
    return carnot_eff * cond / (cond - evap)


def town_demand(temp: np.ndarray, p: dict) -> np.ndarray:
    """Hourly heat demand of the town network (MW): space heat in proportion to degrees below the
    balance point, hot water flat, scaled to the annual total."""
    annual = p["pass2.town.homes"] * p["pass2.town.heat_per_home_mwh"]
    hw = p["pass2.town.hot_water_share"]
    deg = np.clip(p["pass2.town.base_c"] - temp, 0, None)
    space = (1 - hw) * annual * deg / deg.sum() if deg.sum() > 0 else 0.0 * deg
    return space + hw * annual / len(temp)


def greenhouse_demand(temp: np.ndarray, p: dict) -> np.ndarray:
    """Hourly heat loss of the greenhouses through the cover (MW). Solar gain is ignored, so daytime
    demand is overstated: an upper bound on the heat they can take."""
    area = p["pass2.greenhouse.hectares"] * 1e4 * p["pass2.greenhouse.cover_ratio"]
    return p["pass2.greenhouse.u_w_m2k"] * area * np.clip(p["pass2.greenhouse.set_c"] - temp, 0, None) / 1e6


def _trim_share(temp: np.ndarray, supply: float, rise: float, approach: float) -> np.ndarray:
    """Share of a loop's heat the dry coolers can't reject: they cool the return (supply + rise)
    only down to outdoor + approach; chillers take the rest of the way to supply."""
    return np.clip((temp + approach - supply) / rise, 0.0, 1.0)


def conventional(temp: np.ndarray, p: dict) -> Result:
    it = np.full(temp.shape, p["pass2.module.it_mw"] * p["pass2.module.load_factor"])
    cop = p["pass2.conventional.chiller_cop"]
    chiller = it / cop
    fans = (it + chiller) * p["pass2.fans.tower_kw_per_kw"]
    chiller = chiller + fans  # cooling electricity: chillers + tower fans + pumps
    tower_w = (it + chiller) * 1e6
    evap_kg = (tower_w * p["pass2.conventional.evap_fraction"] / H_FG * 3600.0).sum()
    evap_m3 = evap_kg / 1000.0
    blow_m3 = evap_m3 / (p["pass2.conventional.cycles"] - 1.0)
    z = 0.0
    return Result("conventional", it.sum(), chiller.sum(), z, evap_m3, blow_m3, (it + chiller).sum(), z, z, z, z,
                  town_demand(temp, p).sum(), greenhouse_demand(temp, p).sum(), int(len(temp)))


def good_neighbour(temp: np.ndarray, p: dict) -> Result:
    g = "pass2.good_neighbour."
    it = np.full(temp.shape, p["pass2.module.it_mw"] * p["pass2.module.load_factor"])
    liquid = it * p[g + "liquid_fraction"]
    air = it - liquid
    rise, approach = p[g + "liquid_rise_k"], p[g + "approach_k"]
    supply_l, supply_a = p[g + "liquid_supply_c"], p[g + "air_supply_c"]
    trim_l = _trim_share(temp, supply_l, rise, approach)
    trim_a = _trim_share(temp, supply_a, rise, approach)

    # Heat pumps take heat from the liquid loop's return before the dry coolers see it.
    cop_hp = heat_pump_cop(supply_l + rise, p[g + "dh_supply_c"], p[g + "hp_approach_k"], p[g + "hp_carnot_eff"])
    town = town_demand(temp, p)
    gh = greenhouse_demand(temp, p)
    demand = town + gh
    taken = np.minimum(demand * (cop_hp - 1.0) / cop_hp, liquid)  # source heat the pumps use
    delivered = taken * cop_hp / (cop_hp - 1.0)
    share_town = np.divide(town, demand, out=np.zeros_like(demand), where=demand > 0)

    # What the heat pumps take no longer needs rejecting, so trim applies to the rest.
    trim_mw = (liquid - taken) * trim_l / p[g + "trim_cop"] + air * trim_a / p[g + "trim_cop"]
    to_air = it - taken + trim_mw
    fans = to_air * p["pass2.fans.dry_kw_per_kw"]  # dry cooler fans + loop pumps
    trim_mw = trim_mw + fans  # cooling electricity: trim chillers + fans + pumps
    heat_out = it + trim_mw  # all of it leaves as heat, to the town or to the air
    return Result("good neighbour", it.sum(), trim_mw.sum(), (delivered - taken).sum(), 0.0, 0.0, heat_out.sum(),
                  taken.sum(), delivered.sum(), (delivered * share_town).sum(), (delivered * (1 - share_town)).sum(),
                  town.sum(), gh.sum(), int(((trim_l > 0) | (trim_a > 0)).sum()))


def table(results: list[Result]) -> str:
    """The comparison as a Markdown table (per module, per year)."""
    rows = [
        ("IT energy", "GWh", lambda r: r.it_mwh / 1e3, "{:,.0f}"),
        ("Cooling electricity (chillers, trim)", "GWh", lambda r: r.cooling_mwh / 1e3, "{:,.1f}"),
        ("PUE (IT + cooling; electrical losses left out of both)", "", lambda r: r.pue, "{:.3f}"),
        ("Water withdrawn", "million m3", lambda r: r.withdrawn_m3 / 1e6, "{:,.2f}"),
        ("Water withdrawn", "million US gal a day", lambda r: r.withdrawn_m3 / GAL / 365 / 1e6, "{:,.2f}"),
        ("Water evaporated (consumed)", "million m3", lambda r: r.evaporated_m3 / 1e6, "{:,.2f}"),
        ("WUE (withdrawn per IT kWh)", "L/kWh", lambda r: r.wue, "{:.2f}"),
        ("Heat leaving the site", "GWh", lambda r: r.heat_out_mwh / 1e3, "{:,.0f}"),
        ("Heat delivered to town + greenhouses", "GWh", lambda r: r.delivered_mwh / 1e3, "{:,.0f}"),
        ("  of it to the town", "GWh", lambda r: r.town_mwh / 1e3, "{:,.0f}"),
        ("  of it to greenhouses", "GWh", lambda r: r.greenhouse_mwh / 1e3, "{:,.0f}"),
        ("Data center heat reused", "share of heat out", lambda r: r.heat_reused_mwh / r.heat_out_mwh, "{:.0%}"),
        ("Heat pump electricity", "GWh", lambda r: r.heat_pump_mwh / 1e3, "{:,.1f}"),
    ]
    out = ["| Per 100 MW module, per year | Unit | " + " | ".join(r.name for r in results) + " |",
           "|---|---|" + "---|" * len(results)]
    for label, unit, fn, fmt in rows:
        out.append(f"| {label} | {unit} | " + " | ".join(fmt.format(fn(r)) for r in results) + " |")
    return "\n".join(out)
