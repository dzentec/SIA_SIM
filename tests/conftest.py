"""Pytest configuration and shared fixtures for SIA Simulation."""

import pytest


@pytest.fixture
def default_seed() -> int:
    return 42
