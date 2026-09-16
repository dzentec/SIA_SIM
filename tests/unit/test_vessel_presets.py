"""Unit tests for Vessel Presets (Beneteau Oceanis 45 & IOR Classic) and Sail Plan configurations."""

from __future__ import annotations

import pytest

from sia_sim.contracts.scenario import BENETEAU_OCEANIS_45_CONFIG, DEFAULT_VESSEL_CONFIG
from sia_sim.engine.runner import SimulationRunner
from sia_sim.scenarios import get_preset_by_id
from sia_sim.scenarios.presets import (
    SAIL_PLAN_PERCENTAGES,
    VESSEL_PRESETS,
    get_vessel_preset_config,
    list_vessel_presets,
)


def test_vessel_presets_registry() -> None:
    """Verify registry contains Beneteau Oceanis 45 and IOR Classic with correct metadata."""
    presets = list_vessel_presets()
    preset_ids = [p["id"] for p in presets]
    assert "beneteau_oceanis_45" in preset_ids
    assert "monohull_ior" in preset_ids

    b45 = VESSEL_PRESETS["beneteau_oceanis_45"]
    assert b45["loa_m"] == 13.94
    assert b45["beam_m"] == 4.50
    assert b45["displacement_kg"] == 10550.0
    assert b45["sail_area_m2"] == 100.0

    sail_ids = [s["id"] for s in b45["available_sails"]]
    assert "CODE_ZERO" in sail_ids
    assert "FULL_MAIN" in sail_ids
    assert "REEF_1" in sail_ids
    assert "REEF_2" in sail_ids
    assert "STORM_JIB" in sail_ids
    assert "BARE_POLES" in sail_ids


def test_get_vessel_preset_config_sails() -> None:
    """Verify get_vessel_preset_config calculates correct sail trim percentages."""
    cfg_code0 = get_vessel_preset_config("beneteau_oceanis_45", sail_plan="CODE_ZERO")
    assert cfg_code0.loa_m == 13.94
    assert cfg_code0.sail_plan == "CODE_ZERO"
    assert cfg_code0.sail_trim_pct == 130.0

    cfg_reef2 = get_vessel_preset_config("beneteau_oceanis_45", sail_plan="REEF_2")
    assert cfg_reef2.sail_plan == "REEF_2"
    assert cfg_reef2.sail_trim_pct == 50.0

    cfg_bare = get_vessel_preset_config("beneteau_oceanis_45", sail_plan="BARE_POLES")
    assert cfg_bare.sail_plan == "BARE_POLES"
    assert cfg_bare.sail_trim_pct == 0.0


def test_simulation_sail_plan_physics_impact() -> None:
    """Verify that Code Zero generates higher speed and heel than reefed sails or bare poles."""
    base_scenario = get_preset_by_id("cruise", seed=42, duration_s=10)

    # 1. Run with Code Zero (130%)
    cfg_code0 = get_vessel_preset_config("beneteau_oceanis_45", sail_plan="CODE_ZERO")
    sc_code0 = base_scenario.model_copy(update={"vessel": cfg_code0})
    res_code0 = SimulationRunner().run(sc_code0)

    # 2. Run with Full Main (100%)
    cfg_main = get_vessel_preset_config("beneteau_oceanis_45", sail_plan="FULL_MAIN")
    sc_main = base_scenario.model_copy(update={"vessel": cfg_main})
    res_main = SimulationRunner().run(sc_main)

    # 3. Run with Reef 2 (50%)
    cfg_reef2 = get_vessel_preset_config("beneteau_oceanis_45", sail_plan="REEF_2")
    sc_reef2 = base_scenario.model_copy(update={"vessel": cfg_reef2})
    res_reef2 = SimulationRunner().run(sc_reef2)

    # 4. Run with Bare Poles (0%)
    cfg_bare = get_vessel_preset_config("beneteau_oceanis_45", sail_plan="BARE_POLES")
    sc_bare = base_scenario.model_copy(update={"vessel": cfg_bare})
    res_bare = SimulationRunner().run(sc_bare)

    # Extract max heel and final speed
    sog_code0 = res_code0.recorder.records[-1].gt.vessel.sog_m_s
    sog_main = res_main.recorder.records[-1].gt.vessel.sog_m_s
    sog_reef2 = res_reef2.recorder.records[-1].gt.vessel.sog_m_s
    sog_bare = res_bare.recorder.records[-1].gt.vessel.sog_m_s

    heel_code0 = max(abs(r.gt.vessel.heel_deg) for r in res_code0.recorder.records)
    heel_main = max(abs(r.gt.vessel.heel_deg) for r in res_main.recorder.records)
    heel_reef2 = max(abs(r.gt.vessel.heel_deg) for r in res_reef2.recorder.records)
    heel_bare = max(abs(r.gt.vessel.heel_deg) for r in res_bare.recorder.records)

    # Physics assertions:
    # 1. Code 0 produces higher speed and heel than Full Main
    assert sog_code0 > sog_main
    assert heel_code0 >= heel_main

    # 2. Full Main produces higher speed and heel than Reef 2
    assert sog_main > sog_reef2
    assert heel_main > heel_reef2

    # 3. Bare poles has minimal heel (hydro/wave only) and lowest speed
    assert sog_reef2 > sog_bare
    assert heel_reef2 > heel_bare
