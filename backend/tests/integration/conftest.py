"""
Integration test fixtures for testing with real local Supabase database.

These fixtures connect to a local Supabase instance and perform real database operations.
Run `supabase start` before running integration tests.
All tests in this directory are automatically marked as integration tests.
"""
import pytest
import subprocess
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import create_client, Client
from uuid import uuid4


# Path to the project root (where supabase/ folder is located)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def pytest_collection_modifyitems(items):
    """Automatically mark all tests in this directory as integration tests."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def setup_test_environment():
    """Load .env.test at session start."""
    env_test_path = Path(__file__).parent.parent / ".env.test"
    load_dotenv(env_test_path, override=True)
    yield


@pytest.fixture(scope="session")
def supabase_client(setup_test_environment) -> Client:
    """Create a real Supabase client connected to local instance."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        pytest.skip("SUPABASE_URL and SUPABASE_KEY must be set in .env.test")

    return create_client(url, key)


@pytest.fixture(scope="session")
def reset_database(setup_test_environment):
    """
    Reset the database before the test session.

    Note: This fixture is optional. If running inside Docker where supabase CLI
    is not available, it will be skipped. Run `supabase db reset` manually before
    running integration tests if needed.
    """
    try:
        result = subprocess.run(
            ["supabase", "db", "reset", "--no-seed"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            # Log warning but don't fail - database might already be in good state
            import warnings
            warnings.warn(f"Could not reset database: {result.stderr}")
    except FileNotFoundError:
        # supabase CLI not available (e.g., running inside Docker)
        import warnings
        warnings.warn("supabase CLI not found. Skipping database reset.")
    except subprocess.TimeoutExpired:
        import warnings
        warnings.warn("Database reset timed out. Continuing anyway.")

    yield


@pytest.fixture(scope="session")
def integration_client(setup_test_environment, reset_database):
    """
    FastAPI TestClient configured to use real Supabase.

    This patches the supabase client in main.py to use the local instance.
    """
    # Ensure environment is loaded before importing main
    from main import app, supabase

    # The supabase client in main.py will use the env vars we loaded
    # Since we loaded .env.test, it should connect to local Supabase
    return TestClient(app)


@pytest.fixture
def test_user_id():
    """Generate a unique test user ID for each test."""
    return f"test_user_{uuid4().hex[:8]}"


@pytest.fixture
def test_user(supabase_client, test_user_id):
    """
    Create a test user in the database.
    Automatically cleaned up after the test.
    """
    user_data = {
        "user_id": test_user_id,
        "user_name": f"Test User {test_user_id}",
    }

    result = supabase_client.table("user").insert(user_data).execute()

    if not result.data:
        pytest.fail("Failed to create test user")

    yield result.data[0]

    # Cleanup: delete user (cascades to inventories)
    supabase_client.table("user").delete().eq("user_id", test_user_id).execute()


@pytest.fixture
def test_inventory(supabase_client, test_user):
    """
    Create a test inventory for the test user.
    Automatically cleaned up via cascade when user is deleted.
    """
    inventory_data = {
        "user_id": test_user["user_id"],
        "inventory_name": "Test Inventory",
        "inventory_colour": "#FF5733",
    }

    result = supabase_client.table("inventory").insert(inventory_data).execute()

    if not result.data:
        pytest.fail("Failed to create test inventory")

    yield result.data[0]


@pytest.fixture
def sample_card_ids(supabase_client):
    """
    Get real card IDs from the seeded database.
    Returns a list of card IDs that exist in the database.
    """
    result = supabase_client.table("card").select("card_id").limit(10).execute()

    if not result.data:
        pytest.skip("No cards found in database. Run `supabase db reset` to seed data.")

    return [card["card_id"] for card in result.data]


@pytest.fixture
def sample_card_id(sample_card_ids):
    """Get a single valid card ID."""
    return sample_card_ids[0]


@pytest.fixture
def test_inventory_with_cards(supabase_client, test_inventory, sample_card_ids):
    """
    Create a test inventory with some cards added.
    Returns tuple of (inventory, list of inventory_card records).
    """
    inventory_cards = []

    for i, card_id in enumerate(sample_card_ids[:3]):
        card_data = {
            "inventory_id": test_inventory["inventory_id"],
            "card_id": card_id,
            "quantity": (i + 1) * 2,  # 2, 4, 6
            "is_tradeable": i % 2 == 0,  # alternating
        }

        result = supabase_client.table("inventory_card").insert(card_data).execute()
        if result.data:
            inventory_cards.append(result.data[0])

    yield test_inventory, inventory_cards


@pytest.fixture
def clean_test_data(supabase_client):
    """
    Fixture to track and clean up test-created data after each test.

    Usage:
        def test_something(clean_test_data, supabase_client):
            # Create data
            user = supabase_client.table("user").insert({...}).execute()
            clean_test_data.add("user", "user_id", user.data[0]["user_id"])
            # Test runs...
            # Cleanup happens automatically
    """
    class TestDataTracker:
        def __init__(self, client):
            self.client = client
            self.items = []  # List of (table, column, value) tuples

        def add(self, table: str, column: str, value):
            """Track a record for cleanup."""
            self.items.append((table, column, value))

        def cleanup(self):
            """Delete all tracked records in reverse order."""
            for table, column, value in reversed(self.items):
                self.client.table(table).delete().eq(column, value).execute()

    tracker = TestDataTracker(supabase_client)
    yield tracker
    tracker.cleanup()
