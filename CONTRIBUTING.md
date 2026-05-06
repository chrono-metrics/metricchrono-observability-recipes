# Contributing

This repository is a recipe, so changes should improve one of these paths:

- make MetricChrono easier to plug into an existing MLOps monitoring flow,
- make dashboard interpretation clearer,
- improve baseline, calibration, alert, or production guidance,
- keep the local scenario deterministic and reproducible.

Before opening a pull request, run:

```bash
python3 scripts/generate_assets.py
python3 scripts/capture_grafana_screenshots.py
python3 scripts/validate_recipe.py
python3 scripts/smoke_mlops_adapter.py
python3 scripts/smoke_alert_windows.py
python3 -m unittest discover -s tests
promtool check config prometheus/prometheus.yml
promtool check rules rules/metricchrono_recipe_alerts.yml
```

Dashboard changes must preserve the Plan B vocabulary firewall: the entry dashboard should speak in MLOps language, not MetricChrono internals.
