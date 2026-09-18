# Phase 12 Plan 03 Summary: Rig Control JSON API & Preset Interlock Orchestrator

## Executed Work
- Implemented `RigController` and `RigControlError` in `src/sia_sim/engine/rig_controller.py`.
- Implemented safety interlock engine for reefing presets (`REEF_1`, `REEF_2`, `FULL_MAIN`) enforcing preconditions (e.g., rejecting halyard drops if mainsheet is not eased below 35%).
- Added REST endpoints in `src/sia_sim/web/server.py` and `src/sia_sim/workbench/server.py`:
  - `POST /api/v1/controls/rig`
  - `POST /api/v1/controls/preset`
  - `GET /api/v1/telemetry/rig`
- Implemented integration tests in `tests/integration/test_rig_api.py`.

## Verification
- `uv run pytest tests/integration/test_rig_api.py` -> 7 passed.
