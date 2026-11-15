"""HTTP for public data services, with an on-disk cache (the home-search pipeline's pattern).

Each distinct request is cached as a JSON file in .cache/http/, so a re-run asks each service
each question once per `ttl_days` at most.
"""

from __future__ import annotations

import hashlib
import json
import time

import requests

from . import ROOT

CACHE_DIR = ROOT / ".cache" / "http"
USER_AGENT = "brownfield-compute site screen (open research)"

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def fetch_json(url, params=None, ttl_days=90, timeout=120, retries=4):
    key = json.dumps([url, params], sort_keys=True)
    path = CACHE_DIR / f"{hashlib.sha256(key.encode()).hexdigest()[:32]}.json"
    if path.exists() and time.time() - path.stat().st_mtime < ttl_days * 86400:
        return json.loads(path.read_text(encoding="utf-8"))
    for attempt in range(retries):
        try:
            resp = _session.get(url, params=params, timeout=timeout)
            if 400 <= resp.status_code < 500:
                raise RuntimeError(f"{url}: HTTP {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
            data = resp.json()
            break
        except (requests.RequestException, ValueError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)
    if isinstance(data, dict) and "error" in data:  # ArcGIS reports errors inside HTTP 200
        raise RuntimeError(f"{url}: {data['error']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data
