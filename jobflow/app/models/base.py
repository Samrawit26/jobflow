"""
SQLAlchemy declarative base.

All database models should inherit from this Base class.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
