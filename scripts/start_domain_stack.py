#!/usr/bin/env python3
"""Start a persistent local Grafana stack for telemetry recipe dashboards."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from capture_domain_grafana_screenshots import RECIPE_SPECS, copy_dashboards, spec_for, validate_dashboard_data, write_runtime_files
from live_grafana_check import find_grafana_binary, find_grafana_homepath, grafana_server_command, http_json, wait_for
from stop_domain_stack import stop_stack


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/tmp/metricchrono-telemetry-recipes-live")
BASE_PORTS = {
    "metrics": 8010,
    "prometheus": 9092,
    "grafana": 3001,
}


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def choose_port(start: int) -> int:
    for port in range(start, start + 100):
        if port_is_free(port):
            return port
    raise RuntimeError(f"no free port found from {start} to {start + 99}")


def start(name: str, args: list[str]) -> subprocess.Popen[bytes]:
    log_path = RUNTIME / "logs" / f"{name}.log"
    log = log_path.open("ab")
    return subprocess.Popen(
        args,
        cwd=ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def write_pid(name: str, proc: subprocess.Popen[bytes]) -> None:
    (RUNTIME / "pids" / f"{name}.pid").write_text(str(proc.pid), encoding="utf-8")


def start_processes(ports: dict[str, int], recipe: str) -> dict[str, subprocess.Popen[bytes]]:
    prometheus = shutil.which("prometheus")
    grafana = find_grafana_binary()
    if prometheus is None:
        raise RuntimeError("prometheus binary not found")
    grafana_homepath = find_grafana_homepath(grafana)
    return {
        "metrics": start(
            "metrics",
            [
                sys.executable,
                str(ROOT / "scripts/serve_domain_metrics.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(ports["metrics"]),
                "--recipe",
                recipe,
                "--loop",
            ],
        ),
        "prometheus": start(
            "prometheus",
            [
                prometheus,
                f"--config.file={RUNTIME / 'prometheus.yml'}",
                f"--storage.tsdb.path={RUNTIME / 'prometheus-data'}",
                f"--web.listen-address=127.0.0.1:{ports['prometheus']}",
                "--web.enable-lifecycle",
                "--log.level=error",
            ],
        ),
        "grafana": start(
            "grafana",
            grafana_server_command(grafana, grafana_homepath, RUNTIME / "grafana.ini"),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", choices=sorted(RECIPE_SPECS), default="telemetry")
    args = parser.parse_args()
    spec = spec_for(args.recipe)

    stop_stack()
    ports = {name: choose_port(port) for name, port in BASE_PORTS.items()}
    shutil.rmtree(RUNTIME / "prometheus-data", ignore_errors=True)
    shutil.rmtree(RUNTIME / "grafana-data", ignore_errors=True)
    shutil.rmtree(RUNTIME / "dashboards", ignore_errors=True)
    (RUNTIME / "logs").mkdir(parents=True, exist_ok=True)
    (RUNTIME / "pids").mkdir(parents=True, exist_ok=True)
    copy_dashboards(RUNTIME / "dashboards", args.recipe)
    write_runtime_files(RUNTIME, ports["prometheus"], ports["metrics"], ports["grafana"], RUNTIME / "dashboards", args.recipe)
    (RUNTIME / "recipe.txt").write_text(args.recipe, encoding="utf-8")

    processes = start_processes(ports, args.recipe)
    for name, proc in processes.items():
        write_pid(name, proc)

    try:
        prometheus_url = f"http://127.0.0.1:{ports['prometheus']}"
        grafana_url = f"http://127.0.0.1:{ports['grafana']}"
        wait_for(f"{prometheus_url}/api/v1/status/runtimeinfo", timeout=30)
        wait_for(f"{grafana_url}/api/health", auth=True, timeout=60)
        time.sleep(15)
        targets = http_json(f"{prometheus_url}/api/v1/targets")
        active = targets.get("data", {}).get("activeTargets", [])
        if not any(item.get("health") == "up" for item in active):
            raise RuntimeError(f"Prometheus target was not healthy: {active}")
        validate_dashboard_data(prometheus_url, args.recipe)
        search = http_json(f"{grafana_url}/api/search?query=", auth=True)
        by_title = {item["title"]: item for item in search if item.get("type") == "dash-db"}
        missing = sorted(set(spec["screenshots"]) - set(by_title))
        if missing:
            raise RuntimeError(f"Grafana did not provision {args.recipe} dashboards: {missing}")
        urls = {
            "recipe": args.recipe,
            "label": spec["label"],
            "folder": spec["folder"],
            "grafana": f"http://localhost:{ports['grafana']}",
            "prometheus": f"http://localhost:{ports['prometheus']}",
            "metrics": f"http://localhost:{ports['metrics']}/metrics",
            "dashboards": {
                title: f"http://localhost:{ports['grafana']}{by_title[title]['url']}?orgId=1&from=now-2m&to=now"
                for title in sorted(spec["screenshots"])
            },
        }
        (RUNTIME / "urls.json").write_text(json.dumps(urls, indent=2) + "\n", encoding="utf-8")
    except Exception:
        stop_stack()
        raise

    print(f"Recipe: {spec['label']}")
    print(f"Grafana: http://localhost:{ports['grafana']}")
    print(f"Grafana folder: {spec['folder']}")
    print(f"Prometheus: http://localhost:{ports['prometheus']}")
    print(f"Metrics endpoint: http://localhost:{ports['metrics']}/metrics")
    for title, url in urls["dashboards"].items():
        print(f"{title}: {url}")
    print(f"Runtime files: {RUNTIME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
