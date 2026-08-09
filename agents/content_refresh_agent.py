"""
ContentRefreshAgent

Deterministic sitemap indexing + internal link target selection for Stage 3 SEO
without LLM/API calls.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple
from urllib import parse, request
import xml.etree.ElementTree as ET

from agents.ghost_controls import ghost_controls


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "what", "when", "where", "which", "with", "your",
}


@dataclass
class SitemapIndexEntry:
    url: str
    title: str
    primary_keywords: List[str]


class ContentRefreshAgent:
    def __init__(self) -> None:
        self.name = "ContentRefreshAgent"
        self.repo_root = Path(__file__).resolve().parents[1]

    def build_sitemap_index(
        self,
        sitemap_source: str = "",
        output_path: str = "",
        ghost_fixture_path: str = "",
        timeout_seconds: int = 8,
        write_index: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Build a sitemap index payload.

        When write_index=True:
        - writes to output_path if provided
        - otherwise writes to <repo_root>/sitemap_index.json
        """
        controls = ghost_controls()
        fixture_data: Dict[str, Any] = {}

        if controls["ghost_mode"]:
            fixture_candidate = (
                Path(ghost_fixture_path)
                if ghost_fixture_path
                else self.repo_root / "tests" / "fixtures" / "site_ops" / "content_refresh_fixture.json"
            )
            if fixture_candidate.exists():
                fixture_data = json.loads(fixture_candidate.read_text(encoding="utf-8"))

        if fixture_data.get("sitemap_urls"):
            urls = [str(u).strip() for u in fixture_data.get("sitemap_urls", []) if str(u).strip()]
        else:
            urls = self._read_urls_from_sitemap(sitemap_source, timeout_seconds)

        metadata = fixture_data.get("metadata_by_url", {}) if isinstance(fixture_data.get("metadata_by_url"), dict) else {}

        entries: List[SitemapIndexEntry] = []
        for url in self._dedupe(urls):
            md = metadata.get(url, {})
            title = str(md.get("title") or self._title_from_url(url))
            keywords = md.get("primary_keywords")
            if not isinstance(keywords, list) or not keywords:
                keywords = self._extract_keywords(title, max_keywords=5)
            entries.append(
                SitemapIndexEntry(
                    url=url,
                    title=title,
                    primary_keywords=[str(k).lower() for k in keywords if str(k).strip()],
                )
            )

        if write_index:
            output = Path(output_path) if output_path else self.repo_root / "sitemap_index.json"
            output.write_text(
                json.dumps([asdict(entry) for entry in entries], indent=2),
                encoding="utf-8",
            )

        return [asdict(entry) for entry in entries]

    def get_internal_link_targets(
        self,
        draft_text: str,
        index_path: str = "",
        index_entries: List[Dict[str, Any]] | None = None,
        max_targets: int = 8,
    ) -> List[Tuple[str, str]]:
        if index_entries is not None:
            entries = index_entries
        else:
            index_file = Path(index_path) if index_path else self.repo_root / "sitemap_index.json"
            if not index_file.exists():
                raise FileNotFoundError(f"Sitemap index not found: {index_file}")

            try:
                entries = json.loads(index_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return []

        draft_terms = set(self._extract_keywords(draft_text, max_keywords=300))
        candidates: List[Tuple[int, str, str]] = []

        for item in entries:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url", "")).strip()
            title = str(item.get("title", "")).strip()
            keywords = item.get("primary_keywords", [])
            if not url or not isinstance(keywords, list):
                continue

            normalized_keywords = [str(k).lower().strip() for k in keywords if str(k).strip()]
            overlap = [kw for kw in normalized_keywords if kw in draft_terms]
            if not overlap:
                continue

            overlap.sort(key=lambda value: (-len(value), value))
            anchor_text = overlap[0]
            score = len(overlap)
            candidates.append((score, anchor_text, url))

        candidates.sort(key=lambda candidate: (-candidate[0], candidate[2]))

        selected: List[Tuple[str, str]] = []
        seen_urls = set()
        for _score, anchor, url in candidates:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            selected.append((anchor, url))
            if len(selected) >= max_targets:
                break

        return selected

    def _read_urls_from_sitemap(self, sitemap_source: str, timeout_seconds: int) -> List[str]:
        if not sitemap_source:
            return []

        xml_text = self._read_text(sitemap_source, timeout_seconds)
        if not xml_text:
            return []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        urls: List[str] = []
        for elem in root.iter():
            if elem.tag.endswith("loc") and elem.text:
                value = elem.text.strip()
                if value:
                    urls.append(value)
        return urls

    def _read_text(self, source: str, timeout_seconds: int) -> str:
        if source.startswith(("http://", "https://")):
            req = request.Request(source, headers={"User-Agent": "content-refresh-agent/1.0"})
            try:
                with request.urlopen(req, timeout=timeout_seconds) as resp:
                    return resp.read().decode("utf-8", errors="ignore")
            except Exception:
                return ""

        path = Path(source)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _title_from_url(self, url: str) -> str:
        parsed = parse.urlparse(url)
        slug = (parsed.path or "/").strip("/")
        if not slug:
            return "Home"
        parts = [part for part in slug.split("/") if part]
        tail = parts[-1]
        text = tail.replace("-", " ").replace("_", " ")
        return " ".join(word.capitalize() for word in text.split())

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        tokens = [token.lower() for token in re.findall(r"[a-zA-Z0-9]+", text)]
        filtered = [
            token for token in tokens
            if len(token) >= 3 and token not in STOPWORDS and not token.isdigit()
        ]

        seen = set()
        keywords: List[str] = []
        for token in filtered:
            if token in seen:
                continue
            seen.add(token)
            keywords.append(token)
            if len(keywords) >= max_keywords:
                break
        return keywords

    @staticmethod
    def _dedupe(values: Sequence[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
