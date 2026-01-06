# backend/models/trade.py
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


# ============== Enums ==============

class TradeStatus(str, Enum):
    """Trade lifecycle states."""
    PENDING = "pending"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class TradeDirection(str, Enum):
    """Direction of card in trade."""
    OFFER = "offer"      # Cards being given
    REQUEST = "request"  # Cards being requested


class TradeAction(str, Enum):
    """Actions that can be taken on a trade."""
    CREATE = "create"
    COUNTER = "counter"
    ACCEPT = "accept"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    EXPIRE = "expire"
    COMPLETE = "complete"
    FAIL = "fail"


# ============== Base Schemas ==============

class TradeItemBase(BaseModel):
    """Base schema for a trade item."""
    inventory_id: UUID
    card_id: str
    quantity: int = Field(default=1, ge=1, description="Number of copies to trade")


# ============== Create Schemas ==============

class TradeItemCreate(TradeItemBase):
    """Schema for creating a trade item."""
    pass


class TradeCreate(BaseModel):
    """Schema for creating a new trade offer."""
    recipient_id: str = Field(description="User ID of the trade recipient")
    offered_cards: list[TradeItemCreate] = Field(
        min_length=1,
        description="Cards the initiator is offering"
    )
    requested_cards: list[TradeItemCreate] = Field(
        default=[],
        description="Cards the initiator wants in return"
    )
    initiator_dest_inventory_id: UUID = Field(
        description="Inventory where initiator will receive requested cards"
    )
    expires_in_hours: int = Field(
        default=72,
        ge=1,
        le=168,
        description="Hours until trade expires (1-168)"
    )


# ============== Action Schemas ==============

class TradeAccept(BaseModel):
    """Schema for accepting a trade offer."""
    recipient_dest_inventory_id: UUID = Field(
        description="Inventory where recipient will receive offered cards"
    )


class TradeCounter(BaseModel):
    """Schema for countering a trade offer."""
    offered_cards: list[TradeItemCreate] = Field(
        min_length=1,
        description="Cards being offered in counter"
    )
    requested_cards: list[TradeItemCreate] = Field(
        default=[],
        description="Cards being requested in counter"
    )
    dest_inventory_id: UUID = Field(
        description="Inventory where counter-offerer will receive cards"
    )


class TradeCancel(BaseModel):
    """Schema for cancelling a trade."""
    reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional cancellation reason"
    )


# ============== Response Schemas ==============

class TradeItemResponse(TradeItemBase):
    """Full trade item response."""
    trade_item_id: UUID
    trade_id: UUID
    owner_id: str
    direction: TradeDirection
    is_locked: bool = False
    locked_at: Optional[datetime] = None

    # Joined card data
    card_name: Optional[str] = None
    card_image_url: Optional[str] = None
    card_rarity: Optional[str] = None
    set_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TradeResponse(BaseModel):
    """Full trade response."""
    trade_id: UUID
    initiator_id: str
    recipient_id: str
    status: TradeStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    initiator_confirmed: bool
    recipient_confirmed: bool
    initiator_dest_inventory_id: Optional[UUID] = None
    recipient_dest_inventory_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TradeWithItemsResponse(TradeResponse):
    """Trade response with all items included."""
    offered_items: list[TradeItemResponse] = []
    requested_items: list[TradeItemResponse] = []

    # Joined user data
    initiator_name: Optional[str] = None
    recipient_name: Optional[str] = None


# ============== Query/Filter Schemas ==============

class TradeFilters(BaseModel):
    """Filters for querying trades."""
    status: Optional[TradeStatus] = None
    role: Optional[str] = Field(
        default=None,
        pattern="^(initiator|recipient|any)$",
        description="Filter by user's role in trade"
    )
    include_expired: bool = Field(
        default=False,
        description="Include expired trades"
    )


class TradeListResponse(BaseModel):
    """Paginated list of trades."""
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int


# ============== History Schemas ==============

class TradeHistoryResponse(BaseModel):
    """Trade history entry."""
    history_id: UUID
    trade_id: UUID
    actor_id: str
    action: TradeAction
    previous_status: Optional[TradeStatus] = None
    new_status: Optional[TradeStatus] = None
    details: Optional[dict] = None
    created_at: datetime

    # Joined data
    actor_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============== Statistics Schemas ==============

class TradeSummary(BaseModel):
    """Summary statistics for a user's trades."""
    user_id: str
    total_trades: int
    pending_trades: int
    active_trades: int  # accepted + confirmed
    completed_trades: int
    cancelled_trades: int
    cards_traded: int
    cards_received: int
