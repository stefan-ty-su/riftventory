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


# ============== Trade-related fixtures ==============

@pytest.fixture
def sample_trade_id():
    """Generate a sample trade UUID."""
    return uuid4()


@pytest.fixture
def sample_root_trade_id():
    """Generate a sample root trade UUID for counter-offer chains."""
    return uuid4()


@pytest.fixture
def sample_initiator_user_id():
    """Generate a sample initiator user ID."""
    return "initiator_user_123"


@pytest.fixture
def sample_recipient_user_id():
    """Generate a sample recipient user ID."""
    return "recipient_user_456"


@pytest.fixture
def sample_initiator_inventory_id():
    """Generate a sample initiator inventory UUID."""
    return uuid4()


@pytest.fixture
def sample_recipient_inventory_id():
    """Generate a sample recipient inventory UUID."""
    return uuid4()


@pytest.fixture
def sample_escrow_cards(sample_card_id):
    """Create sample escrow cards for trading."""
    return [
        {"card_id": sample_card_id, "quantity": 2},
        {"card_id": "card_escrow_2", "quantity": 1},
    ]


@pytest.fixture
def sample_requested_cards():
    """Create sample requested cards for trading."""
    return [
        {"card_id": "card_requested_1", "quantity": 1},
        {"card_id": "card_requested_2", "quantity": 3},
    ]


@pytest.fixture
def sample_trade_data(
    sample_trade_id,
    sample_initiator_user_id,
    sample_recipient_user_id,
    sample_initiator_inventory_id,
    sample_recipient_inventory_id,
):
    """Create sample PENDING trade data."""
    return {
        "trade_id": str(sample_trade_id),
        "initiator_user_id": sample_initiator_user_id,
        "initiator_inventory_id": str(sample_initiator_inventory_id),
        "recipient_user_id": sample_recipient_user_id,
        "recipient_inventory_id": str(sample_recipient_inventory_id),
        "status": "pending",
        "message": "Test trade offer",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root_trade_id": None,
        "parent_trade_id": None,
        "counter_count": 0,
        "initiator_confirmed": False,
        "initiator_confirmed_at": None,
        "recipient_confirmed": False,
        "recipient_confirmed_at": None,
        "resolved_at": None,
    }


@pytest.fixture
def sample_accepted_trade_data(sample_trade_data):
    """Create sample ACCEPTED trade data with recipient auto-confirmed."""
    trade = sample_trade_data.copy()
    trade["status"] = "accepted"
    trade["recipient_confirmed"] = True
    trade["recipient_confirmed_at"] = datetime.now(timezone.utc).isoformat()
    return trade


@pytest.fixture
def sample_completed_trade_data(sample_trade_data):
    """Create sample COMPLETED trade data."""
    now = datetime.now(timezone.utc).isoformat()
    trade = sample_trade_data.copy()
    trade["status"] = "completed"
    trade["initiator_confirmed"] = True
    trade["initiator_confirmed_at"] = now
    trade["recipient_confirmed"] = True
    trade["recipient_confirmed_at"] = now
    trade["resolved_at"] = now
    return trade


@pytest.fixture
def sample_countered_trade_data(sample_trade_data, sample_root_trade_id):
    """Create sample COUNTERED trade data."""
    trade = sample_trade_data.copy()
    trade["status"] = "countered"
    trade["root_trade_id"] = str(sample_root_trade_id)
    trade["resolved_at"] = datetime.now(timezone.utc).isoformat()
    return trade


@pytest.fixture
def sample_trade_escrow_data(sample_trade_id, sample_escrow_cards):
    """Create sample trade_escrow table data."""
    return [
        {"trade_id": str(sample_trade_id), "card_id": card["card_id"], "quantity": card["quantity"]}
        for card in sample_escrow_cards
    ]


@pytest.fixture
def sample_trade_recipient_data(sample_trade_id, sample_requested_cards):
    """Create sample trade_recipient table data."""
    return [
        {"trade_id": str(sample_trade_id), "card_id": card["card_id"], "quantity": card["quantity"]}
        for card in sample_requested_cards
    ]


@pytest.fixture
def sample_trade_history_data(sample_trade_id, sample_initiator_user_id):
    """Create sample trade history entries."""
    base_time = datetime.now(timezone.utc)
    return [
        {
            "history_id": str(uuid4()),
            "trade_id": str(sample_trade_id),
            "root_trade_id": str(sample_trade_id),
            "sequence_number": 1,
            "actor_user_id": sample_initiator_user_id,
            "action": "created",
            "details": {"message": "Test trade offer"},
            "created_at": base_time.isoformat(),
        },
    ]


@pytest.fixture
def sample_inventory_card_with_lock(sample_inventory_id, sample_card_id):
    """Create sample inventory card with locked_quantity."""
    return {
        "inventory_id": str(sample_inventory_id),
        "card_id": sample_card_id,
        "quantity": 5,
        "locked_quantity": 2,
        "is_tradeable": True,
    }


@pytest.fixture
def sample_trade_card_response(sample_card_id):
    """Create sample trade card response with card details."""
    return {
        "card_id": sample_card_id,
        "quantity": 2,
        "card_name": "Test Card",
        "card_image_url": "https://example.com/card.png",
        "card_rarity": "Rare",
        "set_id": "set001",
    }
