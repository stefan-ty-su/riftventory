# Riftventory API Tests

This directory contains tests for all API endpoints in the Riftventory backend.

## Test Structure

```
tests/
├── conftest.py                 # Root conftest (minimal, shared path setup)
├── README.md                   # This file
├── unit/                       # Unit tests with mocked Supabase
│   ├── conftest.py             # Unit test fixtures (mock client, sample data)
│   ├── test_basic_endpoints.py
│   ├── test_inventory_endpoints.py
│   ├── test_inventory_card_endpoints.py
│   └── test_statistics_endpoint.py
└── integration/                # Integration tests with real local Supabase
    ├── conftest.py             # Integration test fixtures (real DB connection)
    └── (test files)
```

## Running Tests

You can run tests either locally or using Docker.

### Option 1: Run Tests in Docker (Recommended)

Run tests inside the Docker container where all dependencies are installed:

```bash
# From the project root directory

# Run all unit tests (mocked, fast):
docker-compose run --rm backend pytest tests/unit -v

# Run all integration tests (requires local Supabase):
docker-compose run --rm backend pytest tests/integration -v -m integration

# Run all tests:
docker-compose run --rm backend pytest -v

# Run specific test file:
docker-compose run --rm backend pytest tests/unit/test_inventory_endpoints.py

# Run with coverage:
docker-compose run --rm backend pytest --cov=. --cov-report=term-missing
```

### Option 2: Run Tests Locally

First, install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Then run tests:

```bash
# Run all unit tests (mocked, fast)
pytest tests/unit -v

# Run unit tests only (exclude integration)
pytest -m "not integration" -v

# Run integration tests only (requires local Supabase running)
pytest tests/integration -m integration -v

# Run specific test file
pytest tests/unit/test_inventory_endpoints.py

# Run specific test class
pytest tests/unit/test_inventory_endpoints.py::TestCreateInventory

# Run with coverage
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

## Test Coverage

The test suite covers:

### Basic Endpoints
- ✓ Root endpoint (/)
- ✓ Health check endpoint (/health)

### Inventory Endpoints
- ✓ Create inventory (POST /inventories)
- ✓ Get inventory by ID (GET /inventories/{inventory_id})
- ✓ Get user inventories (GET /users/{user_id}/inventories)
- ✓ Update inventory (PATCH /inventories/{inventory_id})
- ✓ Delete inventory (DELETE /inventories/{inventory_id})

### Inventory Card Endpoints
- ✓ Get inventory cards with filters (GET /inventories/{inventory_id}/cards)
- ✓ Get inventory with cards (GET /inventories/{inventory_id}/with-cards)
- ✓ Add card to inventory (POST /inventories/{inventory_id}/cards)
- ✓ Bulk add cards (POST /inventories/{inventory_id}/cards/bulk)
- ✓ Update inventory card (PATCH /inventories/{inventory_id}/cards/{card_id})
- ✓ Adjust card quantity (POST /inventories/{inventory_id}/cards/{card_id}/adjust)
- ✓ Remove card from inventory (DELETE /inventories/{inventory_id}/cards/{card_id})

### Statistics Endpoint
- ✓ Get inventory statistics (GET /inventories/{inventory_id}/stats)

## Test Approach

All tests use mocked Supabase client to avoid requiring a live database connection. This allows:
- Fast test execution
- No database state management
- Predictable test results
- No external dependencies

## Fixtures

### Unit Test Fixtures (`unit/conftest.py`)

- `client` - FastAPI test client
- `mock_supabase_client` - Mocked Supabase client (auto-used)
- `sample_inventory_id` - Sample UUID for testing
- `sample_user_id` - Sample user ID
- `sample_card_id` - Sample card ID
- `sample_inventory_data` - Complete inventory data dict
- `sample_inventory_card_data` - Inventory card data dict
- `sample_inventory_card_with_details` - Inventory card with joined card details

### Integration Test Fixtures (`integration/conftest.py`)

- `supabase_client` - Real Supabase client connected to local instance
- `integration_client` - FastAPI test client with real DB
- `test_user` - Creates and auto-cleans a test user
- `test_inventory` - Creates a test inventory (cleaned via cascade)
- `sample_card_ids` - Real card IDs from seeded database
- `test_inventory_with_cards` - Inventory with cards added
- `clean_test_data` - Manual cleanup tracker for custom test data
