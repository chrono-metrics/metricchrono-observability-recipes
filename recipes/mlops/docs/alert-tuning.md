# Alert Tuning Guide

The rules in `rules/metricchrono_recipe_alerts.yml` are demo-safe examples. They are scoped by `service`, `environment`, `model`, and `stream`, and their `for:` windows are short enough to fire during the accelerated local scenario.

For production, lengthen the `for:` windows and route alerts through your normal ownership labels.

## Behavior Drift Watch

Meaning: behavior moved from normal, but may not be broken. Start with a ticket or low-priority page only if the state persists.

Production tuning:

- group by service, environment, model, and stream;
- suppress during known experiments if shadow traffic is expected to differ;
- require a minimum request volume before alerting.

## Possible AI Behavior Incident

Meaning: behavior movement is large enough to warrant immediate triage, especially when quality proxy drops too.

Production tuning:

- combine behavior score with large-change score;
- optionally add a quality or business metric condition;
- route to the owning model or application team.

## Behavior Changed After Deploy

Meaning: behavior moved after a model, prompt, index, or config change.

Production tuning:

- keep deploy markers reliable;
- correlate with model version, prompt version, index version, or config hash;
- use as rollback evidence, not as automatic rollback logic.

## Retrieval Behavior Drift

Meaning: RAG is retrieving different context than normal.

Production tuning:

- alert per retriever/index/query group;
- suppress during planned reindex windows;
- inspect examples before changing generation policy.

## Agent Workflow Changed

Meaning: tool or step patterns changed from the baseline.

Production tuning:

- keep tool names bounded;
- compare against prompt/model/tool releases;
- inspect traces for the affected path.
