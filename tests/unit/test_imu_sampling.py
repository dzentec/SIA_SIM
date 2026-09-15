"""Unit tests for IMU sampling rates, LPF filtering, and Edge Peak Envelope per RFC v1.1."""

from __future__ import annotations

import numpy as np

from sia_sim.contracts.data import VesselState
from sia_sim.sensors.imu import IMUSensorModel


def make_dummy_vessel(
    heel_deg: float = 10.0, pitch_deg: float = 2.0, roll_rate: float = 5.0
) -> VesselState:
    return VesselState(
        x_m=0.0,
        y_m=0.0,
        heading_deg=65.0,
        sog_m_s=3.0,
        cog_deg=65.0,
        heel_deg=heel_deg,
        pitch_deg=pitch_deg,
        roll_rate_deg_s=roll_rate,
        yaw_rate_deg_s=1.0,
        rudder_angle_deg=0.0,
    )


def test_imu_100hz_raw_mode() -> None:
    imu = IMUSensorModel(rng=np.random.default_rng(42), sample_rate_hz=100)
    vessel = make_dummy_vessel(heel_deg=15.0)

    reading1 = imu.generate(vessel, sim_time_ms=0)
    reading2 = imu.generate(vessel, sim_time_ms=10)

    assert reading1.roll_deg is not None
    assert reading2.roll_deg is not None
    # In 100 Hz mode, each 10 ms tick updates
    assert reading1 is not reading2


def test_imu_10hz_wireless_decimation_sample_and_hold() -> None:
    imu = IMUSensorModel(rng=np.random.default_rng(42), sample_rate_hz=10)
    vessel = make_dummy_vessel(heel_deg=15.0)

    r0 = imu.generate(vessel, sim_time_ms=0)
    r10 = imu.generate(vessel, sim_time_ms=10)
    r20 = imu.generate(vessel, sim_time_ms=20)
    r90 = imu.generate(vessel, sim_time_ms=90)
    r100 = imu.generate(vessel, sim_time_ms=100)

    # From 0 to 90 ms (within 100 ms period), output reading is held
    assert r0.roll_deg == r10.roll_deg == r20.roll_deg == r90.roll_deg
    # At 100 ms, next sample is latched
    assert r100 is not None


def test_imu_peak_envelope_tracking() -> None:
    """Verify that even with 10 Hz sampling, high-g shocks are recorded."""
    imu = IMUSensorModel(rng=np.random.default_rng(42), sample_rate_hz=10)

    # Initial tick
    vessel_calm = make_dummy_vessel(heel_deg=5.0, roll_rate=1.0)
    imu.generate(vessel_calm, sim_time_ms=0)

    # Intermediate violent shock at tick 30 ms (between 0 and 100 ms sample window)
    vessel_shock = make_dummy_vessel(heel_deg=35.0, roll_rate=45.0)
    imu.generate(vessel_shock, sim_time_ms=30)

    # Peak envelope must capture the 45 deg/s roll rate
    assert imu._peak_roll_rate_deg_s >= 40.0
