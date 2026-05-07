# User-Facing Metric Contract

The default dashboards query user-facing MLOps metrics derived from bounded model-service events. Raw MetricChrono internals are advanced-only.

Stable labels: `service`, `environment`, `model`, `model_version`, `stream`, `workload`, `comparison`, `change_size`.

The scenario-state helper also uses bounded `phase` labels.

The triage-table helper metric also uses bounded enum labels: `rank`, `main_change`, `cause`, `next_step`, and `drift_state`. Keep those enums small and controlled; do not put prompts, request IDs, document IDs, or free-form messages in labels.

Allowed `comparison` values: `normal_baseline`, `last_window`, `previous_model_version`, `shadow_model`.

Allowed `change_size` values: `small`, `medium`, `large`.

Forbidden high-cardinality labels: `document_id, email, prompt, raw_query, raw_text, request_id, session_id, span_id, trace_id, user_id`.

| Metric | Type | Meaning |
| --- | --- | --- |
| metricchrono_ai_requests_total | Counter | Synthetic model-service request count. |
| metricchrono_ai_errors_total | Counter | Synthetic model-service error count. |
| metricchrono_ai_request_duration_seconds | Histogram | Synthetic model-service latency. |
| metricchrono_ai_behavior_change_score | Gauge | Overall AI behavior change, normalized to 0-100. |
| metricchrono_ai_input_change_score | Gauge | Input, feature, and embedding change from reference. |
| metricchrono_ai_embedding_change_score | Gauge | Embedding movement from normal baseline. |
| metricchrono_ai_output_change_score | Gauge | Prediction or output distribution change from reference. |
| metricchrono_ai_retrieval_change_score | Gauge | RAG retrieval behavior change. |
| metricchrono_ai_agent_workflow_change_score | Gauge | Agent tool or step workflow change. |
| metricchrono_ai_change_events_total | Counter | Count of meaningful AI behavior change events. |
| metricchrono_ai_change_score_by_size | Gauge | Change score split into small, medium, and large movement. |
| metricchrono_ai_drift_state | Gauge | 0=normal, 1=watch, 2=drift, 3=incident. |
| metricchrono_ai_behavior_distance | Histogram | Raw behavior difference distribution for debug views. |
| metricchrono_ai_quality_proxy | Gauge | Synthetic delayed quality or feedback proxy. |
| metricchrono_ai_baseline_age_seconds | Gauge | Age of the normal baseline reference. |
| metricchrono_ai_source_disagreement_score | Gauge | Source or ensemble disagreement score. |
| metricchrono_ai_source_missing_total | Counter | Synthetic missing-source events. |
| metricchrono_ai_model_version_active | Gauge | One when a model version is active. |
| metricchrono_ai_scenario_state | Gauge | One for the active local scenario phase. |
| metricchrono_ai_inspection_candidate | Gauge | Ranked next-step candidate for triage tables. |
