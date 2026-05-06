#!/usr/bin/env python3
"""Verify demo alert thresholds can fire inside the accelerated scenario."""

from __future__ import annotations

from generate_assets import SAMPLE_COUNT, comparison_scores, scores_for, size_scores


def max_run(values: list[bool]) -> int:
    longest = 0
    current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def main() -> int:
    checks = {
        "BehaviorDriftWatch": (
            [scores_for(index)["behavior"] > 35 for index in range(SAMPLE_COUNT)],
            20,
        ),
        "PossibleAIBehaviorIncident": (
            [
                scores_for(index)["behavior"] > 75
                and size_scores(scores_for(index)["behavior"])["large"] > 25
                for index in range(SAMPLE_COUNT)
            ],
            10,
        ),
        "BehaviorChangedAfterDeploy": (
            [
                comparison_scores(index)["previous_model_version"]["behavior"] > 10 and index >= 70
                for index in range(SAMPLE_COUNT)
            ],
            10,
        ),
        "RetrievalBehaviorDrift": (
            [scores_for(index)["retrieval"] > 45 for index in range(SAMPLE_COUNT)],
            10,
        ),
        "AgentWorkflowChanged": (
            [scores_for(index)["agent"] > 20 for index in range(SAMPLE_COUNT)],
            10,
        ),
    }
    failures = []
    for name, (values, required_seconds) in checks.items():
        observed = max_run(values)
        if observed < required_seconds:
            failures.append(f"{name} max run {observed}s < required {required_seconds}s")
    if failures:
        print("Alert-window smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Alert-window smoke passed: demo alert conditions persist long enough to fire.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
