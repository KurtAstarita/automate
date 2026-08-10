#!/usr/bin/env python3
import argparse
import copy
import json
import sys
import time
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.approval_agent import ApprovalAgent
from agents.boss_agent import BossAgent, ContentType, TargetAudience
from agents.content_agency import ContentAgency
from agents.content_refresh_agent import ContentRefreshAgent
from agents.ghost_controls import ghost_controls
from agents.onpage_seo_agency import OnPageSEOAgency
from agents.site_intelligence_agent import OverseerRefreshValidator, SiteIntelligenceAgent
from agents.site_wide_auditor_agent import SiteWideAuditorAgent
from agents.the_overseer import TheOverseer
from scripts.ghost_contracts import (
    CONTRACT_VERSION,
    GOLDEN_ROOT,
    MAX_FALLBACK_RATE_REGRESSION,
    MAX_MISSING_REQUIRED_FIELD_RATE_REGRESSION,
)

EXPECTED_STAGE_ORDER = [
    "boss_agent",
    "content_agency",
    "onpage_seo_agency",
    "the_overseer",
    "approval_agent",
]

CONTRACT_OBJECTS_BY_STAGE = {
    "site_intelligence": ["candidate", "checklist", "brief", "validation", "issue_payload", "diagnostics"],
    "boss_agent": ["research_brief", "boss_handoff"],
    "content_agency": ["raw_draft", "content_handoff"],
    "onpage_seo_agency": ["optimized_content", "seo_handoff"],
    "the_overseer": ["terminal_briefing", "terminal_dispatch"],
    "approval_agent": [
        "approval_issue_payload",
        "approval_decision",
        "deployment_signal",
        "workflow_dispatch_payload",
    ],
}

REQUIRED_PATHS_BY_STAGE = {
    "site_intelligence": [
        "candidate.url_slug",
        "checklist.checks",
        "brief.brief_id",
        "validation.validation_status",
        "issue_payload.title",
        "diagnostics.mode",
        "diagnostics.fallback_used",
        "diagnostics.error_reasons",
    ],
    "boss_agent": [
        "boss_handoff.status",
        "research_brief.directive_id",
        "research_brief.primary_topic",
        "research_brief.primary_keywords",
    ],
    "content_agency": [
        "content_handoff.status",
        "raw_draft.draft_id",
        "raw_draft.full_draft",
        "raw_draft.overall_word_count",
    ],
    "onpage_seo_agency": [
        "seo_handoff.status",
        "optimized_content.content_id",
        "optimized_content.url_slug",
        "optimized_content.meta_tags.title",
        "optimized_content.meta_tags.description",
        "optimized_content.schema_markup",
    ],
    "the_overseer": [
        "terminal_briefing.briefing_id",
        "terminal_briefing.pipeline_status",
        "terminal_briefing.critical_metrics",
        "terminal_dispatch.dispatch_type",
        "terminal_dispatch.executive_dashboard.quality_score",
    ],
    "approval_agent": [
        "approval_issue_payload.title",
        "approval_issue_payload.body",
        "approval_issue_payload.labels",
        "approval_decision.status",
        "deployment_signal.signal_type",
    ],
}

VALID_CONTENT_TYPES = {value.value for value in ContentType}
VALID_TARGET_AUDIENCES = {value.value for value in TargetAudience}
VALID_APPROVAL_STATUSES = {"approved", "rejected", "revision_requested"}

DEFAULT_CONTENT_TYPE = ContentType.INDUSTRY_REPORT.value
DEFAULT_TARGET_AUDIENCE = TargetAudience.PRODUCT_MANAGERS.value
DEFAULT_APPROVAL_STATUS = "revision_requested"


def _to_dict(value: Any) -> Any:
    return asdict(value) if is_dataclass(value) else value


def _elapsed_ms(start_time: float) -> int:
    return int((time.perf_counter() - start_time) * 1000)


def _require_path(data: Dict[str, Any], path: str) -> bool:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _get_path(data: Dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _record_check(
    checks: List[Dict[str, Any]],
    name: str,
    passed: bool,
    detail: str = "",
    stage: str = "pipeline",
    kind: str = "contract",
) -> None:
    checks.append(
        {
            "check": name,
            "passed": passed,
            "detail": detail,
            "stage": stage,
            "kind": kind,
        }
    )


def _versioned_payload(value: Dict[str, Any], contract_name: str) -> Dict[str, Any]:
    payload = copy.deepcopy(value)
    payload["contract_version"] = CONTRACT_VERSION
    payload["contract_name"] = contract_name
    return payload


def _dedupe_messages(messages: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for message in messages:
        if message and message not in seen:
            ordered.append(message)
            seen.add(message)
    return ordered


def _safe_int(value: Any, default: int, minimum: int = 0) -> int:
    try:
        return max(int(value), minimum)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        return min(max(float(value), minimum), maximum)
    except (TypeError, ValueError):
        return default


def _normalize_gsc_entry(post: Any, index: int, reasons: List[str]) -> Dict[str, Any]:
    if not isinstance(post, dict):
        reasons.append(f"site_intel.gsc_data[{index}] was not an object; row ignored.")
        return {}

    normalized = {
        "post_id": str(post.get("post_id") or f"ghost_post_{index}"),
        "url_slug": str(post.get("url_slug") or f"ghost-slug-{index}"),
        "title": str(post.get("title") or f"Ghost Scenario Post {index}"),
        "published_date": str(post.get("published_date") or ""),
        "position": _safe_int(post.get("position"), 100, minimum=0),
        "impressions": _safe_int(post.get("impressions"), 0, minimum=0),
        "clicks": _safe_int(post.get("clicks"), 0, minimum=0),
    }

    if post.get("position") != normalized["position"]:
        reasons.append(f"site_intel.gsc_data[{index}].position was invalid; defaulted to {normalized['position']}.")
    if post.get("impressions") != normalized["impressions"]:
        reasons.append(
            f"site_intel.gsc_data[{index}].impressions was invalid; defaulted to {normalized['impressions']}."
        )
    if post.get("clicks") != normalized["clicks"]:
        reasons.append(f"site_intel.gsc_data[{index}].clicks was invalid; defaulted to {normalized['clicks']}.")

    if post.get("last_updated") is not None:
        normalized["last_updated"] = str(post.get("last_updated"))

    return normalized


def _normalize_ga4_metrics(raw_metrics: Any, reasons: List[str]) -> Dict[str, Dict[str, Any]]:
    if not isinstance(raw_metrics, dict):
        reasons.append("site_intel.ga4_metrics was not an object; GA4 metrics ignored.")
        return {}

    normalized: Dict[str, Dict[str, Any]] = {}
    for slug, metrics in raw_metrics.items():
        if not isinstance(metrics, dict):
            reasons.append(f"site_intel.ga4_metrics[{slug}] was not an object; row ignored.")
            continue
        normalized[str(slug)] = {
            "sessions": _safe_int(metrics.get("sessions"), 0, minimum=0),
            "engagement_rate": _safe_float(metrics.get("engagement_rate"), 0.0),
            "conversions": _safe_float(metrics.get("conversions"), 0.0, minimum=0.0, maximum=1000000.0),
        }
    return normalized


def _normalize_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(scenario)
    reasons: List[str] = []
    fallback_stages = set()

    content_type = normalized.get("content_type", DEFAULT_CONTENT_TYPE)
    if content_type not in VALID_CONTENT_TYPES:
        reasons.append(f"content_type '{content_type}' is unsupported; defaulted to '{DEFAULT_CONTENT_TYPE}'.")
        normalized["content_type"] = DEFAULT_CONTENT_TYPE
        fallback_stages.add("boss_agent")

    target_audience = normalized.get("target_audience", DEFAULT_TARGET_AUDIENCE)
    if target_audience not in VALID_TARGET_AUDIENCES:
        reasons.append(
            f"target_audience '{target_audience}' is unsupported; defaulted to '{DEFAULT_TARGET_AUDIENCE}'."
        )
        normalized["target_audience"] = DEFAULT_TARGET_AUDIENCE
        fallback_stages.add("boss_agent")

    approval_status = normalized.get("approval_status", DEFAULT_APPROVAL_STATUS)
    if approval_status not in VALID_APPROVAL_STATUSES:
        reasons.append(
            f"approval_status '{approval_status}' is unsupported; defaulted to '{DEFAULT_APPROVAL_STATUS}'."
        )
        normalized["approval_status"] = DEFAULT_APPROVAL_STATUS
        fallback_stages.add("approval_agent")

    site_cfg = normalized.get("site_intel")
    if not isinstance(site_cfg, dict):
        reasons.append("site_intel was missing or invalid; defaulted to an empty fixture.")
        site_cfg = {}
    simulate_api_failure = bool(site_cfg.get("simulate_api_failure", False))
    gsc_data = site_cfg.get("gsc_data", [])
    ga4_metrics = site_cfg.get("ga4_metrics", {})

    if not isinstance(gsc_data, list):
        reasons.append("site_intel.gsc_data was not a list; using an empty list.")
        gsc_data = []

    normalized_gsc = []
    for index, post in enumerate(gsc_data):
        post_payload = _normalize_gsc_entry(post, index, reasons)
        if post_payload:
            normalized_gsc.append(post_payload)

    normalized_ga4 = _normalize_ga4_metrics(ga4_metrics, reasons)

    if simulate_api_failure:
        fallback_stages.add("site_intelligence")
    if not normalized_ga4:
        fallback_stages.add("site_intelligence")
        reasons.append("GA4 metrics unavailable; site intelligence will use fallback scoring.")
    if not normalized_gsc:
        fallback_stages.add("site_intelligence")
        reasons.append("No valid GSC rows available; site intelligence will use its mock candidate fallback.")

    normalized["site_intel"] = {
        "simulate_api_failure": simulate_api_failure,
        "gsc_data": normalized_gsc,
        "ga4_metrics": normalized_ga4,
    }
    normalized["_ghost_hardening"] = {
        "input_error_reasons": _dedupe_messages(reasons),
        "fallback_stages": sorted(fallback_stages),
        "graceful_degradation": bool(reasons),
    }
    return normalized


def _run_site_intel(scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    start_time = time.perf_counter()
    site_cfg = scenario.get("site_intel", {})
    gsc_data = site_cfg.get("gsc_data", [])
    simulate_api_failure = bool(site_cfg.get("simulate_api_failure", False))
    ga4_metrics = site_cfg.get("ga4_metrics", {}) if not simulate_api_failure else None

    agent = SiteIntelligenceAgent()
    overseer = OverseerRefreshValidator()

    no_candidate_fallback_used = False
    try:
        candidate = agent.select_weekly_candidate(gsc_data, ga4_metrics)
    except ValueError:
        no_candidate_fallback_used = True
        candidate = agent.select_weekly_candidate(
            [
                {
                    "post_id": "sample_post",
                    "url_slug": "sample-post",
                    "title": "Sample Post for Refresh",
                    "published_date": "2024-01-01",
                    "position": 8,
                    "impressions": 3000,
                    "clicks": 45,
                }
            ],
            None,
        )
    checklist = agent.create_refresh_checklist(candidate)
    brief = agent.create_overseer_brief(candidate, checklist)
    validation = overseer.validate_refresh_brief(brief)
    issue_payload = agent.create_github_issue_payload(brief)

    error_reasons = list(scenario.get("_ghost_hardening", {}).get("input_error_reasons", []))
    if simulate_api_failure:
        error_reasons.append("GA4 API failure was intentionally simulated.")
    if not ga4_metrics:
        error_reasons.append("GA4 metrics unavailable; site intelligence will use fallback scoring.")
    if not gsc_data:
        error_reasons.append("No valid GSC rows available; site intelligence will use its mock candidate fallback.")
    error_reasons = _dedupe_messages(error_reasons)

    fallback_used = bool(simulate_api_failure or not ga4_metrics or not gsc_data or no_candidate_fallback_used)
    diagnostics = _versioned_payload(
        {
            "mode": "ghost",
            "fallback_used": fallback_used,
            "api_failure_simulated": simulate_api_failure,
            "ga4_records": len(ga4_metrics or {}),
            "candidate_slug": candidate.url_slug,
            "validation_status": validation.get("validation_status"),
            "checklist_complete": validation.get("all_passed"),
            "error_reasons": error_reasons,
            "graceful_degradation": bool(error_reasons),
            "generated_at": datetime.now().isoformat(),
        },
        "site_intelligence.diagnostics",
    )

    return (
        {
            "candidate": _versioned_payload(_to_dict(candidate), "site_intelligence.candidate"),
            "checklist": _versioned_payload(_to_dict(checklist), "site_intelligence.checklist"),
            "brief": _versioned_payload(_to_dict(brief), "site_intelligence.brief"),
            "validation": _versioned_payload(validation, "site_intelligence.validation"),
            "issue_payload": _versioned_payload(issue_payload, "site_intelligence.issue_payload"),
            "diagnostics": diagnostics,
        },
        _elapsed_ms(start_time),
    )


def _run_site_ops() -> Dict[str, Any]:
    """Run SiteWideAuditorAgent and ContentRefreshAgent in ghost mode.

    Both agents are wired as optional: errors are captured rather than
    propagated so they cannot fail the main harness run.
    """
    result: Dict[str, Any] = {}

    try:
        auditor = SiteWideAuditorAgent()
        audit_report = auditor.audit_site()
        result["site_wide_audit"] = {
            "health_score": audit_report.health_score,
            "broken_links": audit_report.broken_links,
            "missing_alt_urls": audit_report.missing_alt_urls,
            "structural_warnings": audit_report.structural_warnings,
            "error": None,
        }
    except Exception as exc:
        result["site_wide_audit"] = {"error": str(exc)}

    try:
        refresh_agent = ContentRefreshAgent()
        index = refresh_agent.build_sitemap_index()
        result["content_refresh"] = {
            "entry_count": len(index),
            "entries": index,
            "error": None,
        }
    except Exception as exc:
        result["content_refresh"] = {"error": str(exc)}

    return result


def _run_pipeline(scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int], List[str]]:
    boss = BossAgent()
    content = ContentAgency()
    seo = OnPageSEOAgency()
    overseer = TheOverseer()
    approval = ApprovalAgent()

    topic = scenario.get("topic", "AI-Powered Content Automation")
    industry = scenario.get("industry", "General")
    content_type = ContentType(scenario.get("content_type", DEFAULT_CONTENT_TYPE))
    audience = TargetAudience(scenario.get("target_audience", DEFAULT_TARGET_AUDIENCE))

    fallback_stages = list(scenario.get("_ghost_hardening", {}).get("fallback_stages", []))
    stage_order: List[str] = []
    stage_timings: Dict[str, int] = {}

    start_time = time.perf_counter()
    directive = boss.generate_content_directive(
        topic=topic,
        content_type=content_type,
        target_audience=audience,
        industry=industry,
    )
    research_brief = _versioned_payload(asdict(directive), "boss_agent.research_brief")
    boss_handoff = _versioned_payload(boss.handoff_to_content_agency(directive), "boss_agent.handoff")
    stage_timings["boss_agent"] = _elapsed_ms(start_time)
    stage_order.append("boss_agent")

    research_brief["research_brief_id"] = directive.directive_id
    research_brief["primary_topic"] = directive.target_focus

    start_time = time.perf_counter()
    raw_draft = content.process_research_brief(research_brief)
    raw_draft_dict = _versioned_payload(asdict(raw_draft), "content_agency.raw_draft")
    content_handoff = _versioned_payload(
        content.handoff_to_onpage_seo_agency(raw_draft),
        "content_agency.handoff",
    )
    stage_timings["content_agency"] = _elapsed_ms(start_time)
    stage_order.append("content_agency")

    primary_keywords = research_brief.get("primary_keywords") or [topic]

    start_time = time.perf_counter()
    optimized = seo.process_raw_creative_draft(raw_draft_dict, primary_keywords)
    optimized_dict = _versioned_payload(asdict(optimized), "onpage_seo_agency.optimized_content")
    seo_handoff = _versioned_payload(seo.handoff_to_overseer(optimized), "onpage_seo_agency.handoff")
    stage_timings["onpage_seo_agency"] = _elapsed_ms(start_time)
    stage_order.append("onpage_seo_agency")

    start_time = time.perf_counter()
    briefing = overseer.process_pipeline_output(research_brief, raw_draft_dict, optimized_dict)
    briefing_dict = _versioned_payload(asdict(briefing), "the_overseer.terminal_briefing")
    dispatch = _versioned_payload(overseer.generate_terminal_dispatch(briefing), "the_overseer.dispatch"    )
    stage_timings["the_overseer"] = _elapsed_ms(start_time)
    stage_order.append("the_overseer")

    start_time = time.perf_counter()
    issue_payload = _versioned_payload(_to_dict(approval.create_approval_issue(briefing_dict)), "approval_agent.issue")
    approval_status = scenario.get("approval_status", DEFAULT_APPROVAL_STATUS)
    decision = approval.process_approval_decision(
        briefing_id=briefing_dict["briefing_id"],
        github_issue_number=0,
        github_issue_url="https://example.invalid/ghost",
        approval_status=approval_status,
        approved_by="ghost-runner",
        approval_method="ghost",
        approval_comment="Ghost test run",
    )
    approval_decision = _versioned_payload(asdict(decision), "approval_agent.decision")
    deployment_signal = _versioned_payload(
        approval.generate_deployment_signal(
            decision,
            content_id=optimized_dict.get("content_id", "ghost-content"),
            content_url_slug=optimized_dict.get("url_slug", "ghost-content"),
        ),
        "approval_agent.deployment_signal",
    )
    workflow_payload = _versioned_payload(
        approval.create_workflow_dispatch_payload(deployment_signal),
        "approval_agent.workflow_dispatch_payload",
    )
    stage_timings["approval_agent"] = _elapsed_ms(start_time)
    stage_order.append("approval_agent")

    return (
        {
            "stage_order": stage_order,
            "boss_handoff": boss_handoff,
            "research_brief": research_brief,
            "content_handoff": content_handoff,
            "raw_draft": raw_draft_dict,
            "seo_handoff": seo_handoff,
            "optimized_content": optimized_dict,
            "terminal_briefing": briefing_dict,
            "terminal_dispatch": dispatch,
            "approval_issue_payload": issue_payload,
            "approval_decision": approval_decision,
            "deployment_signal": deployment_signal,
            "workflow_dispatch_payload": workflow_payload,
        },
        stage_timings,
        fallback_stages,
    )


def _validate_contracts(site_intel: Dict[str, Any], pipeline: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    _record_check(
        checks,
        "stage_order",
        pipeline.get("stage_order") == EXPECTED_STAGE_ORDER,
        f"actual={pipeline.get('stage_order')}",
        stage="pipeline",
        kind="handoff",
    )

    grouped_roots = {"site_intelligence": site_intel, **{stage: pipeline for stage in EXPECTED_STAGE_ORDER}}

    for stage, object_names in CONTRACT_OBJECTS_BY_STAGE.items():
        root = grouped_roots[stage]
        for object_name in object_names:
            payload = root.get(object_name, {})
            actual_version = payload.get("contract_version") if isinstance(payload, dict) else None
            _record_check(
                checks,
                f"contract_version:{object_name}",
                actual_version == CONTRACT_VERSION,
                f"expected={CONTRACT_VERSION} actual={actual_version or 'missing'}",
                stage=stage,
                kind="contract_version",
            )

    for stage, paths in REQUIRED_PATHS_BY_STAGE.items():
        root = grouped_roots[stage]
        for path in paths:
            _record_check(
                checks,
                f"required:{path}",
                _require_path(root, path),
                stage=stage,
                kind="required_field",
            )

    _record_check(
        checks,
        "handoff:research_to_content",
        pipeline["raw_draft"].get("research_brief_id") == pipeline["research_brief"].get("research_brief_id"),
        stage="content_agency",
        kind="handoff",
    )
    _record_check(
        checks,
        "handoff:content_to_seo",
        pipeline["optimized_content"].get("raw_draft_id") == pipeline["raw_draft"].get("draft_id"),
        stage="onpage_seo_agency",
        kind="handoff",
    )
    _record_check(
        checks,
        "handoff:seo_to_overseer",
        pipeline["terminal_briefing"].get("technical_phase", {}).get("content_id")
        == pipeline["optimized_content"].get("content_id"),
        stage="the_overseer",
        kind="handoff",
    )
    _record_check(
        checks,
        "handoff:ghost_dispatch_blocked",
        pipeline["deployment_signal"].get("signal_type") == "DEPLOYMENT_BLOCKED_DRY_RUN",
        f"signal_type={pipeline['deployment_signal'].get('signal_type')}",
        stage="approval_agent",
        kind="handoff",
    )

    return checks


def _build_snapshot(site_intel: Dict[str, Any], pipeline: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "stage_order": pipeline.get("stage_order", []),
        "site_intelligence": {
            "candidate_slug": site_intel["candidate"].get("url_slug"),
            "candidate_title": site_intel["candidate"].get("title"),
            "validation_status": site_intel["validation"].get("validation_status"),
            "checklist_complete": site_intel["diagnostics"].get("checklist_complete"),
            "fallback_used": site_intel["diagnostics"].get("fallback_used"),
            "error_reasons": site_intel["diagnostics"].get("error_reasons", []),
            "issue_title": site_intel["issue_payload"].get("title"),
        },
        "boss_agent": {
            "target_focus": pipeline["research_brief"].get("target_focus"),
            "content_type": pipeline["research_brief"].get("content_type"),
            "primary_keywords": pipeline["research_brief"].get("primary_keywords"),
            "handoff_status": pipeline["boss_handoff"].get("status"),
        },
        "content_agency": {
            "voice_used": pipeline["raw_draft"].get("voice_used"),
            "tone_used": pipeline["raw_draft"].get("tone_used"),
            "section_count": len(pipeline["raw_draft"].get("content_sections", [])),
            "handoff_status": pipeline["content_handoff"].get("status"),
        },
        "onpage_seo_agency": {
            "url_slug": pipeline["optimized_content"].get("url_slug"),
            "seo_score": pipeline["optimized_content"].get("seo_score"),
            "reading_time_minutes": pipeline["optimized_content"].get("reading_time_minutes"),
            "internal_link_count": len(pipeline["optimized_content"].get("internal_links", [])),
            "warnings_count": len(pipeline["optimized_content"].get("warnings", [])),
            "handoff_status": pipeline["seo_handoff"].get("status"),
        },
        "the_overseer": {
            "pipeline_status": pipeline["terminal_briefing"].get("pipeline_status"),
            "total_quality_score": pipeline["terminal_briefing"].get("total_quality_score"),
            "risk_level": pipeline["terminal_briefing"].get("risk_level"),
            "production_ready": pipeline["terminal_briefing"].get("production_ready"),
            "content_url": pipeline["terminal_briefing"].get("content_url"),
            "dispatch_type": pipeline["terminal_dispatch"].get("dispatch_type"),
        },
        "approval_agent": {
            "labels": sorted(pipeline["approval_issue_payload"].get("labels", [])),
            "decision_status": pipeline["approval_decision"].get("status"),
            "signal_type": pipeline["deployment_signal"].get("signal_type"),
            "workflow_dispatch_enabled": bool(pipeline["workflow_dispatch_payload"].get("inputs")),
        },
    }


def _diff_values(path: str, baseline: Any, current: Any, diffs: List[Dict[str, Any]]) -> None:
    if isinstance(baseline, dict) and isinstance(current, dict):
        all_keys = sorted(set(baseline) | set(current))
        for key in all_keys:
            next_path = f"{path}.{key}" if path else key
            if key not in baseline:
                diffs.append({"path": next_path, "type": "added", "baseline": None, "current": current[key]})
            elif key not in current:
                diffs.append({"path": next_path, "type": "removed", "baseline": baseline[key], "current": None})
            else:
                _diff_values(next_path, baseline[key], current[key], diffs)
        return

    if baseline != current:
        diffs.append({"path": path, "type": "changed", "baseline": baseline, "current": current})


def _build_reliability_metrics(
    scenario_name: str,
    checks: List[Dict[str, Any]],
    stage_timings: Dict[str, int],
    fallback_stages: List[str],
    site_intel_fallback_used: bool,
) -> Dict[str, Any]:
    fallback_set = set(fallback_stages)
    if site_intel_fallback_used:
        fallback_set.add("site_intelligence")

    stage_names = ["site_intelligence", *EXPECTED_STAGE_ORDER]
    metrics = {
        "scenario": scenario_name,
        "contract_version": CONTRACT_VERSION,
        "definitions": {
            "pass_rate": "Passed checks divided by total checks for the stage in this single run.",
            "fallback_rate": "1.0 when the stage used a fallback or defaulted input during this run, otherwise 0.0.",
            "retry_rate": "Retries attempted divided by retry opportunities; the harness does not retry stages today so this is deterministically 0.0.",
            "avg_runtime_ms": "Wall-clock runtime for the stage in milliseconds for this run.",
            "missing_required_field_rate": "Failed required-field checks divided by total required-field checks for the stage.",
        },
        "stages": {},
    }

    for stage in stage_names:
        stage_checks = [check for check in checks if check["stage"] == stage]
        required_checks = [check for check in stage_checks if check["kind"] == "required_field"]
        passed_checks = sum(1 for check in stage_checks if check["passed"])
        failed_required_checks = sum(1 for check in required_checks if not check["passed"])
        total_checks = len(stage_checks)
        total_required_checks = len(required_checks)

        metrics["stages"][stage] = {
            "pass_rate": round(passed_checks / total_checks, 4) if total_checks else 1.0,
            "fallback_rate": 1.0 if stage in fallback_set else 0.0,
            "retry_rate": 0.0,
            "avg_runtime_ms": stage_timings.get(stage, 0),
            "missing_required_field_rate": (
                round(failed_required_checks / total_required_checks, 4) if total_required_checks else 0.0
            ),
            "checks_passed": passed_checks,
            "checks_total": total_checks,
            "required_fields_missing": failed_required_checks,
            "required_fields_total": total_required_checks,
        }

    return metrics


def _build_quality_gate_report(
    scenario_name: str,
    baseline_metrics: Dict[str, Any],
    current_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    thresholds = {
        "fallback_rate": MAX_FALLBACK_RATE_REGRESSION,
        "missing_required_field_rate": MAX_MISSING_REQUIRED_FIELD_RATE_REGRESSION,
    }
    regressions: List[Dict[str, Any]] = []

    for stage, current_stage in current_metrics.get("stages", {}).items():
        baseline_stage = baseline_metrics.get("stages", {}).get(stage)
        if baseline_stage is None:
            regressions.append(
                {
                    "stage": stage,
                    "metric": "baseline_missing",
                    "baseline": None,
                    "current": current_stage,
                    "threshold": None,
                    "message": f"{stage}: missing baseline metrics for regression comparison.",
                }
            )
            continue

        for metric_name, threshold in thresholds.items():
            baseline_value = baseline_stage.get(metric_name, 0.0)
            current_value = current_stage.get(metric_name, 0.0)
            if current_value > baseline_value + threshold:
                regressions.append(
                    {
                        "stage": stage,
                        "metric": metric_name,
                        "baseline": baseline_value,
                        "current": current_value,
                        "threshold": threshold,
                        "message": (
                            f"{stage}: {metric_name} regressed from {baseline_value} to {current_value} "
                            f"(allowed increase {threshold})."
                        ),
                    }
                )

    return {
        "scenario": scenario_name,
        "contract_version": CONTRACT_VERSION,
        "passed": not regressions,
        "thresholds": thresholds,
        "regressions": regressions,
    }


def _build_markdown_summary(
    scenario_name: str,
    report: Dict[str, Any],
    reliability_metrics: Dict[str, Any],
    golden_diff_report: Dict[str, Any],
    quality_gate_report: Dict[str, Any],
) -> str:
    lines = [
        f"# Ghost Summary: {scenario_name}",
        "",
        f"- Contract version: `{CONTRACT_VERSION}`",
        f"- Success: `{report['success']}`",
        f"- Golden snapshot status: `{golden_diff_report['status']}`",
        f"- Quality gate passed: `{quality_gate_report['passed']}`",
        "",
        "## Reliability Metrics",
        "",
        "| Stage | pass_rate | fallback_rate | retry_rate | missing_required_field_rate | avg_runtime_ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for stage, metrics in reliability_metrics["stages"].items():
        lines.append(
            "| {stage} | {pass_rate} | {fallback_rate} | {retry_rate} | {missing_rate} | {runtime} |".format(
                stage=stage,
                pass_rate=metrics["pass_rate"],
                fallback_rate=metrics["fallback_rate"],
                retry_rate=metrics["retry_rate"],
                missing_rate=metrics["missing_required_field_rate"],
                runtime=metrics["avg_runtime_ms"],
            )
        )

    lines.extend(["", "## Golden Diff"])
    if golden_diff_report["unexpected_diffs"]:
        for diff in golden_diff_report["unexpected_diffs"]:
            lines.append(
                f"- `{diff['path']}` {diff['type']}: baseline={diff['baseline']!r}, current={diff['current']!r}"
            )
    else:
        lines.append("- No unexpected semantic diffs.")

    lines.extend(["", "## Regression Gate"])
    if quality_gate_report["regressions"]:
        for regression in quality_gate_report["regressions"]:
            lines.append(f"- {regression['message']}")
    else:
        lines.append("- No fallback-rate or missing-field regressions detected.")

    if report.get("failure_reasons"):
        lines.extend(["", "## Failures"])
        for reason in report["failure_reasons"]:
            lines.append(f"- {reason}")

    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ghost-mode end-to-end harness")
    parser.add_argument("--scenario", required=True, help="Scenario name")
    parser.add_argument(
        "--fixtures-dir",
        default="tests/fixtures/ghost_scenarios",
        help="Scenario fixtures directory",
    )
    parser.add_argument(
        "--output-dir",
        default="ghost-artifacts",
        help="Output artifacts directory",
    )
    parser.add_argument(
        "--update-goldens",
        action="store_true",
        help="Refresh the checked-in golden snapshot and baseline metrics for this scenario.",
    )
    args = parser.parse_args()

    output_root = Path(args.output_dir) / args.scenario
    output_root.mkdir(parents=True, exist_ok=True)
    logs_dir = output_root / "agent_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    controls: Dict[str, Any] = {}
    report: Dict[str, Any]
    try:
        controls = ghost_controls()
        if not (controls["ghost_mode"] and controls["dry_run"] and not controls["allow_side_effects"]):
            raise RuntimeError(
                "Ghost harness requires GHOST_MODE=true, DRY_RUN=true, ALLOW_SIDE_EFFECTS=false"
            )

        fixture_path = Path(args.fixtures_dir) / f"{args.scenario}.json"
        if not fixture_path.exists():
            raise FileNotFoundError(f"Missing scenario fixture: {fixture_path}")

        scenario = _normalize_scenario(json.loads(fixture_path.read_text(encoding="utf-8")))
        site_intel, site_intel_runtime_ms = _run_site_intel(scenario)
        site_ops = _run_site_ops()
        pipeline, pipeline_stage_timings, fallback_stages = _run_pipeline(scenario)
        checks = _validate_contracts(site_intel, pipeline)

        stage_timings = {"site_intelligence": site_intel_runtime_ms, **pipeline_stage_timings}
        reliability_metrics = _build_reliability_metrics(
            args.scenario,
            checks,
            stage_timings,
            fallback_stages,
            site_intel["diagnostics"]["fallback_used"],
        )
        snapshot = _build_snapshot(site_intel, pipeline)

        golden_path = REPO_ROOT / GOLDEN_ROOT / f"{args.scenario}.json"
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_baseline = {
            "scenario": args.scenario,
            "contract_version": CONTRACT_VERSION,
            "snapshot": snapshot,
            "reliability_metrics": reliability_metrics,
        }

        previous_baseline = json.loads(golden_path.read_text(encoding="utf-8")) if golden_path.exists() else None
        if args.update_goldens:
            _write_json(golden_path, golden_baseline)

        baseline_payload = previous_baseline
        unexpected_diffs: List[Dict[str, Any]] = []
        if baseline_payload is not None:
            _diff_values("", baseline_payload.get("snapshot", {}), snapshot, unexpected_diffs)
            quality_gate_report = _build_quality_gate_report(
                args.scenario,
                baseline_payload.get("reliability_metrics", {}),
                reliability_metrics,
            )
            if args.update_goldens:
                golden_status = "updated"
            else:
                golden_status = "match" if not unexpected_diffs else "diff"
        elif args.update_goldens:
            quality_gate_report = {
                "scenario": args.scenario,
                "contract_version": CONTRACT_VERSION,
                "passed": True,
                "thresholds": {
                    "fallback_rate": MAX_FALLBACK_RATE_REGRESSION,
                    "missing_required_field_rate": MAX_MISSING_REQUIRED_FIELD_RATE_REGRESSION,
                },
                "regressions": [],
            }
            golden_status = "updated"
        else:
            quality_gate_report = {
                "scenario": args.scenario,
                "contract_version": CONTRACT_VERSION,
                "passed": False,
                "thresholds": {
                    "fallback_rate": MAX_FALLBACK_RATE_REGRESSION,
                    "missing_required_field_rate": MAX_MISSING_REQUIRED_FIELD_RATE_REGRESSION,
                },
                "regressions": [
                    {
                        "stage": "baseline",
                        "metric": "missing_golden",
                        "baseline": None,
                        "current": args.scenario,
                        "threshold": None,
                        "message": f"Missing golden baseline at {golden_path}. Run with --update-goldens.",
                    }
                ],
            }
            golden_status = "missing"

        success = all(check["passed"] for check in checks)
        failure_reasons: List[str] = []
        if not success:
            failed_checks = [check["check"] for check in checks if not check["passed"]]
            failure_reasons.append(f"Contract validation failed: {failed_checks}")
        if unexpected_diffs and not args.update_goldens:
            failure_reasons.append(
                f"Golden snapshot drift detected for {args.scenario}; review golden_diff_report.json and refresh intentionally if expected."
            )
        if baseline_payload is None and not args.update_goldens:
            failure_reasons.append(
                f"Missing golden baseline for {args.scenario}; run `python scripts/ghost_harness.py --scenario {args.scenario} --update-goldens` intentionally."
            )
        if quality_gate_report["regressions"] and not args.update_goldens:
            failure_reasons.append(
                "Quality gate regression detected: "
                + "; ".join(regression["message"] for regression in quality_gate_report["regressions"])
            )

        golden_diff_report = {
            "scenario": args.scenario,
            "contract_version": CONTRACT_VERSION,
            "status": golden_status,
            "golden_path": str(golden_path.relative_to(REPO_ROOT)),
            "unexpected_diffs": unexpected_diffs,
            "update_hint": f"python scripts/ghost_harness.py --scenario {args.scenario} --update-goldens",
        }

        report = {
            "scenario": args.scenario,
            "timestamp": datetime.now().isoformat(),
            "contract_version": CONTRACT_VERSION,
            "ghost_controls": controls,
            "fallback_used": site_intel["diagnostics"]["fallback_used"],
            "contract_checks": checks,
            "success": not failure_reasons and success,
            "failure_reasons": failure_reasons,
            "golden_diff_status": golden_diff_report["status"],
            "quality_gate_passed": quality_gate_report["passed"],
        }

        summary_markdown = _build_markdown_summary(
            args.scenario,
            report,
            reliability_metrics,
            golden_diff_report,
            quality_gate_report,
        )

        _write_json(output_root / "pipeline_result.json", pipeline)
        _write_json(output_root / "site_intel_diagnostics.json", site_intel["diagnostics"])
        _write_json(output_root / "site_ops_result.json", site_ops)
        _write_json(output_root / "ghost_run_report.json", report)
        _write_json(output_root / "golden_snapshot.json", snapshot)
        _write_json(output_root / "golden_diff_report.json", golden_diff_report)
        _write_json(output_root / "reliability_metrics.json", reliability_metrics)
        _write_json(output_root / "quality_gate_report.json", quality_gate_report)
        (output_root / "ghost_summary.md").write_text(summary_markdown, encoding="utf-8")
        (logs_dir / "stages.log").write_text(
            "\n".join(
                [
                    f"scenario={args.scenario}",
                    f"contract_version={CONTRACT_VERSION}",
                    f"ghost_mode={controls['ghost_mode']}",
                    f"dry_run={controls['dry_run']}",
                    f"allow_side_effects={controls['allow_side_effects']}",
                    f"fallback_used={site_intel['diagnostics']['fallback_used']}",
                    f"stage_order={','.join(pipeline['stage_order'])}",
                    f"golden_status={golden_status}",
                    f"quality_gate_passed={quality_gate_report['passed']}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        if failure_reasons:
            (logs_dir / "error.log").write_text("\n".join(failure_reasons) + "\n", encoding="utf-8")
            return 1

    except Exception as exc:
        report = {
            "scenario": args.scenario,
            "timestamp": datetime.now().isoformat(),
            "contract_version": CONTRACT_VERSION,
            "ghost_controls": controls,
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        _write_json(output_root / "ghost_run_report.json", report)
        (logs_dir / "error.log").write_text(report["traceback"], encoding="utf-8")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
