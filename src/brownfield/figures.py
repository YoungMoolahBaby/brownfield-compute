"""Pass 1 figures: the site map and the host-vs-help chart (static PNGs for the report).

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


def _place_labels(fig, ax, items):
    """Put each (x, y, text) label at the first spot whose box overlaps no earlier label and stays
    inside the axes; if none is free, the spot that overlaps least."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    frame = ax.get_window_extent(renderer)
    placed = []
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
