"""Architectural boundary protocol for SIA Core isolation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sia_sim.contracts.data import SensorFrame
from sia_sim.contracts.evaluation import DecisionPayload


@runtime_checkable
class SIACore(Protocol):
    """Runtime protocol defining the architectural boundary for SIA Core.

    Architectural Invariants:
      INV-01: Only SensorFrame enters SIA Core.
      INV-02: Ground truth data (GroundTruthFrame, WorldModel, VesselDynamics)
              is NEVER accessible to this interface.

    Any decision engine (MockSIA, actual SIA Core) must implement this protocol.
    """

    def process(self, frame: SensorFrame) -> DecisionPayload:
        """Process an observable SensorFrame and produce a structured DecisionPayload.

        Args:
            frame: Immutable SensorFrame from the simulation sensor pipeline.

        Returns:
            Immutable DecisionPayload containing hazard diagnosis, risk assessment,
            and candidate response recommendations.
        """
        ...

    def reset(self) -> None:
        """Reset internal temporal states, filters, and estimators to initial state."""
        ...
