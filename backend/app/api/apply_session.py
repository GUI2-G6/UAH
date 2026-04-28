from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.user import User
from app.models.apply_session import ApplySession, ApplySessionEvent, TrackedApplication
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


class AnalyticsEventRequest(BaseModel):
    event_type: str
    payload: Optional[dict] = None
    session_id: Optional[int] = None


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


@router.post("/analytics/events")
def add_analytics_event(
    payload: AnalyticsEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event_type = (payload.event_type or "").strip()
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type is required")

    session_id = payload.session_id
    if session_id is not None:
        session = db.query(ApplySession).filter(
            ApplySession.id == session_id,
            ApplySession.user_id == current_user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = db.query(ApplySession).filter(
            ApplySession.user_id == current_user.id
        ).order_by(
            ApplySession.started_at.desc().nullslast(),
            ApplySession.id.desc()
        ).first()
        if not session:
            raise HTTPException(status_code=400, detail="No apply session available to attach analytics event")

    event = ApplySessionEvent(
        session_id=session.id,
        event_type=event_type,
        payload=payload.payload if isinstance(payload.payload, dict) else {},
    )
    db.add(event)
    db.commit()
    return {"ok": True, "session_id": session.id, "event_type": event_type}


@router.get("/analytics/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.query(ApplySession).filter(
        ApplySession.user_id == current_user.id
    ).order_by(ApplySession.started_at.desc().nullslast()).all()
    tracked_rows = db.query(TrackedApplication).filter(
        TrackedApplication.user_id == current_user.id,
        TrackedApplication.selection_state == "active",
    ).all()

    now = datetime.now(timezone.utc)
    seven_days_ago = now.timestamp() - (7 * 24 * 60 * 60)

    status_counts = {
        "started": 0,
        "in_progress": 0,
        "submitted": 0,
        "abandoned": 0,
    }
    for row in sessions:
        key = (row.status or "").strip().lower()
        if key in status_counts:
            status_counts[key] += 1

    tracked_with_updates = sum(1 for row in tracked_rows if row.has_new_update is True)
    stale_submissions = 0
    for row in sessions:
        if (row.status or "").strip().lower() != "submitted":
            continue
        ts = (row.updated_at or row.finalized_at or row.started_at)
        if ts is None:
            stale_submissions += 1
            continue
        if ts.timestamp() < seven_days_ago:
            stale_submissions += 1

    recent_events = db.query(ApplySessionEvent).join(
        ApplySession, ApplySession.id == ApplySessionEvent.session_id
    ).filter(
        ApplySession.user_id == current_user.id
    ).order_by(
        ApplySessionEvent.created_at.desc().nullslast(),
        ApplySessionEvent.id.desc()
    ).limit(8).all()

    return {
        "status_counts": status_counts,
        "tracked_active_count": len(tracked_rows),
        "tracked_updates_count": tracked_with_updates,
        "stale_submissions_count": stale_submissions,
        "recent_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "created_at": event.created_at,
                "payload": event.payload if isinstance(event.payload, dict) else {},
            }
            for event in recent_events
        ],
        "generated_at": now,
    }


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
