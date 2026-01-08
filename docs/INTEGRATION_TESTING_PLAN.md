# Local Supabase Integration Testing Plan

## Overview
Set up a local Supabase database for integration testing, separate from existing mock unit tests.

---

## Part 1: Local Supabase Setup Instructions

### 1.1 Start Local Supabase
```bash
cd c:\Users\stefa\Desktop\Personal Repos\riftventory
supabase start
```

First run will download Docker images. Output will show:
- API URL: `http://127.0.0.1:54321`
- DB URL: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- Anon key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (local dev key)

### 1.2 Create Migration File
**Create:** `supabase/migrations/20240101000000_initial_schema.sql`

Tables in correct dependency order with `ON DELETE CASCADE`:
1. `user` (no dependencies)
2. `set` (no dependencies)
3. `inventory` (depends on user)
4. `card` (depends on set)
5. `inventory_card` (depends on inventory, card)

### 1.3 Create Seed Data
**Create:** `supabase/seed.sql`

Test data including:
- 3 test users
- 3 test sets
- 8 test cards across sets
- 3 test inventories
- Sample inventory_card entries

### 1.4 Reset Database Command
```bash
supabase db reset  # Drops data, runs migrations, seeds
```

---

## Part 2: Test Infrastructure

### Files to Create

| File | Purpose |
|------|---------|
| `backend/.env.test` | Local Supabase credentials |
| `backend/tests/conftest_integration.py` | Integration test fixtures |
| `backend/tests/integration/__init__.py` | Package marker |
| `backend/tests/integration/conftest.py` | Re-export fixtures |

### Files to Modify

| File | Change |
|------|--------|
| `backend/pytest.ini` | Add `integration` marker |

### Key Fixtures
- `setup_test_environment` - Load `.env.test` at session start
- `supabase_client` - Real Supabase client (session-scoped)
- `reset_database` - Run `supabase db reset` before test session
- `integration_client` - FastAPI TestClient with real DB
- `clean_test_data` - Cleanup test-created records after each test

---

## Part 3: Recommended Integration Tests

### Test Files to Create

```
backend/tests/integration/
    __init__.py
    conftest.py
    test_integration_constraints.py
    test_integration_inventory.py
    test_integration_cards.py
    test_integration_statistics.py
    test_integration_edge_cases.py
```

### Test Categories

**1. Foreign Key Constraint Tests** (`test_integration_constraints.py`)
- Create inventory with non-existent user (should fail)
- Add non-existent card to inventory (should fail)
- Bulk add with invalid card (test atomicity)

**2. Cascade Delete Tests** (`test_integration_constraints.py`)
- Delete inventory cascades to inventory_card entries
- Delete user cascades to inventories

**3. Statistics Accuracy Tests** (`test_integration_statistics.py`)
- Stats match actual card counts
- cards_by_rarity breakdown accuracy
- cards_by_set breakdown accuracy
- Stats update after card changes

**4. Join Accuracy Tests** (`test_integration_statistics.py`)
- Card details populated correctly from joins
- /with-cards total_cards calculation

**5. Edge Case Tests** (`test_integration_edge_cases.py`)
- Stats for empty inventory (all zeros)
- User with no inventories (empty list)
- Quantity zero removes card
- Large quantity handling
- Rapid sequential adjustments

**6. Filter Tests** (`test_integration_edge_cases.py`)
- Multiple filter combinations work correctly

---

## Part 4: Running Tests

```bash
# Unit tests only (mocked, fast)
pytest backend/tests -m "not integration" -v

# Integration tests only (requires local Supabase running)
pytest backend/tests/integration -m integration -v

# All tests
pytest backend/tests -v
```

---

## Implementation Order

1. Create migration file from existing schema (with CASCADE deletes)
2. Create seed.sql with test data
3. Run `supabase start` and `supabase db reset` to verify setup
4. Create `.env.test` with local credentials
5. Create `conftest_integration.py` with fixtures
6. Update `pytest.ini` with integration marker
7. Create integration test directory and files
8. Write constraint tests (FK, cascade)
9. Write statistics/join tests
10. Write edge case tests
11. Run full test suite to verify

---

## Critical Files

- [supabase/config.toml](../supabase/config.toml) - Already configured, seed path at line 63
- [supabase_schema.sql](../supabase_schema.sql) - Source for migration (needs reordering)
- [backend/tests/conftest.py](tests/conftest.py) - Pattern for fixtures
- [backend/main.py](main.py) - Supabase client to override in tests
- [backend/pytest.ini](pytest.ini) - Add integration marker
