# Behavior Changed While Service Health Normal

## Meaning

Behavior evidence changed while latency, errors, traffic, and SLO burn remain normal.

## First checks

Check deploys, model version, prompt version, index version, config version, input shift, retrieval shift, and output behavior.

## Likely causes

Prompt change, model update, index rebuild, input population shift, retrieval change, or agent workflow change.

## What to inspect

Behavior components, release timeline, baseline trust, sample volume, and top inspection candidates.

## What not to do

Do not restart infrastructure first and do not page solely on behavior-change by default.

## Escalation owner

AI/model owner, prompt owner, retrieval owner, or agent workflow owner.

## Recovery criteria

Behavior returns below watch threshold or the owner accepts the new behavior as healthy and refreshes baseline policy.
