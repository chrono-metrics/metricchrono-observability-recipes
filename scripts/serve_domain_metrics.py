#!/usr/bin/env python3
"""Serve telemetry recipe phase metrics for local Grafana review."""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from capture_domain_grafana_screenshots import DomainReplayState, RECIPE_SPECS, make_handler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--recipe", choices=sorted(RECIPE_SPECS), default="telemetry")
    parser.add_argument("--seconds-per-phase", type=float, default=2.0)
    parser.add_argument("--loop", action="store_true", help="cycle through phases continuously")
    args = parser.parse_args()

    replay = DomainReplayState(recipe=args.recipe, seconds_per_phase=args.seconds_per_phase, loop=args.loop)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(replay))
    print(f"serving {args.recipe} recipe metrics at http://{args.host}:{args.port}/metrics")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
