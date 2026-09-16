"""Unit tests for the 10 world presets and continuous living background ocean."""

from __future__ import annotations

from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios.presets import (
    WORLD_PRESET_CONFIGS,
    get_calm_harbour_preset,
    get_coastal_cruise_preset,
    get_gale_force_preset,
    get_preset_by_id,
    list_world_presets,
)


def test_list_world_presets_contains_10_presets() -> None:
    presets = list_world_presets()
    assert len(presets) == 10
    ids = {p["id"] for p in presets}
    assert ids == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    slugs = {p["slug"] for p in presets}
    assert slugs == {
        "calm_harbour",
        "light_breeze",
        "coastal_cruise",
        "fresh_breeze",
        "strong_wind",
        "near_gale",
        "gale_force",
        "storm_survival",
        "ocean_swell",
        "hurricane",
    }


def test_world_preset_configs_match_user_spec() -> None:
    assert len(WORLD_PRESET_CONFIGS) == 10

    # 1. Calm Harbour (Mirror)
    p1 = WORLD_PRESET_CONFIGS[0]
    assert p1["name"] == "Calm Harbour (Mirror)"
    assert p1["category"] == "Fair Weather"
    assert p1["wind"]["speed_knots"] == 2.0
    assert p1["wave"]["height_m"] == 0.1

    # 10. Hurricane / Stress Test
    p10 = WORLD_PRESET_CONFIGS[9]
    assert p10["name"] == "Hurricane / Stress Test"
    assert p10["category"] == "Stress Test"
    assert p10["wind"]["speed_knots"] == 65.0
    assert p10["wave"]["height_m"] == 11.0


def test_all_10_presets_instantiate_valid_scenarios() -> None:
    all_slugs = [
        "calm_harbour",
        "light_breeze",
        "coastal_cruise",
        "fresh_breeze",
        "strong_wind",
        "near_gale",
        "gale_force",
        "storm_survival",
        "ocean_swell",
        "hurricane",
    ]
    for pid in all_slugs:
        scenario = get_preset_by_id(pid, seed=123, duration_s=10)
        assert scenario.duration_ms == 10000
        assert scenario.seed == 123
        assert scenario.initial_tws_kt > 0.0
        assert scenario.vessel.loa_m > 0.0

    # Test numeric IDs as strings and integers
    for num_id in range(1, 11):
        scenario = get_preset_by_id(num_id, seed=42, duration_s=5)
        assert scenario.duration_ms == 5000
        assert scenario.seed == 42


def test_backward_compatibility_ids() -> None:
    for legacy_id in ("harbour", "cruise", "fresh", "gale"):
        scenario = get_preset_by_id(legacy_id, seed=42, duration_s=20)
        assert scenario.duration_ms == 20000


def test_clean_sailing_without_timeline_events() -> None:
    """Verify that with zero events, ship sails continuously with living ocean oscillations."""
    cruise = get_coastal_cruise_preset(seed=42, duration_ms=5000)
    assert len(cruise.events) == 0

    runner = SimulationRunner()
    result = runner.run(cruise)

    # Check that simulation ran to completion
    assert len(result.recorder.records) == 500  # 5s at 100 Hz

    # Check continuous dynamic motion
    heels = [r.gt.vessel.heel_deg for r in result.recorder.records]
    pitches = [r.gt.vessel.pitch_deg for r in result.recorder.records]
    sogs = [r.gt.vessel.sog_m_s for r in result.recorder.records]

    # Vessel is moving forward
    assert all(sog > 1.0 for sog in sogs)

    # Wave-induced living background produces continuous oscillations
    heel_range = max(heels) - min(heels)
    assert heel_range > 0.1, "Continuous waves should generate non-zero roll oscillation"
    pitch_range = max(pitches) - min(pitches)
    assert pitch_range > 0.05, "Continuous waves should generate non-zero pitch oscillation"


def test_harbour_vs_gale_intensity() -> None:
    harbour = get_calm_harbour_preset()
    gale = get_gale_force_preset(with_events=False)

    assert harbour.initial_tws_kt < gale.initial_tws_kt
    assert harbour.initial_wave_height_m < gale.initial_wave_height_m
    assert harbour.vessel.initial_sog_kt < gale.vessel.initial_sog_kt
