"""Verification tests for sensor fault modes, latency queues, and strict null semantics."""

from __future__ import annotations

import math

from sia_sim.contracts.data import EnvironmentState, GroundTruthFrame, VesselState
from sia_sim.contracts.scenario import ScenarioEvent
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig
from sia_sim.sensors.pipeline import SensorPipeline


def make_dynamic_gt(t_ms: int) -> GroundTruthFrame:
    """Generates ground truth with time-varying attitude and speed."""
    t_s = t_ms / 1000.0
    return GroundTruthFrame(
        sim_time_ms=t_ms,
        vessel=VesselState(
            x_m=t_s * 5.0,
            y_m=0.0,
            heading_deg=65.0 + 5.0 * math.sin(t_s),
            sog_m_s=3.0 + 0.5 * math.sin(t_s),
            cog_deg=65.0,
            heel_deg=15.0 + 10.0 * math.sin(t_s),
            pitch_deg=1.0 * math.cos(t_s),
            roll_rate_deg_s=10.0 * math.cos(t_s),
            yaw_rate_deg_s=5.0 * math.cos(t_s),
            rudder_angle_deg=2.0 * math.sin(t_s),
        ),
        environment=EnvironmentState(
            true_wind_speed_m_s=10.0,
            true_wind_angle_deg=90.0,
            wave_height_m=2.0,
            wave_period_s=6.0,
            current_speed_m_s=0.0,
            current_direction_deg=0.0,
        ),
        sequence_number=t_ms // 10,
        active_event_ids=(),
    )


class TestSensorFaultModes:
    def test_latency_queue_exact_tick_delay(self) -> None:
        """Verify 100 ms latency exactly delays measurement by 10 ticks."""
        degrader = ChannelDegrader(
            DegradationConfig(latency_ms=100, noise_std=0.0, warmup_fill=False)
        )

        inputs = [float(i * 10) for i in range(30)]  # 0, 10, 20, ..., 290
        outputs: list[float | None] = []

        for i, val in enumerate(inputs):
            out = degrader.process(val, i * 10)
            outputs.append(out)

        # First 10 ticks (0..90ms): buffer filling -> None
        for i in range(10):
            assert outputs[i] is None, f"Expected None at tick {i}, got {outputs[i]}"

        # Tick 10 (100ms): receives value from tick 0 (0.0)
        assert outputs[10] == 0.0
        # Tick 15 (150ms): receives value from tick 5 (50.0)
        assert outputs[15] == 50.0

    def test_dropout_fault_strict_null_semantics(self) -> None:
        """When sensor drops out, fields MUST be None and never coerced to 0.0 or False."""
        pipeline = SensorPipeline(master_seed=42)
        gt = make_dynamic_gt(0)

        # Trigger wind fault via scenario event
        fault_evt = ScenarioEvent(
            sim_time_ms=1000,
            event_id="EVT-WIND-DROP",
            event_type="wind_fault",
            parameters={},
        )

        frame = pipeline.process(gt, active_events=(fault_evt,))

        # Assert wind reading is faulted and fields are None
        assert frame.wind.fault is True
        assert frame.wind.apparent_wind_speed_kt is None
        assert frame.wind.apparent_wind_angle_deg is None

        # Assert zero-coercion invariant
        assert frame.wind.apparent_wind_speed_kt is not 0.0  # noqa: F632
        assert frame.wind.apparent_wind_angle_deg is not 0.0  # noqa: F632

    def test_frozen_sensor_holds_measurement(self) -> None:
        """Frozen sensor holds its last valid reading constant despite changing physical state."""
        pipeline = SensorPipeline(master_seed=42)

        # Step nominal for 5 ticks
        for t_ms in range(0, 50, 10):
            pipeline.process(make_dynamic_gt(t_ms))

        # Freeze IMU at T=50ms
        freeze_evt = ScenarioEvent(
            sim_time_ms=50,
            event_id="EVT-IMU-FREEZE",
            event_type="imu_freeze",
            parameters={},
        )

        frozen_frame_50 = pipeline.process(make_dynamic_gt(50), active_events=(freeze_evt,))
        frozen_roll = frozen_frame_50.imu.roll_deg

        # Step 20 ticks with freeze active while physical roll angle oscillates
        for t_ms in range(60, 260, 10):
            f = pipeline.process(make_dynamic_gt(t_ms), active_events=(freeze_evt,))
            assert f.imu.roll_deg == frozen_roll

    def test_partial_sensor_failure(self) -> None:
        """Single axis dropout emits None on that axis without failing the whole frame."""
        pipeline = SensorPipeline(master_seed=42)
        gt = make_dynamic_gt(0)

        # Individually fault the yaw rate degrader
        pipeline.imu.degrader_yaw_rate.set_faulted(True)

        frame = pipeline.process(gt)
        assert frame.imu.yaw_rate_deg_s is None
        # Other axes remain valid
        assert frame.imu.roll_deg is not None
        assert frame.imu.pitch_deg is not None

    def test_standard_yacht_absent_mainsheet_sensor(self) -> None:
        """On standard yachts, mainsheet sensor is absent by default (mainsheet_pct is None)."""
        pipeline = SensorPipeline(master_seed=42, enable_mainsheet_sensor=False)
        gt = make_dynamic_gt(0)

        frame = pipeline.process(gt)
        assert frame.actuators.mainsheet_pct is None
        assert frame.actuators.rudder_angle_deg is not None
        assert frame.actuators.fault is False
