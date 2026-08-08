#!/usr/bin/env python3
import argparse
import json
import os
import sys
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.approval_agent import ApprovalAgent
from agents.boss_agent import BossAgent, ContentType, TargetAudience
from agents.content_agency import ContentAgency
from agents.onpage_seo_agency import OnPageSEOAgency
from agents.site_intelligence_agent import OverseerRefreshValidator, SiteIntelligenceAgent
from agents.the_overseer import TheOverseer


TRUTHY = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY


def _ghost_controls() -> Dict[str, bool]:
    ghost_mode = _env_flag("GHOST_MODE", False)
    dry_run = _env_flag("DRY_RUN", ghost_mode)
    allow_side_effects_default = not (ghost_mode or dry_run)
    allow_side_effects = _env_flag("ALLOW_SIDE_EFFECTS", allow_side_effects_default)
    return {
        "ghost_mode": ghost_mode,
        "dry_run": dry_run,
        "allow_side_effects": allow_side_effects,
    }


def _to_dict(value: Any) -> Any:
    return asdict(value) if is_dataclass(value) else value


def _require_path(data: Dict[str, Any], path: str) -> bool:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _record_check(checks: List[Dict[str, Any]], name: str, passed: bool, detail: str = "") -> None:
    checks.append({"check": name, "passed": passed, "detail": detail})


def _run_site_intel(scenario: Dict[str, Any]) -> Dict[str, Any]:
    site_cfg = scenario.get("site_intel", {})
    gsc_data = site_cfg.get("gsc_data", [])
    simulate_api_failure = bool(site_cfg.get("simulate_api_failure", False))
    ga4_metrics = site_cfg.get("ga4_metrics", {}) if not simulate_api_failure else None

    agent = SiteIntelligenceAgent()
    overseer = OverseerRefreshValidator()

    candidate = agent.select_weekly_candidate(gsc_data, ga4_metrics)
    checklist = agent.create_refresh_checklist(candidate)
    brief = agent.create_overseer_brief(candidate, checklist)
    validation = overseer.validate_refresh_brief(brief)
    issue_payload = agent.create_github_issue_payload(brief)

    fallback_used = simulate_api_failure or not ga4_metrics

    diagnostics = {
        "mode": "ghost",
        "fallback_used": fallback_used,
        "api_failure_simulated": simulate_api_failure,
        "ga4_records": len(ga4_metrics or {}),
        "candidate_slug": candidate.url_slug,
        "validation_status": validation.get("validation_status"),
        "checklist_complete": validation.get("all_passed"),
        "generated_at": datetime.now().isoformat(),
    }

    return {
        "candidate": _to_dict(candidate),
        "checklist": _to_dict(checklist),
        "brief": _to_dict(brief),
        "validation": validation,
        "issue_payload": issue_payload,
        "diagnostics": diagnostics,
    }


def _run_pipeline(scenario: Dict[str, Any]) -> Dict[str, Any]:
    boss = BossAgent()
    content = ContentAgency()
    seo = OnPageSEOAgency()
    overseer = TheOverseer()
    approval = ApprovalAgent()

    topic = scenario.get("topic", "AI-Powered Content Automation")
    industry = scenario.get("industry", "General")
    content_type = ContentType(scenario.get("content_type", "industry_report"))
    audience = TargetAudience(scenario.get("target_audience", "product_managers"))

    stage_order: List[str] = []

    directive = boss.generate_content_directive(
        topic=topic,
        content_type=content_type,
        target_audience=audience,
        industry=industry,
    )
    stage_order.append("boss_agent")

    boss_handoff = boss.handoff_to_content_agency(directive)

    research_brief = asdict(directive)
    research_brief["research_brief_id"] = directive.directive_id
    research_brief["primary_topic"] = directive.target_focus

    raw_draft = content.process_research_brief(research_brief)
    stage_order.append("content_agency")
    content_handoff = content.handoff_to_onpage_seo_agency(raw_draft)

    raw_draft_dict = asdict(raw_draft)
    primary_keywords = research_brief.get("primary_keywords") or [topic]

    optimized = seo.process_raw_creative_draft(raw_draft_dict, primary_keywords)
    stage_order.append("onpage_seo_agency")
    seo_handoff = seo.handoff_to_overseer(optimized)

    optimized_dict = asdict(optimized)
    briefing = overseer.process_pipeline_output(research_brief, raw_draft_dict, optimized_dict)
    stage_order.append("the_overseer")
    dispatch = overseer.generate_terminal_dispatch(briefing)

    briefing_dict = asdict(briefing)

    issue_payload = approval.create_approval_issue(briefing_dict)
    stage_order.append("approval_agent")

    approval_status = scenario.get("approval_status", "approved")
    decision = approval.process_approval_decision(
        briefing_id=briefing_dict["briefing_id"],
        github_issue_number=0,
        github_issue_url="https://example.invalid/ghost",
        approval_status=approval_status,
        approved_by="ghost-runner",
        approval_method="ghost",
        approval_comment="Ghost test run",
    )

    deployment_signal = approval.generate_deployment_signal(
        decision,
        content_id=optimized_dict.get("content_id", "ghost-content"),
        content_url_slug=optimized_dict.get("url_slug", "ghost-content"),
    )
    workflow_payload = approval.create_workflow_dispatch_payload(deployment_signal)

    return {
        "stage_order": stage_order,
        "boss_handoff": boss_handoff,
        "research_brief": research_brief,
        "content_handoff": content_handoff,
        "raw_draft": raw_draft_dict,
        "seo_handoff": seo_handoff,
        "optimized_content": optimized_dict,
        "terminal_briefing": briefing_dict,
        "terminal_dispatch": dispatch,
        "approval_issue_payload": asdict(issue_payload),
        "approval_decision": asdict(decision),
        "deployment_signal": deployment_signal,
        "workflow_dispatch_payload": workflow_payload,
    }


def _validate_contracts(pipeline: Dict[str, Any], diagnostics: Dict[str, Any]) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []

    expected_stage_order = [
        "boss_agent",
        "content_agency",
        "onpage_seo_agency",
        "the_overseer",
        "approval_agent",
    ]
    _record_check(
        checks,
        "stage_order",
        pipeline.get("stage_order") == expected_stage_order,
        f"actual={pipeline.get('stage_order')}",
    )

    for path in [
        "boss_handoff.status",
        "research_brief.directive_id",
        "research_brief.primary_topic",
        "research_brief.primary_keywords",
        "content_handoff.status",
        "raw_draft.draft_id",
        "raw_draft.full_draft",
        "raw_draft.overall_word_count",
        "seo_handoff.status",
        "optimized_content.content_id",
        "optimized_content.url_slug",
        "optimized_content.meta_tags.title",
        "optimized_content.meta_tags.description",
        "optimized_content.schema_markup",
        "terminal_briefing.briefing_id",
        "terminal_briefing.pipeline_status",
        "terminal_briefing.critical_metrics",
        "approval_issue_payload.title",
        "approval_issue_payload.body",
        "approval_issue_payload.labels",
        "deployment_signal.signal_type",
    ]:
        _record_check(checks, f"required:{path}", _require_path(pipeline, path))

    _record_check(
        checks,
        "handoff:research_to_content",
        pipeline["raw_draft"].get("research_brief_id") == pipeline["research_brief"].get("research_brief_id"),
    )
    _record_check(
        checks,
        "handoff:content_to_seo",
        pipeline["optimized_content"].get("raw_draft_id") == pipeline["raw_draft"].get("draft_id"),
    )
    _record_check(
        checks,
        "handoff:seo_to_overseer",
        pipeline["terminal_briefing"].get("technical_phase", {}).get("content_id")
        == pipeline["optimized_content"].get("content_id"),
    )

    _record_check(
        checks,
        "diagnostics:mode",
        diagnostics.get("mode") == "ghost",
        f"mode={diagnostics.get('mode')}",
    )
    _record_check(
        checks,
        "diagnostics:fallback_flag_present",
        isinstance(diagnostics.get("fallback_used"), bool),
    )

    return checks


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
    args = parser.parse_args()

    controls = _ghost_controls()
    if not controls["ghost_mode"] or not controls["dry_run"] or controls["allow_side_effects"]:
        raise RuntimeError(
            "Ghost harness requires GHOST_MODE=true, DRY_RUN=true, ALLOW_SIDE_EFFECTS=false"
        )

    fixture_path = Path(args.fixtures_dir) / f"{args.scenario}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Missing scenario fixture: {fixture_path}")

    scenario = json.loads(fixture_path.read_text(encoding="utf-8"))
    output_root = Path(args.output_dir) / args.scenario
    output_root.mkdir(parents=True, exist_ok=True)
    logs_dir = output_root / "agent_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any]
    try:
        site_intel = _run_site_intel(scenario)
        pipeline = _run_pipeline(scenario)
        checks = _validate_contracts(pipeline, site_intel["diagnostics"])
        success = all(check["passed"] for check in checks)

        report = {
            "scenario": args.scenario,
            "timestamp": datetime.now().isoformat(),
            "ghost_controls": controls,
            "fallback_used": site_intel["diagnostics"]["fallback_used"],
            "contract_checks": checks,
            "success": success,
        }

        (output_root / "pipeline_result.json").write_text(
            json.dumps(pipeline, indent=2, default=str), encoding="utf-8"
        )
        (output_root / "site_intel_diagnostics.json").write_text(
            json.dumps(site_intel["diagnostics"], indent=2), encoding="utf-8"
        )
        (output_root / "ghost_run_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        (logs_dir / "stages.log").write_text(
            "\n".join(
                [
                    f"scenario={args.scenario}",
                    f"ghost_mode={controls['ghost_mode']}",
                    f"dry_run={controls['dry_run']}",
                    f"allow_side_effects={controls['allow_side_effects']}",
                    f"fallback_used={site_intel['diagnostics']['fallback_used']}",
                    f"stage_order={','.join(pipeline['stage_order'])}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        if not success:
            failed = [c for c in checks if not c["passed"]]
            raise RuntimeError(f"Contract validation failed: {failed}")

    except Exception as exc:
        report = {
            "scenario": args.scenario,
            "timestamp": datetime.now().isoformat(),
            "ghost_controls": controls,
            "success": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        (output_root / "ghost_run_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        (logs_dir / "error.log").write_text(report["traceback"], encoding="utf-8")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
