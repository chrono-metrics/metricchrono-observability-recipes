#!/usr/bin/env python3
"""Capture real Grafana dashboard screenshots for the MLOps recipe."""

from __future__ import annotations

import subprocess
import tempfile
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from live_grafana_check import (
    free_port,
    http_json,
    start_processes,
    stop_process,
    validate_dashboards,
    wait_for,
    write_runtime_files,
)
from serve_metrics import ReplayState, make_handler


ROOT = Path(__file__).resolve().parents[1]
MLOPS_ROOT = ROOT / "recipes" / "mlops"
SCREENSHOTS = {
    "AI Behavior Overview": "ai-behavior-overview.png",
    "Drift Investigation": "drift-investigation.png",
}


def capture(url: str, output: Path) -> None:
    subprocess.run(
        [
            "npx",
            "playwright",
            "screenshot",
            "--full-page",
            "--viewport-size=1600,1200",
            "--wait-for-timeout=8000",
            url,
            str(output),
        ],
        cwd=ROOT,
        check=True,
        timeout=90,
    )


def main() -> int:
    metrics_port = free_port()
    prometheus_port = free_port()
    grafana_port = free_port()

    replay = ReplayState(loop=False)
    metrics_server = ThreadingHTTPServer(("127.0.0.1", metrics_port), make_handler(replay))
    metrics_thread = Thread(target=metrics_server.serve_forever, daemon=True)
    metrics_thread.start()

    prom_proc = None
    grafana_proc = None
    log_handles = []
    try:
        with tempfile.TemporaryDirectory(prefix="metricchrono-shots-") as tmp_name:
            tmp = Path(tmp_name)
            write_runtime_files(tmp, prometheus_port, metrics_port, grafana_port)
            prom_proc, grafana_proc, log_handles = start_processes(tmp, prometheus_port, grafana_port)
            prometheus_url = f"http://127.0.0.1:{prometheus_port}"
            grafana_url = f"http://127.0.0.1:{grafana_port}"
            wait_for(f"{prometheus_url}/api/v1/status/runtimeinfo", timeout=30)
            wait_for(f"{grafana_url}/api/health", auth=True, timeout=45)
            time.sleep(122)
            validate_dashboards(prometheus_url, grafana_url)
            search = http_json(f"{grafana_url}/api/search?query=", auth=True)
            by_title = {item["title"]: item for item in search if item.get("type") == "dash-db"}
            (MLOPS_ROOT / "screenshots").mkdir(exist_ok=True)
            for title, filename in SCREENSHOTS.items():
                item = by_title[title]
                url = f"{grafana_url}{item['url']}?orgId=1&from=now-2m&to=now&kiosk"
                capture(url, MLOPS_ROOT / "screenshots" / filename)
    finally:
        metrics_server.shutdown()
        metrics_thread.join(timeout=5)
        if prom_proc is not None:
            stop_process(prom_proc)
        if grafana_proc is not None:
            stop_process(grafana_proc)
        for handle in log_handles:
            handle.close()
    print("Captured 2 default Grafana dashboard screenshots in recipes/mlops/screenshots/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
