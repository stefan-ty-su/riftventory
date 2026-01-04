"""
Conftest for unit tests with mocked Supabase client.

All tests in this directory are automatically marked as unit tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4
import sys
from pathlib import Path

# Add parent directory to path to import main
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from main import app


def pytest_collection_modifyitems(items):
    """Automatically mark all tests in this directory as unit tests."""
    for item in items:
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()

    # Setup table method to return the mock itself for chaining
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.gte.return_value = mock
    mock.limit.return_value = mock

    return mock


@pytest.fixture
def sample_inventory_id():
    """Generate a sample inventory UUID."""
    return uuid4()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return "user123"


@pytest.fixture
def sample_card_id():
    """Generate a sample card ID."""
    return "card456"


@pytest.fixture
def sample_inventory_data(sample_inventory_id, sample_user_id):
    """Create sample inventory data."""
    return {
        "inventory_id": str(sample_inventory_id),
        "user_id": sample_user_id,
        "inventory_name": "Test Inventory",
        "inventory_colour": "#FF5733",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_inventory_card_data(sample_inventory_id, sample_card_id):
    """Create sample inventory card data."""
    return {
        "inventory_id": str(sample_inventory_id),
        "card_id": sample_card_id,
        "quantity": 3,
        "is_tradeable": True,
    }


@pytest.fixture
def sample_inventory_card_with_details(sample_inventory_id, sample_card_id):
    """Create sample inventory card data with card details."""
    return {
        "inventory_id": str(sample_inventory_id),
        "card_id": sample_card_id,
        "quantity": 3,
        "is_tradeable": True,
        "card": {
            "card_name": "Test Card",
            "card_image_url": "https://example.com/card.png",
            "card_rarity": "Rare",
            "set_id": "set001",
        }
    }


@pytest.fixture(autouse=True)
def mock_supabase_client(mock_supabase):
    """Automatically mock the Supabase client for all tests."""
    with patch("main.supabase", mock_supabase):
        yield mock_supabase
