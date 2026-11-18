"""Pass 4b: which township and school district each of AWS's buildings stands in, and so where its
property tax goes.

AWS's campus straddles the line between Center Township (Homer-Center School District) and Black
Lick Township (the Blairsville-Saltsburg School District, renamed River Valley). Pass 4 taxed the
whole campus at Center Township's rates; this splits it.

- **The lines:** the Census Bureau's TIGERweb county subdivisions (layer 22) and unified school
  districts (layer 14) over the land box, cached in data/raw/land/tiger_*.geojson.
- **The buildings:** each site's drawn building pixels on the county's master plan, fitted to the
  ground (`land.aws_sites`), and its share of the filing's 39 buildings (`land.site_counts`). A
  site's buildings are split by where its building pixels fall.
- Writes data/aws_buildings_districts.csv (site, township, school district, buildings).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import DATA_DIR, RAW_DIR

TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/"
LAYERS = {"townships": 22, "school_districts": 14}
CSV = DATA_DIR / "aws_buildings_districts.csv"


def polygons(kind: str, p: dict, refresh: bool = False) -> list[tuple[str, object]]:
    """The named polygons (lon/lat) of one TIGERweb layer over the land box."""
    from shapely.geometry import shape

    path = RAW_DIR / "land" / f"tiger_{kind}.geojson"
    if refresh or not path.exists():
        import requests

        b = "land.box."
        env = f"{p[b + 'west']},{p[b + 'south']},{p[b + 'east']},{p[b + 'north']}"
        r = requests.get(TIGER + f"{LAYERS[kind]}/query", headers={"User-Agent": "brownfield-compute (public research)"}, timeout=300,
                         params={"geometry": env, "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": 4326,
                                 "spatialRel": "esriSpatialRelIntersects", "outFields": "NAME,GEOID", "returnGeometry": "true",
                                 "f": "geojson"})
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(r.text, encoding="utf-8")
    g = json.loads(path.read_text(encoding="utf-8"))
    return [(f["properties"]["NAME"], shape(f["geometry"])) for f in g["features"]]


def assign(lon: np.ndarray, lat: np.ndarray, polys: list[tuple[str, object]]) -> np.ndarray:
    """The name of the polygon each point falls in ("" if none)."""
    from shapely import points

    pts = points(np.asarray(lon, float), np.asarray(lat, float))
    out = np.full(len(pts), "", dtype=object)
    for name, poly in polys:
        from shapely import contains

        out[contains(poly, pts) & (out == "")] = name
    return out


def split(sites: dict, towns: list, schools: list, to_ll) -> pd.DataFrame:
    """Each site's buildings (`n`) shared by where its building pixels fall: one row per site,
    township and school district."""
    rows = []
    for site, s in sites.items():
        xy = s["building_xy"]
        lon, lat = to_ll(xy[:, 0], xy[:, 1])
        t, d = assign(lon, lat, towns), assign(lon, lat, schools)
        df = pd.DataFrame({"township": t, "school_district": d})
        share = df.value_counts(normalize=True)
        for (tw, sd), v in share.items():
            rows.append({"site": site, "township": tw, "school_district": sd, "pixel_share": float(v), "buildings": s["n"] * float(v)})
    return pd.DataFrame(rows)


def buildings(p: dict, refresh: bool = False) -> pd.DataFrame:
    """AWS's 39 buildings by site, township and school district (cached in data/)."""
    if CSV.exists() and not refresh:
        return pd.read_csv(CSV, comment="#")
    from . import land
    from .homes import Local

    sites = land.aws_sites(p)
    land.site_counts(p, sites)
    loc = Local(*land.PLANT)
    to_ll = lambda x, y: (loc.lon0 + np.asarray(x) / loc.kx, loc.lat0 + np.asarray(y) / 111_320.0)  # noqa: E731
    df = split(sites, polygons("townships", p, refresh), polygons("school_districts", p, refresh), to_ll)
    head = ("# AWS's 39 buildings by site, township and school district. The buildings: the county's posted master plan\n"
            "# (Kimley-Horn sheet C050.00), each site's drawn building pixels fitted to the ground (land.aws_sites), its share of\n"
            "# the filing's 39 by drawn area. The lines: Census TIGERweb county subdivisions and unified school districts.\n")
    CSV.write_text(head + df.round(4).to_csv(index=False), encoding="utf-8", newline="")
    return df


def shares(p: dict) -> dict[str, dict[str, float]]:
    """The campus's share of buildings by township and by school district."""
    df = buildings(p)
    tot = df.buildings.sum()
    return {"township": (df.groupby("township").buildings.sum() / tot).to_dict(),
            "school_district": (df.groupby("school_district").buildings.sum() / tot).to_dict(),
            "pair": (df.groupby(["township", "school_district"]).buildings.sum() / tot).to_dict()}
