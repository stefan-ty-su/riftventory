# Escrow-Based Card Trading Implementation Plan

## Overview
Implement a card trading system using the Escrow Model where users can safely exchange cards through a multi-step process with card locking and atomic exchanges.

## Key Decisions
- **Destination inventory**: Recipient specifies which inventory to receive cards when accepting trade
- **Trade model**: Offer + Request (both parties specify what they give and want)
- **Authentication**: Header-based user_id (matches existing inventory patterns)

---

## Phase 1: Database Schema

### 1.1 Create new migration file
**File**: `supabase/migrations/[timestamp]_add_trading_tables.sql`

#### `trade` table
```sql
CREATE TABLE public.trade (
    trade_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    initiator_id text NOT NULL REFERENCES public."user"(user_id) ON DELETE CASCADE,
    recipient_id text NOT NULL REFERENCES public."user"(user_id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'countered', 'accepted', 'confirmed', 'completed', 'cancelled', 'expired', 'failed'
    )),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    initiator_confirmed boolean DEFAULT false,
    recipient_confirmed boolean DEFAULT false,
    initiator_dest_inventory_id uuid REFERENCES public.inventory(inventory_id),
    recipient_dest_inventory_id uuid REFERENCES public.inventory(inventory_id),
    completed_at timestamptz,
    cancelled_at timestamptz,
    cancel_reason text,
    CONSTRAINT trade_different_users CHECK (initiator_id <> recipient_id)
);
```

#### `trade_item` table
```sql
CREATE TABLE public.trade_item (
    trade_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id uuid NOT NULL REFERENCES public.trade(trade_id) ON DELETE CASCADE,
    owner_id text NOT NULL REFERENCES public."user"(user_id) ON DELETE CASCADE,
    inventory_id uuid NOT NULL REFERENCES public.inventory(inventory_id) ON DELETE CASCADE,
    card_id text NOT NULL REFERENCES public.card(card_id) ON UPDATE CASCADE,
    quantity smallint NOT NULL DEFAULT 1 CHECK (quantity > 0),
    direction text NOT NULL CHECK (direction IN ('offer', 'request')),
    is_locked boolean DEFAULT false,
    locked_at timestamptz,
    CONSTRAINT trade_item_unique_card UNIQUE (trade_id, owner_id, inventory_id, card_id)
);
```

#### `trade_history` table (audit log)
```sql
CREATE TABLE public.trade_history (
    history_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id uuid NOT NULL REFERENCES public.trade(trade_id) ON DELETE CASCADE,
    actor_id text NOT NULL,
    action text NOT NULL,
    previous_status text,
    new_status text,
    details jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
```

### 1.2 Modify existing `inventory_card` table
```sql
ALTER TABLE public.inventory_card ADD COLUMN locked_quantity smallint DEFAULT 0;
```
*Note: Validation that `locked_quantity <= quantity` will be enforced in the API layer rather than via database constraint.*

---

## Phase 2: Pydantic Models

### 2.1 Create new file
**File**: `backend/models/trade.py`

#### Key models to create:
- `TradeStatus` (enum): pending, countered, accepted, confirmed, completed, cancelled, expired, failed
- `TradeDirection` (enum): offer, request
- `TradeItemCreate`: inventory_id, card_id, quantity
- `TradeCreate`: recipient_id, offered_cards[], requested_cards[], expires_in_hours, destination_inventory_id
- `TradeAccept`: destination_inventory_id (where recipient wants to receive cards)
- `TradeCounter`: offered_cards[], requested_cards[]
- `TradeCancel`: reason (optional)
- `TradeItemResponse`: full item with joined card details
- `TradeResponse`: full trade with timestamps and status
- `TradeWithItemsResponse`: trade + offered_items[] + requested_items[]

### 2.2 Update existing file
**File**: `backend/models/inventory.py`

Add `locked_quantity` field to `InventoryCardResponse`

---

## Phase 3: Trade State Machine

### State Flow
```
pending -> [accept] -> accepted -> [confirm both] -> confirmed -> [execute] -> completed
    |          |            |
    v          v            v
countered  cancelled    cancelled/expired
    |
    v
[accept/counter] -> ...
```

### Valid Transitions
| State | Actions Available | Who Can Act |
|-------|------------------|-------------|
| pending | accept, counter, cancel | recipient |
| countered | accept, counter, cancel | initiator |
| accepted | confirm, cancel | either (once each) |
| confirmed | (auto-execute) | system |

---

## Phase 4: API Endpoints

**Add to**: `backend/main.py`

### Trade CRUD
- `POST /trades` - Create trade offer
- `GET /trades/{trade_id}` - Get trade details
- `GET /users/{user_id}/trades` - List user's trades (with filters)

### Trade Actions
- `POST /trades/{trade_id}/accept` - Accept trade (locks cards in escrow)
- `POST /trades/{trade_id}/counter` - Counter with new proposal
- `POST /trades/{trade_id}/confirm` - Confirm ready to complete
- `POST /trades/{trade_id}/cancel` - Cancel trade (releases escrow)

### Supporting Endpoints
- `GET /trades/{trade_id}/history` - Get trade audit log
- `GET /users/{user_id}/tradeable-cards` - Browse tradeable cards across inventories

---

## Phase 5: Core Logic Implementation

### 5.1 Card Validation (API Layer)
Before creating/accepting trades:
1. Verify cards exist in specified inventory
2. Verify `is_tradeable = true`
3. Verify `quantity - locked_quantity >= requested_quantity`
4. Verify `locked_quantity >= 0` and `locked_quantity <= quantity` on all escrow operations

### 5.2 Escrow Lock
When trade is accepted:
1. Increment `locked_quantity` on inventory_card for all offered cards
2. Set `is_locked = true` on trade_items
3. Validate BOTH parties' cards before locking

### 5.3 Escrow Release
When trade is cancelled/expired:
1. Decrement `locked_quantity` on inventory_card
2. Set `is_locked = false` on trade_items

### 5.4 Atomic Exchange
When both parties confirm:
1. For each trade_item with direction='offer':
   - Decrease quantity in source inventory
   - Increase quantity in destination inventory (upsert)
2. Update trade status to 'completed'
3. On failure: rollback and set status to 'failed'

---

## Phase 6: Testing

**Files**: `backend/tests/unit/test_trade_endpoints.py`, `backend/tests/integration/test_trades.py`

Test scenarios:
- Full trade flow (create -> accept -> confirm -> complete)
- Counter-offer flow
- Cancellation with escrow release
- Double-trading prevention (same card in multiple trades)
- Insufficient quantity validation
- Non-tradeable card rejection

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `supabase/migrations/[timestamp]_add_trading_tables.sql` | CREATE |
| `backend/models/trade.py` | CREATE |
| `backend/models/inventory.py` | MODIFY (add locked_quantity) |
| `backend/main.py` | MODIFY (add trade endpoints) |
| `backend/tests/unit/test_trade_endpoints.py` | CREATE |
| `backend/tests/integration/test_trades.py` | CREATE |

---

## Implementation Order

1. **Database migration** - Create trade tables and modify inventory_card
2. **Pydantic models** - Define all trade-related schemas
3. **Basic endpoints** - Create trade, get trade, list trades
4. **Action endpoints** - Accept, counter, cancel with escrow logic
5. **Confirm & execute** - Final confirmation and atomic exchange
6. **Tests** - Unit and integration tests
