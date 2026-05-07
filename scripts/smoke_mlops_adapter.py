#!/usr/bin/env python3
"""Smoke-test the event-derived MLOps adapter used by the recipe."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "recipes/mlops/examples/python"))

from metricchrono_mlops_adapter import build_demo_events, snapshots_for_events  # noqa: E402


def main() -> int:
    events = build_demo_events()
    snapshots = snapshots_for_events(events)
    by_phase: dict[str, list[float]] = {}
    for snapshot in snapshots:
        by_phase.setdefault(snapshot.event.phase, []).append(snapshot.scores["behavior"])

    checks = [
        ("normal is quiet", max(by_phase["Normal"]) < 15),
        ("noise is not large", max(by_phase["Small Input Noise"]) < 55),
        ("drift rises", by_phase["Gradual Data Drift"][-1] > by_phase["Gradual Data Drift"][0] + 25),
        ("model change is highest", max(by_phase["Model Change"]) > max(by_phase["Gradual Data Drift"]) + 10),
        ("recovery returns low", by_phase["Recovery"][-1] < 15),
    ]
    failures = [name for name, passed in checks if not passed]
    if failures:
        print("MLOps adapter smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("MLOps adapter smoke passed: event-derived scores follow the recipe story.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
