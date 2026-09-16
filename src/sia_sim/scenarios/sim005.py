"""Canonical SIM-005 Broach Precursor scenario preset (GOLD-01)."""

from __future__ import annotations

import json
from pathlib import Path

from sia_sim.contracts.scenario import Scenario, ScenarioEvent, create_vessel_config


def get_sim005_scenario(seed: int = 42) -> Scenario:
    """Returns canonical SIM-005 Broach Precursor scenario matching hydrodynamic parameters."""
    return Scenario(
        scenario_id="SIM-005",
        scenario_version="1.0.0",
        name="Broach Precursor Golden Scenario",
        description=(
            "IOR monohull broach precursor verification scenario: beam/broad reach sailing "
            "followed by leeward wave roll moment impact and gust strike."
        ),
        duration_ms=20000,
        initial_tws_kt=15.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=2.0,
        initial_wave_period_s=6.0,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=5.0,
            initial_heel_deg=-15.0,
        ),
        events=(
            ScenarioEvent(
                sim_time_ms=10000,
                event_id="EVT-WAVE-01",
                event_type="wave_impact",
                parameters={
                    "impact_force_n": 12000.0,
                    "impact_roll_moment_nm": -25000.0,
                    "duration_ms": 2000,
                },
            ),
            ScenarioEvent(
                sim_time_ms=12000,
                event_id="EVT-GUST-01",
                event_type="wind_gust",
                parameters={"tws_kt": 18.0, "duration_s": 4.0, "direction_shift_deg": 15.0},
            ),
        ),
        seed=seed,
    )


def get_benign_scenario(seed: int = 100) -> Scenario:
    """Returns nominal benign sailing scenario with zero hazard onset."""
    return Scenario(
        scenario_id="SIM-BENIGN",
        scenario_version="1.0.0",
        name="Calm Reach",
        description="Benign calm sailing conditions with zero broach precursor risk.",
        duration_ms=10000,
        initial_tws_kt=8.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=0.5,
        initial_wave_period_s=4.0,
        vessel=create_vessel_config(
            initial_heading_deg=45.0,
            initial_sog_kt=4.0,
            initial_heel_deg=-5.0,
        ),
        events=(),
        seed=seed,
    )


def load_scenario(path_or_name: str, seed: int = 42) -> Scenario:
    """Loads a Scenario from a canonical preset ID or a JSON file path."""
    name_clean = path_or_name.lower().replace("preset-", "").replace("preset_", "")
    if name_clean in ("sim-005", "sim005", "broach"):
        return get_sim005_scenario(seed=seed)
    if name_clean in ("sim-benign", "benign"):
        return get_benign_scenario(seed=seed)

    from sia_sim.scenarios.presets import WORLD_PRESETS, get_preset_by_id

    if name_clean in WORLD_PRESETS or str(path_or_name).lower() in WORLD_PRESETS:
        return get_preset_by_id(path_or_name, seed=seed)

    file_path = Path(path_or_name)
    if not file_path.exists():
        raise FileNotFoundError(f"Scenario file or preset not found: {path_or_name}")

    content = file_path.read_text(encoding="utf-8")
    data = json.loads(content)
    if "seed" not in data or seed != 42:
        data["seed"] = seed
    if "events" in data and isinstance(data["events"], list):
        data["events"] = tuple(data["events"])
    return Scenario.model_validate(data)
