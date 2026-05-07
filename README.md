# MetricChrono Observability Recipes

This repository contains publishable MetricChrono recipe packs. Each recipe lives under `recipes/<slug>/` with its own dashboards, docs, fixtures, examples, rules, and screenshots.

## Recipe Packs

- [MLOps / AI Observability](recipes/mlops/README.md)
- [Robotics Telemetry](recipes/robotics-telemetry/README.md)
- [Industrial Telemetry](recipes/industrial-telemetry/README.md)

Planned recipe families are reserved under `recipes/sre-ai-services/` and `recipes/agent-observability/`.

## Local Grafana Servers

The local demo uses independently runnable recipe servers. Shared Grafana/Prometheus plumbing is used where it helps, but robotics and industrial remain separate recipe packs with separate dashboards, docs, screenshots, alerts, examples, fixtures, and language.

| Recipe pack | Make command | npm equivalent | Default Grafana URL | Grafana folder |
| --- | --- | --- | --- | --- |
| MLOps / AI observability | `make mlops` | `npm run mlops:start` | `http://localhost:3000` | `MetricChrono MLOps Recipes` |
| Robotics telemetry | `make robotics` | `npm run robotics:start` | `http://localhost:3001` | `MetricChrono Robotics Recipes` |
| Industrial telemetry | `make industrial` | `npm run industrial:start` | `http://localhost:3001` | `MetricChrono Industrial Recipes` |
| Robotics + industrial together | `make telemetry` | `npm run telemetry:start` | `http://localhost:3001` | `MetricChrono Robotics / Industrial Recipes` |

The telemetry-family commands pick the next free Grafana port if `3001` is occupied. Starting `robotics`, `industrial`, or `telemetry` replaces the previous telemetry-family local stack while leaving the MLOps stack alone. Each start command prints the actual Grafana, Prometheus, metrics, folder, and dashboard URLs.

Stop local servers:

```bash
make stop
```

Docker Compose runs only the MLOps recipe:

```bash
docker compose up
```

## Maintainer Validation

```bash
make validate
make validate-ci
```

Regenerate the MLOps assets:

```bash
npm run mlops:generate
npm run mlops:capture
npm run mlops:validate
npm run mlops:live
```

Regenerate the robotics and industrial recipe packs:

```bash
npm run robotics:generate
npm run robotics:capture
npm run robotics:validate
npm run industrial:generate
npm run industrial:capture
npm run industrial:validate
```

Regenerate and capture the shared telemetry view:

```bash
npm run telemetry:generate
npm run telemetry:capture
npm run telemetry:validate
```
