#!/usr/bin/env python3
"""Validate the SRE AI services recipe pack."""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRE_ROOT = ROOT / "recipes" / "sre-ai-services"

DESCRIPTION_FIELDS = [
    "What this shows:",
    "Why you care:",
    "How to read it:",
    "What to do next:",
]

EXPECTED_DASHBOARDS = {
    "ai-service-on-call-overview.json": ("AI Service On-Call Overview", 9),
    "ai-incident-triage.json": ("AI Incident Triage", 12),
    "ai-release-guardrail.json": ("AI Release Guardrail", 8),
}

EXPECTED_ALERTS = {
    "AIServiceFastBurn",
    "AIServiceSlowBurn",
    "AIServiceLatencyDegraded",
    "AIProviderDependencyDegraded",
    "AIBehaviorChangedWhileServiceHealthNormal",
    "AIBehaviorChangeWithQualityDrop",
    "AIReleaseBehaviorRegression",
    "AIBaselineStaleOrLowVolume",
}

EXPECTED_RUNBOOKS = {
    "ai-service-fast-burn.md",
    "ai-service-slow-burn.md",
    "latency-degraded.md",
    "provider-dependency-degraded.md",
    "behavior-changed-health-normal.md",
    "behavior-change-quality-drop.md",
    "release-behavior-regression.md",
    "baseline-stale-low-volume.md",
}

EXPECTED_SCREENSHOTS = {
    "on-call-overview-normal.png",
    "on-call-overview-silent-behavior-change.png",
    "on-call-overview-infra-capacity-incident.png",
    "incident-triage-dependency-provider-issue.png",
    "incident-triage-behavior-quality-drop.png",
    "release-guardrail-deploy-correlated-behavior-change.png",
    "release-guardrail-post-rollback-recovery.png",
}

REQUIRED_DOCS = {
    "docs/metric-contract.md",
    "docs/scenario.md",
    "docs/validation-guide.md",
    "docs/production-mapping.md",
    "docs/alert-tuning.md",
    "docs/baseline-calibration.md",
    "docs/dashboard-panel-guide.md",
    "docs/integration-guide.md",
    "docs/troubleshooting.md",
    "docs/glossary.md",
}

FORBIDDEN_INTERNAL_WORDS = [
    "tick",
    "tier",
    "epsilon",
    "delta",
    "p exponent",
    "ladder",
    "staircase",
    "metricchrono internals",
    "multiscale ledger",
    "phenomenological",
    "subjective time",
]

FORBIDDEN_LABELS = {
    "prompt",
    "request_id",
    "trace_id",
    "session_id",
    "user_id",
    "raw_text",
    "document_id",
    "tool_call_id",
    "span_id",
    "error_text",
}

COMPARATOR_TERMS = [
    "compare",
    "slo",
    "threshold",
    "baseline",
    "previous",
    "stable",
    "canary",
    "dependency",
    "before",
    "after",
    "quality",
    "minimum",
    "capacity",
    "known-good",
    "burn",
]


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_names(text: str) -> set[str]:
    return set(re.findall(r"\bmetricchrono_sre_ai_[a-zA-Z0-9_]+(?:_bucket|_sum|_count)?\b", text))


def declared_metric_names(text: str) -> set[str]:
    names = set(re.findall(r"^# TYPE (metricchrono_sre_ai_[a-zA-Z0-9_]+) ", text, flags=re.MULTILINE))
    names.update(re.findall(r"^(metricchrono_sre_ai_[a-zA-Z0-9_]+(?:_bucket|_sum|_count)?)\{", text, flags=re.MULTILINE))
    return names


def metric_is_known(name: str, known: set[str]) -> bool:
    if name in known:
        return True
    for suffix in ("_bucket", "_sum", "_count"):
        if name.endswith(suffix) and name[: -len(suffix)] in known:
            return True
    return False


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG file: {path}")
    return struct.unpack(">II", header[16:24])


def validate_description(path: Path, dashboard_title: str, panel: dict[str, Any], failures: list[str]) -> None:
    description = panel.get("description", "")
    for field in DESCRIPTION_FIELDS:
        if description.count(field) != 1:
            fail(failures, f"{dashboard_title} / {panel.get('title')} missing exact description field {field}")
    if not any(term in description.lower() for term in COMPARATOR_TERMS):
        fail(failures, f"{dashboard_title} / {panel.get('title')} lacks an operational comparator in the description")


def validate_visible_text(dashboard_title: str, panel: dict[str, Any], failures: list[str]) -> None:
    visible = "\n".join(
        [
            dashboard_title,
            panel.get("title", ""),
            panel.get("description", ""),
            "\n".join(target.get("legendFormat", "") for target in panel.get("targets", [])),
        ]
    ).lower()
    for word in FORBIDDEN_INTERNAL_WORDS:
        if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", visible):
            fail(failures, f"{dashboard_title} / {panel.get('title')} exposes internal term: {word}")


def validate_selector_labels(expr: str, context: str, failures: list[str]) -> None:
    for selector in re.findall(r"\{([^}]*)\}", expr):
        labels = [part.split("=", 1)[0].strip() for part in selector.split(",") if "=" in part]
        duplicates = sorted({label for label in labels if labels.count(label) > 1})
        if duplicates:
            fail(failures, f"{context} has duplicate label matchers in selector: {duplicates}")
        forbidden = FORBIDDEN_LABELS & set(labels)
        if forbidden:
            fail(failures, f"{context} uses forbidden high-cardinality labels: {sorted(forbidden)}")


def validate_dashboards(known_metrics: set[str], failures: list[str]) -> None:
    dashboard_dir = SRE_ROOT / "grafana" / "dashboards"
    dashboard_paths = sorted(dashboard_dir.glob("*.json"))
    if {path.name for path in dashboard_paths} != set(EXPECTED_DASHBOARDS):
        fail(failures, f"SRE dashboard files mismatch: {sorted(path.name for path in dashboard_paths)}")
    total = 0
    for filename, (expected_title, expected_count) in EXPECTED_DASHBOARDS.items():
        path = dashboard_dir / filename
        if not path.exists():
            continue
        dashboard = read_json(path)
        title = dashboard.get("title", "")
        panels = dashboard.get("panels", [])
        if title != expected_title:
            fail(failures, f"{filename} title {title!r}, expected {expected_title!r}")
        if len(panels) != expected_count:
            fail(failures, f"{title} has {len(panels)} panels, expected {expected_count}")
        total += len(panels)
        for panel in panels:
            context = f"{title} / {panel.get('title')}"
            validate_description(path, title, panel, failures)
            validate_visible_text(title, panel, failures)
            if not panel.get("targets"):
                fail(failures, f"{context} has no targets")
            if not panel.get("fieldConfig", {}).get("defaults", {}).get("unit"):
                fail(failures, f"{context} missing unit")
            ref_ids = [target.get("refId", "") for target in panel.get("targets", [])]
            expected_ref_ids = [chr(ord("A") + index) for index in range(len(ref_ids))]
            if ref_ids != expected_ref_ids:
                fail(failures, f"{context} has unstable target refIds: {ref_ids}")
            panel_metrics: set[str] = set()
            for target in panel.get("targets", []):
                expr = target.get("expr", "")
                validate_selector_labels(expr, context, failures)
                names = metric_names(expr)
                panel_metrics.update(names)
                for name in names:
                    if not metric_is_known(name, known_metrics):
                        fail(failures, f"{context} references metric missing from fixtures: {name}")
            if not panel_metrics:
                fail(failures, f"{context} references no SRE recipe metrics")
    if total != 29:
        fail(failures, f"SRE default dashboards have {total} panels, expected 29")


def validate_fixture_labels(text: str, failures: list[str]) -> None:
    for selector in re.findall(r"\{([^}]*)\}", text):
        label_names = {part.split("=", 1)[0].strip() for part in selector.split(",") if "=" in part}
        forbidden = FORBIDDEN_LABELS & label_names
        if forbidden:
            fail(failures, f"SRE fixture uses forbidden labels: {sorted(forbidden)}")


def validate_scenario(failures: list[str]) -> set[str]:
    scenario_path = SRE_ROOT / "examples" / "synthetic-ai-service-scenario" / "scenario.json"
    if not scenario_path.exists():
        fail(failures, "missing SRE scenario.json")
        return set()
    scenario = read_json(scenario_path)
    required = {
        "Normal",
        "Infrastructure / capacity issue",
        "Dependency/provider issue",
        "Silent AI-behavior change",
        "Deploy-correlated behavior change",
        "Recovery",
    }
    phases = set(scenario.get("phases", []))
    missing = required - phases
    if missing:
        fail(failures, f"SRE scenario missing required phases: {sorted(missing)}")
    if "plays once" not in scenario.get("default_run", ""):
        fail(failures, "SRE scenario does not state that the default run plays once")
    snapshots: list[str] = []
    for item in scenario.get("phase_metrics", []):
        rel = item.get("file", "")
        phase_path = scenario_path.parent / rel
        if not phase_path.exists():
            fail(failures, f"SRE scenario missing phase metric snapshot: {rel}")
            continue
        text = phase_path.read_text(encoding="utf-8")
        if "scenario_phase=" not in text:
            fail(failures, f"SRE phase metric snapshot lacks scenario_phase label: {rel}")
        if len(text.strip()) < 5000:
            fail(failures, f"SRE phase metric snapshot looks too small: {rel}")
        validate_fixture_labels(text, failures)
        snapshots.append(text)
    if len({hash(text) for text in snapshots}) < max(5, len(snapshots) // 2):
        fail(failures, "SRE phase metric snapshots are not meaningfully distinct")
    return declared_metric_names("\n".join(snapshots))


def validate_alerts(failures: list[str]) -> None:
    rules_path = SRE_ROOT / "rules" / "sre-ai-service-alerts.yml"
    if not rules_path.exists():
        fail(failures, "missing SRE alert rules")
        return
    rules_text = rules_path.read_text(encoding="utf-8")
    alerts = set(re.findall(r"^\s*- alert: ([A-Za-z0-9_]+)", rules_text, flags=re.MULTILINE))
    missing = EXPECTED_ALERTS - alerts
    extra = alerts - EXPECTED_ALERTS
    if missing:
        fail(failures, f"SRE alert rules missing alerts: {sorted(missing)}")
    if extra:
        fail(failures, f"SRE alert rules contain unexpected alerts: {sorted(extra)}")
    for alert in EXPECTED_ALERTS:
        match = re.search(rf"  - alert: {re.escape(alert)}\n(?P<body>.*?)(?=\n  - alert: |\Z)", rules_text, flags=re.DOTALL)
        if not match:
            continue
        body = match.group("body")
        for required in ["severity:", "page:", "summary:", "description:", "runbook_url:"]:
            if required not in body:
                fail(failures, f"SRE alert {alert} missing {required}")
        if alert in {"AIBehaviorChangedWhileServiceHealthNormal", "AIReleaseBehaviorRegression"}:
            if 'page: "yes"' in body or "severity: page" in body:
                fail(failures, f"SRE alert {alert} pages solely on behavior evidence")
        if alert == "AIBehaviorChangedWhileServiceHealthNormal":
            for guard in ["metricchrono_sre_ai_slo_burn_rate", "metricchrono_sre_ai_low_traffic_flag", "metricchrono_sre_ai_baseline_trust_state_code"]:
                if guard not in body:
                    fail(failures, f"SRE behavior-health-normal alert missing guard: {guard}")
    for word in FORBIDDEN_INTERNAL_WORDS:
        if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", rules_text.lower()):
            fail(failures, f"SRE alert rules expose internal term: {word}")


def validate_docs(failures: list[str]) -> None:
    required_files = {"README.md", *REQUIRED_DOCS}
    for rel in required_files:
        path = SRE_ROOT / rel
        if not path.exists():
            fail(failures, f"SRE missing required doc: {rel}")
        elif path.stat().st_size == 0:
            fail(failures, f"SRE doc is empty: {rel}")
        else:
            in_fence = False
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if line.strip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if not in_fence and re.match(r" {4,}(#|- |\d+\. )", line):
                    fail(failures, f"SRE doc has Markdown rendered as a code block: {rel}:{line_number}")
    readme = (SRE_ROOT / "README.md").read_text(encoding="utf-8") if (SRE_ROOT / "README.md").exists() else ""
    for required in [
        "This recipe is for SREs and observability engineers running AI services.",
        "It adds AI-behavior evidence beside golden signals and SLO burn.",
        "It does not replace SLOs, incident policy, full ML evaluation, tracing, or human review.",
        "Behavior-change alone is a watch signal by default, not a page.",
        "AI Service On-Call Overview",
        "AI Incident Triage",
        "AI Release Guardrail",
        "make sre",
        "npm run sre:start",
        "MetricChrono SRE AI Services Recipes",
    ]:
        if required not in readme[:2500]:
            fail(failures, f"SRE README missing first-screen requirement: {required}")
    metric_contract = (SRE_ROOT / "docs" / "metric-contract.md").read_text(encoding="utf-8") if (SRE_ROOT / "docs" / "metric-contract.md").exists() else ""
    for category in ["Golden Signals", "SLO And Burn", "AI Behavior Evidence", "Dependency / Provider Health", "Release Correlation"]:
        if category not in metric_contract:
            fail(failures, f"SRE metric contract missing category: {category}")
    for label in FORBIDDEN_LABELS:
        if f"`{label}`" not in metric_contract:
            fail(failures, f"SRE metric contract missing forbidden label: {label}")


def validate_runbooks(failures: list[str]) -> None:
    runbooks = {path.name for path in (SRE_ROOT / "runbooks").glob("*.md")}
    if runbooks != EXPECTED_RUNBOOKS:
        fail(failures, f"SRE runbook set mismatch: {sorted(runbooks)}")
    for filename in EXPECTED_RUNBOOKS:
        path = SRE_ROOT / "runbooks" / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for section in ["Meaning", "First checks", "Likely causes", "What to inspect", "What not to do", "Escalation owner", "Recovery criteria"]:
            if f"## {section}" not in text:
                fail(failures, f"SRE runbook {filename} missing section: {section}")


def validate_screenshots(failures: list[str]) -> None:
    screenshots = {path.name for path in (SRE_ROOT / "screenshots").glob("*.png")}
    if screenshots != EXPECTED_SCREENSHOTS:
        fail(failures, f"SRE screenshots mismatch: {sorted(screenshots)}")
    for filename in EXPECTED_SCREENSHOTS:
        path = SRE_ROOT / "screenshots" / filename
        if not path.exists():
            continue
        if path.stat().st_size < 100_000:
            fail(failures, f"SRE screenshot looks too small to be a real Grafana capture: {filename}")
        try:
            width, height = png_dimensions(path)
        except ValueError as exc:
            fail(failures, f"SRE invalid screenshot PNG: {exc}")
            continue
        if width < 1500 or height < 1000:
            fail(failures, f"SRE screenshot dimensions too small: {filename} {width}x{height}")


def validate_generation_and_capture_paths(failures: list[str]) -> None:
    generator = (ROOT / "scripts" / "generate_sre_recipe.py").read_text(encoding="utf-8")
    for forbidden in ["from PIL", "Image.new", "ImageFont.truetype", "/System/Library/Fonts"]:
        if forbidden in generator:
            fail(failures, f"SRE generator still has non-portable screenshot generation dependency: {forbidden}")
    capture_script = (ROOT / "scripts" / "capture_domain_grafana_screenshots.py").read_text(encoding="utf-8")
    for screenshot in EXPECTED_SCREENSHOTS:
        if screenshot not in capture_script:
            fail(failures, f"SRE real Grafana capture path does not include screenshot: {screenshot}")
    hardcoded_homebrew_home = "/opt/homebrew/opt/" + "grafana"
    for rel in ["scripts/live_grafana_check.py", "scripts/start_domain_stack.py", "scripts/start_local_stack.py"]:
        script = (ROOT / rel).read_text(encoding="utf-8")
        if hardcoded_homebrew_home in script:
            fail(failures, f"SRE local Grafana startup has a hardcoded package homepath: {rel}")


def main() -> int:
    failures: list[str] = []
    if not SRE_ROOT.exists():
        fail(failures, "missing recipes/sre-ai-services")
    known_metrics = validate_scenario(failures)
    fixture_text = ""
    for fixture in ["fixtures/expected-metrics-normal.txt", "fixtures/expected-metrics-incident.txt"]:
        path = SRE_ROOT / fixture
        if not path.exists():
            fail(failures, f"SRE missing fixture: {fixture}")
        else:
            fixture_text += path.read_text(encoding="utf-8")
    known_metrics.update(declared_metric_names(fixture_text))
    validate_fixture_labels(fixture_text, failures)
    validate_dashboards(known_metrics, failures)
    validate_alerts(failures)
    validate_docs(failures)
    validate_runbooks(failures)
    validate_screenshots(failures)
    validate_generation_and_capture_paths(failures)
    if failures:
        print("SRE AI services recipe validation failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print("SRE AI services recipe validation passed.")
    print("Checked dashboards, panels, descriptions, metrics, scenario phases, alerts, runbooks, screenshots, docs, and label guardrails.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
