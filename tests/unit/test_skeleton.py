"""Smoke test verifying project skeleton, version, and core dependencies."""

import numpy as np
import polars as pl
import pydantic
import scipy

import sia_sim


def test_package_version() -> None:
    assert sia_sim.__version__ == "0.1.0"


def test_dependencies_importable(default_seed: int) -> None:
    assert default_seed == 42
    assert pydantic.__version__ is not None
    assert np.__version__ is not None
    assert scipy.__version__ is not None
    assert pl.__version__ is not None
