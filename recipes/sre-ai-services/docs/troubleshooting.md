# Troubleshooting

If dashboards are empty, verify Prometheus is scraping the scenario endpoint and that dashboard variables match `checkout-ai`, `demo`, `assist-ranker`, and `support.answers`.

If behavior alerts fire during low traffic, check `metricchrono_sre_ai_low_traffic_flag` and `metricchrono_sre_ai_sample_volume`.

If behavior evidence looks suspicious, check baseline age, missing-source count, and whether the current workload matches the baseline.
