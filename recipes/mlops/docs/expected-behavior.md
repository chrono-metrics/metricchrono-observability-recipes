# What You Should See

Normal: service health is normal and behavior change is low.

Small Input Noise: small change rises, but large change stays quiet.

Gradual Data Drift: input and embedding change increase over time.

Model Change: behavior change spikes near the model-version marker.

Recovery: behavior change falls and status returns toward Normal.

The key lesson is that request rate, latency, and error rate can look healthy while AI behavior changes.

RAG, agent, and source-agreement dashboards are optional workload-specific views, not the newcomer entry path.
