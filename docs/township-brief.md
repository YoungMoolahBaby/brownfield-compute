# The Homer City data center campus: what the towns can ask for

*A brief for Center Township, Black Lick Township and Homer City Borough, 17 November 2026. From
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
- **The levers left are the state's GRID standards and the benefits agreement.** The governor's
  executive order of 18 August 2026, as reported, requires a data center developer to:
  - win local approval ("If the local community doesn't approve a project, the state won't
    approve it, either");
  - consult municipal leaders early enough for "meaningful public input on key design decisions";
  - report its yearly water consumption and its source;
  - sign a community benefits agreement that covers traffic, noise, lighting and air quality, and
    pays toward local priorities.

  AWS has committed to such an agreement. It isn't written yet.

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
| **Publish the cooling design:** water drawn, used up, and returned to the creeks, and at what temperature | AWS's filing says "non-contact cooling water" from the station, returned to it, but not how much is used up. The GRID standards already require the water figures | Nothing |
| **No water evaporated or discharged to cool the halls** (dry coolers, or outside air) | For comparison: a liquid-cooled campus with its own cooling towers, at ~3,000 MW, would draw ~27 million gallons a day and send ~6.8 million of tower wastewater to the creeks. That would come on top of the gas plant's own proposed 6.84 million. Those towers would also empty Two Lick Creek Reservoir in a drought like 1952's or 1991's. The reservoir also feeds Indiana's water plant ([pass 2f](pass2/water.md)) | **Air-cooled halls:** nothing, since they already use almost no water here. **Liquid-cooled AI halls:** about 3.4% of their power bill, $2.3M a year per 100 MW and ~$70M a year across the campus ([scorecard](SCORECARD.md)) |
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
   - **A specific question:** is any of the halls' heat in the gas plant's 36 million gallons a day?
   - **Why it matters:** that figure is 12 million more than the plant's own condensers need.
     On it alone, the reservoir would fall to 12% in a 1952-type drought.
2. What is the campus's computing load in megawatts? AWS hasn't said, and it sets every water and
   sound figure.
3. How will the halls be backed up, and how often will generators be tested?
4. What will the nearest homes hear at night?
5. How many construction workers will come from beyond a daily commute, and where will they stay?
6. When will the benefits agreement be drafted, and who will sign it?

## What this brief doesn't know

- **AWS's cooling design and computing load.** The campus figures assume 3,000 MW (1,500-3,750),
  bounded by the 4.5 GW gas plant.
- **The tax.** It turns on what the assessor puts on a data center: $48-224M a year across that
  one input.
- **Center Township's zoning.** Whether it has zoning on these sites is unconfirmed.
- **The executive order's own text.** Its terms here are from news reports (Smart Cities Dive,
  2026-08-19).
