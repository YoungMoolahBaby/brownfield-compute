"""Figures for the reports (static PNGs): pass 1's site map and host-vs-help chart, pass 2's homes
map, pass 3's site plans.

Colours follow the dataviz reference palette: status is categorical, slots 1-3 (blue, orange,
aqua; the three that pass its all-pairs colour-vision check for scatter plots); ink and grid
tokens for text and chrome. Light mode only: these are images in a Markdown report.
"""

from __future__ import annotations

import io
import zipfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402
import shapefile  # noqa: E402  (pyshp)

from . import RAW_DIR  # noqa: E402
from .http import USER_AGENT  # noqa: E402

STATES_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_state_20m.zip"
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
STATUS = {"retired": "#2a78d6", "retiring": "#eb6834", "partly staying": "#1baf7a"}
LOWER48 = (-125.0, -66.5, 24.3, 49.5)


def _states():
    path = RAW_DIR / "cb_2024_us_state_20m.zip"
    if not path.exists():
        resp = requests.get(STATES_URL, headers={"User-Agent": USER_AGENT}, timeout=300)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    z = zipfile.ZipFile(path)
    stem = "cb_2024_us_state_20m"
    r = shapefile.Reader(shp=io.BytesIO(z.read(f"{stem}.shp")), dbf=io.BytesIO(z.read(f"{stem}.dbf")),
                         shx=io.BytesIO(z.read(f"{stem}.shx")))
    return r.shapes()


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)


# Offsets (points) and alignment tried in turn for each label.
_SPOTS = [(6, 4, "left", "bottom"), (6, -4, "left", "top"), (-6, 4, "right", "bottom"),
          (-6, -4, "right", "top"), (0, 9, "center", "bottom"), (0, -9, "center", "top"),
          (14, 14, "left", "bottom"), (-14, -14, "right", "top")]


def _place_labels(fig, ax, items, avoid=()):
    """Put each (x, y, text) label at the first spot whose box overlaps no earlier label (nor any
    box in `avoid`) and stays inside the axes; if none is free, the spot that overlaps least."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    frame = ax.get_window_extent(renderer)
    placed = list(avoid)
    for x, y, text in items:
        best = None
        for dx, dy, ha, va in _SPOTS:
            a = ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                            fontsize=7.5, color=INK, zorder=5)
            bb = a.get_window_extent(renderer).expanded(1.04, 1.15)
            cost = sum(_overlap(bb, q) for q in placed) + 1e9 * (1 - _inside(bb, frame))
            if best is None or cost < best[0]:
                if best is not None:
                    best[1].remove()
                best = (cost, a, bb)
            else:
                a.remove()
            if cost == 0:
                break
        placed.append(best[2])


def _overlap(a, b):
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    return max(w, 0) * max(h, 0)


def _inside(bb, frame):
    return float(bb.x0 >= frame.x0 and bb.x1 <= frame.x1 and bb.y0 >= frame.y0 and bb.y1 <= frame.y1)


def _size(mw):
    return 8 + mw / 12.0  # marker area in pt^2: 100 MW ~ 16, 2,000 MW ~ 175


def site_map(r: pd.DataFrame, labels: pd.DataFrame, path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.6), dpi=150, facecolor=SURFACE)
    _style(ax)
    for shp in _states():
        pts = np.array(shp.points)
        parts = list(shp.parts) + [len(pts)]
        for a, b in zip(parts[:-1], parts[1:]):
            ax.fill(pts[a:b, 0], pts[a:b, 1], facecolor="#f3f2ee", edgecolor=GRID, linewidth=0.6, zorder=1)
    m = r[(r["lon"] > LOWER48[0]) & (r["lon"] < LOWER48[1]) & (r["lat"] > LOWER48[2]) & (r["lat"] < LOWER48[3])]
    for status, colour in STATUS.items():
        s = m[m["status"] == status].sort_values("leaving_mw", ascending=False)
        ax.scatter(s["lon"], s["lat"], s=_size(s["leaving_mw"]), color=colour, edgecolors=SURFACE, linewidths=0.8,
                   alpha=0.9, zorder=3, label=f"{status} ({len(s)})")
    ax.set_xlim(LOWER48[0], LOWER48[1])
    ax.set_ylim(LOWER48[2], LOWER48[3])
    ax.set_aspect(1 / np.cos(np.radians(38)))
    ax.set_xticks([])
    ax.set_yticks([])
    leg = ax.legend(loc="lower left", frameon=False, fontsize=8, labelcolor=INK2, title="coal at the site",
                    title_fontsize=8, markerscale=0.8)
    leg.get_title().set_color(INK2)
    for mw in (250, 1000, 2500):
        ax.scatter([], [], s=_size(mw), color=MUTED, edgecolors=SURFACE, label=f"{mw:,} MW")
    handles, names = ax.get_legend_handles_labels()
    ax.add_artist(leg)
    ax.legend(handles[3:], names[3:], loc="lower right", frameon=False, fontsize=8, labelcolor=INK2,
              title="coal MW leaving", title_fontsize=8, labelspacing=1.2).get_title().set_color(INK2)
    out = len(r) - len(m)
    ax.set_title(f"{len(r)} US coal plant sites with 100+ MW of coal retired since 2015 or set to retire by 2035"
                 + (f" ({out} outside the lower 48 not shown)" if out else ""), fontsize=10, color=INK, loc="left")
    fig.text(0.01, 0.01, "EIA-860M, September 2026 data. Labelled: the known cases and the six sites strongest on "
             "both axes (all in the report's table).", fontsize=7, color=MUTED)
    fig.tight_layout()
    _place_labels(fig, ax, [(x["lon"], x["lat"], x["label"]) for _, x in labels.iterrows() if x.name in m.index])
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def host_help(r: pd.DataFrame, labels: pd.DataFrame, path) -> None:
    fig, ax = plt.subplots(figsize=(8, 7), dpi=150, facecolor=SURFACE)
    _style(ax)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for v in (0.75,):
        ax.axvline(v, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
        ax.axhline(v, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
    for status, colour in STATUS.items():
        s = r[r["status"] == status]
        ax.scatter(s["host_pct"], s["help_pct"], s=_size(s["leaving_mw"]), color=colour, edgecolors=SURFACE,
                   linewidths=0.8, alpha=0.9, label=f"{status} ({len(s)})", zorder=3)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("can host a data center (percentile among these sites)", color=INK2, fontsize=9)
    ax.set_ylabel("the town would gain (percentile among these sites)", color=INK2, fontsize=9)
    ax.text(0.99, 1.0, "top quarter on both", ha="right", va="bottom", fontsize=8, color=MUTED,
            transform=ax.transAxes)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=3, frameon=False, fontsize=8,
              labelcolor=INK2, markerscale=0.7)
    ax.set_title("Host vs help: every component weighted equally", fontsize=10, color=INK, loc="left")
    # The top-right corner is crowded: numbers by the points, names in a key under the chart.
    names = [f"{i} {x['label']}" for i, (_, x) in enumerate(labels.iterrows(), 1)]
    key = "\n".join("   ".join(names[k:k + 4]) for k in range(0, len(names), 4))
    fig.text(0.01, 0.03, key, fontsize=7.5, color=INK2, linespacing=1.5)
    fig.text(0.01, 0.01, "Marker size: coal MW leaving the site. Numbered: the six sites strongest on both axes "
             "and the known cases.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _place_labels(fig, ax, [(x["host_pct"], x["help_pct"], str(i)) for i, (_, x) in enumerate(labels.iterrows(), 1)])
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


BANDS = [(300, "#0d366b", "within 300 m"), (700, "#256abf", "300-700 m"),
         (1500, "#5598e7", "700 m-1.5 km"), (1e9, "#9ec5f4", "beyond 1.5 km")]


def homes_map(campus, homes, path, plant_xy=(0.0, 0.0)) -> None:
    """The campus (the plant owner's land near the plant) and every home around it, by distance to
    the campus edge (a one-hue ordinal ramp: darker = closer)."""
    from shapely.geometry import MultiPolygon

    fig, ax = plt.subplots(figsize=(9, 8.2), dpi=150, facecolor=SURFACE)
    _style(ax)
    polys = campus.geoms if isinstance(campus, MultiPolygon) else [campus]
    for poly in polys:
        x, y = poly.exterior.xy
        ax.fill(np.array(x) / 1000, np.array(y) / 1000, facecolor="#d9d7cf", edgecolor="#898781", linewidth=0.6,
                zorder=1)
    lo = 0.0
    for hi, colour, label in BANDS:
        pts = [(h[0], h[1]) for h in homes if lo < h[3] <= hi or (lo == 0.0 and h[3] <= hi)]
        if pts:
            a = np.array(pts) / 1000
            ax.scatter(a[:, 0], a[:, 1], s=6, color=colour, edgecolors="none", zorder=3,
                       label=f"{label} ({len(pts):,})")
        lo = hi
    ax.scatter([plant_xy[0]], [plant_xy[1]], marker="^", s=60, color=INK, zorder=4, label="the old plant")
    ax.set_aspect("equal")
    ax.set_xlabel("km east of the plant", color=INK2, fontsize=9)
    ax.set_ylabel("km north of the plant", color=INK2, fontsize=9)
    ax.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    leg = ax.legend(loc="upper left", frameon=True, fontsize=8, labelcolor=INK2, title="homes, by distance to the campus edge",
                    title_fontsize=8, markerscale=2)
    leg.get_frame().set_facecolor(SURFACE)
    leg.get_frame().set_edgecolor(GRID)
    leg.get_title().set_color(INK2)
    ax.set_title(f"{len(homes):,} homes around the Homer City campus (grey: the plant owner's land, "
                 f"{campus.area / 4046.86:,.0f} acres)", fontsize=10, color=INK, loc="left")
    fig.text(0.01, 0.01, "Indiana County parcels (PASDA, Nov 2023): parcels with a dwelling. Distances from each home "
             "parcel's centre to the campus edge; equipment sits further in.", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


# Pass 3, the site plan (D12): route types in the reference palette's slots 1-3, each with its own
# line style too; modules in quiet fills, named by direct labels.
_ROUTES = [("cars", "#2a78d6", "-", 1.6, "public road to the mobility hub"), ("trucks", "#eb6834", "-", 1.6, "truck roads"),
           ("walks", "#1baf7a", (0, (2.0, 1.4)), 1.3, "main walks")]
_NAMES = {"data hall": "data\nhall", "winter garden": "winter garden", "greenhouse": "greenhouse\n(food court on its town side)",
          "community center": "center\n+ rink", "square": "square", "field and loop": "field", "neighbourhood": "homes",
          "mobility hub": "hub", "remote delivery building": "delivery", "hall front": "mall",
          # The greenhouse as the hall's moat (D16): named once on its big blocks, the food court on its town corner.
          "greenhouse west": "greenhouse\n(the hall's moat)", "greenhouse east": "greenhouse\n(the hall's moat)",
          "greenhouse south-east": "food court", "greenhouse north-west": "", "greenhouse north-east": "", "greenhouse south-west": "",
          "flats": "flats", "townhouses": "townhouses", "houses": "houses"}
# The rings of homes (D16) in one warm hue, darker nearer the centre.
_FILLS = {"data hall": "#3d3c39", "neighbourhood": "#efe4d2", "greenhouse": "#e2ebe0", "field and loop": "#dbe8d2",
          "winter garden": "#dbe8d2", "square": "#ebe8e1", "flats": "#e3cfae", "townhouses": "#ecdcc3", "houses": "#f4ecdd",
          **{f"greenhouse {s}": "#e2ebe0" for s in ("west", "east", "north-west", "north-east", "south-west", "south-east")}}


def site_plans(spec: dict, path) -> None:
    """The current layout and the optimizer's proposals, side by side on one scale; north up, the town below."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import FancyBboxPatch, Rectangle

    lays = [("The current layout", spec["current"])] + [
        (f"Proposal {k + 1}" + (" (the current layout)" if q.get("is_current") else ""), q) for k, q in enumerate(spec["proposals"])]
    xs = [v for _, q in lays for m in q["modules"] for v in m["rect"][:2]] + [spec["gate"][0], spec["town"][0]]
    ys = [v for _, q in lays for m in q["modules"] for v in m["rect"][2:]] + [spec["gate"][1], spec["town"][1]]
    pad = 70.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    n = len(lays)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    w = 6.4
    h = w * (y1 - y0) / (x1 - x0) + 0.55
    fig, axes = plt.subplots(rows, cols, figsize=(w * cols, h * rows + 0.9), dpi=150, facecolor=SURFACE, squeeze=False)
    hall = spec["hall"]
    for ax, (title, q) in zip(axes.flat, lays):
        _style(ax)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y1, y0)  # y runs south: the town at the bottom
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        c = spec["cap"]
        ax.add_patch(Rectangle((c[0], c[2]), c[1] - c[0], c[3] - c[2], facecolor="none", edgecolor=MUTED, hatch="////",
                               linewidth=0.5, zorder=1))
        sb, sd = spec["standoff_m"], spec["setback_m"]
        ax.add_patch(FancyBboxPatch((hall[0], hall[2]), hall[1] - hall[0], hall[3] - hall[2], boxstyle=f"round,pad={sd}",
                                    facecolor="none", edgecolor=MUTED, linewidth=0.8, linestyle=(0, (1, 2)), zorder=2))
        ax.add_patch(Rectangle((hall[0] - sb, hall[2] - sb), hall[1] - hall[0] + 2 * sb, hall[3] - hall[2] + 2 * sb, facecolor="none",
                               edgecolor=INK2, linewidth=0.8, linestyle=(0, (4, 2)), zorder=2))
        small, inside = [], []
        for m in q["modules"]:
            r = m["rect"]
            ax.add_patch(Rectangle((r[0], r[2]), r[1] - r[0], r[3] - r[2], facecolor=_FILLS.get(m["name"], "#e6e4de"),
                                   edgecolor=INK2, linewidth=0.6, zorder=3))
            cx, cy = (r[0] + r[1]) / 2, (r[2] + r[3]) / 2
            name = _NAMES.get(m["name"], m["name"])
            if not name:
                continue
            if min(r[1] - r[0], r[3] - r[2]) >= 85.0 and m["name"] != "data hall":
                inside.append(ax.text(cx, cy, name, ha="center", va="center", fontsize=7.5, color=INK, zorder=6, linespacing=1.1))
            elif m["name"] == "data hall":
                inside.append(ax.text(cx, cy, name, ha="center", va="center", fontsize=7, color=SURFACE, zorder=6, linespacing=1.0))
            else:
                small.append((cx, cy, name.replace("\n", " ")))
        for key, colour, style, lw, _ in _ROUTES:
            for line in q.get(key, []):
                a = np.array(line)
                ax.plot(a[:, 0], a[:, 1], color=colour, linestyle=style, linewidth=lw, solid_capstyle="round", zorder=4)
        # Where a road still meets a walk: an underpass under a truck road, a raised crossing on the public road.
        for key, mark in [("underpasses", "s"), ("raised_crossings", "o")]:
            for cx, cy in q.get(key, []):
                ax.plot([cx], [cy], marker=mark, markersize=6.5, markerfacecolor=SURFACE, markeredgecolor=INK, markeredgewidth=1.1, zorder=6)
        gx, gy = spec["gate"]
        ax.plot([gx], [gy], marker="v", markersize=7, color=INK, zorder=5)
        small.append((gx, gy, "site entrance"))
        tx, ty = spec["town"]
        ax.annotate("", (tx, y1 - 4), xytext=(tx, ty), arrowprops=dict(arrowstyle="->", color=INK2, linewidth=0.8), zorder=5)
        inside.append(ax.text(tx + 14, y1 - 6, "to Homer City borough", ha="left", va="bottom", fontsize=7.5, color=INK2, zorder=5))
        fig.canvas.draw()
        rend = fig.canvas.get_renderer()
        _place_labels(fig, ax, small, avoid=[a.get_window_extent(rend).expanded(1.04, 1.15) for a in inside])
        sub = (f"${q['score']:,.0f}k a year  ·  underpasses {q['crossings']}, raised crossings {q.get('car_crossings', 0)}  ·  "
               f"{q['truck_km_yr']:,.0f} truck-km a year")
        ax.set_title(f"{title}\n{sub}", fontsize=9.5, color=INK, loc="left", linespacing=1.4)
        # A 200 m scale bar in the bottom-left corner.
        bx, by_ = x0 + 30, y1 - 30
        ax.plot([bx, bx + 200], [by_, by_], color=INK, linewidth=1.2, solid_capstyle="butt", zorder=5)
        ax.text(bx + 100, by_ - 10, "200 m", ha="center", va="bottom", fontsize=7, color=INK2)
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    handles = [Line2D([], [], color=c, linestyle=s, linewidth=lw, label=lab) for _, c, s, lw, lab in _ROUTES]
    handles += [Line2D([], [], color=INK, marker="s", linestyle="none", markerfacecolor=SURFACE, markersize=6, label="underpass (truck road over a walk)"),
                Line2D([], [], color=INK, marker="o", linestyle="none", markerfacecolor=SURFACE, markersize=6, label="raised crossing (public road)"),
                Line2D([], [], color=INK2, linestyle=(0, (4, 2)), linewidth=0.8, label=f"stand-off band ({spec['standoff_m']:g} m, no public vehicles)"),
                Line2D([], [], color=MUTED, linestyle=(0, (1, 2)), linewidth=0.8, label=f"noise setback ({spec['setback_m']:g} m, no homes)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8, labelcolor=INK2,
               bbox_to_anchor=(0.5, 0.025))
    fig.text(0.01, 0.006, "North up; the town lies south. Positions are schematic (the real site is not yet mapped); the data hall "
             "is fixed." + chr(10) + "Cost a year (lower is better): walking time at US DOT's value, the trucks' running cost, and the warm main, "
             "underpasses and raised crossings paid off. Routes found on a 10 m grid round the buildings (brownfield site).", fontsize=6.8, color=MUTED)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
