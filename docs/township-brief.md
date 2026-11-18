# The Homer City data center campus: what the towns can ask for

*A brief for Center Township, Black Lick Township and Homer City Borough, 17 November 2026, revised
18 November from the executive order's text and the power station's filed water balance. From
brownfield-compute, independent public research, not affiliated with AWS, Homer City Redevelopment,
the county or any municipality. Not legal advice. Every number comes from a cited source or this
project's model, and the links show how.*

## Where things stand

- **AWS's plan** for 39 data centers on ~2,200 acres in Center and Black Lick Townships was filed
  under the county's land development ordinance on 14 October 2026. The county's 90-day review
  ends **12 January 2027**. The county Planning Commission takes it up on **18 November 2026 at
  5 pm** ([checklist](pass3/checklist.md), [hearing record](hearing-record.md)).
- **New rules won't reshape it.** Once a plan is filed, later changes to zoning, subdivision or
  other governing ordinances can't be used against it (Municipalities Planning Code §508(4);
  Pennsylvania Supreme Court, *Cheltenham Township*, 2019). Rules already in force still apply.
- **The levers left are the state's GRID requirements and the benefits agreement.** Executive Order
  2026-05 (18 August 2026) covers data centers over 25 MW and permits applied for after that date:
  - **Local approval comes first.** DEP issues no such permit until the project has all its local
    approvals and is consistent with the local comprehensive plan.
  - **A GRID agreement with DEP.** A developer that signs a consent order and agreement carrying the
    GRID requirements gets its permits on a rolling basis once local approval is in. One that
    doesn't waits until every application, and any water withdrawal or discharge approval, is in.
    DEP must tell the municipality when an agreement is signed.
  - **The sales tax exemption** on data center equipment now depends on meeting the GRID
    requirements.
  - **Yearly reports from 1 July 2027:** water used, peak-day demand by month, its source and
    whether for cooling, and energy.
  - **No nondisclosure agreements** for state agencies on data center projects.
  - **The GRID requirements** (DCED's summary) include:
    - water recycling and closed-loop cooling where feasible;
    - strict limits on backup generators, with testing logged in real time;
    - paying all the grid costs a project causes;
    - penalties up to revoking permits.
  - **Benefits agreements:** the order asks DCED to write best practices on them for
    municipalities. Press reports describe the standards as expecting:
    - early consultation on "key design decisions";
    - agreements covering traffic, noise, lighting and air quality, with money toward local
      priorities.

    Neither is in the order's text or DCED's list of requirements.

  AWS has committed to a benefits agreement. It isn't written yet.

## What comes whichever design AWS builds

- **Jobs:** 1,500-2,000 permanent jobs at $80,000-100,000 (AWS's filing).
- **Tax:** about $96M a year of property tax at build-out, with no abatement sought.
  - The school district gets $68M, the county $23M, and $5.7M is the township share at Center
    Township's rate. Black Lick Township's own rate applies to the buildings on its side.
  - School tax can't pay for housing. Homer City Borough gets none of it directly
    ([pass 4](pass4/README.md)).
- **Construction:** a decade of it, with ~3,300 workers on site at the peak in June 2029
  (2,900-5,300) ([workforce](pass4/workforce.md)).
  - Indiana's vacant rentals can house most crews from away.
  - Homer City, Center and Black Lick have almost none to spare.

## Ask of the design (AWS pays)

| Ask | Why | What it costs AWS |
|---|---|---|
| **Hold the halls to the water as filed, and publish the design behind it:** at most 1,400 gallons a minute from the station, metered and published, with what cools the halls | The station's water balance, filed with DEP in May 2026, gives the data centers 1,400 gallons a minute and takes 400 back: at most 1.4 million gallons a day used up. That is enough to carry ~6% of a 3,000 MW campus's heat, so the rest must leave dry ([pass 2f](pass2/water.md)). The state's yearly report will require the water figures from 2027 | Nothing, if the design is as filed |
| **No cooling towers at the halls** (dry coolers, or outside air) | For comparison: a liquid-cooled campus with its own towers, at ~3,000 MW, would draw ~27 million gallons a day. With the gas plant that is 48.6 million, more than the station's intake pumps can draw (37.6). Towers would also send ~6.8 million gallons a day of tower wastewater to the creeks, on top of the gas plant's own proposed 6.84 million. Fed from Two Lick Creek Reservoir, they would empty it in a drought like 1952's or 1991's. The reservoir also feeds Indiana's water plant ([pass 2f](pass2/water.md)) | **Air-cooled halls:** nothing, since they already use almost no water here. **Liquid-cooled AI halls:** about 3.4% of their power bill, $2.3M a year per 100 MW and ~$70M a year across the campus ([scorecard](SCORECARD.md)) |
| **40 dB(A) at night at the nearest homes**, monitored and published, with low-frequency sound (dB(C)) | 40 dB is the World Health Organization's night guideline outdoors. Cooling towers need ~700 m to fall to 40 dB(A); dry coolers behind walls need 34-80 m ([pass 2d](pass2/wall.md)) | The walls, $5.4M per 100 MW, are counted in the row above |
| **No routine diesel generator tests:** batteries carry the halls over to the gas plant next door | A conventionally backed campus this size has ~1,300 generators, and their tests put out ~300 t of NOx a year | In the model, batteries cost $58.5M less up front than generators per 100 MW ([pass 2b](pass2/cost.md)). Going without diesel is a reliability call for AWS. If it keeps diesel, ask for tests in daytime only and not on poor-air days |

**For the creek:** DEP is still deciding the gas plant's discharge and renewing its permit. Ask
DEP to ([pass 2e](pass2/creek.md)):
- set its limits from the creek's measured temperatures and Blacklick Creek's own flow;
- require the outfall's temperature to be measured continuously and published;
- require start-ups and shut-downs to ramp within the state's 2 F an hour.

## Ask in the benefits agreement (paid from the campus's money)

| Ask | Why | What it costs |
|---|---|---|
| **Independent monitoring, published:** sound at the nearest homes, water drawn and returned, the creek's temperature | At the hearings, 20 of 40 speakers raised process and openness, and 14 raised monitoring ([hearing record](hearing-record.md)) | Not costed here; small against the rest |
| **A housing fund, paid before the tax arrives** | ~120 newcomer households would rent nearby, and no new flat here pays for itself, even at market rent | $6-20M for 121 flats, depending on tax credits; ~$55M to house the ~209 households already paying too much as well. From the county and township shares, or AWS up front |
| **A crew housing plan** | Crews on $110-a-night allowances can outbid local renters, whose median rent is $699 | Master leases in Indiana borough and White Township; a rental registry and relocation help next to the site; park-and-ride; a camp on campus land if the peak passes 4,500. Not costed |
| **Homer City Borough as a party** | It takes the most new homes (109 of 242, [conference](pass3/conference.md)) and gets no tax | Nothing |
| **A clean-up bond**, set before construction and sized to clear the buildings and restore the land if the campus closes | Raised by 6 of 40 hearing speakers | Not costed |
| **Places to meet** | The new homes join the towns. Two clubhouses and the arena give them common ground | Two clubhouses: $9.6M to build and $1.02M a year, ~$577 for each of the towns' 1,760 households. The arena: $3.2M a year to run, less leagues and memberships |

## Questions for 18 November

1. What cools the halls, how much water will the campus use up, and what goes back to the creeks,
   at what temperature?
   - **A specific question:** will AWS commit to the 1,400 gallons a minute the station's filing
     gives the halls, and what cools them within it?
   - **Why it matters:** the station's intake can't supply cooling towers at the halls alongside
     the gas plant. At its full 37.6 million gallons a day, the reservoir would fall to 7% in a
     1952-type drought.
2. What is the campus's computing load in megawatts? AWS hasn't said, and it sets every water and
   sound figure.
3. How will the halls be backed up, and how often will generators be tested?
4. What will the nearest homes hear at night?
5. How many construction workers will come from beyond a daily commute, and where will they stay?
6. When will the benefits agreement be drafted, and who will sign it?
7. Will AWS sign a GRID consent order and agreement with DEP, and will its terms be public?

## What this brief doesn't know

- **AWS's cooling design and computing load.** The campus figures assume 3,000 MW (1,500-3,750),
  bounded by the 4.5 GW gas plant.
- **The tax.** It turns on what the assessor puts on a data center: $48-224M a year across that
  one input.
- **Center Township's zoning.** Whether it has zoning on these sites is unconfirmed.
- **The GRID agreement's terms.** DEP's template consent order and agreement isn't posted. The
  requirements here are from the order and DCED's summary page.
- **Whether the site is in one of DEP's environmental justice areas.** Under GRID, a project in one
  must add pollution controls, closer air and water monitoring and health safeguards.
