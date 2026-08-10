"""
Site Intelligence Agent - Lightweight Post Refresh Optimizer
Monitors kurtastarita.com for optimization opportunities.
Selects 1 post per week for refresh.
Minimal token usage. Simple approval flow.

Flow: Intelligence Scan → Candidate Selection → Simple Checklist → Overseer → GitHub Issue for Kurt

GA4 integration (v1):
  When GA4_PROPERTY_ID is configured the agent pulls page-level GA4 metrics
  and blends them with the GSC score.  If GA4 is unavailable the workflow
  falls back to GSC-only scoring without failing.

Scoring weights (tune near top of file):
  GSC_WEIGHT  – fraction of final score from GSC signals (default 0.7)
  GA4_WEIGHT  – fraction of final score from GA4 signals (default 0.3)
  When GA4 data is missing for a candidate the full weight reverts to GSC.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from agents.issue_packets import embed_packet

# ---------------------------------------------------------------------------
# Scoring weights – easy to tune
# ---------------------------------------------------------------------------
GSC_WEIGHT: float = 0.7
GA4_WEIGHT: float = 0.3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostRefreshStatus(Enum):
    """Status of post refresh candidate."""
    CANDIDATE = "candidate"
    SELECTED = "selected"
    READY_FOR_APPROVAL = "ready_for_approval"
    APPROVED = "approved"


@dataclass
class PostCandidate:
    """A blog post candidate for refresh."""
    post_id: str
    url_slug: str
    title: str
    published_date: str
    current_position: Optional[int] = None  # Google rank position (1-100)
    impressions: Optional[int] = 0
    clicks: Optional[int] = 0
    ctr: Optional[float] = 0.0  # Click-through rate %
    last_updated: Optional[str] = None
    days_old: int = 0
    reason_for_refresh: str = ""
    potential_ctr_boost: str = ""  # e.g. "15-25%"
    # GA4 metrics (populated when GA4 is available)
    ga4_sessions: Optional[int] = None
    ga4_engagement_rate: Optional[float] = None
    ga4_conversions: Optional[float] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


@dataclass
class RefreshChecklist:
    """Simple approval checklist for post refresh."""
    post_id: str
    url_slug: str
    checks: Optional[Dict[str, bool]] = None
    
    def __post_init__(self):
        if self.checks is None:
            self.checks = {
                "meta_title_updated": False,
                "meta_description_updated": False,
                "outdated_stats_removed": False,
                "publish_date_updated": False,
                "internal_links_added": False,
                "content_accuracy_verified": False
            }
    
    def all_passed(self) -> bool:
        """Check if all items passed."""
        return all(self.checks.values())
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


@dataclass
class RefreshBrief:
    """Brief for The Overseer review."""
    brief_id: str
    post_candidate: PostCandidate
    checklist: RefreshChecklist
    created_timestamp: str
    
    def to_json(self) -> str:
        return json.dumps({
            "brief_id": self.brief_id,
            "post_candidate": asdict(self.post_candidate),
            "checklist": asdict(self.checklist),
            "created_timestamp": self.created_timestamp
        }, indent=2)


class SiteIntelligenceAgent:
    """
    Lightweight site monitoring.
    Finds 1 best candidate per week.
    Minimal complexity, minimal tokens.
    """
    
    def __init__(self):
        self.name = "Site Intelligence Agent"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def select_weekly_candidate(
        self,
        gsc_data: List[Dict[str, Any]],
        ga4_metrics: Optional[Dict[str, Dict]] = None,
    ) -> PostCandidate:
        """
        Select ONE post for refresh this week.
        
        Priority order:
        1. Posts in positions 5-12 (CTR improvable)
        2. High impressions (2000+) but low CTR (<2%)
        3. 6+ months old
        
        When *ga4_metrics* is provided (slug → {sessions, engagement_rate,
        conversions}) the GSC score is blended with a normalised GA4 urgency
        signal: pages with high reach (sessions) and low engagement rate score
        higher (more urgent to refresh).  Both signals are normalised to [0,1]
        before blending so neither dominates due to scale differences.
        
        Args:
            gsc_data:    List of posts with GSC metrics
                         Expected keys: url_slug, title, published_date,
                         position, impressions, clicks
            ga4_metrics: Optional GA4 page metrics keyed by url_slug.
        
        Returns:
            PostCandidate - the selected post for this week
        """
        self.logger.info("Selecting 1 post candidate for weekly refresh...")
        
        candidates = []
        
        for post in gsc_data:
            position = post.get("position", 100)
            impressions = post.get("impressions", 0)
            clicks = post.get("clicks", 0)
            published_date = post.get("published_date", "")
            
            # Calculate metrics
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            days_old = self._days_since(published_date)
            
            # Score: Only consider positions 5-12 with decent impressions
            if 5 <= position <= 12 and impressions >= 2000 and ctr < 2.0:
                gsc_score = (2000 - ctr * 100) + (impressions / 100)

                slug = post.get("url_slug", "unknown")
                ga4_row = (ga4_metrics or {}).get(slug)
                blended_score = self._blend_score(gsc_score, ga4_row)
                
                potential_boost = self._estimate_ctr_boost(position, ctr)
                
                candidate = PostCandidate(
                    post_id=post.get("post_id", f"post_{position}"),
                    url_slug=slug,
                    title=post.get("title", "Untitled"),
                    published_date=published_date,
                    current_position=position,
                    impressions=impressions,
                    clicks=clicks,
                    ctr=round(ctr, 2),
                    last_updated=post.get("last_updated"),
                    days_old=days_old,
                    reason_for_refresh=f"Position {position}, {impressions} impressions, {ctr}% CTR",
                    potential_ctr_boost=potential_boost,
                    ga4_sessions=ga4_row.get("sessions") if ga4_row else None,
                    ga4_engagement_rate=ga4_row.get("engagement_rate") if ga4_row else None,
                    ga4_conversions=ga4_row.get("conversions") if ga4_row else None,
                )
                candidates.append((blended_score, candidate))
        
        if not candidates:
            self.logger.warning(
                "No candidates matched criteria (position 5-12, impressions>=2000, CTR<2%%). "
                "GSC data had %d row(s). Skipping refresh this cycle.",
                len(gsc_data),
            )
            raise ValueError(
                "No refresh candidates found. "
                "No posts currently match position 5-12 with >=2000 impressions and CTR<2%."
            )
        
        # Sort by score (descending) and pick top 1
        candidates.sort(key=lambda x: x[0], reverse=True)
        selected = candidates[0][1]
        
        self.logger.info(f"✓ Selected: {selected.title} ({selected.url_slug})")
        return selected

    # Reference maximum for GSC score normalisation (impressions cap used as denominator).
    # Typical upper bound: 2000 base + (50 000 impressions / 100) = 2500.  Adjust if needed.
    _GSC_SCORE_MAX: float = 2500.0

    def _blend_score(
        self,
        gsc_score: float,
        ga4_row: Optional[Dict],
    ) -> float:
        """
        Blend GSC score with a normalised GA4 urgency signal.

        Both signals are normalised to [0, 1] before blending so they are
        comparable regardless of their raw magnitudes.

        GSC signal (normalised): higher raw score → page is a better refresh
        candidate (low CTR, many impressions at borderline position).

        GA4 urgency signal: pages with more sessions AND lower engagement rate
        are higher priority (lots of visitors experiencing poor engagement).
        Signal = sessions_norm * (1 - engagement_rate), capped to [0, 1].
          sessions_norm = min(sessions / GA4_SESSIONS_CAP, 1.0)

        When ga4_row is None the full weight is given to the GSC signal.
        """
        # Normalise GSC score to [0, 1]
        gsc_norm = min(gsc_score / max(self._GSC_SCORE_MAX, 1.0), 1.0)

        if ga4_row is None:
            return gsc_norm

        sessions = ga4_row.get("sessions", 0) or 0
        engagement_rate = min(ga4_row.get("engagement_rate", 0.0) or 0.0, 1.0)

        # Normalise sessions to [0, 1] using a soft cap of 5 000 sessions/period
        GA4_SESSIONS_CAP = 5000.0
        sessions_norm = min(sessions / GA4_SESSIONS_CAP, 1.0)

        # Pages with high reach (sessions) and low engagement are most urgent
        ga4_urgency = sessions_norm * (1.0 - engagement_rate)

        return GSC_WEIGHT * gsc_norm + GA4_WEIGHT * ga4_urgency
    
    def _days_since(self, date_str: str) -> int:
        """Calculate days since published."""
        try:
            pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            days = (datetime.now(pub_date.tzinfo) - pub_date).days
            return max(0, days)
        except (AttributeError, TypeError, ValueError):
            return 0
    
    def _estimate_ctr_boost(self, position: int, current_ctr: float) -> str:
        """Estimate potential CTR improvement with meta optimization."""
        # Simple heuristic: lower position + lower CTR = higher boost potential
        if position <= 5:
            return "5-10%"
        elif position <= 8:
            return "15-25%"
        else:
            return "10-20%"
    
    def create_refresh_checklist(
        self,
        post_candidate: PostCandidate
    ) -> RefreshChecklist:
        """
        Create simple approval checklist for post refresh.
        
        Args:
            post_candidate: The selected post
            
        Returns:
            RefreshChecklist with 6 simple items
        """
        self.logger.info(f"Creating refresh checklist for: {post_candidate.url_slug}")
        
        checklist = RefreshChecklist(
            post_id=post_candidate.post_id,
            url_slug=post_candidate.url_slug
        )
        
        self.logger.info(f"✓ Checklist created with 6 items")
        return checklist
    
    def create_overseer_brief(
        self,
        post_candidate: PostCandidate,
        checklist: RefreshChecklist
    ) -> RefreshBrief:
        """
        Create brief for The Overseer.
        
        Args:
            post_candidate: Selected post
            checklist: Refresh checklist
            
        Returns:
            RefreshBrief
        """
        self.logger.info(f"Creating Overseer brief...")
        
        brief = RefreshBrief(
            brief_id=f"REFRESH_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            post_candidate=post_candidate,
            checklist=checklist,
            created_timestamp=datetime.now().isoformat()
        )
        
        self.logger.info(f"✓ Overseer brief created: {brief.brief_id}")
        return brief
    
    def create_github_issue_payload(
        self,
        refresh_brief: RefreshBrief,
        refreshed_post: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create GitHub issue payload for Kurt's approval.
        
        Simple format: current metrics → requested changes → checklist
        
        Args:
            refresh_brief: Brief from Overseer
            
        Returns:
            GitHub issue payload
        """
        self.logger.info("Building GitHub issue payload...")
        
        post = refresh_brief.post_candidate
        checklist = refresh_brief.checklist
        
        title = f"[POST REFRESH] {post.title} (Pos. {post.current_position}, {post.ctr}% CTR)"
        
        body = f"""# Post Refresh Approval

## 📊 Current Metrics
- **URL:** `/{post.url_slug}`
- **Title:** {post.title}
- **Published:** {post.published_date} ({post.days_old} days ago)
- **Google Position:** {post.current_position}
- **Impressions:** {post.impressions:,}
- **Clicks:** {post.clicks}
- **Current CTR:** {post.ctr}%

## 🚀 Refresh Opportunity
**Reason:** {post.reason_for_refresh}
**Potential CTR Boost:** {post.potential_ctr_boost}

---

## ✅ Pre-Refresh Checklist

All items below must be completed before publication:

- [ ] **Meta Title Updated** - Improve keyword positioning & CTR appeal
- [ ] **Meta Description Updated** - Compelling call-to-action
- [ ] **Outdated Stats Removed** - Replace with current data/citations
- [ ] **Publish Date Updated** - Set to today (signals freshness)
- [ ] **Internal Links Added** - Link to 2-3 related posts
- [ ] **Content Accuracy Verified** - All claims fact-checked

---

## 🎯 Action Required

**Review the changes above, then:**

- `/approve` - Publish the refresh immediately
- `/reject` - Skip this post for now
- `/revise <notes>` - Request changes before approval

---

**Brief ID:** `{refresh_brief.brief_id}`
**Created:** {refresh_brief.created_timestamp}

*Auto-generated by Site Intelligence Agent*
"""
        
        if refreshed_post:
            body = embed_packet(
                body,
                "refresh_article",
                {
                    "operation": "refresh",
                    "brief_id": refresh_brief.brief_id,
                    "title": refreshed_post.get("title"),
                    "url_slug": refreshed_post.get("url_slug"),
                    "html": refreshed_post.get("html"),
                    "labels": refreshed_post.get("labels", []),
                    "summary": refreshed_post.get("summary"),
                    "citations": refreshed_post.get("citations", []),
                    "internal_links": refreshed_post.get("internal_links", []),
                    "change_log": refreshed_post.get("change_log", []),
                },
            )

        payload = {
            "title": title,
            "body": body,
            "labels": ["post-refresh", "automated"],
            "assignee": "KurtAstarita"
        }
        
        self.logger.info(f"✓ GitHub issue payload created")
        return payload


class OverseerRefreshValidator:
    """
    Lightweight Overseer for refresh briefs.
    Just validates the checklist is complete.
    No complex scoring.
    """
    
    def __init__(self):
        self.name = "Overseer (Refresh Validator)"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def validate_refresh_brief(
        self,
        refresh_brief: RefreshBrief
    ) -> Dict[str, Any]:
        """
        Simple validation: is checklist complete?
        
        Args:
            refresh_brief: Brief to validate
            
        Returns:
            Validation result
        """
        self.logger.info(f"Validating refresh brief: {refresh_brief.brief_id}")
        
        checklist = refresh_brief.checklist
        all_passed = checklist.all_passed()
        
        result = {
            "brief_id": refresh_brief.brief_id,
            "validation_status": "approved" if all_passed else "pending_checklist",
            "checklist_items": checklist.checks,
            "all_passed": all_passed,
            "message": "Ready for publication" if all_passed else "Complete checklist items before approval"
        }
        
        self.logger.info(f"✓ Validation complete: {result['validation_status']}")
        return result


# Example usage
if __name__ == "__main__":
    _demo_logger = logging.getLogger("demo")
    _demo_logger.info("=" * 80)
    _demo_logger.info("SITE INTELLIGENCE AGENT - Weekly Post Refresh")
    _demo_logger.info("=" * 80)

    # Initialize
    site_agent = SiteIntelligenceAgent()
    overseer = OverseerRefreshValidator()

    # Mock GSC data
    mock_gsc_data = [
        {
            "post_id": "post_001",
            "url_slug": "python-automation-guide",
            "title": "Python Automation Guide for Beginners",
            "published_date": "2024-01-15T00:00:00Z",
            "position": 8,
            "impressions": 5200,
            "clicks": 78,
            "last_updated": "2024-02-01T00:00:00Z"
        },
        {
            "post_id": "post_002",
            "url_slug": "seo-checklist-2024",
            "title": "SEO Checklist 2024",
            "published_date": "2024-02-01T00:00:00Z",
            "position": 6,
            "impressions": 8100,
            "clicks": 81,
            "last_updated": "2024-03-01T00:00:00Z"
        },
        {
            "post_id": "post_003",
            "url_slug": "content-marketing-trends",
            "title": "Content Marketing Trends 2024",
            "published_date": "2023-12-10T00:00:00Z",
            "position": 11,
            "impressions": 6300,
            "clicks": 63,
            "last_updated": None
        }
    ]

    # Step 1: Select candidate
    _demo_logger.info("[STEP 1] Selecting Weekly Candidate...")
    candidate = site_agent.select_weekly_candidate(mock_gsc_data)
    _demo_logger.info(
        "Selected: %s | Position: %s | Impressions: %d | CTR: %s%%",
        candidate.title, candidate.current_position,
        candidate.impressions or 0, candidate.ctr,
    )
    _demo_logger.info("Potential Boost: %s", candidate.potential_ctr_boost)

    # Step 2: Create checklist
    _demo_logger.info("[STEP 2] Creating Refresh Checklist...")
    checklist = site_agent.create_refresh_checklist(candidate)
    _demo_logger.info("Checklist created with %d items", len(checklist.checks))
    for item in checklist.checks:
        _demo_logger.info("  [ ] %s", item.replace("_", " ").title())

    # Step 3: Create Overseer brief
    _demo_logger.info("[STEP 3] Creating Overseer Brief...")
    brief = site_agent.create_overseer_brief(candidate, checklist)
    _demo_logger.info("Brief created: %s", brief.brief_id)

    # Step 4: Validate with Overseer
    _demo_logger.info("[STEP 4] Overseer Validation...")
    validation = overseer.validate_refresh_brief(brief)
    _demo_logger.info("Status: %s | Message: %s", validation["validation_status"], validation["message"])

    # Step 5: Create GitHub issue
    _demo_logger.info("[STEP 5] Creating GitHub Issue for Kurt...")
    issue_payload = site_agent.create_github_issue_payload(brief)
    _demo_logger.info("GitHub Issue Ready — Title: %s", issue_payload["title"])
    _demo_logger.info("Labels: %s", ", ".join(issue_payload["labels"]))

    _demo_logger.info("=" * 80)
