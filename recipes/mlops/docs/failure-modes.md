# Failure-Mode Guide

- No dashboard data: confirm `npm run mlops:start` started all services.
- Service health looks bad: inspect request, latency, and error metrics first.
- Behavior changes but quality does not: this is expected early-warning behavior in the demo.
- Optional dashboards are empty: run the scenario long enough to cover the workload-specific period.
- Advanced internals are confusing: return to AI Behavior Overview; internals are not required for MLOps triage.
