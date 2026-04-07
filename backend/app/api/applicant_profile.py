from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.user import User
from app.models.applicant_profile import ApplicantProfile
from app.api.deps import get_current_user
from app.schemas.applicant_profile import (
    ProfileCreate, ProfileUpdate, ProfileResponse, ProfileListItem,
)

router = APIRouter(prefix="/api/applicant-profile", tags=["applicant-profile"])

MAX_PROFILES_PER_USER = 10


@router.get("/", response_model=list[ProfileListItem])
def list_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all applicant profiles owned by the authenticated user.

    Returns profiles sorted by active status first, then most recently updated.
    This endpoint powers profile selection UI where users switch between
    tailored application personas.

    Response codes:
    - 200: Profiles returned successfully (possibly empty list).
    """
    return (
        db.query(ApplicantProfile)
        .filter(ApplicantProfile.user_id == current_user.id)
        .order_by(ApplicantProfile.is_active.desc(), ApplicantProfile.updated_at.desc())
        .all()
    )


@router.get("/active", response_model=ProfileResponse)
def get_active_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the currently active applicant profile.

    Returns the single profile flagged as active for the authenticated user.

    Response codes:
    - 200: Active profile returned.
    - 404: No active profile exists for this user.
    """
    profile = (
        db.query(ApplicantProfile)
        .filter(ApplicantProfile.user_id == current_user.id, ApplicantProfile.is_active == True)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No active profile found")
    return profile


@router.post("/", response_model=ProfileResponse, status_code=201)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new applicant profile for the authenticated user.

    Profiles store reusable application data (contact info, education, work
    history, demographics, and links). The first profile created for a user is
    automatically marked active.

    Response codes:
    - 201: Profile created successfully.
    - 429: User reached the maximum allowed profile count.
    """
    count = db.query(func.count(ApplicantProfile.id)).filter(
        ApplicantProfile.user_id == current_user.id
    ).scalar()
    if count >= MAX_PROFILES_PER_USER:
        raise HTTPException(status_code=429, detail=f"Max {MAX_PROFILES_PER_USER} profiles allowed")

    # If this is the first profile, make it active
    is_first = count == 0

    profile = ApplicantProfile(
        user_id=current_user.id,
        is_active=is_first,
        **payload.model_dump(),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(
    profile_id: int = Path(..., ge=1, description="Numeric profile ID to retrieve."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific applicant profile by ID.

    Only profiles owned by the authenticated user are accessible.

    Response codes:
    - 200: Profile returned successfully.
    - 404: Profile not found for this user.
    """
    profile = db.query(ApplicantProfile).filter(
        ApplicantProfile.id == profile_id, ApplicantProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    profile_id: int = Path(..., ge=1, description="Numeric profile ID to update."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update fields on an existing applicant profile.

    Applies partial updates from the request payload. Fields omitted from the
    request remain unchanged.

    Response codes:
    - 200: Profile updated successfully.
    - 404: Profile not found for this user.
    """
    profile = db.query(ApplicantProfile).filter(
        ApplicantProfile.id == profile_id, ApplicantProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/{profile_id}/activate", response_model=ProfileResponse)
def activate_profile(
    profile_id: int = Path(..., ge=1, description="Numeric profile ID to set as active."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark one profile as active and deactivate all others for this user.

    This endpoint enforces a single-active-profile rule used by autofill flows
    and application defaults.

    Response codes:
    - 200: Profile activated successfully.
    - 404: Target profile not found for this user.
    """
    profile = db.query(ApplicantProfile).filter(
        ApplicantProfile.id == profile_id, ApplicantProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Deactivate all others
    db.query(ApplicantProfile).filter(
        ApplicantProfile.user_id == current_user.id,
        ApplicantProfile.id != profile_id,
    ).update({"is_active": False})

    profile.is_active = True
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/{profile_id}")
def delete_profile(
    profile_id: int = Path(..., ge=1, description="Numeric profile ID to delete permanently."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an applicant profile owned by the authenticated user.

    If the deleted profile was active, the most recently updated remaining
    profile is promoted to active automatically.

    Response codes:
    - 200: Profile deleted successfully.
    - 404: Profile not found for this user.
    """
    profile = db.query(ApplicantProfile).filter(
        ApplicantProfile.id == profile_id, ApplicantProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Count the current user's profiles for this delete request.
    profile_count = db.query(func.count(ApplicantProfile.id)).filter(
        ApplicantProfile.user_id == current_user.id
    ).scalar()

    # Prevent deletion of the only profile or the active profile.
    if profile_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your only profile. Create another profile first.",
        )

    else:
        was_active = profile.is_active
        db.delete(profile)
        db.commit()

    # If we deleted the active profile, activate the most recently updated one
    if was_active:
        next_profile = (
            db.query(ApplicantProfile)
            .filter(ApplicantProfile.user_id == current_user.id)
            .order_by(ApplicantProfile.updated_at.desc())
            .first()
        )
        if next_profile:
            next_profile.is_active = True
            db.commit()

    return {"message": "Profile deleted"}
