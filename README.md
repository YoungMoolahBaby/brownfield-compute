# brownfield-compute

**A data center a town would vote for.**

Data centers are being built at retired coal plants, because those sites still have what a data
center needs: a big grid connection, water rights, rail, industrial zoning. Many of those towns
are shrinking. And many data centers draw the same complaints wherever they go: water drawn for
cooling, strain on the grid and on power bills, a constant hum, diesel generators, few jobs, and
heat dumped into the air.

This project asks one question and answers it with public data and real numbers:

> When a data center comes to a retired coal plant in a shrinking town, how should it be designed
> so that the town comes out ahead?

Every answer is compared with a conventional data center on the same site; the difference is the
result. Each step ships as a short finished report with its figures and an honest list of what we
don't know.

## Passes

1. **Site screen.** Every US coal plant retired or set to retire, from EIA-860M, scored on what a
   host site needs (grid connection, flood risk, climate) and on what the town needs (population
   trend, income). Checked on known cases: sites real developers already picked (TVA's Bull Run
   for a stellarator fusion plant, Homer City for a data center campus) must rank high, or the
   screen is wrong.
2. **The good-neighbour data center** on one case-study site, against a conventional design:
   power, water, noise at the nearest homes, waste heat, backup power, jobs, taxes
   ([scorecard](docs/SCORECARD.md)).
3. **The first neighbourhood module**: a heat network to homes and a greenhouse, the first house,
   built and checked in [CortenForge](https://crates.io/crates/cortenforge).
4. **The economic base**: the employers a data center can't be (hospital, research,
   manufacturing on cheap power), and what housing costs.
5. **Fusion-ready**: a 350 MWe stellarator plant (Type One Energy's Infinity Two class) on the
   site, and what changes. A site option, never something the plan depends on.

**Status:** pass 1 done, [the site screen](docs/pass1/README.md): 205 sites, both known cases
pass, 18 in the top quarter on both axes. Pass 2 done, [Homer City](docs/pass2/README.md): the
good-neighbour data center, its [costs](docs/pass2/cost.md), [firmer inputs](docs/pass2/firm-up.md)
and [the wall in front of its coolers](docs/pass2/wall.md): brick walls between the rows of
coolers, laid by a robot, take ~12 dB off where a berm takes ~1, for about the cost of precast.
What people raised in the public record, against the scorecard:
[docs/hearing-record.md](docs/hearing-record.md). Pass 3 done, [the first neighbourhood module](docs/pass3/README.md): the first house in
CortenForge, heated straight off the data center's warm water; it pays only for dense housing
beside the campus. Decisions and next steps: [docs/PLAN.md](docs/PLAN.md).
Sources: [docs/RESEARCH.md](docs/RESEARCH.md).

## Why

The long view is a town built around shared infrastructure, planned and simulated up front and
then built quickly in repeated modules: housing people can afford, a hospital, research, food
grown on the data center's heat, on land that had lost its reason to exist. It is also a testbed
on Earth for the systems a self-sufficient settlement needs (see
[mothership](https://github.com/YoungMoolahBaby/mothership)). Large planned projects mostly fail
on cost, demand and politics rather than engineering, so this project starts with the parts that
can be checked.

## Run

```sh
uv sync
uv run brownfield sites     # pass 1: the site screen (downloads and caches ~35 MB, ~15 min the first time)
uv run brownfield rank      # pass 1: rank on both axes, draw docs/pass1/*.png
uv run brownfield check     # parameters, and the known cases against the screen
uv run pytest
```

Python (uv) for the screen, economics and GIS; Rust with CortenForge under `forge/` from pass 3.

## License

Apache-2.0.
