from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.user import User
from app.models.apply_session import ApplySession, ApplySessionEvent
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/apply-sessions", tags=["apply-sessions"])


class StartSessionRequest(BaseModel):
    job_title: str
    company: str
    ats_url: Optional[str] = None
    job_url: Optional[str] = None
    job_id: Optional[str] = None
    platform: Optional[str] = None
    resume_id: Optional[int] = None


class SessionEventRequest(BaseModel):
    event_type: str
    payload: Optional[dict] = None


class FinalizeSessionRequest(BaseModel):
    status: str
    fields_matched: Optional[int] = None
    fields_filled: Optional[int] = None
    notes: Optional[str] = None


@router.post("/start", status_code=201)
def start_session(
    payload: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ApplySession(
        user_id=current_user.id,
        job_title=payload.job_title,
        company=payload.company,
        ats_url=payload.ats_url,
        job_url=payload.job_url,
        job_id=payload.job_id,
        platform=payload.platform,
        resume_id=payload.resume_id,
        status="started",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "status": session.status, "started_at": session.started_at}


@router.post("/{session_id}/events")
def add_event(
    session_id: int,
    payload: SessionEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ApplySession).filter(
        ApplySession.id == session_id,
        ApplySession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    event = ApplySessionEvent(
        session_id=session.id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    db.add(event)
    session.status = "in_progress"
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/finalize")
def finalize_session(
    session_id: int,
    payload: FinalizeSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.status not in ("submitted", "abandoned"):
        raise HTTPException(status_code=400, detail="Status must be 'submitted' or 'abandoned'")

    session = db.query(ApplySession).filter(
        ApplySession.id == session_id,
        ApplySession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.status = payload.status
    session.finalized_at = datetime.now(timezone.utc)
    if payload.fields_matched is not None:
        session.fields_matched = payload.fields_matched
    if payload.fields_filled is not None:
        session.fields_filled = payload.fields_filled
    if payload.notes:
        session.notes = payload.notes
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "status": session.status}


@router.get("/")
def list_sessions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ApplySession).filter(ApplySession.user_id == current_user.id)
    if status:
        query = query.filter(ApplySession.status == status)
    sessions = query.order_by(ApplySession.started_at.desc()).all()
    return [
        {
            "id": s.id,
            "job_id": s.job_id,
            "job_title": s.job_title,
            "company": s.company,
            "ats_url": s.ats_url,
            "status": s.status,
            "platform": s.platform,
            "fields_matched": s.fields_matched,
            "fields_filled": s.fields_filled,
            "started_at": s.started_at,
            "finalized_at": s.finalized_at,
        }
        for s in sessions
    ]


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ApplySession).filter(
        ApplySession.id == session_id,
        ApplySession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    events = db.query(ApplySessionEvent).filter(
        ApplySessionEvent.session_id == session.id
    ).order_by(ApplySessionEvent.created_at.asc()).all()

    return {
        "id": session.id,
        "job_id": session.job_id,
        "job_title": session.job_title,
        "company": session.company,
        "ats_url": session.ats_url,
        "job_url": session.job_url,
        "status": session.status,
        "platform": session.platform,
        "resume_id": session.resume_id,
        "fields_matched": session.fields_matched,
        "fields_filled": session.fields_filled,
        "notes": session.notes,
        "started_at": session.started_at,
        "updated_at": session.updated_at,
        "finalized_at": session.finalized_at,
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "payload": e.payload,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }
