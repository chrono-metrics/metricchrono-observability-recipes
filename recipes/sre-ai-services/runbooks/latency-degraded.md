# Latency Degraded

## Meaning

Latency is above the SLO or known-good band, especially when burn is elevated.

## First checks

Compare end-to-end p95/p99 with queue, provider, retrieval, tool-call, and streaming components.

## Likely causes

Queueing, concurrency limit, provider latency, vector DB latency, tool API latency, or traffic spike.

## What to inspect

Open saturation decomposition and dependency health panels.

## What not to do

Do not average successful and failed latency or restart components without checking the leading component.

## Escalation owner

SRE for capacity, dependency owner for upstream latency, app owner for local queues.

## Recovery criteria

p95/p99 below SLO, queue and saturation normal, and burn below thresholds.
