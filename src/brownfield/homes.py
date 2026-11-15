"""Pass 2: the homes around the Homer City campus, from Indiana County's parcels (PASDA, Nov 2023).

The campus is the land of the plant's owner (Homer City Generation LP) near the plant; AWS's ~2,200
acres are part of it, and their six sites' boundaries aren't published. Homes are parcels with a
dwelling type (detached, manufactured, duplex, modular, multi-family). Distances run from each home
parcel's centroid to the campus edge, so they are the shortest a sound path could be: equipment
sits inside the sites, further away.
"""

from __future__ import annotations

import math

from shapely.geometry import Point, shape
from shapely.ops import unary_union

from .http import fetch_json

PARCELS = "https://mapservices.pasda.psu.edu/server/rest/services/pasda/IndianaCounty/MapServer/5/query"
OWNER = "HOMER CITY GENERATION%"
DWELLINGS = {"DETACH", "MANUF", "DUPDBL", "MODULR", "MULTI", "DUPHLF"}
BOX = (-79.27, 40.46, -79.12, 40.57)  # lon/lat box around the plant, ~13 x 12 km


def _geojson(where: str, fields: str, box=None, offset: int = 0) -> list[dict]:
    params = {"where": where, "outFields": fields, "returnGeometry": "true", "outSR": 4326, "f": "geojson",
              "orderByFields": "OBJECTID", "resultOffset": offset, "resultRecordCount": 1000,
              "maxAllowableOffset": 0.00002}
    if box:
        params |= {"geometry": ",".join(map(str, box)), "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                   "spatialRel": "esriSpatialRelIntersects"}
    return fetch_json(PARCELS, params=params, ttl_days=365, timeout=180).get("features", [])


def _all(where: str, fields: str, box=None) -> list[dict]:
    out, off = [], 0
    while True:
        page = _geojson(where, fields, box, off)
        out += page
        if len(page) < 1000:
            return out
        off += 1000


class Local:
    """Metres east and north of a point (equirectangular; fine over ~20 km)."""

    def __init__(self, lat0: float, lon0: float):
        self.lat0, self.lon0 = lat0, lon0
        self.kx = 111_320.0 * math.cos(math.radians(lat0))

    def xy(self, lon: float, lat: float) -> tuple[float, float]:
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * 111_320.0

    def geom(self, g):
        from shapely.ops import transform

        return transform(lambda x, y, z=None: ((x - self.lon0) * self.kx, (y - self.lat0) * 111_320.0), g)


def campus_and_homes(plant_lat: float, plant_lon: float, campus_radius_m: float = 6000.0, strip_m: float = 50.0):
    """(campus polygon in local metres, its acres, list of (home x, y, dwelling type, distance m))."""
    loc = Local(plant_lat, plant_lon)
    owned = [loc.geom(shape(f["geometry"])) for f in _all(f"LAST_NAME LIKE '{OWNER}'", "LAST_NAME,GIS_ACRES")]
    near = [g for g in owned if g.distance(Point(0, 0)) <= campus_radius_m]  # leaves out far-off reservoir land
    campus = unary_union([g.buffer(0) for g in near])
    # Drop strips narrower than 2 x strip_m (rail spurs, conveyor and line corridors): nothing that
    # makes noise will stand on them, and they would put whole streets "next to the campus".
    campus = campus.buffer(-strip_m).buffer(strip_m)
    homes = []
    for f in _all("1=1", "OBJECTID,DWELLING_T,LAST_NAME", BOX):
        kind = (f["properties"].get("DWELLING_T") or "").strip()
        if kind not in DWELLINGS:
            continue
        c = loc.geom(shape(f["geometry"])).centroid
        if campus.contains(c):
            continue  # a house on the owner's own land
        homes.append((c.x, c.y, kind, campus.exterior.distance(c) if campus.geom_type == "Polygon" else campus.distance(c)))
    return campus, campus.area / 4046.86, homes


def bands(homes, edges=(300, 500, 700, 1000, 1500, 2000, 3000)) -> list[tuple[int, int]]:
    """Homes within each distance of the campus edge."""
    return [(e, sum(1 for h in homes if h[3] <= e)) for e in edges]
