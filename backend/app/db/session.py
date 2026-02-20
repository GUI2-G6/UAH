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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine — single connection pool shared across the application.
# In dev we echo SQL to stdout for debugging. Disable in production.
# ---------------------------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,          # Log all SQL statements (dev only)
    pool_pre_ping=True, # Verify connections before use
)

# ---------------------------------------------------------------------------
# Session factory — call SessionLocal() to get a new session.
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
