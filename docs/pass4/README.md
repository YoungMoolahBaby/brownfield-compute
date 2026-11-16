# Pass 4: the economic base

Pass 3 ended on a condition: the data center's warm water pays for itself in new homes only if
about 1,000 flats sit within half a kilometre of the campus. Homer City has 1,716 people. So
before building any more of the walk-up, this pass asks whether the flats would fill and
whether anyone can pay for them:

1. **Who would move in**: AWS's permanent staff, the other local jobs they bring, and how many
   of the newcomers would rent in Homer City or Center Township.
2. **What a flat costs, and what pays for it**: a 2-bedroom walk-up flat against the rents
   households here can pay.
3. **Who could close the gap**: the campus's own property tax.

`uv run brownfield economy` (`src/brownfield/econ.py`, `src/brownfield/acs.py`,
`params/pass4.yaml`; output `out/pass4/economy.md`).

**The answer: the campus can easily pay for the housing it brings, but that's 100-250 flats, not
1,000.** About 120 newcomer households would rent near the campus (85-220). No new flat pays for
itself here, not even at market rent, which is why Homer City has built 13 homes since 2000.
The campus's property tax at full build-out, about $96 million a year (AWS says it won't seek
abatements), is several times what the gap costs: $21 million would cover every newcomer who'd
rent nearby, $55 million a flat for every rent-burdened household already here too. Most of
that tax, though, is school tax, which can't buy housing. The money for flats has to come from
the county and township shares or from the community benefits agreement that's still to be
written. And at this scale pass 3's warm loop only pays if the flats stand at the campus's edge.

## 1. Who would move in

AWS's filing with Indiana County (Project Narrative, 2026-08-27): 39 data centers on six sites in
Center and Blacklick Townships, built from December 2026 to 2036, **1,500-2,000 permanent
operations staff** at average salaries of $80,000-100,000. That is in line with AWS's other
campuses (Pennsylvania $20 billion and 1,250+ jobs, Indiana $11 billion and 1,000+, Mississippi
$10 billion and ~1,000, North Carolina $10 billion and 500). The other local jobs they bring
(suppliers, services, households' spending) are taken at 1 per AWS job (0.5-2.1): independent
studies find 2.1-2.27 statewide (Virginia, Ohio) and the industry's own 4.5 nationally, and a
single county keeps fewer.

| | Central | P10 / P50 / P90 |
|---|---|---|
| AWS permanent staff (2036) | 1,750 | |
| Other local jobs they bring | 1,750 | |
| Households moving in | 808 (538 AWS, 269 others) | |
| **Renters among them who'd live in Homer City or Center Township** | **121** | 85 / 140 / 219 |
| of them AWS staff (market-rate incomes) | 81 | 50 / 82 / 130 |
| of them in other local jobs (local wages) | 40 | 28 / 55 / 101 |

The housing already there (American Community Survey 2019-2023, the Census Bureau's bulk files):
Homer City and Center Township have 636 renter households, **16 homes for rent**, 104 flats in
buildings of 5 or more, and ~209 renter households paying 30% or more of their income in rent.
Homer City's 822 homes are three-quarters pre-1960, 13 built since 2000; renters' median income
there is $35,795 and median gross rent $699. The county's rental vacancy (13%) sits in Indiana
borough and White Township, 8 miles away: the student market around IUP.

- **Not 1,000 flats.** Even with every demand input at the end of its range that raises it
  (and one worker per household) the newcomers who'd rent nearby come to ~1,000; at central
  values ~120, and the Monte Carlo's P90 is ~220. The biggest unknown is how many newcomers
  choose Homer City over Indiana, the county seat with the university and the shops.
- **Two thirds of them are AWS staff** earning $80,000-100,000, above the tax-credit income
  limits (60% of the area median is $46,560 for three people): they need new flats, not cheap
  ones. The rest, and the ~209 households already paying too much, need affordable ones.

## 2. What a flat costs, and what pays for it

A 2-bedroom walk-up flat: HUD's 2024 total development cost limit for the Johnstown market
(land, site, construction, soft costs, financing; HUD's limit is 1.75 times its housing
construction cost of $161,169) raised to 2026: **$304,600**. Pass 3's wood structure, $30,000 a
flat, is 19% of that construction cost (NAHB puts framing at 16.6% of a house's).

| | Rent a month | Net operating income | Mortgage it carries | Tax-credit equity (market: value) | Gap | Gap P10 / P50 / P90 |
|---|---|---|---|---|---|---|
| Tax-credit flat, 60% AMI, 4% credits | $1,044 | $4,402 | $52,387 | $91,136 | **$161,077** | $130k / $158k / $182k |
| Tax-credit flat, 60% AMI, 9% credits | $1,044 | $4,402 | $52,387 | $205,057 | **$47,157** | $28k / $48k / $70k |
| Market-rate flat | $1,350 | $7,890 | | $121,385 | **$183,215** | $125k / $171k / $215k |

Tax-credit rents are PHFA's 2026 limits for Indiana County (2-bedroom at 60% of the $83,800
median: $1,164, less a utility allowance). A market-rate developer needs its rent to carry the
cost at a ~6.5% yield; $1,350 a month carries $121,000 of a $304,600 flat.

- **Nothing pencils without help, not even market-rate flats.** That's the local market's
  problem, not the campus's: rents here are too low for new construction, so for decades little
  has been built. The 9% credits nearly close the gap, but they're competitive and scarce
  statewide; the 4% credits are available but leave ~$160,000 a flat.
- What moves the gap most: the development cost ($109,000-186,000 across its range), then
  operating costs, then what investors pay for credits.

## 3. Who could close the gap: the campus's property tax

AWS: "AWS does not anticipate seeking any economic incentives that would reduce real property
tax assessments for local and County stakeholders, meaning the full assessed value of the
Project will contribute to the local tax base at buildout." Center Township's 2026 millage
(Indiana County Assessment Office) is 25.899: county 6.105, township 1.530, Homer-Center School
District 18.2639. Indiana County assesses at ~70% of market value (common level ratio 0.704,
from the state's 2024 sales data). What a data center's building is worth to the assessor is the
big unknown: Prince William County, Virginia assesses its 29 turnkey data centers at $1,400/sq
ft (5.84 million sq ft, $8.18 billion), but that includes the cooling and power equipment
Virginia taxes as real property; Pennsylvania doesn't tax equipment, so $600/sq ft (300-1,400)
is used.

| Taxing body | Mills | A year at full build-out |
|---|---|---|
| Indiana County | 6.105 | $22.6M |
| Center Township | 1.530 | $5.7M |
| Homer-Center School District | 18.2639 | $67.7M |
| **Total** | 25.899 | **$96.0M** (P10 / P50 / P90 $77M / $117M / $175M; $48M at the low $300/sq ft) |

- **It dwarfs the gap.** Gap funding for every newcomer household who'd rent nearby (81
  market-rate flats for AWS staff, 40 tax-credit flats) is $21.3 million, 22% of one year of
  the campus's tax; with a tax-credit flat for each of the ~209 rent-burdened households already
  here, $54.9 million, 57% of one year. A tenth of the tax, $9.6 million a year, closes the gap
  on ~60 tax-credit flats a year (34-160).
- **But most of it is school tax.** The campus's school tax alone (~$68 million a year) would be
  about three times Homer-Center School District's whole budget (close to $20 million in revenue
  for 2025-26, WCCS) and can't be spent on housing; it would let the district cut its
  residents' school tax instead. The money for flats has to come from the county's and
  township's shares (~$28 million a year together) or from the community benefits agreement AWS
  has committed to under the state's GRID standards, which isn't written yet.
- **Homer City itself gets none of it directly**: the campus is in Center and Blacklick
  Townships. Its residents share through the county and the school district; the community
  benefits agreement is where the borough's housing belongs.
- **Timing**: the tax ramps up as 39 buildings open over ten years; the flats are wanted from
  the first hires, so the fund needs bridging (a bond against the future tax, or AWS paying up
  front in the agreement).

## What it means

- **Build 100-250 flats right at the campus's edge**, mixed: market-rate flats for AWS staff and
  tax-credit flats for the town's lower-paid workers and the households already paying too much.
  At ~200 flats on a 0.25 km main pass 3's warm loop came out ~$1,300 a flat cheaper than heat
  pumps and ~$500 dearer than gas (pass 3, section 4), so the flats should stand at the fence
  line to take the data center's heat, or heat themselves.
- **Fund the gap in the community benefits agreement**: a housing fund of ~$20-55 million over
  the build-out, from the county and township shares or paid by AWS against them.
- **The 1,000-flat neighbourhood isn't the campus's to fill.** It would need far more newcomers
  than the campus brings; the warm loop's heat belongs to greenhouses, the campus itself or the
  flats at its edge, not to a new town.

## What we don't know yet

- The demand shares (who moves, who rents, who chooses Homer City) are judgement; a survey of
  the first hires, or AWS's experience at its other campuses, would set them.
- What Indiana County's assessor will put on a data center: shell and core only, or with its
  fixtures. The tax ranges from $48 to $224 million a year across that one input.
- Operating costs, credit pricing and loan terms are underwriting rules of thumb, to check with
  PHFA; HUD's development cost is a limit, not a bid.
- The construction workforce (2026-2036; the developers projected 10,000+ construction jobs for
  the power plant and the campus together) needs housing too, for a decade: not modelled.
- The hospital, schools and services a growing town needs (the plan's other pass 4 questions).
