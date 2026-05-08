# Release Behavior Regression

## Meaning

Canary or new version behavior differs materially from stable or previous version.

## First checks

Compare canary and stable user impact before deciding whether behavior evidence is rollback-worthy.

## Likely causes

Model rollout, prompt edit, index rebuild, config change, app deploy, or canary traffic mismatch.

## What to inspect

Canary user impact, behavior difference, changed components, dependency/cost difference, and rollback evidence.

## What not to do

Do not roll back without evidence, and do not page solely on behavior difference unless policy says so.

## Escalation owner

Release owner, AI platform owner, and SRE for guardrail enforcement.

## Recovery criteria

Rollback or pause completed, canary difference normal, user SLIs stable, and quality proxy normal.
