# backend/app/models/inventory.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional


# ============== Base Schemas ==============

class InventoryCardBase(BaseModel):
    """Base schema for a card entry within an inventory."""
    card_id: str
    quantity: int = Field(default=0, ge=0, description="Number of copies owned")
    is_tradeable: bool = Field(default=False, description="Whether card is available for trade")
    locked_quantity: int = Field(default=0, ge=0, description="Cards locked in pending trades")


class InventoryBase(BaseModel):
    """Base schema for an inventory collection."""
    inventory_name: str = Field(default="My Inventory", max_length=100)
    inventory_colour: Optional[str] = Field(default=None, description="Hex colour for UI display")


# ============== Create Schemas ==============

class InventoryCreate(InventoryBase):
    """Schema for creating a new inventory."""
    user_id: UUID


class InventoryCardCreate(InventoryCardBase):
    """Schema for adding a card to an inventory."""
    pass


class InventoryCardBulkCreate(BaseModel):
    """Schema for adding multiple cards at once (e.g., opening packs)."""
    cards: list[InventoryCardCreate]


# ============== Update Schemas ==============

class InventoryUpdate(BaseModel):
    """Schema for updating inventory metadata."""
    inventory_name: Optional[str] = Field(default=None, max_length=100)
    inventory_colour: Optional[str] = None


class InventoryCardUpdate(BaseModel):
    """Schema for updating a card entry."""
    quantity: Optional[int] = Field(default=None, ge=0)
    is_tradeable: Optional[bool] = None


class InventoryCardAdjust(BaseModel):
    """Schema for adjusting quantity (add/remove cards)."""
    adjustment: int = Field(description="Positive to add, negative to remove")


# ============== Response Schemas ==============

class InventoryCardResponse(InventoryCardBase):
    """Full card entry with inventory context."""
    inventory_id: UUID

    # Joined card data (populated when fetching with card details)
    card_name: Optional[str] = None
    card_image_url: Optional[str] = None
    card_rarity: Optional[str] = None
    set_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def available_quantity(self) -> int:
        """Cards available for trading (not locked in escrow)."""
        return self.quantity - self.locked_quantity

class InventoryResponse(InventoryBase):
    """Full inventory response."""
    inventory_id: UUID
    user_id: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryWithCardsResponse(InventoryResponse):
    """Inventory with all card entries included."""
    cards: list[InventoryCardResponse] = []
    total_cards: int = Field(default=0, description="Sum of all card quantities")


# ============== Query/Filter Schemas ==============

class InventoryCardFilters(BaseModel):
    """Filters for querying inventory cards."""
    set_id: Optional[str] = None
    card_rarity: Optional[str] = None
    is_tradeable: Optional[bool] = None
    min_quantity: Optional[int] = Field(default=None, ge=1)
    card_type: Optional[str] = None
    domain: Optional[str] = None


class InventoryStats(BaseModel):
    """Aggregated inventory statistics."""
    inventory_id: UUID
    total_unique_cards: int
    total_card_quantity: int
    total_tradeable: int
    cards_by_rarity: dict[str, int] = {}
    cards_by_set: dict[str, int] = {}
    collection_completion: Optional[dict[str, float]] = None  # percentage per set