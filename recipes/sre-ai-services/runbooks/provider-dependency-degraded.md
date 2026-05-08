# Provider Dependency Degraded

## Meaning

Provider, retrieval, vector DB, cache, or tool dependency is degraded or rate limited.

## First checks

Compare provider/dependency latency and errors against service latency and errors.

## Likely causes

Hosted model outage, provider quota, vector store latency, retriever issue, tool API failures, or cache collapse.

## What to inspect

Provider status, quota dashboards, retry budget, fallback configuration, and dependency owner alerts.

## What not to do

Do not treat dependency-led service symptoms as an AI behavior incident.

## Escalation owner

Dependency owner or vendor owner, with SRE coordinating user-impact mitigation.

## Recovery criteria

Dependency health normal, rate limits stopped, service burn recovered, and retries back to normal.
