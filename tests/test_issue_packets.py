import unittest

from agents.issue_packets import embed_packet, extract_packet
from agents.approval_agent import GitHubApprovalIssueBuilder
from agents.site_intelligence_agent import PostCandidate, RefreshBrief, RefreshChecklist, SiteIntelligenceAgent


class IssuePacketTests(unittest.TestCase):
    def test_round_trip_packet_encoding(self):
        body = embed_packet("hello", "fresh_article", {"title": "Hello", "url_slug": "hello"})

        packet = extract_packet(body)

        self.assertIsNotNone(packet)
        self.assertEqual(packet["packet_type"], "fresh_article")
        self.assertEqual(packet["payload"]["url_slug"], "hello")

    def test_content_approval_issue_embeds_publish_packet(self):
        builder = GitHubApprovalIssueBuilder()
        issue = builder.build_approval_issue(
            {
                "content_title": "Fresh Article",
                "content_url": "https://kurtastarita.com/fresh-article",
                "total_quality_score": 88,
                "risk_level": "low",
                "production_ready": True,
                "critical_metrics": {
                    "quality_score": 88,
                    "seo_score": 91,
                    "risk_level": "low",
                    "word_count": 1200,
                    "reading_time": 6,
                },
                "research_phase": {"primary_topic": "Fresh Article", "primary_keywords": ["fresh"], "market_trends_count": 1, "key_statistics_count": 1},
                "creative_phase": {"title": "Fresh Article", "voice_used": "authoritative", "tone_used": "pragmatic", "engagement_score": 0.8, "creativity_score": 0.7},
                "technical_phase": {"url_slug": "fresh-article", "seo_score": 91, "heading_count": 4, "optimized_heading_count": 3, "internal_link_count": 2, "schema_markup_configured": True},
                "compliance_checks": {
                    "creative_integrity_preserved": True,
                    "keyword_density_optimal": True,
                    "meta_tags_complete": True,
                    "schema_valid": True,
                    "heading_hierarchy_valid": True,
                    "links_functional": True,
                    "no_critical_warnings": True,
                    "overall_compliance_score": 0.9,
                },
                "quality_checks": [],
                "risks_identified": [],
                "executive_summary": "Looks good",
                "dispatch_timestamp": "2026-08-10T00:00:00",
                "pipeline_status": "complete",
                "content_payload": {
                    "content_id": "SEO_1",
                    "title": "Fresh Article",
                    "url_slug": "fresh-article",
                    "optimized_content_html": "<p>Hello world</p>",
                    "meta_tags": {"keywords": ["fresh", "article"]},
                    "schema_markup": {"@type": "BlogPosting"},
                },
            }
        )

        packet = extract_packet(issue.body)

        self.assertIsNotNone(packet)
        self.assertEqual(packet["packet_type"], "fresh_article")
        self.assertEqual(packet["payload"]["operation"], "create")
        self.assertEqual(packet["payload"]["url_slug"], "fresh-article")

    def test_refresh_issue_embeds_refresh_packet(self):
        agent = SiteIntelligenceAgent()
        brief = RefreshBrief(
            brief_id="REFRESH_1",
            post_candidate=PostCandidate(
                post_id="1",
                url_slug="existing-post",
                title="Existing Post",
                published_date="2024-01-01",
                current_position=8,
                impressions=4000,
                clicks=50,
                ctr=1.25,
                days_old=200,
            ),
            checklist=RefreshChecklist(post_id="1", url_slug="existing-post"),
            created_timestamp="2026-08-10T00:00:00",
        )

        issue = agent.create_github_issue_payload(
            brief,
            refreshed_post={
                "title": "Existing Post",
                "url_slug": "existing-post",
                "html": "<p>Updated</p>",
                "labels": ["refresh"],
                "summary": "Updated",
                "citations": [],
                "internal_links": [],
                "change_log": ["Added updates"],
            },
        )

        packet = extract_packet(issue["body"])

        self.assertIsNotNone(packet)
        self.assertEqual(packet["packet_type"], "refresh_article")
        self.assertEqual(packet["payload"]["operation"], "refresh")
        self.assertEqual(packet["payload"]["url_slug"], "existing-post")


if __name__ == "__main__":
    unittest.main()
