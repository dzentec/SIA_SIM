"""Core data contracts for SIA Simulation.

SensorFrame and GroundTruthFrame are the primary interface types:
- SensorFrame: the ONLY data type that crosses the Simulation→SIA Core boundary (INV-01).
- GroundTruthFrame: true physical state owned by WorldModel/Dynamics,
  consumed by Oracle only (INV-02).

Critical null semantics:
  Optional[float] / float | None fields that are None mean signal absent or failed.
  Consumers MUST handle None as "no observation" — NEVER coerce to 0.0 or False.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# SensorFrame sub-models
# ---------------------------------------------------------------------------


class IMUReading(BaseModel):
    """Inertial Measurement Unit reading.

    None values indicate sensor failure or dropout — never coerced to 0.0.
    """

    model_config = ConfigDict(frozen=True, strict=True)

    roll_deg: float | None
    """Roll angle in degrees. None = sensor failed / signal absent."""

    pitch_deg: float | None
    """Pitch angle in degrees. None = sensor failed / signal absent."""

    roll_rate_deg_s: float | None
    """Roll rate in deg/s. None = sensor failed / signal absent."""

    pitch_rate_deg_s: float | None
    """Pitch rate in deg/s. None = sensor failed / signal absent."""

    yaw_rate_deg_s: float | None
    """Yaw rate in deg/s. None = sensor failed / signal absent."""

    accel_x_m_s2: float | None
    """Longitudinal acceleration m/s². None = sensor failed / signal absent."""

    accel_y_m_s2: float | None
    """Lateral acceleration m/s². None = sensor failed / signal absent."""

    accel_z_m_s2: float | None
    """Vertical acceleration m/s². None = sensor failed / signal absent."""

    fault: bool
    """True if IMU is in fault state (e.g. power loss, hardware error)."""


class GPSReading(BaseModel):
    """GPS/GNSS position and velocity reading."""

    model_config = ConfigDict(frozen=True, strict=True)

    latitude_deg: float | None
    """WGS84 latitude degrees. None = no fix."""

    longitude_deg: float | None
    """WGS84 longitude degrees. None = no fix."""

    sog_kt: float | None
    """Speed over ground in knots. None = no fix."""

    cog_deg: float | None
    """Course over ground in degrees (0-360). None = no fix."""

    hdop: float | None
    """Horizontal Dilution of Precision. None = no fix."""

    fault: bool
    """True if GPS receiver is in fault state."""


class WindReading(BaseModel):
    """Wind vane / anemometer reading."""

    model_config = ConfigDict(frozen=True, strict=True)

    apparent_wind_speed_kt: float | None
    """Apparent wind speed in knots. None = sensor failed."""

    apparent_wind_angle_deg: float | None
    """Apparent wind angle in degrees (-180 to +180, port negative). None = sensor failed."""

    fault: bool
    """True if wind sensor is in fault state."""


class ActuatorState(BaseModel):
    """Rudder angle and mainsheet actuator feedback."""

    model_config = ConfigDict(frozen=True, strict=True)

    rudder_angle_deg: float | None
    """Rudder angle in degrees (positive = starboard). None = no feedback."""

    mainsheet_pct: float | None
    """Mainsheet trim percentage 0-100%. None = unknown / no sensor."""

    fault: bool
    """True if actuator feedback is in fault state."""


class SafetyChannelStatus(str, Enum):
    """Hardware channel classification for safety-critical latency guarantees (MDA v2.2 §3.5.2).

    - WIRED_VERIFIED: Critical sensors (IMU, rudder) connected via RS-485 (<20ms / <1.0s CRITICAL guarantee).
    - WIRELESS_ADVISORY: Critical sensors connected via RF / 802.15.4 (advisory only, no formal latency guarantee).
    - MIXED: Hybrid wired/wireless configuration (effective safety status degraded to advisory).
    """

    WIRED_VERIFIED = "WIRED_VERIFIED"
    WIRELESS_ADVISORY = "WIRELESS_ADVISORY"
    MIXED = "MIXED"


class SensorFrame(BaseModel):
    """Observable sensor data — the ONLY type crossing the Simulation→SIA Core boundary.

    Architectural invariants:
      INV-01: Only SensorFrame enters SIA Core.
      INV-02: Ground truth data is NEVER present in this model.

    Null semantics:
      None fields indicate signal absence or sensor failure.
      They MUST NOT be coerced to 0.0 or False by any consumer.
      SIA Core must treat None as "no observation available".
    """

    model_config = ConfigDict(frozen=True, strict=True)

    sim_time_ms: int
    """Simulation timestamp in integer milliseconds (from SimulationClock)."""

    imu: IMUReading
    """IMU channel. Individual fields within may be None on partial failure."""

    gps: GPSReading
    """GPS channel. Individual fields within may be None when no fix."""

    wind: WindReading
    """Wind sensor channel. Individual fields within may be None on failure."""

    actuators: ActuatorState
    """Actuator feedback channel. Individual fields within may be None."""

    sequence_number: int = Field(ge=0)
    """Monotonically increasing frame counter (starts at 0, never negative)."""

    safety_channel_status: SafetyChannelStatus = Field(
        default=SafetyChannelStatus.WIRED_VERIFIED,
        description="Physical channel classification for safety-critical latency guarantees (MDA v2.2 §3.5.2).",
    )


# ---------------------------------------------------------------------------
# GroundTruthFrame sub-models
# ---------------------------------------------------------------------------


class VesselState(BaseModel):
    """True physical state of the vessel (ground truth)."""

    model_config = ConfigDict(frozen=True, strict=True)

    x_m: float
    """Position X in simulation frame (meters)."""

    y_m: float
    """Position Y in simulation frame (meters)."""

    heading_deg: float
    """True heading in degrees (0 = North, clockwise)."""

    sog_m_s: float
    """Speed over ground in m/s."""

    cog_deg: float
    """Course over ground in degrees (0-360)."""

    heel_deg: float
    """Heel angle in degrees (positive = starboard heel)."""

    pitch_deg: float
    """Pitch angle in degrees (positive = bow up)."""

    roll_rate_deg_s: float
    """Roll rate in degrees/s."""

    yaw_rate_deg_s: float
    """Yaw rate in degrees/s."""

    rudder_angle_deg: float
    """True rudder angle in degrees (positive = starboard)."""


class EnvironmentState(BaseModel):
    """True environmental state (ground truth)."""

    model_config = ConfigDict(frozen=True, strict=True)

    true_wind_speed_m_s: float
    """True wind speed in m/s."""

    true_wind_angle_deg: float
    """True wind angle in degrees relative to North (meteorological convention)."""

    wave_height_m: float
    """Significant wave height in meters."""

    wave_period_s: float
    """Wave period in seconds."""

    current_speed_m_s: float
    """Sea current speed in m/s."""

    current_direction_deg: float
    """Sea current direction in degrees (direction current flows toward)."""


class GroundTruthFrame(BaseModel):
    """True physical state of the simulation world.

    Architectural invariants:
      INV-02: This MUST NOT enter SIA Core.
      Owner: WorldModel / VesselDynamics.
      Consumer: Oracle only.

    SIA Core can NEVER receive this type. Simulation must make it
    structurally impossible to pass this to SIACore.process().
    """

    model_config = ConfigDict(frozen=True, strict=True)

    sim_time_ms: int
    """Simulation timestamp in integer milliseconds (from SimulationClock)."""

    vessel: VesselState
    """True physical state of the vessel."""

    environment: EnvironmentState
    """True environmental state."""

    sequence_number: int = Field(ge=0)
    """Monotonically increasing frame counter (starts at 0, never negative)."""

    active_event_ids: tuple[str, ...]
    """IDs of scenario events active at this tick."""
