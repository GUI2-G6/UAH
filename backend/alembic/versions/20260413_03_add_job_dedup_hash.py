"""add job dedup hash and sync dedup metrics

Revision ID: 20260413_03
Revises: 20260413_02
Create Date: 2026-04-13 14:30:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re

from alembic import op
import sqlalchemy as sa


revision = "20260413_03"
down_revision = "20260413_02"
branch_labels = None
depends_on = None

_NOISE_WORDS = (
    "senior",
    "sr",
    "jr",
    "junior",
    "lead",
    "staff",
    "principal",
    "associate",
    "remote",
    "hybrid",
    "inc",
    "llc",
    "ltd",
    "corp",
    "corporation",
    "co",
)


def _normalize_dedup_value(value: str | None) -> str:
    cleaned = (value or "").strip().lower()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    for noise in _NOISE_WORDS:
        cleaned = re.sub(rf"\b{noise}\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _compute_dedup_hash(title: str | None, company: str | None) -> str | None:
    normalized_title = _normalize_dedup_value(title)
    normalized_company = _normalize_dedup_value(company)
    if not normalized_title or not normalized_company:
        return None
    return hashlib.md5(f"{normalized_title}|{normalized_company}".encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column("jobs", sa.Column("dedup_hash", sa.String(length=32), nullable=True))
    op.add_column(
        "provider_sync_log",
        sa.Column("jobs_deduplicated", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    bind = op.get_bind()
    jobs = sa.table(
        "jobs",
        sa.column("id", sa.String()),
        sa.column("title", sa.String()),
        sa.column("company", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("first_seen_at", sa.DateTime(timezone=True)),
        sa.column("dedup_hash", sa.String()),
    )

    rows = bind.execute(
        sa.select(
            jobs.c.id,
            jobs.c.title,
            jobs.c.company,
            jobs.c.is_active,
            jobs.c.first_seen_at,
        )
    ).mappings().all()

    inactive_updates: list[tuple[str, str]] = []
    active_groups: dict[str, list[dict]] = {}
    for row in rows:
        dedup_hash = _compute_dedup_hash(row.get("title"), row.get("company"))
        if not dedup_hash:
            continue
        if bool(row.get("is_active")):
            active_groups.setdefault(dedup_hash, []).append(dict(row))
        else:
            inactive_updates.append((row["id"], dedup_hash))

    for row_id, dedup_hash in inactive_updates:
        bind.execute(
            jobs.update().where(jobs.c.id == row_id).values(dedup_hash=dedup_hash)
        )

    for dedup_hash, group in active_groups.items():
        ordered = sorted(
            group,
            key=lambda item: (
                item.get("first_seen_at") or datetime.max.replace(tzinfo=timezone.utc),
                str(item.get("id") or ""),
            ),
        )
        owner = ordered[0]
        bind.execute(
            jobs.update().where(jobs.c.id == owner["id"]).values(dedup_hash=dedup_hash)
        )
        for duplicate in ordered[1:]:
            bind.execute(
                jobs.update().where(jobs.c.id == duplicate["id"]).values(dedup_hash=None)
            )

    op.create_index(
        "idx_jobs_dedup_hash",
        "jobs",
        ["dedup_hash"],
        unique=True,
        postgresql_where=sa.text("dedup_hash IS NOT NULL AND is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_dedup_hash", table_name="jobs")
    op.drop_column("provider_sync_log", "jobs_deduplicated")
    op.drop_column("jobs", "dedup_hash")
