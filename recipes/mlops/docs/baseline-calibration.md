# Baseline And Calibration Guide

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
