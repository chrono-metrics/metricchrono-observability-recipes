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
- `bag_file`
- `raw_topic`
- `trace_id`

Event IDs, bag names, trace IDs, raw topics, and free-form robot logs belong in ROS bags, log stores, traces, video stores, or event tables, not monitoring metric labels.

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
- `same_mission_phase`
- `peer_asset`
- `commanded_vs_actual`
- `sensor_vs_estimator`
- `source_vs_source`
- `pre_maintenance`
- `post_maintenance`
- `actuator_vs_peer_actuator`
- `sensor_vs_controller`

## Change Size

- `small`
- `medium`
- `large`

## Metrics

- `metricchrono_robot_actual_angular_velocity` (gauge): Actual angular velocity.
- `metricchrono_robot_actual_linear_velocity` (gauge): Actual linear velocity.
- `metricchrono_robot_actual_speed` (gauge): Actual speed in meters per second.
- `metricchrono_robot_actual_velocity` (gauge): Actual velocity for incident replay.
- `metricchrono_robot_actuator_effort_change_score` (gauge): Actuator effort change score.
- `metricchrono_robot_battery_change_score` (gauge): Battery state change score.
- `metricchrono_robot_change_score_by_size` (gauge): Robot change score split by small, medium, and large movement.
- `metricchrono_robot_change_state` (gauge): 0 normal, 1 watch, 2 investigate, 3 incident candidate, 4 recovered.
- `metricchrono_robot_commanded_angular_velocity` (gauge): Commanded angular velocity.
- `metricchrono_robot_commanded_linear_velocity` (gauge): Commanded linear velocity.
- `metricchrono_robot_commanded_speed` (gauge): Commanded speed in meters per second.
- `metricchrono_robot_commanded_velocity` (gauge): Commanded velocity for incident replay.
- `metricchrono_robot_current` (gauge): Electrical current.
- `metricchrono_robot_diagnostic_state` (gauge): One-hot robot diagnostic state.
- `metricchrono_robot_diagnostic_state_code` (gauge): Compact robot diagnostic state code for state timelines.
- `metricchrono_robot_diagnostic_summary` (gauge): Bounded diagnostic category summary.
- `metricchrono_robot_feature_count_change_score` (gauge): Perception feature count change score.
- `metricchrono_robot_first_change_offset_seconds` (gauge): Seconds between first meaningful change and main symptom.
- `metricchrono_robot_imu_disagreement_score` (gauge): IMU disagreement score.
- `metricchrono_robot_incident_window_state` (gauge): Incident replay window state.
- `metricchrono_robot_incident_window_state_code` (gauge): Compact incident replay window state code.
- `metricchrono_robot_inspection_candidate` (gauge): Ranked robot inspection candidate.
- `metricchrono_robot_localization_disagreement_score` (gauge): Localization disagreement score.
- `metricchrono_robot_mission_state` (gauge): One-hot robot mission state.
- `metricchrono_robot_mission_state_code` (gauge): Compact robot mission state code for state timelines.
- `metricchrono_robot_motion_change_score` (gauge): Motion-specific behavior change score.
- `metricchrono_robot_motor_current_change_score` (gauge): Motor current change score.
- `metricchrono_robot_motor_temperature_change_score` (gauge): Motor temperature change score.
- `metricchrono_robot_odometry_disagreement_score` (gauge): Odometry disagreement score.
- `metricchrono_robot_overall_change_score` (gauge): Overall robot behavior change score.
- `metricchrono_robot_perception_change_score` (gauge): Perception input change score.
- `metricchrono_robot_perception_confidence_change_score` (gauge): Perception confidence change score.
- `metricchrono_robot_power_change_score` (gauge): Power state change score.
- `metricchrono_robot_recovery_state` (gauge): Recovery confirmation state.
- `metricchrono_robot_replay_artifact` (gauge): Suggested replay artifact row.
- `metricchrono_robot_safety_state` (gauge): One-hot robot safety state.
- `metricchrono_robot_safety_state_code` (gauge): Compact robot safety state code for state timelines.
- `metricchrono_robot_scenario_phase` (gauge): One-hot local robotics scenario phase.
- `metricchrono_robot_source_disagreement_score` (gauge): Source, sensor, or estimator disagreement score.
- `metricchrono_robot_source_freshness_seconds` (gauge): Source freshness age.
- `metricchrono_robot_source_late_total` (counter): Late source events.
- `metricchrono_robot_source_missing_total` (counter): Missing source events.
- `metricchrono_robot_source_reliability_score` (gauge): Source reliability score.
- `metricchrono_robot_temperature` (gauge): Robot temperature.
- `metricchrono_robot_thermal_change_score` (gauge): Thermal state change score.
- `metricchrono_robot_topic_freshness_seconds` (gauge): Topic freshness age.
- `metricchrono_robot_tracking_deviation_score` (gauge): Commanded versus actual motion deviation score.
- `metricchrono_robot_tracking_error_distance` (histogram): Tracking error distance distribution.
- `metricchrono_robot_voltage` (gauge): Battery voltage.
