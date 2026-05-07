# Troubleshooting

Start with the overview dashboard, then inspect agreement, then replay.

Common cases:
- One source is hot: inspect freshness, calibration, wiring, tag subscription, gateway path, or controller mapping before calling it a real process change.
- Many sources are hot: inspect machine state, line state, material, changeover, upstream bottleneck, clock synchronization, or maintenance activity.
- Change appears during planned state transition: verify the same-machine-state baseline.
- Recovery state is normal but scores remain high: treat recovery as incomplete and keep the incident window open.
- A table suggests a broad inspection: narrow the window to the incident candidate and station, source, or quality categories.

The recipe does not replace safety systems, PLC alarms, SCADA, historians, maintenance systems, quality systems, or incident policy.
