"""Minimal MLOps adapter for turning model-service events into recipe metrics.

This module uses MetricChrono tick vectors as the score path while keeping the
user-facing dashboard metrics in MLOps language. Install `requirements.txt` in
production; the local recipe keeps a formula-compatible fallback so the adapter
remains readable in constrained environments.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

try:
    import metricchrono as mc
except ModuleNotFoundError:  # The Docker demo stays dependency-light.
    mc = None


STREAM_KEYS = ("behavior", "input", "embedding", "output", "retrieval", "agent")
LADDER_CONFIG = [
    (0.03, 0.05, 0.5, 1.0),
    (0.08, 0.12, 0.5, 1.0),
    (0.18, 0.27, 0.5, 1.0),
    (0.35, 0.55, 0.5, 1.0),
    (0.70, 1.05, 0.5, 1.0),
    (1.20, 1.80, 0.5, 1.0),
]
INCIDENT_TICK_PRESSURE = {
    "input": 78.0,
    "embedding": 3.0,
    "output": 1.8,
    "retrieval": 22.0,
    "agent": 14.0,
    "source_disagreement": 5.4,
}
SCORE_STREAMS = {
    "behavior": ("metricchrono_ai_behavior_change_score", "model_service", "overall.behavior"),
    "input": ("metricchrono_ai_input_change_score", "inputs", "input.features"),
    "embedding": ("metricchrono_ai_embedding_change_score", "embeddings", "embedding.vector_mean"),
    "output": ("metricchrono_ai_output_change_score", "outputs", "model.output_distribution"),
    "retrieval": ("metricchrono_ai_retrieval_change_score", "retrieval", "rag.retrieval"),
    "agent": ("metricchrono_ai_agent_workflow_change_score", "agent_workflow", "agent.workflow"),
}
BEHAVIOR_BUCKETS = [1, 3, 5, 10, 20, 35, 50, 70, 90, 100]
LATENCY_BUCKETS = [0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
CONTRACT_METRICS = {
    "metricchrono_ai_requests_total": ("counter", "Model-service request count."),
    "metricchrono_ai_errors_total": ("counter", "Model-service error count."),
    "metricchrono_ai_request_duration_seconds": ("histogram", "Model-service latency."),
    "metricchrono_ai_behavior_change_score": ("gauge", "Overall AI behavior change, normalized to 0-100."),
    "metricchrono_ai_input_change_score": ("gauge", "Input, feature, and embedding change from reference."),
    "metricchrono_ai_embedding_change_score": ("gauge", "Embedding movement from normal baseline."),
    "metricchrono_ai_output_change_score": ("gauge", "Prediction or output distribution change from reference."),
    "metricchrono_ai_retrieval_change_score": ("gauge", "RAG retrieval behavior change."),
    "metricchrono_ai_agent_workflow_change_score": ("gauge", "Agent tool or step workflow change."),
    "metricchrono_ai_change_events_total": ("counter", "Count of meaningful AI behavior change events."),
    "metricchrono_ai_change_score_by_size": ("gauge", "Change score split into small, medium, and large movement."),
    "metricchrono_ai_drift_state": ("gauge", "0=normal, 1=watch, 2=drift, 3=incident."),
    "metricchrono_ai_behavior_distance": ("histogram", "Behavior difference distribution for debug views."),
    "metricchrono_ai_quality_proxy": ("gauge", "Delayed quality or feedback proxy."),
    "metricchrono_ai_baseline_age_seconds": ("gauge", "Age of the normal baseline reference."),
    "metricchrono_ai_source_disagreement_score": ("gauge", "Source or ensemble disagreement score."),
    "metricchrono_ai_source_missing_total": ("counter", "Missing-source events."),
    "metricchrono_ai_model_version_active": ("gauge", "One when a model version is active."),
    "metricchrono_ai_scenario_state": ("gauge", "One for the active local scenario phase."),
    "metricchrono_ai_inspection_candidate": ("gauge", "Ranked next-step candidate for triage tables."),
}


@dataclass(frozen=True)
class MLBehaviorEvent:
    service: str
    environment: str
    model: str
    model_version: str
    phase: str
    latency_seconds: float
    error: bool
    input_features: dict[str, float]
    embedding: list[float]
    output_distribution: dict[str, float]
    retrieved_ids: list[str]
    agent_steps: list[str]
    source_scores: dict[str, float]
    quality_proxy: float


@dataclass(frozen=True)
class ScoreSnapshot:
    event: MLBehaviorEvent
    distances: dict[str, float]
    tick_vectors: dict[str, list[float]]
    scores: dict[str, float]
    drift_state: int

    def to_json(self) -> dict[str, object]:
        return {
            "phase": self.event.phase,
            "model_version": self.event.model_version,
            "distances": self.distances,
            "tick_vectors": self.tick_vectors,
            "scores": self.scores,
            "drift_state": self.drift_state,
            "quality_proxy": self.event.quality_proxy,
        }


@dataclass(frozen=True)
class BaselineProfile:
    input_mean: dict[str, float]
    input_std: dict[str, float]
    embedding_centroid: list[float]
    output_distribution: dict[str, float]
    retrieval_set: set[str]
    agent_path: list[str]
    source_mean: float
    normal_p95: dict[str, float]

    @classmethod
    def from_events(cls, events: list[MLBehaviorEvent]) -> "BaselineProfile":
        if not events:
            raise ValueError("baseline requires at least one event")

        feature_names = sorted({name for event in events for name in event.input_features})
        input_mean = {
            name: sum(event.input_features.get(name, 0.0) for event in events) / len(events)
            for name in feature_names
        }
        input_std = {}
        for name in feature_names:
            variance = sum((event.input_features.get(name, 0.0) - input_mean[name]) ** 2 for event in events) / len(events)
            input_std[name] = max(math.sqrt(variance), 0.05)

        dims = max(len(event.embedding) for event in events)
        embedding_centroid = [
            sum((event.embedding[idx] if idx < len(event.embedding) else 0.0) for event in events) / len(events)
            for idx in range(dims)
        ]

        outputs = sorted({name for event in events for name in event.output_distribution})
        output_distribution = normalize_distribution({
            name: sum(event.output_distribution.get(name, 0.0) for event in events) / len(events)
            for name in outputs
        })

        retrieval_counts: Counter[str] = Counter()
        for event in events:
            retrieval_counts.update(event.retrieved_ids)
        retrieval_set = {doc for doc, _ in retrieval_counts.most_common(6)}

        path_counts: Counter[tuple[str, ...]] = Counter(tuple(event.agent_steps) for event in events)
        agent_path = list(path_counts.most_common(1)[0][0])

        source_values = [score for event in events for score in event.source_scores.values()]
        source_mean = sum(source_values) / len(source_values) if source_values else 0.0

        provisional = cls(
            input_mean=input_mean,
            input_std=input_std,
            embedding_centroid=embedding_centroid,
            output_distribution=output_distribution,
            retrieval_set=retrieval_set,
            agent_path=agent_path,
            source_mean=source_mean,
            normal_p95={},
        )
        baseline_distances = [event_distances(event, provisional) for event in events]
        normal_p95 = {
            key: percentile([metricchrono_tick_pressure(metricchrono_tick_vector(distances[key])) for distances in baseline_distances], 95)
            for key in ("input", "embedding", "output", "retrieval", "agent", "source_disagreement")
        }
        return cls(
            input_mean=input_mean,
            input_std=input_std,
            embedding_centroid=embedding_centroid,
            output_distribution=output_distribution,
            retrieval_set=retrieval_set,
            agent_path=agent_path,
            source_mean=source_mean,
            normal_p95=normal_p95,
        )


class BehaviorMonitor:
    """Compute user-facing behavior-change scores from bounded ML events."""

    def __init__(self, baseline: BaselineProfile) -> None:
        self.baseline = baseline

    @classmethod
    def from_baseline_events(cls, events: list[MLBehaviorEvent]) -> "BehaviorMonitor":
        return cls(BaselineProfile.from_events(events))

    def observe(self, event: MLBehaviorEvent) -> ScoreSnapshot:
        distances = event_distances(event, self.baseline)
        tick_vectors = {key: metricchrono_tick_vector(value) for key, value in distances.items()}
        scores = {
            key: score_tick_vector(tick_vectors[key], self.baseline.normal_p95[key], INCIDENT_TICK_PRESSURE[key])
            for key in ("input", "embedding", "output", "retrieval", "agent", "source_disagreement")
        }
        scores["behavior"] = round(
            max(
                scores["embedding"] * 0.92,
                scores["input"] * 0.70,
                scores["output"],
                scores["retrieval"] * 0.70,
                scores["agent"] * 0.65,
            ),
            6,
        )
        return ScoreSnapshot(
            event=event,
            distances=distances,
            tick_vectors=tick_vectors,
            scores=scores,
            drift_state=drift_state(scores["behavior"]),
        )


def event_distances(event: MLBehaviorEvent, baseline: BaselineProfile) -> dict[str, float]:
    return {
        "input": standardized_distance(event.input_features, baseline.input_mean, baseline.input_std),
        "embedding": cosine_distance(event.embedding, baseline.embedding_centroid),
        "output": jensen_shannon_distance(event.output_distribution, baseline.output_distribution),
        "retrieval": jaccard_distance(set(event.retrieved_ids), baseline.retrieval_set),
        "agent": edit_distance(event.agent_steps, baseline.agent_path) / max(len(event.agent_steps), len(baseline.agent_path), 1),
        "source_disagreement": source_disagreement(event.source_scores, baseline.source_mean),
    }


def score_tick_vector(tick_vector: list[float], normal_p95: float, incident_floor: float) -> float:
    """Map a MetricChrono tick vector into the recipe's 0-100 score."""

    pressure = metricchrono_tick_pressure(tick_vector)
    incident_pressure = max(normal_p95 * 10.0, incident_floor)
    return round(max(0.0, min(100.0, 100.0 * pressure / incident_pressure)), 6)


def metricchrono_tick_pressure(tick_vector: list[float]) -> float:
    return sum((index + 1) * value for index, value in enumerate(tick_vector))


def metricchrono_tick_vector(distance: float) -> list[float]:
    """Return the MetricChrono ladder vector for a scalar distance."""

    if mc is None:
        return fallback_tick_vector(distance)
    ladder = mc.geometric_ladder(0.03, 0.05, 2.6, 6, 0.5, 1.0)
    return [round(value, 6) for value in mc.ladder_distance(distance, ladder)]


def fallback_tick_vector(distance: float) -> list[float]:
    """Pure-Python equivalent of the public MetricChrono ladder formula."""

    vector = []
    for epsilon, delta, power, epsilon_ref in LADDER_CONFIG:
        if distance < epsilon:
            vector.append(0.0)
        else:
            value = ((epsilon / epsilon_ref) ** power) * math.ceil(distance / delta)
            vector.append(round(value, 6))
    return vector


def drift_state(score: float) -> int:
    if score >= 82:
        return 3
    if score >= 55:
        return 2
    if score >= 25:
        return 1
    return 0


def emit_prometheus_metrics(
    snapshot: ScoreSnapshot,
    baseline_age_seconds: float = 0.0,
    *,
    request_count: float = 1.0,
    error_count: float | None = None,
    comparison_scores: dict[str, dict[str, float]] | None = None,
    active_model_versions: Iterable[str] | None = None,
    missing_sources: Iterable[str] = (),
) -> str:
    """Render the recipe's Prometheus metric contract for one observed event.

    Production services should usually set these through their Prometheus
    client library. The text bridge is kept complete so teams can copy the
    metric and label contract without first reading the dashboard JSON.
    """

    common = {
        "service": snapshot.event.service,
        "environment": snapshot.event.environment,
        "model": snapshot.event.model,
        "model_version": snapshot.event.model_version,
    }
    lines: list[str] = []
    for name, (metric_type, help_text) in CONTRACT_METRICS.items():
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {metric_type}")

    health_labels = {
        **common,
        "workload": "model_service",
        "stream": "service.health",
        "comparison": "normal_baseline",
    }
    append_metric(lines, "metricchrono_ai_requests_total", health_labels, request_count)
    append_metric(
        lines,
        "metricchrono_ai_errors_total",
        health_labels,
        float(snapshot.event.error) if error_count is None else error_count,
    )
    append_histogram(
        lines,
        "metricchrono_ai_request_duration_seconds",
        health_labels,
        snapshot.event.latency_seconds,
        LATENCY_BUCKETS,
        count=request_count,
    )
    append_metric(lines, "metricchrono_ai_baseline_age_seconds", health_labels, baseline_age_seconds)

    quality_labels = {
        **common,
        "workload": "model_service",
        "stream": "quality.proxy",
        "comparison": "normal_baseline",
    }
    append_metric(lines, "metricchrono_ai_quality_proxy", quality_labels, snapshot.event.quality_proxy)

    scenario_labels = {
        **common,
        "workload": "model_service",
        "stream": "scenario.phase",
        "comparison": "normal_baseline",
        "phase": snapshot.event.phase,
    }
    append_metric(lines, "metricchrono_ai_scenario_state", scenario_labels, 1.0)

    for version in active_model_versions or (snapshot.event.model_version,):
        version_labels = {
            **common,
            "model_version": version,
            "workload": "model_service",
            "stream": "deploy.marker",
            "comparison": "previous_model_version",
        }
        append_metric(lines, "metricchrono_ai_model_version_active", version_labels, 1.0 if version == snapshot.event.model_version else 0.0)

    comparisons = {"normal_baseline": complete_score_map(snapshot.scores, snapshot.scores)}
    if comparison_scores:
        for comparison, scores in comparison_scores.items():
            comparisons[comparison] = complete_score_map(scores, snapshot.scores)

    for comparison, scores in comparisons.items():
        for key, (metric, workload, stream) in SCORE_STREAMS.items():
            metric_labels = {
                **common,
                "workload": workload,
                "stream": stream,
                "comparison": comparison,
            }
            score = scores[key]
            append_metric(lines, metric, metric_labels, score)
            append_metric(lines, "metricchrono_ai_drift_state", metric_labels, drift_state(score))
            append_histogram(lines, "metricchrono_ai_behavior_distance", metric_labels, score, BEHAVIOR_BUCKETS)
            for size, value in size_scores(score).items():
                size_labels = {**metric_labels, "change_size": size}
                append_metric(lines, "metricchrono_ai_change_score_by_size", size_labels, value)
                append_metric(
                    lines,
                    "metricchrono_ai_change_events_total",
                    size_labels,
                    1.0 if value > 18.0 and comparison == "normal_baseline" else 0.0,
                )

    source_rows = source_disagreement_scores(snapshot.event.source_scores)
    missing = set(missing_sources)
    if not source_rows and not missing:
        source_rows = {"not_applicable": 0.0}
    for source, score in source_rows.items():
        labels = {
            **common,
            "workload": "source_agreement",
            "stream": source,
            "comparison": "normal_baseline",
        }
        append_metric(lines, "metricchrono_ai_source_disagreement_score", labels, score)
        append_metric(lines, "metricchrono_ai_drift_state", labels, drift_state(score))
        append_metric(lines, "metricchrono_ai_source_missing_total", labels, 1.0 if source in missing else 0.0)
        for size, value in size_scores(score).items():
            append_metric(lines, "metricchrono_ai_change_score_by_size", {**labels, "change_size": size}, value)
    for source in sorted(missing - set(source_rows)):
        labels = {
            **common,
            "workload": "source_agreement",
            "stream": source,
            "comparison": "normal_baseline",
        }
        append_metric(lines, "metricchrono_ai_source_missing_total", labels, 1.0)

    for rank, candidate in enumerate(inspection_candidates(snapshot.scores, comparisons), start=1):
        labels = {
            **common,
            "workload": candidate["workload"],
            "stream": candidate["stream"],
            "comparison": "normal_baseline",
            "rank": str(rank),
            "main_change": candidate["main_change"],
            "cause": candidate["cause"],
            "next_step": candidate["next_step"],
            "drift_state": str(drift_state(candidate["score"])),
        }
        append_metric(lines, "metricchrono_ai_inspection_candidate", labels, candidate["score"])

    return "\n".join(lines) + "\n"


def append_metric(lines: list[str], name: str, labels: dict[str, str], value: float) -> None:
    lines.append(f"{name}{prometheus_labels(labels)} {value:.6f}")


def append_histogram(
    lines: list[str],
    name: str,
    labels: dict[str, str],
    value: float,
    buckets: list[float],
    *,
    count: float = 1.0,
) -> None:
    for bucket in buckets:
        bucket_labels = {**labels, "le": str(bucket)}
        lines.append(f"{name}_bucket{prometheus_labels(bucket_labels)} {(count if value <= bucket else 0.0):.6f}")
    lines.append(f'{name}_bucket{prometheus_labels({**labels, "le": "+Inf"})} {count:.6f}')
    lines.append(f"{name}_sum{prometheus_labels(labels)} {value * count:.6f}")
    lines.append(f"{name}_count{prometheus_labels(labels)} {count:.6f}")


def complete_score_map(scores: dict[str, float], fallback: dict[str, float]) -> dict[str, float]:
    return {
        "behavior": clamp_score(scores.get("behavior", fallback["behavior"])),
        "input": clamp_score(scores.get("input", fallback["input"])),
        "embedding": clamp_score(scores.get("embedding", fallback["embedding"])),
        "output": clamp_score(scores.get("output", fallback["output"])),
        "retrieval": clamp_score(scores.get("retrieval", fallback["retrieval"])),
        "agent": clamp_score(scores.get("agent", fallback["agent"])),
        "source_disagreement": clamp_score(scores.get("source_disagreement", fallback["source_disagreement"])),
    }


def clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 6)


def size_scores(score: float) -> dict[str, float]:
    return {
        "small": clamp_score(min(score, 25.0)),
        "medium": clamp_score(max(min(score - 20.0, 45.0), 0.0)),
        "large": clamp_score(max(score - 55.0, 0.0)),
    }


def source_disagreement_scores(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    current_mean = sum(values.values()) / len(values)
    return {
        source: clamp_score(6.0 + abs(score - current_mean) * 260.0)
        for source, score in values.items()
    }


def inspection_candidates(scores: dict[str, float], comparisons: dict[str, dict[str, float]]) -> list[dict[str, float | str]]:
    previous_model = comparisons.get("previous_model_version", {})
    candidates: list[dict[str, float | str]] = [
        {"workload": "inputs", "stream": "input.features", "main_change": "inputs", "cause": "data_drift", "next_step": "inspect_inputs", "score": scores["input"]},
        {"workload": "embeddings", "stream": "embedding.vector_mean", "main_change": "embeddings", "cause": "data_drift", "next_step": "inspect_inputs", "score": scores["embedding"]},
        {"workload": "outputs", "stream": "model.output_distribution", "main_change": "outputs", "cause": "output_shift", "next_step": "inspect_outputs", "score": scores["output"]},
        {"workload": "retrieval", "stream": "rag.retrieval", "main_change": "retrieval", "cause": "retrieval_shift", "next_step": "check_retrieval", "score": scores["retrieval"]},
        {"workload": "agent_workflow", "stream": "agent.workflow", "main_change": "agent_workflow", "cause": "agent_workflow_shift", "next_step": "check_agent_trace", "score": scores["agent"]},
        {"workload": "model_service", "stream": "deploy.marker", "main_change": "version_change", "cause": "deploy_change", "next_step": "check_deploy", "score": previous_model.get("behavior", 0.0)},
        {"workload": "source_agreement", "stream": "source_disagreement", "main_change": "source_disagreement", "cause": "source_mismatch", "next_step": "inspect_inputs", "score": scores["source_disagreement"]},
    ]
    return sorted(candidates, key=lambda item: float(item["score"]), reverse=True)


def prometheus_labels(labels: dict[str, str]) -> str:
    return "{" + ",".join(f'{key}="{escape_label(value)}"' for key, value in sorted(labels.items())) + "}"


def escape_label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def standardized_distance(values: dict[str, float], mean: dict[str, float], std: dict[str, float]) -> float:
    if not mean:
        return 0.0
    total = 0.0
    for name, base in mean.items():
        total += ((values.get(name, 0.0) - base) / std[name]) ** 2
    return math.sqrt(total / len(mean))


def cosine_distance(values: list[float], reference: list[float]) -> float:
    dims = max(len(values), len(reference))
    left = values + [0.0] * (dims - len(values))
    right = reference + [0.0] * (dims - len(reference))
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - numerator / (left_norm * right_norm)))


def normalize_distribution(values: dict[str, float]) -> dict[str, float]:
    total = sum(max(value, 0.0) for value in values.values())
    if total == 0:
        return {name: 0.0 for name in values}
    return {name: max(value, 0.0) / total for name, value in values.items()}


def jensen_shannon_distance(left: dict[str, float], right: dict[str, float]) -> float:
    left = normalize_distribution(left)
    right = normalize_distribution(right)
    keys = sorted(set(left) | set(right))
    midpoint = {key: (left.get(key, 0.0) + right.get(key, 0.0)) / 2.0 for key in keys}
    return math.sqrt((kl_divergence(left, midpoint, keys) + kl_divergence(right, midpoint, keys)) / 2.0)


def kl_divergence(left: dict[str, float], right: dict[str, float], keys: Iterable[str]) -> float:
    total = 0.0
    for key in keys:
        value = left.get(key, 0.0)
        reference = right.get(key, 0.0)
        if value > 0 and reference > 0:
            total += value * math.log(value / reference)
    return total


def jaccard_distance(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    return 1.0 - len(left & right) / len(left | right)


def edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_value in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (0 if left_value == right_value else 1),
                )
            )
        previous = current
    return previous[-1]


def source_disagreement(values: dict[str, float], baseline_mean: float) -> float:
    if not values:
        return 0.0
    current_mean = sum(values.values()) / len(values)
    spread = math.sqrt(sum((value - current_mean) ** 2 for value in values.values()) / len(values))
    shift = abs(current_mean - baseline_mean)
    return spread + shift


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile_value / 100.0
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[int(index)]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def phase_for(index: int) -> str:
    if index <= 19:
        return "Normal"
    if index <= 39:
        return "Small Input Noise"
    if index <= 69:
        return "Gradual Data Drift"
    if index <= 84:
        return "Model Change"
    return "Recovery"


def phase_progress(index: int, start: int, end: int) -> float:
    return (index - start) / max(end - start, 1)


def build_demo_events(sample_count: int = 120) -> list[MLBehaviorEvent]:
    """Create deterministic, realistic-enough events for the local recipe."""

    events: list[MLBehaviorEvent] = []
    for index in range(sample_count):
        phase = phase_for(index)
        if phase == "Normal":
            drift = 0.0
            output_shift = 0.0
            retrieval_shift = 0
            agent_variant = 0
            model_version = "v1"
            quality = 98.0
        elif phase == "Small Input Noise":
            drift = 0.12 * math.sin(math.pi * phase_progress(index, 20, 39))
            output_shift = 0.02 * math.sin(math.pi * phase_progress(index, 20, 39))
            retrieval_shift = 0
            agent_variant = 0
            model_version = "v1"
            quality = 97.0
        elif phase == "Gradual Data Drift":
            progress = smoothstep(phase_progress(index, 40, 69))
            drift = 0.62 * progress
            output_shift = 0.24 * smoothstep(max((phase_progress(index, 40, 69) - 0.35) / 0.65, 0.0))
            retrieval_shift = 1 if progress > 0.35 else 0
            agent_variant = 0
            model_version = "v1"
            quality = 96.0 - 8.0 * smoothstep(max((phase_progress(index, 40, 69) - 0.45) / 0.55, 0.0))
        elif phase == "Model Change":
            progress = smoothstep(phase_progress(index, 70, 84))
            drift = 0.58 - 0.04 * progress
            output_shift = 0.48 - 0.05 * progress
            retrieval_shift = 2
            agent_variant = 1
            model_version = "v2"
            quality = 84.0 - 10.0 * progress
        else:
            progress = smoothstep(phase_progress(index, 85, 119))
            remaining = 1.0 - progress
            drift = 0.50 * remaining
            output_shift = 0.44 * remaining
            retrieval_shift = 1 if remaining > 0.45 else 0
            agent_variant = 1 if remaining > 0.35 else 0
            model_version = "v2"
            quality = 74.0 + 20.0 * progress

        events.append(
            MLBehaviorEvent(
                service="checkout-ai",
                environment="local",
                model="recommendation-ranker",
                model_version=model_version,
                phase=phase,
                latency_seconds=0.13 + (0.012 if phase == "Model Change" else 0.0),
                error=phase == "Model Change" and index in {74, 75},
                input_features={
                    "cart_value": 0.50 + 0.16 * drift,
                    "query_complexity": 0.30 + 0.28 * drift,
                    "price_sensitivity": 0.45 + 0.34 * drift,
                    "returning_user": 0.62 - 0.10 * drift,
                },
                embedding=[
                    0.20 + 0.30 * drift,
                    0.35 - 0.16 * drift,
                    0.15 + 0.24 * drift,
                    0.40 + 0.12 * drift,
                ],
                output_distribution=normalize_distribution(
                    {
                        "buy": 0.62 - 0.42 * output_shift,
                        "compare": 0.25 + 0.34 * output_shift,
                        "skip": 0.13 + 0.08 * output_shift,
                    }
                ),
                retrieved_ids=retrieval_docs(retrieval_shift),
                agent_steps=agent_steps(agent_variant),
                source_scores=source_scores_for(index, phase),
                quality_proxy=round(quality, 6),
            )
        )
    return events


def retrieval_docs(shift: int) -> list[str]:
    docs = ["pricing", "reviews", "shipping", "returns", "warranty", "availability"]
    if shift == 1:
        return ["pricing", "reviews", "discounts", "competitors", "warranty", "availability"]
    if shift >= 2:
        return ["discounts", "competitors", "outlet", "bundle", "shipping", "availability"]
    return docs


def agent_steps(variant: int) -> list[str]:
    if variant:
        return ["rank", "lookup_policy", "rerank", "respond"]
    return ["rank", "rerank", "respond"]


def source_scores_for(index: int, phase: str) -> dict[str, float]:
    if phase in {"Gradual Data Drift", "Model Change"} and 64 <= index <= 82:
        return {"source_a": 0.72, "source_b": 0.70, "source_c": 0.28}
    return {"source_a": 0.70, "source_b": 0.72, "source_c": 0.69}


def snapshots_for_events(events: list[MLBehaviorEvent], baseline_count: int = 20) -> list[ScoreSnapshot]:
    monitor = BehaviorMonitor.from_baseline_events(events[:baseline_count])
    return [monitor.observe(event) for event in events]


def write_events_jsonl(events: list[MLBehaviorEvent], path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.__dict__, sort_keys=True) + "\n")
