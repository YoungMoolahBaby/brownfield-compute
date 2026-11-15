"""FEMA flood zones around a site (National Flood Hazard Layer).

Coal plants were built on rivers for cooling water, so many sit partly in the floodplain. A
plant's EIA coordinates are one point on a site of hundreds of acres, so we take a square around
it and report the share inside the 1%-annual-chance floodplain (the Special Flood Hazard Area).
Shares are computed in degrees, which is exact for a ratio over a box this small. Where FEMA has
no digital map, the site is "unmapped", not "dry".
"""

from __future__ import annotations

import math

from shapely import make_valid
from shapely.geometry import box, shape
from shapely.ops import unary_union

from .http import fetch_json

NFHL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
ZONES = f"{NFHL}/28"
PANELS = f"{NFHL}/3"
SFHA_ZONES = {"A", "AE", "AH", "AO", "AR", "A99", "V", "VE"}


def _query(layer: str, bounds, fields: str, geometry: bool) -> list[dict]:
    xmin, ymin, xmax, ymax = bounds
    params = {
        "geometry": f"{xmin},{ymin},{xmax},{ymax}", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": fields, "returnGeometry": str(geometry).lower(),
        "outSR": 4326, "f": "geojson" if geometry else "json"}
    if geometry:
        params["maxAllowableOffset"] = 0.00005  # ~5 m: smaller responses, the share barely moves
    data = fetch_json(f"{layer}/query", params=params, ttl_days=180, timeout=180)
    return data.get("features", [])


def site(lat: float, lon: float, half_m: float) -> tuple[float, str]:
    """(SFHA share, note): note is "mapped", "unmapped" (share NaN) or "failed: ..." (share NaN)
    when FEMA's server errs, so one bad response doesn't stop the screen."""
    try:
        share = sfha_share(lat, lon, half_m)
    except Exception as e:  # noqa: BLE001 - FEMA's service fails in many ways; record and go on
        return float("nan"), f"failed: {str(e)[:80]}"
    return (float("nan"), "unmapped") if share is None else (share, "mapped")


def sfha_share(lat: float, lon: float, half_m: float) -> float | None:
    """Share of a (2 half_m) square around the point inside the SFHA; None where unmapped."""
    dlat = half_m / 111_320.0
    dlon = half_m / (111_320.0 * math.cos(math.radians(lat)))
    bounds = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
    if not _query(PANELS, bounds, "FIRM_PAN", geometry=False):
        return None
    sq = box(*bounds)
    zones = _query(ZONES, bounds, "FLD_ZONE,SFHA_TF", geometry=True)
    # Simplified polygons can self-intersect; make_valid repairs them before the union.
    wet = [make_valid(shape(f["geometry"])) for f in zones
           if f["properties"].get("SFHA_TF") == "T" or f["properties"].get("FLD_ZONE") in SFHA_ZONES]
    if not wet:
        return 0.0
    return float(unary_union(wet).intersection(sq).area / sq.area)
