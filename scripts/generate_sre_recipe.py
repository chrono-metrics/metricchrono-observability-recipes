#!/usr/bin/env python3
"""Generate the SRE AI services recipe pack."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECIPE_ROOT = ROOT / "recipes" / "sre-ai-services"

DESCRIPTION_FIELDS = [
    "What this shows:",
    "Why you care:",
    "How to read it:",
    "What to do next:",
]

FORBIDDEN_LABELS = [
    "prompt",
    "request_id",
    "trace_id",
    "session_id",
    "user_id",
    "raw_text",
    "document_id",
    "tool_call_id",
    "span_id",
    "error_text",
]

STABLE_LABELS = [
    "service",
    "environment",
    "model",
    "model_version",
    "workload",
    "stream",
    "traffic_role",
    "comparison",
    "change_size",
    "component",
    "provider",
    "dependency",
    "error_class",
    "reason",
    "window",
    "state",
    "severity",
    "scenario_phase",
]

STATE_CODE = {"Normal": 0, "Watch": 1, "Incident": 2, "Recovering": 3}
STATE_COLOR = {"Normal": "green", "Watch": "yellow", "Incident": "red", "Recovering": "blue"}
HYPOTHESIS_CODE = {
    "normal": 0,
    "infra": 1,
    "capacity": 2,
    "dependency": 3,
    "deploy": 4,
    "behavior": 5,
    "retrieval": 6,
    "agent": 7,
    "mixed": 8,
    "recovering": 9,
}
HYPOTHESIS_COLOR = {
    "normal": "green",
    "infra": "red",
    "capacity": "orange",
    "dependency": "orange",
    "deploy": "yellow",
    "behavior": "yellow",
    "retrieval": "orange",
    "agent": "orange",
    "mixed": "red",
    "recovering": "blue",
}
ROLLOUT_CODE = {"stable": 0, "shadow": 1, "canary": 2, "paused": 3, "rollback": 4, "complete": 5}
ROLLOUT_COLOR = {"stable": "green", "shadow": "blue", "canary": "yellow", "paused": "orange", "rollback": "red", "complete": "green"}
TRUST_CODE = {"trusted": 0, "stale_baseline": 1, "low_volume": 2, "missing_source": 3}
TRUST_COLOR = {"trusted": "green", "stale_baseline": "orange", "low_volume": "yellow", "missing_source": "orange"}

CHANGE_THRESHOLDS = [
    {"color": "green", "value": None},
    {"color": "yellow", "value": 20},
    {"color": "orange", "value": 50},
    {"color": "red", "value": 75},
]

BURN_THRESHOLDS = [
    {"color": "green", "value": None},
    {"color": "yellow", "value": 1},
    {"color": "orange", "value": 6},
    {"color": "red", "value": 14.4},
]

RATIO_THRESHOLDS = [
    {"color": "green", "value": None},
    {"color": "yellow", "value": 0.6},
    {"color": "orange", "value": 0.8},
    {"color": "red", "value": 0.95},
]

SERVICE = "checkout-ai"
ENVIRONMENT = "demo"
MODEL = "assist-ranker"
STREAM = "support.answers"
WORKLOADS = ["interactive_chat", "ticket_summary"]
TRAFFIC_ROLES = ["stable", "canary", "shadow"]
CHANGE_SIZES = ["small", "medium", "large"]
COMPONENTS = ["input", "embedding", "output", "retrieval", "agent_workflow", "source_disagreement"]
ERROR_CLASSES = ["application", "provider", "timeout", "rate_limit", "policy_block", "malformed_request", "retrieval_failure", "tool_failure", "unknown"]
SLO_REASONS = ["availability_failure", "latency_violation", "dependency_failure", "timeout_failure", "quality_policy_failure"]
DEPENDENCIES = ["model_provider", "retriever", "vector_db", "tool_api", "cache"]
PROVIDERS = ["primary-llm", "embedding-api"]
RESOURCES = ["queue", "inflight", "concurrency", "provider_quota", "token_budget", "cpu", "gpu_memory"]
LATENCY_COMPONENTS = ["end_to_end", "queue", "provider", "retrieval", "tool_call", "response_streaming"]

PHASES = [
    {
        "name": "Normal",
        "slug": "normal",
        "file": "phase-metrics/01-normal.prom",
        "summary": "Traffic, latency, errors, saturation, dependencies, and behavior are normal.",
        "expected": "Current state is Normal, burn is sustainable, behavior is low, and no default alerts fire.",
        "profile": {
            "state": "Normal",
            "hypothesis": "normal",
            "rollout": "stable",
            "model_version": "v1",
            "app_version": "app-2026.05.01",
            "prompt_version": "prompt-14",
            "index_version": "index-2026-04-30",
            "config_version": "config-a",
            "request_rate": 120,
            "error_rate": 0.003,
            "latency": 0.42,
            "failed_latency": 0.18,
            "burn_short": 0.2,
            "burn_long": 0.1,
            "remaining_budget": 0.96,
            "queue_depth": 4,
            "inflight": 22,
            "saturation": 0.35,
            "provider_latency": 0.28,
            "provider_error_rate": 0.002,
            "provider_rate_limits": 0,
            "token_budget": 0.38,
            "behavior": 8,
            "quality": 0.97,
            "baseline_age": 1800,
            "sample_volume": 1800,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "trusted",
            "likely_cause": "normal",
            "next_step": "continue_monitoring",
            "runbook": "runbooks/behavior-changed-health-normal.md",
        },
    },
    {
        "name": "Infrastructure / capacity issue",
        "slug": "infra_capacity",
        "file": "phase-metrics/02-infra-capacity.prom",
        "summary": "Latency and saturation rise, and behavior-change stays secondary.",
        "expected": "Golden signals and burn show user impact; behavior panels do not claim AI behavior as primary cause.",
        "profile": {
            "state": "Incident",
            "hypothesis": "capacity",
            "rollout": "stable",
            "model_version": "v1",
            "app_version": "app-2026.05.01",
            "prompt_version": "prompt-14",
            "index_version": "index-2026-04-30",
            "config_version": "config-a",
            "request_rate": 180,
            "error_rate": 0.035,
            "latency": 1.9,
            "failed_latency": 1.1,
            "burn_short": 18.0,
            "burn_long": 5.0,
            "remaining_budget": 0.78,
            "queue_depth": 86,
            "inflight": 190,
            "saturation": 0.94,
            "provider_latency": 0.32,
            "provider_error_rate": 0.003,
            "provider_rate_limits": 1,
            "token_budget": 0.72,
            "behavior": 14,
            "quality": 0.95,
            "baseline_age": 2400,
            "sample_volume": 2600,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "trusted",
            "likely_cause": "capacity",
            "next_step": "open_latency_degraded_runbook",
            "runbook": "runbooks/latency-degraded.md",
        },
    },
    {
        "name": "Dependency/provider issue",
        "slug": "dependency_provider",
        "file": "phase-metrics/03-dependency-provider.prom",
        "summary": "Provider latency, provider errors, and rate limits rise before or alongside service impact.",
        "expected": "Dependency panels route investigation to the provider/dependency runbook.",
        "profile": {
            "state": "Incident",
            "hypothesis": "dependency",
            "rollout": "stable",
            "model_version": "v1",
            "app_version": "app-2026.05.01",
            "prompt_version": "prompt-14",
            "index_version": "index-2026-04-30",
            "config_version": "config-a",
            "request_rate": 125,
            "error_rate": 0.028,
            "latency": 1.35,
            "failed_latency": 0.92,
            "burn_short": 10.5,
            "burn_long": 4.2,
            "remaining_budget": 0.82,
            "queue_depth": 25,
            "inflight": 58,
            "saturation": 0.58,
            "provider_latency": 1.2,
            "provider_error_rate": 0.05,
            "provider_rate_limits": 16,
            "token_budget": 0.83,
            "behavior": 18,
            "quality": 0.94,
            "baseline_age": 2500,
            "sample_volume": 1750,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "trusted",
            "likely_cause": "provider_degraded",
            "next_step": "open_provider_dependency_runbook",
            "runbook": "runbooks/provider-dependency-degraded.md",
        },
    },
    {
        "name": "Silent AI-behavior change",
        "slug": "silent_behavior_change",
        "file": "phase-metrics/04-silent-behavior-change.prom",
        "summary": "Request rate, latency, and errors stay normal while behavior-change rises.",
        "expected": "Behavior alert is Watch, not Page, and next action routes to AI/model investigation.",
        "profile": {
            "state": "Watch",
            "hypothesis": "behavior",
            "rollout": "stable",
            "model_version": "v1",
            "app_version": "app-2026.05.01",
            "prompt_version": "prompt-14",
            "index_version": "index-2026-04-30",
            "config_version": "config-a",
            "request_rate": 118,
            "error_rate": 0.004,
            "latency": 0.45,
            "failed_latency": 0.2,
            "burn_short": 0.4,
            "burn_long": 0.2,
            "remaining_budget": 0.95,
            "queue_depth": 5,
            "inflight": 24,
            "saturation": 0.37,
            "provider_latency": 0.3,
            "provider_error_rate": 0.002,
            "provider_rate_limits": 0,
            "token_budget": 0.41,
            "behavior": 72,
            "quality": 0.95,
            "baseline_age": 2600,
            "sample_volume": 1900,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "trusted",
            "likely_cause": "ai_behavior_change",
            "next_step": "route_to_ai_owner",
            "runbook": "runbooks/behavior-changed-health-normal.md",
        },
    },
    {
        "name": "Deploy-correlated behavior change",
        "slug": "deploy_correlated_behavior",
        "file": "phase-metrics/05-deploy-correlated-behavior.prom",
        "summary": "A model, prompt, index, config, or app version becomes active before behavior changes.",
        "expected": "Release dashboard shows canary/stable difference and rollback evidence without paging solely on behavior.",
        "profile": {
            "state": "Watch",
            "hypothesis": "deploy",
            "rollout": "canary",
            "model_version": "v2",
            "app_version": "app-2026.05.07",
            "prompt_version": "prompt-15",
            "index_version": "index-2026-05-07",
            "config_version": "config-b",
            "request_rate": 126,
            "error_rate": 0.006,
            "latency": 0.52,
            "failed_latency": 0.22,
            "burn_short": 0.8,
            "burn_long": 0.3,
            "remaining_budget": 0.94,
            "queue_depth": 7,
            "inflight": 28,
            "saturation": 0.42,
            "provider_latency": 0.34,
            "provider_error_rate": 0.003,
            "provider_rate_limits": 1,
            "token_budget": 0.52,
            "behavior": 78,
            "quality": 0.93,
            "baseline_age": 2600,
            "sample_volume": 1850,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "trusted",
            "likely_cause": "release_behavior_regression",
            "next_step": "pause_canary_or_compare_previous_version",
            "runbook": "runbooks/release-behavior-regression.md",
        },
    },
    {
        "name": "Behavior + quality drop",
        "slug": "behavior_quality_drop",
        "file": "phase-metrics/06-behavior-quality-drop.prom",
        "summary": "Behavior-change rises and the delayed quality or business proxy degrades.",
        "expected": "Behavior plus quality evidence can become incident-level under configured policy.",
        "profile": {
            "state": "Incident",
            "hypothesis": "mixed",
            "rollout": "canary",
            "model_version": "v2",
            "app_version": "app-2026.05.07",
            "prompt_version": "prompt-15",
            "index_version": "index-2026-05-07",
            "config_version": "config-b",
            "request_rate": 124,
            "error_rate": 0.008,
            "latency": 0.55,
            "failed_latency": 0.24,
            "burn_short": 1.8,
            "burn_long": 0.9,
            "remaining_budget": 0.90,
            "queue_depth": 8,
            "inflight": 30,
            "saturation": 0.44,
            "provider_latency": 0.35,
            "provider_error_rate": 0.004,
            "provider_rate_limits": 1,
            "token_budget": 0.55,
            "behavior": 86,
            "quality": 0.72,
            "baseline_age": 2700,
            "sample_volume": 1880,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "trusted",
            "likely_cause": "behavior_plus_quality_drop",
            "next_step": "escalate_to_ai_owner_and_incident_commander",
            "runbook": "runbooks/behavior-change-quality-drop.md",
        },
    },
    {
        "name": "Stale baseline",
        "slug": "stale_baseline",
        "file": "phase-metrics/07-stale-baseline.prom",
        "summary": "Behavior movement appears while the baseline is stale.",
        "expected": "Baseline trust warns and behavior alerts are suppressed or downgraded.",
        "profile": {
            "state": "Watch",
            "hypothesis": "behavior",
            "rollout": "stable",
            "model_version": "v1",
            "app_version": "app-2026.05.01",
            "prompt_version": "prompt-14",
            "index_version": "index-2026-04-30",
            "config_version": "config-a",
            "request_rate": 95,
            "error_rate": 0.004,
            "latency": 0.48,
            "failed_latency": 0.22,
            "burn_short": 0.5,
            "burn_long": 0.2,
            "remaining_budget": 0.95,
            "queue_depth": 5,
            "inflight": 19,
            "saturation": 0.34,
            "provider_latency": 0.32,
            "provider_error_rate": 0.002,
            "provider_rate_limits": 0,
            "token_budget": 0.39,
            "behavior": 62,
            "quality": 0.96,
            "baseline_age": 95000,
            "sample_volume": 1500,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "stale_baseline",
            "likely_cause": "signal_trust_weak",
            "next_step": "refresh_or_review_baseline_before_escalation",
            "runbook": "runbooks/baseline-stale-low-volume.md",
        },
    },
    {
        "name": "Low traffic",
        "slug": "low_traffic",
        "file": "phase-metrics/08-low-traffic.prom",
        "summary": "Behavior movement appears with too little traffic to trust the sample.",
        "expected": "Low-volume state appears and behavior alerts are suppressed or downgraded.",
        "profile": {
            "state": "Watch",
            "hypothesis": "behavior",
            "rollout": "stable",
            "model_version": "v1",
            "app_version": "app-2026.05.01",
            "prompt_version": "prompt-14",
            "index_version": "index-2026-04-30",
            "config_version": "config-a",
            "request_rate": 6,
            "error_rate": 0.0,
            "latency": 0.44,
            "failed_latency": 0.2,
            "burn_short": 0.1,
            "burn_long": 0.1,
            "remaining_budget": 0.97,
            "queue_depth": 1,
            "inflight": 2,
            "saturation": 0.08,
            "provider_latency": 0.29,
            "provider_error_rate": 0.001,
            "provider_rate_limits": 0,
            "token_budget": 0.12,
            "behavior": 58,
            "quality": 0.96,
            "baseline_age": 2800,
            "sample_volume": 42,
            "low_traffic": 1,
            "missing_sources": 0,
            "trust": "low_volume",
            "likely_cause": "low_volume_behavior_signal",
            "next_step": "wait_for_minimum_volume_or_use_qualitative_review",
            "runbook": "runbooks/baseline-stale-low-volume.md",
        },
    },
    {
        "name": "Recovery",
        "slug": "recovery",
        "file": "phase-metrics/09-recovery.prom",
        "summary": "Mitigation occurs and SLO burn, dependency health, and behavior evidence return toward normal.",
        "expected": "Recovery panel confirms sustained service-health and behavior stabilization before closure.",
        "profile": {
            "state": "Recovering",
            "hypothesis": "recovering",
            "rollout": "rollback",
            "model_version": "v1",
            "app_version": "app-2026.05.01",
            "prompt_version": "prompt-14",
            "index_version": "index-2026-04-30",
            "config_version": "config-a",
            "request_rate": 116,
            "error_rate": 0.004,
            "latency": 0.47,
            "failed_latency": 0.21,
            "burn_short": 0.6,
            "burn_long": 0.4,
            "remaining_budget": 0.92,
            "queue_depth": 4,
            "inflight": 23,
            "saturation": 0.36,
            "provider_latency": 0.3,
            "provider_error_rate": 0.002,
            "provider_rate_limits": 0,
            "token_budget": 0.4,
            "behavior": 16,
            "quality": 0.96,
            "baseline_age": 3100,
            "sample_volume": 1750,
            "low_traffic": 0,
            "missing_sources": 0,
            "trust": "trusted",
            "likely_cause": "recovery_confirming",
            "next_step": "keep_watch_until_recovery_window_passes",
            "runbook": "runbooks/ai-service-slow-burn.md",
        },
    },
]

METRICS: dict[str, tuple[str, str]] = {
    "metricchrono_sre_ai_current_state_code": ("gauge", "0 normal, 1 watch, 2 incident, 3 recovering."),
    "metricchrono_sre_ai_incident_hypothesis_code": ("gauge", "Human-readable incident hypothesis code for state timelines."),
    "metricchrono_sre_ai_requests_total": ("counter", "AI service request count."),
    "metricchrono_sre_ai_errors_total": ("counter", "AI service error count by bounded error class."),
    "metricchrono_sre_ai_request_duration_seconds": ("histogram", "AI service request duration histogram."),
    "metricchrono_sre_ai_inflight_requests": ("gauge", "In-flight requests."),
    "metricchrono_sre_ai_queue_depth": ("gauge", "Request queue depth."),
    "metricchrono_sre_ai_concurrency_usage_ratio": ("gauge", "Concurrency usage ratio."),
    "metricchrono_sre_ai_token_budget_usage_ratio": ("gauge", "Token budget usage ratio."),
    "metricchrono_sre_ai_saturation_ratio": ("gauge", "Saturation ratio by bounded resource."),
    "metricchrono_sre_ai_latency_component_seconds": ("gauge", "Latency decomposition by component."),
    "metricchrono_sre_ai_slo_burn_rate": ("gauge", "Short and long-window error-budget burn rate."),
    "metricchrono_sre_ai_error_budget_remaining_ratio": ("gauge", "Remaining error budget ratio."),
    "metricchrono_sre_ai_slo_good_events_total": ("counter", "SLO good events."),
    "metricchrono_sre_ai_slo_bad_events_total": ("counter", "SLO bad events by reason."),
    "metricchrono_sre_ai_latency_violations_total": ("counter", "Latency SLI violations."),
    "metricchrono_sre_ai_availability_failures_total": ("counter", "Availability SLI failures."),
    "metricchrono_sre_ai_behavior_change_score": ("gauge", "Overall AI behavior-change score."),
    "metricchrono_sre_ai_behavior_component_score": ("gauge", "AI behavior-change score by operational component."),
    "metricchrono_sre_ai_change_score_by_size": ("gauge", "Behavior-change score split by small, medium, and large movement."),
    "metricchrono_sre_ai_behavior_state_code": ("gauge", "0 normal, 1 watch, 2 incident evidence, 3 recovering."),
    "metricchrono_sre_ai_quality_proxy": ("gauge", "Synthetic delayed quality or business proxy."),
    "metricchrono_sre_ai_baseline_age_seconds": ("gauge", "Age of behavior baseline."),
    "metricchrono_sre_ai_sample_volume": ("gauge", "Sample volume used for behavior evidence."),
    "metricchrono_sre_ai_sampled_request_rate": ("gauge", "Sampled request rate used for behavior evidence."),
    "metricchrono_sre_ai_missing_source_count": ("gauge", "Bounded count of missing behavior sources."),
    "metricchrono_sre_ai_low_traffic_flag": ("gauge", "One when traffic is below the configured minimum for behavior alerting."),
    "metricchrono_sre_ai_baseline_trust_state_code": ("gauge", "Behavior signal trust code."),
    "metricchrono_sre_ai_provider_requests_total": ("counter", "Provider request count."),
    "metricchrono_sre_ai_provider_errors_total": ("counter", "Provider error count."),
    "metricchrono_sre_ai_provider_duration_seconds": ("histogram", "Provider operation duration histogram."),
    "metricchrono_sre_ai_provider_rate_limits_total": ("counter", "Provider rate-limit event count."),
    "metricchrono_sre_ai_token_usage_total": ("counter", "Token usage or cost proxy counter."),
    "metricchrono_sre_ai_cost_proxy": ("gauge", "Synthetic cost proxy."),
    "metricchrono_sre_ai_retrieval_duration_seconds": ("histogram", "Retriever duration histogram."),
    "metricchrono_sre_ai_vector_db_duration_seconds": ("histogram", "Vector DB duration histogram."),
    "metricchrono_sre_ai_tool_call_duration_seconds": ("histogram", "Tool-call duration histogram."),
    "metricchrono_sre_ai_cache_hit_ratio": ("gauge", "Cache hit ratio."),
    "metricchrono_sre_ai_dependency_health_score": ("gauge", "Dependency health score from zero to one."),
    "metricchrono_sre_ai_app_version_active": ("gauge", "One when an app version is active."),
    "metricchrono_sre_ai_model_version_active": ("gauge", "One when a model version is active."),
    "metricchrono_sre_ai_prompt_version_active": ("gauge", "One when a prompt version is active."),
    "metricchrono_sre_ai_index_version_active": ("gauge", "One when a retriever index version is active."),
    "metricchrono_sre_ai_config_version_active": ("gauge", "One when a config version is active."),
    "metricchrono_sre_ai_rollout_state_code": ("gauge", "Rollout state code for stable, shadow, canary, paused, rollback, or complete."),
    "metricchrono_sre_ai_traffic_role_active": ("gauge", "One when a traffic role is serving traffic."),
    "metricchrono_sre_ai_previous_version_behavior_change_score": ("gauge", "Behavior-change score versus previous version."),
    "metricchrono_sre_ai_canary_behavior_difference_score": ("gauge", "Canary versus stable behavior difference."),
    "metricchrono_sre_ai_next_action_candidate": ("gauge", "Ranked blast-radius and next-action candidate."),
    "metricchrono_sre_ai_inspection_candidate": ("gauge", "Ranked inspection candidate for triage."),
    "metricchrono_sre_ai_rollback_evidence": ("gauge", "Release rollback evidence row."),
    "metricchrono_sre_ai_scenario_phase": ("gauge", "One-hot local SRE AI service scenario phase."),
}


def clean(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def description(what: str, why: str, how: str, next_action: str) -> str:
    return "\n\n".join(
        [
            f"What this shows:\n{what}",
            f"Why you care:\n{why}",
            f"How to read it:\n{how}",
            f"What to do next:\n{next_action}",
        ]
    )


def target(expr: str, legend: str, ref_id: str, *, table: bool = False) -> dict[str, Any]:
    item: dict[str, Any] = {
        "datasource": {"type": "prometheus", "uid": "${datasource}"},
        "editorMode": "code",
        "expr": expr,
        "legendFormat": legend,
        "refId": ref_id,
    }
    if table:
        item["format"] = "table"
        item["instant"] = True
        item["range"] = False
    elif ref_id == "A" and legend.endswith("current state"):
        item["instant"] = True
        item["range"] = False
    else:
        item["range"] = True
    return item


def value_mappings(codes: dict[str, int], colors: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "type": "value",
            "options": {
                str(code): {"text": label, "color": colors.get(label, "green")}
                for label, code in codes.items()
            },
        }
    ]


def mapping_override(pattern: str, mappings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "matcher": {"id": "byRegexp", "options": pattern},
        "properties": [{"id": "mappings", "value": mappings}],
    }


def make_panel(
    title: str,
    panel_type: str,
    what: str,
    why: str,
    how: str,
    next_action: str,
    targets: list[tuple[str, str]],
    *,
    unit: str = "short",
    width: int = 12,
    height: int = 8,
    thresholds: list[dict[str, Any]] | None = None,
    mappings: list[dict[str, Any]] | None = None,
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if panel_type == "table":
        width = 24
    options: dict[str, Any]
    transformations: list[dict[str, Any]] = []
    if panel_type == "table":
        options = {"cellHeight": "sm", "showHeader": True}
        transformations = [
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True, "Value": True, "__name__": True},
                    "renameByName": {
                        "model_version": "model version",
                        "traffic_role": "traffic role",
                        "likely_cause": "likely cause",
                        "next_step": "next step",
                        "slo_state": "SLO state",
                        "behavior_state": "behavior state",
                        "runbook": "runbook",
                    },
                },
            }
        ]
    elif panel_type == "state-timeline":
        options = {
            "legend": {"displayMode": "list", "placement": "bottom"},
            "mergeValues": True,
            "rowHeight": 0.9,
            "showValue": "never",
        }
    else:
        options = {"legend": {"displayMode": "list", "placement": "bottom"}}
    defaults: dict[str, Any] = {
        "unit": unit,
        "thresholds": {"mode": "absolute", "steps": thresholds or CHANGE_THRESHOLDS},
    }
    if mappings:
        defaults["mappings"] = mappings
    panel = {
        "title": title,
        "type": panel_type,
        "description": description(what, why, how, next_action),
        "datasource": {"type": "prometheus", "uid": "${datasource}"},
        "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
        "options": options,
        "targets": [
            target(expr, legend, chr(ord("A") + index), table=panel_type == "table")
            for index, (expr, legend) in enumerate(targets)
        ],
        "gridPos": {"h": height, "w": width, "x": 0, "y": 0},
    }
    if transformations:
        panel["transformations"] = transformations
    return panel


def apply_grid(panels: list[dict[str, Any]]) -> None:
    x = 0
    y = 0
    row_height = 0
    for panel in panels:
        width = panel["gridPos"]["w"]
        height = panel["gridPos"]["h"]
        if width >= 24:
            if x:
                y += row_height
                x = 0
                row_height = 0
            panel["gridPos"] = {"h": height, "w": 24, "x": 0, "y": y}
            y += height
            continue
        if x + width > 24:
            y += row_height
            x = 0
            row_height = 0
        panel["gridPos"] = {"h": height, "w": width, "x": x, "y": y}
        x += width
        row_height = max(row_height, height)
        if x >= 24:
            y += row_height
            x = 0
            row_height = 0


def dashboard(title: str, panels: list[dict[str, Any]], tags: list[str]) -> dict[str, Any]:
    apply_grid(panels)
    return {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "panels": panels,
        "schemaVersion": 39,
        "tags": tags,
        "templating": {
            "list": [
                {"name": "datasource", "type": "datasource", "query": "prometheus", "current": {"text": "Prometheus", "value": "Prometheus"}},
                {"name": "service", "type": "textbox", "query": SERVICE, "current": {"text": SERVICE, "value": SERVICE}},
                {"name": "environment", "type": "textbox", "query": ENVIRONMENT, "current": {"text": ENVIRONMENT, "value": ENVIRONMENT}},
                {"name": "model", "type": "textbox", "query": MODEL, "current": {"text": MODEL, "value": MODEL}},
                {"name": "model_version", "type": "textbox", "query": ".*", "current": {"text": ".*", "value": ".*"}},
                {"name": "workload", "type": "textbox", "query": "interactive_chat", "current": {"text": "interactive_chat", "value": "interactive_chat"}},
                {"name": "stream", "type": "textbox", "query": STREAM, "current": {"text": STREAM, "value": STREAM}},
                {"name": "traffic_role", "type": "textbox", "query": "stable|canary", "current": {"text": "stable|canary", "value": "stable|canary"}},
                {"name": "comparison", "type": "textbox", "query": "known_good_baseline", "current": {"text": "known_good_baseline", "value": "known_good_baseline"}},
                {"name": "change_size", "type": "textbox", "query": "small|medium|large", "current": {"text": "small|medium|large", "value": "small|medium|large"}},
            ]
        },
        "time": {"from": "now-6h", "to": "now"},
        "timezone": "browser",
        "title": title,
        "uid": title.lower().replace(" ", "-"),
        "version": 1,
        "refresh": "30s",
    }


def base_labels(extra: str = "") -> str:
    pieces = [
        'service=~"$service"',
        'environment=~"$environment"',
        'model=~"$model"',
        'model_version=~"$model_version"',
        'workload=~"$workload"',
        'stream=~"$stream"',
    ]
    if "traffic_role" not in extra:
        pieces.append('traffic_role=~"$traffic_role"')
    labels = ",".join(pieces)
    if extra:
        labels += "," + extra
    return labels


def e(metric: str, extra: str = "") -> str:
    return f"{metric}{{{base_labels(extra)}}}"


def sum_by(labels: str, expr: str) -> str:
    return f"sum by ({labels}) ({expr})"


def max_by(labels: str, expr: str) -> str:
    return f"max by ({labels}) ({expr})"


def rate(expr: str, window: str = "2m") -> str:
    return f"rate({expr}[{window}])"


def hist(quantile: str, metric: str, by: str = "le") -> str:
    return f"histogram_quantile({quantile}, sum by ({by}) (rate({metric}[2m])))"


def state_overrides() -> list[dict[str, Any]]:
    return [
        mapping_override(".*state.*|.*current.*", value_mappings(STATE_CODE, STATE_COLOR)),
        mapping_override(".*hypothesis.*", value_mappings(HYPOTHESIS_CODE, HYPOTHESIS_COLOR)),
        mapping_override(".*rollout.*", value_mappings(ROLLOUT_CODE, ROLLOUT_COLOR)),
        mapping_override(".*trust.*", value_mappings(TRUST_CODE, TRUST_COLOR)),
    ]


def dashboards() -> dict[str, dict[str, Any]]:
    p95_success = hist("0.95", e("metricchrono_sre_ai_request_duration_seconds_bucket", 'outcome="success"'))
    p99_success = hist("0.99", e("metricchrono_sre_ai_request_duration_seconds_bucket", 'outcome="success"'))
    p95_failed = hist("0.95", e("metricchrono_sre_ai_request_duration_seconds_bucket", 'outcome="failed"'))
    provider_p95 = hist("0.95", e("metricchrono_sre_ai_provider_duration_seconds_bucket", 'provider=~".*"'))
    retrieval_p95 = hist("0.95", e("metricchrono_sre_ai_retrieval_duration_seconds_bucket", 'dependency="retriever"'))
    tool_p95 = hist("0.95", e("metricchrono_sre_ai_tool_call_duration_seconds_bucket", 'dependency="tool_api"'))
    error_rate = sum_by("service", rate(e("metricchrono_sre_ai_errors_total")))
    request_rate = sum_by("service", rate(e("metricchrono_sre_ai_requests_total")))

    overview = [
        make_panel(
            "Current incident state",
            "stat",
            "One operational state: Normal, Watch, Incident, or Recovering.",
            "This is the first decision point for whether the on-call engineer acts now.",
            "Compare SLO burn, latency, errors, dependency health, deploy state, and behavior evidence; behavior-change alone can raise Watch but does not force Incident.",
            "If the state is Incident, open AI Incident Triage; if it is Watch, inspect the top next-action row.",
            [(max_by("service, environment", e("metricchrono_sre_ai_current_state_code")), "{{service}} current state")],
            unit="short",
            width=8,
            height=6,
            mappings=value_mappings(STATE_CODE, STATE_COLOR),
            overrides=state_overrides(),
        ),
        make_panel(
            "Is this burning error budget?",
            "timeseries",
            "Short-window and long-window SLO burn plus remaining budget.",
            "SREs page on user impact and error-budget risk, not on interesting behavior movement alone.",
            "Compare burn against 1x sustainable burn and fast/slow burn thresholds; burn above the fast threshold means page-worthy impact.",
            "Open the slow or fast burn runbook depending on which threshold is crossed.",
            [
                (e("metricchrono_sre_ai_slo_burn_rate", 'window="short"'), "{{traffic_role}} short burn"),
                (e("metricchrono_sre_ai_slo_burn_rate", 'window="long"'), "{{traffic_role}} long burn"),
                (e("metricchrono_sre_ai_error_budget_remaining_ratio"), "{{traffic_role}} remaining budget"),
                ("vector(1)", "1x sustainable burn"),
                ("vector(14.4)", "fast-burn page threshold"),
            ],
            unit="short",
            width=16,
            height=6,
            thresholds=BURN_THRESHOLDS,
        ),
        make_panel(
            "Traffic and saturation",
            "timeseries",
            "Request rate beside in-flight requests, queue depth, concurrency, and token budget usage.",
            "This separates overload or traffic loss from an AI-behavior-only issue.",
            "Compare current traffic to the known-good band and saturation to capacity limits; rising traffic plus queue and latency points to capacity.",
            "If saturation leads latency, use the latency-degraded runbook and inspect capacity controls.",
            [
                (request_rate, "requests/sec"),
                (e("metricchrono_sre_ai_inflight_requests"), "{{traffic_role}} in flight"),
                (e("metricchrono_sre_ai_queue_depth"), "{{traffic_role}} queue"),
                (e("metricchrono_sre_ai_concurrency_usage_ratio"), "{{traffic_role}} concurrency usage"),
                (e("metricchrono_sre_ai_token_budget_usage_ratio"), "{{traffic_role}} token budget usage"),
            ],
            unit="short",
            thresholds=RATIO_THRESHOLDS,
        ),
        make_panel(
            "Latency: successful vs failed requests",
            "timeseries",
            "Successful-request p50, p95, and p99 latency beside failed-request latency.",
            "Mixing successful and failed latency can hide slow successful requests or fast failures.",
            "Compare successful-request latency to the latency SLO and known-good p95/p99 bands; slow failures plus queue growth are worse than fast failures.",
            "If latency is high, open the triage latency decomposition and latency-degraded runbook.",
            [
                (hist("0.50", e("metricchrono_sre_ai_request_duration_seconds_bucket", 'outcome="success"')), "success p50"),
                (p95_success, "success p95"),
                (p99_success, "success p99"),
                (p95_failed, "failed p95"),
                ("vector(1.0)", "latency SLO target"),
            ],
            unit="s",
        ),
        make_panel(
            "What kind of errors are users seeing?",
            "timeseries",
            "Error rate split by application, provider, timeout, rate limit, policy, retrieval, tool, and unknown classes.",
            "Error class is routing information for the on-call engineer.",
            "Compare each class to its normal baseline; provider and rate-limit errors route to dependency investigation, while policy blocks may indicate prompt or input shift.",
            "Open the error decomposition panel and the matching runbook for the dominant error class.",
            [(sum_by("error_class", rate(e("metricchrono_sre_ai_errors_total", 'error_class=~".*"'))), "{{error_class}}")],
            unit="ops",
        ),
        make_panel(
            "Is AI behavior changing while service health is normal?",
            "timeseries",
            "Behavior-change score beside error rate, p95 latency, and quality proxy.",
            "This catches silent AI behavior movement when golden signals are green.",
            "Compare behavior-change to the normal baseline while checking latency, errors, and quality; behavior rising with normal health routes to AI/model owners, not infrastructure restarts.",
            "Open AI Incident Triage and use the behavior-changed runbook.",
            [
                (e("metricchrono_sre_ai_behavior_change_score", 'comparison=~"$comparison"'), "{{traffic_role}} behavior"),
                (error_rate, "error rate"),
                (p95_success, "success p95"),
                (e("metricchrono_sre_ai_quality_proxy"), "{{traffic_role}} quality proxy"),
            ],
            unit="short",
        ),
        make_panel(
            "Did this start after a deploy?",
            "state-timeline",
            "Active app, model, prompt, index, and config versions for deploy correlation.",
            "Recent changes are often the fastest path to mitigation or rollback.",
            "Compare before and after deploy windows; if behavior jumps after a version becomes active, inspect rollout, prompt, model, index, or config.",
            "Open AI Release Guardrail for canary, stable, previous-version, and rollback evidence.",
            [
                (max_by("app_version", e("metricchrono_sre_ai_app_version_active", 'app_version=~".*"')), "app {{app_version}}"),
                (max_by("active_model_version", e("metricchrono_sre_ai_model_version_active", 'active_model_version=~".*"')), "model {{active_model_version}}"),
                (max_by("prompt_version", e("metricchrono_sre_ai_prompt_version_active", 'prompt_version=~".*"')), "prompt {{prompt_version}}"),
                (max_by("index_version", e("metricchrono_sre_ai_index_version_active", 'index_version=~".*"')), "index {{index_version}}"),
                (max_by("config_version", e("metricchrono_sre_ai_config_version_active", 'config_version=~".*"')), "config {{config_version}}"),
            ],
            unit="short",
            overrides=state_overrides(),
        ),
        make_panel(
            "Are AI dependencies healthy?",
            "timeseries",
            "Provider latency, provider errors, rate limits, token usage, retrieval latency, tool latency, and cache hit ratio.",
            "AI incidents often originate in hosted models, vector stores, retrievers, tools, or cache paths.",
            "Compare dependency p95 against service p95 and provider errors against local errors; dependency degradation leading service degradation routes away from app debugging.",
            "Use the provider dependency runbook if provider or retrieval signals lead the incident.",
            [
                (provider_p95, "provider p95"),
                (sum_by("provider", rate(e("metricchrono_sre_ai_provider_errors_total", 'provider=~".*"'))), "{{provider}} errors"),
                (sum_by("provider", rate(e("metricchrono_sre_ai_provider_rate_limits_total", 'provider=~".*"'))), "{{provider}} rate limits"),
                (retrieval_p95, "retrieval p95"),
                (tool_p95, "tool p95"),
                (e("metricchrono_sre_ai_cache_hit_ratio", 'dependency="cache"'), "cache hit ratio"),
            ],
            unit="short",
        ),
        make_panel(
            "Blast radius and next action",
            "table",
            "Ranked service, environment, model, workload, stream, SLO state, behavior state, likely cause, next step, and runbook.",
            "This turns the overview into a runbook entry point.",
            "Compare rows by severity, burn, dependency health, behavior-change, and deploy correlation; the top row is the best next place to inspect.",
            "Follow the top row and open the linked runbook or dashboard.",
            [(e("metricchrono_sre_ai_next_action_candidate", 'rank=~".*"'), "{{rank}} {{likely_cause}}")],
            unit="short",
            height=7,
        ),
    ]

    triage = [
        make_panel(
            "Incident hypothesis timeline",
            "state-timeline",
            "The incident class over time: normal, infra, capacity, dependency, deploy, behavior, retrieval, agent, mixed, or recovering.",
            "SREs route incidents by hypothesis, not by raw metric families.",
            "Compare golden signals, dependency health, deploy markers, behavior-change, and quality proxy; the state sequence should tell the incident story.",
            "Use the next panel matching the active hypothesis.",
            [(max_by("service, environment", e("metricchrono_sre_ai_incident_hypothesis_code")), "{{service}} hypothesis")],
            unit="short",
            mappings=value_mappings(HYPOTHESIS_CODE, HYPOTHESIS_COLOR),
            overrides=state_overrides(),
        ),
        make_panel(
            "What is consuming the SLO?",
            "timeseries",
            "SLO bad-event contribution by availability, latency, dependency, timeout, and configured quality-policy reasons.",
            "Burn rate without reason is hard to triage.",
            "Compare bad-event reasons to total request volume and burn rate; behavior-change is not counted as a bad event by default.",
            "Investigate the largest bad-event band first.",
            [(sum_by("reason", rate(e("metricchrono_sre_ai_slo_bad_events_total", 'reason=~".*"'))), "{{reason}}")],
            unit="ops",
        ),
        make_panel(
            "Where is latency coming from?",
            "timeseries",
            "End-to-end latency decomposed into queue, provider, retrieval, tool-call, and response-streaming components.",
            "AI latency is usually hidden inside dependency, retrieval, queueing, or streaming paths.",
            "Compare each component to its known-good p95/p99; the component that rises first is the likely bottleneck.",
            "Open the runbook for the leading component and inspect saturation.",
            [(e("metricchrono_sre_ai_latency_component_seconds", 'component=~".*"'), "{{component}}")],
            unit="s",
        ),
        make_panel(
            "Which error path is active?",
            "timeseries",
            "Application, provider, timeout, rate-limit, malformed input, policy, retrieval, and tool failures.",
            "The error path determines the owner and first debugging step.",
            "Compare class rates to the baseline and SLO bad-event contribution; malformed input with behavior-change points to input shift, provider errors point to dependency.",
            "Use the matching runbook for the dominant class.",
            [(sum_by("error_class", rate(e("metricchrono_sre_ai_errors_total", 'error_class=~".*"'))), "{{error_class}}")],
            unit="ops",
        ),
        make_panel(
            "What is saturated?",
            "timeseries",
            "Queue, in-flight, concurrency, provider quota, token budget, CPU, and GPU memory saturation.",
            "Saturation often precedes latency and errors.",
            "Compare each resource to the capacity limit and warning threshold; the first resource to rise is the capacity lead.",
            "Mitigate the leading resource and verify burn recovery.",
            [(e("metricchrono_sre_ai_saturation_ratio", 'resource=~".*"'), "{{resource}}")],
            unit="percentunit",
            thresholds=RATIO_THRESHOLDS,
        ),
        make_panel(
            "What AI behavior changed?",
            "bargauge",
            "Input, embedding, output, retrieval, agent workflow, and source disagreement scores.",
            "This translates AI behavior evidence into owner routing.",
            "Compare each component against the normal baseline; output high with input low suggests model or prompt, retrieval high suggests RAG or index, agent high suggests tool workflow.",
            "Route the investigation to the owner of the highest component.",
            [(e("metricchrono_sre_ai_behavior_component_score", 'component=~".*",comparison=~"$comparison"'), "{{component}}")],
            unit="percent",
        ),
        make_panel(
            "Is this small noise or major movement?",
            "timeseries",
            "Behavior-change split into small, medium, and large movement.",
            "Not every behavior movement deserves the same response.",
            "Compare small, medium, and large movement; small-only movement is weak evidence, sustained large movement is strong evidence, and large plus quality or SLO impact can become incident-level.",
            "If large movement persists, inspect behavior components and release correlation.",
            [(max_by("change_size", e("metricchrono_sre_ai_change_score_by_size", 'change_size=~"$change_size"')), "{{change_size}}")],
            unit="percent",
        ),
        make_panel(
            "What changed before the incident?",
            "state-timeline",
            "Rollout state plus active app and model versions for incident change correlation.",
            "Rollback and canary decisions depend on recent change correlation.",
            "Compare current versus previous version and before versus after deploy windows; a rollout or version switch near impact routes the next check to the release owner.",
            "Open AI Release Guardrail for rollback evidence.",
            [
                (max_by("traffic_role", e("metricchrono_sre_ai_rollout_state_code")), "{{traffic_role}} rollout"),
                (max_by("app_version", e("metricchrono_sre_ai_app_version_active", 'app_version=~".*"')), "app {{app_version}}"),
                (max_by("active_model_version", e("metricchrono_sre_ai_model_version_active", 'active_model_version=~".*"')), "model {{active_model_version}}"),
            ],
            unit="short",
            overrides=state_overrides(),
        ),
        make_panel(
            "Can I trust the behavior signal?",
            "timeseries",
            "Baseline age, sample volume, sampled request rate, missing-source count, low-traffic flag, and trust state.",
            "SREs need confidence before acting on a nontraditional signal.",
            "Compare baseline age to refresh policy, request volume to the minimum-volume rule, and missing sources to zero; stale or low-volume states weaken behavior alerts.",
            "Use the baseline-stale-low-volume runbook before escalating on behavior evidence.",
            [
                (e("metricchrono_sre_ai_baseline_age_seconds"), "{{traffic_role}} baseline age"),
                (e("metricchrono_sre_ai_sample_volume"), "{{traffic_role}} sample volume"),
                (e("metricchrono_sre_ai_sampled_request_rate"), "{{traffic_role}} sampled RPS"),
                (e("metricchrono_sre_ai_missing_source_count"), "{{traffic_role}} missing sources"),
                (e("metricchrono_sre_ai_low_traffic_flag"), "{{traffic_role}} low traffic"),
                (e("metricchrono_sre_ai_baseline_trust_state_code"), "{{traffic_role}} trust"),
            ],
            unit="short",
            overrides=state_overrides(),
        ),
        make_panel(
            "Is user quality dropping too?",
            "timeseries",
            "Behavior-change score beside delayed quality or business proxy.",
            "This separates harmless behavior movement from harmful regression evidence.",
            "Compare behavior movement against quality proxy and configured quality threshold; behavior leading quality drop is early warning, while behavior plus quality drop is stronger incident evidence.",
            "Use the behavior-change-quality-drop runbook if quality degradation appears.",
            [
                (e("metricchrono_sre_ai_behavior_change_score"), "{{traffic_role}} behavior"),
                (e("metricchrono_sre_ai_quality_proxy"), "{{traffic_role}} quality proxy"),
                ("vector(0.85)", "quality incident threshold"),
            ],
            unit="short",
        ),
        make_panel(
            "What should I inspect first?",
            "table",
            "Ranked stream, workload, model version, likely cause, current state, next step, and runbook.",
            "The dashboard should reduce first-response time.",
            "Compare candidates by severity, burn, dependency degradation, deploy correlation, and behavior-change; start with the top row.",
            "Open the named runbook or follow the row's next step.",
            [(e("metricchrono_sre_ai_inspection_candidate", 'rank=~".*"'), "{{rank}} {{likely_cause}}")],
            unit="short",
        ),
        make_panel(
            "Has the service recovered?",
            "timeseries",
            "Burn, latency, error rate, dependency health, behavior-change score, and quality proxy.",
            "SREs need exit criteria before closing or downgrading an incident.",
            "Compare all signals against recovery thresholds for a sustained window; recovery requires service-health recovery and behavior or quality stabilization when behavior was involved.",
            "Keep the incident in Recovering until the configured recovery window passes.",
            [
                (e("metricchrono_sre_ai_slo_burn_rate", 'window="short"'), "{{traffic_role}} short burn"),
                (p95_success, "success p95"),
                (error_rate, "error rate"),
                (e("metricchrono_sre_ai_dependency_health_score", 'dependency=~".*"'), "{{dependency}} health"),
                (e("metricchrono_sre_ai_behavior_change_score"), "{{traffic_role}} behavior"),
                (e("metricchrono_sre_ai_quality_proxy"), "{{traffic_role}} quality"),
            ],
            unit="short",
        ),
    ]

    release = [
        make_panel(
            "Rollout state",
            "state-timeline",
            "Stable, canary, shadow, paused, rollback, and complete state with active app/model/prompt/index/config versions.",
            "Release state is the first fact needed for rollback decisions.",
            "Compare rollout phase with SLO, behavior, and dependency panels; any behavior or SLO issue must be interpreted against what is live.",
            "Inspect the canary user-impact and behavior difference panels next.",
            [
                (max_by("traffic_role", e("metricchrono_sre_ai_rollout_state_code")), "{{traffic_role}} rollout"),
                (max_by("app_version", e("metricchrono_sre_ai_app_version_active", 'app_version=~".*"')), "app {{app_version}}"),
                (max_by("active_model_version", e("metricchrono_sre_ai_model_version_active", 'active_model_version=~".*"')), "model {{active_model_version}}"),
                (max_by("prompt_version", e("metricchrono_sre_ai_prompt_version_active", 'prompt_version=~".*"')), "prompt {{prompt_version}}"),
                (max_by("index_version", e("metricchrono_sre_ai_index_version_active", 'index_version=~".*"')), "index {{index_version}}"),
                (max_by("config_version", e("metricchrono_sre_ai_config_version_active", 'config_version=~".*"')), "config {{config_version}}"),
            ],
            unit="short",
            overrides=state_overrides(),
        ),
        make_panel(
            "Canary user impact",
            "timeseries",
            "Canary versus stable error rate, p95 latency, and SLO burn.",
            "SREs prioritize user impact before behavior analysis.",
            "Compare canary to stable and canary to the SLO; if canary is worse on user-facing SLIs, pause or roll back before deeper behavior work.",
            "If user impact is present, use the fast-burn or latency runbook.",
            [
                (sum_by("traffic_role", rate(e("metricchrono_sre_ai_errors_total", 'traffic_role=~"canary|stable"'))), "{{traffic_role}} errors"),
                (hist("0.95", e("metricchrono_sre_ai_request_duration_seconds_bucket", 'traffic_role=~"canary|stable",outcome="success"'), by="le,traffic_role"), "{{traffic_role}} p95"),
                (e("metricchrono_sre_ai_slo_burn_rate", 'traffic_role=~"canary|stable",window="short"'), "{{traffic_role}} short burn"),
            ],
            unit="short",
        ),
        make_panel(
            "Canary behavior difference",
            "timeseries",
            "Behavior-change comparing canary to stable and previous version.",
            "AI releases can change behavior before classic service metrics fail.",
            "Compare canary against stable, previous version, and watch/incident bands; a high difference with normal SLIs means investigate before full rollout.",
            "Use release-behavior-regression runbook if the difference persists.",
            [
                (e("metricchrono_sre_ai_canary_behavior_difference_score", 'traffic_role="canary"'), "canary vs stable"),
                (e("metricchrono_sre_ai_previous_version_behavior_change_score", 'traffic_role="canary"'), "canary vs previous version"),
                ("vector(50)", "watch band"),
                ("vector(75)", "incident evidence band"),
            ],
            unit="percent",
        ),
        make_panel(
            "What changed in the canary?",
            "bargauge",
            "Canary input, embedding, output, retrieval, agent workflow, and source disagreement differences.",
            "This points the rollout issue to the owning team.",
            "Compare canary components against stable and previous version; output high with input low points to model or prompt, retrieval high points to index or retriever, and agent high points to tools.",
            "Route to the owner of the highest canary component.",
            [(e("metricchrono_sre_ai_behavior_component_score", 'traffic_role="canary",component=~".*"'), "{{component}}")],
            unit="percent",
        ),
        make_panel(
            "Dependency and cost difference",
            "timeseries",
            "Token usage, provider duration, provider rate limits, provider errors, and cost proxy for canary versus stable.",
            "AI releases can regress cost and capacity even when quality is acceptable.",
            "Compare canary to stable and previous version; more tokens or slower provider calls may be a release regression.",
            "Pause rollout if dependency or cost regression is material.",
            [
                (sum_by("traffic_role", rate(e("metricchrono_sre_ai_token_usage_total", 'traffic_role=~"canary|stable"'))), "{{traffic_role}} tokens/sec"),
                (hist("0.95", e("metricchrono_sre_ai_provider_duration_seconds_bucket", 'traffic_role=~"canary|stable",provider=~".*"'), by="le,traffic_role"), "{{traffic_role}} provider p95"),
                (sum_by("traffic_role", rate(e("metricchrono_sre_ai_provider_rate_limits_total", 'traffic_role=~"canary|stable"'))), "{{traffic_role}} rate limits"),
                (sum_by("traffic_role", rate(e("metricchrono_sre_ai_provider_errors_total", 'traffic_role=~"canary|stable"'))), "{{traffic_role}} provider errors"),
                (e("metricchrono_sre_ai_cost_proxy", 'traffic_role=~"canary|stable"'), "{{traffic_role}} cost proxy"),
            ],
            unit="short",
        ),
        make_panel(
            "Blast radius by workload",
            "table",
            "Workload, service, environment, model, version, traffic role, SLO state, behavior state, and quality proxy.",
            "Scope determines whether to pause a canary or investigate a global issue.",
            "Compare canary versus stable and top affected workloads by severity; if only canary is affected, pause rollout.",
            "Use the top affected workload to target mitigation.",
            [(e("metricchrono_sre_ai_next_action_candidate", 'rank=~".*"'), "{{workload}} {{traffic_role}}")],
            unit="short",
        ),
        make_panel(
            "Rollback evidence",
            "table",
            "Signal, current value, comparator, severity, first seen, owner, and suggested action.",
            "Rollback recommendations need evidence, not just a graph.",
            "Compare SLO burn, canary versus stable, previous-version behavior, quality proxy, and dependency health; rows should make the rollback argument explicit.",
            "Use the suggested action and owner in the change-management workflow.",
            [(e("metricchrono_sre_ai_rollback_evidence", 'signal=~".*"'), "{{signal}} {{severity}}")],
            unit="short",
        ),
        make_panel(
            "Post-rollback recovery",
            "timeseries",
            "Active version, SLO burn, latency, error rate, behavior-change, and quality proxy after rollback.",
            "SREs need verification, not just a rollback event.",
            "Compare pre-rollback to post-rollback; if service health recovers but behavior remains changed, rollback may have fixed infrastructure but not AI behavior.",
            "Keep watching until all configured recovery conditions are below thresholds.",
            [
                (e("metricchrono_sre_ai_model_version_active", 'active_model_version=~".*"'), "model {{active_model_version}} active"),
                (e("metricchrono_sre_ai_slo_burn_rate", 'window="short"'), "{{traffic_role}} short burn"),
                (p95_success, "success p95"),
                (error_rate, "error rate"),
                (e("metricchrono_sre_ai_behavior_change_score"), "{{traffic_role}} behavior"),
                (e("metricchrono_sre_ai_quality_proxy"), "{{traffic_role}} quality"),
            ],
            unit="short",
        ),
    ]

    return {
        "ai-service-on-call-overview.json": dashboard("AI Service On-Call Overview", overview, ["sre-ai-services", "overview"]),
        "ai-incident-triage.json": dashboard("AI Incident Triage", triage, ["sre-ai-services", "triage"]),
        "ai-release-guardrail.json": dashboard("AI Release Guardrail", release, ["sre-ai-services", "release"]),
    }


def labels_text(labels: dict[str, str]) -> str:
    return "{" + ",".join(f'{key}="{labels[key]}"' for key in sorted(labels)) + "}"


def sample_line(name: str, labels: dict[str, str], value: float | int) -> str:
    return f"{name}{labels_text(labels)} {value}"


def emit_histogram(name: str, labels: dict[str, str], observations: list[float], buckets: list[float], multiplier: int) -> list[str]:
    lines: list[str] = []
    for bucket in buckets:
        count = sum(1 for value in observations if value <= bucket) * multiplier
        lines.append(sample_line(f"{name}_bucket", labels | {"le": str(bucket)}, count))
    lines.append(sample_line(f"{name}_bucket", labels | {"le": "+Inf"}, len(observations) * multiplier))
    lines.append(sample_line(f"{name}_sum", labels, round(sum(observations) * multiplier, 6)))
    lines.append(sample_line(f"{name}_count", labels, len(observations) * multiplier))
    return lines


def metric_header() -> list[str]:
    output: list[str] = []
    for metric, (metric_type, help_text) in METRICS.items():
        output.append(f"# HELP {metric} {help_text}")
        output.append(f"# TYPE {metric} {metric_type}")
    return output


def role_factor(role: str, phase: dict[str, Any]) -> float:
    if role == "stable":
        return 1.0
    if role == "canary":
        return 1.18 if phase["profile"]["rollout"] == "canary" else 0.12
    return 0.05


def component_value(component: str, behavior: float, phase_slug: str) -> float:
    if phase_slug in {"silent_behavior_change", "deploy_correlated_behavior", "behavior_quality_drop"}:
        weights = {
            "input": 0.42,
            "embedding": 0.55,
            "output": 1.0,
            "retrieval": 0.72 if phase_slug == "deploy_correlated_behavior" else 0.48,
            "agent_workflow": 0.62 if phase_slug == "behavior_quality_drop" else 0.38,
            "source_disagreement": 0.35,
        }
    else:
        weights = {
            "input": 0.55,
            "embedding": 0.45,
            "output": 0.65,
            "retrieval": 0.5,
            "agent_workflow": 0.45,
            "source_disagreement": 0.35,
        }
    return round(max(2.0, min(98.0, behavior * weights[component])), 3)


def phase_metric_text(phase: dict[str, Any], index: int) -> str:
    profile = phase["profile"]
    lines = metric_header()
    counter_base = (index + 1) * 10000
    for workload_index, workload in enumerate(WORKLOADS):
        for role in TRAFFIC_ROLES:
            factor = role_factor(role, phase)
            active_role = 1 if factor >= 0.1 else 0
            active_version = profile["model_version"] if role != "stable" or profile["rollout"] != "canary" else "v1"
            behavior = profile["behavior"] * (1.18 if role == "canary" and profile["rollout"] == "canary" else 1.0)
            behavior = min(98.0, behavior)
            error_rate = profile["error_rate"] * (1.35 if role == "canary" and phase["slug"] == "behavior_quality_drop" else 1.0)
            latency = profile["latency"] * (1.2 if role == "canary" and profile["rollout"] == "canary" else 1.0)
            common = {
                "service": SERVICE,
                "environment": ENVIRONMENT,
                "model": MODEL,
                "model_version": active_version,
                "workload": workload,
                "stream": STREAM,
                "traffic_role": role,
                "comparison": "known_good_baseline",
                "scenario_phase": phase["slug"],
            }
            request_count = int(counter_base + profile["request_rate"] * factor * 120 + workload_index * 350)
            error_count = int(counter_base / 20 + profile["request_rate"] * factor * error_rate * 120 + workload_index * 25)
            lines.append(sample_line("metricchrono_sre_ai_current_state_code", common, STATE_CODE[profile["state"]]))
            lines.append(sample_line("metricchrono_sre_ai_incident_hypothesis_code", common, HYPOTHESIS_CODE[profile["hypothesis"]]))
            lines.append(sample_line("metricchrono_sre_ai_requests_total", common | {"status": "all"}, request_count))
            for error_class in ERROR_CLASSES:
                class_factor = {
                    "application": 0.25,
                    "provider": 0.45 if profile["hypothesis"] == "dependency" else 0.08,
                    "timeout": 0.25 if profile["hypothesis"] in {"capacity", "dependency"} else 0.05,
                    "rate_limit": 0.25 if profile["hypothesis"] == "dependency" else 0.03,
                    "policy_block": 0.25 if phase["slug"] in {"behavior_quality_drop", "silent_behavior_change"} else 0.04,
                    "malformed_request": 0.03,
                    "retrieval_failure": 0.2 if profile["hypothesis"] in {"deploy", "mixed"} else 0.04,
                    "tool_failure": 0.16 if phase["slug"] == "behavior_quality_drop" else 0.03,
                    "unknown": 0.03,
                }[error_class]
                lines.append(sample_line("metricchrono_sre_ai_errors_total", common | {"error_class": error_class}, max(0, int(error_count * class_factor))))
            observations_success = [latency * factor for factor in [0.45, 0.65, 0.8, 1.0, 1.1, 1.25, 1.55, 1.9]]
            observations_failed = [profile["failed_latency"] * factor for factor in [0.8, 1.0, 1.35, 1.8]]
            multiplier = max(1, int(20 * max(factor, 0.05)))
            lines.extend(emit_histogram("metricchrono_sre_ai_request_duration_seconds", common | {"outcome": "success"}, observations_success, [0.1, 0.25, 0.5, 1, 2, 5], multiplier))
            lines.extend(emit_histogram("metricchrono_sre_ai_request_duration_seconds", common | {"outcome": "failed"}, observations_failed, [0.1, 0.25, 0.5, 1, 2, 5], multiplier))
            lines.append(sample_line("metricchrono_sre_ai_inflight_requests", common, round(profile["inflight"] * factor, 3)))
            lines.append(sample_line("metricchrono_sre_ai_queue_depth", common, round(profile["queue_depth"] * factor, 3)))
            lines.append(sample_line("metricchrono_sre_ai_concurrency_usage_ratio", common, round(min(1.0, profile["saturation"] * factor), 3)))
            lines.append(sample_line("metricchrono_sre_ai_token_budget_usage_ratio", common, round(min(1.0, profile["token_budget"] * (1.2 if role == "canary" else 1.0)), 3)))
            for resource in RESOURCES:
                resource_factor = {
                    "queue": profile["queue_depth"] / 100,
                    "inflight": profile["inflight"] / 220,
                    "concurrency": profile["saturation"],
                    "provider_quota": profile["token_budget"],
                    "token_budget": profile["token_budget"],
                    "cpu": min(0.98, profile["saturation"] * 0.8 + 0.1),
                    "gpu_memory": min(0.98, profile["saturation"] * 0.55 + 0.2),
                }[resource]
                lines.append(sample_line("metricchrono_sre_ai_saturation_ratio", common | {"resource": resource}, round(min(1.0, resource_factor * (1.15 if role == "canary" else 1.0)), 3)))
            for component in LATENCY_COMPONENTS:
                value = {
                    "end_to_end": latency,
                    "queue": profile["queue_depth"] / 100,
                    "provider": profile["provider_latency"],
                    "retrieval": 0.18 if phase["slug"] != "deploy_correlated_behavior" else 0.55,
                    "tool_call": 0.12 if phase["slug"] != "behavior_quality_drop" else 0.36,
                    "response_streaming": 0.09 if latency < 1 else 0.22,
                }[component]
                lines.append(sample_line("metricchrono_sre_ai_latency_component_seconds", common | {"component": component}, round(value * (1.12 if role == "canary" else 1.0), 3)))
            lines.append(sample_line("metricchrono_sre_ai_slo_burn_rate", common | {"window": "short"}, round(profile["burn_short"] * (1.25 if role == "canary" and profile["rollout"] == "canary" else 1.0), 3)))
            lines.append(sample_line("metricchrono_sre_ai_slo_burn_rate", common | {"window": "long"}, round(profile["burn_long"] * (1.15 if role == "canary" and profile["rollout"] == "canary" else 1.0), 3)))
            lines.append(sample_line("metricchrono_sre_ai_error_budget_remaining_ratio", common, profile["remaining_budget"]))
            lines.append(sample_line("metricchrono_sre_ai_slo_good_events_total", common, int(request_count * (1 - error_rate))))
            for reason in SLO_REASONS:
                reason_factor = {
                    "availability_failure": 0.4 if error_rate > 0.01 else 0.05,
                    "latency_violation": 0.45 if latency > 1 else 0.08,
                    "dependency_failure": 0.65 if profile["hypothesis"] == "dependency" else 0.04,
                    "timeout_failure": 0.28 if profile["hypothesis"] in {"capacity", "dependency"} else 0.03,
                    "quality_policy_failure": 0.5 if phase["slug"] == "behavior_quality_drop" else 0.0,
                }[reason]
                lines.append(sample_line("metricchrono_sre_ai_slo_bad_events_total", common | {"reason": reason}, int(error_count * reason_factor + index)))
            lines.append(sample_line("metricchrono_sre_ai_latency_violations_total", common, int(error_count * (2.5 if latency > 1 else 0.2) + index)))
            lines.append(sample_line("metricchrono_sre_ai_availability_failures_total", common, int(error_count + index)))
            lines.append(sample_line("metricchrono_sre_ai_behavior_change_score", common, round(behavior, 3)))
            for component in COMPONENTS:
                lines.append(sample_line("metricchrono_sre_ai_behavior_component_score", common | {"component": component}, component_value(component, behavior, phase["slug"])))
            size_values = {
                "small": min(30, behavior * 0.55),
                "medium": max(0, behavior - 25) * 0.75,
                "large": max(0, behavior - 55),
            }
            for size, value in size_values.items():
                lines.append(sample_line("metricchrono_sre_ai_change_score_by_size", common | {"change_size": size}, round(value, 3)))
            behavior_state = 2 if behavior >= 75 and profile["quality"] < 0.85 else 1 if behavior >= 50 else 0
            if profile["state"] == "Recovering":
                behavior_state = 3
            lines.append(sample_line("metricchrono_sre_ai_behavior_state_code", common, behavior_state))
            lines.append(sample_line("metricchrono_sre_ai_quality_proxy", common, round(profile["quality"] - (0.04 if role == "canary" and phase["slug"] == "behavior_quality_drop" else 0), 3)))
            lines.append(sample_line("metricchrono_sre_ai_baseline_age_seconds", common, profile["baseline_age"]))
            lines.append(sample_line("metricchrono_sre_ai_sample_volume", common, profile["sample_volume"]))
            lines.append(sample_line("metricchrono_sre_ai_sampled_request_rate", common, round(profile["request_rate"] * factor, 3)))
            lines.append(sample_line("metricchrono_sre_ai_missing_source_count", common, profile["missing_sources"]))
            lines.append(sample_line("metricchrono_sre_ai_low_traffic_flag", common, profile["low_traffic"]))
            lines.append(sample_line("metricchrono_sre_ai_baseline_trust_state_code", common, TRUST_CODE[profile["trust"]]))
            for provider in PROVIDERS:
                p_common = common | {"provider": provider}
                lines.append(sample_line("metricchrono_sre_ai_provider_requests_total", p_common, request_count + 40))
                lines.append(sample_line("metricchrono_sre_ai_provider_errors_total", p_common, int(request_count * profile["provider_error_rate"] * (1.5 if provider == "primary-llm" else 0.3))))
                lines.append(sample_line("metricchrono_sre_ai_provider_rate_limits_total", p_common, int(counter_base / 50 + profile["provider_rate_limits"] * (2 if provider == "primary-llm" else 1))))
                lines.extend(emit_histogram("metricchrono_sre_ai_provider_duration_seconds", p_common, [profile["provider_latency"] * value for value in [0.6, 0.8, 1.0, 1.25, 1.7]], [0.1, 0.25, 0.5, 1, 2, 5], multiplier))
            lines.append(sample_line("metricchrono_sre_ai_token_usage_total", common | {"token_kind": "input"}, int(counter_base + request_count * (24 if role != "canary" else 32))))
            lines.append(sample_line("metricchrono_sre_ai_token_usage_total", common | {"token_kind": "output"}, int(counter_base + request_count * (42 if role != "canary" else 58))))
            lines.append(sample_line("metricchrono_sre_ai_cost_proxy", common, round(request_count * (0.0002 if role != "canary" else 0.00032), 4)))
            dep_health = {
                "model_provider": max(0.0, 1.0 - profile["provider_error_rate"] * 8 - profile["provider_latency"] / 4),
                "retriever": 0.72 if phase["slug"] == "deploy_correlated_behavior" else 0.95,
                "vector_db": 0.94,
                "tool_api": 0.7 if phase["slug"] == "behavior_quality_drop" else 0.96,
                "cache": 0.9,
            }
            for dep in DEPENDENCIES:
                dep_common = common | {"dependency": dep}
                lines.append(sample_line("metricchrono_sre_ai_dependency_health_score", dep_common, round(dep_health[dep], 3)))
            lines.extend(emit_histogram("metricchrono_sre_ai_retrieval_duration_seconds", common | {"dependency": "retriever"}, [0.12, 0.16, 0.22, 0.3 if phase["slug"] != "deploy_correlated_behavior" else 0.78], [0.05, 0.1, 0.25, 0.5, 1, 2], multiplier))
            lines.extend(emit_histogram("metricchrono_sre_ai_vector_db_duration_seconds", common | {"dependency": "vector_db"}, [0.05, 0.08, 0.11, 0.16], [0.05, 0.1, 0.25, 0.5, 1], multiplier))
            lines.extend(emit_histogram("metricchrono_sre_ai_tool_call_duration_seconds", common | {"dependency": "tool_api"}, [0.07, 0.12, 0.2, 0.4 if phase["slug"] == "behavior_quality_drop" else 0.18], [0.05, 0.1, 0.25, 0.5, 1, 2], multiplier))
            lines.append(sample_line("metricchrono_sre_ai_cache_hit_ratio", common | {"dependency": "cache"}, 0.72 if phase["slug"] == "deploy_correlated_behavior" else 0.9))
            for version_name, metric, label in [
                (profile["app_version"], "metricchrono_sre_ai_app_version_active", "app_version"),
                (profile["model_version"], "metricchrono_sre_ai_model_version_active", "active_model_version"),
                (profile["prompt_version"], "metricchrono_sre_ai_prompt_version_active", "prompt_version"),
                (profile["index_version"], "metricchrono_sre_ai_index_version_active", "index_version"),
                (profile["config_version"], "metricchrono_sre_ai_config_version_active", "config_version"),
            ]:
                lines.append(sample_line(metric, common | {label: version_name}, 1))
            lines.append(sample_line("metricchrono_sre_ai_rollout_state_code", common, ROLLOUT_CODE[profile["rollout"]]))
            lines.append(sample_line("metricchrono_sre_ai_traffic_role_active", common | {"state": "serving"}, active_role))
            lines.append(sample_line("metricchrono_sre_ai_previous_version_behavior_change_score", common, round(max(0.0, behavior - 12), 3)))
            canary_difference = behavior - (profile["behavior"] * 0.55 if profile["rollout"] == "canary" else profile["behavior"] * 0.2)
            lines.append(sample_line("metricchrono_sre_ai_canary_behavior_difference_score", common, round(max(0, canary_difference if role == "canary" else canary_difference * 0.2), 3)))
            candidate_labels = common | {
                "rank": str(1 + workload_index),
                "slo_state": profile["state"].lower(),
                "behavior_state": "watch" if behavior >= 50 else "normal",
                "likely_cause": profile["likely_cause"],
                "next_step": profile["next_step"],
                "runbook": profile["runbook"],
                "severity": profile["state"].lower(),
            }
            lines.append(sample_line("metricchrono_sre_ai_next_action_candidate", candidate_labels, 1 if role in {"stable", "canary"} else 0))
            lines.append(sample_line("metricchrono_sre_ai_inspection_candidate", candidate_labels | {"owner": "ai-platform" if "behavior" in profile["likely_cause"] else "sre"}, 1 if role in {"stable", "canary"} else 0))
            for row, signal in enumerate(["slo_burn", "canary_vs_stable", "previous_version", "quality_proxy", "dependency_health"], start=1):
                evidence_value = {
                    "slo_burn": profile["burn_short"],
                    "canary_vs_stable": canary_difference,
                    "previous_version": max(0.0, behavior - 12),
                    "quality_proxy": profile["quality"],
                    "dependency_health": dep_health["model_provider"],
                }[signal]
                severity = "incident" if evidence_value > 75 or evidence_value < 0.85 or profile["state"] == "Incident" else "watch"
                lines.append(
                    sample_line(
                        "metricchrono_sre_ai_rollback_evidence",
                        common
                        | {
                            "rank": str(row),
                            "signal": signal,
                            "comparator": "canary_vs_stable" if role == "canary" else "current_vs_previous",
                            "severity": severity,
                            "first_seen": "2m_ago",
                            "owner": "ai-platform",
                            "suggested_action": "pause_or_rollback_canary" if profile["rollout"] == "canary" else "continue_watch",
                        },
                        1 if role in {"stable", "canary"} else 0,
                    )
                )
            for scenario_phase in [item["slug"] for item in PHASES]:
                lines.append(sample_line("metricchrono_sre_ai_scenario_phase", common | {"scenario_phase": scenario_phase}, 1 if scenario_phase == phase["slug"] else 0))
    return "\n".join(lines) + "\n"


def write_scenario() -> None:
    scenario_dir = RECIPE_ROOT / "examples" / "synthetic-ai-service-scenario"
    phase_items = []
    for index, phase in enumerate(PHASES):
        text = phase_metric_text(phase, index)
        write(scenario_dir / phase["file"], text)
        phase_items.append({"name": phase["name"], "file": phase["file"], "summary": phase["summary"], "expected": phase["expected"]})
    scenario = {
        "name": "Synthetic AI service reliability scenario",
        "default_run": "The default run plays once and holds recovery. Use --loop only for repeating local demos.",
        "phases": [phase["name"] for phase in PHASES],
        "phase_metrics": phase_items,
    }
    write_json(scenario_dir / "scenario.json", scenario)
    write(
        scenario_dir / "run_scenario.py",
        clean(
            """
            #!/usr/bin/env python3
            \"\"\"Replay the synthetic AI service SRE scenario as Prometheus text snapshots.\"\"\"

            from __future__ import annotations

            import argparse
            import json
            import time
            from pathlib import Path


            HERE = Path(__file__).resolve().parent


            def main() -> int:
                parser = argparse.ArgumentParser()
                parser.add_argument("--output", default="scenario-metrics.prom")
                parser.add_argument("--seconds-per-phase", type=float, default=1.0)
                parser.add_argument("--loop", action="store_true")
                args = parser.parse_args()
                scenario = json.loads((HERE / "scenario.json").read_text(encoding="utf-8"))
                output = HERE / args.output
                while True:
                    for item in scenario["phase_metrics"]:
                        text = (HERE / item["file"]).read_text(encoding="utf-8")
                        output.write_text(text, encoding="utf-8")
                        print(f"wrote {output} for phase: {item['name']}")
                        time.sleep(args.seconds_per_phase)
                    if not args.loop:
                        break
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ),
    )
    normal = (scenario_dir / PHASES[0]["file"]).read_text(encoding="utf-8")
    incident = (scenario_dir / PHASES[1]["file"]).read_text(encoding="utf-8")
    write(RECIPE_ROOT / "fixtures" / "expected-metrics-normal.txt", normal)
    write(RECIPE_ROOT / "fixtures" / "expected-metrics-incident.txt", incident)


def write_rules() -> None:
    write(
        RECIPE_ROOT / "rules" / "sre-ai-service-alerts.yml",
        clean(
            """
            groups:
            - name: sre-ai-services
              rules:
              - alert: AIServiceFastBurn
                expr: max by (service, environment, model, workload) (metricchrono_sre_ai_slo_burn_rate{window="short"} > 14.4)
                for: 2m
                labels:
                  severity: page
                  page: "yes"
                annotations:
                  summary: "AI service is burning error budget quickly"
                  description: "User-impacting SLO burn is above the fast-burn threshold. Treat this as a service incident."
                  runbook_url: "runbooks/ai-service-fast-burn.md"
                  suggested_dashboard: "AI Service On-Call Overview"
                  suggested_next_action: "Confirm user impact, identify the largest bad-event reason, and mitigate the leading golden-signal failure."
              - alert: AIServiceSlowBurn
                expr: max by (service, environment, model, workload) (metricchrono_sre_ai_slo_burn_rate{window="long"} > 1)
                for: 15m
                labels:
                  severity: watch
                  page: "no"
                annotations:
                  summary: "AI service has sustained error-budget burn"
                  description: "Long-window burn is above sustainable rate. Create or update an incident ticket unless policy says to page."
                  runbook_url: "runbooks/ai-service-slow-burn.md"
                  suggested_dashboard: "AI Incident Triage"
                  suggested_next_action: "Find whether latency, availability, dependency, or quality policy is consuming the SLO."
              - alert: AIServiceLatencyDegraded
                expr: max by (service, environment, model, workload) (metricchrono_sre_ai_latency_component_seconds{component="end_to_end"} > 1 and metricchrono_sre_ai_slo_burn_rate{window="short"} > 1)
                for: 5m
                labels:
                  severity: conditional
                  page: "conditional"
                annotations:
                  summary: "AI service latency is degraded"
                  description: "End-to-end latency is above the example SLO target and burn is elevated."
                  runbook_url: "runbooks/latency-degraded.md"
                  suggested_dashboard: "AI Incident Triage"
                  suggested_next_action: "Inspect queue, provider, retrieval, tool-call, and streaming latency components."
              - alert: AIProviderDependencyDegraded
                expr: max by (service, environment, model, workload, provider) ((metricchrono_sre_ai_dependency_health_score{dependency="model_provider"} < 0.75) or (increase(metricchrono_sre_ai_provider_rate_limits_total[5m]) > 5))
                for: 5m
                labels:
                  severity: conditional
                  page: "conditional"
                annotations:
                  summary: "AI provider or upstream dependency is degraded"
                  description: "Provider health, rate limits, errors, or latency suggest dependency impact. Page only if SLO or incident policy is affected."
                  runbook_url: "runbooks/provider-dependency-degraded.md"
                  suggested_dashboard: "AI Incident Triage"
                  suggested_next_action: "Compare provider latency/errors with service latency/errors and route to the dependency owner if it leads."
              - alert: AIBehaviorChangedWhileServiceHealthNormal
                expr: max by (service, environment, model, workload, stream) (metricchrono_sre_ai_behavior_change_score > 50 and metricchrono_sre_ai_slo_burn_rate{window="short"} < 1 and metricchrono_sre_ai_latency_component_seconds{component="end_to_end"} < 1 and metricchrono_sre_ai_low_traffic_flag == 0 and metricchrono_sre_ai_baseline_trust_state_code == 0)
                for: 10m
                labels:
                  severity: watch
                  page: "no"
                annotations:
                  summary: "AI behavior changed while service health is normal"
                  description: "Behavior evidence moved while latency, errors, SLO burn, baseline trust, and traffic volume remain acceptable. This is a watch signal, not a default page."
                  runbook_url: "runbooks/behavior-changed-health-normal.md"
                  suggested_dashboard: "AI Incident Triage"
                  suggested_next_action: "Route affected stream, workload, and model version to the AI/model owner with deploy and component evidence."
              - alert: AIBehaviorChangeWithQualityDrop
                expr: max by (service, environment, model, workload, stream) (metricchrono_sre_ai_behavior_change_score > 75 and metricchrono_sre_ai_quality_proxy < 0.85 and metricchrono_sre_ai_low_traffic_flag == 0 and metricchrono_sre_ai_baseline_trust_state_code == 0)
                for: 5m
                labels:
                  severity: incident
                  page: "conditional"
                annotations:
                  summary: "AI behavior changed with quality degradation"
                  description: "Behavior evidence and quality or business proxy are degraded together. Page only where production policy treats this as user impact."
                  runbook_url: "runbooks/behavior-change-quality-drop.md"
                  suggested_dashboard: "AI Incident Triage"
                  suggested_next_action: "Escalate to AI owner with affected stream, quality proxy, and release-correlation evidence."
              - alert: AIReleaseBehaviorRegression
                expr: max by (service, environment, model, workload, stream, traffic_role) (metricchrono_sre_ai_canary_behavior_difference_score{traffic_role="canary"} > 50 and metricchrono_sre_ai_low_traffic_flag == 0 and metricchrono_sre_ai_baseline_trust_state_code == 0)
                for: 10m
                labels:
                  severity: watch
                  page: "conditional"
                annotations:
                  summary: "AI release has behavior regression evidence"
                  description: "Canary behavior differs materially from stable or previous version. Do not page solely on behavior; pause or escalate according to release policy."
                  runbook_url: "runbooks/release-behavior-regression.md"
                  suggested_dashboard: "AI Release Guardrail"
                  suggested_next_action: "Compare canary user impact, behavior components, dependency/cost difference, and rollback evidence."
              - alert: AIBaselineStaleOrLowVolume
                expr: max by (service, environment, model, workload, stream) ((metricchrono_sre_ai_baseline_trust_state_code > 0) or (metricchrono_sre_ai_low_traffic_flag == 1) or (metricchrono_sre_ai_sample_volume < 100))
                for: 10m
                labels:
                  severity: info
                  page: "no"
                annotations:
                  summary: "AI behavior signal trust is weak"
                  description: "Baseline freshness, source availability, or minimum-volume guard weakens behavior interpretation and should suppress or downgrade behavior alerts."
                  runbook_url: "runbooks/baseline-stale-low-volume.md"
                  suggested_dashboard: "AI Incident Triage"
                  suggested_next_action: "Fix baseline trust or wait for minimum traffic before treating behavior evidence as incident-grade."
            """
        ),
    )


RUNBOOKS = {
    "ai-service-fast-burn.md": {
        "title": "AI Service Fast Burn",
        "meaning": "Short-window SLO burn is high enough to page under the example policy.",
        "first": "Confirm affected service, workload, traffic role, request rate, errors, latency, and saturation.",
        "causes": "Capacity, dependency failure, bad deploy, provider rate limit, timeout path, or widespread app failure.",
        "inspect": "Open AI Incident Triage, then inspect SLO bad-event reason, latency decomposition, error path, and dependency health.",
        "not_do": "Do not start with AI behavior analysis if user-facing SLIs are clearly burning.",
        "owner": "SRE incident commander first, then service owner or dependency owner based on evidence.",
        "recovery": "Short and long burn below thresholds, latency and errors normal, and recovery window sustained.",
    },
    "ai-service-slow-burn.md": {
        "title": "AI Service Slow Burn",
        "meaning": "Long-window burn is above sustainable rate but may not require an immediate page.",
        "first": "Check whether the burn is worsening, which SLO reason dominates, and whether fast burn is also active.",
        "causes": "Sustained low-grade errors, latency creep, dependency instability, or configured quality-policy failures.",
        "inspect": "Review trend duration, affected workload, dependency health, and recent deploys.",
        "not_do": "Do not ignore slow burn because the current minute looks quiet.",
        "owner": "Service SRE and application owner.",
        "recovery": "Long-window burn returns below 1x and remains there through the configured window.",
    },
    "latency-degraded.md": {
        "title": "Latency Degraded",
        "meaning": "Latency is above the SLO or known-good band, especially when burn is elevated.",
        "first": "Compare end-to-end p95/p99 with queue, provider, retrieval, tool-call, and streaming components.",
        "causes": "Queueing, concurrency limit, provider latency, vector DB latency, tool API latency, or traffic spike.",
        "inspect": "Open saturation decomposition and dependency health panels.",
        "not_do": "Do not average successful and failed latency or restart components without checking the leading component.",
        "owner": "SRE for capacity, dependency owner for upstream latency, app owner for local queues.",
        "recovery": "p95/p99 below SLO, queue and saturation normal, and burn below thresholds.",
    },
    "provider-dependency-degraded.md": {
        "title": "Provider Dependency Degraded",
        "meaning": "Provider, retrieval, vector DB, cache, or tool dependency is degraded or rate limited.",
        "first": "Compare provider/dependency latency and errors against service latency and errors.",
        "causes": "Hosted model outage, provider quota, vector store latency, retriever issue, tool API failures, or cache collapse.",
        "inspect": "Provider status, quota dashboards, retry budget, fallback configuration, and dependency owner alerts.",
        "not_do": "Do not treat dependency-led service symptoms as an AI behavior incident.",
        "owner": "Dependency owner or vendor owner, with SRE coordinating user-impact mitigation.",
        "recovery": "Dependency health normal, rate limits stopped, service burn recovered, and retries back to normal.",
    },
    "behavior-changed-health-normal.md": {
        "title": "Behavior Changed While Service Health Normal",
        "meaning": "Behavior evidence changed while latency, errors, traffic, and SLO burn remain normal.",
        "first": "Check deploys, model version, prompt version, index version, config version, input shift, retrieval shift, and output behavior.",
        "causes": "Prompt change, model update, index rebuild, input population shift, retrieval change, or agent workflow change.",
        "inspect": "Behavior components, release timeline, baseline trust, sample volume, and top inspection candidates.",
        "not_do": "Do not restart infrastructure first and do not page solely on behavior-change by default.",
        "owner": "AI/model owner, prompt owner, retrieval owner, or agent workflow owner.",
        "recovery": "Behavior returns below watch threshold or the owner accepts the new behavior as healthy and refreshes baseline policy.",
    },
    "behavior-change-quality-drop.md": {
        "title": "Behavior Change With Quality Drop",
        "meaning": "Behavior evidence and quality or business proxy are degraded together.",
        "first": "Confirm quality proxy semantics, delay window, sample volume, and baseline trust.",
        "causes": "Bad model/prompt release, harmful retrieval change, input shift, policy regression, or agent workflow failure.",
        "inspect": "Release guardrail, behavior components, quality proxy history, rollback evidence, and affected stream.",
        "not_do": "Do not claim behavior-change alone proves harm; require quality, SLO, or configured impact evidence.",
        "owner": "AI/model owner with SRE incident coordination when policy treats this as user impact.",
        "recovery": "Quality proxy recovers and behavior evidence returns below configured incident thresholds.",
    },
    "release-behavior-regression.md": {
        "title": "Release Behavior Regression",
        "meaning": "Canary or new version behavior differs materially from stable or previous version.",
        "first": "Compare canary and stable user impact before deciding whether behavior evidence is rollback-worthy.",
        "causes": "Model rollout, prompt edit, index rebuild, config change, app deploy, or canary traffic mismatch.",
        "inspect": "Canary user impact, behavior difference, changed components, dependency/cost difference, and rollback evidence.",
        "not_do": "Do not roll back without evidence, and do not page solely on behavior difference unless policy says so.",
        "owner": "Release owner, AI platform owner, and SRE for guardrail enforcement.",
        "recovery": "Rollback or pause completed, canary difference normal, user SLIs stable, and quality proxy normal.",
    },
    "baseline-stale-low-volume.md": {
        "title": "Baseline Stale Or Low Volume",
        "meaning": "Behavior signal is weak because baseline, traffic volume, or source availability is not trustworthy.",
        "first": "Check baseline age, sample volume, sampled request rate, missing-source count, and low-traffic flag.",
        "causes": "Stale baseline, under-sampled workload, telemetry source missing, or traffic pattern too sparse.",
        "inspect": "Baseline refresh policy, representative known-good windows, source freshness, and minimum-volume threshold.",
        "not_do": "Do not escalate behavior movement as incident-grade while trust gates are failing.",
        "owner": "Observability owner and AI/model owner for baseline acceptance.",
        "recovery": "Baseline is fresh, sample volume clears policy, missing sources are zero, and alerts regain normal severity.",
    },
}


def write_runbooks() -> None:
    for filename, item in RUNBOOKS.items():
        write(
            RECIPE_ROOT / "runbooks" / filename,
            clean(
                f"""
                # {item['title']}

                ## Meaning

                {item['meaning']}

                ## First checks

                {item['first']}

                ## Likely causes

                {item['causes']}

                ## What to inspect

                {item['inspect']}

                ## What not to do

                {item['not_do']}

                ## Escalation owner

                {item['owner']}

                ## Recovery criteria

                {item['recovery']}
                """
            ),
        )


def write_docs() -> None:
    write(
        RECIPE_ROOT / "README.md",
        clean(
            """
            # AI Service Reliability Recipe

            This recipe is for SREs and observability engineers running AI services. It helps on-call engineers triage AI-service incidents with golden signals, SLO burn, deploy correlation, dependency health, and AI behavior-change evidence.

            It adds AI-behavior evidence beside golden signals and SLO burn. It does not replace SLOs, incident policy, full ML evaluation, tracing, or human review. Behavior-change alone is a watch signal by default, not a page.

            ![AI Service On-Call Overview - Normal](screenshots/on-call-overview-normal.png)

            ## What Incident Does This Help With?

            Use it when users report an AI service changed behavior, a canary looks suspicious, or a normal service incident might actually be infrastructure, dependency, deploy, retrieval, agent workflow, or behavior-related.

            The first dashboard to open is `AI Service On-Call Overview`.

            ## Run The Local Scenario

            ```bash
            make sre
            ```

            npm equivalent:

            ```bash
            npm run sre:start
            ```

            Open the Grafana URL printed by the command. The dashboards are provisioned in the `MetricChrono SRE AI Services Recipes` Grafana folder.

            To replay only the deterministic Prometheus text scenario:

            ```bash
            cd recipes/sre-ai-services/examples/synthetic-ai-service-scenario
            python3 run_scenario.py
            ```

            ## Dashboards Included

            - AI Service On-Call Overview
            - AI Incident Triage
            - AI Release Guardrail

            ## Alerts Included

            - `AIServiceFastBurn`
            - `AIServiceSlowBurn`
            - `AIServiceLatencyDegraded`
            - `AIProviderDependencyDegraded`
            - `AIBehaviorChangedWhileServiceHealthNormal`
            - `AIBehaviorChangeWithQualityDrop`
            - `AIReleaseBehaviorRegression`
            - `AIBaselineStaleOrLowVolume`

            ## Local Scenario Phases

            Normal, infrastructure/capacity issue, dependency/provider issue, silent AI-behavior change, deploy-correlated behavior change, behavior plus quality drop, stale baseline, low traffic, and recovery.

            ## What To Do When Behavior Changes But Service Health Is Green

            Treat it as watch-level evidence. Check deploys, prompt/model/index/config changes, input shift, retrieval shift, agent workflow, baseline freshness, and sample volume. Route the evidence to the AI/model owner instead of restarting infrastructure first.

            ## Production Mapping

            See `docs/production-mapping.md` for how to map these example metrics to production Prometheus, OpenTelemetry, Grafana Cloud, Datadog, Splunk, or custom observability pipelines.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "metric-contract.md",
        clean(
            f"""
            # SRE-Facing Metric Contract

            Default dashboards use operational categories: golden signals, SLO and burn, AI behavior evidence, dependency/provider health, and release correlation.

            ## Stable Labels

            {chr(10).join(f"- `{label}`" for label in STABLE_LABELS).replace(chr(10), chr(10) + "            ")}

            ## Forbidden Labels

            {chr(10).join(f"- `{label}`" for label in FORBIDDEN_LABELS).replace(chr(10), chr(10) + "            ")}

            Raw prompts, request IDs, trace IDs, user IDs, session IDs, raw text, tool call IDs, span IDs, document IDs, and error text belong in logs, traces, exemplars, or review systems, not Prometheus labels.

            ## Category A - Golden Signals

            Required metrics are request count, error count, request duration histogram, and saturation/queue/capacity signals:

            - `metricchrono_sre_ai_requests_total`
            - `metricchrono_sre_ai_errors_total`
            - `metricchrono_sre_ai_request_duration_seconds`
            - `metricchrono_sre_ai_inflight_requests`
            - `metricchrono_sre_ai_queue_depth`
            - `metricchrono_sre_ai_saturation_ratio`

            ## Category B - SLO And Burn

            Behavior-change is not counted as a bad event by default.

            - `metricchrono_sre_ai_slo_good_events_total`
            - `metricchrono_sre_ai_slo_bad_events_total`
            - `metricchrono_sre_ai_slo_burn_rate`
            - `metricchrono_sre_ai_latency_violations_total`
            - `metricchrono_sre_ai_availability_failures_total`

            ## Category C - AI Behavior Evidence

            - `metricchrono_sre_ai_behavior_change_score`
            - `metricchrono_sre_ai_behavior_component_score`
            - `metricchrono_sre_ai_change_score_by_size`
            - `metricchrono_sre_ai_behavior_state_code`
            - `metricchrono_sre_ai_baseline_age_seconds`
            - `metricchrono_sre_ai_sample_volume`
            - `metricchrono_sre_ai_baseline_trust_state_code`

            Component values include `input`, `embedding`, `output`, `retrieval`, `agent_workflow`, and `source_disagreement`. Change size values are `small`, `medium`, and `large`.

            ## Category D - Dependency / Provider Health

            - `metricchrono_sre_ai_provider_requests_total`
            - `metricchrono_sre_ai_provider_errors_total`
            - `metricchrono_sre_ai_provider_duration_seconds`
            - `metricchrono_sre_ai_provider_rate_limits_total`
            - `metricchrono_sre_ai_token_usage_total`
            - `metricchrono_sre_ai_retrieval_duration_seconds`
            - `metricchrono_sre_ai_vector_db_duration_seconds`
            - `metricchrono_sre_ai_tool_call_duration_seconds`

            ## Category E - Release Correlation

            - `metricchrono_sre_ai_app_version_active`
            - `metricchrono_sre_ai_model_version_active`
            - `metricchrono_sre_ai_prompt_version_active`
            - `metricchrono_sre_ai_index_version_active`
            - `metricchrono_sre_ai_config_version_active`
            - `metricchrono_sre_ai_rollout_state_code`
            - `metricchrono_sre_ai_previous_version_behavior_change_score`
            - `metricchrono_sre_ai_canary_behavior_difference_score`

            Comparisons used by dashboards include `known_good_baseline`, `previous_version`, `stable_vs_canary`, `before_vs_after_deploy`, `dependency_vs_service`, `quality_proxy`, `minimum_traffic_volume`, `baseline_freshness_policy`, and `capacity_limit`.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "scenario.md",
        clean(
            """
            # Local Scenario Guide

            The synthetic scenario is deterministic and requires no real provider, vector DB, model endpoint, or traffic generator.

            The default run plays once and holds recovery. Use `--loop` only for a repeating demo.

            ## Phases

            1. Normal: traffic, latency, errors, saturation, dependencies, and behavior are normal.
            2. Infrastructure / capacity issue: latency and saturation rise while behavior remains secondary.
            3. Dependency/provider issue: provider latency, errors, or rate limits lead service impact.
            4. Silent AI-behavior change: behavior rises while golden signals stay green.
            5. Deploy-correlated behavior change: app/model/prompt/index/config changes before behavior movement.
            6. Behavior + quality drop: behavior movement aligns with quality or business proxy degradation.
            7. Stale baseline: baseline trust weakens behavior interpretation.
            8. Low traffic: minimum traffic volume is not met.
            9. Recovery: mitigation occurs and service-health and behavior evidence stabilize.

            ## Run

            ```bash
            python3 run_scenario.py
            ```

            The script writes `scenario-metrics.prom` for each phase. Phase snapshots are stored under `phase-metrics/`.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "validation-guide.md",
        clean(
            """
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
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "production-mapping.md",
        clean(
            """
            # Mapping This Recipe To Production Metrics

            Keep the dashboard vocabulary and alert posture, then map each example metric to your existing telemetry source.

            ## Golden Signals

            Map `metricchrono_sre_ai_requests_total`, `metricchrono_sre_ai_errors_total`, and `metricchrono_sre_ai_request_duration_seconds` to your HTTP, RPC, queue, or gateway metrics. Keep status and error class bounded.

            ## SLO And Burn

            Prefer your production SLO pipeline for good events, bad events, burn rate, latency violations, and availability failures. Behavior-change should remain evidence unless your production SLI policy explicitly defines it as impact.

            ## Dependency / Provider Health

            Map provider latency, errors, rate limits, token usage, retrieval latency, vector DB latency, tool-call latency, and cache hit ratio from OpenTelemetry, provider SDKs, gateway logs, or dependency exporters.

            ## Release Correlation

            Emit active app version, model version, prompt version, retriever/index version, config version, and traffic role as bounded labels or state gauges. Keep raw commit SHAs and free-form deploy notes outside Prometheus labels if they create high cardinality.

            ## Behavior Evidence

            Map behavior-change, component scores, source disagreement, baseline age, minimum traffic, and sample trust from your AI evaluation or behavior-monitoring pipeline. Do not copy demo thresholds into production without calibration.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "alert-tuning.md",
        clean(
            """
            # Alert Tuning

            These alerts are examples, not production-ready thresholds.

            Hard rule: no default alert pages solely because behavior-change is high.

            Behavior-change alone is watch evidence by default. It can become incident-level only when combined with configured user impact, quality degradation, severe deploy correlation, or production policy.

            Use minimum traffic volume and baseline freshness gates before routing behavior alerts. Tune by service, environment, model, workload, stream, and traffic role.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "baseline-calibration.md",
        clean(
            """
            # Baseline Calibration

            Demo thresholds are not production thresholds.

            Build baselines from known-good representative traffic for each service, workload, stream, model, and traffic role. Refresh baselines only after current behavior is accepted as healthy.

            Behavior alerts should be suppressed or downgraded when baseline age exceeds policy, sample volume is below minimum traffic, or required behavior sources are missing.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "dashboard-panel-guide.md",
        clean(
            """
            # Dashboard Panel Guide

            Every default panel uses this description standard:

            - What this shows
            - Why you care
            - How to read it
            - What to do next

            Every graph compares against an operational reference such as SLO target, burn threshold, known-good baseline, previous version, stable versus canary, dependency versus service, before versus after deploy, quality proxy, minimum traffic volume, baseline freshness policy, or capacity limit.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "integration-guide.md",
        clean(
            """
            # Integration Guide

            Start by emitting the metric contract from your AI gateway or service wrapper. Add dependency/provider metrics from SDK middleware, OpenTelemetry instrumentation, or existing exporters.

            Keep labels bounded. Put prompts, request IDs, trace IDs, user IDs, raw text, raw documents, and free-form errors in logs or traces, not Prometheus labels.

            Roll out in three steps:

            1. Wire golden signals, SLO burn, and dependency health.
            2. Add release correlation for app, model, prompt, index, config, and traffic role.
            3. Add behavior evidence with baseline freshness and minimum-volume gates.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "troubleshooting.md",
        clean(
            """
            # Troubleshooting

            If dashboards are empty, verify Prometheus is scraping the scenario endpoint and that dashboard variables match `checkout-ai`, `demo`, `assist-ranker`, and `support.answers`.

            If behavior alerts fire during low traffic, check `metricchrono_sre_ai_low_traffic_flag` and `metricchrono_sre_ai_sample_volume`.

            If behavior evidence looks suspicious, check baseline age, missing-source count, and whether the current workload matches the baseline.
            """
        ),
    )
    write(
        RECIPE_ROOT / "docs" / "glossary.md",
        clean(
            """
            # Glossary

            SLO burn:
            How quickly the service is consuming error budget.

            Behavior change:
            Evidence that AI inputs, embeddings, outputs, retrieval, agent workflow, or source agreement moved away from a reference.

            Comparison:
            The reference used to interpret a signal, such as `known_good_baseline`, `previous_version`, or `stable_vs_canary`.

            Change size:
            `small` means noise or early movement, `medium` means operational deviation worth watching, and `large` means strong behavior evidence.

            Traffic role:
            Whether traffic is stable, canary, or shadow.
            """
        ),
    )
    write(
        RECIPE_ROOT / "prometheus" / "prometheus.yml",
        clean(
            """
            global:
              scrape_interval: 1s
              evaluation_interval: 1s

            rule_files:
              - ../rules/sre-ai-service-alerts.yml

            scrape_configs:
              - job_name: metricchrono-sre-ai-services-recipe
                metrics_path: /metrics
                static_configs:
                  - targets: ["127.0.0.1:8020"]
            """
        ),
    )
    write(
        RECIPE_ROOT / "grafana" / "provisioning" / "datasources" / "prometheus.yml",
        clean(
            """
            apiVersion: 1
            datasources:
              - name: Prometheus
                uid: Prometheus
                type: prometheus
                access: proxy
                url: http://prometheus:9090
                isDefault: true
                editable: true
            """
        ),
    )
    write(
        RECIPE_ROOT / "grafana" / "provisioning" / "dashboards" / "dashboards.yml",
        clean(
            """
            apiVersion: 1
            providers:
              - name: metricchrono-sre-ai-services-recipes
                orgId: 1
                folder: MetricChrono SRE AI Services Recipes
                type: file
                disableDeletion: false
                editable: true
                options:
                  path: /var/lib/grafana/dashboards
            """
        ),
    )


def main() -> int:
    for path in [
        RECIPE_ROOT / "grafana" / "dashboards",
        RECIPE_ROOT / "rules",
        RECIPE_ROOT / "runbooks",
        RECIPE_ROOT / "docs",
        RECIPE_ROOT / "fixtures",
        RECIPE_ROOT / "screenshots",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    for filename, data in dashboards().items():
        write_json(RECIPE_ROOT / "grafana" / "dashboards" / filename, data)
    write_scenario()
    write_rules()
    write_runbooks()
    write_docs()
    print("Generated SRE AI services recipe assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
