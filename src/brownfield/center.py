"""D16: the centre's running costs, and the memberships that pay them. Jon, 2026-11-17: "a next
generation costco x planet fitness x your adult rec sports type of town".

The square, the mall to the great doors, the winter garden, the walks and the field's loop stay free
to everyone: a members-only centre would be an enclave and lose the natural surveillance that guards
the hall (D12). Memberships pay for the facilities: the gym, the courts, the rink, the climbing walls
and the makerspace, open 24 hours (D11).

    running cost = staff posts x hours / 2,080 x NRPA's operating cost per FTE  (the building)
                 + one sheet of ice (Victus 2025, halved) + the field's upkeep
    income       = leagues (teams x fee x seasons) + ice rented by the hour + memberships
    break-even fee a month = (running cost - leagues - ice) / members / 12

The township's own people get memberships free, paid by the trust (D11's share of the campus's tax).
"""

from __future__ import annotations

M = "village.membership."


def running(p: dict) -> dict[str, float]:
    """What the centre costs to run a year (USD)."""
    fte = (p[M + "posts_day"] * p[M + "day_h"] + p[M + "posts_night"] * (24.0 - p[M + "day_h"])) * 365.0 / p[M + "fte_h"]
    return {"the building (staff, supplies, energy, upkeep)": fte * p[M + "opex_per_fte"], "the rink": p[M + "rink_opex_usd"],
            "the field": p[M + "field_upkeep_usd"], "fte": fte}


def income(p: dict) -> dict[str, float]:
    """What leagues and ice rental bring in a year (USD), before memberships."""
    return {"hockey league": p[M + "hockey_teams"] * p[M + "hockey_fee_usd"],
            "volleyball leagues": p[M + "volleyball_teams"] * p[M + "volleyball_fee_usd"] * p[M + "seasons_yr"],
            "pickleball leagues": p[M + "pickleball_teams"] * p[M + "pickleball_fee_usd"] * p[M + "seasons_yr"],
            "ice rented by the hour": p[M + "ice_hours_week"] * p[M + "ice_weeks"] * p[M + "ice_usd_h"]}


def break_even(p: dict, members: float) -> float:
    """The monthly fee that covers the running cost not met by leagues and ice."""
    cost = sum(v for k, v in running(p).items() if k != "fte")
    return max(cost - sum(income(p).values()), 0.0) / members / 12.0


def free_local(p: dict, fee: float) -> dict[str, float]:
    """Free memberships for the host municipalities' people who take them, at the break-even fee, paid
    by the trust; against the trust's yearly share (`village.trust_money`)."""
    from . import village

    n = p[M + "local_people"] * p[M + "local_uptake"]
    trust = village.trust_money(p)
    return {"people": n, "cost": n * fee * 12.0, "trust": trust["trust"], "trust_after_cut": trust["trust_after_24%_cut"]}


def report(p: dict) -> str:
    run, inc = running(p), income(p)
    cost = sum(v for k, v in run.items() if k != "fte")
    L = ["**Running the centre** (D16; open 24 hours, D11)", "",
         "| A year | USD |", "|---|---|"]
    L += [f"| {k} | ${v:,.0f} |" for k, v in run.items() if k != "fte"]
    L += [f"| **Running cost** | **${cost:,.0f}** |"]
    L += [f"| {k} | -${v:,.0f} |" for k, v in inc.items()]
    left = cost - sum(inc.values())
    L += [f"| **Left for memberships** | **${left:,.0f}** |", "",
          f"The building's staff: {p[M + 'posts_day']:g} on duty by day and {p[M + 'posts_night']:g} at night, {run['fte']:.1f} full-time posts, "
          f"at NRPA's ${p[M + 'opex_per_fte']:,.0f} of operating cost per full-time post (54% of it pay). The rink from a 2025 study of a "
          "two-sheet centre, halved.", "",
          "| Paying members | Break-even fee a month | Against Planet Fitness's Classic | Against the YMCA of Indiana County's adult rate |",
          "|---|---|---|---|"]
    for n in (3000, p[M + "members"], 10000):
        fee = break_even(p, n)
        L.append(f"| {n:,.0f} | ${fee:,.2f} | ${p[M + 'pf_classic_usd']:g} | ${p[M + 'ymca_adult_usd']:.2f} |")
    fee = break_even(p, p[M + "members"])
    fl = free_local(p, fee)
    L += ["", f"At {p[M + 'members']:,.0f} members (Planet Fitness's average club) the fee that covers the cost is ${fee:,.2f} a month: "
          + ("under Planet Fitness's $15." if fee <= p[M + "pf_classic_usd"] else
             "between Planet Fitness's $15 and the Y's $47.50." if fee <= p[M + "ymca_adult_usd"] else "above the Y's $47.50.")
          + f" Free memberships for the host township and borough ({fl['people']:,.0f} people taking them, "
          f"{p[M + 'local_uptake']:.0%} of {p[M + 'local_people']:,.0f}) cost the trust ${fl['cost'] / 1e6:,.2f}M a year at that fee, against its "
          f"${fl['trust'] / 1e6:,.2f}M a year (${fl['trust_after_cut'] / 1e6:,.2f}M after a won appeal). Leagues and ice, at Pittsburgh-area "
          f"prices, cover ${sum(inc.values()) / 1e3:,.0f}k of the cost; the food court is a business of its own and isn't counted."]
    return "\n".join(L)
