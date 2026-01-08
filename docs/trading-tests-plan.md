# Test Plan for Trading Features

## Overview
This plan covers both unit tests and integration tests for the trading functionality including locked_quantity field, counter offering, accepting, confirming, unconfirming, rejecting, cancelling, trade history, trade history chain, admin cleanup, self-transfers, and concurrent trades.

## Test File Structure
Create new test files:
- `backend/tests/unit/test_trade_endpoints.py` - Unit tests with mocked Supabase
- `backend/tests/integration/test_integration_trades.py` - Integration tests with real database

---

## 1. locked_quantity Field Tests

### Class: `TestLockedQuantity`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_create_trade_locks_escrow_cards` | Verify that when a trade is created, the locked_quantity on the initiator's escrow cards is incremented by the escrowed amount |
| `test_accept_trade_locks_recipient_cards` | Verify that when a trade is accepted, the locked_quantity on the recipient's requested cards is incremented |
| `test_cancel_trade_unlocks_initiator_cards` | Verify that cancelling a pending trade decrements locked_quantity back to 0 for initiator's escrow cards |
| `test_reject_trade_unlocks_initiator_cards` | Verify that rejecting a trade decrements locked_quantity for initiator's escrow cards |
| `test_complete_trade_clears_locked_quantity` | Verify that after trade completion, locked_quantity is properly handled (transferred cards no longer locked) |
| `test_available_quantity_calculation` | Verify that available quantity = total quantity - locked_quantity is correctly calculated when validating trades |
| `test_create_trade_fails_insufficient_available_quantity` | Verify that creating a trade fails when quantity - locked_quantity < requested escrow amount |
| `test_multiple_trades_accumulate_locked_quantity` | Verify that multiple pending trades on the same card correctly accumulate locked_quantity |

---

## 2. Counter Offering Tests

### Class: `TestCounterOffer`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_counter_offer_success` | Verify successful counter-offer creates new trade with swapped roles (recipient becomes initiator) |
| `test_counter_offer_sets_status_to_countered` | Verify original trade status changes to COUNTERED after counter-offer |
| `test_counter_offer_increments_counter_count` | Verify new trade has counter_count = original counter_count + 1 |
| `test_counter_offer_preserves_root_trade_id` | Verify new trade has same root_trade_id as original trade chain |
| `test_counter_offer_sets_parent_trade_id` | Verify new trade's parent_trade_id points to the original trade |
| `test_counter_offer_unlocks_original_initiator_cards` | Verify original initiator's escrow cards are unlocked after counter-offer |
| `test_counter_offer_locks_new_initiator_cards` | Verify counter-offerer's escrow cards become locked |
| `test_counter_offer_only_recipient_can_counter` | Verify 403 error when non-recipient tries to counter-offer |
| `test_counter_offer_requires_pending_status` | Verify 400 error when attempting to counter a non-PENDING trade |
| `test_counter_offer_requires_escrow_cards` | Verify 422 error when counter-offer has empty escrow_cards list |
| `test_counter_offer_validates_card_availability` | Verify 400 error when counter-offerer doesn't have enough cards available |
| `test_counter_offer_records_history_entry` | Verify COUNTER_OFFERED action is recorded in trade_history |

---

## 3. Accept Trade Tests

### Class: `TestAcceptTrade`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_accept_trade_success` | Verify successful trade acceptance returns updated trade with ACCEPTED status |
| `test_accept_trade_updates_status_to_accepted` | Verify trade status changes from PENDING to ACCEPTED |
| `test_accept_trade_locks_recipient_cards` | Verify recipient's requested cards get locked_quantity incremented |
| `test_accept_trade_auto_confirms_recipient` | Verify recipient_confirmed is set to True and recipient_confirmed_at is set |
| `test_accept_trade_only_recipient_can_accept` | Verify 403 error when non-recipient (initiator or other user) tries to accept |
| `test_accept_trade_requires_pending_status` | Verify 400 error when attempting to accept a non-PENDING trade |
| `test_accept_trade_validates_recipient_has_cards` | Verify 400 error when recipient doesn't have the requested cards |
| `test_accept_trade_validates_card_availability` | Verify 400 error when recipient has cards but insufficient available quantity (locked) |
| `test_accept_trade_records_history_entry` | Verify ACCEPTED action is recorded in trade_history |

---

## 4. Confirm Trade Tests

### Class: `TestConfirmTrade`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_confirm_trade_initiator_success` | Verify initiator can successfully confirm an ACCEPTED trade |
| `test_confirm_trade_recipient_success` | Verify recipient can successfully confirm an ACCEPTED trade (though auto-confirmed on accept) |
| `test_confirm_trade_sets_confirmed_flag` | Verify confirming sets initiator_confirmed or recipient_confirmed to True with timestamp |
| `test_confirm_trade_both_confirmed_executes_trade` | Verify trade auto-executes (status=COMPLETED) when both parties have confirmed |
| `test_confirm_trade_transfers_escrow_cards` | Verify escrow cards are transferred from initiator to recipient on completion |
| `test_confirm_trade_transfers_requested_cards` | Verify requested cards are transferred from recipient to initiator on completion |
| `test_confirm_trade_sets_resolved_at` | Verify resolved_at timestamp is set when trade completes |
| `test_confirm_trade_requires_accepted_status` | Verify 400 error when attempting to confirm a non-ACCEPTED trade |
| `test_confirm_trade_prevents_double_confirmation` | Verify 400 error when same party tries to confirm twice |
| `test_confirm_trade_only_participants_can_confirm` | Verify 403 error when non-participant tries to confirm |
| `test_confirm_trade_records_history_entry` | Verify CONFIRMED action is recorded in trade_history |
| `test_confirm_trade_records_completed_on_execution` | Verify COMPLETED action is recorded when both confirm |

---

## 5. Unconfirm Trade Tests

### Class: `TestUnconfirmTrade`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_unconfirm_trade_success` | Verify successful unconfirmation resets the confirmed flag to False |
| `test_unconfirm_trade_clears_confirmed_timestamp` | Verify initiator_confirmed_at or recipient_confirmed_at is cleared |
| `test_unconfirm_trade_requires_accepted_status` | Verify 400 error when attempting to unconfirm a non-ACCEPTED trade |
| `test_unconfirm_trade_only_confirmed_party_can_unconfirm` | Verify 400 error when unconfirmed party tries to unconfirm |
| `test_unconfirm_trade_blocked_if_both_confirmed` | Verify 400 error when attempting to unconfirm after both parties confirmed (trade should execute immediately) |
| `test_unconfirm_trade_only_participants_can_unconfirm` | Verify 403 error when non-participant tries to unconfirm |
| `test_unconfirm_trade_records_history_entry` | Verify UNCONFIRMED action is recorded in trade_history |

---

## 6. Reject Trade Tests

### Class: `TestRejectTrade`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_reject_trade_success` | Verify successful rejection returns trade with REJECTED status |
| `test_reject_trade_updates_status_to_rejected` | Verify trade status changes from PENDING to REJECTED |
| `test_reject_trade_unlocks_initiator_cards` | Verify initiator's escrow cards have locked_quantity decremented |
| `test_reject_trade_sets_resolved_at` | Verify resolved_at timestamp is set on rejection |
| `test_reject_trade_only_recipient_can_reject` | Verify 403 error when non-recipient tries to reject |
| `test_reject_trade_requires_pending_status` | Verify 400 error when attempting to reject a non-PENDING trade |
| `test_reject_trade_records_history_entry` | Verify REJECTED action is recorded in trade_history |

---

## 7. Cancel Trade Tests

### Class: `TestCancelTrade`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_cancel_trade_success` | Verify successful cancellation returns trade with CANCELLED status |
| `test_cancel_trade_updates_status_to_cancelled` | Verify trade status changes from PENDING to CANCELLED |
| `test_cancel_trade_unlocks_initiator_cards` | Verify initiator's escrow cards have locked_quantity decremented |
| `test_cancel_trade_sets_resolved_at` | Verify resolved_at timestamp is set on cancellation |
| `test_cancel_trade_only_initiator_can_cancel` | Verify 403 error when non-initiator tries to cancel |
| `test_cancel_trade_requires_pending_status` | Verify 400 error when attempting to cancel a non-PENDING trade |
| `test_cancel_trade_with_reason` | Verify cancellation reason is stored when provided in TradeCancel body |
| `test_cancel_trade_records_history_entry` | Verify CANCELLED action is recorded in trade_history with optional reason |

---

## 8. Trade History Recording Tests

### Class: `TestTradeHistoryRecording`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_create_trade_records_created_action` | Verify CREATED action is recorded when trade is created |
| `test_history_entry_has_correct_trade_id` | Verify history entry references the correct trade_id |
| `test_history_entry_has_correct_root_trade_id` | Verify history entry uses root_trade_id (for chain tracking) |
| `test_history_entry_has_correct_actor` | Verify actor_user_id matches the user performing the action |
| `test_history_entry_sequence_numbers_increment` | Verify sequence_number increments for each action in a chain |
| `test_history_entry_includes_details` | Verify details JSON contains relevant action metadata |
| `test_history_records_all_action_types` | Verify all TradeHistoryAction enum values are recorded appropriately |

---

## 9. Get Trade History Chain Tests

### Class: `TestGetTradeHistoryChain`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_get_trade_history_success` | Verify successful retrieval of trade history returns list of history entries |
| `test_get_trade_history_returns_all_chain_entries` | Verify history includes entries from all trades in the counter-offer chain (same root_trade_id) |
| `test_get_trade_history_ordered_by_sequence` | Verify history entries are returned in sequence_number order |
| `test_get_trade_history_includes_actor_names` | Verify actor_user_name is populated in response |
| `test_get_trade_history_not_found` | Verify 404 error when trade_id doesn't exist |
| `test_get_trade_history_uses_root_trade_id` | Verify when querying a counter-offer trade, history from original trade is included |
| `test_get_trade_history_empty_chain` | Verify proper response when trade exists but has minimal history |

---

## 10. Self-Transfer Tests

### Class: `TestSelfTransfer`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_self_transfer_success` | Verify a user can create a trade transferring cards between their own inventories |
| `test_self_transfer_auto_executes` | Verify self-transfer trades auto-execute immediately (skip confirmation flow) |
| `test_self_transfer_skips_tradeable_check` | Verify self-transfers don't require cards to be marked as tradeable |
| `test_self_transfer_updates_quantities` | Verify card quantities are correctly moved between inventories |
| `test_self_transfer_status_completed` | Verify self-transfer trades have COMPLETED status immediately |
| `test_self_transfer_records_history` | Verify CREATED and COMPLETED history entries are recorded for self-transfer |

---

## 11. Concurrent Trade Tests

### Class: `TestConcurrentTrades`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_multiple_pending_trades_same_card` | Verify multiple trades can be pending on the same card as long as total locked <= available |
| `test_concurrent_trade_fails_exceeds_available` | Verify creating a trade fails when total locked_quantity across pending trades exceeds available |
| `test_accepting_trade_validates_current_locked_quantity` | Verify accepting checks current locked_quantity at accept time, not just at creation |
| `test_cancel_one_trade_frees_quantity_for_another` | Verify cancelling one trade frees locked_quantity allowing another trade to proceed |
| `test_counter_offer_chain_locks_correctly` | Verify lock/unlock is handled correctly through a chain of counter-offers |
| `test_race_condition_double_accept` | Verify proper handling when two trades try to lock the same cards simultaneously |

---

## 12. Admin Cleanup Endpoint Tests

### Class: `TestTradeCleanup`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_cleanup_dry_run_returns_counts` | Verify dry_run=True returns counts without deleting data |
| `test_cleanup_deletes_old_resolved_trades` | Verify resolved trades older than retention_days are cleaned up |
| `test_cleanup_preserves_recent_resolved_trades` | Verify resolved trades within retention_days are preserved |
| `test_cleanup_preserves_active_trades` | Verify PENDING and ACCEPTED trades are never cleaned up |
| `test_cleanup_removes_escrow_and_recipient_rows` | Verify trade_escrow and trade_recipient rows are deleted for cleaned trades |
| `test_cleanup_custom_retention_days` | Verify custom retention_days parameter is respected |
| `test_cleanup_returns_deleted_counts` | Verify response includes accurate counts of deleted rows |

---

## 13. Integration Tests (Real Database)

### File: `backend/tests/integration/test_integration_trades.py`

### Class: `TestTradeIntegration`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_full_trade_flow_accept_confirm_complete` | End-to-end test: create trade -> accept -> confirm -> verify cards transferred |
| `test_full_trade_flow_counter_offer_chain` | End-to-end test: create -> counter -> counter -> accept -> confirm -> complete |
| `test_trade_locked_quantity_persists` | Verify locked_quantity is correctly persisted and updated in database |
| `test_trade_history_chain_persists` | Verify trade_history records are correctly stored with proper sequence numbers |
| `test_trade_cascade_on_user_delete` | Verify trade data is properly handled when a user is deleted |
| `test_trade_foreign_key_constraints` | Verify foreign key constraints (inventory_id, user_id, card_id) are enforced |

### Class: `TestSelfTransferIntegration`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_self_transfer_moves_cards_between_inventories` | Verify cards are actually moved between user's inventories in database |
| `test_self_transfer_quantity_consistency` | Verify total card count remains consistent before and after self-transfer |

### Class: `TestConcurrentTradesIntegration`

| Test Function | Test Case Description |
|---------------|----------------------|
| `test_locked_quantity_accumulation` | Verify locked_quantity correctly accumulates with multiple pending trades in real DB |
| `test_locked_quantity_released_on_resolution` | Verify locked_quantity is correctly released when trades are resolved |

---

## Required Test Fixtures

### Unit Test Fixtures (add to `backend/tests/unit/conftest.py`)

```python
# Sample trade IDs
sample_trade_id: UUID
sample_root_trade_id: UUID

# Sample trade data
sample_trade_data: Dict  # PENDING trade with all required fields
sample_accepted_trade_data: Dict  # ACCEPTED trade with confirmation flags
sample_completed_trade_data: Dict  # COMPLETED trade
sample_trade_with_counter: Dict  # Trade that has been countered

# Sample trade cards
sample_escrow_cards: list[dict]  # Cards being offered by initiator
sample_requested_cards: list[dict]  # Cards requested from recipient

# Sample trade history
sample_trade_history_data: list[dict]  # List of history entries for a chain

# Sample inventory card with locked_quantity
sample_inventory_card_with_lock: Dict  # Card with non-zero locked_quantity
```

### Integration Test Fixtures (add to `backend/tests/integration/conftest.py`)

```python
# Test users for trading (need two users)
test_trade_initiator: Dict  # First test user (initiator)
test_trade_recipient: Dict  # Second test user (recipient)

# Test inventories for trading
test_initiator_inventory: Dict  # Initiator's inventory with cards
test_recipient_inventory: Dict  # Recipient's inventory with cards

# Pre-populated inventories with tradeable cards
test_trading_setup: Dict  # Complete setup with users, inventories, and cards ready for trading
```

---

## Test Summary

| Category | Test Count |
|----------|------------|
| locked_quantity Field | 8 |
| Counter Offering | 12 |
| Accept Trade | 9 |
| Confirm Trade | 12 |
| Unconfirm Trade | 7 |
| Reject Trade | 7 |
| Cancel Trade | 8 |
| Trade History Recording | 7 |
| Get Trade History Chain | 7 |
| Self-Transfer | 6 |
| Concurrent Trades | 6 |
| Admin Cleanup | 7 |
| Integration Tests | 10 |
| **Total** | **106** |

---

## Critical Files to Modify

1. **Create:** `backend/tests/unit/test_trade_endpoints.py` - Unit tests with mocked Supabase
2. **Create:** `backend/tests/integration/test_integration_trades.py` - Integration tests with real database
3. **Modify:** `backend/tests/unit/conftest.py` - Add trade-related unit test fixtures
4. **Modify:** `backend/tests/integration/conftest.py` - Add trade-related integration test fixtures
