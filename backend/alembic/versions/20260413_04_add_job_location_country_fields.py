"""add job location country fields

Revision ID: 20260413_04
Revises: 20260413_03
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260413_04"
down_revision = "20260413_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("location_country_code", sa.String(length=2), nullable=True))
    op.add_column("jobs", sa.Column("location_country_name", sa.String(length=120), nullable=True))
    op.create_index("ix_jobs_location_country_code", "jobs", ["location_country_code"], unique=False)
    op.create_index("ix_jobs_location_country_name", "jobs", ["location_country_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_location_country_name", table_name="jobs")
    op.drop_index("ix_jobs_location_country_code", table_name="jobs")
    op.drop_column("jobs", "location_country_name")
    op.drop_column("jobs", "location_country_code")
