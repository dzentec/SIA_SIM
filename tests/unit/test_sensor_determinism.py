"""Determinism and PRNG isolation verification tests for the sensor pipeline."""

from __future__ import annotations

import math

import numpy as np

from sia_sim.contracts.data import EnvironmentState, GroundTruthFrame, VesselState
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig
from sia_sim.sensors.pipeline import SensorPipeline


def make_static_gt(sim_time_ms: int = 0) -> GroundTruthFrame:
    return GroundTruthFrame(
        sim_time_ms=sim_time_ms,
        vessel=VesselState(
            x_m=0.0,
            y_m=0.0,
            heading_deg=45.0,
            sog_m_s=3.0,
            cog_deg=45.0,
            heel_deg=10.0,
            pitch_deg=0.0,
            roll_rate_deg_s=0.0,
            yaw_rate_deg_s=0.0,
            rudder_angle_deg=0.0,
        ),
        environment=EnvironmentState(
            true_wind_speed_m_s=10.0,
            true_wind_angle_deg=90.0,
            wave_height_m=1.0,
            wave_period_s=5.0,
            current_speed_m_s=0.0,
            current_direction_deg=0.0,
        ),
        sequence_number=0,
        active_event_ids=(),
    )


class TestSensorDeterminism:
    def test_identical_seeds_produce_bit_identical_frames(self) -> None:
        p1 = SensorPipeline(master_seed=12345)
        p2 = SensorPipeline(master_seed=12345)

        gt = make_static_gt()

        for t_ms in range(0, 1000, 10):
            frame1 = p1.process(gt)
            frame2 = p2.process(gt)
            assert frame1 == frame2, f"Divergence at t={t_ms}ms"

    def test_different_seeds_produce_distinct_frames(self) -> None:
        p1 = SensorPipeline(master_seed=1)
        p2 = SensorPipeline(master_seed=2)

        gt = make_static_gt()
        frame1 = p1.process(gt)
        frame2 = p2.process(gt)

        # IMU noise should differ
        assert frame1.imu.roll_deg != frame2.imu.roll_deg

    def test_channel_rng_stream_independence(self) -> None:
        """Modifying one channel degrader must not alter random values drawn by other channels."""
        p1 = SensorPipeline(master_seed=42)
        p2 = SensorPipeline(master_seed=42)

        # Draw extra samples on p1's IMU RNG
        _ = p1.imu.rng.normal(0, 1, 100)

        gt = make_static_gt()
        frame1 = p1.process(gt)
        frame2 = p2.process(gt)

        # GPS and Wind were spawned independently, so their values must still match exactly!
        assert frame1.gps == frame2.gps
        assert frame1.wind == frame2.wind
        assert frame1.actuators == frame2.actuators

    def test_gaussian_noise_statistical_distribution(self) -> None:
        """Sample 5000 noise values and verify sample mean ~ 0 and sample std ~ config."""
        target_std = 0.5
        degrader = ChannelDegrader(DegradationConfig(noise_std=target_std), rng=np.random.default_rng(999))

        samples: list[float] = []
        for i in range(5000):
            val = degrader.process(0.0, i * 10)
            assert val is not None
            samples.append(val)

        arr = np.array(samples)
        sample_mean = float(np.mean(arr))
        sample_std = float(np.std(arr))

        assert math.isclose(sample_mean, 0.0, abs_tol=0.03)
        assert math.isclose(sample_std, target_std, abs_tol=0.03)
