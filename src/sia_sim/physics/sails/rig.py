"""SailRig multi-sail assembly, mutual interaction engine, and extension hooks.

Calculates:
- Combined aerodynamic forces F_sails = [Fx, Fy, Fz] and 3D moments M_sails = [Mx, My, Mz].
- Downwind blanketing / wind shadowing on TWA > 130°.
- Upwind slot effect / Venturi lift enhancement on TWA = 30°..60°.
- Extensibility protocols for Hydrodynamics, Apparent Wind Feedback, Wave-Sail interaction,
  and Trim Profiles.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from sia_sim.physics.sails.polars import SailType
from sia_sim.physics.sails.sail import Sail, SailConfig, SailEvaluationResult

# ---------------------------------------------------------------------------
# Extensibility Hook Protocols (For future physics subsystems)
# ---------------------------------------------------------------------------


@runtime_checkable
class HullHydrodynamicsHook(Protocol):
    """Extension hook for hull resistance, keel/rudder lift/drag, and ventilation."""

    def compute_hydrodynamic_forces(
        self,
        u_m_s: float,
        v_m_s: float,
        yaw_rate_rad_s: float,
        heel_deg: float,
        leeway_angle_deg: float,
    ) -> tuple[float, float, float]:
        """Returns (X_drag_n, Y_keel_lift_n, N_keel_moment_nm)."""
        ...


@runtime_checkable
class ApparentWindFeedbackHook(Protocol):
    """Extension hook for dynamic closed-loop apparent wind incorporating mast rotation."""

    def compute_local_apparent_wind(
        self,
        true_wind_speed_m_s: float,
        true_wind_angle_deg: float,
        vessel_speed_m_s: float,
        roll_rate_rad_s: float,
        pitch_rate_rad_s: float,
        z_height_m: float,
    ) -> tuple[float, float]:
        """Returns (local_aws_m_s, local_awa_deg) at height z."""
        ...


@runtime_checkable
class WaveSailInteractionHook(Protocol):
    """Extension hook for wave trough shadowing and mast pitching kinematics."""

    def compute_wave_wind_attenuation(
        self,
        wave_height_m: float,
        relative_wave_position: float,
        nominal_aws_m_s: float,
    ) -> float:
        """Returns attenuated local wind speed factor [0.0 ... 1.0]."""
        ...


@runtime_checkable
class SailTrimProfileHook(Protocol):
    """Extension hook for furling shape degradation and Boom Vang twist distribution."""

    def compute_twist_angle_deg(
        self,
        vang_tension_ratio: float,
        mainsheet_tension_ratio: float,
        z_relative: float,
    ) -> float:
        """Returns local sail twist offset delta_alpha(z)."""
        ...


# ---------------------------------------------------------------------------
# SailRig Assembly
# ---------------------------------------------------------------------------


@dataclass
class RigEvaluationResult:
    """Aggregated result of all active sails in the rig."""

    thrust_n: float  # Fx forward thrust (N)
    side_force_n: float  # Fy lateral side force (N, + starboard, - port)
    vertical_force_n: float  # Fz (N)
    heeling_moment_nm: float  # Mx heeling moment (Nm, + starboard roll)
    pitching_moment_nm: float  # My pitching moment (Nm, + bow down)
    yawing_moment_nm: float  # Mz yawing / weather helm moment (Nm, + starboard)
    center_of_effort: tuple[float, float, float]  # Composite 3D CoE (x, y, z)
    total_effective_area_m2: float
    sail_results: list[SailEvaluationResult] = field(default_factory=list)


class SailRig:
    """Multi-sail rig coordinating individual sails, interactions, and moments."""

    def __init__(self, sails: list[Sail] | None = None) -> None:
        self.sails: list[Sail] = sails or []
        self.hydrodynamics_hook: HullHydrodynamicsHook | None = None
        self.apparent_wind_hook: ApparentWindFeedbackHook | None = None
        self.wave_sail_hook: WaveSailInteractionHook | None = None
        self.trim_profile_hook: SailTrimProfileHook | None = None

    def add_sail(self, sail: Sail) -> None:
        self.sails.append(sail)

    def get_sail(self, sail_id: str) -> Sail | None:
        target = sail_id.lower().replace("-", "_").strip()
        for s in self.sails:
            if s.config.sail_id.lower() == target:
                return s
        # Aliases fallback for wardrobe identifiers
        if "main" in target:
            for s in self.sails:
                if s.config.sail_id.lower() in ("mainsail", "main") or s.config.sail_type == SailType.MAINSAIL:
                    return s
        if any(w in target for w in ("headsail", "genoa", "jib", "solent")):
            for s in self.sails:
                if s.config.sail_id.lower() in ("headsail", "genoa", "jib") or s.config.sail_type in (SailType.GENOA, SailType.JIB):
                    return s
        if "code" in target:
            for s in self.sails:
                if s.config.sail_id.lower() in ("code_zero", "code0", "code_0") or s.config.sail_type == SailType.CODE_ZERO:
                    return s
        if any(w in target for w in ("gennaker", "spinnaker", "para", "a2", "a3")):
            for s in self.sails:
                if s.config.sail_id.lower() in ("gennaker", "spinnaker", "a2") or s.config.sail_type in (SailType.GENNAKER, SailType.SPINNAKER):
                    return s
        if "storm" in target:
            for s in self.sails:
                if s.config.sail_id.lower() in ("storm_jib", "stormjib", "storm") or s.config.sail_type == SailType.STORM_JIB:
                    return s
        return None

    def configure_active_sails(self, active_sails: dict[str, float]) -> None:
        """Activate specified sails with custom reef ratios and deactivate unlisted sails.

        Args:
            active_sails: Mapping of sail_id / alias to reef ratio (0.0 to 1.0).
                          e.g. {"mainsail": 0.75, "genoa": 1.0, "code_zero": 1.0}
        """
        for s in self.sails:
            s.is_active = False

        for sail_id, reef_ratio in active_sails.items():
            if reef_ratio > 0.0:
                sail = self.get_sail(sail_id)
                if sail:
                    sail.is_active = True
                    sail.reefed_ratio = max(0.01, min(1.0, float(reef_ratio)))

    def set_sail_plan(self, plan_name: str) -> None:
        """Configure active sails and reefing levels based on high-level sail plan."""
        plan_upper = plan_name.upper().replace("-", "_").replace(" ", "_")
        main = self.get_sail("mainsail")
        headsail = self.get_sail("headsail") or self.get_sail("genoa") or self.get_sail("jib")
        code0 = self.get_sail("code_zero")
        gennaker = self.get_sail("gennaker")

        if plan_upper in ("BARE_POLES", "ENGINE_ONLY"):
            for s in self.sails:
                s.is_active = False
        elif plan_upper in ("FULL_MAIN", "FULL_SAILS", "STANDARD"):
            if main:
                main.is_active = True
                main.reefed_ratio = 1.0
            if headsail:
                headsail.is_active = True
                headsail.reefed_ratio = 1.0
            if code0:
                code0.is_active = False
            if gennaker:
                gennaker.is_active = False
        elif plan_upper in ("REEF_1", "MAIN_REEF_1"):
            if main:
                main.is_active = True
                main.reefed_ratio = 0.75
            if headsail:
                headsail.is_active = True
                headsail.reefed_ratio = 0.85
        elif plan_upper in ("REEF_2", "MAIN_REEF_2"):
            if main:
                main.is_active = True
                main.reefed_ratio = 0.55
            if headsail:
                headsail.is_active = True
                headsail.reefed_ratio = 0.65
        elif plan_upper in ("REEF_3", "MAIN_REEF_3"):
            if main:
                main.is_active = True
                main.reefed_ratio = 0.35
            if headsail:
                headsail.is_active = True
                headsail.reefed_ratio = 0.40
        elif plan_upper in ("STORM_JIB", "STORM_JIB_ONLY", "HEAVY_WEATHER"):
            if main:
                main.is_active = False
            storm_jib = self.get_sail("storm_jib")
            if storm_jib:
                storm_jib.is_active = True
                storm_jib.reefed_ratio = 1.0
            elif headsail:
                headsail.is_active = True
                headsail.reefed_ratio = 0.25
        elif plan_upper in ("CODE_ZERO", "REACHER"):
            if main:
                main.is_active = True
                main.reefed_ratio = 1.0
            if code0:
                code0.is_active = True
                code0.reefed_ratio = 1.0
            if headsail:
                headsail.is_active = False
        elif plan_upper in ("GENNAKER", "SPINNAKER", "A2", "A3"):
            if main:
                main.is_active = True
                main.reefed_ratio = 1.0
            if gennaker:
                gennaker.is_active = True
                gennaker.reefed_ratio = 1.0
            if headsail:
                headsail.is_active = False
        elif plan_upper in ("PARASAILOR", "WING_SAIL"):
            if main:
                main.is_active = False  # Parasailor is flown solo on dead runs
            if gennaker:
                gennaker.is_active = True
                gennaker.reefed_ratio = 1.0
            if headsail:
                headsail.is_active = False
        elif plan_upper in ("JIB_ONLY", "GENOA_ONLY"):
            if main:
                main.is_active = False
            if headsail:
                headsail.is_active = True
                headsail.reefed_ratio = 1.0

    def evaluate_interactions(self, awa_deg: float) -> tuple[dict[str, float], dict[str, float]]:
        """Calculate mutual interference factors: blanketing ratio and slot effect boost."""
        blanket_map: dict[str, float] = {}
        slot_map: dict[str, float] = {}

        abs_awa = abs(awa_deg)

        # 1. Downwind blanketing / wind shadow (TWA > 130°)
        # When sailing downwind, the large mainsail blankets the headsail on the same side
        for s in self.sails:
            blanket_map[s.config.sail_id] = 0.0
            slot_map[s.config.sail_id] = 0.0

        if abs_awa > 130.0:
            # If both main and headsail are active, headsail is heavily blanketed on dead run
            main = self.get_sail("mainsail")
            if main and main.is_active:
                shadow_intensity = min(1.0, (abs_awa - 130.0) / 40.0)  # reaches 1.0 at 170°
                for s in self.sails:
                    if s.config.sail_id != "mainsail" and s.config.sail_type in (
                        SailType.GENOA,
                        SailType.JIB,
                        SailType.STORM_JIB,
                    ):
                        blanket_map[s.config.sail_id] = 0.85 * shadow_intensity

        # 2. Upwind slot effect (Venturi acceleration on AWA 30°..60°)
        if 25.0 <= abs_awa <= 65.0:
            # If both main and headsail are active and trimmed, airflow in the slot accelerates
            main = self.get_sail("mainsail")
            headsail = self.get_sail("headsail") or self.get_sail("genoa") or self.get_sail("jib")
            if main and main.is_active and headsail and headsail.is_active:
                slot_boost = 0.15 * math.sin(math.pi * ((abs_awa - 25.0) / 40.0))
                slot_map["mainsail"] = slot_boost

        return blanket_map, slot_map

    def evaluate(
        self,
        aws_m_s: float,
        awa_deg: float,
        heel_deg: float = 0.0,
        mainsheet_pct: float = 100.0,
    ) -> RigEvaluationResult:
        """Calculate total aerodynamic forces, 3D moments, and composite Center of Effort."""
        if aws_m_s <= 0.0:
            return RigEvaluationResult(
                thrust_n=0.0,
                side_force_n=0.0,
                vertical_force_n=0.0,
                heeling_moment_nm=0.0,
                pitching_moment_nm=0.0,
                yawing_moment_nm=0.0,
                center_of_effort=(0.0, 0.0, 0.0),
                total_effective_area_m2=0.0,
                sail_results=[],
            )

        # Sync sheet trim across active sails
        trim_ratio = max(0.0, min(1.0, mainsheet_pct / 100.0))
        for s in self.sails:
            s.sheet_trim_ratio = trim_ratio

        blanket_map, slot_map = self.evaluate_interactions(awa_deg)

        total_fx = 0.0
        total_fy = 0.0
        total_fz = 0.0
        total_mx = 0.0
        total_my = 0.0
        total_mz = 0.0
        total_eff_area = 0.0

        weighted_coe_x = 0.0
        weighted_coe_y = 0.0
        weighted_coe_z = 0.0

        results: list[SailEvaluationResult] = []

        for sail in self.sails:
            b_ratio = blanket_map.get(sail.config.sail_id, 0.0)
            s_boost = slot_map.get(sail.config.sail_id, 0.0)
            res = sail.evaluate(
                aws_m_s=aws_m_s,
                awa_deg=awa_deg,
                heel_deg=heel_deg,
                blanket_ratio=b_ratio,
                slot_effect_boost=s_boost,
            )
            results.append(res)

            if res.is_active:
                total_fx += res.force_body_n[0]
                total_fy += res.force_body_n[1]
                total_fz += res.force_body_n[2]
                total_mx += res.moment_body_nm[0]
                total_my += res.moment_body_nm[1]
                total_mz += res.moment_body_nm[2]
                total_eff_area += res.effective_area_m2

                weighted_coe_x += res.coe[0] * res.effective_area_m2
                weighted_coe_y += res.coe[1] * res.effective_area_m2
                weighted_coe_z += res.coe[2] * res.effective_area_m2

        comp_coe_x = (weighted_coe_x / total_eff_area) if total_eff_area > 0.0 else 0.0
        comp_coe_y = (weighted_coe_y / total_eff_area) if total_eff_area > 0.0 else 0.0
        comp_coe_z = (weighted_coe_z / total_eff_area) if total_eff_area > 0.0 else 0.0

        return RigEvaluationResult(
            thrust_n=total_fx,
            side_force_n=total_fy,
            vertical_force_n=total_fz,
            heeling_moment_nm=total_mx,
            pitching_moment_nm=total_my,
            yawing_moment_nm=total_mz,
            center_of_effort=(comp_coe_x, comp_coe_y, comp_coe_z),
            total_effective_area_m2=total_eff_area,
            sail_results=results,
        )


def create_standard_sloop_rig(
    mainsail_area_m2: float = 50.0,
    headsail_area_m2: float = 50.0,
    mast_height_m: float = 19.5,
    loa_m: float = 13.94,
) -> SailRig:
    """Creates a standard modern sloop rig with mainsail, genoa, code 0, gennaker, and storm jib."""
    # Proportional foot & luff dimensions
    main_foot = max(3.5, loa_m * 0.38)
    main_luff = mast_height_m * 0.85
    tack_z = 0.8  # ~deck/gooseneck height above waterline

    main_config = SailConfig(
        sail_id="mainsail",
        sail_type=SailType.MAINSAIL,
        nominal_area_m2=mainsail_area_m2,
        tack_point=(loa_m * 0.05, 0.0, tack_z),  # at gooseneck (5% loa forward of CLR)
        head_point=(loa_m * 0.02, 0.0, tack_z + main_luff),
        clew_base_point=(loa_m * 0.05 - main_foot, 0.0, tack_z),
        foot_length_m=main_foot,
        luff_length_m=main_luff,
        camber_ratio=0.12,
        max_boom_angle_deg=75.0,
        is_furling=False,
    )

    # Genoa 135% geometry
    genoa_foot = max(4.0, loa_m * 0.48)
    genoa_luff = mast_height_m * 0.90
    genoa_config = SailConfig(
        sail_id="headsail",
        sail_type=SailType.GENOA,
        nominal_area_m2=headsail_area_m2,
        tack_point=(loa_m * 0.45, 0.0, tack_z),  # at bow pulpit / furler
        head_point=(loa_m * 0.05, 0.0, tack_z + genoa_luff),
        clew_base_point=(loa_m * 0.05 - loa_m * 0.08, 0.0, tack_z + 0.2),
        foot_length_m=genoa_foot,
        luff_length_m=genoa_luff,
        camber_ratio=0.14,
        max_boom_angle_deg=75.0,
        is_furling=True,
    )

    # Code 0 (Reaching/light air genoa 130%)
    code0_config = SailConfig(
        sail_id="code_zero",
        sail_type=SailType.CODE_ZERO,
        nominal_area_m2=headsail_area_m2 * 1.30,
        tack_point=(loa_m * 0.52, 0.0, tack_z),  # on bowsprit
        head_point=(loa_m * 0.05, 0.0, tack_z + mast_height_m * 0.95),
        clew_base_point=(loa_m * 0.05 - loa_m * 0.15, 0.0, tack_z + 0.3),
        foot_length_m=genoa_foot * 1.25,
        luff_length_m=mast_height_m * 0.95,
        camber_ratio=0.16,
        max_boom_angle_deg=80.0,
        is_furling=True,
    )

    # Gennaker / Spinnaker A2
    gennaker_config = SailConfig(
        sail_id="gennaker",
        sail_type=SailType.GENNAKER,
        nominal_area_m2=headsail_area_m2 * 1.60,
        tack_point=(loa_m * 0.55, 0.0, tack_z),  # bowsprit tip
        head_point=(loa_m * 0.05, 0.0, tack_z + mast_height_m * 0.98),
        clew_base_point=(loa_m * 0.05 - loa_m * 0.20, 0.0, tack_z + 0.5),
        foot_length_m=genoa_foot * 1.45,
        luff_length_m=mast_height_m * 0.98,
        camber_ratio=0.22,
        max_boom_angle_deg=85.0,
        is_furling=False,
    )

    # Storm Jib geometry
    storm_config = SailConfig(
        sail_id="storm_jib",
        sail_type=SailType.STORM_JIB,
        nominal_area_m2=max(8.0, headsail_area_m2 * 0.25),
        tack_point=(loa_m * 0.28, 0.0, tack_z),  # inner forestay
        head_point=(loa_m * 0.05, 0.0, tack_z + mast_height_m * 0.55),
        clew_base_point=(loa_m * 0.08, 0.0, tack_z + 0.3),
        foot_length_m=max(2.5, loa_m * 0.22),
        luff_length_m=mast_height_m * 0.55,
        camber_ratio=0.08,
        max_boom_angle_deg=65.0,
        is_furling=False,
    )

    code0_sail = Sail(code0_config)
    code0_sail.is_active = False

    gennaker_sail = Sail(gennaker_config)
    gennaker_sail.is_active = False

    storm_sail = Sail(storm_config)
    storm_sail.is_active = False

    return SailRig(
        sails=[
            Sail(main_config),
            Sail(genoa_config),
            code0_sail,
            gennaker_sail,
            storm_sail,
        ]
    )
