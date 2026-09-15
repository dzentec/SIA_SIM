"""SIA Simulation data contracts (Pydantic v2 models).

These are the only types that cross component boundaries.

Hard invariant: SensorFrame is the ONLY type that enters SIA Core.
GroundTruthFrame must NEVER be passed to SIA Core.
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

__all__ = [
    "ActuatorState",
    "EnvironmentState",
    "GPSReading",
    "GroundTruthFrame",
    "IMUReading",
    "SensorFrame",
    "VesselState",
    "WindReading",
]
