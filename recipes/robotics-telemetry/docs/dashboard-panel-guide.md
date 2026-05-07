# Dashboard Panel Guide

Every panel description has exactly these fields:

- `Question answered:`
- `How to read it:`
- `Why it matters:`
- `Next action:`

## Robot Fleet Overview

### Fleet / Mission State

Question answered: What was the robot trying to do when the change happened?

How to read it: Look for whether a change occurred during normal navigation, a state transition, recovery, or a safety event.

Why it matters: Phase context separates expected maneuver changes from suspicious behavior during steady work.

Next action: If the change overlaps fault, recovery, paused, or estop, open Robot Incident Replay.

### Fleet Change State By Robot

Question answered: Which robot is behaving differently right now?

How to read it: Rows are robots. Watch, investigate, and incident candidate bands show robots whose behavior differs from the selected reference.

Why it matters: A fleet engineer first needs to know whether this is one robot, several robots, or the whole fleet.

Next action: If one robot is abnormal, inspect source agreement for that robot. If many robots change together, inspect environment, map, network, or mission update.

### Overall Robot Change Score

Question answered: Did the robot's overall behavior move outside normal variation?

How to read it: A low stable score means ordinary behavior. A rising score means the robot is moving away from the selected reference.

Why it matters: Robot logs are too large to inspect blindly, so this gives a first signal for when to look.

Next action: If high only versus last_window, look for a sudden disturbance. If high versus known_good_baseline but flat, look for slow drift or changed conditions.

### Change Size Split

Question answered: Is this harmless jitter or a large behavior shift?

How to read it: Small change alone is usually jitter. Sustained medium change deserves attention. Large change is an incident candidate.

Why it matters: Robotics data is noisy; engineers need to separate vibration and chatter from meaningful regime shifts.

Next action: If large change appears, inspect Source Agreement and Incident Replay. If only small rises, inspect freshness or controller jitter.

### Commanded vs Actual Tracking Deviation

Question answered: Did the robot fail to execute the motion it was commanded to perform?

How to read it: A rising tracking deviation with stable command means actual motion is separating from requested motion.

Why it matters: This separates upstream planning or perception problems from downstream execution and control problems.

Next action: If tracking deviation rises, inspect actuator effort, motor current, temperature, wheel slip, joint effort, and safety state.

### Sensor / Estimator Disagreement Summary

Question answered: Which sensor or estimator disagrees most with the rest of the robot?

How to read it: The highest bar is the source that currently disagrees most. It points to where to inspect first but does not prove fault.

Why it matters: When localization, odometry, IMU, lidar, or camera disagree, engineers need a ranked list.

Next action: Open Robot Source Agreement for the top source.

### Missing Or Late Sources

Question answered: Is the dashboard seeing a behavior change, or did telemetry go missing?

How to read it: Missing-source counters rising during a change event mean disagreement may be caused by data loss or stale sources.

Why it matters: Robotics incidents often look like state changes when the real problem is delayed or stale sensor data.

Next action: Inspect drivers, middleware, CPU load, network, and source timestamps before blaming robot behavior.

### Actuator Effort / Thermal Change

Question answered: Is the robot working harder than usual to perform the same task?

How to read it: Rising effort, current, or temperature change while mission state is unchanged can indicate load, terrain, joint issue, motor degradation, or compensation.

Why it matters: Mechanical and actuator problems often appear before a hard fault.

Next action: Inspect the corresponding joint, wheel, motor, payload, terrain, or docking interaction.

### Safety And Diagnostics Timeline

Question answered: Did a safety or diagnostic state change explain the behavior change?

How to read it: Look for warnings or faults aligned with change-score spikes.

Why it matters: Engineers should not infer from change metrics when the robot already emitted a clear safety or diagnostic signal.

Next action: If diagnostic state changed, use it as the primary investigation path and use change panels as supporting context.

### Top Incident Candidates

Question answered: Where should I click first?

How to read it: The top row is the highest-priority investigation candidate and names the robot, subsystem, source, comparison, and reason.

Why it matters: Operators and engineers need a triage queue, not twenty unrelated graphs.

Next action: Open Robot Incident Replay for the top row.

## Robot Source Agreement

### Source Agreement Heatmap

Question answered: Which sensor or subsystem stopped agreeing, and when?

How to read it: A single hot row points to one diverging source. Many hot rows can mean real scene change, estimator issue, synchronization problem, or global telemetry issue.

Why it matters: Robotics engineers debug by source such as lidar, camera, IMU, wheel encoders, odometry, localization, controller, and actuator.

Next action: If one row is hot, inspect that source. If many rows are hot, inspect estimator, clock sync, environment event, or mission transition.

### Source Reliability / Trust Score

Question answered: Which source is currently least trustworthy?

How to read it: Low score means the source has repeatedly disagreed, gone missing, or become stale. It is a triage hint, not a permanent calibration judgment.

Why it matters: Engineers need a prioritized sensor list during incidents.

Next action: Inspect the lowest-trust source's driver status, timestamps, physical condition, and mounting.

### Odometry / Localization / IMU Agreement

Question answered: Is the robot losing localization or just moving differently?

How to read it: Localization disagreement with stable actuator tracking points toward estimator or perception. Tracking deviation with stable localization points toward control or actuation.

Why it matters: This separates the robot not knowing where it is from the robot not executing what it wants.

Next action: Inspect map, feature quality, lidar/camera health, IMU calibration, wheel slip, and covariance.

### Perception Source Change

Question answered: Did the robot's perception input change even though the mission state did not?

How to read it: Rising perception change with normal motion can indicate occlusion, lighting change, dust, scene change, feature loss, or camera/lidar degradation.

Why it matters: Perception problems often present as downstream navigation or control anomalies.

Next action: Inspect camera/lidar status, lighting, occlusion, lens or sensor cleanliness, and environment.

### Topic / Source Freshness

Question answered: Did the source actually publish on time?

How to read it: Freshness increasing means the source is stale. Missing and late counters rising mean data availability changed.

Why it matters: Robotics systems are sensitive to stale perception, stale transforms, and delayed actuator feedback.

Next action: Inspect middleware, CPU, network, driver frequency, and timestamp handling.

### Commanded vs Actual Velocity

Question answered: Is the controller asking for one thing while the robot does another?

How to read it: Divergence between commanded and actual velocity indicates tracking failure, slip, saturation, load, or controller instability.

Why it matters: This is the simplest control-language explanation of a behavior change.

Next action: Inspect motor current, effort, wheel slip, actuator saturation, terrain, and safety limits.

### Tracking Error Distribution

Question answered: Is tracking error a one-off spike or a changed distribution?

How to read it: A shifted distribution means persistent behavior change. A single spike means a transient event.

Why it matters: Robotics engineers need to distinguish one bad moment from a new operating condition.

Next action: If the distribution shifts, inspect calibration, controller parameters, payload, terrain, and hardware wear.

### Actuator Effort By Joint / Wheel / Motor

Question answered: Which actuator is working unusually hard?

How to read it: A single high actuator points to a local mechanical or electrical issue. Many high actuators point to load, terrain, payload, or global control compensation.

Why it matters: This moves investigation from robot weird to a specific wheel, joint, or lift motor.

Next action: Inspect the named actuator, load path, mechanical resistance, current limits, temperature, and maintenance history.

### Battery / Power / Thermal Context

Question answered: Is power or thermal behavior contributing to the issue?

How to read it: Power or temperature change rising before motion deviation can indicate load, degradation, thermal throttling, or battery issue.

Why it matters: Power and thermal context explains many intermittent robotics failures.

Next action: Inspect battery state, charger or dock, thermal limits, current draw, and duty cycle.

### Diagnostic Messages Summary

Question answered: What did the robot itself report?

How to read it: Rows summarize bounded diagnostic categories, not raw free-form messages.

Why it matters: The robot's own diagnostics may already identify the issue. Change metrics should support, not obscure, that signal.

Next action: Use diagnostic category as the primary investigation path if it aligns with change score.

### Suggested Next Inspection

Question answered: What should I inspect next?

How to read it: Rows translate metrics into engineering next steps.

Why it matters: A solution recipe should reduce cognitive load.

Next action: Follow the top suggested inspection, then open Robot Incident Replay around the listed window.

## Robot Incident Replay

### Incident Window Timeline

Question answered: What was the robot doing before, during, and after the incident?

How to read it: The incident candidate should be bounded by pre-incident, incident, and recovery periods.

Why it matters: Replay without phase context wastes time.

Next action: Use the highlighted interval for logs, traces, bag replay, or video review.

### First Meaningful Change

Question answered: What changed first?

How to read it: This panel names the first subsystem or source whose change became meaningful inside the incident window.

Why it matters: Root-cause investigation depends heavily on ordering.

Next action: Inspect the first changed source before later downstream symptoms.

### Change Score Around Incident

Question answered: How did the incident evolve?

How to read it: Look for which score rises first and which score remains high after recovery.

Why it matters: Incident investigation depends on cause, propagation, and recovery order.

Next action: If source disagreement rises first, inspect source. If tracking rises first, inspect controls or actuation.

### Source Disagreement Around Incident

Question answered: Was this one bad source or a broad system change?

How to read it: One hot row suggests a source-specific issue. Many hot rows suggest environment, estimator, clock sync, or global behavior change.

Why it matters: This prevents blaming a sensor when the scene or estimator changed globally.

Next action: Use the row pattern to choose between source inspection and system-wide investigation.

### Command / Actual / Effort Around Incident

Question answered: Was this a control execution problem?

How to read it: If command remains steady but actual and effort change, the robot likely struggled to execute. If command changes first, planner or mission may be upstream.

Why it matters: This maps directly to controls and actuation debugging.

Next action: Inspect controller, actuator, terrain or contact, payload, and safety constraints.

### Missing / Late Data Around Incident

Question answered: Was the incident actually a telemetry freshness problem?

How to read it: Freshness gaps near incident start mean stale data may be the trigger or an important confounder.

Why it matters: Robotics incidents are often timestamp, transform, middleware, or source-latency issues.

Next action: Inspect source timestamps, middleware, CPU, network, and driver health.

### Replay Artifacts

Question answered: What should I replay or inspect offline?

How to read it: Rows give bounded windows and source categories instead of asking you to search the full stream.

Why it matters: Engineers do not want to search the full log stream.

Next action: Use the suggested window and sources to inspect bags, logs, traces, or video.

### Recovery Confirmation

Question answered: Did the robot actually recover?

How to read it: Recovery requires the state to return to normal and the relevant change, disagreement, and tracking scores to fall.

Why it matters: A robot can leave fault state while still behaving abnormally.

Next action: If recovery state is normal but scores remain high, keep investigating.
