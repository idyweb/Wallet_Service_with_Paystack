import uuid
from typing import Optional
from sqlalchemy import JSON, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from api.db.base_model import BaseModel


class WebhookLog(BaseModel):
    __tablename__ = "webhook_logs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'paystack'
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
