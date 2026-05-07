#!/usr/bin/env python3
"""Capture real Grafana screenshots for telemetry recipe dashboards."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

from live_grafana_check import (
    free_port,
    http_json,
    query_prometheus,
    start_processes,
    stop_process,
    wait_for,
)


ROOT = Path(__file__).resolve().parents[1]

RECIPE_SPECS = {
    "robotics": {
        "label": "Robotics Telemetry",
        "folder": "MetricChrono Robotics Recipes",
        "provider": "metricchrono-robotics-recipes",
        "job": "metricchrono-robotics-recipe",
        "scenario_paths": [
            ROOT / "recipes/robotics-telemetry/examples/synthetic-robot-scenario/scenario.json",
        ],
        "dashboard_dirs": [
            ROOT / "recipes/robotics-telemetry/grafana/dashboards",
        ],
        "screenshots": {
            "Robot Fleet Overview": ROOT / "recipes/robotics-telemetry/screenshots/robot-fleet-overview.png",
            "Robot Source Agreement": ROOT / "recipes/robotics-telemetry/screenshots/robot-source-agreement.png",
            "Robot Incident Replay": ROOT / "recipes/robotics-telemetry/screenshots/robot-incident-replay.png",
        },
    },
    "industrial": {
        "label": "Industrial Telemetry",
        "folder": "MetricChrono Industrial Recipes",
        "provider": "metricchrono-industrial-recipes",
        "job": "metricchrono-industrial-recipe",
        "scenario_paths": [
            ROOT / "recipes/industrial-telemetry/examples/synthetic-industrial-scenario/scenario.json",
        ],
        "dashboard_dirs": [
            ROOT / "recipes/industrial-telemetry/grafana/dashboards",
        ],
        "screenshots": {
            "Industrial Line Overview": ROOT / "recipes/industrial-telemetry/screenshots/industrial-line-overview.png",
            "Machine / Process Agreement": ROOT / "recipes/industrial-telemetry/screenshots/industrial-machine-agreement.png",
            "Industrial Incident Replay": ROOT / "recipes/industrial-telemetry/screenshots/industrial-incident-replay.png",
        },
    },
}

RECIPE_SPECS["telemetry"] = {
    "label": "Robotics + Industrial Telemetry",
    "folder": "MetricChrono Robotics / Industrial Recipes",
    "provider": "metricchrono-telemetry-recipes",
    "job": "metricchrono-telemetry-recipes",
    "scenario_paths": RECIPE_SPECS["robotics"]["scenario_paths"] + RECIPE_SPECS["industrial"]["scenario_paths"],
    "dashboard_dirs": RECIPE_SPECS["robotics"]["dashboard_dirs"] + RECIPE_SPECS["industrial"]["dashboard_dirs"],
    "screenshots": RECIPE_SPECS["robotics"]["screenshots"] | RECIPE_SPECS["industrial"]["screenshots"],
}

SUBSTITUTIONS = {
    "$site": "local-lab",
    "$environment": "demo",
    "$asset_group": "fleet-a|line-1",
    "$asset": ".*",
    "$source": ".*",
    "$comparison": "known_good_baseline|same_mission_phase|same_machine_state|last_window|commanded_vs_actual|sensor_vs_estimator|sensor_vs_sensor|station_vs_line|current_vs_target|source_vs_source|peer_asset",
    "$change_size": "small|medium|large",
    "$__range": "15m",
}


def spec_for(recipe: str) -> dict[str, Any]:
    try:
        return RECIPE_SPECS[recipe]
    except KeyError as exc:
        raise ValueError(f"unknown recipe {recipe!r}") from exc


def load_phase_snapshots(scenario_path: Path) -> list[str]:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    snapshots: list[str] = []
    for item in scenario["phase_metrics"]:
        path = scenario_path.parent / item["file"]
        snapshots.append(path.read_text(encoding="utf-8"))
    return snapshots


class DomainReplayState:
    def __init__(self, recipe: str = "telemetry", seconds_per_phase: float = 1.2, loop: bool = False) -> None:
        self.recipe = recipe
        self.started_at = time.monotonic()
        self.seconds_per_phase = seconds_per_phase
        self.loop = loop
        self.streams = [load_phase_snapshots(path) for path in spec_for(recipe)["scenario_paths"]]

    def body(self) -> bytes:
        index = int((time.monotonic() - self.started_at) / self.seconds_per_phase)
        parts: list[str] = []
        for snapshots in self.streams:
            phase_index = index % len(snapshots) if self.loop else min(index, len(snapshots) - 1)
            parts.append(snapshots[phase_index])
        return ("\n".join(parts)).encode("utf-8")

    def replay_seconds(self) -> float:
        return max(len(stream) for stream in self.streams) * self.seconds_per_phase + 3.0


def make_handler(replay: DomainReplayState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib hook
            if self.path not in {"/", "/metrics"}:
                self.send_response(404)
                self.end_headers()
                return
            body = replay.body()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return Handler


def write_runtime_files(tmp: Path, prometheus_port: int, metrics_port: int, grafana_port: int, dashboards_dir: Path, recipe: str = "telemetry") -> None:
    spec = spec_for(recipe)
    (tmp / "prometheus-data").mkdir(exist_ok=True)
    (tmp / "grafana-data").mkdir(exist_ok=True)
    (tmp / "grafana-logs").mkdir(exist_ok=True)
    (tmp / "grafana-plugins").mkdir(exist_ok=True)
    (tmp / "grafana-provisioning/datasources").mkdir(parents=True, exist_ok=True)
    (tmp / "grafana-provisioning/dashboards").mkdir(parents=True, exist_ok=True)

    (tmp / "prometheus.yml").write_text(
        f"""global:
  scrape_interval: 1s
  evaluation_interval: 1s

scrape_configs:
  - job_name: {spec["job"]}
    metrics_path: /metrics
    static_configs:
      - targets: ["127.0.0.1:{metrics_port}"]
""",
        encoding="utf-8",
    )
    (tmp / "grafana-provisioning/datasources/prometheus.yml").write_text(
        f"""apiVersion: 1
datasources:
  - name: Prometheus
    uid: Prometheus
    type: prometheus
    access: proxy
    url: http://127.0.0.1:{prometheus_port}
    isDefault: true
    editable: true
""",
        encoding="utf-8",
    )
    (tmp / "grafana-provisioning/dashboards/dashboards.yml").write_text(
        f"""apiVersion: 1
providers:
  - name: {spec["provider"]}
    orgId: 1
    folder: {spec["folder"]}
    type: file
    disableDeletion: false
    editable: true
    options:
      path: {dashboards_dir}
""",
        encoding="utf-8",
    )
    (tmp / "grafana.ini").write_text(
        f"""[paths]
data = {tmp / "grafana-data"}
logs = {tmp / "grafana-logs"}
plugins = {tmp / "grafana-plugins"}
provisioning = {tmp / "grafana-provisioning"}

[server]
http_addr = 127.0.0.1
http_port = {grafana_port}

[security]
admin_user = admin
admin_password = admin

[auth.anonymous]
enabled = true
org_role = Admin

[analytics]
reporting_enabled = false
check_for_updates = false
""",
        encoding="utf-8",
    )


def copy_dashboards(dashboards_dir: Path, recipe: str = "telemetry") -> None:
    dashboards_dir.mkdir(parents=True, exist_ok=True)
    for source_dir in spec_for(recipe)["dashboard_dirs"]:
        for path in source_dir.glob("*.json"):
            shutil.copy2(path, dashboards_dir / path.name)


def substitute(expr: str) -> str:
    rendered = expr
    for key, value in SUBSTITUTIONS.items():
        rendered = rendered.replace(key, value)
    return rendered


def validate_dashboard_data(prometheus_url: str, recipe: str = "telemetry") -> None:
    empty_panels: list[str] = []
    for source_dir in spec_for(recipe)["dashboard_dirs"]:
        for path in sorted(source_dir.glob("*.json")):
            dashboard = json.loads(path.read_text(encoding="utf-8"))
            for panel in dashboard["panels"]:
                panel_has_data = False
                for target in panel.get("targets", []):
                    expr = substitute(target["expr"])
                    if query_prometheus(prometheus_url, expr):
                        panel_has_data = True
                        break
                if not panel_has_data:
                    empty_panels.append(f"{dashboard['title']} / {panel['title']}")
    if empty_panels:
        raise RuntimeError(f"{recipe} dashboard panels with empty Prometheus data: {empty_panels}")


def capture(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "npx",
            "playwright",
            "screenshot",
            "--full-page",
            "--viewport-size=1600,2200",
            "--wait-for-timeout=9000",
            url,
            str(output),
        ],
        cwd=ROOT,
        check=True,
        timeout=120,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", choices=sorted(RECIPE_SPECS), default="telemetry")
    args = parser.parse_args()

    metrics_port = free_port()
    prometheus_port = free_port()
    grafana_port = free_port()
    replay = DomainReplayState(recipe=args.recipe, seconds_per_phase=2.0, loop=True)
    metrics_server = ThreadingHTTPServer(("127.0.0.1", metrics_port), make_handler(replay))
    metrics_thread = Thread(target=metrics_server.serve_forever, daemon=True)
    metrics_thread.start()

    prom_proc = None
    grafana_proc = None
    log_handles: list[Any] = []
    try:
        with tempfile.TemporaryDirectory(prefix=f"metricchrono-{args.recipe}-shots-") as tmp_name:
            tmp = Path(tmp_name)
            dashboards_dir = tmp / "dashboards"
            copy_dashboards(dashboards_dir, args.recipe)
            write_runtime_files(tmp, prometheus_port, metrics_port, grafana_port, dashboards_dir, args.recipe)
            prom_proc, grafana_proc, log_handles = start_processes(tmp, prometheus_port, grafana_port)
            prometheus_url = f"http://127.0.0.1:{prometheus_port}"
            grafana_url = f"http://127.0.0.1:{grafana_port}"
            wait_for(f"{prometheus_url}/api/v1/status/runtimeinfo", timeout=30)
            wait_for(f"{grafana_url}/api/health", auth=True, timeout=45)
            time.sleep(80)
            validate_dashboard_data(prometheus_url, args.recipe)
            search = http_json(f"{grafana_url}/api/search?{urllib.parse.urlencode({'query': ''})}", auth=True)
            by_title = {item["title"]: item for item in search if item.get("type") == "dash-db"}
            screenshots = spec_for(args.recipe)["screenshots"]
            missing = sorted(set(screenshots) - set(by_title))
            if missing:
                raise RuntimeError(f"Grafana did not provision {args.recipe} dashboards: {missing}; search={search}")
            for title, output in screenshots.items():
                url = f"{grafana_url}{by_title[title]['url']}?orgId=1&from=now-2m&to=now&kiosk"
                capture(url, output)
    finally:
        metrics_server.shutdown()
        metrics_thread.join(timeout=5)
        if prom_proc is not None:
            stop_process(prom_proc)
        if grafana_proc is not None:
            stop_process(grafana_proc)
        for handle in log_handles:
            handle.close()
    print(f"Captured {len(spec_for(args.recipe)['screenshots'])} real Grafana {args.recipe} dashboard screenshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
