"""
Integration tests for database constraints (foreign keys and cascades).

These tests verify that the database enforces referential integrity
and properly cascades deletes.
"""
import pytest
from uuid import uuid4
from postgrest.exceptions import APIError


class TestForeignKeyConstraints:
    """Tests for foreign key constraint enforcement."""

    def test_create_inventory_with_nonexistent_user_fails(self, supabase_client):
        """Creating an inventory for a non-existent user should fail."""
        inventory_data = {
            "user_id": "nonexistent_user_12345",
            "inventory_name": "Test Inventory",
        }

        with pytest.raises(APIError) as exc_info:
            supabase_client.table("inventory").insert(inventory_data).execute()

        # Verify it's a foreign key violation
        assert exc_info.value.code == "23503"
        assert "foreign key constraint" in exc_info.value.message

    def test_add_nonexistent_card_to_inventory_fails(self, supabase_client, test_inventory):
        """Adding a non-existent card to an inventory should fail."""
        card_data = {
            "inventory_id": test_inventory["inventory_id"],
            "card_id": "nonexistent_card_xyz",
            "quantity": 1,
            "is_tradeable": False,
            "locked_quantity": 0,
        }

        with pytest.raises(APIError) as exc_info:
            supabase_client.table("inventory_card").insert(card_data).execute()

        # Should fail due to FK constraint on card_id
        assert exc_info.value.code == "23503"
        assert "inventory_card_card_id_fkey" in exc_info.value.message

    def test_add_card_to_nonexistent_inventory_fails(self, supabase_client, sample_card_id):
        """Adding a card to a non-existent inventory should fail."""
        card_data = {
            "inventory_id": str(uuid4()),  # Random UUID that doesn't exist
            "card_id": sample_card_id,
            "quantity": 1,
            "is_tradeable": False,
            "locked_quantity": 0,
        }

        with pytest.raises(APIError) as exc_info:
            supabase_client.table("inventory_card").insert(card_data).execute()

        # Should fail due to FK constraint on inventory_id
        assert exc_info.value.code == "23503"
        assert "inventory_card_inventory_id_fkey" in exc_info.value.message

    def test_bulk_add_with_one_invalid_card_raises_error(
        self, supabase_client, test_inventory, sample_card_ids
    ):
        """
        Adding an invalid card should raise an FK constraint error.
        Valid cards can be added, but invalid ones will fail.
        """
        valid_card_id = sample_card_ids[0]

        # Add valid card first - should succeed
        supabase_client.table("inventory_card").insert({
            "inventory_id": test_inventory["inventory_id"],
            "card_id": valid_card_id,
            "quantity": 1,
            "is_tradeable": False,
            "locked_quantity": 0,
        }).execute()

        # Try to add invalid card - should fail with FK error
        with pytest.raises(APIError) as exc_info:
            supabase_client.table("inventory_card").insert({
                "inventory_id": test_inventory["inventory_id"],
                "card_id": "invalid_card_id_xyz",
                "quantity": 1,
                "is_tradeable": False,
                "locked_quantity": 0,
            }).execute()

        assert exc_info.value.code == "23503"


class TestCascadeDeletes:
    """Tests for cascade delete behavior."""

    def test_delete_inventory_cascades_to_inventory_cards(
        self, supabase_client, test_user, sample_card_ids
    ):
        """Deleting an inventory should cascade delete all its cards."""
        # Create inventory
        inventory_data = {
            "user_id": test_user["user_id"],
            "inventory_name": "Cascade Test Inventory",
        }
        inv_result = supabase_client.table("inventory").insert(inventory_data).execute()
        inventory_id = inv_result.data[0]["inventory_id"]

        # Add some cards to it
        for card_id in sample_card_ids[:3]:
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": 1,
                "is_tradeable": False,
                "locked_quantity": 0,
            }).execute()

        # Verify cards were added
        cards_before = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", inventory_id
        ).execute()
        assert len(cards_before.data) == 3

        # Delete the inventory
        supabase_client.table("inventory").delete().eq(
            "inventory_id", inventory_id
        ).execute()

        # Verify cards were cascade deleted
        cards_after = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", inventory_id
        ).execute()
        assert len(cards_after.data) == 0

    def test_delete_user_cascades_to_inventories(self, supabase_client, sample_card_ids):
        """Deleting a user should cascade delete all their inventories and cards."""
        # Create a test user
        user_id = f"cascade_test_user_{uuid4().hex[:8]}"
        supabase_client.table("user").insert({
            "user_id": user_id,
            "user_name": f"Cascade Test {user_id}",
        }).execute()

        # Create multiple inventories for the user
        inventory_ids = []
        for i in range(2):
            inv_result = supabase_client.table("inventory").insert({
                "user_id": user_id,
                "inventory_name": f"Cascade Inventory {i}",
            }).execute()
            inventory_ids.append(inv_result.data[0]["inventory_id"])

        # Add cards to each inventory
        for inv_id in inventory_ids:
            for card_id in sample_card_ids[:2]:
                supabase_client.table("inventory_card").insert({
                    "inventory_id": inv_id,
                    "card_id": card_id,
                    "quantity": 1,
                    "is_tradeable": False,
                    "locked_quantity": 0,
                }).execute()

        # Verify setup
        inventories_before = supabase_client.table("inventory").select("*").eq(
            "user_id", user_id
        ).execute()
        assert len(inventories_before.data) == 2

        # Delete the user
        supabase_client.table("user").delete().eq("user_id", user_id).execute()

        # Verify inventories were cascade deleted
        inventories_after = supabase_client.table("inventory").select("*").eq(
            "user_id", user_id
        ).execute()
        assert len(inventories_after.data) == 0

        # Verify inventory_cards were cascade deleted
        for inv_id in inventory_ids:
            cards = supabase_client.table("inventory_card").select("*").eq(
                "inventory_id", inv_id
            ).execute()
            assert len(cards.data) == 0

    def test_inventory_remains_after_removing_all_cards(
        self, supabase_client, test_inventory, sample_card_ids
    ):
        """Removing all cards from an inventory should not delete the inventory."""
        inventory_id = test_inventory["inventory_id"]

        # Add some cards
        for card_id in sample_card_ids[:2]:
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": 1,
                "is_tradeable": False,
                "locked_quantity": 0,
            }).execute()

        # Remove all cards
        supabase_client.table("inventory_card").delete().eq(
            "inventory_id", inventory_id
        ).execute()

        # Verify inventory still exists
        inventory = supabase_client.table("inventory").select("*").eq(
            "inventory_id", inventory_id
        ).execute()
        assert len(inventory.data) == 1
        assert inventory.data[0]["inventory_id"] == inventory_id
