# Metric Contract

Default dashboards use user-facing metrics only. Raw MetricChrono internals are not required to read these dashboards.

## Stable Labels

Use these bounded labels where applicable:

- `site`
- `environment`
- `recipe`
- `asset_class`
- `asset_group`
- `asset`
- `subsystem`
- `source`
- `comparison`
- `change_size`
- `state`
- `severity`
- `scenario_phase`

## Forbidden Labels

Never use these as metric labels:

- `serial_number`
- `operator_id`
- `user_id`
- `session_id`
- `event_id`
- `free_form_message`
- `error_text`
- `document_id`
- `part_id`
- `lot_id`
- `work_order_id`
- `raw_tag`

Event IDs, work orders, raw tags, raw messages, part or lot identifiers, and free-form maintenance notes belong in historians, PLC or SCADA event logs, quality records, maintenance systems, or event tables, not monitoring metric labels.

## Change Score

These are demo defaults, not production thresholds:

```text
0-20: normal variation
20-50: watch
50-75: investigate
75-100: incident candidate
```

## Comparison

Allowed values include:

- `known_good_baseline`
- `last_window`
- `same_machine_state`
- `peer_asset`
- `station_vs_line`
- `sensor_vs_sensor`
- `source_vs_source`
- `pre_maintenance`
- `post_maintenance`
- `sensor_vs_controller`
- `current_vs_target`

## Change Size

- `small`
- `medium`
- `large`

## Metrics

- `metricchrono_industrial_baseline_in_use` (gauge): One when the state-matched baseline is active.
- `metricchrono_industrial_cell_state` (gauge): One-hot cell state.
- `metricchrono_industrial_cell_state_code` (gauge): Compact cell state code for state timelines.
- `metricchrono_industrial_change_score_by_size` (gauge): Process change score split by small, medium, and large movement.
- `metricchrono_industrial_cycle_change_score` (gauge): Cycle behavior change score.
- `metricchrono_industrial_cycle_time_seconds` (gauge): Observed cycle time.
- `metricchrono_industrial_diagnostic_summary` (gauge): Bounded diagnostic category summary.
- `metricchrono_industrial_first_change_offset_seconds` (gauge): Seconds between first meaningful change and impact.
- `metricchrono_industrial_flow_change_score` (gauge): Flow change score.
- `metricchrono_industrial_incident_window_state` (gauge): Incident replay window state.
- `metricchrono_industrial_incident_window_state_code` (gauge): Compact incident replay window state code.
- `metricchrono_industrial_inspection_candidate` (gauge): Ranked industrial inspection candidate.
- `metricchrono_industrial_line_change_score` (gauge): Line-level change score.
- `metricchrono_industrial_line_state` (gauge): One-hot production line state.
- `metricchrono_industrial_line_state_code` (gauge): Compact line state code for state timelines.
- `metricchrono_industrial_machine_state` (gauge): One-hot machine state.
- `metricchrono_industrial_machine_state_code` (gauge): Compact machine state code for state timelines.
- `metricchrono_industrial_motor_current_change_score` (gauge): Motor current change score.
- `metricchrono_industrial_physical_machine_change_score` (gauge): Combined physical-machine change score.
- `metricchrono_industrial_pressure_change_score` (gauge): Pressure change score.
- `metricchrono_industrial_process_change_score` (gauge): Overall process change score.
- `metricchrono_industrial_process_variable_value` (gauge): Selected process variable value.
- `metricchrono_industrial_quality_change_score` (gauge): Quality proxy change score.
- `metricchrono_industrial_quality_proxy` (gauge): Synthetic quality proxy.
- `metricchrono_industrial_reject_rate` (gauge): Synthetic reject rate.
- `metricchrono_industrial_replay_artifact` (gauge): Suggested replay artifact row.
- `metricchrono_industrial_scenario_phase` (gauge): One-hot local industrial scenario phase.
- `metricchrono_industrial_sensor_disagreement_score` (gauge): Sensor or controller disagreement score.
- `metricchrono_industrial_sensor_reliability_score` (gauge): Sensor reliability score.
- `metricchrono_industrial_source_late_total` (counter): Late source or tag events.
- `metricchrono_industrial_source_missing_total` (counter): Missing source or tag events.
- `metricchrono_industrial_station_change_score` (gauge): Station-level change score.
- `metricchrono_industrial_station_change_state` (gauge): 0 normal, 1 watch, 2 investigate, 3 incident candidate, 4 recovered.
- `metricchrono_industrial_tag_freshness_seconds` (gauge): Tag freshness age.
- `metricchrono_industrial_target_cycle_time_seconds` (gauge): Target cycle time.
- `metricchrono_industrial_temperature_change_score` (gauge): Temperature change score.
- `metricchrono_industrial_vibration_change_score` (gauge): Vibration change score.
- `metricchrono_industrial_wip_or_queue_change_score` (gauge): Work-in-process or queue change score.
