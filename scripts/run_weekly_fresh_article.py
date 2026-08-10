import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict

sys.path.insert(0, ".")

from agents.boss_agent import BossAgent, ContentType, TargetAudience
from agents.content_agency import ContentAgency
from agents.onpage_seo_agency import OnPageSEOAgency
from agents.the_overseer import TheOverseer
from agents.approval_agent import ApprovalAgent
from agents.content_refresh_agent import ContentRefreshAgent


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("weekly_fresh_article")


def _seed_topics() -> list[str]:
    raw = os.environ.get("EDITORIAL_SEED_TOPICS", "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def main() -> int:
    boss = BossAgent()
    content = ContentAgency()
    seo = OnPageSEOAgency()
    overseer = TheOverseer()
    approval = ApprovalAgent()
    refresh_agent = ContentRefreshAgent()  # Reuse sitemap/link target helpers for fresh content

    industry = os.environ.get("EDITORIAL_INDUSTRY", "General").strip() or "General"
    topic_pick = boss.discover_weekly_topic(seed_topics=_seed_topics(), industry=industry)
    topic = topic_pick["headline"]
    LOG.info("Selected weekly topic: %s", topic)

    directive = boss.generate_content_directive(
        topic=topic,
        content_type=ContentType.BLOG_POST,
        target_audience=TargetAudience.PRODUCT_MANAGERS,
        industry=industry,
        custom_context={"weekly_topic_pick": topic_pick},
    )
    research_brief = asdict(directive)
    research_brief["research_brief_id"] = directive.directive_id
    research_brief["primary_topic"] = directive.target_focus

    raw_draft = content.process_research_brief(research_brief)
    index_entries = refresh_agent.build_sitemap_index(
        sitemap_source=os.environ.get("SITEMAP_URL", "https://kurtastarita.com/sitemap.xml")
    )
    related = refresh_agent.get_internal_link_targets(raw_draft.full_draft, index_entries=index_entries)
    optimized = seo.process_raw_creative_draft(asdict(raw_draft), directive.primary_keywords, related_content_urls=related)
    briefing = overseer.process_pipeline_output(research_brief, asdict(raw_draft), asdict(optimized))
    issue_payload = asdict(approval.create_approval_issue(asdict(briefing)))

    result = {
        "topic_pick": topic_pick,
        "directive_id": directive.directive_id,
        "briefing_id": briefing.briefing_id,
        "issue_payload": issue_payload,
    }
    output_path = "fresh_article_result.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, suffix=".json", dir="."
    ) as tmp:
        json.dump(result, tmp, indent=2)
        tmp_name = tmp.name
    os.replace(tmp_name, output_path)
    LOG.info("Fresh article package prepared: %s", briefing.briefing_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
