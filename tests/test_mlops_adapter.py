from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/python"))

from metricchrono_mlops_adapter import (  # noqa: E402
    BehaviorMonitor,
    CONTRACT_METRICS,
    emit_prometheus_metrics,
    build_demo_events,
    snapshots_for_events,
)


class MLOpsAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.events = build_demo_events()
        self.snapshots = snapshots_for_events(self.events)

    def phase_scores(self, phase: str) -> list[float]:
        return [snapshot.scores["behavior"] for snapshot in self.snapshots if snapshot.event.phase == phase]

    def test_scenario_shape(self) -> None:
        self.assertLess(max(self.phase_scores("Normal")), 15)
        self.assertLess(max(self.phase_scores("Small Input Noise")), 55)
        self.assertGreater(self.phase_scores("Gradual Data Drift")[-1], self.phase_scores("Gradual Data Drift")[0] + 25)
        self.assertGreater(max(self.phase_scores("Model Change")), max(self.phase_scores("Gradual Data Drift")) + 10)
        self.assertLess(self.phase_scores("Recovery")[-1], 15)

    def test_events_include_real_ml_surfaces(self) -> None:
        event = self.events[70]
        self.assertTrue(event.input_features)
        self.assertTrue(event.embedding)
        self.assertTrue(event.output_distribution)
        self.assertTrue(event.retrieved_ids)
        self.assertTrue(event.agent_steps)
        self.assertTrue(event.source_scores)

    def test_no_forbidden_label_like_fields_in_events(self) -> None:
        forbidden = {"user_id", "request_id", "trace_id", "prompt", "raw_query", "document_id"}
        for event in self.events:
            self.assertFalse(forbidden & set(event.__dict__))

    def test_classifier_style_events_without_source_scores(self) -> None:
        classifier_events = [
            event.__class__(
                **{
                    **event.__dict__,
                    "retrieved_ids": [],
                    "agent_steps": [],
                    "source_scores": {},
                }
            )
            for event in self.events[:24]
        ]
        monitor = BehaviorMonitor.from_baseline_events(classifier_events[:12])
        snapshot = monitor.observe(classifier_events[18])
        self.assertEqual(snapshot.distances["source_disagreement"], 0.0)
        self.assertEqual(snapshot.scores["source_disagreement"], 0.0)

    def test_prometheus_bridge_and_tick_vectors_are_present(self) -> None:
        snapshot = self.snapshots[70]
        self.assertTrue(snapshot.tick_vectors["output"])
        self.assertTrue(all(isinstance(value, float) for value in snapshot.tick_vectors["output"]))
        body = emit_prometheus_metrics(
            snapshot,
            baseline_age_seconds=3600,
            comparison_scores={"previous_model_version": {"behavior": 12.0}},
        )
        for metric_name in CONTRACT_METRICS:
            self.assertIn(metric_name, body)
        self.assertIn("metricchrono_ai_behavior_change_score", body)
        self.assertIn("metricchrono_ai_drift_state", body)
        self.assertIn("metricchrono_ai_change_score_by_size", body)
        self.assertIn("metricchrono_ai_request_duration_seconds_bucket", body)
        self.assertIn('comparison="previous_model_version"', body)
        self.assertIn('service="checkout-ai"', body)
        self.assertIn("metricchrono_ai_baseline_age_seconds", body)


if __name__ == "__main__":
    unittest.main()
