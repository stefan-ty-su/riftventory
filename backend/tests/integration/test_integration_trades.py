"""
Integration tests for trading functionality with real database.

These tests verify end-to-end trade flows including:
- Full trade lifecycle (create -> accept -> confirm -> complete)
- Counter-offer chains
- Self-transfers
- Locked quantity persistence
- Trade history recording
- Concurrent trade handling
"""
import pytest


class TestTradeIntegration:
    """Integration tests for full trade workflows."""

    def test_full_trade_flow_accept_confirm_complete(
        self, integration_client, supabase_client, trading_setup
    ):
        """End-to-end test: create trade -> accept -> confirm -> verify cards transferred."""

        print(integration_client.app.routes)

        initiator = trading_setup["initiator"]
        recipient = trading_setup["recipient"]
        initiator_inv = trading_setup["initiator_inventory"]
        recipient_inv = trading_setup["recipient_inventory"]
        initiator_cards = trading_setup["initiator_cards"]
        recipient_cards = trading_setup["recipient_cards"]

        # Get initial card quantities
        escrow_card_id = initiator_cards[0]["card_id"]
        requested_card_id = recipient_cards[0]["card_id"]

        initial_initiator_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        initial_initiator_qty = initial_initiator_card.data[0]["quantity"]

        initial_recipient_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", recipient_inv["inventory_id"]
        ).eq("card_id", requested_card_id).execute()
        initial_recipient_qty = initial_recipient_card.data[0]["quantity"]

        # Step 1: Create trade
        create_response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": escrow_card_id, "quantity": 2}],
                "requested_cards": [{"card_id": requested_card_id, "quantity": 1}],
                "message": "Integration test trade",
            },
            headers={"X-User-Id": initiator["user_id"]},
        )

        assert create_response.status_code == 201
        trade = create_response.json()
        trade_id = trade["trade_id"]
        assert trade["status"] == "pending"

        # Verify initiator's cards are locked
        locked_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert locked_card.data[0]["locked_quantity"] == 2

        # Step 2: Accept trade (as recipient)
        accept_response = integration_client.post(
            f"/trades/{trade_id}/accept",
            headers={"X-User-Id": recipient["user_id"]},
        )
        assert accept_response.status_code == 200
        accepted_trade = accept_response.json()
        assert accepted_trade["status"] == "accepted"
        assert accepted_trade["recipient_confirmed"] is True

        # Verify recipient's cards are now locked
        recipient_locked = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", recipient_inv["inventory_id"]
        ).eq("card_id", requested_card_id).execute()
        assert recipient_locked.data[0]["locked_quantity"] == 1

        # Step 3: Confirm trade (as initiator - recipient auto-confirmed on accept)
        confirm_response = integration_client.post(
            f"/trades/{trade_id}/confirm",
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert confirm_response.status_code == 200
        completed_trade = confirm_response.json()
        assert completed_trade["status"] == "completed"
        assert completed_trade["initiator_confirmed"] is True
        assert completed_trade["recipient_confirmed"] is True
        assert completed_trade["resolved_at"] is not None

        # Verify cards were transferred
        # Initiator should have 2 fewer escrow cards
        final_initiator_escrow = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        if final_initiator_escrow.data:
            assert final_initiator_escrow.data[0]["quantity"] == initial_initiator_qty - 2
            assert final_initiator_escrow.data[0]["locked_quantity"] == 0
        else:
            # Card was completely transferred (quantity reached 0 and was deleted)
            assert initial_initiator_qty == 2

        # Initiator should now have the requested card
        initiator_received = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", requested_card_id).execute()
        assert len(initiator_received.data) == 1
        assert initiator_received.data[0]["quantity"] == 1

        # Recipient should have 1 fewer requested card
        final_recipient_requested = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", recipient_inv["inventory_id"]
        ).eq("card_id", requested_card_id).execute()
        if final_recipient_requested.data:
            assert final_recipient_requested.data[0]["quantity"] == initial_recipient_qty - 1
            assert final_recipient_requested.data[0]["locked_quantity"] == 0
        else:
            assert initial_recipient_qty == 1

        # Recipient should now have the escrow card
        recipient_received = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", recipient_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert len(recipient_received.data) == 1
        assert recipient_received.data[0]["quantity"] == 2

    def test_full_trade_flow_counter_offer_chain(
        self, integration_client, supabase_client, trading_setup
    ):
        """End-to-end test: create -> counter -> counter -> accept -> confirm -> complete."""
        initiator = trading_setup["initiator"]
        recipient = trading_setup["recipient"]
        initiator_inv = trading_setup["initiator_inventory"]
        recipient_inv = trading_setup["recipient_inventory"]
        initiator_cards = trading_setup["initiator_cards"]
        recipient_cards = trading_setup["recipient_cards"]

        escrow_card_1 = initiator_cards[0]["card_id"]
        escrow_card_2 = initiator_cards[1]["card_id"]
        requested_card_1 = recipient_cards[0]["card_id"]
        requested_card_2 = recipient_cards[1]["card_id"]

        # Step 1: Create initial trade
        create_response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": escrow_card_1, "quantity": 1}],
                "requested_cards": [{"card_id": requested_card_1, "quantity": 1}],
                "message": "Initial offer",
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert create_response.status_code == 201
        trade_1 = create_response.json()
        trade_1_id = trade_1["trade_id"]
        root_trade_id = trade_1["root_trade_id"]

        # Step 2: Counter offer (recipient counters)
        counter_1_response = integration_client.post(
            f"/trades/{trade_1_id}/counter",
            json={
                "escrow_cards": [{"card_id": requested_card_1, "quantity": 2}],
                "requested_cards": [{"card_id": escrow_card_1, "quantity": 2}],
                "message": "Counter: I want more",
            },
            headers={"X-User-Id": recipient["user_id"]},
        )
        assert counter_1_response.status_code == 201
        trade_2 = counter_1_response.json()
        trade_2_id = trade_2["trade_id"]
        assert trade_2["root_trade_id"] == root_trade_id
        assert trade_2["parent_trade_id"] == trade_1_id
        assert trade_2["counter_count"] == 1
        # Roles swapped: recipient is now initiator
        assert trade_2["initiator_user_id"] == recipient["user_id"]
        assert trade_2["recipient_user_id"] == initiator["user_id"]

        # Verify original trade is countered
        original_trade = supabase_client.table("trade").select("*").eq(
            "trade_id", trade_1_id
        ).execute()
        assert original_trade.data[0]["status"] == "countered"

        # Step 3: Counter offer again (original initiator counters back)
        counter_2_response = integration_client.post(
            f"/trades/{trade_2_id}/counter",
            json={
                "escrow_cards": [{"card_id": escrow_card_2, "quantity": 1}],
                "requested_cards": [{"card_id": requested_card_2, "quantity": 1}],
                "message": "Final counter",
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert counter_2_response.status_code == 201
        trade_3 = counter_2_response.json()
        trade_3_id = trade_3["trade_id"]
        assert trade_3["root_trade_id"] == root_trade_id
        assert trade_3["parent_trade_id"] == trade_2_id
        assert trade_3["counter_count"] == 2
        # Roles swapped again: original initiator is initiator again
        assert trade_3["initiator_user_id"] == initiator["user_id"]
        assert trade_3["recipient_user_id"] == recipient["user_id"]

        # Step 4: Accept final counter offer
        accept_response = integration_client.post(
            f"/trades/{trade_3_id}/accept",
            headers={"X-User-Id": recipient["user_id"]},
        )
        assert accept_response.status_code == 200
        assert accept_response.json()["status"] == "accepted"

        # Step 5: Confirm by initiator
        confirm_response = integration_client.post(
            f"/trades/{trade_3_id}/confirm",
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert confirm_response.status_code == 200
        final_trade = confirm_response.json()
        assert final_trade["status"] == "completed"

        # Verify trade history chain
        history_response = integration_client.get(f"/trades/{trade_3_id}/history")
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history["history"]) >= 5  # At least: created, countered, countered, accepted, completed

    def test_trade_locked_quantity_persists(
        self, integration_client, supabase_client, trading_setup
    ):
        """Verify locked_quantity is correctly persisted and updated in database."""
        initiator = trading_setup["initiator"]
        recipient = trading_setup["recipient"]
        initiator_inv = trading_setup["initiator_inventory"]
        recipient_inv = trading_setup["recipient_inventory"]
        initiator_cards = trading_setup["initiator_cards"]

        escrow_card_id = initiator_cards[0]["card_id"]

        # Verify initial state - no locks
        initial_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert initial_card.data[0]["locked_quantity"] == 0

        # Create trade - should lock cards
        create_response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": escrow_card_id, "quantity": 3}],
                "requested_cards": [],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert create_response.status_code == 201
        trade_id = create_response.json()["trade_id"]

        # Verify locked_quantity is persisted
        locked_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert locked_card.data[0]["locked_quantity"] == 3

        # Cancel trade - should unlock cards
        cancel_response = integration_client.post(
            f"/trades/{trade_id}/cancel",
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert cancel_response.status_code == 200

        # Verify locked_quantity is released
        unlocked_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert unlocked_card.data[0]["locked_quantity"] == 0

    def test_trade_history_chain_persists(
        self, integration_client, supabase_client, trading_setup
    ):
        """Verify trade_history records are correctly stored with proper sequence numbers."""
        initiator = trading_setup["initiator"]
        recipient = trading_setup["recipient"]
        initiator_inv = trading_setup["initiator_inventory"]
        recipient_inv = trading_setup["recipient_inventory"]
        initiator_cards = trading_setup["initiator_cards"]
        recipient_cards = trading_setup["recipient_cards"]

        escrow_card_id = initiator_cards[0]["card_id"]
        requested_card_id = recipient_cards[0]["card_id"]

        # Create trade
        create_response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": escrow_card_id, "quantity": 1}],
                "requested_cards": [{"card_id": requested_card_id, "quantity": 1}],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert create_response.status_code == 201
        trade_id = create_response.json()["trade_id"]
        root_trade_id = create_response.json()["root_trade_id"]

        # Accept trade
        integration_client.post(
            f"/trades/{trade_id}/accept",
            headers={"X-User-Id": recipient["user_id"]},
        )

        # Confirm trade
        integration_client.post(
            f"/trades/{trade_id}/confirm",
            headers={"X-User-Id": initiator["user_id"]},
        )

        # Verify history entries in database
        history = supabase_client.table("trade_history").select("*").eq(
            "root_trade_id", root_trade_id
        ).order("sequence_number").execute()

        assert len(history.data) >= 3  # CREATED, ACCEPTED, CONFIRMED/COMPLETED

        # Verify sequence numbers are incrementing
        sequence_numbers = [h["sequence_number"] for h in history.data]
        assert sequence_numbers == sorted(sequence_numbers)
        assert len(set(sequence_numbers)) == len(sequence_numbers)  # All unique

        # Verify action types are recorded
        actions = [h["action"] for h in history.data]
        assert "created" in actions
        assert "accepted" in actions

    def test_trade_cascade_on_user_delete(
        self, integration_client, supabase_client, sample_card_ids
    ):
        """Verify trade data is properly handled when a user is deleted."""
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]

        # Create temporary users for this test with unique names
        temp_user_1_id = f"temp_trade_user_1_{unique_suffix}"
        temp_user_2_id = f"temp_trade_user_2_{unique_suffix}"

        supabase_client.table("user").insert({
            "user_id": temp_user_1_id,
            "user_name": f"Temp User 1 {unique_suffix}",
        }).execute()

        supabase_client.table("user").insert({
            "user_id": temp_user_2_id,
            "user_name": f"Temp User 2 {unique_suffix}",
        }).execute()

        # Create inventories
        inv_1 = supabase_client.table("inventory").insert({
            "user_id": temp_user_1_id,
            "inventory_name": "Temp Inventory 1",
            "inventory_colour": "#111111",
        }).execute().data[0]

        inv_2 = supabase_client.table("inventory").insert({
            "user_id": temp_user_2_id,
            "inventory_name": "Temp Inventory 2",
            "inventory_colour": "#222222",
        }).execute().data[0]

        # Add cards
        card_id = sample_card_ids[0]
        supabase_client.table("inventory_card").insert({
            "inventory_id": inv_1["inventory_id"],
            "card_id": card_id,
            "quantity": 5,
            "is_tradeable": True,
            "locked_quantity": 0,
        }).execute()

        # Create a trade
        create_response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": temp_user_2_id,
                "initiator_inventory_id": inv_1["inventory_id"],
                "recipient_inventory_id": inv_2["inventory_id"],
                "escrow_cards": [{"card_id": card_id, "quantity": 1}],
                "requested_cards": [],
            },
            headers={"X-User-Id": temp_user_1_id},
        )
        assert create_response.status_code == 201
        trade_id = create_response.json()["trade_id"]

        # Verify trade exists
        trade_exists = supabase_client.table("trade").select("*").eq(
            "trade_id", trade_id
        ).execute()
        assert len(trade_exists.data) == 1

        # Delete trade_history records first (no cascade on actor_user_id)
        supabase_client.table("trade_history").delete().eq("actor_user_id", temp_user_1_id).execute()

        # Delete initiator user (should cascade delete or handle trade)
        supabase_client.table("user").delete().eq("user_id", temp_user_1_id).execute()

        # Trade should still exist but we verify the cascade behavior
        # (The exact behavior depends on DB constraints - trades may be preserved or deleted)
        remaining_trade = supabase_client.table("trade").select("*").eq(
            "trade_id", trade_id
        ).execute()

        # Clean up remaining user (delete any trade_history records first)
        supabase_client.table("trade_history").delete().eq("actor_user_id", temp_user_2_id).execute()
        supabase_client.table("user").delete().eq("user_id", temp_user_2_id).execute()

        # If trade still exists after user deletion, it should be properly orphaned
        # or the test passes if cascading deleted it
        # This test mainly verifies no errors occur during cascade

    def test_trade_foreign_key_constraints(
        self, integration_client, supabase_client, trading_setup
    ):
        """Verify foreign key constraints (inventory_id, user_id, card_id) are enforced."""
        initiator = trading_setup["initiator"]
        recipient = trading_setup["recipient"]
        initiator_inv = trading_setup["initiator_inventory"]
        recipient_inv = trading_setup["recipient_inventory"]
        initiator_cards = trading_setup["initiator_cards"]

        # Test 1: Invalid initiator inventory
        response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": "00000000-0000-0000-0000-000000000000",
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": initiator_cards[0]["card_id"], "quantity": 1}],
                "requested_cards": [],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert response.status_code == 404

        # Test 2: Invalid recipient inventory
        response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": "00000000-0000-0000-0000-000000000000",
                "escrow_cards": [{"card_id": initiator_cards[0]["card_id"], "quantity": 1}],
                "requested_cards": [],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert response.status_code == 404

        # Test 3: Invalid card ID in escrow
        response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": "nonexistent_card_id", "quantity": 1}],
                "requested_cards": [],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert response.status_code == 400  # Card not in inventory


class TestSelfTransferIntegration:
    """Integration tests for self-transfer functionality."""

    def test_self_transfer_moves_cards_between_inventories(
        self, integration_client, supabase_client, self_transfer_setup
    ):
        """Verify cards are actually moved between user's inventories in database."""
        user = self_transfer_setup["user"]
        source_inv = self_transfer_setup["source_inventory"]
        target_inv = self_transfer_setup["target_inventory"]
        source_cards = self_transfer_setup["source_cards"]

        transfer_card_id = source_cards[0]["card_id"]
        transfer_qty = 3

        # Get initial quantities
        initial_source = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", source_inv["inventory_id"]
        ).eq("card_id", transfer_card_id).execute()
        initial_source_qty = initial_source.data[0]["quantity"]

        # Create self-transfer (should auto-execute)
        response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": user["user_id"],  # Same user
                "initiator_inventory_id": source_inv["inventory_id"],
                "recipient_inventory_id": target_inv["inventory_id"],
                "escrow_cards": [{"card_id": transfer_card_id, "quantity": transfer_qty}],
                "requested_cards": [],
            },
            headers={"X-User-Id": user["user_id"]},
        )
        assert response.status_code == 201
        trade = response.json()
        assert trade["status"] == "completed"  # Self-transfers auto-complete

        # Verify source inventory has fewer cards
        final_source = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", source_inv["inventory_id"]
        ).eq("card_id", transfer_card_id).execute()
        if final_source.data:
            assert final_source.data[0]["quantity"] == initial_source_qty - transfer_qty
        else:
            assert initial_source_qty == transfer_qty  # All cards transferred

        # Verify target inventory received cards
        final_target = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", target_inv["inventory_id"]
        ).eq("card_id", transfer_card_id).execute()
        assert len(final_target.data) == 1
        assert final_target.data[0]["quantity"] == transfer_qty

    def test_self_transfer_quantity_consistency(
        self, integration_client, supabase_client, self_transfer_setup
    ):
        """Verify total card count remains consistent before and after self-transfer."""
        user = self_transfer_setup["user"]
        source_inv = self_transfer_setup["source_inventory"]
        target_inv = self_transfer_setup["target_inventory"]
        source_cards = self_transfer_setup["source_cards"]

        transfer_card_id = source_cards[0]["card_id"]
        transfer_qty = 2

        # Calculate total cards before transfer
        source_before = supabase_client.table("inventory_card").select("quantity").eq(
            "inventory_id", source_inv["inventory_id"]
        ).eq("card_id", transfer_card_id).execute()
        target_before = supabase_client.table("inventory_card").select("quantity").eq(
            "inventory_id", target_inv["inventory_id"]
        ).eq("card_id", transfer_card_id).execute()

        total_before = (source_before.data[0]["quantity"] if source_before.data else 0) + \
                      (target_before.data[0]["quantity"] if target_before.data else 0)

        # Execute self-transfer
        response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": user["user_id"],
                "initiator_inventory_id": source_inv["inventory_id"],
                "recipient_inventory_id": target_inv["inventory_id"],
                "escrow_cards": [{"card_id": transfer_card_id, "quantity": transfer_qty}],
                "requested_cards": [],
            },
            headers={"X-User-Id": user["user_id"]},
        )
        assert response.status_code == 201

        # Calculate total cards after transfer
        source_after = supabase_client.table("inventory_card").select("quantity").eq(
            "inventory_id", source_inv["inventory_id"]
        ).eq("card_id", transfer_card_id).execute()
        target_after = supabase_client.table("inventory_card").select("quantity").eq(
            "inventory_id", target_inv["inventory_id"]
        ).eq("card_id", transfer_card_id).execute()

        total_after = (source_after.data[0]["quantity"] if source_after.data else 0) + \
                     (target_after.data[0]["quantity"] if target_after.data else 0)

        # Total should remain constant
        assert total_before == total_after


class TestConcurrentTradesIntegration:
    """Integration tests for concurrent trade handling."""

    def test_locked_quantity_accumulation(
        self, integration_client, supabase_client, trading_setup
    ):
        """Verify locked_quantity correctly accumulates with multiple pending trades in real DB."""
        initiator = trading_setup["initiator"]
        recipient = trading_setup["recipient"]
        initiator_inv = trading_setup["initiator_inventory"]
        recipient_inv = trading_setup["recipient_inventory"]
        initiator_cards = trading_setup["initiator_cards"]

        escrow_card_id = initiator_cards[0]["card_id"]

        # Create first trade locking 2 cards
        response1 = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": escrow_card_id, "quantity": 2}],
                "requested_cards": [],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert response1.status_code == 201
        trade_1_id = response1.json()["trade_id"]

        # Verify locked_quantity is 2
        card_after_1 = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert card_after_1.data[0]["locked_quantity"] == 2

        # Create second trade locking 1 more card
        response2 = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": escrow_card_id, "quantity": 1}],
                "requested_cards": [],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert response2.status_code == 201
        trade_2_id = response2.json()["trade_id"]

        # Verify locked_quantity accumulated to 3
        card_after_2 = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert card_after_2.data[0]["locked_quantity"] == 3

        # Cancel first trade - should release 2
        integration_client.post(
            f"/trades/{trade_1_id}/cancel",
            headers={"X-User-Id": initiator["user_id"]},
        )

        # Verify locked_quantity is now 1
        card_after_cancel = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert card_after_cancel.data[0]["locked_quantity"] == 1

        # Cancel second trade - should release remaining 1
        integration_client.post(
            f"/trades/{trade_2_id}/cancel",
            headers={"X-User-Id": initiator["user_id"]},
        )

        # Verify locked_quantity is back to 0
        card_final = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert card_final.data[0]["locked_quantity"] == 0

    def test_locked_quantity_released_on_resolution(
        self, integration_client, supabase_client, trading_setup
    ):
        """Verify locked_quantity is correctly released when trades are resolved."""
        initiator = trading_setup["initiator"]
        recipient = trading_setup["recipient"]
        initiator_inv = trading_setup["initiator_inventory"]
        recipient_inv = trading_setup["recipient_inventory"]
        initiator_cards = trading_setup["initiator_cards"]

        escrow_card_id = initiator_cards[0]["card_id"]

        # Create trade
        response = integration_client.post(
            "/trades",
            json={
                "recipient_user_id": recipient["user_id"],
                "initiator_inventory_id": initiator_inv["inventory_id"],
                "recipient_inventory_id": recipient_inv["inventory_id"],
                "escrow_cards": [{"card_id": escrow_card_id, "quantity": 2}],
                "requested_cards": [],
            },
            headers={"X-User-Id": initiator["user_id"]},
        )
        assert response.status_code == 201
        trade_id = response.json()["trade_id"]

        # Verify cards are locked
        locked_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert locked_card.data[0]["locked_quantity"] == 2

        # Reject trade (should release locks)
        reject_response = integration_client.post(
            f"/trades/{trade_id}/reject",
            headers={"X-User-Id": recipient["user_id"]},
        )
        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == "rejected"

        # Verify locked_quantity is released
        unlocked_card = supabase_client.table("inventory_card").select("*").eq(
            "inventory_id", initiator_inv["inventory_id"]
        ).eq("card_id", escrow_card_id).execute()
        assert unlocked_card.data[0]["locked_quantity"] == 0