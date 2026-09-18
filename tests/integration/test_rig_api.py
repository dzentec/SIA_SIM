"""Integration tests for Phase 12 Rig Control API & Preset Interlock Orchestrator."""

import json
import threading
from collections.abc import Iterator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from sia_sim.web.server import global_rig_controller
from sia_sim.workbench.server import WorkbenchServer


@pytest.fixture(scope="module")
def workbench_server() -> Iterator[str]:
    """Spins up WorkbenchServer on a test port in a background thread."""
    port = 8199
    server = WorkbenchServer(host="127.0.0.1", port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture(autouse=True)
def reset_rig_controller() -> None:
    # Reset controller state before each test
    global_rig_controller.rig_system.winches["mainsheet"].actual_trim = 0.60
    global_rig_controller.rig_system.winches["mainsheet"].target_trim = 0.60
    global_rig_controller.rig_system.winches["mainsheet"].clamped = True
    global_rig_controller.rig_system.reef_level = 0


def test_get_rig_telemetry(workbench_server: str) -> None:
    """GET /api/v1/telemetry/rig returns valid RigState telemetry."""
    url = f"{workbench_server}/api/v1/telemetry/rig"
    with urlopen(url) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert "ropes" in data
        assert "traveler" in data
        assert "furler" in data
        assert "sails" in data
        assert "mainsheet" in data["ropes"]
        assert "jib_sheet_port" in data["ropes"]


def test_post_rig_controls_roundtrip(workbench_server: str) -> None:
    """POST /api/v1/controls/rig updates target_trim and clamped states."""
    url = f"{workbench_server}/api/v1/controls/rig"
    payload = {
        "timestamp_ms": 1726690000000,
        "controls": [
            {"rope_id": "mainsheet", "target_trim": 0.80, "clamped": False},
            {"rope_id": "traveler", "target_pos": -0.35, "clamped": False},
        ],
    }
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urlopen(req) as response:
        assert response.status == 200
        res_data = json.loads(response.read().decode("utf-8"))
        assert res_data["status"] == "APPLIED"
        assert res_data["applied_ropes"] == 1
        assert res_data["applied_traveler"] == 1

    # Verify updated target in telemetry
    t_url = f"{workbench_server}/api/v1/telemetry/rig"
    with urlopen(t_url) as t_resp:
        assert t_resp.status == 200
        t_data = json.loads(t_resp.read().decode("utf-8"))
        assert t_data["ropes"]["mainsheet"]["target_trim"] == 0.80
        assert t_data["ropes"]["mainsheet"]["clamped"] is False
        assert t_data["traveler"]["target_pos"] == -0.35
        assert t_data["traveler"]["clamped"] is False


def test_post_rig_controls_invalid_rope_id(workbench_server: str) -> None:
    """POST /api/v1/controls/rig returns 400 on unrecognized rope_id."""
    url = f"{workbench_server}/api/v1/controls/rig"
    payload = {
        "timestamp_ms": 1726690000000,
        "controls": [{"rope_id": "unknown_rope_xyz", "target_trim": 0.5, "clamped": True}],
    }
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert err_body["error"] == "INVALID_ROPE_ID"


def test_post_rig_controls_invalid_range(workbench_server: str) -> None:
    """POST /api/v1/controls/rig returns 400 on out-of-range trim."""
    url = f"{workbench_server}/api/v1/controls/rig"
    payload = {
        "timestamp_ms": 1726690000000,
        "controls": [{"rope_id": "mainsheet", "target_trim": 1.5, "clamped": True}],
    }
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    assert exc_info.value.code == 400
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert err_body["error"] == "INVALID_RANGE"


def test_preset_reef_interlock_rejected_when_sheeted_tight(workbench_server: str) -> None:
    """Preset REEF_1 is rejected with 409 Conflict if mainsheet is not eased."""
    global_rig_controller.rig_system.winches["mainsheet"].actual_trim = 0.60

    url = f"{workbench_server}/api/v1/controls/preset"
    payload = {"timestamp_ms": 1726690000100, "preset": "REEF_1"}
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with pytest.raises(HTTPError) as exc_info:
        urlopen(req)
    assert exc_info.value.code == 409
    err_body = json.loads(exc_info.value.read().decode("utf-8"))
    assert err_body["status"] == "REJECTED"
    assert err_body["reason"] == "MAINSHEET_NOT_EASED"


def test_preset_reef_accepted_when_mainsheet_eased(workbench_server: str) -> None:
    """Preset REEF_1 is accepted when mainsheet is eased below 0.35."""
    global_rig_controller.rig_system.winches["mainsheet"].actual_trim = 0.25

    url = f"{workbench_server}/api/v1/controls/preset"
    payload = {"timestamp_ms": 1726690000100, "preset": "REEF_1"}
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urlopen(req) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data["status"] == "ACCEPTED"
        assert data["reef_level"] == 1
        assert data["expected_area_ratio"] == 0.75
        assert "mainsheet_eased" in data["interlocks"]


def test_preset_full_main_unreef(workbench_server: str) -> None:
    """Preset FULL_MAIN shakes out reef back to full area."""
    global_rig_controller.rig_system.winches["mainsheet"].actual_trim = 0.20
    global_rig_controller.rig_system.reef_level = 1

    url = f"{workbench_server}/api/v1/controls/preset"
    payload = {"timestamp_ms": 1726690000200, "preset": "FULL_MAIN"}
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urlopen(req) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data["status"] == "ACCEPTED"
        assert data["reef_level"] == 0
        assert data["expected_area_ratio"] == 1.0
