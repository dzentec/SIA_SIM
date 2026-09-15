"""GPS/GNSS sensor simulation model with fix loss, latency, and noise."""

from __future__ import annotations

import math

import numpy as np

from sia_sim.contracts.data import GPSReading, VesselState
from sia_sim.sensors.degradation import ChannelDegrader, DegradationConfig

# Reference origin for local Cartesian to WGS84 conversion (Adriatic Sea / Split)
DEFAULT_ORIGIN_LAT = 43.500000
DEFAULT_ORIGIN_LON = 16.400000
METERS_PER_DEG_LAT = 111132.95
MPS_TO_KNOTS = 1.943844


class GPSSensorModel:
    """Simulates marine GNSS/GPS receiver with position, SOG, COG, and HDOP."""

    def __init__(
        self,
        rng: np.random.Generator | None = None,
        origin_lat_deg: float = DEFAULT_ORIGIN_LAT,
        origin_lon_deg: float = DEFAULT_ORIGIN_LON,
        sog_config: DegradationConfig | None = None,
        cog_config: DegradationConfig | None = None,
        pos_noise_m: float = 1.5,
        latency_ms: int = 100,  # Typical 10 Hz GPS output latency
    ) -> None:
        self.rng = rng or np.random.default_rng(0)
        self.origin_lat = origin_lat_deg
        self.origin_lon = origin_lon_deg
        self.pos_noise_m = pos_noise_m

        # Degraders for SOG, COG, and position
        self.degrader_sog = ChannelDegrader(
            sog_config
            or DegradationConfig(
                noise_std=0.08,
                latency_ms=latency_ms,
                min_value=0.0,
            ),
            self.rng,
        )
        self.degrader_cog = ChannelDegrader(
            cog_config or DegradationConfig(noise_std=0.5, latency_ms=latency_ms),
            self.rng,
        )

        self._fix_loss = False
        self._frozen = False

    def reset(self, rng: np.random.Generator | None = None) -> None:
        if rng is not None:
            self.rng = rng
        self.degrader_sog.reset(self.rng)
        self.degrader_cog.reset(self.rng)
        self._fix_loss = False
        self._frozen = False

    def set_fix_loss(self, fix_loss: bool) -> None:
        self._fix_loss = fix_loss

    def set_frozen(self, frozen: bool) -> None:
        self._frozen = frozen

    def generate(
        self,
        vessel: VesselState,
        sim_time_ms: int,
        fault_override: bool = False,
        freeze_override: bool = False,
    ) -> GPSReading:
        """Transform true physical vessel motion into degraded GPSReading."""
        is_fault = self._fix_loss or fault_override
        is_freeze = self._frozen or freeze_override

        if is_fault:
            return GPSReading(
                latitude_deg=None,
                longitude_deg=None,
                sog_kt=None,
                cog_deg=None,
                hdop=None,
                fault=True,
            )

        # Raw true coordinates
        meters_per_deg_lon = METERS_PER_DEG_LAT * math.cos(math.radians(self.origin_lat))
        true_lat = self.origin_lat + (vessel.y_m / METERS_PER_DEG_LAT)
        true_lon = self.origin_lon + (vessel.x_m / meters_per_deg_lon)

        # Apply position noise
        lat_noise_deg = (self.rng.normal(0.0, self.pos_noise_m)) / METERS_PER_DEG_LAT
        lon_noise_deg = (self.rng.normal(0.0, self.pos_noise_m)) / meters_per_deg_lon

        sog_raw_kt = vessel.sog_m_s * MPS_TO_KNOTS
        sog_kt = self.degrader_sog.process(sog_raw_kt, sim_time_ms, is_fault, is_freeze)
        cog_deg = self.degrader_cog.process(vessel.cog_deg, sim_time_ms, is_fault, is_freeze)
        if cog_deg is not None:
            cog_deg = cog_deg % 360.0

        lat_out = true_lat + lat_noise_deg
        lon_out = true_lon + lon_noise_deg
        hdop = float(0.8 + abs(self.rng.normal(0.0, 0.1)))

        return GPSReading(
            latitude_deg=float(lat_out),
            longitude_deg=float(lon_out),
            sog_kt=sog_kt,
            cog_deg=cog_deg,
            hdop=hdop,
            fault=False,
        )
