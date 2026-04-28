from __future__ import annotations

import re
from dataclasses import dataclass
from email.utils import parseaddr
from typing import Iterable


ATS_DOMAIN_HINTS = (
    "greenhouse",
    "workday",
    "myworkdayjobs",
    "lever",
    "icims",
    "jobvite",
    "smartrecruiters",
    "ashby",
    "ashbyhq",
    "bamboohr",
)

CONSUMER_EMAIL_DOMAINS = {"gmail", "yahoo", "outlook", "hotmail", "icloud", "protonmail"}
STATUS_KEYWORDS = {
    "rejection": ["unfortunately", "regret", "not selected", "not moving forward", "will not be"],
    "interview_invite": ["interview", "schedule", "meet with", "next steps", "phone screen"],
    "offer": ["offer", "congratulations", "pleased to extend", "welcome aboard"],
    "application_received": ["received your application", "application received", "thank you for applying", "we have received"],
}

_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)
_CONTROL_PATTERN = re.compile(r"[\x00-\x1F\x7F]+")


@dataclass(frozen=True)
class ScanMessage:
    subject: str
    from_header: str
    date: str
    snippet: str
    source_id: str | None = None


def sanitize_preview_text(value: str | None, *, max_len: int = 400) -> str:
    normalized = _CONTROL_PATTERN.sub(" ", str(value or ""))
    normalized = " ".join(normalized.split())
    return normalized[:max_len]


def parse_sender_domain(from_header: str | None) -> str:
    _, email_addr = parseaddr(str(from_header or ""))
    if "@" not in email_addr:
        return ""
    return email_addr.split("@", 1)[-1].strip().lower()


def extract_company_hint(from_header: str, subject: str) -> str | None:
    domain = parse_sender_domain(from_header)
    if not domain:
        return None

    parts = [part for part in domain.split(".") if part]
    if len(parts) < 2:
        return None
    candidate = parts[-2].lower()
    if candidate in CONSUMER_EMAIL_DOMAINS:
        return None
    if any(hint in candidate for hint in ATS_DOMAIN_HINTS):
        match = re.search(r"\b(?:at|for)\s+([A-Za-z0-9&.\- ]{2,60})", subject or "", flags=re.IGNORECASE)
        if match:
            guessed = " ".join(match.group(1).split()).strip(" -_,.")
            return guessed[:60] or None
        return None
    return candidate.capitalize()


def classify_message_status(subject: str, snippet: str) -> str:
    combined = f"{(subject or '').lower()} {(snippet or '').lower()}"
    for status in ("rejection", "interview_invite", "offer", "application_received"):
        if any(keyword in combined for keyword in STATUS_KEYWORDS[status]):
            return status
    return "unknown"


def is_ats_message(from_header: str, subject: str, snippet: str) -> bool:
    domain = parse_sender_domain(from_header)
    combined = f"{(subject or '').lower()} {(snippet or '').lower()} {domain}"
    return any(hint in combined for hint in ATS_DOMAIN_HINTS)


def _tokenize(*parts: str) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        for token in _TOKEN_PATTERN.findall(str(part or "").lower()):
            tokens.add(token)
    return tokens


def _normalize_company(company: str | None) -> str:
    return " ".join(str(company or "").lower().split())


def message_matches_applied_job(
    message: ScanMessage,
    *,
    apply_sessions: Iterable[dict],
    allowed_statuses: set[str],
) -> bool:
    message_tokens = _tokenize(message.subject, message.snippet, message.from_header)
    message_company = _normalize_company(extract_company_hint(message.from_header, message.subject))

    for session in apply_sessions:
        status = str(session.get("status") or "").strip().lower()
        if status not in allowed_statuses:
            continue

        company = _normalize_company(session.get("company"))
        title = str(session.get("job_title") or "")
        session_tokens = _tokenize(company, title)
        if not session_tokens:
            continue

        if company and message_company and (company == message_company or company in message_company or message_company in company):
            return True

        overlap = len(message_tokens.intersection(session_tokens))
        if overlap >= 2:
            return True
    return False


def evaluate_message(
    message: ScanMessage,
    *,
    apply_sessions: Iterable[dict],
    allowed_statuses: set[str],
    require_ats: bool,
) -> dict:
    subject = sanitize_preview_text(message.subject, max_len=220)
    snippet = sanitize_preview_text(message.snippet, max_len=320)
    from_header = sanitize_preview_text(message.from_header, max_len=220)
    date = sanitize_preview_text(message.date, max_len=120)
    status = classify_message_status(subject, snippet)
    company_hint = extract_company_hint(from_header, subject)
    ats_detected = is_ats_message(from_header, subject, snippet)

    matched_applied_job = message_matches_applied_job(
        ScanMessage(subject=subject, from_header=from_header, date=date, snippet=snippet, source_id=message.source_id),
        apply_sessions=apply_sessions,
        allowed_statuses=allowed_statuses,
    )

    include = True
    reason = "included"
    if require_ats and not ats_detected:
        include = False
        reason = "non_ats_sender"
    elif not matched_applied_job:
        include = False
        reason = "no_applied_job_match"

    return {
        "source_id": message.source_id,
        "subject": subject,
        "from": from_header,
        "date": date,
        "detected_status": status,
        "company_hint": company_hint,
        "snippet": snippet,
        "ats_detected": ats_detected,
        "matched_applied_job": matched_applied_job,
        "include": include,
        "exclude_reason": None if include else reason,
    }
