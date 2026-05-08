# Baseline Calibration

Demo thresholds are not production thresholds.

Build baselines from known-good representative traffic for each service, workload, stream, model, and traffic role. Refresh baselines only after current behavior is accepted as healthy.

Behavior alerts should be suppressed or downgraded when baseline age exceeds policy, sample volume is below minimum traffic, or required behavior sources are missing.
