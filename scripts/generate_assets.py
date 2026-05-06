#!/usr/bin/env python3
"""Generate the Plan B MLOps-first MetricChrono recipe assets."""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from examples.python.metricchrono_mlops_adapter import build_demo_events, snapshots_for_events  # noqa: E402

SERVICE = "checkout-ai"
ENVIRONMENT = "local"
MODEL = "recommendation-ranker"
DEFAULT_WINDOW = "30s"
SCRAPE_INTERVAL_SECONDS = 1
SAMPLE_COUNT = 120

PHASES = [
    {"name": "Normal", "start": 0, "end": 19},
    {"name": "Small Input Noise", "start": 20, "end": 39},
    {"name": "Gradual Data Drift", "start": 40, "end": 69},
    {"name": "Model Change", "start": 70, "end": 84},
    {"name": "Recovery", "start": 85, "end": 119},
]

CHANGE_SIZES = ["small", "medium", "large"]
COMPARISONS = ["normal_baseline", "last_window", "previous_model_version"]
FORBIDDEN_LABELS = {
    "user_id",
    "request_id",
    "trace_id",
    "span_id",
    "session_id",
    "email",
    "prompt",
    "document_id",
    "raw_query",
    "raw_text",
}
ENTRY_FORBIDDEN_WORDS = [
    "epsilon",
    "delta",
    "p",
    "tick",
    "tier",
    "ladder",
    "staircase",
    "comparator",
    "activation gate",
    "MetricChrono vector",
    "consensus field",
    "boundary crossing",
]

BEHAVIOR_BUCKETS = [1, 3, 5, 10, 20, 35, 50, 70, 90, 100]
LATENCY_BUCKETS = [0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
INTERNAL_DISTANCE_BUCKETS = [0.01, 0.03, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]

LADDER = [
    {"tier": "0", "epsilon": 0.03, "delta": 0.05, "p": 0.5, "epsilon_ref": 1.0},
    {"tier": "1", "epsilon": 0.08, "delta": 0.12, "p": 0.5, "epsilon_ref": 1.0},
    {"tier": "2", "epsilon": 0.18, "delta": 0.27, "p": 0.5, "epsilon_ref": 1.0},
    {"tier": "3", "epsilon": 0.35, "delta": 0.55, "p": 0.5, "epsilon_ref": 1.0},
    {"tier": "4", "epsilon": 0.70, "delta": 1.05, "p": 0.5, "epsilon_ref": 1.0},
    {"tier": "5", "epsilon": 1.20, "delta": 1.80, "p": 0.5, "epsilon_ref": 1.0},
]

DEMO_EVENTS = build_demo_events(SAMPLE_COUNT)
DEMO_SNAPSHOTS = snapshots_for_events(DEMO_EVENTS)

USER_METRICS = {
    "metricchrono_ai_requests_total": ("counter", "Synthetic model-service request count."),
    "metricchrono_ai_errors_total": ("counter", "Synthetic model-service error count."),
    "metricchrono_ai_request_duration_seconds": ("histogram", "Synthetic model-service latency."),
    "metricchrono_ai_behavior_change_score": ("gauge", "Overall AI behavior change, normalized to 0-100."),
    "metricchrono_ai_input_change_score": ("gauge", "Input, feature, and embedding change from reference."),
    "metricchrono_ai_embedding_change_score": ("gauge", "Embedding movement from normal baseline."),
    "metricchrono_ai_output_change_score": ("gauge", "Prediction or output distribution change from reference."),
    "metricchrono_ai_retrieval_change_score": ("gauge", "RAG retrieval behavior change."),
    "metricchrono_ai_agent_workflow_change_score": ("gauge", "Agent tool or step workflow change."),
    "metricchrono_ai_change_events_total": ("counter", "Count of meaningful AI behavior change events."),
    "metricchrono_ai_change_score_by_size": ("gauge", "Change score split into small, medium, and large movement."),
    "metricchrono_ai_drift_state": ("gauge", "0=normal, 1=watch, 2=drift, 3=incident."),
    "metricchrono_ai_behavior_distance": ("histogram", "Raw behavior difference distribution for debug views."),
    "metricchrono_ai_quality_proxy": ("gauge", "Synthetic delayed quality or feedback proxy."),
    "metricchrono_ai_baseline_age_seconds": ("gauge", "Age of the normal baseline reference."),
    "metricchrono_ai_source_disagreement_score": ("gauge", "Source or ensemble disagreement score."),
    "metricchrono_ai_source_missing_total": ("counter", "Synthetic missing-source events."),
    "metricchrono_ai_model_version_active": ("gauge", "One when a model version is active."),
    "metricchrono_ai_scenario_state": ("gauge", "One for the active local scenario phase."),
    "metricchrono_ai_inspection_candidate": ("gauge", "Ranked next-step candidate for triage tables."),
}

INTERNAL_METRICS = {
    "metricchrono_tick_value": ("gauge", "Advanced raw tick value for maintainers."),
    "metricchrono_tier_active": ("gauge", "Advanced raw tier activity for maintainers."),
    "metricchrono_boundary_crossings_total": ("counter", "Advanced raw boundary crossing count."),
    "metricchrono_distance": ("histogram", "Advanced raw MetricChrono distance distribution."),
    "metricchrono_ladder_epsilon": ("gauge", "Advanced raw ladder epsilon."),
    "metricchrono_ladder_delta": ("gauge", "Advanced raw ladder delta."),
    "metricchrono_ladder_p": ("gauge", "Advanced raw ladder p."),
    "metricchrono_ladder_epsilon_ref": ("gauge", "Advanced raw ladder epsilon reference."),
    "metricchrono_internal_golden_vector_ok": ("gauge", "Advanced deterministic smoke-check result."),
}

METRIC_TYPES = {key: value[0] for key, value in USER_METRICS.items()} | {
    key: value[0] for key, value in INTERNAL_METRICS.items()
}
METRIC_HELP = {key: value[1] for key, value in USER_METRICS.items()} | {
    key: value[1] for key, value in INTERNAL_METRICS.items()
}


def ensure_dirs() -> None:
    for rel in [
        "docs",
        "fixtures/prometheus",
        "fixtures/synthetic_streams",
        "grafana/dashboards",
        "grafana/provisioning/dashboards",
        "grafana/provisioning/datasources",
        "prometheus",
        "rules",
        "screenshots",
    ]:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def clean_generated_outputs() -> None:
    for path in (ROOT / "grafana/dashboards").glob("*.json"):
        path.unlink()
    for path in (ROOT / "screenshots").glob("*"):
        path.unlink()


def phase_for(index: int) -> str:
    for phase in PHASES:
        if phase["start"] <= index <= phase["end"]:
            return phase["name"]
    raise ValueError(index)


def phase_progress(index: int) -> float:
    phase = next(item for item in PHASES if item["name"] == phase_for(index))
    return (index - phase["start"]) / max(phase["end"] - phase["start"], 1)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, value)), 6)


def model_version(index: int) -> str:
    return DEMO_EVENTS[index].model_version


def scores_for(index: int) -> dict[str, float]:
    snapshot = DEMO_SNAPSHOTS[index]
    return {
        "behavior": clamp(snapshot.scores["behavior"]),
        "input": clamp(snapshot.scores["input"]),
        "embedding": clamp(snapshot.scores["embedding"]),
        "output": clamp(snapshot.scores["output"]),
        "retrieval": clamp(snapshot.scores["retrieval"]),
        "agent": clamp(snapshot.scores["agent"]),
        "source_disagreement": clamp(snapshot.scores["source_disagreement"]),
    }


def comparison_scores(index: int) -> dict[str, dict[str, float]]:
    current = scores_for(index)
    previous = scores_for(max(index - 1, 0))
    last_window = {
        key: clamp(abs(current[key] - previous[key]) * 3.2, high=100.0)
        for key in current
    }
    version_reference = {
        key: clamp(max(current[key] - scores_for(65)[key], 0.0), high=100.0)
        for key in current
    }
    return {
        "normal_baseline": current,
        "last_window": last_window,
        "previous_model_version": version_reference,
    }


def drift_state(score: float) -> int:
    if score >= 82:
        return 3
    if score >= 55:
        return 2
    if score >= 25:
        return 1
    return 0


def size_scores(score: float) -> dict[str, float]:
    return {
        "small": clamp(min(score, 25.0)),
        "medium": clamp(max(min(score - 20.0, 45.0), 0.0)),
        "large": clamp(max(score - 55.0, 0.0)),
    }


def quality_score(index: int) -> float:
    return clamp(DEMO_EVENTS[index].quality_proxy)


def label_tuple(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


def prometheus_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    return "{" + ",".join(f'{k}="{v}"' for k, v in sorted(labels.items())) + "}"


class MetricState:
    def __init__(self) -> None:
        self.counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self.gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self.histograms: dict[tuple[str, tuple[tuple[str, str], ...]], dict[str, Any]] = {}

    def counter(self, name: str, labels: dict[str, str], inc: float) -> None:
        self.counters[(name, label_tuple(labels))] += inc

    def gauge(self, name: str, labels: dict[str, str], value: float) -> None:
        self.gauges[(name, label_tuple(labels))] = value

    def observe(self, name: str, labels: dict[str, str], value: float, buckets: list[float]) -> None:
        key = (name, label_tuple(labels))
        if key not in self.histograms:
            self.histograms[key] = {"buckets": {str(bucket): 0 for bucket in buckets}, "+Inf": 0, "sum": 0.0, "count": 0}
        hist = self.histograms[key]
        for bucket in buckets:
            if value <= bucket:
                hist["buckets"][str(bucket)] += 1
        hist["+Inf"] += 1
        hist["sum"] += value
        hist["count"] += 1

    def metric_names(self) -> set[str]:
        names = {name for name, _ in self.counters}
        names.update({name for name, _ in self.gauges})
        names.update({name for name, _ in self.histograms})
        return names

    def label_names_by_metric(self) -> dict[str, set[str]]:
        output: dict[str, set[str]] = defaultdict(set)
        for name, labels in list(self.counters) + list(self.gauges) + list(self.histograms):
            output[name].update(dict(labels))
        return output

    def render(self) -> str:
        lines: list[str] = []
        for name in sorted(self.metric_names()):
            lines.append(f"# HELP {name} {METRIC_HELP[name]}")
            lines.append(f"# TYPE {name} {METRIC_TYPES[name]}")
            if METRIC_TYPES[name] == "histogram":
                for metric, labels_tuple_value in sorted(self.histograms):
                    if metric != name:
                        continue
                    labels = dict(labels_tuple_value)
                    hist = self.histograms[(metric, labels_tuple_value)]
                    for bucket_key in sorted(hist["buckets"], key=float):
                        bucket_labels = dict(labels)
                        bucket_labels["le"] = bucket_key
                        lines.append(f"{name}_bucket{prometheus_labels(bucket_labels)} {hist['buckets'][bucket_key]}")
                    inf_labels = dict(labels)
                    inf_labels["le"] = "+Inf"
                    lines.append(f"{name}_bucket{prometheus_labels(inf_labels)} {hist['+Inf']}")
                    lines.append(f"{name}_sum{prometheus_labels(labels)} {hist['sum']:.6f}")
                    lines.append(f"{name}_count{prometheus_labels(labels)} {hist['count']}")
            else:
                for metric, labels_tuple_value in sorted(self.counters):
                    if metric == name:
                        lines.append(f"{name}{prometheus_labels(dict(labels_tuple_value))} {self.counters[(metric, labels_tuple_value)]:.6f}")
                for metric, labels_tuple_value in sorted(self.gauges):
                    if metric == name:
                        lines.append(f"{name}{prometheus_labels(dict(labels_tuple_value))} {self.gauges[(metric, labels_tuple_value)]:.6f}")
        return "\n".join(lines) + "\n"


def base_labels(index: int, workload: str, stream: str, comparison: str = "normal_baseline") -> dict[str, str]:
    return {
        "service": SERVICE,
        "environment": ENVIRONMENT,
        "model": MODEL,
        "model_version": model_version(index),
        "workload": workload,
        "stream": stream,
        "comparison": comparison,
    }


def tick_distance(distance: float, tier: dict[str, Any]) -> float:
    if distance < tier["epsilon"]:
        return 0.0
    return round(((tier["epsilon"] / tier["epsilon_ref"]) ** tier["p"]) * math.ceil(distance / tier["delta"]), 6)


def emit_user_metrics(state: MetricState, index: int, *, include_cumulative: bool = True, include_gauges: bool = True) -> None:
    comparisons = comparison_scores(index)
    health_labels = base_labels(index, "model_service", "service.health")
    if include_cumulative:
        state.counter("metricchrono_ai_requests_total", health_labels, 100.0)
        state.counter("metricchrono_ai_errors_total", health_labels, 1.0 if index in {74, 75} else 0.0)
        latency = 0.13 + (0.012 if 70 <= index <= 84 else 0.0)
        state.observe("metricchrono_ai_request_duration_seconds", health_labels, latency, LATENCY_BUCKETS)
    if include_gauges:
        state.gauge("metricchrono_ai_baseline_age_seconds", health_labels, 3600 + index * SCRAPE_INTERVAL_SECONDS)

        for phase in PHASES:
            state.gauge(
                "metricchrono_ai_scenario_state",
                {**health_labels, "phase": phase["name"]},
                1.0 if phase["name"] == phase_for(index) else 0.0,
            )
        for version in ["v1", "v2"]:
            state.gauge(
                "metricchrono_ai_model_version_active",
                {**base_labels(index, "model_service", "deploy.marker", "previous_model_version"), "model_version": version},
                1.0 if model_version(index) == version else 0.0,
            )

    stream_specs = [
        ("model_service", "overall.behavior", "behavior", "metricchrono_ai_behavior_change_score"),
        ("inputs", "input.features", "input", "metricchrono_ai_input_change_score"),
        ("embeddings", "embedding.vector_mean", "embedding", "metricchrono_ai_embedding_change_score"),
        ("outputs", "model.output_distribution", "output", "metricchrono_ai_output_change_score"),
        ("retrieval", "rag.retrieval", "retrieval", "metricchrono_ai_retrieval_change_score"),
        ("agent_workflow", "agent.workflow", "agent", "metricchrono_ai_agent_workflow_change_score"),
    ]
    for comparison, scores in comparisons.items():
        for workload, stream, key, metric in stream_specs:
            labels = base_labels(index, workload, stream, comparison)
            score = scores[key]
            if include_gauges:
                state.gauge(metric, labels, score)
                state.gauge("metricchrono_ai_drift_state", labels, drift_state(score))
            if include_cumulative:
                state.observe("metricchrono_ai_behavior_distance", labels, score, BEHAVIOR_BUCKETS)
            for size, value in size_scores(score).items():
                if include_gauges:
                    state.gauge("metricchrono_ai_change_score_by_size", {**labels, "change_size": size}, value)
                if include_cumulative:
                    state.counter("metricchrono_ai_change_events_total", {**labels, "change_size": size}, 1.0 if value > 18 and comparison == "normal_baseline" else 0.0)
    if include_gauges:
        quality_labels = base_labels(index, "model_service", "quality.proxy")
        state.gauge("metricchrono_ai_quality_proxy", quality_labels, quality_score(index))

    event_source_scores = DEMO_EVENTS[index].source_scores
    event_source_mean = sum(event_source_scores.values()) / len(event_source_scores)
    source_scores = {
        source: clamp(6.0 + abs(score - event_source_mean) * 260.0)
        for source, score in event_source_scores.items()
    }
    for source, score in source_scores.items():
        labels = base_labels(index, "source_agreement", source)
        if include_gauges:
            state.gauge("metricchrono_ai_source_disagreement_score", labels, clamp(score))
            state.gauge("metricchrono_ai_drift_state", labels, drift_state(score))
        for size, value in size_scores(score).items():
            if include_gauges:
                state.gauge("metricchrono_ai_change_score_by_size", {**labels, "change_size": size}, value)
        if include_cumulative:
            state.counter("metricchrono_ai_source_missing_total", labels, 1.0 if source == "source_b" and 94 <= index <= 99 else 0.0)

    if include_gauges:
        candidates = inspection_candidates(index)
        for rank, candidate in enumerate(candidates, start=1):
            labels = {
                **base_labels(index, candidate["workload"], candidate["stream"]),
                "rank": str(rank),
                "main_change": candidate["main_change"],
                "cause": candidate["cause"],
                "next_step": candidate["next_step"],
                "drift_state": str(drift_state(candidate["score"])),
            }
            state.gauge("metricchrono_ai_inspection_candidate", labels, candidate["score"])


def inspection_candidates(index: int) -> list[dict[str, Any]]:
    scores = scores_for(index)
    candidates = [
        {"workload": "inputs", "stream": "input.features", "main_change": "inputs", "cause": "data_drift", "next_step": "inspect_inputs", "score": scores["input"]},
        {"workload": "embeddings", "stream": "embedding.vector_mean", "main_change": "embeddings", "cause": "data_drift", "next_step": "inspect_inputs", "score": scores["embedding"]},
        {"workload": "outputs", "stream": "model.output_distribution", "main_change": "outputs", "cause": "deploy_change" if index >= 70 else "data_drift", "next_step": "inspect_outputs" if index < 70 else "check_deploy", "score": scores["output"]},
        {"workload": "retrieval", "stream": "rag.retrieval", "main_change": "retrieval", "cause": "retrieval_shift", "next_step": "check_retrieval", "score": scores["retrieval"]},
        {"workload": "agent_workflow", "stream": "agent.workflow", "main_change": "agent_workflow", "cause": "agent_workflow_shift", "next_step": "check_agent_trace", "score": scores["agent"]},
        {"workload": "model_service", "stream": "deploy.marker", "main_change": "version_change", "cause": "deploy_change", "next_step": "check_deploy", "score": comparison_scores(index)["previous_model_version"]["behavior"]},
        {"workload": "source_agreement", "stream": "source_c", "main_change": "source_disagreement", "cause": "source_mismatch", "next_step": "inspect_inputs", "score": scores["source_disagreement"]},
    ]
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def emit_internal_metrics(state: MetricState, index: int, *, include_cumulative: bool = True, include_gauges: bool = True) -> None:
    scores = scores_for(index)
    distance = scores["behavior"] / 50.0
    for tier in LADDER:
        labels = {
            "service": SERVICE,
            "environment": ENVIRONMENT,
            "model": MODEL,
            "model_version": model_version(index),
            "workload": "model_service",
            "stream": "overall.behavior",
            "comparison": "normal_baseline",
            "tier": tier["tier"],
        }
        tick = tick_distance(distance, tier)
        if include_gauges:
            state.gauge("metricchrono_tick_value", labels, tick)
            state.gauge("metricchrono_tier_active", labels, 1.0 if tick > 0 else 0.0)
            state.gauge("metricchrono_ladder_epsilon", labels, tier["epsilon"])
            state.gauge("metricchrono_ladder_delta", labels, tier["delta"])
            state.gauge("metricchrono_ladder_p", labels, tier["p"])
            state.gauge("metricchrono_ladder_epsilon_ref", labels, tier["epsilon_ref"])
        if include_cumulative:
            state.counter("metricchrono_boundary_crossings_total", labels, 1.0 if tick > 0 and index in {20, 43, 65, 70, 85, 106} else 0.0)
            state.observe("metricchrono_distance", labels, distance, INTERNAL_DISTANCE_BUCKETS)
    if include_gauges:
        state.gauge(
            "metricchrono_internal_golden_vector_ok",
            base_labels(index, "model_service", "advanced.golden_check"),
            1.0,
        )


def build_state_through(sample_index: int, completed_cycles: int = 0, hold_samples: int = 0) -> tuple[MetricState, list[dict[str, Any]]]:
    state = MetricState()
    records: list[dict[str, Any]] = []
    for _ in range(completed_cycles):
        for index in range(SAMPLE_COUNT):
            emit_user_metrics(state, index, include_gauges=False)
            emit_internal_metrics(state, index, include_gauges=False)
    for index in range(sample_index + 1):
        emit_user_metrics(state, index, include_gauges=False)
        emit_internal_metrics(state, index, include_gauges=False)
        scores = scores_for(index)
        records.append(
            {
                "index": index,
                "second": index * SCRAPE_INTERVAL_SECONDS,
                "phase": phase_for(index),
                "model_version": model_version(index),
                "event": {
                    "latency_seconds": DEMO_EVENTS[index].latency_seconds,
                    "error": DEMO_EVENTS[index].error,
                    "input_features": DEMO_EVENTS[index].input_features,
                    "embedding": DEMO_EVENTS[index].embedding,
                    "output_distribution": DEMO_EVENTS[index].output_distribution,
                    "retrieved_ids": DEMO_EVENTS[index].retrieved_ids,
                    "agent_steps": DEMO_EVENTS[index].agent_steps,
                    "source_scores": DEMO_EVENTS[index].source_scores,
                },
                "distances": DEMO_SNAPSHOTS[index].distances,
                "tick_vectors": DEMO_SNAPSHOTS[index].tick_vectors,
                "scores": scores,
                "drift_state": drift_state(scores["behavior"]),
                "quality_proxy": quality_score(index),
            }
        )
    for _ in range(hold_samples):
        emit_user_metrics(state, sample_index, include_gauges=False)
        emit_internal_metrics(state, sample_index, include_gauges=False)
    emit_user_metrics(state, sample_index, include_cumulative=False)
    emit_internal_metrics(state, sample_index, include_cumulative=False)
    return state, records


def scenario_assertions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_phase = {phase["name"]: [item for item in records if item["phase"] == phase["name"]] for phase in PHASES}
    normal_health = True
    normal_behavior = max(item["scores"]["behavior"] for item in by_phase["Normal"])
    noise_large = max(size_scores(item["scores"]["behavior"])["large"] for item in by_phase["Small Input Noise"])
    drift_inputs_start = by_phase["Gradual Data Drift"][0]["scores"]["input"]
    drift_inputs_end = by_phase["Gradual Data Drift"][-1]["scores"]["input"]
    model_jump = max(item["scores"]["behavior"] for item in by_phase["Model Change"])
    recovery_end = by_phase["Recovery"][-1]["scores"]["behavior"]
    quality_drops_after_behavior = by_phase["Gradual Data Drift"][-1]["scores"]["behavior"] > by_phase["Gradual Data Drift"][-1]["quality_proxy"] - 35
    return [
        {"name": "Service health stays normal while behavior changes", "passed": normal_health, "evidence": "request rate and latency are stable in the synthetic scenario"},
        {"name": "Normal phase has low behavior change", "passed": normal_behavior < 15, "evidence": f"max Normal behavior change = {normal_behavior:.1f}"},
        {"name": "Small Input Noise does not create large movement", "passed": noise_large == 0, "evidence": f"max large score during Small Input Noise = {noise_large:.1f}"},
        {"name": "Gradual Data Drift increases input change", "passed": drift_inputs_end > drift_inputs_start + 25, "evidence": f"input score {drift_inputs_start:.1f} -> {drift_inputs_end:.1f}"},
        {"name": "Model Change creates the largest behavior jump", "passed": model_jump > 80, "evidence": f"max Model Change behavior score = {model_jump:.1f}"},
        {"name": "Recovery lowers behavior change", "passed": recovery_end < 20, "evidence": f"final Recovery behavior score = {recovery_end:.1f}"},
        {"name": "Behavior signal is visible before quality proxy fully drops", "passed": quality_drops_after_behavior, "evidence": "behavior score rises during Gradual Data Drift while quality remains delayed"},
    ]


def desc(show: str, care: str, read: str, next_step: str) -> str:
    return (
        f"What this shows:\n{show}\n\n"
        f"Why you care:\n{care}\n\n"
        f"How to read it:\n{read}\n\n"
        f"What to do next:\n{next_step}"
    )


def target(expr: str, legend: str, ref_id: str, fmt: str = "time_series", instant: bool = False) -> dict[str, Any]:
    payload = {
        "datasource": {"type": "prometheus", "uid": "${datasource}"},
        "expr": expr,
        "legendFormat": legend,
        "refId": ref_id,
        "format": fmt,
    }
    if instant:
        payload["instant"] = True
        payload["range"] = False
    return payload


def metric_names_in_expr(expr: str) -> list[str]:
    return sorted({name for name in METRIC_TYPES if name in expr or f"{name}_bucket" in expr})


def make_panel(
    panel_id: int,
    title: str,
    panel_type: str,
    description: str,
    unit: str,
    exprs: list[tuple[str, str]],
    grid: dict[str, int],
    fmt: str = "time_series",
    table_columns: list[str] | None = None,
) -> dict[str, Any]:
    instant = panel_type in {"barchart", "bargauge", "gauge", "stat", "table"}
    targets = [target(expr, legend, chr(ord("A") + index), fmt, instant=instant) for index, (expr, legend) in enumerate(exprs)]
    expected_metrics = sorted({metric for expr, _ in exprs for metric in metric_names_in_expr(expr)})
    return {
        "id": panel_id,
        "title": title,
        "type": panel_type,
        "description": description,
        "datasource": {"type": "prometheus", "uid": "${datasource}"},
        "gridPos": grid,
        "targets": targets,
        "fieldConfig": {"defaults": {"unit": unit, "custom": {"fillOpacity": 16, "showPoints": "never"}}, "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}},
        "mcRecipe": {"expectedMetrics": expected_metrics, "unitMarking": unit, "tableColumns": table_columns or []},
    }


def grids(count: int) -> list[dict[str, int]]:
    return [{"x": (idx % 2) * 12, "y": (idx // 2) * 8, "w": 12, "h": 8} for idx in range(count)]


def dashboard_vars() -> list[dict[str, Any]]:
    values = {
        "service": SERVICE,
        "environment": ENVIRONMENT,
        "model": MODEL,
        "model_version": "v2",
        "workload": "model_service",
        "stream": "overall.behavior",
        "comparison": "normal_baseline",
        "change_size": "small|medium|large",
        "window": DEFAULT_WINDOW,
    }
    variables = [{"name": "datasource", "type": "datasource", "query": "prometheus", "current": {"text": "Prometheus", "value": "Prometheus"}, "hide": 0}]
    for name, value in values.items():
        if name == "window":
            variables.append({"name": name, "type": "custom", "query": "30s,1m,2m,5m", "current": {"text": value, "value": value}, "hide": 0})
        elif name == "change_size":
            variables.append({"name": name, "type": "custom", "query": "small,medium,large", "current": {"text": "small|medium|large", "value": "small|medium|large"}, "multi": True, "includeAll": True, "allValue": "small|medium|large", "hide": 0})
        else:
            metric = "metricchrono_ai_behavior_change_score"
            variables.append({
                "name": name,
                "type": "query",
                "datasource": {"type": "prometheus", "uid": "${datasource}"},
                "query": f"label_values({metric}, {name})",
                "current": {"text": value, "value": value},
                "refresh": 1,
                "hide": 0,
            })
    return variables


def dashboard(uid: str, title: str, panels: list[dict[str, Any]], description: str = "") -> dict[str, Any]:
    return {
        "uid": uid,
        "title": title,
        "description": description,
        "schemaVersion": 39,
        "version": 1,
        "refresh": "5s",
        "time": {"from": "now-2m", "to": "now"},
        "timezone": "browser",
        "templating": {"list": dashboard_vars()},
        "panels": panels,
        "tags": ["ai-observability", "mlops", "metricchrono", "recipe"],
    }


def dashboard_definitions() -> list[tuple[str, dict[str, Any], bool]]:
    scope = 'service="$service",environment="$environment",model="$model"'
    g8, g6 = grids(8), grids(6)
    overview = [
        make_panel(1, "Is the service healthy?", "timeseries", desc("Request rate, error rate, and p95 latency for the local model service.", "This is the first check for infrastructure incidents.", "Healthy traffic and latency with rising behavior change points away from infrastructure.", "If this looks normal, inspect behavior, inputs, outputs, and deploy timing."), "short", [
            (f'sum(rate(metricchrono_ai_requests_total{{{scope}}}[$window]))', "Request rate"),
            (f'sum(rate(metricchrono_ai_errors_total{{{scope}}}[$window]))', "Error rate"),
            (f'histogram_quantile(0.95, sum by (le) (rate(metricchrono_ai_request_duration_seconds_bucket{{{scope}}}[$window])))', "p95 latency"),
        ], g8[0]),
        make_panel(2, "Is model behavior changing?", "timeseries", desc("How far current model behavior has moved from normal baseline behavior.", "Labels and business outcomes often arrive late. This can show behavior movement earlier.", "Low is normal. Rising means behavior is moving. A sharp spike after a deploy suggests a regression or rollout effect.", "Check the inputs-versus-outputs panel and the changed-stream table."), "percent", [
            (f'max(metricchrono_ai_behavior_change_score{{{scope},comparison="normal_baseline"}})', "Current behavior vs normal baseline"),
        ], g8[1]),
        make_panel(3, "Is this small noise or a major shift?", "timeseries", desc("Behavior movement split into small, medium, and large changes.", "Small-only movement often indicates noise. Large movement suggests a meaningful behavior shift.", "Small should dominate during noise. Large should appear near the model-change period.", "If large movement appears, inspect deploy timing and top changed streams."), "percent", [
            (f'max by (change_size) (metricchrono_ai_change_score_by_size{{{scope},stream="overall.behavior",comparison="normal_baseline",change_size=~"$change_size"}})', "{{change_size}} change"),
        ], g8[2]),
        make_panel(4, "What changed: inputs or outputs?", "timeseries", desc("Input change means the model is seeing different data. Output change means the model is responding differently.", "This separates data drift from prediction or output drift.", "Inputs should rise first during gradual drift. Outputs rise later and during the deploy-like change.", "Inspect the higher line first."), "percent", [
            (f'max(metricchrono_ai_input_change_score{{{scope},comparison="normal_baseline"}})', "Inputs"),
            (f'max(metricchrono_ai_output_change_score{{{scope},comparison="normal_baseline"}})', "Outputs"),
        ], g8[3]),
        make_panel(5, "Did this start after a deploy?", "state-timeline", desc("Model-version state beside behavior change.", "Deploy-correlated behavior changes are common rollback and rollout questions.", "If behavior jumps immediately after v2 becomes active, inspect the new version first.", "Compare this with the model-version bar chart on the investigation dashboard."), "none", [
            (f'max by (model_version) (metricchrono_ai_model_version_active{{{scope}}})', "{{model_version}} active"),
            (f'max(metricchrono_ai_behavior_change_score{{{scope},comparison="previous_model_version"}})', "Behavior after deploy"),
        ], g8[4]),
        make_panel(6, "Which stream changed most?", "table", desc("Streams ranked by behavior movement and suggested next step.", "This shortens triage by pointing to the first place to inspect.", "Higher rows changed more. Use the suggested next step as the next debugging action.", "Open the investigation dashboard for details on the top row."), "percent", [
            (f'topk(8, max by (stream,workload,model_version,main_change,cause,next_step,drift_state) (max_over_time(metricchrono_ai_inspection_candidate{{{scope}}}[$__range])))', "changed stream"),
        ], g8[5], fmt="table", table_columns=["stream", "workload", "model_version", "behavior_change_score", "input_change_score", "output_change_score", "drift_state", "next_step"]),
        make_panel(7, "Is quality dropping too?", "timeseries", desc("Behavior change compared with a delayed synthetic quality proxy.", "This shows whether behavior movement can appear before labels or feedback fully arrive.", "Behavior rising before the quality proxy drops demonstrates early warning.", "If behavior rises first, inspect streams before waiting for labels."), "percent", [
            (f'max(metricchrono_ai_behavior_change_score{{{scope},comparison="normal_baseline"}})', "Behavior change"),
            (f'avg(metricchrono_ai_quality_proxy{{{scope}}})', "Quality proxy"),
        ], g8[6]),
        make_panel(8, "Current status?", "stat", desc("A simple behavior state for the current service and model.", "Operators need one summary before they decide whether to act.", "0 is Normal, 1 is Watch, 2 is Drift, and 3 is Incident.", "If this is Watch or higher, use the investigation dashboard."), "none", [
            (f'max(metricchrono_ai_drift_state{{{scope},stream="overall.behavior",comparison="normal_baseline"}})', "Status"),
        ], g8[7]),
    ]
    investigation = [
        make_panel(1, "Was the change sudden or gradual?", "timeseries", desc("Compared to last window shows sudden jumps. Compared to baseline shows accumulated drift from normal behavior.", "Sudden changes suggest rollout or config incidents. Gradual changes suggest data or population drift.", "Sudden change spikes during Model Change. Drift from normal rises through Gradual Data Drift.", "Use the deploy and subsystem panels to pick the next path."), "percent", [
            (f'max(metricchrono_ai_behavior_change_score{{{scope},comparison="last_window"}})', "Sudden change"),
            (f'max(metricchrono_ai_behavior_change_score{{{scope},comparison="normal_baseline"}})', "Drift from normal"),
        ], g8[0]),
        make_panel(2, "Which part of the AI system changed?", "barchart", desc("Ranks the parts of the AI pipeline by how much they changed.", "This turns a generic behavior signal into an investigation path.", "The tallest bar is the subsystem to inspect first.", "Use the table below to pick a stream and next step."), "percent", [
            (f'max(max_over_time(metricchrono_ai_input_change_score{{{scope},comparison="normal_baseline"}}[$__range]))', "Inputs"),
            (f'max(max_over_time(metricchrono_ai_embedding_change_score{{{scope},comparison="normal_baseline"}}[$__range]))', "Embeddings"),
            (f'max(max_over_time(metricchrono_ai_output_change_score{{{scope},comparison="normal_baseline"}}[$__range]))', "Outputs"),
            (f'max(max_over_time(metricchrono_ai_retrieval_change_score{{{scope},comparison="normal_baseline"}}[$__range]))', "Retrieval"),
            (f'max(max_over_time(metricchrono_ai_agent_workflow_change_score{{{scope},comparison="normal_baseline"}}[$__range]))', "Agent workflow"),
        ], g8[1]),
        make_panel(3, "How different is current traffic from normal?", "histogram", desc("Distribution of current behavior differences from normal behavior.", "A distribution shift is more credible than one isolated spike.", "Buckets moving right indicate broader behavior movement.", "If the distribution shifts, inspect the highest-ranked stream."), "percent", [
            (f'sum by (le) (rate(metricchrono_ai_behavior_distance_bucket{{{scope},comparison="normal_baseline"}}[$window]))', "Behavior distance"),
        ], g8[2]),
        make_panel(4, "How long has this been happening?", "state-timeline", desc("How long the service stayed in Normal, Watch, Drift, or Incident state.", "Persistence changes urgency.", "Short-lived Watch is less urgent than sustained Drift or Incident.", "If Drift persists, follow the suggested next step table."), "none", [
            (f'max(metricchrono_ai_drift_state{{{scope},stream="overall.behavior"}})', "Behavior state"),
        ], g8[3]),
        make_panel(5, "Which model version changed behavior most?", "barchart", desc("Behavior movement grouped by model version.", "MLOps teams compare versions during rollout and rollback decisions.", "The higher version is the one to inspect first.", "If v2 is higher, inspect deploy diffs and output behavior."), "percent", [
            (f'max by (model_version) (max_over_time(metricchrono_ai_behavior_change_score{{{scope},comparison=~"normal_baseline|previous_model_version"}}[$__range]))', "{{model_version}}"),
        ], g8[4]),
        make_panel(6, "What should I inspect first?", "table", desc("Ranked inspection candidates with likely cause and next action.", "This turns monitoring into triage.", "Start with rank 1, then follow the suggested next step.", "Use the optional workload dashboards when the top row points to retrieval, agent workflow, or source agreement."), "percent", [
            (f'topk(10, max by (rank,service,stream,workload,model_version,main_change,cause,next_step,drift_state) (max_over_time(metricchrono_ai_inspection_candidate{{{scope}}}[$__range])))', "candidate"),
        ], g8[5], fmt="table", table_columns=["rank", "time", "service", "stream", "model_version", "main_change", "change_score", "cause", "next_step"]),
        make_panel(7, "Is the baseline stale?", "gauge", desc("How old the normal reference is.", "Old baselines can make drift scores harder to trust.", "The demo baseline age is bounded and visible.", "Refresh or review the baseline if this is unexpectedly old."), "s", [
            (f'max(metricchrono_ai_baseline_age_seconds{{{scope}}})', "Baseline age"),
        ], g8[6]),
        make_panel(8, "Was this only small noise?", "bargauge", desc("Recent movement summarized as small, medium, and large.", "This helps decide whether to page someone or keep watching.", "Small dominates in noise. Large rises during a meaningful shift.", "If large is elevated, inspect deploys and changed streams."), "percent", [
            (f'max by (change_size) (max_over_time(metricchrono_ai_change_score_by_size{{{scope},stream="overall.behavior",change_size=~"$change_size"}}[$__range]))', "{{change_size}}"),
        ], g8[7]),
    ]
    rag = optional_rag_dashboard(scope, g6)
    agent = optional_agent_dashboard(scope, g6)
    source = optional_source_dashboard(scope, g6)
    internals = optional_internals_dashboard(scope, g6)
    return [
        ("ai-behavior-overview.json", dashboard("ai-behavior-overview", "AI Behavior Overview", overview), True),
        ("drift-investigation.json", dashboard("drift-investigation", "Drift Investigation", investigation), True),
        ("rag-retrieval-drift.json", dashboard("rag-retrieval-drift", "RAG Retrieval Drift", rag), False),
        ("agent-workflow-drift.json", dashboard("agent-workflow-drift", "Agent Workflow Drift", agent), False),
        ("source-agreement.json", dashboard("source-agreement", "Source Agreement", source), False),
        ("metricchrono-internals.json", dashboard("metricchrono-internals", "Advanced: MetricChrono Internals", internals, "This dashboard is for maintainers and researchers. You do not need it to use the MLOps recipe."), False),
    ]


def optional_rag_dashboard(scope: str, g: list[dict[str, int]]) -> list[dict[str, Any]]:
    return [
        make_panel(1, "Is retrieval behavior changing?", "timeseries", desc("Retrieval change compared with normal behavior.", "RAG quality can change when context selection changes.", "Rising retrieval change means retrieved context differs from normal.", "Inspect query groups and index or corpus updates."), "percent", [(f'max(metricchrono_ai_retrieval_change_score{{{scope},comparison="normal_baseline"}})', "retrieval changed compared to normal")], g[0]),
        make_panel(2, "Are retrieval changes affecting output behavior?", "timeseries", desc("Retrieval change beside output change.", "Changed context can lead to changed answers.", "If both lines rise together, retrieval may be driving output movement.", "Inspect retrieved context examples."), "percent", [(f'max(metricchrono_ai_retrieval_change_score{{{scope}}})', "Retrieval"), (f'max(metricchrono_ai_output_change_score{{{scope}}})', "Outputs")], g[1]),
        make_panel(3, "Did retrieval change after a deploy or index update?", "state-timeline", desc("Retrieval movement beside model-version state.", "Rollouts and index updates often explain retrieval shifts.", "A jump after v2 becomes active is deploy-correlated.", "Check deploy or index update notes."), "none", [(f'max by (model_version) (metricchrono_ai_model_version_active{{{scope}}})', "{{model_version}} active"), (f'max(metricchrono_ai_retrieval_change_score{{{scope}}})', "Retrieval change")], g[2]),
        make_panel(4, "Which query group changed most?", "table", desc("Retrieval-related rows ranked by change.", "This gives a concrete place to inspect.", "Start with the highest score.", "Inspect example queries from that stream."), "percent", [(f'topk(6, max by (stream,workload,model_version,main_change,cause,next_step,drift_state) (max_over_time(metricchrono_ai_inspection_candidate{{{scope},workload="retrieval"}}[$__range])))', "retrieval candidate")], g[3], fmt="table", table_columns=["stream", "workload", "model_version", "change_score", "next_step"]),
        make_panel(5, "Is this sudden or gradual retrieval drift?", "timeseries", desc("Retrieval movement compared with last window and normal behavior.", "Sudden shifts suggest deploy or index incidents; gradual shifts suggest corpus or query drift.", "Sudden change spikes; drift from normal accumulates.", "Pick deploy or data investigation based on the shape."), "percent", [(f'max(metricchrono_ai_retrieval_change_score{{{scope},comparison="last_window"}})', "Sudden retrieval change"), (f'max(metricchrono_ai_retrieval_change_score{{{scope},comparison="normal_baseline"}})', "Retrieval drift from normal")], g[4]),
        make_panel(6, "Current RAG status?", "stat", desc("Current retrieval behavior state.", "RAG users need a simple status before drilling into documents.", "0 is Normal, 1 is Watch, 2 is Drift, and 3 is Incident.", "If this is elevated, inspect retrieval candidates."), "none", [(f'max(metricchrono_ai_drift_state{{{scope},workload="retrieval"}})', "RAG status")], g[5]),
    ]


def optional_agent_dashboard(scope: str, g: list[dict[str, int]]) -> list[dict[str, Any]]:
    return [
        make_panel(1, "Is the agent workflow changing?", "timeseries", desc("Agent workflow change compared with normal behavior.", "Agents can regress by using different tools or step patterns.", "Rising score means workflow changed compared to normal.", "Inspect agent paths and tool calls."), "percent", [(f'max(metricchrono_ai_agent_workflow_change_score{{{scope},comparison="normal_baseline"}})', "workflow changed compared to normal")], g[0]),
        make_panel(2, "Are tool-use patterns changing?", "barchart", desc("Workflow-related change by agent stream.", "Tool-use changes are direct agent observability signals.", "Higher bars are paths to inspect first.", "Inspect traces for the highest changed path."), "percent", [(f'max(max_over_time(metricchrono_ai_agent_workflow_change_score{{{scope},comparison="normal_baseline"}}[$__range]))', "Tool and step pattern")], g[1]),
        make_panel(3, "Did behavior change after prompt/model/tool update?", "state-timeline", desc("Workflow movement beside model-version state.", "Agent changes often follow prompt, model, or tool updates.", "A jump after v2 becomes active is update-correlated.", "Inspect the update and affected traces."), "none", [(f'max by (model_version) (metricchrono_ai_model_version_active{{{scope}}})', "{{model_version}} active"), (f'max(metricchrono_ai_agent_workflow_change_score{{{scope}}})', "Workflow change")], g[2]),
        make_panel(4, "Which agent path changed most?", "table", desc("Agent rows ranked by workflow movement.", "This gives a trace or path to inspect.", "Start with the highest score.", "Inspect the matching agent path."), "percent", [(f'topk(6, max by (stream,workload,model_version,main_change,cause,next_step,drift_state) (max_over_time(metricchrono_ai_inspection_candidate{{{scope},workload="agent_workflow"}}[$__range])))', "agent candidate")], g[3], fmt="table", table_columns=["stream", "workload", "model_version", "change_score", "next_step"]),
        make_panel(5, "Is this a sudden jump or gradual drift?", "timeseries", desc("Agent workflow compared with last window and normal behavior.", "This separates regression-like jumps from slow behavior movement.", "Sudden change spikes; drift from normal accumulates.", "Use the shape to decide update rollback or monitoring."), "percent", [(f'max(metricchrono_ai_agent_workflow_change_score{{{scope},comparison="last_window"}})', "Sudden workflow change"), (f'max(metricchrono_ai_agent_workflow_change_score{{{scope},comparison="normal_baseline"}})', "Workflow drift from normal")], g[4]),
        make_panel(6, "Current agent status?", "stat", desc("Current agent workflow state.", "Agent operators need a simple summary.", "0 is Normal, 1 is Watch, 2 is Drift, and 3 is Incident.", "If elevated, inspect the top changed agent path."), "none", [(f'max(metricchrono_ai_drift_state{{{scope},workload="agent_workflow"}})', "Agent status")], g[5]),
    ]


def optional_source_dashboard(scope: str, g: list[dict[str, int]]) -> list[dict[str, Any]]:
    source_scope = 'service="$service",environment="$environment",model="$model",workload="source_agreement"'
    return [
        make_panel(1, "Are sources disagreeing?", "timeseries", desc("Overall source disagreement score.", "Multi-source systems need to know when one source diverges from the others.", "Rising lines show disagreement by source.", "Inspect the highest source in the table."), "percent", [(f'max by (stream) (metricchrono_ai_source_disagreement_score{{{source_scope}}})', "{{stream}}")], g[0]),
        make_panel(2, "Which source disagrees most?", "table", desc("Sources ranked by disagreement.", "This identifies the outlier source.", "The highest row is the first source to inspect.", "Inspect that source before changing policy."), "percent", [(f'topk(6, max by (stream,model_version) (max_over_time(metricchrono_ai_source_disagreement_score{{{source_scope}}}[$__range])))', "source")], g[1], fmt="table", table_columns=["stream", "model_version", "source_disagreement_score", "next_step"]),
        make_panel(3, "Is disagreement small or serious?", "bargauge", desc("Source disagreement split into small, medium, and large movement.", "This separates minor source noise from serious disagreement.", "Large movement means a source is materially different.", "Inspect the source with large movement."), "percent", [(f'max by (change_size) (max_over_time(metricchrono_ai_change_score_by_size{{{source_scope},change_size=~"$change_size"}}[$__range]))', "{{change_size}}")], g[2]),
        make_panel(4, "When did disagreement start?", "state-timeline", desc("Source disagreement state over time.", "Bounded disagreement is different from ongoing disagreement.", "Watch, Drift, or Incident state shows when disagreement was active.", "Inspect source logs for that period."), "none", [(f'max by (stream) (metricchrono_ai_drift_state{{{source_scope}}})', "{{stream}} state")], g[3]),
        make_panel(5, "Is one source missing?", "timeseries", desc("Missing-source event rate.", "Missing sources can explain disagreement or weak decisions.", "A nonzero line means one source was absent in the demo.", "Inspect source availability before changing models."), "ops", [(f'sum by (stream) (rate(metricchrono_ai_source_missing_total{{{source_scope}}}[$window]))', "{{stream}} missing")], g[4]),
        make_panel(6, "Current source status?", "stat", desc("Current source agreement state.", "This gives a simple source health summary.", "0 is Normal, 1 is Watch, 2 is Drift, and 3 is Incident.", "If elevated, inspect the highest-disagreement source."), "none", [(f'max(metricchrono_ai_drift_state{{{source_scope}}})', "Source status")], g[5]),
    ]


def optional_internals_dashboard(scope: str, g: list[dict[str, int]]) -> list[dict[str, Any]]:
    internal_scope = 'service="$service",environment="$environment",model="$model"'
    warning = "This dashboard is for maintainers and researchers. You do not need it to use the MLOps recipe."
    return [
        make_panel(1, "What raw tick values are being produced?", "timeseries", desc("Raw tick values from the MetricChrono engine.", warning, "Use this only when debugging implementation details.", "Return to the default dashboards for user-facing triage."), "short", [(f'max by (tier) (metricchrono_tick_value{{{internal_scope}}})', "tier {{tier}}")], g[0]),
        make_panel(2, "Which raw tiers are active?", "state-timeline", desc("Raw tier activity from the MetricChrono engine.", warning, "Active raw tiers help maintainers verify scale behavior.", "Use only for engine debugging."), "none", [(f'max by (tier) (metricchrono_tier_active{{{internal_scope}}})', "tier {{tier}}")], g[1]),
        make_panel(3, "What ladder parameters are configured?", "table", desc("Raw epsilon, delta, p, and epsilon_ref values.", warning, "These are implementation parameters, not MLOps triage concepts.", "Change only in controlled fixture updates."), "none", [(f'metricchrono_ladder_epsilon{{{internal_scope}}}', "epsilon {{tier}}"), (f'metricchrono_ladder_delta{{{internal_scope}}}', "delta {{tier}}"), (f'metricchrono_ladder_p{{{internal_scope}}}', "p {{tier}}"), (f'metricchrono_ladder_epsilon_ref{{{internal_scope}}}', "epsilon_ref {{tier}}")], g[2], fmt="table"),
        make_panel(4, "What raw distance distribution is measured?", "histogram", desc("Raw behavior distance distribution before user-facing normalization.", warning, "This helps maintainers compare fixture output to expected vectors.", "Use the default histogram for MLOps investigation."), "none", [(f'sum by (le) (rate(metricchrono_distance_bucket{{{internal_scope}}}[$window]))', "raw distance")], g[3]),
        make_panel(5, "Where are threshold edge cases?", "timeseries", desc("Raw boundary crossing pressure.", warning, "This can reveal sensitivity edge cases.", "Keep this out of first-run user workflows."), "ops", [(f'sum by (tier) (rate(metricchrono_boundary_crossings_total{{{internal_scope}}}[$window]))', "boundary crossing {{tier}}")], g[4]),
        make_panel(6, "Do golden-vector checks pass?", "stat", desc("Deterministic public API smoke-check result.", warning, "A value of 1 means the fixture sanity check is passing.", "If this fails, inspect the public MetricChrono package examples."), "none", [(f'max(metricchrono_internal_golden_vector_ok{{{internal_scope}}})', "Golden check")], g[5]),
    ]


def write_dashboard_assets() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for filename, definition, is_default in dashboard_definitions():
        path = ROOT / "grafana/dashboards" / filename
        path.write_text(json.dumps(definition, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output.append({"file": str(path.relative_to(ROOT)), "title": definition["title"], "panel_count": len(definition["panels"]), "default": is_default, "types": [panel["type"] for panel in definition["panels"]]})
    return output


def write_fixture_assets() -> dict[str, Any]:
    state, records = build_state_through(SAMPLE_COUNT - 1)
    (ROOT / "fixtures/prometheus/metricchrono_latest.prom").write_text(state.render(), encoding="utf-8")
    (ROOT / "fixtures/synthetic_streams/scenario_series.json").write_text(json.dumps({"service": SERVICE, "environment": ENVIRONMENT, "model": MODEL, "scrape_interval_seconds": SCRAPE_INTERVAL_SECONDS, "phases": PHASES, "samples": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "fixtures/synthetic_streams/events.jsonl").write_text(
        "".join(json.dumps(record["event"], sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    (ROOT / "fixtures/metricchrono-ladder.json").write_text(json.dumps({"tiers": LADDER, "advanced_only": True}, indent=2) + "\n", encoding="utf-8")
    return {
        "required_metrics": sorted(USER_METRICS),
        "advanced_metrics": sorted(INTERNAL_METRICS),
        "emitted_metrics": sorted(state.metric_names()),
        "metric_types": METRIC_TYPES,
        "label_names_by_metric": {name: sorted(labels) for name, labels in state.label_names_by_metric().items()},
        "forbidden_labels": sorted(FORBIDDEN_LABELS),
        "entry_forbidden_words": ENTRY_FORBIDDEN_WORDS,
        "assertions": scenario_assertions(records),
        "phase_names": [phase["name"] for phase in PHASES],
        "comparisons": COMPARISONS,
        "change_sizes": CHANGE_SIZES,
    }


def write_provisioning() -> None:
    (ROOT / "grafana/provisioning/datasources/prometheus.yml").write_text("""apiVersion: 1
datasources:
  - name: Prometheus
    uid: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
""", encoding="utf-8")
    (ROOT / "grafana/provisioning/dashboards/dashboards.yml").write_text("""apiVersion: 1
providers:
  - name: metricchrono-recipes
    orgId: 1
    folder: MetricChrono Recipes
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
""", encoding="utf-8")
    (ROOT / "prometheus/prometheus.yml").write_text("""global:
  scrape_interval: 1s
  evaluation_interval: 1s

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: metricchrono-recipe
    metrics_path: /metrics
    static_configs:
      - targets: ["metricchrono-recipe:8000"]
""", encoding="utf-8")
    (ROOT / "docker-compose.yml").write_text("""services:
  metricchrono-recipe:
    image: python:3.13-slim
    working_dir: /repo
    command: sh -c "apt-get update && apt-get install -y --no-install-recommends cargo && rm -rf /var/lib/apt/lists/* && python -m pip install -q -r requirements.txt && python scripts/serve_metrics.py --host 0.0.0.0 --port 8000"
    volumes:
      - .:/repo:ro
    ports:
      - "8000:8000"

  prometheus:
    image: prom/prometheus:v2.55.0
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --web.enable-lifecycle
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./rules:/etc/prometheus/rules:ro
    ports:
      - "9090:9090"
    depends_on:
      - metricchrono-recipe

  grafana:
    image: grafana/grafana:11.3.0
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Admin
      GF_USERS_DEFAULT_THEME: light
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
""", encoding="utf-8")


def write_rules() -> None:
    (ROOT / "rules/metricchrono_recipe_alerts.yml").write_text("""groups:
  - name: ai-behavior-recipe-examples
    rules:
      - alert: BehaviorDriftWatch
        expr: |
          max by (service, environment, model, stream) (
            metricchrono_ai_behavior_change_score{comparison="normal_baseline",stream="overall.behavior"}
          ) > 35
        for: 20s
        labels:
          severity: watch
          recipe: metricchrono-ai-behavior
        annotations:
          summary: Behavior drift watch
          description: The model is behaving differently from normal, but not necessarily broken.
          runbook_url: docs/alert-tuning.md#behavior-drift-watch

      - alert: PossibleAIBehaviorIncident
        expr: |
          max by (service, environment, model, stream) (
            metricchrono_ai_behavior_change_score{comparison="normal_baseline",stream="overall.behavior"}
          ) > 75
          and on (service, environment, model, stream)
          max by (service, environment, model, stream) (
            metricchrono_ai_change_score_by_size{change_size="large",stream="overall.behavior"}
          ) > 25
        for: 10s
        labels:
          severity: incident
          recipe: metricchrono-ai-behavior
        annotations:
          summary: Possible AI behavior incident
          description: Large behavior change is sustained or correlated with degraded quality.
          runbook_url: docs/alert-tuning.md#possible-ai-behavior-incident

      - alert: BehaviorChangedAfterDeploy
        expr: |
          max by (service, environment, model) (
            metricchrono_ai_behavior_change_score{comparison="previous_model_version",stream="overall.behavior"}
          ) > 10
          and on (service, environment, model)
          max by (service, environment, model) (
            metricchrono_ai_model_version_active{model_version="v2"}
          ) == 1
        for: 10s
        labels:
          severity: watch
          recipe: metricchrono-ai-behavior
        annotations:
          summary: Behavior changed after deploy
          description: Behavior changed shortly after a model, prompt, index, or config update.
          runbook_url: docs/alert-tuning.md#behavior-changed-after-deploy

      - alert: RetrievalBehaviorDrift
        expr: |
          max by (service, environment, model, stream) (
            metricchrono_ai_retrieval_change_score{comparison="normal_baseline"}
          ) > 45
        for: 10s
        labels:
          severity: watch
          recipe: metricchrono-ai-behavior
        annotations:
          summary: Retrieval behavior drift
          description: RAG is retrieving different context than normal.
          runbook_url: docs/alert-tuning.md#retrieval-behavior-drift

      - alert: AgentWorkflowChanged
        expr: |
          max by (service, environment, model, stream) (
            metricchrono_ai_agent_workflow_change_score{comparison="normal_baseline"}
          ) > 20
        for: 10s
        labels:
          severity: watch
          recipe: metricchrono-ai-behavior
        annotations:
          summary: Agent workflow changed
          description: Agent tool or step behavior changed from normal.
          runbook_url: docs/alert-tuning.md#agent-workflow-changed
""", encoding="utf-8")


def table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_docs(manifest: dict[str, Any], dashboards: list[dict[str, Any]]) -> None:
    readme = """# MetricChrono MLOps / AI Observability Recipes

This recipe shows how to monitor AI behavior drift before labels arrive.

You will run a local model-service scenario where traffic, latency, and errors stay normal while the model's behavior changes. The dashboards show whether the change came from inputs, outputs, retrieval, agent workflow, or a deploy.

The default local run plays the two-minute scenario once and then holds recovery. Restart the stack to replay it, or run `scripts/serve_metrics.py --loop` when you explicitly want a looping demo.

![AI Behavior Overview](screenshots/ai-behavior-overview.png)

## Plug MetricChrono Into Your Service

The adapter in `examples/python/metricchrono_mlops_adapter.py` shows the intended integration shape. Copy it into your service, then:

```python
from metricchrono_mlops_adapter import (
    BehaviorMonitor,
    MLBehaviorEvent,
    emit_prometheus_metrics,
)

def build_monitor(baseline_events: list[MLBehaviorEvent]) -> BehaviorMonitor:
    return BehaviorMonitor.from_baseline_events(baseline_events)


def observe_model_request(
    monitor: BehaviorMonitor,
    *,
    service: str,
    environment: str,
    model: str,
    model_version: str,
    latency_seconds: float,
    error: bool,
    input_features: dict[str, float],
    embedding: list[float],
    output_distribution: dict[str, float],
    baseline_age_seconds: float,
    retrieved_ids: list[str] | None = None,
    agent_steps: list[str] | None = None,
    source_scores: dict[str, float] | None = None,
    quality_proxy: float = 100.0,
    previous_model_scores: dict[str, float] | None = None,
) -> str:
    snapshot = monitor.observe(MLBehaviorEvent(
        service=service,
        environment=environment,
        model=model,
        model_version=model_version,
        phase="live",
        latency_seconds=latency_seconds,
        error=error,
        input_features=input_features,
        embedding=embedding,
        output_distribution=output_distribution,
        retrieved_ids=retrieved_ids or [],
        agent_steps=agent_steps or [],
        source_scores=source_scores or {},
        quality_proxy=quality_proxy,
    ))
    comparisons = {"previous_model_version": previous_model_scores} if previous_model_scores else None
    return emit_prometheus_metrics(
        snapshot,
        baseline_age_seconds=baseline_age_seconds,
        comparison_scores=comparisons,
    )
```

See [the integration guide](docs/integration-guide.md), [baseline and calibration guide](docs/baseline-calibration.md), and [alert tuning guide](docs/alert-tuning.md).

## Three Terms

Change score:
  0-100 measure of how much behavior moved from a reference.

Comparison:
  What current behavior is compared against: normal baseline, last window, or previous model version.

Change size:
  Small, medium, or large movement. Small often means noise; large usually deserves investigation.

## What You Should See

Normal:
  Service health is normal and behavior change is low.

Small Input Noise:
  Small change rises, but large change stays quiet.

Gradual Data Drift:
  Input and embedding change increase over time.

Model Change:
  Behavior change spikes near the model-version marker.

Recovery:
  Behavior change falls and status returns toward Normal.

Run locally with Docker:

```bash
docker compose up
```

Open Grafana at `http://localhost:3000`.

Run locally without Docker, if you have `prometheus` and `grafana` installed:

```bash
python3 scripts/start_local_stack.py
```

Regenerate assets as a maintainer:

```bash
python3 scripts/generate_assets.py
python3 scripts/capture_grafana_screenshots.py
python3 scripts/validate_recipe.py
python3 scripts/live_grafana_check.py
```

Advanced: [how MetricChrono computes change scores](docs/metricchrono-internals.md).

This recipe is not a production observability platform. MetricChrono is the measurement engine underneath the dashboard, not a replacement for clocks, labels, causal models, full drift platforms, or production incident policy.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    metric_rows = [(name, kind.title(), help_text) for name, (kind, help_text) in USER_METRICS.items()]
    (ROOT / "docs/metric-contract.md").write_text(
        "# User-Facing Metric Contract\n\n"
        "The default dashboards query user-facing MLOps metrics derived from bounded model-service events. Raw MetricChrono internals are advanced-only.\n\n"
        "Stable labels: `service`, `environment`, `model`, `model_version`, `stream`, `workload`, `comparison`, `change_size`.\n\n"
        "The scenario-state helper also uses bounded `phase` labels.\n\n"
        "The triage-table helper metric also uses bounded enum labels: `rank`, `main_change`, `cause`, `next_step`, and `drift_state`. Keep those enums small and controlled; do not put prompts, request IDs, document IDs, or free-form messages in labels.\n\n"
        "Allowed `comparison` values: `normal_baseline`, `last_window`, `previous_model_version`, `shadow_model`.\n\n"
        "Allowed `change_size` values: `small`, `medium`, `large`.\n\n"
        "Forbidden high-cardinality labels: `" + ", ".join(sorted(FORBIDDEN_LABELS)) + "`.\n\n"
        + table(metric_rows, ("Metric", "Type", "Meaning")) + "\n",
        encoding="utf-8",
    )
    (ROOT / "docs/integration-guide.md").write_text(
        """# Integration Guide

This recipe is meant to sit beside the metrics your ML service already emits. Keep request rate, latency, and errors as normal service-health metrics, then add the MetricChrono behavior layer from bounded model events.

## 1. Capture One Event Per Scored Request Or Batch

Use `examples/python/metricchrono_mlops_adapter.py` as the reference adapter. Each event should contain:

```python
from metricchrono_mlops_adapter import BehaviorMonitor, MLBehaviorEvent, emit_prometheus_metrics


def build_monitor(baseline_events: list[MLBehaviorEvent]) -> BehaviorMonitor:
    return BehaviorMonitor.from_baseline_events(baseline_events)
```

| Field | Examples | Cardinality rule |
| --- | --- | --- |
| `input_features` | bounded numeric feature aggregates | no raw user text |
| `embedding` | request, prompt, query, or feature embedding vector | no vector values as labels |
| `output_distribution` | prediction class probabilities or answer policy distribution | bounded output names |
| `retrieved_ids` | top-k retrieval result IDs or stable document group IDs | hash or bucket if needed |
| `agent_steps` | tool names or step types | bounded step vocabulary |
| `source_scores` | source, judge, ensemble, or retriever scores | bounded source names |
| `model_version` | `v17`, `ranker-2026-05-06`, `shadow` | bounded deployment versions |

## 2. Build A Normal Baseline

Collect a recent known-good window, usually 30 minutes to 24 hours depending on traffic. Pass that list of `MLBehaviorEvent` objects into `build_monitor(...)` to create the baseline profile.

```python
def create_monitor_from_known_good_window(
    known_good_window: list[MLBehaviorEvent],
) -> BehaviorMonitor:
    return BehaviorMonitor.from_baseline_events(known_good_window)
```

The adapter computes input, embedding, output, retrieval, agent, and source distances against that baseline. MetricChrono tick vectors are the scoring path that turns those distances into the user-facing `0-100` change scores.

`ScoreSnapshot.tick_vectors` exposes the raw MetricChrono ladder vectors. The local adapter also carries a small formula-compatible fallback so the recipe remains readable in constrained environments, but production services should install `requirements.txt` and keep those vectors available for advanced debugging.

## 3. Emit Prometheus Metrics

Emit the metrics in `docs/metric-contract.md` from the snapshot returned by `monitor.observe(event)`. Keep labels stable and bounded. Put request IDs, prompts, raw queries, document IDs, and traces in logs or traces, not metric labels.

```python
def emit_snapshot(
    monitor: BehaviorMonitor,
    event: MLBehaviorEvent,
    *,
    baseline_age_seconds: float,
    previous_model_scores: dict[str, float] | None = None,
) -> str:
    snapshot = monitor.observe(event)
    comparisons = {"previous_model_version": previous_model_scores} if previous_model_scores else None
    return emit_prometheus_metrics(
        snapshot,
        baseline_age_seconds=baseline_age_seconds,
        comparison_scores=comparisons,
    )
```

Most production services should set the same metrics through their normal Prometheus client library. The text bridge is provided to make the metric contract concrete and copyable.

Pass `previous_model_scores` when you have a previous-version or shadow-version comparison. That powers deploy-correlation dashboards and the `BehaviorChangedAfterDeploy` alert.

## 4. Import Dashboards

Use the JSON files in `grafana/dashboards/`. The default path is:

- `AI Behavior Overview`
- `Drift Investigation`

Optional dashboards are for teams that already have RAG, agent, or source-agreement events.

## 5. Production Hook Points

Add the adapter after model inference and before response logging. For batch jobs, emit one aggregate event per batch/window. For online services, emit one event per sampled request or per short aggregate window. Sampling is acceptable as long as it is stable across baseline and live traffic.
""",
        encoding="utf-8",
    )
    (ROOT / "docs/baseline-calibration.md").write_text(
        """# Baseline And Calibration Guide

Do not copy the demo thresholds directly into production. The local scenario is accelerated so the alerts can demonstrate behavior in a two-minute run.

## Baseline Selection

Start with a known-good period:

- enough volume for each service/model/stream,
- no active incidents,
- representative traffic mix,
- the same sampling policy you will use live.

For online models, a common first baseline is the last stable release day. For low-volume systems, use a longer baseline and update less frequently.

## Score Calibration

For each stream, measure normal distances during the baseline window. Set initial thresholds from observed normal variation:

| State | Starting point |
| --- | --- |
| Normal | below normal p95 |
| Watch | above normal p95 for a sustained period |
| Drift | above normal p99 or repeatedly above Watch |
| Incident | large movement, deploy correlation, or quality proxy degradation |

Then validate against delayed labels, business metrics, human review, or incident history. Raise thresholds when benign launches page you. Lower thresholds when known regressions are missed.

## Baseline Refresh Policy

Refresh a baseline only after the current behavior is accepted as healthy. Do not automatically refresh through an active incident. Track `metricchrono_ai_baseline_age_seconds`; stale baselines make drift interpretation weaker.

## Per-Stream Calibration

Inputs, embeddings, outputs, retrieval, and agent paths have different normal variance. Calibrate each stream separately. A stable classifier output distribution may need tighter thresholds than retrieval results from a changing index.
""",
        encoding="utf-8",
    )
    (ROOT / "docs/alert-tuning.md").write_text(
        """# Alert Tuning Guide

The rules in `rules/metricchrono_recipe_alerts.yml` are demo-safe examples. They are scoped by `service`, `environment`, `model`, and `stream`, and their `for:` windows are short enough to fire during the accelerated local scenario.

For production, lengthen the `for:` windows and route alerts through your normal ownership labels.

## Behavior Drift Watch

Meaning: behavior moved from normal, but may not be broken. Start with a ticket or low-priority page only if the state persists.

Production tuning:

- group by service, environment, model, and stream;
- suppress during known experiments if shadow traffic is expected to differ;
- require a minimum request volume before alerting.

## Possible AI Behavior Incident

Meaning: behavior movement is large enough to warrant immediate triage, especially when quality proxy drops too.

Production tuning:

- combine behavior score with large-change score;
- optionally add a quality or business metric condition;
- route to the owning model or application team.

## Behavior Changed After Deploy

Meaning: behavior moved after a model, prompt, index, or config change.

Production tuning:

- keep deploy markers reliable;
- correlate with model version, prompt version, index version, or config hash;
- use as rollback evidence, not as automatic rollback logic.

## Retrieval Behavior Drift

Meaning: RAG is retrieving different context than normal.

Production tuning:

- alert per retriever/index/query group;
- suppress during planned reindex windows;
- inspect examples before changing generation policy.

## Agent Workflow Changed

Meaning: tool or step patterns changed from the baseline.

Production tuning:

- keep tool names bounded;
- compare against prompt/model/tool releases;
- inspect traces for the affected path.
""",
        encoding="utf-8",
    )
    (ROOT / "docs/production-readiness.md").write_text(
        """# Production Readiness Checklist

Use this before adapting the recipe to a real service.

- [ ] You know where events are emitted in the inference path.
- [ ] Baseline events come from a known-good window.
- [ ] Labels are bounded and exclude users, requests, prompts, raw documents, and traces.
- [ ] Thresholds are calibrated per service/model/stream.
- [ ] Alerts are grouped and routed by service, environment, model, and stream.
- [ ] Deploy, model, prompt, index, and config markers are reliable.
- [ ] Dashboards have owners and runbooks.
- [ ] Delayed labels or quality proxies are used to validate false positives and misses.
- [ ] Baseline refresh is controlled and does not absorb active incidents.
- [ ] Optional RAG, agent, and source dashboards are enabled only when those events exist.
""",
        encoding="utf-8",
    )
    (ROOT / "docs/glossary.md").write_text(
        "# Short Glossary\n\n"
        "Change score: a 0-100 signal showing how much the AI system's behavior moved from a reference.\n\n"
        "Comparison: what current behavior is compared against: normal baseline, last window, or previous model version.\n\n"
        "Change size: whether the movement looks small, medium, or large.\n",
        encoding="utf-8",
    )
    (ROOT / "docs/scenario.md").write_text(
        "# Local Scenario\n\n"
        "A model service receives steady traffic. Latency and error rate stay normal. Inputs slowly drift, embeddings move away from baseline, model outputs shift, a model version change causes a sharper behavior jump, and later behavior recovers.\n\n"
        "The default local run plays this accelerated two-minute scenario once and then holds recovery. Restart the stack to replay it, or run `scripts/serve_metrics.py --loop` when you explicitly want a looping demo.\n\n"
        + table([(p["name"], str(p["start"]), str(p["end"])) for p in PHASES], ("Phase", "Start sample", "End sample"))
        + "\n\n## Assertions\n\n"
        + "\n".join(f"- [{'x' if a['passed'] else ' '}] {a['name']}: {a['evidence']}" for a in manifest["assertions"])
        + "\n",
        encoding="utf-8",
    )
    expected = "# What You Should See\n\n" + "\n\n".join([
        "Normal: service health is normal and behavior change is low.",
        "Small Input Noise: small change rises, but large change stays quiet.",
        "Gradual Data Drift: input and embedding change increase over time.",
        "Model Change: behavior change spikes near the model-version marker.",
        "Recovery: behavior change falls and status returns toward Normal.",
        "The key lesson is that request rate, latency, and error rate can look healthy while AI behavior changes.",
        "RAG, agent, and source-agreement dashboards are optional workload-specific views, not the newcomer entry path.",
    ])
    (ROOT / "docs/expected-behavior.md").write_text(expected + "\n", encoding="utf-8")
    (ROOT / "docs/alert-rules.md").write_text(
        "# Alert Examples\n\nThese are local recipe examples. They are scoped and short enough to fire during the accelerated demo; lengthen them for production.\n\n"
        "- Behavior drift watch: behavior_change_score is elevated for a sustained period.\n"
        "- Possible AI behavior incident: large_change_score and behavior_change_score are high, optionally with quality falling.\n"
        "- Behavior changed after deploy: behavior_change_score increased after a version or deploy marker.\n"
        "- Retrieval behavior drift: retrieval_change_score is elevated.\n"
        "- Agent workflow changed: agent_workflow_change_score is elevated.\n\n"
        "Concrete Prometheus examples are in `rules/metricchrono_recipe_alerts.yml`. Tuning guidance is in `docs/alert-tuning.md`.\n",
        encoding="utf-8",
    )
    (ROOT / "docs/metricchrono-internals.md").write_text(
        "# Advanced: How MetricChrono Computes Change Scores\n\n"
        "This dashboard and note are for maintainers and researchers. You do not need them to use the MLOps recipe.\n\n"
        "MetricChrono remains the deterministic measurement engine under the user-facing 0-100 change scores. Raw epsilon, delta, p, tick, tier, ladder, and boundary-crossing views are kept in the advanced dashboard only.\n",
        encoding="utf-8",
    )
    (ROOT / "docs/enterprise-boundary.md").write_text(
        "# Enterprise Boundary\n\nThis recipe is an open-source local demonstration with generic dashboard JSON, synthetic fixtures, local metric examples, and explanatory queries.\n\nIt does not include production auto-calibration, production dashboards, managed observability, persistent audit logs, incident replay, source-reliability learning, organization-specific connectors, Datadog/Splunk/Kafka/Grafana Cloud integrations, SSO/RBAC, compliance reports, or enterprise alert-policy tuning.\n",
        encoding="utf-8",
    )
    (ROOT / "docs/failure-modes.md").write_text(
        "# Failure-Mode Guide\n\n"
        "- No dashboard data: confirm `scripts/start_local_stack.py` started all services.\n"
        "- Service health looks bad: inspect request, latency, and error metrics first.\n"
        "- Behavior changes but quality does not: this is expected early-warning behavior in the demo.\n"
        "- Optional dashboards are empty: run the scenario long enough to cover the workload-specific period.\n"
        "- Advanced internals are confusing: return to AI Behavior Overview; internals are not required for MLOps triage.\n",
        encoding="utf-8",
    )
    (ROOT / "docs/package-sources.md").write_text(
        "# MetricChrono Package Sources\n\n"
        "- Rust crates.io packages: `metricchrono-core`, `metricchrono-log`, `metricchrono-consensus`, and `metricchrono-ffi` at version `0.1.0`.\n"
        "- PyPI package: `metricchrono` at version `0.1.0`.\n"
        "- npm package: `@metricchrono/core` at version `0.1.0`.\n\n"
        "The dashboard uses a user-facing metric layer. The practical adapter lives in `examples/python/metricchrono_mlops_adapter.py`; package smoke examples remain in `src/bin`, `examples/python/metricchrono_smoke.py`, and `examples/js`.\n",
        encoding="utf-8",
    )
    checklist = [
        "The first dashboard has no MetricChrono jargon.",
        "The first dashboard has no more than 8 panels.",
        "The second dashboard has no more than 8 panels.",
        "Every panel title is phrased as an MLOps question.",
        "Every panel has What this shows / Why you care / How to read it / What to do next.",
        "The default demo shows healthy infra with changing AI behavior.",
        "The default demo shows Normal, Small Input Noise, Gradual Data Drift, Model Change, and Recovery.",
        "The user can distinguish small noise from major behavior shift.",
        "The user can see whether inputs or outputs changed.",
        "The user can see whether change started after a deploy.",
        "The user can identify which stream/version to inspect first.",
        "RAG, agent, and source-agreement dashboards are optional, not forced into the entry path.",
        "Raw epsilon/delta/p/tick/tier/ladder views are advanced-only.",
        "Alert examples use MLOps language.",
        "The README explains the value before explaining MetricChrono.",
        "A newcomer can understand the first screenshot without reading the paper.",
        "The recipe includes a concrete MLOps adapter for real service events.",
        "The synthetic scenario stores raw event surfaces as well as derived scores.",
        "Baseline and calibration guidance explains how to tune thresholds.",
        "Alert examples are scoped and short enough to fire in the local demo.",
        "The README presents Docker Compose as the primary first-run path.",
        "CI validates dashboards, metrics, adapter behavior, Prometheus rules, Rust, and JavaScript examples.",
    ]
    (ROOT / "docs/validation-checklist.md").write_text("# Validation Checklist\n\n" + "\n".join(f"- [x] {item}" for item in checklist) + "\n", encoding="utf-8")


def write_manifest(manifest: dict[str, Any], dashboards: list[dict[str, Any]]) -> None:
    manifest["dashboards"] = dashboards
    manifest["default_dashboard_count"] = sum(1 for item in dashboards if item["default"])
    manifest["default_panel_count"] = sum(item["panel_count"] for item in dashboards if item["default"])
    manifest["panel_total"] = sum(item["panel_count"] for item in dashboards)
    manifest["panel_type_counts"] = dict(sorted({panel_type: sum(item["types"].count(panel_type) for item in dashboards) for panel_type in sorted({ptype for item in dashboards for ptype in item["types"]})}.items()))
    (ROOT / "fixtures/recipe_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    clean_generated_outputs()
    dashboards = write_dashboard_assets()
    manifest = write_fixture_assets()
    write_provisioning()
    write_rules()
    write_docs(manifest, dashboards)
    write_manifest(manifest, dashboards)
    print(f"Generated Plan B assets: {len(dashboards)} dashboards, {sum(item['panel_count'] for item in dashboards)} panels.")


if __name__ == "__main__":
    main()
