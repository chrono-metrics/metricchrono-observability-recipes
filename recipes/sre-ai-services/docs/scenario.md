# Local Scenario Guide

The synthetic scenario is deterministic and requires no real provider, vector DB, model endpoint, or traffic generator.

The default run plays once and holds recovery. Use `--loop` only for a repeating demo.

## Phases

1. Normal: traffic, latency, errors, saturation, dependencies, and behavior are normal.
2. Infrastructure / capacity issue: latency and saturation rise while behavior remains secondary.
3. Dependency/provider issue: provider latency, errors, or rate limits lead service impact.
4. Silent AI-behavior change: behavior rises while golden signals stay green.
5. Deploy-correlated behavior change: app/model/prompt/index/config changes before behavior movement.
6. Behavior + quality drop: behavior movement aligns with quality or business proxy degradation.
7. Stale baseline: baseline trust weakens behavior interpretation.
8. Low traffic: minimum traffic volume is not met.
9. Recovery: mitigation occurs and service-health and behavior evidence stabilize.

## Run

```bash
python3 run_scenario.py
```

The script writes `scenario-metrics.prom` for each phase. Phase snapshots are stored under `phase-metrics/`.
