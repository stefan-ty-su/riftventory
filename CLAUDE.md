# Riftventory - Project Overview

Riftbound Card Inventory, Market, and Deckbuilding Application. Full-stack app with React Native/Expo frontend, Python FastAPI backend, and Supabase (PostgreSQL) database.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React Native 0.81.5, Expo 54, Expo Router, TypeScript 5.9 |
| Backend | Python 3.13, FastAPI, Uvicorn, Pydantic |
| Database | PostgreSQL 17 via Supabase |
| Testing | pytest, pytest-asyncio, httpx |
| Deployment | Docker, Docker Compose |

## Project Structure

```
riftventory/
├── app/                    # React Native frontend (Expo)
│   ├── app/                # Expo Router pages
│   │   └── (tabs)/         # Tab navigation
│   ├── components/         # Reusable UI components
│   ├── config/             # Supabase client setup
│   ├── constants/          # Theme definitions
│   └── hooks/              # Custom React hooks
├── backend/                # Python FastAPI backend
│   ├── main.py             # API entry point (all endpoints)
│   ├── models/             # Pydantic schemas
│   │   ├── inventory.py    # Inventory models
│   │   └── trade.py        # Trade models & enums
│   └── tests/
│       ├── unit/           # Mocked tests (fast)
│       └── integration/    # Real DB tests
├── supabase/               # Database config
│   └── migrations/         # Schema migrations
├── data_ingestion/         # Data import scripts
├── docs/                   # Planning & design docs
└── docker-compose.yml      # Container orchestration
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | All FastAPI endpoints (43+ routes) |
| `backend/models/inventory.py` | Inventory & card schemas |
| `backend/models/trade.py` | Trade schemas, enums (TradeStatus) |
| `supabase/migrations/20260108000000_initial_schema.sql` | Full database schema |
| `app/config/supabase.ts` | Frontend Supabase client |
| `app/app/(tabs)/_layout.tsx` | Tab navigation layout |

## Database Tables

- **card** - Master card definitions (name, type, rarity, stats)
- **set** - Card sets
- **user** - User accounts
- **inventory** - User card collections
- **inventory_card** - Cards in inventories (quantity, tradeable, locked_quantity)
- **trade** - Trade offers with counter-offer chain support
- **trade_escrow** - Cards locked by trade initiator
- **trade_recipient** - Cards requested from recipient
- **trade_history** - Audit trail of trade actions

## API Endpoints

### Inventory
- `POST /inventories` - Create inventory
- `GET /inventories/{id}` - Get inventory
- `GET /inventories/{id}/cards` - List cards with filters
- `POST /inventories/{id}/cards/bulk` - Bulk add cards
- `GET /inventories/{id}/stats` - Get statistics

### Trading
- `POST /trades` - Create trade offer
- `POST /trades/{id}/accept` - Accept trade
- `POST /trades/{id}/counter-offer` - Counter-offer
- `POST /trades/{id}/confirm` - Confirm trade
- `GET /trades/{id}/history` - Get trade chain history
- `DELETE /admin/cleanup/trades` - Cleanup old trades

## Running the Project

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd app
npm install
npx expo start
```

### Database (Local)
```bash
supabase start
supabase db reset  # Apply migrations
```

### Tests
```bash
# Unit tests (no DB required)
cd backend && pytest tests/unit -v

# Integration tests (requires supabase start)
cd backend && pytest tests/integration -v

# All tests with coverage
pytest --cov=. --cov-report=term-missing
```

### Docker
```bash
docker-compose up --build
```

## Core Features

1. **Inventory System** - Multi-inventory per user, card tracking with quantity/tradeable status
2. **Trading** - Escrow mechanism, counter-offer chains, dual confirmation, full audit trail
3. **Statistics** - Cards by rarity, by set, totals

## Trade Status Flow

```
PENDING → ACCEPTED → COMPLETED
    ↓         ↓
COUNTERED  CANCELLED/REJECTED
```

## Environment Variables

Backend requires in `.env`:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SERVICE_ROLE_KEY`

## Current Branch

`api_inventory_implementation` - Trading feature implementation
