import uuid
from typing import Optional

from sqlalchemy import String, BigInteger, Index,ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db.base_model import BaseModel


def generate_wallet_number():
    """
    Simple deterministic/random generation function placeholder.

    """
    import secrets
    return secrets.token_hex(8)  # 16 hex chars


class Wallet(BaseModel):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, nullable=False
    )

    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)


    wallet_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, default=generate_wallet_number)

    # Balance stored in smallest currency unit (e.g., kobo). Use BIGINT for safety.
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="NGN")

    # relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_wallet_user_id", "user_id"),
    )

    def credit(self, amount: int):
        """Increase balance (amount in smallest unit)."""
        self.balance += amount

    def debit(self, amount: int):
        """Decrease balance. Caller must ensure sufficient funds."""
        self.balance -= amount
