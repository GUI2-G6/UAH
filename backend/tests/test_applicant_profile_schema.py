"""Regression: profile schemas must accept messy contact values from imports (e.g. apply-review)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.applicant_profile import ProfileResponse


def test_profile_response_accepts_invalid_email_from_storage():
    payload = {
        "id": 1,
        "user_id": 42,
        "name": "Imported",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "email": "person@example",
    }
    model = ProfileResponse.model_validate(payload)
    assert model.email == "person@example"


def test_profile_response_accepts_invalid_phone_from_storage():
    payload = {
        "id": 1,
        "user_id": 42,
        "name": "Imported",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "phone": "not-a-phone",
    }
    model = ProfileResponse.model_validate(payload)
    assert model.phone == "not-a-phone"


def test_profile_response_blank_email_becomes_none():
    payload = {
        "id": 1,
        "user_id": 42,
        "name": "Imported",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "email": "   ",
    }
    model = ProfileResponse.model_validate(payload)
    assert model.email is None


def test_profile_response_valid_email_still_normalized():
    payload = {
        "id": 1,
        "user_id": 42,
        "name": "Imported",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "email": "  Jane.Doe@Example.COM  ",
    }
    model = ProfileResponse.model_validate(payload)
    assert model.email == "jane.doe@example.com"


def test_profile_response_truncates_overlong_invalid_email():
    long_invalid = "x" * 300 + "@"
    payload = {
        "id": 1,
        "user_id": 42,
        "name": "Imported",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "email": long_invalid,
    }
    model = ProfileResponse.model_validate(payload)
    assert len(model.email or "") == 255


def test_profile_response_rejects_email_over_max_after_truncation_path():
    """Valid emails longer than 255 should still fail max_length."""
    long_local = "a" * 251 + "@x.co"
    payload = {
        "id": 1,
        "user_id": 42,
        "name": "Imported",
        "is_active": True,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
        "email": long_local,
    }
    with pytest.raises(ValidationError):
        ProfileResponse.model_validate(payload)
