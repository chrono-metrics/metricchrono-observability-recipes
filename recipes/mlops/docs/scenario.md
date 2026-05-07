# Local Scenario

A model service receives steady traffic. Latency and error rate stay normal. Inputs slowly drift, embeddings move away from baseline, model outputs shift, a model version change causes a sharper behavior jump, and later behavior recovers.

The default local run plays this accelerated two-minute scenario once and then holds recovery. Restart the stack to replay it, or run `npm run mlops:serve -- --loop` when you explicitly want a looping demo.

| Phase | Start sample | End sample |
| --- | --- | --- |
| Normal | 0 | 19 |
| Small Input Noise | 20 | 39 |
| Gradual Data Drift | 40 | 69 |
| Model Change | 70 | 84 |
| Recovery | 85 | 119 |

## Assertions

- [x] Service health stays normal while behavior changes: request rate and latency are stable in the synthetic scenario
- [x] Normal phase has low behavior change: max Normal behavior change = 0.0
- [x] Small Input Noise does not create large movement: max large score during Small Input Noise = 0.0
- [x] Gradual Data Drift increases input change: input score 0.0 -> 75.3
- [x] Model Change creates the largest behavior jump: max Model Change behavior score = 90.9
- [x] Recovery lowers behavior change: final Recovery behavior score = 0.0
- [x] Behavior signal is visible before quality proxy fully drops: behavior score exceeds 25 while quality proxy is still above 94 during Gradual Data Drift
