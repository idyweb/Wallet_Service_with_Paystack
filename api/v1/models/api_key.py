import uuid
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ARRAY, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from api.db.base_model import BaseModel


class APIKey(BaseModel):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
    PG_UUID(as_uuid=True),
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False
)


    name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    
    hashed_key: Mapped[str] = mapped_column(String(512), nullable=False)


    permissions: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "revoked", "expires_at"),
    )

    def is_active(self) -> bool:
        return (not self.revoked) and (self.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc))
