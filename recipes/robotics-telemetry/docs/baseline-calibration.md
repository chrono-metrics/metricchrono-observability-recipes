# Baseline Calibration

Demo thresholds are not production thresholds. Do not copy them directly into production. Start from a known-good period with representative operation and no active incident.

## Baseline Examples

- known-good navigation on same map / route type
- known-good docking behavior
- known-good manipulation cycle
- known-good idle state
- known-good robot of same hardware class
- previous stable software release

## Comparator Guidance

- `known_good_baseline`: use to answer is this outside normal?
- `last_window`: use to answer did something sudden happen?
- `same_mission_phase`: use to avoid comparing unlike operating states
- `peer_asset`: use to answer is this asset different from comparable assets?
- `commanded_vs_actual`: use to separate execution divergence from plan
- `sensor_vs_estimator`: use to answer did a source disagree with the fused state?

## Calibration Steps

1. Choose a known-good period for each operating state.
2. Verify source freshness and diagnostic health before fitting baselines.
3. Run the synthetic scenario and compare expected normal versus incident fixtures.
4. Tune alert windows conservatively and review with domain engineers.
5. Refresh baselines after planned hardware, route, map, payload, software, controller, or mission changes.
