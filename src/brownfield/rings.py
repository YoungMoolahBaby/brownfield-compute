"""D16: the rings of homes round the town centre. Jon, 2026-11-17: "smaller apartments are closer to
the city center while the larger/more remote the house gets, the further away from our city center we
get".

Three home types, in rings out from the square:
- **flats** in 3-storey walk-ups (pass 3b's shell, 100 x 40 ft), studios to 3-beds in the mix now
  built to rent;
- **townhouses**, Jon's, over their garage-workshops (D11, `village`);
- **houses**, detached, at the Census median new house and lot, the garage-workshop beside them.

Who lives in them (`counts`): pass 4's newcomers who rent take the flats; those who buy take the
townhouses, or the houses if they need 4 bedrooms or more, in the share Indiana County's owners do.
For each type: its heat (pass 3's model), the hall's noise at its top windows at night, the sound
through the floors between flats, what it costs against what its household can pay, school-age
children, and land. Positions from params/site.yaml (flats, townhouses, houses); rows of lots either
side of a public spine street as pass 3e's (`rows`).
"""

from __future__ import annotations

import math

import numpy as np

RINGS = ("flats", "townhouses", "houses")
R = "village.rings."
FT2_M2 = 0.09290304


def _apportion(n: int, shares: list[float]) -> list[int]:
    """Whole numbers in proportion to `shares` summing to n (largest remainder)."""
    raw = [n * s for s in shares]
    out = [int(math.floor(x)) for x in raw]
    for k in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[: n - sum(out)]:
        out[k] += 1
    return out


def counts(p: dict) -> dict:
    """Phase 1's homes from pass 4's newcomers near the campus: renters in flats (by bedrooms, as new
    rental flats are built), owners in townhouses, or in houses if they need 4 bedrooms or more."""
    from . import econ

    d = econ.demand(p)
    renters = d["near_renters"]
    owners = d["households"] * (1 - p["pass4.demand.renter_share"]) * p[R + "owners_near_share"]
    mix = [p[R + f"flat_mix_{b}"] for b in range(4)]
    flats = _apportion(round(renters), [m / sum(mix) for m in mix])
    n_own = round(owners)
    houses = round(n_own * p[R + "owners_4bed_share"])
    ft2 = sum(n * p[R + f"ft2_{b}"] for b, n in enumerate(flats))
    return {"renters": renters, "owners": owners, "flats_by_bed": flats, "flats": sum(flats), "flat_ft2": ft2,
            "walkups": math.ceil(ft2 / p[R + "walkup_flats_ft2"]), "townhouses": n_own - houses, "houses": houses}


def persons(p: dict, c: dict | None = None) -> dict[str, float]:
    c = c or counts(p)
    return {"flats": sum(n * p[R + f"persons_{b}"] for b, n in enumerate(c["flats_by_bed"])),
            "townhouses": c["townhouses"] * p[R + "persons_3"], "houses": c["houses"] * p[R + "persons_4"]}


# --- Where they stand -------------------------------------------------------------------------------

def lot(p: dict, kind: str, variant: str = "gap") -> tuple[float, float]:
    """A lot's frontage and depth (m)."""
    if kind == "flats":
        return p[R + "walkup_lot_w_m"], p[R + "walkup_lot_d_m"]
    if kind == "townhouses":
        return p[f"village.townhouse.width_{variant}"] + p[f"village.townhouse.gap_{variant}"], p["village.site.lot_depth_m"]
    w = p[R + "house_lot_w_m"]
    return w, p[R + "house_lot_ft2"] * FT2_M2 / w


def n_lots(p: dict, kind: str, c: dict | None = None) -> int:
    c = c or counts(p)
    return c["walkups"] if kind == "flats" else c[kind]


def rows(p: dict, n: int, lot_w: float, lot_d: float, cx: float, cy: float) -> list[tuple[float, float]]:
    """Lot centres: east-west streets (every home has a wall facing south), lots both sides, either side
    of a public spine street that runs from the town toward the square, so townspeople cross the
    neighbourhood, not go round it (no gates, no private roads). Between each pair of back-to-back rows,
    a green with big trees and a path (Radburn, Savannah). The block's middle at (cx, cy)."""
    s = "village.site."
    half = (p[s + "street_m"] - p[s + "spine_w_m"]) / 2
    per_half = max(1, int(half // lot_w))
    out, street = [], 0
    while len(out) < n:
        y_street = street * (2 * lot_d + p[s + "street_w_m"] + p[s + "green_w_m"])
        for side in (0, 1):
            y = y_street + side * (lot_d + p[s + "street_w_m"])
            for k in range(per_half):
                for sign in (-1, 1):
                    if len(out) < n:
                        out.append((sign * (p[s + "spine_w_m"] / 2 + (k + 0.5) * lot_w), y))
        street += 1
    xs, ys = [x for x, _ in out], [y for _, y in out]
    dx, dy = cx - (min(xs) + max(xs)) / 2, cy - (min(ys) + max(ys)) / 2
    return [(x + dx, y + dy) for x, y in out]


def lots(p: dict, kind: str, variant: str = "gap") -> list[tuple[float, float]]:
    w, d = lot(p, kind, variant)
    return rows(p, n_lots(p, kind), w, d, p[f"site.{kind}.x"], p[f"site.{kind}.y"])


def rect(p: dict, kind: str, variant: str = "gap") -> tuple[float, float, float, float]:
    """The ring's footprint: its lots, a lot's width beyond the end lots, half a lot beyond the end rows."""
    pts = lots(p, kind, variant)
    w, d = lot(p, kind, variant)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return (min(xs) - w, max(xs) + w, min(ys) - d / 2, max(ys) + d / 2)


# --- Heat -------------------------------------------------------------------------------------------

def _hourly(h: dict, temp: np.ndarray) -> np.ndarray:
    return h["ua_w_k"] * np.clip(h["balance_c"] - temp, 0.0, None)


def flats_hourly_w_m2(p: dict, temp: np.ndarray) -> tuple[np.ndarray, dict]:
    """Space heat each hour per m2 of flat: pass 3b's walk-up, every flat's own balance (party walls
    and floors between flats lose nothing), summed over its floor area."""
    from . import house

    apt = house.apartment()
    tot = np.zeros(len(temp))
    area = 0.0
    for f in apt["flats"]:
        h = house.heat(f, temp, p)
        tot += _hourly(h, temp)
        area += f["floor_m2"]
    m = house.flats_heat(apt, temp, p)["mean"]
    return tot / area, {"kwh_m2": tot.sum() / area / 1e3, "design_w_m2": m["design_kw"] * 1e3 / m["floor_m2"], "supply_c": m["supply_c"]}


def hot_water_mwh(p: dict, persons_: float) -> float:
    """Hot water a year, pass 3's household's scaled by its people."""
    return p["pass3.loads.hot_water_mwh"] * persons_ / p["site.visits.persons_per_home"]


def house_env(p: dict) -> dict:
    """The outer ring's house in `house.ua`'s shape: two storeys on a slab, its floor the median new
    house's, a footprint 1.2 times as wide as deep facing the street (south or north), windows on all
    sides as the detached townhouses have."""
    t = "village.townhouse."
    floor = p["village.housing_cost.median_new_sf_floor_area"] * FT2_M2
    n, h = int(p[R + "house_storeys"]), p[R + "house_storey_m"]
    fp = floor / n
    d = math.sqrt(fp / 1.2)
    w = 1.2 * d
    front_back, sides = 2 * w * h * n, 2 * d * h * n
    glaze = p[t + "glazing_front_back"] * front_back + p[t + "glazing_sides"] * sides
    door = p[t + "door_m2"]
    return {"floor_m2": floor, "interior_volume_m3": floor * (h - 0.3), "wall_net_m2": front_back + sides - glaze - door,
            "glazed_m2": glaze, "door_m2": door, "ceiling_m2": fp, "slab_perimeter_m": 2 * (w + d), "width_m": w, "depth_m": d}


def house_heat(p: dict, temp: np.ndarray) -> dict:
    """The house (pass 3's model, ventilation for its bedrooms), plus its garage-workshop beside it at the
    townhouses' set point, and hot water for its people."""
    from . import house

    env = house_env(p)
    q = dict(p, **{"pass3.air.bedrooms": p[R + "house_bedrooms"], "pass3.loads.hot_water_mwh": hot_water_mwh(p, p[R + "persons_4"])})
    h = house.heat(env, temp, q)
    t, e = "village.townhouse.", "pass3.envelope."
    gw, gd = p[t + "width_gap"], p[t + "depth_m"]  # the townhouse's garage footprint, a two-car garage
    perim = 2 * (gw + gd) - gd  # one side against the house
    walls = perim * p[t + "garage_h_m"] - p[t + "garage_door_m2"]
    from .house import BTU_FT, BTU_FT2

    garage_ua = (p[e + "wall_u"] * BTU_FT2 * walls + p[t + "garage_door_u_si"] * p[t + "garage_door_m2"]
                 + p[e + "ceiling_u"] * BTU_FT2 * gw * gd + p[e + "slab_f"] * BTU_FT * perim)
    garage_w = garage_ua * np.clip(p[t + "garage_c"] - temp, 0.0, None)
    space_w = _hourly(h, temp)
    hourly = space_w + garage_w + h["hot_water_mwh"] * 1e6 / len(temp)
    return dict(h, env=env, garage_mwh=garage_w.sum() / 1e6, garage_m2=gw * gd, hourly_w=hourly,
                total_mwh=hourly.sum() / 1e6, design_kw=h["design_kw"] + garage_ua * (p[t + "garage_c"] - p["pass3.loads.design_c"]) / 1e3)


def loop_vs_heat_pump(p: dict, temp: np.ndarray, kind: str, bedrooms: int = 2) -> dict:
    """Pass 3's comparison (`block.per_home`) for one home of the type, over the equipment's life: the
    loop with its share of the network (street at the home's frontage, main, plant), the loop with
    the operator paying the network (the benefits agreement, D11), and the home's own heat pump."""
    from . import block, village
    from .cost import annuity

    c = counts(p)
    q = dict(p, **{"pass3.block.homes": c["flats"] + c["townhouses"] + c["houses"], "pass3.block.main_km": p["village.money.main_km"]})
    if kind == "flats":
        _, fh = flats_hourly_w_m2(p, temp)
        m2 = p[R + f"ft2_{bedrooms}"] * FT2_M2
        # A walk-up's frontage shared by its flats.
        front = lot(p, "flats")[0] * c["walkups"] / c["flats"]
        r = block.per_home(q, fh["kwh_m2"] * m2 / 1e3, hot_water_mwh(p, p[R + f"persons_{bedrooms}"]), fh["design_w_m2"] * m2 / 1e3, m2, front)
    elif kind == "townhouses":
        env = village.townhouse_env(p, "gap")
        h = village.townhouse_heat(env, temp, p)
        r = block.per_home(q, h["house_mwh"] + h["garage_mwh"], h["hot_water_mwh"], h["design_kw"], env["floor_m2"], lot(p, "townhouses")[0])
    else:
        h = house_heat(p, temp)
        r = block.per_home(q, h["space_mwh"] + h["garage_mwh"], h["hot_water_mwh"], h["design_kw"], h["env"]["floor_m2"], lot(p, "houses")[0])
    af = annuity(p["cost.money.discount"], p["cost.money.life_yr"])
    return dict(r, A_operator=r["A"] - r["network"] * (1 + p["pass3.block.om_share"] * af))


def houses_on_loop(p: dict, temp: np.ndarray) -> dict:
    """Whether the outer ring's houses heat from the loop or their own heat pumps. Pass 3 found the loop
    loses to a heat pump on its whole cost for townhouses and detached houses alike; the townhouses are
    on it because the operator pays for the pipes (D11). The houses join only if the loop beats the
    heat pump on its whole cost at their frontage."""
    r = loop_vs_heat_pump(p, temp, "houses")
    return dict(r, loop=r["A_minus_B"] < 0.0)


def hourly_w(p: dict, temp: np.ndarray, variant: str = "gap") -> dict[str, np.ndarray]:
    """Each ring's heat each hour (W), the homes on the loop only (the houses, if their own heat pumps
    win, are left off)."""
    from . import village

    c = counts(p)
    pm2, _ = flats_hourly_w_m2(p, temp)
    flat_m2 = c["flat_ft2"] * FT2_M2
    dhw = sum(n * hot_water_mwh(p, p[R + f"persons_{b}"]) for b, n in enumerate(c["flats_by_bed"])) * 1e6 / len(temp)
    town, _ = village.home_hourly_w(p, temp, variant)
    out = {"flats": pm2 * flat_m2 + dhw, "townhouses": town * c["townhouses"]}
    hh = house_heat(p, temp)
    out["houses"] = hh["hourly_w"] * c["houses"] if houses_on_loop(p, temp)["loop"] else np.zeros(len(temp))
    return out


# --- Noise, sound, children, money --------------------------------------------------------------

def windows(p: dict, kind: str) -> list[float]:
    """Each floor's window height (m) for the type: the walk-ups' three floors, the townhouses' floors
    over the garage (`village.noise_by_floor`), the houses' two."""
    if kind == "flats":
        return [1.5 + k * p[R + "walkup_storey_m"] for k in range(int(p[R + "walkup_storeys"]))]
    if kind == "houses":
        return [1.5 + k * p[R + "house_storey_m"] for k in range(int(p[R + "house_storeys"]))]
    t = "village.townhouse."
    return [1.5] + [p[t + "garage_h_m"] + (k + 0.5) * p[t + "storey_m"] for k in range(int(p[t + "storeys"]) + 1)]


def night_db(p: dict, kind: str, distance_m: float, fan_cut_db: float) -> float:
    """The hall's coolers at night at the ring's loudest window."""
    from . import garden

    return max(float(garden.rooftop_noise(p, fan_cut_db=fan_cut_db, distances=[distance_m], h_r=h)["levels"][0])
               for h in windows(p, kind))


def children(p: dict, c: dict | None = None) -> dict[str, float]:
    c = c or counts(p)
    f = c["flats_by_bed"]
    return {"flats": (f[0] + f[1]) * p[R + "kids_flat_01"] + f[2] * p[R + "kids_flat_2"] + f[3] * p[R + "kids_flat_3"],
            "townhouses": c["townhouses"] * p[R + "kids_townhouse"], "houses": c["houses"] * p[R + "kids_house"]}


LIHTC_PERSONS = {0: 1.0, 1: 1.5, 2: 3.0, 3: 4.5}  # 26 USC 42(g)(2)(C): 1.5 persons a bedroom, 1 for none
FAMILY_ADJ = {1: 0.70, 2: 0.80, 3: 0.90, 4: 1.00, 5: 1.08, 6: 1.16}  # HUD income limits by household size


def lihtc_rent(p: dict, bedrooms: int) -> float:
    """The 60% tax-credit rent limit a month, net of utilities, from PHFA's 3-person limit scaled by
    HUD's household-size factors at 1.5 persons a bedroom."""
    four = p["pass4.rents.lihtc_60_3p_usd"] / FAMILY_ADJ[3]
    n = LIHTC_PERSONS[bedrooms]
    adj = (FAMILY_ADJ[int(n)] + FAMILY_ADJ[int(n) + 1]) / 2 if n % 1 else FAMILY_ADJ[int(n)]
    return four * adj * 0.30 / 12 - p["pass4.rents.utility_allowance_usd"]


def flat_money(p: dict) -> dict[int, dict]:
    """Per flat by bedrooms (pass 4's method, `econ.flat`): HUD's total development cost for a walk-up
    of its size (with the gypsum-concrete floor for the upper two thirds), at market rent and as a
    tax-credit flat, and the gap each leaves."""
    from . import econ

    out = {}
    for b in range(4):
        tdc = p[f"pass4.cost.tdc_walkup_{b}"] * p["pass4.cost.tdc_to_2026"] + p[R + "topping_usd_ft2"] * p[R + f"ft2_{b}"] * 2 / 3
        q = dict(p, **{"pass4.cost.tdc_per_flat": tdc, "pass4.rents.market_rent_usd": p["pass4.rents.market_rent_usd"] * p[f"pass4.rents.fmr_ratio_{b}"],
                       "pass4.rents.lihtc_60_3p_usd": (lihtc_rent(p, b) + p["pass4.rents.utility_allowance_usd"]) * 12 / 0.30})
        out[b] = {"tdc": tdc, **{k: v for k, v in econ.flat(q).items()}}
    return out


def owner_money(p: dict, kind: str) -> dict:
    """A townhouse or house to buy: built at NAHB's $/ft2 (the garage-workshop at ICC's), priced with
    land, fees and profit; against what the county's median household and an AWS household can pay."""
    from . import village

    c = "village.housing_cost."
    if kind == "townhouses":
        living = village.townhouse_env(p, "gap")["floor_m2"] / FT2_M2
        garage = village.townhouse_env(p, "gap")["garage_m2"] / FT2_M2
    else:
        living = p[c + "median_new_sf_floor_area"]
        garage = p["village.townhouse.width_gap"] * p["village.townhouse.depth_m"] / FT2_M2
    build = living * p[c + "cost_per_ft2_nahb"] + garage * p[c + "garage_cost_per_ft2"]
    price = build / p[c + "construction_share"]
    afford = {k: _afford(p, inc) for k, inc in (("county median", p["pass4.rents.ami_usd"]),
                                               ("an AWS household", p["pass4.demand.salary_usd"] * p["pass4.demand.workers_per_household"]))}
    return {"living_ft2": living, "garage_ft2": garage, "build": build, "price": price, "afford": afford,
            "gap": {k: price - v for k, v in afford.items()}}


def _afford(p: dict, income: float) -> float:
    m, f = "village.money.", "pass4.finance."
    pay = income * p[m + "front_end"] / 12
    r, n = p[f + "rate"] / 12, p[f + "term_yr"] * 12
    return pay * (1 - (1 + r) ** -n) / r / (1 - p[m + "down_payment"])


# --- The report -----------------------------------------------------------------------------------

def report(p: dict, wx: dict, variant: str = "gap") -> str:
    from . import site, village

    temp = wx["t"]
    c = counts(p)
    ps = persons(p, c)
    kids = children(p, c)
    names = {0: "studio", 1: "1-bed", 2: "2-bed", 3: "3-bed"}
    L = ["**The rings of homes** (D16: flats nearest the centre, the townhouses next, houses furthest out)", "",
         f"Who: pass 4's newcomers near the campus, {c['renters']:.0f} renting and {c['owners']:.0f} buying. Renters take the flats, "
         "in the mix now built to rent (Census 2025: " + ", ".join(f"{names[b]} {p[R + f'flat_mix_{b}']:.0%}" for b in range(4))
         + f"); buyers take townhouses, or houses if they need 4 bedrooms or more ({p[R + 'owners_4bed_share']:.0%} of Indiana County's "
         "owners do, ACS B25042).", "",
         "| Ring | Homes | People | Each home | Lots | Land | Homes a hectare | School-age children |", "|---|---|---|---|---|---|---|---|"]
    mods = site.modules(p, p["site.greenhouse_ha"], site.homes_rect(p))
    for kind in RINGS:
        r = site.by(mods, kind).rect
        ha = (r[1] - r[0]) * (r[3] - r[2]) / 1e4
        n = c["flats"] if kind == "flats" else c[kind]
        each = (", ".join(f"{k} {names[b]}" for b, k in enumerate(c["flats_by_bed"]))
                + f" in {c['walkups']} walk-ups") if kind == "flats" else (
            f"{village.townhouse_env(p, variant)['floor_m2'] / FT2_M2:,.0f} ft2 over a garage-workshop" if kind == "townhouses"
            else f"{p['village.housing_cost.median_new_sf_floor_area']:,.0f} ft2, {p[R + 'house_bedrooms']:g} bedrooms, a garage-workshop beside")
        w, d = lot(p, kind, variant)
        L.append(f"| {kind} | {n} | {ps[kind]:.0f} | {each} | {w:.0f} x {d:.0f} m | {ha:.1f} ha | {n / ha:.0f} | {kids[kind]:.0f} |")
    tot_kids = sum(kids.values())
    L += ["", f"School-age children in all: about {tot_kids:.0f}, {tot_kids / 13:.0f} a grade against Homer-Center's ~"
          f"{p['village.growth_limits.school_cohort_per_grade']:.0f} (Rutgers CUPR 2018 multipliers, New Jersey)."]

    # Heat
    pm2, fh = flats_hourly_w_m2(p, temp)
    hh = house_heat(p, temp)
    loop = houses_on_loop(p, temp)
    town = village.townhouse_heat(village.townhouse_env(p, variant), temp, p)
    L += ["", "**Heat** (pass 3's model; a year, one home)", "",
          "| Home | Floor | Space heat | Garage | Hot water | Design load | On the loop? |", "|---|---|---|---|---|---|---|"]
    for b in range(4):
        m2 = p[R + f"ft2_{b}"] * FT2_M2
        L.append(f"| {names[b]} flat | {m2:.0f} m2 | {fh['kwh_m2'] * m2 / 1e3:.1f} MWh | | {hot_water_mwh(p, p[R + f'persons_{b}']):.1f} MWh "
                 f"| {fh['design_w_m2'] * m2 / 1e3:.1f} kW | yes |")
    L.append(f"| townhouse | {village.townhouse_env(p, variant)['floor_m2']:.0f} m2 | "
             f"{town['house_mwh']:.1f} MWh | {town['garage_mwh']:.1f} MWh | {town['hot_water_mwh']:.1f} MWh | {town['design_kw']:.1f} kW | yes |")
    L.append(f"| house | {hh['env']['floor_m2']:.0f} m2 | {hh['space_mwh']:.1f} MWh | {hh['garage_mwh']:.1f} MWh | {hh['hot_water_mwh']:.1f} MWh "
             f"| {hh['design_kw']:.1f} kW | {'yes' if loop['loop'] else 'no: its own heat pump'} |")
    L += ["", f"**The loop against a home's own heat pump** (pass 3's comparison over {p['cost.money.life_yr']:g} years, at each type's frontage)", "",
          "| Home | Frontage | The loop, its share of the pipes in | The loop, the operator paying the pipes | Its own heat pump |", "|---|---|---|---|---|"]
    for kind, b in (("flats", 1), ("flats", 2), ("townhouses", 2), ("houses", 2)):
        r = loop_vs_heat_pump(p, temp, kind, b)
        nm = f"{names[b]} flat" if kind == "flats" else kind[:-1]
        fr = lot(p, kind)[0] * (c["walkups"] / c["flats"] if kind == "flats" else 1)
        L.append(f"| {nm} | {fr:.1f} m | ${r['A']:,.0f} | ${r['A_operator']:,.0f} | ${r['B']:,.0f} |")
    L += ["", "The flats beat a heat pump even paying their share of the pipes. The townhouses are on the loop because the operator "
          "pays for the pipes (D11). At the houses' spacing the pipes cost too much a home, so "
          + ("they join the loop all the same." if loop["loop"] else "the outer ring heats itself with heat pumps, as pass 3 found for detached homes.")]

    # Noise
    L += ["", "**The hall at night** (WHO's guideline 40 dB(A) outside a bedroom window; the loudest window of each ring's nearest homes)", "",
          "| Ring | From the hall | Windows up to | Pass 2's fans | Fans 3 dB quieter | Fans 6 dB quieter |", "|---|---|---|---|---|---|"]
    for kind in RINGS:
        dist = site.gap(site.by(mods, kind).rect, site.HALL)
        L.append(f"| {kind} | {dist:.0f} m | {max(windows(p, kind)):.1f} m | " + " | ".join(f"{night_db(p, kind, dist, cut):.1f} dB(A)" for cut in (0.0, 3.0, 6.0)) + " |")

    # Sound between flats
    L += ["", f"**Sound between flats**: the code asks STC {p[R + 'floor_stc_code']:g} and IIC {p[R + 'floor_iic_code']:g} (IBC 1206). Pass 3b's "
          f"I-joist floor with a gypsum ceiling on resilient channel rates STC {p[R + 'floor_stc_plain']:g} / IIC {p[R + 'floor_iic_plain']:g} "
          f"with carpet, under the code's airborne rating; with 1 in. of gypsum concrete over a mat, STC {p[R + 'floor_stc_topped']:g} / "
          f"IIC {p[R + 'floor_iic_topped']:g} (AWC DCA 3, modelled; RedBuilt's tested 3/4 in. detail 58 / 54). The flats get the topping, "
          f"about ${p[R + 'topping_usd_ft2']:g} a square foot, so a neighbour's noise stays well under the code's limit. Townhouses share "
          f"no wall (or twin walls, STC {p['village.acoustics.stc_double_stud_1layer']:g}-{p['village.acoustics.stc_double_stud_2layer']:g}); "
          "houses stand apart."]

    # Money
    fm = flat_money(p)
    L += ["", "**The flats' money** (pass 4's method by size: HUD's 2024 walk-up total development cost for Johnstown, to 2026; "
          "the gap is what a builder can't raise against the rent)", "",
          "| Flat | To build | Market rent | Gap at market rent | Tax-credit rent (60% AMI) | Gap, 4% credits | Gap, 9% credits |",
          "|---|---|---|---|---|---|---|"]
    gaps = {"market-rate flat": 0.0, "tax-credit flat, 60% AMI, 4% credits": 0.0, "tax-credit flat, 60% AMI, 9% credits": 0.0}
    for b in range(4):
        f = fm[b]
        L.append(f"| {names[b]} | ${f['tdc']:,.0f} | ${f['market-rate flat']['rent']:,.0f} | ${f['market-rate flat']['gap']:,.0f} | "
                 f"${f['tax-credit flat, 60% AMI, 4% credits']['rent']:,.0f} | ${f['tax-credit flat, 60% AMI, 4% credits']['gap']:,.0f} | "
                 f"${f['tax-credit flat, 60% AMI, 9% credits']['gap']:,.0f} |")
        for k in gaps:
            gaps[k] += f[k]["gap"] * c["flats_by_bed"][b]
    L += ["", f"For phase 1's {c['flats']} flats: ${gaps['market-rate flat'] / 1e6:,.1f}M of gap at market rents, "
          f"${gaps['tax-credit flat, 60% AMI, 4% credits'] / 1e6:,.1f}M as 4% tax-credit flats, ${gaps['tax-credit flat, 60% AMI, 9% credits'] / 1e6:,.1f}M "
          "as 9% (9% credits are competitive and scarce)."]
    L += ["", "**To buy**", "", "| Home | Living / garage | To build | Price | The county's median household can pay | An AWS household | Gap (median) | Gap (AWS) |",
          "|---|---|---|---|---|---|---|---|"]
    for kind in ("townhouses", "houses"):
        o = owner_money(p, kind)
        a, g = o["afford"], o["gap"]
        gp = lambda v: f"${v:,.0f}" if v > 0 else f"none (${-v:,.0f} to spare)"
        L.append(f"| {kind[:-1]} | {o['living_ft2']:,.0f} / {o['garage_ft2']:,.0f} ft2 | ${o['build']:,.0f} | ${o['price']:,.0f} | ${a['county median']:,.0f} | "
                 f"${a['an AWS household']:,.0f} | {gp(g['county median'])} | {gp(g['an AWS household'])} |")
    aws = p["pass4.demand.salary_usd"] * p["pass4.demand.workers_per_household"]
    L += ["", f"Prices with land, fees and profit (construction {p['village.housing_cost.construction_share']:.0%} of the price, NAHB); what a "
          f"household can pay at {p['village.money.front_end']:.0%} of income: the county's median (${p['pass4.rents.ami_usd']:,.0f}) and an AWS "
          f"household (${p['pass4.demand.salary_usd']:,.0f} x {p['pass4.demand.workers_per_household']:g} workers = ${aws:,.0f})."]
    return "\n".join(L)
