"""Small public PyPI package smoke example for MetricChrono recipes."""

from __future__ import annotations

import metricchrono as mc


def main() -> None:
    tier = mc.Tier(0.03, 0.05, 0.5, 1.0)
    fine_tick = mc.tick_distance(0.075, tier)
    ladder = mc.geometric_ladder(0.03, 0.05, 2.6, 6, 0.5, 1.0)
    shock_ticks = mc.ladder_distance(1.62, ladder)
    consensus = mc.weighted_consensus(
        [
            [fine_tick, 0.0, 0.0, 0.0, 0.0, 0.0],
            shock_ticks,
            [fine_tick, fine_tick, 0.0, 0.0, 0.0, 0.0],
        ],
        [0.34, 0.33, 0.33],
    )
    print(
        "MetricChrono Python smoke: "
        f"fine_tick={fine_tick:.6f} shock_tiers={len(shock_ticks)} "
        f"consensus_tiers={len(consensus)}"
    )


if __name__ == "__main__":
    main()
