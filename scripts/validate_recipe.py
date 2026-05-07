#!/usr/bin/env python3
"""Validate the MLOps recipe assets."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from generate_assets import (
    CHANGE_SIZES,
    COMPARISONS,
    ENTRY_FORBIDDEN_WORDS,
    FORBIDDEN_LABELS,
    PHASES,
    SAMPLE_COUNT,
    USER_METRICS,
    build_state_through,
)


ROOT = Path(__file__).resolve().parents[1]
MLOPS_ROOT = ROOT / "recipes" / "mlops"

EXPECTED_DASHBOARDS = {
    "AI Behavior Overview": {"panels": 8, "default": True},
    "Drift Investigation": {"panels": 8, "default": True},
    "RAG Retrieval Drift": {"panels": 6, "default": False},
    "Agent Workflow Drift": {"panels": 6, "default": False},
    "Source Agreement": {"panels": 6, "default": False},
    "Advanced: MetricChrono Internals": {"panels": 6, "default": False},
}
REQUIRED_DEFAULT_TITLES = {"AI Behavior Overview", "Drift Investigation"}
REQUIRED_VARIABLES = {
    "service",
    "environment",
    "model",
    "model_version",
    "workload",
    "stream",
    "comparison",
    "change_size",
    "window",
}
REQUIRED_DOCS = [
    "README.md",
    "docs/metric-contract.md",
    "docs/glossary.md",
    "docs/scenario.md",
    "docs/expected-behavior.md",
    "docs/failure-modes.md",
    "docs/enterprise-boundary.md",
    "docs/alert-rules.md",
    "docs/integration-guide.md",
    "docs/baseline-calibration.md",
    "docs/alert-tuning.md",
    "docs/production-readiness.md",
    "docs/metricchrono-internals.md",
    "docs/package-sources.md",
    "docs/validation-checklist.md",
]
REQUIRED_ARTIFACTS = [
    "fixtures/metricchrono-ladder.json",
    "fixtures/prometheus/metricchrono_latest.prom",
    "fixtures/synthetic_streams/events.jsonl",
    "fixtures/synthetic_streams/scenario_series.json",
    "grafana/provisioning/datasources/prometheus.yml",
    "grafana/provisioning/dashboards/dashboards.yml",
    "prometheus/prometheus.yml",
    "rules/metricchrono_recipe_alerts.yml",
    "examples/python/metricchrono_mlops_adapter.py",
    "examples/python/demo_model_service.py",
]
REQUIRED_REPO_ARTIFACTS = [
    "docker-compose.yml",
    "scripts/smoke_mlops_adapter.py",
    "scripts/smoke_alert_windows.py",
    "tests/test_mlops_adapter.py",
    ".github/workflows/ci.yml",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
]
DESCRIPTION_SECTIONS = [
    "What this shows:",
    "Why you care:",
    "How to read it:",
    "What to do next:",
]
LEGACY_ROOT_ASSET_DIRS = [
    "docs",
    "examples",
    "fixtures",
    "grafana",
    "prometheus",
    "rules",
    "screenshots",
]


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_names(expr: str, known_metrics: set[str]) -> set[str]:
    return {name for name in known_metrics if re.search(rf"\b{name}(?:_bucket|_sum|_count)?\b", expr)}


def has_forbidden_entry_word(text: str) -> str | None:
    lowered = text.lower()
    for word in ENTRY_FORBIDDEN_WORDS:
        if word == "p":
            if re.search(r"\bp\b", lowered):
                return word
        elif word.lower() in lowered:
            return word
    return None


def validate_dashboards(manifest: dict[str, Any], failures: list[str]) -> None:
    dashboard_paths = sorted((MLOPS_ROOT / "grafana/dashboards").glob("*.json"))
    if len(dashboard_paths) != 6:
        fail(f"expected 6 MLOps dashboard JSON files, found {len(dashboard_paths)}", failures)
        return

    known_metrics = set(manifest["required_metrics"]) | set(manifest["advanced_metrics"])
    panel_total = 0
    default_total = 0
    type_counts: Counter[str] = Counter()

    for path in dashboard_paths:
        dashboard = load_json(path)
        title = dashboard.get("title", "")
        if title not in EXPECTED_DASHBOARDS:
            fail(f"unexpected dashboard title in {path}: {title}", failures)
            continue
        expected = EXPECTED_DASHBOARDS[title]
        panels = dashboard.get("panels", [])
        panel_total += len(panels)
        if expected["default"]:
            default_total += len(panels)
        if len(panels) != expected["panels"]:
            fail(f"{title} has {len(panels)} panels, expected {expected['panels']}", failures)
        vars_seen = {item.get("name") for item in dashboard.get("templating", {}).get("list", [])}
        missing_vars = REQUIRED_VARIABLES - vars_seen
        if missing_vars:
            fail(f"{title} missing variables: {sorted(missing_vars)}", failures)

        if expected["default"] and len(panels) > 8:
            fail(f"default dashboard {title} has more than 8 panels", failures)

        for panel in panels:
            panel_title = panel.get("title", "")
            if not panel_title.endswith("?"):
                fail(f"{title} / {panel_title} is not phrased as a question", failures)
            description = panel.get("description", "")
            for section in DESCRIPTION_SECTIONS:
                if section not in description:
                    fail(f"{title} / {panel_title} missing description section {section}", failures)
            if not panel.get("fieldConfig", {}).get("defaults", {}).get("unit"):
                fail(f"{title} / {panel_title} missing unit", failures)
            if not panel.get("datasource"):
                fail(f"{title} / {panel_title} missing datasource", failures)
            targets = panel.get("targets", [])
            if not targets:
                fail(f"{title} / {panel_title} has no targets", failures)

            text_for_entry_check = [title, panel_title, description]
            panel_metrics: set[str] = set()
            scoped = False
            for item in targets:
                expr = item.get("expr", "")
                legend = item.get("legendFormat", "")
                panel_metrics.update(metric_names(expr, known_metrics))
                if 'service="' in expr or 'service="$service"' in expr:
                    scoped = True
                if FORBIDDEN_LABELS & set(re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)=", expr)):
                    fail(f"{title} / {panel_title} uses forbidden high-cardinality label in {expr}", failures)
                text_for_entry_check.append(legend)
                if title in REQUIRED_DEFAULT_TITLES and any(metric.startswith("metricchrono_ladder") or metric.startswith("metricchrono_tick") or metric == "metricchrono_boundary_crossings_total" for metric in panel_metrics):
                    fail(f"default dashboard {title} uses advanced internal metrics in {panel_title}", failures)
            if not scoped:
                fail(f"{title} / {panel_title} has no service scope", failures)
            if not panel_metrics:
                fail(f"{title} / {panel_title} references no known recipe metrics", failures)
            if not panel_metrics <= known_metrics:
                fail(f"{title} / {panel_title} references unknown metrics: {sorted(panel_metrics - known_metrics)}", failures)
            if title == "AI Behavior Overview":
                for text in text_for_entry_check:
                    forbidden = has_forbidden_entry_word(text)
                    if forbidden:
                        fail(f"entry dashboard contains forbidden word '{forbidden}' in {panel_title}", failures)
            type_counts[panel.get("type", "")] += 1

    if panel_total != 40:
        fail(f"expected 40 total MLOps panels including optional dashboards, found {panel_total}", failures)
    if default_total != 16:
        fail(f"expected 16 default panels, found {default_total}", failures)
    if type_counts["table"] < 3:
        fail("expected at least three actionable table panels", failures)


def validate_metrics(manifest: dict[str, Any], failures: list[str]) -> None:
    required = set(USER_METRICS)
    emitted = set(manifest["emitted_metrics"])
    missing = required - emitted
    if missing:
        fail(f"user-facing metrics missing from fixture: {sorted(missing)}", failures)

    labels_by_metric = manifest["label_names_by_metric"]
    for metric, labels in labels_by_metric.items():
        forbidden = FORBIDDEN_LABELS & set(labels)
        if forbidden:
            fail(f"{metric} exposes forbidden high-cardinality labels: {sorted(forbidden)}", failures)

    latest = (MLOPS_ROOT / "fixtures/prometheus/metricchrono_latest.prom").read_text(encoding="utf-8")
    for metric, metric_type in manifest["metric_types"].items():
        if f"# TYPE {metric} {metric_type}" not in latest:
            fail(f"{metric} missing TYPE line in Prometheus fixture", failures)
        if metric_type == "histogram":
            for suffix in ("_bucket", "_sum", "_count"):
                if f"{metric}{suffix}" not in latest:
                    fail(f"{metric} missing histogram suffix {suffix}", failures)

    if set(manifest["phase_names"]) != {phase["name"] for phase in PHASES}:
        fail(f"scenario phases do not match MLOps recipe labels: {manifest['phase_names']}", failures)
    if set(manifest["comparisons"]) != set(COMPARISONS):
        fail("comparison values do not match MLOps recipe")
    if set(manifest["change_sizes"]) != set(CHANGE_SIZES):
        fail("change size values do not match MLOps recipe")
    for assertion in manifest["assertions"]:
        if not assertion["passed"]:
            fail(f"scenario assertion failed: {assertion['name']} ({assertion['evidence']})", failures)

    scenario = load_json(MLOPS_ROOT / "fixtures/synthetic_streams/scenario_series.json")
    samples = scenario.get("samples", [])
    if not samples:
        fail("scenario_series.json has no samples", failures)
    for field in ["input_features", "embedding", "output_distribution", "retrieved_ids", "agent_steps", "source_scores"]:
        if not all(field in sample.get("event", {}) for sample in samples):
            fail(f"scenario samples do not include raw event field: {field}", failures)
    events_path = MLOPS_ROOT / "fixtures/synthetic_streams/events.jsonl"
    if events_path.exists():
        event_lines = [line for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(event_lines) != SAMPLE_COUNT:
            fail(f"events.jsonl has {len(event_lines)} events, expected {SAMPLE_COUNT}", failures)

    previous_counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
    gauge_history: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
    for sample in range(SAMPLE_COUNT):
        state, _ = build_state_through(sample)
        for key, value in state.counters.items():
            if value < previous_counters.get(key, 0.0):
                fail(f"counter decreased before process restart: {key}", failures)
        previous_counters = dict(state.counters)
        for key, value in state.gauges.items():
            gauge_history.setdefault(key, []).append(value)
    for gauge_name in [
        "metricchrono_ai_behavior_change_score",
        "metricchrono_ai_input_change_score",
        "metricchrono_ai_output_change_score",
        "metricchrono_ai_change_score_by_size",
        "metricchrono_ai_drift_state",
        "metricchrono_ai_quality_proxy",
    ]:
        histories = [values for (metric, _), values in gauge_history.items() if metric == gauge_name and len(values) > 1]
        moved = any(max(values) > min(values) for values in histories)
        if not moved:
            fail(f"user-facing gauge did not move in scenario: {gauge_name}", failures)


def validate_docs_and_artifacts(manifest: dict[str, Any], failures: list[str]) -> None:
    for rel in REQUIRED_DOCS + REQUIRED_ARTIFACTS:
        path = MLOPS_ROOT / rel
        if not path.exists():
            fail(f"missing required MLOps recipe artifact: recipes/mlops/{rel}", failures)
        elif path.is_file() and path.stat().st_size == 0:
            fail(f"empty required MLOps recipe artifact: recipes/mlops/{rel}", failures)

    for rel in REQUIRED_REPO_ARTIFACTS:
        path = ROOT / rel
        if not path.exists():
            fail(f"missing required artifact: {rel}", failures)
        elif path.is_file() and path.stat().st_size == 0:
            fail(f"empty required artifact: {rel}", failures)

    if (MLOPS_ROOT / "docs/comparators.md").exists():
        fail("old comparator taxonomy doc should not remain in MLOps output", failures)

    screenshots = {
        path.name for path in (MLOPS_ROOT / "screenshots").glob("*.png")
    }
    required_screenshots = {"ai-behavior-overview.png", "drift-investigation.png"}
    missing_shots = required_screenshots - screenshots
    if missing_shots:
        fail(f"missing default dashboard screenshots: {sorted(missing_shots)}", failures)
    for shot in required_screenshots & screenshots:
        path = MLOPS_ROOT / "screenshots" / shot
        if path.stat().st_size < 10_000:
            fail(f"default dashboard screenshot looks too small: {shot}", failures)

    readme = (MLOPS_ROOT / "README.md").read_text(encoding="utf-8") if (MLOPS_ROOT / "README.md").exists() else ""
    opening = "This recipe shows how to monitor AI behavior drift before labels arrive."
    if opening not in readme[:400]:
        fail("README does not open with MLOps value statement", failures)
    if "![AI Behavior Overview](screenshots/ai-behavior-overview.png)" not in readme:
        fail("README does not immediately show AI Behavior Overview screenshot", failures)
    for term in ["Change score:", "Comparison:", "Change size:"]:
        if term not in readme:
            fail(f"README missing three-term glossary item: {term}", failures)
    advanced_index = readme.find("Advanced:")
    metricchrono_index = readme.find("MetricChrono is the measurement engine")
    if metricchrono_index != -1 and advanced_index != -1 and metricchrono_index < advanced_index:
        fail("README explains MetricChrono before the advanced link", failures)

    alert_text = (MLOPS_ROOT / "docs/alert-rules.md").read_text(encoding="utf-8") + "\n" + (MLOPS_ROOT / "rules/metricchrono_recipe_alerts.yml").read_text(encoding="utf-8")
    forbidden_alert_words = ["coarse", "tier tick", "epsilon", "delta", "ladder"]
    for word in forbidden_alert_words:
        if word in alert_text.lower():
            fail(f"alert examples use non-MLOps wording: {word}", failures)
    for required in ["max by (service, environment, model", "runbook_url", "for: 20s", "for: 10s"]:
        if required not in alert_text:
            fail(f"alert examples missing publishable alert element: {required}", failures)

    for rel, required_terms in {
        "docs/integration-guide.md": ["BehaviorMonitor.from_baseline_events", "MLBehaviorEvent", "Emit Prometheus Metrics"],
        "docs/baseline-calibration.md": ["Baseline Selection", "Score Calibration", "Baseline Refresh Policy"],
        "docs/alert-tuning.md": ["Production tuning", "Behavior Drift Watch", "Possible AI Behavior Incident"],
        "docs/production-readiness.md": ["Production Readiness Checklist", "Baseline events", "Alerts are grouped"],
    }.items():
        text = (MLOPS_ROOT / rel).read_text(encoding="utf-8") if (MLOPS_ROOT / rel).exists() else ""
        for term in required_terms:
            if term not in text:
                fail(f"{rel} missing required guidance term: {term}", failures)

    if "docker compose up" not in readme:
        fail("README does not present Docker Compose as the primary first-run path", failures)
    if "npm run mlops:generate\nnpm run mlops:capture\nnpm run mlops:validate" not in readme:
        fail("README maintainer regeneration order would break screenshot validation", failures)
    if "MetricChrono MLOps Recipes" not in readme:
        fail("README does not name the MLOps Grafana folder", failures)

    provisioning_text = (MLOPS_ROOT / "grafana/provisioning/dashboards/dashboards.yml").read_text(encoding="utf-8")
    prometheus_text = (MLOPS_ROOT / "prometheus/prometheus.yml").read_text(encoding="utf-8")
    docker_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for required, source_name, text in [
        ("folder: MetricChrono MLOps Recipes", "MLOps Grafana provisioning", provisioning_text),
        ("name: metricchrono-mlops-recipes", "MLOps Grafana provisioning", provisioning_text),
        ("job_name: metricchrono-mlops-recipe", "MLOps Prometheus config", prometheus_text),
        ("metricchrono-mlops-recipe:", "Docker Compose", docker_text),
    ]:
        if required not in text:
            fail(f"{source_name} missing expected MLOps-specific name: {required}", failures)

    checklist = (MLOPS_ROOT / "docs/validation-checklist.md").read_text(encoding="utf-8")
    unchecked = re.findall(r"- \[ \]", checklist)
    if unchecked:
        fail("validation checklist contains unchecked items", failures)


def validate_no_legacy_root_assets(failures: list[str]) -> None:
    existing = [rel for rel in LEGACY_ROOT_ASSET_DIRS if (ROOT / rel).exists()]
    if existing:
        fail(f"legacy root MLOps asset directories should not remain; use recipes/mlops instead: {existing}", failures)


def main() -> int:
    failures: list[str] = []
    if not MLOPS_ROOT.exists():
        fail("missing canonical MLOps recipe directory: recipes/mlops", failures)
    manifest_path = MLOPS_ROOT / "fixtures/recipe_manifest.json"
    if not manifest_path.exists():
        fail("recipes/mlops/fixtures/recipe_manifest.json missing; run scripts/generate_assets.py first", failures)
        manifest: dict[str, Any] = {}
    else:
        manifest = load_json(manifest_path)
        validate_dashboards(manifest, failures)
        validate_metrics(manifest, failures)
    validate_docs_and_artifacts(manifest, failures)
    validate_no_legacy_root_assets(failures)

    if failures:
        print("MLOps recipe validation failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("MLOps recipe validation passed.")
    print("Checked: recipes/mlops structure, vocabulary firewall, dashboards, user-facing metrics, docs, screenshots, scenario assertions, alert language, and absence of legacy root MLOps assets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
