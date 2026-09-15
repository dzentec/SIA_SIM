"""FastAPI and WebSocket Server for SIA Simulation Workbench.

Streams 100 Hz simulation data (GroundTruthFrame, SensorFrame, DecisionPayload)
to the web cockpit in real-time.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

from sia_sim.contracts.data import GroundTruthFrame
from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig
from sia_sim.physics.dynamics import VesselDynamics
from sia_sim.physics.world import WorldModel
from sia_sim.sensors.pipeline import SensorPipeline
from sia_sim.sia.mock_sia import MockSIA

logger = logging.getLogger("sia_sim.web")
logging.basicConfig(level=logging.INFO)

# Path to the HTML interface
HTML_PATH = Path(__file__).parents[3] / ".planning" / "sketches" / "sia-simulation-workbench" / "index.html"

app = FastAPI(title="SIA Simulation Workbench API")

MS_TO_KT = 1.943844


def get_default_scenario(scenario_id: str = "SIM-005") -> Scenario:
    """Builds reference scenario configurations."""
    if scenario_id == "SIM-006":
        return Scenario(
            scenario_id="SIM-006",
            scenario_version="1.0.0",
            name="Squall Knockdown Scenario",
            description="Close-hauled squall load with sudden heel spike",
            duration_ms=30000,
            seed=42,
            vessel=VesselConfig(
                vessel_type="monohull_cruiser",
                loa_m=12.0,
                beam_m=3.8,
                displacement_kg=6500.0,
                initial_heel_deg=18.0,
                initial_heading_deg=45.0,
                initial_sog_kt=6.5,
            ),
            events=(
                ScenarioEvent(
                    sim_time_ms=1800,
                    event_id="SQUALL_01",
                    event_type="wind_gust",
                    parameters={"tws_kt": 18.0, "duration_s": 5.5, "direction_shift_deg": 15.0},
                ),
            ),
            initial_tws_kt=22.0,
            initial_twa_deg=45.0,
            initial_wave_height_m=3.5,
            initial_wave_period_s=5.2,
        )
    elif scenario_id == "SIM-007":
        return Scenario(
            scenario_id="SIM-007",
            scenario_version="1.0.0",
            name="IMU Sensor Loss Scenario",
            description="Heavy sea state with sensor dropout",
            duration_ms=30000,
            seed=42,
            vessel=VesselConfig(
                vessel_type="monohull_performance",
                loa_m=11.0,
                beam_m=3.5,
                displacement_kg=5000.0,
                initial_heel_deg=15.0,
                initial_heading_deg=270.0,
                initial_sog_kt=7.0,
            ),
            events=(
                ScenarioEvent(
                    sim_time_ms=4000,
                    event_id="FAULT_IMU",
                    event_type="sensor_fault",
                    parameters={"fault_type": "dropout", "duration_ms": 4000},
                ),
            ),
            initial_tws_kt=25.0,
            initial_twa_deg=120.0,
            initial_wave_height_m=3.0,
            initial_wave_period_s=6.0,
        )
    else:  # SIM-005 default
        return Scenario(
            scenario_id="SIM-005",
            scenario_version="1.0.0",
            name="Broach Precursor Golden Scenario",
            description="IOR narrow stern monohull broach precursor dynamics (100 Hz)",
            duration_ms=15000,
            seed=42,
            vessel=VesselConfig(
                vessel_type="monohull_ior",
                loa_m=10.5,
                beam_m=3.2,
                displacement_kg=4500.0,
                initial_heel_deg=12.0,
                initial_heading_deg=65.0,
                initial_sog_kt=7.8,
            ),
            events=(
                ScenarioEvent(
                    sim_time_ms=2500,
                    event_id="GUST_01",
                    event_type="wind_gust",
                    parameters={"tws_kt": 14.0, "duration_s": 4.5, "direction_shift_deg": 10.0},
                ),
                ScenarioEvent(
                    sim_time_ms=4000,
                    event_id="WAVE_01",
                    event_type="wave_impact",
                    parameters={
                        "impact_force_n": 12000.0,
                        "impact_roll_moment_nm": 22000.0,
                        "duration_ms": 3300,
                    },
                ),
            ),
            initial_tws_kt=18.0,
            initial_twa_deg=135.0,
            initial_wave_height_m=2.8,
            initial_wave_period_s=6.5,
        )


class SimulationRunner:
    """Manages active simulation instance and deterministic state stepping."""

    def __init__(self, scenario_id: str = "SIM-005") -> None:
        self.scenario_id = scenario_id
        self.scenario = get_default_scenario(scenario_id)
        self.world = WorldModel.from_scenario(self.scenario)
        self.world.apply_events(self.scenario.events)
        self.dynamics = VesselDynamics.from_config(self.scenario.vessel)
        self.sensor_pipeline = SensorPipeline(master_seed=self.scenario.seed)
        self.sia = MockSIA()

        self.sim_time_ms = 0
        self.sequence_number = 0
        self.is_playing = False
        self.sim_speed = 1.0
        self.rudder_deg = 0.0
        self.mainsheet_pct = 100.0
        self.total_duration_ms = self.scenario.duration_ms

    def reset(self) -> None:
        """Resets the simulation to t=0."""
        self.scenario = get_default_scenario(self.scenario_id)
        self.scenario = self.scenario.model_copy(update={"duration_ms": self.total_duration_ms})
        self.world = WorldModel.from_scenario(self.scenario)
        self.world.apply_events(self.scenario.events)
        self.dynamics = VesselDynamics.from_config(self.scenario.vessel)
        self.sensor_pipeline.reset()
        self.sia.reset()
        self.sim_time_ms = 0
        self.sequence_number = 0
        self.rudder_deg = 0.0
        self.mainsheet_pct = 100.0

    def step(self) -> Dict[str, Any]:
        """Advances simulation by one 10 ms (100 Hz) tick."""
        dt_s = 0.01
        env = self.world.step(self.sim_time_ms)
        wave_f, wave_rm, wave_ym = self.world.wave.evaluate_impact(self.sim_time_ms)

        # 1. Physics Step -> VesselState
        vessel_state = self.dynamics.step(
            dt_s=dt_s,
            env=env,
            rudder_deg=self.rudder_deg,
            mainsheet_pct=self.mainsheet_pct,
            wave_impact_force_n=wave_f,
            wave_impact_roll_moment_nm=wave_rm,
            wave_impact_yaw_moment_nm=wave_ym,
        )

        # 2. Construct GroundTruthFrame
        gt_frame = GroundTruthFrame(
            sim_time_ms=self.sim_time_ms,
            vessel=vessel_state,
            environment=env,
            sequence_number=self.sequence_number,
            active_event_ids=(),
        )

        # 3. Sensor Degradation Pipeline -> SensorFrame
        sensor_frame = self.sensor_pipeline.process(gt_frame)

        # 4. SIA Decision Layer -> DecisionPayload
        decision = self.sia.process(sensor_frame)

        # Update and increment clock
        current_time_ms = self.sim_time_ms
        self.sim_time_ms += 10
        self.sequence_number += 1
        if self.sim_time_ms > self.total_duration_ms:
            self.sim_time_ms = 0

        tws_kt = env.true_wind_speed_m_s * MS_TO_KT
        sog_kt = vessel_state.sog_m_s * MS_TO_KT

        return {
            "type": "SIM_TICK",
            "sim_time_ms": current_time_ms,
            "total_duration_ms": self.total_duration_ms,
            "is_playing": self.is_playing,
            "ground_truth": {
                "tws_kt": tws_kt,
                "twd_deg": env.true_wind_angle_deg,
                "wave_height_m": env.wave_height_m,
                "wave_period_s": env.wave_period_s,
                "heel_deg": vessel_state.heel_deg,
                "roll_rate_deg_s": vessel_state.roll_rate_deg_s,
                "pitch_deg": vessel_state.pitch_deg,
                "pitch_rate_deg_s": 0.0,
                "yaw_deg": vessel_state.heading_deg,
                "yaw_rate_deg_s": vessel_state.yaw_rate_deg_s,
                "sog_kt": sog_kt,
                "cog_deg": vessel_state.cog_deg,
                "accel_z_g": 1.0,
                "rudder_deg": vessel_state.rudder_angle_deg,
                "active_events": [],
            },
            "sensor_frame": {
                "imu": {
                    "roll_deg": sensor_frame.imu.roll_deg if sensor_frame.imu else None,
                    "roll_rate_deg_s": sensor_frame.imu.roll_rate_deg_s if sensor_frame.imu else None,
                    "pitch_deg": sensor_frame.imu.pitch_deg if sensor_frame.imu else None,
                    "pitch_rate_deg_s": sensor_frame.imu.pitch_rate_deg_s if sensor_frame.imu else None,
                    "yaw_rate_deg_s": sensor_frame.imu.yaw_rate_deg_s if sensor_frame.imu else None,
                },
                "gps": {
                    "sog_kt": sensor_frame.gps.sog_kt if sensor_frame.gps else None,
                    "cog_deg": sensor_frame.gps.cog_deg if sensor_frame.gps else None,
                    "hdop": sensor_frame.gps.hdop if sensor_frame.gps else None,
                },
                "wind": {
                    "awa_deg": sensor_frame.wind.apparent_wind_angle_deg if sensor_frame.wind else None,
                    "aws_kt": sensor_frame.wind.apparent_wind_speed_kt if sensor_frame.wind else None,
                },
                "actuators": {
                    "rudder_angle_deg": sensor_frame.actuators.rudder_angle_deg if sensor_frame.actuators else None,
                },
            },
            "decision": {
                "confidence": decision.risk_assessment.confidence,
                "risk_score": decision.risk_assessment.risk_score,
                "primary_action": decision.selected_response.action_type if decision.selected_response else None,
                "primary_score": decision.selected_response.priority_score if decision.selected_response else None,
                "target_hazard": decision.risk_assessment.hazard_id,
                "candidates_count": len(decision.candidates),
            },
        }


@app.get("/", response_class=HTMLResponse)
async def get_workbench_ui() -> str:
    """Serves the Workbench interface HTML directly."""
    if HTML_PATH.exists():
        return HTML_PATH.read_text(encoding="utf-8")
    return "<h1>Error: Workbench HTML not found</h1>"


@app.websocket("/ws/sim")
async def websocket_sim_endpoint(websocket: WebSocket) -> None:
    """WebSocket handler for high-speed simulation streaming and control."""
    await websocket.accept()
    runner = SimulationRunner()
    logger.info("Client connected to Simulation WebSocket.")

    async def send_state() -> None:
        try:
            state = runner.step()
            await websocket.send_text(json.dumps(state))
        except Exception as e:
            logger.error(f"Error sending tick: {e}")

    try:
        while True:
            try:
                msg_text = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                data = json.loads(msg_text)
                action = data.get("action")

                if action == "play":
                    runner.is_playing = True
                    runner.sim_speed = float(data.get("speed", 1.0))
                elif action == "pause":
                    runner.is_playing = False
                elif action == "reset":
                    runner.is_playing = False
                    runner.reset()
                    await send_state()
                elif action == "step":
                    runner.is_playing = False
                    await send_state()
                elif action == "set_scenario":
                    scenario_id = data.get("scenario_id", "SIM-005")
                    runner.scenario_id = scenario_id
                    runner.reset()
                    await send_state()
                elif action == "set_duration":
                    dur_ms = int(data.get("duration_ms", 15000))
                    runner.total_duration_ms = dur_ms
                    runner.reset()
                    await send_state()
                elif action == "set_speed":
                    runner.sim_speed = float(data.get("speed", 1.0))
                elif action == "user_input":
                    config = data.get("sail_config")
                    if config == "FULL MAIN":
                        runner.rudder_deg = -15.0
                    elif "REEF" in str(config):
                        runner.rudder_deg = -8.0
                    else:
                        runner.rudder_deg = 0.0

            except asyncio.TimeoutError:
                pass

            if runner.is_playing:
                delay = 0.01 / max(0.1, runner.sim_speed)
                await send_state()
                await asyncio.sleep(min(delay, 0.05))
            else:
                await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket.")


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Runs the Uvicorn web server."""
    print(f"\n=======================================================")
    print(f"  SIA Simulation Workbench Server running at:")
    print(f"  --> http://{host}:{port}/")
    print(f"=======================================================\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
