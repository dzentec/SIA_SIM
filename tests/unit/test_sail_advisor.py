from sia_sim.contracts.data import (
    ActuatorState,
    GPSReading,
    IMUReading,
    SensorFrame,
    WindReading,
)
from sia_sim.contracts.sails import (
    ALL_SAIL_IDS,
    SailSuitabilityStatus,
)
from sia_sim.contracts.scenario import create_vessel_config
from sia_sim.engine.runner import SimulationRunner
from sia_sim.sails.advisor import (
    evaluate_reefing_schedule,
    evaluate_sail_suitability,
    generate_sail_advisory,
    resolve_wardrobe_for_hull,
)
from sia_sim.scenarios import load_scenario
from sia_sim.sia.mock_sia import MockSIA


def test_wardrobe_resolution_monohull_vs_catamaran() -> None:
    """Test that catamaran overrides are applied properly from catalog v1.1."""
    mono_wardrobe = resolve_wardrobe_for_hull("monohull")
    cat_wardrobe = resolve_wardrobe_for_hull("catamaran")

    # Code Zero on catamaran has narrower TWS (4-14 vs 4-15) and max gust 18 kt
    mono_c0 = mono_wardrobe["code_zero"]
    cat_c0 = cat_wardrobe["code_zero"]

    assert mono_c0.wind_speed_range_kt == (4.0, 15.0)
    assert cat_c0.wind_speed_range_kt == (4.0, 14.0)
    assert cat_c0.max_gust_kt == 18.0

    # Parasailor on catamaran limits TWA to 160 vs 180 on monohull
    mono_para = mono_wardrobe["parasailor"]
    cat_para = cat_wardrobe["parasailor"]

    assert mono_para.optimal_twa_range_deg == (130.0, 180.0)
    assert cat_para.optimal_twa_range_deg == (120.0, 160.0)


def test_evaluate_sail_suitability_optimal_and_dangerous() -> None:
    """Test suitability status and safety gust triggers."""
    wardrobe = resolve_wardrobe_for_hull("catamaran")
    c0 = wardrobe["code_zero"]

    # 1. Optimal conditions: 8 kt wind, 75 deg TWA, gusts 10 kt
    eval_opt = evaluate_sail_suitability(c0, tws_kt=8.0, twa_deg=75.0, gust_kt=10.0)
    assert eval_opt.status == SailSuitabilityStatus.OPTIMAL
    assert eval_opt.score > 0.8

    # 2. Dangerous conditions: gust 22 kt exceeds cat Code 0 limit (18 kt)
    eval_dang = evaluate_sail_suitability(c0, tws_kt=12.0, twa_deg=75.0, gust_kt=22.0)
    assert eval_dang.status == SailSuitabilityStatus.DANGEROUS
    assert eval_dang.score == 0.0
    assert "превышает лимит" in eval_dang.reason


def test_evaluate_reefing_schedule() -> None:
    """Test mainsail reefing recommendations."""
    wardrobe = resolve_wardrobe_for_hull("monohull")
    main = wardrobe["mainsail_square_top"]

    # Light/Moderate (12 kt) -> 0 reefs
    reef_0, _ = evaluate_reefing_schedule(main, 12.0)
    assert reef_0 == 0

    # Moderate/Heavy (19 kt) -> Reef 1
    reef_1, note_1 = evaluate_reefing_schedule(main, 19.0)
    assert reef_1 == 1
    assert "1-й риф" in note_1

    # Heavy (27 kt) -> Reef 2
    reef_2, note_2 = evaluate_reefing_schedule(main, 27.0)
    assert reef_2 == 2
    assert "2-й риф" in note_2

    # Extreme (33 kt) -> Reef 3
    reef_3, note_3 = evaluate_reefing_schedule(main, 33.0)
    assert reef_3 == 3
    assert "3-й риф" in note_3


def test_inventory_filtering_strict_boundary() -> None:
    """Test that SIA only recommends sails present in the on-board inventory."""
    # Moderate air beam reach: 16 kt wind, 50 deg TWA
    # With full wardrobe, solent_jib is optimal headsail
    full_adv = generate_sail_advisory(
        tws_kt=16.0,
        twa_deg=50.0,
        hull_type="monohull",
        available_sails=ALL_SAIL_IDS,
    )
    assert full_adv.recommended_headsail == "solent_jib"

    # Now simulate a boat that does NOT have solent_jib on board (only genoa_furling and storm_jib)
    limited_sails = ("mainsail_square_top", "genoa_furling", "storm_jib")
    limited_adv = generate_sail_advisory(
        tws_kt=16.0,
        twa_deg=50.0,
        hull_type="monohull",
        available_sails=limited_sails,
    )

    # Must NEVER recommend solent_jib if not in available_sails
    assert limited_adv.recommended_headsail != "solent_jib"
    assert limited_adv.recommended_headsail in limited_sails


def test_mock_sia_respects_vessel_context() -> None:
    """Test MockSIA respects custom available sails and hull type."""
    sia = MockSIA(hull_type="catamaran", available_sails=["mainsail_square_top", "storm_jib"])

    # Provide sensor frame with storm conditions (35 kt) where storm_jib is suitable
    frame = SensorFrame(
        sim_time_ms=1000,
        imu=IMUReading(
            roll_deg=5.0,
            pitch_deg=0.0,
            roll_rate_deg_s=0.0,
            pitch_rate_deg_s=0.0,
            yaw_rate_deg_s=0.0,
            accel_x_m_s2=0.0,
            accel_y_m_s2=0.0,
            accel_z_m_s2=9.81,
            fault=False,
        ),
        gps=GPSReading(
            latitude_deg=43.0,
            longitude_deg=5.0,
            sog_kt=5.0,
            cog_deg=90.0,
            hdop=1.0,
            fault=False,
        ),
        wind=WindReading(apparent_wind_speed_kt=35.0, apparent_wind_angle_deg=80.0, fault=False),
        actuators=ActuatorState(rudder_angle_deg=0.0, mainsheet_pct=100.0, fault=False),
        sequence_number=1,
    )

    dec = sia.process(frame)
    assert dec is not None
    assert sia.last_sail_advisory is not None
    # Recommended headsail must be storm_jib because it's available and suitable in storm conditions
    assert sia.last_sail_advisory.recommended_headsail == "storm_jib"


def test_simulation_runner_with_custom_vessel_wardrobe() -> None:
    """Test full simulation run end-to-end with custom vessel and sail wardrobe."""
    scenario = load_scenario("cruise", seed=42)
    custom_vessel = create_vessel_config(
        loa_m=12.0,
        beam_m=3.8,
        displacement_kg=7500.0,
        hull_type="monohull",
        available_sails=("mainsail_square_top", "solent_jib"),
    )
    scenario = scenario.model_copy(update={"vessel": custom_vessel, "duration_ms": 1000})

    runner = SimulationRunner()
    result = runner.run(scenario)

    assert len(result.recorder.records) > 0
    assert result.evaluation.verdict in ("PASS", "FAIL")
