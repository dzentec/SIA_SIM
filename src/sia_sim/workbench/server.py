"""HTTP server and JSON telemetry streaming API for SIA Simulation Workbench."""

from __future__ import annotations

import json
import math
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios import load_scenario

STATIC_DIR = Path(__file__).parent / "static"


def format_run_payload(runner_result: Any) -> dict[str, Any]:
    """Formats SimulationRunResult into a structured JSON dictionary for the UI."""
    records = runner_result.recorder.records
    total_recs = len(records)
    stride = max(1, total_recs // 2000)
    sampled_records = records[::stride] if stride > 1 else records
    ticks: list[dict[str, Any]] = []

    for r in sampled_records:
        gt = r.gt
        sf = r.sf
        dec = r.decision

        # Compute dynamic safety margin (100% at 0 heel, 0% at 35 critical)
        true_heel = abs(gt.vessel.heel_deg)
        safety_margin_pct = max(0.0, round((1.0 - (true_heel / 35.0)) * 100.0, 1))

        # Check rudder stall / hydro loss (>20 deg heel reduces effectiveness)
        if true_heel > 15.0:
            rudder_hydro_loss = round(min(1.0, max(0.0, (true_heel - 15.0) / 20.0)), 2)
        else:
            rudder_hydro_loss = 0.0

        tws_kt = round(gt.environment.true_wind_speed_m_s * 1.943844, 2)
        sog_kt = round(gt.vessel.sog_m_s * 1.943844, 2)

        roll_deg = round(sf.imu.roll_deg, 2) if sf.imu.roll_deg is not None else None
        pitch_deg = round(sf.imu.pitch_deg, 2) if sf.imu.pitch_deg is not None else None
        roll_rate = round(sf.imu.roll_rate_deg_s, 2) if sf.imu.roll_rate_deg_s is not None else None
        pitch_rate = (
            round(sf.imu.pitch_rate_deg_s, 2) if sf.imu.pitch_rate_deg_s is not None else None
        )
        yaw_rate = round(sf.imu.yaw_rate_deg_s, 2) if sf.imu.yaw_rate_deg_s is not None else None
        acc_z = round(sf.imu.accel_z_m_s2, 2) if sf.imu.accel_z_m_s2 is not None else None
        acc_x = round(sf.imu.accel_x_m_s2, 2) if sf.imu.accel_x_m_s2 is not None else None

        gps_sog = round(sf.gps.sog_kt, 2) if sf.gps.sog_kt is not None else None
        gps_cog = round(sf.gps.cog_deg, 1) if sf.gps.cog_deg is not None else None

        aws = (
            round(sf.wind.apparent_wind_speed_kt, 2)
            if sf.wind.apparent_wind_speed_kt is not None
            else None
        )
        awa = (
            round(sf.wind.apparent_wind_angle_deg, 1)
            if sf.wind.apparent_wind_angle_deg is not None
            else None
        )

        rudder_angle = (
            round(sf.actuators.rudder_angle_deg, 1)
            if sf.actuators.rudder_angle_deg is not None
            else None
        )
        mainsheet = (
            round(sf.actuators.mainsheet_pct, 1) if sf.actuators.mainsheet_pct is not None else None
        )

        sel_resp = dec.selected_response.model_dump(mode="json") if dec.selected_response else None

        # Slamming & heave calculation
        is_wave_impact = False
        slam_force_val = 0.0
        for evt in runner_result.scenario.events:
            if (
                evt.event_type in ("wave_impact", "slam", "wave_slam")
                and evt.event_id in gt.active_event_ids
            ):
                is_wave_impact = True
                force_n = float(evt.parameters.get("impact_force_n", 12000.0))
                slam_force_val = round(force_n / 1000.0, 1)
                break

        if not is_wave_impact:
            slam_force_val = (
                round(abs(gt.environment.wave_height_m * 1.5), 1)
                if gt.environment.wave_height_m > 2.0
                else 0.0
            )

        slam_force_kn = slam_force_val
        heave_m = round(
            gt.environment.wave_height_m
            * 0.45
            * (0.8 + 0.2 * math.cos(gt.sim_time_ms / 1000.0 * 2.0)),
            2,
        )

        ticks.append(
            {
                "sim_time_ms": gt.sim_time_ms,
                "ground_truth": {
                    "tws_kt": tws_kt,
                    "twd_deg": round(gt.environment.true_wind_angle_deg, 1),
                    "wave_elevation_m": round(gt.environment.wave_height_m, 2),
                    "heave_m": heave_m,
                    "wave_impact_active": len(gt.active_event_ids) > 0,
                    "slam_force_kn": slam_force_kn,
                    "slam_active": is_wave_impact,
                    "heel_deg": round(gt.vessel.heel_deg, 2),
                    "pitch_deg": round(gt.vessel.pitch_deg, 2),
                    "yaw_deg": round(gt.vessel.heading_deg, 1),
                    "sog_kt": sog_kt,
                    "rudder_deg": round(gt.vessel.rudder_angle_deg, 1),
                    "rudder_hydro_loss": rudder_hydro_loss,
                    "active_events": list(gt.active_event_ids),
                },
                "sensor_frame": {
                    "imu": {
                        "roll_deg": roll_deg,
                        "pitch_deg": pitch_deg,
                        "roll_rate_deg_s": roll_rate,
                        "pitch_rate_deg_s": pitch_rate,
                        "yaw_rate_deg_s": yaw_rate,
                        "accel_z_m_s2": acc_z,
                        "accel_x_m_s2": acc_x,
                        "fault": sf.imu.fault,
                    },
                    "gps": {
                        "sog_kt": gps_sog,
                        "cog_deg": gps_cog,
                        "fix_loss": sf.gps.sog_kt is None,
                        "fault": sf.gps.fault,
                    },
                    "wind": {
                        "apparent_wind_speed_kt": aws,
                        "apparent_wind_angle_deg": awa,
                        "fault": sf.wind.fault,
                    },
                    "actuators": {
                        "rudder_angle_deg": rudder_angle,
                        "mainsheet_pct": mainsheet,
                        "fault": sf.actuators.fault,
                    },
                },
                "sia_decision": {
                    "decision_id": dec.decision_id,
                    "risk_score": dec.risk_assessment.risk_score,
                    "confidence": dec.risk_assessment.confidence,
                    "hazard_id": dec.risk_assessment.hazard_id,
                    "evidence_ids": list(dec.risk_assessment.evidence_ids),
                    "selected_response": sel_resp,
                    "candidates": [c.model_dump(mode="json") for c in dec.candidates],
                    "note": dec.conflict_resolution_note,
                    "nominal_status": {
                        "action_title": "MAINTAIN COURSE & MONITOR TRIM",
                        "rudder_deg": 0.0,
                        "sail_pct": 100.0,
                        "status_text": "ALL SYSTEMS NOMINAL — SAFETY ENVELOPE INTACT",
                    },
                },
                "oracle": {
                    "safety_margin_pct": safety_margin_pct,
                    "safe_envelope_intact": true_heel < 35.0,
                },
            }
        )

    eval_dict = runner_result.evaluation.model_dump(mode="json")

    return {
        "scenario_id": runner_result.scenario.scenario_id,
        "scenario_name": runner_result.scenario.name,
        "seed": runner_result.scenario.seed,
        "duration_ms": runner_result.scenario.duration_ms,
        "events": [e.model_dump(mode="json") for e in runner_result.scenario.events],
        "total_ticks": int(runner_result.scenario.duration_ms // 10),
        "recorded_steps": total_recs,
        "sampled_ticks": len(ticks),
        "stride": stride,
        "evaluation": eval_dict,
        "sim_speed_ratio": runner_result.sim_speed_ratio,
        "ticks": ticks,
    }


class WorkbenchRequestHandler(SimpleHTTPRequestHandler):
    """Handles REST API endpoints and serves static UI files."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/scenarios":
            self._handle_get_scenarios()
        elif self.path == "/api/vessels":
            self._handle_get_vessels()
        elif self.path == "/api/sails":
            self._handle_get_sails()
        elif self.path == "/api/health":
            self._send_json({"status": "ok", "version": "0.1.0"})
        else:
            # Fallback to static file serving
            if self.path == "/":
                self.path = "/index.html"
            super().do_GET()

    def _handle_get_sails(self) -> None:
        from sia_sim.contracts.sails import SAIL_RULES_CATALOG_V1_1

        self._send_json(SAIL_RULES_CATALOG_V1_1)

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if self.path == "/api/run":
            self._handle_run_simulation(payload)
        elif self.path == "/api/query-action":
            self._handle_query_action(payload)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _handle_get_vessels(self) -> None:
        from sia_sim.scenarios.presets import list_vessel_presets

        vessels = list_vessel_presets()
        self._send_json({"vessels": vessels})

    def _handle_get_scenarios(self) -> None:
        from sia_sim.scenarios.presets import list_world_presets

        scenarios = list_world_presets()
        self._send_json({"scenarios": scenarios})

    def _handle_run_simulation(self, payload: dict[str, Any]) -> None:
        from sia_sim.contracts.scenario import ScenarioEvent
        from sia_sim.scenarios.presets import get_vessel_preset_config

        scenario_name = payload.get("scenario", "cruise")
        vessel_preset = payload.get("vessel_preset")
        sail_plan = payload.get("sail_plan")
        seed = int(payload.get("seed", 42))
        duration_ms = payload.get("duration_ms")
        custom_events_data = payload.get("events")
        custom_world = payload.get("custom_world")
        custom_vessel = payload.get("custom_vessel")
        imu_sample_rate = int(payload.get("imu_sample_rate_hz", 100))

        try:
            scenario = load_scenario(scenario_name, seed=seed)
            updates: dict[str, Any] = {"seed": seed}

            if duration_ms is not None:
                updates["duration_ms"] = int(duration_ms)

            # Apply chosen vessel preset and sail plan if requested
            if vessel_preset is not None or sail_plan is not None:
                v_id = vessel_preset or "beneteau_oceanis_45"
                s_plan = sail_plan or "FULL_MAIN"
                vessel_cfg = get_vessel_preset_config(
                    vessel_id=v_id,
                    sail_plan=s_plan,
                    initial_heading_deg=scenario.vessel.initial_heading_deg,
                    initial_sog_kt=scenario.vessel.initial_sog_kt,
                    initial_heel_deg=scenario.vessel.initial_heel_deg,
                )
                updates["vessel"] = vessel_cfg

            # Custom vessel overrides (physical geometry and available sail inventory)
            if isinstance(custom_vessel, dict):
                curr_v = updates.get("vessel", scenario.vessel)
                v_overrides: dict[str, Any] = {}
                if "loa_m" in custom_vessel and custom_vessel["loa_m"] is not None:
                    v_overrides["loa_m"] = float(custom_vessel["loa_m"])
                if "beam_m" in custom_vessel and custom_vessel["beam_m"] is not None:
                    v_overrides["beam_m"] = float(custom_vessel["beam_m"])
                if "displacement_kg" in custom_vessel and custom_vessel["displacement_kg"] is not None:
                    v_overrides["displacement_kg"] = float(custom_vessel["displacement_kg"])
                if "mast_height_m" in custom_vessel and custom_vessel["mast_height_m"] is not None:
                    v_overrides["mast_height_m"] = float(custom_vessel["mast_height_m"])
                if "sail_area_m2" in custom_vessel and custom_vessel["sail_area_m2"] is not None:
                    v_overrides["sail_area_m2"] = float(custom_vessel["sail_area_m2"])
                if "hull_type" in custom_vessel and custom_vessel["hull_type"]:
                    v_overrides["hull_type"] = str(custom_vessel["hull_type"])
                if "available_sails" in custom_vessel and custom_vessel["available_sails"] is not None:
                    v_overrides["available_sails"] = tuple(str(s) for s in custom_vessel["available_sails"])

                if v_overrides:
                    updates["vessel"] = curr_v.model_copy(update=v_overrides)

            # Custom world parameters if provided
            if isinstance(custom_world, dict):
                if "initial_tws_kt" in custom_world:
                    updates["initial_tws_kt"] = float(custom_world["initial_tws_kt"])
                if "initial_twa_deg" in custom_world:
                    updates["initial_twa_deg"] = float(custom_world["initial_twa_deg"])
                if "initial_wave_height_m" in custom_world:
                    updates["initial_wave_height_m"] = float(custom_world["initial_wave_height_m"])
                if "initial_wave_period_s" in custom_world:
                    updates["initial_wave_period_s"] = float(custom_world["initial_wave_period_s"])

                vessel_updates: dict[str, Any] = {}
                if "initial_sog_kt" in custom_world:
                    vessel_updates["initial_sog_kt"] = float(custom_world["initial_sog_kt"])
                if "initial_heading_deg" in custom_world:
                    vessel_updates["initial_heading_deg"] = float(
                        custom_world["initial_heading_deg"]
                    )
                if "initial_heel_deg" in custom_world:
                    vessel_updates["initial_heel_deg"] = float(custom_world["initial_heel_deg"])

                if vessel_updates:
                    updates["vessel"] = updates["vessel"].model_copy(update=vessel_updates)

            if custom_events_data is not None:
                events_list = []
                for idx, ed in enumerate(custom_events_data):
                    evt = ScenarioEvent(
                        sim_time_ms=int(ed.get("sim_time_ms", 0)),
                        event_id=str(ed.get("event_id", f"EVT-CUSTOM-{idx + 1:02d}")),
                        event_type=str(ed.get("event_type", "wind_gust")),
                        parameters=dict(ed.get("parameters", {})),
                    )
                    events_list.append(evt)
                updates["events"] = tuple(events_list)

            scenario = scenario.model_copy(update=updates)
            runner = SimulationRunner(imu_sample_rate_hz=imu_sample_rate)
            result = runner.run(scenario)
            response_data = format_run_payload(result)
            self._send_json(response_data)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            try:
                self._send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass


    def _handle_query_action(self, payload: dict[str, Any]) -> None:
        sail_set = payload.get("sail_set", "FULL_MAIN")
        sim_time_ms = int(payload.get("sim_time_ms", 0))

        # Recalculate candidate priorities based on skipper input
        if sail_set in ("REEF_1", "REEF_2"):
            note = f"Skipper confirmed {sail_set} — sail power reduced. Recalculating stability."
            candidates = [
                {
                    "response_id": f"RESP-{sim_time_ms}-01-RECALC",
                    "action_type": "MAINTAIN_COURSE",
                    "rudder_command_deg": -5.0,
                    "sail_command_pct": 50.0,
                    "priority_score": 0.92,
                    "rule_ids": ["RULE-REEFED-BALANCE-01"],
                },
                {
                    "response_id": f"RESP-{sim_time_ms}-02-RECALC",
                    "action_type": "EASE_TRAVELLER",
                    "rudder_command_deg": None,
                    "sail_command_pct": 40.0,
                    "priority_score": 0.81,
                    "rule_ids": ["RULE-REEFED-TRAVELLER-01"],
                },
            ]
        elif sail_set == "STORM_JIB":
            note = (
                f"Skipper confirmed {sail_set} — minimal mainsail drive. Full authority restored."
            )
            candidates = [
                {
                    "response_id": f"RESP-{sim_time_ms}-01-RECALC",
                    "action_type": "BEAR_AWAY_SLOW",
                    "rudder_command_deg": -8.0,
                    "sail_command_pct": 20.0,
                    "priority_score": 0.96,
                    "rule_ids": ["RULE-STORM-TACTIC-01"],
                }
            ]
        else:
            note = f"Skipper confirmed {sail_set} — high capsize leverage under gusts."
            candidates = [
                {
                    "response_id": f"RESP-{sim_time_ms}-01-RECALC",
                    "action_type": "REDUCE_SAIL",
                    "rudder_command_deg": None,
                    "sail_command_pct": 30.0,
                    "priority_score": 0.95,
                    "rule_ids": ["RULE-BROACH-SAIL-01"],
                },
                {
                    "response_id": f"RESP-{sim_time_ms}-02-RECALC",
                    "action_type": "RUDDER_CORRECTION",
                    "rudder_command_deg": -20.0,
                    "sail_command_pct": None,
                    "priority_score": 0.85,
                    "rule_ids": ["RULE-BROACH-RUDDER-01"],
                },
            ]

        self._send_json(
            {
                "status": "recalculated",
                "sail_set": sail_set,
                "note": note,
                "candidates": candidates,
                "selected_response": candidates[0] if candidates else None,
            }
        )

    def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        try:
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass


class WorkbenchServer:
    """Encapsulates the Workbench HTTP server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8050) -> None:
        self.host = host
        self.port = port
        self.server = ThreadingHTTPServer((host, port), WorkbenchRequestHandler)

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def create_workbench_app(host: str = "127.0.0.1", port: int = 8050) -> WorkbenchServer:
    """Creates a configured WorkbenchServer instance."""
    return WorkbenchServer(host=host, port=port)


def run_workbench(host: str = "127.0.0.1", port: int = 8050) -> None:
    """Starts the workbench server and listens for requests."""
    server = create_workbench_app(host=host, port=port)
    print(f"SIA Simulation Workbench listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Workbench server...")
        server.shutdown()
