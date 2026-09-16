"""Unit tests for environmental physics models (WindModel, WaveModel, CurrentModel)."""

from __future__ import annotations

import math

from sia_sim.physics.environment import (
    ActiveGust,
    ActiveWaveImpact,
    CurrentModel,
    WaveModel,
    WindModel,
)


class TestWindModel:
    def test_base_wind_constant(self) -> None:
        wind = WindModel(base_tws_m_s=10.0, base_twa_deg=45.0)
        speed, direction = wind.evaluate(0)
        assert speed == 10.0
        assert direction == 45.0

        speed_later, dir_later = wind.evaluate(5000)
        assert speed_later == 10.0
        assert dir_later == 45.0

    def test_gust_profile_smooth_envelope(self) -> None:
        wind = WindModel(base_tws_m_s=10.0, base_twa_deg=60.0)
        gust = ActiveGust(
            event_id="GUST-1",
            start_time_ms=1000,
            duration_ms=4000,
            peak_speed_increase_m_s=6.0,
            direction_shift_deg=10.0,
        )
        wind.add_gust(gust)

        # Before gust
        s0, d0 = wind.evaluate(500)
        assert s0 == 10.0
        assert d0 == 60.0

        # At peak (midpoint of gust, 1000 + 2000 = 3000ms)
        s_peak, d_peak = wind.evaluate(3000)
        assert math.isclose(s_peak, 16.0, rel_tol=1e-3)
        assert math.isclose(d_peak, 70.0, rel_tol=1e-3)

        # After gust expiration (>5000ms)
        s_after, d_after = wind.evaluate(6000)
        assert s_after == 10.0
        assert d_after == 60.0

    def test_turbulence_living_wind_fluctuations(self) -> None:
        """Verify living wind model with enable_turbulence=True produces realistic continuous fluctuations."""
        wind = WindModel(base_tws_m_s=10.0, base_twa_deg=60.0, seed=42, enable_turbulence=True)
        # At T=0, matches initial state
        s0, d0 = wind.evaluate(0)
        assert math.isclose(s0, 10.0, rel_tol=1e-5)
        assert math.isclose(d0, 60.0, rel_tol=1e-5)

        speeds = [wind.evaluate(t * 1000)[0] for t in range(1, 30)]
        directions = [wind.evaluate(t * 1000)[1] for t in range(1, 30)]

        # Verify speeds and directions fluctuate and are not static
        assert min(speeds) < max(speeds)
        assert min(directions) < max(directions)
        # Verify fluctuations stay within realistic marine bounds
        for s in speeds:
            assert 6.0 <= s <= 16.0
        for d in directions:
            assert 45.0 <= d <= 75.0

    def test_turbulence_seed_diversity(self) -> None:
        """Verify different seeds produce distinct wind trajectories."""
        wind_seed42 = WindModel(base_tws_m_s=10.0, base_twa_deg=60.0, seed=42, enable_turbulence=True)
        wind_seed99 = WindModel(base_tws_m_s=10.0, base_twa_deg=60.0, seed=99, enable_turbulence=True)

        samples42 = [wind_seed42.evaluate(t * 1000) for t in range(1, 20)]
        samples99 = [wind_seed99.evaluate(t * 1000) for t in range(1, 20)]

        # Must diverge because different seeds create distinct harmonic profiles
        assert samples42 != samples99

    def test_turbulence_bit_for_bit_determinism(self) -> None:
        """Verify same seed produces identical sequence across multiple instances."""
        w1 = WindModel(base_tws_m_s=12.0, base_twa_deg=90.0, seed=123, enable_turbulence=True)
        w2 = WindModel(base_tws_m_s=12.0, base_twa_deg=90.0, seed=123, enable_turbulence=True)

        for t_ms in range(0, 30000, 100):
            assert w1.evaluate(t_ms) == w2.evaluate(t_ms)


class TestWaveModel:
    def test_dispersion_kinematics(self) -> None:
        wave = WaveModel(wave_height_m=3.0, wave_period_s=7.0, wave_direction_deg=65.0)
        # Deep water wavelength = g * T^2 / (2 * pi) approx 9.80665 * 49 / 6.283185 = 76.47 m
        assert math.isclose(wave.wavelength_m, 76.48, rel_tol=1e-2)
        assert wave.wave_height_m == 3.0
        assert wave.wave_period_s == 7.0

    def test_wave_elevation_spatial(self) -> None:
        wave = WaveModel(wave_height_m=2.0, wave_period_s=6.0, wave_direction_deg=0.0)
        # At origin (0, 0) and t=0, eta = H/2 = 1.0
        eta0 = wave.wave_elevation(0.0, 0.0, 0.0)
        assert math.isclose(eta0, 1.0, rel_tol=1e-5)

    def test_wave_impact_event(self) -> None:
        wave = WaveModel(wave_height_m=3.0, wave_period_s=7.0)
        impact = ActiveWaveImpact(
            event_id="IMPACT-1",
            impact_time_ms=5000,
            duration_ms=1000,
            impact_force_n=10000.0,
            impact_roll_moment_nm=25000.0,
        )
        wave.add_impact(impact)

        # Before impact
        f0, rm0, ym0 = wave.evaluate_impact(4000)
        assert f0 == 0.0
        assert rm0 == 0.0
        assert ym0 == 0.0

        # During impact
        f_mid, rm_mid, ym_mid = wave.evaluate_impact(5200)
        assert f_mid > 0.0
        assert rm_mid > 0.0
        assert ym_mid != 0.0

        # After impact
        f_after, rm_after, ym_after = wave.evaluate_impact(7000)
        assert f_after == 0.0
        assert rm_after == 0.0
        assert ym_after == 0.0


class TestCurrentModel:
    def test_current_constant(self) -> None:
        curr = CurrentModel(current_speed_m_s=0.75, current_direction_deg=180.0)
        spd, heading = curr.evaluate()
        assert spd == 0.75
        assert heading == 180.0
