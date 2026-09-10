"""Unit tests for RNGManager and PRNG determinism."""

import numpy as np
import pytest

from sia_sim.core.rng import RNGManager


def test_rng_identical_seeds_produce_identical_sequences() -> None:
    rng1 = RNGManager(master_seed=12345)
    rng2 = RNGManager(master_seed=12345)

    gen1 = rng1.get_channel("wind")
    gen2 = rng2.get_channel("wind")

    samples1 = gen1.normal(size=100)
    samples2 = gen2.normal(size=100)

    np.testing.assert_array_equal(samples1, samples2)


def test_rng_different_seeds_produce_distinct_sequences() -> None:
    rng1 = RNGManager(master_seed=12345)
    rng2 = RNGManager(master_seed=67890)

    samples1 = rng1.get_channel("wind").normal(size=100)
    samples2 = rng2.get_channel("wind").normal(size=100)

    assert not np.array_equal(samples1, samples2)


def test_rng_cross_channel_independence() -> None:
    """Drawing numbers from one channel must not perturb another channel's sequence."""
    rngA = RNGManager(master_seed=42)
    rngB = RNGManager(master_seed=42)

    # In rngA, draw 500 samples from 'imu' first
    _ = rngA.get_channel("imu").normal(size=500)
    # Then draw from 'wind'
    wind_samples_A = rngA.get_channel("wind").uniform(size=50)

    # In rngB, draw from 'wind' directly without touching 'imu'
    wind_samples_B = rngB.get_channel("wind").uniform(size=50)

    np.testing.assert_array_equal(wind_samples_A, wind_samples_B)


def test_rng_spawn_independent_streams() -> None:
    rng = RNGManager(master_seed=999)
    streams = rng.spawn(3)
    assert len(streams) == 3

    seq0 = streams[0].integers(0, 10000, size=20)
    seq1 = streams[1].integers(0, 10000, size=20)
    seq2 = streams[2].integers(0, 10000, size=20)

    assert not np.array_equal(seq0, seq1)
    assert not np.array_equal(seq1, seq2)


def test_rng_reset() -> None:
    rng = RNGManager(master_seed=777)
    gen = rng.get_channel("gps")
    first_draw = gen.normal(size=10)

    rng.reset()
    gen_after_reset = rng.get_channel("gps")
    second_draw = gen_after_reset.normal(size=10)

    np.testing.assert_array_equal(first_draw, second_draw)


def test_rng_invalid_spawn() -> None:
    rng = RNGManager(master_seed=1)
    with pytest.raises(ValueError, match="num_streams must be >= 1"):
        rng.spawn(0)
