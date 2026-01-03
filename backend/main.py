from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from supabase import create_client, Client
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

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


# ============== Inventory Endpoints ==============

@app.post("/inventories", response_model=InventoryResponse, status_code=201)
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
async def get_user_inventories(user_id: str):
    """Get all inventories for a specific user."""
    result = supabase.table("inventory").select("*").eq("user_id", user_id).execute()

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

