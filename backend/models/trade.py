# backend/models/trade.py
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any


# ============== Enums ==============

class TradeStatus(str, Enum):
    """Trade lifecycle states."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    COUNTERED = "countered"  # Original trade was counter-offered


class TradeHistoryAction(str, Enum):
    """Actions that can be recorded in trade history."""
    CREATED = "created"
    ACCEPTED = "accepted"
    COUNTER_OFFERED = "counter_offered"
    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


# ============== Base Schemas ==============

class TradeCardItem(BaseModel):
    """A card item in a trade (escrow or recipient)."""
    card_id: str
    quantity: int = Field(default=1, ge=1, description="Number of copies to trade")


# ============== Create Schemas ==============

class TradeCreate(BaseModel):
    """Schema for creating a new trade offer."""
    recipient_user_id: str = Field(description="User ID of the trade recipient")
    initiator_inventory_id: UUID = Field(description="Inventory the initiator is trading from")
    recipient_inventory_id: UUID = Field(description="Inventory the recipient will trade from")
    escrow_cards: list[TradeCardItem] = Field(
        default=[],
        description="Cards the initiator is offering (goes to escrow)"
    )
    requested_cards: list[TradeCardItem] = Field(
        default=[],
        description="Cards the initiator wants from recipient"
    )
    message: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional message to recipient"
    )


# ============== Action Schemas ==============

class TradeAccept(BaseModel):
    """Schema for accepting a trade offer."""
    pass  # No additional data needed - recipient inventory already specified


class TradeCancel(BaseModel):
    """Schema for cancelling a trade."""
    reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional cancellation reason"
    )


class TradeCounterOffer(BaseModel):
    """Schema for creating a counter-offer to a trade."""
    escrow_cards: list[TradeCardItem] = Field(
        min_length=1,
        description="Cards the counter-offerer will give"
    )
    requested_cards: list[TradeCardItem] = Field(
        default=[],
        description="Cards the counter-offerer wants in return"
    )
    message: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional message to the other party"
    )


# ============== Response Schemas ==============

class TradeCardResponse(TradeCardItem):
    """Trade card with joined card details."""
    card_name: Optional[str] = None
    card_image_url: Optional[str] = None
    card_rarity: Optional[str] = None
    set_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TradeResponse(BaseModel):
    """Full trade response."""
    trade_id: UUID
    initiator_user_id: str
    initiator_inventory_id: UUID
    recipient_user_id: str
    recipient_inventory_id: UUID
    status: TradeStatus
    message: Optional[str] = None
    created_at: datetime

    # Counter-offer chain tracking
    root_trade_id: Optional[UUID] = None
    parent_trade_id: Optional[UUID] = None
    counter_count: int = 0

    # Confirmation tracking
    initiator_confirmed: bool = False
    initiator_confirmed_at: Optional[datetime] = None
    recipient_confirmed: bool = False
    recipient_confirmed_at: Optional[datetime] = None

    # Resolution
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TradeWithCardsResponse(TradeResponse):
    """Trade response with all card items included."""
    escrow_cards: list[TradeCardResponse] = []
    requested_cards: list[TradeCardResponse] = []

    # Joined user data
    initiator_user_name: Optional[str] = None
    recipient_user_name: Optional[str] = None


# ============== Query/Filter Schemas ==============

class TradeFilters(BaseModel):
    """Filters for querying trades."""
    status: Optional[TradeStatus] = None
    role: Optional[str] = Field(
        default=None,
        pattern="^(initiator|recipient|any)$",
        description="Filter by user's role in trade"
    )


class TradeListResponse(BaseModel):
    """Paginated list of trades."""
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int


# ============== Statistics Schemas ==============

class TradeSummary(BaseModel):
    """Summary statistics for a user's trades."""
    user_id: str
    total_trades: int
    pending_trades: int
    completed_trades: int
    cancelled_trades: int


# ============== Trade History Schemas ==============

class TradeHistoryCreate(BaseModel):
    """Schema for creating a trade history entry."""
    trade_id: UUID = Field(description="The specific trade this action relates to")
    root_trade_id: UUID = Field(description="The root trade of the counter-offer chain")
    sequence_number: int = Field(ge=0, description="Order of this action in the chain")
    actor_user_id: str = Field(description="User who performed the action")
    action: TradeHistoryAction = Field(description="The action performed")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional action details (cards involved, reason, etc.)"
    )


class TradeHistoryResponse(BaseModel):
    """Response schema for a trade history entry."""
    history_id: UUID
    trade_id: UUID
    root_trade_id: UUID
    sequence_number: int
    actor_user_id: str
    action: TradeHistoryAction
    details: dict[str, Any]
    created_at: datetime

    # Joined data
    actor_user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TradeHistoryListResponse(BaseModel):
    """List of trade history entries for a trade chain."""
    history: list[TradeHistoryResponse]
    total: int


# ============== Admin Schemas ==============

class TradeCleanupResponse(BaseModel):
    """Response from trade cleanup operation."""
    trades_cleaned: int = Field(description="Number of trades whose records were removed")
    escrow_records_deleted: int = Field(description="Number of trade_escrow rows deleted")
    recipient_records_deleted: int = Field(description="Number of trade_recipient rows deleted")
    dry_run: bool = Field(description="Whether this was a preview (no actual deletions)")
    retention_days: int = Field(description="Trades resolved before this many days ago were cleaned")
