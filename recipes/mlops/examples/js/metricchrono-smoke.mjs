import {
  geometricLadder,
  ladderDistance,
  tier,
  tickDistance,
  weightedConsensus,
} from "@metricchrono/core";

const fineTier = tier(0.03, 0.05, 0.5, 1.0);
const fineTick = tickDistance(0.075, fineTier);
const ladder = geometricLadder(0.03, 0.05, 2.6, 6, 0.5, 1.0);
const shockTicks = ladderDistance(1.62, ladder);
const consensus = weightedConsensus(
  [
    [fineTick, 0, 0, 0, 0, 0],
    shockTicks,
    [fineTick, fineTick, 0, 0, 0, 0],
  ],
  [0.34, 0.33, 0.33],
);

console.log(
  `MetricChrono JS smoke: fine_tick=${fineTick.toFixed(6)} ` +
    `shock_tiers=${shockTicks.length} consensus_tiers=${consensus.length}`,
);
