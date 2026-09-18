"""Aerodynamic polar curves (CL, CD) for marine sails.

Provides angle-of-attack dependent lift and drag coefficients
for diverse sail types: Mainsail, Genoa, Jib, Code 0, Gennaker/Spinnaker, Storm Jib.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class SailType(StrEnum):
    """Supported sail categories."""

    MAINSAIL = "mainsail"
    GENOA = "genoa"
    JIB = "jib"
    CODE_ZERO = "code_zero"
    GENNAKER = "gennaker"
    SPINNAKER = "spinnaker"
    STORM_JIB = "storm_jib"


@dataclass(frozen=True)
class PolarCoefficients:
    """Aerodynamic lift and drag coefficients at a specific angle of attack."""

    cl: float
    cd: float
    is_stalled: bool


def evaluate_sail_polar(
    sail_type: SailType,
    alpha_deg: float,
    camber_ratio: float = 0.12,
    is_furled: bool = False,
    furled_ratio: float = 0.0,
) -> PolarCoefficients:
    """Calculate lift (CL) and drag (CD) as a function of angle of attack (alpha)."""
    abs_alpha = abs(alpha_deg)
    sign_alpha = 1.0 if alpha_deg >= 0 else -1.0
    alpha_rad = math.radians(abs_alpha)

    # Base polar parameters by sail category (3D aspect ratio & parasitic drag)
    if sail_type in (SailType.MAINSAIL,):
        cl_max = 1.60 + (camber_ratio - 0.12) * 2.0
        alpha_stall_deg = 28.0
        cd_0 = 0.04
        induced_drag_factor = 0.08
    elif sail_type in (SailType.GENOA,):
        cl_max = 1.70 + (camber_ratio - 0.12) * 2.5
        alpha_stall_deg = 26.0
        cd_0 = 0.035
        induced_drag_factor = 0.07
    elif sail_type in (SailType.JIB,):
        cl_max = 1.50
        alpha_stall_deg = 25.0
        cd_0 = 0.030
        induced_drag_factor = 0.06
    elif sail_type in (SailType.CODE_ZERO,):
        cl_max = 1.95
        alpha_stall_deg = 30.0
        cd_0 = 0.040
        induced_drag_factor = 0.06
    elif sail_type in (SailType.GENNAKER, SailType.SPINNAKER):
        cl_max = 1.85
        alpha_stall_deg = 35.0
        cd_0 = 0.060
        induced_drag_factor = 0.07
    elif sail_type in (SailType.STORM_JIB,):
        cl_max = 1.20
        alpha_stall_deg = 22.0
        cd_0 = 0.050
        induced_drag_factor = 0.08
    else:
        cl_max = 1.50
        alpha_stall_deg = 16.0
        cd_0 = 0.08
        induced_drag_factor = 0.11

    # Furling draft degradation (bagginess increases CD, decreases CL)
    if is_furled and furled_ratio > 0.0:
        degradation_factor = 1.0 - (0.35 * furled_ratio)
        cl_max *= degradation_factor
        cd_0 += 0.08 * furled_ratio

    # Lift & Drag curve evaluation
    if abs_alpha < 3.0:
        # Luffing / in irons
        cl = (cl_max / alpha_stall_deg) * abs_alpha * 0.5
        cd = cd_0 + 0.05 * (1.0 - abs_alpha / 3.0)
        is_stalled = True
    elif abs_alpha <= alpha_stall_deg:
        # Linear attached flow regime (thin airfoil theory)
        cl = cl_max * math.sin((math.pi / 2.0) * (abs_alpha / alpha_stall_deg))
        cd = cd_0 + induced_drag_factor * (cl**2)
        is_stalled = False
    elif abs_alpha <= 45.0:
        # Stall & separation regime
        stall_decay = math.cos((math.pi / 2.0) * ((abs_alpha - alpha_stall_deg) / (45.0 - alpha_stall_deg)))
        cl = (cl_max * 0.7 * stall_decay) + (1.2 * math.sin(alpha_rad) * math.cos(alpha_rad) * (1.0 - stall_decay))
        cd = cd_0 + 0.35 * (1.0 - stall_decay) + (1.2 * (math.sin(alpha_rad) ** 2))
        is_stalled = True
    else:
        # Flat plate cross-flow drag regime (broad reach / run)
        cl = 1.1 * math.sin(2.0 * alpha_rad)
        cd = cd_0 + 1.35 * (math.sin(alpha_rad) ** 2)
        is_stalled = True

    return PolarCoefficients(
        cl=sign_alpha * cl,
        cd=max(0.01, cd),
        is_stalled=is_stalled,
    )
