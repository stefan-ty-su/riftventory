"""Tests for inventory card endpoints."""
import pytest
from unittest.mock import Mock
from uuid import uuid4


class TestGetInventoryCards:
    """Tests for GET /inventories/{inventory_id}/cards."""

    def test_get_inventory_cards_success(self, client, mock_supabase_client, sample_inventory_id):
        """Test successfully retrieving all cards in an inventory."""
        mock_response = Mock()
        mock_response.data = [
            {
                "inventory_id": str(sample_inventory_id),
                "card_id": "card1",
                "quantity": 3,
                "is_tradeable": True,
                "card": {
                    "card_name": "Card One",
                    "card_image_url": "https://example.com/card1.png",
                    "card_rarity": "Rare",
                    "set_id": "set001",
                }
            },
            {
                "inventory_id": str(sample_inventory_id),
                "card_id": "card2",
                "quantity": 1,
                "is_tradeable": False,
                "card": {
                    "card_name": "Card Two",
                    "card_image_url": "https://example.com/card2.png",
                    "card_rarity": "Common",
                    "set_id": "set001",
                }
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/cards")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["card_name"] == "Card One"
        assert data[1]["card_name"] == "Card Two"

    def test_get_inventory_cards_with_set_filter(self, client, mock_supabase_client, sample_inventory_id):
        """Test retrieving cards filtered by set_id."""
        mock_response = Mock()
        mock_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card1",
            "quantity": 3,
            "is_tradeable": True,
            "card": {
                "card_name": "Card One",
                "card_image_url": "https://example.com/card1.png",
                "card_rarity": "Rare",
                "set_id": "set001",
            }
        }]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/cards?set_id=set001")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["set_id"] == "set001"

    def test_get_inventory_cards_with_rarity_filter(self, client, mock_supabase_client, sample_inventory_id):
        """Test retrieving cards filtered by rarity."""
        mock_response = Mock()
        mock_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card1",
            "quantity": 3,
            "is_tradeable": True,
            "card": {
                "card_name": "Card One",
                "card_image_url": "https://example.com/card1.png",
                "card_rarity": "Rare",
                "set_id": "set001",
            }
        }]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/cards?card_rarity=Rare")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["card_rarity"] == "Rare"

    def test_get_inventory_cards_with_tradeable_filter(self, client, mock_supabase_client, sample_inventory_id):
        """Test retrieving cards filtered by is_tradeable."""
        mock_response = Mock()
        mock_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card1",
            "quantity": 3,
            "is_tradeable": True,
            "card": {
                "card_name": "Card One",
                "card_image_url": "https://example.com/card1.png",
                "card_rarity": "Rare",
                "set_id": "set001",
            }
        }]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/cards?is_tradeable=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_tradeable"] is True

    def test_get_inventory_cards_with_min_quantity_filter(self, client, mock_supabase_client, sample_inventory_id):
        """Test retrieving cards filtered by minimum quantity."""
        mock_response = Mock()
        mock_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card1",
            "quantity": 5,
            "is_tradeable": True,
            "card": {
                "card_name": "Card One",
                "card_image_url": "https://example.com/card1.png",
                "card_rarity": "Rare",
                "set_id": "set001",
            }
        }]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/cards?min_quantity=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["quantity"] >= 3

    def test_get_inventory_cards_empty(self, client, mock_supabase_client, sample_inventory_id):
        """Test retrieving cards from an empty inventory."""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/inventories/{sample_inventory_id}/cards")

        assert response.status_code == 200
        assert response.json() == []


class TestGetInventoryWithCards:
    """Tests for GET /inventories/{inventory_id}/with-cards."""

    def test_get_inventory_with_cards_success(self, client, mock_supabase_client, sample_inventory_data):
        """Test successfully retrieving inventory with all its cards."""
        # Mock inventory response
        inventory_response = Mock()
        inventory_response.data = [sample_inventory_data]

        # Mock cards response
        cards_response = Mock()
        cards_response.data = [
            {
                "inventory_id": sample_inventory_data["inventory_id"],
                "card_id": "card1",
                "quantity": 3,
                "is_tradeable": True,
                "card": {
                    "card_name": "Card One",
                    "card_image_url": "https://example.com/card1.png",
                    "card_rarity": "Rare",
                    "set_id": "set001",
                }
            },
            {
                "inventory_id": sample_inventory_data["inventory_id"],
                "card_id": "card2",
                "quantity": 2,
                "is_tradeable": False,
                "card": {
                    "card_name": "Card Two",
                    "card_image_url": "https://example.com/card2.png",
                    "card_rarity": "Common",
                    "set_id": "set001",
                }
            },
        ]

        # Setup mock to return different responses for different calls
        mock_supabase_client.execute.side_effect = [inventory_response, cards_response]

        inventory_id = sample_inventory_data["inventory_id"]
        response = client.get(f"/inventories/{inventory_id}/with-cards")

        assert response.status_code == 200
        data = response.json()
        assert data["inventory_id"] == inventory_id
        assert data["inventory_name"] == sample_inventory_data["inventory_name"]
        assert len(data["cards"]) == 2
        assert data["total_cards"] == 5  # 3 + 2

    def test_get_inventory_with_cards_not_found(self, client, mock_supabase_client):
        """Test retrieving a non-existent inventory with cards."""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = str(uuid4())
        response = client.get(f"/inventories/{inventory_id}/with-cards")

        assert response.status_code == 404
        assert "Inventory not found" in response.json()["detail"]


class TestAddCardToInventory:
    """Tests for POST /inventories/{inventory_id}/cards."""

    def test_add_new_card_to_inventory(self, client, mock_supabase_client, sample_inventory_id):
        """Test adding a new card to inventory."""
        # Mock check for existing card (not found)
        existing_response = Mock()
        existing_response.data = []

        # Mock insert response
        insert_response = Mock()
        insert_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 2,
            "is_tradeable": True,
        }]

        # Mock update inventory timestamp
        update_response = Mock()
        update_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            existing_response,
            insert_response,
            update_response
        ]

        payload = {
            "card_id": "card123",
            "quantity": 2,
            "is_tradeable": True,
        }

        response = client.post(f"/inventories/{sample_inventory_id}/cards", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["card_id"] == "card123"
        assert data["quantity"] == 2
        assert data["is_tradeable"] is True

    def test_add_existing_card_to_inventory(self, client, mock_supabase_client, sample_inventory_id):
        """Test adding quantity to an existing card."""
        # Mock existing card
        existing_response = Mock()
        existing_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 3,
            "is_tradeable": True,
        }]

        # Mock update response
        update_response = Mock()
        update_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 5,  # 3 + 2
            "is_tradeable": True,
        }]

        # Mock update inventory timestamp
        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            existing_response,
            update_response,
            timestamp_response
        ]

        payload = {
            "card_id": "card123",
            "quantity": 2,
            "is_tradeable": True,
        }

        response = client.post(f"/inventories/{sample_inventory_id}/cards", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 5

    def test_add_card_to_inventory_failure(self, client, mock_supabase_client, sample_inventory_id):
        """Test failed card addition."""
        # Mock check for existing card
        existing_response = Mock()
        existing_response.data = []

        # Mock failed insert
        insert_response = Mock()
        insert_response.data = None

        # Mock update inventory timestamp
        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            existing_response,
            insert_response,
            timestamp_response
        ]

        payload = {
            "card_id": "card123",
            "quantity": 2,
            "is_tradeable": True,
        }

        response = client.post(f"/inventories/{sample_inventory_id}/cards", json=payload)

        assert response.status_code == 400
        assert "Failed to add card to inventory" in response.json()["detail"]


class TestAddCardsBulk:
    """Tests for POST /inventories/{inventory_id}/cards/bulk."""

    def test_add_multiple_new_cards(self, client, mock_supabase_client, sample_inventory_id):
        """Test adding multiple new cards at once."""
        # Mock responses for two cards - each gets checked and inserted
        empty_check = Mock()
        empty_check.data = []

        insert_response_1 = Mock()
        insert_response_1.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card1",
            "quantity": 2,
            "is_tradeable": True,
        }]

        insert_response_2 = Mock()
        insert_response_2.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card2",
            "quantity": 3,
            "is_tradeable": False,
        }]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            empty_check,
            insert_response_1,
            empty_check,
            insert_response_2,
            timestamp_response
        ]

        payload = {
            "cards": [
                {"card_id": "card1", "quantity": 2, "is_tradeable": True},
                {"card_id": "card2", "quantity": 3, "is_tradeable": False},
            ]
        }

        response = client.post(f"/inventories/{sample_inventory_id}/cards/bulk", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_add_bulk_cards_mixed_new_and_existing(self, client, mock_supabase_client, sample_inventory_id):
        """Test bulk adding with mix of new and existing cards."""
        # First card exists
        existing_response = Mock()
        existing_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card1",
            "quantity": 5,
            "is_tradeable": True,
        }]

        update_response = Mock()
        update_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card1",
            "quantity": 7,
            "is_tradeable": True,
        }]

        # Second card is new
        empty_check = Mock()
        empty_check.data = []

        insert_response = Mock()
        insert_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card2",
            "quantity": 2,
            "is_tradeable": False,
        }]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            existing_response,
            update_response,
            empty_check,
            insert_response,
            timestamp_response
        ]

        payload = {
            "cards": [
                {"card_id": "card1", "quantity": 2, "is_tradeable": True},
                {"card_id": "card2", "quantity": 2, "is_tradeable": False},
            ]
        }

        response = client.post(f"/inventories/{sample_inventory_id}/cards/bulk", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestUpdateInventoryCard:
    """Tests for PATCH /inventories/{inventory_id}/cards/{card_id}."""

    def test_update_card_quantity(self, client, mock_supabase_client, sample_inventory_id):
        """Test updating card quantity."""
        update_response = Mock()
        update_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 5,
            "is_tradeable": True,
        }]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [update_response, timestamp_response]

        payload = {"quantity": 5}

        response = client.patch(
            f"/inventories/{sample_inventory_id}/cards/card123",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 5

    def test_update_card_tradeable_status(self, client, mock_supabase_client, sample_inventory_id):
        """Test updating card tradeable status."""
        update_response = Mock()
        update_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 3,
            "is_tradeable": False,
        }]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [update_response, timestamp_response]

        payload = {"is_tradeable": False}

        response = client.patch(
            f"/inventories/{sample_inventory_id}/cards/card123",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_tradeable"] is False

    def test_update_card_no_fields(self, client, mock_supabase_client, sample_inventory_id):
        """Test updating card with no fields."""
        response = client.patch(
            f"/inventories/{sample_inventory_id}/cards/card123",
            json={}
        )

        assert response.status_code == 400
        assert "No fields to update" in response.json()["detail"]

    def test_update_card_not_found(self, client, mock_supabase_client, sample_inventory_id):
        """Test updating a non-existent card."""
        update_response = Mock()
        update_response.data = []

        mock_supabase_client.execute.return_value = update_response

        payload = {"quantity": 5}

        response = client.patch(
            f"/inventories/{sample_inventory_id}/cards/card123",
            json=payload
        )

        assert response.status_code == 404
        assert "Card not found in inventory" in response.json()["detail"]


class TestAdjustCardQuantity:
    """Tests for POST /inventories/{inventory_id}/cards/{card_id}/adjust."""

    def test_adjust_increase_quantity(self, client, mock_supabase_client, sample_inventory_id):
        """Test increasing card quantity."""
        current_response = Mock()
        current_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 3,
            "is_tradeable": True,
        }]

        update_response = Mock()
        update_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 5,
            "is_tradeable": True,
        }]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            current_response,
            update_response,
            timestamp_response
        ]

        payload = {"adjustment": 2}

        response = client.post(
            f"/inventories/{sample_inventory_id}/cards/card123/adjust",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 5

    def test_adjust_decrease_quantity(self, client, mock_supabase_client, sample_inventory_id):
        """Test decreasing card quantity."""
        current_response = Mock()
        current_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 5,
            "is_tradeable": True,
        }]

        update_response = Mock()
        update_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 3,
            "is_tradeable": True,
        }]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            current_response,
            update_response,
            timestamp_response
        ]

        payload = {"adjustment": -2}

        response = client.post(
            f"/inventories/{sample_inventory_id}/cards/card123/adjust",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 3

    def test_adjust_to_zero_removes_card(self, client, mock_supabase_client, sample_inventory_id):
        """Test adjusting to zero quantity removes the card."""
        current_response = Mock()
        current_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 2,
            "is_tradeable": True,
        }]

        delete_response = Mock()
        delete_response.data = [{}]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [
            current_response,
            delete_response,
            timestamp_response
        ]

        payload = {"adjustment": -2}

        response = client.post(
            f"/inventories/{sample_inventory_id}/cards/card123/adjust",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 0

    def test_adjust_to_negative_fails(self, client, mock_supabase_client, sample_inventory_id):
        """Test that adjusting to negative quantity fails."""
        current_response = Mock()
        current_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
            "quantity": 2,
            "is_tradeable": True,
        }]

        mock_supabase_client.execute.return_value = current_response

        payload = {"adjustment": -5}

        response = client.post(
            f"/inventories/{sample_inventory_id}/cards/card123/adjust",
            json=payload
        )

        assert response.status_code == 400
        assert "Cannot adjust to negative quantity" in response.json()["detail"]

    def test_adjust_card_not_found(self, client, mock_supabase_client, sample_inventory_id):
        """Test adjusting a non-existent card."""
        current_response = Mock()
        current_response.data = []

        mock_supabase_client.execute.return_value = current_response

        payload = {"adjustment": 2}

        response = client.post(
            f"/inventories/{sample_inventory_id}/cards/card123/adjust",
            json=payload
        )

        assert response.status_code == 404
        assert "Card not found in inventory" in response.json()["detail"]


class TestRemoveCardFromInventory:
    """Tests for DELETE /inventories/{inventory_id}/cards/{card_id}."""

    def test_remove_card_success(self, client, mock_supabase_client, sample_inventory_id):
        """Test successfully removing a card from inventory."""
        delete_response = Mock()
        delete_response.data = [{
            "inventory_id": str(sample_inventory_id),
            "card_id": "card123",
        }]

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [delete_response, timestamp_response]

        response = client.delete(f"/inventories/{sample_inventory_id}/cards/card123")

        assert response.status_code == 204

    def test_remove_card_not_found(self, client, mock_supabase_client, sample_inventory_id):
        """Test removing a non-existent card."""
        delete_response = Mock()
        delete_response.data = []

        timestamp_response = Mock()
        timestamp_response.data = [{}]

        mock_supabase_client.execute.side_effect = [delete_response, timestamp_response]

        response = client.delete(f"/inventories/{sample_inventory_id}/cards/card123")

        assert response.status_code == 404
        assert "Card not found in inventory" in response.json()["detail"]
