"""SIA Simulation data contracts (Pydantic v2 models).

These are the only types that cross component boundaries.

Hard invariants:
  INV-01: SensorFrame is the ONLY type that enters SIA Core.
  INV-02: GroundTruthFrame must NEVER be passed to SIA Core.
  INV-03: Oracle evaluates ground truth independently without SIA outputs.
  INV-06: Scenario is frozen during Run.
  INV-08: Evaluator observes and scores, never corrects SIA Core decisions.
"""

from sia_sim.contracts.data import (
    ActuatorState,
    EnvironmentState,
    GPSReading,
    GroundTruthFrame,
    IMUReading,
    SensorFrame,
    VesselState,
    WindReading,
)
from sia_sim.contracts.evaluation import (
    CandidateResponse,
    DecisionPayload,
    EvaluationResult,
    OracleResult,
    RiskAssessment,
)
from sia_sim.contracts.scenario import (
    Scenario,
    ScenarioEvent,
    VesselConfig,
)

__all__ = [
    "ActuatorState",
    "CandidateResponse",
    "DecisionPayload",
    "EnvironmentState",
    "EvaluationResult",
    "GPSReading",
    "GroundTruthFrame",
    "IMUReading",
    "OracleResult",
    "RiskAssessment",
    "Scenario",
    "ScenarioEvent",
    "SensorFrame",
    "VesselConfig",
    "VesselState",
    "WindReading",
]
