"""Unit tests for SensorFrame and GroundTruthFrame data contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sia_sim.contracts.data import (
    ActuatorState,
    EnvironmentState,
    GPSReading,
    GroundTruthFrame,
    IMUReading,
    SensorFrame,
    VesselState,
    WindReading,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def imu_all_none() -> IMUReading:
    """IMU with all signal fields None (complete failure)."""
    return IMUReading(
        roll_deg=None,
        pitch_deg=None,
        roll_rate_deg_s=None,
        pitch_rate_deg_s=None,
        yaw_rate_deg_s=None,
        accel_x_m_s2=None,
        accel_y_m_s2=None,
        accel_z_m_s2=None,
        fault=True,
    )


@pytest.fixture
def imu_healthy() -> IMUReading:
    """IMU with all signal fields populated (healthy state)."""
    return IMUReading(
        roll_deg=15.0,
        pitch_deg=2.5,
        roll_rate_deg_s=3.0,
        pitch_rate_deg_s=0.5,
        yaw_rate_deg_s=-1.0,
        accel_x_m_s2=0.1,
        accel_y_m_s2=9.8,
        accel_z_m_s2=0.05,
        fault=False,
    )


@pytest.fixture
def gps_no_fix() -> GPSReading:
    """GPS with no fix (all position fields None)."""
    return GPSReading(
        latitude_deg=None,
        longitude_deg=None,
        sog_kt=None,
        cog_deg=None,
        hdop=None,
        fault=True,
    )


@pytest.fixture
def gps_healthy() -> GPSReading:
    return GPSReading(
        latitude_deg=59.3293,
        longitude_deg=18.0686,
        sog_kt=5.8,
        cog_deg=45.0,
        hdop=1.2,
        fault=False,
    )


@pytest.fixture
def wind_failed() -> WindReading:
    return WindReading(
        apparent_wind_speed_kt=None,
        apparent_wind_angle_deg=None,
        fault=True,
    )


@pytest.fixture
def wind_healthy() -> WindReading:
    return WindReading(
        apparent_wind_speed_kt=20.5,
        apparent_wind_angle_deg=-35.0,
        fault=False,
    )


@pytest.fixture
def actuators_no_feedback() -> ActuatorState:
    return ActuatorState(
        rudder_angle_deg=None,
        mainsheet_pct=None,
        fault=True,
    )


@pytest.fixture
def actuators_healthy() -> ActuatorState:
    return ActuatorState(
        rudder_angle_deg=5.0,
        mainsheet_pct=75.0,
        fault=False,
    )


@pytest.fixture
def sensor_frame_all_failed(
    imu_all_none: IMUReading,
    gps_no_fix: GPSReading,
    wind_failed: WindReading,
    actuators_no_feedback: ActuatorState,
) -> SensorFrame:
    """SensorFrame representing complete sensor failure state."""
    return SensorFrame(
        sim_time_ms=0,
        imu=imu_all_none,
        gps=gps_no_fix,
        wind=wind_failed,
        actuators=actuators_no_feedback,
        sequence_number=0,
    )


@pytest.fixture
def sensor_frame_healthy(
    imu_healthy: IMUReading,
    gps_healthy: GPSReading,
    wind_healthy: WindReading,
    actuators_healthy: ActuatorState,
) -> SensorFrame:
    """SensorFrame representing healthy sensor state."""
    return SensorFrame(
        sim_time_ms=10,
        imu=imu_healthy,
        gps=gps_healthy,
        wind=wind_healthy,
        actuators=actuators_healthy,
        sequence_number=1,
    )


@pytest.fixture
def vessel_state() -> VesselState:
    return VesselState(
        x_m=0.0,
        y_m=0.0,
        heading_deg=45.0,
        sog_m_s=3.0,
        cog_deg=47.0,
        heel_deg=15.0,
        pitch_deg=2.0,
        roll_rate_deg_s=1.5,
        yaw_rate_deg_s=-0.5,
        rudder_angle_deg=3.0,
    )


@pytest.fixture
def environment_state() -> EnvironmentState:
    return EnvironmentState(
        true_wind_speed_m_s=10.3,
        true_wind_angle_deg=200.0,
        wave_height_m=3.0,
        wave_period_s=7.0,
        current_speed_m_s=0.5,
        current_direction_deg=90.0,
    )


@pytest.fixture
def ground_truth_frame(
    vessel_state: VesselState,
    environment_state: EnvironmentState,
) -> GroundTruthFrame:
    return GroundTruthFrame(
        sim_time_ms=0,
        vessel=vessel_state,
        environment=environment_state,
        sequence_number=0,
        active_event_ids=(),
    )


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


class TestSensorFrameConstruction:
    def test_sensor_frame_all_failed_constructs(self, sensor_frame_all_failed: SensorFrame) -> None:
        assert sensor_frame_all_failed.sim_time_ms == 0
        assert sensor_frame_all_failed.sequence_number == 0

    def test_sensor_frame_healthy_constructs(self, sensor_frame_healthy: SensorFrame) -> None:
        assert sensor_frame_healthy.sim_time_ms == 10
        assert sensor_frame_healthy.sequence_number == 1
        assert sensor_frame_healthy.imu.roll_deg == 15.0

    def test_sensor_frame_sequence_number_zero_valid(
        self,
        imu_all_none: IMUReading,
        gps_no_fix: GPSReading,
        wind_failed: WindReading,
        actuators_no_feedback: ActuatorState,
    ) -> None:
        frame = SensorFrame(
            sim_time_ms=0,
            imu=imu_all_none,
            gps=gps_no_fix,
            wind=wind_failed,
            actuators=actuators_no_feedback,
            sequence_number=0,
        )
        assert frame.sequence_number == 0

    def test_imu_fault_true_with_all_none_is_valid(self, imu_all_none: IMUReading) -> None:
        """Complete IMU failure: fault=True and all signals None is valid."""
        assert imu_all_none.fault is True
        assert imu_all_none.roll_deg is None
        assert imu_all_none.accel_z_m_s2 is None

    def test_imu_fault_false_with_partial_none_is_valid(self) -> None:
        """Partial signal loss: fault=False and some fields None is valid."""
        imu = IMUReading(
            roll_deg=None,  # dropout on roll only
            pitch_deg=2.0,
            roll_rate_deg_s=None,
            pitch_rate_deg_s=0.5,
            yaw_rate_deg_s=-0.5,
            accel_x_m_s2=None,
            accel_y_m_s2=9.8,
            accel_z_m_s2=0.1,
            fault=False,
        )
        assert imu.fault is False
        assert imu.roll_deg is None
        assert imu.pitch_deg == 2.0


class TestGroundTruthFrameConstruction:
    def test_ground_truth_frame_constructs(self, ground_truth_frame: GroundTruthFrame) -> None:
        assert ground_truth_frame.sim_time_ms == 0
        assert ground_truth_frame.sequence_number == 0
        assert ground_truth_frame.active_event_ids == ()

    def test_ground_truth_with_events(
        self, vessel_state: VesselState, environment_state: EnvironmentState
    ) -> None:
        frame = GroundTruthFrame(
            sim_time_ms=10000,
            vessel=vessel_state,
            environment=environment_state,
            sequence_number=1000,
            active_event_ids=("EVT-001", "EVT-002"),
        )
        assert len(frame.active_event_ids) == 2
        assert "EVT-001" in frame.active_event_ids


# ---------------------------------------------------------------------------
# None-preservation tests (critical: no zero-coercion)
# ---------------------------------------------------------------------------


class TestNonePreservation:
    def test_imu_none_fields_preserved_in_model_dump(
        self, sensor_frame_all_failed: SensorFrame
    ) -> None:
        """None sensor values must NOT be coerced to 0.0 in serialized output."""
        dumped = sensor_frame_all_failed.model_dump()
        imu = dumped["imu"]
        assert imu["roll_deg"] is None, "None must not be coerced to 0.0"
        assert imu["pitch_deg"] is None, "None must not be coerced to 0.0"
        assert imu["accel_z_m_s2"] is None, "None must not be coerced to 0.0"
        # Keys must exist (not omitted)
        assert "roll_deg" in imu, "None field must not be omitted from dump"
        assert "accel_x_m_s2" in imu, "None field must not be omitted"

    def test_gps_none_fields_preserved_in_model_dump(
        self, sensor_frame_all_failed: SensorFrame
    ) -> None:
        dumped = sensor_frame_all_failed.model_dump()
        gps = dumped["gps"]
        assert gps["latitude_deg"] is None
        assert gps["sog_kt"] is None
        assert "latitude_deg" in gps

    def test_wind_none_fields_preserved_in_model_dump(
        self, sensor_frame_all_failed: SensorFrame
    ) -> None:
        dumped = sensor_frame_all_failed.model_dump()
        wind = dumped["wind"]
        assert wind["apparent_wind_speed_kt"] is None
        assert wind["apparent_wind_angle_deg"] is None

    def test_actuator_none_fields_preserved_in_model_dump(
        self, sensor_frame_all_failed: SensorFrame
    ) -> None:
        dumped = sensor_frame_all_failed.model_dump()
        act = dumped["actuators"]
        assert act["rudder_angle_deg"] is None
        assert act["mainsheet_pct"] is None


# ---------------------------------------------------------------------------
# Immutability tests
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_sensor_frame_is_frozen(self, sensor_frame_all_failed: SensorFrame) -> None:
        with pytest.raises(ValidationError):
            setattr(sensor_frame_all_failed, "sequence_number", 999)  # noqa: B010

    def test_imu_reading_is_frozen(self, imu_all_none: IMUReading) -> None:
        with pytest.raises(ValidationError):
            setattr(imu_all_none, "roll_deg", 1.0)  # noqa: B010

    def test_gps_reading_is_frozen(self, gps_no_fix: GPSReading) -> None:
        with pytest.raises(ValidationError):
            setattr(gps_no_fix, "fault", False)  # noqa: B010

    def test_ground_truth_frame_is_frozen(self, ground_truth_frame: GroundTruthFrame) -> None:
        with pytest.raises(ValidationError):
            setattr(ground_truth_frame, "sim_time_ms", 999)  # noqa: B010

    def test_vessel_state_is_frozen(self, vessel_state: VesselState) -> None:
        with pytest.raises(ValidationError):
            setattr(vessel_state, "heel_deg", 99.0)  # noqa: B010


# ---------------------------------------------------------------------------
# Strict type enforcement tests
# ---------------------------------------------------------------------------


class TestStrictTypeEnforcement:
    def test_sim_time_ms_must_be_int(
        self,
        imu_all_none: IMUReading,
        gps_no_fix: GPSReading,
        wind_failed: WindReading,
        actuators_no_feedback: ActuatorState,
    ) -> None:
        """strict=True: passing float where int is expected raises ValidationError."""
        with pytest.raises(ValidationError):
            SensorFrame(
                sim_time_ms=10.5,  # type: ignore[arg-type]
                imu=imu_all_none,
                gps=gps_no_fix,
                wind=wind_failed,
                actuators=actuators_no_feedback,
                sequence_number=0,
            )

    def test_sequence_number_must_be_int(
        self,
        imu_all_none: IMUReading,
        gps_no_fix: GPSReading,
        wind_failed: WindReading,
        actuators_no_feedback: ActuatorState,
    ) -> None:
        with pytest.raises(ValidationError):
            SensorFrame(
                sim_time_ms=0,
                imu=imu_all_none,
                gps=gps_no_fix,
                wind=wind_failed,
                actuators=actuators_no_feedback,
                sequence_number=1.0,  # type: ignore[arg-type]
            )

    def test_sequence_number_cannot_be_negative(
        self,
        imu_all_none: IMUReading,
        gps_no_fix: GPSReading,
        wind_failed: WindReading,
        actuators_no_feedback: ActuatorState,
    ) -> None:
        with pytest.raises(ValidationError):
            invalid_seq = int("-1")
            SensorFrame(
                sim_time_ms=0,
                imu=imu_all_none,
                gps=gps_no_fix,
                wind=wind_failed,
                actuators=actuators_no_feedback,
                sequence_number=invalid_seq,
            )

    def test_ground_truth_active_event_ids_must_be_tuple(
        self,
        vessel_state: VesselState,
        environment_state: EnvironmentState,
    ) -> None:
        """strict=True: list is not accepted where tuple is expected."""
        with pytest.raises(ValidationError):
            GroundTruthFrame(
                sim_time_ms=0,
                vessel=vessel_state,
                environment=environment_state,
                sequence_number=0,
                active_event_ids=["EVT-001"],  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Round-trip serialization tests
# ---------------------------------------------------------------------------


class TestRoundTripSerialization:
    def test_sensor_frame_all_failed_round_trips(
        self, sensor_frame_all_failed: SensorFrame
    ) -> None:
        dumped = sensor_frame_all_failed.model_dump()
        restored = SensorFrame.model_validate(dumped)
        assert restored == sensor_frame_all_failed

    def test_sensor_frame_healthy_round_trips(self, sensor_frame_healthy: SensorFrame) -> None:
        dumped = sensor_frame_healthy.model_dump()
        restored = SensorFrame.model_validate(dumped)
        assert restored == sensor_frame_healthy

    def test_ground_truth_frame_round_trips(self, ground_truth_frame: GroundTruthFrame) -> None:
        dumped = ground_truth_frame.model_dump()
        restored = GroundTruthFrame.model_validate(dumped)
        assert restored == ground_truth_frame

    def test_json_round_trip_sensor_frame(self, sensor_frame_all_failed: SensorFrame) -> None:
        json_str = sensor_frame_all_failed.model_dump_json()
        restored = SensorFrame.model_validate_json(json_str)
        assert restored == sensor_frame_all_failed

    def test_json_round_trip_preserves_none(self, sensor_frame_all_failed: SensorFrame) -> None:
        json_str = sensor_frame_all_failed.model_dump_json()
        restored = SensorFrame.model_validate_json(json_str)
        assert restored.imu.roll_deg is None
        assert restored.gps.latitude_deg is None


class TestSafetyChannelStatusContracts:
    def test_default_safety_channel_status_is_wired_verified(
        self, sensor_frame_healthy: SensorFrame
    ) -> None:
        from sia_sim.contracts.data import SafetyChannelStatus

        assert sensor_frame_healthy.safety_channel_status == SafetyChannelStatus.WIRED_VERIFIED

    def test_explicit_safety_channel_status(self, sensor_frame_healthy: SensorFrame) -> None:
        from sia_sim.contracts.data import SafetyChannelStatus

        frame_wireless = SensorFrame(
            sim_time_ms=100,
            imu=sensor_frame_healthy.imu,
            gps=sensor_frame_healthy.gps,
            wind=sensor_frame_healthy.wind,
            actuators=sensor_frame_healthy.actuators,
            sequence_number=1,
            safety_channel_status=SafetyChannelStatus.WIRELESS_ADVISORY,
        )
        assert frame_wireless.safety_channel_status == SafetyChannelStatus.WIRELESS_ADVISORY

        frame_mixed = SensorFrame(
            sim_time_ms=100,
            imu=sensor_frame_healthy.imu,
            gps=sensor_frame_healthy.gps,
            wind=sensor_frame_healthy.wind,
            actuators=sensor_frame_healthy.actuators,
            sequence_number=1,
            safety_channel_status=SafetyChannelStatus.MIXED,
        )
        assert frame_mixed.safety_channel_status == SafetyChannelStatus.MIXED

    def test_invalid_safety_channel_status_raises_validation_error(
        self, sensor_frame_healthy: SensorFrame
    ) -> None:
        with pytest.raises(ValidationError):
            SensorFrame(
                sim_time_ms=100,
                imu=sensor_frame_healthy.imu,
                gps=sensor_frame_healthy.gps,
                wind=sensor_frame_healthy.wind,
                actuators=sensor_frame_healthy.actuators,
                sequence_number=1,
                safety_channel_status="INVALID_STATUS",  # type: ignore[arg-type]
            )

