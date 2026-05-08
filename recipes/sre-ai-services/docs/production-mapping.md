# Mapping This Recipe To Production Metrics

Keep the dashboard vocabulary and alert posture, then map each example metric to your existing telemetry source.

## Golden Signals

Map `metricchrono_sre_ai_requests_total`, `metricchrono_sre_ai_errors_total`, and `metricchrono_sre_ai_request_duration_seconds` to your HTTP, RPC, queue, or gateway metrics. Keep status and error class bounded.

## SLO And Burn

Prefer your production SLO pipeline for good events, bad events, burn rate, latency violations, and availability failures. Behavior-change should remain evidence unless your production SLI policy explicitly defines it as impact.

## Dependency / Provider Health

Map provider latency, errors, rate limits, token usage, retrieval latency, vector DB latency, tool-call latency, and cache hit ratio from OpenTelemetry, provider SDKs, gateway logs, or dependency exporters.

## Release Correlation

Emit active app version, model version, prompt version, retriever/index version, config version, and traffic role as bounded labels or state gauges. Keep raw commit SHAs and free-form deploy notes outside Prometheus labels if they create high cardinality.

## Behavior Evidence

Map behavior-change, component scores, source disagreement, baseline age, minimum traffic, and sample trust from your AI evaluation or behavior-monitoring pipeline. Do not copy demo thresholds into production without calibration.
