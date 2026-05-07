# Production Readiness Checklist

Use this before adapting the recipe to a real service.

- [ ] You know where events are emitted in the inference path.
- [ ] Baseline events come from a known-good window.
- [ ] Labels are bounded and exclude users, requests, prompts, raw documents, and traces.
- [ ] Thresholds are calibrated per service/model/stream.
- [ ] Alerts are grouped and routed by service, environment, model, and stream.
- [ ] Deploy, model, prompt, index, and config markers are reliable.
- [ ] Dashboards have owners and runbooks.
- [ ] Delayed labels or quality proxies are used to validate false positives and misses.
- [ ] Baseline refresh is controlled and does not absorb active incidents.
- [ ] Optional RAG, agent, and source dashboards are enabled only when those events exist.
