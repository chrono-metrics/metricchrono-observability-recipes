#!/usr/bin/env python3
"""Run a local Prometheus/Grafana provisioning check for the recipe dashboards."""

from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

from serve_metrics import ReplayState, make_handler


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "$service": "checkout-ai",
    "$environment": "local",
    "$workload": "model_service",
    "$stream": "overall.behavior",
    "$model": "recommendation-ranker",
    "$model_version": "v2",
    "$comparison": "normal_baseline",
    "$change_size": "small|medium|large",
    "$window": "30s",
    "$__range": "2m",
}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str, auth: bool = False, payload: dict[str, Any] | None = None) -> Any:
    request = urllib.request.Request(url)
    if auth:
        token = base64.b64encode(b"admin:admin").decode("ascii")
        request.add_header("Authorization", f"Basic {token}")
    if payload is not None:
        request.data = json.dumps(payload).encode("utf-8")
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc
    return json.loads(body)


def wait_for(url: str, auth: bool = False, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            http_json(url, auth=auth)
            return
        except Exception as exc:  # noqa: BLE001 - status probe only
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def substitute(expr: str) -> str:
    rendered = expr
    for key, value in DEFAULTS.items():
        rendered = rendered.replace(key, value)
    return rendered


def query_prometheus(prometheus_url: str, expr: str) -> list[Any]:
    encoded = urllib.parse.urlencode({"query": expr})
    payload = http_json(f"{prometheus_url}/api/v1/query?{encoded}")
    if payload.get("status") != "success":
        raise RuntimeError(f"query failed: {expr}: {payload}")
    result = payload.get("data", {}).get("result", [])
    if isinstance(result, list):
        return result
    return [result]


def write_runtime_files(tmp: Path, prometheus_port: int, metrics_port: int, grafana_port: int) -> None:
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
  - job_name: metricchrono-recipe
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
  - name: metricchrono-recipes
    orgId: 1
    folder: MetricChrono Recipes
    type: file
    disableDeletion: false
    editable: true
    options:
      path: {ROOT / "grafana/dashboards"}
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


def start_processes(
    tmp: Path,
    prometheus_port: int,
    grafana_port: int,
) -> tuple[subprocess.Popen[str], subprocess.Popen[str], list[Any]]:
    prometheus = shutil.which("prometheus")
    grafana = shutil.which("grafana")
    if prometheus is None:
        raise RuntimeError("prometheus binary not found")
    if grafana is None:
        raise RuntimeError("grafana binary not found")
    prom_log = (tmp / "prometheus.log").open("w", encoding="utf-8")
    grafana_log = (tmp / "grafana.log").open("w", encoding="utf-8")
    prom_proc = subprocess.Popen(
        [
            prometheus,
            f"--config.file={tmp / 'prometheus.yml'}",
            f"--storage.tsdb.path={tmp / 'prometheus-data'}",
            f"--web.listen-address=127.0.0.1:{prometheus_port}",
            "--web.enable-lifecycle",
            "--log.level=error",
        ],
        stdout=prom_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    grafana_proc = subprocess.Popen(
        [
            grafana,
            "server",
            "--homepath",
            "/opt/homebrew/opt/grafana/share/grafana",
            "--config",
            str(tmp / "grafana.ini"),
        ],
        env={**os.environ, "GF_LOG_LEVEL": "info"},
        stdout=grafana_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return prom_proc, grafana_proc, [prom_log, grafana_log]


def stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def assert_running(proc: subprocess.Popen[str], name: str) -> None:
    if proc.poll() is not None:
        raise RuntimeError(f"{name} exited early with code {proc.returncode}")


def tail(path: Path, limit: int = 4000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[-limit:]


def validate_dashboards(prometheus_url: str, grafana_url: str) -> dict[str, Any]:
    expected_titles = {
        "AI Behavior Overview",
        "Drift Investigation",
        "RAG Retrieval Drift",
        "Agent Workflow Drift",
        "Source Agreement",
        "Advanced: MetricChrono Internals",
    }
    search = http_json(f"{grafana_url}/api/search?query=", auth=True)
    provisioned_titles = {item["title"] for item in search if item.get("type") == "dash-db"}
    missing = expected_titles - provisioned_titles
    if missing:
        imports: dict[str, str] = {}
        for path in sorted((ROOT / "grafana/dashboards").glob("*.json")):
            dashboard = json.loads(path.read_text(encoding="utf-8"))
            if dashboard.get("title") not in missing:
                continue
            try:
                response = http_json(
                    f"{grafana_url}/api/dashboards/db",
                    auth=True,
                    payload={"dashboard": dashboard, "overwrite": True},
                )
                imports[dashboard["title"]] = json.dumps(response, sort_keys=True)
            except Exception as exc:  # noqa: BLE001 - diagnostic path only
                imports[dashboard["title"]] = repr(exc)
        raise RuntimeError(
            f"Grafana provisioning missing dashboards: {sorted(missing)}; "
            f"search returned: {json.dumps(search, sort_keys=True)}; "
            f"manual import diagnostics: {json.dumps(imports, sort_keys=True)}"
        )

    checked_panels = 0
    empty_panels: list[str] = []
    dashboard_paths = sorted((ROOT / "grafana/dashboards").glob("*.json"))
    for path in dashboard_paths:
        dashboard = json.loads(path.read_text(encoding="utf-8"))
        for panel in dashboard["panels"]:
            checked_panels += 1
            panel_has_data = False
            for target in panel.get("targets", []):
                expr = substitute(target["expr"])
                result = query_prometheus(prometheus_url, expr)
                if result:
                    panel_has_data = True
                    break
            if not panel_has_data:
                empty_panels.append(f"{dashboard['title']} / {panel['title']}")
    if empty_panels:
        raise RuntimeError(f"panels with empty live data: {empty_panels}")
    return {
        "provisioned_dashboards": sorted(provisioned_titles & expected_titles),
        "checked_panels": checked_panels,
    }


def main() -> int:
    metrics_port = free_port()
    prometheus_port = free_port()
    grafana_port = free_port()

    replay = ReplayState(loop=False)
    metrics_server = ThreadingHTTPServer(("127.0.0.1", metrics_port), make_handler(replay))
    metrics_thread = Thread(target=metrics_server.serve_forever, daemon=True)
    metrics_thread.start()

    prom_proc: subprocess.Popen[str] | None = None
    grafana_proc: subprocess.Popen[str] | None = None
    log_handles: list[Any] = []
    try:
        with tempfile.TemporaryDirectory(prefix="metricchrono-live-") as tmp_name:
            tmp = Path(tmp_name)
            write_runtime_files(tmp, prometheus_port, metrics_port, grafana_port)
            prom_proc, grafana_proc, log_handles = start_processes(tmp, prometheus_port, grafana_port)
            prometheus_url = f"http://127.0.0.1:{prometheus_port}"
            grafana_url = f"http://127.0.0.1:{grafana_port}"
            try:
                wait_for(f"{prometheus_url}/api/v1/status/runtimeinfo", timeout=30)
                wait_for(f"{grafana_url}/api/health", auth=True, timeout=45)
                time.sleep(35)
                assert_running(prom_proc, "prometheus")
                assert_running(grafana_proc, "grafana")
                targets = http_json(f"{prometheus_url}/api/v1/targets")
                active = targets.get("data", {}).get("activeTargets", [])
                if not any(item.get("health") == "up" for item in active):
                    raise RuntimeError(f"Prometheus target was not healthy: {active}")
                summary = validate_dashboards(prometheus_url, grafana_url)
            except Exception as exc:
                raise RuntimeError(
                    f"{exc}\n--- prometheus log ---\n{tail(tmp / 'prometheus.log')}"
                    f"\n--- grafana log ---\n{tail(tmp / 'grafana.log')}"
                ) from exc
    finally:
        metrics_server.shutdown()
        metrics_thread.join(timeout=5)
        if prom_proc is not None:
            stop_process(prom_proc)
        if grafana_proc is not None:
            stop_process(grafana_proc)
        for handle in log_handles:
            handle.close()

    print(
        "Live Grafana check passed: "
        f"{len(summary['provisioned_dashboards'])} provisioned dashboards, "
        f"{summary['checked_panels']} panels with live Prometheus data."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
