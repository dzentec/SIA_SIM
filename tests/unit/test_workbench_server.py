"""Unit tests for Workbench HTTP server and API endpoints."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from urllib.request import Request, urlopen

import pytest

from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios.sim005 import get_sim005_scenario
from sia_sim.workbench.server import WorkbenchServer, format_run_payload


def test_format_run_payload() -> None:
    """Verifies that format_run_payload creates valid JSON-serializable structured data."""
    scenario = get_sim005_scenario(seed=42)
    # Fast short run for test
    short_scenario = scenario.model_copy(update={"duration_ms": 500})
    runner = SimulationRunner()
    result = runner.run(short_scenario)

    payload = format_run_payload(result)
    assert payload["scenario_id"] == "SIM-005"
    assert payload["seed"] == 42
    assert payload["total_ticks"] == 50
    assert len(payload["ticks"]) == 50

    first_tick = payload["ticks"][0]
    assert "ground_truth" in first_tick
    assert "sensor_frame" in first_tick
    assert "sia_decision" in first_tick
    assert "oracle" in first_tick
    assert "safety_margin_pct" in first_tick["oracle"]

    # Verify JSON serializability
    serialized = json.dumps(payload)
    assert len(serialized) > 0


@pytest.fixture(scope="module")
def workbench_server() -> Iterator[None]:
    """Spins up WorkbenchServer on a test port in a background thread."""
    server = WorkbenchServer(host="127.0.0.1", port=8099)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield
    server.shutdown()


def test_get_scenarios_endpoint(workbench_server: None) -> None:
    """Verifies /api/scenarios endpoint returns available presets."""
    url = "http://127.0.0.1:8099/api/scenarios"
    with urlopen(url) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert "scenarios" in data
        ids = [s["id"] for s in data["scenarios"]]
        assert "sim005" in ids
        assert "benign" in ids


def test_run_simulation_endpoint(workbench_server: None) -> None:
    """Verifies /api/run executes simulation and returns complete trajectory."""
    url = "http://127.0.0.1:8099/api/run"
    req_body = json.dumps({"scenario": "sim005", "seed": 42}).encode("utf-8")
    req = Request(url, data=req_body, headers={"Content-Type": "application/json"}, method="POST")

    with urlopen(req) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data["scenario_id"] == "SIM-005"
        assert data["total_ticks"] == 2000
        assert data["evaluation"]["verdict"] == "PASS"


def test_query_action_endpoint(workbench_server: None) -> None:
    """Verifies /api/query-action processes skipper context updates."""
    url = "http://127.0.0.1:8099/api/query-action"
    req_body = json.dumps(
        {
            "sail_set": "REEF_1",
            "sim_time_ms": 12000,
            "heel_deg": 22.5,
        }
    ).encode("utf-8")
    req = Request(url, data=req_body, headers={"Content-Type": "application/json"}, method="POST")

    with urlopen(req) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data["status"] == "recalculated"
        assert data["sail_set"] == "REEF_1"
        assert len(data["candidates"]) > 0


def test_run_simulation_with_custom_events_and_duration(workbench_server: None) -> None:
    """Verifies /api/run supports custom duration, custom events, and new telemetry fields."""
    url = "http://127.0.0.1:8099/api/run"
    custom_events = [
        {
            "event_id": "EVT-CUSTOM-01",
            "event_type": "wind_gust",
            "sim_time_ms": 2000,
            "parameters": {"tws_kt": 25.0, "duration_ms": 3000},
        },
        {
            "event_id": "EVT-CUSTOM-02",
            "event_type": "wave_impact",
            "sim_time_ms": 4000,
            "parameters": {"impact_force_n": 16000.0, "duration_ms": 1500},
        },
    ]
    req_body = json.dumps(
        {
            "scenario": "sim005",
            "seed": 42,
            "duration_ms": 8000,
            "events": custom_events,
        }
    ).encode("utf-8")
    req = Request(url, data=req_body, headers={"Content-Type": "application/json"}, method="POST")

    with urlopen(req) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data["duration_ms"] == 8000
        assert data["total_ticks"] == 800
        assert len(data["ticks"]) == 800

        # Check telemetry fields on a sample tick
        sample_tick = data["ticks"][450]  # T=4500ms (during wave slam)
        assert "pitch_deg" in sample_tick["ground_truth"]
        assert "heave_m" in sample_tick["ground_truth"]
        assert "slam_force_kn" in sample_tick["ground_truth"]
        assert "accel_z_m_s2" in sample_tick["sensor_frame"]["imu"]
        assert "pitch_deg" in sample_tick["sensor_frame"]["imu"]
        assert "pitch_rate_deg_s" in sample_tick["sensor_frame"]["imu"]
        assert sample_tick["ground_truth"]["slam_force_kn"] > 0
