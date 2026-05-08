# AI Service Fast Burn

## Meaning

Short-window SLO burn is high enough to page under the example policy.

## First checks

Confirm affected service, workload, traffic role, request rate, errors, latency, and saturation.

## Likely causes

Capacity, dependency failure, bad deploy, provider rate limit, timeout path, or widespread app failure.

## What to inspect

Open AI Incident Triage, then inspect SLO bad-event reason, latency decomposition, error path, and dependency health.

## What not to do

Do not start with AI behavior analysis if user-facing SLIs are clearly burning.

## Escalation owner

SRE incident commander first, then service owner or dependency owner based on evidence.

## Recovery criteria

Short and long burn below thresholds, latency and errors normal, and recovery window sustained.
