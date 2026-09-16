"""Realistic Marine Environment World Presets and Custom Preset Registry.

Provides 10 realistic living sea background presets covering Fair Weather,
Moderate, Heavy, Extreme, Special, and Stress Test conditions with zero forced events by default:
1. Calm Harbour (Mirror) - 2 kt, 0.1 m wave
2. Light Breeze (Smooth) - 8 kt, 0.5 m wave
3. Coastal Cruise (Moderate) - 13 kt, 1.0 m wave
4. Fresh Breeze (Whitecaps) - 19 kt, 1.8 m wave
5. Strong Wind (Choppy Sea) - 24 kt, 2.5 m wave
6. Near Gale (Rough) - 30 kt, 3.5 m wave
7. Gale Force (Heavy Sea) - 38 kt, 5.5 m wave
8. Storm / Survival - 48 kt, 8.5 m wave
9. Ocean Swell (No Wind) - 5 kt, 2.5 m wave (long period)
10. Hurricane / Stress Test - 65 kt, 11.0 m wave
"""

from __future__ import annotations

from typing import Any

from sia_sim.contracts.scenario import Scenario, ScenarioEvent, create_vessel_config

# ---------------------------------------------------------------------------
# Canonical World Preset Configurations (JSON-compatible metadata)
# ---------------------------------------------------------------------------

WORLD_PRESET_CONFIGS: list[dict[str, Any]] = [
    {
        "id": 1,
        "slug": "calm_harbour",
        "name": "Calm Harbour (Mirror)",
        "category": "Fair Weather",
        "wind": {
            "speed_knots": 2.0,
            "speed_m_s": 1.0,
        },
        "wave": {
            "height_m": 0.1,
            "period_s_min": 2.0,
            "period_s_max": 3.0,
        },
        "description": "Тест маневрирования в марине, швартовка",
    },
    {
        "id": 2,
        "slug": "light_breeze",
        "name": "Light Breeze (Smooth)",
        "category": "Fair Weather",
        "wind": {
            "speed_knots": 8.0,
            "speed_m_s": 4.1,
        },
        "wave": {
            "height_m": 0.5,
            "period_s_min": 3.0,
            "period_s_max": 4.0,
        },
        "description": "Учебный режим, лёгкая рябь, тесты AI",
    },
    {
        "id": 3,
        "slug": "coastal_cruise",
        "name": "Coastal Cruise (Moderate)",
        "category": "Moderate",
        "wind": {
            "speed_knots": 13.0,
            "speed_m_s": 6.7,
        },
        "wave": {
            "height_m": 1.0,
            "period_s_min": 4.0,
            "period_s_max": 5.0,
        },
        "description": "Стандартный прибрежный круиз, идеальный парусный день",
    },
    {
        "id": 4,
        "slug": "fresh_breeze",
        "name": "Fresh Breeze (Whitecaps)",
        "category": "Moderate",
        "wind": {
            "speed_knots": 19.0,
            "speed_m_s": 9.8,
        },
        "wave": {
            "height_m": 1.8,
            "period_s_min": 5.0,
            "period_s_max": 6.0,
        },
        "description": "Энергичный ход, появление белых барашков",
    },
    {
        "id": 5,
        "slug": "strong_wind",
        "name": "Strong Wind (Choppy Sea)",
        "category": "Heavy",
        "wind": {
            "speed_knots": 24.0,
            "speed_m_s": 12.3,
        },
        "wave": {
            "height_m": 2.5,
            "period_s_min": 5.0,
            "period_s_max": 7.0,
        },
        "description": "Короткая крутая волна, рубеж рифления парусов",
    },
    {
        "id": 6,
        "slug": "near_gale",
        "name": "Near Gale (Rough)",
        "category": "Heavy",
        "wind": {
            "speed_knots": 30.0,
            "speed_m_s": 15.4,
        },
        "wave": {
            "height_m": 3.5,
            "period_s_min": 7.0,
            "period_s_max": 8.0,
        },
        "description": "Сильная качка, брызги, тест авторулевого",
    },
    {
        "id": 7,
        "slug": "gale_force",
        "name": "Gale Force (Heavy Sea)",
        "category": "Extreme",
        "wind": {
            "speed_knots": 38.0,
            "speed_m_s": 19.5,
        },
        "wave": {
            "height_m": 5.5,
            "period_s_min": 8.0,
            "period_s_max": 10.0,
        },
        "description": "Настоящий шторм, управление на попутной волне",
    },
    {
        "id": 8,
        "slug": "storm_survival",
        "name": "Storm / Survival",
        "category": "Extreme",
        "wind": {
            "speed_knots": 48.0,
            "speed_m_s": 24.7,
        },
        "wave": {
            "height_m": 8.5,
            "period_s_min": 10.0,
            "period_s_max": 12.0,
        },
        "description": "Штормование, огромные гребни, тест выживаемости",
    },
    {
        "id": 9,
        "slug": "ocean_swell",
        "name": "Ocean Swell (No Wind)",
        "category": "Special",
        "wind": {
            "speed_knots": 5.0,
            "speed_m_s": 2.6,
        },
        "wave": {
            "height_m": 2.5,
            "period_s_min": 12.0,
            "period_s_max": 15.0,
        },
        "description": "Длинная океанская зыбь без ветра (тест валкости/бортовой качки)",
    },
    {
        "id": 10,
        "slug": "hurricane",
        "name": "Hurricane / Stress Test",
        "category": "Stress Test",
        "wind": {
            "speed_knots": 65.0,
            "speed_m_s": 33.5,
        },
        "wave": {
            "height_m": 11.0,
            "period_s_min": 14.0,
            "period_s_max": 20.0,
        },
        "description": "Максимальный стресс-тест физики и алгоритмов",
    },
]


# ---------------------------------------------------------------------------
# Individual Preset Constructors
# ---------------------------------------------------------------------------


def get_calm_harbour_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 1: Calm Harbour (Mirror) - 2 kt wind, 0.1 m wave."""
    return Scenario(
        scenario_id="PRESET-01-CALM-HARBOUR",
        scenario_version="1.2.0",
        name="Calm Harbour (Mirror)",
        description="Тест маневрирования в марине, швартовка",
        duration_ms=duration_ms,
        initial_tws_kt=2.0,
        initial_twa_deg=30.0,
        initial_wave_height_m=0.1,
        initial_wave_period_s=2.5,
        vessel=create_vessel_config(
            initial_heading_deg=45.0,
            initial_sog_kt=2.0,
            initial_heel_deg=-1.0,
        ),
        events=(),
        seed=seed,
    )


# Backward-compatible alias
get_harbour_preset = get_calm_harbour_preset


def get_light_breeze_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 2: Light Breeze (Smooth) - 8 kt wind, 0.5 m wave."""
    return Scenario(
        scenario_id="PRESET-02-LIGHT-BREEZE",
        scenario_version="1.2.0",
        name="Light Breeze (Smooth)",
        description="Учебный режим, лёгкая рябь, тесты AI",
        duration_ms=duration_ms,
        initial_tws_kt=8.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=0.5,
        initial_wave_period_s=3.5,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=4.5,
            initial_heel_deg=-5.0,
        ),
        events=(),
        seed=seed,
    )


def get_coastal_cruise_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 3: Coastal Cruise (Moderate) - 13 kt wind, 1.0 m wave."""
    return Scenario(
        scenario_id="PRESET-03-COASTAL-CRUISE",
        scenario_version="1.2.0",
        name="Coastal Cruise (Moderate)",
        description="Стандартный прибрежный круиз, идеальный парусный день",
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
    """Returns PRESET 4: Fresh Breeze (Whitecaps) - 19 kt wind, 1.8 m wave."""
    return Scenario(
        scenario_id="PRESET-04-FRESH-BREEZE",
        scenario_version="1.2.0",
        name="Fresh Breeze (Whitecaps)",
        description="Энергичный ход, появление белых барашков",
        duration_ms=duration_ms,
        initial_tws_kt=19.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=1.8,
        initial_wave_period_s=5.5,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=7.0,
            initial_heel_deg=-18.0,
        ),
        events=(),
        seed=seed,
    )


def get_strong_wind_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 5: Strong Wind (Choppy Sea) - 24 kt wind, 2.5 m wave."""
    return Scenario(
        scenario_id="PRESET-05-STRONG-WIND",
        scenario_version="1.2.0",
        name="Strong Wind (Choppy Sea)",
        description="Короткая крутая волна, рубеж рифления парусов",
        duration_ms=duration_ms,
        initial_tws_kt=24.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=2.5,
        initial_wave_period_s=6.0,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=7.8,
            initial_heel_deg=-22.0,
        ),
        events=(),
        seed=seed,
    )


def get_near_gale_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 6: Near Gale (Rough) - 30 kt wind, 3.5 m wave."""
    return Scenario(
        scenario_id="PRESET-06-NEAR-GALE",
        scenario_version="1.2.0",
        name="Near Gale (Rough)",
        description="Сильная качка, брызги, тест авторулевого",
        duration_ms=duration_ms,
        initial_tws_kt=30.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=3.5,
        initial_wave_period_s=7.5,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=8.5,
            initial_heel_deg=-25.0,
        ),
        events=(),
        seed=seed,
    )


def get_gale_force_preset(
    seed: int = 42,
    duration_ms: int = 20000,
    with_events: bool = False,
) -> Scenario:
    """Returns PRESET 7: Gale Force (Heavy Sea) - 38 kt wind, 5.5 m wave."""
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
        scenario_id="PRESET-07-GALE-FORCE",
        scenario_version="1.2.0",
        name="Gale Force (Heavy Sea)",
        description="Настоящий шторм, управление на попутной волне",
        duration_ms=duration_ms,
        initial_tws_kt=38.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=5.5,
        initial_wave_period_s=9.0,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=9.0,
            initial_heel_deg=-28.0,
        ),
        events=events,
        seed=seed,
    )


# Backward-compatible alias
get_gale_broach_preset = get_gale_force_preset


def get_storm_survival_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 8: Storm / Survival - 48 kt wind, 8.5 m wave."""
    return Scenario(
        scenario_id="PRESET-08-STORM-SURVIVAL",
        scenario_version="1.2.0",
        name="Storm / Survival",
        description="Штормование, огромные гребни, тест выживаемости",
        duration_ms=duration_ms,
        initial_tws_kt=48.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=8.5,
        initial_wave_period_s=11.0,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=9.5,
            initial_heel_deg=-30.0,
        ),
        events=(),
        seed=seed,
    )


def get_ocean_swell_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 9: Ocean Swell (No Wind) - 5 kt wind, 2.5 m long-period swell."""
    return Scenario(
        scenario_id="PRESET-09-OCEAN-SWELL",
        scenario_version="1.2.0",
        name="Ocean Swell (No Wind)",
        description="Длинная океанская зыбь без ветра (тест валкости/бортовой качки)",
        duration_ms=duration_ms,
        initial_tws_kt=5.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=2.5,
        initial_wave_period_s=13.5,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=3.0,
            initial_heel_deg=-2.0,
        ),
        events=(),
        seed=seed,
    )


def get_hurricane_preset(seed: int = 42, duration_ms: int = 20000) -> Scenario:
    """Returns PRESET 10: Hurricane / Stress Test - 65 kt wind, 11.0 m wave."""
    return Scenario(
        scenario_id="PRESET-10-HURRICANE",
        scenario_version="1.2.0",
        name="Hurricane / Stress Test",
        description="Максимальный стресс-тест физики и алгоритмов",
        duration_ms=duration_ms,
        initial_tws_kt=65.0,
        initial_twa_deg=0.0,
        initial_wave_height_m=11.0,
        initial_wave_period_s=17.0,
        vessel=create_vessel_config(
            initial_heading_deg=65.0,
            initial_sog_kt=10.0,
            initial_heel_deg=-35.0,
        ),
        events=(),
        seed=seed,
    )


WORLD_PRESETS = {
    # 1. Calm Harbour
    "1": get_calm_harbour_preset,
    "calm_harbour": get_calm_harbour_preset,
    "harbour": get_calm_harbour_preset,
    "calm": get_calm_harbour_preset,
    "mooring": get_calm_harbour_preset,
    # 2. Light Breeze
    "2": get_light_breeze_preset,
    "light_breeze": get_light_breeze_preset,
    "smooth": get_light_breeze_preset,
    # 3. Coastal Cruise
    "3": get_coastal_cruise_preset,
    "coastal_cruise": get_coastal_cruise_preset,
    "cruise": get_coastal_cruise_preset,
    "coastal": get_coastal_cruise_preset,
    "moderate": get_coastal_cruise_preset,
    # 4. Fresh Breeze
    "4": get_fresh_breeze_preset,
    "fresh_breeze": get_fresh_breeze_preset,
    "fresh": get_fresh_breeze_preset,
    "whitecaps": get_fresh_breeze_preset,
    # 5. Strong Wind
    "5": get_strong_wind_preset,
    "strong_wind": get_strong_wind_preset,
    "choppy": get_strong_wind_preset,
    # 6. Near Gale
    "6": get_near_gale_preset,
    "near_gale": get_near_gale_preset,
    "rough": get_near_gale_preset,
    # 7. Gale Force
    "7": get_gale_force_preset,
    "gale_force": get_gale_force_preset,
    "gale": get_gale_force_preset,
    "broach": get_gale_force_preset,
    # 8. Storm / Survival
    "8": get_storm_survival_preset,
    "storm_survival": get_storm_survival_preset,
    "storm": get_storm_survival_preset,
    "survival": get_storm_survival_preset,
    # 9. Ocean Swell
    "9": get_ocean_swell_preset,
    "ocean_swell": get_ocean_swell_preset,
    "swell": get_ocean_swell_preset,
    # 10. Hurricane / Stress Test
    "10": get_hurricane_preset,
    "hurricane": get_hurricane_preset,
    "stress_test": get_hurricane_preset,
}


def list_world_presets() -> list[dict[str, Any]]:
    """Returns rich descriptor metadata for all registered presets."""
    result: list[dict[str, Any]] = []
    for cfg in WORLD_PRESET_CONFIGS:
        fn = WORLD_PRESETS[str(cfg["id"])]
        sc = fn(seed=42, duration_ms=20000)
        item = {
            **cfg,
            "tws_kt": sc.initial_tws_kt,
            "wave_height_m": sc.initial_wave_height_m,
            "wave_period_s": sc.initial_wave_period_s,
            "sog_kt": sc.vessel.initial_sog_kt,
            "heading_deg": sc.vessel.initial_heading_deg,
            "heel_deg": sc.vessel.initial_heel_deg,
            "twa_deg": sc.initial_twa_deg,
        }
        result.append(item)
    return result


def get_preset_by_id(
    preset_id: str | int,
    seed: int = 42,
    duration_s: int = 20,
    with_events: bool = False,
) -> Scenario:
    """Retrieve Scenario preset by identifier."""
    pid = str(preset_id).lower().replace("preset-", "").replace("preset_", "")
    duration_ms = duration_s * 1000

    if pid in ("sim-005", "sim005"):
        # Explicit SIM-005 scenario keeps default verification events
        return get_gale_force_preset(
            seed=seed,
            duration_ms=duration_ms,
            with_events=True,
        )

    if pid in WORLD_PRESETS:
        fn = WORLD_PRESETS[pid]
        if fn is get_gale_force_preset:
            return get_gale_force_preset(
                seed=seed, duration_ms=duration_ms, with_events=with_events
            )
        return fn(seed=seed, duration_ms=duration_ms)

    # Fallback to coastal cruise
    return get_coastal_cruise_preset(seed=seed, duration_ms=duration_ms)


# ---------------------------------------------------------------------------
# Vessel Presets Registry & Sail Plan Configuration
# ---------------------------------------------------------------------------

SAIL_PLAN_PERCENTAGES: dict[str, float] = {
    "GENNAKER": 150.0,
    "PARASAILOR": 140.0,
    "CODE_ZERO": 130.0,
    "FULL_MAIN": 100.0,
    "REEF_1": 75.0,
    "REEF_2": 50.0,
    "REEF_3": 35.0,
    "GENOA_ONLY": 50.0,
    "JIB_ONLY": 40.0,
    "STORM_JIB": 25.0,
    "BARE_POLES": 0.0,
}

VESSEL_PRESETS: dict[str, dict[str, Any]] = {
    "beneteau_oceanis_45": {
        "id": "beneteau_oceanis_45",
        "name": "Beneteau Oceanis 45",
        "archetype": "modern_cruiser",
        "description": "Modern 45ft wide-beam cruising yacht with high form stability and twin rudders.",
        "loa_m": 13.94,
        "beam_m": 4.50,
        "displacement_kg": 10550.0,
        "sail_area_m2": 100.0,
        "mast_height_m": 19.5,
        "available_sails": [
            {"id": "CODE_ZERO", "name": "Code 0 (130%)", "trim_pct": 130.0, "icon": "⛵"},
            {"id": "FULL_MAIN", "name": "Full Main (100%)", "trim_pct": 100.0, "icon": "⛵"},
            {"id": "REEF_1", "name": "Reef 1 (75%)", "trim_pct": 75.0, "icon": "📉"},
            {"id": "REEF_2", "name": "Reef 2 (50%)", "trim_pct": 50.0, "icon": "📉"},
            {"id": "STORM_JIB", "name": "Storm Jib (25%)", "trim_pct": 25.0, "icon": "⛈"},
            {"id": "BARE_POLES", "name": "Bare Poles (0%)", "trim_pct": 0.0, "icon": "⚙"},
        ],
    },
    "monohull_ior": {
        "id": "monohull_ior",
        "name": "IOR Classic 10.5m",
        "archetype": "ior_classic_narrow_stern",
        "description": "Classic 34ft IOR racer/cruiser with narrow stern, single deep rudder, broach-prone.",
        "loa_m": 10.5,
        "beam_m": 3.2,
        "displacement_kg": 4500.0,
        "sail_area_m2": 45.0,
        "mast_height_m": 14.0,
        "available_sails": [
            {"id": "FULL_MAIN", "name": "Full Main (100%)", "trim_pct": 100.0, "icon": "⛵"},
            {"id": "REEF_1", "name": "Reef 1 (75%)", "trim_pct": 75.0, "icon": "📉"},
            {"id": "REEF_2", "name": "Reef 2 (50%)", "trim_pct": 50.0, "icon": "📉"},
            {"id": "STORM_JIB", "name": "Storm Jib (25%)", "trim_pct": 25.0, "icon": "⛈"},
            {"id": "BARE_POLES", "name": "Bare Poles (0%)", "trim_pct": 0.0, "icon": "⚙"},
        ],
    },
}


def list_vessel_presets() -> list[dict[str, Any]]:
    """Returns descriptor metadata for all registered vessel presets."""
    return list(VESSEL_PRESETS.values())


def get_vessel_preset_config(
    vessel_id: str = "beneteau_oceanis_45",
    sail_plan: str = "FULL_MAIN",
    initial_heading_deg: float = 65.0,
    initial_sog_kt: float = 6.0,
    initial_heel_deg: float = 0.0,
) -> Any:
    """Creates a VesselConfig for a given vessel preset ID and sail configuration."""
    from sia_sim.contracts.scenario import (
        BENETEAU_OCEANIS_45_CONFIG,
        DEFAULT_VESSEL_CONFIG,
    )

    vid = vessel_id.lower().replace("-", "_")
    plan_key = sail_plan.upper()
    trim_pct = SAIL_PLAN_PERCENTAGES.get(plan_key, 100.0)

    if "beneteau" in vid or "oceanis" in vid:
        return BENETEAU_OCEANIS_45_CONFIG.model_copy(
            update={
                "sail_plan": plan_key,
                "sail_trim_pct": trim_pct,
                "initial_heading_deg": initial_heading_deg,
                "initial_sog_kt": initial_sog_kt,
                "initial_heel_deg": initial_heel_deg,
            }
        )

    return DEFAULT_VESSEL_CONFIG.model_copy(
        update={
            "sail_plan": plan_key,
            "sail_trim_pct": trim_pct,
            "initial_heading_deg": initial_heading_deg,
            "initial_sog_kt": initial_sog_kt,
            "initial_heel_deg": initial_heel_deg,
        }
    )
