"""Pass 1 ranking: two axes kept apart, every component shown.

- host: can the site take a data center? (grid connection left behind, flood, hot hours,
  how fresh the retirement is)
- help: would the town gain? (shrinking, low income, heat it could use)

Each component is a percentile rank within the list, 0 worst to 1 best, so units never mix; an
axis is the weighted mean of its components. Percentiles say where a site stands among these
sites, not how good it is in absolute terms.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _pct(x: pd.Series, higher_is_better: bool) -> pd.Series:
    r = x.rank(pct=True, method="average", ascending=higher_is_better)
    return r.fillna(0.5)  # missing data counts as the median, and is flagged in the report


HOST = {
    "grid": lambda t: _pct(np.log(t["leaving_mw"]), True),
    "flood": lambda t: _pct(t["sfha_share"], False),
    "heat": lambda t: _pct(t["hot_hours"], False),
    "fresh": lambda t: _pct(t["years_since"], False),
}
HELP = {
    "shrinking": lambda t: _pct(t["pop_change"], False),
    "income": lambda t: _pct(t["income_vs_us"], False),
    "heat_use": lambda t: _pct(t["hdd"], True),
}


def rank(t: pd.DataFrame, p: dict) -> pd.DataFrame:
    t = t.copy()
    retired_only = t["coal_retiring_mw"] == 0
    t["years_since"] = np.where(retired_only, p["screen.rank.now_year"] - t["last_retired"], 0.0)
    for axis, comps in (("host", HOST), ("help", HELP)):
        num = 0.0
        den = 0.0
        for name, fn in comps.items():
            w = p[f"screen.rank.{axis}.{name}"]
            t[f"{axis}_{name}"] = fn(t)
            num = num + w * t[f"{axis}_{name}"]
            den += w
        t[axis] = num / den
    t["host_pct"] = t["host"].rank(pct=True)
    t["help_pct"] = t["help"].rank(pct=True)
    return t.sort_values("host", ascending=False)
