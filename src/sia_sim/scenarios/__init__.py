"""Scenario catalog and preset loader package."""

from __future__ import annotations

from sia_sim.scenarios.presets import (
    WORLD_PRESET_CONFIGS,
    WORLD_PRESETS,
    get_calm_harbour_preset,
    get_coastal_cruise_preset,
    get_fresh_breeze_preset,
    get_gale_broach_preset,
    get_gale_force_preset,
    get_harbour_preset,
    get_hurricane_preset,
    get_light_breeze_preset,
    get_near_gale_preset,
    get_ocean_swell_preset,
    get_preset_by_id,
    get_storm_survival_preset,
    get_strong_wind_preset,
    list_world_presets,
)
from sia_sim.scenarios.sim005 import get_benign_scenario, get_sim005_scenario, load_scenario

__all__ = [
    "WORLD_PRESETS",
    "WORLD_PRESET_CONFIGS",
    "get_benign_scenario",
    "get_calm_harbour_preset",
    "get_coastal_cruise_preset",
    "get_fresh_breeze_preset",
    "get_gale_broach_preset",
    "get_gale_force_preset",
    "get_harbour_preset",
    "get_hurricane_preset",
    "get_light_breeze_preset",
    "get_near_gale_preset",
    "get_ocean_swell_preset",
    "get_preset_by_id",
    "get_sim005_scenario",
    "get_storm_survival_preset",
    "get_strong_wind_preset",
    "list_world_presets",
    "load_scenario",
]
