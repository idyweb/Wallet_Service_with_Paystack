import uuid
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150), unique=True, nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(200), unique=True, nullable=True)

    # relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
