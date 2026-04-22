"""
Declarative Base
=================

All SQLAlchemy models inherit from this Base class.

How to create a new model:
  1. Create a file in app/models/ (e.g., app/models/user.py).
  2. Import Base from this module.
  3. Define your model:

      from app.db.base import Base
      from sqlalchemy import Column, Integer, String

      class User(Base):
          __tablename__ = "users"
          id = Column(Integer, primary_key=True, index=True)
          email = Column(String, unique=True, nullable=False)

  4. Import the model in app/models/__init__.py and add a migration
     (alembic revision) for production schema. Tests may use create_all.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
