"""Composite SensorPipeline for transforming GroundTruthFrame into SensorFrame."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sia_sim.contracts.data import GroundTruthFrame, SafetyChannelStatus, SensorFrame
from sia_sim.core.rng import RNGManager
from sia_sim.sensors.actuator import ActuatorSensorModel
from sia_sim.sensors.gps import GPSSensorModel
from sia_sim.sensors.imu import IMUSensorModel
from sia_sim.sensors.wind import WindSensorModel

if TYPE_CHECKING:
    from sia_sim.contracts.scenario import ScenarioEvent


class SensorPipeline:
    """Orchestrates all sensor models, PRNG isolation, fault injection, and SensorFrame generation.

    Architectural guarantees:
    - INV-01: Outputs SensorFrame as the only object crossing into SIA Core.
    - INV-02: Ground truth fields are never attached or leaked into SensorFrame.
    - PRNG isolation: Each sensor channel operates on an independent PRNG stream.
    - Monotonic frame sequence numbering starting at 0.
    - Safety channel status propagation for MDA v2.2 §3.5.2 latency guarantees.
    """

    def __init__(
        self,
        master_seed: int = 0,
        enable_mainsheet_sensor: bool = False,
        imu_sample_rate_hz: int = 100,
        imu_lpf_cutoff_hz: float = 20.0,
        safety_channel_status: SafetyChannelStatus = SafetyChannelStatus.WIRED_VERIFIED,
    ) -> None:
        self.master_seed = master_seed
        self.rng_manager = RNGManager(master_seed)
        self.enable_mainsheet_sensor = enable_mainsheet_sensor
        self.imu_sample_rate_hz = imu_sample_rate_hz
        self.imu_lpf_cutoff_hz = imu_lpf_cutoff_hz
        self.safety_channel_status = safety_channel_status

        self.imu = IMUSensorModel(
            rng=self.rng_manager.get_channel("imu"),
            sample_rate_hz=imu_sample_rate_hz,
            lpf_cutoff_hz=imu_lpf_cutoff_hz,
        )
        self.gps = GPSSensorModel(rng=self.rng_manager.get_channel("gps"))
        self.wind = WindSensorModel(rng=self.rng_manager.get_channel("wind"))
        self.actuators = ActuatorSensorModel(
            rng=self.rng_manager.get_channel("actuators"),
            enable_mainsheet_sensor=enable_mainsheet_sensor,
        )

        self._sequence_number = 0

    def reset(self, master_seed: int | None = None) -> None:
        """Reset all channel degraders, PRNG streams, and frame counters."""
        if master_seed is not None:
            self.master_seed = master_seed
        self.rng_manager = RNGManager(self.master_seed)
        self.imu.reset(self.rng_manager.get_channel("imu"))
        self.gps.reset(self.rng_manager.get_channel("gps"))
        self.wind.reset(self.rng_manager.get_channel("wind"))
        self.actuators.reset(self.rng_manager.get_channel("actuators"))
        self._sequence_number = 0

    def process(
        self,
        gt: GroundTruthFrame,
        active_events: tuple[ScenarioEvent, ...] = (),
    ) -> SensorFrame:
        """Transform GroundTruthFrame into observable SensorFrame at current simulation tick."""
        # 1. Evaluate active fault overrides and channel status from scenario events
        imu_fault = False
        imu_freeze = False
        gps_fault = False
        gps_freeze = False
        wind_fault = False
        wind_freeze = False
        actuator_fault = False
        actuator_freeze = False
        current_channel_status = self.safety_channel_status

        for evt in active_events:
            evt_type = evt.event_type.lower()
            sensor_param = str(evt.parameters.get("sensor", "")).lower()

            if evt_type in ("imu_fault", "imu_failure", "sensor_fault_imu") or (
                evt_type == "sensor_fault" and sensor_param == "imu"
            ):
                imu_fault = True
            elif evt_type in ("imu_freeze", "sensor_freeze_imu"):
                imu_freeze = True
            elif evt_type in ("gps_loss", "gps_fix_loss", "sensor_fault_gps") or (
                evt_type == "sensor_fault" and sensor_param == "gps"
            ):
                gps_fault = True
            elif evt_type in ("gps_freeze", "sensor_freeze_gps"):
                gps_freeze = True
            elif evt_type in ("wind_fault", "anemometer_failure", "sensor_fault_wind") or (
                evt_type == "sensor_fault" and sensor_param in ("wind", "anemometer")
            ):
                wind_fault = True
            elif evt_type in ("wind_freeze", "sensor_freeze_wind"):
                wind_freeze = True
            elif evt_type in ("actuator_fault", "rudder_sensor_fault", "sensor_fault_rudder") or (
                evt_type == "sensor_fault" and sensor_param in ("actuator", "actuators", "rudder")
            ):
                actuator_fault = True
            elif evt_type in ("actuator_freeze", "rudder_sensor_freeze"):
                actuator_freeze = True
            elif evt_type in ("channel_status_override", "safety_channel_status", "wireless_mode"):
                status_str = str(evt.parameters.get("status", evt.parameters.get("mode", ""))).upper()
                if status_str in ("WIRELESS", "WIRELESS_ADVISORY", "RF"):
                    current_channel_status = SafetyChannelStatus.WIRELESS_ADVISORY
                elif status_str in ("MIXED", "HYBRID"):
                    current_channel_status = SafetyChannelStatus.MIXED
                elif status_str in ("WIRED", "WIRED_VERIFIED", "RS485"):
                    current_channel_status = SafetyChannelStatus.WIRED_VERIFIED

        # 2. Run channel models
        imu_reading = self.imu.generate(
            vessel=gt.vessel,
            sim_time_ms=gt.sim_time_ms,
            fault_override=imu_fault,
            freeze_override=imu_freeze,
        )

        gps_reading = self.gps.generate(
            vessel=gt.vessel,
            sim_time_ms=gt.sim_time_ms,
            fault_override=gps_fault,
            freeze_override=gps_freeze,
        )

        wind_reading = self.wind.generate(
            env=gt.environment,
            vessel=gt.vessel,
            sim_time_ms=gt.sim_time_ms,
            fault_override=wind_fault,
            freeze_override=wind_freeze,
        )

        actuator_reading = self.actuators.generate(
            vessel=gt.vessel,
            sim_time_ms=gt.sim_time_ms,
            fault_override=actuator_fault,
            freeze_override=actuator_freeze,
        )

        # 3. Assemble immutable SensorFrame
        frame = SensorFrame(
            sim_time_ms=gt.sim_time_ms,
            imu=imu_reading,
            gps=gps_reading,
            wind=wind_reading,
            actuators=actuator_reading,
            sequence_number=self._sequence_number,
            safety_channel_status=current_channel_status,
        )

        self._sequence_number += 1
        return frame
