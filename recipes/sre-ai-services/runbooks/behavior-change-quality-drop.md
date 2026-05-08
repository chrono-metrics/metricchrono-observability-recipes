# Behavior Change With Quality Drop

## Meaning

Behavior evidence and quality or business proxy are degraded together.

## First checks

Confirm quality proxy semantics, delay window, sample volume, and baseline trust.

## Likely causes

Bad model/prompt release, harmful retrieval change, input shift, policy regression, or agent workflow failure.

## What to inspect

Release guardrail, behavior components, quality proxy history, rollback evidence, and affected stream.

## What not to do

Do not claim behavior-change alone proves harm; require quality, SLO, or configured impact evidence.

## Escalation owner

AI/model owner with SRE incident coordination when policy treats this as user impact.

## Recovery criteria

Quality proxy recovers and behavior evidence returns below configured incident thresholds.
