"""
Database Session Management
============================

This module sets up the SQLAlchemy engine and session factory.

How DB session will be injected:
  - Import `get_db` as a FastAPI dependency in your route handlers:

      from fastapi import Depends
      from sqlalchemy.orm import Session
      from app.db.session import get_db

      @router.get("/items")
      async def list_items(db: Session = Depends(get_db)):
          items = db.query(Item).all()
          return items

  - The `get_db` generator handles opening and closing the session
    automatically per-request via FastAPI's dependency injection.

Important:
  - The engine is created once at module load using DATABASE_URL.
  - Each request gets its own Session via SessionLocal().
  - Sessions are automatically closed after the request completes.
"""

from __future__ import annotations

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_lock = threading.Lock()
_engine = None
_SessionMaker = None

def init_engine() -> None:
    """Initialize the global SQLAlchemy engine + session factory.

    This is intentionally lazy so importing route modules (e.g. in unit tests)
    does not require database env vars to be present.
    """

    global _engine, _SessionMaker
    if _engine is not None and _SessionMaker is not None:
        return

    with _lock:
        if _engine is not None and _SessionMaker is not None:
            return

        from app.core.config import settings

        _engine = create_engine(
            settings.DATABASE_URL,
            echo=True,  # Log all SQL statements (dev only)
            pool_pre_ping=True,  # Verify connections before use
        )
        _SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine():
    init_engine()
    return _engine


def SessionLocal():
    """Backward-compatible helper that returns a new DB session."""
    init_engine()
    return _SessionMaker()


def get_db():
    """
    FastAPI dependency that yields a database session.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The session is committed/rolled-back and closed automatically.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
