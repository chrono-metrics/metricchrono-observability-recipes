# Troubleshooting

Start with the overview dashboard, then inspect agreement, then replay.

Common cases:
- One source is hot: inspect freshness, calibration, mounting, driver, middleware, timestamping, or controller mapping before calling it a real behavior change.
- Many sources are hot: inspect mission state, environment, estimator health, map or route change, clock synchronization, or fleet update.
- Change appears during planned mission transition: verify the same-mission-phase baseline.
- Recovery state is normal but scores remain high: treat recovery as incomplete and keep the incident window open.
- A table suggests a broad replay: narrow the window to the incident candidate and source categories.

The recipe does not replace safety systems, robot controllers, ROS diagnostics, fleet managers, or incident policy.
