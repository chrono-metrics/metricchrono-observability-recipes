#!/usr/bin/env python3
"""Serve the deterministic MetricChrono recipe as Prometheus text."""

from __future__ import annotations

import argparse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from generate_assets import SAMPLE_COUNT, SCRAPE_INTERVAL_SECONDS, build_state_through


class ReplayState:
    def __init__(self, loop: bool, seconds_per_sample: float = SCRAPE_INTERVAL_SECONDS) -> None:
        self.loop = loop
        self.seconds_per_sample = seconds_per_sample
        self.started_at = time.monotonic()

    def position(self) -> tuple[int, int, int]:
        elapsed_samples = int((time.monotonic() - self.started_at) / self.seconds_per_sample)
        if self.loop:
            cycles, index = divmod(elapsed_samples, SAMPLE_COUNT)
            return index, cycles, 0
        if elapsed_samples >= SAMPLE_COUNT:
            return SAMPLE_COUNT - 1, 0, elapsed_samples - (SAMPLE_COUNT - 1)
        return elapsed_samples, 0, 0

    def exposition(self) -> bytes:
        index, cycles, hold_samples = self.position()
        state, _ = build_state_through(index, completed_cycles=cycles, hold_samples=hold_samples)
        body = state.render().encode("utf-8")
        return body


def make_handler(replay: ReplayState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib hook name
            if self.path not in {"/", "/metrics"}:
                self.send_response(404)
                self.end_headers()
                return
            body = replay.exposition()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()

    replay = ReplayState(loop=args.loop)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(replay))
    print(f"serving MetricChrono recipe metrics at http://{args.host}:{args.port}/metrics")
    server.serve_forever()


if __name__ == "__main__":
    main()
