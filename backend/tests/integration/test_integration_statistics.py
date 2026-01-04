"""
Integration tests for statistics accuracy and join operations.

These tests verify that statistics are calculated correctly from real data
and that joins return accurate card details.
"""
import pytest


class TestStatisticsAccuracy:
    """Tests for inventory statistics accuracy."""

    def test_stats_match_actual_card_counts(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Statistics should accurately reflect actual card counts."""
        inventory_id = test_inventory["inventory_id"]

        # Add cards with known quantities
        quantities = [3, 5, 2]
        for i, card_id in enumerate(sample_card_ids[:3]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": quantities[i],
                "is_tradeable": i % 2 == 0,  # 0 and 2 are tradeable
            }).execute()

        # Get stats from API
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        assert response.status_code == 200
        stats = response.json()

        # Verify counts
        assert stats["total_unique_cards"] == 3
        assert stats["total_card_quantity"] == sum(quantities)  # 10
        assert stats["total_tradeable"] == quantities[0] + quantities[2]  # 5

    def test_cards_by_rarity_breakdown_accuracy(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """cards_by_rarity should accurately group cards by their rarity."""
        inventory_id = test_inventory["inventory_id"]

        # Add cards with known quantities
        for i, card_id in enumerate(sample_card_ids[:5]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": i + 1,
                "is_tradeable": False,
            }).execute()

        # Get stats from API
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        assert response.status_code == 200
        stats = response.json()

        # Verify rarity breakdown exists and sums correctly
        rarity_total = sum(stats["cards_by_rarity"].values())
        assert rarity_total == stats["total_card_quantity"]

    def test_cards_by_set_breakdown_accuracy(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """cards_by_set should accurately group cards by their set."""
        inventory_id = test_inventory["inventory_id"]

        # Add cards with known quantities
        for i, card_id in enumerate(sample_card_ids[:5]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": (i + 1) * 2,
                "is_tradeable": False,
            }).execute()

        # Get stats from API
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        assert response.status_code == 200
        stats = response.json()

        # Verify set breakdown exists and sums correctly
        set_total = sum(stats["cards_by_set"].values())
        assert set_total == stats["total_card_quantity"]

    def test_stats_update_after_adding_cards(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Statistics should update correctly after adding cards."""
        inventory_id = test_inventory["inventory_id"]

        # Get initial stats
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        initial_stats = response.json()
        initial_quantity = initial_stats["total_card_quantity"]

        # Add a card
        supabase_client.table("inventory_card").insert({
            "inventory_id": inventory_id,
            "card_id": sample_card_ids[0],
            "quantity": 5,
            "is_tradeable": True,
        }).execute()

        # Get updated stats
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        updated_stats = response.json()

        assert updated_stats["total_card_quantity"] == initial_quantity + 5
        assert updated_stats["total_unique_cards"] == initial_stats["total_unique_cards"] + 1

    def test_stats_update_after_removing_cards(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Statistics should update correctly after removing cards."""
        inventory_id = test_inventory["inventory_id"]

        # Add cards first
        for card_id in sample_card_ids[:3]:
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": 2,
                "is_tradeable": False,
            }).execute()

        # Get stats before removal
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        before_stats = response.json()

        # Remove one card
        supabase_client.table("inventory_card").delete().eq(
            "inventory_id", inventory_id
        ).eq("card_id", sample_card_ids[0]).execute()

        # Get stats after removal
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        after_stats = response.json()

        assert after_stats["total_unique_cards"] == before_stats["total_unique_cards"] - 1
        assert after_stats["total_card_quantity"] == before_stats["total_card_quantity"] - 2


class TestJoinAccuracy:
    """Tests for join operation accuracy."""

    def test_card_details_populated_from_joins(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Card details should be correctly populated from joins."""
        inventory_id = test_inventory["inventory_id"]
        card_id = sample_card_ids[0]

        # Add a card
        supabase_client.table("inventory_card").insert({
            "inventory_id": inventory_id,
            "card_id": card_id,
            "quantity": 3,
            "is_tradeable": True,
        }).execute()

        # Get cards with details
        response = integration_client.get(f"/inventories/{inventory_id}/cards")
        assert response.status_code == 200
        cards = response.json()

        assert len(cards) >= 1

        # Find our card
        our_card = next((c for c in cards if c["card_id"] == card_id), None)
        assert our_card is not None

        # Verify joined fields are present
        assert "card_name" in our_card
        assert "card_rarity" in our_card
        assert "set_id" in our_card
        assert our_card["card_name"] is not None

    def test_with_cards_total_calculation(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """/with-cards endpoint should correctly calculate total_cards."""
        inventory_id = test_inventory["inventory_id"]

        # Add cards with specific quantities
        quantities = [4, 6, 10]
        for i, card_id in enumerate(sample_card_ids[:3]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": quantities[i],
                "is_tradeable": False,
            }).execute()

        # Get inventory with cards
        response = integration_client.get(f"/inventories/{inventory_id}/with-cards")
        assert response.status_code == 200
        data = response.json()

        # Verify total_cards matches sum of quantities
        assert data["total_cards"] == sum(quantities)
        assert len(data["cards"]) == 3

    def test_with_cards_includes_all_card_details(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """/with-cards should include full card details for each card."""
        inventory_id = test_inventory["inventory_id"]

        # Add a card
        supabase_client.table("inventory_card").insert({
            "inventory_id": inventory_id,
            "card_id": sample_card_ids[0],
            "quantity": 1,
            "is_tradeable": True,
        }).execute()

        # Get inventory with cards
        response = integration_client.get(f"/inventories/{inventory_id}/with-cards")
        assert response.status_code == 200
        data = response.json()

        # Verify card has all expected fields
        card = data["cards"][0]
        assert "inventory_id" in card
        assert "card_id" in card
        assert "quantity" in card
        assert "is_tradeable" in card
        assert "card_name" in card
        assert "card_rarity" in card
        assert "set_id" in card

    def test_cards_endpoint_returns_correct_inventory_id(
        self, integration_client, supabase_client, test_user, sample_card_ids
    ):
        """Each card should have the correct inventory_id in the response."""
        # Create two inventories
        inv1 = supabase_client.table("inventory").insert({
            "user_id": test_user["user_id"],
            "inventory_name": "Inventory 1",
        }).execute().data[0]

        inv2 = supabase_client.table("inventory").insert({
            "user_id": test_user["user_id"],
            "inventory_name": "Inventory 2",
        }).execute().data[0]

        # Add same card to both inventories
        for inv in [inv1, inv2]:
            supabase_client.table("inventory_card").insert({
                "inventory_id": inv["inventory_id"],
                "card_id": sample_card_ids[0],
                "quantity": 1,
                "is_tradeable": False,
            }).execute()

        # Get cards from first inventory
        response = integration_client.get(f"/inventories/{inv1['inventory_id']}/cards")
        cards = response.json()

        # All cards should have inventory 1's ID
        for card in cards:
            assert card["inventory_id"] == inv1["inventory_id"]

        # Cleanup
        supabase_client.table("inventory").delete().eq(
            "inventory_id", inv2["inventory_id"]
        ).execute()
