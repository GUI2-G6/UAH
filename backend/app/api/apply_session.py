from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.user import User
from app.models.apply_session import ApplySession
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/apply-sessions", tags=["apply-sessions"])


class StartSessionRequest(BaseModel):
    job_title: str
    company: str
    job_url: Optional[str] = None
    platform: Optional[str] = None
    resume_id: Optional[int] = None


class SessionEventRequest(BaseModel):
    type: str
    data: Optional[dict] = None


class FinalizeSessionRequest(BaseModel):
    status: str
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
        job_url=payload.job_url,
        platform=payload.platform,
        resume_id=payload.resume_id,
        status="in_progress",
        events=[],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "started_at": session.started_at, "status": session.status}


@router.post("/{session_id}/event")
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

    events = list(session.events or [])
    events.append({
        "type": payload.type,
        "data": payload.data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    session.events = events
    db.commit()
    return {"id": session.id, "event_count": len(events)}


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
    if payload.notes:
        session.notes = payload.notes
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "status": session.status,
        "started_at": session.started_at,
        "finalized_at": session.finalized_at,
        "job_title": session.job_title,
        "company": session.company,
        "notes": session.notes,
        "event_count": len(session.events or []),
    }


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
            "job_title": s.job_title,
            "company": s.company,
            "status": s.status,
            "platform": s.platform,
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
    return {
        "id": session.id,
        "job_title": session.job_title,
        "company": session.company,
        "job_url": session.job_url,
        "status": session.status,
        "platform": session.platform,
        "resume_id": session.resume_id,
        "notes": session.notes,
        "events": session.events or [],
        "event_count": len(session.events or []),
        "started_at": session.started_at,
        "finalized_at": session.finalized_at,
    }
