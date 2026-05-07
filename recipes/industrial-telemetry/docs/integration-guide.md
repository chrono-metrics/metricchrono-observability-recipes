# Integration Guide

This recipe is designed for industrial telemetry engineers. The local path is a synthetic Prometheus textfile scenario, so evaluation does not require OPC UA, PLC, SCADA, and historian exports.

Production integration should map domain signals into the metric contract in `metric-contract.md`. Keep labels bounded. Use `asset_group` for lines, cells, stations, or machine groups, and use `asset` only when the station or machine list is bounded.

## Emit Prometheus Metrics

1. Select a known-good baseline for each operating state.
2. Compute user-facing change scores from domain streams.
3. Emit Prometheus gauges, counters, and histograms using the metric names in this recipe.
4. Preserve raw historian rows, PLC or SCADA events, maintenance records, quality records, and controller logs outside metric labels.

Optional integration path:
OPC UA, PLC, SCADA, and historian exports can feed the metrics, but it is intentionally not required for the demo.
