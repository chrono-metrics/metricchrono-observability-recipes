#!/usr/bin/env python3
"""Stop the detached local recipe stack started by start_local_stack.py."""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path


RUNTIME = Path("/tmp/metricchrono-observability-recipes-live")


def stop_pid(path: Path) -> None:
    pid = int(path.read_text(encoding="utf-8").strip())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        path.unlink(missing_ok=True)
        return
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            path.unlink(missing_ok=True)
            return
        time.sleep(0.25)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    path.unlink(missing_ok=True)


def main() -> int:
    pid_dir = RUNTIME / "pids"
    if not pid_dir.exists():
        print("No local stack PID directory found.")
        return 0
    for path in sorted(pid_dir.glob("*.pid")):
        stop_pid(path)
    print("Stopped local MetricChrono recipe stack.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
