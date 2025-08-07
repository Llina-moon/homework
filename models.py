from datetime import datetime
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """Represents a payment made by a user."""

    id: int
    user: str
    amount: float
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Payout(BaseModel):
    """Represents an outgoing payout to a user."""

    id: int
    transaction_id: int
    amount: float
    status: str = Field(default="pending", description="pending or confirmed")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Balance(BaseModel):
    """Represents current and pending balances for a user."""

    available: float
    pending: float
