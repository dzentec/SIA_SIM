"""Scenario catalog and preset loader package."""

from __future__ import annotations

from sia_sim.scenarios.presets import (
    get_coastal_cruise_preset,
    get_fresh_breeze_preset,
    get_gale_broach_preset,
    get_harbour_preset,
    get_preset_by_id,
    list_world_presets,
)
from sia_sim.scenarios.sim005 import get_benign_scenario, get_sim005_scenario, load_scenario

__all__ = [
    "get_benign_scenario",
    "get_coastal_cruise_preset",
    "get_fresh_breeze_preset",
    "get_gale_broach_preset",
    "get_harbour_preset",
    "get_preset_by_id",
    "get_sim005_scenario",
    "list_world_presets",
    "load_scenario",
]
