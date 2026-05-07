# Dashboard Panel Guide

Every panel description has exactly these fields:

- `Question answered:`
- `How to read it:`
- `Why it matters:`
- `Next action:`

## Industrial Line Overview

### Production State Timeline

Question answered: Was the machine running, blocked, starved, changing over, or faulted when the change happened?

How to read it: Changes during planned changeover are interpreted differently from changes during steady running.

Why it matters: Industrial telemetry is state-dependent. Comparing changeover to steady production creates false alarms.

Next action: If the change occurs during running, inspect cycle and process panels. If during changeover, compare against changeover baseline.

### Line Change State By Station

Question answered: Which station or machine is behaving differently?

How to read it: Rows are stations or machines. Watch, investigate, and incident candidate bands show stations that differ from the selected reference.

Why it matters: Industrial engineers debug by station and machine, not by abstract signal.

Next action: Inspect the abnormal station first. If multiple stations changed, inspect line state, material, schedule, or upstream bottleneck.

### Overall Process Change Score

Question answered: Did the process move outside known-good behavior?

How to read it: A rising process score means the station or line behavior is moving away from the selected reference.

Why it matters: This gives an early signal before downtime, scrap, or hard controller alarms.

Next action: If the score rises during running, inspect cycle time, vibration, current, thermal behavior, sensor agreement, and quality proxy.

### Cycle Time vs Target

Question answered: Is the station drifting from expected cycle time?

How to read it: Cycle time above target means slowdown. Cycle change rising while cycle time is near target means early behavior change.

Why it matters: Cycle time is familiar to plant teams. Change detection should augment it, not replace it.

Next action: Inspect bottleneck, mechanical load, process variables, operator or material changes, and upstream or downstream blocking.

### Change Size Split

Question answered: Is this normal variation, sustained drift, or a major process shift?

How to read it: Small change often means normal noise. Sustained medium change means drift. Large change means incident candidate or state mismatch.

Why it matters: Plant signals are noisy; engineers need scale separation without internal terminology.

Next action: Use large change for immediate inspection and sustained medium change for early maintenance or process review.

### Bottleneck / Top Station Change

Question answered: Which station is currently the best first suspect?

How to read it: The highest station is the one with the largest process or cycle deviation relative to the line or baseline.

Why it matters: Industrial engineers need station-level triage, not aggregate line noise.

Next action: Inspect the top station's cycle, machine state, process variables, and sensor agreement.

### Quality / Reject Proxy

Question answered: Is process change showing up in quality?

How to read it: Quality proxy degradation aligned with process change increases urgency. Process change without quality degradation is still useful as early warning.

Why it matters: Factories care about scrap, rework, and quality escape.

Next action: If quality proxy falls or reject rate rises, inspect the station or process variables that changed first.

### Vibration / Current / Thermal Change

Question answered: Is the machine physically behaving differently?

How to read it: Rising vibration, current, or temperature change can indicate load, friction, bearing wear, motor issue, process resistance, or environmental condition.

Why it matters: Industrial telemetry engineers monitor these variables for early maintenance and process health.

Next action: Inspect mechanical load, lubrication, bearing or motor condition, process resistance, and maintenance history.

### Sensor Disagreement Summary

Question answered: Is this process drift or one bad sensor or tag?

How to read it: One high source suggests sensor or tag issue. Many high sources suggest process or machine behavior changed.

Why it matters: Bad tags and stale sensors are common industrial telemetry failure modes.

Next action: If one sensor is high, inspect calibration, wiring, freshness, and mapping. If many sensors are high, inspect the process.

### Top Inspection Candidates

Question answered: Where should I inspect first?

How to read it: The top row is the highest-priority station, machine, or source with an explainable reason.

Why it matters: This converts the dashboard into a triage tool.

Next action: Open Industrial Incident Replay for the top row.

## Machine / Process Agreement

### Sensor Agreement Heatmap

Question answered: Which sensor, tag, or station stopped agreeing?

How to read it: A single hot sensor row points to a sensor or tag problem. A station-wide hot band points to machine or process change.

Why it matters: This prevents treating bad telemetry as machine drift.

Next action: Inspect the hot sensor or tag first if isolated; inspect process variables if station-wide.

### Sensor Reliability Score

Question answered: Which sensor or tag is least reliable right now?

How to read it: Low score means the source may be stale, missing, noisy, or inconsistent.

Why it matters: Industrial dashboards often contain stale tags that look like stable process values.

Next action: Inspect tag mapping, controller update, network path, sensor wiring, or calibration.

### Missing / Late Tags

Question answered: Did the data stream degrade?

How to read it: Missing or late tags rising during a process-change event may mean telemetry degraded rather than the machine changed.

Why it matters: Telemetry reliability is often the difference between a process incident and a data incident.

Next action: Inspect controller connectivity, gateway, tag subscription, network, and historian or exporter path.

### Cycle-Time Distribution

Question answered: Did cycle behavior shift, or was there one bad cycle?

How to read it: A distribution shift indicates sustained process or cycle drift. A single tail event suggests a transient interruption.

Why it matters: Industrial engineers care about recurring cycle loss, not just isolated outliers.

Next action: If the distribution shifts, inspect bottleneck, mechanical condition, process variable drift, and material flow.

### Machine Physical Change

Question answered: Is the machine physically behaving differently?

How to read it: Rising physical change indicates machine or process load changed even before quality or downtime changes.

Why it matters: This is the industrial engineer's early warning layer.

Next action: Inspect load, friction, bearings, motor, cooling, pressure or flow path, lubrication, or process material.

### Process Variable vs Change Score

Question answered: Which process variable moved with the change score?

How to read it: If a process variable moves before the change score, it may be causal or upstream. If it moves after, it may be an effect.

Why it matters: Industrial engineers need to connect change detection to known process variables.

Next action: Inspect the process variable that moves first.

### Station vs Line Comparison

Question answered: Is this station uniquely abnormal or part of a line-wide shift?

How to read it: A station much higher than the line suggests local issue. Station and line rising together suggests material, schedule, changeover, or line-wide condition.

Why it matters: This points investigation to local maintenance or line/system conditions.

Next action: Inspect local station if isolated; inspect material flow, line state, upstream and downstream if broad.

### Quality Impact Correlation

Question answered: Is the process change affecting output quality?

How to read it: If quality change rises after process change, the drift may be turning into scrap or rework risk.

Why it matters: This connects telemetry to production impact.

Next action: Prioritize incidents with quality impact over isolated telemetry movement.

### Planned Changeover Guard

Question answered: Are we comparing the machine to the correct state?

How to read it: If machine state is changeover, the dashboard should compare against changeover behavior, not running behavior.

Why it matters: False positives during changeover destroy trust.

Next action: If baseline is wrong, do not treat the change as an incident; fix baseline and state mapping.

### Machine Diagnostics Summary

Question answered: What did the machine or controller already report?

How to read it: Rows summarize bounded categories, not raw messages.

Why it matters: Existing controller diagnostics should remain primary when they are clear.

Next action: Use diagnostics as primary explanation if aligned with process change.

### Suggested Next Inspection

Question answered: What should I inspect next?

How to read it: Rows translate metrics into plant actions.

Why it matters: The recipe should reduce decision time.

Next action: Follow the top row and inspect station, sensor, cycle, physical machine signal, or quality path.

## Industrial Incident Replay

### Incident Window Timeline

Question answered: What was the line doing before, during, and after the incident?

How to read it: The incident must be bounded by pre-incident, incident, and recovery or ongoing state.

Why it matters: State context determines whether the change is expected.

Next action: Use the highlighted window to inspect historian data, controller logs, maintenance logs, or quality records.

### First Meaningful Process Change

Question answered: What changed first?

How to read it: This panel names the first station and signal group such as cycle, vibration, current, thermal, sensor, or quality.

Why it matters: This helps distinguish cause from downstream effects.

Next action: Inspect the first changed station or source before later symptoms.

### Process Change Around Incident

Question answered: How did the incident evolve?

How to read it: Look for which signal rises first and whether quality impact follows.

Why it matters: Industrial incidents propagate from physical change to cycle drift to quality or downtime.

Next action: Prioritize the first changed signal group.

### Sensor Disagreement Around Incident

Question answered: Was it bad data or real process change?

How to read it: A single hot sensor row suggests bad or stale sensor. Many related sensors changing together suggests real process or machine behavior.

Why it matters: This is the central industrial telemetry distinction.

Next action: Inspect sensor or tag if isolated; inspect machine or process if broad.

### Cycle And Bottleneck Around Incident

Question answered: Did the incident affect throughput?

How to read it: Cycle time above target with rising station change points to throughput impact.

Why it matters: Throughput loss is immediately actionable.

Next action: Inspect station bottleneck, mechanical delays, material flow, and upstream or downstream blocking.

### Physical Machine Signals Around Incident

Question answered: Was the machine physically degrading or under abnormal load?

How to read it: Rising physical-machine scores before cycle or quality impact suggest early mechanical or process stress.

Why it matters: This is where maintenance and controls engineers can act.

Next action: Inspect mechanical load, lubrication, motor, bearings, cooling, and process resistance.

### Quality / Reject Impact Around Incident

Question answered: Did the incident affect production quality?

How to read it: Quality impact after process drift increases urgency and helps prioritize action.

Why it matters: Quality loss is the business consequence users care about.

Next action: Escalate if quality impact appears; otherwise treat as early warning or maintenance candidate.

### Replay / Investigation Artifacts

Question answered: What should I inspect offline?

How to read it: Rows give bounded windows and signal groups.

Why it matters: The recipe should save the engineer from opening the entire historian or log stream.

Next action: Use suggested tags and windows to inspect historian, controller logs, maintenance records, and quality records.
