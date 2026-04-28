from __future__ import annotations

import re
from typing import Iterable


SKILL_CATEGORIES = ("technical", "languages", "tools", "soft_skills")
_SKILL_SPLIT_RE = re.compile(r"[\n,;]+")

_LANGUAGE_KEYWORDS = {
    "english",
    "spanish",
    "french",
    "german",
    "chinese",
    "mandarin",
    "cantonese",
    "japanese",
    "korean",
    "arabic",
    "hindi",
    "portuguese",
    "russian",
    "italian",
    "vietnamese",
    "tagalog",
    "turkish",
    "polish",
    "dutch",
    "greek",
    "hebrew",
    "swahili",
    "urdu",
    "bengali",
    "thai",
    "creole",
    "haitian creole",
    "cape verdean",
    "khmer",
    "cambodian",
}

_TOOL_KEYWORDS = {
    "docker",
    "kubernetes",
    "git",
    "github",
    "gitlab",
    "jira",
    "trello",
    "slack",
    "zoom",
    "teams",
    "figma",
    "photoshop",
    "illustrator",
    "tableau",
    "salesforce",
    "excel",
    "word",
    "powerpoint",
    "outlook",
    "office",
    "vscode",
    "visual studio",
    "intellij",
    "eclipse",
    "postman",
    "aws",
    "azure",
    "gcp",
}

_SOFT_SKILL_KEYWORDS = {
    "communication",
    "leadership",
    "teamwork",
    "problem solving",
    "problem-solving",
    "critical thinking",
    "time management",
    "organization",
    "collaboration",
    "adaptability",
    "creativity",
    "attention to detail",
    "customer service",
    "presentation",
    "negotiation",
    "conflict resolution",
    "decision making",
    "mentoring",
    "reliability",
    "empathy",
    "resilience",
}


def _clean_skill_token(value: str) -> str:
    token = str(value or "").strip()
    token = re.sub(r"\s+", " ", token)
    token = token.strip(" .:-|")
    return token


def _token_variants(token: str) -> list[str]:
    lowered = token.casefold()
    base = lowered.strip()
    variants = {base}
    if "(" in base and ")" in base:
        no_paren = re.sub(r"\s*\([^)]*\)", "", base).strip()
        if no_paren:
            variants.add(no_paren)
    return [item for item in variants if item]


def _preferred_display(token: str) -> str:
    raw = _clean_skill_token(token)
    if not raw:
        return ""
    parts = raw.split()
    if len(parts) == 1 and parts[0].isupper():
        return parts[0]
    return " ".join(part if any(ch.isupper() for ch in part) else part.capitalize() for part in parts)


def _detect_category(token: str) -> str:
    variants = _token_variants(token)
    for value in variants:
        if value in _LANGUAGE_KEYWORDS:
            return "languages"
    for value in variants:
        if value in _TOOL_KEYWORDS:
            return "tools"
    for value in variants:
        if value in _SOFT_SKILL_KEYWORDS:
            return "soft_skills"
    return "technical"


def iter_skill_tokens(values: Iterable[str]) -> list[str]:
    tokens: list[str] = []
    for value in values:
        for chunk in _SKILL_SPLIT_RE.split(str(value or "")):
            token = _clean_skill_token(chunk)
            if token:
                tokens.append(token)
    return tokens


def normalize_and_classify_skills(raw_skills: dict | None) -> dict[str, list[str]]:
    source = raw_skills if isinstance(raw_skills, dict) else {}
    ranked: dict[str, list[str]] = {key: [] for key in SKILL_CATEGORIES}
    seen: set[str] = set()

    # Process in fixed source order so results remain stable/idempotent.
    for category in SKILL_CATEGORIES:
        values = source.get(category)
        if not isinstance(values, list):
            continue
        for token in iter_skill_tokens(values):
            dedupe_key = token.casefold()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            resolved_category = _detect_category(token)
            ranked[resolved_category].append(_preferred_display(token))

    return ranked
