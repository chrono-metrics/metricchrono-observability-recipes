# Alert Examples

These are local recipe examples. They are scoped and short enough to fire during the accelerated demo; lengthen them for production.

- Behavior drift watch: behavior_change_score is elevated for a sustained period.
- Possible AI behavior incident: large_change_score and behavior_change_score are high, optionally with quality falling.
- Behavior changed after deploy: behavior_change_score increased after a version or deploy marker.
- Retrieval behavior drift: retrieval_change_score is elevated.
- Agent workflow changed: agent_workflow_change_score is elevated.

Concrete Prometheus examples are in `rules/metricchrono_recipe_alerts.yml`. Tuning guidance is in `docs/alert-tuning.md`.
