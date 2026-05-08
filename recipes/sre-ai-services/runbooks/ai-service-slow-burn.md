# AI Service Slow Burn

## Meaning

Long-window burn is above sustainable rate but may not require an immediate page.

## First checks

Check whether the burn is worsening, which SLO reason dominates, and whether fast burn is also active.

## Likely causes

Sustained low-grade errors, latency creep, dependency instability, or configured quality-policy failures.

## What to inspect

Review trend duration, affected workload, dependency health, and recent deploys.

## What not to do

Do not ignore slow burn because the current minute looks quiet.

## Escalation owner

Service SRE and application owner.

## Recovery criteria

Long-window burn returns below 1x and remains there through the configured window.
