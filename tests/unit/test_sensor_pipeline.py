"""Integration tests for the composite SensorPipeline."""

from __future__ import annotations

from sia_sim.contracts.data import GroundTruthFrame, SensorFrame
from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig
from sia_sim.physics.dynamics import VesselDynamics
from sia_sim.physics.world import WorldModel
from sia_sim.sensors.pipeline import SensorPipeline


def create_test_scenario() -> Scenario:
    return Scenario(
        scenario_id="SIM-PIPE-001",
        scenario_version="1.0.0",
        name="Pipeline Integration Scenario",
        description="Verify end-to-end GroundTruthFrame to SensorFrame conversion",
        duration_ms=10000,
        seed=42,
        vessel=VesselConfig(
            vessel_type="monohull_ior",
            loa_m=10.5,
            beam_m=3.2,
            displacement_kg=4500.0,
            initial_heel_deg=10.0,
            initial_heading_deg=65.0,
            initial_sog_kt=5.5,
        ),
        events=(
            ScenarioEvent(
                sim_time_ms=5000,
                event_id="EVT-WIND-01",
                event_type="wind_gust",
                parameters={"tws_kt": 15.0, "duration_s": 3.0, "direction_shift_deg": 10.0},
            ),
        ),
        initial_tws_kt=20.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=2.5,
        initial_wave_period_s=6.5,
    )


class TestSensorPipelineIntegration:
    def test_continuous_frame_synthesis_at_100hz(self) -> None:
        scenario = create_test_scenario()
        world = WorldModel.from_scenario(scenario)
        world.apply_events(scenario.events)
        dynamics = VesselDynamics.from_config(scenario.vessel)
        pipeline = SensorPipeline(master_seed=scenario.seed)

        sensor_frames: list[SensorFrame] = []
        ground_truth_frames: list[GroundTruthFrame] = []

        for seq, t_ms in enumerate(range(0, scenario.duration_ms, 10)):
            env = world.step(t_ms)
            wave_f, wave_rm, wave_ym = world.wave.evaluate_impact(t_ms)
            vessel = dynamics.step(
                dt_s=0.01,
                env=env,
                rudder_deg=0.0,
                wave_impact_force_n=wave_f,
                wave_impact_roll_moment_nm=wave_rm,
                wave_impact_yaw_moment_nm=wave_ym,
            )

            gt_frame = GroundTruthFrame(
                sim_time_ms=t_ms,
                vessel=vessel,
                environment=env,
                sequence_number=seq,
                active_event_ids=(),
            )
            ground_truth_frames.append(gt_frame)

            sensor_frame = pipeline.process(gt_frame)
            sensor_frames.append(sensor_frame)

        assert len(sensor_frames) == 1000
        assert len(ground_truth_frames) == 1000

        for i, sf in enumerate(sensor_frames):
            assert sf.sim_time_ms == i * 10
            assert sf.sequence_number == i
            # Basic validation of channels
            assert isinstance(sf, SensorFrame)
            assert sf.imu is not None
            assert sf.gps is not None
            assert sf.wind is not None
            assert sf.actuators is not None

    def test_pipeline_reset_restores_initial_state(self) -> None:
        scenario = create_test_scenario()
        world = WorldModel.from_scenario(scenario)
        dynamics = VesselDynamics.from_config(scenario.vessel)
        pipeline = SensorPipeline(master_seed=42)

        # Run 100 ticks
        frames1: list[SensorFrame] = []
        for seq, t_ms in enumerate(range(0, 1000, 10)):
            env = world.step(t_ms)
            vessel = dynamics.step(0.01, env)
            gt = GroundTruthFrame(
                sim_time_ms=t_ms,
                vessel=vessel,
                environment=env,
                sequence_number=seq,
                active_event_ids=(),
            )
            frames1.append(pipeline.process(gt))

        # Reset pipeline and world
        pipeline.reset(master_seed=42)
        world = WorldModel.from_scenario(scenario)
        dynamics.reset()

        frames2: list[SensorFrame] = []
        for seq, t_ms in enumerate(range(0, 1000, 10)):
            env = world.step(t_ms)
            vessel = dynamics.step(0.01, env)
            gt = GroundTruthFrame(
                sim_time_ms=t_ms,
                vessel=vessel,
                environment=env,
                sequence_number=seq,
                active_event_ids=(),
            )
            frames2.append(pipeline.process(gt))

        assert len(frames1) == len(frames2)
        for f1, f2 in zip(frames1, frames2, strict=True):
            assert f1 == f2

    def test_safety_channel_status_propagation(self) -> None:
        from sia_sim.contracts.data import SafetyChannelStatus

        scenario = create_test_scenario()
        world = WorldModel.from_scenario(scenario)
        dynamics = VesselDynamics.from_config(scenario.vessel)

        # Default wired verified
        pipeline_wired = SensorPipeline(master_seed=42)
        env = world.step(0)
        vessel = dynamics.step(0.01, env)
        gt = GroundTruthFrame(
            sim_time_ms=0,
            vessel=vessel,
            environment=env,
            sequence_number=0,
            active_event_ids=(),
        )
        sf_wired = pipeline_wired.process(gt)
        assert sf_wired.safety_channel_status == SafetyChannelStatus.WIRED_VERIFIED

        # Custom wireless advisory pipeline
        pipeline_wireless = SensorPipeline(master_seed=42, safety_channel_status=SafetyChannelStatus.WIRELESS_ADVISORY)
        sf_wireless = pipeline_wireless.process(gt)
        assert sf_wireless.safety_channel_status == SafetyChannelStatus.WIRELESS_ADVISORY

    def test_safety_channel_event_override(self) -> None:
        from sia_sim.contracts.data import SafetyChannelStatus

        scenario = create_test_scenario()
        world = WorldModel.from_scenario(scenario)
        dynamics = VesselDynamics.from_config(scenario.vessel)
        pipeline = SensorPipeline(master_seed=42)

        env = world.step(0)
        vessel = dynamics.step(0.01, env)
        gt = GroundTruthFrame(
            sim_time_ms=0,
            vessel=vessel,
            environment=env,
            sequence_number=0,
            active_event_ids=(),
        )

        # Event overriding to wireless
        override_event = ScenarioEvent(
            sim_time_ms=0,
            event_id="EVT-RF-MODE",
            event_type="channel_status_override",
            parameters={"status": "WIRELESS_ADVISORY"},
        )
        sf = pipeline.process(gt, active_events=(override_event,))
        assert sf.safety_channel_status == SafetyChannelStatus.WIRELESS_ADVISORY
