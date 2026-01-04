"""
Integration tests for edge cases and filter functionality.

These tests verify handling of edge cases like empty inventories,
zero quantities, large values, and filter combinations.
"""
import pytest


class TestEmptyInventoryEdgeCases:
    """Tests for edge cases with empty inventories."""

    def test_stats_for_empty_inventory(self, integration_client, test_inventory):
        """Stats for an empty inventory should return all zeros."""
        inventory_id = test_inventory["inventory_id"]

        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        assert response.status_code == 200
        stats = response.json()

        assert stats["total_unique_cards"] == 0
        assert stats["total_card_quantity"] == 0
        assert stats["total_tradeable"] == 0
        assert stats["cards_by_rarity"] == {}
        assert stats["cards_by_set"] == {}

    def test_get_cards_from_empty_inventory(self, integration_client, test_inventory):
        """Getting cards from empty inventory should return empty list."""
        inventory_id = test_inventory["inventory_id"]

        response = integration_client.get(f"/inventories/{inventory_id}/cards")
        assert response.status_code == 200
        assert response.json() == []

    def test_with_cards_for_empty_inventory(self, integration_client, test_inventory):
        """/with-cards for empty inventory should return inventory with empty cards list."""
        inventory_id = test_inventory["inventory_id"]

        response = integration_client.get(f"/inventories/{inventory_id}/with-cards")
        assert response.status_code == 200
        data = response.json()

        assert data["inventory_id"] == inventory_id
        assert data["cards"] == []
        assert data["total_cards"] == 0

    def test_user_with_no_inventories(self, integration_client, supabase_client):
        """User with no inventories should return empty list."""
        # Create user with no inventories
        user_id = "empty_user_test_12345"
        supabase_client.table("user").insert({
            "user_id": user_id,
            "user_name": f"Empty User {user_id}",
        }).execute()

        try:
            response = integration_client.get(f"/users/{user_id}/inventories")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            # Cleanup
            supabase_client.table("user").delete().eq("user_id", user_id).execute()


class TestQuantityEdgeCases:
    """Tests for quantity-related edge cases."""

    def test_adjust_quantity_to_zero_removes_card(
        self, integration_client, supabase_client, test_inventory, sample_card_id
    ):
        """Adjusting quantity to zero should remove the card from inventory."""
        inventory_id = test_inventory["inventory_id"]

        # Add card with quantity 3
        supabase_client.table("inventory_card").insert({
            "inventory_id": inventory_id,
            "card_id": sample_card_id,
            "quantity": 3,
            "is_tradeable": False,
        }).execute()

        # Adjust by -3 to reach zero
        response = integration_client.post(
            f"/inventories/{inventory_id}/cards/{sample_card_id}/adjust",
            json={"adjustment": -3}
        )
        assert response.status_code == 200
        assert response.json()["quantity"] == 0

        # Verify card is removed from database
        result = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", inventory_id
        ).eq("card_id", sample_card_id).execute()
        assert len(result.data) == 0

    def test_large_quantity_handling(
        self, integration_client, supabase_client, test_inventory, sample_card_id
    ):
        """Large quantities should be handled correctly."""
        inventory_id = test_inventory["inventory_id"]
        large_quantity = 9999

        # Add card with large quantity
        supabase_client.table("inventory_card").insert({
            "inventory_id": inventory_id,
            "card_id": sample_card_id,
            "quantity": large_quantity,
            "is_tradeable": True,
        }).execute()

        # Verify via stats
        response = integration_client.get(f"/inventories/{inventory_id}/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_card_quantity"] == large_quantity

        # Verify via cards endpoint
        response = integration_client.get(f"/inventories/{inventory_id}/cards")
        cards = response.json()
        card = next(c for c in cards if c["card_id"] == sample_card_id)
        assert card["quantity"] == large_quantity

    def test_rapid_sequential_adjustments(
        self, integration_client, supabase_client, test_inventory, sample_card_id
    ):
        """Rapid sequential adjustments should maintain data consistency."""
        inventory_id = test_inventory["inventory_id"]

        # Add card with initial quantity
        supabase_client.table("inventory_card").insert({
            "inventory_id": inventory_id,
            "card_id": sample_card_id,
            "quantity": 10,
            "is_tradeable": False,
        }).execute()

        # Make rapid adjustments
        adjustments = [+5, -3, +2, -1, +4]
        expected_quantity = 10

        for adj in adjustments:
            response = integration_client.post(
                f"/inventories/{inventory_id}/cards/{sample_card_id}/adjust",
                json={"adjustment": adj}
            )
            assert response.status_code == 200
            expected_quantity += adj

        # Verify final quantity
        response = integration_client.get(f"/inventories/{inventory_id}/cards")
        cards = response.json()
        card = next(c for c in cards if c["card_id"] == sample_card_id)
        assert card["quantity"] == expected_quantity

    def test_add_same_card_multiple_times_increases_quantity(
        self, integration_client, supabase_client, test_inventory, sample_card_id
    ):
        """Adding the same card multiple times should increase quantity."""
        inventory_id = test_inventory["inventory_id"]

        # Add card first time
        response = integration_client.post(
            f"/inventories/{inventory_id}/cards",
            json={"card_id": sample_card_id, "quantity": 2, "is_tradeable": False}
        )
        assert response.status_code == 201

        # Add same card again
        response = integration_client.post(
            f"/inventories/{inventory_id}/cards",
            json={"card_id": sample_card_id, "quantity": 3, "is_tradeable": False}
        )
        assert response.status_code == 201
        assert response.json()["quantity"] == 5  # 2 + 3


class TestFilterFunctionality:
    """Tests for filter functionality on cards endpoint."""

    def test_filter_by_set_id(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Filtering by set_id should return only cards from that set."""
        inventory_id = test_inventory["inventory_id"]

        # Add multiple cards
        for card_id in sample_card_ids[:5]:
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": 1,
                "is_tradeable": False,
            }).execute()

        # Get all cards first to find a set_id
        response = integration_client.get(f"/inventories/{inventory_id}/cards")
        all_cards = response.json()

        if not all_cards or not all_cards[0].get("set_id"):
            pytest.skip("No cards with set_id found")

        target_set_id = all_cards[0]["set_id"]

        # Filter by set_id
        response = integration_client.get(
            f"/inventories/{inventory_id}/cards?set_id={target_set_id}"
        )
        filtered_cards = response.json()

        # All returned cards should have the target set_id
        for card in filtered_cards:
            assert card.get("set_id") == target_set_id

    def test_filter_by_rarity(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Filtering by card_rarity should return only cards with that rarity."""
        inventory_id = test_inventory["inventory_id"]

        # Add multiple cards
        for card_id in sample_card_ids[:5]:
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": 1,
                "is_tradeable": False,
            }).execute()

        # Get all cards first to find a rarity
        response = integration_client.get(f"/inventories/{inventory_id}/cards")
        all_cards = response.json()

        if not all_cards or not all_cards[0].get("card_rarity"):
            pytest.skip("No cards with card_rarity found")

        target_rarity = all_cards[0]["card_rarity"]

        # Filter by rarity
        response = integration_client.get(
            f"/inventories/{inventory_id}/cards?card_rarity={target_rarity}"
        )
        filtered_cards = response.json()

        # All returned cards should have the target rarity
        for card in filtered_cards:
            assert card.get("card_rarity") == target_rarity

    def test_filter_by_tradeable_true(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Filtering by is_tradeable=true should return only tradeable cards."""
        inventory_id = test_inventory["inventory_id"]

        # Add mix of tradeable and non-tradeable cards
        for i, card_id in enumerate(sample_card_ids[:4]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": 1,
                "is_tradeable": i % 2 == 0,  # Even indices are tradeable
            }).execute()

        # Filter by tradeable
        response = integration_client.get(
            f"/inventories/{inventory_id}/cards?is_tradeable=true"
        )
        filtered_cards = response.json()

        # All returned cards should be tradeable
        for card in filtered_cards:
            assert card["is_tradeable"] is True

    def test_filter_by_tradeable_false(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Filtering by is_tradeable=false should return only non-tradeable cards."""
        inventory_id = test_inventory["inventory_id"]

        # Add mix of tradeable and non-tradeable cards
        for i, card_id in enumerate(sample_card_ids[:4]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": 1,
                "is_tradeable": i % 2 == 0,  # Even indices are tradeable
            }).execute()

        # Filter by non-tradeable
        response = integration_client.get(
            f"/inventories/{inventory_id}/cards?is_tradeable=false"
        )
        filtered_cards = response.json()

        # All returned cards should not be tradeable
        for card in filtered_cards:
            assert card["is_tradeable"] is False

    def test_filter_by_min_quantity(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Filtering by min_quantity should return only cards meeting threshold."""
        inventory_id = test_inventory["inventory_id"]

        # Add cards with varying quantities
        quantities = [1, 3, 5, 7, 9]
        for i, card_id in enumerate(sample_card_ids[:5]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": quantities[i],
                "is_tradeable": False,
            }).execute()

        # Filter by min_quantity=5
        response = integration_client.get(
            f"/inventories/{inventory_id}/cards?min_quantity=5"
        )
        filtered_cards = response.json()

        # All returned cards should have quantity >= 5
        for card in filtered_cards:
            assert card["quantity"] >= 5

        # Should have 3 cards (5, 7, 9)
        assert len(filtered_cards) == 3

    def test_multiple_filters_combined(
        self, integration_client, supabase_client, test_inventory, sample_card_ids
    ):
        """Multiple filters should work together correctly."""
        inventory_id = test_inventory["inventory_id"]

        # Add cards with varying properties
        for i, card_id in enumerate(sample_card_ids[:5]):
            supabase_client.table("inventory_card").insert({
                "inventory_id": inventory_id,
                "card_id": card_id,
                "quantity": (i + 1) * 2,  # 2, 4, 6, 8, 10
                "is_tradeable": i % 2 == 0,  # 0, 2, 4 are tradeable
            }).execute()

        # Filter by tradeable AND min_quantity
        response = integration_client.get(
            f"/inventories/{inventory_id}/cards?is_tradeable=true&min_quantity=5"
        )
        filtered_cards = response.json()

        # All returned cards should be tradeable AND have quantity >= 5
        for card in filtered_cards:
            assert card["is_tradeable"] is True
            assert card["quantity"] >= 5
