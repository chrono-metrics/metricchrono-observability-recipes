# Validation Guide

Run:

```bash
npm run sre:generate
npm run sre:capture
npm run sre:validate
```

Expected outcomes:

- Normal: Current state is Normal, burn is normal, behavior-change is low, and no default alerts fire.
- Infra/capacity issue: golden signals degrade and behavior is not the primary incident hypothesis.
- Dependency/provider issue: provider/dependency panels lead or align with service impact and route to the dependency runbook.
- Silent behavior change: latency, traffic, and errors remain normal, behavior rises, and alert severity is Watch, not Page.
- Deploy-correlated behavior change: release dashboard shows version/config changes before behavior movement and rollback evidence.
- Behavior + quality drop: quality proxy degradation strengthens behavior evidence under configured policy.
- Recovery: burn, golden signals, dependency health, behavior, and quality return below watch thresholds.
- Stale baseline: trust panel warns and behavior alerts are suppressed or downgraded.
- Low traffic: low-volume state appears and behavior alerts are suppressed or downgraded.

Do not use passing syntax checks as the only publish gate. Inspect dashboard language, alert routing, screenshots, and runbooks against the SRE-plan checklist.
