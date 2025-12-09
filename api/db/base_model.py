import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, select
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, Session


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class BaseModel(Base):
    """Abstract base model with common fields and CRUD methods"""
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def add(self, db: Session):
        """Add new object to db session without committing"""
        db.add(self)
        return self
    
    def remove(self, db: Session):
        """Mark Object for deletion without committing"""
        db.delete(self)
        return self

    def insert(self, db_session: Session, commit=True):
        """Insert new object to db"""
        db_session.add(self)
        if commit:
            db_session.commit()
            db_session.refresh(self)
        return self

    def update(self, db_session: Session, commit=True):
        """Save updates to the object"""
        self.updated_at = datetime.now(timezone.utc)
        if commit:
            db_session.commit()
            db_session.refresh(self)
        return self

    def delete(self, db_session: Session, commit=True):
        """Delete object from db"""
        db_session.delete(self)
        if commit:
            db_session.commit()
        return self

    @classmethod
    def fetch_one(cls, db_session: Session, **kwargs):
        """Get first matching object"""
        result = db_session.execute(
            select(cls).filter_by(**kwargs)
        )
        return result.scalars().first()

    @classmethod
    def fetch_unique(cls, db_session: Session, **kwargs):
        """Get unique object or None"""
        result = db_session.execute(
            select(cls).filter_by(**kwargs)
        )
        return result.scalars().one_or_none()

    @classmethod
    def fetch_all(cls, db_session: Session, **kwargs):
        """Get all matching objects"""
        result = db_session.execute(
            select(cls).filter_by(**kwargs)
        )
        return result.scalars().all()