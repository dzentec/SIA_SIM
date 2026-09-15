"""Integration tests for Workbench web application assets and end-to-end server flow."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from urllib.request import urlopen

import pytest

from sia_sim.workbench.server import STATIC_DIR, WorkbenchServer


def test_static_assets_exist() -> None:
    """Verifies all required static files for the 5-zone UI exist and are populated."""
    assert STATIC_DIR.is_dir()
    index_html = STATIC_DIR / "index.html"
    assert index_html.exists() and index_html.stat().st_size > 500

    css_file = STATIC_DIR / "css" / "workbench.css"
    assert css_file.exists() and css_file.stat().st_size > 500

    js_files = ["instruments.js", "timeline.js", "query_loop.js", "app.js"]
    for js_name in js_files:
        js_file = STATIC_DIR / "js" / js_name
        assert js_file.exists() and js_file.stat().st_size > 200


@pytest.fixture(scope="module")
def running_workbench() -> Iterator[str]:
    """Runs a live WorkbenchServer for HTTP integration testing."""
    host = "127.0.0.1"
    port = 8098
    server = WorkbenchServer(host=host, port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{host}:{port}"
    yield base_url
    server.shutdown()


def test_serve_static_index(running_workbench: str) -> None:
    """Verifies that GET / serves index.html with valid HTML."""
    with urlopen(f"{running_workbench}/") as response:
        assert response.status == 200
        content = response.read().decode("utf-8")
        assert "<title>SIA Simulation Workbench" in content
        assert "id=\"zoneGroundTruth\"" in content
        assert "id=\"zoneSensorView\"" in content
        assert "id=\"zoneSiaAdvisory\"" in content
        assert "id=\"zoneTimeline\"" in content
        assert "id=\"zoneQueryLoop\"" in content


def test_serve_static_js_and_css(running_workbench: str) -> None:
    """Verifies that CSS and JS bundles are served correctly with HTTP 200."""
    endpoints = [
        "/css/workbench.css",
        "/js/instruments.js",
        "/js/timeline.js",
        "/js/query_loop.js",
        "/js/app.js",
    ]
    for ep in endpoints:
        with urlopen(f"{running_workbench}{ep}") as response:
            assert response.status == 200
            content = response.read()
            assert len(content) > 100
