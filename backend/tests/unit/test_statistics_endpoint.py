"""Tests for inventory statistics endpoint."""
import pytest
from unittest.mock import Mock
from uuid import uuid4


class TestGetInventoryStats:
    """Tests for GET /inventories/{inventory_id}/stats."""

    def test_get_stats_success(self, client, mock_supabase_client, sample_inventory_id):
        """Test successfully retrieving inventory statistics."""
        mock_response = Mock()
        mock_response.data = [
            {
                "quantity": 3,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Rare",
                    "set_id": "set001",
                }
            },
            {
                "quantity": 5,
                "is_tradeable": False,
                "card": {
                    "card_rarity": "Common",
                    "set_id": "set001",
                }
            },
            {
                "quantity": 2,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Rare",
                    "set_id": "set002",
                }
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["inventory_id"] == str(sample_inventory_id)
        assert data["total_unique_cards"] == 3
        assert data["total_card_quantity"] == 10  # 3 + 5 + 2
        assert data["total_tradeable"] == 5  # 3 + 2
        assert data["cards_by_rarity"]["Rare"] == 5  # 3 + 2
        assert data["cards_by_rarity"]["Common"] == 5
        assert data["cards_by_set"]["set001"] == 8  # 3 + 5
        assert data["cards_by_set"]["set002"] == 2

    def test_get_stats_empty_inventory(self, client, mock_supabase_client, sample_inventory_id):
        """Test retrieving statistics for an empty inventory."""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["inventory_id"] == str(sample_inventory_id)
        assert data["total_unique_cards"] == 0
        assert data["total_card_quantity"] == 0
        assert data["total_tradeable"] == 0
        assert data["cards_by_rarity"] == {}
        assert data["cards_by_set"] == {}

    def test_get_stats_all_tradeable(self, client, mock_supabase_client, sample_inventory_id):
        """Test statistics when all cards are tradeable."""
        mock_response = Mock()
        mock_response.data = [
            {
                "quantity": 3,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Rare",
                    "set_id": "set001",
                }
            },
            {
                "quantity": 2,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Common",
                    "set_id": "set001",
                }
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_card_quantity"] == 5
        assert data["total_tradeable"] == 5

    def test_get_stats_none_tradeable(self, client, mock_supabase_client, sample_inventory_id):
        """Test statistics when no cards are tradeable."""
        mock_response = Mock()
        mock_response.data = [
            {
                "quantity": 3,
                "is_tradeable": False,
                "card": {
                    "card_rarity": "Rare",
                    "set_id": "set001",
                }
            },
            {
                "quantity": 2,
                "is_tradeable": False,
                "card": {
                    "card_rarity": "Common",
                    "set_id": "set001",
                }
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_card_quantity"] == 5
        assert data["total_tradeable"] == 0

    def test_get_stats_multiple_rarities(self, client, mock_supabase_client, sample_inventory_id):
        """Test statistics with multiple card rarities."""
        mock_response = Mock()
        mock_response.data = [
            {
                "quantity": 1,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Mythic",
                    "set_id": "set001",
                }
            },
            {
                "quantity": 3,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Rare",
                    "set_id": "set001",
                }
            },
            {
                "quantity": 5,
                "is_tradeable": False,
                "card": {
                    "card_rarity": "Common",
                    "set_id": "set001",
                }
            },
            {
                "quantity": 10,
                "is_tradeable": False,
                "card": {
                    "card_rarity": "Common",
                    "set_id": "set002",
                }
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_unique_cards"] == 4
        assert data["total_card_quantity"] == 19  # 1 + 3 + 5 + 10
        assert data["cards_by_rarity"]["Mythic"] == 1
        assert data["cards_by_rarity"]["Rare"] == 3
        assert data["cards_by_rarity"]["Common"] == 15  # 5 + 10

    def test_get_stats_multiple_sets(self, client, mock_supabase_client, sample_inventory_id):
        """Test statistics with multiple sets."""
        mock_response = Mock()
        mock_response.data = [
            {
                "quantity": 3,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Rare",
                    "set_id": "alpha",
                }
            },
            {
                "quantity": 5,
                "is_tradeable": True,
                "card": {
                    "card_rarity": "Common",
                    "set_id": "beta",
                }
            },
            {
                "quantity": 2,
                "is_tradeable": False,
                "card": {
                    "card_rarity": "Rare",
                    "set_id": "gamma",
                }
            },
            {
                "quantity": 4,
                "is_tradeable": False,
                "card": {
                    "card_rarity": "Common",
                    "set_id": "alpha",
                }
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_unique_cards"] == 4
        assert data["cards_by_set"]["alpha"] == 7  # 3 + 4
        assert data["cards_by_set"]["beta"] == 5
        assert data["cards_by_set"]["gamma"] == 2

    def test_get_stats_missing_card_data(self, client, mock_supabase_client, sample_inventory_id):
        """Test statistics when card data is missing."""
        mock_response = Mock()
        mock_response.data = [
            {
                "quantity": 3,
                "is_tradeable": True,
                "card": {},  # Empty card data (missing rarity and set_id)
            },
            {
                "quantity": 2,
                "is_tradeable": False,
                "card": {},  # Empty card data (missing rarity and set_id)
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_unique_cards"] == 2
        assert data["total_card_quantity"] == 5
        assert data["total_tradeable"] == 3
        # Missing data should be categorized as "Unknown"
        assert data["cards_by_rarity"]["Unknown"] == 5
        assert data["cards_by_set"]["Unknown"] == 5
