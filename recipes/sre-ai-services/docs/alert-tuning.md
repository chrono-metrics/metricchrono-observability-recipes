# Alert Tuning

These alerts are examples, not production-ready thresholds.

Hard rule: no default alert pages solely because behavior-change is high.

Behavior-change alone is watch evidence by default. It can become incident-level only when combined with configured user impact, quality degradation, severe deploy correlation, or production policy.

Use minimum traffic volume and baseline freshness gates before routing behavior alerts. Tune by service, environment, model, workload, stream, and traffic role.
