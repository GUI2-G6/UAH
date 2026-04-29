from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any, Iterable


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
    "action_required": [
        "additional information needed",
        "information appears to be missing",
        "missing from your job application",
        "complete your job application",
        "complete our job application",
        "please follow the below steps",
        "check your email inbox to retrieve the temporary password",
        "confirm your contact information",
        "proceed until you see a thank you message",
    ],
    "rejection": [
        "unfortunately",
        "regret",
        "regret to inform you",
        "unable to consider you further",
        "not selected",
        "not moving forward",
        "will not be moving forward",
        "move forward with other candidates",
    ],
    "interview_invite": ["interview", "schedule", "meet with", "next steps", "phone screen"],
    "offer": [
        "offer",
        "offer letter",
        "formal offer",
        "written offer",
        "official offer",
        "compensation package",
        "congratulations",
        "pleased to extend",
        "welcome aboard",
        "join us as",
        "join our team",
        "summer intern",
        "summer internship",
        "confirm your interest",
        "still interested",
    ],
    "application_received": ["received your application", "application received", "thank you for applying", "we have received"],
}
STATUS_PATTERNS = {
    "action_required": [
        re.compile(r"\badditional information needed\b", flags=re.IGNORECASE),
        re.compile(r"\binformation appears to be missing\b", flags=re.IGNORECASE),
        re.compile(r"\bmissing from your job application\b", flags=re.IGNORECASE),
        re.compile(r"\bcomplete (?:your|our)\s+job application\b", flags=re.IGNORECASE),
        re.compile(r"\bplease follow (?:the|these)\s+below steps\b", flags=re.IGNORECASE),
        re.compile(r"\bretrieve the temporary password\b", flags=re.IGNORECASE),
    ],
    "rejection": [
        re.compile(r"\bregret to inform you\b", flags=re.IGNORECASE),
        re.compile(r"\bunable to consider you further\b", flags=re.IGNORECASE),
        re.compile(r"\bnot selected\b", flags=re.IGNORECASE),
        re.compile(r"\bnot (?:be )?moving forward\b", flags=re.IGNORECASE),
        re.compile(r"\bmove forward with other candidates\b", flags=re.IGNORECASE),
    ],
    "interview_invite": [
        re.compile(r"\b(?:schedule|scheduling).{0,25}\binterview\b", flags=re.IGNORECASE),
        re.compile(r"\binterview (?:next steps|invitation)\b", flags=re.IGNORECASE),
        re.compile(r"\bphone screen\b", flags=re.IGNORECASE),
    ],
    "offer": [
        re.compile(r"\bpleased to extend\b", flags=re.IGNORECASE),
        re.compile(r"\bjob offer\b", flags=re.IGNORECASE),
        re.compile(r"\bwelcome aboard\b", flags=re.IGNORECASE),
        re.compile(r"\b(?:formal|official|written)\s+offer\b", flags=re.IGNORECASE),
        re.compile(r"\boffer letter\b", flags=re.IGNORECASE),
        re.compile(r"\bextend(?:ing)?\s+(?:you\s+)?(?:an?\s+)?offer\b", flags=re.IGNORECASE),
        re.compile(r"\bconfirm (?:your )?interest\b.{0,50}\boffer\b", flags=re.IGNORECASE),
        re.compile(r"\bjoin us as\b.{0,60}\bintern\b", flags=re.IGNORECASE),
        re.compile(r"\bcompensation package\b", flags=re.IGNORECASE),
    ],
    "application_received": [
        re.compile(r"\bthank you for applying\b", flags=re.IGNORECASE),
        re.compile(r"\b(?:we have )?received your application\b", flags=re.IGNORECASE),
        re.compile(r"\bapplication (?:has been )?received\b", flags=re.IGNORECASE),
    ],
}
JOB_UPDATE_KEYWORDS = (
    "application",
    "additional information needed",
    "missing information",
    "complete your application",
    "position",
    "interview",
    "offer",
    "offer letter",
    "formal offer",
    "written offer",
    "summer intern",
    "summer internship",
    "join us",
    "hiring",
    "recruit",
    "candidate",
    "next steps",
    "status update",
)
NEGATIVE_INTENT_KEYWORDS = (
    "deal awaits",
    "limited time offer",
    "coupon",
    "promo",
    "newsletter",
    "breaking news",
    "view in browser",
    "premium",
    "learn how to",
    "support hunger",
    "digest",
    "unsubscribe",
)
JOB_PLATFORM_HINTS = ("linkedin", "ripplematch", "handshake", "indeed", "ziprecruiter")
RECRUITER_HINTS = ("candidatecare", "career", "careers", "talent", "recruit")
RECRUITER_FROM_HINTS = (
    "recruit",
    "recruiting",
    "recruiter",
    "talent",
    "talent acquisition",
    "hiring",
    "human resources",
    "hr team",
    "people operations",
)
LINKEDIN_APPLY_SIGNALS = (
    "your application was sent",
    "application was sent",
    "application submitted",
    "jobs-noreply",
    "job application",
    "thanks for your interest",
    "what's next",
)
LINKEDIN_NON_APPLY_SIGNALS = (
    "premium",
    "next steps after adding",
    "share their thoughts",
    "learn how to stand out",
    "profile",
    "connection",
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)
_CONTROL_PATTERN = re.compile(r"[\x00-\x1F\x7F]+")


@dataclass(frozen=True)
class ScanMessage:
    subject: str
    from_header: str
    date: str
    snippet: str
    body: str = ""
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


def _sender_localpart(from_header: str | None) -> str:
    _, email_addr = parseaddr(str(from_header or ""))
    if "@" not in email_addr:
        return ""
    return email_addr.split("@", 1)[0].strip().lower()


def normalize_subject_key(subject: str | None) -> str:
    raw = sanitize_preview_text(subject, max_len=220).lower()
    raw = re.sub(r"\b(re|fwd?)\s*:\s*", "", raw)
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return " ".join(raw.split())[:120]


def normalize_company_key(value: str | None) -> str:
    raw = sanitize_preview_text(value, max_len=120).lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return " ".join(raw.split())[:80]


def normalize_employer_key_cluster(value: str | None) -> str:
    """
    Collapses common suffix variants ("Expedia" vs "Expedia Group") for chain bucketing only.
    """
    base = normalize_company_key(value)
    if not base:
        return ""
    tokens = base.split()
    if len(tokens) >= 2 and tokens[-1] in {"group", "holdings", "global", "inc", "llc"}:
        tokens = tokens[:-1]
    return " ".join(tokens).strip()[:80]


def sender_domain_hints_job_platform(from_header: str | None) -> bool:
    domain = parse_sender_domain(from_header)
    dl = domain.lower()
    if not dl:
        return False
    return any(hint in dl for hint in JOB_PLATFORM_HINTS)


_CANONICAL_EMPLOYER_PATTERNS = (
    # "Thanks for your interest in Expedia Group"
    re.compile(
        r"\bthanks\s+for\s+your\s+interest\s+in\s+([A-Za-z0-9&+'’.\- ]{2,80}?)(?:\s*[!.\?]|(?:\s+What)|(?:\s+We\b)|(?:\s+Here\b)|(?:\s+Your\b)|$)",
        re.IGNORECASE,
    ),
    re.compile(r"\binterest\s+in\s+([A-Za-z0-9&+'’.\- ]{2,80}?)(?:\s*[!.\?]|$)", re.IGNORECASE),
    re.compile(r"\byour\s+application\s+to\s+([A-Za-z0-9&+'’.\- ]{2,80}?)(?:\s*[!.\?]|$)", re.IGNORECASE),
    re.compile(r"\bapplication\s+to\s+([A-Za-z0-9&+'’.\- ]{2,80}?)(?:\.|,|\s+has|\s+has\s+been|$)", re.IGNORECASE),
    re.compile(r"\bapplication\s+(?:with|for)\s+([A-Za-z0-9&+'’.\- ]{2,80}?)(?:\s*[!.\?]|$)", re.IGNORECASE),
    re.compile(r"\bmove\s+forward\s+[^\n]{0,80}?\sfor\s+(?:the\s+)?(?:position|role)[^:]{0,20}:[ \t\r\n]*([^|<\n]{6,140})", re.IGNORECASE),
    re.compile(
        r"\b(?:would\s+)?like\s+to\s+move\s+forward\s+with\s+[^\n]{0,40}?\sfor\s+(?:the\s+)?(?:position)[^:]+:\s*([^\n|<]{6,140})",
        re.IGNORECASE,
    ),
    # "Position Update from XYZ" handled elsewhere; ATS Workday naming
    re.compile(r"\bposition\s+update\s+from\s+([A-Za-z0-9&+'’.\- ]{2,80}?)(?:\s*[!.\?]|$)", re.IGNORECASE),
)


def extract_canonical_employer_hint(
    from_header: str,
    subject: str,
    snippet: str = "",
    body: str = "",
    *,
    source_bucket: str = "",
    company_hint: str | None = None,
) -> str | None:
    """
    Prefer the hiring company named in subject/body for job-platform / forwarder senders
    (Ripplematch, Handshake, …) instead of the mailbox vendor name alone.
    """
    combined_raw = "\n".join(part for part in (subject or "", snippet or "", body or "") if part)

    wants_body_scan = sender_domain_hints_job_platform(from_header) or (source_bucket or "").strip().lower() == "job_platform"
    wants_body_scan |= (source_bucket or "").strip().lower() == "recruiter_direct"
    content = sanitize_preview_text(combined_raw, max_len=2600)

    if wants_body_scan or any(h in (subject or "").lower() for h in ("interest in", "application to ", "thanks for applying")):
        for pattern in _CANONICAL_EMPLOYER_PATTERNS:
            match = pattern.search(content)
            if not match:
                continue
            captured = _clean_company_capture(match.group(1))
            if captured and _looks_like_company_name(captured):
                return captured

    return _format_company_name((company_hint or "").strip()) if company_hint else None


def _looks_like_company_name(value: str | None) -> bool:
    s = str(value or "").strip().lower()
    if len(s) < 2:
        return False
    noise = {"you", "we", "our", "this", "the", "candidate", "position", "internship", "summer"}
    head = re.sub(r"[^a-z\s]+", " ", s.split()[0])
    if head in noise:
        return False
    return True


def extract_role_anchor(subject: str = "", snippet: str = "", body: str = "") -> str:
    blob = sanitize_preview_text(" ".join(p for p in (subject or "", snippet or "", body or "") if p), max_len=1500).lower()

    chunk = ""

    patterns = (
        r"for\s+the\s+position[s]?[:\s\u2014\-]+\s*([^\n|<]{6,120})",
        r"after\s+reviewing[^\n]{0,40}[^\n:]+:\s*([^\n|<]{8,140})",
        r"internship[^\n]{0,10}[^\n:]+:\s*([^\n|<]{10,140})",
    )
    for pat in patterns:
        m = re.search(pat, blob, flags=re.IGNORECASE)
        if m:
            chunk = sanitize_preview_text(m.group(1).strip(), max_len=240)
            break

    if not chunk:
        # Title after em dash often names role cohort
        m = re.search(r"[^\w](\d{4})\s+(?:summer\s+)?intern(?:ship)?[^\n]{2,140}", blob)
        if m:
            chunk = sanitize_preview_text(re.sub(r"[^a-z0-9\s]+", " ", m.group(0)), max_len=80)

    if not chunk:
        return ""

    # Drop trailing employer noise captured accidentally
    chunk = re.split(r"\b(?:would like|would like to|thank you|thanks|we have)\b", chunk, maxsplit=1, flags=re.IGNORECASE)[0]
    nk = normalize_subject_key(chunk)
    return nk[:100] if nk else ""


def build_application_chain_key(
    *,
    canonical_company_hint: str | None,
    company_hint: str | None,
    sender_domain: str,
    subject_key: str,
    company_key: str,
    subject: str,
    snippet_body: str,
) -> tuple[str, str, str]:
    """
    Stable key for collapsing multi-sender pipelines (ATS + Ripplematch) for same employer/path.
    Returns (application_chain_key, employer_key_normalized, role_anchor_normalized).
    """
    hint = canonical_company_hint or company_hint or ""
    employer_key = normalize_employer_key_cluster(hint)
    rak = extract_role_anchor(subject=subject, snippet=snippet_body, body=snippet_body)

    if employer_key:
        if rak:
            key = f"{employer_key}|{rak}"
        else:
            sk = normalize_subject_key(subject)
            tail = sk[:96] if sk else normalize_company_key(snippet_body)[:96]
            key = f"{employer_key}|subj::{tail}"
        return key, employer_key, rak

    key = f"legacy::{sender_domain}|{subject_key}|{company_key}"
    return key, employer_key or "", rak


def stable_application_cluster_id(application_chain_key: str) -> str:
    digest = hashlib.sha256(application_chain_key.encode("utf-8")).hexdigest()
    return digest[:16]


def parse_scan_row_date_isoish(value: str | None) -> datetime:
    raw = sanitize_preview_text(str(value or ""), max_len=200)
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        pass
    try:
        iso = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def annotate_flat_scan_results_cluster_metadata(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Populate cluster_id/cluster_rank/cluster_leader_source_id/reorder clusters latest-first.
    """
    from collections import defaultdict

    if not rows:
        return rows
    keyed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        k = str(row.get("application_chain_key") or row.get("thread_key") or "")
        keyed[k].append(row)

    cluster_blocks: list[tuple[datetime, list[dict[str, Any]]]] = []

    for k, grp in keyed.items():
        grp_sorted = sorted(grp, key=lambda r: parse_scan_row_date_isoish(str(r.get("date") or "")), reverse=True)
        cid = stable_application_cluster_id(
            k if k != "" else f"nohash|{grp_sorted[0].get('source_id') or grp_sorted[0].get('thread_key') or 'unknown'}"
        )
        leader_sid = grp_sorted[0].get("source_id")
        sz = len(grp_sorted)
        leader_dt = parse_scan_row_date_isoish(str(grp_sorted[0].get("date") or ""))

        for rank, rr in enumerate(grp_sorted):
            rr["cluster_id"] = cid
            rr["cluster_size"] = sz
            rr["cluster_rank"] = rank
            rr["cluster_leader_source_id"] = str(leader_sid or "")
        cluster_blocks.append((leader_dt, grp_sorted))

    cluster_blocks.sort(key=lambda t: t[0], reverse=True)

    out: list[dict[str, Any]] = []
    for _dt, grp in cluster_blocks:
        out.extend(grp)
    return out


def build_thread_signature(*, from_header: str, subject: str, company_hint: str | None) -> tuple[str, str, str]:
    sender_domain = parse_sender_domain(from_header)
    subject_key = normalize_subject_key(subject)
    company_key = normalize_company_key(company_hint)
    return sender_domain, subject_key, company_key


def _format_company_name(value: str | None) -> str | None:
    compact = " ".join(str(value or "").split()).strip(" -_,.")
    if not compact:
        return None
    words: list[str] = []
    for token in compact.split():
        clean = token.strip()
        if len(clean) <= 3 and clean.isalpha() and clean.upper() == clean:
            words.append(clean)
        elif clean.isupper() and len(clean) <= 4:
            words.append(clean)
        else:
            words.append(clean.capitalize())
    return " ".join(words)[:60] or None


def _clean_company_capture(value: str | None) -> str | None:
    trimmed = str(value or "")
    trimmed = re.split(
        r"\b(?:position|role|opportunity|team|thanks|thank you|we've|we have|regret|unable)\b",
        trimmed,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    trimmed = re.sub(r"^\s*the\s+", "", trimmed, flags=re.IGNORECASE)
    lowered = trimmed.lower()
    if "interest in" in lowered:
        return None
    if any(token in lowered for token in ("your ", " this ", " our ")):
        return None
    return _format_company_name(trimmed)


def _company_from_sender_localpart(from_header: str | None) -> str | None:
    localpart = _sender_localpart(from_header)
    if not localpart:
        return None
    common = {
        "no-reply",
        "noreply",
        "donotreply",
        "do-not-reply",
        "notifications",
        "notification",
        "jobs",
        "careers",
        "recruiting",
        "workday",
    }
    if localpart in common:
        return None
    cleaned = re.sub(r"[^a-z0-9]+", " ", localpart).strip()
    if not cleaned or len(cleaned) < 2:
        return None
    parts = [part for part in cleaned.split() if part]
    if len(parts) == 1 and parts[0].isalpha() and len(parts[0]) <= 5:
        return parts[0].upper()
    return _format_company_name(cleaned)


def extract_company_hint(from_header: str, subject: str, snippet: str = "", body: str = "") -> str | None:
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
        subject_patterns = [
            r"\bposition update from\s+([A-Za-z0-9&.\- ]{2,60})$",
            r"\bupdate from\s+([A-Za-z0-9&.\- ]{2,60})$",
            r"\b(?:application|position|role)\s+(?:with|at|for)\s+([A-Za-z0-9&.\- ]{2,60})$",
        ]
        for pattern in subject_patterns:
            subject_match = re.search(pattern, subject or "", flags=re.IGNORECASE)
            if subject_match:
                captured = _clean_company_capture(subject_match.group(1))
                if captured:
                    return captured

        content = " ".join(part for part in [subject or "", snippet or "", body or ""] if part)
        patterns = [
            r"\bposition update from\s+([A-Za-z0-9&.\- ]{2,60})",
            r"\bupdate from\s+([A-Za-z0-9&.\- ]{2,60})",
            r"\b(?:application|position|role)\s+(?:with|at|for)\s+([A-Za-z0-9&.\- ]{2,60})",
            r"\b(?:at|for|with)\s+([A-Za-z0-9&.\- ]{2,60})\s+(?:position|role|opportunity)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, content, flags=re.IGNORECASE)
            if match:
                captured = _clean_company_capture(match.group(1))
                if captured:
                    return captured
        localpart_hint = _company_from_sender_localpart(from_header)
        if localpart_hint:
            return localpart_hint
        return None
    return _format_company_name(candidate)


def _score_status_for_text(text: str) -> dict[str, int]:
    normalized = str(text or "").lower()
    scores: dict[str, int] = {}
    for status in ("rejection", "action_required", "interview_invite", "offer", "application_received"):
        score = 0
        score += sum(1 for keyword in STATUS_KEYWORDS[status] if keyword in normalized)
        score += 2 * sum(1 for pattern in STATUS_PATTERNS[status] if pattern.search(normalized))
        scores[status] = score
    return scores


def classify_message_status(subject: str, snippet: str, body: str = "") -> str:
    min_score = {
        "rejection": 2,
        "action_required": 2,
        "interview_invite": 2,
        "offer": 2,
        "application_received": 1,
    }
    for content in (body, subject, snippet):
        scores = _score_status_for_text(content)
        for status in ("rejection", "action_required", "interview_invite", "offer", "application_received"):
            if scores.get(status, 0) >= min_score[status]:
                return status
    return "unknown"


def is_job_update_message(subject: str, snippet: str, body: str = "") -> bool:
    status = classify_message_status(subject, snippet, body)
    if status != "unknown":
        return True
    combined = f"{(subject or '').lower()} {(snippet or '').lower()} {(body or '').lower()}"
    return any(keyword in combined for keyword in JOB_UPDATE_KEYWORDS)


def _intent_score(subject: str, snippet: str, body: str = "") -> int:
    combined = f"{(subject or '').lower()} {(snippet or '').lower()} {(body or '').lower()}"
    return sum(1 for keyword in JOB_UPDATE_KEYWORDS if keyword in combined)


def _negative_intent_detected(subject: str, snippet: str, body: str = "") -> bool:
    combined = f"{(subject or '').lower()} {(snippet or '').lower()} {(body or '').lower()}"
    return any(keyword in combined for keyword in NEGATIVE_INTENT_KEYWORDS)


def _source_bucket(from_header: str, subject: str, snippet: str, body: str = "") -> str:
    domain = parse_sender_domain(from_header)
    combined = f"{domain} {(from_header or '').lower()} {(subject or '').lower()} {(snippet or '').lower()} {(body or '').lower()}"
    second_level_domain = ""
    if "." in domain:
        parts = [part for part in domain.split(".") if part]
        if len(parts) >= 2:
            second_level_domain = parts[-2]
    if any(hint in combined for hint in ATS_DOMAIN_HINTS):
        return "ats_portal"
    if any(hint in combined for hint in JOB_PLATFORM_HINTS):
        return "job_platform"
    if any(hint in combined for hint in RECRUITER_HINTS):
        return "recruiter_direct"
    if any(hint in combined for hint in RECRUITER_FROM_HINTS):
        return "recruiter_direct"
    if second_level_domain and second_level_domain not in CONSUMER_EMAIL_DOMAINS:
        if _intent_score(subject, snippet, body) >= 2:
            return "recruiter_direct"
    return "non_career"


def _has_strong_job_signal(
    *,
    status: str,
    intent_score: int,
    job_update_detected: bool,
    matched_applied_job: bool,
    from_header: str,
    subject: str,
    snippet: str,
    body: str,
) -> bool:
    if status in {"offer", "interview_invite", "rejection", "action_required"}:
        return True
    if matched_applied_job and job_update_detected:
        return True
    if intent_score >= 3 and job_update_detected:
        return True

    domain = parse_sender_domain(from_header)
    parts = [part for part in domain.split(".") if part]
    second_level_domain = parts[-2] if len(parts) >= 2 else ""
    if second_level_domain in CONSUMER_EMAIL_DOMAINS:
        return False

    combined = f"{(subject or '').lower()} {(snippet or '').lower()} {(body or '').lower()}"
    high_signal_phrases = (
        "offer letter",
        "formal offer",
        "written offer",
        "official offer",
        "confirm your interest",
        "still interested",
        "join us as",
        "summer intern",
        "summer internship",
    )
    return any(phrase in combined for phrase in high_signal_phrases)


def _linkedin_apply_detected(from_header: str, subject: str, snippet: str, body: str = "") -> bool:
    domain = parse_sender_domain(from_header)
    if "linkedin" not in domain:
        return False
    combined = f"{domain} {(subject or '').lower()} {(snippet or '').lower()} {(body or '').lower()}"
    if any(marker in combined for marker in LINKEDIN_NON_APPLY_SIGNALS):
        return False
    return any(marker in combined for marker in LINKEDIN_APPLY_SIGNALS)


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


def _company_acronym(company: str | None) -> str:
    words = [w for w in re.split(r"[^a-z0-9]+", str(company or "").lower()) if w and len(w) > 1]
    if len(words) < 2:
        return ""
    acronym = "".join(word[0] for word in words)
    return acronym if len(acronym) >= 2 else ""


def message_matches_applied_job(
    message: ScanMessage,
    *,
    apply_sessions: Iterable[dict],
    allowed_statuses: set[str],
) -> bool:
    message_tokens = _tokenize(message.subject, message.snippet, message.body, message.from_header)
    message_company = _normalize_company(extract_company_hint(message.from_header, message.subject, message.snippet, message.body))

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

        company_tokens = _tokenize(company)
        if company_tokens and message_tokens and len(company_tokens.intersection(message_tokens)) >= 1:
            title_tokens = _tokenize(title)
            title_overlap = len(message_tokens.intersection(title_tokens))
            if title_overlap >= 1:
                return True

        acronym = _company_acronym(company)
        if acronym and acronym in message_tokens:
            title_tokens = _tokenize(title)
            if len(message_tokens.intersection(title_tokens)) >= 1:
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
    source_strictness: str = "strict_career_domains",
    linkedin_mode: str = "linkedin_apply_only",
) -> dict:
    subject = sanitize_preview_text(message.subject, max_len=220)
    snippet = sanitize_preview_text(message.snippet, max_len=320)
    body = sanitize_preview_text(message.body, max_len=1500)
    body_preview = sanitize_preview_text(message.body, max_len=1200)
    from_header = sanitize_preview_text(message.from_header, max_len=220)
    date = sanitize_preview_text(message.date, max_len=120)
    status = classify_message_status(subject, snippet, body)
    company_hint = extract_company_hint(from_header, subject, snippet, body)
    ats_detected = is_ats_message(from_header, subject, f"{snippet} {body}")
    job_update_detected = is_job_update_message(subject, snippet, body)
    source_bucket = _source_bucket(from_header, subject, snippet, body)
    canonical_company_hint = extract_canonical_employer_hint(
        from_header,
        subject,
        snippet,
        body,
        source_bucket=str(source_bucket or ""),
        company_hint=company_hint,
    )
    intent_score = _intent_score(subject, snippet, body)
    negative_intent_detected = _negative_intent_detected(subject, snippet, body)
    linkedin_apply_detected = _linkedin_apply_detected(from_header, subject, snippet, body)

    matched_applied_job = message_matches_applied_job(
        ScanMessage(subject=subject, from_header=from_header, date=date, snippet=snippet, body=body, source_id=message.source_id),
        apply_sessions=apply_sessions,
        allowed_statuses=allowed_statuses,
    )
    strong_job_signal = _has_strong_job_signal(
        status=status,
        intent_score=intent_score,
        job_update_detected=job_update_detected,
        matched_applied_job=matched_applied_job,
        from_header=from_header,
        subject=subject,
        snippet=snippet,
        body=body,
    )

    include = True
    reason = "included"
    if source_strictness == "strict_career_domains" and source_bucket == "non_career" and not strong_job_signal:
        include = False
        reason = "noncareer_source"
    elif "linkedin" in parse_sender_domain(from_header):
        if linkedin_mode == "linkedin_off":
            include = False
            reason = "linkedin_disabled"
        elif linkedin_mode == "linkedin_apply_only" and not linkedin_apply_detected:
            include = False
            reason = "linkedin_non_apply"
    elif negative_intent_detected:
        include = False
        reason = "negative_intent"
    elif require_ats and not (ats_detected or (job_update_detected and intent_score >= 2) or strong_job_signal):
        include = False
        reason = "non_ats_or_job_update"

    return {
        "source_id": message.source_id,
        "subject": subject,
        "from": from_header,
        "date": date,
        "detected_status": status,
        "company_hint": company_hint,
        "canonical_company_hint": canonical_company_hint,
        "snippet": snippet,
        "body_preview": body_preview,
        "ats_detected": ats_detected,
        "job_update_detected": job_update_detected,
        "linkedin_apply_detected": linkedin_apply_detected,
        "negative_intent_detected": negative_intent_detected,
        "source_bucket": source_bucket,
        "intent_score": intent_score,
        "matched_applied_job": matched_applied_job,
        "include": include,
        "exclude_reason": None if include else reason,
    }
