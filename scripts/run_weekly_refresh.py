import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict

sys.path.insert(0, ".")

from agents.boss_agent import BossAgent
from agents.content_refresh_agent import ContentRefreshAgent
from agents.content_refresh_writer import ContentRefreshWriter
from agents.site_intelligence_agent import SiteIntelligenceAgent
from scripts.ga4_fetcher import fetch_ga4_metrics


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("weekly_refresh")


def _load_gsc_data() -> list[dict]:
    # Priority 1: freshly fetched file from gsc_fetcher.py
    if os.path.exists("gsc_data.json"):
        try:
            with open("gsc_data.json", encoding="utf-8") as f:
                data = json.load(f)
            if data:
                LOG.info("Loaded %d GSC rows from gsc_data.json", len(data))
                return data
        except Exception as exc:
            LOG.warning("Failed to read gsc_data.json: %s", exc)

    # Priority 2: GSC_DATA_JSON env var (secret or workflow input)
    raw = os.environ.get("GSC_DATA_JSON", "").strip()
    if raw:
        LOG.info("Using GSC_DATA_JSON from environment")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            LOG.warning("Invalid JSON in GSC_DATA_JSON: %s", exc)

    # Priority 3: built-in sample data (last resort)
    LOG.warning("No GSC data available — using built-in sample data")
    return [
        {
            "url_slug": "sample-post",
            "title": "Sample Post for Refresh",
            "published_date": "2024-01-01",
            "position": 8,
            "impressions": 3000,
            "clicks": 45,
        }
    ]


def main() -> int:
    gsc_data = _load_gsc_data()
    candidate_slugs = [p.get("url_slug", "") for p in gsc_data if p.get("url_slug")]
    ga4_metrics, ga4_error = fetch_ga4_metrics(candidate_slugs)

    site_agent = SiteIntelligenceAgent()
    refresh_agent = ContentRefreshAgent()
    writer = ContentRefreshWriter()
    boss = BossAgent()

    candidate = site_agent.select_weekly_candidate(gsc_data, ga4_metrics if not ga4_error else None)
    checklist = site_agent.create_refresh_checklist(candidate)
    brief = site_agent.create_overseer_brief(candidate, checklist)

    insights = boss.research_market_trends(candidate.title, "content refresh", num_results=3)
    index_entries = refresh_agent.build_sitemap_index(
        sitemap_source=os.environ.get("SITEMAP_URL", "https://kurtastarita.com/sitemap.xml")
    )
    link_targets = refresh_agent.get_internal_link_targets(candidate.title, index_entries=index_entries)
    refresh_package = writer.build_refresh_package(
        post_candidate=asdict(candidate),
        market_insights=[asdict(item) for item in insights],
        internal_link_targets=link_targets,
    )
    issue_payload = site_agent.create_github_issue_payload(brief, refreshed_post=asdict(refresh_package))

    result = {
        "brief_id": brief.brief_id,
        "candidate_slug": candidate.url_slug,
        "issue_payload": issue_payload,
        "created_at": brief.created_timestamp,
        "refresh_package": asdict(refresh_package),
        "diagnostics": {
            "mode": "gsc_ga4" if not ga4_error else "gsc_only_fallback",
            "ga4_error": ga4_error,
            "ga4_slugs_matched": len(ga4_metrics) if ga4_metrics else 0,
        },
    }

    output_path = "refresh_result.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, suffix=".json", dir="."
    ) as tmp:
        json.dump(result, tmp, indent=2)
        tmp_name = tmp.name
    os.replace(tmp_name, output_path)
    LOG.info("Refresh package prepared: %s", brief.brief_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
