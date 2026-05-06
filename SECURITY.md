# Security

This recipe is a local observability example. Do not put secrets, prompts, raw
queries, request IDs, user IDs, document IDs, traces, or personal data in metric
labels.

If you adapt the recipe for production:

- keep MetricChrono metric labels bounded,
- store raw examples in logs or traces with your normal access controls,
- review Grafana dashboard access before exposing it broadly,
- route alerts through your existing incident system,
- do not auto-refresh baselines through active incidents.

For vulnerabilities in this recipe, open a private security advisory or contact
the repository maintainers through the normal project channel.
