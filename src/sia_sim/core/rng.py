"""Deterministic, isolated PRNG stream management for SIA Simulation."""

import hashlib
from collections.abc import Sequence

import numpy as np


class RNGManager:
    """Manager for isolated, reproducible NumPy PRNG generators.

    Uses SeedSequence spawning and deterministic channel hashing to ensure:
    1. Independent PRNG streams per sensor/subsystem channel.
    2. Zero cross-channel RNG coupling (drawing numbers on 'wind' does not mutate 'imu').
    3. Bit-for-bit repeatability given the same master seed.
    """

    def __init__(self, master_seed: int) -> None:
        self._master_seed = master_seed
        self._seed_seq = np.random.SeedSequence(master_seed)
        self._channel_generators: dict[str, np.random.Generator] = {}

    @property
    def master_seed(self) -> int:
        """Master seed used for initializing this RNGManager."""
        return self._master_seed

    def get_channel(self, channel_name: str) -> np.random.Generator:
        """Retrieve or create an isolated, deterministic Generator for a named channel."""
        if channel_name not in self._channel_generators:
            # Hash channel_name into a stable 32-bit integer offset
            channel_hash = int(hashlib.sha256(channel_name.encode("utf-8")).hexdigest()[:8], 16)
            # Spawn a unique SeedSequence child using master_seed and channel_hash
            child_seed_seq = np.random.SeedSequence(
                entropy=self._master_seed,
                spawn_key=(channel_hash,),
            )
            self._channel_generators[channel_name] = np.random.default_rng(child_seed_seq)

        return self._channel_generators[channel_name]

    def spawn(self, num_streams: int) -> Sequence[np.random.Generator]:
        """Spawn N independent child generators from the master sequence."""
        if num_streams < 1:
            raise ValueError(f"num_streams must be >= 1, got {num_streams}")
        child_sequences = self._seed_seq.spawn(num_streams)
        return [np.random.default_rng(seq) for seq in child_sequences]

    def reset(self) -> None:
        """Reset all channel generators to their initial state with the master seed."""
        self._seed_seq = np.random.SeedSequence(self._master_seed)
        self._channel_generators.clear()

    def __repr__(self) -> str:
        channels = list(self._channel_generators.keys())
        return f"RNGManager(master_seed={self._master_seed}, active_channels={channels})"
