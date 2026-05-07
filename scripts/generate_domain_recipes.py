#!/usr/bin/env python3
"""Generate robotics and industrial telemetry recipe packs.

The generated files are intentionally plain Grafana/Prometheus/docs assets so
the recipes are useful without ROS, OPC UA, PLCs, or live equipment.
"""

from __future__ import annotations

import argparse
import json
import textwrap
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECIPES_ROOT = ROOT / "recipes"

DESCRIPTION_FIELDS = [
    "Question answered:",
    "How to read it:",
    "Why it matters:",
    "Next action:",
]

CHANGE_SCORE_GUIDE = """0-20: normal variation
20-50: watch
50-75: investigate
75-100: incident candidate"""

CHANGE_THRESHOLDS = [
    {"color": "green", "value": None},
    {"color": "yellow", "value": 20},
    {"color": "orange", "value": 50},
    {"color": "red", "value": 75},
]

RELIABILITY_THRESHOLDS = [
    {"color": "red", "value": None},
    {"color": "orange", "value": 50},
    {"color": "yellow", "value": 80},
    {"color": "green", "value": 90},
]

ROBOTICS_COMPARISONS = [
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
]

INDUSTRIAL_COMPARISONS = [
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
]

CHANGE_SIZES = ["small", "medium", "large"]

COMMON_FORBIDDEN_LABELS = [
    "serial_number",
    "operator_id",
    "user_id",
    "session_id",
    "event_id",
    "free_form_message",
    "error_text",
    "document_id",
]

ROBOTICS_FORBIDDEN_LABELS = [
    *COMMON_FORBIDDEN_LABELS,
    "bag_file",
    "raw_topic",
    "trace_id",
]

INDUSTRIAL_FORBIDDEN_LABELS = [
    *COMMON_FORBIDDEN_LABELS,
    "part_id",
    "lot_id",
    "work_order_id",
    "raw_tag",
]

STABLE_LABELS = [
    "site",
    "environment",
    "recipe",
    "asset_class",
    "asset_group",
    "asset",
    "subsystem",
    "source",
    "comparison",
    "change_size",
    "state",
    "severity",
    "scenario_phase",
]


def comparisons_for(recipe: str) -> list[str]:
    return ROBOTICS_COMPARISONS if recipe == "robotics" else INDUSTRIAL_COMPARISONS


def forbidden_labels_for(recipe: str) -> list[str]:
    return ROBOTICS_FORBIDDEN_LABELS if recipe == "robotics" else INDUSTRIAL_FORBIDDEN_LABELS


def panel_description(question: str, how: str, why: str, next_action: str) -> str:
    return "\n\n".join(
        [
            f"Question answered: {question}",
            f"How to read it: {how}",
            f"Why it matters: {why}",
            f"Next action: {next_action}",
        ]
    )


def target(expr: str, legend: str, ref_id: str, *, table: bool = False) -> dict[str, Any]:
    output = {
        "datasource": {"type": "prometheus", "uid": "${datasource}"},
        "editorMode": "code",
        "expr": expr,
        "legendFormat": legend,
        "refId": ref_id,
    }
    if table:
        output["format"] = "table"
        output["instant"] = True
        output["range"] = False
    else:
        output["range"] = True
    return output


def max_by(labels: str, expr: str) -> str:
    return f"max by ({labels}) ({expr})"


def sum_by(labels: str, expr: str) -> str:
    return f"sum by ({labels}) ({expr})"


def topk_max(n: int, labels: str, expr: str) -> str:
    return f"topk({n}, {max_by(labels, expr)})"


def positive_over_range(labels: str, expr: str, window: str = "2m") -> str:
    return f"max by ({labels}) (max_over_time({expr}[{window}])) > 0"


def min_over_range(labels: str, expr: str, window: str = "2m") -> str:
    return f"min by ({labels}) (min_over_time({expr}[{window}]))"


def histogram_percentile(quantile: str, bucket_expr: str) -> str:
    return f"histogram_quantile({quantile}, {sum_by('le', bucket_expr)})"


def value_mappings(code_by_label: dict[str, int], colors_by_label: dict[str, str] | None = None) -> list[dict[str, Any]]:
    colors_by_label = colors_by_label or {}
    return [
        {
            "type": "value",
            "options": {
                str(code): {"text": label.replace("_", " "), "color": colors_by_label.get(label, "green")}
                for label, code in code_by_label.items()
            },
        }
    ]


def mapping_override(pattern: str, mappings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "matcher": {"id": "byRegexp", "options": pattern},
        "properties": [{"id": "mappings", "value": mappings}],
    }


def table_transformations() -> list[dict[str, Any]]:
    return [
        {
            "id": "organize",
            "options": {
                "excludeByName": {"Time": True, "Value": True},
                "indexByName": {
                    "rank": 0,
                    "asset": 1,
                    "source": 2,
                    "subsystem": 3,
                    "reason": 4,
                    "comparison": 5,
                    "next_dashboard": 6,
                    "time_window": 7,
                    "severity": 8,
                },
                "renameByName": {
                    "comparison": "reference",
                    "next_dashboard": "open",
                    "subsystem": "area",
                    "time_window": "window",
                },
            },
        }
    ]


def make_panel(
    title: str,
    panel_type: str,
    question: str,
    how: str,
    why: str,
    next_action: str,
    targets: list[tuple[str, str]],
    *,
    unit: str = "short",
    width: int = 12,
    height: int = 8,
    legend_display: str = "list",
    thresholds: list[dict[str, Any]] | None = None,
    mappings: list[dict[str, Any]] | None = None,
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if panel_type == "table" and width == 12:
        width = 24
    defaults = {
        "unit": unit,
        "thresholds": {
            "mode": "absolute",
            "steps": thresholds or CHANGE_THRESHOLDS,
        },
    }
    if mappings:
        defaults["mappings"] = mappings
    options: dict[str, Any] = {"legend": {"displayMode": legend_display, "placement": "bottom"}}
    transformations: list[dict[str, Any]] = []
    if panel_type == "table":
        options = {"cellHeight": "sm", "showHeader": True}
        transformations = table_transformations()
    panel = {
        "title": title,
        "type": panel_type,
        "description": panel_description(question, how, why, next_action),
        "datasource": {"type": "prometheus", "uid": "${datasource}"},
        "fieldConfig": {
            "defaults": defaults,
            "overrides": overrides or [],
        },
        "options": options,
        "targets": [
            target(expr, legend, chr(ord("A") + index), table=panel_type == "table")
            for index, (expr, legend) in enumerate(targets)
        ],
        "gridPos": {"h": height, "w": width, "x": 0, "y": 0},
    }
    if transformations:
        panel["transformations"] = transformations
    return panel


def apply_grid(panels: list[dict[str, Any]]) -> None:
    x = 0
    y = 0
    row_height = 0
    for panel in panels:
        width = panel["gridPos"].get("w", 12)
        height = panel["gridPos"].get("h", 8)
        if width >= 24:
            if x:
                y += row_height
                x = 0
                row_height = 0
            panel["gridPos"] = {"h": height, "w": 24, "x": 0, "y": y}
            y += height
            continue
        if x + width > 24:
            y += row_height
            x = 0
            row_height = 0
        panel["gridPos"] = {"h": height, "w": width, "x": x, "y": y}
        x += width
        row_height = max(row_height, height)
        if x >= 24:
            y += row_height
            x = 0
            row_height = 0


def dashboard(
    title: str,
    panels: list[dict[str, Any]],
    tags: list[str],
    *,
    default_asset_group: str,
    default_asset: str = ".*",
    default_source: str = ".*",
    default_comparison: str = "known_good_baseline",
    default_change_size: str = ".*",
) -> dict[str, Any]:
    apply_grid(panels)
    return {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "panels": panels,
        "schemaVersion": 39,
        "tags": tags,
        "templating": {
            "list": [
                {
                    "name": "datasource",
                    "type": "datasource",
                    "query": "prometheus",
                    "current": {"text": "Prometheus", "value": "Prometheus"},
                },
                {"name": "site", "type": "textbox", "query": "local-lab", "current": {"text": "local-lab", "value": "local-lab"}},
                {"name": "environment", "type": "textbox", "query": "demo", "current": {"text": "demo", "value": "demo"}},
                {"name": "asset_group", "type": "textbox", "query": default_asset_group, "current": {"text": default_asset_group, "value": default_asset_group}},
                {"name": "asset", "type": "textbox", "query": default_asset, "current": {"text": default_asset, "value": default_asset}},
                {"name": "source", "type": "textbox", "query": default_source, "current": {"text": default_source, "value": default_source}},
                {"name": "comparison", "type": "textbox", "query": default_comparison, "current": {"text": default_comparison, "value": default_comparison}},
                {"name": "change_size", "type": "textbox", "query": default_change_size, "current": {"text": default_change_size, "value": default_change_size}},
            ]
        },
        "time": {"from": "now-2m", "to": "now"},
        "timezone": "browser",
        "title": title,
        "uid": title.lower().replace(" / ", "-").replace(" ", "-"),
        "version": 1,
    }


def robot_expr(metric: str, extra: str = "") -> str:
    labels = 'site="$site",environment="$environment",recipe="robotics-telemetry",asset_group=~"$asset_group",asset=~"$asset"'
    if extra:
        labels += "," + extra
    return f"{metric}{{{labels}}}"


def industrial_expr(metric: str, extra: str = "") -> str:
    labels = 'site="$site",environment="$environment",recipe="industrial-telemetry",asset_group=~"$asset_group",asset=~"$asset"'
    if extra:
        labels += "," + extra
    return f"{metric}{{{labels}}}"


ROBOT_METRICS = {
    "metricchrono_robot_mission_state": ("gauge", "One-hot robot mission state."),
    "metricchrono_robot_safety_state": ("gauge", "One-hot robot safety state."),
    "metricchrono_robot_diagnostic_state": ("gauge", "One-hot robot diagnostic state."),
    "metricchrono_robot_mission_state_code": ("gauge", "Compact robot mission state code for state timelines."),
    "metricchrono_robot_safety_state_code": ("gauge", "Compact robot safety state code for state timelines."),
    "metricchrono_robot_diagnostic_state_code": ("gauge", "Compact robot diagnostic state code for state timelines."),
    "metricchrono_robot_change_state": ("gauge", "0 normal, 1 watch, 2 investigate, 3 incident candidate, 4 recovered."),
    "metricchrono_robot_overall_change_score": ("gauge", "Overall robot behavior change score."),
    "metricchrono_robot_motion_change_score": ("gauge", "Motion-specific behavior change score."),
    "metricchrono_robot_change_score_by_size": ("gauge", "Robot change score split by small, medium, and large movement."),
    "metricchrono_robot_tracking_deviation_score": ("gauge", "Commanded versus actual motion deviation score."),
    "metricchrono_robot_commanded_speed": ("gauge", "Commanded speed in meters per second."),
    "metricchrono_robot_actual_speed": ("gauge", "Actual speed in meters per second."),
    "metricchrono_robot_commanded_linear_velocity": ("gauge", "Commanded linear velocity."),
    "metricchrono_robot_actual_linear_velocity": ("gauge", "Actual linear velocity."),
    "metricchrono_robot_commanded_angular_velocity": ("gauge", "Commanded angular velocity."),
    "metricchrono_robot_actual_angular_velocity": ("gauge", "Actual angular velocity."),
    "metricchrono_robot_commanded_velocity": ("gauge", "Commanded velocity for incident replay."),
    "metricchrono_robot_actual_velocity": ("gauge", "Actual velocity for incident replay."),
    "metricchrono_robot_source_disagreement_score": ("gauge", "Source, sensor, or estimator disagreement score."),
    "metricchrono_robot_source_reliability_score": ("gauge", "Source reliability score."),
    "metricchrono_robot_source_missing_total": ("counter", "Missing source events."),
    "metricchrono_robot_source_late_total": ("counter", "Late source events."),
    "metricchrono_robot_topic_freshness_seconds": ("gauge", "Topic freshness age."),
    "metricchrono_robot_source_freshness_seconds": ("gauge", "Source freshness age."),
    "metricchrono_robot_actuator_effort_change_score": ("gauge", "Actuator effort change score."),
    "metricchrono_robot_motor_current_change_score": ("gauge", "Motor current change score."),
    "metricchrono_robot_motor_temperature_change_score": ("gauge", "Motor temperature change score."),
    "metricchrono_robot_localization_disagreement_score": ("gauge", "Localization disagreement score."),
    "metricchrono_robot_odometry_disagreement_score": ("gauge", "Odometry disagreement score."),
    "metricchrono_robot_imu_disagreement_score": ("gauge", "IMU disagreement score."),
    "metricchrono_robot_perception_change_score": ("gauge", "Perception input change score."),
    "metricchrono_robot_feature_count_change_score": ("gauge", "Perception feature count change score."),
    "metricchrono_robot_perception_confidence_change_score": ("gauge", "Perception confidence change score."),
    "metricchrono_robot_tracking_error_distance": ("histogram", "Tracking error distance distribution."),
    "metricchrono_robot_battery_change_score": ("gauge", "Battery state change score."),
    "metricchrono_robot_power_change_score": ("gauge", "Power state change score."),
    "metricchrono_robot_thermal_change_score": ("gauge", "Thermal state change score."),
    "metricchrono_robot_voltage": ("gauge", "Battery voltage."),
    "metricchrono_robot_current": ("gauge", "Electrical current."),
    "metricchrono_robot_temperature": ("gauge", "Robot temperature."),
    "metricchrono_robot_diagnostic_summary": ("gauge", "Bounded diagnostic category summary."),
    "metricchrono_robot_inspection_candidate": ("gauge", "Ranked robot inspection candidate."),
    "metricchrono_robot_incident_window_state": ("gauge", "Incident replay window state."),
    "metricchrono_robot_incident_window_state_code": ("gauge", "Compact incident replay window state code."),
    "metricchrono_robot_first_change_offset_seconds": ("gauge", "Seconds between first meaningful change and main symptom."),
    "metricchrono_robot_replay_artifact": ("gauge", "Suggested replay artifact row."),
    "metricchrono_robot_recovery_state": ("gauge", "Recovery confirmation state."),
    "metricchrono_robot_scenario_phase": ("gauge", "One-hot local robotics scenario phase."),
}


INDUSTRIAL_METRICS = {
    "metricchrono_industrial_line_state": ("gauge", "One-hot production line state."),
    "metricchrono_industrial_cell_state": ("gauge", "One-hot cell state."),
    "metricchrono_industrial_machine_state": ("gauge", "One-hot machine state."),
    "metricchrono_industrial_line_state_code": ("gauge", "Compact line state code for state timelines."),
    "metricchrono_industrial_cell_state_code": ("gauge", "Compact cell state code for state timelines."),
    "metricchrono_industrial_machine_state_code": ("gauge", "Compact machine state code for state timelines."),
    "metricchrono_industrial_station_change_state": ("gauge", "0 normal, 1 watch, 2 investigate, 3 incident candidate, 4 recovered."),
    "metricchrono_industrial_process_change_score": ("gauge", "Overall process change score."),
    "metricchrono_industrial_cycle_time_seconds": ("gauge", "Observed cycle time."),
    "metricchrono_industrial_target_cycle_time_seconds": ("gauge", "Target cycle time."),
    "metricchrono_industrial_cycle_change_score": ("gauge", "Cycle behavior change score."),
    "metricchrono_industrial_change_score_by_size": ("gauge", "Process change score split by small, medium, and large movement."),
    "metricchrono_industrial_station_change_score": ("gauge", "Station-level change score."),
    "metricchrono_industrial_line_change_score": ("gauge", "Line-level change score."),
    "metricchrono_industrial_wip_or_queue_change_score": ("gauge", "Work-in-process or queue change score."),
    "metricchrono_industrial_quality_proxy": ("gauge", "Synthetic quality proxy."),
    "metricchrono_industrial_reject_rate": ("gauge", "Synthetic reject rate."),
    "metricchrono_industrial_quality_change_score": ("gauge", "Quality proxy change score."),
    "metricchrono_industrial_vibration_change_score": ("gauge", "Vibration change score."),
    "metricchrono_industrial_motor_current_change_score": ("gauge", "Motor current change score."),
    "metricchrono_industrial_temperature_change_score": ("gauge", "Temperature change score."),
    "metricchrono_industrial_pressure_change_score": ("gauge", "Pressure change score."),
    "metricchrono_industrial_flow_change_score": ("gauge", "Flow change score."),
    "metricchrono_industrial_physical_machine_change_score": ("gauge", "Combined physical-machine change score."),
    "metricchrono_industrial_sensor_disagreement_score": ("gauge", "Sensor or controller disagreement score."),
    "metricchrono_industrial_sensor_reliability_score": ("gauge", "Sensor reliability score."),
    "metricchrono_industrial_tag_freshness_seconds": ("gauge", "Tag freshness age."),
    "metricchrono_industrial_source_missing_total": ("counter", "Missing source or tag events."),
    "metricchrono_industrial_source_late_total": ("counter", "Late source or tag events."),
    "metricchrono_industrial_process_variable_value": ("gauge", "Selected process variable value."),
    "metricchrono_industrial_baseline_in_use": ("gauge", "One when the state-matched baseline is active."),
    "metricchrono_industrial_diagnostic_summary": ("gauge", "Bounded diagnostic category summary."),
    "metricchrono_industrial_inspection_candidate": ("gauge", "Ranked industrial inspection candidate."),
    "metricchrono_industrial_incident_window_state": ("gauge", "Incident replay window state."),
    "metricchrono_industrial_incident_window_state_code": ("gauge", "Compact incident replay window state code."),
    "metricchrono_industrial_first_change_offset_seconds": ("gauge", "Seconds between first meaningful change and impact."),
    "metricchrono_industrial_replay_artifact": ("gauge", "Suggested replay artifact row."),
    "metricchrono_industrial_scenario_phase": ("gauge", "One-hot local industrial scenario phase."),
}


def robotics_dashboards() -> dict[str, dict[str, Any]]:
    e = robot_expr
    overview = [
        make_panel("Fleet / Mission State", "state-timeline", "What was the robot trying to do when the change happened?", "Look for whether a change occurred during normal navigation, a state transition, recovery, or a safety event.", "Phase context separates expected maneuver changes from suspicious behavior during steady work.", "If the change overlaps fault, recovery, paused, or estop, open Robot Incident Replay.", [(e("metricchrono_robot_mission_state_code"), "{{asset}} mission"), (e("metricchrono_robot_safety_state_code"), "{{asset}} safety"), (e("metricchrono_robot_diagnostic_state_code"), "{{asset}} diagnostics")], overrides=robot_timeline_overrides()),
        make_panel("Fleet Change State By Robot", "status-history", "Which robot is behaving differently right now?", "Rows are robots. Watch, investigate, and incident candidate bands show robots whose behavior differs from the selected reference.", "A fleet engineer first needs to know whether this is one robot, several robots, or the whole fleet.", "If one robot is abnormal, inspect source agreement for that robot. If many robots change together, inspect environment, map, network, or mission update.", [(max_by("asset", e("metricchrono_robot_change_state", 'comparison=~"$comparison"')), "{{asset}}")], mappings=value_mappings(CHANGE_STATE_CODE, CHANGE_STATE_COLORS)),
        make_panel("Overall Robot Change Score", "timeseries", "Did the robot's overall behavior move outside normal variation?", "A low stable score means ordinary behavior. A rising score means the robot is moving away from the selected reference.", "Robot logs are too large to inspect blindly, so this gives a first signal for when to look.", "If high only versus last_window, look for a sudden disturbance. If high versus known_good_baseline but flat, look for slow drift or changed conditions.", [(e("metricchrono_robot_overall_change_score", 'comparison=~"$comparison"'), "{{asset}} {{comparison}}")], unit="percent"),
        make_panel("Change Size Split", "timeseries", "Is this harmless jitter or a large behavior shift?", "Small change alone is usually jitter. Sustained medium change deserves attention. Large change is an incident candidate.", "Robotics data is noisy; engineers need to separate vibration and chatter from meaningful regime shifts.", "If large change appears, inspect Source Agreement and Incident Replay. If only small rises, inspect freshness or controller jitter.", [(max_by("change_size", e("metricchrono_robot_change_score_by_size", 'change_size=~"$change_size",comparison=~"$comparison"')), "{{change_size}}")], unit="percent"),
        make_panel("Commanded vs Actual Tracking Deviation", "timeseries", "Did the robot fail to execute the motion it was commanded to perform?", "A rising tracking deviation with stable command means actual motion is separating from requested motion.", "This separates upstream planning or perception problems from downstream execution and control problems.", "If tracking deviation rises, inspect actuator effort, motor current, temperature, wheel slip, joint effort, and safety state.", [(e("metricchrono_robot_tracking_deviation_score", 'comparison="commanded_vs_actual"'), "{{asset}} tracking deviation")], unit="percent"),
        make_panel("Sensor / Estimator Disagreement Summary", "bargauge", "Which sensor or estimator disagrees most with the rest of the robot?", "The highest bar is the source that currently disagrees most. It points to where to inspect first but does not prove fault.", "When localization, odometry, IMU, lidar, or camera disagree, engineers need a ranked list.", "Open Robot Source Agreement for the top source.", [(topk_max(5, "asset, source", e("metricchrono_robot_source_disagreement_score", 'source=~"$source",comparison=~"sensor_vs_estimator|source_vs_source"')), "{{asset}} {{source}}")], unit="percent"),
        make_panel("Missing Or Late Sources", "timeseries", "Is the dashboard seeing a behavior change, or did telemetry go missing?", "Missing-source counters rising during a change event mean disagreement may be caused by data loss or stale sources.", "Robotics incidents often look like state changes when the real problem is delayed or stale sensor data.", "Inspect drivers, middleware, CPU load, network, and source timestamps before blaming robot behavior.", [(sum_by("asset", e("metricchrono_robot_source_missing_total", 'source=~"$source"')), "{{asset}} missing"), (sum_by("asset", e("metricchrono_robot_source_late_total", 'source=~"$source"')), "{{asset}} late"), (max_by("asset", e("metricchrono_robot_topic_freshness_seconds", 'source=~"$source"')), "{{asset}} freshness")]),
        make_panel("Actuator Effort / Thermal Change", "timeseries", "Is the robot working harder than usual to perform the same task?", "Rising effort, current, or temperature change while mission state is unchanged can indicate load, terrain, joint issue, motor degradation, or compensation.", "Mechanical and actuator problems often appear before a hard fault.", "Inspect the corresponding joint, wheel, motor, payload, terrain, or docking interaction.", [(max_by("asset", e("metricchrono_robot_actuator_effort_change_score", 'source=~"$source"')), "{{asset}} effort"), (max_by("asset", e("metricchrono_robot_motor_current_change_score", 'source=~"$source"')), "{{asset}} current"), (max_by("asset", e("metricchrono_robot_motor_temperature_change_score", 'source=~"$source"')), "{{asset}} temperature")], unit="percent"),
        make_panel("Safety And Diagnostics Timeline", "state-timeline", "Did a safety or diagnostic state change explain the behavior change?", "Look for warnings or faults aligned with change-score spikes.", "Engineers should not infer from change metrics when the robot already emitted a clear safety or diagnostic signal.", "If diagnostic state changed, use it as the primary investigation path and use change panels as supporting context.", [(e("metricchrono_robot_safety_state_code"), "{{asset}} safety"), (e("metricchrono_robot_diagnostic_state_code"), "{{asset}} diagnostics")], overrides=robot_timeline_overrides()),
        make_panel("Top Incident Candidates", "table", "Where should I click first?", "The top row is the highest-priority investigation candidate and names the robot, subsystem, source, comparison, and reason.", "Operators and engineers need a triage queue, not twenty unrelated graphs.", "Open Robot Incident Replay for the top row.", [(positive_over_range("rank, asset, subsystem, source, reason, next_dashboard, comparison", e("metricchrono_robot_inspection_candidate", 'severity=~"watch|investigate|incident_candidate"')), "{{asset}} {{subsystem}} {{source}}")]),
    ]
    agreement = [
        make_panel("Source Agreement Heatmap", "heatmap", "Which sensor or subsystem stopped agreeing, and when?", "A single hot row points to one diverging source. Many hot rows can mean real scene change, estimator issue, synchronization problem, or global telemetry issue.", "Robotics engineers debug by source such as lidar, camera, IMU, wheel encoders, odometry, localization, controller, and actuator.", "If one row is hot, inspect that source. If many rows are hot, inspect estimator, clock sync, environment event, or mission transition.", [(max_by("source, subsystem", e("metricchrono_robot_source_disagreement_score", 'source=~"$source",comparison=~"source_vs_source|sensor_vs_estimator"')), "{{source}} {{subsystem}}")], unit="percent"),
        make_panel("Source Reliability / Trust Score", "stat", "Which source is currently least trustworthy?", "Low score means the source has repeatedly disagreed, gone missing, or become stale. It is a triage hint, not a permanent calibration judgment.", "Engineers need a prioritized sensor list during incidents.", "Inspect the lowest-trust source's driver status, timestamps, physical condition, and mounting.", [(min_over_range("source", e("metricchrono_robot_source_reliability_score", 'source=~"$source"')), "{{source}} reliability")], unit="percent", thresholds=RELIABILITY_THRESHOLDS),
        make_panel("Odometry / Localization / IMU Agreement", "timeseries", "Is the robot losing localization or just moving differently?", "Localization disagreement with stable actuator tracking points toward estimator or perception. Tracking deviation with stable localization points toward control or actuation.", "This separates the robot not knowing where it is from the robot not executing what it wants.", "Inspect map, feature quality, lidar/camera health, IMU calibration, wheel slip, and covariance.", [(e("metricchrono_robot_localization_disagreement_score", 'comparison="sensor_vs_estimator"'), "{{asset}} localization"), (e("metricchrono_robot_odometry_disagreement_score", 'comparison="source_vs_source"'), "{{asset}} odometry"), (e("metricchrono_robot_imu_disagreement_score", 'comparison="source_vs_source"'), "{{asset}} IMU")], unit="percent"),
        make_panel("Perception Source Change", "timeseries", "Did the robot's perception input change even though the mission state did not?", "Rising perception change with normal motion can indicate occlusion, lighting change, dust, scene change, feature loss, or camera/lidar degradation.", "Perception problems often present as downstream navigation or control anomalies.", "Inspect camera/lidar status, lighting, occlusion, lens or sensor cleanliness, and environment.", [(e("metricchrono_robot_perception_change_score", 'comparison="known_good_baseline"'), "{{asset}} perception"), (e("metricchrono_robot_feature_count_change_score", 'comparison="sensor_vs_estimator"'), "{{asset}} feature count change"), (e("metricchrono_robot_perception_confidence_change_score", 'comparison="sensor_vs_estimator"'), "{{asset}} confidence change")], unit="percent"),
        make_panel("Topic / Source Freshness", "timeseries", "Did the source actually publish on time?", "Freshness increasing means the source is stale. Missing and late counters rising mean data availability changed.", "Robotics systems are sensitive to stale perception, stale transforms, and delayed actuator feedback.", "Inspect middleware, CPU, network, driver frequency, and timestamp handling.", [(e("metricchrono_robot_source_freshness_seconds", 'source=~"$source"'), "{{source}} freshness"), (e("metricchrono_robot_source_late_total", 'source=~"$source"'), "{{source}} late"), (e("metricchrono_robot_source_missing_total", 'source=~"$source"'), "{{source}} missing")]),
        make_panel("Commanded vs Actual Velocity", "timeseries", "Is the controller asking for one thing while the robot does another?", "Divergence between commanded and actual velocity indicates tracking failure, slip, saturation, load, or controller instability.", "This is the simplest control-language explanation of a behavior change.", "Inspect motor current, effort, wheel slip, actuator saturation, terrain, and safety limits.", [(e("metricchrono_robot_commanded_linear_velocity"), "{{asset}} commanded linear"), (e("metricchrono_robot_actual_linear_velocity"), "{{asset}} actual linear"), (e("metricchrono_robot_commanded_angular_velocity"), "{{asset}} commanded angular"), (e("metricchrono_robot_actual_angular_velocity"), "{{asset}} actual angular"), (e("metricchrono_robot_tracking_deviation_score", 'comparison="commanded_vs_actual"'), "{{asset}} tracking")]),
        make_panel("Tracking Error Distribution", "timeseries", "Is tracking error a one-off spike or a changed distribution?", "A shifted distribution means persistent behavior change. A single spike means a transient event.", "Robotics engineers need to distinguish one bad moment from a new operating condition.", "If the distribution shifts, inspect calibration, controller parameters, payload, terrain, and hardware wear.", [(histogram_percentile("0.50", e("metricchrono_robot_tracking_error_distance_bucket", 'le=~".*"')), "p50 tracking error"), (histogram_percentile("0.95", e("metricchrono_robot_tracking_error_distance_bucket", 'le=~".*"')), "p95 tracking error")]),
        make_panel("Actuator Effort By Joint / Wheel / Motor", "bargauge", "Which actuator is working unusually hard?", "A single high actuator points to a local mechanical or electrical issue. Many high actuators point to load, terrain, payload, or global control compensation.", "This moves investigation from robot weird to a specific wheel, joint, or lift motor.", "Inspect the named actuator, load path, mechanical resistance, current limits, temperature, and maintenance history.", [(e("metricchrono_robot_actuator_effort_change_score", 'source=~"$source"'), "{{source}} effort"), (e("metricchrono_robot_motor_current_change_score", 'source=~"$source"'), "{{source}} current"), (e("metricchrono_robot_motor_temperature_change_score", 'source=~"$source"'), "{{source}} temperature")], unit="percent"),
        make_panel("Battery / Power / Thermal Context", "timeseries", "Is power or thermal behavior contributing to the issue?", "Power or temperature change rising before motion deviation can indicate load, degradation, thermal throttling, or battery issue.", "Power and thermal context explains many intermittent robotics failures.", "Inspect battery state, charger or dock, thermal limits, current draw, and duty cycle.", [(e("metricchrono_robot_battery_change_score"), "{{asset}} battery change"), (e("metricchrono_robot_power_change_score"), "{{asset}} power change"), (e("metricchrono_robot_thermal_change_score"), "{{asset}} thermal change"), (e("metricchrono_robot_voltage"), "{{asset}} voltage"), (e("metricchrono_robot_current"), "{{asset}} current"), (e("metricchrono_robot_temperature"), "{{asset}} temperature")]),
        make_panel("Diagnostic Messages Summary", "table", "What did the robot itself report?", "Rows summarize bounded diagnostic categories, not raw free-form messages.", "The robot's own diagnostics may already identify the issue. Change metrics should support, not obscure, that signal.", "Use diagnostic category as the primary investigation path if it aligns with change score.", [(positive_over_range("asset, source, state", e("metricchrono_robot_diagnostic_summary", 'source=~"$source",state=~"sensor_stale|temperature_warning|actuator_limit|localization_warning"')), "{{source}} {{state}}")]),
        make_panel("Suggested Next Inspection", "table", "What should I inspect next?", "Rows translate metrics into engineering next steps.", "A solution recipe should reduce cognitive load.", "Follow the top suggested inspection, then open Robot Incident Replay around the listed window.", [(positive_over_range("rank, asset, subsystem, source, reason, next_dashboard, comparison", e("metricchrono_robot_inspection_candidate", 'severity=~"watch|investigate|incident_candidate"')), "{{asset}} {{subsystem}} {{source}}")]),
    ]
    replay = [
        make_panel("Incident Window Timeline", "state-timeline", "What was the robot doing before, during, and after the incident?", "The incident candidate should be bounded by pre-incident, incident, and recovery periods.", "Replay without phase context wastes time.", "Use the highlighted interval for logs, traces, bag replay, or video review.", [(e("metricchrono_robot_incident_window_state_code"), "{{asset}} incident window"), (e("metricchrono_robot_mission_state_code"), "{{asset}} mission"), (e("metricchrono_robot_diagnostic_state_code"), "{{asset}} diagnostics"), (e("metricchrono_robot_safety_state_code"), "{{asset}} safety")], overrides=robot_timeline_overrides()),
        make_panel("First Meaningful Change", "stat", "What changed first?", "This panel names the first subsystem or source whose change became meaningful inside the incident window.", "Root-cause investigation depends heavily on ordering.", "Inspect the first changed source before later downstream symptoms.", [(positive_over_range("asset, subsystem, source, comparison", e("metricchrono_robot_first_change_offset_seconds", 'subsystem=~"perception|motion|actuator"')), "{{subsystem}} {{source}} before main symptom")], unit="s"),
        make_panel("Change Score Around Incident", "timeseries", "How did the incident evolve?", "Look for which score rises first and which score remains high after recovery.", "Incident investigation depends on cause, propagation, and recovery order.", "If source disagreement rises first, inspect source. If tracking rises first, inspect controls or actuation.", [(e("metricchrono_robot_overall_change_score", 'comparison=~"known_good_baseline|last_window|same_mission_phase"'), "{{asset}} overall {{comparison}}"), (e("metricchrono_robot_motion_change_score", 'comparison="commanded_vs_actual"'), "{{asset}} motion"), (e("metricchrono_robot_tracking_deviation_score", 'comparison="commanded_vs_actual"'), "{{asset}} tracking"), (max_by("source", e("metricchrono_robot_source_disagreement_score", 'source=~"$source",comparison=~"sensor_vs_estimator|source_vs_source"')), "{{source}} disagreement")], unit="percent"),
        make_panel("Source Disagreement Around Incident", "heatmap", "Was this one bad source or a broad system change?", "One hot row suggests a source-specific issue. Many hot rows suggest environment, estimator, clock sync, or global behavior change.", "This prevents blaming a sensor when the scene or estimator changed globally.", "Use the row pattern to choose between source inspection and system-wide investigation.", [(max_by("source, subsystem", e("metricchrono_robot_source_disagreement_score", 'source=~"$source",comparison=~"sensor_vs_estimator|source_vs_source"')), "{{source}} {{subsystem}}")], unit="percent"),
        make_panel("Command / Actual / Effort Around Incident", "timeseries", "Was this a control execution problem?", "If command remains steady but actual and effort change, the robot likely struggled to execute. If command changes first, planner or mission may be upstream.", "This maps directly to controls and actuation debugging.", "Inspect controller, actuator, terrain or contact, payload, and safety constraints.", [(e("metricchrono_robot_commanded_velocity"), "{{asset}} commanded"), (e("metricchrono_robot_actual_velocity"), "{{asset}} actual"), (e("metricchrono_robot_tracking_deviation_score", 'comparison="commanded_vs_actual"'), "{{asset}} tracking"), (e("metricchrono_robot_actuator_effort_change_score", 'source=~"$source"'), "{{source}} effort")]),
        make_panel("Missing / Late Data Around Incident", "timeseries", "Was the incident actually a telemetry freshness problem?", "Freshness gaps near incident start mean stale data may be the trigger or an important confounder.", "Robotics incidents are often timestamp, transform, middleware, or source-latency issues.", "Inspect source timestamps, middleware, CPU, network, and driver health.", [(e("metricchrono_robot_source_missing_total", 'source=~"$source"'), "{{source}} missing"), (e("metricchrono_robot_source_late_total", 'source=~"$source"'), "{{source}} late"), (e("metricchrono_robot_source_freshness_seconds", 'source=~"$source"'), "{{source}} freshness")]),
        make_panel("Replay Artifacts", "table", "What should I replay or inspect offline?", "Rows give bounded windows and source categories instead of asking you to search the full stream.", "Engineers do not want to search the full log stream.", "Use the suggested window and sources to inspect bags, logs, traces, or video.", [(positive_over_range("asset, time_window, subsystem, source, reason", e("metricchrono_robot_replay_artifact", 'severity=~"investigate|incident_candidate"')), "{{asset}} {{subsystem}} {{source}}")]),
        make_panel("Recovery Confirmation", "stat", "Did the robot actually recover?", "Recovery requires the state to return to normal and the relevant change, disagreement, and tracking scores to fall.", "A robot can leave fault state while still behaving abnormally.", "If recovery state is normal but scores remain high, keep investigating.", [(e("metricchrono_robot_recovery_state", 'state="recovered"'), "{{asset}} recovered"), (e("metricchrono_robot_overall_change_score", 'comparison="known_good_baseline"'), "{{asset}} overall"), (max_by("source", e("metricchrono_robot_source_disagreement_score", 'source=~"$source",comparison=~"sensor_vs_estimator|source_vs_source"')), "{{source}} disagreement"), (e("metricchrono_robot_tracking_deviation_score", 'comparison="commanded_vs_actual"'), "{{asset}} tracking")]),
    ]
    return {
        "robot-fleet-overview.json": dashboard("Robot Fleet Overview", overview, ["robotics-telemetry", "overview"], default_asset_group="fleet-a"),
        "robot-source-agreement.json": dashboard("Robot Source Agreement", agreement, ["robotics-telemetry", "source-agreement"], default_asset_group="fleet-a", default_asset="robot-r2"),
        "robot-incident-replay.json": dashboard("Robot Incident Replay", replay, ["robotics-telemetry", "incident-replay"], default_asset_group="fleet-a", default_asset="robot-r2", default_source="lidar|front_left_wheel|localization|camera"),
    }


def industrial_dashboards() -> dict[str, dict[str, Any]]:
    e = industrial_expr
    overview = [
        make_panel("Production State Timeline", "state-timeline", "Was the machine running, blocked, starved, changing over, or faulted when the change happened?", "Changes during planned changeover are interpreted differently from changes during steady running.", "Industrial telemetry is state-dependent. Comparing changeover to steady production creates false alarms.", "If the change occurs during running, inspect cycle and process panels. If during changeover, compare against changeover baseline.", [(e("metricchrono_industrial_line_state_code"), "{{asset}} line"), (e("metricchrono_industrial_cell_state_code"), "{{asset}} cell"), (e("metricchrono_industrial_machine_state_code"), "{{asset}} machine")], overrides=industrial_timeline_overrides()),
        make_panel("Line Change State By Station", "status-history", "Which station or machine is behaving differently?", "Rows are stations or machines. Watch, investigate, and incident candidate bands show stations that differ from the selected reference.", "Industrial engineers debug by station and machine, not by abstract signal.", "Inspect the abnormal station first. If multiple stations changed, inspect line state, material, schedule, or upstream bottleneck.", [(max_by("asset", e("metricchrono_industrial_station_change_state", 'comparison=~"$comparison"')), "{{asset}}")], mappings=value_mappings(CHANGE_STATE_CODE, CHANGE_STATE_COLORS)),
        make_panel("Overall Process Change Score", "timeseries", "Did the process move outside known-good behavior?", "A rising process score means the station or line behavior is moving away from the selected reference.", "This gives an early signal before downtime, scrap, or hard controller alarms.", "If the score rises during running, inspect cycle time, vibration, current, thermal behavior, sensor agreement, and quality proxy.", [(e("metricchrono_industrial_process_change_score", 'comparison=~"$comparison"'), "{{asset}} {{comparison}}")], unit="percent"),
        make_panel("Cycle Time vs Target", "timeseries", "Is the station drifting from expected cycle time?", "Cycle time above target means slowdown. Cycle change rising while cycle time is near target means early behavior change.", "Cycle time is familiar to plant teams. Change detection should augment it, not replace it.", "Inspect bottleneck, mechanical load, process variables, operator or material changes, and upstream or downstream blocking.", [(e("metricchrono_industrial_cycle_time_seconds"), "{{asset}} cycle"), (e("metricchrono_industrial_target_cycle_time_seconds"), "{{asset}} target"), (e("metricchrono_industrial_cycle_change_score", 'comparison="current_vs_target"'), "{{asset}} cycle change")], unit="s"),
        make_panel("Change Size Split", "timeseries", "Is this normal variation, sustained drift, or a major process shift?", "Small change often means normal noise. Sustained medium change means drift. Large change means incident candidate or state mismatch.", "Plant signals are noisy; engineers need scale separation without internal terminology.", "Use large change for immediate inspection and sustained medium change for early maintenance or process review.", [(max_by("change_size", e("metricchrono_industrial_change_score_by_size", 'change_size=~"$change_size",comparison=~"$comparison"')), "{{change_size}}")], unit="percent"),
        make_panel("Bottleneck / Top Station Change", "bargauge", "Which station is currently the best first suspect?", "The highest station is the one with the largest process or cycle deviation relative to the line or baseline.", "Industrial engineers need station-level triage, not aggregate line noise.", "Inspect the top station's cycle, machine state, process variables, and sensor agreement.", [(topk_max(5, "asset", e("metricchrono_industrial_station_change_score", 'comparison="station_vs_line"')), "{{asset}} station")], unit="percent"),
        make_panel("Quality / Reject Proxy", "timeseries", "Is process change showing up in quality?", "Quality proxy degradation aligned with process change increases urgency. Process change without quality degradation is still useful as early warning.", "Factories care about scrap, rework, and quality escape.", "If quality proxy falls or reject rate rises, inspect the station or process variables that changed first.", [(e("metricchrono_industrial_quality_proxy"), "{{asset}} quality proxy"), (e("metricchrono_industrial_reject_rate"), "{{asset}} reject rate"), (e("metricchrono_industrial_quality_change_score", 'comparison="known_good_baseline"'), "{{asset}} quality change")]),
        make_panel("Vibration / Current / Thermal Change", "timeseries", "Is the machine physically behaving differently?", "Rising vibration, current, or temperature change can indicate load, friction, bearing wear, motor issue, process resistance, or environmental condition.", "Industrial telemetry engineers monitor these variables for early maintenance and process health.", "Inspect mechanical load, lubrication, bearing or motor condition, process resistance, and maintenance history.", [(e("metricchrono_industrial_vibration_change_score"), "{{asset}} vibration"), (e("metricchrono_industrial_motor_current_change_score"), "{{asset}} current"), (e("metricchrono_industrial_temperature_change_score"), "{{asset}} temperature")], unit="percent"),
        make_panel("Sensor Disagreement Summary", "bargauge", "Is this process drift or one bad sensor or tag?", "One high source suggests sensor or tag issue. Many high sources suggest process or machine behavior changed.", "Bad tags and stale sensors are common industrial telemetry failure modes.", "If one sensor is high, inspect calibration, wiring, freshness, and mapping. If many sensors are high, inspect the process.", [(topk_max(5, "asset, source", e("metricchrono_industrial_sensor_disagreement_score", 'source=~"$source",comparison=~"sensor_vs_sensor|sensor_vs_controller|station_vs_line"')), "{{asset}} {{source}}")], unit="percent"),
        make_panel("Top Inspection Candidates", "table", "Where should I inspect first?", "The top row is the highest-priority station, machine, or source with an explainable reason.", "This converts the dashboard into a triage tool.", "Open Industrial Incident Replay for the top row.", [(positive_over_range("rank, asset, subsystem, source, reason, next_dashboard, comparison", e("metricchrono_industrial_inspection_candidate", 'severity=~"watch|investigate|incident_candidate"')), "{{asset}} {{subsystem}} {{source}}")]),
    ]
    agreement = [
        make_panel("Sensor Agreement Heatmap", "heatmap", "Which sensor, tag, or station stopped agreeing?", "A single hot sensor row points to a sensor or tag problem. A station-wide hot band points to machine or process change.", "This prevents treating bad telemetry as machine drift.", "Inspect the hot sensor or tag first if isolated; inspect process variables if station-wide.", [(max_by("source, subsystem", e("metricchrono_industrial_sensor_disagreement_score", 'source=~"$source",comparison=~"sensor_vs_sensor|sensor_vs_controller|station_vs_line"')), "{{source}} {{subsystem}}")], unit="percent"),
        make_panel("Sensor Reliability Score", "stat", "Which sensor or tag is least reliable right now?", "Low score means the source may be stale, missing, noisy, or inconsistent.", "Industrial dashboards often contain stale tags that look like stable process values.", "Inspect tag mapping, controller update, network path, sensor wiring, or calibration.", [(min_over_range("source", e("metricchrono_industrial_sensor_reliability_score", 'source=~"$source"')), "{{source}} reliability")], unit="percent", thresholds=RELIABILITY_THRESHOLDS),
        make_panel("Missing / Late Tags", "timeseries", "Did the data stream degrade?", "Missing or late tags rising during a process-change event may mean telemetry degraded rather than the machine changed.", "Telemetry reliability is often the difference between a process incident and a data incident.", "Inspect controller connectivity, gateway, tag subscription, network, and historian or exporter path.", [(sum_by("source", e("metricchrono_industrial_source_missing_total", 'source=~"$source"')), "{{source}} missing"), (sum_by("source", e("metricchrono_industrial_source_late_total", 'source=~"$source"')), "{{source}} late"), (max_by("source", e("metricchrono_industrial_tag_freshness_seconds", 'source=~"$source"')), "{{source}} freshness")]),
        make_panel("Cycle-Time Distribution", "timeseries", "Did cycle behavior shift, or was there one bad cycle?", "A distribution shift indicates sustained process or cycle drift. A single tail event suggests a transient interruption.", "Industrial engineers care about recurring cycle loss, not just isolated outliers.", "If the distribution shifts, inspect bottleneck, mechanical condition, process variable drift, and material flow.", [(histogram_percentile("0.50", e("metricchrono_industrial_cycle_time_seconds_bucket", 'le=~".*"')), "p50 cycle time"), (histogram_percentile("0.95", e("metricchrono_industrial_cycle_time_seconds_bucket", 'le=~".*"')), "p95 cycle time")], unit="s"),
        make_panel("Machine Physical Change", "timeseries", "Is the machine physically behaving differently?", "Rising physical change indicates machine or process load changed even before quality or downtime changes.", "This is the industrial engineer's early warning layer.", "Inspect load, friction, bearings, motor, cooling, pressure or flow path, lubrication, or process material.", [(e("metricchrono_industrial_vibration_change_score"), "{{asset}} vibration"), (e("metricchrono_industrial_motor_current_change_score"), "{{asset}} current"), (e("metricchrono_industrial_temperature_change_score"), "{{asset}} temperature"), (e("metricchrono_industrial_pressure_change_score"), "{{asset}} pressure"), (e("metricchrono_industrial_flow_change_score"), "{{asset}} flow")], unit="percent"),
        make_panel("Process Variable vs Change Score", "timeseries", "Which process variable moved with the change score?", "If a process variable moves before the change score, it may be causal or upstream. If it moves after, it may be an effect.", "Industrial engineers need to connect change detection to known process variables.", "Inspect the process variable that moves first.", [(e("metricchrono_industrial_process_variable_value", 'source="torque"'), "{{source}} value"), (e("metricchrono_industrial_process_change_score", 'comparison="known_good_baseline"'), "{{asset}} process change"), (e("metricchrono_industrial_cycle_change_score", 'comparison="current_vs_target"'), "{{asset}} cycle change")]),
        make_panel("Station vs Line Comparison", "bargauge", "Is this station uniquely abnormal or part of a line-wide shift?", "A station much higher than the line suggests local issue. Station and line rising together suggests material, schedule, changeover, or line-wide condition.", "This points investigation to local maintenance or line/system conditions.", "Inspect local station if isolated; inspect material flow, line state, upstream and downstream if broad.", [(e("metricchrono_industrial_station_change_score", 'comparison=~"station_vs_line|peer_asset"'), "{{asset}} station"), (e("metricchrono_industrial_line_change_score", 'comparison="station_vs_line"'), "{{asset_group}} line")], unit="percent"),
        make_panel("Quality Impact Correlation", "timeseries", "Is the process change affecting output quality?", "If quality change rises after process change, the drift may be turning into scrap or rework risk.", "This connects telemetry to production impact.", "Prioritize incidents with quality impact over isolated telemetry movement.", [(e("metricchrono_industrial_process_change_score", 'comparison="known_good_baseline"'), "{{asset}} process"), (e("metricchrono_industrial_quality_change_score", 'comparison="known_good_baseline"'), "{{asset}} quality change"), (e("metricchrono_industrial_reject_rate"), "{{asset}} reject rate")]),
        make_panel("Planned Changeover Guard", "state-timeline", "Are we comparing the machine to the correct state?", "If machine state is changeover, the dashboard should compare against changeover behavior, not running behavior.", "False positives during changeover destroy trust.", "If baseline is wrong, do not treat the change as an incident; fix baseline and state mapping.", [(e("metricchrono_industrial_machine_state_code"), "{{asset}} machine state"), (e("metricchrono_industrial_line_state_code"), "{{asset}} line state"), (e("metricchrono_industrial_baseline_in_use", 'comparison=~"same_machine_state|known_good_baseline"'), "{{asset}} baseline {{comparison}}"), (e("metricchrono_industrial_process_change_score", 'comparison=~"same_machine_state|known_good_baseline"'), "{{asset}} process {{comparison}}")], overrides=industrial_timeline_overrides()),
        make_panel("Machine Diagnostics Summary", "table", "What did the machine or controller already report?", "Rows summarize bounded categories, not raw messages.", "Existing controller diagnostics should remain primary when they are clear.", "Use diagnostics as primary explanation if aligned with process change.", [(positive_over_range("asset, subsystem, state", e("metricchrono_industrial_diagnostic_summary", 'state=~"sensor_stale|temperature_warning|motor_current_warning|cycle_timeout|quality_warning"')), "{{asset}} {{state}}")]),
        make_panel("Suggested Next Inspection", "table", "What should I inspect next?", "Rows translate metrics into plant actions.", "The recipe should reduce decision time.", "Follow the top row and inspect station, sensor, cycle, physical machine signal, or quality path.", [(positive_over_range("rank, asset, subsystem, source, reason, next_dashboard, comparison", e("metricchrono_industrial_inspection_candidate", 'severity=~"watch|investigate|incident_candidate"')), "{{asset}} {{subsystem}} {{source}}")]),
    ]
    replay = [
        make_panel("Incident Window Timeline", "state-timeline", "What was the line doing before, during, and after the incident?", "The incident must be bounded by pre-incident, incident, and recovery or ongoing state.", "State context determines whether the change is expected.", "Use the highlighted window to inspect historian data, controller logs, maintenance logs, or quality records.", [(e("metricchrono_industrial_line_state_code"), "{{asset}} line"), (e("metricchrono_industrial_machine_state_code"), "{{asset}} machine"), (e("metricchrono_industrial_incident_window_state_code"), "{{asset}} incident window")], overrides=industrial_timeline_overrides()),
        make_panel("First Meaningful Process Change", "stat", "What changed first?", "This panel names the first station and signal group such as cycle, vibration, current, thermal, sensor, or quality.", "This helps distinguish cause from downstream effects.", "Inspect the first changed station or source before later symptoms.", [(positive_over_range("asset, subsystem, source, comparison", e("metricchrono_industrial_first_change_offset_seconds", 'subsystem=~"cycle|physical_machine|sensor|quality"')), "{{asset}} {{subsystem}} {{source}} before impact")], unit="s"),
        make_panel("Process Change Around Incident", "timeseries", "How did the incident evolve?", "Look for which signal rises first and whether quality impact follows.", "Industrial incidents propagate from physical change to cycle drift to quality or downtime.", "Prioritize the first changed signal group.", [(e("metricchrono_industrial_process_change_score", 'comparison=~"known_good_baseline|same_machine_state|last_window"'), "{{asset}} process {{comparison}}"), (e("metricchrono_industrial_cycle_change_score", 'comparison="current_vs_target"'), "{{asset}} cycle"), (e("metricchrono_industrial_physical_machine_change_score"), "{{asset}} physical"), (e("metricchrono_industrial_quality_change_score", 'comparison="known_good_baseline"'), "{{asset}} quality")], unit="percent"),
        make_panel("Sensor Disagreement Around Incident", "heatmap", "Was it bad data or real process change?", "A single hot sensor row suggests bad or stale sensor. Many related sensors changing together suggests real process or machine behavior.", "This is the central industrial telemetry distinction.", "Inspect sensor or tag if isolated; inspect machine or process if broad.", [(max_by("source, subsystem", e("metricchrono_industrial_sensor_disagreement_score", 'source=~"$source",comparison=~"sensor_vs_sensor|sensor_vs_controller|station_vs_line"')), "{{source}} {{subsystem}}")], unit="percent"),
        make_panel("Cycle And Bottleneck Around Incident", "timeseries", "Did the incident affect throughput?", "Cycle time above target with rising station change points to throughput impact.", "Throughput loss is immediately actionable.", "Inspect station bottleneck, mechanical delays, material flow, and upstream or downstream blocking.", [(e("metricchrono_industrial_cycle_time_seconds"), "{{asset}} cycle"), (e("metricchrono_industrial_target_cycle_time_seconds"), "{{asset}} target"), (e("metricchrono_industrial_cycle_change_score", 'comparison="current_vs_target"'), "{{asset}} cycle change"), (e("metricchrono_industrial_station_change_score", 'comparison="station_vs_line"'), "{{asset}} station change")]),
        make_panel("Physical Machine Signals Around Incident", "timeseries", "Was the machine physically degrading or under abnormal load?", "Rising physical-machine scores before cycle or quality impact suggest early mechanical or process stress.", "This is where maintenance and controls engineers can act.", "Inspect mechanical load, lubrication, motor, bearings, cooling, and process resistance.", [(e("metricchrono_industrial_vibration_change_score"), "{{asset}} vibration"), (e("metricchrono_industrial_motor_current_change_score"), "{{asset}} current"), (e("metricchrono_industrial_temperature_change_score"), "{{asset}} temperature")], unit="percent"),
        make_panel("Quality / Reject Impact Around Incident", "timeseries", "Did the incident affect production quality?", "Quality impact after process drift increases urgency and helps prioritize action.", "Quality loss is the business consequence users care about.", "Escalate if quality impact appears; otherwise treat as early warning or maintenance candidate.", [(e("metricchrono_industrial_quality_proxy"), "{{asset}} quality proxy"), (e("metricchrono_industrial_reject_rate"), "{{asset}} reject rate"), (e("metricchrono_industrial_quality_change_score", 'comparison="known_good_baseline"'), "{{asset}} quality change")]),
        make_panel("Replay / Investigation Artifacts", "table", "What should I inspect offline?", "Rows give bounded windows and signal groups.", "The recipe should save the engineer from opening the entire historian or log stream.", "Use suggested tags and windows to inspect historian, controller logs, maintenance records, and quality records.", [(positive_over_range("asset, time_window, subsystem, source, reason", e("metricchrono_industrial_replay_artifact", 'severity=~"investigate|incident_candidate"')), "{{asset}} {{subsystem}} {{source}}")]),
    ]
    return {
        "industrial-line-overview.json": dashboard("Industrial Line Overview", overview, ["industrial-telemetry", "overview"], default_asset_group="line-1"),
        "industrial-machine-agreement.json": dashboard("Machine / Process Agreement", agreement, ["industrial-telemetry", "machine-agreement"], default_asset_group="line-1", default_asset="station-3"),
        "industrial-incident-replay.json": dashboard("Industrial Incident Replay", replay, ["industrial-telemetry", "incident-replay"], default_asset_group="line-1", default_asset="station-3", default_source="vibration_sensor|motor_current|pressure|quality_proxy|temperature"),
    }


def sample_line(name: str, labels: dict[str, str], value: float | int) -> str:
    label_text = "{" + ",".join(f'{key}="{labels[key]}"' for key in sorted(labels)) + "}"
    return f"{name}{label_text} {value}"


def emit_histogram(name: str, labels: dict[str, str], observations: list[float], buckets: list[float]) -> list[str]:
    lines: list[str] = []
    total = 0
    for bucket in buckets:
        count = sum(1 for value in observations if value <= bucket)
        total = max(total, count)
        lines.append(sample_line(f"{name}_bucket", labels | {"le": str(bucket)}, count))
    lines.append(sample_line(f"{name}_bucket", labels | {"le": "+Inf"}, len(observations)))
    lines.append(sample_line(f"{name}_sum", labels, round(sum(observations), 6)))
    lines.append(sample_line(f"{name}_count", labels, len(observations)))
    return lines


ROBOT_MISSION_CODE = {
    "idle": 0,
    "navigating": 1,
    "docking": 2,
    "manipulating": 3,
    "paused": 4,
    "fault": 5,
    "recovery": 6,
    "estop": 7,
    "unknown": 8,
}
ROBOT_STATUS_CODE = {
    "ok": 0,
    "warn": 1,
    "error": 2,
    "stale": 3,
    "fault": 4,
    "estop": 5,
    "recovery": 6,
}
ROBOT_WINDOW_CODE = {"pre_incident": 0, "incident": 1, "recovery": 2}

INDUSTRIAL_STATE_CODE = {
    "running": 0,
    "idle": 1,
    "starved": 2,
    "blocked": 3,
    "changeover": 4,
    "maintenance": 5,
    "fault": 6,
    "recovery": 7,
    "unknown": 8,
}
INDUSTRIAL_WINDOW_CODE = {"pre_incident": 0, "incident": 1, "recovery": 2, "ongoing": 3}

CHANGE_STATE_CODE = {"normal": 0, "watch": 1, "investigate": 2, "incident_candidate": 3, "recovered": 4}

ROBOT_MISSION_COLORS = {
    "idle": "green",
    "navigating": "green",
    "docking": "blue",
    "manipulating": "blue",
    "paused": "yellow",
    "fault": "red",
    "recovery": "blue",
    "estop": "red",
    "unknown": "orange",
}
ROBOT_STATUS_COLORS = {
    "ok": "green",
    "warn": "yellow",
    "error": "red",
    "stale": "orange",
    "fault": "red",
    "estop": "red",
    "recovery": "blue",
}
INDUSTRIAL_STATE_COLORS = {
    "running": "green",
    "idle": "green",
    "starved": "yellow",
    "blocked": "orange",
    "changeover": "blue",
    "maintenance": "blue",
    "fault": "red",
    "recovery": "blue",
    "unknown": "orange",
}
WINDOW_COLORS = {"pre_incident": "green", "incident": "red", "recovery": "blue", "ongoing": "orange"}
CHANGE_STATE_COLORS = {"normal": "green", "watch": "yellow", "investigate": "orange", "incident_candidate": "red", "recovered": "green"}


def robot_timeline_overrides() -> list[dict[str, Any]]:
    return [
        mapping_override(".* mission$", value_mappings(ROBOT_MISSION_CODE, ROBOT_MISSION_COLORS)),
        mapping_override(".* safety$|.* diagnostics$", value_mappings(ROBOT_STATUS_CODE, ROBOT_STATUS_COLORS)),
        mapping_override(".* incident window$", value_mappings(ROBOT_WINDOW_CODE, WINDOW_COLORS)),
    ]


def industrial_timeline_overrides() -> list[dict[str, Any]]:
    return [
        mapping_override(".* line$|.* cell$|.* machine$|.* line state$|.* machine state$", value_mappings(INDUSTRIAL_STATE_CODE, INDUSTRIAL_STATE_COLORS)),
        mapping_override(".* incident window$", value_mappings(INDUSTRIAL_WINDOW_CODE, WINDOW_COLORS)),
    ]


def metrics_text(metric_info: dict[str, tuple[str, str]], sample_lines: list[str]) -> str:
    output: list[str] = []
    for metric, (metric_type, help_text) in metric_info.items():
        output.append(f"# HELP {metric} {help_text}")
        output.append(f"# TYPE {metric} {metric_type}")
    output.extend(sample_lines)
    return "\n".join(output) + "\n"


def robot_samples(profile: bool | str) -> list[str]:
    if isinstance(profile, bool):
        profile = "incident" if profile else "normal"
    values_by_profile = {
        "normal": {"phase": "normal_navigation", "mission": "navigating", "safety": "ok", "diagnostic": "ok", "change_state": 0, "overall": 8, "tracking": 5, "source_score": 6, "effort": 7, "actual_speed": 1.05, "missing": 0, "late": 0, "freshness": 0.08, "small": 5, "medium": 0, "large": 0, "recovery": "recovered", "window": "pre_incident"},
        "jitter": {"phase": "harmless_small_jitter", "mission": "navigating", "safety": "ok", "diagnostic": "ok", "change_state": 1, "overall": 18, "tracking": 8, "source_score": 8, "effort": 9, "actual_speed": 1.02, "missing": 0, "late": 0, "freshness": 0.1, "small": 19, "medium": 0, "large": 0, "recovery": "recovered", "window": "pre_incident"},
        "source": {"phase": "perception_source_degradation", "mission": "navigating", "safety": "warn", "diagnostic": "stale", "change_state": 2, "overall": 44, "tracking": 12, "source_score": 72, "effort": 11, "actual_speed": 1.0, "missing": 3, "late": 6, "freshness": 2.8, "small": 19, "medium": 24, "large": 0, "recovery": "incomplete", "window": "pre_incident"},
        "tracking": {"phase": "tracking_deviation", "mission": "navigating", "safety": "warn", "diagnostic": "warn", "change_state": 2, "overall": 58, "tracking": 67, "source_score": 34, "effort": 24, "actual_speed": 0.69, "missing": 1, "late": 2, "freshness": 0.7, "small": 18, "medium": 38, "large": 7, "recovery": "incomplete", "window": "incident"},
        "actuator": {"phase": "actuator_effort_thermal_current_change", "mission": "navigating", "safety": "warn", "diagnostic": "warn", "change_state": 2, "overall": 66, "tracking": 60, "source_score": 30, "effort": 72, "actual_speed": 0.78, "missing": 0, "late": 1, "freshness": 0.4, "small": 18, "medium": 42, "large": 16, "recovery": "incomplete", "window": "incident"},
        "incident": {"phase": "incident_candidate", "mission": "navigating", "safety": "warn", "diagnostic": "stale", "change_state": 3, "overall": 84, "tracking": 76, "source_score": 72, "effort": 68, "actual_speed": 0.65, "missing": 4, "late": 7, "freshness": 2.8, "small": 19, "medium": 42, "large": 31, "recovery": "incomplete", "window": "incident"},
        "recovery": {"phase": "recovery", "mission": "recovery", "safety": "ok", "diagnostic": "ok", "change_state": 4, "overall": 14, "tracking": 10, "source_score": 9, "effort": 13, "actual_speed": 0.98, "missing": 0, "late": 0, "freshness": 0.1, "small": 12, "medium": 0, "large": 0, "recovery": "recovered", "window": "recovery"},
    }
    focus_values = values_by_profile[str(profile)]
    normal_values = values_by_profile["normal"]
    lines: list[str] = []
    assets = ["robot-r1", "robot-r2", "robot-r3"]
    sources = ["lidar", "camera", "imu", "wheel_encoders", "localization", "front_left_wheel"]
    for asset in assets:
        primary = asset == "robot-r2"
        values = focus_values if primary else normal_values
        base = {
            "site": "local-lab",
            "environment": "demo",
            "recipe": "robotics-telemetry",
            "asset_class": "amr",
            "asset_group": "fleet-a",
            "asset": asset,
        }
        phase_base = base | {"scenario_phase": values["phase"]}
        for phase in ["normal_navigation", "harmless_small_jitter", "perception_source_degradation", "tracking_deviation", "actuator_effort_thermal_current_change", "incident_candidate", "recovery"]:
            lines.append(sample_line("metricchrono_robot_scenario_phase", base | {"scenario_phase": phase}, 1 if phase == values["phase"] else 0))
        for metric, active in [
            ("metricchrono_robot_mission_state", values["mission"]),
            ("metricchrono_robot_safety_state", values["safety"]),
            ("metricchrono_robot_diagnostic_state", values["diagnostic"]),
        ]:
            for state in ["idle", "navigating", "docking", "manipulating", "paused", "fault", "recovery", "estop", "unknown", "ok", "warn", "error", "stale"]:
                if (metric.endswith("mission_state") and state not in ["idle", "navigating", "docking", "manipulating", "paused", "fault", "recovery", "estop", "unknown"]) or (not metric.endswith("mission_state") and state not in ["ok", "warn", "error", "stale", "fault", "estop", "recovery"]):
                    continue
                lines.append(sample_line(metric, base | {"state": state}, 1 if state == active else 0))
        lines.append(sample_line("metricchrono_robot_mission_state_code", base, ROBOT_MISSION_CODE[str(values["mission"])]))
        lines.append(sample_line("metricchrono_robot_safety_state_code", base, ROBOT_STATUS_CODE[str(values["safety"])]))
        lines.append(sample_line("metricchrono_robot_diagnostic_state_code", base, ROBOT_STATUS_CODE[str(values["diagnostic"])]))
        score = float(values["overall"])
        tracking = float(values["tracking"])
        source_score = float(values["source_score"])
        effort = float(values["effort"])
        for comparison in ["known_good_baseline", "same_mission_phase", "last_window", "commanded_vs_actual", "sensor_vs_estimator", "source_vs_source", "peer_asset"]:
            lines.append(sample_line("metricchrono_robot_change_state", base | {"comparison": comparison}, values["change_state"]))
            lines.append(sample_line("metricchrono_robot_overall_change_score", base | {"comparison": comparison}, score if comparison != "last_window" else max(score - 10, 2)))
            lines.append(sample_line("metricchrono_robot_motion_change_score", base | {"comparison": comparison}, max(tracking, effort, min(score, 70)) if primary else 5))
            lines.append(sample_line("metricchrono_robot_tracking_deviation_score", base | {"comparison": comparison}, tracking if comparison == "commanded_vs_actual" else max(tracking - 12, 0)))
            for size in ["small", "medium", "large"]:
                lines.append(sample_line("metricchrono_robot_change_score_by_size", base | {"comparison": comparison, "change_size": size}, values[size]))
        speed_actual = float(values["actual_speed"])
        for name, value in [
            ("metricchrono_robot_commanded_speed", 1.05),
            ("metricchrono_robot_actual_speed", speed_actual),
            ("metricchrono_robot_commanded_linear_velocity", 1.05),
            ("metricchrono_robot_actual_linear_velocity", speed_actual),
            ("metricchrono_robot_commanded_angular_velocity", 0.08),
            ("metricchrono_robot_actual_angular_velocity", 0.22 if primary else 0.08),
            ("metricchrono_robot_commanded_velocity", 1.05),
            ("metricchrono_robot_actual_velocity", speed_actual),
            ("metricchrono_robot_battery_change_score", max(min(effort - 35, 18), 4) if primary else 4),
            ("metricchrono_robot_power_change_score", max(min(effort - 20, 42), 5) if primary else 5),
            ("metricchrono_robot_thermal_change_score", max(min(effort - 15, 47), 4) if primary else 4),
            ("metricchrono_robot_voltage", 47.8 if primary else 49.2),
            ("metricchrono_robot_current", 24 if primary else 11),
            ("metricchrono_robot_temperature", 54 if primary else 37),
        ]:
            lines.append(sample_line(name, base, value))
        for state in ["recovered", "incomplete"]:
            lines.append(sample_line("metricchrono_robot_recovery_state", base | {"state": state}, 1 if state == values["recovery"] else 0))
        for source in sources:
            source_primary = primary and source in {"lidar", "front_left_wheel"} and max(source_score, effort) > 40
            source_base = base | {"source": source, "subsystem": "perception" if source in {"lidar", "camera"} else ("actuator" if "wheel" in source else "localization")}
            lines.append(sample_line("metricchrono_robot_source_disagreement_score", source_base | {"comparison": "sensor_vs_estimator"}, source_score if source == "lidar" and primary else (38 if primary and source == "camera" and source_score > 30 else 4)))
            lines.append(sample_line("metricchrono_robot_source_disagreement_score", source_base | {"comparison": "source_vs_source"}, source_score if source == "lidar" and primary else (46 if primary and source == "localization" and source_score > 50 else 5)))
            lines.append(sample_line("metricchrono_robot_source_reliability_score", source_base, 42 if source_primary else 94))
            lines.append(sample_line("metricchrono_robot_source_missing_total", source_base, values["missing"] if primary and source == "lidar" else 0))
            lines.append(sample_line("metricchrono_robot_source_late_total", source_base, values["late"] if primary and source == "lidar" else 0))
            lines.append(sample_line("metricchrono_robot_topic_freshness_seconds", source_base, values["freshness"] if primary and source == "lidar" else 0.08))
            lines.append(sample_line("metricchrono_robot_source_freshness_seconds", source_base, values["freshness"] if primary and source == "lidar" else 0.08))
            lines.append(sample_line("metricchrono_robot_actuator_effort_change_score", source_base, effort if source == "front_left_wheel" and primary else 6))
            lines.append(sample_line("metricchrono_robot_motor_current_change_score", source_base, max(effort - 5, 0) if source == "front_left_wheel" and primary else 5))
            lines.append(sample_line("metricchrono_robot_motor_temperature_change_score", source_base, max(effort - 20, 0) if source == "front_left_wheel" and primary else 3))
        for name, value in [
            ("metricchrono_robot_localization_disagreement_score", max(source_score - 11, 4) if primary else 4),
            ("metricchrono_robot_odometry_disagreement_score", max(source_score - 28, 3) if primary else 3),
            ("metricchrono_robot_imu_disagreement_score", max(source_score - 54, 2) if primary else 2),
            ("metricchrono_robot_perception_change_score", max(source_score - 6, 5) if primary else 5),
            ("metricchrono_robot_feature_count_change_score", max(source_score - 15, 4) if primary else 4),
            ("metricchrono_robot_perception_confidence_change_score", max(source_score - 20, 3) if primary else 3),
        ]:
            lines.append(sample_line(name, base | {"comparison": "sensor_vs_estimator"}, value))
        lines.extend(emit_histogram("metricchrono_robot_tracking_error_distance", base, [0.03, 0.04, 0.09, 0.17, 0.34 if tracking > 50 else 0.08], [0.02, 0.05, 0.1, 0.2, 0.5, 1.0]))
        for category in ["sensor_stale", "temperature_warning", "actuator_limit", "localization_warning"]:
            active_category = "sensor_stale" if values["diagnostic"] == "stale" else ("localization_warning" if values["diagnostic"] == "warn" else "")
            lines.append(sample_line("metricchrono_robot_diagnostic_summary", base | {"source": "lidar", "state": category}, 1 if primary and category == active_category else 0))
        severity = "incident_candidate" if score >= 75 else ("investigate" if score >= 50 else "watch")
        candidate_value = 1 if primary and score >= 40 else 0
        lines.append(sample_line("metricchrono_robot_inspection_candidate", base | {"rank": "1", "subsystem": "motion", "source": "front_left_wheel", "reason": "tracking deviation", "next_dashboard": "Robot Incident Replay", "comparison": "commanded_vs_actual", "change_size": "large" if values["large"] else "medium", "severity": severity}, candidate_value))
        for state in ["pre_incident", "incident", "recovery"]:
            lines.append(sample_line("metricchrono_robot_incident_window_state", base | {"state": state}, 1 if state == values["window"] else 0))
        lines.append(sample_line("metricchrono_robot_incident_window_state_code", base, ROBOT_WINDOW_CODE[str(values["window"])]))
        lines.append(sample_line("metricchrono_robot_first_change_offset_seconds", base | {"subsystem": "perception", "source": "lidar", "comparison": "sensor_vs_estimator"}, 12 if primary and profile in {"source", "tracking", "actuator", "incident"} else 0))
        for artifact_severity in ["watch", "investigate", "incident_candidate"]:
            lines.append(sample_line("metricchrono_robot_replay_artifact", base | {"time_window": "incident -30s to +60s", "subsystem": "perception", "source": "lidar", "reason": "freshness then tracking", "severity": artifact_severity}, candidate_value if artifact_severity == severity else 0))
    return lines


def industrial_samples(profile: bool | str) -> list[str]:
    if isinstance(profile, bool):
        profile = "incident" if profile else "normal"
    values_by_profile = {
        "normal": {"phase": "normal_running", "line": "running", "machine": "running", "change_state": 0, "process": 7, "cycle": 5, "station": 6, "line_score": 5, "cycle_time": 6.1, "quality": 98, "reject": 0.006, "quality_score": 3, "vibration": 4, "current": 5, "temperature": 4, "pressure": 3, "flow": 2, "physical": 4, "process_var": 51, "source": 4, "reliability": 96, "freshness": 0.25, "missing": 0, "late": 0, "small": 6, "medium": 0, "large": 0, "window": "pre_incident", "diag": "ok"},
        "changeover": {"phase": "planned_changeover", "line": "changeover", "machine": "changeover", "change_state": 0, "process": 12, "cycle": 9, "station": 8, "line_score": 9, "cycle_time": 7.2, "quality": 98, "reject": 0.006, "quality_score": 2, "vibration": 7, "current": 8, "temperature": 5, "pressure": 5, "flow": 4, "physical": 8, "process_var": 53, "source": 5, "reliability": 95, "freshness": 0.3, "missing": 0, "late": 0, "small": 12, "medium": 0, "large": 0, "window": "pre_incident", "diag": "ok"},
        "variation": {"phase": "harmless_small_process_variation", "line": "running", "machine": "running", "change_state": 1, "process": 18, "cycle": 9, "station": 14, "line_score": 8, "cycle_time": 6.3, "quality": 98, "reject": 0.006, "quality_score": 4, "vibration": 9, "current": 8, "temperature": 5, "pressure": 4, "flow": 4, "physical": 9, "process_var": 54, "source": 6, "reliability": 94, "freshness": 0.35, "missing": 0, "late": 0, "small": 18, "medium": 0, "large": 0, "window": "pre_incident", "diag": "ok"},
        "sensor": {"phase": "sensor_tag_degradation", "line": "running", "machine": "running", "change_state": 1, "process": 32, "cycle": 12, "station": 20, "line_score": 8, "cycle_time": 6.4, "quality": 98, "reject": 0.006, "quality_score": 5, "vibration": 18, "current": 10, "temperature": 6, "pressure": 8, "flow": 6, "physical": 16, "process_var": 55, "source": 68, "reliability": 52, "freshness": 5.4, "missing": 3, "late": 5, "small": 18, "medium": 12, "large": 0, "window": "pre_incident", "diag": "sensor_stale"},
        "physical": {"phase": "physical_machine_drift", "line": "running", "machine": "running", "change_state": 2, "process": 48, "cycle": 23, "station": 42, "line_score": 18, "cycle_time": 6.7, "quality": 97, "reject": 0.008, "quality_score": 10, "vibration": 72, "current": 54, "temperature": 42, "pressure": 26, "flow": 18, "physical": 70, "process_var": 63, "source": 34, "reliability": 83, "freshness": 0.4, "missing": 0, "late": 1, "small": 18, "medium": 28, "large": 0, "window": "incident", "diag": "motor_current_warning"},
        "cycle": {"phase": "cycle_drift_bottleneck", "line": "running", "machine": "running", "change_state": 2, "process": 64, "cycle": 72, "station": 70, "line_score": 30, "cycle_time": 8.6, "quality": 96, "reject": 0.012, "quality_score": 18, "vibration": 66, "current": 50, "temperature": 39, "pressure": 32, "flow": 22, "physical": 62, "process_var": 66, "source": 30, "reliability": 87, "freshness": 0.45, "missing": 0, "late": 1, "small": 18, "medium": 39, "large": 18, "window": "incident", "diag": "cycle_timeout"},
        "quality": {"phase": "quality_proxy_degradation", "line": "running", "machine": "running", "change_state": 2, "process": 70, "cycle": 66, "station": 72, "line_score": 32, "cycle_time": 8.4, "quality": 87, "reject": 0.038, "quality_score": 56, "vibration": 62, "current": 49, "temperature": 42, "pressure": 35, "flow": 24, "physical": 63, "process_var": 67, "source": 28, "reliability": 88, "freshness": 0.45, "missing": 0, "late": 1, "small": 18, "medium": 39, "large": 24, "window": "incident", "diag": "quality_warning"},
        "incident": {"phase": "incident_candidate", "line": "running", "machine": "fault", "change_state": 3, "process": 82, "cycle": 71, "station": 77, "line_score": 34, "cycle_time": 8.9, "quality": 86, "reject": 0.045, "quality_score": 52, "vibration": 75, "current": 58, "temperature": 49, "pressure": 38, "flow": 28, "physical": 73, "process_var": 68, "source": 69, "reliability": 51, "freshness": 5.4, "missing": 3, "late": 5, "small": 18, "medium": 39, "large": 34, "window": "incident", "diag": "motor_current_warning"},
        "recovery": {"phase": "recovery", "line": "recovery", "machine": "recovery", "change_state": 4, "process": 16, "cycle": 11, "station": 13, "line_score": 8, "cycle_time": 6.4, "quality": 97, "reject": 0.008, "quality_score": 7, "vibration": 12, "current": 10, "temperature": 8, "pressure": 5, "flow": 4, "physical": 11, "process_var": 54, "source": 8, "reliability": 93, "freshness": 0.35, "missing": 0, "late": 0, "small": 12, "medium": 0, "large": 0, "window": "recovery", "diag": "ok"},
    }
    focus_values = values_by_profile[str(profile)]
    normal_values = values_by_profile["normal"]
    lines: list[str] = []
    assets = ["station-1", "station-2", "station-3"]
    sources = ["vibration_sensor", "motor_current", "temperature", "pressure", "quality_proxy"]
    for asset in assets:
        focus = asset == "station-3"
        values = focus_values if focus or profile == "changeover" else normal_values
        base = {
            "site": "local-lab",
            "environment": "demo",
            "recipe": "industrial-telemetry",
            "asset_class": "packaging_cell",
            "asset_group": "line-1",
            "asset": asset,
        }
        for phase in ["normal_running", "planned_changeover", "harmless_small_process_variation", "sensor_tag_degradation", "physical_machine_drift", "cycle_drift_bottleneck", "quality_proxy_degradation", "incident_candidate", "recovery"]:
            lines.append(sample_line("metricchrono_industrial_scenario_phase", base | {"scenario_phase": phase}, 1 if phase == values["phase"] else 0))
        for metric, active in [
            ("metricchrono_industrial_line_state", values["line"]),
            ("metricchrono_industrial_cell_state", values["line"]),
            ("metricchrono_industrial_machine_state", values["machine"]),
        ]:
            for state in ["running", "idle", "starved", "blocked", "changeover", "maintenance", "fault", "recovery", "unknown"]:
                lines.append(sample_line(metric, base | {"state": state}, 1 if state == active else 0))
        lines.append(sample_line("metricchrono_industrial_line_state_code", base, INDUSTRIAL_STATE_CODE[str(values["line"])]))
        lines.append(sample_line("metricchrono_industrial_cell_state_code", base, INDUSTRIAL_STATE_CODE[str(values["line"])]))
        lines.append(sample_line("metricchrono_industrial_machine_state_code", base, INDUSTRIAL_STATE_CODE[str(values["machine"])]))
        for comparison in ["known_good_baseline", "same_machine_state", "last_window", "station_vs_line", "peer_asset", "sensor_vs_sensor", "sensor_vs_controller", "current_vs_target"]:
            process_value = values["process"]
            if profile == "changeover" and comparison == "known_good_baseline":
                process_value = 34
            if profile == "changeover" and comparison == "same_machine_state":
                process_value = 8
            lines.append(sample_line("metricchrono_industrial_station_change_state", base | {"comparison": comparison}, values["change_state"]))
            lines.append(sample_line("metricchrono_industrial_process_change_score", base | {"comparison": comparison}, process_value if comparison != "last_window" else max(process_value - 10, 2)))
            lines.append(sample_line("metricchrono_industrial_cycle_change_score", base | {"comparison": comparison}, values["cycle"]))
            lines.append(sample_line("metricchrono_industrial_station_change_score", base | {"comparison": comparison}, values["station"]))
            lines.append(sample_line("metricchrono_industrial_line_change_score", base | {"comparison": comparison}, values["line_score"]))
            lines.append(sample_line("metricchrono_industrial_baseline_in_use", base | {"comparison": comparison}, 1 if comparison in {"same_machine_state", "known_good_baseline"} else 0))
            for size in ["small", "medium", "large"]:
                lines.append(sample_line("metricchrono_industrial_change_score_by_size", base | {"comparison": comparison, "change_size": size}, values[size]))
        for name, value in [
            ("metricchrono_industrial_cycle_time_seconds", values["cycle_time"]),
            ("metricchrono_industrial_target_cycle_time_seconds", 6.0),
            ("metricchrono_industrial_wip_or_queue_change_score", max(values["cycle"] - 8, 4)),
            ("metricchrono_industrial_quality_proxy", values["quality"]),
            ("metricchrono_industrial_reject_rate", values["reject"]),
            ("metricchrono_industrial_quality_change_score", values["quality_score"]),
            ("metricchrono_industrial_vibration_change_score", values["vibration"]),
            ("metricchrono_industrial_motor_current_change_score", values["current"]),
            ("metricchrono_industrial_temperature_change_score", values["temperature"]),
            ("metricchrono_industrial_pressure_change_score", values["pressure"]),
            ("metricchrono_industrial_flow_change_score", values["flow"]),
            ("metricchrono_industrial_physical_machine_change_score", values["physical"]),
        ]:
            lines.append(sample_line(name, base, value))
        lines.append(sample_line("metricchrono_industrial_process_variable_value", base | {"source": "torque"}, values["process_var"]))
        for source in sources:
            source_primary = focus and source in {"vibration_sensor", "motor_current"} and values["source"] > 40
            source_base = base | {"source": source, "subsystem": "physical_machine" if source != "quality_proxy" else "quality"}
            disagreement = values["source"] if source_primary else (43 if focus and source == "pressure" and values["process"] > 70 else 4)
            for comparison in ["sensor_vs_sensor", "sensor_vs_controller", "station_vs_line"]:
                lines.append(sample_line("metricchrono_industrial_sensor_disagreement_score", source_base | {"comparison": comparison}, disagreement if comparison != "station_vs_line" else max(disagreement - 8, 3)))
            lines.append(sample_line("metricchrono_industrial_sensor_reliability_score", source_base, values["reliability"] if source_primary else 96))
            lines.append(sample_line("metricchrono_industrial_tag_freshness_seconds", source_base, values["freshness"] if source_primary else 0.25))
            lines.append(sample_line("metricchrono_industrial_source_missing_total", source_base, values["missing"] if focus and source == "vibration_sensor" else 0))
            lines.append(sample_line("metricchrono_industrial_source_late_total", source_base, values["late"] if focus and source == "vibration_sensor" else 0))
        lines.extend(emit_histogram("metricchrono_industrial_cycle_time_seconds", base, [5.9, 6.1, 6.2, 7.7, values["cycle_time"]], [5, 6, 7, 8, 10, 12]))
        for category in ["sensor_stale", "temperature_warning", "motor_current_warning", "cycle_timeout", "quality_warning"]:
            lines.append(sample_line("metricchrono_industrial_diagnostic_summary", base | {"state": category, "subsystem": "physical_machine"}, 1 if values["diag"] == category else 0))
        severity = "incident_candidate" if values["process"] >= 75 else ("investigate" if values["process"] >= 45 else "watch")
        candidate_value = 1 if focus and values["process"] >= 32 else 0
        lines.append(sample_line("metricchrono_industrial_inspection_candidate", base | {"rank": "1", "subsystem": "physical_machine", "source": "vibration_sensor", "reason": "vibration then cycle drift", "next_dashboard": "Industrial Incident Replay", "comparison": "station_vs_line", "change_size": "large" if values["large"] else "medium", "severity": severity}, candidate_value))
        for state in ["pre_incident", "incident", "recovery", "ongoing"]:
            lines.append(sample_line("metricchrono_industrial_incident_window_state", base | {"state": state}, 1 if state == values["window"] else 0))
        lines.append(sample_line("metricchrono_industrial_incident_window_state_code", base, INDUSTRIAL_WINDOW_CODE[str(values["window"])]))
        lines.append(sample_line("metricchrono_industrial_first_change_offset_seconds", base | {"subsystem": "physical_machine", "source": "vibration_sensor", "comparison": "station_vs_line"}, 480 if focus and profile in {"physical", "cycle", "quality", "incident"} else 0))
        for artifact_severity in ["watch", "investigate", "incident_candidate"]:
            lines.append(sample_line("metricchrono_industrial_replay_artifact", base | {"time_window": "incident -10m to +5m", "subsystem": "physical_machine", "source": "vibration_sensor", "reason": "vibration then cycle and quality", "severity": artifact_severity}, candidate_value if artifact_severity == severity else 0))
    return lines


ROBOT_PHASES = [
    "Normal navigation",
    "Harmless small jitter",
    "Perception/source degradation",
    "Tracking deviation or control oscillation",
    "Actuator effort / thermal or current change",
    "Incident candidate",
    "Recovery or incomplete recovery",
]

ROBOT_PHASE_PROFILES = [
    ("01-normal-navigation.prom", "normal"),
    ("02-harmless-small-jitter.prom", "jitter"),
    ("03-perception-source-degradation.prom", "source"),
    ("04-tracking-deviation.prom", "tracking"),
    ("05-actuator-effort.prom", "actuator"),
    ("06-incident-candidate.prom", "incident"),
    ("07-recovery.prom", "recovery"),
]

INDUSTRIAL_PHASES = [
    "Normal running",
    "Planned changeover or state transition",
    "Harmless small process variation",
    "Sensor/tag degradation",
    "Physical machine drift",
    "Cycle drift or bottleneck",
    "Quality proxy degradation or explicit no-quality-impact period",
    "Incident candidate",
    "Recovery or incomplete recovery",
]

INDUSTRIAL_PHASE_PROFILES = [
    ("01-normal-running.prom", "normal"),
    ("02-planned-changeover.prom", "changeover"),
    ("03-harmless-process-variation.prom", "variation"),
    ("04-sensor-tag-degradation.prom", "sensor"),
    ("05-physical-machine-drift.prom", "physical"),
    ("06-cycle-drift-bottleneck.prom", "cycle"),
    ("07-quality-proxy-impact.prom", "quality"),
    ("08-incident-candidate.prom", "incident"),
    ("09-recovery.prom", "recovery"),
]


def scenario_json(kind: str) -> dict[str, Any]:
    if kind == "robotics":
        return {
            "recipe": "robotics-telemetry",
            "default_run": "plays once and holds recovery unless --loop is passed",
            "assets": ["robot-r1", "robot-r2", "robot-r3"],
            "normal_peer_during_incident": "robot-r1",
            "phases": ROBOT_PHASES,
            "phase_metrics": [
                {"phase": phase, "file": f"phase-metrics/{filename}"}
                for phase, (filename, _profile) in zip(ROBOT_PHASES, ROBOT_PHASE_PROFILES)
            ],
            "visible_behavior": {
                "Normal navigation": "overview normal, source agreement low, tracking stable",
                "Harmless small jitter": "small change rises, medium and large remain low, no incident",
                "Perception/source degradation": "lidar disagreement and freshness age rise",
                "Tracking deviation or control oscillation": "commanded velocity remains steady while actual velocity diverges",
                "Actuator effort / thermal or current change": "front-left wheel effort/current/thermal scores rise",
                "Incident candidate": "robot-r2 becomes investigate or incident_candidate with bounded replay window",
                "Recovery or incomplete recovery": "scores fall; recovery state confirms or flags residual",
            },
        }
    return {
        "recipe": "industrial-telemetry",
        "default_run": "plays once and holds recovery unless --loop is passed",
        "assets": ["station-1", "station-2", "station-3"],
        "normal_peer_during_incident": "station-1",
        "phases": INDUSTRIAL_PHASES,
        "phase_metrics": [
            {"phase": phase, "file": f"phase-metrics/{filename}"}
            for phase, (filename, _profile) in zip(INDUSTRIAL_PHASES, INDUSTRIAL_PHASE_PROFILES)
        ],
        "visible_behavior": {
            "Normal running": "line overview normal, cycle near target",
            "Planned changeover or state transition": "production state changes without incident when same-state comparison is used",
            "Harmless small process variation": "small change rises only",
            "Sensor/tag degradation": "vibration sensor freshness and disagreement rise",
            "Physical machine drift": "vibration, current, and thermal scores rise",
            "Cycle drift or bottleneck": "cycle time distribution shifts and station-3 ranks highest",
            "Quality proxy degradation or explicit no-quality-impact period": "quality impact follows process drift",
            "Incident candidate": "top inspection table names station-3 and physical-machine reason",
            "Recovery or incomplete recovery": "process, cycle, and source scores fall or incomplete recovery remains visible",
        },
    }


def example_runner(kind: str) -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env python3
        \"\"\"Play the local {kind} synthetic scenario once by default.\"\"\"

        from __future__ import annotations

        import argparse
        import json
        import time
        from pathlib import Path

        SCENARIO = Path(__file__).with_name("scenario.json")


        def main() -> int:
            parser = argparse.ArgumentParser()
            parser.add_argument("--loop", action="store_true", help="repeat the scenario until interrupted")
            parser.add_argument("--sleep", type=float, default=0.15, help="seconds between demo phases")
            parser.add_argument("--output", default="scenario-metrics.prom", help="file to update with the current Prometheus snapshot")
            args = parser.parse_args()

            scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
            output = Path(args.output)

            while True:
                last_snapshot = ""
                for item in scenario["phase_metrics"]:
                    phase = item["phase"]
                    snapshot_path = Path(__file__).resolve().parent / item["file"]
                    snapshot = snapshot_path.read_text(encoding="utf-8")
                    output.write_text(snapshot, encoding="utf-8")
                    print(f"{{scenario['recipe']}}: {{phase}} -> {{output}}")
                    last_snapshot = snapshot
                    time.sleep(args.sleep)
                output.write_text(last_snapshot, encoding="utf-8")
                print(f"{{scenario['recipe']}}: recovery held in {{output}}")
                if not args.loop:
                    return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    )


def readme(recipe: str) -> str:
    if recipe == "robotics":
        title = "MetricChrono Robotics Telemetry Recipe"
        opening = "This recipe helps robotics engineers see when a robot's motion, estimator, sensors, or actuators changed meaningfully while ordinary telemetry may still look normal."
        screenshot = "robot-fleet-overview.png"
        run_dir = "synthetic-robot-scenario"
        concepts = "pose / odometry, commanded velocity, actual velocity, tracking error, localization confidence, source freshness, perception confidence, motor current, motor temperature, battery or power state, diagnostics, mission state, and safety state"
        dashboards = ["Robot Fleet Overview", "Robot Source Agreement", "Robot Incident Replay"]
        not_required = "ROS, ROS bags, a robot, a fleet manager, or a live sensor stack"
        make_command = "make robotics"
        npm_command = "npm run robotics:start"
        grafana_folder = "MetricChrono Robotics Recipes"
        comparison_examples = "`known_good_baseline`, `last_window`, `same_mission_phase`, `peer_asset`, `commanded_vs_actual`, `sensor_vs_estimator`, `source_vs_source`, and `actuator_vs_peer_actuator`"
        boundary = "It does not control, halt, or safely operate robots. It does not replace safety systems, robot controllers, ROS diagnostics, fleet managers, or incident policy."
    else:
        title = "MetricChrono Industrial Telemetry Recipe"
        opening = "This recipe helps industrial telemetry engineers see when a machine, station, line, sensor, or process cycle changed meaningfully before the failure becomes obvious in downtime, scrap, or alarms."
        screenshot = "industrial-line-overview.png"
        run_dir = "synthetic-industrial-scenario"
        concepts = "line, cell, station, machine state, cycle time, target cycle time, reject proxy, quality proxy, vibration, motor current, temperature, pressure, flow, controller state, sensor freshness, tag missingness, bottleneck, changeover, and fault state"
        dashboards = ["Industrial Line Overview", "Machine / Process Agreement", "Industrial Incident Replay"]
        not_required = "OPC UA, PLCs, SCADA, historians, a machine, or a line"
        make_command = "make industrial"
        npm_command = "npm run industrial:start"
        grafana_folder = "MetricChrono Industrial Recipes"
        comparison_examples = "`known_good_baseline`, `last_window`, `same_machine_state`, `peer_asset`, `station_vs_line`, `sensor_vs_sensor`, `source_vs_source`, and `current_vs_target`"
        boundary = "It does not control, halt, or safely operate machines, stations, or lines. It does not replace safety systems, PLC alarms, SCADA, historians, maintenance systems, quality systems, or incident policy."
    return textwrap.dedent(
        f"""\
        # {title}

        {opening}

        The local demo is synthetic and deterministic. It does not require {not_required}. The default run plays once and holds recovery; pass `--loop` only when you explicitly want a repeating demo.

        ![{dashboards[0]}](screenshots/{screenshot})

        ## Run The Grafana Demo

        From the repository root:

        ```bash
        {make_command}
        ```

        npm equivalent:

        ```bash
        {npm_command}
        ```

        Open the Grafana URL printed by the command. The dashboards are provisioned in the `{grafana_folder}` Grafana folder.

        ## Run The Fixture Scenario

        ```bash
        cd recipes/{'robotics-telemetry' if recipe == 'robotics' else 'industrial-telemetry'}/examples/{run_dir}
        python3 run_scenario.py
        ```

        The script writes `scenario-metrics.prom` as a Prometheus text snapshot for each phase. Use `fixtures/expected-metrics-normal.txt` and `fixtures/expected-metrics-incident.txt` as deterministic expected output.

        ## Three Terms

        Change score:
        {CHANGE_SCORE_GUIDE}

        Comparison:
        The reference used to judge current behavior. This recipe uses domain comparisons such as {comparison_examples}.

        Change size:
        `small` = jitter / noise / early movement, `medium` = operational deviation worth watching, and `large` = regime shift or incident candidate.

        ## What Ships

        Default dashboards:
        - {dashboards[0]}
        - {dashboards[1]}
        - {dashboards[2]}

        Out-of-the-box concepts:
        {concepts}.

        ## Boundaries

        This open recipe ships generic dashboard JSON, local synthetic scenarios, a metric contract, baseline guidance, alert examples, a panel guide, screenshots, and bounded demo fixtures. {boundary}

        See `docs/integration-guide.md`, `docs/metric-contract.md`, `docs/baseline-calibration.md`, `docs/alert-tuning.md`, and `docs/troubleshooting.md`.
        """
    )


def docs(recipe: str, panels_by_dashboard: dict[str, dict[str, Any]], metrics: dict[str, tuple[str, str]]) -> dict[str, str]:
    is_robot = recipe == "robotics"
    recipe_name = "robotics-telemetry" if is_robot else "industrial-telemetry"
    persona = "robotics engineers" if is_robot else "industrial telemetry engineers"
    optional_path = "ROS 2 topics, diagnostics, and bags" if is_robot else "OPC UA, PLC, SCADA, and historian exports"
    asset_guidance = (
        "Use `asset_group` for fleets or robot classes, and use `asset` only when the robot list is bounded."
        if is_robot
        else "Use `asset_group` for lines, cells, stations, or machine groups, and use `asset` only when the station or machine list is bounded."
    )
    raw_artifact_guidance = (
        "Preserve raw logs, ROS bags, traces, or video outside metric labels."
        if is_robot
        else "Preserve raw historian rows, PLC or SCADA events, maintenance records, quality records, and controller logs outside metric labels."
    )
    metric_contract_artifacts = (
        "Event IDs, bag names, trace IDs, raw topics, and free-form robot logs belong in ROS bags, log stores, traces, video stores, or event tables, not monitoring metric labels."
        if is_robot
        else "Event IDs, work orders, raw tags, raw messages, part or lot identifiers, and free-form maintenance notes belong in historians, PLC or SCADA event logs, quality records, maintenance systems, or event tables, not monitoring metric labels."
    )
    calibration_refresh = (
        "Refresh baselines after planned hardware, route, map, payload, software, controller, or mission changes."
        if is_robot
        else "Refresh baselines after planned machine, line, product, recipe, maintenance, tooling, or process changes."
    )
    troubleshooting_cases = (
        [
            "One source is hot: inspect freshness, calibration, mounting, driver, middleware, timestamping, or controller mapping before calling it a real behavior change.",
            "Many sources are hot: inspect mission state, environment, estimator health, map or route change, clock synchronization, or fleet update.",
            "Change appears during planned mission transition: verify the same-mission-phase baseline.",
            "Recovery state is normal but scores remain high: treat recovery as incomplete and keep the incident window open.",
            "A table suggests a broad replay: narrow the window to the incident candidate and source categories.",
        ]
        if is_robot
        else [
            "One source is hot: inspect freshness, calibration, wiring, tag subscription, gateway path, or controller mapping before calling it a real process change.",
            "Many sources are hot: inspect machine state, line state, material, changeover, upstream bottleneck, clock synchronization, or maintenance activity.",
            "Change appears during planned state transition: verify the same-machine-state baseline.",
            "Recovery state is normal but scores remain high: treat recovery as incomplete and keep the incident window open.",
            "A table suggests a broad inspection: narrow the window to the incident candidate and station, source, or quality categories.",
        ]
    )
    boundary_statement = (
        "The recipe does not replace safety systems, robot controllers, ROS diagnostics, fleet managers, or incident policy."
        if is_robot
        else "The recipe does not replace safety systems, PLC alarms, SCADA, historians, maintenance systems, quality systems, or incident policy."
    )
    source_disagreement_gloss = (
        "A signal that one source, sensor, estimator, controller, or actuator differs from its peers or reference. It is an inspection hint, not proof of fault."
        if is_robot
        else "A signal that one sensor, tag, controller state, station, or machine differs from its peers or reference. It is an inspection hint, not proof of fault."
    )
    replay_window_gloss = (
        "A bounded incident interval for logs, ROS bags, traces, or video review."
        if is_robot
        else "A bounded incident interval for historian data, PLC or SCADA events, maintenance records, quality records, or controller logs."
    )
    baselines = [
        "known-good navigation on same map / route type",
        "known-good docking behavior",
        "known-good manipulation cycle",
        "known-good idle state",
        "known-good robot of same hardware class",
        "previous stable software release",
    ] if is_robot else [
        "known-good running state",
        "known-good changeover state",
        "known-good station cycle",
        "known-good machine state",
        "known-good shift or product family",
        "peer station / peer machine",
        "previous stable maintenance period",
    ]
    comparator_guidance = [
        ("known_good_baseline", "use to answer is this outside normal?"),
        ("last_window", "use to answer did something sudden happen?"),
        ("same_mission_phase" if is_robot else "same_machine_state", "use to avoid comparing unlike operating states"),
        ("peer_asset", "use to answer is this asset different from comparable assets?"),
        ("commanded_vs_actual" if is_robot else "station_vs_line", "use to separate execution divergence from plan" if is_robot else "use to answer is this local or line-wide?"),
        ("sensor_vs_estimator" if is_robot else "sensor_vs_sensor", "use to answer did a source disagree with the fused state?" if is_robot else "use to answer is one tag or source lying?"),
    ]
    if not is_robot:
        comparator_guidance.append(("current_vs_target", "use for cycle time, throughput, and process setpoint checks"))
    docs_out: dict[str, str] = {}
    docs_out["docs/integration-guide.md"] = textwrap.dedent(
        f"""\
        # Integration Guide

        This recipe is designed for {persona}. The local path is a synthetic Prometheus textfile scenario, so evaluation does not require {optional_path}.

        Production integration should map domain signals into the metric contract in `metric-contract.md`. Keep labels bounded. {asset_guidance}

        ## Emit Prometheus Metrics

        1. Select a known-good baseline for each operating state.
        2. Compute user-facing change scores from domain streams.
        3. Emit Prometheus gauges, counters, and histograms using the metric names in this recipe.
        4. {raw_artifact_guidance}

        Optional integration path:
        {optional_path} can feed the metrics, but it is intentionally not required for the demo.
        """
    )
    docs_out["docs/metric-contract.md"] = textwrap.dedent(
        f"""\
        # Metric Contract

        Default dashboards use user-facing metrics only. Raw MetricChrono internals are not required to read these dashboards.

        ## Stable Labels

        Use these bounded labels where applicable:

        {chr(10).join(f"- `{label}`" for label in STABLE_LABELS)}

        ## Forbidden Labels

        Never use these as metric labels:

        {chr(10).join(f"- `{label}`" for label in forbidden_labels_for(recipe))}

        {metric_contract_artifacts}

        ## Change Score

        These are demo defaults, not production thresholds:

        ```text
        {CHANGE_SCORE_GUIDE}
        ```

        ## Comparison

        Allowed values include:

        {chr(10).join(f"- `{item}`" for item in comparisons_for(recipe))}

        ## Change Size

        {chr(10).join(f"- `{item}`" for item in CHANGE_SIZES)}

        ## Metrics

        {chr(10).join(f"- `{name}` ({kind}): {help_text}" for name, (kind, help_text) in sorted(metrics.items()))}
        """
    )
    docs_out["docs/baseline-calibration.md"] = textwrap.dedent(
        f"""\
        # Baseline Calibration

        Demo thresholds are not production thresholds. Do not copy them directly into production. Start from a known-good period with representative operation and no active incident.

        ## Baseline Examples

        {chr(10).join(f"- {item}" for item in baselines)}

        ## Comparator Guidance

        {chr(10).join(f"- `{name}`: {guidance}" for name, guidance in comparator_guidance)}

        ## Calibration Steps

        1. Choose a known-good period for each operating state.
        2. Verify source freshness and diagnostic health before fitting baselines.
        3. Run the synthetic scenario and compare expected normal versus incident fixtures.
        4. Tune alert windows conservatively and review with domain engineers.
        5. {calibration_refresh}
        """
    )
    docs_out["docs/alert-tuning.md"] = textwrap.dedent(
        f"""\
        # Alert Tuning

        Alerts are examples, not production policy. Keep them conservative and route them to engineers who can inspect the suggested dashboard and source.

        Tuning rules:
        - Alert on sustained watch or investigate bands, not single small-change spikes.
        - Include asset group, asset, subsystem, comparison, suggested dashboard, and next action.
        - Suppress or reclassify state-mismatch alerts during planned state changes when the correct same-state baseline is active.
        - Treat source disagreement as an inspection hint, not proof of a bad source.

        See `../rules/{'robotics-alerts.yml' if is_robot else 'industrial-alerts.yml'}` for example rules.
        """
    )
    guide_lines = ["# Dashboard Panel Guide", "", "Every panel description has exactly these fields:", "", *[f"- `{field}`" for field in DESCRIPTION_FIELDS], ""]
    for filename, dash in panels_by_dashboard.items():
        guide_lines.extend([f"## {dash['title']}", ""])
        for panel in dash["panels"]:
            guide_lines.extend([f"### {panel['title']}", "", panel["description"], ""])
    docs_out["docs/dashboard-panel-guide.md"] = "\n".join(guide_lines)
    docs_out["docs/troubleshooting.md"] = textwrap.dedent(
        f"""\
        # Troubleshooting

        Start with the overview dashboard, then inspect agreement, then replay.

        Common cases:
        {chr(10).join(f"- {item}" for item in troubleshooting_cases)}

        {boundary_statement}
        """
    )
    docs_out["docs/glossary.md"] = textwrap.dedent(
        f"""\
        # Glossary

        Change score:
        A normalized 0-100 score showing how much a stream moved from its reference.

        Comparison:
        The reference used to judge whether the current stream changed.

        Change size:
        A human-readable scale: small, medium, or large.

        Source disagreement:
        {source_disagreement_gloss}

        Replay window:
        {replay_window_gloss}

        Baseline:
        A known-good period selected in domain language and matched to the current operating state.
        """
    )
    return docs_out


def alerts(recipe: str) -> str:
    if recipe == "robotics":
        items = [
            ("RobotBehaviorChanged", 'metricchrono_robot_overall_change_score{comparison="known_good_baseline"} > 50', "Robot behavior changed", "Robot shows sustained behavior change. Inspect fleet overview and source agreement.", "motion", "known_good_baseline", "Robot Fleet Overview"),
            ("RobotSourceDisagreement", 'metricchrono_robot_source_disagreement_score{comparison="sensor_vs_estimator"} > 55', "Robot source disagreement", "A robot source disagrees with estimator or peers. Inspect Robot Source Agreement.", "perception", "sensor_vs_estimator", "Robot Source Agreement"),
            ("RobotSourceMissingOrLate", "increase(metricchrono_robot_source_late_total[2m]) > 0 or increase(metricchrono_robot_source_missing_total[2m]) > 0", "Robot source missing or late", "Telemetry freshness changed. Inspect drivers, middleware, CPU, network, and timestamps.", "telemetry", "current_freshness_vs_expected", "Robot Source Agreement"),
            ("RobotTrackingDeviation", 'metricchrono_robot_tracking_deviation_score{comparison="commanded_vs_actual"} > 55', "Robot tracking deviation", "Commanded and actual motion diverged. Inspect actuator effort and control context.", "motion", "commanded_vs_actual", "Robot Incident Replay"),
            ("RobotActuatorEffortChanged", "metricchrono_robot_actuator_effort_change_score > 55", "Robot actuator effort changed", "Robot is working harder than usual. Inspect named actuator, current, temperature, payload, and terrain.", "actuator", "known_good_baseline", "Robot Source Agreement"),
            ("RobotLocalizationDisagreement", "metricchrono_robot_localization_disagreement_score > 55", "Robot localization disagreement", "Localization disagrees with supporting sources. Inspect map, features, lidar/camera, IMU, and odometry.", "localization", "sensor_vs_estimator", "Robot Source Agreement"),
            ("RobotIncidentCandidate", 'metricchrono_robot_inspection_candidate{severity="incident_candidate"} > 0', "Robot incident candidate", "Top candidate requires replay. Open Robot Incident Replay for the affected robot.", "triage", "known_good_baseline", "Robot Incident Replay"),
            ("RobotRecoveryIncomplete", 'metricchrono_robot_recovery_state{state="incomplete"} > 0', "Robot recovery incomplete", "Robot left the incident state but change scores remain elevated. Continue investigation.", "recovery", "post_incident_vs_pre_incident", "Robot Incident Replay"),
        ]
        group = "robotics-telemetry"
    else:
        items = [
            ("IndustrialProcessChanged", 'metricchrono_industrial_process_change_score{comparison="known_good_baseline"} > 50', "Industrial process changed", "Station or line behavior moved outside known-good behavior. Inspect Industrial Line Overview.", "process", "known_good_baseline", "Industrial Line Overview"),
            ("IndustrialCycleDrift", "metricchrono_industrial_cycle_change_score > 55", "Industrial cycle drift", "Station shows sustained cycle drift. Inspect cycle time, bottleneck, and station context.", "cycle", "current_vs_target", "Industrial Incident Replay"),
            ("IndustrialSensorDisagreement", 'metricchrono_industrial_sensor_disagreement_score{comparison="sensor_vs_sensor"} > 55', "Industrial sensor disagreement", "A sensor or tag disagrees with peers or controller state. Inspect Machine / Process Agreement.", "sensor", "sensor_vs_sensor", "Machine / Process Agreement"),
            ("IndustrialTagMissingOrLate", "increase(metricchrono_industrial_source_late_total[2m]) > 0 or increase(metricchrono_industrial_source_missing_total[2m]) > 0", "Industrial tag missing or late", "Telemetry freshness degraded. Inspect controller, gateway, tag subscription, network, and exporter path.", "telemetry", "current_freshness_vs_expected", "Machine / Process Agreement"),
            ("IndustrialPhysicalMachineChanged", "metricchrono_industrial_physical_machine_change_score > 55", "Industrial physical machine changed", "Vibration, current, thermal, pressure, or flow behavior changed. Inspect physical machine signals.", "physical_machine", "known_good_baseline", "Machine / Process Agreement"),
            ("IndustrialQualityImpact", "metricchrono_industrial_quality_change_score > 45", "Industrial quality impact", "Quality proxy changed after process drift. Inspect quality and station signals.", "quality", "post_incident_vs_pre_incident", "Industrial Incident Replay"),
            ("IndustrialIncidentCandidate", 'metricchrono_industrial_inspection_candidate{severity="incident_candidate"} > 0', "Industrial incident candidate", "Top station or machine candidate requires replay. Open Industrial Incident Replay.", "triage", "station_vs_line", "Industrial Incident Replay"),
            ("IndustrialRecoveryIncomplete", 'metricchrono_industrial_incident_window_state{state="ongoing"} > 0', "Industrial recovery incomplete", "Incident window remains ongoing. Continue station and quality investigation.", "recovery", "post_incident_vs_pre_incident", "Industrial Incident Replay"),
        ]
        group = "industrial-telemetry"
    rules = ["groups:", f"- name: {group}", "  rules:"]
    for alert, expr, summary, description, main_subsystem, comparison, dashboard_name in items:
        rules.extend(
            [
                f"  - alert: {alert}",
                f"    expr: {expr}",
                "    for: 2m",
                "    labels:",
                "      severity: warning",
                f"      main_subsystem: {json.dumps(main_subsystem)}",
                f"      comparison: {json.dumps(comparison)}",
                "    annotations:",
                f"      summary: {json.dumps(summary)}",
                f"      description: {json.dumps(description)}",
                '      asset_group: "{{ $labels.asset_group }}"',
                '      asset: "{{ $labels.asset }}"',
                '      main_subsystem: "{{ $labels.main_subsystem }}"',
                '      comparison: "{{ $labels.comparison }}"',
                f"      suggested_dashboard: {json.dumps(dashboard_name)}",
                '      suggested_next_action: "Inspect the named subsystem/source, then open the suggested dashboard around the incident window."',
            ]
        )
    return "\n".join(rules) + "\n"


def normalize_markdown(content: str) -> str:
    lines = content.splitlines()
    normalized = [line[8:] if line.startswith("        ") else line for line in lines]
    return "\n".join(normalized).strip() + "\n"


def write(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".md":
        content = normalize_markdown(content)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate_recipe(kind: str) -> None:
    if kind == "robotics":
        slug = "robotics-telemetry"
        dashboards = robotics_dashboards()
        metrics = ROBOT_METRICS
        normal = metrics_text(metrics, robot_samples(False))
        incident = metrics_text(metrics, robot_samples(True))
        example_dir = "synthetic-robot-scenario"
        rules_file = "robotics-alerts.yml"
        phase_profiles = ROBOT_PHASE_PROFILES
        phase_samples = robot_samples
    else:
        slug = "industrial-telemetry"
        dashboards = industrial_dashboards()
        metrics = INDUSTRIAL_METRICS
        normal = metrics_text(metrics, industrial_samples(False))
        incident = metrics_text(metrics, industrial_samples(True))
        example_dir = "synthetic-industrial-scenario"
        rules_file = "industrial-alerts.yml"
        phase_profiles = INDUSTRIAL_PHASE_PROFILES
        phase_samples = industrial_samples
    root = RECIPES_ROOT / slug
    write(root / "README.md", readme(kind))
    for rel, content in docs(kind, dashboards, metrics).items():
        write(root / rel, content)
    for filename, data in dashboards.items():
        write_json(root / "grafana" / "dashboards" / filename, data)
    write(root / "rules" / rules_file, alerts(kind))
    write(root / "fixtures" / "expected-metrics-normal.txt", normal)
    write(root / "fixtures" / "expected-metrics-incident.txt", incident)
    for filename, profile in phase_profiles:
        write(root / "examples" / example_dir / "phase-metrics" / filename, metrics_text(metrics, phase_samples(profile)))
    write_json(root / "examples" / example_dir / "scenario.json", scenario_json(kind))
    write(root / "examples" / example_dir / "run_scenario.py", example_runner(kind), executable=True)


def write_recipe_index() -> None:
    write(
        RECIPES_ROOT / "README.md",
        textwrap.dedent(
            """\
            # MetricChrono Observability Recipes

            Each published recipe pack is rooted here as `recipes/<slug>/`.

            Published recipe packs:
            - `mlops`
            - `robotics-telemetry`
            - `industrial-telemetry`

            Reserved recipe families:
            - `sre-ai-services`
            - `agent-observability`
            """
        ),
    )
    for slug, title in [
        ("sre-ai-services", "SRE AI Services Recipe"),
        ("agent-observability", "Agent Observability Recipe"),
    ]:
        write(
            RECIPES_ROOT / slug / "README.md",
            textwrap.dedent(
                f"""\
                # {title}

                This directory reserves the expected multi-recipe layout. Published recipe packs live alongside it under `../mlops`, `../robotics-telemetry`, and `../industrial-telemetry`.
                """
            ),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", choices=["robotics", "industrial", "all"], default="all")
    args = parser.parse_args()
    if args.recipe in {"robotics", "all"}:
        generate_recipe("robotics")
    if args.recipe in {"industrial", "all"}:
        generate_recipe("industrial")
    write_recipe_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
