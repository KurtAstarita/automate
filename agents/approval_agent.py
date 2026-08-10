"""
Approval Agent - Stage 5: Human CEO Review & GitHub Issue-Based Approval
Responsibility: Create GitHub approval issue, monitor for CEO decision, trigger deployment.

Execution: Takes Terminal Briefing from The Overseer and creates a GitHub Issue
for CEO review. Monitors for approval signal (comment, label, reaction).
On approval, triggers GitHub Actions deployment workflow.

Handoff Output: DEPLOYMENT_AUTHORIZED signal to GitHub Actions pipeline.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from agents.ghost_controls import side_effects_allowed
from agents import brand_voice as bv
from agents.issue_packets import embed_packet


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval status states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class ApprovalMethod(Enum):
    """Methods for CEO to approve."""
    COMMENT_SLASH_COMMAND = "/approve"
    COMMENT_DEPLOY = "/publish"
    LABEL_APPROVED = "approved"
    REACTION_CHECKMARK = "✅"
    REACTION_THUMBSUP = "+1"


@dataclass
class ApprovalIssuePayload:
    """Payload for creating GitHub approval issue."""
    title: str
    body: str
    labels: List[str]
    assignee: str = "KurtAstarita"
    milestone: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON format."""
        return json.dumps(asdict(self), indent=2)


@dataclass
class ApprovalDecision:
    """Record of CEO approval decision."""
    decision_id: str
    briefing_id: str
    github_issue_number: int
    github_issue_url: str
    
    # Decision details
    status: str  # approved, rejected, revision_requested
    approved_by: str  # GitHub username
    approval_timestamp: str
    approval_method: str  # comment, label, reaction
    approval_comment: Optional[str] = None
    
    # Action tracking
    action_taken: str = ""  # deployment_triggered, revision_scheduled
    action_timestamp: str = ""
    github_actions_workflow_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON format."""
        return json.dumps(asdict(self), indent=2)


class GitHubApprovalIssueBuilder:
    """Builds formatted GitHub approval issues."""
    
    def __init__(self):
        """Initialize issue builder."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def build_approval_issue(
        self,
        terminal_briefing: Dict[str, Any],
        repository: str = "KurtAstarita/automate"
    ) -> ApprovalIssuePayload:
        """
        Build formatted GitHub approval issue.
        
        Args:
            terminal_briefing: Terminal briefing from The Overseer
            repository: GitHub repository (owner/repo)
            
        Returns:
            ApprovalIssuePayload ready for GitHub API
        """
        self.logger.info("Building GitHub approval issue...")
        
        briefing = terminal_briefing
        content_title = briefing.get("content_title", "Untitled")
        quality_score = briefing.get("total_quality_score", 0)
        production_ready = briefing.get("production_ready", False)
        risk_level = briefing.get("risk_level", "unknown")
        
        # Build title
        status_emoji = "✅" if production_ready else "⚠️"
        title = f"[CONTENT APPROVAL] {status_emoji} {content_title}"
        
        # Build issue body with all critical info
        body = self._build_issue_body(briefing)
        
        # Set labels
        labels = ["content-approval", f"status-{risk_level}"]
        if production_ready:
            labels.append("ready-to-publish")
        else:
            labels.append("requires-attention")
        
        issue_payload = ApprovalIssuePayload(
            title=title,
            body=body,
            labels=labels,
            assignee="KurtAstarita"
        )
        
        self.logger.info(f"Approval issue built: {title}")
        return issue_payload
    
    def _build_issue_body(self, briefing: Dict[str, Any]) -> str:
        """Build detailed GitHub issue body."""
        
        critical_metrics = briefing.get("critical_metrics") or {}
        compliance = briefing.get("compliance_checks", {})
        risks = briefing.get("risks_identified", [])
        production_ready = briefing.get("production_ready", False)
        
        body = f"""# Content Approval Request: {briefing.get('content_title', 'Untitled')}

**Content URL:** `{briefing.get('content_url', 'N/A')}`

---

## 🎯 Executive Summary

{briefing.get('executive_summary', 'No summary available')}

---

## 📊 Quality Metrics Dashboard

| Metric | Score | Status |
|--------|-------|--------|
| **Overall Quality** | {critical_metrics.get('quality_score', 'N/A')}/100 | {'✅ PASS' if critical_metrics.get('quality_score', 0) >= 75 else '⚠️ CHECK'} |
| **SEO Score** | {critical_metrics.get('seo_score', 'N/A')}/100 | {'✅ OPTIMIZED' if critical_metrics.get('seo_score', 0) >= 75 else '⚠️ REVIEW'} |
| **Risk Level** | **{critical_metrics.get('risk_level', 'unknown').upper()}** | {'🟢 LOW' if critical_metrics.get('risk_level') == 'low' else '🟡 MEDIUM' if critical_metrics.get('risk_level') == 'medium' else '🔴 HIGH'} |
| **Production Ready** | {'✅ YES' if production_ready else '❌ NO'} | {'🚀 READY' if production_ready else '⏸️ REVIEW NEEDED'} |
| **Word Count** | {critical_metrics.get('word_count', 'N/A'):,} words | - |
| **Reading Time** | {critical_metrics.get('reading_time', 'N/A')} min | - |

---

## 📋 Phase Reports

### Research Phase
- **Topic:** {briefing.get('research_phase', {}).get('primary_topic', 'N/A')}
- **Keywords:** {', '.join(briefing.get('research_phase', {}).get('primary_keywords', [])) or 'N/A'}
- **Market Trends:** {briefing.get('research_phase', {}).get('market_trends_count', 0)} identified
- **Key Statistics:** {briefing.get('research_phase', {}).get('key_statistics_count', 0)} compiled

### Creative Phase
- **Title:** {briefing.get('creative_phase', {}).get('title', 'N/A')}
- **Voice:** {briefing.get('creative_phase', {}).get('voice_used', 'N/A')}
- **Tone:** {briefing.get('creative_phase', {}).get('tone_used', 'N/A')}
- **Engagement:** {round(briefing.get('creative_phase', {}).get('engagement_score', 0) * 100, 1)}%
- **Creativity:** {round(briefing.get('creative_phase', {}).get('creativity_score', 0) * 100, 1)}%

### Technical Phase
- **URL Slug:** `/{briefing.get('technical_phase', {}).get('url_slug', 'N/A')}`
- **SEO Score:** {briefing.get('technical_phase', {}).get('seo_score', 'N/A')}/100
- **Headings:** {briefing.get('technical_phase', {}).get('heading_count', 0)} total ({briefing.get('technical_phase', {}).get('optimized_heading_count', 0)} optimized)
- **Internal Links:** {briefing.get('technical_phase', {}).get('internal_link_count', 0)}
- **Schema:** {'✅ Configured' if briefing.get('technical_phase', {}).get('schema_markup_configured') else '❌ Missing'}

---

## ✅ Compliance Checklist

| Check | Status |
|-------|--------|
| Creative Integrity | {'✅ PASS' if compliance.get('creative_integrity_preserved') else '❌ FAIL'} |
| Keyword Density | {'✅ PASS' if compliance.get('keyword_density_optimal') else '❌ FAIL'} |
| Meta Tags Complete | {'✅ PASS' if compliance.get('meta_tags_complete') else '❌ FAIL'} |
| Schema Markup Valid | {'✅ PASS' if compliance.get('schema_valid') else '❌ FAIL'} |
| Heading Hierarchy | {'✅ PASS' if compliance.get('heading_hierarchy_valid') else '❌ FAIL'} |
| Links Functional | {'✅ PASS' if compliance.get('links_functional') else '❌ FAIL'} |
| No Critical Warnings | {'✅ PASS' if compliance.get('no_critical_warnings') else '❌ FAIL'} |

**Overall Compliance:** {round(compliance.get('overall_compliance_score', 0) * 100, 1)}%

---

## 🔍 Quality Checks Summary

"""
        
        quality_checks = briefing.get("quality_checks", [])
        passed = sum(1 for c in quality_checks if c.get("level") == "pass")
        warnings = sum(1 for c in quality_checks if c.get("level") == "warning")
        critical = sum(1 for c in quality_checks if c.get("level") == "critical")
        
        body += f"- ✅ **{passed} Passed**\n"
        body += f"- ⚠️ **{warnings} Warnings**\n"
        body += f"- 🔴 **{critical} Critical**\n\n"
        
        if critical > 0:
            body += "### Critical Issues (Must Address)\n"
            for check in quality_checks:
                if check.get("level") == "critical":
                    body += f"- **{check.get('check_name')}:** {check.get('message')}\n"
            body += "\n"
        
        if warnings > 0:
            body += "### Warnings (Review)\n"
            for check in quality_checks:
                if check.get("level") == "warning":
                    body += f"- **{check.get('check_name')}:** {check.get('message')}\n"
            body += "\n"
        
        # Risk assessment
        body += """---

## ⚠️ Risk Assessment

"""
        
        if risks:
            body += f"**Risk Level:** {critical_metrics.get('risk_level', 'unknown').upper()}\n\n"
            body += "**Identified Risks:**\n"
            for risk in risks:
                body += f"- {risk}\n"
            body += "\n"
        else:
            body += "**Risk Level:** LOW\n\n**No identified risks.**\n\n"
        
        recommendations = briefing.get("recommendations", [])
        if recommendations:
            body += "**Recommendations:**\n"
            for rec in recommendations:
                body += f"- {rec}\n"
            body += "\n"
        
        # Approval instructions
        body += """---

## 🚀 Approval Instructions

**To APPROVE this content and publish immediately:**

Reply with one of:
- `/approve` — Publish as-is
- `/publish` — Publish as-is
- Add the label `approved`
- React with ✅

**To REQUEST REVISIONS:**

Reply with:
- `/revision <your notes>` — Send back for revision
- Add the label `needs-revision`

**To REJECT this content:**

Reply with:
- `/reject <reason>` — Reject publication
- Add the label `rejected`

---

## 📝 Briefing Details

**Briefing ID:** `{briefing.get('briefing_id', 'N/A')}`
**Created:** {briefing.get('dispatch_timestamp', 'N/A')}
**Pipeline Status:** {briefing.get('pipeline_status', 'N/A')}

---

## 🔗 Full Briefing Package

<details>
<summary><b>Full Terminal Briefing (Click to expand)</b></summary>

```json
{json.dumps({k: v for k, v in briefing.items() if k != 'content_payload'}, indent=2, default=str)}
```

</details>

---

**Auto-generated by Vault-Tec Pipeline**
*Stage 4 (The Overseer) → Stage 5 (CEO Approval)*
"""

        publish_payload = self._build_publish_payload(briefing)
        if publish_payload:
            body = embed_packet(body, "fresh_article", publish_payload)
        
        return body

    @staticmethod
    def _build_publish_payload(briefing: Dict[str, Any]) -> Dict[str, Any]:
        content_payload = briefing.get("content_payload")
        if not isinstance(content_payload, dict):
            return {}

        meta_tags = content_payload.get("meta_tags", {}) if isinstance(content_payload.get("meta_tags"), dict) else {}
        schema_markup = content_payload.get("schema_markup", {}) if isinstance(content_payload.get("schema_markup"), dict) else {}
        return {
            "operation": "create",
            "content_id": content_payload.get("content_id"),
            "briefing_id": briefing.get("briefing_id"),
            "approval_reference": briefing.get("briefing_id"),
            "title": content_payload.get("title"),
            "url_slug": content_payload.get("url_slug"),
            "html": content_payload.get("optimized_content_html"),
            "labels": list(meta_tags.get("keywords", []))[:10],
            "meta_tags": meta_tags,
            "schema_markup": schema_markup,
        }


class ApprovalAgent:
    """
    Stage 5: Approval Agent - Human CEO Review via GitHub Issues
    
    Part of the Vault-Tec Automation Pipeline.
    Receives TERMINAL_BRIEFING from The Overseer.
    Creates GitHub issue for CEO review.
    Monitors for approval decision.
    Produces DEPLOYMENT_AUTHORIZED signal on approval.
    
    This is where HUMAN intervention happens - you (Kurt) make the final call.
    """
    
    def __init__(self):
        """Initialize Approval Agent."""
        self.name = "Approval Agent"
        self.stage = "Stage 5: CEO Review & Approval"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.issue_builder = GitHubApprovalIssueBuilder()
    
    def create_approval_issue(
        self,
        terminal_briefing: Dict[str, Any],
        repository: str = "KurtAstarita/automate"
    ) -> ApprovalIssuePayload:
        """
        Create GitHub approval issue from terminal briefing.
        
        This is meant to be called by a GitHub Actions workflow or deployment script
        that will then call the GitHub API to create the actual issue.
        
        Args:
            terminal_briefing: Terminal briefing from The Overseer
            repository: GitHub repository (owner/repo)
            
        Returns:
            ApprovalIssuePayload ready to send to GitHub API
        """
        self.logger.info(f"Creating approval issue for: {terminal_briefing.get('content_title')}")
        
        issue_payload = self.issue_builder.build_approval_issue(
            terminal_briefing,
            repository
        )
        
        self.logger.info(f"Approval issue payload created and ready for GitHub API")
        return issue_payload
    
    def parse_approval_comment(
        self,
        comment_text: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse GitHub comment for approval and brand voice commands.

        Supported commands:
          /approve                       — Publish as-is
          /publish                       — Alias for approve
          /revision <notes>              — Send back for revision
          /reject <reason>               — Reject publication
          /style <text or example>       — Learn new style rule from text/example
          /remember <fact>               — Add a domain knowledge fact
          /ban "<phrase>"                — Add a banned phrase
          /tone <new tone description>   — Replace the tone string
          /punch <paragraph>             — Learn from a rewritten paragraph

        Returns:
            Tuple of (command: str, argument: str) or (None, None)
        """
        comment_lower = comment_text.lower().strip()

        # Approval commands
        if comment_lower.startswith("/approve"):
            return ("approve", None)
        elif comment_lower.startswith("/publish"):
            return ("publish", None)
        elif comment_lower.startswith("/revision"):
            parts = comment_text.split(" ", 1)
            revision_note = parts[1] if len(parts) > 1 else "Revision requested"
            return ("revision", revision_note)
        elif comment_lower.startswith("/reject"):
            parts = comment_text.split(" ", 1)
            reject_reason = parts[1] if len(parts) > 1 else "Rejected by CEO"
            return ("reject", reject_reason)

        # Brand voice learning commands
        elif comment_lower.startswith("/style "):
            parts = comment_text.split(" ", 1)
            return ("style", parts[1].strip() if len(parts) > 1 else "")
        elif comment_lower.startswith("/remember "):
            parts = comment_text.split(" ", 1)
            return ("remember", parts[1].strip() if len(parts) > 1 else "")
        elif comment_lower.startswith("/ban "):
            parts = comment_text.split(" ", 1)
            return ("ban", parts[1].strip() if len(parts) > 1 else "")
        elif comment_lower.startswith("/tone "):
            parts = comment_text.split(" ", 1)
            return ("tone", parts[1].strip() if len(parts) > 1 else "")
        elif comment_lower.startswith("/punch "):
            parts = comment_text.split(" ", 1)
            return ("punch", parts[1].strip() if len(parts) > 1 else "")

        return (None, None)

    def process_brand_voice_command(
        self,
        command: str,
        argument: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a brand voice learning command and persist the update.

        In dry_run mode the config is not written to disk — safe for
        ghost/CI runs.

        Returns a dict describing what was done.
        """
        result: Dict[str, Any] = {
            "command": command,
            "argument": argument[:200] if argument else "",
            "persisted": False,
            "rules_added": [],
        }

        if not argument:
            result["error"] = "Empty argument — nothing to learn."
            return result

        if command == "style":
            # Distill concise rules from potentially long text (one-time cost)
            rules = bv.distill_style_rules(argument, max_rules=3)
            for rule in rules:
                if not dry_run:
                    bv.append_learned_feedback(rule)
            result["rules_added"] = rules
            result["persisted"] = not dry_run

        elif command == "remember":
            if not dry_run:
                bv.append_domain_knowledge(argument)
            result["rules_added"] = [argument]
            result["persisted"] = not dry_run

        elif command == "ban":
            if not dry_run:
                bv.append_banned_phrase(argument)
            result["rules_added"] = [argument]
            result["persisted"] = not dry_run

        elif command == "tone":
            if not dry_run:
                bv.update_tone(argument)
            result["rules_added"] = [argument]
            result["persisted"] = not dry_run

        elif command == "punch":
            # Learn style from a rewritten paragraph example
            rules = bv.distill_style_rules(argument, max_rules=2)
            for rule in rules:
                if not dry_run:
                    bv.append_learned_feedback(rule)
            result["rules_added"] = rules
            result["persisted"] = not dry_run

        else:
            result["error"] = f"Unknown brand voice command: {command}"

        if result["persisted"]:
            self.logger.info(
                "Brand voice updated via /%s: %s", command, result["rules_added"]
            )

        return result

    
    def process_approval_decision(
        self,
        briefing_id: str,
        github_issue_number: int,
        github_issue_url: str,
        approval_status: str,  # approved, rejected, revision_requested
        approved_by: str = "KurtAstarita",
        approval_method: str = "comment",
        approval_comment: Optional[str] = None
    ) -> ApprovalDecision:
        """
        Process CEO approval decision.
        
        Args:
            briefing_id: Briefing ID being approved
            github_issue_number: GitHub issue number
            github_issue_url: GitHub issue URL
            approval_status: Status of approval (approved/rejected/revision_requested)
            approved_by: GitHub username who approved
            approval_method: Method used (comment/label/reaction)
            approval_comment: Optional comment text
            
        Returns:
            ApprovalDecision object
        """
        self.logger.info(f"Processing approval decision: {approval_status}")
        
        # Determine action
        if approval_status == "approved":
            action = "deployment_triggered"
        elif approval_status == "revision_requested":
            action = "revision_scheduled"
        elif approval_status == "rejected":
            action = "publication_cancelled"
        else:
            action = "unknown"
        
        decision = ApprovalDecision(
            decision_id=f"APPROVAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            briefing_id=briefing_id,
            github_issue_number=github_issue_number,
            github_issue_url=github_issue_url,
            status=approval_status,
            approved_by=approved_by,
            approval_timestamp=datetime.now().isoformat(),
            approval_method=approval_method,
            approval_comment=approval_comment,
            action_taken=action,
            action_timestamp=datetime.now().isoformat()
        )
        
        self.logger.info(f"Approval decision processed: {decision.decision_id}")
        return decision
    
    def generate_deployment_signal(
        self,
        approval_decision: ApprovalDecision,
        content_id: str,
        content_url_slug: str
    ) -> Dict[str, Any]:
        """
        Generate deployment authorization signal for GitHub Actions.
        
        This is the output that triggers the deployment workflow.
        
        Args:
            approval_decision: Approval decision object
            content_id: Content ID to deploy
            content_url_slug: URL slug for the content
            
        Returns:
            Deployment signal dictionary
        """
        self.logger.info(f"Generating deployment signal: {approval_decision.decision_id}")

        if not side_effects_allowed():
            signal = {
                "deployment_authorized": False,
                "signal_type": "DEPLOYMENT_BLOCKED_DRY_RUN",
                "reason": "Side effects disabled by ghost-mode controls",
                "approval_decision": asdict(approval_decision),
                "timestamp": datetime.now().isoformat()
            }
            self.logger.info("Deployment blocked - ghost mode or dry run is active")
            return signal

        if approval_decision.status != "approved":
            signal = {
                "deployment_authorized": False,
                "signal_type": "DEPLOYMENT_CANCELLED",
                "reason": approval_decision.status,
                "approval_decision": asdict(approval_decision),
                "timestamp": datetime.now().isoformat()
            }
            self.logger.info("Deployment cancelled - not approved")
            return signal
        
        signal = {
            "deployment_authorized": True,
            "signal_type": "DEPLOYMENT_AUTHORIZED",
            "approval_decision_id": approval_decision.decision_id,
            "content_id": content_id,
            "content_url_slug": content_url_slug,
            "github_issue_number": approval_decision.github_issue_number,
            "github_issue_url": approval_decision.github_issue_url,
            "approved_by": approval_decision.approved_by,
            "approval_timestamp": approval_decision.approval_timestamp,
            "deployment_timestamp": datetime.now().isoformat(),
            "next_action": "TRIGGER_GITHUB_ACTIONS_DEPLOY",
            "github_actions_parameters": {
                "workflow": "deploy-content.yml",
                "content_id": content_id,
                "url_slug": content_url_slug,
                "approval_reference": approval_decision.decision_id
            },
            "approval_decision": asdict(approval_decision)
        }
        
        self.logger.info(f"Deployment signal authorized: {signal['signal_type']}")
        return signal
    
    def create_workflow_dispatch_payload(
        self,
        deployment_signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create GitHub Actions workflow dispatch payload.
        
        This payload can be used with GitHub's workflow_dispatch trigger
        to automatically start the deployment workflow.
        
        Args:
            deployment_signal: Deployment signal from generate_deployment_signal
            
        Returns:
            Workflow dispatch payload
        """
        self.logger.info("Creating GitHub Actions workflow dispatch payload")
        
        if not deployment_signal.get("deployment_authorized"):
            self.logger.warning("Deployment not authorized - cannot create dispatch payload")
            return {}
        
        payload = {
            "ref": "main",  # Branch to run workflow on
            "inputs": {
                "content_id": deployment_signal.get("content_id"),
                "url_slug": deployment_signal.get("content_url_slug"),
                "approval_reference": deployment_signal.get("approval_decision_id"),
                "approved_by": deployment_signal.get("approved_by"),
                "issue_number": str(deployment_signal.get("github_issue_number"))
            }
        }
        
        self.logger.info("Workflow dispatch payload created")
        return payload


# Example usage
if __name__ == "__main__":
    # Initialize Approval Agent
    approval_agent = ApprovalAgent()
    
    # Example terminal briefing from The Overseer
    sample_terminal_briefing = {
        "briefing_id": "BRIEFING_20260808_180000",
        "dispatch_timestamp": datetime.now().isoformat(),
        "pipeline_status": "complete",
        "content_title": "AI-Powered Content Automation",
        "content_url": "https://kurtastarita.com/ai-powered-content-automation",
        "target_audience": "Product Managers",
        "executive_summary": """✅ READY FOR PUBLICATION

CONTENT: AI-Powered Content Automation
URL: /ai-powered-content-automation

QUALITY METRICS:
- Overall Quality Score: 87.5/100
- Creative Engagement: 82.0%
- SEO Optimization: 87.5/100
- Content Word Count: 2,500 words
- Reading Time: 12 minutes

PRODUCTION STATUS:
✓ All systems green. Ready to deploy.

ACTION REQUIRED:
Click "APPROVE & PUBLISH" to deploy immediately.""",
        "critical_metrics": {
            "quality_score": 87.5,
            "seo_score": 87.5,
            "word_count": 2500,
            "reading_time": 12,
            "risk_level": "low",
            "production_ready": True
        },
        "research_phase": {
            "primary_topic": "AI-Powered Content Automation",
            "primary_keywords": ["AI content automation", "automated content creation"],
            "market_trends_count": 5,
            "key_statistics_count": 8
        },
        "creative_phase": {
            "title": "AI-Powered Content Automation",
            "voice_used": "authoritative",
            "tone_used": "educational",
            "engagement_score": 0.82,
            "creativity_score": 0.82
        },
        "technical_phase": {
            "url_slug": "ai-powered-content-automation",
            "seo_score": 87.5,
            "heading_count": 8,
            "optimized_heading_count": 7,
            "internal_link_count": 5,
            "schema_markup_configured": True
        },
        "total_quality_score": 87.5,
        "quality_checks": [
            {"check_name": "Meta Tags Quality", "level": "pass", "message": "All meta tags properly configured"},
            {"check_name": "Schema Markup", "level": "pass", "message": "JSON-LD schema valid"},
            {"check_name": "Heading Hierarchy", "level": "pass", "message": "Hierarchy valid: 1 H1, 2 H2s, 5 H3s"}
        ],
        "compliance_checks": {
            "creative_integrity_preserved": True,
            "keyword_density_optimal": True,
            "meta_tags_complete": True,
            "schema_valid": True,
            "heading_hierarchy_valid": True,
            "links_functional": True,
            "no_critical_warnings": True,
            "overall_compliance_score": 0.95
        },
        "risk_level": "low",
        "risks_identified": [],
        "recommendations": [
            "Review content on staging environment before publication",
            "Verify all links are functional"
        ],
        "production_ready": True
    }
    
    # Step 1: Create approval issue
    print("\n" + "="*80)
    print("APPROVAL AGENT - GITHUB ISSUE CREATION")
    print("Vault-Tec Pipeline: Stage 5")
    print("="*80)
    
    issue_payload = approval_agent.create_approval_issue(sample_terminal_briefing)
    
    print(f"\n✅ GitHub Issue Ready to Create:")
    print(f"\nTitle: {issue_payload.title}")
    print(f"Labels: {', '.join(issue_payload.labels)}")
    print(f"Assignee: {issue_payload.assignee}")
    print(f"\nIssue Body Preview (first 1000 chars):")
    print(issue_payload.body[:1000] + "...\n")
    
    # Step 2: Simulate approval decision
    print("="*80)
    print("SIMULATING CEO APPROVAL DECISION")
    print("="*80)
    
    approval_decision = approval_agent.process_approval_decision(
        briefing_id="BRIEFING_20260808_180000",
        github_issue_number=42,
        github_issue_url="https://github.com/KurtAstarita/automate/issues/42",
        approval_status="approved",
        approved_by="KurtAstarita",
        approval_method="comment",
        approval_comment="/approve"
    )
    
    print(f"\n✅ Approval Decision Recorded:")
    print(f"Decision ID: {approval_decision.decision_id}")
    print(f"Status: {approval_decision.status}")
    print(f"Issue: #{approval_decision.github_issue_number}")
    print(f"Approved By: @{approval_decision.approved_by}")
    print(f"Action: {approval_decision.action_taken}")
    
    # Step 3: Generate deployment signal
    print("\n" + "="*80)
    print("GENERATING DEPLOYMENT SIGNAL")
    print("="*80)
    
    deployment_signal = approval_agent.generate_deployment_signal(
        approval_decision,
        content_id="SEO_20260808_180000",
        content_url_slug="ai-powered-content-automation"
    )
    
    print(f"\n✅ Deployment Signal Generated:")
    print(f"Authorization: {deployment_signal['deployment_authorized']}")
    print(f"Signal Type: {deployment_signal['signal_type']}")
    print(f"Content ID: {deployment_signal['content_id']}")
    print(f"URL Slug: {deployment_signal['content_url_slug']}")
    
    # Step 4: Create workflow dispatch payload
    print("\n" + "="*80)
    print("GITHUB ACTIONS WORKFLOW DISPATCH")
    print("="*80)
    
    workflow_payload = approval_agent.create_workflow_dispatch_payload(deployment_signal)
    
    print(f"\n✅ Workflow Dispatch Payload Ready:")
    print(json.dumps(workflow_payload, indent=2))
    
    print("\n" + "="*80)
    print("FULL GITHUB ISSUE BODY")
    print("="*80)
    print(issue_payload.body)
    print("="*80)
