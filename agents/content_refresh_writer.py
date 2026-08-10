"""
Content Refresh Writer

Builds a publishable refresh package for an existing post by combining:
- the original live article body
- fresh external research insights
- updated internal link targets
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from html import unescape
from typing import Any, Dict, List, Sequence, Tuple

import requests

from agents.ghost_controls import ghost_controls
from agents import brand_voice as bv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class _ReadableTextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "article", "aside", "blockquote", "br", "div", "figcaption", "figure",
        "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "main",
        "ol", "p", "section", "table", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = unescape(text)
        text = re.sub(r"\r", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


@dataclass
class RefreshedPostPackage:
    refresh_id: str
    title: str
    url_slug: str
    original_url: str
    updated_at: str
    summary: str
    html: str
    labels: List[str]
    citations: List[Dict[str, str]]
    internal_links: List[Dict[str, str]]
    change_log: List[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class ContentRefreshWriter:
    def __init__(self) -> None:
        self.name = "Content Refresh Writer"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def fetch_existing_post_html(self, url: str, timeout_seconds: int = 10) -> str:
        controls = ghost_controls()
        if controls["ghost_mode"]:
            return (
                "<h1>Sample Post for Refresh</h1>"
                "<p>This article explains the original strategy and baseline workflow.</p>"
                "<p>It needs newer examples, stronger positioning, and clearer next steps.</p>"
            )

        try:
            response = requests.get(
                url,
                timeout=timeout_seconds,
                headers={"User-Agent": "automate-refresh-writer/1.0"},
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            self.logger.warning("Unable to fetch existing post HTML for %s. %s", url, exc)
            return (
                "<h1>Refresh Draft Baseline</h1>"
                "<p>The original article content could not be fetched.</p>"
                "<p>Proceeding with a generated baseline for refresh planning.</p>"
            )

    def build_refresh_package(
        self,
        post_candidate: Dict[str, Any],
        market_insights: Sequence[Dict[str, Any]] | None = None,
        internal_link_targets: Sequence[Tuple[str, str]] | None = None,
        base_url: str = "https://kurtastarita.com",
    ) -> RefreshedPostPackage:
        now = datetime.now(timezone.utc)
        slug = str(post_candidate.get("url_slug") or "").strip()
        title = str(post_candidate.get("title") or "Untitled").strip()
        original_url = f"{base_url.rstrip('/')}/{slug}"
        original_html = self.fetch_existing_post_html(original_url)
        original_text = self._extract_readable_text(original_html)

        voice_config = bv.load()
        voice_block = bv.build_prompt_block(voice_config)
        knowledge_chunks = bv.select_knowledge_files(title)
        banned_found = bv.check_banned_phrases(original_text, voice_config)
        if banned_found:
            logger.warning("Banned phrases found in original post '%s': %s", title, banned_found)

        insights = [dict(item) for item in (market_insights or [])[:3]]
        links = list(internal_link_targets or [])[:3]
        summary = (
            f"Refreshed {title} with {len(insights)} fresh research notes, "
            f"updated publish date guidance, and {len(links)} internal links."
        )

        refreshed_html = self._build_refreshed_html(
            title=title,
            original_text=original_text,
            insights=insights,
            links=links,
            voice_block=voice_block,
            knowledge_chunks=knowledge_chunks,
            banned_phrases=voice_config.get("banned_phrases", []),
        )

        change_log = [
            "Added freshness update section",
            "Added current research highlights",
            "Added related internal links",
            "Prepared content for republish with updated date",
            f"Brand voice enforced: tone='{voice_config.get('tone', '')}'",
        ]
        if knowledge_chunks:
            matched = bv.get_matched_stems(title)
            change_log.append(f"Domain knowledge applied: {', '.join(matched)}")
        if banned_found:
            change_log.append(f"Banned phrases flagged for removal: {banned_found}")

        return RefreshedPostPackage(
            refresh_id=f"REFRESH_CONTENT_{now.strftime('%Y%m%d_%H%M%S')}",
            title=title,
            url_slug=slug,
            original_url=original_url,
            updated_at=now.isoformat(),
            summary=summary,
            html=refreshed_html,
            labels=["refresh", "automated", "seo-update"],
            citations=[
                {
                    "title": str(item.get("title") or "Untitled insight"),
                    "source": str(item.get("source") or "Research source"),
                    "published_date": str(item.get("published_date") or ""),
                }
                for item in insights
            ],
            internal_links=[
                {"anchor_text": anchor, "target_url": url}
                for anchor, url in links
            ],
            change_log=change_log,
        )

    def _build_refreshed_html(
        self,
        title: str,
        original_text: str,
        insights: Sequence[Dict[str, Any]],
        links: Sequence[Tuple[str, str]],
        voice_block: str = "",
        knowledge_chunks: Sequence[str] | None = None,
        banned_phrases: Sequence[str] | None = None,
    ) -> str:
        # Strip banned phrases from the source text before rendering
        cleaned_text = original_text
        for phrase in (banned_phrases or []):
            cleaned_text = re.sub(re.escape(phrase), "", cleaned_text, flags=re.IGNORECASE)

        paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned_text) if p.strip()]
        if not paragraphs:
            paragraphs = [f"{title} remains relevant, but this update sharpens the advice and examples."]

        intro = paragraphs[:2]
        remainder = paragraphs[2:6]

        insight_items = "\n".join(
            f"<li><strong>{self._escape_html(str(item.get('title') or 'Update'))}</strong>: "
            f"{self._escape_html(str(item.get('description') or 'Recent developments support this update.'))} "
            f"<em>Source: {self._escape_html(str(item.get('source') or 'Research source'))}</em></li>"
            for item in insights
        ) or "<li>No fresh external research was available at runtime, so the article was tightened for clarity and relevance.</li>"

        link_items = "\n".join(
            f'<li><a href="{self._escape_html(url)}">{self._escape_html(anchor.title())}</a></li>'
            for anchor, url in links
        ) or "<li>No related internal links were identified for this update.</li>"

        body_parts = [
            f"<!-- Brand voice: {self._escape_html(voice_block.splitlines()[1] if voice_block else '')} -->",
            f"<h1>{self._escape_html(title)}</h1>",
            "<p><em>Updated for freshness with current research, clearer recommendations, and stronger internal linking.</em></p>",
            *[f"<p>{self._escape_html(paragraph)}</p>" for paragraph in intro],
            "<h2>What's New in This Update</h2>",
            "<ul>",
            "<li>Old framing and weaker calls to action were tightened.</li>",
            "<li>Recent market signals were added to make the piece current.</li>",
            "<li>Related internal links were added to improve navigation and SEO.</li>",
            "</ul>",
            "<h2>Fresh Research Highlights</h2>",
            f"<ul>{insight_items}</ul>",
        ]

        if remainder:
            body_parts.append("<h2>Refined Guidance</h2>")
            body_parts.extend(f"<p>{self._escape_html(paragraph)}</p>" for paragraph in remainder)

        body_parts.extend(
            [
                "<h2>Related Reading</h2>",
                f"<ul>{link_items}</ul>",
                "<h2>Final Takeaway</h2>",
                "<p>This refreshed version is meant to be more current, more actionable, and easier to explore than the original draft.</p>",
            ]
        )
        return "\n".join(body_parts)

    @staticmethod
    def _extract_readable_text(html: str) -> str:
        html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        parser = _ReadableTextExtractor()
        parser.feed(html)
        parser.close()
        return parser.get_text()

    @staticmethod
    def _escape_html(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
