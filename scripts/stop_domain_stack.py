#!/usr/bin/env python3
"""Stop the local telemetry-family Grafana/Prometheus stack."""

from __future__ import annotations

import argparse
import os
import signal
import time
from pathlib import Path


RUNTIME = Path("/tmp/metricchrono-telemetry-recipes-live")


def stop_pid(path: Path) -> None:
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        return
    except ValueError:
        path.unlink(missing_ok=True)
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        path.unlink(missing_ok=True)
        return
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            path.unlink(missing_ok=True)
            return
        time.sleep(0.2)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    path.unlink(missing_ok=True)


def stop_stack() -> None:
    for name in ["grafana", "prometheus", "metrics"]:
        stop_pid(RUNTIME / "pids" / f"{name}.pid")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", choices=["robotics", "industrial", "telemetry"], default="telemetry")
    args = parser.parse_args()
    recorded = (RUNTIME / "recipe.txt").read_text(encoding="utf-8").strip() if (RUNTIME / "recipe.txt").exists() else "unknown"
    stop_stack()
    print(f"Stopped {args.recipe} telemetry-family stack processes recorded in {RUNTIME / 'pids'}; previous recipe: {recorded}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
