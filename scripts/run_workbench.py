"""Convenience runner script for SIA Simulation Workbench Server."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src directory to path
src_dir = Path(__file__).parents[1] / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from sia_sim.web.server import run_server

if __name__ == "__main__":
    run_server(host="127.0.0.1", port=8000)
