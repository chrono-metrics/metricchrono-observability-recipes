#!/usr/bin/env python3
"""Smoke-test the local Prometheus endpoint implementation without Docker."""

from __future__ import annotations

from http.client import HTTPConnection
from threading import Thread

from serve_metrics import ReplayState, make_handler
from http.server import ThreadingHTTPServer


def main() -> int:
    replay = ReplayState(loop=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(replay))
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        observed_phases: list[str] = []
        for _ in range(3):
            conn = HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/metrics")
            response = conn.getresponse()
            body = response.read().decode("utf-8")
            conn.close()
            if response.status != 200:
                raise RuntimeError(f"unexpected status {response.status}")
            if "# TYPE metricchrono_ai_behavior_change_score gauge" not in body:
                raise RuntimeError("missing behavior change gauge TYPE line")
            if "metricchrono_ai_behavior_distance_bucket" not in body:
                raise RuntimeError("missing behavior distance histogram buckets")
            if 'metricchrono_ai_scenario_state{comparison="normal_baseline",environment="local",model="recommendation-ranker",model_version="v1",phase="Normal",service="checkout-ai",stream="service.health",workload="model_service"} 1.000000' in body:
                observed_phases.append("Normal")
        if not observed_phases:
            raise RuntimeError("did not observe Normal phase marker")
    finally:
        server.shutdown()
        thread.join(timeout=5)
    print(f"Endpoint smoke passed on ephemeral port {port}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
