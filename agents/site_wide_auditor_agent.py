"""
SiteWideAuditorAgent

Deterministic whole-site auditing for:
- sitemap URL discovery
- internal URL health checks (200 vs 4xx/5xx/unreachable)
- missing image alt attributes
- heading hierarchy warnings
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, parse, request
import xml.etree.ElementTree as ET

from agents.ghost_controls import ghost_controls


@dataclass
class SiteAuditReport:
    health_score: float
    broken_links: List[Dict[str, Any]] = field(default_factory=list)
    missing_alt_urls: List[str] = field(default_factory=list)
    structural_warnings: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class _AuditHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.missing_alt_count = 0
        self.heading_levels: List[int] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag_lower == "img":
            if "alt" not in attrs_dict or not attrs_dict["alt"].strip():
                self.missing_alt_count += 1
            return

        if tag_lower in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_levels.append(int(tag_lower[1]))


class SiteWideAuditorAgent:
    def __init__(self) -> None:
        self.name = "SiteWideAuditorAgent"
        self.repo_root = Path(__file__).resolve().parents[1]
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def audit_site(
        self,
        sitemap_source: str = "",
        base_domain: str = "",
        timeout_seconds: int = 8,
        ghost_fixture_path: str = "",
    ) -> SiteAuditReport:
        controls = ghost_controls()
        fixture_data: Dict[str, Any] = {}

        if controls["ghost_mode"]:
            fixture_candidate = (
                Path(ghost_fixture_path)
                if ghost_fixture_path
                else self.repo_root / "tests" / "fixtures" / "site_ops" / "site_wide_auditor_fixture.json"
            )
            if fixture_candidate.exists():
                fixture_data = json.loads(fixture_candidate.read_text(encoding="utf-8"))

        urls = self._resolve_urls(sitemap_source, fixture_data, timeout_seconds)
        if not urls:
            return SiteAuditReport(
                health_score=0.0,
                structural_warnings=[{"url": "site", "warnings": ["No URLs discovered from sitemap/fixture."]}],
            )

        inferred_domain = base_domain.strip() or parse.urlparse(urls[0]).netloc
        internal_urls = [u for u in urls if self._is_internal(u, inferred_domain)]

        broken_links: List[Dict[str, Any]] = []
        missing_alt_urls: List[str] = []
        structural_warnings: List[Dict[str, Any]] = []

        fixture_pages = fixture_data.get("pages", {}) if isinstance(fixture_data.get("pages"), dict) else {}

        for url in internal_urls:
            status, html = self._fetch_url(url, timeout_seconds, fixture_pages)

            if status < 200 or status >= 400:
                link_error = {"url": url, "status_code": status}
                if status == -1:
                    link_error["error"] = "unreachable"
                broken_links.append(link_error)

            if html:
                parser = _AuditHTMLParser()
                parser.feed(html)
                parser.close()

                if parser.missing_alt_count > 0:
                    missing_alt_urls.append(url)

                warnings = self._heading_warnings(parser.heading_levels)
                if warnings:
                    structural_warnings.append({"url": url, "warnings": warnings})

        health_score = self._calculate_health_score(
            len(internal_urls),
            len(broken_links),
            len(missing_alt_urls),
            len(structural_warnings),
        )

        return SiteAuditReport(
            health_score=health_score,
            broken_links=broken_links,
            missing_alt_urls=sorted(set(missing_alt_urls)),
            structural_warnings=structural_warnings,
        )

    def _resolve_urls(
        self,
        sitemap_source: str,
        fixture_data: Dict[str, Any],
        timeout_seconds: int,
    ) -> List[str]:
        if fixture_data.get("sitemap_urls"):
            return self._dedupe([str(u).strip() for u in fixture_data.get("sitemap_urls", []) if str(u).strip()])

        if not sitemap_source:
            return []

        xml_text = self._read_text(sitemap_source, timeout_seconds)
        if not xml_text:
            return []

        return self._parse_sitemap_xml(xml_text)

    def _read_text(self, source: str, timeout_seconds: int) -> str:
        if source.startswith(("http://", "https://")):
            req = request.Request(source, headers={"User-Agent": "site-wide-auditor/1.0"})
            try:
                with request.urlopen(req, timeout=timeout_seconds) as resp:
                    return resp.read().decode("utf-8", errors="ignore")
            except (error.URLError, TimeoutError, ValueError) as exc:
                self.logger.warning("Unable to read source %s. %s", source, exc)
                return ""

        path = Path(source)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _parse_sitemap_xml(self, xml_text: str) -> List[str]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        urls: List[str] = []
        for elem in root.iter():
            if elem.tag.endswith("loc") and elem.text:
                url = elem.text.strip()
                if url:
                    urls.append(url)
        return self._dedupe(urls)

    def _is_internal(self, url: str, domain: str) -> bool:
        parsed = parse.urlparse(url)
        if not parsed.netloc:
            return True
        return parsed.netloc == domain

    def _fetch_url(
        self,
        url: str,
        timeout_seconds: int,
        fixture_pages: Dict[str, Dict[str, Any]],
    ) -> Tuple[int, str]:
        if url in fixture_pages:
            payload = fixture_pages[url]
            return int(payload.get("status", 0)), str(payload.get("html", ""))

        req = request.Request(url, headers={"User-Agent": "site-wide-auditor/1.0"})
        try:
            with request.urlopen(req, timeout=timeout_seconds) as resp:
                status = int(getattr(resp, "status", resp.getcode()))
                content_type = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8", errors="ignore")
                if "text/html" in content_type or "<html" in body.lower():
                    return status, body
                return status, ""
        except error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="ignore")
            except OSError:
                body = ""
            return int(exc.code), body
        except (error.URLError, TimeoutError, ValueError) as exc:
            self.logger.warning("Unable to fetch URL %s. %s", url, exc)
            return -1, ""

    def _heading_warnings(self, levels: List[int]) -> List[str]:
        warnings: List[str] = []
        if not levels:
            warnings.append("No heading tags found.")
            return warnings

        if levels[0] != 1:
            warnings.append(f"First heading should be H1, found H{levels[0]}.")

        h1_count = sum(1 for level in levels if level == 1)
        if h1_count != 1:
            warnings.append(f"Expected exactly one H1, found {h1_count}.")

        prev = levels[0]
        for level in levels[1:]:
            if level - prev > 1:
                warnings.append(f"Heading jump detected: H{prev} -> H{level}.")
            prev = level

        return warnings

    def _calculate_health_score(
        self,
        total_urls: int,
        broken_count: int,
        missing_alt_count: int,
        structural_warning_count: int,
    ) -> float:
        if total_urls <= 0:
            return 0.0

        broken_rate = broken_count / total_urls
        missing_alt_rate = missing_alt_count / total_urls
        structural_rate = structural_warning_count / total_urls

        weighted_risk = (0.60 * broken_rate) + (0.25 * missing_alt_rate) + (0.15 * structural_rate)
        return round(max(0.0, 100.0 * (1.0 - weighted_risk)), 2)

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
