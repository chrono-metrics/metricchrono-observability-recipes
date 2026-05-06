# Advanced: MetricChrono Internals

This page is for maintainers, reviewers, and teams adapting the recipe to a real service. You do not need it for first-run dashboard triage.

Use it when you need to answer one question: why did this `0-100` behavior score move?

## Score Pipeline

The recipe keeps the user-facing dashboards in MLOps language, but the score path is deterministic:

```text
MLBehaviorEvent
  -> per-surface distance from the normal baseline
  -> MetricChrono tick vector
  -> weighted tick pressure
  -> calibrated 0-100 stream score
  -> aggregate behavior score
  -> Prometheus metric
  -> Grafana panel or alert
```

The reference implementation is `examples/python/metricchrono_mlops_adapter.py`.

## Event Surfaces

Each observed request or short aggregate window becomes an `MLBehaviorEvent`. The adapter compares bounded, label-safe fields against a normal baseline:

| Surface | Event field | Distance function | Why it matters |
| --- | --- | --- | --- |
| Inputs | `input_features` | standardized distance | Catches feature and traffic-mix movement. |
| Embeddings | `embedding` | cosine distance | Catches semantic movement in prompt, query, or feature space. |
| Outputs | `output_distribution` | Jensen-Shannon distance | Catches prediction or policy distribution shifts. |
| Retrieval | `retrieved_ids` | Jaccard distance | Catches RAG context movement. |
| Agent workflow | `agent_steps` | normalized edit distance | Catches tool or workflow changes. |
| Source agreement | `source_scores` | spread plus baseline shift | Catches ensemble, judge, or source disagreement. |

Classifier services can leave `retrieved_ids`, `agent_steps`, and `source_scores` empty. The adapter treats missing optional surfaces as zero movement instead of crashing.

## MetricChrono Tick Vectors

The scalar distance for each surface is converted into a MetricChrono tick vector with `metricchrono_tick_vector(...)`.

The vector exists to separate tiny jitter from meaningful movement. A small distance may activate no tiers. Larger movement activates progressively stronger tiers. The dashboard does not expose those raw tiers by default because operators usually need the answer, not the mechanism.

The local adapter includes a formula-compatible fallback so the recipe stays readable in constrained environments. Production services should install `requirements.txt` so the public `metricchrono` package provides the tick-vector implementation.

## From Tick Vector To Score

The adapter turns each tick vector into a stream score:

```text
tick pressure = sum((tier_index + 1) * tick_value)
incident pressure = max(normal_baseline_p95 * 10, stream_incident_floor)
stream score = clamp(100 * tick_pressure / incident_pressure, 0, 100)
```

The baseline p95 comes from the known-good baseline window. The incident floor prevents naturally quiet streams from becoming too sensitive just because their baseline variance is near zero.

Each stream has its own floor because input features, embeddings, output distributions, retrieval sets, agent paths, and source scores have different normal variance.

## Aggregate Behavior Score

The overall behavior score is intentionally conservative. It uses the strongest meaningful stream movement rather than averaging everything away:

```text
behavior = max(
  embedding_score * 0.92,
  input_score * 0.70,
  output_score,
  retrieval_score * 0.70,
  agent_score * 0.65,
)
```

This makes a deploy-induced output shift visible even if service health is normal, while still letting the investigation dashboard show which stream moved.

## Prometheus Mapping

`emit_prometheus_metrics(...)` renders the user-facing metric contract for one snapshot. The most important metrics are:

| Metric | Meaning |
| --- | --- |
| `metricchrono_ai_behavior_change_score` | Overall behavior movement from the selected comparison. |
| `metricchrono_ai_input_change_score` | Input and feature movement. |
| `metricchrono_ai_embedding_change_score` | Embedding movement. |
| `metricchrono_ai_output_change_score` | Output distribution movement. |
| `metricchrono_ai_retrieval_change_score` | Retrieval result movement. |
| `metricchrono_ai_agent_workflow_change_score` | Agent step movement. |
| `metricchrono_ai_change_score_by_size` | Small, medium, and large movement split. |
| `metricchrono_ai_drift_state` | `0=normal`, `1=watch`, `2=drift`, `3=incident`. |
| `metricchrono_ai_inspection_candidate` | Bounded triage hint for table panels. |

The complete metric list is in `docs/metric-contract.md`.

## Advanced Dashboard

The `Advanced: MetricChrono Internals` dashboard is for implementation checks:

- Confirm raw tick values are nonzero when a stream score rises.
- Confirm configured ladder parameters match `fixtures/metricchrono-ladder.json`.
- Confirm boundary-crossing counters move during the synthetic scenario.
- Confirm the golden-vector smoke metric remains healthy.

Do not use the advanced dashboard as the on-call entry point. Start with `AI Behavior Overview`, then use `Drift Investigation`. Open the internals dashboard only when the score itself looks suspicious.

## Debug Checklist

When a score surprises you:

1. Check `fixtures/synthetic_streams/scenario_series.json` or your captured events to confirm the raw event surface changed.
2. Check `ScoreSnapshot.distances` to see which distance moved.
3. Check `ScoreSnapshot.tick_vectors` to see whether MetricChrono converted the movement into tick pressure.
4. Check `BaselineProfile.normal_p95` and the stream incident floor if the score feels too sensitive or too quiet.
5. Check the Prometheus labels in `docs/metric-contract.md` before changing dashboards or alerts.

## Boundaries

MetricChrono measures deterministic movement from a reference. It does not prove root cause, replace delayed labels, or decide incident policy. The recipe deliberately turns internals into bounded MLOps metrics so production users can triage behavior change without learning the raw tick model first.
