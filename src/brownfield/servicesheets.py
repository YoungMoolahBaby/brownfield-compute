"""Pass 3g step 8a (D28): the services drawn as sheets, for the installers' round.

Addendum 5 issued the services as a model (`services-addendum-5.ifc`), its schedules and the
viewer's layers, with no sheets, and a trade reviews and bids from sheets. `brownfield sheets`
draws them from the published files, as pass 3f drew the bid set's sheets from its IFC:
- **each trade's plan of each storey** (P-101-103, M-101-103 and the roof M-104, E-101-103,
  FP-101-103): the building's walls, doors, windows and rooms from `apartment-addendum-5.ifc`,
  cut 4 ft above each floor, and the trade's runs, risers, fixtures, equipment and terminals from
  the services model, each run tagged with its system and size;
- **the plumbing walls in elevation** (P-201, P-202), every trade in them, over the frame's studs,
  plates and joists from `framing-addendum-5.ifc`;
- **diagrams and schedules** (P-601, M-601, E-601, E-602, FP-601): the water service and the
  hot-water plant, the heating loop, the one-line and the panel schedules, the fire service and
  the hydraulic summary. Their figures (loads, flows, pressures, temperatures) are 7c's designs on
  the routes (`routed.summary`), which the model doesn't carry; each sheet says which it uses.

Each storey's plan shows its flats' own runs wherever in the joist spaces they go (a floor's drains
serve the storey above it, a ceiling's sprinkler pipe the one below), and the mains, risers, the
stair's and the annex's by the storey they're in; on Level 1 what runs under the ground slab,
dashed. A riser is drawn on every storey it passes.

The model has none of these, so neither do the sheets (G-001 lists them): the mechanical and
electrical rooms' wall-hung equipment (the diagrams show it: the riser assembly, the backflow
assemblies, the exchangers, the pumps, the mixing valve, the meter stack), the devices at the
branch circuits' ends, the smoke alarms, and the PV.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import OUT_DIR, pdfset
from .servicesifc import FT, IN, read_back

BIDSET = Path(__file__).resolve().parents[2] / "docs" / "pass3" / "bidset"
OUT = OUT_DIR / "pass3" / "services" / "sheets"
REV = "addendum-5"  # the building and the frame the sheets are drawn on, as published
SERVICES_REV = "addendum-7"  # the services model they're drawn from (servicesifc.ISSUE)
SHEETS_REV = "Addendum 7"  # the addendum that issues the sheets (Addendum 6 issued the first set, published as it was)
PDF_NAME = "services-sheets-addendum-7.pdf"

SW, SH, BORDER, TITLE_W = pdfset.SHEET_W, pdfset.SHEET_H, pdfset.BORDER, pdfset.TITLE_W
RIGHT = SW - BORDER - TITLE_W  # the title block's left edge, sheet in.
S = pdfset.SCALE_IN_PER_M  # 1/4" = 1'-0", sheet in. a metre
CUT_M = 1.2  # each plan's cut above its floor (4 ft)
PT = 72.0  # points an inch

# Each system's tag on the sheets: what it is, its colour and its line.
TAGS = {
    "CW": ("cold water, PEX-a", "#1f5fbf", "-"),
    "HW": ("hot water, PEX-a", "#c0392b", "-"),
    "HWR": ("hot-water return, PEX-a", "#c0392b", (0, (6, 2, 1, 2))),
    "SAN": ("sanitary drain, cast iron", "#5d4037", "-"),
    "V": ("vent, cast iron", "#2e7d32", (0, (4, 2))),
    "CD": ("condensate drain, PVC", "#00838f", (0, (1, 1.5))),
    "HS": ("heating supply, the building loop, PEX-a", "#e67e22", "-"),
    "HR": ("heating return", "#e67e22", (0, (4, 2))),
    "OA": ("outdoor air to the ERV, insulated", "#2c7fb8", "-"),
    "EA": ("the ERV's exhaust out", "#8e44ad", "-"),
    "VS": ("the ERV's fresh air to the mini-split", "#41b6c4", "-"),
    "EX": ("bath and kitchen exhaust to the ERV", "#c51b7d", "-"),
    "SA": ("supply air, the mini-split", "#3b7dd8", "-"),
    "RL": ("refrigerant line set, copper", "#b0306b", "-"),
    "F": ("feeder, PVC conduit", "#212121", (0, (8, 3))),
    "BC": ("branch circuit, NM-B cable", "#757575", "-"),
    "SP": ("sprinkler pipe, CPVC", "#d35400", "-"),
}
DUCTS = {"OA", "EA", "VS", "EX", "SA"}
TRADES = {  # discipline: (layers, the plans' name)
    "P": (("plumbing",), "PLUMBING"),
    "M": (("hvac",), "HEATING, COOLING AND AIR"),
    "E": (("electrical",), "POWER"),
    "FP": (("sprinklers",), "SPRINKLER"),
}
SHORT = {  # a box's label on a plan, by its key's last part (or kind)
    "wc": "WC", "lav": "LAV", "tub": "TUB", "sink": "SINK", "dishwasher": "DW", "washer": "W", "dryer": "D",
    "erv": "ERV", "minisplit": "MS", "outdoor-unit": "ODU", "manifold": "MF", "panel": "LC", "storage-tank-a": "ST-1A",
    "storage-tank-b": "ST-1B", "swing-tank": "ST-2", "heat-pump": "HP-1", "backup-heater": "BK-1",
}
HIDDEN = (0, (3, 2))


# ---- Reading the published files ----

def _boxes(f, elements) -> dict:
    from .bidset import _world_boxes
    return _world_boxes(f, [e for e in elements if e.Representation])


def building(path: Path) -> dict:
    """What the plans draw under the services: walls (each with its kind), doors, windows, rooms,
    slabs, the stair's flights, and each storey's floor level."""
    import ifcopenshell
    import ifcopenshell.util.element as U

    f = ifcopenshell.open(str(path))

    def wall_kind(w) -> str:
        t = U.get_type(w)
        n = w.Name or ""
        if t is not None and t.PredefinedType == "PLUMBINGWALL":
            return "plumbing"
        if n.startswith("annex"):
            return "annex"
        if n.startswith(("ext", "spine", "stair-left", "stair-right")):
            return "heavy"
        return "partition"

    walls, doors, wins = f.by_type("IfcWall"), f.by_type("IfcDoor"), f.by_type("IfcWindow")
    spaces, slabs, flights = f.by_type("IfcSpace"), f.by_type("IfcSlab"), f.by_type("IfcStairFlight")
    b = _boxes(f, list(walls) + list(doors) + list(wins) + list(spaces) + list(slabs) + list(flights))

    def rec(e, **kw):
        lo, hi = b[e.GlobalId]
        return {"name": e.Name or "", "lo": np.asarray(lo), "hi": np.asarray(hi), **kw}

    out = {
        "storeys": {i + 1: s.Elevation or 0.0 for i, s in enumerate(sorted(f.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation or 0.0))},
        "walls": [rec(w, kind=wall_kind(w)) for w in walls if w.GlobalId in b],
        "doors": [rec(d, pre=d.PredefinedType or (U.get_type(d).PredefinedType if U.get_type(d) else None)) for d in doors if d.GlobalId in b],
        "windows": [rec(w) for w in wins if w.GlobalId in b],
        "rooms": [rec(s, use=s.LongName or "") for s in spaces if s.GlobalId in b],
        "slabs": [rec(s, pre=s.PredefinedType) for s in slabs if s.GlobalId in b],
        "flights": [rec(s) for s in flights if s.GlobalId in b],
    }
    roof = next(s for s in out["slabs"] if s["pre"] == "ROOF")
    floors = [s for s in out["slabs"] if s["pre"] == "FLOOR"]
    # Each storey's band: from the underside of its floor to the underside of the next (the roof's).
    under = {k: min((s["lo"][2] for s in floors if abs(s["hi"][2] - z) < 0.05), default=z) for k, z in out["storeys"].items()}
    ks = sorted(out["storeys"])
    out["bands"] = [(k, -math.inf if k == ks[0] else under[k], under[k + 1] if k + 1 in under else roof["lo"][2]) for k in ks]
    out["bands"].append(("roof", roof["lo"][2], math.inf))
    lo = np.min([w["lo"] for w in out["walls"]] + [roof["lo"]], axis=0)
    hi = np.max([w["hi"] for w in out["walls"]] + [roof["hi"]], axis=0)
    out["lo"], out["hi"], out["roof"] = lo, hi, roof
    return out


def services(path: Path) -> list[dict]:
    """The services model read back (`servicesifc.read_back`), each box element with its world box."""
    import ifcopenshell

    rb = read_back(path)
    f = ifcopenshell.open(str(path))
    by_gid = {e.GlobalId: e for e in f.by_type("IfcDistributionElement")}
    boxes = _boxes(f, [by_gid[r["gid"]] for r in rb if r["sweep"] is None])
    for r in rb:
        r["box"] = None if r["sweep"] is not None else tuple(np.asarray(v) for v in boxes[r["gid"]])
        r["key"] = r["props"].get("Key", "")
        r["tag"] = tag(r)
    return rb


def framing(path: Path) -> list[dict]:
    """The frame's members with their boxes (`framing-addendum-5.ifc`)."""
    import ifcopenshell
    import ifcopenshell.util.element as U

    f = ifcopenshell.open(str(path))
    els = list(f.by_type("IfcMember")) + list(f.by_type("IfcBeam"))
    b = _boxes(f, els)
    out = []
    for e in els:
        if e.GlobalId in b:
            m = U.get_pset(e, "BF_Member") or {}
            out.append({"name": e.Name or "", "kind": m.get("Kind", ""), "lo": np.asarray(b[e.GlobalId][0]), "hi": np.asarray(b[e.GlobalId][1])})
    return out


def tag(r: dict) -> str | None:
    """A run's tag on the sheets, from its system and run."""
    pr = r["props"]
    s, run = pr.get("System"), pr.get("Run", "") or ""
    if s == "cold":
        return "CW"
    if s == "hot":
        return "HWR" if "return" in run else "HW"
    if s == "drain":
        return "SAN"
    if s == "vent":
        return "V"
    if s == "condensate":
        return "CD"
    if s == "loop":
        return "HR" if "return" in run else "HS"
    if s == "ventilation":
        part = run.split("/")[1] if run.startswith("hvac/") else ""
        return {"erv-oa": "OA", "erv-ea": "EA", "erv-supply": "VS", "erv-exhaust": "EX"}.get(part)
    if s == "air":
        return "SA"
    if s == "refrigerant":
        return "RL"
    if s == "power":
        return "F" if "feeder" in run else "BC"
    if s == "sprinkler":
        return "SP"
    return None


def drawn_as_run(r: dict) -> bool:
    """A run's own piece (not a fitting): drawn as a line."""
    return r["sweep"] is not None and r["key"].startswith(("run/", "pinned/", "drop/"))


def label_text(r: dict) -> str:
    t, pr = r["tag"], r["props"]
    size = str(pr.get("Size", "") or "")
    if t == "BC":
        return f"{pr.get('Circuit', '')} {size if size.endswith('AWG') else size + ' AWG'}"
    if t == "RL":
        return "RL " + "+".join(f'{s_}"' for s_ in size.split(" and "))
    return f'{size}" {t}' if size else t


def band_of(z: float, bands) -> int | str:
    for name, z0, z1 in bands:
        if z0 <= z < z1:
            return name
    return bands[-1][0]


def level_of(r: dict, z: float, bands) -> int | str:
    """The plan a piece at height `z` is drawn on: the roof's from the roof up; Level 1's under the
    ground slab; a flat's own run on its flat's storey, wherever in the joist spaces above or
    below it runs (a floor's drains serve the storey above it, a ceiling's sprinkler pipe the one
    below); anything else (mains, risers, the stair's, the annex's) by the storey it's in."""
    b = band_of(z, bands)
    if b == "roof" or z < 0:
        return b
    flat = str(r["props"].get("Flat") or "")
    return int(flat.split("-", 1)[0]) if flat[:1].isdigit() else b


def segments(r: dict):
    """A run's straight pieces: (a, b, vertical)."""
    pts = np.asarray(r["sweep"], float)
    for a, b in zip(pts, pts[1:]):
        d = b - a
        h, v = math.hypot(d[0], d[1]), abs(d[2])
        if h < 1e-6 and v < 1e-6:
            continue
        yield a, b, (h < 0.02 and v > h)


# ---- The sheet ----

def _figure():
    return pdfset._figure()


def title_block(ax, number: str, title: str, revision: str = SHEETS_REV, status: str = "for review: the installers' round") -> None:
    from matplotlib.patches import Rectangle

    ax.add_patch(Rectangle((BORDER, BORDER), SW - 2 * BORDER, SH - 2 * BORDER, fill=False, lw=1.5))
    ax.add_patch(Rectangle((RIGHT, BORDER), TITLE_W, SH - 2 * BORDER, fill=False, lw=1.0))
    x = RIGHT + 0.2
    lines = [("brownfield-compute, pass 3g", 11), ("12-flat walk-up", 11), ("SERVICES", 14), ("", 8),
             ("NOT FOR CONSTRUCTION", 12), ("a made-up design for a study,", 8), ("not a real project:", 8),
             ("nothing is out to bid", 8), ("", 8), ("drawn from the bid set's models:", 8), (f"the building and frame of {_rev(REV)},", 8),
             (f"the services of {_rev(SERVICES_REV)}", 8), ("", 8),
             (f"revision: {revision}", 9), (status, 9)]
    y = SH - 1.2
    for text, size in lines:
        ax.text(x, y, text, fontsize=size, va="top")
        y -= size / PT * 1.8
    ax.text(x, 3.2, "\n".join(_wrap(title.upper(), 26)), fontsize=12, va="top", weight="bold", linespacing=1.15)
    ax.text(x, 1.5, number, fontsize=28, va="top", weight="bold")


def _rev(r: str) -> str:
    return r.replace("-", " ").title()


def _wrap(text: str, width: int) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width) or [""]


class Labels:
    """Text placed where it doesn't overlap text already placed (sheet in.), trying a few offsets."""

    def __init__(self, ax, bounds=(BORDER, BORDER, RIGHT, SH - BORDER)):
        self.ax, self.boxes, self.bounds = ax, [], bounds
        self.placed = self.skipped = 0

    @staticmethod
    def _extent(text, fs, rot):
        w, h = len(text) * fs / PT * 0.56, fs / PT * 1.15
        return (h, w) if rot else (w, h)

    def free(self, x0, y0, x1, y1) -> bool:
        bx0, by0, bx1, by1 = self.bounds
        if x0 < bx0 or y0 < by0 or x1 > bx1 or y1 > by1:
            return False
        return all(x1 <= a or x0 >= c or y1 <= b or y0 >= d for a, b, c, d in self.boxes)

    def block(self, x0, y0, x1, y1):
        self.boxes.append((x0, y0, x1, y1))

    def place(self, text, x, y, fs=4.5, rot=False, color="black", tries=None, force=False, **kw) -> bool:
        w, h = self._extent(text, fs, rot)
        offs = tries or ([(0, h * 0.9), (0, -h * 0.9), (0, h * 2.0), (0, -h * 2.0), (w * 0.6, h * 0.9), (-w * 0.6, h * 0.9)] if not rot
                         else [(w * 0.9, 0), (-w * 0.9, 0), (w * 2.0, 0), (-w * 2.0, 0), (w * 0.9, h * 0.6), (w * 0.9, -h * 0.6)])
        for dx, dy in offs:
            cx, cy = x + dx, y + dy
            box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            if self.free(*box) or force:
                self.ax.text(cx, cy, text, fontsize=fs, ha="center", va="center", rotation=90 if rot else 0, color=color, zorder=7, **kw)
                self.block(*box)
                self.placed += 1
                return True
        self.skipped += 1
        return False


# ---- Plans ----

class PlanT:
    """Building (x, y) in m to sheet in.: the long side (y) across, the front (x = 0) at the top."""

    def __init__(self, bld: dict, px: float = 1.4, top: float = SH - 1.4):
        self.ymin, self.xmax = bld["lo"][1], bld["hi"][0]
        self.px = px - self.ymin * S
        self.top = top
        self.w = (bld["hi"][1] - bld["lo"][1]) * S
        self.h = (bld["hi"][0] - bld["lo"][0]) * S
        self.bottom = top - self.h

    def __call__(self, x, y):
        return self.px + y * S, self.bottom + (self.xmax - x) * S

    def rect(self, lo, hi):
        (x0, y0), (x1, y1) = self(lo[0], lo[1]), self(hi[0], hi[1])
        return min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)


def _background(ax, T: PlanT, bld: dict, level, L: Labels, roof: bool = False) -> None:
    from matplotlib.patches import Rectangle

    if roof:
        r = bld["roof"]
        ax.add_patch(Rectangle(T.rect(r["lo"], r["hi"])[:2], *T.rect(r["lo"], r["hi"])[2:], fill=False, lw=1.0, ec="#424242"))
        for w in bld["walls"]:
            if w["kind"] == "annex":
                ax.add_patch(Rectangle(T.rect(w["lo"], w["hi"])[:2], *T.rect(w["lo"], w["hi"])[2:], fill=False, lw=0.5, ec="#9e9e9e", ls=HIDDEN))
        for d in bld["doors"]:
            if d["pre"] == "TRAPDOOR":
                x, y, w_, h_ = T.rect(d["lo"], d["hi"])
                ax.add_patch(Rectangle((x, y), w_, h_, fill=False, lw=0.9, ec="black"))
                ax.plot([x, x + w_], [y, y + h_], color="black", lw=0.4)
                ax.plot([x, x + w_], [y + h_, y], color="black", lw=0.4)
                a_in, b_in = sorted(round((d["hi"][k] - d["lo"][k]) / IN) for k in (0, 1))
                L.place(f"ROOF HATCH {a_in} x {b_in} IN. (ADDENDUM 5 ITEM 2)", x + w_ / 2, y - 0.12, fs=5, force=True)
        return
    z = bld["storeys"][level] + CUT_M
    for w in bld["walls"]:
        if w["lo"][2] - 1e-6 <= z <= w["hi"][2] + 1e-6:
            fc = {"heavy": "#9e9e9e", "plumbing": "#d7ccc8", "annex": "#9e9e9e", "partition": "#cfcfcf"}[w["kind"]]
            x, y, w_, h_ = T.rect(w["lo"], w["hi"])
            ax.add_patch(Rectangle((x, y), w_, h_, fc=fc, ec="#616161", lw=0.25))
        elif w["kind"] == "annex" and level != 1:
            x, y, w_, h_ = T.rect(w["lo"], w["hi"])
            ax.add_patch(Rectangle((x, y), w_, h_, fill=False, ec="#bdbdbd", lw=0.4, ls=HIDDEN))
    for d in bld["doors"] + bld["windows"]:
        if d["lo"][2] - 1e-6 <= z <= d["hi"][2] + 1e-6:
            x, y, w_, h_ = T.rect(d["lo"], d["hi"])
            ax.add_patch(Rectangle((x, y), w_, h_, fc="white", ec="#616161", lw=0.25))
    for fl in bld["flights"]:
        if fl["lo"][2] - 0.2 <= z <= fl["hi"][2] + 1.5 and fl["lo"][2] < z:
            x, y, w_, h_ = T.rect(fl["lo"], fl["hi"])
            ax.add_patch(Rectangle((x, y), w_, h_, fill=False, ec="#9e9e9e", lw=0.4))
    base = bld["storeys"][level]
    flats: dict[str, list] = defaultdict(list)
    for r in bld["rooms"]:
        if abs(r["lo"][2] - base) > 0.5:
            continue
        x, y, w_, h_ = T.rect(r["lo"], r["hi"])
        name = r["name"].split("/")[-1].replace("-", " ").upper()
        ax.text(x + 0.06, y + h_ - 0.06, name, fontsize=4.5, color="#9e9e9e", ha="left", va="top")
        L.block(x + 0.02, y + h_ - 0.14, x + 0.1 + len(name) * 0.035, y + h_ - 0.02)
        if "/" in r["name"] and r["name"][0].isdigit():
            flats[r["name"].split("/")[0]].append((r["lo"], r["hi"]))
    for flat, bs in flats.items():
        lo, hi = np.min([b[0] for b in bs], axis=0), np.max([b[1] for b in bs], axis=0)
        cx, cy = T((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
        ax.text(cx, cy, f"FLAT {flat.upper()}", fontsize=11, color="#e0e0e0", ha="center", va="center", weight="bold", zorder=0)


def _style(t: str, below: bool) -> dict:
    _, colour, ls = TAGS[t]
    return {"color": colour, "ls": HIDDEN if below else ls}


def _lw(r: dict) -> float:
    """A line's width in points: a duct at its true width at 1/4" = 1'-0", a pipe by its size."""
    d = float(r["props"].get("OutsideDiameter") or r.get("d") or 0.02)
    if r["tag"] in DUCTS:
        return max(d * S * PT, 2.0)
    if r["tag"] == "BC":
        return 0.45
    return min(max(0.5 + d / IN * 0.35, 0.6), 2.4)


def draw_plan(ax, bld: dict, rb: list[dict], trade: str, level, s7: dict | None, drawn: set, L: Labels, T: PlanT) -> Counter:
    """One trade's plan of one storey (or the roof): its lines, risers, boxes and tags. Returns the
    tags drawn (for the legend)."""
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Circle, Rectangle

    layers = TRADES[trade][0] if level != "roof" else tuple(lay for ls, _ in TRADES.values() for lay in ls)
    bands = bld["bands"]
    used: Counter = Counter()
    lines: dict[tuple, list] = defaultdict(list)
    risers = []
    labels = []
    design = set()
    if trade == "FP" and s7:
        w = s7["fire"]["worst"]
        design = set(w["design"])
    for r in rb:
        if r["props"].get("Layer") not in layers:
            continue
        if drawn_as_run(r) and r["tag"]:
            best, best_len = None, 0.0
            for a, b, vert in segments(r):
                if vert:
                    z0, z1 = sorted((a[2], b[2]))
                    if r["key"].startswith("pinned/") or not str(r["props"].get("Flat") or "")[:1].isdigit():
                        on = [n for n, b0, b1 in bands if min(z1, b1) - max(z0, b0) > 0.05]  # on every storey it passes
                    else:
                        on = [level_of(r, (z0 + z1) / 2, bands)]
                    if level in on:
                        risers.append((r, a))
                        drawn.add(r["key"])
                    continue
                zm = (a[2] + b[2]) / 2
                if level_of(r, zm, bands) != level:
                    continue
                below = zm < 0 and level == 1
                key = (r["tag"], below, round(_lw(r), 2))
                lines[key].append([T(a[0], a[1]), T(b[0], b[1])])
                used[r["tag"]] += 1
                drawn.add(r["key"])
                ln = math.hypot(b[0] - a[0], b[1] - a[1])
                if ln > best_len:
                    best, best_len = (a, b), ln
            if best is not None and best_len >= 0.5:
                labels.append((r, best))
        elif r["box"] is not None or r["key"].startswith("head/"):
            if r["key"].startswith("head/"):
                at = np.asarray(r["sweep"][0], float)
                if level_of(r, at[2], bands) != level:
                    continue
                x, y = T(at[0], at[1])
                rad = 0.05
                filled = r["key"][len("head/"):] in design
                ax.add_patch(Circle((x, y), rad, fc="#d35400" if filled else "white", ec="#d35400", lw=0.6, zorder=5))
                ax.plot([x - rad, x + rad], [y - rad, y + rad], color="#d35400", lw=0.4, zorder=6)
                ax.plot([x - rad, x + rad], [y + rad, y - rad], color="#d35400", lw=0.4, zorder=6)
                L.block(x - rad, y - rad, x + rad, y + rad)
                drawn.add(r["key"])
                used["head"] += 1
                continue
            lo, hi = r["box"]
            if level_of(r, (lo[2] + hi[2]) / 2, bands) != level:
                continue
            x, y, w_, h_ = T.rect(lo, hi)
            kind = r["key"].split("/")[0]
            if kind == "air":
                ax.add_patch(Rectangle((x, y), w_, h_, fc="white", ec="#3b7dd8", lw=0.5, zorder=4))
                ax.plot([x, x + w_], [y, y + h_], color="#3b7dd8", lw=0.3, zorder=4)
                ax.plot([x, x + w_], [y + h_, y], color="#3b7dd8", lw=0.3, zorder=4)
                txt = _terminal_text(r, s7)
                L.place(txt, x + w_ / 2, y + h_ / 2, fs=5.0, color="#1a237e")
            else:
                ax.add_patch(Rectangle((x, y), w_, h_, fc="white", ec="black", lw=0.5, zorder=3, alpha=0.9))
                last = r["key"].split("/")[-1]
                short = SHORT.get(last, "LS" if kind == "switch" else last.upper()[:4])
                # On the roof each outdoor unit says whose it is: their line sets are all one size.
                text = f"{short} {r['props'].get('Flat', '')}" if last == "outdoor-unit" else short
                ax.text(x + w_ / 2, y + h_ / 2, text, fontsize=4.5 if min(w_, h_) > 0.12 and text == short else 3.5, ha="center",
                        va="center", zorder=4)
                L.block(x, y, x + w_, y + h_)
                used[f"box:{short}"] += 1
            drawn.add(r["key"])
    for (t, below, lw), segs in sorted(lines.items(), key=lambda kv: kv[0][0] not in DUCTS):  # ducts first, under the pipes
        st = _style(t, below)
        if t in DUCTS:
            ax.add_collection(LineCollection(segs, colors=st["color"], linewidths=lw, alpha=0.28, capstyle="butt", zorder=1))
            ax.add_collection(LineCollection(segs, colors=st["color"], linewidths=0.35, linestyles=st["ls"], zorder=2))
        else:
            ax.add_collection(LineCollection(segs, colors=st["color"], linewidths=lw, linestyles=st["ls"], capstyle="butt", zorder=2))
    seen_riser = set()
    for r, a in risers:
        x, y = T(a[0], a[1])
        k = (r["key"], round(x, 2), round(y, 2))
        if k in seen_riser:
            continue
        seen_riser.add(k)
        d = float(r["props"].get("OutsideDiameter") or r.get("d") or 0.02)
        rad = max(d * S / 2, 0.025)
        ax.add_patch(Circle((x, y), rad, fc="white", ec=TAGS[r["tag"]][1], lw=0.6, zorder=5))
        used[r["tag"]] += 1
        if r["key"].startswith("pinned/"):
            L.place(label_text(r), x, y + rad + 0.07, fs=5.0, color=TAGS[r["tag"]][1])
    for r, (a, b) in labels:
        if level == "roof" and r["tag"] == "RL":
            continue  # each outdoor unit is tagged with its flat; the line sets' one size is in the notes
        (x0, y0), (x1, y1) = T(a[0], a[1]), T(b[0], b[1])
        rot = abs(y1 - y0) > abs(x1 - x0)
        L.place(label_text(r), (x0 + x1) / 2, (y0 + y1) / 2, fs=5.0, rot=rot, color=TAGS[r["tag"]][1])
    return used


def _terminal_text(r: dict, s7: dict | None) -> str:
    """A register's, grille's or wall cap's tag: its size and, where 7c gives it, its air."""
    pr = r["props"]
    rid = pr.get("Run", "")
    term = r["key"][len("air/") + len(rid) + 1:]
    kind = pr.get("Kind", "")
    cfm, size = None, pr.get("Size", "")
    if s7 and pr.get("Flat"):
        d = s7["ducts"].get(pr["Flat"], {})
        role = rid.split("/")[1] if "/" in rid else ""
        part = {"ms-supply": "ms", "erv-exhaust": "erv_exhaust", "erv-supply": "erv_supply"}.get(role)
        if part and term in d.get(part, {}).get("paths", {}):
            cfm, size = d[part]["paths"][term]["cfm"], f"{d[part]['paths'][term]['in']:g}"
    head = "S" if "supply" in kind else "E" if "exhaust grille" in kind else "CAP"
    return f"{head} {size}\"" + (f" {cfm:.0f} CFM" if cfm is not None else "") + (" OA" if "intake" in kind else " EA" if "(exhaust)" in kind else "")


def _legend(ax, x: float, y: float, used: Counter, trade: str, extra: list[str] | None = None) -> float:
    """The sheet's legend: each tag drawn with its line, the boxes' abbreviations."""
    ax.text(x, y, "LEGEND", fontsize=8, weight="bold", va="top")
    y -= 0.3
    for t, (what, colour, ls) in TAGS.items():
        if not used.get(t):
            continue
        if t in DUCTS:
            ax.plot([x, x + 0.5], [y, y], color=colour, lw=6, alpha=0.28, solid_capstyle="butt")
            ax.plot([x, x + 0.5], [y, y], color=colour, lw=0.35)
        else:
            ax.plot([x, x + 0.5], [y, y], color=colour, lw=1.0, ls=ls)
        ax.text(x + 0.6, y, f"{t}  {what}", fontsize=5.5, va="center")
        y -= 0.2
    if any(used.get(t) for t in TAGS):
        ax.plot([x, x + 0.5], [y, y], color="#616161", lw=1.0, ls=HIDDEN)
        ax.text(x + 0.6, y, "dashed: under the ground slab", fontsize=5.5, va="center")
        y -= 0.2
        from matplotlib.patches import Circle
        ax.add_patch(Circle((x + 0.25, y), 0.04, fc="white", ec="black", lw=0.6))
        ax.text(x + 0.6, y, "a riser or a drop (up or down)", fontsize=5.5, va="center")
        y -= 0.2
    if used.get("head"):
        from matplotlib.patches import Circle
        for filled, what in ((False, "sprinkler, residential pendent (FP-601)"), (True, "sprinkler in the design area (FP-601)")):
            ax.add_patch(Circle((x + 0.25, y), 0.05, fc="#d35400" if filled else "white", ec="#d35400", lw=0.6))
            ax.text(x + 0.6, y, what, fontsize=5.5, va="center")
            y -= 0.2
    boxes = {
        "WC": "water closet", "LAV": "lavatory", "TUB": "bathtub", "SINK": "kitchen sink", "DW": "dishwasher", "W": "washer (D over it)",
        "D": "dryer", "ERV": "energy recovery ventilator (M-601)", "MS": "mini-split indoor unit, ducted (M-601)",
        "ODU": "mini-split outdoor unit (M-601)", "MF": "radiant manifold in its cabinet", "LC": "load centre (E-602)",
        "ST-1": "hot-water storage tank (P-601)", "ST-2": "swing tank (P-601)", "HP-1": "water-to-water heat pump (P-601)",
        "LS": "water-level switch (IMC 307.2.3)"}
    shown = [(k, v) for k, v in boxes.items() if used.get(f"box:{k}")]
    if shown:
        y -= 0.1
        for k, v in shown:
            ax.text(x, y, k, fontsize=5.5, va="center", weight="bold")
            ax.text(x + 0.6, y, v, fontsize=5.5, va="center")
            y -= 0.18
    for line in extra or []:
        y -= 0.05
        for part in _wrap(line, 62):
            ax.text(x, y, part, fontsize=5.5, va="center")
            y -= 0.17
    return y


NOTES = {
    "P": [
        "PEX is bent on a bend support at its turns; elbows only at the fixtures' stub-outs, the risers' feet, where the top flat's "
        "branch leaves its riser, and at the manifolds (Addendum 5, item 4a).",
        "Holes through studs, plates and joists are bored at the member's centre: there every pipe clears IPC 305.6 without a steel "
        "plate. Joist holes within APA's Table 5 for the PRI-60 (the holes schedule) (item 4b).",
        "A 2 in. vent stack in each column's plumbing wall (IPC 905.1, Table 906.1) (item 4d). Stacks and branches above the slab are "
        "cast iron, for quiet.",
        "Firestop every opening through a rated assembly by its condition in the firestop schedule (item 5); pipe insulation stops at "
        "each face of a rated floor (IBC 714.3).",
        "The fixtures' sizes are placeholders for the drawing: no fixture is chosen.",
    ],
    "M": [
        "Each mini-split's static pressure is set to its ducts by Fujitsu's function setting (M-601), and each takes a UL 508 "
        "water-level switch at its drain, wired to its forced stop (IMC 307.2.3 item 4) (Addendum 5, item 4e).",
        "The flats' ducts run in soffits below the rated ceiling, not in the joists: APA's hole chart all but bars the ducts' sizes "
        "there, and IBC 717.6.2 would ask a ceiling radiation damper at every register.",
        "The radiant loops run in the floors' topping and are not drawn; each flat's manifold (MF) and its tails are.",
        "Line sets to the roof run in the plumbing walls; the outdoor units on the roof (M-104).",
        "Firestop every opening through a rated assembly by its condition in the firestop schedule (Addendum 5, item 5).",
    ],
    "E": [
        "The feeders' PVC conduit runs straight under the slab between its stub-ups, at most 356 degrees of bends from the meter to a "
        "panel (NEC 352.26: 360), with no pull point between (Addendum 5, item 4c).",
        "Holes through studs and plates are bored at the member's centre: there every cable clears NEC 300.4(A)(1) without a steel "
        "plate (item 4b).",
        "Each branch circuit is drawn to its farthest outlet, as routed; the outlets, switches and luminaires are not placed in the "
        "model. The panel schedules (E-602) give each circuit's breaker, wire, load and drop.",
        "The meter stack is on the annex's outside wall (E-601); it is not in the model.",
    ],
    "FP": [
        "NFPA 13R (2019) throughout, CPVC (BlazeMaster, SDR 13.5), concealed. None in the roof's joist space or the floors (13R 6.6.6).",
        "Each flat's feed leaves the stair's riser through the stair's side wall at its door (IBC 1023.5); the stair's own sprinklers "
        "on the same riser.",
        "The fire service, its backflow assembly and its supervised valves: FP-601. The hydraulic summary: FP-601.",
        "Firestop every opening through a rated assembly by its condition in the firestop schedule (Addendum 5, item 5).",
    ],
}


def plan_sheet(ax, number: str, bld: dict, rb: list[dict], trade: str, level, s7: dict | None, drawn: set) -> Labels:
    title = "ROOF PLAN, ALL TRADES" if level == "roof" else f"LEVEL {level} {TRADES[trade][1]} PLAN"
    title_block(ax, number, title)
    L = Labels(ax)
    T = PlanT(bld)
    roof = level == "roof"
    _background(ax, T, bld, level, L, roof=roof)
    used = draw_plan(ax, bld, rb, trade, level, s7, drawn, L, T)
    ax.text(T.px + T.ymin * S, T.top + 0.25, "FRONT", fontsize=7, va="bottom", color="#616161")
    ax.text(T.px + T.ymin * S, T.bottom - 0.2, "BACK", fontsize=7, va="top", color="#616161")
    ax.text(1.4, T.bottom - 0.6, title, fontsize=12, weight="bold", va="top")
    span = ("from the roof up" if roof else
            f"cut {CUT_M / FT:.0f} ft above the floor; each flat's own runs, in the floor and ceiling spaces too"
            + ("; under the ground slab dashed" if level == 1 else ""))
    ax.text(1.4, T.bottom - 0.95, f'SCALE: 1/4" = 1\'-0"   ({span})', fontsize=7, va="top")
    extra = []
    if trade == "FP" and s7 and level != "roof":
        w = s7["fire"]["worst"]
        if w["flat"].startswith(f"{level}-"):
            extra.append(f"Design area: {w['flat']}'s {w['comp']} area, {len(w['design'])} sprinklers, {w['q_gpm']:.0f} gpm, "
                         f"{w['need_psi']:.1f} psi needed at the street, of {s7['fire']['target_psi']:.0f} (FP-601).")
    y = _legend(ax, RIGHT - 4.4, SH - 1.4, used, trade, extra)
    rl = sorted({label_text(r) for r in rb if r["tag"] == "RL" and drawn_as_run(r)})
    notes = NOTES[trade] if not roof else [
        "The outdoor units on stands at Fujitsu's clearances, each tagged with its flat; each line set rises in its column's plumbing "
        f"wall and crosses the roof to its unit ({', '.join(rl)}).",
        "Stacks and vent stacks through the roof (VTR) at the height the authority adopts (IPC 903.1.1 leaves it to it; Pennsylvania's "
        "not found).",
        "The roof hatch and its fixed ladder: Addendum 5, item 2.",
    ]
    yy = min(y - 0.3, T.bottom - 1.5)
    ax.text(RIGHT - 4.4 if yy > 6 else 1.4, yy, "NOTES", fontsize=8, weight="bold", va="top")
    x_notes = RIGHT - 4.4 if yy > 6 else 1.4
    width = 62 if x_notes > 10 else 150
    yy -= 0.3
    for i, n in enumerate(notes, 1):
        parts = _wrap(n, width)
        ax.text(x_notes, yy, f"{i}.", fontsize=5.8, va="top")
        for p_ in parts:
            ax.text(x_notes + 0.18, yy, p_, fontsize=5.8, va="top")
            yy -= 0.17
        yy -= 0.06
    return L


# ---- The plumbing walls in elevation ----

COLUMNS = ("front-left", "back-left", "front-right", "back-right")


def wall_box(bld: dict, col: str):
    ws = [w for w in bld["walls"] if w["kind"] == "plumbing" and w["name"].split("/")[0].split("-", 1)[1] == col]
    return np.min([w["lo"] for w in ws], axis=0), np.max([w["hi"] for w in ws], axis=0)


def draw_wall(ax, x0: float, y0: float, scale: float, bld: dict, rb: list[dict], members: list[dict], col: str, drawn: set, L: Labels) -> tuple:
    """A column's plumbing wall seen from its flats, every trade in it: x0, y0 the sheet in. of
    its lower left. Returns its width and height on the sheet, and the tags it drew."""
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Circle, Rectangle

    lo, hi = wall_box(bld, col)
    margin = 0.6
    ylo, yhi = lo[1] - margin, hi[1] + margin
    zlo, zhi = -1.4, bld["roof"]["hi"][2] + 1.0
    front = col.startswith("front")

    def U(y):  # along the wall as seen from the flat: front flats look +x, so y runs right to left
        return x0 + ((yhi - y) if front else (y - ylo)) * scale

    def Z(z):
        return y0 + (z - zlo) * scale

    width, height = (yhi - ylo) * scale, (zhi - zlo) * scale
    # The floors and the roof, and the ground.
    for s in bld["slabs"]:
        if s["hi"][1] < ylo or s["lo"][1] > yhi or s["hi"][0] < lo[0] or s["lo"][0] > hi[0]:
            continue
        a, b = max(s["lo"][1], ylo), min(s["hi"][1], yhi)
        ux0, ux1 = sorted((U(a), U(b)))
        ax.add_patch(Rectangle((ux0, Z(s["lo"][2])), ux1 - ux0, (s["hi"][2] - s["lo"][2]) * scale, fc="#eeeeee", ec="#bdbdbd", lw=0.3, zorder=0))
    ax.plot([x0, x0 + width], [Z(-0.1016), Z(-0.1016)], color="#8d6e63", lw=0.6)
    ax.text(x0 + 0.05, Z(-0.1016) - 0.05, "UNDER THE SLAB", fontsize=4.5, color="#8d6e63", va="top")
    # The frame: the wall's studs and plates, and the joists crossing it.
    for m in members:
        if m["hi"][0] <= lo[0] + 1e-3 or m["lo"][0] >= hi[0] - 1e-3 or m["hi"][1] < ylo or m["lo"][1] > yhi:
            continue
        a, b = max(m["lo"][1], ylo), min(m["hi"][1], yhi)
        ux0, ux1 = sorted((U(a), U(b)))
        ax.add_patch(Rectangle((ux0, Z(m["lo"][2])), ux1 - ux0, (m["hi"][2] - m["lo"][2]) * scale, fill=False, ec="#a1887f", lw=0.25, zorder=1))
    # The rooms along it, at each floor.
    for r in bld["rooms"]:
        if r["name"].split("/")[0].split("-", 1)[-1] != col or not r["name"][0].isdigit():
            continue
        near = min(abs(r["hi"][0] - lo[0]), abs(r["lo"][0] - hi[0]))
        if near > 0.3 or r["hi"][1] < lo[1] or r["lo"][1] > hi[1]:
            continue
        a, b = max(r["lo"][1], ylo), min(r["hi"][1], yhi)
        L.place(r["name"].split("/")[-1].upper(), (U(a) + U(b)) / 2, Z(r["lo"][2]) + 0.22, fs=5, color="#9e9e9e", force=True)
    # The fixtures in front of it, faint.
    for r in rb:
        if not r["key"].startswith(("fixture/", "eq/")) or r["box"] is None:
            continue
        blo, bhi = r["box"]
        if r["props"].get("Flat", "").split("-", 1)[-1] != col or min(abs(bhi[0] - lo[0]), abs(blo[0] - hi[0])) > 1.0:
            continue
        if bhi[1] < ylo or blo[1] > yhi:
            continue
        ux0, ux1 = sorted((U(max(blo[1], ylo)), U(min(bhi[1], yhi))))
        ax.add_patch(Rectangle((ux0, Z(blo[2])), ux1 - ux0, (bhi[2] - blo[2]) * scale, fill=False, ec="#bdbdbd", lw=0.4, ls=HIDDEN, zorder=1))
        last = r["key"].split("/")[-1]
        ax.text((ux0 + ux1) / 2, Z(bhi[2]) - 0.05, SHORT.get(last, last.upper()), fontsize=4, color="#9e9e9e", ha="center", va="top")
    # The services in the wall.
    lines: dict[tuple, list] = defaultdict(list)
    used = Counter()
    risers: dict[str, list] = defaultdict(list)
    for r in rb:
        if not drawn_as_run(r) or not r["tag"]:
            continue
        for a, b, vert in segments(r):
            m = (a + b) / 2
            inside_x = lo[0] - 0.015 <= m[0] <= hi[0] + 0.015
            inside_y = ylo <= m[1] <= yhi
            if not inside_y:
                continue
            along_x = abs(b[0] - a[0]) > 0.02 and abs(b[1] - a[1]) < 0.01 and abs(b[2] - a[2]) < 0.01
            if along_x:
                xs = sorted((a[0], b[0]))
                if xs[0] <= hi[0] and xs[1] >= lo[0]:
                    d = float(r["props"].get("OutsideDiameter") or r.get("d") or 0.02)
                    ax.add_patch(Circle((U(a[1]), Z(a[2])), max(d * scale / 2, 0.02), fc="white", ec=TAGS[r["tag"]][1], lw=0.5, zorder=4))
                    drawn.add(r["key"])
                continue
            if not inside_x:
                continue
            lw = _lw(r) if r["tag"] not in DUCTS else min(max(float(r["props"].get("OutsideDiameter") or 0.02) * scale * PT, 0.5), 6.0)
            lines[(r["tag"], round(lw, 1))].append([(U(a[1]), Z(a[2])), (U(b[1]), Z(b[2]))])
            used[r["tag"]] += 1
            drawn.add(r["key"])
            if vert and r["key"].startswith("pinned/"):
                risers[r["key"]].append((r, a, b))
    for (t, lw), segs in lines.items():
        st = _style(t, False)
        ax.add_collection(LineCollection(segs, colors=st["color"], linewidths=lw, linestyles=st["ls"], alpha=0.85, capstyle="butt", zorder=3))
    # Each riser tagged once a storey.
    for key, parts in sorted(risers.items()):
        r = parts[0][0]
        z0 = min(min(a[2], b[2]) for _, a, b in parts)
        z1 = max(max(a[2], b[2]) for _, a, b in parts)
        u = U(parts[0][1][1])
        for k, base in bld["storeys"].items():
            zm = base + 1.6
            if z0 <= zm <= z1:
                L.place(label_text(r), u, Z(zm), fs=5.2, rot=True, color=TAGS[r["tag"]][1])
    flats = ", ".join(f"{k}-{col}" for k in sorted(bld["storeys"]))
    ax.text(x0, y0 - 0.25, f"PLUMBING WALL, COLUMN {col.upper()}", fontsize=10, weight="bold", va="top")
    ax.text(x0, y0 - 0.55, f"flats {flats}, seen from the flats; every trade in the wall, over its frame", fontsize=6.5, va="top")
    return width, height, used


def wall_sheet(ax, number: str, cols: tuple[str, str], bld, rb, members, drawn) -> Labels:
    title_block(ax, number, "PLUMBING WALLS IN ELEVATION, ALL TRADES")
    L = Labels(ax)
    span = max(wall_box(bld, c)[1][1] - wall_box(bld, c)[0][1] for c in COLUMNS) + 1.2
    scale = 0.375 / FT  # 3/8" = 1'-0"
    if 2 * span * scale + 2.5 > RIGHT - 1.4 - 4.6:
        scale = S
    x = 1.4
    used = Counter()
    for c in cols:
        w, h, u = draw_wall(ax, x, 2.6, scale, bld, rb, members, c, drawn, L)
        used.update(u)
        x += w + 1.4
    sc = '3/8" = 1\'-0"' if abs(scale - 0.375 / FT) < 1e-9 else '1/4" = 1\'-0"'
    ax.text(1.4, 1.75, f"SCALE: {sc}", fontsize=7, va="top")
    y = _legend(ax, RIGHT - 4.4, SH - 1.4, used, "P")
    notes = [
        "Studs, plates and joists from the frame model (framing-addendum-5.ifc); the joists cross the wall in section. A run "
        "crossing a member is bored through it at its centre (Addendum 5, item 4b; the holes schedule).",
        "A circle is a run leaving the wall square to it: a stub-out to a fixture, the closet bend, a branch into the floor.",
        "Firestop each opening through a rated assembly by its condition in the firestop schedule (item 5).",
        "Lengths and sizes: the services schedules; each run's tag gives its size and system.",
    ]
    yy = y - 0.3
    ax.text(RIGHT - 4.4, yy, "NOTES", fontsize=8, weight="bold", va="top")
    yy -= 0.3
    for i, n in enumerate(notes, 1):
        ax.text(RIGHT - 4.4, yy, f"{i}.", fontsize=5.8, va="top")
        for p_ in _wrap(n, 62):
            ax.text(RIGHT - 4.22, yy, p_, fontsize=5.8, va="top")
            yy -= 0.17
        yy -= 0.06
    return L


# ---- Diagrams and schedules ----

def _box(ax, x, y, w, h, text, fs=6.0, fc="white", ec="black", lw=0.8, bold_first=True):
    from matplotlib.patches import Rectangle

    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, zorder=3))
    lines = text.split("\n")
    yy = y + h / 2 + (len(lines) - 1) * fs / PT * 0.62
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, yy, ln, fontsize=fs, ha="center", va="center", weight="bold" if (i == 0 and bold_first) else "normal", zorder=4)
        yy -= fs / PT * 1.25
    return (x, y, w, h)


def _pipe(ax, pts, colour="black", lw=1.2, ls="-", arrow=True, text=None, fs=5.5, at=0.5, side=1):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=colour, lw=lw, ls=ls, zorder=2, solid_capstyle="butt")
    if arrow and len(pts) >= 2:
        (xa, ya), (xb, yb) = pts[-2], pts[-1]
        ax.annotate("", xy=(xb, yb), xytext=(xa + (xb - xa) * 0.6, ya + (yb - ya) * 0.6),
                    arrowprops={"arrowstyle": "-|>", "color": colour, "lw": lw, "mutation_scale": 7}, zorder=2)
    if text:
        # on the longest leg
        legs = [(math.dist(a, b), a, b) for a, b in zip(pts, pts[1:])]
        _, a, b = max(legs)
        mx, my = a[0] + (b[0] - a[0]) * at, a[1] + (b[1] - a[1]) * at
        vert = abs(b[0] - a[0]) < abs(b[1] - a[1])
        ax.text(mx + (0.08 * side if vert else 0), my + (0 if vert else 0.08 * side), text, fontsize=fs, color=colour,
                ha="left" if vert else "center", va="center" if vert else ("bottom" if side > 0 else "top"),
                rotation=0, zorder=4)


def _table(ax, x, y, cols: list[tuple[str, float]], rows: list[list[str]], fs=5.8, row_h=0.19, title: str | None = None,
           bold_rows: set | None = None) -> float:
    """A schedule: `cols` (heading, width in.), rows of cells. Returns the y under it."""
    if title:
        ax.text(x, y, title, fontsize=8, weight="bold", va="bottom")
        y -= 0.08
    xs = [x]
    for _, w in cols:
        xs.append(xs[-1] + w)
    ax.plot([xs[0], xs[-1]], [y, y], color="black", lw=0.8)
    yy = y - 0.05
    for (head, _), cx in zip(cols, xs):
        ax.text(cx + 0.04, yy, head, fontsize=fs, weight="bold", va="top")
    nl = max(len(h.split("\n")) for h, _ in cols)
    yy -= nl * fs / PT * 1.3 + 0.04
    ax.plot([xs[0], xs[-1]], [yy, yy], color="black", lw=0.5)
    yy -= 0.04
    for i, row in enumerate(rows):
        for cell, cx in zip(row, xs):
            ax.text(cx + 0.04, yy, cell, fontsize=fs, va="top", weight="bold" if bold_rows and i in bold_rows else "normal")
        yy -= row_h
    ax.plot([xs[0], xs[-1]], [yy + 0.02, yy + 0.02], color="black", lw=0.8)
    return yy - 0.1


def _f(c: float) -> float:
    return c * 9 / 5 + 32


def lengths_rows(rb: list[dict], layers: tuple[str, ...]) -> list[list[str]]:
    """Pipe, duct, conduit and cable by system, material and size, from the file read back (as the
    lengths schedule)."""
    from .servicesifc import SYSTEMS

    agg: dict[tuple, list] = {}
    for r in rb:
        if not drawn_as_run(r) or r["cls"].endswith("Fitting") or r["props"].get("Layer") not in layers:
            continue
        pr = r["props"]
        k = (SYSTEMS[pr["System"]][1], pr["Material"], str(pr["Size"]))
        a = agg.setdefault(k, [0.0, 0])
        a[0] += float(np.linalg.norm(np.diff(np.asarray(r["sweep"], float), axis=0), axis=1).sum())
        a[1] += 1
    from .servicesifc import size_in
    rows = []
    for (s, m, z), (mm, n) in sorted(agg.items(), key=lambda kv: (kv[0][0], kv[0][1], size_in(kv[0][2]) or 0.0)):
        rows.append([s, m.split(",")[0], z, f"{mm / FT:,.0f}", str(n)])
    return rows


def plumbing_diagram(ax, s7: dict, p: dict, rb: list[dict]) -> None:
    """P-601: the domestic water service and the hot-water plant, from step 4's design on the routes."""
    title_block(ax, "P-601", "WATER SERVICE AND HOT-WATER PLANT: DIAGRAM AND SCHEDULES")
    w = s7["water"]
    cold, hot = w["paths"]["cold"], w["paths"]["hot"]
    pl = "systems.plumbing."
    ax.text(1.4, SH - 1.2, "DOMESTIC WATER SERVICE", fontsize=11, weight="bold", va="top")
    y = SH - 3.0
    up = w["upstream"]
    boxes = [
        ("STREET MAIN", f"{p[pl + 'street_psi']:.0f} psi: a placeholder\nuntil the hydrant test (NFPA 291)"),
        ("TAP AND SERVICE", f"{p[pl + 'tap_in']:g} in. tap\n{up['the tap in the main (Table E103.3(4))']:.1f} psi at the peak"),
        ("WATER METER", f"the authority's\n{up['the main meter']:.1f} psi at the peak"),
        ("DOUBLE CHECK VALVE\nASSEMBLY, 2 IN.", f"{up['the double check valve assembly']:.1f} psi at the peak\n(the authority may ask an RPZ:\n"
         f"about {up['the double check valve assembly'] * (p[pl + 'rpz_psi_40'] / p[pl + 'dcva_psi_40'] - 1):.1f} psi more)"),
        ("PRESSURE-REDUCING\nVALVE", f"set {p[pl + 'max_static_psi']:g} psi static,\nfor quiet"),
        (f"COLD MAIN {cold['sizes']['main']:g} IN.", f"PEX-a under the slab\nto four {cold['sizes']['riser']:g} in. risers,\n{cold['sizes']['branch']:g} in. to each flat"),
    ]
    x = 1.4
    for i, (head, body) in enumerate(boxes):
        _box(ax, x, y, 3.3, 1.25, head + "\n" + body, fs=6)
        if i:
            _pipe(ax, [(x - 0.6, y + 0.62), (x, y + 0.62)], colour=TAGS["CW"][1])
        x += 3.9
    ax.text(1.4, y - 0.35, (f"The street must give {w['street_need_psi']:.1f} psi at the peak for the hot path: its needs plus the meter, the tap, "
                            f"the backflow assembly and the main's depth ({up['up from the main']:.1f} psi). Under it, the building needs a booster."),
            fontsize=6.5, va="top")
    ax.text(1.4, y - 0.6, (f"Pressure to spare at the worst shower on the routed pipe: cold {cold['spare_psi']:.1f} psi ({cold['flat']}), "
                           f"hot {hot['spare_psi']:.1f} psi ({hot['flat']}); 7c's designs on the routes (IPC Appendix E as a method, PEX bent through "
                           "its turns)."), fontsize=6.5, va="top")

    ax.text(1.4, SH - 6.0, "THE HOT-WATER PLANT (THE ANNEX'S MECHANICAL ROOM)", fontsize=11, weight="bold", va="top")
    h, pr, tm, lp, rc = w["heater"], w["primary"], w["tm"], w["loop"], w["recirc"]
    hw, rt, ct = "systems.hot_water.", "systems.routing.", "systems.controls."
    t_store, t_out, t_back = p[hw + "storage_f"], p[hw + "distribution_f"], p[hw + "return_min_f"]
    from .params import load_params
    from .plumbing import SWING_DEADBAND_F, storage_held
    from .sequence import aquastat_at
    spread = load_params()[hw + "recirc_w_per_flat"]
    by = SH - 13.2
    dc = _box(ax, 1.4, by + 4.2, 3.4, 1.3, f"DATA CENTER'S LIQUID LOOP\nits return, {h['dc_in_f']:.0f} F ({(h['dc_in_f'] - 32) * 5 / 9:.0f} C)\n"
              f"{h['dc_per_circuit']:.2f} times the heater\ncircuit's flow", fs=6)
    hx = _box(ax, 6.2, by + 4.2, 3.4, 1.3, f"HX-1 PLATE EXCHANGER\npreheats the heater circuit\nto {h['preheat_f']:.1f} F: {h['preheat_kw']:.1f} kW\n"
              f"({h['preheat_share']:.0%} of the plant's heat)", fs=6)
    hp = _box(ax, 11.0, by + 4.2, 3.6, 1.3, f"HP-1 WATER-TO-WATER HEAT PUMP\nClimateMaster Tranquility SW036\n(basis of design): to {t_store:g} F,\n"
              f"{h['hp_kw']:.1f} kW of heat, COP {h['hp_cop']:g}", fs=6)
    bk = _box(ax, 16.0, by + 4.2, 3.8, 1.3, f"BK-1 BACKUP HEATER (ADD. 7)\nA. O. Smith DRE-52-12 (basis of\ndesign): {p[hw + 'backup_w'] / 1000:.1f} kW, "
              f"its own {p[hw + 'backup_gal']:g} gal;\nlocked out unless the DC's heat is gone", fs=6)
    st1 = _box(ax, 11.0, by + 1.0, 3.6, 1.8, f"ST-1A + ST-1B STORAGE (ADD. 7)\n{p[rt + 'tank_count']:g} x {p[rt + 'tank_gal']:g} gal in series, "
               f"{storage_held(p):g} gal\nat {t_store:g} F (Lochinvar HP150G,\nbasis of design); Ecosizer asks {pr['storage_gal']:.0f}\n"
               f"{pr['capacity_kbtuh']:.1f} kBtu/h over {p[hw + 'run_hr']:g} h", fs=6)
    st2 = _box(ax, 16.0, by + 1.0, 3.3, 1.8, f"ST-2 SWING TANK\n{tm['volume_gal']:.0f} gal, {p['systems.house.swing_element_va'] / 1000:.1f} kW element\n"
               f"(Bradford White RE340S6,\nbasis of design; Addendum 7)\non at {t_out:g} F, off at {t_out + SWING_DEADBAND_F:g} F", fs=6)
    mv = _box(ax, 20.7, by + 1.2, 3.3, 1.6, f"MV-1 MIXING VALVE\nASSE 1017 master valve\n{t_out:g} F out", fs=6)
    hm = _box(ax, 25.4, by + 1.2, 3.3, 1.6, f"HOT MAIN {hot['sizes']['main']:g} IN.\nto four {hot['sizes']['riser']:g} in. risers,\n"
              f"{hot['sizes']['branch']:g} in. to each flat's loop", fs=6)
    rp = _box(ax, 20.7, by - 1.9, 3.8, 1.5, f"P-3 RECIRCULATION PUMP\nGrundfos ALPHA2 15-55SF\n{lp['gpm']:.2f} gpm at {rc['ft']:.1f} ft; TS-5 at ST-2:\n"
              f"on under {t_back:g} F, off at {p[ct + 'recirc_stop_f']:g} F (C404.6.1)", fs=6)
    # The data center's water: to HX-1, then the heat pump's source, then back.
    _pipe(ax, [(dc[0] + dc[2], dc[1] + 0.95), (hx[0], hx[1] + 0.95)], colour="#6a1b9a", text="DC water")
    _pipe(ax, [(hx[0] + hx[2], hx[1] + 0.95), (hp[0], hp[1] + 0.95)], colour="#6a1b9a", text="source, throttled")
    _pipe(ax, [(hp[0] + hp[2] * 0.5, hp[1] + hp[3]), (hp[0] + hp[2] * 0.5, hp[1] + hp[3] + 0.5), (dc[0] + dc[2] * 0.5, hp[1] + hp[3] + 0.5),
               (dc[0] + dc[2] * 0.5, dc[1] + dc[3])], colour="#6a1b9a", text=f"back to the data center at {h['source_f']:.0f} F", side=1)
    # The heater circuit (P-2): ST-1B's bottom through HX-1, HP-1 and BK-1 to ST-1A's top.
    _pipe(ax, [(st1[0], st1[1] + 0.3), (hx[0] + hx[2] * 0.5, st1[1] + 0.3), (hx[0] + hx[2] * 0.5, hx[1])], colour=TAGS["CW"][1],
          text="heater circuit (P-2), from ST-1B's bottom", side=-1)
    _pipe(ax, [(hx[0] + hx[2], hx[1] + 0.3), (hp[0], hp[1] + 0.3)], colour="#ef6c00", text=f"{h['preheat_f']:.1f} F", side=-1)
    _pipe(ax, [(hp[0] + hp[2], hp[1] + 0.3), (bk[0], bk[1] + 0.3)], colour=TAGS["HW"][1], text=f"{t_store:g} F", side=-1)
    _pipe(ax, [(bk[0] + bk[2] * 0.5, bk[1]), (bk[0] + bk[2] * 0.5, by + 3.4), (st1[0] + st1[2] * 0.5, by + 3.4), (st1[0] + st1[2] * 0.5, st1[1] + st1[3])],
          colour=TAGS["HW"][1], text=f"to ST-1A's top, {t_store:g} F", side=1)
    _pipe(ax, [(st1[0] + st1[2], st1[1] + 1.0), (st2[0], st2[1] + 1.0)], colour=TAGS["HW"][1], text=f"{t_store:g} F")
    _pipe(ax, [(st2[0] + st2[2], mv[1] + 1.0), (mv[0], mv[1] + 1.0)], colour=TAGS["HW"][1])
    _pipe(ax, [(mv[0] + mv[2], mv[1] + 1.0), (hm[0], hm[1] + 1.0)], colour=TAGS["HW"][1], text=f"{t_out:g} F")
    _pipe(ax, [(hm[0] + hm[2] * 0.5, hm[1]), (hm[0] + hm[2] * 0.5, rp[1] + 0.75), (rp[0] + rp[2], rp[1] + 0.75)], colour=TAGS["HWR"][1],
          ls=TAGS["HWR"][2], text=f"return {lp['return_main_in']:g} in. main, {lp['return_riser_in']:g} in. risers", side=1)
    _pipe(ax, [(rp[0], rp[1] + 0.75), (st2[0] + st2[2] * 0.5, rp[1] + 0.75), (st2[0] + st2[2] * 0.5, st2[1])], colour=TAGS["HWR"][1], ls=TAGS["HWR"][2])
    _pipe(ax, [(st1[0] + st1[2] * 0.3, by - 1.0), (st1[0] + st1[2] * 0.3, st1[1])], colour=TAGS["CW"][1], text="cold in, to ST-1B's bottom")
    _pipe(ax, [(mv[0] + mv[2] * 0.25, by - 0.2), (mv[0] + mv[2] * 0.25, mv[1])], colour=TAGS["CW"][1], text="cold to the mixing valve")
    notes = [
        f"Sized by Ecosizer (Ecotope's engine, read, not run): the design day's {w['day_gal']:.0f} gal at {t_out:g} F, a swing-tank plant "
        f"({pr['running_gal']:.0f} gal running; {pr['storage_gal']:.0f} gal of storage, against a floor of {pr['minimum_gal']:.0f}).",
        f"The storage is two tanks in series, for its stratification (Ecotope): cold in at ST-1B's bottom, hot out of ST-1A's top. P-2 runs "
        f"on TS-4, the aquastat {aquastat_at(p)}.",
        f"Stored and leaving the heater at {t_store:g} F (WHO: not less than 60 C; CDC: above 140 F); sent out at {t_out:g} F; back at "
        f"{t_back:g} F or more.",
        f"The loop loses {lp['w_per_flat']:.0f} W a flat on its routes, {lp['riser_mains_w_per_flat']:.0f} of it in the risers and mains "
        f"(Ecosizer's spread of measured buildings {spread.low:g}-{spread.high:g}). The swing tank's element gives {tm['kwh_day']:.1f} kWh "
        f"on the design day; the plant carries {tm['plant_share']:.0%} of the loop's loss.",
        f"Most of the hot water's heat comes from the data center: the preheat ({h['preheat_share']:.0%} of the plant's), and what the "
        "heat pump draws from its water. When it's gone, BK-1 heats the storage instead, never with HP-1 (a wired interlock).",
        "Not in the model: the plant's wall-hung assemblies (the exchanger, the pumps, the mixing valve, the backflow assembly, the "
        "pressure-reducing valve). Their places in the mechanical room are for the plumber to propose.",
        "The control sequence: specification section 23 09 93 (M-602). The tests and inspections: 01 45 00 (G-002).",
    ]
    yy = by - 2.6
    ax.text(1.4, yy, "NOTES", fontsize=8, weight="bold", va="top")
    yy -= 0.3
    for i, n in enumerate(notes, 1):
        ax.text(1.4, yy, f"{i}. {n}", fontsize=6.3, va="top")
        yy -= 0.24
    flat_loop_inset(ax, 1.4, yy - 0.3, s7, p)
    # The plumbing's pipe by system and size, from the file.
    rows = lengths_rows(rb, ("plumbing",))
    _table(ax, RIGHT - 9.6, SH - 6.0, [("SYSTEM", 2.4), ("MATERIAL", 3.9), ("SIZE IN.", 0.8), ("FT", 0.8), ("PIECES", 0.7)], rows,
           title="PLUMBING PIPE BY SYSTEM AND SIZE (FROM THE MODEL)")
    fx = Counter(r["props"].get("Kind") for r in rb if r["key"].startswith("fixture/"))
    frow = [[k, str(n)] for k, n in sorted(fx.items())]
    _table(ax, RIGHT - 9.6, 6.4, [("FIXTURE", 2.4), ("COUNT", 0.8)], frow, title="FIXTURES (FROM THE MODEL; NONE CHOSEN)")
    ax.text(1.4, 1.2, f"Figures: 7c's designs on the routes (routed.summary, on the routes {SHEETS_REV}'s services model was built from); the tables from the services model.",
            fontsize=6, va="top", color="#616161")


def flat_loop_inset(ax, x0: float, top: float, s7: dict, p: dict) -> None:
    """P-601's inset (Addendum 7): one flat's own hot-water loop, as every flat's runs (IECC C404.5):
    from its riser along its hot branch past its fixtures, each on its own pipe at its own size, to
    the lavatory, where the thermostatic balancing valve in the vanity starts its return; and each
    flat's loop as routed."""
    from .plumbing import LOOP_END

    w = s7["water"]
    lp, rc, c4 = w["loop"], w["recirc"], w["c404"]
    hw = "systems.hot_water."
    ax.text(x0, top, "EACH FLAT'S OWN LOOP (ADDENDUM 7; IECC C404.4-C404.6)", fontsize=8, weight="bold", va="top")
    red = TAGS["HW"][1]
    y_hot, y_ret = top - 0.8, top - 3.0
    xr, xrr, x_end = x0 + 0.3, x0 + 0.75, x0 + 8.6
    ax.plot([xr, xr], [y_ret - 0.5, y_hot + 0.35], color=red, lw=2.0)
    ax.plot([xrr, xrr], [y_ret - 0.5, y_hot + 0.35], color=red, lw=1.6, ls=TAGS["HWR"][2])
    ax.text(xr - 0.05, y_ret - 0.55, f"hot riser\n{w['paths']['hot']['sizes']['riser']:g} in.", fontsize=5.5, ha="right", va="top", color=red)
    ax.text(xrr + 0.05, y_ret - 0.55, f"return riser\n{lp['return_riser_in']:g} in.", fontsize=5.5, ha="left", va="top", color=red)
    _pipe(ax, [(xr, y_hot), (x_end, y_hot)], colour=red, text=f"the flat's hot branch, {lp['flat_branch_in']:g} in., in its joists' space and "
          "plumbing wall", side=1, at=0.42)
    own = c4["own_in"]
    fixtures = [k for k in ("tub", "sink", "dishwasher", "washer") if k in own]
    for i, k in enumerate(fixtures):
        fx = x0 + 1.7 + i * 1.65
        ax.plot([fx, fx], [y_hot, y_hot - 0.95], color=red, lw=1.0)
        _box(ax, fx - 0.55, y_hot - 1.4, 1.1, 0.45, f"{SHORT.get(k, k.upper())}\n{own[k]:g} in.", fs=5.6)
    lav_x = x_end
    ax.plot([lav_x, lav_x], [y_hot, y_hot - 0.95], color=red, lw=1.0)
    _box(ax, lav_x - 0.55, y_hot - 1.4, 1.1, 0.45, f"LAV\n{own.get(LOOP_END, 0.5):g} in.", fs=5.6)
    # The TBV in the vanity, then the return back to its riser.
    ty = y_hot - 1.9
    ax.plot([lav_x, lav_x], [y_hot - 1.4, ty + 0.12], color=red, lw=1.0, ls=TAGS["HWR"][2])
    ax.fill([lav_x - 0.12, lav_x + 0.12, lav_x - 0.12, lav_x + 0.12], [ty + 0.12, ty - 0.12, ty - 0.12, ty + 0.12], color="white",
            edgecolor="black", lw=0.8, zorder=4)
    ax.text(lav_x + 0.2, ty, f"TBV: Caleffi ThermoSetter 116, 1/2 in. (basis of design), set {p[hw + 'tbv_set_f']:g} F;\nin the vanity, "
            "reached through its doors (C404.6)", fontsize=5.6, va="center", ha="left")
    ax.plot([lav_x, lav_x], [ty - 0.12, y_ret], color=red, lw=1.0, ls=TAGS["HWR"][2])
    _pipe(ax, [(lav_x, y_ret), (xrr, y_ret)], colour=red, ls=TAGS["HWR"][2],
          text=f"its return, {lp['flat_return_in']:g} in.: up the wall beside the lavatory, back through the joists' space", side=1, at=0.5)
    worst = c4["worst"]
    lines = [
        f"Every hot fixture within {c4['limit_oz']:g} fl oz (half a gallon) of the loop (C404.5.2): the worst {worst['oz']:.0f}, "
        f"{worst['flat']}'s {worst['fixture']}. Each fixture's own pipe sized for it alone (Appendix E).",
        f"The flats' hot pipe and their returns insulated {p['systems.routing.branch_insulation_in']:g} in. (C404.4, Table C403.12.3), "
        "stopped at each plate and joist; holes bored for the bare pipe.",
        f"Each TBV passes {rc['flat_gpm']:.2f} gpm at the design's loss, {rc['tbv_psi']:.2f} psi across it (Caleffi's Cv "
        f"{p[hw + 'tbv_cv_design']:g}); {lp['gpm']:.2f} gpm in all.",
    ]
    rows = []
    for n in sorted(lp["flats"], key=lambda n: (int(n[0]), n)):
        fl = lp["flats"][n]
        oz = c4["by_flat"].get(n, {})
        rows.append([n, f"{fl['hot_ft']:.0f}", f"{fl['return_ft']:.0f}", f"{fl['loss_btuh'] / 3.412142:.0f}", f"{max(oz.values()):.0f}" if oz else "-"])
    yy = _table(ax, x0 + 12.6, top, [("FLAT", 1.4), ("HOT FT", 0.8), ("RETURN FT", 0.9), ("LOSS W", 0.8), ("WORST FL OZ", 1.0)], rows,
                title="EACH FLAT'S LOOP, AS ROUTED", fs=5.6, row_h=0.18)
    for ln in lines:
        parts = _wrap(ln, _chars(9.4, 5.9))
        ax.text(x0 + 12.6, yy, "\n".join(parts), fontsize=5.9, va="top", linespacing=1.2)
        yy -= len(parts) * 5.9 / PT * 1.45 + 0.06


def hvac_diagram(ax, s7: dict, p: dict, rb: list[dict]) -> None:
    """M-601: the building loop, the flats' equipment and their air."""
    title_block(ax, "M-601", "HEATING LOOP, EQUIPMENT AND AIR: DIAGRAM AND SCHEDULES")
    L = s7["loop"]
    ax.text(1.4, SH - 1.2, "THE BUILDING LOOP (RADIANT FLOORS)", fontsize=11, weight="bold", va="top")
    y = SH - 4.0
    dc = _box(ax, 1.4, y, 3.4, 1.4, f"DATA CENTER'S LIQUID LOOP\nits return, {L['primary_in_c']:.0f} C ({_f(L['primary_in_c']):.0f} F)\n"
              f"{L['primary_gpm']:.2f} gpm, back at {L['primary_out_c']:.1f} C", fs=6)
    hx = _box(ax, 6.2, y, 3.4, 1.4, f"HX-2 PLATE EXCHANGER\n{L['w'] / 1000:.1f} kW at design\n(an approach of {p['systems.substation.approach_k']:g} K,\n"
              "judgement until selected)", fs=6)
    pu = _box(ax, 11.0, y, 3.4, 1.4, f"P-1 CIRCULATOR\nGrundfos ALPHA2 15-55F\n{L['gpm']:.2f} gpm at {L['pump_ft']:.1f} ft\n(worst path: {L['pump_path']})\n"
              f"its curve III: {L['pump_curve_ft']:.1f} ft (Addendum 7)", fs=6)
    hd = _box(ax, 15.8, y, 3.4, 1.4, f"HEADER {L['header_in']:g} IN.\n{L['supply_c']:.1f} C out, {L['return_c']:.1f} C back\n"
              "pre-insulated PEX-a mains\nunder the slab", fs=6)
    _pipe(ax, [(dc[0] + dc[2], y + 0.9), (hx[0], y + 0.9)], colour="#6a1b9a", text="DC water")
    _pipe(ax, [(hx[0], y + 0.4), (dc[0] + dc[2], y + 0.4)], colour="#6a1b9a", ls=(0, (4, 2)))
    _pipe(ax, [(hx[0] + hx[2], y + 0.9), (pu[0], y + 0.9)], colour=TAGS["HS"][1], text=f"{L['supply_c']:.1f} C")
    _pipe(ax, [(pu[0] + pu[2], y + 0.9), (hd[0], y + 0.9)], colour=TAGS["HS"][1])
    _pipe(ax, [(hd[0], y + 0.4), (hx[0] + hx[2], y + 0.4)], colour=TAGS["HR"][1], ls=TAGS["HR"][2], text=f"{L['return_c']:.1f} C back", side=-1)
    rx = 21.0
    for i, (col, r) in enumerate(sorted(L["risers"].items())):
        yy = y + 1.6 - i * 0.95
        _box(ax, rx, yy - 0.35, 5.6, 0.75, f"RISER PAIR {col.upper()}: {r['pipe_in']:g} IN.\n{r['gpm']:.2f} gpm to flats "
             f"{', '.join(r['flats'])}; {r['main_ft']:.0f} ft of main, {r['rise_ft']:.0f} ft up", fs=5.6)
        _pipe(ax, [(hd[0] + hd[2], y + 0.7), (hd[0] + hd[2] + 0.8, y + 0.7), (hd[0] + hd[2] + 0.8, yy), (rx, yy)], colour=TAGS["HS"][1], arrow=True)
    ax.text(rx, y - 2.3, f"AT EACH FLAT: a heat meter (Kamstrup MULTICAL 403, qp {p['systems.heat_meter.qp_m3h']:g} m3/h), then its "
            "manifold (MF) and its loops.", fontsize=6.3, va="top")
    # The flats: heat, water, circuits, meters; the mini-split and the ERV.
    rows = []
    for n in sorted(L["flats"]):
        fl, m = L["flats"][n], L["meters"][n]
        c = s7["cooling"][n]
        d = s7["ducts"][n]
        rows.append([n, f"{fl['w']:,.0f}", f"{fl['supply_c']:.1f}", str(fl["circuits"]), f"{fl['gpm']:.2f}", f"{m['l_h']:.0f}",
                     f"{d['ms']['esp']:.2f}", f"{c['line_ft']:.0f}", f"{c['sensible_capacity_w'] / 1000:.2f} / {c['sensible_w'] / 1000:.2f}",
                     f"{fl['erv']['preheat_w']:.0f}", f"{max(d['erv_supply']['worst_inwc'], d['erv_exhaust']['worst_inwc']):.2f}"])
    yy = _table(ax, 1.4, SH - 8.6,
                [("FLAT", 1.4), ("HEAT\nW", 0.7), ("WATER\nC", 0.7), ("LOOPS", 0.6), ("GPM", 0.6), ("METER\nL/H", 0.7),
                 ("MINI-SPLIT\nSET IN. W.C.", 1.2), ("LINE SET\nFT", 0.8), ("SENSIBLE KW\nUNIT / LOAD", 1.3), ("ERV PRE-\nHEAT W", 0.8),
                 ("ERV WORST\nIN. W.C.", 0.9)], rows, title="THE FLATS: HEAT, COOLING AND VENTILATION (7c, ON THE ROUTES)")
    # The air at each terminal.
    rooms = ["living", "bed-1", "bed-2", "study"]
    arow = []
    for n in sorted(s7["ducts"]):
        d = s7["ducts"][n]
        cells = [n]
        for rm in rooms:
            pth = d["ms"]["paths"].get(f"{n}/{rm}")
            cells.append(f"{pth['cfm']:.0f} / {pth['in']:g}" if pth else "-")
        for rm in ("bath", "kitchen"):
            pth = d["erv_exhaust"]["paths"].get(f"{n}/{rm}")
            cells.append(f"{pth['cfm']:.0f} / {pth['in']:g}" if pth else "-")
        arow.append(cells)
    _table(ax, 1.4, yy - 0.3, [("FLAT", 1.4)] + [(f"SUPPLY {r.upper()}\nCFM / IN.", 1.25) for r in rooms]
           + [(f"EXHAUST {r.upper()}\nCFM / IN.", 1.35) for r in ("bath", "kitchen")], arow,
           title="AIR AT EACH TERMINAL (THE MINI-SPLIT'S SUPPLIES; THE ERV'S EXHAUSTS)")
    # Equipment from the model.
    eq = Counter((r["cls"], r["props"].get("Kind", "")) for r in rb if r["key"].startswith("eq/") and r["props"].get("Layer") == "hvac")
    erow = [[k.split(" (")[0], k[k.find("(") + 1:-1] if "(" in k else "", str(n)] for (_, k), n in sorted(eq.items(), key=lambda kv: kv[0][1])]
    erow.append(["ERV preheater, electric in-line duct heater", f"Ouellet ODHR0501002, {p['systems.electrical.preheater_va']:,.0f} W "
                 f"{p['systems.electrical.preheater_v']:.0f} V (step 3), in the outdoor-air duct", str(len(s7["ducts"]))])
    _table(ax, 14.6, SH - 8.6, [("EQUIPMENT", 3.6), ("BASIS OF DESIGN", 6.4), ("COUNT", 0.6)], erow,
           title="HVAC EQUIPMENT (FROM THE MODEL; BASIS OF DESIGN, NOT CHOSEN)")
    rows = lengths_rows(rb, ("hvac",))
    _table(ax, 14.6, SH - 12.4, [("SYSTEM", 2.9), ("MATERIAL", 4.2), ("SIZE IN.", 1.4), ("FT", 0.8), ("PIECES", 0.7)], rows,
           title="HVAC PIPE AND DUCT BY SYSTEM AND SIZE (FROM THE MODEL)", fs=5.4, row_h=0.17)
    ax.text(1.4, 1.2, f"Figures: 7c's designs on the routes (routed.summary, on the routes {SHEETS_REV}'s services model was built from); the equipment and lengths from the "
            "services model.", fontsize=6, va="top", color="#616161")


def one_line(ax, s7: dict, p: dict, rb: list[dict]) -> None:
    """E-601: the service, the meter stack, the feeders and the house panel."""
    title_block(ax, "E-601", "ONE-LINE DIAGRAM AND FEEDER SCHEDULE")
    el = s7["electrical"]
    sv, fa = el["service"], el["faults"]
    ax.text(1.4, SH - 1.2, "ONE-LINE DIAGRAM", fontsize=11, weight="bold", va="top")
    x = 1.4
    y = SH - 3.2
    _box(ax, x, y, 3.2, 1.3, f"UTILITY TRANSFORMER\nFirstEnergy's, pad-mounted\n{p['systems.service.transformer_kva']:g} kVA: a placeholder,\nFirstEnergy sizes it\n"
             f"{fa['transformer_a'] / 1000:.1f} kA at its terminals", fs=6)
    _box(ax, x, y - 2.6, 3.2, 1.6, f"SERVICE AND MAIN\n208Y/120 V, 3 phase, 4 wire\n{sv['sets']} sets of {sv['size']} kcmil Cu a phase\n"
              f"({sv['ampacity']:.0f} A); main {sv['main_a']} A\n{sv['amps']:.0f} A calculated (NEC 220.84)", fs=6)
    _pipe(ax, [(x + 1.6, y), (x + 1.6, y - 1.0)], colour="black", lw=1.6, text="service lateral", side=1)
    _box(ax, x, y - 6.0, 3.2, 2.0, f"METER STACK\non the annex's outside wall\n({el['meter_wall']['wall']}), outdoors as\nFirstEnergy asks\n"
              f"12 tenant meters + house\n{fa['stack_a'] / 1000:.1f} kA at the stack\nGEC {sv['gec']} Cu", fs=6)
    _pipe(ax, [(x + 1.6, y - 2.6), (x + 1.6, y - 4.0)], colour="black", lw=1.6)
    # The feeders fan out to the flats' panels.
    fx = 6.4
    feeders = el["feeders"]
    cond = {}
    for r in rb:
        if r["props"].get("System") == "power" and r["props"].get("Conductors") and r["props"].get("Flat"):
            cond.setdefault(r["props"]["Flat"], (r["props"]["Conductors"], r["props"].get("Size", "")))
    names = sorted(feeders, key=lambda n: (int(n[0]), n))
    top = SH - 2.4
    step = 0.82
    for i, n in enumerate(names):
        f = feeders[n]
        yy = top - i * step
        _pipe(ax, [(x + 3.2, y - 5.0), (fx - 0.3, y - 5.0), (fx - 0.3, yy), (fx + 0.4, yy)], colour="#212121", lw=0.8, ls=(0, (8, 3)), arrow=False)
        c, trade = cond.get(n, ("", ""))
        ax.text(fx + 0.5, yy + 0.13, f"FEEDER {n.upper()}: {f['breaker_a']:.0f} A, {c}", fontsize=5.6, va="center")
        ax.text(fx + 0.5, yy - 0.1, f'in {trade}" PVC; {f["ft"]:.0f} ft routed; drop {max(f["drop"]["ll"], f["drop"]["an"], f["drop"]["bn"]):.2%}; '
                f"{fa['flats_a'][n] / 1000:.1f} kA at the panel", fontsize=5.3, va="center", color="#424242")
        _box(ax, fx + 6.9, yy - 0.28, 2.4, 0.56, f"LC {n.upper()}\nQO130L125PG, {el['panels'][n]['spaces']} spaces", fs=5.2)
    hp = el["service"]["house"]
    hb = _box(ax, x, 2.2, 3.2, 1.9, f"HOUSE PANEL\n{hp['breaker_a']:.0f} A from the house meter\n{hp['calculated_va']:,.0f} VA calculated\n"
              f"{hp['amps']:.1f} A; the heat pump\non {hp['dhw_breaker_a']:.0f} A (MOCP {hp['dhw_mocp_a']:.0f})", fs=6)
    _pipe(ax, [(x + 1.6, y - 6.0), (x + 1.6, hb[1] + hb[3])], colour="black", lw=1.0)
    rows = [[r["what"][:70], f"{r['va']:,.0f}", f"{r['calc_va']:,.0f}" if "calc_va" in r else "-"] for r in hp["rows"]]
    _table(ax, 17.6, SH - 2.2, [("HOUSE LOAD", 6.6), ("VA", 0.8), ("CALC. VA", 0.9)], rows, title="THE HOUSE PANEL'S LOADS (STEP 5)", fs=5.6)
    fl = sv["flats"]
    notes = [
        f"The service by NEC 220.84 (multifamily, optional): {fl['connected_va']:,.0f} VA connected in the flats at a factor of "
        f"{fl['factor']:.2f}, {fl['calculated_va']:,.0f} VA; with the house, {sv['total_va']:,.0f} VA, {sv['amps']:.0f} A at 208 V.",
        "Each tenant reaches the breaker on their own feeder outdoors at the meter stack (NEC 240.24(B)).",
        f"Feeders by NEC 310.16 at 75 C, held to {p['systems.wiring.vd_feeder_max']:.0%} drop on their routes; feeder and branch together "
        f"within {p['systems.wiring.vd_total_max']:.0%}: worst {max(el['total_drop'].values()):.2%}.",
        f"The flats share the phases in threes: {'; '.join(f'{k} {len(v)} flats' for k, v in sv['pairs'].items())}.",
        "Not in the model: the meter stack, the house panel and the electrical room's equipment. Fault currents from the "
        "transformer's assumed size and impedance until FirstEnergy gives them.",
        "No chargers at the walk-up: they are at the mobility hub (D14). Room for PV on the roof (step 5), not drawn.",
    ]
    yy = 9.6
    ax.text(17.6, yy, "NOTES", fontsize=8, weight="bold", va="top")
    yy -= 0.3
    for i, n in enumerate(notes, 1):
        parts = _wrap(n, 92)
        ax.text(17.6, yy, f"{i}.", fontsize=6, va="top")
        for p_ in parts:
            ax.text(17.8, yy, p_, fontsize=6, va="top")
            yy -= 0.19
        yy -= 0.05
    ax.text(1.4, 1.2, f"Figures: 7c's designs on the routes (routed.summary, on the routes {SHEETS_REV}'s services model was built from); the conductors and conduit from the "
            "services model.", fontsize=6, va="top", color="#616161")


def panel_schedules(ax, s7: dict, p: dict) -> None:
    """E-602: every flat's panel."""
    title_block(ax, "E-602", "PANEL SCHEDULES")
    el = s7["electrical"]
    names = sorted(el["panels"], key=lambda n: (int(n[0]), n))
    cols = [("CKT", 0.32), ("SERVES", 2.95), ("A", 0.35), ("P", 0.25), ("PROT.", 0.85), ("AWG", 0.4), ("VA", 0.55), ("FT", 0.35), ("VD", 0.45), ("LEG", 0.4)]
    width = sum(w for _, w in cols) + 0.25
    x0, y0 = 1.4, SH - 1.2
    per_row = int((RIGHT - 1.4) // width)
    heights = []
    for i, n in enumerate(names):
        pn = el["panels"][n]
        cx = x0 + (i % per_row) * width
        row = i // per_row
        if row >= len(heights):
            heights.append(y0 if not heights else heights[-1])
        cy = y0 if row == 0 else heights[row]
        rows = []
        for k, c in enumerate(pn["circuits"], 1):
            serves = c["what"].replace("(210.11(C)(1))", "").replace("(210.11(C)(2))", "").replace("(210.11(C)(3))", "").strip()
            rows.append([str(k), serves[:44], f"{c['breaker_a']:.0f}", str(c["poles"]), c["protection"] or "-", c["awg"], f"{c['va']:,.0f}",
                         f"{c['ft']:.0f}", f"{c['drop']:.1%}", c["leg"]])
        bottom = _table(ax, cx, cy, cols, rows, fs=5.4, row_h=0.2,
                        title=f"LC {n.upper()}: Square D QO130L125PG, 125 A main lugs, fed {el['feeders'][n]['breaker_a']:.0f} A")
        ax.text(cx, bottom, f"A {pn['a_va']:,.0f} VA, B {pn['b_va']:,.0f} VA ({pn['imbalance']:.1%} apart); {pn['poles']} of {pn['spaces']} spaces",
                fontsize=5.4, va="top")
        nxt = bottom - 0.55
        if len(heights) <= row + 1:
            heights.append(nxt)
        else:
            heights[row + 1] = min(heights[row + 1], nxt)
    ax.text(1.4, 1.2, "From 7c's designs on the routes: each circuit's length is its routed run to its farthest outlet; its drop at its design "
            "load (a receptacle circuit 1,500 VA at the farthest outlet). AFCI: NEC 210.12(A); GFCI: 210.8. The mini-split's GFCI breaker: "
            "a model made for inverter equipment (Schneider's QO HF-rated), a question for this round.", fontsize=6, va="top", color="#616161")


def fire_diagram(ax, s7: dict, p: dict, rb: list[dict]) -> None:
    """FP-601: the fire service and the hydraulic summary."""
    title_block(ax, "FP-601", "FIRE SERVICE, HYDRAULIC SUMMARY AND SPRINKLER SCHEDULE")
    fh = s7["fire"]
    sz = fh["sizes"]
    sp = "systems.sprinkler."
    ax.text(1.4, SH - 1.2, "THE FIRE SERVICE (SEPARATE, SUPERVISED)", fontsize=11, weight="bold", va="top")
    y = SH - 3.2
    items = [
        ("STREET MAIN", f"{p['systems.plumbing.street_psi']:.0f} psi: a placeholder\nheld to {fh['target_psi']:.0f} for its swing\n(IBC 903.3.5)"),
        ("FIRE SERVICE", f"{p[sp + 'underground_id_in']:g} in. underground\n{p[sp + 'underground_ft']:.0f} ft (step 6)"),
        ("SHUTOFF VALVE", "listed OS&Y gate valve,\nsupervised (tamper switch)\nAddendum 6, item 1"),
        (f"DOUBLE CHECK\nASSEMBLY {sz['backflow']} IN.", "Watts LF007: UL Classified\nwithout shutoff valves only"),
        ("SHUTOFF VALVE", "listed OS&Y gate valve,\nsupervised (tamper switch)\nAddendum 6, item 1"),
        ("WATERFLOW SWITCH", "and an exterior\nhorn-strobe (903.4.2)"),
        (f"MAIN {sz['main']} IN.", "CPVC under the slab\nto the stair"),
        (f"RISER {sz['riser']} IN.", "in the stair, at the back\nof each storey's hall"),
    ]
    x = 1.4
    for i, (head, body) in enumerate(items):
        _box(ax, x, y, 2.75, 1.25, head + "\n" + body, fs=5.8)
        if i:
            _pipe(ax, [(x - 0.45, y + 0.62), (x, y + 0.62)], colour=TAGS["SP"][1])
        x += 3.2
    ax.text(1.4, y - 0.3, (f"From the riser at each storey: each flat's feed {sz['feed']} in. through the stair's side wall at its door, its branch "
                           f"lines {sz['branch']} in.; the stair's own sprinklers on the riser. A fire department connection on the street side "
                           "(13R 6.11.1, IBC 912.2.1) with a check valve and an automatic drip. A monitoring panel (Potter PFC-6006) sends to a "
                           "supervising station (903.4.1)."), fontsize=6.3, va="top")
    w = fh["worst"]
    gate, bfly_ft = p[sp + "shutoff_valve_el_ft"], p[sp + "butterfly_valve_el_ft"]
    bfly = w["need_psi"] + w["valves_psi"] * (bfly_ft / gate - 1)  # a butterfly valve instead, at the same flow
    ax.text(1.4, y - 0.55, ("The system's control valves are the listed, supervised shutoff valves on each side of the backflow assembly "
                            f"(Addendum 6, item 1): Watts lists its {sz['backflow']} in. LF007 as UL Classified without its own shutoff "
                            f"valves only. The hydraulics count them (NFPA 13's chart: a {sz['backflow']} in. gate valve is {gate:g} ft of "
                            f"Schedule 40 steel pipe; a butterfly valve's {bfly_ft:g} ft would put the governing design at {bfly:.1f} psi, "
                            + ("over" if bfly > fh["target_psi"] else "within") + " what the street gives, so an equal loses no more than "
                            "a gate valve)."),
            fontsize=6.3, va="top")
    # The hydraulic summary.
    w = fh["worst"]
    ax.text(1.4, SH - 6.2, "HYDRAULIC SUMMARY (13R 7.1.1.3.1: EACH COMPARTMENT'S WORST FOUR; THE STAIR'S SIX)", fontsize=11, weight="bold", va="top")
    rows = [["at the riser assembly (the routed pipe, Hazen-Williams, C 150)", f"{w['p_assembly_psi']:.1f}"],
            ["the underground service", f"{w['underground_psi']:.2f}"],
            ["the backflow assembly", f"{w['backflow_psi']:.1f}"],
            ["its shutoff valves", f"{w['valves_psi']:.2f}"],
            ["up from the main", f"{w['elevation_psi']:.1f}"],
            ["needed at the street", f"{w['need_psi']:.1f}"],
            [f"the street, less its margin ({p[sp + 'margin_psi']:g} psi)", f"{fh['target_psi']:.1f}"]]
    yy = _table(ax, 1.4, SH - 7.0, [(f"THE MOST DEMANDING: {w['flat'].upper()} {w['comp'].upper()}, {len(w['design'])} SPRINKLERS, {w['q_gpm']:.0f} GPM", 6.4),
                                    ("PSI", 0.8)], rows, fs=6.2, row_h=0.21, bold_rows={5})
    cases = sorted(fh["cases"], key=lambda c: -c["need_psi"])
    crow = [[c["flat"], c["comp"], str(c["heads"]), f"{c['q_gpm']:.0f}", f"{c['p_assembly_psi']:.1f}", f"{c['need_psi']:.1f}"] for c in cases[:18]]
    _table(ax, 9.4, SH - 7.0, [("FLAT", 1.3), ("COMPARTMENT", 1.3), ("HEADS", 0.6), ("GPM", 0.6), ("AT ASSEMBLY\nPSI", 1.1), ("AT STREET\nPSI", 1.0)],
           crow, title=f"THE {len(crow)} MOST DEMANDING OF {len(cases)} DESIGNS", fs=5.8)
    ax.text(1.4, yy - 0.1, (f"Supply: {fh['water_gal']:,.0f} gal over {p[sp + 'duration_min']:g} min (13R 9.2.1). The street's pressure is step 4's "
                            "placeholder until the hydrant test (NFPA 291)."), fontsize=6.3, va="top")
    # The sprinklers from the model.
    hs = Counter((r["props"].get("Model", ""), str(r["props"].get("K", "")), r["props"].get("Coverage", "") or "-",
                  str(r["props"].get("Temperature", "") or "-")) for r in rb if r["key"].startswith("head/"))
    hrow = [[m, k, c, t, str(n)] for (m, k, c, t), n in sorted(hs.items())]
    _table(ax, 18.6, SH - 7.0, [("SPRINKLER", 5.0), ("K", 0.5), ("COVERAGE", 1.2), ("TEMP.", 0.8), ("COUNT", 0.6)], hrow,
           title="SPRINKLERS (FROM THE MODEL)", fs=5.8)
    rows = lengths_rows(rb, ("sprinklers",))
    _table(ax, 18.6, SH - 9.8, [("SYSTEM", 2.4), ("MATERIAL", 3.6), ("SIZE IN.", 0.8), ("FT", 0.7), ("PIECES", 0.7)], rows,
           title="SPRINKLER PIPE BY SIZE (FROM THE MODEL)", fs=5.8)
    ax.text(1.4, 1.2, f"Figures: 7c's designs on the routes (routed.summary, on the routes {SHEETS_REV}'s services model was built from); the sprinklers and lengths from the "
            "services model.", fontsize=6, va="top", color="#616161")


def _chars(width_in: float, fs: float) -> int:
    """About how many characters of a `fs`-point font fit across `width_in` inches."""
    return max(8, int(width_in * PT / (fs * 0.6)))


def _wtable(ax, x: float, y: float, cols: list[tuple[str, float]], rows: list[list[str]], fs: float = 5.6,
            groups: dict[int, str] | None = None) -> float:
    """A table whose cells wrap to their column's width; `groups` puts a heading row before a row
    index. Returns the y under it."""
    xs = [x]
    for _, wd in cols:
        xs.append(xs[-1] + wd)
    line = fs / PT * 1.3
    for (head, _), cx in zip(cols, xs):
        ax.text(cx + 0.04, y, head, fontsize=fs, va="top", weight="bold")
    y -= line * 1.2
    ax.plot([xs[0], xs[-1]], [y, y], color="black", lw=0.6)
    y -= 0.05
    for i, row in enumerate(rows):
        if groups and i in groups:
            y -= 0.04
            ax.text(xs[0] + 0.04, y, groups[i].upper(), fontsize=fs + 0.6, va="top", weight="bold")
            y -= line * 1.25
        wrapped = [_wrap(cell, _chars(wd - 0.1, fs)) for cell, (_, wd) in zip(row, cols)]
        for cell, cx in zip(wrapped, xs):
            ax.text(cx + 0.04, y, "\n".join(cell), fontsize=fs, va="top", linespacing=1.15)
        y -= max(len(c) for c in wrapped) * line + 0.06
        ax.plot([xs[0], xs[-1]], [y + 0.03, y + 0.03], color="#bdbdbd", lw=0.3)
    ax.plot([xs[0], xs[-1]], [y + 0.03, y + 0.03], color="black", lw=0.6)
    return y - 0.1


def tests_sheet(ax, s7: dict, p: dict) -> None:
    """G-002 (Addendum 7): the tests and inspections, specification section 01 45 00 as a schedule."""
    from . import acceptance

    title_block(ax, "G-002", "TESTS AND INSPECTIONS (SPECIFICATION 01 45 00)")
    ax.text(1.4, SH - 1.2, "TESTS AND INSPECTIONS", fontsize=14, weight="bold", va="top")
    ax.text(1.4, SH - 1.65, "Specification section 01 45 00 (Addendum 7) governs, with the codes' own words for each test it quotes. Each test is "
            "the code's own or the design's claim to be proved, its figures the design's. Pennsylvania's code official inspects as 34 Pa. Code "
            "403.45 asks.", fontsize=8.5, va="top")
    its = acceptance.items(p, s7)
    groups, rows = {}, []
    for it in its:
        if not rows or its[len(rows) - 1]["area"] != it["area"]:
            groups[len(rows)] = it["area"]
        rows.append([it["id"], it["what"], it["who"], it["when"], it["passes"], it["basis"]])
    _wtable(ax, 1.4, SH - 2.3, [("ID", 0.6), ("WHAT", 3.8), ("WHO", 3.4), ("WHEN", 3.4), ("PASSES WHEN", 12.0), ("BASIS", 4.6)], rows,
            fs=10, groups=groups)


def sequence_sheet(ax, s7: dict, p: dict) -> None:
    """M-602 (Addendum 7): the control sequence, specification section 23 09 93, with its interlocks
    and its points."""
    from . import sequence as sq

    title_block(ax, "M-602", "CONTROL SEQUENCE AND POINTS (SPECIFICATION 23 09 93)")
    ax.text(1.4, SH - 1.2, "SEQUENCE OF OPERATIONS", fontsize=14, weight="bold", va="top")
    ax.text(1.4, SH - 1.65, "Specification section 23 09 93 (Addendum 7) governs. Setpoints are the design's; the fallback's timers, the warm-weather "
            "shutdown, the mini-splits' offset and the loop's alarm are judgements, set at commissioning.", fontsize=8.5, va="top")
    seq = sq.sequence(p, s7)
    width, fs = 9.4, 10.5
    line = fs / PT * 1.3
    cols = [1.4, 1.4 + width + 0.5, 1.4 + 2 * (width + 0.5)]
    col, y = 0, SH - 2.2
    bottom = 1.6

    def need(paras: list[str]) -> float:
        return sum(len(_wrap(t, _chars(width - 0.25, fs))) * line + 0.05 for t in paras)

    blocks = []
    for i, s in enumerate(seq, 1):
        for m in s["modes"]:
            blocks.append((f"{i}. {s['system']}".upper() if m is s["modes"][0] else None, m["mode"], m["steps"]))
    heights = [(line * 1.5 if head else 0) + line * 1.3 + need(steps) + 0.08 for head, _, steps in blocks]
    half = sum(heights) / 2  # the sequence over the first two columns, about evenly
    used = 0.0
    for (head, mode, steps), h in zip(blocks, heights):
        if col == 0 and (used + h / 2 > half or y - h < bottom):
            col, y = 1, SH - 2.2
        elif y - h < bottom and col < 2:
            col, y = col + 1, SH - 2.2
        used += h
        x = cols[col]
        if head:
            ax.text(x, y, head, fontsize=fs + 1.2, weight="bold", va="top")
            y -= line * 1.5
        ax.text(x, y, mode + ".", fontsize=fs, weight="bold", va="top")
        y -= line * 1.3
        for t in steps:
            parts = _wrap(t, _chars(width - 0.25, fs))
            ax.text(x, y, "-", fontsize=fs, va="top")
            ax.text(x + 0.15, y, "\n".join(parts), fontsize=fs, va="top", linespacing=1.15)
            y -= len(parts) * line + 0.05
        y -= 0.08
    # The interlocks and the points, in the last column.
    if col < 2:
        col, y = 2, SH - 2.2
    x = cols[2]
    y -= 0.1
    ax.text(x, y, "INTERLOCKS, WIRED, NOT PROGRAMMED", fontsize=fs + 1.2, weight="bold", va="top")
    y -= line * 1.5
    for a, b in sq.INTERLOCKS:
        parts = _wrap(f"{a}: {b}", _chars(width - 0.25, fs))
        ax.text(x, y, "\n".join(parts), fontsize=fs, va="top", linespacing=1.15)
        y -= len(parts) * line + 0.08
    y -= 0.15
    ax.text(x, y, "CONTROL POINTS", fontsize=fs + 1.2, weight="bold", va="top")
    _wtable(ax, x, y - line * 1.6, [("TAG", 0.6), ("WHAT", 5.4), ("CHOSEN", 3.4)], [list(r) for r in sq.POINTS], fs=9.0)


# ---- The set ----

def sheet_list() -> list[tuple[str, str]]:
    out = [("G-001", "COVER, SHEET INDEX, NOTES AND LEGEND"), ("G-002", "TESTS AND INSPECTIONS (SPECIFICATION 01 45 00)")]
    for trade, prefix in (("P", "P"), ("M", "M"), ("E", "E"), ("FP", "FP")):
        for k in (1, 2, 3):
            out.append((f"{prefix}-10{k}", f"LEVEL {k} {TRADES[trade][1]} PLAN"))
        if trade == "M":
            out.append(("M-104", "ROOF PLAN, ALL TRADES"))
        if trade == "P":
            out += [("P-201", "PLUMBING WALLS IN ELEVATION, COLUMNS FRONT-LEFT AND BACK-LEFT"),
                    ("P-202", "PLUMBING WALLS IN ELEVATION, COLUMNS FRONT-RIGHT AND BACK-RIGHT"),
                    ("P-601", "WATER SERVICE AND HOT-WATER PLANT: DIAGRAM AND SCHEDULES")]
        if trade == "M":
            out += [("M-601", "HEATING LOOP, EQUIPMENT AND AIR: DIAGRAM AND SCHEDULES"),
                    ("M-602", "CONTROL SEQUENCE AND POINTS (SPECIFICATION 23 09 93)")]
        if trade == "E":
            out += [("E-601", "ONE-LINE DIAGRAM AND FEEDER SCHEDULE"), ("E-602", "PANEL SCHEDULES")]
        if trade == "FP":
            out.append(("FP-601", "FIRE SERVICE, HYDRAULIC SUMMARY AND SPRINKLER SCHEDULE"))
    order = {"G": 0, "P": 1, "M": 2, "E": 3, "FP": 4}
    return sorted(out, key=lambda s: (order[s[0].split("-")[0]], s[0]))


def cover(ax, sheets: list[tuple[str, str]]) -> None:
    title_block(ax, "G-001", "COVER, SHEET INDEX, NOTES AND LEGEND")
    ax.text(1.4, SH - 1.2, "12-FLAT WALK-UP: THE SERVICES", fontsize=22, weight="bold", va="top")
    ax.text(1.4, SH - 2.0, f"Plumbing, heating, cooling and air, power and sprinklers, drawn from {SHEETS_REV}'s services model for review by the "
            "trades: the installers' round.", fontsize=10, va="top")
    ax.text(1.4, SH - 2.4, "Made up, from the brownfield-compute study: not a real project, nothing is out to bid. Not for construction.",
            fontsize=10, va="top", color="#c00000")
    rows = [[n, t] for n, t in sheets]
    _table(ax, 1.4, SH - 3.3, [("SHEET", 0.9), ("TITLE", 7.2)], rows, title="SHEET INDEX", fs=7, row_h=0.26)
    general = [
        "Codes as Pennsylvania enforces them (34 Pa. Code 403.21, from 2026-01-01): the 2021 IBC, IPC, IMC and IECC; NFPA 70 (2020), "
        "13R (2019) and 72 (2019).",
        f"The bid set's documents govern: the services model (services-{SERVICES_REV}.ifc), its schedules (lengths, fittings, equipment, "
        f"fixtures, sprinklers, registers, switches, holes, plates, openings, firestop) and Addenda 1-{SHEETS_REV.split()[-1]}. These sheets "
        "are drawn from the model and add nothing to it.",
        "Each run is tagged with its system and nominal size in inches; a circuit with its name and wire.",
        "Each storey's plan shows its flats' own runs wherever they go in the floor and ceiling spaces (a floor's drains serve the "
        "storey above it, a ceiling's sprinkler pipe the one below), and the mains and risers by the storey they're in. Under the "
        "ground slab: dashed, on Level 1.",
        "PEX is bent on a bend support at its turns (Addendum 5, item 4a). Holes through studs, plates and joists are bored at the "
        "member's centre (item 4b). The feeders' conduit runs straight under the slab (item 4c). A 2 in. vent stack in each column's "
        "plumbing wall (item 4d). Each mini-split's static pressure set to its ducts, and a water-level switch at its drain (item 4e).",
        "Firestop every opening through a rated assembly by its condition in the firestop schedule (item 5): listed systems where they "
        "fit as tested, the maker's engineering judgments for the authority's approval for the rest.",
        "Each flat's hot water is a loop of its own (Addendum 7, item 1; IECC C404.5): from its riser along its hot branch past its "
        "fixtures to the lavatory, where a thermostatic balancing valve (TBV) in the vanity starts its return to the return riser. The "
        "flats' hot pipe and returns are insulated 1 in. (C404.4), stopped at each plate and joist (P-601).",
        "The plant's storage is two tanks in series, and a backup heater (BK-1) is on its heater circuit (Addendum 7, items 2 and 3; "
        "P-601). The control sequence is specification section 23 09 93 (M-602); the tests and inspections, 01 45 00 (G-002).",
        "Basis of design: every make and model named is a basis of design, not a choice; equals by the bidder, with their data.",
    ]
    missing = [
        "the mechanical and electrical rooms' wall-hung equipment: the exchangers, the pumps, the mixing valve, the backflow assemblies "
        "and the riser assembly, the pressure-reducing valve, the meter stack, the house panel (the diagrams P-601, M-601, E-601 and "
        "FP-601 show them);",
        "the outlets, switches and luminaires at the branch circuits' ends (each circuit drawn to its farthest outlet);",
        "the smoke alarms (36, three a flat: step 6), the fire alarm's devices and the telecom;",
        "the PV on the roof, the radiant loops in the floors' topping, and the ports connecting one element to the next.",
    ]
    x = 11.6
    y = SH - 3.3
    ax.text(x, y, "GENERAL NOTES", fontsize=8, weight="bold", va="bottom")
    y -= 0.15
    for i, n in enumerate(general, 1):
        ax.text(x, y, f"{i}.", fontsize=6.5, va="top")
        for part in _wrap(n, 120):
            ax.text(x + 0.22, y, part, fontsize=6.5, va="top")
            y -= 0.2
        y -= 0.07
    y -= 0.25
    ax.text(x, y, "NOT IN THE MODEL, SO NOT DRAWN", fontsize=8, weight="bold", va="bottom")
    y -= 0.15
    for n in missing:
        for k, part in enumerate(_wrap(n, 120)):
            ax.text(x + (0 if k == 0 else 0.22), y, ("- " if k == 0 else "") + part, fontsize=6.5, va="top")
            y -= 0.2
        y -= 0.05
    y -= 0.3
    used = Counter({t: 1 for t in TAGS})
    _legend(ax, x, y, used, "P")


def draw_sheet(ax, number: str, ctx: dict, drawn: set) -> Labels | None:
    """One sheet; returns its labels where it places tags (a plan or an elevation)."""
    bld, rb, s7, p = ctx["bld"], ctx["rb"], ctx["s7"], ctx["p"]
    pre, num = number.split("-")
    if number == "G-001":
        cover(ax, sheet_list())
    elif number == "G-002":
        tests_sheet(ax, s7, p)
    elif number == "M-602":
        sequence_sheet(ax, s7, p)
    elif number in ("P-201", "P-202"):
        cols = ("front-left", "back-left") if number == "P-201" else ("front-right", "back-right")
        return wall_sheet(ax, number, cols, bld, rb, ctx["members"], drawn)
    elif number == "P-601":
        plumbing_diagram(ax, s7, p, rb)
    elif number == "M-601":
        hvac_diagram(ax, s7, p, rb)
    elif number == "E-601":
        one_line(ax, s7, p, rb)
    elif number == "E-602":
        panel_schedules(ax, s7, p)
    elif number == "FP-601":
        fire_diagram(ax, s7, p, rb)
    elif num.startswith("10"):
        level = "roof" if number == "M-104" else int(num[-1])
        return plan_sheet(ax, number, bld, rb, pre, level, s7, drawn)
    else:
        raise ValueError(f"no sheet {number}")
    return None


def context(apt: dict, p: dict, routes=None, s7: dict | None = None, src: Path = BIDSET, services_path: Path | None = None) -> dict:
    """The building and the frame as published (`src`), the services model as `SERVICES_REV` issues
    it (built by `brownfield routes --ifc`, before it is published: `services_path`), and 7c's
    designs on the routes it was built from."""
    from . import servicesifc

    from . import routed

    routes = routes or routed.load(apt, p)
    if routes is None or not routes.fresh:
        raise SystemExit("the routes aren't fresh for the latest model: `brownfield routes` first")
    s7 = s7 or routed.summary(apt, p, routes)
    if "incomplete" in s7:
        raise SystemExit(f"7c's designs didn't run: {s7['incomplete']}")
    if servicesifc.ISSUE != SERVICES_REV:
        raise SystemExit(f"the services model is {servicesifc.ISSUE}'s; the sheets are drawn from {SERVICES_REV}'s")
    services_path = services_path or servicesifc.OUT / f"services-{SERVICES_REV}.ifc"
    return {"bld": building(src / f"apartment-{REV}.ifc"), "rb": services(services_path), "services_path": services_path,
            "members": framing(src / f"framing-{REV}.ifc"), "s7": s7, "p": p, "routes": routes, "src": src}


def write(ctx: dict, path: Path, numbers: list[str] | None = None) -> dict:
    """The sheets as one PDF (TrueType text, no creation date, so it repeats). Returns what each
    sheet drew."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    sheets = [n for n, _ in sheet_list() if numbers is None or n in numbers]
    drawn: set = set()
    per: dict[str, int] = {}
    tags: dict[str, tuple[int, int]] = {}
    path.parent.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context({"pdf.fonttype": 42}), PdfPages(
            path, metadata={"Title": f"walk-up services sheets ({SHEETS_REV})", "Creator": "brownfield-compute pass 3g steps 8a and 9d",
                            "CreationDate": None}) as pdf:
        for n in sheets:
            fig, ax = _figure()
            try:
                before = len(drawn)
                lab = draw_sheet(ax, n, ctx, drawn)
                per[n] = len(drawn) - before
                if lab is not None:
                    tags[n] = (lab.placed, lab.skipped)
                pdf.savefig(fig)
            finally:
                plt.close(fig)
    return {"sheets": sheets, "drawn": drawn, "new_per_sheet": per, "tags": tags}


def sheet_png(ctx: dict, number: str, path: Path, dpi: int = 60, crop: tuple | None = None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = _figure()
    try:
        draw_sheet(ax, number, ctx, set())
        if crop:
            x0, x1, y0, y1 = crop
            ax.set_xlim(x0, x1)
            ax.set_ylim(y0, y1)
            fig.set_size_inches(x1 - x0, y1 - y0)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, facecolor="white")
    finally:
        plt.close(fig)


def checks(ctx: dict, res: dict, path: Path) -> list[tuple[str, bool, str]]:
    """What the sheets must hold: every element of the model drawn somewhere but its fittings (the
    schedules count those), drawn from the model the routes built, and the PDF's text as text."""
    import ifcopenshell
    import pypdf

    rb = ctx["rb"]
    want = {r["key"] for r in rb if not r["cls"].endswith("Fitting") or r["key"].startswith("pinned/") or r["obj"] == "manifold"}
    missing = sorted(want - res["drawn"])
    f = ifcopenshell.open(str(ctx["services_path"]))
    desc = f.by_type("IfcBuilding")[0].Description or ""
    sha = ctx["routes"].rt["requests_sha"]
    text = pypdf.PdfReader(str(path))
    found = [n for n in res["sheets"] if any(n in (pg.extract_text() or "") for pg in text.pages)]
    return [
        ("every element of the services model on a sheet (its fittings in the schedules)", not missing,
         f"{len(want) - len(missing)} of {len(want)}" + (f"; not drawn: {missing[:6]}" if missing else "")),
        ("the services model was built from the routes these sheets' figures come from", sha in desc, f"requests {sha}"),
        ("each sheet's number reads as text in the PDF (what a bidder's tools search)", len(found) == len(res["sheets"]),
         f"{len(found)} of {len(res['sheets'])} sheets"),
    ]


def run(apt: dict, p: dict, out: Path = OUT, routes=None, s7: dict | None = None) -> dict:
    ctx = context(apt, p, routes=routes, s7=s7)
    path = out / PDF_NAME
    res = write(ctx, path)
    ch = checks(ctx, res, path)
    for n in res["sheets"]:
        sheet_png(ctx, n, out / "png" / f"{n}.png", dpi=40)
    return {"checks": ch, "path": path, "sheets": res["sheets"], "drawn": len(res["drawn"]), "tags": res["tags"], "ctx": ctx}


def report(s: dict) -> str:
    from .systems import report as checks_report

    placed = sum(a for a, _ in s["tags"].values())
    skipped = sum(b for _, b in s["tags"].values())
    lines = ["Pass 3g step 8a: the services as sheets, for the installers' round", "", checks_report(s["checks"]), "",
             f"{len(s['sheets'])} sheets in {s['path'].name}: " + ", ".join(s["sheets"]),
             f"Tags on the plans and elevations: {placed:,} placed, {skipped:,} left off where they would overlap another "
             "(each run's size is in the schedules and the model): " + ", ".join(f"{n} {a}/{a + b}" for n, (a, b) in s["tags"].items())]
    return "\n".join(lines)
