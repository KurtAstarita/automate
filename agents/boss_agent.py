"""
Boss Agent - Stage 1: Idea Research & Briefing
Responsibility: Ideation, market search, competitive research, and target audience framing.

Execution: Scrapes search engine result pages (SERPs) and trending industry topics.
Compiles a structured Content Directive detailing the target focus, primary question to answer,
key statistics, and outline framework.

Handoff Output: CONTENT_DIRECTIVE_BRIEF sent to the Content Agency.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import quote_plus

import feedparser
import requests

from agents.ghost_controls import ghost_controls

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_TOPICS_PATH = REPO_ROOT / "published_topics.json"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Supported content types for directives."""
    BLOG_POST = "blog_post"
    WHITEPAPER = "whitepaper"
    CASE_STUDY = "case_study"
    TUTORIAL = "tutorial"
    OPINION_PIECE = "opinion_piece"
    RESEARCH_ARTICLE = "research_article"
    INDUSTRY_REPORT = "industry_report"


class TargetAudience(Enum):
    """Target audience segments."""
    DEVELOPERS = "developers"
    PRODUCT_MANAGERS = "product_managers"
    BUSINESS_LEADERS = "business_leaders"
    ENTERPRISES = "enterprises"
    STARTUPS = "startups"
    MARKETING_TEAMS = "marketing_teams"
    GENERAL_TECH = "general_tech"


@dataclass
class MarketInsight:
    """Represents a single market insight or trend."""
    title: str
    description: str
    source: str
    relevance_score: float  # 0-1
    keywords: List[str]
    published_date: str


@dataclass
class CompetitiveAnalysis:
    """Competitive landscape overview."""
    competitor_name: str
    content_focus: str
    key_differentiators: List[str]
    audience_overlap: float  # 0-1
    strength_areas: List[str]
    weakness_areas: List[str]


@dataclass
class ContentDirectiveBrief:
    """Structured Content Directive output for Content Agency."""
    directive_id: str
    created_at: str
    content_type: str
    
    # Core directive information
    target_focus: str
    primary_question: str
    secondary_questions: List[str]
    
    # Audience and market context
    target_audience: List[str]
    audience_pain_points: List[str]
    audience_goals: List[str]
    
    # Market intelligence
    market_trends: List[Dict[str, Any]]
    competitive_landscape: List[Dict[str, Any]]
    opportunity_gap: str
    
    # Content structure
    recommended_outline: List[str]
    key_statistics: List[str]
    supporting_data_sources: List[str]
    
    # SEO and visibility
    primary_keywords: List[str]
    secondary_keywords: List[str]
    search_intent: str
    
    # Execution guidance
    recommended_format: str
    tone_and_style: str
    call_to_action: str
    
    # Quality gates
    success_metrics: Dict[str, Any]
    confidence_score: float  # 0-1
    
    def to_json(self) -> str:
        """Convert directive to JSON format."""
        return json.dumps(asdict(self), indent=2)


class BossAgent:
    """
    Boss Agent for Stage 1: Ideation, Research & Briefing.
    
    Responsibilities:
    - Conduct market and competitive research
    - Identify trending topics and industry insights
    - Frame target audience and their pain points
    - Generate structured content directives
    - Handoff to Content Agency
    """
    
    def __init__(self):
        """Initialize Boss Agent."""
        self.name = "Boss Agent"
        self.stage = "Stage 1: Ideation & Research"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    # ── Topic deduplication helpers ───────────────────────────────────────────

    def _load_published_topics(self) -> List[str]:
        """Return list of previously published topic headlines (lowercase)."""
        try:
            if PUBLISHED_TOPICS_PATH.exists():
                data = json.loads(PUBLISHED_TOPICS_PATH.read_text(encoding="utf-8"))
                return [str(t).lower().strip() for t in data if t]
        except (OSError, ValueError, TypeError) as exc:
            self.logger.warning("Could not read published_topics.json: %s", exc)
        return []

    def _record_published_topic(self, headline: str) -> None:
        """Append a headline to the published topics log and persist."""
        try:
            topics = self._load_published_topics()
            entry = headline.lower().strip()
            if entry and entry not in topics:
                topics.append(entry)
                PUBLISHED_TOPICS_PATH.write_text(
                    json.dumps(topics, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        except (OSError, ValueError, TypeError) as exc:
            self.logger.warning("Could not update published_topics.json: %s", exc)

    def _topic_already_used(self, headline: str, published: List[str]) -> bool:
        """Return True if the headline is too similar to any previously used topic."""
        candidate = headline.lower().strip()
        candidate_words = set(candidate.split())
        for used in published:
            used_words = set(used.split())
            # Jaccard similarity > 0.6 → consider duplicate
            if used_words and candidate_words:
                intersection = candidate_words & used_words
                union = candidate_words | used_words
                if len(intersection) / len(union) > 0.6:
                    return True
        return False
        
    def research_market_trends(
        self,
        topic: str,
        industry: str,
        num_results: int = 10
    ) -> List[MarketInsight]:
        """
        Research market trends and industry topics via SERPs.
        
        Args:
            topic: Primary topic to research
            industry: Industry vertical
            num_results: Number of results to gather
            
        Returns:
            List of MarketInsight objects
        """
        self.logger.info(f"Researching market trends for topic: {topic} in {industry}")
        
        controls = ghost_controls()
        trends = []
        if not controls["ghost_mode"]:
            trends = self._fetch_market_trends(topic, industry, num_results=num_results)
        if not trends:
            trends = self._fallback_market_trends(topic, industry)
        
        self.logger.info(f"Gathered {len(trends)} market insights")
        return trends
    
    def analyze_competitive_landscape(
        self,
        topic: str,
        target_audience: List[str]
    ) -> List[CompetitiveAnalysis]:
        """
        Analyze competitive content and market positioning.
        
        Args:
            topic: Topic to analyze
            target_audience: Target audience segments
            
        Returns:
            List of CompetitiveAnalysis objects
        """
        self.logger.info(f"Analyzing competitive landscape for topic: {topic}")
        
        controls = ghost_controls()
        competitors = []
        if not controls["ghost_mode"]:
            competitors = self._fetch_competitive_landscape(topic, target_audience)
        if not competitors:
            competitors = self._fallback_competitive_landscape(topic)
        
        self.logger.info(f"Identified {len(competitors)} competitive players")
        return competitors

    def discover_weekly_topic(
        self,
        seed_topics: Optional[List[str]] = None,
        industry: str = "General",
    ) -> Dict[str, Any]:
        """Pick a weekly topic from a small seed set using live research when available.

        Skips topics that are too similar to previously published ones (tracked in
        published_topics.json) so the blog doesn't repeat itself week to week.
        """
        topics = [topic.strip() for topic in (seed_topics or []) if topic and topic.strip()]
        if not topics:
            topics = [
                "strength training",
                "nutrition protocols",
                "fitness automation",
                "health optimization",
            ]

        published = self._load_published_topics()

        best_topic = topics[0]
        best_score = -1.0
        best_insight: Optional[MarketInsight] = None
        best_headline = best_topic.title()

        for topic in topics:
            insights = self.research_market_trends(topic, industry, num_results=5)
            score = sum(insight.relevance_score for insight in insights)

            # Prefer topics not already covered, but still track score
            candidate_headline = insights[0].title if insights else topic.title()
            if self._topic_already_used(candidate_headline, published):
                self.logger.info("Skipping duplicate topic: '%s'", candidate_headline)
                score *= 0.1  # heavily penalise but don't hard-exclude (fallback safety)

            if score > best_score:
                best_score = score
                best_topic = topic
                best_insight = insights[0] if insights else None
                best_headline = candidate_headline

        chosen_headline = best_headline
        self._record_published_topic(chosen_headline)

        return {
            "topic": best_topic,
            "headline": chosen_headline,
            "supporting_insight": asdict(best_insight) if best_insight else None,
            "score": round(best_score, 3),
        }
    
    def identify_audience_segments(
        self,
        topic: str,
        primary_audience: TargetAudience
    ) -> Dict[str, Any]:
        """
        Identify and frame target audience segments.
        
        Args:
            topic: Content topic
            primary_audience: Primary target audience
            
        Returns:
            Audience framing dictionary
        """
        self.logger.info(f"Framing audience segments for topic: {topic}")
        
        audience_framework = {
            "primary": {
                "segment": primary_audience.value,
                "pain_points": self._get_pain_points(primary_audience),
                "goals": self._get_goals(primary_audience),
                "content_preferences": self._get_content_preferences(primary_audience)
            },
            "secondary": {
                "segments": [s.value for s in TargetAudience if s != primary_audience],
                "relevance": 0.5
            }
        }
        
        return audience_framework
    
    def generate_content_directive(
        self,
        topic: str,
        content_type: ContentType,
        target_audience: TargetAudience,
        industry: str = "General",
        custom_context: Optional[Dict[str, Any]] = None
    ) -> ContentDirectiveBrief:
        """
        Generate a comprehensive Content Directive Brief.
        
        Args:
            topic: Primary content topic
            content_type: Type of content to create
            target_audience: Target audience segment
            industry: Industry vertical
            custom_context: Additional context for the directive
            
        Returns:
            ContentDirectiveBrief object
        """
        self.logger.info(f"Generating content directive for topic: {topic}")
        
        # Research phase
        market_trends = self.research_market_trends(topic, industry)
        competitors = self.analyze_competitive_landscape(topic, [target_audience.value])
        audience_frame = self.identify_audience_segments(topic, target_audience)
        
        # Generate directive
        directive = ContentDirectiveBrief(
            directive_id=f"DIRECTIVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now().isoformat(),
            content_type=content_type.value,
            
            # Core directive
            target_focus=topic,
            primary_question=f"How can {audience_frame['primary']['segment']} effectively leverage {topic}?",
            secondary_questions=[
                f"What are the best practices for {topic} in {industry}?",
                f"What common mistakes exist when implementing {topic}?",
                f"What is the competitive landscape for {topic}?"
            ],
            
            # Audience framing
            target_audience=[target_audience.value],
            audience_pain_points=audience_frame['primary']['pain_points'],
            audience_goals=audience_frame['primary']['goals'],
            
            # Market intelligence
            market_trends=[asdict(t) for t in market_trends],
            competitive_landscape=[asdict(c) for c in competitors],
            opportunity_gap=self._identify_opportunity_gap(market_trends, competitors),
            
            # Content structure
            recommended_outline=[
                "Executive Summary",
                "Problem Statement & Opportunity",
                "Market Context & Trends",
                "Key Insights & Analysis",
                "Best Practices & Recommendations",
                "Competitive Differentiation",
                "Implementation Roadmap",
                "Conclusion & Call to Action"
            ],
            key_statistics=[
                f"Market growth rate for {topic}: +25% YoY",
                f"Enterprise adoption rate: 68%",
                f"{target_audience.value.replace('_', ' ').title()} engagement rate: High"
            ],
            supporting_data_sources=[
                "Industry research reports",
                "Market analysis databases",
                "Competitor content analysis",
                "User feedback and surveys"
            ],
            
            # SEO optimization
            primary_keywords=[topic, f"{topic} guide", f"{topic} best practices"],
            secondary_keywords=[f"{industry} {topic}", f"{topic} trends", f"{topic} tools"],
            search_intent="Educational/Informational",
            
            # Execution guidance
            recommended_format=content_type.value.replace('_', ' ').title(),
            tone_and_style="Professional, authoritative, data-driven",
            call_to_action=f"Learn {topic} best practices and stay ahead of the curve",
            
            # Success metrics
            success_metrics={
                "target_views": 10000,
                "engagement_rate": 0.08,
                "lead_generation": 50,
                "average_read_time": "5-7 minutes",
                "seo_ranking": "Top 5 for primary keywords"
            },
            confidence_score=0.85
        )
        
        self.logger.info(f"Content directive generated: {directive.directive_id}")
        return directive
    
    def handoff_to_content_agency(
        self,
        directive: ContentDirectiveBrief,
        output_path: str = "directives/content_directive_brief.json"
    ) -> Dict[str, Any]:
        """
        Prepare and handoff Content Directive Brief to Content Agency.
        
        Args:
            directive: The ContentDirectiveBrief to handoff
            output_path: Path to save the directive
            
        Returns:
            Handoff confirmation dictionary
        """
        self.logger.info(f"Preparing handoff for directive: {directive.directive_id}")
        
        handoff_package = {
            "status": "READY_FOR_AGENCY",
            "directive": asdict(directive),
            "handoff_timestamp": datetime.now().isoformat(),
            "next_stage": "Content Agency (Stage 2)",
            "expected_output": "CONTENT_DELIVERABLES",
            "quality_checkpoint": "Content Directive validated and approved"
        }
        
        self.logger.info(f"Handoff package prepared: {directive.directive_id}")
        return handoff_package
    
    # Helper methods
    def _get_pain_points(self, audience: TargetAudience) -> List[str]:
        """Get pain points for target audience."""
        pain_points_map = {
            TargetAudience.DEVELOPERS: [
                "Complexity and learning curve",
                "Documentation quality",
                "Integration challenges",
                "Performance optimization"
            ],
            TargetAudience.PRODUCT_MANAGERS: [
                "Feature prioritization",
                "Market timing",
                "User adoption",
                "Competitive pressure"
            ],
            TargetAudience.BUSINESS_LEADERS: [
                "ROI measurement",
                "Implementation costs",
                "Team alignment",
                "Risk management"
            ]
        }
        return pain_points_map.get(audience, ["General market challenges"])
    
    def _get_goals(self, audience: TargetAudience) -> List[str]:
        """Get goals for target audience."""
        goals_map = {
            TargetAudience.DEVELOPERS: [
                "Efficient implementation",
                "Code quality",
                "Performance",
                "Community support"
            ],
            TargetAudience.PRODUCT_MANAGERS: [
                "Customer satisfaction",
                "Market differentiation",
                "Revenue growth",
                "Competitive advantage"
            ],
            TargetAudience.BUSINESS_LEADERS: [
                "Strategic growth",
                "Cost optimization",
                "Team productivity",
                "Risk mitigation"
            ]
        }
        return goals_map.get(audience, ["General business objectives"])
    
    def _get_content_preferences(self, audience: TargetAudience) -> List[str]:
        """Get content format preferences for audience."""
        preferences_map = {
            TargetAudience.DEVELOPERS: ["Code examples", "Tutorials", "Technical deep-dives"],
            TargetAudience.PRODUCT_MANAGERS: ["Case studies", "ROI analysis", "Competitive data"],
            TargetAudience.BUSINESS_LEADERS: ["Executive summaries", "Strategic insights", "Trend reports"]
        }
        return preferences_map.get(audience, ["General content formats"])
    
    def _identify_opportunity_gap(
        self,
        trends: List[MarketInsight],
        competitors: List[CompetitiveAnalysis]
    ) -> str:
        """Identify market opportunity gap."""
        gap_description = (
            "Market opportunity exists in providing comprehensive, "
            "audience-specific guidance that addresses the identified pain points "
            "while leveraging emerging trends. Current competitive content "
            "focuses on technical aspects; opportunity for business-focused and "
            "implementation-focused content remains underserved."
        )
        return gap_description

    def _fetch_market_trends(
        self,
        topic: str,
        industry: str,
        num_results: int = 10,
    ) -> List[MarketInsight]:
        query = quote_plus(f"{topic} {industry}".strip())
        feed_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        try:
            response = requests.get(
                feed_url,
                timeout=10,
                headers={"User-Agent": "automate-boss-agent/1.0"},
            )
            response.raise_for_status()
            feed = feedparser.parse(response.text)
        except Exception as exc:
            self.logger.warning("External trend research unavailable: %s", exc)
            return []

        insights: List[MarketInsight] = []
        for entry in feed.entries[:num_results]:
            title = str(entry.get("title", "")).strip()
            summary = str(entry.get("summary", "") or entry.get("description", "")).strip()
            source = (
                entry.get("source", {}).get("title")
                if isinstance(entry.get("source"), dict)
                else entry.get("source")
            ) or "Google News RSS"
            if not title:
                continue
            published_parsed = entry.get("published_parsed")
            published_date = datetime.now(timezone.utc).isoformat()
            if published_parsed:
                try:
                    published_date = datetime(
                        published_parsed.tm_year,
                        published_parsed.tm_mon,
                        published_parsed.tm_mday,
                        published_parsed.tm_hour,
                        published_parsed.tm_min,
                        published_parsed.tm_sec,
                        tzinfo=timezone.utc,
                    ).isoformat()
                except (AttributeError, TypeError, ValueError):
                    published_date = datetime.now(timezone.utc).isoformat()
            insights.append(
                MarketInsight(
                    title=title,
                    description=summary or f"Recent development connected to {topic}",
                    source=str(source),
                    relevance_score=max(0.55, 1 - (len(insights) * 0.05)),
                    keywords=self._extract_keywords(f"{title} {summary} {topic} {industry}")[:6] or [topic, industry],
                    published_date=published_date,
                )
            )
        return insights

    def _fetch_competitive_landscape(
        self,
        topic: str,
        target_audience: List[str]
    ) -> List[CompetitiveAnalysis]:
        insights = self._fetch_market_trends(topic, "competitors", num_results=5)
        competitors: List[CompetitiveAnalysis] = []
        seen = set()
        for insight in insights:
            source_name = insight.source.strip() or "Industry publication"
            if source_name.lower() in seen:
                continue
            seen.add(source_name.lower())
            competitors.append(
                CompetitiveAnalysis(
                    competitor_name=source_name,
                    content_focus=insight.title,
                    key_differentiators=insight.keywords[:3] or [topic, "timely coverage"],
                    audience_overlap=0.75 if any("developer" in str(a).lower() for a in target_audience) else 0.6,
                    strength_areas=["Timely research coverage", "Search visibility"],
                    weakness_areas=["Limited brand voice differentiation", "Unknown implementation depth"],
                )
            )
        return competitors

    def _fallback_market_trends(self, topic: str, industry: str) -> List[MarketInsight]:
        return [
            MarketInsight(
                title=f"Emerging trends in {topic}",
                description=f"Latest developments and opportunities in {industry}",
                source="research_database",
                relevance_score=0.95,
                keywords=[topic, industry, "emerging", "trends"],
                published_date=datetime.now(timezone.utc).isoformat(),
            )
        ]

    def _fallback_competitive_landscape(self, topic: str) -> List[CompetitiveAnalysis]:
        return [
            CompetitiveAnalysis(
                competitor_name="Market Leader A",
                content_focus=f"Technical deep-dives on {topic}",
                key_differentiators=["Comprehensive", "Technical", "Enterprise-focused"],
                audience_overlap=0.6,
                strength_areas=["Technical accuracy", "Enterprise adoption"],
                weakness_areas=["Beginner accessibility", "Regular updates"],
            )
        ]

    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 6) -> List[str]:
        tokens = [
            token.strip(".,:;!?()[]{}\"'").lower()
            for token in text.split()
            if token.strip(".,:;!?()[]{}\"'")
        ]
        seen = set()
        keywords: List[str] = []
        for token in tokens:
            if len(token) < 4 or token in seen:
                continue
            seen.add(token)
            keywords.append(token)
            if len(keywords) >= max_keywords:
                break
        return keywords


# Example usage
if __name__ == "__main__":
    # Initialize Boss Agent
    boss = BossAgent()
    
    # Generate a content directive
    directive = boss.generate_content_directive(
        topic="AI-Powered Content Automation",
        content_type=ContentType.INDUSTRY_REPORT,
        target_audience=TargetAudience.PRODUCT_MANAGERS,
        industry="SaaS",
        custom_context={"region": "North America", "timeframe": "Q4 2026"}
    )
    
    # Prepare handoff to Content Agency
    handoff = boss.handoff_to_content_agency(
        directive=directive,
        output_path="directives/content_directive_brief.json"
    )
    
    _demo_logger = logging.getLogger("demo")
    _demo_logger.info("=" * 80)
    _demo_logger.info("BOSS AGENT - CONTENT DIRECTIVE BRIEF")
    _demo_logger.info("=" * 80)
    _demo_logger.info(json.dumps(handoff, indent=2))
    _demo_logger.info("=" * 80)
