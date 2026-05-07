#!/usr/bin/env python3
"""Validate telemetry recipe packs."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECIPES = ROOT / "recipes"

DESCRIPTION_FIELDS = [
    "Question answered:",
    "How to read it:",
    "Why it matters:",
    "Next action:",
]

FORBIDDEN_INTERNAL_WORDS = [
    "epsilon",
    "delta",
    " tick",
    " tier",
    "ladder",
    "consensus tick field",
    "skip-list",
]

FORBIDDEN_LABELS = {
    "serial_number",
    "part_id",
    "lot_id",
    "work_order_id",
    "operator_id",
    "user_id",
    "session_id",
    "trace_id",
    "event_id",
    "bag_file",
    "raw_topic",
    "raw_tag",
    "free_form_message",
    "error_text",
    "document_id",
}

EXPECTED = {
    "robotics-telemetry": {
        "readme_opening": "This recipe helps robotics engineers see when a robot's motion, estimator, sensors, or actuators changed meaningfully while ordinary telemetry may still look normal.",
        "dashboards": {
            "robot-fleet-overview.json": ("Robot Fleet Overview", 10),
            "robot-source-agreement.json": ("Robot Source Agreement", 11),
            "robot-incident-replay.json": ("Robot Incident Replay", 8),
        },
        "screenshots": [
            "robot-fleet-overview.png",
            "robot-source-agreement.png",
            "robot-incident-replay.png",
        ],
        "rules": "robotics-alerts.yml",
        "alerts": {
            "RobotBehaviorChanged",
            "RobotSourceDisagreement",
            "RobotSourceMissingOrLate",
            "RobotTrackingDeviation",
            "RobotActuatorEffortChanged",
            "RobotLocalizationDisagreement",
            "RobotIncidentCandidate",
            "RobotRecoveryIncomplete",
        },
        "example": "synthetic-robot-scenario",
        "make_command": "make robotics",
        "npm_command": "npm run robotics:start",
        "grafana_folder": "MetricChrono Robotics Recipes",
        "operational_boundary": "does not replace safety systems, robot controllers, ROS diagnostics, fleet managers, or incident policy",
        "contract_forbidden_labels": {
            "serial_number",
            "operator_id",
            "user_id",
            "session_id",
            "event_id",
            "free_form_message",
            "error_text",
            "document_id",
            "bag_file",
            "raw_topic",
            "trace_id",
        },
        "comparison_terms": {
            "known_good_baseline",
            "last_window",
            "same_mission_phase",
            "peer_asset",
            "commanded_vs_actual",
            "sensor_vs_estimator",
            "source_vs_source",
            "pre_maintenance",
            "post_maintenance",
            "actuator_vs_peer_actuator",
            "sensor_vs_controller",
        },
        "forbidden_doc_terms": {
            "same_machine_state",
            "station_vs_line",
            "sensor_vs_sensor",
            "current_vs_target",
            "line-wide",
            "lines, cells",
            "machine state",
            "station cycle",
            "process setpoint",
            "opc ua",
            "plc",
            "scada",
            "historian",
            "historians",
            "work order",
        },
        "phases": {
            "Normal navigation",
            "Harmless small jitter",
            "Perception/source degradation",
            "Tracking deviation or control oscillation",
            "Actuator effort / thermal or current change",
            "Incident candidate",
            "Recovery or incomplete recovery",
        },
        "baseline_terms": {
            "known-good navigation on same map / route type",
            "known-good docking behavior",
            "known-good manipulation cycle",
            "known-good idle state",
            "known-good robot of same hardware class",
            "previous stable software release",
            "same_mission_phase",
            "commanded_vs_actual",
            "sensor_vs_estimator",
        },
        "native_metric_fragments": [
            "_state",
            "_speed",
            "_velocity",
            "_freshness_seconds",
            "_voltage",
            "_current",
            "_temperature",
            "_distance_bucket",
        ],
    },
    "industrial-telemetry": {
        "readme_opening": "This recipe helps industrial telemetry engineers see when a machine, station, line, sensor, or process cycle changed meaningfully before the failure becomes obvious in downtime, scrap, or alarms.",
        "dashboards": {
            "industrial-line-overview.json": ("Industrial Line Overview", 10),
            "industrial-machine-agreement.json": ("Machine / Process Agreement", 11),
            "industrial-incident-replay.json": ("Industrial Incident Replay", 8),
        },
        "screenshots": [
            "industrial-line-overview.png",
            "industrial-machine-agreement.png",
            "industrial-incident-replay.png",
        ],
        "rules": "industrial-alerts.yml",
        "alerts": {
            "IndustrialProcessChanged",
            "IndustrialCycleDrift",
            "IndustrialSensorDisagreement",
            "IndustrialTagMissingOrLate",
            "IndustrialPhysicalMachineChanged",
            "IndustrialQualityImpact",
            "IndustrialIncidentCandidate",
            "IndustrialRecoveryIncomplete",
        },
        "example": "synthetic-industrial-scenario",
        "make_command": "make industrial",
        "npm_command": "npm run industrial:start",
        "grafana_folder": "MetricChrono Industrial Recipes",
        "operational_boundary": "does not replace safety systems, PLC alarms, SCADA, historians, maintenance systems, quality systems, or incident policy",
        "contract_forbidden_labels": {
            "serial_number",
            "operator_id",
            "user_id",
            "session_id",
            "event_id",
            "free_form_message",
            "error_text",
            "document_id",
            "part_id",
            "lot_id",
            "work_order_id",
            "raw_tag",
        },
        "comparison_terms": {
            "known_good_baseline",
            "last_window",
            "same_machine_state",
            "peer_asset",
            "station_vs_line",
            "sensor_vs_sensor",
            "source_vs_source",
            "pre_maintenance",
            "post_maintenance",
            "sensor_vs_controller",
            "current_vs_target",
        },
        "forbidden_doc_terms": {
            "same_mission_phase",
            "commanded_vs_actual",
            "sensor_vs_estimator",
            "actuator_vs_peer_actuator",
            "ros",
            "bag",
            "bags",
            "robot",
            "robots",
            "fleet",
            "mission",
            "docking",
            "manipulation",
            "estimator",
            "odometry",
            "localization",
            "lidar",
            "camera",
            "imu",
            "map / route",
            "route type",
        },
        "phases": {
            "Normal running",
            "Planned changeover or state transition",
            "Harmless small process variation",
            "Sensor/tag degradation",
            "Physical machine drift",
            "Cycle drift or bottleneck",
            "Quality proxy degradation or explicit no-quality-impact period",
            "Incident candidate",
            "Recovery or incomplete recovery",
        },
        "baseline_terms": {
            "known-good running state",
            "known-good changeover state",
            "known-good station cycle",
            "known-good machine state",
            "known-good shift or product family",
            "peer station / peer machine",
            "previous stable maintenance period",
            "same_machine_state",
            "station_vs_line",
            "sensor_vs_sensor",
            "current_vs_target",
        },
        "native_metric_fragments": [
            "_state",
            "_cycle_time_seconds",
            "_target_cycle_time_seconds",
            "_quality_proxy",
            "_reject_rate",
            "_freshness_seconds",
            "_process_variable_value",
            "_bucket",
        ],
    },
}

REQUIRED_DOCS = [
    "docs/integration-guide.md",
    "docs/metric-contract.md",
    "docs/baseline-calibration.md",
    "docs/alert-tuning.md",
    "docs/dashboard-panel-guide.md",
    "docs/troubleshooting.md",
    "docs/glossary.md",
]

REQUIRED_TOP_LEVEL = [
    "mlops",
    "robotics-telemetry",
    "industrial-telemetry",
    "sre-ai-services",
    "agent-observability",
]


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_names_from_expr(expr: str) -> set[str]:
    return set(re.findall(r"\bmetricchrono_[a-zA-Z0-9_]+(?:_bucket|_sum|_count)?\b", expr))


def declared_and_sampled_metric_names(text: str) -> set[str]:
    names = set(re.findall(r"^# TYPE (metricchrono_[a-zA-Z0-9_]+) ", text, flags=re.MULTILINE))
    names.update(re.findall(r"^(metricchrono_[a-zA-Z0-9_]+(?:_bucket|_sum|_count)?)\{", text, flags=re.MULTILINE))
    return names


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG file: {path}")
    return struct.unpack(">II", header[16:24])


def sample_values(text: str, metric: str) -> list[float]:
    values: list[float] = []
    for line in text.splitlines():
        if not line.startswith(metric + "{"):
            continue
        try:
            values.append(float(line.rsplit(" ", 1)[1]))
        except ValueError:
            continue
    return values


def metric_is_known(name: str, known: set[str]) -> bool:
    if name in known:
        return True
    for suffix in ("_bucket", "_sum", "_count"):
        if name.endswith(suffix) and name[: -len(suffix)] in known:
            return True
    return False


def validate_description(recipe: str, dashboard_title: str, panel: dict[str, Any], failures: list[str]) -> None:
    description = panel.get("description", "")
    for field in DESCRIPTION_FIELDS:
        if description.count(field) != 1:
            fail(failures, f"{recipe} / {dashboard_title} / {panel.get('title')} missing exact description field {field}")
    labels = re.findall(r"^[A-Z][A-Za-z ]+:", description, flags=re.MULTILINE)
    extra = [item for item in labels if item not in DESCRIPTION_FIELDS]
    if extra:
        fail(failures, f"{recipe} / {dashboard_title} / {panel.get('title')} has extra description fields: {extra}")


def validate_visible_text(recipe: str, dashboard_title: str, panel: dict[str, Any], failures: list[str]) -> None:
    text = "\n".join([dashboard_title, panel.get("title", ""), panel.get("description", "")]).lower()
    for forbidden in FORBIDDEN_INTERNAL_WORDS:
        if forbidden in text:
            fail(failures, f"{recipe} / {dashboard_title} / {panel.get('title')} exposes internal word: {forbidden.strip()}")
    for target in panel.get("targets", []):
        legend = target.get("legendFormat", "").lower()
        for forbidden in FORBIDDEN_INTERNAL_WORDS:
            if forbidden in legend:
                fail(failures, f"{recipe} / {dashboard_title} / {panel.get('title')} legend exposes internal word: {forbidden.strip()}")


def validate_labels(recipe: str, fixture_text: str, failures: list[str]) -> None:
    for label_blob in re.findall(r"\{([^}]*)\}", fixture_text):
        label_names = {part.split("=", 1)[0].strip() for part in label_blob.split(",") if "=" in part}
        forbidden = FORBIDDEN_LABELS & label_names
        if forbidden:
            fail(failures, f"{recipe} fixture uses forbidden labels: {sorted(forbidden)}")


def validate_persona_text(slug: str, root: Path, spec: dict[str, Any], failures: list[str]) -> None:
    scanned = ["README.md", *REQUIRED_DOCS]
    for rel in scanned:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        for term in sorted(spec["forbidden_doc_terms"]):
            if term.lower() in text:
                fail(failures, f"{slug} {rel} contains wrong-persona term: {term}")


def validate_recipe(slug: str, spec: dict[str, Any], failures: list[str]) -> None:
    root = RECIPES / slug
    if not root.exists():
        fail(failures, f"missing recipe directory: recipes/{slug}")
        return

    required_paths = [
        "README.md",
        "fixtures/expected-metrics-normal.txt",
        "fixtures/expected-metrics-incident.txt",
        f"rules/{spec['rules']}",
        f"examples/{spec['example']}/scenario.json",
        f"examples/{spec['example']}/run_scenario.py",
    ] + REQUIRED_DOCS
    for rel in required_paths:
        path = root / rel
        if not path.exists():
            fail(failures, f"{slug} missing required file: {rel}")
        elif path.is_file() and path.stat().st_size == 0:
            fail(failures, f"{slug} has empty required file: {rel}")

    readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""
    if spec["readme_opening"] not in readme[:700]:
        fail(failures, f"{slug} README does not open with required user-pain statement")
    for term in ["Change score:", "Comparison:", "Change size:"]:
        if term not in readme:
            fail(failures, f"{slug} README missing three-term glossary item: {term}")
    for term in [spec["make_command"], spec["npm_command"], spec["grafana_folder"]]:
        if term not in readme:
            fail(failures, f"{slug} README missing run or Grafana folder term: {term}")
    if spec["operational_boundary"] not in readme:
        fail(failures, f"{slug} README missing operational boundary statement")
    validate_persona_text(slug, root, spec, failures)

    normal = (root / "fixtures/expected-metrics-normal.txt").read_text(encoding="utf-8") if (root / "fixtures/expected-metrics-normal.txt").exists() else ""
    incident = (root / "fixtures/expected-metrics-incident.txt").read_text(encoding="utf-8") if (root / "fixtures/expected-metrics-incident.txt").exists() else ""
    known_metrics = declared_and_sampled_metric_names(normal + "\n" + incident)
    validate_labels(slug, normal + "\n" + incident, failures)

    dashboard_dir = root / "grafana" / "dashboards"
    dashboard_paths = sorted(dashboard_dir.glob("*.json"))
    if set(path.name for path in dashboard_paths) != set(spec["dashboards"]):
        fail(failures, f"{slug} dashboard files mismatch: {sorted(path.name for path in dashboard_paths)}")
    total_panels = 0
    for filename, (expected_title, expected_count) in spec["dashboards"].items():
        path = dashboard_dir / filename
        if not path.exists():
            continue
        dash = read_json(path)
        title = dash.get("title")
        panels = dash.get("panels", [])
        if title != expected_title:
            fail(failures, f"{slug} / {filename} title {title!r}, expected {expected_title!r}")
        if len(panels) != expected_count:
            fail(failures, f"{slug} / {title} has {len(panels)} panels, expected {expected_count}")
        total_panels += len(panels)
        dashboard_metrics: set[str] = set()
        for panel in panels:
            validate_description(slug, title, panel, failures)
            validate_visible_text(slug, title, panel, failures)
            if not panel.get("targets"):
                fail(failures, f"{slug} / {title} / {panel.get('title')} has no targets")
            if not panel.get("fieldConfig", {}).get("defaults", {}).get("unit"):
                fail(failures, f"{slug} / {title} / {panel.get('title')} has no unit")
            ref_ids = [target.get("refId", "") for target in panel.get("targets", [])]
            expected_ref_ids = [chr(ord("A") + index) for index in range(len(ref_ids))]
            if ref_ids != expected_ref_ids:
                fail(failures, f"{slug} / {title} / {panel.get('title')} has unstable target refIds: {ref_ids}, expected {expected_ref_ids}")
            for target in panel.get("targets", []):
                names = metric_names_from_expr(target.get("expr", ""))
                dashboard_metrics.update(names)
                for name in names:
                    if not metric_is_known(name, known_metrics):
                        fail(failures, f"{slug} / {title} / {panel.get('title')} references metric missing from fixtures: {name}")
        if not any(any(fragment in name for fragment in spec["native_metric_fragments"]) for name in dashboard_metrics):
            fail(failures, f"{slug} / {title} does not include domain-native metrics alongside change scores")
    if total_panels != 29:
        fail(failures, f"{slug} has {total_panels} total default panels, expected 29")

    for screenshot in spec["screenshots"]:
        path = root / "screenshots" / screenshot
        if not path.exists():
            fail(failures, f"{slug} missing screenshot: {screenshot}")
        elif path.stat().st_size < 100_000:
            fail(failures, f"{slug} screenshot looks too small to be a real Grafana capture: {screenshot}")
        else:
            try:
                width, height = png_dimensions(path)
            except ValueError as exc:
                fail(failures, f"{slug} invalid screenshot PNG: {exc}")
            else:
                if width < 1500 or height < 1200:
                    fail(failures, f"{slug} screenshot dimensions look unlike full Grafana capture: {screenshot} {width}x{height}")

    scenario_path = root / "examples" / spec["example"] / "scenario.json"
    if scenario_path.exists():
        scenario = read_json(scenario_path)
        phases = set(scenario.get("phases", []))
        missing_phases = spec["phases"] - phases
        if missing_phases:
            fail(failures, f"{slug} scenario missing phases: {sorted(missing_phases)}")
        if "plays once" not in scenario.get("default_run", ""):
            fail(failures, f"{slug} scenario does not state that the default run plays once")
        phase_metrics = scenario.get("phase_metrics", [])
        if len(phase_metrics) != len(scenario.get("phases", [])):
            fail(failures, f"{slug} scenario does not map every phase to a metric snapshot")
        seen_phase_files: set[str] = set()
        for item in phase_metrics:
            rel = item.get("file", "")
            phase_file = scenario_path.parent / rel
            if not phase_file.exists():
                fail(failures, f"{slug} missing phase metric snapshot: {rel}")
                continue
            text = phase_file.read_text(encoding="utf-8")
            if "scenario_phase=" not in text:
                fail(failures, f"{slug} phase metric snapshot lacks scenario_phase label: {rel}")
            if len(text.strip()) < 1000:
                fail(failures, f"{slug} phase metric snapshot looks too small: {rel}")
            seen_phase_files.add(text)
        if len(seen_phase_files) < max(3, len(phase_metrics) // 2):
            fail(failures, f"{slug} phase metric snapshots are not meaningfully distinct")
        if slug == "robotics-telemetry":
            for rel in ["phase-metrics/01-normal-navigation.prom", "phase-metrics/07-recovery.prom"]:
                path = scenario_path.parent / rel
                if path.exists():
                    values = sample_values(path.read_text(encoding="utf-8"), "metricchrono_robot_source_disagreement_score")
                    if values and max(values) >= 20:
                        fail(failures, f"{slug} {rel} has source disagreement >= 20; expected low normal/recovery agreement")

    baseline_text = (root / "docs" / "baseline-calibration.md").read_text(encoding="utf-8") if (root / "docs" / "baseline-calibration.md").exists() else ""
    for term in spec["baseline_terms"]:
        if term not in baseline_text:
            fail(failures, f"{slug} baseline guide missing term: {term}")
    if "Demo thresholds are not production thresholds" not in baseline_text:
        fail(failures, f"{slug} baseline guide does not warn about demo thresholds")

    contract_text = (root / "docs" / "metric-contract.md").read_text(encoding="utf-8") if (root / "docs" / "metric-contract.md").exists() else ""
    for label in spec["contract_forbidden_labels"]:
        if f"`{label}`" not in contract_text:
            fail(failures, f"{slug} metric contract missing forbidden label: {label}")
    for item in [*spec["comparison_terms"], "small", "medium", "large"]:
        if f"`{item}`" not in contract_text:
            fail(failures, f"{slug} metric contract missing expected term: {item}")

    rules_text = (root / "rules" / spec["rules"]).read_text(encoding="utf-8") if (root / "rules" / spec["rules"]).exists() else ""
    alerts = set(re.findall(r"^\s*- alert: ([A-Za-z0-9_]+)", rules_text, flags=re.MULTILINE))
    missing_alerts = spec["alerts"] - alerts
    if missing_alerts:
        fail(failures, f"{slug} alert rules missing: {sorted(missing_alerts)}")
    for alert_name in spec["alerts"]:
        match = re.search(rf"  - alert: {re.escape(alert_name)}\n(?P<body>.*?)(?=\n  - alert: |\Z)", rules_text, flags=re.DOTALL)
        if not match:
            continue
        before_annotations = match.group("body").split("    annotations:", 1)[0]
        for label in ["main_subsystem:", "comparison:"]:
            if f"      {label}" not in before_annotations:
                fail(failures, f"{slug} alert {alert_name} does not set explicit label {label}")
    for required in ["summary:", "asset_group:", "main_subsystem:", "comparison:", "suggested_dashboard:", "suggested_next_action:"]:
        if required not in rules_text:
            fail(failures, f"{slug} alert rules missing annotation field {required}")
    if any(word in rules_text.lower() for word in ["epsilon", "delta", "tier", "ladder"]):
        fail(failures, f"{slug} alert rules expose internal terminology")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", choices=["robotics", "industrial", "telemetry"], default="telemetry")
    args = parser.parse_args()

    failures: list[str] = []
    for rel in REQUIRED_TOP_LEVEL:
        if not (RECIPES / rel).exists():
            fail(failures, f"missing expected top-level recipe directory: recipes/{rel}")
    selected = {
        "robotics": ["robotics-telemetry"],
        "industrial": ["industrial-telemetry"],
        "telemetry": ["robotics-telemetry", "industrial-telemetry"],
    }[args.recipe]
    for slug in selected:
        spec = EXPECTED[slug]
        validate_recipe(slug, spec, failures)
    if failures:
        print(f"{args.recipe} recipe validation failed:")
        for item in failures:
            print(f"- {item}")
        return 1
    print(f"{args.recipe} recipe validation passed.")
    print(f"Checked {', '.join(selected)} structure, dashboards, panels, docs, fixtures, alerts, screenshots, labels, and local scenario definitions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
