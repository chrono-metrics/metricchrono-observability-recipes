# Baseline Stale Or Low Volume

## Meaning

Behavior signal is weak because baseline, traffic volume, or source availability is not trustworthy.

## First checks

Check baseline age, sample volume, sampled request rate, missing-source count, and low-traffic flag.

## Likely causes

Stale baseline, under-sampled workload, telemetry source missing, or traffic pattern too sparse.

## What to inspect

Baseline refresh policy, representative known-good windows, source freshness, and minimum-volume threshold.

## What not to do

Do not escalate behavior movement as incident-grade while trust gates are failing.

## Escalation owner

Observability owner and AI/model owner for baseline acceptance.

## Recovery criteria

Baseline is fresh, sample volume clears policy, missing sources are zero, and alerts regain normal severity.
