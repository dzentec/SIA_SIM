"""Unit tests for the 4 world presets and continuous living background ocean."""

from __future__ import annotations

from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios.presets import (
    get_coastal_cruise_preset,
    get_gale_broach_preset,
    get_harbour_preset,
    get_preset_by_id,
    list_world_presets,
)


def test_list_world_presets_contains_4_presets() -> None:
    presets = list_world_presets()
    assert len(presets) == 4
    preset_ids = {p["id"] for p in presets}
    assert preset_ids == {"harbour", "cruise", "fresh", "gale"}


def test_all_presets_instantiate_valid_scenarios() -> None:
    for pid in ("harbour", "cruise", "fresh", "gale"):
        scenario = get_preset_by_id(pid, seed=123, duration_s=10)
        assert scenario.duration_ms == 10000
        assert scenario.seed == 123
        assert scenario.initial_tws_kt > 0.0
        assert scenario.vessel.loa_m == 10.5


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
    harbour = get_harbour_preset()
    gale = get_gale_broach_preset(with_events=False)

    assert harbour.initial_tws_kt < gale.initial_tws_kt
    assert harbour.initial_wave_height_m < gale.initial_wave_height_m
    assert harbour.vessel.initial_sog_kt < gale.vessel.initial_sog_kt
