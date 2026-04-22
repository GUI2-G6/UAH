"""
Models Package
===============

Import all SQLAlchemy models here so that:
  - Base.metadata knows about every table.
  - Alembic can load the full model graph. Apply schema with `alembic upgrade head`.
  - Tests may call `create_all()` for isolated engines as needed.

Example:
  from app.models.user import User        # noqa: F401
  from app.models.job import Job          # noqa: F401

Keep model imports in sync as new tables are added.
"""
from app.models.user import User  # noqa: F401
from app.models.resume import Resume  # noqa: F401
from app.models.parse_job import ParseJob  # noqa: F401
from app.models.applicant_profile import ApplicantProfile  # noqa: F401
from app.models.muse_location import MuseSupportedLocation  # noqa: F401
from app.models.apply_session import ApplySession, ApplySessionEvent  # noqa: F401
from app.models.job import Job, ProviderSyncLog, QuotaUsage  # noqa: F401
from app.models.invite import Invite  # noqa: F401
from app.models.deleted_identity import DeletedIdentity  # noqa: F401
from app.models.beta_access_request import BetaAccessRequest  # noqa: F401
