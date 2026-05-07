#!/usr/bin/env python3
"""Play the local industrial synthetic scenario once by default."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

SCENARIO = Path(__file__).with_name("scenario.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="repeat the scenario until interrupted")
    parser.add_argument("--sleep", type=float, default=0.15, help="seconds between demo phases")
    parser.add_argument("--output", default="scenario-metrics.prom", help="file to update with the current Prometheus snapshot")
    args = parser.parse_args()

    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    output = Path(args.output)

    while True:
        last_snapshot = ""
        for item in scenario["phase_metrics"]:
            phase = item["phase"]
            snapshot_path = Path(__file__).resolve().parent / item["file"]
            snapshot = snapshot_path.read_text(encoding="utf-8")
            output.write_text(snapshot, encoding="utf-8")
            print(f"{scenario['recipe']}: {phase} -> {output}")
            last_snapshot = snapshot
            time.sleep(args.sleep)
        output.write_text(last_snapshot, encoding="utf-8")
        print(f"{scenario['recipe']}: recovery held in {output}")
        if not args.loop:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
