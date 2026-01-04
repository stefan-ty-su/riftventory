"""Tests for inventory endpoints."""
import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from uuid import uuid4


class TestCreateInventory:
    """Tests for POST /inventories."""

    def test_create_inventory_success(self, client, mock_supabase_client, sample_user_id):
        """Test successful inventory creation."""
        mock_response = Mock()
        mock_response.data = [{
            "inventory_id": str(uuid4()),
            "user_id": sample_user_id,
            "inventory_name": "My Collection",
            "inventory_colour": "#FF5733",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }]
        mock_supabase_client.execute.return_value = mock_response

        payload = {
            "user_id": sample_user_id,
            "inventory_name": "My Collection",
            "inventory_colour": "#FF5733",
        }

        response = client.post("/inventories", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == sample_user_id
        assert data["inventory_name"] == "My Collection"
        assert data["inventory_colour"] == "#FF5733"
        assert "inventory_id" in data
        assert "created_at" in data
        assert "last_updated" in data

    def test_create_inventory_default_values(self, client, mock_supabase_client, sample_user_id):
        """Test inventory creation with default values."""
        mock_response = Mock()
        mock_response.data = [{
            "inventory_id": str(uuid4()),
            "user_id": sample_user_id,
            "inventory_name": "My Inventory",
            "inventory_colour": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }]
        mock_supabase_client.execute.return_value = mock_response

        payload = {
            "user_id": sample_user_id,
        }

        response = client.post("/inventories", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["inventory_name"] == "My Inventory"

    def test_create_inventory_failure(self, client, mock_supabase_client, sample_user_id):
        """Test inventory creation failure."""
        mock_response = Mock()
        mock_response.data = None
        mock_supabase_client.execute.return_value = mock_response

        payload = {
            "user_id": sample_user_id,
            "inventory_name": "Test",
        }

        response = client.post("/inventories", json=payload)

        assert response.status_code == 400
        assert "Failed to create inventory" in response.json()["detail"]


class TestGetInventory:
    """Tests for GET /inventories/{inventory_id}."""

    def test_get_inventory_success(self, client, mock_supabase_client, sample_inventory_data):
        """Test successfully retrieving an inventory."""
        mock_response = Mock()
        mock_response.data = [sample_inventory_data]
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = sample_inventory_data["inventory_id"]
        response = client.get(f"/inventories/{inventory_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["inventory_id"] == inventory_id
        assert data["inventory_name"] == sample_inventory_data["inventory_name"]

    def test_get_inventory_not_found(self, client, mock_supabase_client):
        """Test retrieving a non-existent inventory."""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = str(uuid4())
        response = client.get(f"/inventories/{inventory_id}")

        assert response.status_code == 404
        assert "Inventory not found" in response.json()["detail"]


class TestGetUserInventories:
    """Tests for GET /users/{user_id}/inventories."""

    def test_get_user_inventories_success(self, client, mock_supabase_client, sample_user_id):
        """Test successfully retrieving all inventories for a user."""
        mock_response = Mock()
        mock_response.data = [
            {
                "inventory_id": str(uuid4()),
                "user_id": sample_user_id,
                "inventory_name": "Collection 1",
                "inventory_colour": "#FF5733",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
            {
                "inventory_id": str(uuid4()),
                "user_id": sample_user_id,
                "inventory_name": "Collection 2",
                "inventory_colour": "#33FF57",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
        ]
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/users/{sample_user_id}/inventories")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(inv["user_id"] == sample_user_id for inv in data)

    def test_get_user_inventories_empty(self, client, mock_supabase_client, sample_user_id):
        """Test retrieving inventories for a user with none."""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.execute.return_value = mock_response

        response = client.get(f"/users/{sample_user_id}/inventories")

        assert response.status_code == 200
        assert response.json() == []


class TestUpdateInventory:
    """Tests for PATCH /inventories/{inventory_id}."""

    def test_update_inventory_name(self, client, mock_supabase_client, sample_inventory_data):
        """Test updating inventory name."""
        updated_data = sample_inventory_data.copy()
        updated_data["inventory_name"] = "Updated Name"

        mock_response = Mock()
        mock_response.data = [updated_data]
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = sample_inventory_data["inventory_id"]
        payload = {"inventory_name": "Updated Name"}

        response = client.patch(f"/inventories/{inventory_id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["inventory_name"] == "Updated Name"

    def test_update_inventory_colour(self, client, mock_supabase_client, sample_inventory_data):
        """Test updating inventory colour."""
        updated_data = sample_inventory_data.copy()
        updated_data["inventory_colour"] = "#00FF00"

        mock_response = Mock()
        mock_response.data = [updated_data]
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = sample_inventory_data["inventory_id"]
        payload = {"inventory_colour": "#00FF00"}

        response = client.patch(f"/inventories/{inventory_id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["inventory_colour"] == "#00FF00"

    def test_update_inventory_both_fields(self, client, mock_supabase_client, sample_inventory_data):
        """Test updating both inventory fields."""
        updated_data = sample_inventory_data.copy()
        updated_data["inventory_name"] = "New Name"
        updated_data["inventory_colour"] = "#0000FF"

        mock_response = Mock()
        mock_response.data = [updated_data]
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = sample_inventory_data["inventory_id"]
        payload = {
            "inventory_name": "New Name",
            "inventory_colour": "#0000FF"
        }

        response = client.patch(f"/inventories/{inventory_id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["inventory_name"] == "New Name"
        assert data["inventory_colour"] == "#0000FF"

    def test_update_inventory_no_fields(self, client, mock_supabase_client, sample_inventory_id):
        """Test updating with no fields provided."""
        response = client.patch(f"/inventories/{sample_inventory_id}", json={})

        assert response.status_code == 400
        assert "No fields to update" in response.json()["detail"]

    def test_update_inventory_not_found(self, client, mock_supabase_client):
        """Test updating a non-existent inventory."""
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = str(uuid4())
        payload = {"inventory_name": "Updated"}

        response = client.patch(f"/inventories/{inventory_id}", json=payload)

        assert response.status_code == 404
        assert "Inventory not found" in response.json()["detail"]


class TestDeleteInventory:
    """Tests for DELETE /inventories/{inventory_id}."""

    def test_delete_inventory_success(self, client, mock_supabase_client, sample_inventory_data):
        """Test successfully deleting an inventory."""
        mock_response = Mock()
        mock_response.data = [sample_inventory_data]
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = sample_inventory_data["inventory_id"]
        response = client.delete(f"/inventories/{inventory_id}")

        assert response.status_code == 204

    def test_delete_inventory_not_found(self, client, mock_supabase_client):
        """Test deleting a non-existent inventory."""
        # First call for deleting cards returns empty
        # Second call for deleting inventory returns empty
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.execute.return_value = mock_response

        inventory_id = str(uuid4())
        response = client.delete(f"/inventories/{inventory_id}")

        assert response.status_code == 404
        assert "Inventory not found" in response.json()["detail"]
