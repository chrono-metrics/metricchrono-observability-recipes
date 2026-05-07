# Alert Tuning

Alerts are examples, not production policy. Keep them conservative and route them to engineers who can inspect the suggested dashboard and source.

Tuning rules:
- Alert on sustained watch or investigate bands, not single small-change spikes.
- Include asset group, asset, subsystem, comparison, suggested dashboard, and next action.
- Suppress or reclassify state-mismatch alerts during planned state changes when the correct same-state baseline is active.
- Treat source disagreement as an inspection hint, not proof of a bad source.

See `../rules/industrial-alerts.yml` for example rules.
