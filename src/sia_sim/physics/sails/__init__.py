"""SIA Simulation — 3D Sail Aerodynamics Engine.

Provides multi-component aerodynamic models, dynamic boom kinematics,
3D Center of Effort, sail interaction, and extensibility hooks.
"""

from __future__ import annotations

from sia_sim.physics.sails.polars import PolarCoefficients, SailType, evaluate_sail_polar
from sia_sim.physics.sails.rig import (
    ApparentWindFeedbackHook,
    HullHydrodynamicsHook,
    RigEvaluationResult,
    SailRig,
    SailTrimProfileHook,
    WaveSailInteractionHook,
    create_standard_sloop_rig,
)
from sia_sim.physics.sails.sail import Sail, SailConfig, SailEvaluationResult

__all__ = [
    "ApparentWindFeedbackHook",
    "HullHydrodynamicsHook",
    "PolarCoefficients",
    "RigEvaluationResult",
    "Sail",
    "SailConfig",
    "SailEvaluationResult",
    "SailRig",
    "SailTrimProfileHook",
    "SailType",
    "WaveSailInteractionHook",
    "create_standard_sloop_rig",
    "evaluate_sail_polar",
]
