from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
import os
from supabase import create_client, Client
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional

from models.card import (
    CardBase,
    CardListResponse,
    CardResponse
)

from models.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
    InventoryWithCardsResponse,
    InventoryCardCreate,
    InventoryCardUpdate,
    InventoryCardAdjust,
    InventoryCardResponse,
    InventoryCardBulkCreate,
    InventoryStats,
)

from models.trade import (
    TradeStatus,
    TradeHistoryAction,
    TradeCreate,
    TradeAccept,
    TradeCancel,
    TradeCounterOffer,
    TradeResponse,
    TradeWithCardsResponse,
    TradeCardResponse,
    TradeCardItem,
    TradeHistoryResponse,
    TradeHistoryListResponse,
    TradeCleanupResponse,
)
from datetime import timedelta

app = FastAPI()

# CORS for Expo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

@app.get("/")
def read_root():
    return {"message": "Riftventory API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ============== Card Information Endpoints ==============
@app.get("/cards", response_model=CardListResponse)
async def get_cards(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
    set_id: Optional[str] = None,
    rarity: Optional[str] = None,
    domain: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(
        "card_id",
        regex="^(card_id|card_name|card_number|attr_energy|attr_power|attr_might|card_rarity|set_id)$",
        description="Field to sort by"
    ),
    sort_desc: Optional[bool] = False
):
    """Get all cards in Riftbound with optional filters and sorting"""

    # First, get total count with filters applied
    count_query = supabase.table("card").select("*", count="exact")

    if set_id:
        count_query = count_query.eq("set_id", set_id)
    if rarity:
        rarity_list = [r.strip() for r in rarity.split(',') if r.strip()]
        if len(rarity_list) == 1:
            count_query = count_query.eq("card_rarity", rarity_list[0])
        else:
            count_query = count_query.in_("card_rarity", rarity_list)
    if domain:
        domain_list = [d.strip() for d in domain.split(',') if d.strip()]
        if len(domain_list) == 1:
            count_query = count_query.contains("card_domain", domain_list)
        else:
            count_query = count_query.overlaps("card_domain", domain_list)
    if search:
        count_query = count_query.ilike("card_name", f"%{search}%")

    count_result = count_query.execute()
    total_count = count_result.count if count_result.count is not None else len(count_result.data)

    # Build the paginated data query with same filters
    query = supabase.table("card").select("*")

    if set_id:
        query = query.eq("set_id", set_id)
    if rarity:
        rarity_list = [r.strip() for r in rarity.split(',') if r.strip()]
        if len(rarity_list) == 1:
            query = query.eq("card_rarity", rarity_list[0])
        else:
            query = query.in_("card_rarity", rarity_list)
    if domain:
        domain_list = [d.strip() for d in domain.split(',') if d.strip()]
        if len(domain_list) == 1:
            query = query.contains("card_domain", domain_list)
        else:
            query = query.overlaps("card_domain", domain_list)
    if search:
        query = query.ilike("card_name", f"%{search}%")

    query = query.order(sort_by, desc=sort_desc)

    # Pagination
    offset = (page-1) * page_size
    query = query.range(offset, offset + page_size-1)

    result = query.execute()
    cards = []
    for item in result.data:
        card_data = {
            "card_id": item["card_id"],
            "set_id": item["set_id"],
            "card_number": item["card_number"],
            "public_code": item["public_code"],
            "card_name": item["card_name"],
            "attr_energy": item["attr_energy"],
            "attr_power": item["attr_power"],
            "attr_might": item["attr_might"],
            "card_type": item["card_type"],
            "card_supertype": item["card_supertype"],
            "card_rarity": item["card_rarity"],
            "card_domain": item["card_domain"],
            "card_image_url": item["card_image_url"],
            "card_artist": item["card_artist"],
            "card_tags": item["card_tags"],
            "alternate_art": item["alternate_art"],
            "overnumbered": item["overnumbered"],
            "signature": item["signature"],
        }

        cards.append(card_data)

    return {
        "cards": cards,
        "total": total_count,
        "page": page,
        "limit": page_size
    }

@app.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: str
):
    query = supabase.table("card").select("*").eq(
        "card_id", card_id
    )

    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Card not found")


    item = result.data[0]

    return item
    

# ============== Inventory Endpoints ==============

@app.post("/inventories", response_model=InventoryResponse)
async def create_inventory(inventory: InventoryCreate):
    """Create a new inventory for a user."""
    data = {
        "user_id": inventory.user_id,
        "inventory_name": inventory.inventory_name,
        "inventory_colour": inventory.inventory_colour,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.table("inventory").insert(data).execute()

    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to create inventory")

    return result.data[0]


@app.get("/inventories/{inventory_id}", response_model=InventoryResponse)
async def get_inventory(inventory_id: UUID):
    """Get a specific inventory by ID."""
    result = supabase.table("inventory").select("*").eq("inventory_id", str(inventory_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Inventory not found")

    return result.data[0]


@app.get("/users/{user_id}/inventories", response_model=list[InventoryResponse])
async def get_user_inventories(user_id: UUID):
    """Get all inventories for a specific user."""
    result = supabase.table("inventory").select("*").eq("user_id", str(user_id)).execute()

    return result.data


@app.patch("/inventories/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(inventory_id: UUID, inventory: InventoryUpdate):
    """Update inventory metadata (name, colour)."""
    update_data = inventory.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["last_updated"] = datetime.utcnow().isoformat()

    result = supabase.table("inventory").update(update_data).eq("inventory_id", str(inventory_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Inventory not found")

    return result.data[0]


@app.delete("/inventories/{inventory_id}", status_code=204)
async def delete_inventory(inventory_id: UUID):
    """Delete an inventory and all its cards."""
    # Delete inventory cards first (cascade should handle this, but being explicit)
    supabase.table("inventory_card").delete().eq("inventory_id", str(inventory_id)).execute()

    # Delete inventory
    result = supabase.table("inventory").delete().eq("inventory_id", str(inventory_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Inventory not found")

    return None


# ============== Inventory Card Endpoints ==============

@app.get("/inventories/{inventory_id}/cards", response_model=list[InventoryCardResponse])
async def get_inventory_cards(
    inventory_id: UUID,
    set_id: Optional[str] = Query(None),
    card_rarity: Optional[str] = Query(None),
    is_tradeable: Optional[bool] = Query(None),
    min_quantity: Optional[int] = Query(None),
):
    """Get all cards in an inventory with optional filters."""
    query = supabase.table("inventory_card").select(
        "*, card:card_id(card_name, card_image_url, card_rarity, set_id)"
    ).eq("inventory_id", str(inventory_id))

    if set_id:
        query = query.eq("card.set_id", set_id)
    if card_rarity:
        query = query.eq("card.card_rarity", card_rarity)
    if is_tradeable is not None:
        query = query.eq("is_tradeable", is_tradeable)
    if min_quantity is not None:
        query = query.gte("quantity", min_quantity)

    result = query.execute()

    # Flatten the joined card data
    cards = []
    for item in result.data:
        card_data = {
            "inventory_id": item["inventory_id"],
            "card_id": item["card_id"],
            "quantity": item["quantity"],
            "is_tradeable": item["is_tradeable"],
        }

        if item.get("card"):
            card_data.update({
                "card_name": item["card"].get("card_name"),
                "card_image_url": item["card"].get("card_image_url"),
                "card_rarity": item["card"].get("card_rarity"),
                "set_id": item["card"].get("set_id"),
            })

        cards.append(card_data)

    return cards


@app.get("/inventories/{inventory_id}/with-cards", response_model=InventoryWithCardsResponse)
async def get_inventory_with_cards(inventory_id: UUID):
    """Get inventory with all its cards included."""
    # Get inventory
    inventory_result = supabase.table("inventory").select("*").eq("inventory_id", str(inventory_id)).execute()

    if not inventory_result.data:
        raise HTTPException(status_code=404, detail="Inventory not found")

    inventory_data = inventory_result.data[0]

    # Get cards
    cards_result = supabase.table("inventory_card").select(
        "*, card:card_id(card_name, card_image_url, card_rarity, set_id)"
    ).eq("inventory_id", str(inventory_id)).execute()

    # Flatten card data
    cards = []
    total_cards = 0
    for item in cards_result.data:
        card_data = {
            "inventory_id": item["inventory_id"],
            "card_id": item["card_id"],
            "quantity": item["quantity"],
            "is_tradeable": item["is_tradeable"],
        }

        if item.get("card"):
            card_data.update({
                "card_name": item["card"].get("card_name"),
                "card_image_url": item["card"].get("card_image_url"),
                "card_rarity": item["card"].get("card_rarity"),
                "set_id": item["card"].get("set_id"),
            })

        cards.append(card_data)
        total_cards += item["quantity"]

    return {
        **inventory_data,
        "cards": cards,
        "total_cards": total_cards,
    }


@app.post("/inventories/{inventory_id}/cards", response_model=InventoryCardResponse, status_code=201)
async def add_card_to_inventory(inventory_id: UUID, card: InventoryCardCreate):
    """Add a card to an inventory or update quantity if it exists."""
    # Check if card already exists in inventory
    existing = supabase.table("inventory_card").select("*").eq(
        "inventory_id", str(inventory_id)
    ).eq("card_id", card.card_id).execute()

    if existing.data:
        # Update existing card
        new_quantity = existing.data[0]["quantity"] + card.quantity
        result = supabase.table("inventory_card").update({
            "quantity": new_quantity,
            "is_tradeable": card.is_tradeable,
        }).eq("inventory_id", str(inventory_id)).eq("card_id", card.card_id).execute()
    else:
        # Insert new card
        data = {
            "inventory_id": str(inventory_id),
            "card_id": card.card_id,
            "quantity": card.quantity,
            "is_tradeable": card.is_tradeable,
        }
        result = supabase.table("inventory_card").insert(data).execute()

    # Update inventory last_updated
    supabase.table("inventory").update({
        "last_updated": datetime.now(timezone.utc).isoformat()
    }).eq("inventory_id", str(inventory_id)).execute()

    if not result.data:
        raise HTTPException(status_code=400, detail="Failed to add card to inventory")

    return result.data[0]


@app.post("/inventories/{inventory_id}/cards/bulk", response_model=list[InventoryCardResponse])
async def add_cards_bulk(inventory_id: UUID, bulk_data: InventoryCardBulkCreate):
    """Add multiple cards to inventory at once."""
    added_cards = []

    for card in bulk_data.cards:
        # Check if card exists
        existing = supabase.table("inventory_card").select("*").eq(
            "inventory_id", str(inventory_id)
        ).eq("card_id", card.card_id).execute()

        if existing.data:
            new_quantity = existing.data[0]["quantity"] + card.quantity
            result = supabase.table("inventory_card").update({
                "quantity": new_quantity,
                "is_tradeable": card.is_tradeable,
            }).eq("inventory_id", str(inventory_id)).eq("card_id", card.card_id).execute()
        else:
            data = {
                "inventory_id": str(inventory_id),
                "card_id": card.card_id,
                "quantity": card.quantity,
                "is_tradeable": card.is_tradeable,
            }
            result = supabase.table("inventory_card").insert(data).execute()

        if result.data:
            added_cards.extend(result.data)

    # Update inventory last_updated
    supabase.table("inventory").update({
        "last_updated": datetime.now(timezone.utc).isoformat()
    }).eq("inventory_id", str(inventory_id)).execute()

    return added_cards


@app.patch("/inventories/{inventory_id}/cards/{card_id}", response_model=InventoryCardResponse)
async def update_inventory_card(
    inventory_id: UUID,
    card_id: str,
    card_update: InventoryCardUpdate
):
    """Update a card in the inventory."""
    update_data = card_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = supabase.table("inventory_card").update(update_data).eq(
        "inventory_id", str(inventory_id)
    ).eq("card_id", card_id).execute()

    # Update inventory last_updated
    supabase.table("inventory").update({
        "last_updated": datetime.now(timezone.utc).isoformat()
    }).eq("inventory_id", str(inventory_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Card not found in inventory")

    return result.data[0]


@app.post("/inventories/{inventory_id}/cards/{card_id}/adjust", response_model=InventoryCardResponse)
async def adjust_card_quantity(
    inventory_id: UUID,
    card_id: str,
    adjust: InventoryCardAdjust
):
    """Adjust card quantity by adding or removing copies."""
    # Get current card
    result = supabase.table("inventory_card").select("*").eq(
        "inventory_id", str(inventory_id)
    ).eq("card_id", card_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Card not found in inventory")

    current_quantity = result.data[0]["quantity"]
    new_quantity = current_quantity + adjust.adjustment

    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Cannot adjust to negative quantity")

    if new_quantity == 0:
        # Remove card from inventory
        supabase.table("inventory_card").delete().eq(
            "inventory_id", str(inventory_id)
        ).eq("card_id", card_id).execute()

        # Update inventory last_updated
        supabase.table("inventory").update({
            "last_updated": datetime.now(timezone.utc).isoformat()
        }).eq("inventory_id", str(inventory_id)).execute()

        return {
            "inventory_id": str(inventory_id),
            "card_id": card_id,
            "quantity": 0,
            "is_tradeable": result.data[0]["is_tradeable"],
        }

    # Update quantity
    update_result = supabase.table("inventory_card").update({
        "quantity": new_quantity
    }).eq("inventory_id", str(inventory_id)).eq("card_id", card_id).execute()

    # Update inventory last_updated
    supabase.table("inventory").update({
        "last_updated": datetime.now(timezone.utc).isoformat()
    }).eq("inventory_id", str(inventory_id)).execute()

    return update_result.data[0]


@app.delete("/inventories/{inventory_id}/cards/{card_id}", status_code=204)
async def remove_card_from_inventory(inventory_id: UUID, card_id: str):
    """Remove a card completely from the inventory."""
    result = supabase.table("inventory_card").delete().eq(
        "inventory_id", str(inventory_id)
    ).eq("card_id", card_id).execute()

    # Update inventory last_updated
    supabase.table("inventory").update({
        "last_updated": datetime.now(timezone.utc).isoformat()
    }).eq("inventory_id", str(inventory_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Card not found in inventory")

    return None


# ============== Statistics Endpoints ==============

@app.get("/inventories/{inventory_id}/stats", response_model=InventoryStats)
async def get_inventory_stats(inventory_id: UUID):
    """Get aggregated statistics for an inventory."""
    # Get all cards with card details
    cards_result = supabase.table("inventory_card").select(
        "quantity, is_tradeable, card:card_id(card_rarity, set_id)"
    ).eq("inventory_id", str(inventory_id)).execute()

    total_unique_cards = len(cards_result.data)
    total_card_quantity = sum(card["quantity"] for card in cards_result.data)
    total_tradeable = sum(card["quantity"] for card in cards_result.data if card["is_tradeable"])

    cards_by_rarity = {}
    cards_by_set = {}

    for card in cards_result.data:
        card_info = card.get("card", {})

        rarity = card_info.get("card_rarity", "Unknown")
        if rarity in cards_by_rarity:
            cards_by_rarity[rarity] += card["quantity"]
        else:
            cards_by_rarity[rarity] = card["quantity"]

        set_id = card_info.get("set_id", "Unknown")
        if set_id in cards_by_set:
            cards_by_set[set_id] += card["quantity"]
        else:
            cards_by_set[set_id] = card["quantity"]

    return {
        "inventory_id": str(inventory_id),
        "total_unique_cards": total_unique_cards,
        "total_card_quantity": total_card_quantity,
        "total_tradeable": total_tradeable,
        "cards_by_rarity": cards_by_rarity,
        "cards_by_set": cards_by_set,
    }


# ============== Trade Endpoints ==============

def _get_trade_cards(trade_id: str, table: str) -> list[dict]:
    """Helper to get trade cards with joined card details."""
    result = supabase.table(table).select(
        "*, card:card_id(card_name, card_image_url, card_rarity, set_id)"
    ).eq("trade_id", trade_id).execute()

    cards = []
    for item in result.data:
        card_data = {
            "card_id": item["card_id"],
            "quantity": item["quantity"],
        }
        if item.get("card"):
            card_data.update({
                "card_name": item["card"].get("card_name"),
                "card_image_url": item["card"].get("card_image_url"),
                "card_rarity": item["card"].get("card_rarity"),
                "set_id": item["card"].get("set_id"),
            })
        cards.append(card_data)
    return cards


def _validate_cards_available(
    inventory_id: str,
    cards: list[TradeCardItem],
    skip_tradeable_check: bool = False
) -> None:
    """Validate that cards exist, are tradeable (unless skipped), and have sufficient available quantity."""
    for card_item in cards:
        result = supabase.table("inventory_card").select(
            "quantity, locked_quantity, is_tradeable"
        ).eq("inventory_id", inventory_id).eq("card_id", card_item.card_id).execute()

        if not result.data:
            raise HTTPException(
                status_code=400,
                detail=f"Card {card_item.card_id} not found in inventory"
            )

        inv_card = result.data[0]
        if not skip_tradeable_check and not inv_card.get("is_tradeable", False):
            raise HTTPException(
                status_code=400,
                detail=f"Card {card_item.card_id} is not marked as tradeable"
            )

        available = inv_card["quantity"] - (inv_card.get("locked_quantity") or 0)
        if available < card_item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient quantity for card {card_item.card_id}. Available: {available}, Requested: {card_item.quantity}"
            )


def _lock_cards(inventory_id: str, cards: list[TradeCardItem]) -> None:
    """Lock cards in escrow by incrementing locked_quantity."""
    for card_item in cards:
        result = supabase.table("inventory_card").select(
            "locked_quantity"
        ).eq("inventory_id", inventory_id).eq("card_id", card_item.card_id).execute()

        current_locked = result.data[0].get("locked_quantity") or 0
        new_locked = current_locked + card_item.quantity

        supabase.table("inventory_card").update({
            "locked_quantity": new_locked
        }).eq("inventory_id", inventory_id).eq("card_id", card_item.card_id).execute()


def _unlock_cards(inventory_id: str, cards: list[dict]) -> None:
    """Unlock cards from escrow by decrementing locked_quantity."""
    for card_item in cards:
        result = supabase.table("inventory_card").select(
            "locked_quantity"
        ).eq("inventory_id", inventory_id).eq("card_id", card_item["card_id"]).execute()

        if result.data:
            current_locked = result.data[0].get("locked_quantity") or 0
            new_locked = max(0, current_locked - card_item["quantity"])

            supabase.table("inventory_card").update({
                "locked_quantity": new_locked
            }).eq("inventory_id", inventory_id).eq("card_id", card_item["card_id"]).execute()


def _transfer_cards(from_inventory_id: str, to_inventory_id: str, cards: list[dict]) -> None:
    """Transfer cards between inventories."""
    for card_item in cards:
        # Decrease from source inventory
        source = supabase.table("inventory_card").select(
            "quantity, locked_quantity"
        ).eq("inventory_id", from_inventory_id).eq("card_id", card_item["card_id"]).execute()

        if source.data:
            current_qty = source.data[0]["quantity"]
            current_locked = source.data[0].get("locked_quantity") or 0
            new_qty = current_qty - card_item["quantity"]
            new_locked = max(0, current_locked - card_item["quantity"])

            if new_qty <= 0:
                supabase.table("inventory_card").delete().eq(
                    "inventory_id", from_inventory_id
                ).eq("card_id", card_item["card_id"]).execute()
            else:
                supabase.table("inventory_card").update({
                    "quantity": new_qty,
                    "locked_quantity": new_locked
                }).eq("inventory_id", from_inventory_id).eq("card_id", card_item["card_id"]).execute()

        # Increase in destination inventory (upsert)
        dest = supabase.table("inventory_card").select(
            "quantity"
        ).eq("inventory_id", to_inventory_id).eq("card_id", card_item["card_id"]).execute()

        if dest.data:
            new_qty = dest.data[0]["quantity"] + card_item["quantity"]
            supabase.table("inventory_card").update({
                "quantity": new_qty
            }).eq("inventory_id", to_inventory_id).eq("card_id", card_item["card_id"]).execute()
        else:
            supabase.table("inventory_card").insert({
                "inventory_id": to_inventory_id,
                "card_id": card_item["card_id"],
                "quantity": card_item["quantity"],
                "is_tradeable": False,
                "locked_quantity": 0
            }).execute()


def _get_next_sequence_number(root_trade_id: str) -> int:
    """Get the next sequence number for a trade history entry in a chain."""
    result = supabase.table("trade_history").select(
        "sequence_number"
    ).eq("root_trade_id", root_trade_id).order(
        "sequence_number", desc=True
    ).limit(1).execute()

    if result.data:
        return result.data[0]["sequence_number"] + 1
    return 0


def _record_trade_history(
    trade_id: str,
    root_trade_id: str,
    actor_user_id: str,
    action: TradeHistoryAction,
    details: Optional[dict] = None
) -> None:
    """Record a trade history entry."""
    sequence_number = _get_next_sequence_number(root_trade_id)

    history_data = {
        "trade_id": trade_id,
        "root_trade_id": root_trade_id,
        "sequence_number": sequence_number,
        "actor_user_id": actor_user_id,
        "action": action.value,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    supabase.table("trade_history").insert(history_data).execute()


def _build_trade_response(trade_id: str, trade: dict) -> dict:
    """Build a full trade response with cards and user names."""
    initiator = supabase.table("user").select("user_name").eq("user_id", trade["initiator_user_id"]).execute()
    recipient = supabase.table("user").select("user_name").eq("user_id", trade["recipient_user_id"]).execute()

    return {
        **trade,
        "escrow_cards": _get_trade_cards(trade_id, "trade_escrow"),
        "requested_cards": _get_trade_cards(trade_id, "trade_recipient"),
        "initiator_user_name": initiator.data[0]["user_name"] if initiator.data else None,
        "recipient_user_name": recipient.data[0]["user_name"] if recipient.data else None,
    }


async def _execute_trade(trade_id: str, trade: dict) -> dict:
    """Execute a trade by transferring cards between inventories."""
    # Get escrow and requested cards
    escrow_cards = supabase.table("trade_escrow").select("*").eq("trade_id", trade_id).execute()
    requested_cards = supabase.table("trade_recipient").select("*").eq("trade_id", trade_id).execute()

    # Lock recipient's cards if any (only if not already locked via accept)
    # Note: For self-transfers and immediate execution, we need to lock here
    is_self_transfer = trade["initiator_user_id"] == trade["recipient_user_id"]
    if requested_cards.data and is_self_transfer:
        _lock_cards(trade["recipient_inventory_id"], [
            TradeCardItem(card_id=c["card_id"], quantity=c["quantity"])
            for c in requested_cards.data
        ])

    # Transfer escrow cards (initiator -> recipient)
    if escrow_cards.data:
        _transfer_cards(
            trade["initiator_inventory_id"],
            trade["recipient_inventory_id"],
            escrow_cards.data
        )

    # Transfer requested cards (recipient -> initiator)
    if requested_cards.data:
        _transfer_cards(
            trade["recipient_inventory_id"],
            trade["initiator_inventory_id"],
            requested_cards.data
        )

    # Update trade status to completed
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("trade").update({
        "status": TradeStatus.COMPLETED.value,
        "initiator_confirmed": True,
        "initiator_confirmed_at": now,
        "recipient_confirmed": True,
        "recipient_confirmed_at": now,
        "resolved_at": now,
    }).eq("trade_id", trade_id).execute()

    # Record COMPLETED history
    root_trade_id = trade.get("root_trade_id") or trade_id
    actor_user_id = trade["initiator_user_id"]
    other_user_id = trade["recipient_user_id"] if actor_user_id == trade["initiator_user_id"] else trade["initiator_user_id"]
    _record_trade_history(
        trade_id=trade_id,
        root_trade_id=root_trade_id,
        actor_user_id=actor_user_id,
        action=TradeHistoryAction.COMPLETED,
        details={
            "other_user_id": other_user_id,
            "escrow_cards_count": len(escrow_cards.data) if escrow_cards.data else 0,
            "requested_cards_count": len(requested_cards.data) if requested_cards.data else 0,
        }
    )

    # Return updated trade
    updated_trade = supabase.table("trade").select("*").eq("trade_id", trade_id).execute()

    initiator = supabase.table("user").select("user_name").eq("user_id", trade["initiator_user_id"]).execute()
    recipient = supabase.table("user").select("user_name").eq("user_id", trade["recipient_user_id"]).execute()

    return {
        **updated_trade.data[0],
        "escrow_cards": _get_trade_cards(trade_id, "trade_escrow"),
        "requested_cards": _get_trade_cards(trade_id, "trade_recipient"),
        "initiator_user_name": initiator.data[0]["user_name"] if initiator.data else None,
        "recipient_user_name": recipient.data[0]["user_name"] if recipient.data else None,
    }


@app.post("/trades", response_model=TradeWithCardsResponse, status_code=201)
async def create_trade(
    trade: TradeCreate,
    x_user_id: UUID = Header(..., description="User ID of the trade initiator")
):
    """Create a new trade offer. Can be used for trades between users or transfers between own inventories."""
    # Verify initiator owns the initiator inventory
    inv_result = supabase.table("inventory").select("user_id").eq(
        "inventory_id", str(trade.initiator_inventory_id)
    ).execute()

    if not inv_result.data:
        raise HTTPException(status_code=404, detail="Initiator inventory not found")
    if inv_result.data[0]["user_id"] != str(x_user_id):
        raise HTTPException(status_code=403, detail="You don't own this inventory")

    # Verify recipient inventory exists
    recipient_inv = supabase.table("inventory").select("user_id").eq(
        "inventory_id", str(trade.recipient_inventory_id)
    ).execute()

    if not recipient_inv.data:
        raise HTTPException(status_code=404, detail="Recipient inventory not found")
    if recipient_inv.data[0]["user_id"] != str(trade.recipient_user_id):
        raise HTTPException(status_code=400, detail="Recipient inventory doesn't belong to recipient user")

    # Check if this is a self-transfer (same user, different inventories)
    is_self_transfer = (x_user_id == trade.recipient_user_id)

    # Validate escrow cards are available (skip tradeable check for self-transfers)
    _validate_cards_available(str(trade.initiator_inventory_id), trade.escrow_cards, skip_tradeable_check=is_self_transfer)

    # Validate requested cards exist in recipient inventory (if any)
    if trade.requested_cards:
        _validate_cards_available(str(trade.recipient_inventory_id), trade.requested_cards, skip_tradeable_check=is_self_transfer)

    # Lock the initiator's cards
    _lock_cards(str(trade.initiator_inventory_id), trade.escrow_cards)

    # Create the trade record with client-generated UUID for self-referencing root_trade_id
    now = datetime.now(timezone.utc).isoformat()
    trade_id = str(uuid4()) # trade_id generated to avoid race conditions. (As opposed to db generation, the obtaining generated UUID)
    trade_data = {
        "trade_id": trade_id,
        "root_trade_id": trade_id,
        "initiator_user_id": str(x_user_id),
        "initiator_inventory_id": str(trade.initiator_inventory_id),
        "recipient_user_id": str(trade.recipient_user_id),
        "recipient_inventory_id": str(trade.recipient_inventory_id),
        "status": TradeStatus.PENDING.value,
        "message": trade.message,
        "created_at": now,
    }

    trade_result = supabase.table("trade").insert(trade_data).execute()

    if not trade_result.data:
        # Unlock cards if trade creation failed
        _unlock_cards(str(trade.initiator_inventory_id), [c.model_dump() for c in trade.escrow_cards])
        raise HTTPException(status_code=400, detail="Failed to create trade")

    # Insert escrow cards
    for card in trade.escrow_cards:
        supabase.table("trade_escrow").insert({
            "trade_id": trade_id,
            "card_id": card.card_id,
            "quantity": card.quantity,
        }).execute()

    # Insert requested cards
    for card in trade.requested_cards:
        supabase.table("trade_recipient").insert({
            "trade_id": trade_id,
            "card_id": card.card_id,
            "quantity": card.quantity,
        }).execute()

    # Record CREATED history
    _record_trade_history(
        trade_id=trade_id,
        root_trade_id=trade_id,
        actor_user_id=str(x_user_id),
        action=TradeHistoryAction.CREATED,
        details={
            "other_user_id": str(trade.recipient_user_id),
            "escrow_cards": [c.model_dump() for c in trade.escrow_cards],
            "requested_cards": [c.model_dump() for c in trade.requested_cards],
        }
    )

    # If self-transfer, auto-accept immediately
    if is_self_transfer:
        return await _execute_trade(trade_id, trade_result.data[0])

    # Get user names for response
    initiator = supabase.table("user").select("user_name").eq("user_id", x_user_id).execute()
    recipient = supabase.table("user").select("user_name").eq("user_id", trade.recipient_user_id).execute()

    return {
        **trade_result.data[0],
        "escrow_cards": _get_trade_cards(trade_id, "trade_escrow"),
        "requested_cards": _get_trade_cards(trade_id, "trade_recipient"),
        "initiator_user_name": initiator.data[0]["user_name"] if initiator.data else None,
        "recipient_user_name": recipient.data[0]["user_name"] if recipient.data else None,
    }


@app.get("/trades/{trade_id}", response_model=TradeWithCardsResponse)
async def get_trade(trade_id: UUID):
    """Get a specific trade by ID with all card details."""
    result = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade = result.data[0]

    # Get user names
    initiator = supabase.table("user").select("user_name").eq("user_id", trade["initiator_user_id"]).execute()
    recipient = supabase.table("user").select("user_name").eq("user_id", trade["recipient_user_id"]).execute()

    return {
        **trade,
        "escrow_cards": _get_trade_cards(str(trade_id), "trade_escrow"),
        "requested_cards": _get_trade_cards(str(trade_id), "trade_recipient"),
        "initiator_user_name": initiator.data[0]["user_name"] if initiator.data else None,
        "recipient_user_name": recipient.data[0]["user_name"] if recipient.data else None,
    }


@app.get("/users/{user_id}/trades", response_model=list[TradeResponse])
async def get_user_trades(
    user_id: UUID,
    status: Optional[str] = Query(None, description="Filter by trade status"),
    role: Optional[str] = Query(None, pattern="^(initiator|recipient|any)$", description="Filter by role"),
):
    """Get all trades for a user with optional filters."""
    user_id_str = str(user_id)
    # Build query for trades where user is initiator OR recipient
    if role == "initiator":
        query = supabase.table("trade").select("*").eq("initiator_user_id", user_id_str)
    elif role == "recipient":
        query = supabase.table("trade").select("*").eq("recipient_user_id", user_id_str)
    else:
        # Get both - need to do two queries and merge
        initiator_trades = supabase.table("trade").select("*").eq("initiator_user_id", user_id_str).execute()
        recipient_trades = supabase.table("trade").select("*").eq("recipient_user_id", user_id_str).execute()

        # Merge and dedupe
        all_trades = {t["trade_id"]: t for t in initiator_trades.data}
        for t in recipient_trades.data:
            all_trades[t["trade_id"]] = t

        trades = list(all_trades.values())

        # Apply status filter
        if status:
            trades = [t for t in trades if t["status"] == status]

        # Sort by created_at descending
        trades.sort(key=lambda x: x["created_at"], reverse=True)
        return trades

    # Single role query
    if status:
        query = query.eq("status", status)

    result = query.order("created_at", desc=True).execute()
    return result.data


# ============== Trade Action Endpoints ==============

@app.post("/trades/{trade_id}/accept", response_model=TradeWithCardsResponse)
async def accept_trade(
    trade_id: UUID,
    x_user_id: UUID = Header(..., description="User ID accepting the trade")
):
    """Accept a pending trade. Locks recipient's cards and waits for initiator confirmation."""
    # Get the trade
    trade_result = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()

    if not trade_result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade = trade_result.data[0]

    # Verify user is the recipient
    if trade["recipient_user_id"] != str(x_user_id):
        raise HTTPException(status_code=403, detail="Only the recipient can accept this trade")

    # Verify trade is pending
    if trade["status"] != TradeStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"Trade cannot be accepted. Current status: {trade['status']}")

    # Get requested cards from trade_recipient table
    requested_cards = supabase.table("trade_recipient").select("*").eq("trade_id", str(trade_id)).execute()

    # Validate recipient has the requested cards available
    if requested_cards.data:
        for card in requested_cards.data:
            _validate_cards_available(
                trade["recipient_inventory_id"],
                [TradeCardItem(card_id=card["card_id"], quantity=card["quantity"])]
            )

    # Lock recipient's cards
    if requested_cards.data:
        _lock_cards(trade["recipient_inventory_id"], [
            TradeCardItem(card_id=c["card_id"], quantity=c["quantity"])
            for c in requested_cards.data
        ])

    # Update trade status to ACCEPTED with recipient auto-confirmed
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("trade").update({
        "status": TradeStatus.ACCEPTED.value,
        "recipient_confirmed": True,
        "recipient_confirmed_at": now,
    }).eq("trade_id", str(trade_id)).execute()

    # Record history
    root_trade_id = trade.get("root_trade_id") or str(trade_id)
    _record_trade_history(
        trade_id=str(trade_id),
        root_trade_id=root_trade_id,
        actor_user_id=str(x_user_id),
        action=TradeHistoryAction.ACCEPTED,
        details={
            "other_user_id": trade["initiator_user_id"],
            "requested_cards_locked": len(requested_cards.data) if requested_cards.data else 0,
        }
    )

    # Return updated trade (update in-memory object instead of re-querying)
    trade["status"] = TradeStatus.ACCEPTED.value
    trade["recipient_confirmed"] = True
    trade["recipient_confirmed_at"] = now
    return _build_trade_response(str(trade_id), trade)


@app.post("/trades/{trade_id}/reject", response_model=TradeWithCardsResponse)
async def reject_trade(
    trade_id: UUID,
    x_user_id: UUID = Header(..., description="User ID rejecting the trade")
):
    """Reject a pending trade. Unlocks initiator's escrowed cards."""
    # Get the trade
    trade_result = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()

    if not trade_result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade = trade_result.data[0]

    # Verify user is the recipient
    if trade["recipient_user_id"] != str(x_user_id):
        raise HTTPException(status_code=403, detail="Only the recipient can reject this trade")

    # Verify trade is pending
    if trade["status"] != TradeStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"Trade cannot be rejected. Current status: {trade['status']}")

    # Get escrow cards and unlock them
    escrow_cards = supabase.table("trade_escrow").select("*").eq("trade_id", str(trade_id)).execute()

    if escrow_cards.data:
        _unlock_cards(trade["initiator_inventory_id"], escrow_cards.data)

    # Update trade status
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("trade").update({
        "status": TradeStatus.REJECTED.value,
        "resolved_at": now,
    }).eq("trade_id", str(trade_id)).execute()

    # Record history
    root_trade_id = trade.get("root_trade_id") or str(trade_id)
    _record_trade_history(
        trade_id=str(trade_id),
        root_trade_id=root_trade_id,
        actor_user_id=str(x_user_id),
        action=TradeHistoryAction.REJECTED,
        details={"other_user_id": trade["initiator_user_id"]}
    )

    return await get_trade(trade_id)


@app.post("/trades/{trade_id}/cancel", response_model=TradeWithCardsResponse)
async def cancel_trade(
    trade_id: UUID,
    cancel_data: TradeCancel = None,
    x_user_id: UUID = Header(..., description="User ID cancelling the trade")
):
    """Cancel a pending trade. Only the initiator can cancel."""
    # Get the trade
    trade_result = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()

    if not trade_result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade = trade_result.data[0]

    # Verify user is the initiator
    if trade["initiator_user_id"] != str(x_user_id):
        raise HTTPException(status_code=403, detail="Only the initiator can cancel this trade")

    # Verify trade is pending
    if trade["status"] != TradeStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"Trade cannot be cancelled. Current status: {trade['status']}")

    # Get escrow cards and unlock them
    escrow_cards = supabase.table("trade_escrow").select("*").eq("trade_id", str(trade_id)).execute()

    if escrow_cards.data:
        _unlock_cards(trade["initiator_inventory_id"], escrow_cards.data)

    # Update trade status
    now = datetime.now(timezone.utc).isoformat()
    update_data = {
        "status": TradeStatus.CANCELLED.value,
        "resolved_at": now,
    }
    if cancel_data and cancel_data.reason:
        update_data["message"] = f"Cancelled: {cancel_data.reason}"

    supabase.table("trade").update(update_data).eq("trade_id", str(trade_id)).execute()

    # Record history
    root_trade_id = trade.get("root_trade_id") or str(trade_id)
    _record_trade_history(
        trade_id=str(trade_id),
        root_trade_id=root_trade_id,
        actor_user_id=str(x_user_id),
        action=TradeHistoryAction.CANCELLED,
        details={
            "other_user_id": trade["recipient_user_id"],
            "reason": cancel_data.reason if cancel_data and cancel_data.reason else None,
        }
    )

    return await get_trade(trade_id)


@app.post("/trades/{trade_id}/counter", response_model=TradeWithCardsResponse, status_code=201)
async def counter_offer_trade(
    trade_id: UUID,
    counter_offer: TradeCounterOffer,
    x_user_id: UUID = Header(..., description="User ID creating the counter-offer")
):
    """Create a counter-offer to a pending trade. Roles swap - recipient becomes new initiator."""
    # Get the original trade
    trade_result = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()

    if not trade_result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    original_trade = trade_result.data[0]

    # Verify user is the current recipient
    if original_trade["recipient_user_id"] != str(x_user_id):
        raise HTTPException(status_code=403, detail="Only the recipient can counter-offer this trade")

    # Verify trade is pending
    if original_trade["status"] != TradeStatus.PENDING.value:
        raise HTTPException(status_code=400, detail=f"Trade cannot be counter-offered. Current status: {original_trade['status']}")

    # The counter-offerer (original recipient) becomes the new initiator
    # They will use the original recipient_inventory_id as their initiator inventory
    new_initiator_inventory_id = original_trade["recipient_inventory_id"]
    new_recipient_inventory_id = original_trade["initiator_inventory_id"]

    # Validate counter-offerer has the escrow cards available
    _validate_cards_available(new_initiator_inventory_id, counter_offer.escrow_cards)

    # Validate requested cards exist in original initiator's inventory (if any)
    if counter_offer.requested_cards:
        _validate_cards_available(new_recipient_inventory_id, counter_offer.requested_cards)

    # Unlock original initiator's escrowed cards
    original_escrow = supabase.table("trade_escrow").select("*").eq("trade_id", str(trade_id)).execute()
    if original_escrow.data:
        _unlock_cards(original_trade["initiator_inventory_id"], original_escrow.data)

    # Update original trade status to COUNTERED
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("trade").update({
        "status": TradeStatus.COUNTERED.value,
        "resolved_at": now,
    }).eq("trade_id", str(trade_id)).execute()

    # Determine root_trade_id and counter_count
    root_trade_id = original_trade.get("root_trade_id") or str(trade_id)
    new_counter_count = (original_trade.get("counter_count") or 0) + 1

    # Lock counter-offerer's cards
    _lock_cards(new_initiator_inventory_id, counter_offer.escrow_cards)

    # Create the new counter-offer trade
    new_trade_id = str(uuid4())
    new_trade_data = {
        "trade_id": new_trade_id,
        "root_trade_id": root_trade_id,
        "parent_trade_id": str(trade_id),
        "counter_count": new_counter_count,
        "initiator_user_id": original_trade["recipient_user_id"],  # Role swap
        "initiator_inventory_id": new_initiator_inventory_id,
        "recipient_user_id": original_trade["initiator_user_id"],  # Role swap
        "recipient_inventory_id": new_recipient_inventory_id,
        "status": TradeStatus.PENDING.value,
        "message": counter_offer.message,
        "created_at": now,
    }

    trade_insert = supabase.table("trade").insert(new_trade_data).execute()

    if not trade_insert.data:
        # Rollback: unlock cards and restore original trade
        _unlock_cards(new_initiator_inventory_id, [c.model_dump() for c in counter_offer.escrow_cards])
        supabase.table("trade").update({
            "status": TradeStatus.PENDING.value,
            "resolved_at": None,
        }).eq("trade_id", str(trade_id)).execute()
        if original_escrow.data:
            _lock_cards(original_trade["initiator_inventory_id"], [
                TradeCardItem(card_id=c["card_id"], quantity=c["quantity"])
                for c in original_escrow.data
            ])
        raise HTTPException(status_code=400, detail="Failed to create counter-offer")

    # Insert escrow cards for new trade
    for card in counter_offer.escrow_cards:
        supabase.table("trade_escrow").insert({
            "trade_id": new_trade_id,
            "card_id": card.card_id,
            "quantity": card.quantity,
        }).execute()

    # Insert requested cards for new trade
    for card in counter_offer.requested_cards:
        supabase.table("trade_recipient").insert({
            "trade_id": new_trade_id,
            "card_id": card.card_id,
            "quantity": card.quantity,
        }).execute()

    # Record history for the counter-offer
    _record_trade_history(
        trade_id=new_trade_id,
        root_trade_id=root_trade_id,
        actor_user_id=str(x_user_id),
        action=TradeHistoryAction.COUNTER_OFFERED,
        details={
            "other_user_id": original_trade["initiator_user_id"],
            "parent_trade_id": str(trade_id),
            "counter_count": new_counter_count,
            "escrow_cards": [c.model_dump() for c in counter_offer.escrow_cards],
            "requested_cards": [c.model_dump() for c in counter_offer.requested_cards],
        }
    )

    return _build_trade_response(new_trade_id, trade_insert.data[0])


@app.post("/trades/{trade_id}/confirm", response_model=TradeWithCardsResponse)
async def confirm_trade(
    trade_id: UUID,
    x_user_id: UUID = Header(..., description="User ID confirming the trade")
):
    """Confirm readiness to complete an accepted trade. Trade executes when both parties confirm."""
    # Get the trade
    trade_result = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()

    if not trade_result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade = trade_result.data[0]
    x_user_id_str = str(x_user_id)

    # Verify user is initiator or recipient
    is_initiator = trade["initiator_user_id"] == x_user_id_str
    is_recipient = trade["recipient_user_id"] == x_user_id_str

    if not is_initiator and not is_recipient:
        raise HTTPException(status_code=403, detail="Only trade participants can confirm")

    # Verify trade is accepted
    if trade["status"] != TradeStatus.ACCEPTED.value:
        raise HTTPException(status_code=400, detail=f"Trade cannot be confirmed. Current status: {trade['status']}")

    # Check if user already confirmed
    if is_initiator and trade.get("initiator_confirmed"):
        raise HTTPException(status_code=400, detail="You have already confirmed this trade")
    if is_recipient and trade.get("recipient_confirmed"):
        raise HTTPException(status_code=400, detail="You have already confirmed this trade")

    # Update confirmation status
    now = datetime.now(timezone.utc).isoformat()
    update_data = {}

    if is_initiator:
        update_data["initiator_confirmed"] = True
        update_data["initiator_confirmed_at"] = now
    else:
        update_data["recipient_confirmed"] = True
        update_data["recipient_confirmed_at"] = now

    supabase.table("trade").update(update_data).eq("trade_id", str(trade_id)).execute()

    # Record history
    root_trade_id = trade.get("root_trade_id") or str(trade_id)
    other_user_id = trade["recipient_user_id"] if is_initiator else trade["initiator_user_id"]
    _record_trade_history(
        trade_id=str(trade_id),
        root_trade_id=root_trade_id,
        actor_user_id=x_user_id_str,
        action=TradeHistoryAction.CONFIRMED,
        details={
            "other_user_id": other_user_id,
            "role": "initiator" if is_initiator else "recipient",
        }
    )

    # Check if both parties have now confirmed
    updated_trade = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()
    trade = updated_trade.data[0]

    if trade.get("initiator_confirmed") and trade.get("recipient_confirmed"):
        # Both confirmed - execute the trade
        return await _execute_trade(str(trade_id), trade)

    return _build_trade_response(str(trade_id), trade)


@app.post("/trades/{trade_id}/unconfirm", response_model=TradeWithCardsResponse)
async def unconfirm_trade(
    trade_id: UUID,
    x_user_id: UUID = Header(..., description="User ID revoking confirmation")
):
    """Revoke confirmation before both parties have confirmed."""
    # Get the trade
    trade_result = supabase.table("trade").select("*").eq("trade_id", str(trade_id)).execute()

    if not trade_result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade = trade_result.data[0]
    x_user_id_str = str(x_user_id)

    # Verify user is initiator or recipient
    is_initiator = trade["initiator_user_id"] == x_user_id_str
    is_recipient = trade["recipient_user_id"] == x_user_id_str

    if not is_initiator and not is_recipient:
        raise HTTPException(status_code=403, detail="Only trade participants can unconfirm")

    # Verify trade is accepted
    if trade["status"] != TradeStatus.ACCEPTED.value:
        raise HTTPException(status_code=400, detail=f"Trade cannot be unconfirmed. Current status: {trade['status']}")

    # Check if user has confirmed
    if is_initiator and not trade.get("initiator_confirmed"):
        raise HTTPException(status_code=400, detail="You have not confirmed this trade")
    if is_recipient and not trade.get("recipient_confirmed"):
        raise HTTPException(status_code=400, detail="You have not confirmed this trade")

    # Check if other party has already confirmed (cannot unconfirm if both confirmed)
    other_confirmed = trade.get("recipient_confirmed") if is_initiator else trade.get("initiator_confirmed")
    if other_confirmed:
        raise HTTPException(status_code=400, detail="Cannot unconfirm after both parties have confirmed")

    # Update confirmation status
    update_data = {}

    if is_initiator:
        update_data["initiator_confirmed"] = False
        update_data["initiator_confirmed_at"] = None
    else:
        update_data["recipient_confirmed"] = False
        update_data["recipient_confirmed_at"] = None

    supabase.table("trade").update(update_data).eq("trade_id", str(trade_id)).execute()

    # Record history
    root_trade_id = trade.get("root_trade_id") or str(trade_id)
    other_user_id = trade["recipient_user_id"] if is_initiator else trade["initiator_user_id"]
    _record_trade_history(
        trade_id=str(trade_id),
        root_trade_id=root_trade_id,
        actor_user_id=x_user_id_str,
        action=TradeHistoryAction.UNCONFIRMED,
        details={
            "other_user_id": other_user_id,
            "role": "initiator" if is_initiator else "recipient",
        }
    )

    # Return updated trade (update in-memory object instead of re-querying)
    if is_initiator:
        trade["initiator_confirmed"] = False
        trade["initiator_confirmed_at"] = None
    else:
        trade["recipient_confirmed"] = False
        trade["recipient_confirmed_at"] = None
    return _build_trade_response(str(trade_id), trade)


# ============== Trade History Endpoints ==============

@app.get("/trades/{trade_id}/history", response_model=TradeHistoryListResponse)
async def get_trade_history(trade_id: UUID):
    """Get full history for a trade chain (including all counter-offers)."""
    # Get the trade to find its root_trade_id
    trade_result = supabase.table("trade").select("root_trade_id").eq("trade_id", str(trade_id)).execute()

    if not trade_result.data:
        raise HTTPException(status_code=404, detail="Trade not found")

    # Use root_trade_id to get the full chain history
    root_trade_id = trade_result.data[0].get("root_trade_id") or str(trade_id)

    # Get all history entries for the chain
    history_result = supabase.table("trade_history").select("*").eq(
        "root_trade_id", root_trade_id
    ).order("sequence_number", desc=False).execute()

    # Get actor names
    history_with_names = []
    for entry in history_result.data:
        actor = supabase.table("user").select("user_name").eq("user_id", entry["actor_user_id"]).execute()
        history_with_names.append({
            **entry,
            "actor_user_name": actor.data[0]["user_name"] if actor.data else None,
        })

    return {
        "history": history_with_names,
        "total": len(history_with_names),
    }


# ============== Trade Supporting Endpoints ==============

@app.get("/users/{user_id}/tradeable-cards", response_model=list[InventoryCardResponse])
async def get_user_tradeable_cards(
    user_id: UUID,
    inventory_id: Optional[UUID] = Query(None, description="Filter by specific inventory"),
):
    """Get all tradeable cards for a user across their inventories."""
    user_id_str = str(user_id)
    # Get user's inventories
    if inventory_id:
        inv_query = supabase.table("inventory").select("inventory_id").eq(
            "inventory_id", str(inventory_id)
        ).eq("user_id", user_id_str)
    else:
        inv_query = supabase.table("inventory").select("inventory_id").eq("user_id", user_id_str)

    inventories = inv_query.execute()

    if not inventories.data:
        return []

    all_cards = []
    for inv in inventories.data:
        cards_result = supabase.table("inventory_card").select(
            "*, card:card_id(card_name, card_image_url, card_rarity, set_id)"
        ).eq("inventory_id", inv["inventory_id"]).eq("is_tradeable", True).execute()

        for item in cards_result.data:
            # Only include cards with available quantity
            available = item["quantity"] - (item.get("locked_quantity") or 0)
            if available > 0:
                card_data = {
                    "inventory_id": item["inventory_id"],
                    "card_id": item["card_id"],
                    "quantity": item["quantity"],
                    "is_tradeable": item["is_tradeable"],
                    "locked_quantity": item.get("locked_quantity") or 0,
                }
                if item.get("card"):
                    card_data.update({
                        "card_name": item["card"].get("card_name"),
                        "card_image_url": item["card"].get("card_image_url"),
                        "card_rarity": item["card"].get("card_rarity"),
                        "set_id": item["card"].get("set_id"),
                    })
                all_cards.append(card_data)

    return all_cards


# ============== Admin Endpoints ==============

async def _cleanup_old_resolved_trades(
    retention_days: int = 30,
    dry_run: bool = True
) -> dict:
    """
    Removes trade_escrow and trade_recipient rows for trades
    resolved more than retention_days ago.

    Returns counts of what was (or would be) deleted.
    """
    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_iso = cutoff_date.isoformat()

    # Find resolved trades older than retention period
    resolved_trades = supabase.table("trade").select("trade_id").not_.is_("resolved_at", "null").lt("resolved_at", cutoff_iso).execute()

    if not resolved_trades.data:
        return {
            "trades_cleaned": 0,
            "escrow_records_deleted": 0,
            "recipient_records_deleted": 0,
        }

    trade_ids = [t["trade_id"] for t in resolved_trades.data]

    # Count records that would be deleted
    escrow_count = 0
    recipient_count = 0

    for trade_id in trade_ids:
        escrow_result = supabase.table("trade_escrow").select("*", count="exact").eq("trade_id", trade_id).execute()
        recipient_result = supabase.table("trade_recipient").select("*", count="exact").eq("trade_id", trade_id).execute()
        escrow_count += len(escrow_result.data) if escrow_result.data else 0
        recipient_count += len(recipient_result.data) if recipient_result.data else 0

    if not dry_run:
        # Actually delete the records
        for trade_id in trade_ids:
            supabase.table("trade_escrow").delete().eq("trade_id", trade_id).execute()
            supabase.table("trade_recipient").delete().eq("trade_id", trade_id).execute()

    return {
        "trades_cleaned": len(trade_ids),
        "escrow_records_deleted": escrow_count,
        "recipient_records_deleted": recipient_count,
    }


@app.delete("/admin/trades/cleanup", response_model=TradeCleanupResponse)
async def cleanup_resolved_trades(
    retention_days: int = Query(default=30, ge=1, description="Keep resolved trades newer than this many days"),
    dry_run: bool = Query(default=True, description="Preview what would be deleted without actually deleting"),
):
    """
    Admin endpoint to clean up old resolved trade records.

    Removes trade_escrow and trade_recipient rows for trades that have been
    resolved (COMPLETED, CANCELLED, REJECTED, EXPIRED) for longer than
    the retention period.

    Use dry_run=True (default) to preview what would be deleted.
    Set dry_run=False to actually perform the cleanup.
    """
    result = await _cleanup_old_resolved_trades(
        retention_days=retention_days,
        dry_run=dry_run
    )

    return TradeCleanupResponse(
        trades_cleaned=result["trades_cleaned"],
        escrow_records_deleted=result["escrow_records_deleted"],
        recipient_records_deleted=result["recipient_records_deleted"],
        dry_run=dry_run,
        retention_days=retention_days,
    )

