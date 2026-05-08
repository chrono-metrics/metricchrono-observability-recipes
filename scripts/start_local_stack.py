#!/usr/bin/env python3
"""Start the MLOps recipe stack on stable localhost ports without Docker."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from live_grafana_check import find_grafana_binary, find_grafana_homepath, grafana_server_command, http_json, wait_for, write_runtime_files


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/tmp/metricchrono-observability-recipes-live")
PORTS = {
    "metrics": 8000,
    "prometheus": 9091,
    "grafana": 3000,
}


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def require_ports() -> None:
    busy = [f"{name}:{port}" for name, port in PORTS.items() if not port_is_free(port)]
    if busy:
        raise RuntimeError(f"ports already in use: {', '.join(busy)}")


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


def main() -> int:
    require_ports()
    shutil.rmtree(RUNTIME / "prometheus-data", ignore_errors=True)
    shutil.rmtree(RUNTIME / "grafana-data", ignore_errors=True)
    (RUNTIME / "logs").mkdir(parents=True, exist_ok=True)
    (RUNTIME / "pids").mkdir(parents=True, exist_ok=True)
    write_runtime_files(RUNTIME, PORTS["prometheus"], PORTS["metrics"], PORTS["grafana"])
    grafana = find_grafana_binary()
    grafana_homepath = find_grafana_homepath(grafana)

    processes = {
        "metrics": start(
            "metrics",
            [
                sys.executable,
                str(ROOT / "scripts/serve_metrics.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(PORTS["metrics"]),
            ],
        ),
        "prometheus": start(
            "prometheus",
            [
                "prometheus",
                f"--config.file={RUNTIME / 'prometheus.yml'}",
                f"--storage.tsdb.path={RUNTIME / 'prometheus-data'}",
                f"--web.listen-address=127.0.0.1:{PORTS['prometheus']}",
                "--web.enable-lifecycle",
                "--log.level=error",
            ],
        ),
        "grafana": start(
            "grafana",
            grafana_server_command(grafana, grafana_homepath, RUNTIME / "grafana.ini"),
        ),
    }
    for name, proc in processes.items():
        write_pid(name, proc)

    try:
        wait_for(f"http://127.0.0.1:{PORTS['prometheus']}/api/v1/status/runtimeinfo", timeout=30)
        wait_for(f"http://127.0.0.1:{PORTS['grafana']}/api/health", auth=True, timeout=60)
        time.sleep(8)
        search = http_json(f"http://127.0.0.1:{PORTS['grafana']}/api/search?query=", auth=True)
        dashboards = sorted(item["title"] for item in search if item.get("type") == "dash-db")
        if len(dashboards) != 6:
            raise RuntimeError(f"expected 6 provisioned dashboards, found {dashboards}")
        (RUNTIME / "urls.json").write_text(
            json.dumps(
                {
                    "grafana": f"http://localhost:{PORTS['grafana']}",
                    "prometheus": f"http://localhost:{PORTS['prometheus']}",
                    "metrics": f"http://localhost:{PORTS['metrics']}/metrics",
                    "folder": "MetricChrono MLOps Recipes",
                    "dashboards": dashboards,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        for proc in processes.values():
            proc.terminate()
        raise

    print(f"Grafana: http://localhost:{PORTS['grafana']}")
    print("Grafana folder: MetricChrono MLOps Recipes")
    print(f"Prometheus: http://localhost:{PORTS['prometheus']}")
    print(f"Metrics endpoint: http://localhost:{PORTS['metrics']}/metrics")
    print(f"Runtime files: {RUNTIME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
