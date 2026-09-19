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
from typing import Literal, Protocol, runtime_checkable

from sia_sim.contracts.sails import (
    ClampState,
    FurlerState,
    RigState,
    RopeControlInput,
    RopeLoadStatus,
    RopeState,
    RopeStatus,
    SailState,
    TravelerControlInput,
    TravelerState,
    compute_load_status,
)
from sia_sim.physics.sails.polars import SailType
from sia_sim.physics.sails.sail import Sail, SailConfig, SailEvaluationResult

# ---------------------------------------------------------------------------
# Phase 12: Rig Kinematics & Winch/Clutch Dynamic Models ([CORRECT] fidelity)
# ---------------------------------------------------------------------------


@dataclass
class WinchModel:
    """Deterministic dynamic winch and clutch/stopper physics model.

    Adheres strictly to [CORRECT] fidelity:
    - clamped == True: d(actual_trim)/dt = 0, tension continues to update from aerodynamic forces.
    - load_factor: hauling speed drops under tension (1.0 - tension / SWL).
    - acceleration limit: clamped by a_winch_max.
    - breaking load: tension >= breaking_load_n transitions to BROKEN.
    - load status is independent of clamped state (evaluated via compute_load_status).
    """

    id: str
    side: Literal["port", "starboard", "center"]
    group: Literal["jib", "main", "reef", "rig"]
    max_length_m: float = 10.0
    v_winch_max_m_s: float = 0.5
    a_winch_max_m_s2: float = 2.0
    max_working_load_n: float = 2500.0  # Safe Working Load (SWL)
    breaking_load_n: float = 5000.0
    slack_threshold_n: float = 100.0
    taut_threshold_n: float = 2100.0  # ~84% SWL

    target_trim: float = 0.5
    actual_trim: float = 0.5
    clamped: bool = True
    speed_m_s: float = 0.0
    accel_m_s2: float = 0.0
    tension_n: float = 0.0
    is_broken: bool = False

    def step(
        self,
        target_trim: float,
        clamped: bool,
        external_tension_n: float,
        dt: float,
        ease_rate: float = 1.0,
    ) -> RopeState:
        """Advance winch state by dt seconds."""
        self.target_trim = max(0.0, min(1.0, target_trim))
        self.clamped = clamped
        self.tension_n = max(0.0, external_tension_n)

        if self.tension_n >= self.breaking_load_n:
            self.is_broken = True

        if self.is_broken:
            self.speed_m_s = 0.0
            self.accel_m_s2 = 0.0
            return self.get_state(RopeLoadStatus.BROKEN)

        if self.clamped:
            self.speed_m_s = 0.0
            self.accel_m_s2 = 0.0
            status = self._evaluate_status()
            return self.get_state(status)

        # Winch kinematics when unclamped
        trim_diff = self.target_trim - self.actual_trim
        if abs(trim_diff) < 1e-4:
            self.speed_m_s = 0.0
            self.accel_m_s2 = 0.0
            self.actual_trim = self.target_trim
        else:
            direction = 1.0 if trim_diff > 0 else -1.0
            is_hauling = direction > 0
            base_speed = self.v_winch_max_m_s if is_hauling else (self.v_winch_max_m_s * ease_rate)

            # Load factor drops hauling speed under tension
            if is_hauling and self.max_working_load_n > 0:
                load_factor = max(0.1, min(1.0, 1.0 - (self.tension_n / self.max_working_load_n)))
            else:
                load_factor = 1.0

            v_desired = direction * base_speed * load_factor
            a_desired = (v_desired - self.speed_m_s) / max(1e-4, dt)
            self.accel_m_s2 = max(-self.a_winch_max_m_s2, min(self.a_winch_max_m_s2, a_desired))
            self.speed_m_s += self.accel_m_s2 * dt

            trim_delta = (self.speed_m_s * dt) / max(0.1, self.max_length_m)
            self.actual_trim = max(0.0, min(1.0, self.actual_trim + trim_delta))

        status = self._evaluate_status()
        return self.get_state(status)

    def _evaluate_status(self) -> RopeLoadStatus:
        if self.is_broken:
            return RopeLoadStatus.BROKEN
        return compute_load_status(
            tension_n=self.tension_n,
            slack_threshold_n=self.slack_threshold_n,
            taut_threshold_n=self.taut_threshold_n,
            max_working_load_n=self.max_working_load_n,
            breaking_load_n=self.breaking_load_n,
        )

    def get_state(self, status: RopeLoadStatus | None = None) -> RopeState:
        stat = status or self._evaluate_status()
        length_m = (1.0 - self.actual_trim) * self.max_length_m
        return RopeState(
            id=self.id,
            side=self.side,
            group=self.group,
            target_trim=self.target_trim,
            actual_trim=self.actual_trim,
            clamped=self.clamped,
            length_m=length_m,
            speed_m_s=self.speed_m_s,
            accel_m_s2=self.accel_m_s2,
            tension_n=self.tension_n,
            slack_threshold_n=self.slack_threshold_n,
            taut_threshold_n=self.taut_threshold_n,
            max_working_load_n=self.max_working_load_n,
            breaking_load_n=self.breaking_load_n,
            status=stat,
        )


@dataclass
class TravelerModel:
    """Mainsheet traveler car with signed range [-1.0 ... +1.0]."""

    id: str = "traveler"
    target_pos: float = 0.0
    actual_pos: float = 0.0
    speed_m_s: float = 0.0
    clamped: bool = True
    v_traveler_max: float = 0.4  # travel pos units/s

    def step(self, target_pos: float, clamped: bool, dt: float) -> TravelerState:
        self.target_pos = max(-1.0, min(1.0, target_pos))
        self.clamped = clamped
        if not self.clamped:
            diff = self.target_pos - self.actual_pos
            step_max = self.v_traveler_max * dt
            step = max(-step_max, min(step_max, diff))
            self.actual_pos = max(-1.0, min(1.0, self.actual_pos + step))
            self.speed_m_s = step / max(1e-4, dt)
        else:
            self.speed_m_s = 0.0

        status = RopeLoadStatus.OK
        return TravelerState(
            id=self.id,
            target_pos=self.target_pos,
            actual_pos=self.actual_pos,
            speed_m_s=self.speed_m_s,
            clamped=self.clamped,
            status=status,
        )


@dataclass
class FurlerModel:
    """Headsail furling drum physical geometry model."""

    id: str = "jib_furler"
    drum_circumference_m: float = 0.4
    furling_pitch_m: float = 0.25
    luff_length_m: float = 14.0
    max_furling_line_m: float = 20.0
    cd_furled_penalty: float = 0.35

    line_trim: float = 0.0  # 0.0 = line eased (unfurled), 1.0 = line hauled (furled)
    furled_ratio: float = 0.0
    area_ratio: float = 1.0
    clamped: bool = True

    def step(self, line_trim: float, clamped: bool, dt: float) -> FurlerState:
        self.line_trim = max(0.0, min(1.0, line_trim))
        self.clamped = clamped
        line_length_m = self.line_trim * self.max_furling_line_m
        drum_turns = line_length_m / max(0.01, self.drum_circumference_m)
        furled_length_m = drum_turns * self.furling_pitch_m
        self.furled_ratio = max(0.0, min(1.0, furled_length_m / max(0.01, self.luff_length_m)))
        self.area_ratio = max(0.0, min(1.0, 1.0 - self.furled_ratio))

        status = RopeLoadStatus.OK
        return FurlerState(
            id=self.id,
            line_trim=self.line_trim,
            line_length_m=line_length_m,
            drum_turns=drum_turns,
            furled_ratio=self.furled_ratio,
            area_ratio=self.area_ratio,
            status=status,
        )


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

    @property
    def sails(self) -> list[SailEvaluationResult]:
        """Convenience alias for sail_results."""
        return self.sail_results


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
                if s.config.sail_id.lower() in ("headsail", "genoa", "jib") or s.config.sail_type in (
                    SailType.GENOA,
                    SailType.JIB,
                ):
                    return s
        if "code" in target:
            for s in self.sails:
                if (
                    s.config.sail_id.lower() in ("code_zero", "code0", "code_0")
                    or s.config.sail_type == SailType.CODE_ZERO
                ):
                    return s
        if any(w in target for w in ("gennaker", "spinnaker", "para", "a2", "a3")):
            for s in self.sails:
                if s.config.sail_id.lower() in ("gennaker", "spinnaker", "a2") or s.config.sail_type in (
                    SailType.GENNAKER,
                    SailType.SPINNAKER,
                ):
                    return s
        if "storm" in target:
            for s in self.sails:
                if (
                    s.config.sail_id.lower() in ("storm_jib", "stormjib", "storm")
                    or s.config.sail_type == SailType.STORM_JIB
                ):
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
                    sail.reefed_ratio = max(0.01, min(1.0, reef_ratio))

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


# ---------------------------------------------------------------------------
# Rig Control System Manager (Phase 12 [CORRECT] Orchestrator)
# ---------------------------------------------------------------------------


class RigControlSystem:
    """Coordinates winch physics, traveler kinematics, furler drum, and aerodynamic rig.

    Provides discrete simulation step advancing all lines, calculating realistic tension loads
    from sail aerodynamics, and emitting immutable RigState telemetry.
    """

    def __init__(self, rig: SailRig) -> None:
        self.rig = rig
        self.winches: dict[str, WinchModel] = {
            "jib_sheet_port": WinchModel(
                id="jib_sheet_port",
                side="port",
                group="jib",
                slack_threshold_n=100.0,
                taut_threshold_n=1500.0,
                max_working_load_n=1800.0,
                breaking_load_n=4000.0,
            ),
            "jib_sheet_starboard": WinchModel(
                id="jib_sheet_starboard",
                side="starboard",
                group="jib",
                slack_threshold_n=100.0,
                taut_threshold_n=1500.0,
                max_working_load_n=1800.0,
                breaking_load_n=4000.0,
            ),
            "jib_halyard": WinchModel(
                id="jib_halyard",
                side="port",
                group="jib",
                slack_threshold_n=150.0,
                taut_threshold_n=2100.0,
                max_working_load_n=2500.0,
                breaking_load_n=5000.0,
                actual_trim=1.0,
            ),
            "furling_line": WinchModel(
                id="furling_line",
                side="port",
                group="jib",
                slack_threshold_n=80.0,
                taut_threshold_n=1000.0,
                max_working_load_n=1200.0,
                breaking_load_n=2500.0,
                actual_trim=0.0,
            ),
            "cunningham": WinchModel(
                id="cunningham",
                side="port",
                group="main",
                slack_threshold_n=100.0,
                taut_threshold_n=1250.0,
                max_working_load_n=1500.0,
                breaking_load_n=3000.0,
                actual_trim=0.0,
            ),
            "outhaul": WinchModel(
                id="outhaul",
                side="port",
                group="main",
                slack_threshold_n=100.0,
                taut_threshold_n=1250.0,
                max_working_load_n=1500.0,
                breaking_load_n=3000.0,
                actual_trim=0.5,
            ),
            "reef_line_1": WinchModel(
                id="reef_line_1",
                side="port",
                group="reef",
                slack_threshold_n=120.0,
                taut_threshold_n=1700.0,
                max_working_load_n=2000.0,
                breaking_load_n=4500.0,
                actual_trim=0.0,
            ),
            "reef_line_2": WinchModel(
                id="reef_line_2",
                side="port",
                group="reef",
                slack_threshold_n=120.0,
                taut_threshold_n=1700.0,
                max_working_load_n=2000.0,
                breaking_load_n=4500.0,
                actual_trim=0.0,
            ),
            "reef_line_3": WinchModel(
                id="reef_line_3",
                side="port",
                group="reef",
                slack_threshold_n=120.0,
                taut_threshold_n=1700.0,
                max_working_load_n=2000.0,
                breaking_load_n=4500.0,
                actual_trim=0.0,
            ),
            "mainsheet": WinchModel(
                id="mainsheet",
                side="starboard",
                group="main",
                slack_threshold_n=150.0,
                taut_threshold_n=2100.0,
                max_working_load_n=2500.0,
                breaking_load_n=5500.0,
                actual_trim=0.6,
            ),
            "main_halyard": WinchModel(
                id="main_halyard",
                side="starboard",
                group="main",
                slack_threshold_n=180.0,
                taut_threshold_n=2550.0,
                max_working_load_n=3000.0,
                breaking_load_n=6000.0,
                actual_trim=1.0,
            ),
            "boom_vang": WinchModel(
                id="boom_vang",
                side="starboard",
                group="main",
                slack_threshold_n=150.0,
                taut_threshold_n=2100.0,
                max_working_load_n=2500.0,
                breaking_load_n=5000.0,
                actual_trim=0.8,
            ),
        }
        self.traveler = TravelerModel(id="traveler", target_pos=0.0, actual_pos=0.0, clamped=True)
        self.furler = FurlerModel(id="jib_furler", line_trim=0.0, furled_ratio=0.0, area_ratio=1.0, clamped=True)
        self.reef_level: int = 0

    def apply_rope_control(self, control: RopeControlInput) -> None:
        """Apply skipper command to a specific line."""
        if control.rope_id in self.winches:
            winch = self.winches[control.rope_id]
            winch.target_trim = control.target_trim
            winch.clamped = control.clamped

    def apply_traveler_control(self, control: TravelerControlInput) -> None:
        """Apply skipper command to traveler."""
        self.traveler.target_pos = control.target_pos
        self.traveler.clamped = control.clamped

    def step(
        self,
        timestamp_ms: int,
        dt: float,
        aws_m_s: float,
        awa_deg: float,
        heel_deg: float = 0.0,
        rope_controls: list[RopeControlInput] | None = None,
        traveler_control: TravelerControlInput | None = None,
    ) -> tuple[RigEvaluationResult, RigState]:
        """Advance rig physics by dt seconds and return forces and telemetry state."""
        # 1. Apply incoming controls if provided
        if rope_controls:
            for rc in rope_controls:
                self.apply_rope_control(rc)
        if traveler_control:
            self.apply_traveler_control(traveler_control)

        # 2. Advance traveler kinematics
        traveler_state = self.traveler.step(self.traveler.target_pos, self.traveler.clamped, dt)

        # 3. Advance furler kinematics from furling line
        furling_winch = self.winches["furling_line"]
        furler_state = self.furler.step(furling_winch.actual_trim, furling_winch.clamped, dt)

        # 4. Map control states to aerodynamic sails
        main_sail = self.rig.get_sail("mainsail")
        headsail = self.rig.get_sail("headsail") or self.rig.get_sail("jib") or self.rig.get_sail("genoa")

        if main_sail:
            main_sail.sheet_trim_ratio = self.winches["mainsheet"].actual_trim
            main_sail.twist_trim = self.winches["boom_vang"].actual_trim
            main_sail.outhaul_trim = self.winches["outhaul"].actual_trim
            main_sail.cunningham_trim = self.winches["cunningham"].actual_trim

            # Reefing level geometry
            if self.reef_level == 1:
                main_sail.reefed_ratio = 0.75
            elif self.reef_level == 2:
                main_sail.reefed_ratio = 0.50
            elif self.reef_level >= 3:
                main_sail.reefed_ratio = 0.25
            else:
                main_sail.reefed_ratio = self.winches["main_halyard"].actual_trim

        if headsail:
            # Side-aware jib sheet: active sheet depends on tack (AWA sign)
            # AWA > 0: starboard tack -> port sheet loaded; AWA < 0: port tack -> starboard sheet loaded
            if awa_deg >= 0:
                active_sheet = self.winches["jib_sheet_port"]
                inactive_sheet = self.winches["jib_sheet_starboard"]
            else:
                active_sheet = self.winches["jib_sheet_starboard"]
                inactive_sheet = self.winches["jib_sheet_port"]

            headsail.sheet_trim_ratio = active_sheet.actual_trim
            headsail.reefed_ratio = furler_state.area_ratio

        # 5. Evaluate rig aerodynamic forces
        eval_result = self.rig.evaluate(aws_m_s=aws_m_s, awa_deg=awa_deg, heel_deg=heel_deg)

        # 6. Estimate line tensions from aerodynamic forces
        main_eval = next((s for s in eval_result.sail_results if s.sail_id == "mainsail"), None)
        head_eval = next((s for s in eval_result.sail_results if s.sail_id in ("headsail", "genoa", "jib")), None)

        main_force_mag = (
            math.sqrt(main_eval.force_body_n[0] ** 2 + main_eval.force_body_n[1] ** 2) if main_eval else 0.0
        )
        head_force_mag = (
            math.sqrt(head_eval.force_body_n[0] ** 2 + head_eval.force_body_n[1] ** 2) if head_eval else 0.0
        )

        # Main sheet tension scales with main drive force and trim
        mainsheet_tension = main_force_mag * 0.85 * (0.3 + 0.7 * self.winches["mainsheet"].actual_trim)
        # Jib sheet tension scales with headsail force
        active_jib_tension = head_force_mag * 0.90 * (0.3 + 0.7 * active_sheet.actual_trim) if headsail else 0.0
        inactive_jib_tension = 10.0  # slack line

        # Assign external tensions
        tensions: dict[str, float] = {
            "mainsheet": mainsheet_tension,
            "boom_vang": main_force_mag * 0.40 * (1.0 - (main_eval.twist_deg / 20.0 if main_eval else 0.0)),
            "main_halyard": main_force_mag * 0.50,
            "outhaul": main_force_mag * 0.25 * self.winches["outhaul"].actual_trim,
            "cunningham": main_force_mag * 0.20 * self.winches["cunningham"].actual_trim,
            "reef_line_1": main_force_mag * 0.60 if self.reef_level == 1 else 0.0,
            "reef_line_2": main_force_mag * 0.60 if self.reef_level == 2 else 0.0,
            "reef_line_3": main_force_mag * 0.70 if self.reef_level == 3 else 0.0,
            "furling_line": head_force_mag * 0.35 * (1.0 - furler_state.area_ratio),
            "jib_halyard": head_force_mag * 0.45,
            active_sheet.id: active_jib_tension,
            inactive_sheet.id: inactive_jib_tension,
        }

        # 7. Step winches
        rope_states: dict[str, RopeState] = {}
        for wid, winch in self.winches.items():
            ext_t = tensions.get(wid, 20.0)
            rope_states[wid] = winch.step(
                target_trim=winch.target_trim,
                clamped=winch.clamped,
                external_tension_n=ext_t,
                dt=dt,
            )

        # 8. Build SailStates
        sail_states: dict[str, SailState] = {}
        for s_eval in eval_result.sail_results:
            sail_states[s_eval.sail_id] = SailState(
                sail_id=s_eval.sail_id,
                effective_area_m2=s_eval.effective_area_m2,
                area_ratio=s_eval.reefed_ratio,
                angle_of_attack_deg=s_eval.alpha_deg,
                twist_deg=s_eval.twist_deg,
                camber_ratio=s_eval.camber_ratio,
                lift_force_n=math.sqrt(s_eval.force_body_n[0] ** 2 + s_eval.force_body_n[1] ** 2),
                drag_force_n=abs(s_eval.force_body_n[0]),
                center_of_effort_z=s_eval.coe[2],
                reef_level=self.reef_level if s_eval.sail_id == "mainsail" else 0,
                status=s_eval.status,
            )

        rig_state = RigState(
            timestamp_ms=timestamp_ms,
            ropes=rope_states,
            traveler=traveler_state,
            furler=furler_state,
            sails=sail_states,
            wind={"aws_m_s": aws_m_s, "awa_deg": awa_deg, "heel_deg": heel_deg},
        )

        return eval_result, rig_state


def create_default_rig_control_system(
    loa_m: float = 13.94,
    mainsail_area_m2: float = 52.0,
    headsail_area_m2: float = 48.0,
    mast_height_m: float = 18.5,
) -> RigControlSystem:
    """Create a fully initialized RigControlSystem with standard Oceanis 45 rig geometry."""
    rig = create_standard_sloop_rig(
        loa_m=loa_m,
        mainsail_area_m2=mainsail_area_m2,
        headsail_area_m2=headsail_area_m2,
        mast_height_m=mast_height_m,
    )
    return RigControlSystem(rig=rig)
