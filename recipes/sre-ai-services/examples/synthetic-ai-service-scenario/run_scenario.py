#!/usr/bin/env python3
"""Replay the synthetic AI service SRE scenario as Prometheus text snapshots."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scenario-metrics.prom")
    parser.add_argument("--seconds-per-phase", type=float, default=1.0)
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    scenario = json.loads((HERE / "scenario.json").read_text(encoding="utf-8"))
    output = HERE / args.output
    while True:
        for item in scenario["phase_metrics"]:
            text = (HERE / item["file"]).read_text(encoding="utf-8")
            output.write_text(text, encoding="utf-8")
            print(f"wrote {output} for phase: {item['name']}")
            time.sleep(args.seconds_per_phase)
        if not args.loop:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
