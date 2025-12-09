import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import String, BigInteger, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from api.db.base_model import BaseModel


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class TransactionDirection(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


from sqlalchemy import Enum as SQLEnum


class Transaction(BaseModel):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    reference: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False)
    direction: Mapped[TransactionDirection] = mapped_column(SQLEnum(TransactionDirection), nullable=False)

    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False
    )

    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    related_tx_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    wallet = relationship("Wallet", back_populates="transactions")
    user = relationship("User", back_populates="transactions")

