from __future__ import annotations

from app.core.config import settings
from app.models.user import User
from app.schemas.integration import ServiceAction, ServiceDetail, ServiceReadiness, ServiceSummary

SERVICE_KEYS = ("gmail", "calendar_sync", "resume_imports")


def _gmail_configured() -> bool:
    return bool(
        (settings.GMAIL_CLIENT_ID or "").strip()
        and (settings.GMAIL_CLIENT_SECRET or "").strip()
        and (settings.GMAIL_REDIRECT_URI or "").strip()
    )


def _coming_soon_action() -> ServiceAction:
    return ServiceAction(
        key="coming_soon",
        label="Coming soon",
        enabled=False,
        style="muted",
    )


def _gmail_connect_action() -> ServiceAction:
    return ServiceAction(
        key="connect",
        label="Connect",
        enabled=True,
        style="primary",
        method="POST",
        href="/api/integrations/gmail/connect/start",
    )


def _gmail_disconnect_action() -> ServiceAction:
    return ServiceAction(
        key="disconnect",
        label="Disconnect",
        enabled=True,
        style="secondary",
        method="DELETE",
        href="/api/integrations/gmail/disconnect",
    )


def _gmail_unavailable_action() -> ServiceAction:
    return ServiceAction(
        key="unavailable",
        label="Unavailable",
        enabled=False,
        style="muted",
    )


def _gmail_summary(user: User) -> ServiceSummary:
    connected = bool(user.gmail_refresh_token)
    configured = _gmail_configured()
    account_label = (user.gmail_email or "").strip() or None

    if connected:
        return ServiceSummary(
            key="gmail",
            label="Gmail Updates",
            category="communication",
            status="connected",
            connected=True,
            availability="available",
            summary="Mailbox ready for future job-update scanning and timeline enrichment.",
            account_label=account_label or "Connected to Gmail",
            primary_action=_gmail_disconnect_action(),
            can_view_details=True,
        )

    if configured:
        return ServiceSummary(
            key="gmail",
            label="Gmail Updates",
            category="communication",
            status="available",
            connected=False,
            availability="available",
            summary="Opt in to read-only inbox access so UAH can prepare for job update workflows.",
            account_label="No Gmail mailbox connected yet.",
            primary_action=_gmail_connect_action(),
            can_view_details=True,
        )

    return ServiceSummary(
        key="gmail",
        label="Gmail Updates",
        category="communication",
        status="needs_attention",
        connected=False,
        availability="available",
        summary="Gmail support exists, but this environment still needs OAuth configuration before users can connect.",
        account_label="Gmail OAuth is not configured for this environment.",
        primary_action=_gmail_unavailable_action(),
        can_view_details=True,
    )


def _gmail_detail(user: User) -> ServiceDetail:
    summary = _gmail_summary(user)
    connected = summary.connected
    configured = _gmail_configured()

    if connected:
        readiness = ServiceReadiness(
            title="Ready for mailbox-powered updates",
            description="UAH can use this mailbox connection for future job-update scanning, status inference, and timeline enrichment without asking you to reconnect.",
            tone="positive",
        )
    elif configured:
        readiness = ServiceReadiness(
            title="Available to connect",
            description="Connect Gmail when you want UAH ready for inbox-based job update features. Nothing is scanned automatically in this phase.",
            tone="neutral",
        )
    else:
        readiness = ServiceReadiness(
            title="Needs environment setup",
            description="An administrator still needs to configure Gmail OAuth credentials for this environment before users can opt in.",
            tone="warning",
        )

    actions = (
        [_gmail_disconnect_action()]
        if connected
        else ([_gmail_connect_action()] if configured else [_gmail_unavailable_action()])
    )

    return ServiceDetail(
        key="gmail",
        label="Gmail Updates",
        status=summary.status,
        connected=summary.connected,
        account_label=summary.account_label,
        availability=summary.availability,
        description="Connect Gmail so UAH can prepare for inbox-driven job update workflows and future email-based status intelligence.",
        capabilities=[
            "Recognize job-update emails like application receipts, interview invites, and decisions.",
            "Enrich your future application timeline with inbox-derived signals.",
            "Help surface job communication context without making Gmail your sign-in method.",
        ],
        permissions=[
            "Read-only Gmail mailbox access via Google OAuth.",
            "Google account email is used to label the mailbox connection in Settings.",
            "Disconnecting removes the stored refresh token and stops future mailbox access.",
        ],
        readiness=readiness,
        planned_features=[
            "Inbox-powered application status detection",
            "Timeline enrichment from recruiter communications",
            "Optional service-level scan controls and summaries in a later phase",
        ],
        actions=actions,
    )


def _calendar_detail() -> ServiceDetail:
    return ServiceDetail(
        key="calendar_sync",
        label="Calendar Sync",
        status="coming_soon",
        connected=False,
        account_label="Planned for a future release.",
        availability="coming_soon",
        description="Calendar Sync will help UAH coordinate interview timing, reminders, and event context when the service launches.",
        capabilities=[
            "Match interview invites to tracked applications.",
            "Highlight upcoming conversations and scheduling windows.",
            "Reduce manual copy-and-paste between recruiting emails and your calendar.",
        ],
        permissions=[
            "No calendar access is requested in this release.",
            "Any future calendar permissions will be explained clearly before opt-in.",
        ],
        readiness=ServiceReadiness(
            title="On the roadmap",
            description="This service is being designed for a future release and is not yet connectable.",
            tone="muted",
        ),
        planned_features=[
            "Interview scheduling awareness",
            "Reminder and event enrichment",
            "Meeting context linked back to job applications",
        ],
        actions=[_coming_soon_action()],
    )


def _resume_imports_detail() -> ServiceDetail:
    return ServiceDetail(
        key="resume_imports",
        label="Resume Imports",
        status="coming_soon",
        connected=False,
        account_label="Planned for a future release.",
        availability="coming_soon",
        description="Resume Imports will make it easier to bring documents into UAH from external services without rebuilding your profile by hand.",
        capabilities=[
            "Import resumes and supporting documents from connected storage providers.",
            "Keep document sources organized for future autofill workflows.",
            "Reduce friction when refreshing resumes across multiple applications.",
        ],
        permissions=[
            "No document-provider access is requested in this release.",
            "Future providers will explain exactly which files or folders are shared.",
        ],
        readiness=ServiceReadiness(
            title="Planned for later",
            description="This service is intentionally listed early so Settings reads as a reusable integrations hub from day one.",
            tone="muted",
        ),
        planned_features=[
            "External resume import flows",
            "Document source organization",
            "Future profile/document sync helpers",
        ],
        actions=[_coming_soon_action()],
    )


def _coming_soon_summary(detail: ServiceDetail, category: str, summary: str) -> ServiceSummary:
    return ServiceSummary(
        key=detail.key,
        label=detail.label,
        category=category,
        status=detail.status,
        connected=False,
        availability=detail.availability,
        summary=summary,
        account_label=detail.account_label,
        primary_action=_coming_soon_action(),
        can_view_details=True,
    )


def list_service_summaries(user: User) -> list[ServiceSummary]:
    calendar_detail = _calendar_detail()
    resume_imports_detail = _resume_imports_detail()
    return [
        _gmail_summary(user),
        _coming_soon_summary(
            calendar_detail,
            category="productivity",
            summary="Prepare for future interview scheduling and reminder enrichment.",
        ),
        _coming_soon_summary(
            resume_imports_detail,
            category="documents",
            summary="Bring resumes and related documents into UAH from future connected sources.",
        ),
    ]


def get_service_detail(user: User, service_key: str) -> ServiceDetail:
    normalized_key = (service_key or "").strip().lower()
    if normalized_key == "gmail":
        return _gmail_detail(user)
    if normalized_key == "calendar_sync":
        return _calendar_detail()
    if normalized_key == "resume_imports":
        return _resume_imports_detail()
    raise KeyError(normalized_key)
