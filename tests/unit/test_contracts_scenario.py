"""Unit tests for Scenario and ScenarioEvent data contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sia_sim.contracts.scenario import Scenario, ScenarioEvent, VesselConfig


@pytest.fixture
def sample_vessel() -> VesselConfig:
    return VesselConfig(
        vessel_type="monohull_ior",
        loa_m=10.5,
        beam_m=3.2,
        displacement_kg=4500.0,
        initial_heel_deg=15.0,
        initial_heading_deg=65.0,
        initial_sog_kt=5.8,
    )


@pytest.fixture
def sample_events() -> tuple[ScenarioEvent, ...]:
    return (
        ScenarioEvent(
            sim_time_ms=10000,
            event_id="EVT-001",
            event_type="wave_impact",
            parameters={"height_m": 3.0, "period_s": 7.0},
        ),
        ScenarioEvent(
            sim_time_ms=12000,
            event_id="EVT-002",
            event_type="wind_gust",
            parameters={"tws_kt": 30.0},
        ),
    )


@pytest.fixture
def sample_scenario(sample_vessel: VesselConfig, sample_events: tuple[ScenarioEvent, ...]) -> Scenario:
    return Scenario(
        scenario_id="SIM-005",
        scenario_version="1.0.0",
        name="Broach Precursor Scenario",
        description="Classic broach precursor with wave impact followed by wind gust",
        duration_ms=30000,
        seed=42,
        vessel=sample_vessel,
        events=sample_events,
        initial_tws_kt=20.0,
        initial_twa_deg=65.0,
        initial_wave_height_m=3.0,
        initial_wave_period_s=7.0,
    )


class TestScenarioConstruction:
    def test_scenario_constructs_valid(self, sample_scenario: Scenario) -> None:
        assert sample_scenario.scenario_id == "SIM-005"
        assert sample_scenario.duration_ms == 30000
        assert sample_scenario.seed == 42
        assert len(sample_scenario.events) == 2

    def test_scenario_empty_events_valid(self, sample_vessel: VesselConfig) -> None:
        scenario = Scenario(
            scenario_id="SIM-001",
            scenario_version="1.0.0",
            name="Normal Sailing",
            description="Calm sea without events",
            duration_ms=10000,
            seed=123,
            vessel=sample_vessel,
            events=(),
            initial_tws_kt=15.0,
            initial_twa_deg=45.0,
            initial_wave_height_m=1.0,
            initial_wave_period_s=5.0,
        )
        assert scenario.events == ()


class TestScenarioImmutability:
    def test_scenario_is_frozen(self, sample_scenario: Scenario) -> None:
        with pytest.raises(ValidationError):
            setattr(sample_scenario, "seed", 999)  # noqa: B010

    def test_scenario_event_is_frozen(self, sample_events: tuple[ScenarioEvent, ...]) -> None:
        with pytest.raises(ValidationError):
            setattr(sample_events[0], "sim_time_ms", 99999)  # noqa: B010

    def test_vessel_config_is_frozen(self, sample_vessel: VesselConfig) -> None:
        with pytest.raises(ValidationError):
            setattr(sample_vessel, "displacement_kg", 5000.0)  # noqa: B010


class TestScenarioValidation:
    def test_duration_must_be_positive(self, sample_vessel: VesselConfig) -> None:
        with pytest.raises(ValidationError):
            Scenario(
                scenario_id="SIM-001",
                scenario_version="1.0.0",
                name="Test",
                description="Test",
                duration_ms=0,
                seed=42,
                vessel=sample_vessel,
                events=(),
                initial_tws_kt=15.0,
                initial_twa_deg=45.0,
                initial_wave_height_m=1.0,
                initial_wave_period_s=5.0,
            )

    def test_vessel_loa_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            VesselConfig(
                vessel_type="monohull_ior",
                loa_m=0.0,
                beam_m=3.0,
                displacement_kg=4000.0,
                initial_heel_deg=0.0,
                initial_heading_deg=0.0,
                initial_sog_kt=5.0,
            )

    def test_event_sim_time_cannot_be_negative(self) -> None:
        with pytest.raises(ValidationError):
            invalid_time = int("-100")
            ScenarioEvent(
                sim_time_ms=invalid_time,
                event_id="EVT-001",
                event_type="test",
                parameters={},
            )


class TestScenarioRoundTrip:
    def test_json_round_trip(self, sample_scenario: Scenario) -> None:
        json_str = sample_scenario.model_dump_json()
        restored = Scenario.model_validate_json(json_str)
        assert restored == sample_scenario
