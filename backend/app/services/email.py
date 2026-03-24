import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


class EmailNotConfiguredError(RuntimeError):
    pass


def _bool(v: str | None) -> bool:
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}


def send_email(*, to: str, subject: str, text: str, html: str | None = None) -> None:
    """Send an email using SMTP settings from environment variables.

    This is intentionally minimal: it supports TLS/SSL + optional SMTP auth.
    """

    if not settings.EMAILS_ENABLED:
        raise EmailNotConfiguredError("EMAILS_ENABLED is false")

    if not settings.SMTP_HOST:
        raise EmailNotConfiguredError("SMTP_HOST is not set")

    if not settings.SMTP_FROM:
        raise EmailNotConfiguredError("SMTP_FROM is not set")

    if settings.SMTP_USERNAME and not settings.SMTP_PASSWORD:
        raise EmailNotConfiguredError("SMTP_PASSWORD is not set")

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    timeout_s = settings.SMTP_TIMEOUT_SECONDS

    if settings.SMTP_USE_SSL:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout_s, context=context) as server:
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout_s) as server:
        server.ehlo()
        if settings.SMTP_USE_TLS:
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
