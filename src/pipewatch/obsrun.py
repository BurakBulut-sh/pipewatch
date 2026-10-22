#!/usr/bin/env python3
"""Entry point for obsrun command.

This module provides a Python wrapper that invokes the obsrun bash script.
It ensures the bash script is available and executable.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def get_obsrun_script() -> str:
    """Get the path to the obsrun bash script."""
    # First check if OBSRUN_PATH is set
    if obsrun_path := os.environ.get("OBSRUN_PATH"):
        return obsrun_path

    # Look in the same directory as this file
    module_dir = Path(__file__).parent
    script_path = module_dir / "obsrun.sh"

    if script_path.exists():
        return str(script_path)

    # Check in PATH
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        script = Path(path_dir) / "obsrun"
        if script.exists():
            return str(script)
        script = Path(path_dir) / "obsrun.sh"
        if script.exists():
            return str(script)

    raise RuntimeError("obsrun script not found. Set OBSRUN_PATH environment variable.")


def main() -> int:
    """Run obsrun with the provided command."""
    if len(sys.argv) < 2:
        print("Usage: obsrun <command>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Environment variables:", file=sys.stderr)
        print("  PIPEWATCH_EVENTS_FILE    Output file for events", file=sys.stderr)
        print("  PIPEWATCH_STEP_NAME      Name of the step being executed", file=sys.stderr)
        print("  PIPEWATCH_SAMPLE_ID      Sample identifier", file=sys.stderr)
        print("  PIPEWATCH_STDOUT_PATH    Path to stdout log file", file=sys.stderr)
        print("  PIPEWATCH_STDERR_PATH    Path to stderr log file", file=sys.stderr)
        return 1

    obsrun_script = get_obsrun_script()

    # The command to execute is everything after the script name
    command = " ".join(sys.argv[1:])

    # Run obsrun.sh with the command
    result = subprocess.run(
        ["bash", obsrun_script, command],
        capture_output=False,
    )

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
