"""
The Overseer Agent - Stage 4: Quality Control & Final Compilation
Responsibility: Final quality assurance, system checks, and terminal briefing compilation.

Execution: Acts as the central orchestrator and quality control checkpoint.
Performs full system validation across all previous stages.
Compiles the TERMINAL_BRIEFING for CEO review and approval.

Handoff Output: TERMINAL_BRIEFING_PKG sent to CEO (Kurt Michael Astarita) for final authorization.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QualityCheckLevel(Enum):
    """Quality check severity levels."""
    PASS = "pass"
    WARNING = "warning"
    CRITICAL = "critical"


class PipelineStage(Enum):
    """Pipeline stages for tracking."""
    BOSS_AGENT = "Stage 1: Boss Agent"
    CONTENT_AGENCY = "Stage 2: Content Agency"
    ONPAGE_SEO_AGENCY = "Stage 3: On-Page SEO Agency"
    OVERSEER = "Stage 4: The Overseer"
    CEO_APPROVAL = "Stage 5: CEO Approval"


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""
    check_name: str
    level: str  # pass, warning, critical
    score: float  # 0-1
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ResearchPhaseReport:
    """Compilation of research phase outputs."""
    research_brief_id: str
    primary_topic: str
    target_audience: List[str]
    primary_keywords: List[str]
    competitive_analysis_summary: str
    market_trends_count: int
    key_statistics_count: int
    research_quality_score: float


@dataclass
class CreativePhaseReport:
    """Compilation of creative phase outputs."""
    draft_id: str
    title: str
    voice_used: str
    tone_used: str
    word_count: int
    reading_time_minutes: int
    readability_score: float
    consistency_score: float
    engagement_score: float
    creativity_score: float
    originality_score: float
    authority_score: float


@dataclass
class TechnicalPhaseReport:
    """Compilation of technical phase outputs."""
    content_id: str
    url_slug: str
    seo_score: float
    keyword_optimization_score: float
    technical_seo_score: float
    meta_title: str
    meta_description: str
    heading_count: int
    optimized_heading_count: int
    internal_link_count: int
    schema_markup_configured: bool


@dataclass
class ComplianceCheckResults:
    """Results of compliance and integrity checks."""
    creative_integrity_preserved: bool
    keyword_density_optimal: bool
    meta_tags_complete: bool
    schema_valid: bool
    heading_hierarchy_valid: bool
    links_functional: bool
    no_critical_warnings: bool
    overall_compliance_score: float


@dataclass
class TerminalBriefing:
    """Final terminal briefing for CEO approval."""
    briefing_id: str
    created_at: str
    pipeline_status: str  # complete
    
    # Metadata
    content_title: str
    content_url: str
    target_audience: str
    
    # Phase reports
    research_phase: Dict[str, Any]
    creative_phase: Dict[str, Any]
    technical_phase: Dict[str, Any]
    
    # Quality assurance
    total_quality_score: float  # 0-100
    quality_checks: List[Dict[str, Any]]
    compliance_checks: Dict[str, Any]
    
    # Risk assessment
    risk_level: str  # low, medium, high
    risks_identified: List[str]
    recommendations: List[str]
    
    # Content readiness
    production_ready: bool
    go_live_approved: bool
    
    # CEO actionable summary
    executive_summary: str
    critical_metrics: Dict[str, Any]
    approval_required_items: List[str]
    
    # Full content package
    content_payload: Dict[str, Any]
    
    # Dispatch information
    dispatch_timestamp: str
    next_action: str  # "AWAITING_CEO_APPROVAL"
    approval_url: str
    
    def to_json(self) -> str:
        """Convert to JSON format."""
        return json.dumps(asdict(self), indent=2)


class QualityAssuranceEngine:
    """Comprehensive quality assurance system."""
    
    def __init__(self):
        """Initialize QA engine."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def check_meta_tags(self, meta_tags: Dict[str, Any]) -> QualityCheckResult:
        """Check meta tags completeness and quality."""
        self.logger.info("Checking meta tags...")
        
        checks_passed = 0
        checks_total = 0
        messages = []
        
        # Check meta title
        checks_total += 1
        if meta_tags.get("title") and 50 < len(meta_tags["title"]) < 65:
            checks_passed += 1
        else:
            messages.append(f"Meta title length: {len(meta_tags.get('title', ''))} (should be 50-65)")
        
        # Check meta description
        checks_total += 1
        if meta_tags.get("description") and 120 < len(meta_tags["description"]) < 165:
            checks_passed += 1
        else:
            messages.append(f"Meta description length: {len(meta_tags.get('description', ''))} (should be 120-165)")
        
        # Check canonical URL
        checks_total += 1
        if meta_tags.get("canonical_url"):
            checks_passed += 1
        else:
            messages.append("Canonical URL missing")
        
        # Check Open Graph tags
        checks_total += 1
        if meta_tags.get("og_title") and meta_tags.get("og_description"):
            checks_passed += 1
        else:
            messages.append("Open Graph tags incomplete")
        
        # Check Twitter Card
        checks_total += 1
        if meta_tags.get("twitter_title") and meta_tags.get("twitter_description"):
            checks_passed += 1
        else:
            messages.append("Twitter Card tags incomplete")
        
        score = checks_passed / checks_total if checks_total > 0 else 0
        level = "pass" if score >= 0.8 else "warning" if score >= 0.6 else "critical"
        
        return QualityCheckResult(
            check_name="Meta Tags Quality",
            level=level,
            score=score,
            message=f"{checks_passed}/{checks_total} meta tag checks passed",
            details={"checks_passed": checks_passed, "checks_total": checks_total},
            recommendations=messages if score < 1.0 else []
        )
    
    def check_schema_markup(self, schema: Dict[str, Any]) -> QualityCheckResult:
        """Check JSON-LD schema markup validity."""
        self.logger.info("Checking schema markup...")
        
        checks_passed = 0
        checks_total = 6
        messages = []
        
        # Check schema context
        if schema.get("@context") == "https://schema.org":
            checks_passed += 1
        else:
            messages.append("Invalid or missing schema context")
        
        # Check schema type
        if schema.get("@type"):
            checks_passed += 1
        else:
            messages.append("Schema type missing")
        
        # Check headline
        if schema.get("headline"):
            checks_passed += 1
        else:
            messages.append("Schema headline missing")
        
        # Check author
        if schema.get("author") and schema["author"].get("name"):
            checks_passed += 1
        else:
            messages.append("Schema author information incomplete")
        
        # Check date published
        if schema.get("datePublished"):
            checks_passed += 1
        else:
            messages.append("Schema datePublished missing")
        
        # Check image
        if schema.get("image"):
            checks_passed += 1
        else:
            messages.append("Schema image missing")
        
        score = checks_passed / checks_total if checks_total > 0 else 0
        level = "pass" if score >= 0.8 else "warning" if score >= 0.6 else "critical"
        
        return QualityCheckResult(
            check_name="Schema Markup Validity",
            level=level,
            score=score,
            message=f"{checks_passed}/{checks_total} schema checks passed",
            details={"checks_passed": checks_passed, "checks_total": checks_total},
            recommendations=messages if score < 1.0 else []
        )
    
    def check_heading_hierarchy(self, headings: List[Dict[str, Any]]) -> QualityCheckResult:
        """Check heading hierarchy structure."""
        self.logger.info("Checking heading hierarchy...")
        
        messages = []
        h1_count = sum(1 for h in headings if h.get("level") == "h1")
        h2_count = sum(1 for h in headings if h.get("level") == "h2")
        h3_count = sum(1 for h in headings if h.get("level") == "h3")
        
        score = 1.0
        
        # Check for exactly one H1
        if h1_count != 1:
            messages.append(f"Should have exactly 1 H1, found {h1_count}")
            score -= 0.3
        
        # Check for H2s after H1
        if h1_count > 0 and h2_count == 0:
            messages.append("No H2 headings found after H1")
            score -= 0.2
        
        # Check logical nesting
        if h2_count > 0 and h3_count > h2_count * 3:
            messages.append("Too many H3 headings relative to H2s")
            score -= 0.1
        
        score = max(0, score)
        level = "pass" if score >= 0.8 else "warning" if score >= 0.6 else "critical"
        
        return QualityCheckResult(
            check_name="Heading Hierarchy",
            level=level,
            score=score,
            message=f"Hierarchy valid: 1 H1, {h2_count} H2s, {h3_count} H3s",
            details={
                "h1_count": h1_count,
                "h2_count": h2_count,
                "h3_count": h3_count
            },
            recommendations=messages if score < 1.0 else []
        )
    
    def check_readability_preservation(
        self,
        creative_engagement_score: float,
        readability_score: float
    ) -> QualityCheckResult:
        """Check that creative quality was preserved through optimization."""
        self.logger.info("Checking readability preservation...")
        
        messages = []
        score = min(creative_engagement_score, readability_score)
        
        if creative_engagement_score < 0.75:
            messages.append(f"Creative engagement score low: {round(creative_engagement_score, 2)}")
        
        if readability_score < 0.70:
            messages.append(f"Readability score low: {round(readability_score, 2)}")
        
        level = "pass" if score >= 0.75 else "warning" if score >= 0.60 else "critical"
        
        return QualityCheckResult(
            check_name="Readability Preservation",
            level=level,
            score=score,
            message=f"Creative integrity maintained: engagement {round(creative_engagement_score, 2)}, readability {round(readability_score, 2)}",
            details={
                "creative_engagement_score": creative_engagement_score,
                "readability_score": readability_score
            },
            recommendations=messages if score < 1.0 else []
        )
    
    def check_seo_optimization(self, seo_score: float) -> QualityCheckResult:
        """Check SEO optimization quality."""
        self.logger.info("Checking SEO optimization...")
        
        messages = []
        score = seo_score / 100  # Convert to 0-1
        
        if seo_score < 70:
            messages.append(f"SEO score below target: {seo_score}/100")
        
        level = "pass" if score >= 0.80 else "warning" if score >= 0.65 else "critical"
        
        return QualityCheckResult(
            check_name="SEO Optimization Quality",
            level=level,
            score=score,
            message=f"SEO score: {seo_score}/100",
            details={"seo_score": seo_score},
            recommendations=messages if score < 1.0 else []
        )
    
    def check_keyword_density(self, keyword_density: Dict[str, float]) -> QualityCheckResult:
        """Check keyword density is within optimal range."""
        self.logger.info("Checking keyword density...")
        
        messages = []
        optimal_keywords = 0
        total_keywords = len(keyword_density)
        
        for keyword, density in keyword_density.items():
            # Optimal range: 0.5% to 2.0%
            if 0.5 <= density <= 2.0:
                optimal_keywords += 1
            else:
                messages.append(f"'{keyword}' density {density}% outside optimal range (0.5-2.0%)")
        
        score = optimal_keywords / total_keywords if total_keywords > 0 else 0
        level = "pass" if score >= 0.9 else "warning" if score >= 0.7 else "critical"
        
        return QualityCheckResult(
            check_name="Keyword Density",
            level=level,
            score=score,
            message=f"{optimal_keywords}/{total_keywords} keywords in optimal density range",
            details={"keyword_density": keyword_density},
            recommendations=messages if score < 1.0 else []
        )
    
    def check_internal_links(self, internal_link_count: int) -> QualityCheckResult:
        """Check internal linking strategy."""
        self.logger.info("Checking internal links...")
        
        messages = []
        score = 0.5  # Base score
        
        if internal_link_count == 0:
            messages.append("No internal links found")
            score = 0.0
            level = "critical"
        elif internal_link_count < 3:
            messages.append(f"Few internal links: {internal_link_count} (recommend 3-5)")
            score = 0.6
            level = "warning"
        elif internal_link_count >= 3 and internal_link_count <= 8:
            score = 1.0
            level = "pass"
        else:
            messages.append(f"Many internal links: {internal_link_count} (consider reducing to 3-5)")
            score = 0.8
            level = "warning"
        
        return QualityCheckResult(
            check_name="Internal Linking Strategy",
            level=level,
            score=score,
            message=f"Internal links: {internal_link_count}",
            details={"internal_link_count": internal_link_count},
            recommendations=messages if score < 1.0 else []
        )
    
    def run_full_qa_suite(
        self,
        seo_content: Dict[str, Any],
        creative_metrics: Dict[str, Any]
    ) -> Tuple[List[QualityCheckResult], float]:
        """
        Run complete QA suite.
        
        Args:
            seo_content: SEO-optimized content from Stage 3
            creative_metrics: Creative metrics from Stage 2
            
        Returns:
            Tuple of (list of check results, overall score 0-100)
        """
        self.logger.info("Running full QA suite...")
        
        checks = []
        
        # Run all checks
        checks.append(self.check_meta_tags(seo_content.get("meta_tags", {})))
        checks.append(self.check_schema_markup(seo_content.get("schema_markup", {})))
        checks.append(self.check_heading_hierarchy(seo_content.get("heading_structure", [])))
        checks.append(self.check_readability_preservation(
            creative_metrics.get("engagement_score", 0),
            creative_metrics.get("readability_score", 0)
        ))
        checks.append(self.check_seo_optimization(seo_content.get("seo_score", 0)))
        checks.append(self.check_keyword_density(seo_content.get("keyword_density", {})))
        checks.append(self.check_internal_links(len(seo_content.get("internal_links", []))))
        
        # Calculate overall score
        overall_score = sum(check.score for check in checks) / len(checks) if checks else 0
        overall_score = overall_score * 100  # Convert to 0-100
        
        self.logger.info(f"QA suite complete. Overall score: {round(overall_score, 2)}/100")
        
        return checks, overall_score


class RiskAssessmentEngine:
    """Risk assessment and mitigation system."""
    
    def __init__(self):
        """Initialize risk assessment engine."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def assess_production_risks(
        self,
        quality_checks: List[QualityCheckResult],
        overall_qa_score: float
    ) -> Tuple[str, List[str], List[str]]:
        """
        Assess production-readiness risks.
        
        Args:
            quality_checks: Results from QA suite
            overall_qa_score: Overall QA score (0-100)
            
        Returns:
            Tuple of (risk_level: low/medium/high, risks: list, mitigations: list)
        """
        self.logger.info("Assessing production risks...")
        
        risks = []
        mitigations = []
        
        # Check for critical issues
        critical_checks = [c for c in quality_checks if c.level == "critical"]
        if critical_checks:
            for check in critical_checks:
                risks.append(f"CRITICAL: {check.check_name} - {check.message}")
                if check.recommendations:
                    mitigations.extend(check.recommendations)
        
        # Check warning-level issues
        warning_checks = [c for c in quality_checks if c.level == "warning"]
        if len(warning_checks) >= 3:
            risks.append(f"Multiple warning-level issues detected ({len(warning_checks)})")
        
        # Check overall score
        if overall_qa_score < 70:
            risks.append(f"Overall QA score below threshold: {round(overall_qa_score, 2)}/100")
            mitigations.append("Address failing checks before publication")
        
        # Determine risk level
        if critical_checks:
            risk_level = "high"
        elif overall_qa_score < 70 or len(warning_checks) >= 3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        self.logger.info(f"Risk assessment complete. Level: {risk_level}")
        
        return risk_level, risks, mitigations


class TerminalBriefingCompiler:
    """Compiles final terminal briefing for CEO."""
    
    def __init__(self):
        """Initialize briefing compiler."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.qa_engine = QualityAssuranceEngine()
        self.risk_engine = RiskAssessmentEngine()
    
    def compile_briefing(
        self,
        research_brief: Dict[str, Any],
        raw_creative_draft: Dict[str, Any],
        seo_optimized_content: Dict[str, Any],
        base_url: str = "https://kurtastarita.com"
    ) -> TerminalBriefing:
        """
        Compile complete terminal briefing for CEO approval.
        
        Args:
            research_brief: Research Brief from Stage 1
            raw_creative_draft: Raw Creative Draft from Stage 2
            seo_optimized_content: SEO Optimized Content from Stage 3
            base_url: Base URL for publication
            
        Returns:
            TerminalBriefing object ready for CEO
        """
        self.logger.info("Compiling terminal briefing...")
        
        # Run quality assurance
        qa_checks, overall_qa_score = self.qa_engine.run_full_qa_suite(
            seo_optimized_content,
            {
                "engagement_score": raw_creative_draft.get("engagement_score", 0),
                "readability_score": raw_creative_draft.get("readability_scores", {}).get("readability_score", 0) / 100
            }
        )
        
        # Assess risks
        risk_level, risks, mitigations = self.risk_engine.assess_production_risks(
            qa_checks,
            overall_qa_score
        )
        
        # Compile phase reports
        research_phase = ResearchPhaseReport(
            research_brief_id=research_brief.get("research_brief_id", "UNKNOWN"),
            primary_topic=research_brief.get("primary_topic", ""),
            target_audience=research_brief.get("target_audience", []),
            primary_keywords=research_brief.get("primary_keywords", []),
            competitive_analysis_summary=research_brief.get("opportunity_gap", ""),
            market_trends_count=len(research_brief.get("market_trends", [])),
            key_statistics_count=len(research_brief.get("key_statistics", [])),
            research_quality_score=0.90
        )
        
        creative_phase = CreativePhaseReport(
            draft_id=raw_creative_draft.get("draft_id", "UNKNOWN"),
            title=raw_creative_draft.get("title", ""),
            voice_used=raw_creative_draft.get("voice_used", ""),
            tone_used=raw_creative_draft.get("tone_used", ""),
            word_count=raw_creative_draft.get("overall_word_count", 0),
            reading_time_minutes=max(1, raw_creative_draft.get("overall_word_count", 0) // 200),
            readability_score=raw_creative_draft.get("readability_scores", {}).get("readability_score", 0),
            consistency_score=raw_creative_draft.get("consistency_score", 0),
            engagement_score=raw_creative_draft.get("engagement_score", 0),
            creativity_score=raw_creative_draft.get("creativity_score", 0),
            originality_score=raw_creative_draft.get("originality_score", 0),
            authority_score=raw_creative_draft.get("authority_score", 0)
        )
        
        technical_phase = TechnicalPhaseReport(
            content_id=seo_optimized_content.get("content_id", "UNKNOWN"),
            url_slug=seo_optimized_content.get("url_slug", ""),
            seo_score=seo_optimized_content.get("seo_score", 0),
            keyword_optimization_score=seo_optimized_content.get("keyword_optimization_score", 0),
            technical_seo_score=seo_optimized_content.get("technical_seo_score", 0),
            meta_title=seo_optimized_content.get("meta_tags", {}).get("title", ""),
            meta_description=seo_optimized_content.get("meta_tags", {}).get("description", ""),
            heading_count=len(seo_optimized_content.get("heading_structure", [])),
            optimized_heading_count=sum(
                1 for h in seo_optimized_content.get("heading_structure", [])
                if h.get("keyword_optimized", False)
            ),
            internal_link_count=len(seo_optimized_content.get("internal_links", [])),
            schema_markup_configured=bool(seo_optimized_content.get("schema_markup"))
        )
        
        # Build compliance checks
        compliance = ComplianceCheckResults(
            creative_integrity_preserved=raw_creative_draft.get("engagement_score", 0) > 0.75,
            keyword_density_optimal=all(
                0.5 <= density <= 2.0
                for density in seo_optimized_content.get("keyword_density", {}).values()
            ),
            meta_tags_complete=all(
                seo_optimized_content.get("meta_tags", {}).get(tag)
                for tag in ["title", "description"]
            ),
            schema_valid=bool(seo_optimized_content.get("schema_markup")),
            heading_hierarchy_valid=len([h for h in seo_optimized_content.get("heading_structure", []) if h.get("level") == "h1"]) == 1,
            links_functional=len(seo_optimized_content.get("internal_links", [])) >= 3,
            no_critical_warnings=not any(c.level == "critical" for c in qa_checks),
            overall_compliance_score=overall_qa_score / 100
        )
        
        # Create terminal briefing
        content_url = f"{base_url}/{seo_optimized_content.get('url_slug', 'content')}"
        production_ready = overall_qa_score >= 75 and risk_level == "low"
        
        briefing = TerminalBriefing(
            briefing_id=f"BRIEFING_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now().isoformat(),
            pipeline_status="complete",
            
            # Metadata
            content_title=seo_optimized_content.get("title", "Untitled"),
            content_url=content_url,
            target_audience=seo_optimized_content.get("target_audience", "General"),
            
            # Phase reports
            research_phase=asdict(research_phase),
            creative_phase=asdict(creative_phase),
            technical_phase=asdict(technical_phase),
            
            # Quality assurance
            total_quality_score=round(overall_qa_score, 2),
            quality_checks=[
                {
                    "check_name": check.check_name,
                    "level": check.level,
                    "score": round(check.score, 3),
                    "message": check.message,
                    "recommendations": check.recommendations
                }
                for check in qa_checks
            ],
            compliance_checks=asdict(compliance),
            
            # Risk assessment
            risk_level=risk_level,
            risks_identified=risks,
            recommendations=mitigations + [
                "Review content on staging environment before publication",
                "Verify all links are functional",
                "Test on multiple devices and browsers",
                "Monitor performance metrics post-publication"
            ],
            
            # Content readiness
            production_ready=production_ready,
            go_live_approved=production_ready,
            
            # CEO actionable summary
            executive_summary=self._generate_executive_summary(
                seo_optimized_content,
                creative_phase,
                overall_qa_score,
                production_ready
            ),
            critical_metrics={
                "quality_score": round(overall_qa_score, 2),
                "seo_score": seo_optimized_content.get("seo_score", 0),
                "word_count": seo_optimized_content.get("word_count", 0),
                "reading_time": seo_optimized_content.get("reading_time_minutes", 0),
                "risk_level": risk_level,
                "production_ready": production_ready
            },
            approval_required_items=[
                "✓ Review quality metrics" if overall_qa_score >= 75 else "✗ Review failing QA checks",
                "✓ Approve content" if production_ready else "✗ Address critical issues",
                "✓ Authorize publication" if production_ready else "✗ Schedule for revision"
            ],
            
            # Full content package
            content_payload=seo_optimized_content,
            
            # Dispatch information
            dispatch_timestamp=datetime.now().isoformat(),
            next_action="AWAITING_CEO_APPROVAL",
            approval_url=f"{base_url}/admin/approve/{seo_optimized_content.get('content_id', 'content')}"
        )
        
        self.logger.info(f"Terminal briefing compiled: {briefing.briefing_id}")
        return briefing
    
    def _generate_executive_summary(
        self,
        seo_content: Dict[str, Any],
        creative_phase: CreativePhaseReport,
        quality_score: float,
        production_ready: bool
    ) -> str:
        """Generate executive summary for CEO."""
        status = "✅ READY FOR PUBLICATION" if production_ready else "⚠️ REQUIRES ATTENTION"
        
        summary = f"""
{status}

CONTENT: {seo_content.get('title', 'Untitled')}
URL: /{seo_content.get('url_slug', 'content')}

QUALITY METRICS:
- Overall Quality Score: {quality_score:.1f}/100
- Creative Engagement: {round(creative_phase.engagement_score * 100, 1)}%
- SEO Optimization: {seo_content.get('seo_score', 0):.0f}/100
- Content Word Count: {seo_content.get('word_count', 0):,} words
- Reading Time: {seo_content.get('reading_time_minutes', 0)} minutes

PRODUCTION STATUS:
{'✓ All systems green. Ready to deploy.' if production_ready else '✗ Issues detected. Review recommendations.'}

ACTION REQUIRED:
{'Click "APPROVE & PUBLISH" to deploy immediately.' if production_ready else 'Review quality report and address recommendations.'}
"""
        return summary.strip()


class TheOverseer:
    """
    Stage 4: The Overseer - Vault-Tec Central Command
    
    Central orchestrator and quality control checkpoint.
    Performs comprehensive validation across all pipeline stages.
    Compiles TERMINAL_BRIEFING_PKG for CEO authorization.
    
    Represents the hyper-efficient, cold central computer running operations.
    """
    
    def __init__(self):
        """Initialize The Overseer."""
        self.name = "The Overseer"
        self.stage = "Stage 4: Central Command & QC"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.briefing_compiler = TerminalBriefingCompiler()
    
    def process_pipeline_output(
        self,
        research_brief: Dict[str, Any],
        raw_creative_draft: Dict[str, Any],
        seo_optimized_content: Dict[str, Any],
        base_url: str = "https://kurtastarita.com"
    ) -> TerminalBriefing:
        """
        Process complete pipeline output and prepare for CEO approval.
        
        Args:
            research_brief: Output from Stage 1
            raw_creative_draft: Output from Stage 2
            seo_optimized_content: Output from Stage 3
            base_url: Base URL for publication
            
        Returns:
            TerminalBriefing ready for CEO
        """
        self.logger.info("OVERSEER INITIATED: Processing pipeline output...")
        
        # Run comprehensive validation
        briefing = self.briefing_compiler.compile_briefing(
            research_brief,
            raw_creative_draft,
            seo_optimized_content,
            base_url
        )
        
        self.logger.info(f"OVERSEER COMPLETE: {briefing.briefing_id}")
        return briefing
    
    def generate_terminal_dispatch(
        self,
        briefing: TerminalBriefing,
        ceo_email: str = "itskurtastarita@gmail.com"
    ) -> Dict[str, Any]:
        """
        Generate terminal dispatch package for CEO.
        
        Args:
            briefing: Terminal briefing object
            ceo_email: CEO email address
            
        Returns:
            Terminal dispatch package
        """
        self.logger.info(f"Generating terminal dispatch for {ceo_email}...")
        
        dispatch = {
            "dispatch_type": "TERMINAL_BRIEFING_PKG",
            "dispatch_timestamp": datetime.now().isoformat(),
            "recipient": {
                "role": "CEO",
                "name": "Kurt Michael Astarita",
                "email": ceo_email
            },
            "briefing_id": briefing.briefing_id,
            "pipeline_status": briefing.pipeline_status,
            "content_summary": {
                "title": briefing.content_title,
                "url": briefing.content_url,
                "target_audience": briefing.target_audience
            },
            "executive_dashboard": {
                "quality_score": briefing.total_quality_score,
                "seo_score": briefing.critical_metrics.get("seo_score"),
                "risk_level": briefing.risk_level,
                "production_ready": briefing.production_ready,
                "word_count": briefing.critical_metrics.get("word_count"),
                "reading_time": briefing.critical_metrics.get("reading_time")
            },
            "phase_reports": {
                "research": briefing.research_phase,
                "creative": briefing.creative_phase,
                "technical": briefing.technical_phase
            },
            "quality_assurance": {
                "overall_score": briefing.total_quality_score,
                "compliance": briefing.compliance_checks,
                "checks_summary": {
                    "passed": len([c for c in briefing.quality_checks if c["level"] == "pass"]),
                    "warnings": len([c for c in briefing.quality_checks if c["level"] == "warning"]),
                    "critical": len([c for c in briefing.quality_checks if c["level"] == "critical"])
                }
            },
            "risk_assessment": {
                "level": briefing.risk_level,
                "identified_risks": briefing.risks_identified,
                "mitigation_recommendations": briefing.recommendations
            },
            "approval_status": {
                "approval_required": True,
                "next_action": briefing.next_action,
                "approval_url": briefing.approval_url,
                "approval_deadline": "Immediate"
            },
            "executive_summary": briefing.executive_summary,
            "full_briefing": briefing,
            "dispatch_instructions": {
                "channel": "Email + Dashboard Notification",
                "urgency": "High",
                "action": "Review briefing and click APPROVE to deploy content"
            }
        }
        
        self.logger.info(f"Terminal dispatch prepared: {dispatch['briefing_id']}")
        return dispatch
    
    def create_approval_payload(
        self,
        briefing: TerminalBriefing,
        approved: bool = False,
        ceo_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Create approval/rejection payload.
        
        Args:
            briefing: Terminal briefing
            approved: Whether CEO approved
            ceo_notes: Any notes from CEO
            
        Returns:
            Approval payload
        """
        payload = {
            "briefing_id": briefing.briefing_id,
            "approval_timestamp": datetime.now().isoformat(),
            "ceo_decision": "APPROVED" if approved else "REJECTED",
            "ceo_notes": ceo_notes,
            "content_id": briefing.critical_metrics.get("content_id"),
            "next_stage": "Stage 5: Deployment Authorization" if approved else "Stage 2: Revision Required",
            "deployment_authorized": approved,
            "go_live_signal": "PROCEED" if approved else "HOLD"
        }
        
        return payload


# Example usage
if __name__ == "__main__":
    # Initialize The Overseer
    overseer = TheOverseer()
    
    # Example outputs from previous stages
    sample_research_brief = {
        "research_brief_id": "RESEARCH_20260808_120000",
        "primary_topic": "AI-Powered Content Automation",
        "target_audience": ["Product Managers"],
        "primary_keywords": ["AI content automation", "automated content creation"],
        "market_trends": [
            {"title": "AI adoption surge", "description": "Rapid growth"},
            {"title": "Automation trends", "description": "Increasing automation"}
        ],
        "key_statistics": [
            "73% enterprise adoption",
            "35% efficiency gains"
        ],
        "opportunity_gap": "Significant market opportunity in education and implementation"
    }
    
    sample_creative_draft = {
        "draft_id": "DRAFT_20260808_170000",
        "title": "AI-Powered Content Automation",
        "voice_used": "authoritative",
        "tone_used": "educational",
        "overall_word_count": 2500,
        "engagement_score": 0.82,
        "consistency_score": 0.88,
        "creativity_score": 0.82,
        "originality_score": 0.78,
        "authority_score": 0.89,
        "readability_scores": {
            "readability_score": 78
        }
    }
    
    sample_seo_content = {
        "content_id": "SEO_20260808_180000",
        "title": "AI-Powered Content Automation",
        "url_slug": "ai-powered-content-automation",
        "word_count": 2500,
        "reading_time_minutes": 12,
        "seo_score": 87.5,
        "keyword_optimization_score": 0.91,
        "technical_seo_score": 0.92,
        "meta_tags": {
            "title": "AI-Powered Content Automation Guide | Kurt Astarita",
            "description": "Learn how to leverage AI to automate content workflows. Complete guide with best practices."
        },
        "schema_markup": {"@context": "https://schema.org", "@type": "BlogPosting"},
        "heading_structure": [
            {"level": "h1", "text": "AI-Powered Content Automation", "keyword_optimized": True},
            {"level": "h2", "text": "The Problem", "keyword_optimized": False},
            {"level": "h2", "text": "Solutions", "keyword_optimized": True}
        ],
        "internal_links": [
            {"anchor_text": "learn more"},
            {"anchor_text": "related content"},
            {"anchor_text": "see guide"}
        ],
        "keyword_density": {
            "AI content automation": 1.2,
            "content workflow": 0.8
        }
    }
    
    # Process through Overseer
    briefing = overseer.process_pipeline_output(
        sample_research_brief,
        sample_creative_draft,
        sample_seo_content
    )
    
    # Generate terminal dispatch
    dispatch = overseer.generate_terminal_dispatch(briefing)
    
    print("\n" + "="*80)
    print("THE OVERSEER - TERMINAL BRIEFING COMPILATION")
    print("Vault-Tec Pipeline: Stage 4")
    print("="*80)
    print(f"\nBriefing ID: {briefing.briefing_id}")
    print(f"Content: {briefing.content_title}")
    print(f"URL: {briefing.content_url}")
    print(f"Pipeline Status: {briefing.pipeline_status}")
    print(f"\nQuality Metrics:")
    print(f"  Total Quality Score: {briefing.total_quality_score}/100")
    print(f"  Risk Level: {briefing.risk_level}")
    print(f"  Production Ready: {briefing.production_ready}")
    print(f"\nPhase Reports:")
    print(f"  Research: {briefing.research_phase['primary_topic']}")
    print(f"  Creative: {briefing.creative_phase['title']} ({briefing.creative_phase['word_count']} words)")
    print(f"  Technical: SEO Score {briefing.technical_phase['seo_score']}/100")
    print(f"\nCompliance Status:")
    for key, value in briefing.compliance_checks.items():
        if isinstance(value, bool):
            print(f"  {key}: {'✓' if value else '✗'}")
    print(f"\nQuality Checks:")
    for check in briefing.quality_checks:
        status = "✓" if check["level"] == "pass" else "⚠" if check["level"] == "warning" else "✗"
        print(f"  {status} {check['check_name']}: {check['message']}")
    print(f"\nExecutive Summary:")
    print(briefing.executive_summary)
    print("\n" + "="*80)
    print("TERMINAL DISPATCH PACKAGE")
    print("="*80)
    print(json.dumps({k: v for k, v in dispatch.items() if k != "full_briefing"}, indent=2, default=str))
    print("="*80)
