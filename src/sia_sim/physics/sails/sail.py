"""Individual Sail aerodynamic object model with 3D Center of Effort and dynamic boom kinematics.

Represents an isolated sail (Mainsail, Genoa, Jib, Code 0, Spinnaker) with:
- Physical geometry: tack, head, clew in Body frame (meters).
- Dynamic boom angle theta_boom calculated from sheet trim and apparent wind.
- 3D Center of Effort (CoE) shifting laterally as boom eases out and vertically during reefing.
- Lift and drag decomposition into vessel body axes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple

from sia_sim.physics.forces import RHO_AIR
from sia_sim.physics.sails.polars import SailType, evaluate_sail_polar


class Vector3D(NamedTuple):
    x: float  # forward (+) / aft (-)
    y: float  # starboard (+) / port (-)
    z: float  # down (+) / up (-) in marine NED, or body frame where +z is up


@dataclass(frozen=True)
class SailConfig:
    """Static geometric design parameters for a single sail."""

    sail_id: str
    sail_type: SailType
    nominal_area_m2: float
    tack_point: tuple[float, float, float]  # (x, y, z) relative to CoG
    head_point: tuple[float, float, float]  # (x, y, z) relative to CoG
    clew_base_point: tuple[float, float, float]  # (x, y, z) when sheeted to centerline
    foot_length_m: float
    luff_length_m: float
    camber_ratio: float = 0.12
    max_boom_angle_deg: float = 75.0
    is_furling: bool = False


@dataclass
class SailEvaluationResult:
    """Computed state, forces, and moments of a single sail."""

    sail_id: str
    is_active: bool
    effective_area_m2: float
    reefed_ratio: float
    sheet_trim_ratio: float
    boom_angle_deg: float
    alpha_deg: float
    cl: float
    cd: float
    is_stalled: bool
    blanket_ratio: float
    coe: tuple[float, float, float]  # (x, y, z) in body frame
    force_body_n: tuple[float, float, float]  # (Fx drive, Fy side, Fz vertical)
    moment_body_nm: tuple[float, float, float]  # (Mx heel, My pitch, Mz yaw)


class Sail:
    """Individual aerodynamic lifting surface."""

    def __init__(self, config: SailConfig) -> None:
        self.config = config
        self.is_active: bool = True
        self.reefed_ratio: float = 1.0  # [0.0 ... 1.0]
        self.sheet_trim_ratio: float = 1.0  # 1.0 = trimmed in, 0.0 = fully eased
        self.manual_boom_angle_deg: float | None = None

    def calculate_boom_angle(self, awa_deg: float) -> float:
        """Calculate dynamic boom/clew angle (degrees) based on sheet trim and apparent wind.

        At sheet_trim_ratio = 1.0 (trimmed in), boom/clew follows sheet lead.
        As sheet is eased (sheet_trim_ratio -> 0.0), boom swings out to max_boom_angle_deg,
        dumping lift, side force, and heeling moment.
        """
        if self.manual_boom_angle_deg is not None:
            return self.manual_boom_angle_deg

        sign_wind = 1.0 if awa_deg >= 0 else -1.0  # +1 starboard wind (blows to port), -1 port wind
        abs_awa = abs(awa_deg)

        # In-trim lead angle by sail type
        if self.config.sail_type == SailType.MAINSAIL:
            trimmed_boom = min(self.config.max_boom_angle_deg, abs_awa * 0.45)
        elif self.config.sail_type in (SailType.GENNAKER, SailType.SPINNAKER):
            trimmed_boom = min(self.config.max_boom_angle_deg, abs_awa * 0.65)
        else:
            # Headsails (Genoa, Jib, Code 0, Storm Jib)
            trimmed_boom = min(self.config.max_boom_angle_deg, abs_awa * 0.35)

        # Easing sheet lets boom travel out towards max limit
        trim_factor = max(0.0, min(1.0, self.sheet_trim_ratio))
        eased_travel = (1.0 - trim_factor) * (self.config.max_boom_angle_deg - trimmed_boom)
        target_boom_angle = trimmed_boom + eased_travel

        # Boom moves to leeward: if wind is from starboard (+AWA), boom swings to port (-y -> -deg)
        return -sign_wind * min(self.config.max_boom_angle_deg, target_boom_angle)

    def compute_center_of_effort(
        self, boom_angle_deg: float, reefed_ratio: float
    ) -> tuple[float, float, float]:
        """Compute instantaneous 3D Center of Effort (CoE) in body frame coordinates.

        - Base CoE is centroid of triangle (Tack, Head, Clew).
        - Lateral shift y_CoE shifts with boom angle sin(theta_boom).
        - Vertical z_CoE drops as sail is reefed.
        """
        tack = self.config.tack_point
        head = self.config.head_point
        clew = self.config.clew_base_point

        # Dynamic clew point rotated around mast/tack pivot by boom_angle_deg
        boom_rad = math.radians(boom_angle_deg)
        clew_x = tack[0] + (clew[0] - tack[0]) * math.cos(boom_rad)
        clew_y = tack[1] + self.config.foot_length_m * math.sin(boom_rad)
        clew_z = clew[2]

        # Effective head point drops under reefing
        effective_head_z = tack[2] + (head[2] - tack[2]) * reefed_ratio
        effective_head_x = tack[0] + (head[0] - tack[0]) * reefed_ratio

        # Triangular centroid of sail
        coe_x = (tack[0] + effective_head_x + clew_x) / 3.0
        coe_y = (tack[1] + head[1] + clew_y) / 3.0
        coe_z = (tack[2] + effective_head_z + clew_z) / 3.0

        return (coe_x, coe_y, coe_z)

    def evaluate(
        self,
        aws_m_s: float,
        awa_deg: float,
        heel_deg: float = 0.0,
        blanket_ratio: float = 0.0,
        slot_effect_boost: float = 0.0,
    ) -> SailEvaluationResult:
        """Calculate aerodynamic forces and 3D moments for this sail."""
        if not self.is_active or self.reefed_ratio <= 0.0 or aws_m_s <= 0.0:
            coe = self.compute_center_of_effort(0.0, max(0.1, self.reefed_ratio))
            return SailEvaluationResult(
                sail_id=self.config.sail_id,
                is_active=False,
                effective_area_m2=0.0,
                reefed_ratio=self.reefed_ratio,
                sheet_trim_ratio=self.sheet_trim_ratio,
                boom_angle_deg=0.0,
                alpha_deg=0.0,
                cl=0.0,
                cd=0.0,
                is_stalled=False,
                blanket_ratio=blanket_ratio,
                coe=coe,
                force_body_n=(0.0, 0.0, 0.0),
                moment_body_nm=(0.0, 0.0, 0.0),
            )

        # 1. Boom angle and angle of attack
        boom_angle_deg = self.calculate_boom_angle(awa_deg)
        abs_awa = abs(awa_deg)
        abs_boom = abs(boom_angle_deg)
        # Angle of attack alpha = |AWA| - |theta_boom| (angle between incoming wind and sail chord)
        alpha_deg = max(0.0, abs_awa - abs_boom)

        # 2. Polar evaluation
        is_furled = self.config.is_furling and (self.reefed_ratio < 0.95)
        polar = evaluate_sail_polar(
            sail_type=self.config.sail_type,
            alpha_deg=alpha_deg,
            camber_ratio=self.config.camber_ratio,
            is_furled=is_furled,
            furled_ratio=(1.0 - self.reefed_ratio) if is_furled else 0.0,
        )

        cl = polar.cl * (1.0 + slot_effect_boost)
        cd = polar.cd

        # 3. Dynamic pressure & effective sail area
        heel_rad = math.radians(heel_deg)
        cos_heel = max(0.1, math.cos(heel_rad))
        effective_area = (
            self.config.nominal_area_m2 * self.reefed_ratio * (1.0 - blanket_ratio) * cos_heel
        )
        q = 0.5 * RHO_AIR * (aws_m_s**2) * effective_area

        # 4. Aerodynamic lift (perpendicular to AWA) & drag (parallel to AWA)
        # In wind coordinates:
        # L acts at +90° to apparent wind flow vector, D acts along wind flow vector
        abs_awa_rad = math.radians(abs(awa_deg))
        sign_wind = 1.0 if awa_deg >= 0 else -1.0

        # Decompose into Vessel Body frame:
        # Fx (Drive): forward along keel centerline (+x)
        # Fy (Side): lateral (+y starboard, -y port)
        # Fz (Vertical): down (+z in NED) or roll induced lift
        fx_drive = q * (abs(cl) * math.sin(abs_awa_rad) - cd * math.cos(abs_awa_rad))
        side_mag = q * (abs(cl) * math.cos(abs_awa_rad) + cd * math.sin(abs_awa_rad))
        fy_side = -sign_wind * side_mag  # Starboard wind (+AWA) pushes vessel to port (-y)
        fz_vert = -q * abs(cl) * math.sin(abs(heel_rad)) * 0.1  # small vertical aerodynamic lift

        # 5. Dynamic 3D Center of Effort
        coe_x, coe_y, coe_z = self.compute_center_of_effort(boom_angle_deg, self.reefed_ratio)

        # 6. 3D Cross-Product Moments: M = r x F
        # r = [coe_x, coe_y, coe_z] (relative to Center of Gravity / Center of Lateral Resistance)
        # F = [fx_drive, fy_side, fz_vert]
        # Mx = ry * Fz - rz * Fy  (Heeling moment, + starboard roll)
        # My = rz * Fx - rx * Fz  (Pitching moment, + bow down)
        # Mz = rx * Fy - ry * Fx  (Yawing moment, + starboard turning / weather helm)
        mx_heel = (coe_y * fz_vert) - (coe_z * fy_side)
        my_pitch = (coe_z * fx_drive) - (coe_x * fz_vert)
        mz_yaw = (coe_x * fy_side) - (coe_y * fx_drive)

        return SailEvaluationResult(
            sail_id=self.config.sail_id,
            is_active=True,
            effective_area_m2=effective_area,
            reefed_ratio=self.reefed_ratio,
            sheet_trim_ratio=self.sheet_trim_ratio,
            boom_angle_deg=boom_angle_deg,
            alpha_deg=alpha_deg,
            cl=cl,
            cd=cd,
            is_stalled=polar.is_stalled,
            blanket_ratio=blanket_ratio,
            coe=(coe_x, coe_y, coe_z),
            force_body_n=(fx_drive, fy_side, fz_vert),
            moment_body_nm=(mx_heel, my_pitch, mz_yaw),
        )
