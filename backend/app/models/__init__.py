"""
Models Package
===============

Import all SQLAlchemy models here so that:
  - Base.metadata knows about every table.
  - Alembic auto-generates migrations correctly.
  - create_all() creates all tables in one call.

Example:
  from app.models.user import User        # noqa: F401
  from app.models.job import Job          # noqa: F401

Currently empty — add imports as you create models.
"""
from app.models.user import User  # noqa: F401
from app.models.resume import Resume  # noqa: F401
from app.models.parse_job import ParseJob  # noqa: F401
from app.models.applicant_profile import ApplicantProfile  # noqa: F401
from app.models.muse_location import MuseSupportedLocation  # noqa: F401
from app.models.apply_session import ApplySession, ApplySessionEvent  # noqa: F401
from app.models.job import Job, ProviderSyncLog, QuotaUsage  # noqa: F401
