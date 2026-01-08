# Riftventory API Test Suite Summary

## Overview

A comprehensive test suite has been created for the Riftventory backend, consisting of both **unit tests** (with mocked database) and **integration tests** (against a real local Supabase instance).

## Statistics

### Overall
- **Total Test Files**: 7
- **Total Test Functions**: 78
- **Total Test Classes**: 26

### Unit Tests
- **Test Files**: 4
- **Test Functions**: 47
- **Test Classes**: 19
- **Endpoints Covered**: 16

### Integration Tests
- **Test Files**: 3
- **Test Functions**: 31
- **Test Classes**: 7

## Directory Structure

```
tests/
├── conftest.py                 # Root test configuration
├── __init__.py                 # Package initialization
├── unit/                       # Unit tests (mocked Supabase)
│   ├── conftest.py             # Unit test fixtures with mocks
│   ├── test_basic_endpoints.py
│   ├── test_inventory_endpoints.py
│   ├── test_inventory_card_endpoints.py
│   └── test_statistics_endpoint.py
└── integration/                # Integration tests (real Supabase)
    ├── conftest.py             # Integration test fixtures
    ├── test_integration_statistics.py
    ├── test_integration_edge_cases.py
    └── test_integration_constraints.py
```

---

## Unit Tests

Unit tests use **mocked Supabase client** to avoid requiring a live database connection. This provides:

- ✓ Fast test execution
- ✓ No database state management
- ✓ Predictable test results
- ✓ No external dependencies
- ✓ Isolated unit testing

### Coverage by Endpoint

#### Basic Endpoints (2 tests)
- ✓ `GET /` - Root endpoint
- ✓ `GET /health` - Health check

#### Inventory Endpoints (15 tests)
- ✓ `POST /inventories` - Create inventory (3 tests)
  - Success case
  - Default values
  - Failure case
- ✓ `GET /inventories/{inventory_id}` - Get inventory (2 tests)
  - Success case
  - Not found case
- ✓ `GET /users/{user_id}/inventories` - Get user inventories (2 tests)
  - Success case
  - Empty list case
- ✓ `PATCH /inventories/{inventory_id}` - Update inventory (5 tests)
  - Update name only
  - Update colour only
  - Update both fields
  - No fields provided
  - Not found case
- ✓ `DELETE /inventories/{inventory_id}` - Delete inventory (2 tests)
  - Success case
  - Not found case

#### Inventory Card Endpoints (22 tests)
- ✓ `GET /inventories/{inventory_id}/cards` - Get inventory cards (6 tests)
  - Success case
  - Filter by set_id
  - Filter by card_rarity
  - Filter by is_tradeable
  - Filter by min_quantity
  - Empty inventory
- ✓ `GET /inventories/{inventory_id}/with-cards` - Get inventory with cards (2 tests)
  - Success case
  - Not found case
- ✓ `POST /inventories/{inventory_id}/cards` - Add card to inventory (3 tests)
  - Add new card
  - Update existing card
  - Failure case
- ✓ `POST /inventories/{inventory_id}/cards/bulk` - Bulk add cards (2 tests)
  - Add multiple new cards
  - Mixed new and existing cards
- ✓ `PATCH /inventories/{inventory_id}/cards/{card_id}` - Update card (4 tests)
  - Update quantity
  - Update tradeable status
  - No fields provided
  - Not found case
- ✓ `POST /inventories/{inventory_id}/cards/{card_id}/adjust` - Adjust quantity (5 tests)
  - Increase quantity
  - Decrease quantity
  - Adjust to zero (removes card)
  - Prevent negative quantity
  - Not found case
- ✓ `DELETE /inventories/{inventory_id}/cards/{card_id}` - Remove card (2 tests)
  - Success case
  - Not found case

#### Statistics Endpoint (8 tests)
- ✓ `GET /inventories/{inventory_id}/stats` - Get inventory stats (8 tests)
  - Success case with multiple cards
  - Empty inventory
  - All cards tradeable
  - No cards tradeable
  - Multiple rarities
  - Multiple sets
  - Missing card data handling

---

## Integration Tests

Integration tests connect to a **real local Supabase instance** to verify end-to-end functionality. This provides:

- ✓ Real database constraint validation
- ✓ Actual join operation verification
- ✓ True cascade delete behavior testing
- ✓ Real statistics calculation accuracy
- ✓ Production-like environment testing

### Prerequisites

1. Install Supabase CLI
2. Run `supabase start` in the project root
3. Ensure `.env.test` contains local Supabase credentials

### Test Coverage

#### Statistics Accuracy (5 tests)
- ✓ Stats match actual card counts
- ✓ Cards by rarity breakdown accuracy
- ✓ Cards by set breakdown accuracy
- ✓ Stats update after adding cards
- ✓ Stats update after removing cards

#### Join Accuracy (4 tests)
- ✓ Card details populated from joins
- ✓ `/with-cards` total calculation
- ✓ `/with-cards` includes all card details
- ✓ Cards endpoint returns correct inventory_id

#### Empty Inventory Edge Cases (4 tests)
- ✓ Stats for empty inventory returns zeros
- ✓ Get cards from empty inventory returns empty list
- ✓ `/with-cards` for empty inventory returns empty cards list
- ✓ User with no inventories returns empty list

#### Quantity Edge Cases (4 tests)
- ✓ Adjust quantity to zero removes card
- ✓ Large quantity handling (9999)
- ✓ Rapid sequential adjustments maintain consistency
- ✓ Add same card multiple times increases quantity

#### Filter Functionality (7 tests)
- ✓ Filter by set_id
- ✓ Filter by rarity
- ✓ Filter by is_tradeable=true
- ✓ Filter by is_tradeable=false
- ✓ Filter by min_quantity
- ✓ Multiple filters combined

#### Foreign Key Constraints (4 tests)
- ✓ Create inventory with nonexistent user fails
- ✓ Add nonexistent card to inventory fails
- ✓ Add card to nonexistent inventory fails
- ✓ Bulk add with invalid card raises error

#### Cascade Deletes (3 tests)
- ✓ Delete inventory cascades to inventory_cards
- ✓ Delete user cascades to inventories and cards
- ✓ Inventory remains after removing all cards

---

## How to Run Tests

### Unit Tests Only
```bash
# Run unit tests (no database required)
cd backend
pytest tests/unit -v

# With coverage
pytest tests/unit --cov=. --cov-report=term-missing
```

### Integration Tests Only
```bash
# Start local Supabase first
supabase start

# Run integration tests
cd backend
pytest tests/integration -v

# Or use the marker
pytest -m integration -v
```

### All Tests
```bash
# Run all tests
cd backend
pytest -v

# With coverage report
pytest --cov=. --cov-report=term-missing
```

### Using Docker
```bash
# From project root (unit tests only in Docker)
docker-compose run --rm backend pytest tests/unit -v

# With coverage report
docker-compose run --rm backend pytest tests/unit --cov=. --cov-report=term-missing
```

## Key Features

- **Comprehensive Coverage**: All endpoints have multiple test cases covering success and failure scenarios
- **Two-Tier Testing**: Unit tests for fast, isolated testing; integration tests for real database validation
- **Edge Cases**: Tests include boundary conditions, empty states, and error handling
- **Filtering Tests**: All query parameter filters are tested
- **Data Validation**: Tests verify response structure and data integrity
- **Error Handling**: Tests ensure proper HTTP status codes and error messages
- **Constraint Testing**: Integration tests verify foreign keys and cascade deletes
- **Fixtures**: Reusable test data and mock objects for consistency

## Quick Start

### For Unit Tests (Fast, No Setup Required)
```bash
cd backend
pip install -r requirements.txt
pytest tests/unit -v
```

### For Integration Tests (Requires Local Supabase)
```bash
# 1. Start Supabase
supabase start

# 2. Run integration tests
cd backend
pytest tests/integration -v
```
