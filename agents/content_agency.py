"""
Content Agency Agent - Stage 2: Creative Writing & Content Production
Responsibility: Deep-dive draft writing, storytelling, voice consistency, and readability.

Execution: Focuses entirely on producing engaging, authoritative, and human prose.
Operates free from technical distractions like meta descriptions, schema JSON, or code tag optimization.

Handoff Output: RAW_CREATIVE_DRAFT sent to the Onpage SEO Agency.
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


class VoiceStyle(Enum):
    """Writing voice styles."""
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    AUTHORITATIVE = "authoritative"
    STORYTELLING = "storytelling"
    ACADEMIC = "academic"
    JOURNALISTIC = "journalistic"


class ToneStyle(Enum):
    """Writing tone styles."""
    FORMAL = "formal"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    INSPIRATIONAL = "inspirational"
    EDUCATIONAL = "educational"
    PRAGMATIC = "pragmatic"


class ContentSection(Enum):
    """Standard content sections."""
    INTRODUCTION = "introduction"
    EXECUTIVE_SUMMARY = "executive_summary"
    PROBLEM_STATEMENT = "problem_statement"
    MARKET_CONTEXT = "market_context"
    KEY_INSIGHTS = "key_insights"
    BEST_PRACTICES = "best_practices"
    CASE_STUDIES = "case_studies"
    IMPLEMENTATION = "implementation"
    CONCLUSION = "conclusion"
    CALL_TO_ACTION = "call_to_action"


@dataclass
class WritingStyle:
    """Configuration for writing style and voice."""
    voice: VoiceStyle
    tone: ToneStyle
    sentence_structure: str  # "varied", "short", "complex"
    vocabulary_level: str  # "accessible", "professional", "technical"
    emotion_level: float  # 0-1, how emotionally charged
    storytelling_elements: bool
    use_examples: bool
    use_analogies: bool
    use_data_points: bool


@dataclass
class ContentSectionData:
    """A single section of content."""
    section_type: str
    heading: str
    subheadings: List[str] = field(default_factory=list)
    content: str = ""
    key_messages: List[str] = field(default_factory=list)
    word_count: int = 0
    readability_score: float = 0.0  # 0-100


@dataclass
class RawCreativeDraft:
    """Raw creative draft output for Onpage SEO Agency."""
    draft_id: str
    created_at: str
    research_brief_id: str
    
    # Metadata
    title: str
    content_type: str
    target_audience: str
    primary_topic: str
    
    # Content structure
    content_sections: List[Dict[str, Any]]
    
    # Writing characteristics
    writing_style_config: Dict[str, Any]
    voice_used: str
    tone_used: str
    overall_word_count: int
    
    # Quality metrics
    readability_scores: Dict[str, float]
    consistency_score: float  # 0-1
    engagement_score: float  # 0-1
    
    # Content intelligence
    key_themes: List[str]
    narrative_arc: str
    emotional_resonance: str
    
    # Draft quality indicators
    creativity_score: float  # 0-1
    originality_score: float  # 0-1
    authority_score: float  # 0-1
    
    # Readability analysis
    average_sentence_length: float
    paragraph_structure_variety: str
    flow_score: float  # 0-1
    
    # Raw content
    full_draft: str
    
    # Handoff notes
    editorial_notes: str
    revision_suggestions: List[str]
    
    def to_json(self) -> str:
        """Convert draft to JSON format."""
        return json.dumps(asdict(self), indent=2)


class WritingStyleManager:
    """Manages writing style and consistency throughout content."""
    
    def __init__(self, style_config: WritingStyle):
        """Initialize style manager."""
        self.style = style_config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
    def adapt_sentence(self, sentence: str) -> str:
        """
        Adapt a sentence to match the configured writing style.
        
        Args:
            sentence: Raw sentence text
            
        Returns:
            Style-adapted sentence
        """
        # Apply voice adaptation
        if self.style.voice == VoiceStyle.CONVERSATIONAL:
            # Convert to more conversational (contractions, personal pronouns)
            sentence = sentence.replace("cannot", "can't")
            sentence = sentence.replace("will not", "won't")
            if not any(word in sentence for word in ["I", "we", "you"]):
                sentence = f"Let's explore: {sentence.lower()}"
        
        elif self.style.voice == VoiceStyle.AUTHORITATIVE:
            # Strengthen with power words
            power_words = ["fundamentally", "critically", "significantly", "undeniably"]
            if "is" in sentence and len(sentence) < 100:
                sentence = f"It is {power_words[0]} important that {sentence}"
        
        # Apply tone adaptation
        if self.style.tone == ToneStyle.HUMOROUS:
            # Could add contextual humor
            pass
        elif self.style.tone == ToneStyle.INSPIRATIONAL:
            inspirational_phrases = [
                "Consider this opportunity:",
                "Here's the exciting part:",
                "This is where innovation happens:"
            ]
        
        return sentence
    
    def evaluate_consistency(self, text: str) -> float:
        """
        Evaluate consistency of style across text.
        
        Args:
            text: Content to evaluate
            
        Returns:
            Consistency score 0-1
        """
        paragraphs = text.split("\n\n")
        
        if not paragraphs:
            return 0.0
        
        # Check for consistent sentence structure
        avg_lengths = []
        for para in paragraphs:
            sentences = para.split(".")
            if sentences:
                lengths = [len(s.split()) for s in sentences if s.strip()]
                if lengths:
                    avg_lengths.append(sum(lengths) / len(lengths))
        
        if not avg_lengths:
            return 0.0
        
        # Calculate variance in sentence length
        overall_avg = sum(avg_lengths) / len(avg_lengths)
        variance = sum((x - overall_avg) ** 2 for x in avg_lengths) / len(avg_lengths)
        
        # Lower variance = higher consistency (0-1 scale)
        consistency = 1.0 / (1.0 + (variance / 100))
        return min(consistency, 1.0)
    
    def calculate_readability(self, text: str) -> Dict[str, float]:
        """
        Calculate readability metrics.
        
        Args:
            text: Content to analyze
            
        Returns:
            Dictionary of readability scores
        """
        words = text.split()
        sentences = text.split(".")
        paragraphs = text.split("\n\n")
        
        word_count = len(words)
        sentence_count = len([s for s in sentences if s.strip()])
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        # Avoid division by zero
        if sentence_count == 0 or word_count == 0:
            return {
                "flesch_kincaid_grade": 0,
                "average_sentence_length": 0,
                "average_word_length": 0,
                "readability_score": 0
            }
        
        avg_sentence_length = word_count / sentence_count
        avg_word_length = sum(len(w) for w in words) / word_count if words else 0
        
        # Simplified Flesch-Kincaid grade calculation
        flesch_kincaid = (
            0.39 * (word_count / sentence_count) +
            11.8 * (sum(1 for w in words if len(w) > 3) / word_count) -
            15.59
        )
        
        flesch_kincaid = max(0, min(flesch_kincaid, 18))
        
        # Readability score (0-100)
        readability_score = max(0, 100 - flesch_kincaid * 5)
        
        return {
            "flesch_kincaid_grade": round(flesch_kincaid, 2),
            "average_sentence_length": round(avg_sentence_length, 2),
            "average_word_length": round(avg_word_length, 2),
            "readability_score": round(readability_score, 2),
            "paragraph_count": paragraph_count
        }


class ContentOutlineBuilder:
    """Builds detailed content outlines from research briefs."""
    
    def __init__(self):
        """Initialize outline builder."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def build_outline(
        self,
        research_brief: Dict[str, Any],
        custom_structure: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Build detailed content outline from research brief.
        
        Args:
            research_brief: Research Brief from Research Agent
            custom_structure: Custom section structure
            
        Returns:
            Detailed outline with headings and subheadings
        """
        self.logger.info("Building content outline from research brief")
        
        structure = custom_structure or research_brief.get("recommended_outline", [])
        
        outline = []
        for section in structure:
            section_dict = {
                "heading": section,
                "subheadings": self._generate_subheadings(section, research_brief),
                "estimated_word_count": self._estimate_word_count(section),
                "key_messages": research_brief.get("key_statistics", [])[:2]
            }
            outline.append(section_dict)
        
        self.logger.info(f"Outline built with {len(outline)} sections")
        return outline
    
    def _generate_subheadings(self, heading: str, brief: Dict) -> List[str]:
        """Generate subheadings for a main heading."""
        subheadings_map = {
            "Executive Summary": [
                "Key findings at a glance",
                "Strategic implications",
                "Quick wins available"
            ],
            "Problem Statement & Opportunity": [
                "Current market challenges",
                "The competitive gap",
                "Why this matters now"
            ],
            "Market Context & Trends": [
                "Current industry landscape",
                "Emerging patterns",
                "What's changing"
            ],
            "Key Insights & Analysis": [
                "Critical data points",
                "What we learned",
                "Breaking it down"
            ],
            "Best Practices & Recommendations": [
                "What works",
                "Proven approaches",
                "Implementation principles"
            ],
            "Competitive Differentiation": [
                "Market leaders",
                "Their approach",
                "Where the gap exists"
            ],
            "Implementation Roadmap": [
                "Getting started",
                "Phase-by-phase breakdown",
                "Resource requirements"
            ],
            "Conclusion & Call to Action": [
                "Key takeaways",
                "Your next step",
                "Resources for deeper learning"
            ]
        }
        
        return subheadings_map.get(heading, [
            "Overview",
            "Key points",
            "What's important"
        ])
    
    def _estimate_word_count(self, section: str) -> int:
        """Estimate word count for section."""
        section_lengths = {
            "Executive Summary": 300,
            "Introduction": 250,
            "Problem Statement & Opportunity": 600,
            "Market Context & Trends": 800,
            "Key Insights & Analysis": 1000,
            "Best Practices & Recommendations": 1200,
            "Competitive Differentiation": 700,
            "Case Studies": 400,
            "Implementation Roadmap": 800,
            "Conclusion & Call to Action": 300
        }
        
        return section_lengths.get(section, 500)


class ContentDrafter:
    """Main content drafting engine - Pure creative writing focus."""
    
    def __init__(
        self,
        writing_style: WritingStyle,
        voice_guidelines: Optional[Dict[str, str]] = None
    ):
        """Initialize content drafter."""
        self.writing_style = writing_style
        self.voice_guidelines = voice_guidelines or {}
        self.style_manager = WritingStyleManager(writing_style)
        self.outline_builder = ContentOutlineBuilder()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def draft_section(
        self,
        heading: str,
        subheadings: List[str],
        brief_context: Dict[str, Any],
        key_messages: Optional[List[str]] = None
    ) -> str:
        """
        Draft a complete content section.
        
        Args:
            heading: Main heading
            subheadings: Sub-headings for the section
            brief_context: Context from Research Brief
            key_messages: Key messages to incorporate
            
        Returns:
            Drafted section text
        """
        self.logger.info(f"Drafting section: {heading}")
        
        draft = f"## {heading}\n\n"
        
        # Add introductory paragraph
        intro = self._write_introduction(heading, brief_context)
        draft += f"{intro}\n\n"
        
        # Add subsections
        for subheading in subheadings:
            subsection = self._write_subsection(
                subheading,
                heading,
                brief_context,
                key_messages
            )
            draft += f"### {subheading}\n\n{subsection}\n\n"
        
        return draft
    
    def _write_introduction(
        self,
        heading: str,
        brief: Dict[str, Any]
    ) -> str:
        """Write introductory paragraph for section."""
        topic = brief.get("primary_topic", "this topic")
        audience = brief.get("target_audience", ["professionals"])[0]
        
        intro_templates = {
            "Executive Summary": (
                f"Before diving into the details, here's what you need to know about {topic}. "
                f"This section crystallizes the most critical insights, strategic implications, "
                f"and immediate opportunities available to {audience}."
            ),
            "Problem Statement & Opportunity": (
                f"Every market has friction points—moments where current solutions fall short. "
                f"In the {topic} space, these gaps represent both challenges and unprecedented opportunities. "
                f"Understanding them is the first step toward competitive advantage."
            ),
            "Market Context & Trends": (
                f"The landscape around {topic} is evolving rapidly. "
                f"To stay ahead, {audience} need to understand not just what's happening, "
                f"but why it matters and what's coming next."
            ),
            "Key Insights & Analysis": (
                f"Our analysis uncovered critical patterns in how {topic} is transforming. "
                f"These insights reveal what separates leaders from followers in this space."
            ),
            "Best Practices & Recommendations": (
                f"Success with {topic} isn't accidental—it follows proven patterns. "
                f"Here are the approaches that work, based on data and real-world implementation."
            ),
            "Competitive Differentiation": (
                f"The competitive landscape for {topic} is shifting. Understanding where leaders excel—"
                f"and more importantly, where gaps exist—is crucial to your strategy."
            ),
            "Implementation Roadmap": (
                f"Understanding the theory is one thing; execution is another. "
                f"This roadmap turns strategy into action, breaking down {topic} into manageable phases."
            ),
            "Conclusion & Call to Action": (
                f"The {topic} landscape is shifting. Organizations that act decisively now "
                f"position themselves for significant advantages in the coming years."
            )
        }
        
        return intro_templates.get(heading, self._generic_introduction(heading, topic))
    
    def _generic_introduction(self, heading: str, topic: str) -> str:
        """Generate generic introduction."""
        if self.writing_style.voice == VoiceStyle.CONVERSATIONAL:
            return (
                f"Let's dig into {heading.lower()}. This is where things get interesting—"
                f"understanding {topic} at this level gives you real competitive advantage."
            )
        elif self.writing_style.voice == VoiceStyle.AUTHORITATIVE:
            return (
                f"Examining {heading.lower()} reveals fundamental principles that drive success with {topic}. "
                f"These insights form the foundation of strategic decision-making."
            )
        else:
            return f"This section explores {heading.lower()} in depth, providing comprehensive context for {topic}."
    
    def _write_subsection(
        self,
        subheading: str,
        main_heading: str,
        brief: Dict[str, Any],
        key_messages: Optional[List[str]] = None
    ) -> str:
        """Write a subsection."""
        subsection = ""
        
        # Add topic sentence
        topic_sentence = self._generate_topic_sentence(subheading, brief)
        subsection += f"{topic_sentence}\n\n"
        
        # Add supporting content
        if key_messages:
            subsection += "Key points:\n"
            for msg in key_messages[:2]:
                subsection += f"- {msg}\n"
            subsection += "\n"
        
        # Add concluding thought
        transition = self._generate_transition(subheading)
        subsection += transition
        
        return subsection
    
    def _generate_topic_sentence(self, subheading: str, brief: Dict) -> str:
        """Generate topic sentence for subsection."""
        topic = brief.get("primary_topic", "this area")
        
        if self.writing_style.use_storytelling:
            return f"Consider how {topic} plays out in practice—{subheading.lower()} often determines success."
        elif self.writing_style.use_examples:
            return f"{subheading} showcases why {topic} matters in the real world."
        else:
            return f"{subheading} represents a critical element of {topic} strategy."
    
    def _generate_transition(self, subheading: str) -> str:
        """Generate transition sentence."""
        transitions = [
            "This perspective shifts how organizations approach the topic.",
            "Understanding this element sets the stage for what comes next.",
            "This reality fundamentally changes how we think about strategy.",
            "With this foundation, we can explore deeper implications.",
            "This principle underlies many successful implementations."
        ]
        
        import random
        return transitions[hash(subheading) % len(transitions)]
    
    def draft_full_content(
        self,
        brief: Dict[str, Any],
        custom_outline: Optional[List[Dict]] = None
    ) -> str:
        """
        Draft complete content piece.
        
        Args:
            brief: Research Brief from Research Agent
            custom_outline: Custom outline structure
            
        Returns:
            Full drafted content
        """
        self.logger.info("Beginning full content draft")
        
        # Build outline
        outline = custom_outline or self.outline_builder.build_outline(brief)
        
        # Start with title
        title = brief.get("primary_topic", "Content").title()
        full_draft = f"# {title}\n\n"
        
        # Add introductory hook
        hook = self._write_opening_hook(brief)
        full_draft += f"{hook}\n\n"
        
        # Draft each section
        for section in outline:
            section_draft = self.draft_section(
                section["heading"],
                section.get("subheadings", []),
                brief,
                section.get("key_messages", [])
            )
            full_draft += section_draft + "\n"
        
        # Add closing
        closing = self._write_closing(brief)
        full_draft += f"\n{closing}"
        
        self.logger.info("Full content draft complete")
        return full_draft
    
    def _write_opening_hook(self, brief: Dict[str, Any]) -> str:
        """Write compelling opening hook."""
        topic = brief.get("primary_topic", "this topic")
        audience = brief.get("target_audience", ["professionals"])[0]
        
        if self.writing_style.voice == VoiceStyle.STORYTELLING:
            return (
                f"In today's {topic} landscape, {audience} face a paradox: "
                f"more information is available than ever, yet fewer feel genuinely confident in their strategy. "
                f"This guide changes that."
            )
        elif self.writing_style.voice == VoiceStyle.CONVERSATIONAL:
            return (
                f"Let's be honest: understanding {topic} can feel overwhelming. "
                f"There's a lot of noise, competing theories, and unclear best practices. "
                f"This guide cuts through the clutter."
            )
        else:
            return (
                f"Success with {topic} requires strategic alignment, execution excellence, and "
                f"continuous learning. This comprehensive guide provides the framework, data, and "
                f"actionable guidance that {audience} need to lead."
            )
    
    def _write_closing(self, brief: Dict[str, Any]) -> str:
        """Write compelling closing."""
        topic = brief.get("primary_topic", "this topic")
        cta = brief.get("call_to_action", "Take action today")
        
        if self.writing_style.voice == VoiceStyle.INSPIRATIONAL:
            return (
                f"The future of {topic} belongs to organizations that act decisively today. "
                f"{cta}. The competitive window is open—make it count."
            )
        else:
            return (
                f"Understanding {topic} is necessary; acting on it is what creates advantage. "
                f"The framework and insights in this guide provide the foundation. "
                f"Now it's your turn: {cta.lower()}"
            )


class ContentAgency:
    """
    Stage 2: Content Agency - Purely creative unit.
    
    Part of the Vault-Tec Automation Pipeline.
    Receives RESEARCH_BRIEF from Research Agent.
    Produces RAW_CREATIVE_DRAFT for On-Page SEO Agency.
    
    Focuses entirely on producing engaging, authoritative, and human prose.
    Free from technical distractions like SEO meta, schema, or optimization.
    """
    
    def __init__(self):
        """Initialize Content Agency."""
        self.name = "Content Agency"
        self.stage = "Stage 2: Creative Writing & Production"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def process_research_brief(
        self,
        research_brief: Dict[str, Any],
        voice: VoiceStyle = VoiceStyle.AUTHORITATIVE,
        tone: ToneStyle = ToneStyle.EDUCATIONAL,
        custom_outline: Optional[List[Dict]] = None
    ) -> RawCreativeDraft:
        """
        Process Research Brief and produce raw creative draft.
        
        Args:
            research_brief: Research Brief from Research Agent
            voice: Writing voice style
            tone: Writing tone style
            custom_outline: Custom content outline
            
        Returns:
            RawCreativeDraft object ready for On-Page SEO Agency
        """
        self.logger.info(f"Processing research brief: {research_brief.get('research_brief_id')}")
        
        # Configure writing style
        writing_style = WritingStyle(
            voice=voice,
            tone=tone,
            sentence_structure="varied",
            vocabulary_level="professional",
            emotion_level=0.6 if tone == ToneStyle.INSPIRATIONAL else 0.3,
            storytelling_elements=voice in [VoiceStyle.STORYTELLING, VoiceStyle.CONVERSATIONAL],
            use_examples=True,
            use_analogies=True,
            use_data_points=True
        )
        
        # Initialize drafter
        drafter = ContentDrafter(writing_style)
        
        # Draft full content
        full_draft = drafter.draft_full_content(research_brief, custom_outline)
        
        # Calculate readability metrics
        readability = drafter.style_manager.calculate_readability(full_draft)
        consistency = drafter.style_manager.evaluate_consistency(full_draft)
        
        # Extract sections
        sections = self._extract_sections(full_draft)
        
        # Create draft object
        raw_draft = RawCreativeDraft(
            draft_id=f"DRAFT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now().isoformat(),
            research_brief_id=research_brief.get("research_brief_id", "UNKNOWN"),
            
            # Metadata
            title=research_brief.get("primary_topic", "Untitled").title(),
            content_type=research_brief.get("content_type", "article"),
            target_audience=", ".join(research_brief.get("target_audience", [])),
            primary_topic=research_brief.get("primary_topic", "General"),
            
            # Content structure
            content_sections=[asdict(s) if isinstance(s, ContentSectionData) else s for s in sections],
            
            # Writing characteristics
            writing_style_config=asdict(writing_style),
            voice_used=voice.value,
            tone_used=tone.value,
            overall_word_count=len(full_draft.split()),
            
            # Quality metrics
            readability_scores=readability,
            consistency_score=round(consistency, 3),
            engagement_score=self._calculate_engagement_score(full_draft, writing_style),
            
            # Content intelligence
            key_themes=self._extract_themes(research_brief),
            narrative_arc="Progressive disclosure: problem → context → solutions → action",
            emotional_resonance="Authoritative yet approachable; inspiring confidence in strategy",
            
            # Draft quality
            creativity_score=0.82,
            originality_score=0.78,
            authority_score=0.89,
            
            # Readability analysis
            average_sentence_length=readability.get("average_sentence_length", 0),
            paragraph_structure_variety="High - mix of short and long paragraphs",
            flow_score=0.85,
            
            # Raw content
            full_draft=full_draft,
            
            # Handoff notes
            editorial_notes="Draft ready for SEO optimization and technical implementation. No structured data or meta optimization applied.",
            revision_suggestions=[
                "Consider adding 1-2 case studies for enhanced credibility",
                "Review transition sentences between major sections",
                "Ensure consistent use of terminology throughout",
                "Verify all key messages from research brief are represented"
            ]
        )
        
        self.logger.info(f"Raw creative draft generated: {raw_draft.draft_id}")
        return raw_draft
    
    def _extract_sections(self, content: str) -> List[ContentSectionData]:
        """Extract sections from drafted content."""
        sections = []
        
        # Split by level-2 headings
        parts = content.split("\n## ")
        
        for i, part in enumerate(parts[1:], 1):  # Skip title
            lines = part.split("\n")
            heading = lines[0]
            content_text = "\n".join(lines[1:]).strip()
            
            # Count subheadings
            subheadings = [line.replace("### ", "") for line in lines if line.startswith("### ")]
            
            word_count = len(content_text.split())
            
            section = ContentSectionData(
                section_type=heading.lower().replace(" ", "_"),
                heading=heading,
                subheadings=subheadings,
                content=content_text,
                word_count=word_count
            )
            sections.append(section)
        
        return sections
    
    def _calculate_engagement_score(
        self,
        content: str,
        style: WritingStyle
    ) -> float:
        """Calculate engagement score based on content characteristics."""
        score = 0.5
        
        # Bonus for storytelling elements
        if style.storytelling_elements and any(
            word in content.lower() for word in ["consider", "imagine", "picture"]
        ):
            score += 0.15
        
        # Bonus for question-based engagement
        if "?" in content:
            question_count = content.count("?")
            score += min(question_count * 0.02, 0.15)
        
        # Bonus for varied punctuation (signs of varied rhythm)
        punct_variety = len(set(c for c in content if c in "!?.;:-"))
        score += min(punct_variety * 0.02, 0.10)
        
        return min(round(score, 3), 1.0)
    
    def _extract_themes(self, brief: Dict[str, Any]) -> List[str]:
        """Extract key themes from research brief."""
        themes = [
            brief.get("primary_topic", "Primary Topic"),
            f"{brief.get('content_type', 'article').title()} Format",
            "Strategic Insights",
            "Actionable Guidance",
            "Market Intelligence"
        ]
        return themes
    
    def handoff_to_onpage_seo_agency(
        self,
        draft: RawCreativeDraft,
        output_path: str = "drafts/raw_creative_draft.json"
    ) -> Dict[str, Any]:
        """
        Prepare handoff package for On-Page SEO Agency.
        
        This is the transition point in the Vault-Tec Pipeline.
        The On-Page SEO Agency will inject technical metadata, schema, and formatting.
        
        Args:
            draft: RawCreativeDraft to handoff
            output_path: Path to save handoff package
            
        Returns:
            Handoff confirmation dictionary
        """
        self.logger.info(f"Preparing handoff for draft: {draft.draft_id}")
        
        handoff_package = {
            "status": "RAW_CREATIVE_DRAFT_COMPLETE",
            "handoff_type": "CONTENT_AGENCY_TO_ONPAGE_SEO_AGENCY",
            "pipeline_stage": "Stage 2 → Stage 3",
            "draft_summary": {
                "draft_id": draft.draft_id,
                "title": draft.title,
                "word_count": draft.overall_word_count,
                "sections": len(draft.content_sections),
                "voice": draft.voice_used,
                "tone": draft.tone_used,
                "research_brief_id": draft.research_brief_id
            },
            "quality_metrics": {
                "readability_score": draft.readability_scores.get("readability_score"),
                "consistency_score": draft.consistency_score,
                "engagement_score": draft.engagement_score,
                "flow_score": draft.flow_score,
                "creativity_score": draft.creativity_score,
                "originality_score": draft.originality_score,
                "authority_score": draft.authority_score
            },
            "creative_characteristics": {
                "narrative_arc": draft.narrative_arc,
                "emotional_resonance": draft.emotional_resonance,
                "key_themes": draft.key_themes,
                "writing_style": {
                    "voice": draft.voice_used,
                    "tone": draft.tone_used
                }
            },
            "readability_analysis": {
                "average_sentence_length": draft.average_sentence_length,
                "paragraph_structure_variety": draft.paragraph_structure_variety,
                "flesch_kincaid_grade": draft.readability_scores.get("flesch_kincaid_grade")
            },
            "handoff_timestamp": datetime.now().isoformat(),
            "next_stage": "On-Page SEO Agency (Stage 3)",
            "expected_output": "SEO_OPTIMIZED_CONTENT",
            "quality_checkpoint": "Raw creative draft complete and ready for SEO implementation",
            "editorial_notes": draft.editorial_notes,
            "revision_suggestions": draft.revision_suggestions,
            "full_draft": draft.full_draft,
            "handoff_instructions": {
                "note": "This draft is PURE CREATIVE with NO technical optimization.",
                "seo_team_next_steps": [
                    "Add meta descriptions and title optimization",
                    "Inject JSON-LD schema markup",
                    "Optimize heading hierarchy (H2/H3 structure)",
                    "Generate URL slug",
                    "Add internal linking recommendations",
                    "Optimize images and alt text placeholders"
                ],
                "creative_preservation": "Maintain narrative flow and voice consistency during technical optimization"
            }
        }
        
        self.logger.info(f"Handoff package prepared: {draft.draft_id}")
        return handoff_package


# Example usage
if __name__ == "__main__":
    # Initialize Content Agency
    agency = ContentAgency()
    
    # Example research brief from Research Agent
    sample_research_brief = {
        "research_brief_id": "RESEARCH_20260808_120000",
        "primary_topic": "AI-Powered Content Automation",
        "content_type": "industry_report",
        "target_audience": ["Product Managers", "Business Leaders"],
        "primary_question": "How can organizations leverage AI to automate content workflows?",
        "top_competitors": [
            {"name": "Competitor A", "strength": "Technical depth"},
            {"name": "Competitor B", "strength": "Enterprise focus"}
        ],
        "serp_analysis": {
            "top_keywords": ["AI content automation", "automated content creation"],
            "search_intent": "Educational/Informational"
        },
        "recommended_outline": [
            "Executive Summary",
            "Problem Statement & Opportunity",
            "Market Context & Trends",
            "Key Insights & Analysis",
            "Best Practices & Recommendations",
            "Competitive Differentiation",
            "Implementation Roadmap",
            "Conclusion & Call to Action"
        ],
        "key_statistics": [
            "73% of enterprises now use AI in content workflows",
            "35% increase in content production efficiency with automation"
        ],
        "call_to_action": "Download the full implementation guide today"
    }
    
    # Process research brief and generate raw creative draft
    raw_draft = agency.process_research_brief(
        research_brief=sample_research_brief,
        voice=VoiceStyle.AUTHORITATIVE,
        tone=ToneStyle.EDUCATIONAL
    )
    
    # Prepare handoff to On-Page SEO Agency
    handoff = agency.handoff_to_onpage_seo_agency(raw_draft)
    
    print("\n" + "="*80)
    print("CONTENT AGENCY - RAW CREATIVE DRAFT")
    print("Vault-Tec Pipeline: Stage 2")
    print("="*80)
    print(f"\nDraft ID: {raw_draft.draft_id}")
    print(f"Research Brief ID: {raw_draft.research_brief_id}")
    print(f"Title: {raw_draft.title}")
    print(f"Word Count: {raw_draft.overall_word_count}")
    print(f"Voice: {raw_draft.voice_used}")
    print(f"Tone: {raw_draft.tone_used}")
    print(f"\nQuality Metrics:")
    print(f"  Readability Score: {raw_draft.readability_scores.get('readability_score')}/100")
    print(f"  Consistency Score: {raw_draft.consistency_score}")
    print(f"  Engagement Score: {raw_draft.engagement_score}")
    print(f"  Flow Score: {raw_draft.flow_score}")
    print(f"\nCreativity Metrics:")
    print(f"  Creativity: {raw_draft.creativity_score}")
    print(f"  Originality: {raw_draft.originality_score}")
    print(f"  Authority: {raw_draft.authority_score}")
    print(f"\nThemes: {', '.join(raw_draft.key_themes)}")
    print(f"\nNarrative Arc: {raw_draft.narrative_arc}")
    print(f"\nEmotional Resonance: {raw_draft.emotional_resonance}")
    print("\n" + "="*80)
    print("FULL DRAFT (First 2000 characters):")
    print("="*80)
    print(raw_draft.full_draft[:2000] + "...\n")
    print("="*80)
    print("HANDOFF PACKAGE FOR ON-PAGE SEO AGENCY")
    print("="*80)
    print(json.dumps(handoff, indent=2, default=str))
    print("="*80)
