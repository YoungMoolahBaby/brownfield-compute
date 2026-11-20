"""Pass 3f (D27): the local IFC viewer's server (`brownfield viewer`)."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from brownfield import viewer


def test_routes_and_nothing_outside_them():
    assert viewer.resolve("/") == (viewer.VIEWER / "index.html").resolve()
    assert viewer.resolve("/models/apartment.ifc") == (viewer.MODELS / "apartment.ifc").resolve()
    assert viewer.resolve("/vendor/web-ifc/web-ifc.wasm") == (viewer.VIEWER / "node_modules/web-ifc/web-ifc.wasm").resolve()
    refused = [
        "/models/../../../pyproject.toml", "/vendor/three/../../../../README.md",
        "/models/%2e%2e/%2e%2e/%2e%2e/README.md", "/../../README.md", "/models/%2e%2e/x",
        "/%5c%5chost%5cshare%5cx", "/models/%5c%5chost%5cshare",  # a Windows network path
        "/c:/windows/win.ini", "/models/C:%5cWindows",  # a drive
        "/NUL", "/models/NUL", "/CON.txt", "/vendor/three/com1",  # Windows devices
        "/index.html%00", "/models/apartment.ifc.", "/models/apartment.ifc%20",
        "/node_modules/three/package.json", "/package.json", "/package-lock.json",  # the page's folder: only the page
    ]
    for sneaky in refused:
        assert viewer.resolve(sneaky) is None, sneaky


def test_the_viewer_and_the_checks_pin_the_same_web_ifc():
    def locked(folder):
        lock = json.loads((viewer.ROOT / "tools" / folder / "package-lock.json").read_text(encoding="utf-8"))
        return lock["packages"]["node_modules/web-ifc"]["version"]

    assert locked("viewer") == locked("webifc")


def test_a_package_older_than_the_lock_means_install(monkeypatch):
    monkeypatch.setattr(viewer, "installed", lambda pkg: "0.0.1")
    assert viewer.status()[0] in ("install", "missing")
    monkeypatch.setattr(viewer, "installed", lambda pkg: None)
    assert viewer.status()[0] in ("install", "missing")


READY = viewer.status()


@pytest.mark.skipif(READY[0] != "ok", reason=f"viewer not ready: {READY[1]}")
def test_the_server_serves_the_model_and_refuses_the_rest():
    server = viewer.make_server(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"

    def get(path):
        try:
            with urllib.request.urlopen(base + path) as r:
                return r.status, r.headers.get("Content-Type"), r.read()
        except urllib.error.HTTPError as e:
            return e.code, None, b""

    try:
        status, kind, body = get("/models/apartment.ifc")
        assert status == 200 and body.startswith(b"ISO-10303-21;")
        assert get("/vendor/web-ifc/web-ifc.wasm")[:2] == (200, "application/wasm")
        assert get("/")[0] == 200
        for path in ("/models/", "/models/%2e%2e/%2e%2e/%2e%2e/README.md", "/NUL", "/index.html%00", "/%5c%5chost%5cshare%5cx"):
            assert get(path)[0] == 404, path
        with pytest.raises(OSError):  # the port is this server's alone
            viewer.make_server(port)
    finally:
        server.shutdown()
        server.server_close()
