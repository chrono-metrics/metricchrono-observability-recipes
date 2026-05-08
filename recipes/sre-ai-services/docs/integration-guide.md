# Integration Guide

Start by emitting the metric contract from your AI gateway or service wrapper. Add dependency/provider metrics from SDK middleware, OpenTelemetry instrumentation, or existing exporters.

Keep labels bounded. Put prompts, request IDs, trace IDs, user IDs, raw text, raw documents, and free-form errors in logs or traces, not Prometheus labels.

Roll out in three steps:

1. Wire golden signals, SLO burn, and dependency health.
2. Add release correlation for app, model, prompt, index, config, and traffic role.
3. Add behavior evidence with baseline freshness and minimum-volume gates.
