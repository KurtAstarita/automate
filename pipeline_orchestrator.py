"""
Pipeline Orchestrator - Chains the 5 production agents for new content creation.

Agents (in order):
  Stage 1 - Boss Agent          -> ContentDirectiveBrief
  Stage 2 - Content Agency      -> RawCreativeDraft
  Stage 3 - On-Page SEO Agency  -> SEOOptimizedContent
  Stage 4 - The Overseer        -> TerminalBriefing
  Stage 5 - Approval Agent      -> ApprovalIssuePayload (GitHub issue)

CLI Usage:
  python pipeline_orchestrator.py --topic "AI automation" --content-type blog_post \
      --audience developers --industry SaaS

Environment Variables (optional, consumed by agents):
  GITHUB_TOKEN       - Required to create the approval issue via GitHub API.
  GITHUB_REPOSITORY  - Override target repo (default: KurtAstarita/automate).
  BASE_URL           - Override publication base URL (default: https://kurtastarita.com).
"""

import argparse
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime

from agents.boss_agent import BossAgent, ContentType, TargetAudience
from agents.content_agency import ContentAgency, VoiceStyle, ToneStyle
from agents.onpage_seo_agency import OnPageSEOAgency
from agents.the_overseer import TheOverseer
from agents.approval_agent import ApprovalAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pipeline_orchestrator")


def run_pipeline(
    topic: str,
    content_type: str = "blog_post",
    audience: str = "general_tech",
    industry: str = "General",
    base_url: str = "https://kurtastarita.com",
    repository: str = "KurtAstarita/automate",
    dry_run: bool = False,
) -> dict:
    """
    Execute the full content pipeline end-to-end.

    Args:
        topic:        Primary topic / brief for the content.
        content_type: ContentType enum value (e.g. "blog_post").
        audience:     TargetAudience enum value (e.g. "developers").
        industry:     Industry vertical string.
        base_url:     Publication base URL.
        repository:   GitHub repository for approval issue.
        dry_run:      If True, skip the GitHub issue creation step.

    Returns:
        Dictionary with keys:
          - directive_id, draft_id, seo_content_id, briefing_id,
            approval_issue (or None), pipeline_status, completed_at
    """
    result = {
        "pipeline_status": "RUNNING",
        "topic": topic,
        "started_at": datetime.now().isoformat(),
    }

    # ------------------------------------------------------------------
    # Stage 1 – Boss Agent: Research & Briefing
    # ------------------------------------------------------------------
    logger.info("=== STAGE 1: Boss Agent – Research & Briefing ===")
    try:
        ct = ContentType(content_type)
    except ValueError:
        logger.warning("Unknown content_type '%s'; defaulting to blog_post", content_type)
        ct = ContentType.BLOG_POST

    try:
        ta = TargetAudience(audience)
    except ValueError:
        logger.warning("Unknown audience '%s'; defaulting to general_tech", audience)
        ta = TargetAudience.GENERAL_TECH

    boss = BossAgent()
    directive = boss.generate_content_directive(
        topic=topic,
        content_type=ct,
        target_audience=ta,
        industry=industry,
    )
    handoff = boss.handoff_to_content_agency(directive)
    research_brief = handoff["directive"]
    result["directive_id"] = directive.directive_id
    logger.info("Stage 1 complete: %s", directive.directive_id)

    # ------------------------------------------------------------------
    # Stage 2 – Content Agency: Creative Writing
    # ------------------------------------------------------------------
    logger.info("=== STAGE 2: Content Agency – Creative Writing ===")
    agency = ContentAgency()
    raw_draft_obj = agency.process_research_brief(
        research_brief=research_brief,
        voice=VoiceStyle.AUTHORITATIVE,
        tone=ToneStyle.EDUCATIONAL,
    )
    raw_draft = asdict(raw_draft_obj)
    result["draft_id"] = raw_draft.get("draft_id")
    logger.info("Stage 2 complete: %s", raw_draft.get("draft_id"))

    # ------------------------------------------------------------------
    # Stage 3 – On-Page SEO Agency: Technical Optimisation
    # ------------------------------------------------------------------
    logger.info("=== STAGE 3: On-Page SEO Agency – SEO Optimisation ===")
    seo_agency = OnPageSEOAgency()
    primary_keywords = research_brief.get("primary_keywords", [topic])
    seo_content_obj = seo_agency.process_raw_creative_draft(
        raw_draft=raw_draft,
        primary_keywords=primary_keywords,
        base_url=base_url,
    )
    seo_content = asdict(seo_content_obj)
    result["seo_content_id"] = seo_content.get("content_id")
    logger.info("Stage 3 complete: %s", seo_content.get("content_id"))

    # ------------------------------------------------------------------
    # Stage 4 – The Overseer: QA & Terminal Briefing
    # ------------------------------------------------------------------
    logger.info("=== STAGE 4: The Overseer – QA & Terminal Briefing ===")
    overseer = TheOverseer()
    briefing_obj = overseer.process_pipeline_output(
        research_brief=research_brief,
        raw_creative_draft=raw_draft,
        seo_optimized_content=seo_content,
        base_url=base_url,
    )
    overseer.generate_terminal_dispatch(briefing_obj)
    terminal_briefing = asdict(briefing_obj)
    result["briefing_id"] = briefing_obj.briefing_id
    logger.info("Stage 4 complete: %s", briefing_obj.briefing_id)

    # ------------------------------------------------------------------
    # Stage 5 – Approval Agent: GitHub Issue Creation
    # ------------------------------------------------------------------
    logger.info("=== STAGE 5: Approval Agent – GitHub Issue ===")
    approval_issue = None
    if not dry_run:
        approval_agent = ApprovalAgent()
        issue_payload_obj = approval_agent.create_approval_issue(
            terminal_briefing=terminal_briefing,
            repository=repository,
        )
        approval_issue = asdict(issue_payload_obj)
        result["approval_issue"] = approval_issue
        logger.info("Stage 5 complete: approval issue payload built")
    else:
        logger.info("Stage 5 skipped (dry_run=True)")
        result["approval_issue"] = None

    result["pipeline_status"] = "COMPLETE"
    result["completed_at"] = datetime.now().isoformat()
    logger.info("Pipeline complete for topic: %s", topic)
    return result


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full 5-stage content production pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Primary topic or brief for the new content piece.",
    )
    parser.add_argument(
        "--content-type",
        default="blog_post",
        choices=[ct.value for ct in ContentType],
        help="Type of content to produce (default: blog_post).",
    )
    parser.add_argument(
        "--audience",
        default="general_tech",
        choices=[ta.value for ta in TargetAudience],
        help="Target audience segment (default: general_tech).",
    )
    parser.add_argument(
        "--industry",
        default="General",
        help="Industry vertical (default: General).",
    )
    parser.add_argument(
        "--base-url",
        default="https://kurtastarita.com",
        help="Publication base URL.",
    )
    parser.add_argument(
        "--repository",
        default="KurtAstarita/automate",
        help="GitHub repository for approval issue (owner/repo).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip GitHub issue creation (Stage 5).",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Path to write JSON result, or '-' for stdout (default).",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        result = run_pipeline(
            topic=args.topic,
            content_type=args.content_type,
            audience=args.audience,
            industry=args.industry,
            base_url=args.base_url,
            repository=args.repository,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        error_output = {
            "pipeline_status": "FAILED",
            "error": str(exc),
            "topic": args.topic,
            "failed_at": datetime.now().isoformat(),
        }
        output_json = json.dumps(error_output, indent=2)
        if args.output == "-":
            print(output_json)
        else:
            with open(args.output, "w") as fh:
                fh.write(output_json)
        sys.exit(1)

    output_json = json.dumps(result, indent=2, default=str)
    if args.output == "-":
        print(output_json)
    else:
        with open(args.output, "w") as fh:
            fh.write(output_json)
        logger.info("Result written to %s", args.output)


if __name__ == "__main__":
    main()
