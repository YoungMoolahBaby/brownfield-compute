"""D17: the real land round the Homer City plant, from public map services.

Every layer Indiana County's land development ordinance asks an applicant to show (SALDO 302.6:
topography, water features, mining and spoiled land, wells, roads, utilities, flood), fetched for a
~15 x 15 km box round the plant and put in metres east and north of the old plant (`homes.Local`):

- ground: USGS 3DEP 1/3 arc-second (10 m) elevation, slope and hillshade;
- water: FEMA's flood zones, the National Wetlands Inventory, NHD streams and water bodies;
- mining: DEP's mined-out underground areas, longwall panels, surface-mining permits, coal refuse
  disposal areas and abandoned mine land;
- wells: DEP's oil and gas wells;
- roads, rail and transmission corridors; the towns round the site (Census places);
- the plant owner's land (PASDA parcels, as pass 2).

AWS's six sites come from the county's posted master plan (`sites`), traced and georeferenced on
published points. Substations and anything finer than a site's outline are left out: this repo is
public and stays at published principles.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

import numpy as np
import requests
from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import unary_union

from . import ROOT
from .homes import Local
from .http import USER_AGENT, fetch_json

RAW = ROOT / "data" / "raw" / "land"
PLANT = (40.512825, -79.19611)  # EIA-860, Homer City Generating Station (pass 1)

PASDA = "https://mapservices.pasda.psu.edu/server/rest/services/pasda"
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer"
LAYERS = {
    # name: (layer URL, fields, page size, simplify in degrees or None)
    "parcels": (f"{PASDA}/IndianaCounty/MapServer/5", "LAST_NAME,GIS_ACRES,PARCEL_ID,DWELLING_T", 1000, 0.00002),
    "flood": ("https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28", "FLD_ZONE,SFHA_TF", 1000, 0.00005),
    "wetlands": ("https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0",
                 "ATTRIBUTE,WETLAND_TYPE,ACRES", 500, 0.00002),
    "streams": ("https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/6", "gnis_name,ftype", 1000, 0.00002),
    "water": ("https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/12", "gnis_name,ftype", 100, 0.0001),
    "wells": (f"{PASDA}/DEP/MapServer/22", "PERMIT_NUM,WELL_TYPE,WELL_STATU,UNCONVENTI", 1000, None),
    "mined": (f"{PASDA}/DEP2/MapServer/1", "COAL_SEAM,LASTMINED", 1000, 0.00003),
    "longwall": (f"{PASDA}/DEP2/MapServer/0", "*", 1000, 0.00003),
    "surface_mining": (f"{PASDA}/DEP2/MapServer/22", "*", 1000, 0.00003),
    "refuse": (f"{PASDA}/DEP2/MapServer/5", "*", 1000, 0.00002),
    "aml": (f"{PASDA}/DEP/MapServer/1", "*", 1000, 0.00002),
    "state_roads": (f"{PASDA}/PennDOT/MapServer/4", "STREET_NAM,TRAF_RT_NO,CUR_AADT", 1000, 0.00002),
    "local_roads": (f"{PASDA}/PennDOT/MapServer/3", "LR_NAME,ROAD_OWNER", 1000, 0.00002),
    "rail": (f"{PASDA}/PennDOT/MapServer/22", "RR_OPERRR,TRACK_USE", 1000, 0.00002),
    "transmission": (f"{PASDA}/HIFLD_FEMA_PA/MapServer/215", "VOLTAGE,VOLT_CLASS", 1000, 0.00002),
    # The towns round the site (Census incorporated places and designated places) and the townships.
    "places": (f"{TIGER}/4", "NAME,BASENAME,LSADC", 1000, 0.0001),
    "cdps": (f"{TIGER}/5", "NAME,BASENAME,LSADC", 1000, 0.0001),
    "townships": (f"{TIGER}/1", "NAME,BASENAME", 1000, 0.0001),
}


def box(p: dict) -> tuple[float, float, float, float]:
    b = "land.box."
    return (p[b + "west"], p[b + "south"], p[b + "east"], p[b + "north"])


def features(name: str, bbox: tuple) -> list[dict]:
    """A layer's features touching the box, as GeoJSON (lon/lat), paged and cached."""
    url, fields, page, simplify = LAYERS[name]
    out, offset = [], 0
    while True:
        params = {"where": "1=1", "outFields": fields, "returnGeometry": "true", "outSR": 4326, "f": "geojson",
                  "geometry": ",".join(map(str, bbox)), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                  "spatialRel": "esriSpatialRelIntersects", "resultOffset": offset, "resultRecordCount": page}
        if simplify:
            params["maxAllowableOffset"] = simplify
        got = fetch_json(f"{url}/query", params=params, ttl_days=365, timeout=300).get("features", [])
        out += got
        if len(got) < page:
            return out
        offset += page


def dem(p: dict) -> tuple[np.ndarray, tuple]:
    """Ground elevation (m) over the box: USGS 3DEP, lon/lat grid of `land.dem_px` cells a side, row 0
    at the north edge. Cached as a GeoTIFF in data/raw/land/."""
    from PIL import Image

    w, s, e, n = box(p)
    px = int(p["land.dem_px"])
    path = RAW / f"dem_{px}.tif"
    if not path.exists():
        resp = requests.get("https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage",
                            params={"bbox": f"{w},{s},{e},{n}", "bboxSR": 4326, "imageSR": 4326, "size": f"{px},{px}",
                                    "format": "tiff", "pixelType": "F32", "noData": -9999,
                                    "interpolation": "RSP_BilinearInterpolation", "f": "image"},
                            headers={"User-Agent": USER_AGENT}, timeout=300)
        resp.raise_for_status()
        RAW.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    z = np.asarray(Image.open(io.BytesIO(path.read_bytes())), dtype=float)
    z[z < -1000] = np.nan
    return z, (w, s, e, n)


def slope_pct(z: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Slope (%) of a grid with cells dx by dy metres (central differences)."""
    gy, gx = np.gradient(z, dy, dx)
    return 100.0 * np.hypot(gx, gy)


def local_geoms(feats: list[dict], loc: Local) -> list:
    """Features' geometries in metres from the plant (repaired where simplification broke them)."""
    out = []
    for f in feats:
        g = f.get("geometry")
        if not g:
            continue
        geom = loc.geom(shape(g))
        out.append(make_valid(geom) if not geom.is_valid else geom)
    return out


def union(geoms: list):
    return unary_union(geoms) if geoms else None


def fetch_all(p: dict) -> dict[str, list[dict]]:
    """Every vector layer for the box (cached)."""
    bbox = box(p)
    return {name: features(name, bbox) for name in LAYERS}




# --- The towns as built, and the land's cover (D18) -----------------------------------------------

# Microsoft's building footprints (machine-traced from imagery; ODbL), in zoom-9 quadkey tiles. The
# tiles over the box are listed in its dataset index. OpenStreetMap maps only ~61 of Homer City's
# ~800 buildings, so it isn't used.
MS_INDEX = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"


def _quadkey(lat: float, lon: float, z: int = 9) -> str:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    s = math.sin(math.radians(lat))
    y = int((0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n)
    return "".join(str(((x >> i) & 1) + 2 * ((y >> i) & 1)) for i in range(z - 1, -1, -1))


def _download(url: str, path) -> None:
    if path.exists():
        return
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=600)
    resp.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(resp.content)


def buildings(p: dict) -> list[dict]:
    """Every building footprint in the box: {"lonlat": [(lon, lat), ...], "height": m or None}. The
    tiles (~21 MB) and the box's buildings are cached in data/raw/land/msbuildings/."""
    import gzip
    import json

    d = RAW / "msbuildings"
    cache = d / "box.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    w, s, e, n = box(p)
    keys = sorted({_quadkey(la, lo) for la in (s, n) for lo in (w, e)})
    _download(MS_INDEX, d / "dataset-links.csv")
    urls = {}
    for line in (d / "dataset-links.csv").read_text(encoding="utf-8").splitlines():
        f = line.split(",")
        if len(f) >= 3 and f[0] == "UnitedStates" and f[1] in keys:
            urls[f[1]] = f[2]
    out = []
    for k in keys:
        path = d / f"{k}.csv.gz"
        _download(urls[k], path)
        for line in gzip.decompress(path.read_bytes()).decode("utf-8").splitlines():
            f = json.loads(line)
            ring = f["geometry"]["coordinates"][0]
            lo, la = ring[0]
            if w <= lo <= e and s <= la <= n:
                h = f["properties"].get("height", -1.0)
                out.append({"lonlat": [(round(a, 7), round(b, 7)) for a, b in ring], "height": h if h and h > 0 else None})
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


# NLCD 2021 land cover (MRLC, 30 m), fetched as its styled WMS image; each class has its own colour.
NLCD_WMS = "https://www.mrlc.gov/geoserver/mrlc_display/NLCD_2021_Land_Cover_L48/wms"
NLCD = {11: (70, 107, 159), 21: (222, 197, 197), 22: (217, 146, 130), 23: (235, 0, 0), 24: (171, 0, 0), 31: (179, 172, 159),
        41: (104, 171, 95), 42: (28, 95, 44), 43: (181, 197, 143), 52: (204, 184, 121), 71: (223, 223, 194), 81: (220, 217, 57),
        82: (171, 108, 40), 90: (184, 217, 235), 95: (108, 159, 184)}


def landcover(p: dict, px: int = 1200) -> tuple[np.ndarray, tuple]:
    """NLCD classes over the box on a lon/lat grid (row 0 north), each pixel the class whose legend
    colour is nearest (the WMS image's colours sit within a few units of the legend's)."""
    from PIL import Image

    w, s, e, n = box(p)
    h = int(round(px * (n - s) / (e - w)))
    path = RAW / "nlcd" / f"lc_{px}.png"
    if not path.exists():
        resp = requests.get(NLCD_WMS, params={"service": "WMS", "version": "1.1.1", "request": "GetMap",
                                              "layers": "NLCD_2021_Land_Cover_L48", "styles": "", "srs": "EPSG:4326",
                                              "bbox": f"{w},{s},{e},{n}", "width": px, "height": h, "format": "image/png"},
                            headers={"User-Agent": USER_AGENT}, timeout=300)
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    keys = np.array(list(NLCD))
    cols = np.array([NLCD[k] for k in keys], dtype=float)
    d = ((rgb[:, :, None, :] - cols[None, None, :, :]) ** 2).sum(-1)
    return keys[np.argmin(d, axis=2)].astype(np.uint8), (w, s, e, n)


# --- The master plan, georeferenced (D17) ---------------------------------------------------------
#
# The county's posted master plan (Kimley-Horn sheet C050.00, ~1,000 px across) has no coordinates.
# It is fitted to the real map by chamfer matching: its grey line work (roads, parcel lines, the
# township line) is moved by a similarity transform (scale, turn, shift) until it lies as close as
# it can to the real roads, parcel boundaries and township lines; the median distance left over is
# the outlines' accuracy.

PLAN_URL = "https://www.icopd.org/images/overall_site_new.jpg"
PLAN_AREA = (0, 0, 790, 682)  # the sheet's map, without its title block and legend (pixels)


def master_plan() -> np.ndarray:
    """The posted master plan as an RGB array (cached in data/raw/land/)."""
    from PIL import Image

    path = RAW / "overall_site_new.jpg"
    if not path.exists():
        resp = requests.get(PLAN_URL, headers={"User-Agent": USER_AGENT}, timeout=120)
        resp.raise_for_status()
        RAW.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
    return np.asarray(Image.open(path).convert("RGB"), dtype=float)


def line_pixels(img: np.ndarray) -> np.ndarray:
    """(px, py) of the sheet's grey and black line work: dark and unsaturated, in the map area."""
    x0, y0, x1, y1 = PLAN_AREA
    sub = img[y0:y1, x0:x1]
    hi, lo = sub.max(axis=2), sub.min(axis=2)
    ys, xs = np.nonzero((hi < 175) & (hi - lo < 28))
    return np.column_stack([xs + x0, ys + y0]).astype(float)


@dataclass
class Fit:
    """Pixel (px, py) to metres from the plant: scale s (m a pixel), turn th (radians), shift (tx, ty);
    the sheet's y runs down, the map's up."""

    s: float
    th: float
    tx: float
    ty: float
    cx: float = 400.0
    cy: float = 340.0

    def xy(self, px, py):
        u, v = np.asarray(px, float) - self.cx, -(np.asarray(py, float) - self.cy)
        c, s_ = math.cos(self.th), math.sin(self.th)
        return self.tx + self.s * (c * u - s_ * v), self.ty + self.s * (s_ * u + c * v)


class Chamfer:
    """Distance (m, capped) from any point to the nearest real line: roads, parcel boundaries and
    township lines rasterised at `cell` m and grown cell by cell."""

    def __init__(self, lines: list, extent: tuple, cell: float = 5.0, cap: int = 30):
        from PIL import Image, ImageDraw, ImageFilter

        self.x0, self.y0, x1, y1 = extent
        self.cell = cell
        self.nx, self.ny = int((x1 - self.x0) / cell), int((y1 - self.y0) / cell)
        im = Image.new("L", (self.nx, self.ny), 0)
        d = ImageDraw.Draw(im)
        for g in lines:
            for part in getattr(g, "geoms", [g]):
                coords = list(part.exterior.coords) if part.geom_type == "Polygon" else list(part.coords)
                pts = [((x - self.x0) / cell, (y1 - y) / cell) for x, y, *_ in coords]
                if len(pts) > 1:
                    d.line(pts, fill=255, width=1)
        dist = np.full((self.ny, self.nx), float(cap))
        grown = im
        for k in range(cap):
            a = np.asarray(grown) > 0
            dist[a & (dist >= cap)] = k
            grown = grown.filter(ImageFilter.MaxFilter(3))
        self.dist = dist * cell
        self.y1 = y1
        self.cap = cap * cell

    def at(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        i = ((x - self.x0) / self.cell).astype(int)
        j = ((self.y1 - y) / self.cell).astype(int)
        ok = (i >= 0) & (i < self.nx) & (j >= 0) & (j < self.ny)
        out = np.full(x.shape, self.cap)
        out[ok] = self.dist[j[ok], i[ok]]
        return out


def _nelder_mead(f, x0: np.ndarray, step: np.ndarray, iters: int = 400) -> np.ndarray:
    """A plain Nelder-Mead minimiser (no scipy in this project)."""
    n = len(x0)
    pts = [x0] + [x0 + np.eye(n)[i] * step[i] for i in range(n)]
    vals = [f(q) for q in pts]
    for _ in range(iters):
        order = np.argsort(vals)
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        cen = np.mean(pts[:-1], axis=0)
        xr = cen + (cen - pts[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = cen + 2 * (cen - pts[-1])
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = cen + 0.5 * (pts[-1] - cen)
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                pts = [pts[0]] + [pts[0] + 0.5 * (q - pts[0]) for q in pts[1:]]
                vals = [vals[0]] + [f(q) for q in pts[1:]]
    return pts[int(np.argmin(vals))]


# Two published points to start the fit: Rura's drawn buildings on DEP's Rura Field grading permit
# (PAC320065, 40.50361 N, 79.18379 W), and the power block's drawn gas units on HCR's gas plant permit
# point (E3206225-004, 40.517958 N, 79.196697 W); sheet pixels, then lat/lon.
START_PX = ((622.0, 460.0), (505.0, 280.0))
START_LL = ((40.50361, -79.18379), (40.517958, -79.196697))


def two_point_start() -> Fit:
    """The similarity transform that puts the two start pixels on their published points exactly."""
    loc = Local(*PLANT)
    (a_px, b_px), (a_ll, b_ll) = START_PX, START_LL
    a_m, b_m = loc.xy(a_ll[1], a_ll[0]), loc.xy(b_ll[1], b_ll[0])
    vi = (b_px[0] - a_px[0], -(b_px[1] - a_px[1]))
    vm = (b_m[0] - a_m[0], b_m[1] - a_m[1])
    s = math.hypot(*vm) / math.hypot(*vi)
    th = math.atan2(vm[1], vm[0]) - math.atan2(vi[1], vi[0])
    x, y = Fit(s, th, 0.0, 0.0).xy(*b_px)
    return Fit(s, th, b_m[0] - float(x), b_m[1] - float(y))


def georeference(p: dict, layers: dict, start: Fit | None = None) -> tuple[Fit, dict]:
    """The similarity transform that lays the master plan's line work on the real lines (roads,
    parcel boundaries, township lines), refined from the two-point start; with the median and
    80th-percentile distance of its line pixels from the real lines (m). The search stays near the
    start: a wide one finds false matches among the many parcel lines."""
    loc = Local(*PLANT)
    lines = (local_geoms(layers["state_roads"], loc) + local_geoms(layers["local_roads"], loc)
             + [g.boundary for g in local_geoms(layers["townships"], loc)]
             + [g.boundary for g in local_geoms(layers["parcels"], loc)])
    ch = Chamfer(lines, (-8000.0, -7000.0, 8000.0, 7000.0))
    px = line_pixels(master_plan())
    start = start or two_point_start()

    def cost(q):
        f = Fit(q[0], q[1], q[2], q[3])
        x, y = f.xy(px[:, 0], px[:, 1])
        return float(np.mean(ch.at(x, y)))

    q = _nelder_mead(cost, np.array([start.s, start.th, start.tx, start.ty]), np.array([0.2, 0.005, 30.0, 30.0]))
    f = Fit(*q)
    d = ch.at(*f.xy(px[:, 0], px[:, 1]))
    return f, {"median_m": float(np.median(d)), "p80_m": float(np.percentile(d, 80)), "cost": cost(q)}


# --- AWS's six sites, from the master plan's drawn development (D17) ------------------------------

# Where each site's buildings stand on the sheet (pixels), to group the drawn features by site; the
# names are the narrative's (the sheet labels two "Westfield" and "Greenfield").
SITE_SEEDS = {"Bruner": (255, 205), "Helen": (445, 338), "Green": (515, 392), "West": (432, 420),
              "Harvey/Gaston": (362, 520), "Rura": (618, 460)}
FIT = (9.467961995427117, 0.016248587531517297, -951.727701849333, 43.96725370397553)  # 2026-11-17, from a hand-read start; `georeference()` gives the same within ~5 m on the ground


def colour_masks(img: np.ndarray) -> dict[str, np.ndarray]:
    """The sheet's drawn development by colour: orange buildings, blue stormwater basins, the dark grey
    of yards, substations and parking (in the map area only)."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    area = np.zeros(r.shape, bool)
    x0, y0, x1, y1 = PLAN_AREA
    area[y0:y1, x0:x1] = True
    hi, lo = img.max(axis=2), img.min(axis=2)
    return {"buildings": area & (r > 200) & (g > 110) & (g < 200) & (b < 100),
            "basins": area & (b > 180) & (r < 90) & (g < 150),
            "yards": area & (hi < 120) & (hi - lo < 20) & (hi > 50)}


def components(mask: np.ndarray, min_px: int = 4) -> list[np.ndarray]:
    """Connected groups of pixels (8-way), as (row, col) arrays."""
    seen = np.zeros(mask.shape, bool)
    out = []
    rows, cols = np.nonzero(mask)
    for r0, c0 in zip(rows, cols):
        if seen[r0, c0]:
            continue
        stack, pts = [(r0, c0)], []
        seen[r0, c0] = True
        while stack:
            r, c = stack.pop()
            pts.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < mask.shape[0] and 0 <= cc < mask.shape[1] and mask[rr, cc] and not seen[rr, cc]:
                        seen[rr, cc] = True
                        stack.append((rr, cc))
        if len(pts) >= min_px:
            out.append(np.array(pts))
    return out


def aws_sites(p: dict, fit: Fit | None = None, reach_px: float = 70.0) -> dict[str, dict]:
    """Each site's drawn development in metres from the plant: its buildings' area, an estimate of
    how many 112,500 ft2 footprints that is, and its footprint (buildings, basins and yards wrapped,
    with a margin of half a road)."""
    from shapely.geometry import MultiPoint

    fit = fit or Fit(*FIT)
    img = master_plan()
    masks = colour_masks(img)
    px_m2 = fit.s ** 2
    out = {k: {"building_px": 0, "pts": [], "bpts": []} for k in SITE_SEEDS}
    for kind, mask in masks.items():
        for comp in components(mask):
            cy, cx = comp.mean(axis=0)
            name, d = min(((n, math.dist((cx, cy), q)) for n, q in SITE_SEEDS.items()), key=lambda t: t[1])
            if d > reach_px:
                continue  # drawn features away from any site (the power block's own works, the legend)
            if kind == "buildings":
                out[name]["building_px"] += len(comp)
                out[name]["bpts"] += [tuple(q) for q in comp[:, ::-1]]
            out[name]["pts"] += [tuple(q) for q in comp[:, ::-1]]
    foot_m2 = p["land.aws.footprint_ft2"] * 0.09290304
    for name, s in out.items():
        pts = np.array(s.pop("pts"), float)
        x, y = fit.xy(pts[:, 0], pts[:, 1])
        hull = MultiPoint(list(zip(x, y))).convex_hull.buffer(p["land.aws.margin_m"])
        b = np.array(s.pop("bpts"), float)
        s.update(building_m2=s["building_px"] * px_m2, buildings=s["building_px"] * px_m2 / foot_m2, footprint=hull,
                 acres=hull.area / 4046.86, centre=(hull.centroid.x, hull.centroid.y),
                 building_xy=np.column_stack(fit.xy(b[:, 0], b[:, 1])))  # each drawn building pixel, m from the plant
    return out


# The power block on the master plan: HCR's retained land round the old plant and the gas plant, the
# sheet's large dashed loop, traced by hand (pixels; approximate).
POWER_BLOCK_PX = [(320, 120), (377, 82), (432, 119), (485, 75), (492, 50), (520, 77), (572, 80), (575, 50), (592, 45),
                  (587, 77), (620, 100), (632, 145), (647, 185), (660, 187), (652, 330), (645, 380), (618, 405), (560, 335),
                  (480, 318), (420, 300), (360, 268), (320, 230)]


def power_block(fit: Fit | None = None):
    from shapely.geometry import Polygon

    fit = fit or Fit(*FIT)
    xs, ys = fit.xy([q[0] for q in POWER_BLOCK_PX], [q[1] for q in POWER_BLOCK_PX])
    return Polygon(list(zip(xs, ys)))


# --- The land as a 10 m grid: what limits building, and where homes could go (D17) ----------------

class Grid:
    """The elevation grid's cells (lon/lat, row 0 north), and local-metre geometries drawn onto it."""

    def __init__(self, p: dict):
        self.z, (self.w, self.s, self.e, self.n) = dem(p)
        self.ny, self.nx = self.z.shape
        self.loc = Local(*PLANT)
        self.dlon, self.dlat = (self.e - self.w) / self.nx, (self.n - self.s) / self.ny
        self.dx, self.dy = self.dlon * self.loc.kx, self.dlat * 111_320.0
        self.cell_ha = self.dx * self.dy / 1e4

    def pix(self, x, y):
        lon = self.loc.lon0 + np.asarray(x, float) / self.loc.kx
        lat = self.loc.lat0 + np.asarray(y, float) / 111_320.0
        return (lon - self.w) / self.dlon, (self.n - lat) / self.dlat

    def xy(self, col, row):
        """Local metres of cell centres."""
        lon = self.w + (np.asarray(col, float) + 0.5) * self.dlon
        lat = self.n - (np.asarray(row, float) + 0.5) * self.dlat
        return self.loc.xy(lon, lat)

    def draw(self, geoms: list) -> np.ndarray:
        """Cells covered by polygons (holes kept open), lines and points in local metres."""
        from PIL import Image, ImageDraw

        im = Image.new("L", (self.nx, self.ny), 0)
        d = ImageDraw.Draw(im)
        for g in geoms:
            for part in getattr(g, "geoms", [g]):
                if part.is_empty:
                    continue
                if part.geom_type == "Polygon":
                    c, r = self.pix(*np.array(part.exterior.coords)[:, :2].T)
                    d.polygon(list(zip(c, r)), fill=255)
                    for hole in part.interiors:
                        c, r = self.pix(*np.array(hole.coords)[:, :2].T)
                        d.polygon(list(zip(c, r)), fill=0)
                elif part.geom_type in ("LineString", "LinearRing"):
                    c, r = self.pix(*np.array(part.coords)[:, :2].T)
                    d.line(list(zip(c, r)), fill=255, width=1)
                elif part.geom_type == "Point":
                    c, r = self.pix(part.x, part.y)
                    d.point((float(c), float(r)), fill=255)
        return np.asarray(im) > 0

    def distance(self, mask: np.ndarray, upto_m: float) -> np.ndarray:
        """Metres from each cell to the mask (to `upto_m`, beyond it inf), grown a cell at a time
        (8-way, so a little short on the diagonals: within ~8% of the true distance)."""
        from PIL import Image, ImageFilter

        cell = (self.dx + self.dy) / 2
        out = np.full(mask.shape, np.inf)
        im = Image.fromarray((mask * 255).astype(np.uint8))
        for k in range(int(upto_m / cell) + 1):
            a = np.asarray(im) > 0
            out[a & np.isinf(out)] = k * cell
            im = im.filter(ImageFilter.MaxFilter(3))
        return out


BANDS = ((0.0, 300.0), (300.0, 700.0), (700.0, 1500.0))


def analysis(p: dict, layers: dict, sites: dict) -> dict:
    """What limits building on every cell, the land left where homes could go, and how much of it lies
    near each site."""
    g = Grid(p)
    loc = g.loc
    geo = lambda name: local_geoms(layers[name], loc)
    slope = slope_pct(g.z, g.dx, g.dy)
    sfha = [geom for f, geom in zip([f for f in layers["flood"] if f.get("geometry")], geo("flood"))
            if f["properties"].get("SFHA_TF") == "T"]
    house = [f for f in layers["parcels"] if f.get("geometry") and (f["properties"].get("DWELLING_T") or "").strip()]
    lot = lambda f: (f["properties"].get("GIS_ACRES") or 0.0) <= p["land.home_lot_max_ac"]
    homes = [loc.geom(shape(f["geometry"])) for f in house if lot(f)]
    farms = [loc.geom(shape(f["geometry"])) for f in house if not lot(f)]
    wells = {"unconventional": [], "conventional": [], "plugged": []}
    for f in layers["wells"]:
        st, unc = (f["properties"].get("WELL_STATU") or ""), f["properties"].get("UNCONVENTI") == "Y"
        if not f.get("geometry") or "Not Drilled" in st or "Never" in st or st == "Duplicate":
            continue
        key = "plugged" if ("Plugged" in st or "Abandoned" in st or "Orphan" in st) else ("unconventional" if unc else "conventional")
        wells[key].append(loc.geom(shape(f["geometry"])))
    L = "land."
    m = {
        "steep slopes": slope > p[L + "slope_hard"],
        "flood zone": g.draw(sfha),
        "wetlands": g.draw([q.buffer(p[L + "wetland_buffer_m"]) for q in geo("wetlands")]),
        "streams": g.draw([q.buffer(p[L + "stream_buffer_m"]) for q in geo("streams")]),
        "lakes and ponds": g.draw(geo("water")),
        "oil and gas wells": g.draw([q.buffer(p[L + "well_setback_m"]) for q in wells["unconventional"]]
                                    + [q.buffer(p[L + "conventional_well_m"]) for q in wells["conventional"]]
                                    + [q.buffer(p[L + "plugged_well_m"]) for q in wells["plugged"]]),
        "coal refuse": g.draw(geo("refuse")),
        "abandoned mine land": g.draw(geo("aml")),
        "transmission lines": g.draw([q.buffer(p[L + "transmission_m"]) for q in geo("transmission")]),
        "existing homes": g.draw(homes),
        "AWS's sites": g.draw([s["footprint"] for s in sites.values()]),
        "the power block": g.draw([power_block()]),
    }
    flags = {"sloping (15-25%)": (slope > p[L + "slope_soft"]) & (slope <= p[L + "slope_hard"]),
             "undermined": g.draw(geo("mined") + geo("longwall")),
             "surface-mined": g.draw(geo("surface_mining")),
             "farms and estates with a house": g.draw(farms)}
    valid = ~np.isnan(g.z)
    excluded = np.zeros(g.z.shape, bool)
    for v in m.values():
        excluded |= v
    buildable = valid & ~excluded
    near = {}
    for name, s in sites.items():
        dist = g.distance(g.draw([s["footprint"]]), BANDS[-1][1])
        rows = []
        for a, b in BANDS:
            band = (dist > a) & (dist <= b) & valid
            ok = band & buildable
            rows.append({"band": (a, b), "ha": float(band.sum() * g.cell_ha), "buildable_ha": float(ok.sum() * g.cell_ha),
                         "flat_ha": float((ok & ~flags["sloping (15-25%)"]).sum() * g.cell_ha),
                         "undermined_ha": float((ok & flags["undermined"]).sum() * g.cell_ha)})
        near[name] = rows
    return {"grid": g, "slope": slope, "masks": m, "flags": flags, "buildable": buildable, "near": near,
            "total_ha": float(valid.sum() * g.cell_ha),
            "excluded_ha": {k: float((v & valid).sum() * g.cell_ha) for k, v in m.items()},
            "flag_ha": {k: float((v & valid).sum() * g.cell_ha) for k, v in flags.items()},
            "buildable_ha": float(buildable.sum() * g.cell_ha)}


def site_counts(p: dict, sites: dict) -> None:
    """The filing's 39 buildings shared among the sites in proportion to their drawn building area."""
    from .rings import _apportion

    tot = sum(s["building_m2"] for s in sites.values())
    names = list(sites)
    for name, n in zip(names, _apportion(int(p["land.aws.buildings"]), [sites[k]["building_m2"] / tot for k in names])):
        sites[name]["n"] = n


def sites_geojson(sites: dict, fit: Fit | None = None) -> dict:
    """The six sites in lon/lat for data/aws_sites.geojson (a derived table, its source named)."""
    from shapely.geometry import mapping
    from shapely.ops import transform

    loc = Local(*PLANT)
    to_ll = lambda x, y, z=None: (loc.lon0 + np.asarray(x) / loc.kx, loc.lat0 + np.asarray(y) / 111_320.0)
    fit = fit or Fit(*FIT)
    feats = [{"type": "Feature", "properties": {"site": k, "buildings": s["n"], "drawn_building_m2": round(s["building_m2"]),
                                                 "developed_acres": round(s["acres"])},
              "geometry": mapping(transform(to_ll, s["footprint"].simplify(5.0)))} for k, s in sites.items()]
    return {"type": "FeatureCollection",
            "source": ("Traced from the county's posted master plan, Kimley-Horn sheet C050.00 'PIT100 Master Plan, Overall Campus "
                       f"Site Plan' ({PLAN_URL}): the drawn buildings, basins and yards of each site, wrapped, with a margin; fitted "
                       f"to PennDOT roads, parcel lines and the township line (scale {fit.s:.2f} m a pixel). Buildings: the AWS "
                       "Project Narrative's 39 shared by drawn building area. Approximate: the deeded boundaries aren't public."),
            "features": feats}


def report(p: dict, a: dict, sites: dict, fit_note: str = "") -> str:
    L = ["**The land round the plant** (a ~15 x 15 km box; USGS 3DEP 10 m elevation and public map services)", "",
         f"Of {a['total_ha']:,.0f} ha, {a['buildable_ha']:,.0f} ha ({a['buildable_ha'] / a['total_ha']:.0%}) has no constraint "
         "below on it.", "", "| Left unbuilt | ha |", "|---|---|"]
    L += [f"| {k} | {v:,.0f} |" for k, v in a["excluded_ha"].items()]
    L += ["", "| Buildable, with care | ha |", "|---|---|"]
    L += [f"| {k} | {v:,.0f} |" for k, v in a["flag_ha"].items()]
    L += ["", "(Layers overlap, so the rows don't add up to the total.)", "",
          "**AWS's six sites** (the county's posted master plan, traced and fitted to the roads" + (f"; {fit_note}" if fit_note else "") + ")", "",
          "| Site | Buildings | Drawn development | Its middle (km east, north of the old plant) |", "|---|---|---|---|"]
    L += [f"| {k} | {s['n']} | {s['acres']:,.0f} acres | {s['centre'][0] / 1000:.1f}, {s['centre'][1] / 1000:.1f} |" for k, s in sites.items()]
    L += [f"| **All six** | **{sum(s['n'] for s in sites.values())}** | **{sum(s['acres'] for s in sites.values()):,.0f} acres** | |", "",
          "**Land homes could go on near each site** (ha with no constraint; of it, flatter than 15% and over old mines)", "",
          "| Site | 0-300 m | 300-700 m | 700-1,500 m |", "|---|---|---|---|"]
    for k, rows in a["near"].items():
        L.append(f"| {k} | " + " | ".join(f"{r['buildable_ha']:.0f} ({r['flat_ha']:.0f} flat, {r['undermined_ha']:.0f} undermined)" for r in rows) + " |")
    return "\n".join(L)
