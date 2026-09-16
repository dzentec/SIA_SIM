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
    """Vessel archetype, e.g. 'monohull_ior', 'beneteau_oceanis_45', 'modern_cruiser'."""

    loa_m: float = Field(gt=0.0)
    """Length overall in meters."""

    beam_m: float = Field(gt=0.0)
    """Beam in meters."""

    displacement_kg: float = Field(gt=0.0)
    """Displacement in kilograms."""

    sail_area_m2: float = Field(default=45.0, gt=0.0)
    """Base nominal sail area (Main + Jib) in m²."""

    mast_height_m: float = Field(default=14.0, gt=0.0)
    """Mast height above waterline in meters."""

    sail_plan: str = Field(default="FULL_MAIN")
    """Configured sail plan (e.g. 'CODE_ZERO', 'FULL_MAIN', 'REEF_1', 'REEF_2', 'STORM_JIB', 'BARE_POLES')."""

    sail_trim_pct: float = Field(default=100.0, ge=0.0, le=150.0)
    """Effective sail trim / reef percentage (0-150%). 130% for Code Zero, 100% for Full Main."""

    initial_heel_deg: float
    """Starting heel angle in degrees (+ starboard)."""

    initial_heading_deg: float
    """Starting heading in degrees (0-360)."""

    initial_sog_kt: float = Field(ge=0.0)
    """Starting speed over ground in knots."""


# Canonical Single Source of Truth for IOR Classic 10.5m
DEFAULT_VESSEL_CONFIG = VesselConfig(
    vessel_type="monohull_ior",
    loa_m=10.5,
    beam_m=3.2,
    displacement_kg=4500.0,
    sail_area_m2=45.0,
    mast_height_m=14.0,
    sail_plan="FULL_MAIN",
    sail_trim_pct=100.0,
    initial_heading_deg=65.0,
    initial_sog_kt=5.0,
    initial_heel_deg=0.0,
)

# Canonical Single Source of Truth for Beneteau Oceanis 45
BENETEAU_OCEANIS_45_CONFIG = VesselConfig(
    vessel_type="beneteau_oceanis_45",
    loa_m=13.94,
    beam_m=4.50,
    displacement_kg=10550.0,
    sail_area_m2=100.0,
    mast_height_m=19.5,
    sail_plan="FULL_MAIN",
    sail_trim_pct=100.0,
    initial_heading_deg=65.0,
    initial_sog_kt=6.5,
    initial_heel_deg=0.0,
)


def create_vessel_config(
    initial_heading_deg: float = 65.0,
    initial_sog_kt: float = 5.0,
    initial_heel_deg: float = 0.0,
    vessel_type: str = "monohull_ior",
    sail_plan: str = "FULL_MAIN",
    sail_trim_pct: float = 100.0,
) -> VesselConfig:
    """Create a VesselConfig by overriding initial state or archetype."""
    base = BENETEAU_OCEANIS_45_CONFIG if "beneteau" in vessel_type.lower() or "oceanis" in vessel_type.lower() else DEFAULT_VESSEL_CONFIG
    return base.model_copy(
        update={
            "initial_heading_deg": initial_heading_deg,
            "initial_sog_kt": initial_sog_kt,
            "initial_heel_deg": initial_heel_deg,
            "sail_plan": sail_plan,
            "sail_trim_pct": sail_trim_pct,
        }
    )



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
