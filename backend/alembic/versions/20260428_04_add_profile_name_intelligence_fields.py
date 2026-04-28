"""add applicant profile name intelligence fields

Revision ID: 20260428_04
Revises: 20260428_03
Create Date: 2026-04-28 18:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260428_04"
down_revision = "20260428_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applicant_profiles", sa.Column("middle_name", sa.String(length=100), nullable=True))
    op.add_column("applicant_profiles", sa.Column("full_legal_name", sa.String(length=255), nullable=True))
    op.add_column("applicant_profiles", sa.Column("preferred_name", sa.String(length=100), nullable=True))
    op.add_column("applicant_profiles", sa.Column("suffix", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("applicant_profiles", "suffix")
    op.drop_column("applicant_profiles", "preferred_name")
    op.drop_column("applicant_profiles", "full_legal_name")
    op.drop_column("applicant_profiles", "middle_name")
