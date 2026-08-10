"""
brand_voice.py — Shared brand voice loader and updater.

Token-efficient design:
- brand_voice.json is always loaded (~100-200 tokens injected per run).
- config/knowledge/*.md files are loaded selectively by topic keyword match.
- Updates are atomic: read → mutate → write (no partial writes).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BRAND_VOICE_PATH = REPO_ROOT / "config" / "brand_voice.json"
KNOWLEDGE_DIR = REPO_ROOT / "config" / "knowledge"

_DEFAULTS: Dict[str, Any] = {
    "author": "Kurt",
    "tone": "Direct, conversational, engineering-focused, authoritative, zero fluff",
    "formatting_rules": [
        "Lead directly with core insights or solutions without generic setups",
        "Use practical examples and concrete technical details",
        "Maintain short, punchy paragraphs and scannable sections",
    ],
    "banned_phrases": [
        "In today's fast-paced digital world",
        "game-changer",
        "delve into",
        "seamlessly integrate",
    ],
    "domain_knowledge": [],
    "learned_style_feedback": [],
}

# Map topic keywords → knowledge file stems (stem must match config/knowledge/<stem>.md).
# Any .md file added to config/knowledge/ is also auto-discovered: its stem words
# (split on underscores) are used as implicit keywords so no manual entry is needed.
_TOPIC_KEYWORD_MAP: Dict[str, str] = {
    # training_regimen.md
    "training": "training_regimen",
    "workout": "training_regimen",
    "lift": "training_regimen",
    "strength": "training_regimen",
    "exercise": "training_regimen",
    # nutrition_protocol.md
    "nutrition": "nutrition_protocol",
    "diet": "nutrition_protocol",
    "macro": "nutrition_protocol",
    "protein": "nutrition_protocol",
    "calorie": "nutrition_protocol",
    # tech_stack.md
    "tech": "tech_stack",
    "software": "tech_stack",
    "code": "tech_stack",
    "developer": "tech_stack",
    "automation": "tech_stack",
    "api": "tech_stack",
    "github": "tech_stack",
    "saas": "tech_stack",
    "engineering": "tech_stack",
    # business_philosophy.md
    "business": "business_philosophy",
    "entrepreneur": "business_philosophy",
    "startup": "business_philosophy",
    "founder": "business_philosophy",
    "strategy": "business_philosophy",
}


def load() -> Dict[str, Any]:
    """Load brand voice config, falling back to defaults if missing or corrupt."""
    try:
        if BRAND_VOICE_PATH.exists():
            data = json.loads(BRAND_VOICE_PATH.read_text(encoding="utf-8"))
            # Merge any missing keys from defaults
            for key, value in _DEFAULTS.items():
                data.setdefault(key, value)
            return data
    except Exception:
        pass
    return dict(_DEFAULTS)


def save(config: Dict[str, Any]) -> None:
    """Atomically persist brand voice config to disk."""
    BRAND_VOICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = BRAND_VOICE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(BRAND_VOICE_PATH)


def build_prompt_block(config: Dict[str, Any]) -> str:
    """
    Build a compact, token-efficient prompt block from brand voice config.

    Designed for injection into any agent prompt. Total overhead: ~100-200 tokens.
    """
    lines: List[str] = ["=== BRAND VOICE ==="]

    lines.append(f"Author: {config.get('author', 'Kurt')}")
    lines.append(f"Tone: {config.get('tone', '')}")

    rules = config.get("formatting_rules", [])
    if rules:
        lines.append("Formatting rules:")
        for rule in rules:
            lines.append(f"  - {rule}")

    banned = config.get("banned_phrases", [])
    if banned:
        lines.append(f"Banned phrases (never use): {', '.join(repr(p) for p in banned)}")

    domain = config.get("domain_knowledge", [])
    if domain:
        lines.append("Domain knowledge:")
        for item in domain:
            lines.append(f"  - {item}")

    feedback = config.get("learned_style_feedback", [])
    if feedback:
        lines.append("Learned style directives (highest priority):")
        for item in feedback[-10:]:  # cap at 10 most recent to limit tokens
            lines.append(f"  - {item}")

    lines.append("===================")
    return "\n".join(lines)


def load_knowledge_file(stem: str) -> str:
    """Load a knowledge file by stem name. Returns empty string if not found."""
    path = KNOWLEDGE_DIR / f"{stem}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _build_auto_keyword_map() -> Dict[str, str]:
    """
    Scan config/knowledge/ and build an implicit keyword map from filenames.

    Each .md stem is split on underscores; every word becomes a keyword that
    maps back to that stem.  Example: ``supplement_stack.md`` → keywords
    "supplement" and "stack" both map to "supplement_stack".

    Explicit entries in _TOPIC_KEYWORD_MAP always win (they are merged last).
    """
    auto: Dict[str, str] = {}
    if KNOWLEDGE_DIR.is_dir():
        for md_file in KNOWLEDGE_DIR.glob("*.md"):
            stem = md_file.stem
            for word in stem.split("_"):
                if word and word not in auto:
                    auto[word] = stem
    # Explicit map overrides auto-derived entries
    auto.update(_TOPIC_KEYWORD_MAP)
    return auto


def select_knowledge_files(topic: str) -> List[str]:
    """
    Return content of knowledge files relevant to the given topic string.

    Checks both the explicit _TOPIC_KEYWORD_MAP and any .md file present in
    config/knowledge/ (auto-discovered via filename keywords).  Only loads
    files that match — keeps token cost near zero for unrelated topics.
    """
    combined_map = _build_auto_keyword_map()
    topic_lower = topic.lower()
    seen_stems: set = set()
    chunks: List[str] = []

    for keyword, stem in combined_map.items():
        if keyword in topic_lower and stem not in seen_stems:
            seen_stems.add(stem)
            text = load_knowledge_file(stem)
            if text.strip():
                chunks.append(f"=== DOMAIN KNOWLEDGE: {stem.replace('_', ' ').upper()} ===\n{text}\n===================")

    return chunks


def get_matched_stems(topic: str) -> List[str]:
    """Return deduplicated knowledge-file stems that match the given topic string."""
    combined_map = _build_auto_keyword_map()
    topic_lower = topic.lower()
    seen: dict = {}
    for keyword, stem in combined_map.items():
        if keyword in topic_lower and stem not in seen:
            seen[stem] = True
    return list(seen.keys())


def check_banned_phrases(text: str, config: Dict[str, Any]) -> List[str]:
    """Return list of banned phrases found in text."""
    banned = config.get("banned_phrases", [])
    found: List[str] = []
    text_lower = text.lower()
    for phrase in banned:
        if phrase.lower() in text_lower:
            found.append(phrase)
    return found


# ── Mutation helpers (used by ApprovalAgent) ─────────────────────────────────

def append_learned_feedback(directive: str) -> None:
    """Append a new style directive to learned_style_feedback and persist."""
    config = load()
    feedback: List[str] = config.setdefault("learned_style_feedback", [])
    directive = directive.strip()
    if directive and directive not in feedback:
        feedback.append(directive)
        save(config)


def append_domain_knowledge(fact: str) -> None:
    """Append a domain knowledge bullet and persist."""
    config = load()
    domain: List[str] = config.setdefault("domain_knowledge", [])
    fact = fact.strip()
    if fact and fact not in domain:
        domain.append(fact)
        save(config)


def append_banned_phrase(phrase: str) -> None:
    """Add a banned phrase and persist."""
    config = load()
    banned: List[str] = config.setdefault("banned_phrases", [])
    phrase = phrase.strip().strip('"\'')
    if phrase and phrase not in banned:
        banned.append(phrase)
        save(config)


def update_tone(new_tone: str) -> None:
    """Replace the tone string and persist."""
    config = load()
    config["tone"] = new_tone.strip()
    save(config)


def save_knowledge_file(stem: str, content: str) -> None:
    """Write (or overwrite) a knowledge file."""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    path = KNOWLEDGE_DIR / f"{stem}.md"
    path.write_text(content, encoding="utf-8")


def distill_style_rules(raw_text: str, max_rules: int = 3) -> List[str]:
    """
    Extract concise style rules from free-form text without an LLM call.

    This is a deterministic fallback that pulls meaningful sentences from the
    text. A real deployment would call an LLM here (one-time cost ~300 tokens)
    to produce higher-quality rules. For ghost/dry-run mode this keeps things
    fully offline.
    """
    sentences = re.split(r"(?<=[.!?])\s+", raw_text.strip())
    rules: List[str] = []
    style_keywords = {
        "short", "punchy", "direct", "clear", "avoid", "never", "always",
        "concise", "tone", "voice", "paragraph", "sentence", "hook",
        "lead", "active", "passive", "example", "concrete",
    }
    for sentence in sentences:
        if len(sentence) < 15 or len(sentence) > 200:
            continue
        tokens = set(sentence.lower().split())
        if tokens & style_keywords:
            rules.append(sentence.strip())
        if len(rules) >= max_rules:
            break
    # If nothing matched, take the first max_rules short sentences
    if not rules:
        for sentence in sentences:
            if 15 <= len(sentence) <= 200:
                rules.append(sentence.strip())
            if len(rules) >= max_rules:
                break
    return rules
