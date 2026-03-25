from fastapi import APIRouter, Depends, HTTPException
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
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(ApplicantProfile).filter(
        ApplicantProfile.id == profile_id, ApplicantProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: int,
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = db.query(ApplicantProfile).filter(
        ApplicantProfile.id == profile_id, ApplicantProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

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
