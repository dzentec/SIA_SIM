"""WorldModel maintaining ground-truth environmental state and events."""

from __future__ import annotations

from collections.abc import Sequence

from sia_sim.contracts.data import EnvironmentState
from sia_sim.contracts.scenario import Scenario, ScenarioEvent
from sia_sim.physics.environment import (
    KNOTS_TO_M_S,
    ActiveGust,
    ActiveWaveImpact,
    CurrentModel,
    WaveModel,
    WindModel,
)


class WorldModel:
    """Ground truth environment and scenario event manager.

    Evaluates wind, waves, current, and active events at any simulation tick.
    """

    def __init__(
        self,
        initial_tws_kt: float,
        initial_twa_deg: float,
        initial_wave_height_m: float,
        initial_wave_period_s: float,
        current_speed_m_s: float = 0.0,
        current_direction_deg: float = 0.0,
        seed: int = 42,
        enable_turbulence: bool = True,
    ) -> None:
        self._wind = WindModel(
            base_tws_m_s=initial_tws_kt * KNOTS_TO_M_S,
            base_twa_deg=initial_twa_deg,
            seed=seed,
            enable_turbulence=enable_turbulence,
        )
        self._wave = WaveModel(
            wave_height_m=initial_wave_height_m,
            wave_period_s=initial_wave_period_s,
            wave_direction_deg=initial_twa_deg,
        )
        self._current = CurrentModel(
            current_speed_m_s=current_speed_m_s,
            current_direction_deg=current_direction_deg,
        )
        self._active_events: dict[str, ScenarioEvent] = {}

    @classmethod
    def from_scenario(cls, scenario: Scenario) -> WorldModel:
        """Construct WorldModel from a Scenario specification."""
        return cls(
            initial_tws_kt=scenario.initial_tws_kt,
            initial_twa_deg=scenario.initial_twa_deg,
            initial_wave_height_m=scenario.initial_wave_height_m,
            initial_wave_period_s=scenario.initial_wave_period_s,
            seed=scenario.seed,
            enable_turbulence=scenario.enable_turbulence,
        )

    @property
    def wind(self) -> WindModel:
        return self._wind

    @property
    def wave(self) -> WaveModel:
        return self._wave

    @property
    def current(self) -> CurrentModel:
        return self._current

    def apply_events(self, events: Sequence[ScenarioEvent]) -> None:
        """Apply timed scenario events that trigger at the current tick."""
        for evt in events:
            self._active_events[evt.event_id] = evt
            if evt.event_type == "wind_gust":
                peak_kt = float(evt.parameters.get("tws_kt", 10.0))
                duration_s = float(evt.parameters.get("duration_s", 5.0))
                duration_ms = int(evt.parameters.get("duration_ms", int(duration_s * 1000)))
                shift_deg = float(evt.parameters.get("direction_shift_deg", 0.0))

                gust = ActiveGust(
                    event_id=evt.event_id,
                    start_time_ms=evt.sim_time_ms,
                    duration_ms=duration_ms,
                    peak_speed_increase_m_s=peak_kt * KNOTS_TO_M_S,
                    direction_shift_deg=shift_deg,
                )
                self._wind.add_gust(gust)

            elif evt.event_type == "wave_impact":
                force_n = float(evt.parameters.get("impact_force_n", 5000.0))
                moment_nm = float(evt.parameters.get("impact_roll_moment_nm", 12000.0))
                duration_ms = int(evt.parameters.get("duration_ms", 2000))

                impact = ActiveWaveImpact(
                    event_id=evt.event_id,
                    impact_time_ms=evt.sim_time_ms,
                    duration_ms=duration_ms,
                    impact_force_n=force_n,
                    impact_roll_moment_nm=moment_nm,
                )
                self._wave.add_impact(impact)

    def step(self, time_ms: int) -> EnvironmentState:
        """Advance environment to time_ms and return immutable EnvironmentState."""
        tws_m_s, twa_deg = self._wind.evaluate(time_ms)
        curr_speed, curr_dir = self._current.evaluate()

        return EnvironmentState(
            true_wind_speed_m_s=tws_m_s,
            true_wind_angle_deg=twa_deg,
            wave_height_m=self._wave.wave_height_m,
            wave_period_s=self._wave.wave_period_s,
            current_speed_m_s=curr_speed,
            current_direction_deg=curr_dir,
        )

    def get_active_event_ids(self, time_ms: int) -> tuple[str, ...]:
        """Return IDs of scenario events currently active at time_ms."""
        return tuple(evt.event_id for evt in self.get_active_events(time_ms))

    def get_active_events(self, time_ms: int) -> tuple[ScenarioEvent, ...]:
        """Return scenario events currently active at time_ms."""
        active = []
        for evt in self._active_events.values():
            dur_ms = int(
                evt.parameters.get(
                    "duration_ms",
                    int(float(evt.parameters.get("duration_s", 5.0)) * 1000),
                )
            )
            if evt.sim_time_ms <= time_ms < evt.sim_time_ms + dur_ms:
                active.append(evt)
        return tuple(active)
