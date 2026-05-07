# Baseline Calibration

Demo thresholds are not production thresholds. Do not copy them directly into production. Start from a known-good period with representative operation and no active incident.

## Baseline Examples

- known-good running state
- known-good changeover state
- known-good station cycle
- known-good machine state
- known-good shift or product family
- peer station / peer machine
- previous stable maintenance period

## Comparator Guidance

- `known_good_baseline`: use to answer is this outside normal?
- `last_window`: use to answer did something sudden happen?
- `same_machine_state`: use to avoid comparing unlike operating states
- `peer_asset`: use to answer is this asset different from comparable assets?
- `station_vs_line`: use to answer is this local or line-wide?
- `sensor_vs_sensor`: use to answer is one tag or source lying?
- `current_vs_target`: use for cycle time, throughput, and process setpoint checks

## Calibration Steps

1. Choose a known-good period for each operating state.
2. Verify source freshness and diagnostic health before fitting baselines.
3. Run the synthetic scenario and compare expected normal versus incident fixtures.
4. Tune alert windows conservatively and review with domain engineers.
5. Refresh baselines after planned machine, line, product, recipe, maintenance, tooling, or process changes.
