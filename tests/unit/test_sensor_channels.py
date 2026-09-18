"""Unit tests for individual sensor channels and degradation primitives."""

from __future__ import annotations

import math

import numpy as np

from sia_sim.contracts.data import EnvironmentState, VesselState
from sia_sim.sensors.actuator import ActuatorSensorModel
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig
from sia_sim.sensors.gps import GPSSensorModel
from sia_sim.sensors.imu import IMUSensorModel
from sia_sim.sensors.wind import WindSensorModel


def make_sample_vessel() -> VesselState:
    return VesselState(
        x_m=100.0,
        y_m=200.0,
        heading_deg=45.0,
        sog_m_s=3.0,  # ~5.83 kt
        cog_deg=48.0,
        heel_deg=12.0,
        pitch_deg=2.0,
        roll_rate_deg_s=1.5,
        yaw_rate_deg_s=-0.8,
        rudder_angle_deg=5.0,
    )


def make_sample_environment() -> EnvironmentState:
    return EnvironmentState(
        true_wind_speed_m_s=10.0,
        true_wind_angle_deg=90.0,
        wave_height_m=2.0,
        wave_period_s=6.0,
        current_speed_m_s=0.5,
        current_direction_deg=180.0,
    )


class TestDegradationPrimitives:
    def test_zero_noise_passthrough(self) -> None:
        degrader = ChannelDegrader(DegradationConfig(noise_std=0.0))
        val = degrader.process(42.0, 0)
        assert val == 42.0

    def test_bias_and_linear_drift(self) -> None:
        # Bias = 2.0, drift = 0.5 units/s
        degrader = ChannelDegrader(DegradationConfig(bias=2.0, drift_rate=0.5, noise_std=0.0))
        # At t=0s: 10 + 2 + 0 = 12.0
        assert math.isclose(degrader.process(10.0, 0) or 0.0, 12.0, abs_tol=1e-5)
        # At t=2s (2000ms): 10 + 2 + 0.5*2 = 13.0
        assert math.isclose(degrader.process(10.0, 2000) or 0.0, 13.0, abs_tol=1e-5)

    def test_latency_queue_delay(self) -> None:
        # 50 ms latency = 5 ticks of 10ms
        degrader = ChannelDegrader(DegradationConfig(latency_ms=50, noise_std=0.0, warmup_fill=False))

        # Ticks 0..4 (0..40ms): queue is filling, returns None
        for t_ms in range(0, 50, 10):
            out = degrader.process(float(t_ms), t_ms)
            assert out is None

        # Tick 5 (50ms): returns value from T=0 (0.0)
        out50 = degrader.process(50.0, 50)
        assert out50 == 0.0

        # Tick 6 (60ms): returns value from T=10 (10.0)
        out60 = degrader.process(60.0, 60)
        assert out60 == 10.0

    def test_frozen_fault_holds_value(self) -> None:
        degrader = ChannelDegrader(DegradationConfig(noise_std=0.0))
        degrader.process(15.0, 0)

        degrader.set_frozen(True)
        # Even as input changes to 25.0 and 35.0, output remains frozen at 15.0
        assert degrader.process(25.0, 10) == 15.0
        assert degrader.process(35.0, 20) == 15.0

        degrader.set_frozen(False)
        assert degrader.process(50.0, 30) == 50.0

    def test_dropout_fault_returns_none(self) -> None:
        degrader = ChannelDegrader(DegradationConfig(noise_std=0.0))
        assert degrader.process(10.0, 0) == 10.0

        degrader.set_faulted(True)
        assert degrader.process(10.0, 10) is None


class TestIMUSensorModel:
    def test_imu_measurement_generation(self) -> None:
        vessel = make_sample_vessel()
        imu = IMUSensorModel(rng=np.random.default_rng(42))

        reading = imu.generate(vessel, 0)
        assert reading.fault is False
        assert reading.roll_deg is not None
        assert math.isclose(reading.roll_deg, 12.0, abs_tol=0.5)
        assert reading.pitch_deg is not None
        assert math.isclose(reading.pitch_deg, 2.0, abs_tol=0.5)
        assert reading.yaw_rate_deg_s is not None
        assert math.isclose(reading.yaw_rate_deg_s, -0.8, abs_tol=0.8)
        assert reading.accel_z_m_s2 is not None

    def test_imu_fault_drops_all_axes(self) -> None:
        vessel = make_sample_vessel()
        imu = IMUSensorModel()
        imu.set_fault(True)

        reading = imu.generate(vessel, 0)
        assert reading.fault is True
        assert reading.roll_deg is None
        assert reading.yaw_rate_deg_s is None
        assert reading.accel_x_m_s2 is None


class TestGPSSensorModel:
    def test_gps_coordinates_and_speed(self) -> None:
        vessel = make_sample_vessel()
        # Latency=0 for direct test
        gps = GPSSensorModel(
            rng=np.random.default_rng(42),
            sog_config=DegradationConfig(latency_ms=0, noise_std=0.0),
            cog_config=DegradationConfig(latency_ms=0, noise_std=0.0),
        )

        reading = gps.generate(vessel, 0)
        assert reading.fault is False
        assert reading.latitude_deg is not None
        assert reading.longitude_deg is not None
        assert reading.sog_kt is not None
        # 3.0 m/s * 1.943844 = 5.8315 kt
        assert math.isclose(reading.sog_kt, 5.8315, abs_tol=0.1)
        assert reading.cog_deg is not None
        assert math.isclose(reading.cog_deg, 48.0, abs_tol=0.1)

    def test_gps_fix_loss(self) -> None:
        vessel = make_sample_vessel()
        gps = GPSSensorModel()
        gps.set_fix_loss(True)

        reading = gps.generate(vessel, 0)
        assert reading.fault is True
        assert reading.latitude_deg is None
        assert reading.sog_kt is None
        assert reading.cog_deg is None


class TestWindSensorModel:
    def test_wind_measurement_calculation(self) -> None:
        vessel = make_sample_vessel()
        env = make_sample_environment()
        wind = WindSensorModel(
            rng=np.random.default_rng(42),
            speed_config=DegradationConfig(noise_std=0.0),
            angle_config=DegradationConfig(noise_std=0.0),
        )

        reading = wind.generate(env, vessel, 0)
        assert reading.fault is False
        assert reading.apparent_wind_speed_kt is not None
        assert reading.apparent_wind_angle_deg is not None
        assert reading.apparent_wind_speed_kt > 0.0


class TestActuatorSensorModel:
    def test_actuator_rudder_and_absent_mainsheet_by_default(self) -> None:
        vessel = make_sample_vessel()
        # Latency=0 for direct test
        actuator = ActuatorSensorModel(
            rng=np.random.default_rng(42),
            rudder_config=DegradationConfig(latency_ms=0, noise_std=0.0),
            enable_mainsheet_sensor=False,
        )

        state = actuator.generate(vessel, 0)
        assert state.fault is False
        assert state.rudder_angle_deg is not None
        assert math.isclose(state.rudder_angle_deg, 5.0, abs_tol=0.1)
        # CRITICAL HARDWARE INVARIANT: mainsheet sensor absent by default
        assert state.mainsheet_pct is None
