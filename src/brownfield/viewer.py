"""Pass 3f (D27): a local 3D viewer for the bid set's IFC (`brownfield viewer`).

The page (tools/viewer/index.html) loads That Open's web-ifc, which parses the IFC in the browser
(WebAssembly), and three.js, which draws it. It opens the bid set and Addendum 1 from
docs/pass3/bidset/, or any IFC file the viewer picks. Click a window or door to see what the
model says about it and what a quote still needs.

Both libraries are pinned in tools/viewer/package-lock.json and installed into its node_modules
(gitignored) with the Node the `webifc` dependency group brings, install scripts off; Node is
needed only to install. The server listens on 127.0.0.1 only, binds its port exclusively, and
serves four places, nothing else:
- `/` the page (tools/viewer);
- `/vendor/web-ifc/` and `/vendor/three/` the two installed packages;
- `/models/` the published bid set (docs/pass3/bidset).

A request's path is checked as text before anything touches the filesystem: no backslashes,
colons, NUL bytes, `..` or Windows device names. On Windows, a path naming a network share would
otherwise make the machine connect out to that host.
"""

from __future__ import annotations

import functools
import http.server
import json
import posixpath
import socket
import sys
import urllib.parse
from pathlib import Path

from . import OUT_DIR

ROOT = OUT_DIR.parent
VIEWER = ROOT / "tools" / "viewer"
MODELS = ROOT / "docs" / "pass3" / "bidset"
ROUTES = [  # URL prefix -> directory; anything else comes from the page's own folder
    ("/vendor/web-ifc/", VIEWER / "node_modules" / "web-ifc"),
    ("/vendor/three/", VIEWER / "node_modules" / "three"),
    ("/models/", MODELS),
]
PACKAGES = ("web-ifc", "three")
TYPES = {".wasm": "application/wasm", ".js": "text/javascript", ".mjs": "text/javascript", ".ifc": "application/octet-stream"}
DEVICES = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)), *(f"lpt{i}" for i in range(10))}


def resolve(url_path: str) -> Path | None:
    """The file a URL path names, or None if it isn't one this server serves."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(url_path).path)
    # As text first: nothing that could become a drive, a network path or a device.
    if any(c in path for c in ("\\", ":", "\x00")) or ".." in path.split("/"):
        return None
    norm = posixpath.normpath(path)
    segments = [s for s in norm.split("/") if s]
    if any(s.split(".")[0].lower() in DEVICES or s.endswith((" ", ".")) for s in segments):
        return None
    base, rest = None, norm
    for prefix, root in ROUTES:
        if (norm + "/").startswith(prefix):
            base, rest = root, norm[len(prefix.rstrip("/")):]
            break
    if base is None:  # outside the routes: the page itself, nothing else in its folder
        return (VIEWER / "index.html").resolve() if norm in ("/", "/index.html") else None
    try:
        target = (base / rest.lstrip("/")).resolve()
        if not target.is_relative_to(base.resolve()):
            return None
        return target / "index.html" if target.is_dir() else target
    except (OSError, ValueError):
        return None


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **TYPES}

    def translate_path(self, path):
        target = resolve(path)
        return str(target) if target is not None else str(VIEWER / "__not_served__")

    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):  # quiet: only errors
        if len(args) > 1 and str(args[1]).startswith(("4", "5")):
            super().log_message(format, *args)


class Server(http.server.ThreadingHTTPServer):
    """Binds its port alone: a second server on the same port fails instead of sharing it
    (Windows lets two sockets share a port when SO_REUSEADDR is set)."""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(port: int) -> Server:
    return Server(("127.0.0.1", port), functools.partial(Handler, directory=str(VIEWER)))


def locked(pkg: str) -> str | None:
    lock = VIEWER / "package-lock.json"
    if not lock.exists():
        return None
    return json.loads(lock.read_text(encoding="utf-8"))["packages"].get(f"node_modules/{pkg}", {}).get("version")


def installed(pkg: str) -> str | None:
    p = VIEWER / "node_modules" / pkg / "package.json"
    return json.loads(p.read_text(encoding="utf-8"))["version"] if p.exists() else None


def status() -> tuple[str, str]:
    """('ok', ''), ('install', why) when the packages are missing or not the lock's versions, or
    ('missing', why) when something an install can't fix is missing."""
    for f in ("apartment.ifc", "apartment-addendum-1.ifc"):
        if not (MODELS / f).exists():
            return "missing", f"no docs/pass3/bidset/{f}: run `uv run brownfield pdfset --publish`"
    for pkg in PACKAGES:
        have, want = installed(pkg), locked(pkg)
        if have is None or have != want:
            return "install", f"{pkg} {have or 'is not installed'}, and the lock pins {want}"
    return "ok", ""


def setup() -> int:
    """Install the two packages from tools/viewer's lock file (npm ci, install scripts off)."""
    from . import bidset

    node = bidset._node_wheel()
    if node is None:
        print("no Node to install with: install the `webifc` dependency group (`uv sync --group webifc`), "
              "or run `npm ci --ignore-scripts` in tools/viewer yourself")
        return 1
    return node.npm(["ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=str(VIEWER))


def serve(port: int = 8765) -> int:
    try:
        server = make_server(port)
    except OSError as e:
        print(f"FAIL port {port} is in use on 127.0.0.1 ({e.strerror or e}): stop what's using it, or pass --port")
        return 1
    print(f"IFC viewer at http://127.0.0.1:{port}/  (this computer only; Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
