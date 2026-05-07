# Contributing

This repository contains multiple recipe packs, so changes should improve one of these paths:

- make MetricChrono easier to plug into an existing MLOps monitoring flow,
- make robotics telemetry investigation clearer without industrial language,
- make industrial telemetry investigation clearer without robotics language,
- make dashboard interpretation clearer,
- improve baseline, calibration, alert, or production guidance,
- keep the local scenario deterministic and reproducible.

Before opening a pull request, run:

```bash
npm run validate:ci
```

For screenshot or generated asset changes, run the recipe-specific commands first:

```bash
npm run mlops:generate
npm run mlops:capture
npm run robotics:generate
npm run robotics:capture
npm run industrial:generate
npm run industrial:capture
npm run telemetry:capture
```

Dashboard changes must preserve the recipe vocabulary firewall: MLOps dashboards should speak in MLOps language, robotics dashboards should speak in robotics language, industrial dashboards should speak in industrial language, and default user-facing dashboards should not expose MetricChrono internals.
