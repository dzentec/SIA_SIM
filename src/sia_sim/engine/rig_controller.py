"""RigController and PresetOrchestrator for managing rig commands and interlocks."""

from __future__ import annotations

import time
from typing import Any

from sia_sim.contracts.sails import (
    RigState,
    RopeControlInput,
    TravelerControlInput,
)
from sia_sim.physics.sails.rig import RigControlSystem, create_default_rig_control_system


class RigControlError(Exception):
    """Base exception for rig control errors."""

    def __init__(
        self, error_code: str, message: str, status_code: int = 400, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class RigController:
    """Manages rig controls, validates inputs, and orchestrates safety-interlocked presets."""

    def __init__(self, rig_system: RigControlSystem | None = None) -> None:
        self.rig_system = rig_system or create_default_rig_control_system()
        self.active_preset: dict[str, Any] | None = None

    def process_controls(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate and apply a batch of rope / traveler control commands.

        Payload schema:
        {
            "timestamp_ms": int,
            "controls": [
                {"rope_id": "mainsheet", "target_trim": 0.65, "clamped": true},
                {"rope_id": "traveler", "target_pos": -0.20, "clamped": true}
            ]
        }
        """
        controls_list = payload.get("controls", [])
        if not isinstance(controls_list, list):
            raise RigControlError("INVALID_PAYLOAD", "controls must be a list", 400)

        applied_ropes = 0
        applied_traveler = 0

        for item in controls_list:
            if not isinstance(item, dict):
                continue

            rope_id = item.get("rope_id")
            if not rope_id or not isinstance(rope_id, str):
                raise RigControlError("INVALID_ROPE_ID", "Missing or invalid rope_id", 400)

            clamped = bool(item.get("clamped", True))

            if rope_id == "traveler":
                if "target_pos" not in item:
                    raise RigControlError("INVALID_RANGE", "traveler requires target_pos", 400)
                try:
                    pos = float(item["target_pos"])
                except (ValueError, TypeError):
                    raise RigControlError("INVALID_RANGE", "target_pos must be a float", 400) from None

                if not (-1.0 <= pos <= 1.0):
                    raise RigControlError(
                        "INVALID_RANGE",
                        f"target_pos {pos} outside allowed signed range [-1.0, 1.0]",
                        400,
                    )

                self.rig_system.apply_traveler_control(
                    TravelerControlInput(traveler_id="traveler", target_pos=pos, clamped=clamped)
                )
                applied_traveler += 1

            else:
                if rope_id not in self.rig_system.winches:
                    raise RigControlError("INVALID_ROPE_ID", f"Unknown rope_id '{rope_id}'", 400)

                winch = self.rig_system.winches[rope_id]
                if winch.is_broken:
                    raise RigControlError("ROPE_BROKEN", f"Cannot operate broken line '{rope_id}'", 409)

                if "target_trim" not in item:
                    raise RigControlError("INVALID_RANGE", f"Line '{rope_id}' requires target_trim", 400)
                try:
                    trim = float(item["target_trim"])
                except (ValueError, TypeError):
                    raise RigControlError("INVALID_RANGE", "target_trim must be a float", 400) from None

                if not (0.0 <= trim <= 1.0):
                    raise RigControlError(
                        "INVALID_RANGE",
                        f"target_trim {trim} outside allowed range [0.0, 1.0]",
                        400,
                    )

                ease_rate = float(item.get("ease_rate", 1.0))
                self.rig_system.apply_rope_control(
                    RopeControlInput(
                        rope_id=rope_id,
                        target_trim=trim,
                        clamped=clamped,
                        ease_rate=max(0.1, min(5.0, ease_rate)),
                    )
                )
                applied_ropes += 1

        return {
            "status": "APPLIED",
            "applied_ropes": applied_ropes,
            "applied_traveler": applied_traveler,
        }

    def execute_preset(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Orchestrate a multi-step reefing scenario with strict interlock validation.

        Payload schema:
        {
            "timestamp_ms": int,
            "preset": "REEF_1" | "REEF_2" | "FULL_MAIN",
            "params": {}
        }
        """
        preset_name = str(payload.get("preset", "")).upper().strip()
        timestamp_ms = int(payload.get("timestamp_ms", int(time.time() * 1000)))

        mainsheet = self.rig_system.winches["mainsheet"]

        if preset_name in ("REEF_1", "REEF_2", "REEF_3"):
            # Interlock 1: Mainsheet must be eased below 0.35 to relieve boom tension before dropping halyard
            if mainsheet.actual_trim > 0.35:
                return {
                    "status": "REJECTED",
                    "reason": "MAINSHEET_NOT_EASED",
                    "required": {"mainsheet_actual_trim_max": 0.35},
                    "current": {"mainsheet_actual_trim": round(mainsheet.actual_trim, 3)},
                    "message": "Cannot reef: Ease mainsheet below 35% before dropping halyard.",
                }

            reef_level = 1 if preset_name == "REEF_1" else (2 if preset_name == "REEF_2" else 3)
            self.rig_system.reef_level = reef_level

            # Step 2-6: Execute reefing lines
            halyard = self.rig_system.winches["main_halyard"]
            halyard.clamped = False
            halyard.target_trim = 0.75 if reef_level == 1 else (0.50 if reef_level == 2 else 0.25)
            halyard.actual_trim = halyard.target_trim
            halyard.clamped = True

            reef_line = self.rig_system.winches.get(f"reef_line_{reef_level}")
            if reef_line:
                reef_line.clamped = False
                reef_line.target_trim = 1.0
                reef_line.actual_trim = 1.0
                reef_line.clamped = True

            # Ease unused reef lines
            other_reef = self.rig_system.winches.get("reef_line_2" if reef_level == 1 else "reef_line_1")
            if other_reef:
                other_reef.target_trim = 0.0
                other_reef.actual_trim = 0.0

            return {
                "status": "ACCEPTED",
                "preset_id": f"{preset_name.lower()}_{timestamp_ms}",
                "steps": 7,
                "interlocks": ["mainsheet_eased", "halyard_unclamped"],
                "reef_level": reef_level,
                "expected_area_ratio": 0.75 if reef_level == 1 else (0.50 if reef_level == 2 else 0.25),
            }

        elif preset_name in ("FULL_MAIN", "UNREEF"):
            # Interlock: Mainsheet eased below 0.40
            if mainsheet.actual_trim > 0.40:
                return {
                    "status": "REJECTED",
                    "reason": "MAINSHEET_NOT_EASED",
                    "required": {"mainsheet_actual_trim_max": 0.40},
                    "current": {"mainsheet_actual_trim": round(mainsheet.actual_trim, 3)},
                    "message": "Cannot shake out reef: Ease mainsheet below 40%.",
                }

            self.rig_system.reef_level = 0
            halyard = self.rig_system.winches["main_halyard"]
            halyard.clamped = False
            halyard.target_trim = 1.0
            halyard.actual_trim = 1.0
            halyard.clamped = True

            for r_id in ("reef_line_1", "reef_line_2"):
                r_winch = self.rig_system.winches.get(r_id)
                if r_winch:
                    r_winch.target_trim = 0.0
                    r_winch.actual_trim = 0.0
                    r_winch.clamped = True

            return {
                "status": "ACCEPTED",
                "preset_id": f"full_main_{timestamp_ms}",
                "steps": 5,
                "interlocks": ["mainsheet_eased"],
                "reef_level": 0,
                "expected_area_ratio": 1.0,
            }

        else:
            raise RigControlError("INVALID_PRESET", f"Unknown preset '{preset_name}'", 400)

    def get_telemetry_state(
        self,
        timestamp_ms: int | None = None,
        dt: float = 0.01,
        aws_m_s: float = 8.0,
        awa_deg: float = 45.0,
        heel_deg: float = 10.0,
    ) -> RigState:
        """Step or query current rig state."""
        ts = timestamp_ms or int(time.time() * 1000)
        _, rig_state = self.rig_system.step(
            timestamp_ms=ts,
            dt=dt,
            aws_m_s=aws_m_s,
            awa_deg=awa_deg,
            heel_deg=heel_deg,
        )
        return rig_state
