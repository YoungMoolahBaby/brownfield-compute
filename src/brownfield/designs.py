"""The walk-up's two designs (pass 3g, D28; Addendum 11).

- **network**: Addenda 2-10's, for housing beside the campus on its heat network. The flats'
  radiant floors on a building loop from the data center's water through a substation; the
  hot-water plant preheated by that water and lifted by a water-to-water heat pump (HX-1, HP-1);
  the mini-splits cool, and heat only when the data center's heat is gone; solar panels on the
  house meter; a pressure-reducing valve on the service. Step 10's report prices this design.
- **edge**: Addendum 11's, for a town's edge, off the network (D16, D18): the quality walk-up 10h
  priced. No floors, loop or substation; the mini-splits heat; the plant kept, heated by an
  outdoor air-source heat pump water heater; no solar panels and no reducing valve.

The param `systems.design.network` names the bid set's design. `network(params)` and
`edge(params)` set it on the Param dict itself, so a Monte Carlo's workers, which rebuild the
values from it (`ranges.draws`), get the same design. Code asks which design through the readers
here, not the param.

Each design keeps its own routes: forge routes what it asks, and the network design's files stay
where they always were (`out/pass3/routes.json`, `data/route_sizes.json`), the edge design's go
under `out/pass3/edge/` (`paths`).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from . import OUT_DIR, ROOT

KEY = "systems.design.network"
# The services model each design last issued (the addendum's), named in its file and its IFC header.
ISSUE = {"network": "addendum-10", "edge": "addendum-11"}
# Both designs are drawn on Addendum 5's building and frame; step 10 is pinned to it.
MODEL = "apartment-addendum-5.json"


def _set(params: dict, v: float) -> dict:
    return {**params, KEY: replace(params[KEY], value=v, low=v, high=v)}


def network(params: dict) -> dict:
    """The parameters (the Param dict) with the network design named."""
    return _set(params, 1.0)


def edge(params: dict) -> dict:
    """The parameters (the Param dict) with the edge design named."""
    return _set(params, 0.0)


def name(p: dict) -> str:
    """'network' or 'edge', from the values or the Param dict."""
    v = p[KEY]
    return "network" if float(getattr(v, "value", v)) >= 0.5 else "edge"


def on_network(p: dict) -> bool:
    return name(p) == "network"


def floors(p: dict) -> bool:
    """The flats heated by radiant floors on the building loop (and the substation, the manifolds
    and the heat meters with them)."""
    return on_network(p)


def plant_heat(p: dict) -> str:
    """Where the hot-water plant's heat comes from: 'dc' (the data center's water, HX-1 and HP-1) or
    'air' (an outdoor air-source heat pump water heater)."""
    return "dc" if on_network(p) else "air"


def pv(p: dict) -> bool:
    """Solar panels on the house meter."""
    return on_network(p)


def prv(p: dict) -> bool:
    """A pressure-reducing valve on the water service."""
    return on_network(p)


def issue(p: dict) -> str:
    """The services model the design last issued: 'addendum-10' or 'addendum-11'."""
    return ISSUE[name(p)]


def paths(p: dict) -> dict[str, Path]:
    """The design's own files: forge's requests and routes, steps 7a-7d's records, the sizes 7c grew
    (in git), and the services model's output folder."""
    d = name(p)
    base = OUT_DIR / "pass3" if d == "network" else OUT_DIR / "pass3" / "edge"
    return {"requests": base / "route-requests.json", "routes": base / "routes.json",
            **{s: base / f"routes-{s}.json" for s in ("7a", "7b", "7c", "7d")},
            "sizes": ROOT / "data" / ("route_sizes.json" if d == "network" else "route_sizes-edge.json"),
            "services": base / "services"}
