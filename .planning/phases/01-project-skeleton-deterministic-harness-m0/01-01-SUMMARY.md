---
phase: 01-project-skeleton-deterministic-harness-m0
plan: 01
subsystem: infra
tags: [uv, python312, pydantic, numpy, scipy, polars, pyarrow, pytest, ruff, mypy]

requires: []
provides:
  - "Configured Python 3.12+ uv environment with dependencies"
  - "Tested package skeleton in src/sia_sim"
  - "Strict linting (ruff) and type checking (mypy) configurations"
affects:
  - "01-02-PLAN"
  - "all subsequent phases"

actuals:
  tokens: 1800
  tasks: 2
  commits: 1

tech-stack:
  added:
    - "Python 3.12.14"
    - "uv 0.10.2"
    - "Pydantic 2.13.5"
    - "NumPy 2.5.3"
    - "SciPy 1.18.1"
    - "Polars 1.44.2"
    - "PyArrow 25.0.1"
    - "pytest 9.1.1"
    - "ruff 0.16.7"
    - "mypy 2.3.1"
  patterns:
    - "uv-managed virtualenv with pyproject.toml and hatchling wheel build"
    - "strict static typing with mypy and strict ruff lint rules"

key-files:
  created:
    - pyproject.toml
    - ruff.toml
    - README.md
    - src/sia_sim/__init__.py
    - tests/conftest.py
    - tests/unit/test_skeleton.py
  modified: []

key-decisions:
  - "Use hatchling build backend for clean src/ layout packaging"
  - "Apply mypy ignore_missing_imports override for scipy modules"

requirements-completed:
  - SKEL-01

coverage:
  - id: D1
    description: "Configured Python 3.12+ project with uv, pyproject.toml, and dependencies"
    requirement: "SKEL-01"
    verification:
      - kind: unit
        ref: "tests/unit/test_skeleton.py"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-09-11
status: complete
---

# Plan 01-01 Summary: Project Skeleton & Tooling

**Configured reproducible Python 3.12+ repository with uv, core dependencies, package skeleton in `src/sia_sim`, and green pytest/ruff/mypy suites.**

## Accomplishments

- Initialized `pyproject.toml` targeting Python 3.12+ with runtime dependencies (`pydantic>=2.10`, `numpy>=2.0`, `scipy>=1.14`, `polars>=1.0`, `pyarrow>=18.0`) and dev dependencies (`pytest`, `hypothesis`, `ruff`, `mypy`).
- Configured strict linting rules in `ruff.toml` and static type checking in `pyproject.toml`.
- Created package root `src/sia_sim/__init__.py` exposing `__version__ = "0.1.0"`.
- Setup test harness in `tests/conftest.py` and smoke tests in `tests/unit/test_skeleton.py`.
- Verified `uv sync`, `uv run pytest`, `uv run ruff check .`, and `uv run mypy src tests` pass with 0 errors.
