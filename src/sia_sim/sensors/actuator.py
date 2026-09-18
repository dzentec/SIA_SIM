"""Actuator feedback sensor simulation model (rudder angle feedback)."""

from __future__ import annotations

import numpy as np

from sia_sim.contracts.data import ActuatorState, VesselState
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig


class ActuatorSensorModel:
    """Simulates actuator feedback telemetry.

    - rudder_angle_deg: Standard rudder stock feedback potentiometer with noise and latency.
    - mainsheet_pct: None by default (95%+ of sailing yachts have no mainsheet position sensor).
    """

    def __init__(
        self,
        rng: np.random.Generator | None = None,
        rudder_config: DegradationConfig | None = None,
        enable_mainsheet_sensor: bool = False,
    ) -> None:
        self.rng = rng or np.random.default_rng(0)
        self.enable_mainsheet_sensor = enable_mainsheet_sensor

        self.degrader_rudder = ChannelDegrader(
            rudder_config
            or DegradationConfig(
                noise_std=0.1,  # ~0.1 deg potentiometer noise
                latency_ms=20,  # 20 ms bus feedback delay
                min_value=-45.0,
                max_value=45.0,
            ),
            self.rng,
        )

        self._hardware_fault = False
        self._frozen = False

    def reset(self, rng: np.random.Generator | None = None) -> None:
        if rng is not None:
            self.rng = rng
        self.degrader_rudder.reset(self.rng)
        self._hardware_fault = False
        self._frozen = False

    def set_fault(self, fault: bool) -> None:
        self._hardware_fault = fault

    def set_frozen(self, frozen: bool) -> None:
        self._frozen = frozen

    def generate(
        self,
        vessel: VesselState,
        sim_time_ms: int,
        fault_override: bool = False,
        freeze_override: bool = False,
        mainsheet_trim_pct: float | None = None,
    ) -> ActuatorState:
        """Transform physical vessel rudder position into degraded ActuatorState."""
        is_fault = self._hardware_fault or fault_override
        is_freeze = self._frozen or freeze_override

        rudder = self.degrader_rudder.process(vessel.rudder_angle_deg, sim_time_ms, is_fault, is_freeze)

        # Mainsheet feedback is None on standard vessels unless explicitly enabled
        mainsheet = mainsheet_trim_pct if self.enable_mainsheet_sensor else None

        return ActuatorState(
            rudder_angle_deg=rudder,
            mainsheet_pct=mainsheet,
            fault=is_fault or (rudder is None),
        )
