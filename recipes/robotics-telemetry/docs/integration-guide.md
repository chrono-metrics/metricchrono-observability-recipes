# Integration Guide

This recipe is designed for robotics engineers. The local path is a synthetic Prometheus textfile scenario, so evaluation does not require ROS 2 topics, diagnostics, and bags.

Production integration should map domain signals into the metric contract in `metric-contract.md`. Keep labels bounded. Use `asset_group` for fleets or robot classes, and use `asset` only when the robot list is bounded.

## Emit Prometheus Metrics

1. Select a known-good baseline for each operating state.
2. Compute user-facing change scores from domain streams.
3. Emit Prometheus gauges, counters, and histograms using the metric names in this recipe.
4. Preserve raw logs, ROS bags, traces, or video outside metric labels.

Optional integration path:
ROS 2 topics, diagnostics, and bags can feed the metrics, but it is intentionally not required for the demo.
