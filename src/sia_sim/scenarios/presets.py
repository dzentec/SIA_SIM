"""Realistic Marine Environment World Presets and Custom Preset Registry.

Provides 4 living sea background presets with zero forced events by default:
1. PRESET-HARBOUR: Calm harbour / motoring / gentle breeze.
2. PRESET-COASTAL-CRUISE: Moderate reach sailing in lively coastal seas.
3. PRESET-FRESH-BREEZE: Fresh breeze with steep chop and active wave action.
4. PRESET-GALE-BROACH: Heavy gale conditions with severe seas and broach risk.
"""

from __future__ import annotations

from typing import Any

from sia_sim.contracts.scenario import Scenario, ScenarioEvent, create_vessel_config


def get_harbour_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET-HARBOUR: calm waters, light ripple, engine or light sail."""
    return Scenario(
        scenario_id="PRESET-HARBOUR",
        scenario_version="1.1.0",
        name="Calm Harbour / Mooring",
        description="Protected waters with light 4 kt air, 0.2 m ripple, smooth forward transit.",
        duration_ms=duration_ms,
        initial_tws_kt=4.0,
        initial_twa_deg=30.0,
        initial_wave_height_m=0.2,
        initial_wave_period_s=3.0,
        vessel=create_vessel_config(
            initial_heading_deg=45.0,
            initial_sog_kt=2.5,
            initial_heel_deg=-1.5,
        ),
        events=(),
        seed=seed,
    )


def get_coastal_cruise_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET-COASTAL-CRUISE: ideal cruising conditions, moderate swell."""
    return Scenario(
        scenario_id="PRESET-COASTAL-CRUISE",
        scenario_version="1.1.0",
        name="Coastal Cruise (Moderate Reach)",
        description="Steady 13 kt true wind, 1.0 m swell, sailing at 5.8 kt with 12 deg heel.",
        duration_ms=duration_ms,
        initial_tws_kt=13.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=1.0,
        initial_wave_period_s=4.5,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=5.8,
            initial_heel_deg=-12.0,
        ),
        events=(),
        seed=seed,
    )


def get_fresh_breeze_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET-FRESH-BREEZE: lively sailing in fresh breeze and steep chop."""
    return Scenario(
        scenario_id="PRESET-FRESH-BREEZE",
        scenario_version="1.1.0",
        name="Fresh Breeze (Steep Chop)",
        description="Fresh 21 kt wind, 2.1 m steep waves, 7.2 kt SOG with dynamic wave motion.",
        duration_ms=duration_ms,
        initial_tws_kt=21.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=2.1,
        initial_wave_period_s=5.0,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=7.2,
            initial_heel_deg=-20.0,
        ),
        events=(),
        seed=seed,
    )


def get_gale_broach_preset(
    seed: int = 42,
    duration_ms: int = 20000,
    with_events: bool = False,
) -> Scenario:
    """Returns PRESET-GALE-BROACH: severe 28 kt gale, 3.2 m breaking sea."""
    events: tuple[ScenarioEvent, ...] = ()
    if with_events:
        events = (
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
        )

    return Scenario(
        scenario_id="PRESET-GALE-BROACH",
        scenario_version="1.1.0",
        name="Gale / Broach Risk",
        description="Near-gale 28 kt wind, 3.2 m heavy seas, high speed and capsize leverage.",
        duration_ms=duration_ms,
        initial_tws_kt=28.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=3.2,
        initial_wave_period_s=6.5,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=8.5,
            initial_heel_deg=-24.0,
        ),
        events=events,
        seed=seed,
    )


WORLD_PRESETS = {
    "harbour": get_harbour_preset,
    "cruise": get_coastal_cruise_preset,
    "fresh": get_fresh_breeze_preset,
    "gale": get_gale_broach_preset,
}


def list_world_presets() -> list[dict[str, Any]]:
    """Returns descriptor metadata for all registered presets."""
    return [
        {
            "id": "harbour",
            "name": "Calm Harbour",
            "description": "TWS 4 kt | Wave 0.2m (3.0s) | Smooth motoring / calm ripple",
            "tws_kt": 4.0,
            "wave_height_m": 0.2,
            "wave_period_s": 3.0,
            "sog_kt": 2.5,
        },
        {
            "id": "cruise",
            "name": "Coastal Cruise",
            "description": "TWS 13 kt | Wave 1.0m (4.5s) | Moderate reach with 12° heel",
            "tws_kt": 13.0,
            "wave_height_m": 1.0,
            "wave_period_s": 4.5,
            "sog_kt": 5.8,
        },
        {
            "id": "fresh",
            "name": "Fresh Breeze",
            "description": "TWS 21 kt | Wave 2.1m (5.0s) | Steep chop, active roll/pitch",
            "tws_kt": 21.0,
            "wave_height_m": 2.1,
            "wave_period_s": 5.0,
            "sog_kt": 7.2,
        },
        {
            "id": "gale",
            "name": "Gale / Broach Risk",
            "description": "TWS 28 kt | Wave 3.2m (6.5s) | Heavy sea, broach threshold",
            "tws_kt": 28.0,
            "wave_height_m": 3.2,
            "wave_period_s": 6.5,
            "sog_kt": 8.5,
        },
    ]


def get_preset_by_id(
    preset_id: str,
    seed: int = 42,
    duration_s: int = 20,
    with_events: bool = False,
) -> Scenario:
    """Retrieve Scenario preset by identifier."""
    pid = preset_id.lower().replace("preset-", "").replace("preset_", "")
    duration_ms = duration_s * 1000

    if pid in ("harbour", "calm", "mooring", "sim-benign", "benign"):
        return get_harbour_preset(seed=seed, duration_ms=duration_ms)
    if pid in ("cruise", "coastal", "coastal_cruise", "reach"):
        return get_coastal_cruise_preset(seed=seed, duration_ms=duration_ms)
    if pid in ("fresh", "fresh_breeze", "chop", "rough"):
        return get_fresh_breeze_preset(seed=seed, duration_ms=duration_ms)
    if pid in ("gale", "broach"):
        return get_gale_broach_preset(seed=seed, duration_ms=duration_ms, with_events=with_events)
    if pid in ("sim-005", "sim005"):
        # Explicit SIM-005 scenario keeps default verification events
        return get_gale_broach_preset(
            seed=seed,
            duration_ms=duration_ms,
            with_events=True,
        )

    # Fallback to cruise
    return get_coastal_cruise_preset(seed=seed, duration_ms=duration_ms)
