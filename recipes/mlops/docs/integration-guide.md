# Integration Guide

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
