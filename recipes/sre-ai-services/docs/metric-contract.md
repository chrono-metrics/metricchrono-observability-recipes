# SRE-Facing Metric Contract

Default dashboards use operational categories: golden signals, SLO and burn, AI behavior evidence, dependency/provider health, and release correlation.

## Stable Labels

- `service`
- `environment`
- `model`
- `model_version`
- `workload`
- `stream`
- `traffic_role`
- `comparison`
- `change_size`
- `component`
- `provider`
- `dependency`
- `error_class`
- `reason`
- `window`
- `state`
- `severity`
- `scenario_phase`

## Forbidden Labels

- `prompt`
- `request_id`
- `trace_id`
- `session_id`
- `user_id`
- `raw_text`
- `document_id`
- `tool_call_id`
- `span_id`
- `error_text`

Raw prompts, request IDs, trace IDs, user IDs, session IDs, raw text, tool call IDs, span IDs, document IDs, and error text belong in logs, traces, exemplars, or review systems, not Prometheus labels.

## Category A - Golden Signals

Required metrics are request count, error count, request duration histogram, and saturation/queue/capacity signals:

- `metricchrono_sre_ai_requests_total`
- `metricchrono_sre_ai_errors_total`
- `metricchrono_sre_ai_request_duration_seconds`
- `metricchrono_sre_ai_inflight_requests`
- `metricchrono_sre_ai_queue_depth`
- `metricchrono_sre_ai_saturation_ratio`

## Category B - SLO And Burn

Behavior-change is not counted as a bad event by default.

- `metricchrono_sre_ai_slo_good_events_total`
- `metricchrono_sre_ai_slo_bad_events_total`
- `metricchrono_sre_ai_slo_burn_rate`
- `metricchrono_sre_ai_latency_violations_total`
- `metricchrono_sre_ai_availability_failures_total`

## Category C - AI Behavior Evidence

- `metricchrono_sre_ai_behavior_change_score`
- `metricchrono_sre_ai_behavior_component_score`
- `metricchrono_sre_ai_change_score_by_size`
- `metricchrono_sre_ai_behavior_state_code`
- `metricchrono_sre_ai_baseline_age_seconds`
- `metricchrono_sre_ai_sample_volume`
- `metricchrono_sre_ai_baseline_trust_state_code`

Component values include `input`, `embedding`, `output`, `retrieval`, `agent_workflow`, and `source_disagreement`. Change size values are `small`, `medium`, and `large`.

## Category D - Dependency / Provider Health

- `metricchrono_sre_ai_provider_requests_total`
- `metricchrono_sre_ai_provider_errors_total`
- `metricchrono_sre_ai_provider_duration_seconds`
- `metricchrono_sre_ai_provider_rate_limits_total`
- `metricchrono_sre_ai_token_usage_total`
- `metricchrono_sre_ai_retrieval_duration_seconds`
- `metricchrono_sre_ai_vector_db_duration_seconds`
- `metricchrono_sre_ai_tool_call_duration_seconds`

## Category E - Release Correlation

- `metricchrono_sre_ai_app_version_active`
- `metricchrono_sre_ai_model_version_active`
- `metricchrono_sre_ai_prompt_version_active`
- `metricchrono_sre_ai_index_version_active`
- `metricchrono_sre_ai_config_version_active`
- `metricchrono_sre_ai_rollout_state_code`
- `metricchrono_sre_ai_previous_version_behavior_change_score`
- `metricchrono_sre_ai_canary_behavior_difference_score`

Comparisons used by dashboards include `known_good_baseline`, `previous_version`, `stable_vs_canary`, `before_vs_after_deploy`, `dependency_vs_service`, `quality_proxy`, `minimum_traffic_volume`, `baseline_freshness_policy`, and `capacity_limit`.
