"""Pass 3e: the neighbourhood at the campus edge (D11).

Townhouses over their own two-car garages, set back from the data hall so that night noise from the
roof's coolers stays under the guideline at their windows; between them and the garden, the square
(the food hall and its market-garden house, the community center with its courts, rink, gym and
makerspace); heated grass fields on the capped ash site. The model:

- Heat: each townhouse variant's envelope, through pass 3's `house.heat` (walls, windows, doors,
  roof, air), plus the floor over the garage and the garage itself, both kept warm off the loop.
- Noise: the roof's coolers at each floor's windows (`garden.rooftop_noise` at the window height).
- Walks: from every door to the square, the food hall, the community center, the fields and the
  garden, along the street grid.
- Heat by month, money, growth: once the research inputs are in (params/village.yaml).

Frame as forge `garden`: metres; x east, y south (the town), the hall's south face at y = -3.
"""

from __future__ import annotations

import numpy as np

from . import garden, house

HALL_FACE_Y = -3.0
VARIANTS = ("gap", "narrow", "twin")  # detached with a ~3 m gap; detached with ~1 m; attached on twin walls


def townhouse_env(p: dict, variant: str, end: bool = False) -> dict:
    """The heated part of a townhouse (the storeys over the garage) in `house.ua`'s shape. Side walls
    lose heat on detached houses and on the ends of a twin-wall row; between twin walls they don't
    (each wall faces its neighbour's across an air gap: counted as no loss)."""
    t = "village.townhouse."
    w, d = p[t + "width_" + variant], p[t + "depth_m"]
    n, h = int(p[t + "storeys"]), p[t + "storey_m"]
    floor = w * d * n
    front_back = 2 * w * h * n
    sides = 2 * d * h * n if variant != "twin" or end else 0.0
    glaze = p[t + "glazing_front_back"] * front_back + (p[t + "glazing_sides"] * sides if variant == "gap" else 0.0)
    door = p[t + "door_m2"]
    return {"floor_m2": floor, "interior_volume_m3": floor * (h - 0.3), "wall_net_m2": front_back + sides - glaze - door,
            "glazed_m2": glaze, "door_m2": door, "ceiling_m2": w * d, "slab_perimeter_m": 0.0,
            "garage_m2": w * d, "width_m": w, "depth_m": d}


def townhouse_heat(env: dict, temp: np.ndarray, p: dict) -> dict:
    """The house's heat (pass 3's `house.heat`), plus the floor over the garage and the garage, held
    at its own set point (a workshop you can stand in all winter), off the loop."""
    t, e = "village.townhouse.", "pass3.envelope."
    h = house.heat(env, temp, p)
    garage_c = p[t + "garage_c"]
    over = p[t + "garage_floor_u"] * house.BTU_FT2 * env["garage_m2"] * (p["pass3.loads.indoor_c"] - garage_c)  # W, house to garage
    perim = 2 * (env["width_m"] + env["depth_m"])
    walls = perim * p[t + "garage_h_m"] - p[t + "garage_door_m2"]
    garage_ua = (p[e + "wall_u"] * house.BTU_FT2 * walls + p[t + "garage_door_u_si"] * p[t + "garage_door_m2"]
                 + p[e + "slab_f"] * house.BTU_FT * perim)
    # The garage loses through its own walls, door and slab edge; the floor above gives it `over`.
    garage_w = np.clip(garage_ua * np.clip(garage_c - temp, 0.0, None) - over, 0.0, None)
    space = h["space_mwh"] + over * 8760 / 1e6
    design_garage_kw = max(garage_ua * (garage_c - p["pass3.loads.design_c"]) - over, 0.0) / 1e3
    return dict(h, floor_over_garage_w=over, garage_ua_w_k=garage_ua, garage_mwh=garage_w.sum() / 1e6,
                house_mwh=space, total_mwh=space + garage_w.sum() / 1e6 + h["hot_water_mwh"],
                design_kw=h["design_kw"] + over / 1e3 + design_garage_kw)


def noise_by_floor(p: dict, distance_m: float, fan_cut_db: float) -> list[tuple[float, float]]:
    """Night level (dB(A)) at a home `distance_m` from the hall's face, at each floor's windows."""
    t = "village.townhouse."
    heights = [1.5] + [p[t + "garage_h_m"] + (k + 0.5) * p[t + "storey_m"] for k in range(int(p[t + "storeys"]) + 1)]
    return [(h, float(garden.rooftop_noise(p, fan_cut_db=fan_cut_db, distances=[distance_m], h_r=h)["levels"][0]))
            for h in heights]


def lots(p: dict, variant: str) -> list[tuple[float, float]]:
    """Phase 1's lot centres: east-west streets south of the setback line, lots both sides, either side
    of a public spine street that runs from the town (south) straight to the square, so townspeople
    reach the square through the neighbourhood, not round it (no gates, no private roads). Between
    each pair of back-to-back rows, a green with big trees and a path (Radburn, Savannah)."""
    t, s = "village.townhouse.", "village.site."
    n = int(p[s + "phase1_homes"])
    lot_w = p[t + "width_" + variant] + p[t + "gap_" + variant]
    half = (p[s + "street_m"] - p[s + "spine_w_m"]) / 2
    per_half = int(half // lot_w)
    y0 = HALL_FACE_Y + p[s + "home_setback_m"] + p[s + "lot_depth_m"] / 2
    xc = p[s + "square_x"]
    out = []
    street = 0
    while len(out) < n:
        y_street = y0 + street * (2 * p[s + "lot_depth_m"] + p[s + "street_w_m"] + p[s + "green_w_m"])
        for side in (0, 1):
            y = y_street + side * (p[s + "lot_depth_m"] + p[s + "street_w_m"])
            for k in range(per_half):
                for sign in (-1, 1):
                    if len(out) < n:
                        out.append((xc + sign * (p[s + "spine_w_m"] / 2 + (k + 0.5) * lot_w), y))
        street += 1
    return out


def walks(p: dict, homes: list[tuple[float, float]]) -> dict[str, np.ndarray]:
    """Minutes on foot from each door to each place, along the street grid (x then y)."""
    s = "village.site."
    places = {"the square": (p[s + "square_x"], p[s + "square_y"]), "the winter garden": (p[s + "garden_x"], p[s + "garden_y"]),
              "the fields": (p[s + "fields_x"], p[s + "fields_y"])}
    speed = p["village.walking.speed_hcm_sidewalk"] * 60.0
    return {k: np.array([(abs(x - px) + abs(y - py)) / speed for x, y in homes]) for k, (px, py) in places.items()}


# --- Heat hour by hour: the homes, the shared buildings, the fields, the market garden -------------

M2_FT2 = 10.7639
MONTHS = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]) * 24


def home_hourly_w(p: dict, temp: np.ndarray, variant: str = "gap") -> tuple[np.ndarray, dict]:
    """One townhouse's heat each hour (W): the house (pass 3's balance-point method), its loss to the
    garage below, the garage, and hot water spread flat."""
    env = townhouse_env(p, variant)
    h = townhouse_heat(env, temp, p)
    house_w = h["ua_w_k"] * np.clip(h["balance_c"] - temp, 0.0, None) + h["floor_over_garage_w"]
    garage_w = np.clip(h["garage_ua_w_k"] * np.clip(p["village.townhouse.garage_c"] - temp, 0.0, None) - h["floor_over_garage_w"], 0.0, None)
    return house_w + garage_w + h["hot_water_mwh"] * 1e6 / len(temp), h


def loads_mw(p: dict, wx: dict, variant: str = "gap") -> dict[str, np.ndarray]:
    """The neighbourhood's heat each hour (MW), by use. The rink heats itself from its refrigeration
    and gives its surplus to the community center (research: CO2 rinks meet 88-100% of their own heat
    and export 80-100 kW); the fields are kept growing below their root-zone target."""
    from . import food

    temp, a, r, f = wx["t"], "village.amenities.", "village.rink.", "village.fields."
    per_home, _ = home_hourly_w(p, temp, variant)
    homes = per_home * p["village.site.phase1_homes"] / 1e6
    floor_m2 = (p[a + "center_ft2"] + p[a + "food_hall_ft2"]) / M2_FT2
    deg = np.clip(p["pass3.loads.indoor_c"] - temp, 0.0, None)
    buildings = floor_m2 * p[a + "building_heat_kwh_m2"] * 1e3 * deg / deg.sum() / 1e6  # MW, shaped by degree-hours
    in_season = np.zeros(len(temp), bool)
    for m in list(range(0, 4)) + list(range(9, 12)):  # ice from October to April (research: 7-9 months)
        in_season[MONTHS[m]:MONTHS[m + 1]] = True
    buildings = np.clip(buildings - in_season * p[r + "heat_export_surplus"] / 1e3, 0.0, None)
    area = p[f + "pitch_area_soccer"]  # one multi-use field, soccer-sized (also lined for youth and flag football, lacrosse)
    cold = np.clip(p[f + "root_zone_target_growth"] - temp, 0.0, None)
    fields = np.minimum(area * p[f + "heat_energy_grass_growth"] * 1e3 * cold / cold.sum(), area * p[f + "heat_design_load"]) / 1e6
    hs = food.house(wx, p, "lettuce", "glass")
    garden_ha = p[a + "market_garden_ha"] * 1e4
    sm = "village.snowmelt."
    walk_m2 = p[sm + "heated_walk_m2"]
    gain = 1 + p[sm + "loss_share"]
    freeze = np.clip(2.0 - temp, 0.0, None)  # kept above freezing below ~2 C
    walks = np.minimum(walk_m2 * p[sm + "energy_kwh_m2"] * gain * 1e3 * freeze / freeze.sum(),
                       walk_m2 * p[sm + "design_w_m2"] * gain) / 1e6
    return {"homes": homes, "shared buildings": buildings, "fields": fields, "heated walks": walks,
            "market section": hs["heat_w"] * garden_ha / 1e6,
            "market section lamps": hs["lamp_w"] * garden_ha / 1e6}


def balance(p: dict, wx: dict) -> dict:
    """The module's spare heat (after the town network) by month: the neighbourhood first, then the
    tomato houses take what's left at pass 3d's design rule. The houses' area before and after."""
    from . import food

    avail = food.dc_heat(wx["t"], p)
    ld = loads_mw(p, wx)
    village = sum(v for k, v in ld.items() if k != "market section lamps")
    left = np.clip(avail - village, 0.0, None)
    short = np.clip(village - avail, 0.0, None)  # hours the neighbourhood alone exceeds the spare heat
    hs = food.house(wx, p, "tomato", "glass")
    ha0 = food.design_ha(hs, avail, p, "tomato", "glass")
    ha1 = food.design_ha(hs, left, p, "tomato", "glass")
    run = food.simulate(hs, left, p, "tomato", "glass", ha1)
    tomato = hs["heat_w"] * ha1 * 1e4 / 1e6
    taken = np.minimum(tomato, left)
    months = []
    for m in range(12):
        sl = slice(MONTHS[m], MONTHS[m + 1])
        months.append({"spare": avail[sl].sum(), **{k: v[sl].sum() for k, v in ld.items() if k != "market section lamps"},
                       "tomatoes": taken[sl].sum(), "left": (avail[sl] - np.minimum(village[sl], avail[sl]) - taken[sl]).sum()})
    return {"loads": ld, "village_mwh": float(village.sum()), "village_peak_mw": float(village.max()), "short_mwh": float(short.sum()),
            "ha_before": ha0, "ha_after": ha1, "run": run, "months": months, "avail": avail}


# --- The price ceiling, money, growth ------------------------------------------------------------

def price_ceiling(p: dict, temp: np.ndarray, variant: str = "gap") -> dict:
    """Pass 3's per-home comparison (block.per_home) at the neighbourhood's own density: the loop
    against a home's own heat pump and a gas furnace, over the equipment's life."""
    from . import block

    _, h = home_hourly_w(p, temp, variant)
    q = dict(p, **{"pass3.block.homes": p["village.site.phase1_homes"], "pass3.block.main_km": p["village.money.main_km"]})
    frontage = p["village.townhouse.width_" + variant] + p["village.townhouse.gap_" + variant]
    return block.per_home(q, h["house_mwh"] + h["garage_mwh"], h["hot_water_mwh"], h["design_kw"], townhouse_env(p, variant)["floor_m2"], frontage)


def home_cost(p: dict, variant: str = "gap") -> dict:
    """Building one townhouse (construction only, NAHB / ICC rates), and the price a household on the
    area's median income could pay at the conventional share of income."""
    env = townhouse_env(p, variant)
    c = "village.housing_cost."
    living_ft2, garage_ft2 = env["floor_m2"] * M2_FT2, env["garage_m2"] * M2_FT2
    build = living_ft2 * p[c + "cost_per_ft2_nahb"] + garage_ft2 * p[c + "garage_cost_per_ft2"]
    m, f = "village.money.", "pass4.finance."
    pay = p["pass4.rents.ami_usd"] * p[m + "front_end"] / 12
    r, n = p[f + "rate"] / 12, p[f + "term_yr"] * 12
    loan = pay * (1 - (1 + r) ** -n) / r
    afford = loan / (1 - p[m + "down_payment"])
    return {"living_ft2": living_ft2, "garage_ft2": garage_ft2, "build_usd": build, "afford_usd": afford, "gap_usd": build - afford}


def amenities_cost(p: dict) -> dict[str, float]:
    a, cc, f, r, m = "village.amenities.", "village.community_center.", "village.fields.", "village.rink.", "village.money."
    area_m2 = p[f + "pitch_area_soccer"]
    fields = area_m2 * M2_FT2 * p[f + "field_cost_sand_based"] + area_m2 * p[f + "heat_install_cost_in_field"] * p[m + "nok_usd_2015"]
    loop_m = 2 * (p[f + "pitch_length_soccer"] + p[f + "pitch_width_soccer"]) + 8 * 20.0  # a ring ~20 m outside the touchlines
    return {"ice rink (one sheet)": p[r + "build_cost_single_sheet"],
            "community center (courts, roller hockey, indoor pickleball, bouldering, golf simulators, gym, makerspace)": p[a + "center_ft2"] * p[cc + "rec_center_build_usd_ft2"],
            "food court at the greenhouse's entrance": p[a + "food_hall_ft2"] * p[cc + "restaurant_build_usd_ft2"] + p["village.kitchen.infinite_kitchen_incremental_capex"],
            "makerspace tools": p[a + "makerspace_tools_usd"],
            "bouldering walls": p[a + "climbing_usd"],
            "one heated grass field and a walking loop": fields + loop_m * p[a + "loop_usd_m"],
            "market section inside the greenhouse": p[a + "market_garden_ha"] * 1e4 * p["food.cost.house_usd_m2"]}


def trust_money(p: dict) -> dict:
    """The trust's set share of the campus's county and township tax (pass 4), as assessed and after a
    won appeal."""
    from . import econ

    tax = econ.campus_tax(p)
    local = tax["county"] + tax["township"]
    share = p["village.money.trust_share"]
    out = {"local_tax": local, "school_tax": tax["school"], "trust": local * share}
    for cut in (p["village.money.appeal_cut"], 0.90):
        out[f"trust_after_{cut:.0%}_cut"] = local * (1 - cut) * share
    return out


def growth(p: dict, wx: dict, variant: str = "gap") -> dict:
    """How far the neighbourhood could grow before each limit binds."""
    from . import food

    avail = food.dc_heat(wx["t"], p)
    per_home, _ = home_hourly_w(p, wx["t"], variant)
    ratio = avail / (per_home / 1e6)
    g = "village.growth_limits."
    gpd_home = p[g + "sewer_avg_flow_mgd"] * 1e6 / p[g + "sewer_residential_customers"]
    return {"homes_on_heat": float(np.percentile(ratio, 1)),
            "sewer_gpd_per_home": gpd_home, "homes_on_sewer": p[g + "sewer_spare_mgd"] * 1e6 / gpd_home,
            "sewer_wet_month_mgd": q_range_high(p, g + "sewer_avg_flow_mgd"), "sewer_design_mgd": p[g + "sewer_design_mgd"],
            "school": p[g + "school_enrolment"], "per_grade": p[g + "school_cohort_per_grade"]}


_HIGH: dict = {}


def q_range_high(p: dict, key: str) -> float:
    return _HIGH.get(key, p[key])


def set_ranges(params: dict) -> None:
    _HIGH.update({k: v.high for k, v in params.items() if k.startswith("village.")})


def report(p: dict, wx: dict, variant: str = "gap") -> str:
    from . import econ

    L = []
    t = "village.townhouse."
    L += ["**The townhouses** (heat through pass 3's model, over a garage-workshop held at "
          f"{p[t + 'garage_c']:g} C)", "",
          "| Variant | Living floor | Home's heat a year | Per m2 | Garage | Hot water | Design load | Water needed |",
          "|---|---|---|---|---|---|---|---|"]
    names = {"gap": "detached, 3 m gap", "narrow": "detached, 1 m gap", "twin": "twin walls, mid-row"}
    for v in VARIANTS:
        env = townhouse_env(p, v)
        h = townhouse_heat(env, wx["t"], p)
        L.append(f"| {names[v]} | {env['floor_m2']:.0f} m2 | {h['house_mwh']:.1f} MWh | {h['house_mwh'] * 1e3 / env['floor_m2']:.0f} kWh | "
                 f"{h['garage_mwh']:.1f} MWh | {h['hot_water_mwh']:.1f} MWh | {h['design_kw']:.1f} kW | {h['supply_c']:.0f} C |")
    a = "village.acoustics."
    L += ["", f"Sound between homes: a single stud wall rates STC {p[a + 'stc_single_stud']:g}; twin stud walls with an air gap "
          f"{p[a + 'stc_double_stud_1layer']:g}-{p[a + 'stc_double_stud_2layer']:g}, against the code's {p[a + 'ibc_stc_min']:g}; "
          "separate houses share no wall at all.", ""]

    s = "village.site."
    L += [f"**Noise at the windows** ({p[s + 'home_setback_m']:g} m from the hall, night, 3 m parapet)", "",
          "| Window | Pass 2's fans | Fans 3 dB quieter | Fans 6 dB quieter |", "|---|---|---|---|"]
    rows = {cut: village_floors for cut, village_floors in ((c, noise_by_floor(p, p[s + "home_setback_m"], c)) for c in (0.0, 3.0, 6.0))}
    for i, (h, _) in enumerate(rows[0.0]):
        L.append(f"| {h:.1f} m up | " + " | ".join(f"{rows[c][i][1]:.1f} dB(A)" for c in (0.0, 3.0, 6.0)) + " |")

    homes = lots(p, variant)
    w = walks(p, homes)
    L += ["", f"**Walks** from phase 1's {len(homes)} doors (minutes, along the streets)", "",
          "| To | Nearest | Furthest |", "|---|---|---|"]
    L += [f"| {k} | {v.min():.1f} | {v.max():.1f} |" for k, v in w.items()]

    b = balance(p, wx)
    L += ["", "**Heat by month** (GWh; the module's spare heat after the town network, the neighbourhood first, then the tomato houses)", "",
          "| Month | Spare | Homes | Shared buildings | Field | Heated walks | Market section | Tomato houses | Left to the air |",
          "|---|---|---|---|---|---|---|---|---|"]
    for m, r in enumerate(b["months"]):
        L.append(f"| {m + 1} | {r['spare'] / 1e3:.1f} | {r['homes'] / 1e3:.2f} | {r['shared buildings'] / 1e3:.2f} | {r['fields'] / 1e3:.2f} | "
                 f"{r['heated walks'] / 1e3:.2f} | {r['market section'] / 1e3:.2f} | {r['tomatoes'] / 1e3:.1f} | {r['left'] / 1e3:.1f} |")
    L += ["", f"The neighbourhood takes {b['village_mwh'] / 1e3:.1f} GWh a year ({b['village_peak_mw']:.1f} MW at its peak) and is never "
          f"short; the tomato houses' design area goes from {b['ha_before']:g} ha to {b['ha_after']:g} ha."]

    pc = price_ceiling(p, wx["t"], variant)
    af = __import__("brownfield.cost", fromlist=["annuity"]).annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    a_op = pc["A"] - pc["network"] * (1 + p["pass3.block.om_share"] * af)
    L += ["", f"**A home's heat over {p['cost.money.life_yr']:g} years** (pass 3's comparison, at this neighbourhood's density)", "",
          "| | Up front | A year | Over the life |", "|---|---|---|---|",
          f"| On the loop (the home pays for its share of the network) | ${pc['A_capex']:,.0f} | ${pc['A_year']:,.0f} | ${pc['A']:,.0f} |",
          f"| On the loop (the operator pays for the network) | ${pc['A_capex'] - pc['network']:,.0f} | | ${a_op:,.0f} |",
          f"| Its own heat pump | ${pc['B_capex']:,.0f} | ${pc['B_year']:,.0f} | ${pc['B']:,.0f} |",
          f"| A gas furnace | ${pc['C_capex']:,.0f} | ${pc['C_year']:,.0f} | ${pc['C']:,.0f} |"]

    hc = home_cost(p, variant)
    price = hc["build_usd"] / p["village.housing_cost.construction_share"]
    L += ["", f"**Building a townhouse**: {hc['living_ft2']:,.0f} ft2 of home over a {hc['garage_ft2']:,.0f} ft2 garage: "
          f"${hc['build_usd']:,.0f} to build (construction only); about ${price:,.0f} as a price with land, fees and profit "
          f"(construction is {p['village.housing_cost.construction_share']:.0%} of a new home's price). A household on the area's "
          f"median income (${p['pass4.rents.ami_usd']:,.0f}) can pay about ${hc['afford_usd']:,.0f} at {p['village.money.front_end']:.0%} of "
          f"income: a gap of about ${price - hc['afford_usd']:,.0f} a home."]

    ac = amenities_cost(p)
    tm = trust_money(p)
    L += ["", "**The shared places**: to build", "", "| | USD |", "|---|---|"]
    L += [f"| {k} | ${v / 1e6:,.1f}M |" for k, v in ac.items()]
    L += [f"| **In all** | **${sum(ac.values()) / 1e6:,.1f}M** |", "",
          f"The campus's county and township tax is about ${tm['local_tax'] / 1e6:,.1f}M a year (its school tax "
          f"${tm['school_tax'] / 1e6:,.1f}M more, which can't pay for these). A {p['village.money.trust_share']:.0%} share gives the trust "
          f"${tm['trust'] / 1e6:,.2f}M a year; after a won appeal cutting the assessment {p['village.money.appeal_cut']:.0%}, "
          f"${tm['trust_after_24%_cut'] / 1e6:,.2f}M; after a 90% cut, ${tm['trust_after_90%_cut'] / 1e6:,.2f}M. So the building has to "
          "come from the endowment paid up front under the benefits agreement, and the yearly share keeps them running."]

    g = growth(p, wx, variant)
    d = econ.demand(p)
    L += ["", "**How far it could grow, and what binds first**", "",
          f"- Heat: the module's spare heat could carry about {g['homes_on_heat']:,.0f} townhouses in all but the coldest 1% of hours, "
          "if the tomato houses gave way.",
          f"- Sewage: Homer City's plant is rated {g['sewer_design_mgd']:.2f} million gallons a day and averages about "
          f"{p['village.growth_limits.sewer_avg_flow_mgd']:.2f}; at {g['sewer_gpd_per_home']:.0f} gallons a day per customer that is room for "
          f"about {g['homes_on_sewer']:,.0f} homes on average, but a wet month already reached the rating. A town beyond phase 1-2 needs "
          "a new plant or the leaks into the sewers fixed.",
          f"- Schools: Homer-Center has {g['school']:,.0f} pupils, about {g['per_grade']:.0f} a grade; its capacity wasn't found.",
          f"- People: pass 4's jobs bring about {d['near_renters']:,.0f} "
          "renter households near the campus. Programmes that pay people to move for a place: Tulsa Remote "
          f"{p['village.demand.tulsa_remote_participants']:,.0f} movers since 2018 at ${p['village.demand.tulsa_remote_incentive']:,.0f} each "
          f"({p['village.demand.tulsa_remote_but_for_rate']:.0%} wouldn't have come without it); Ascend WV "
          f"{p['village.demand.ascend_wv_participants']:,.0f} since 2021."]
    return "\n".join(L)


def forge_spec(p: dict, variant: str = "gap") -> dict:
    """What forge `garden` draws for the neighbourhood (metres, the campus frame)."""
    t, s, f = "village.townhouse.", "village.site.", "village.fields."
    homes = lots(p, variant)
    y_rows = sorted({round(y, 3) for _, y in homes})
    # Rows pair up across each street: the first of a pair faces south (the street below it), the second north.
    facing = {y: (1 if i % 2 == 0 else -1) for i, y in enumerate(y_rows)}
    streets = [(y_rows[i] + y_rows[i + 1]) / 2 for i in range(0, len(y_rows) - 1, 2)]
    lot_d = p[s + "lot_depth_m"]
    lot_w = p[t + "width_" + variant] + p[t + "gap_" + variant]
    gx = [x for x, _ in homes]
    greens = [[min(gx) - lot_w, max(gx) + lot_w, y_rows[i] + lot_d / 2, y_rows[i + 1] - lot_d / 2]
              for i in range(1, len(y_rows) - 1, 2)]
    if len(y_rows) % 2:  # a last row on its own faces a street of its own to the south
        streets.append(y_rows[-1] + (p[s + "lot_depth_m"] + p[s + "street_w_m"]) / 2)
    lot_w = p[t + "width_" + variant] + p[t + "gap_" + variant]
    xs = [x for x, _ in homes]
    soccer = (p[f + "pitch_width_soccer"], p[f + "pitch_length_soccer"])
    football = (p[f + "field_width_football"], p[f + "field_length_football"])
    return {"source": "brownfield village (pass 3e): phase 1 of the neighbourhood, for forge `garden`",
            "village": {
                "variant": variant, "house_w": p[t + "width_" + variant], "house_d": p[t + "depth_m"], "lot_w": lot_w,
                "storeys": int(p[t + "storeys"]), "storey_m": p[t + "storey_m"], "garage_h": p[t + "garage_h_m"],
                "homes": [{"x": x, "y": y, "facing": facing[round(y, 3)]} for x, y in homes],
                "streets_y": streets, "greens": greens, "street_w": p[s + "street_w_m"], "street_x": [min(xs) - lot_w, max(xs) + lot_w],
                "spine_x": p[s + "square_x"], "spine_w": p[s + "spine_w_m"], "spine_y": [120.0, max(y for _, y in homes) + 60.0],
                "square": [0.0, 60.0, 60.0, 120.0], "food_hall": [0.0, 0.0, 0.0, 0.0], "market_garden": [0.0, 0.0, 0.0, 0.0],
                "center": [72.0, 162.0, 12.0, 140.0],
                "fields": [{"name": "soccer (multi-use)", "cx": -150.0, "cy": 110.0, "w": soccer[0], "l": soccer[1]}]}}
