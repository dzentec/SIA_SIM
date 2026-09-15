"""Scenario contract models for SIA Simulation.

Scenarios define the initial conditions, vessel configuration, and scheduled
events for a simulation run.

Architectural invariants:
  INV-06: Scenario is frozen during Run.
  Loaded and validated by ScenarioEngine before simulation starts.
  Simulation MUST NOT start if Scenario validation fails.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScenarioEvent(BaseModel):
    """A timed event in a scenario schedule (e.g. wind gust, wave impact, sensor failure)."""

    model_config = ConfigDict(frozen=True, strict=True)

    sim_time_ms: int = Field(ge=0)
    """When this event fires in simulation milliseconds."""

    event_id: str
    """Unique event identifier within the scenario."""

    event_type: str
    """Category: 'wind_gust', 'wave_impact', 'rudder_stall', 'sensor_fault', etc."""

    parameters: dict[str, float | int | str | bool]
    """Event-specific parameters dictionary."""


class VesselConfig(BaseModel):
    """Initial vessel configuration and hydrodynamics parameters for a scenario."""

    model_config = ConfigDict(frozen=True, strict=True)

    vessel_type: str
    """Vessel archetype, e.g. 'monohull_ior', 'catamaran'."""

    loa_m: float = Field(gt=0.0)
    """Length overall in meters."""

    beam_m: float = Field(gt=0.0)
    """Beam in meters."""

    displacement_kg: float = Field(gt=0.0)
    """Displacement in kilograms."""

    initial_heel_deg: float
    """Starting heel angle in degrees (+ starboard)."""

    initial_heading_deg: float
    """Starting heading in degrees (0-360)."""

    initial_sog_kt: float = Field(ge=0.0)
    """Starting speed over ground in knots."""


class Scenario(BaseModel):
    """Immutable scenario specification.

    INV-06: Scenario is frozen during Run.
    """

    model_config = ConfigDict(frozen=True, strict=True)

    scenario_id: str
    """Unique identifier (e.g. 'SIM-005')."""

    scenario_version: str
    """Schema version for reproducibility."""

    name: str
    """Human-readable scenario name."""

    description: str
    """Human-readable description and test objective."""

    duration_ms: int = Field(gt=0)
    """Total simulation duration in milliseconds."""

    seed: int
    """Master PRNG seed for reproducible execution."""

    vessel: VesselConfig
    """Initial vessel configuration."""

    events: tuple[ScenarioEvent, ...]
    """Timed event schedule, sorted by sim_time_ms."""

    initial_tws_kt: float = Field(ge=0.0)
    """True wind speed in knots at T=0."""

    initial_twa_deg: float
    """True wind angle in degrees at T=0."""

    initial_wave_height_m: float = Field(ge=0.0)
    """Significant wave height in meters at T=0."""

    initial_wave_period_s: float = Field(gt=0.0)
    """Wave period in seconds at T=0."""
