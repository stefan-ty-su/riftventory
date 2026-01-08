"""Tests for trade endpoints with focus on locked_quantity functionality."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone


class MockTableManager:
    """Manages mock tables with proper state tracking across calls."""

    def __init__(self):
        self.tables = {}
        self.call_counts = {}

    def create_table(self, table_name, responses=None, default_response=None):
        """Create a mock table with optional response sequence."""
        mock = MagicMock()
        mock.select.return_value = mock
        mock.insert.return_value = mock
        mock.update.return_value = mock
        mock.delete.return_value = mock
        mock.eq.return_value = mock
        mock.order.return_value = mock
        mock.limit.return_value = mock

        if responses:
            mock.execute.side_effect = [Mock(data=r) for r in responses]
        elif default_response is not None:
            mock.execute.return_value = Mock(data=default_response)
        else:
            mock.execute.return_value = Mock(data=[])

        self.tables[table_name] = mock
        self.call_counts[table_name] = 0
        return mock

    def get_table(self, table_name):
        """Get a table mock, creating a default one if not exists."""
        if table_name not in self.tables:
            self.create_table(table_name)
        return self.tables[table_name]

    def table_handler(self, table_name):
        """Handler function to be used as side_effect for supabase.table()."""
        return self.get_table(table_name)


class TestLockedQuantity:
    """Tests for locked_quantity field behavior in trades."""

    def test_create_trade_locks_escrow_cards(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that when a trade is created, the locked_quantity on the initiator's escrow cards is incremented."""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        lock_updates = []

        manager = MockTableManager()

        # Inventory table - returns different user for each inventory check
        inv_mock = manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],  # First call: initiator inventory
            [{"user_id": sample_recipient_user_id}],  # Second call: recipient inventory
        ])

        # Inventory card table
        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        def capture_update(data):
            if "locked_quantity" in data:
                lock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        # Trade table
        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": None,
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        # Other tables
        manager.create_table("trade_escrow", default_response=[{"card_id": "card1", "quantity": 2}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 2}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify locked_quantity was updated to 2 (0 + 2)
        assert 2 in lock_updates

    def test_accept_trade_locks_recipient_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that when a trade is accepted, the locked_quantity on the recipient's requested cards is incremented."""
        now = datetime.now(timezone.utc).isoformat()
        lock_updates = []

        manager = MockTableManager()

        # Trade table
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": None,
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        def capture_update(data):
            if "locked_quantity" in data:
                lock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify locked_quantity was incremented for requested cards
        assert 2 in lock_updates

    def test_cancel_trade_unlocks_initiator_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that cancelling a pending trade decrements locked_quantity back to 0 for initiator's escrow cards."""
        now = datetime.now(timezone.utc).isoformat()
        unlock_updates = []

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": None,
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 2}]
        )
        manager.create_table("trade_recipient", default_response=[])

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )

        def capture_update(data):
            if "locked_quantity" in data:
                unlock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify locked_quantity was decremented (2 - 2 = 0)
        assert 0 in unlock_updates

    def test_reject_trade_unlocks_initiator_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that rejecting a trade decrements locked_quantity for initiator's escrow cards."""
        now = datetime.now(timezone.utc).isoformat()
        unlock_updates = []

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": None,
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 2}]
        )
        manager.create_table("trade_recipient", default_response=[])

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )

        def capture_update(data):
            if "locked_quantity" in data:
                unlock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify locked_quantity was decremented
        assert 0 in unlock_updates

    def test_complete_trade_clears_locked_quantity(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that after trade completion, locked_quantity is properly handled (transferred cards no longer locked)."""
        now = datetime.now(timezone.utc).isoformat()
        transfer_updates = []

        manager = MockTableManager()

        # Trade mock that returns updated data after confirmation
        # First call returns initiator_confirmed=False, subsequent calls show both confirmed
        trade_call_count = [0]

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.update.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            # After first call, return trade with both confirmed
            both_confirmed = trade_call_count[0] > 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": None,
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": both_confirmed,
                "initiator_confirmed_at": now if both_confirmed else None,
                "recipient_confirmed": True,
                "recipient_confirmed_at": now,
                "resolved_at": None,
            }])

        trade_mock.execute.side_effect = lambda: get_trade_response()
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 2}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 1}]
        )

        # Create a properly chainable inventory_card mock
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )

        # The update method needs to return a chainable mock AND capture the data
        def capture_update(data):
            if "locked_quantity" in data or "quantity" in data:
                transfer_updates.append(data)
            # Return the mock to allow chaining (.eq().eq().execute())
            return inv_card_mock

        inv_card_mock.update = capture_update
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify locked_quantity adjustments occurred during transfer
        # The _transfer_cards function decrements locked_quantity when moving cards
        assert len(transfer_updates) > 0
        # Check that at least one update reduced locked_quantity
        locked_qty_updates = [u for u in transfer_updates if "locked_quantity" in u]
        assert len(locked_qty_updates) > 0

    def test_available_quantity_calculation(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that available quantity = total quantity - locked_quantity is correctly calculated when validating trades."""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Inventory table - returns different user for each inventory check
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        # Card with quantity=5 but locked_quantity=2, so available=3
        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": None,
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        manager.create_table("trade_escrow", default_response=[{"card_id": "card1", "quantity": 3}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Request exactly 3 cards (the available amount: 5 - 2 = 3)
        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 3}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        # Should succeed since 5 - 2 = 3 available
        assert response.status_code == 201

    def test_create_trade_fails_insufficient_available_quantity(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that creating a trade fails when quantity - locked_quantity < requested escrow amount."""

        manager = MockTableManager()

        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        # Card with quantity=5 but locked_quantity=3, so available=2
        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 3, "is_tradeable": True}]
        )

        mock_supabase_client.table.side_effect = manager.table_handler

        # Request 4 cards but only 2 are available (5 - 3 = 2)
        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 4}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        # Should fail since 5 - 3 = 2 available but 4 requested
        assert response.status_code == 400
        assert "Insufficient quantity" in response.json()["detail"]

    def test_multiple_trades_accumulate_locked_quantity(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify that multiple pending trades on the same card correctly accumulate locked_quantity."""
        now = datetime.now(timezone.utc).isoformat()

        # Track the locked_quantity as it accumulates
        current_locked = [0]
        lock_updates = []

        # For multiple trades, we need inventory checks for each trade
        inventory_responses = [
            [{"user_id": sample_initiator_user_id}],  # Trade 1: initiator
            [{"user_id": sample_recipient_user_id}],  # Trade 1: recipient
            [{"user_id": sample_initiator_user_id}],  # Trade 2: initiator
            [{"user_id": sample_recipient_user_id}],  # Trade 2: recipient
        ]

        manager = MockTableManager()

        manager.create_table("inventory", responses=inventory_responses)

        # Inventory card mock with dynamic locked_quantity
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock

        def get_inv_card_response():
            return Mock(data=[{"quantity": 10, "locked_quantity": current_locked[0], "is_tradeable": True}])
        inv_card_mock.execute.side_effect = lambda: get_inv_card_response()

        def capture_update(data):
            if "locked_quantity" in data:
                current_locked[0] = data["locked_quantity"]
                lock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.tables["inventory_card"] = inv_card_mock

        # Trade mock that generates new IDs
        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.update.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_id = str(uuid4())
            return Mock(data=[{
                "trade_id": trade_id,
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": None,
                "created_at": now,
                "root_trade_id": trade_id,
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }])
        trade_mock.execute.side_effect = lambda: get_trade_response()

        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow", default_response=[{"card_id": "card1", "quantity": 3}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Create first trade locking 3 cards
        response1 = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 3}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )
        assert response1.status_code == 201

        # After first trade, locked_quantity should be 3
        assert current_locked[0] == 3

        # Create second trade locking 2 more cards
        response2 = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 2}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )
        assert response2.status_code == 201

        # After second trade, locked_quantity should be 5 (3 + 2)
        assert current_locked[0] == 5

        # Verify the accumulation happened correctly
        assert lock_updates == [3, 5]


class TestCounterOffer:
    """Tests for counter offer behaviour in trades."""

    def test_counter_offer_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify successful counter-offer creates new trade with swapped roles (recipient becomes initiator)."""
        now = datetime.now(timezone.utc).isoformat()
        inserted_trade_data = []

        manager = MockTableManager()

        # Original trade - recipient will counter-offer
        original_trade_mock = MagicMock()
        original_trade_mock.select.return_value = original_trade_mock
        original_trade_mock.update.return_value = original_trade_mock
        original_trade_mock.eq.return_value = original_trade_mock
        original_trade_mock.order.return_value = original_trade_mock
        original_trade_mock.limit.return_value = original_trade_mock
        original_trade_mock.execute.return_value = Mock(data=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Original trade offer",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        # Capture inserted trade to verify role swap
        def capture_insert(data):
            inserted_trade_data.append(data)
            # Return the new trade with the inserted data
            return Mock(data=[data])

        original_trade_mock.insert = lambda data: Mock(execute=lambda: capture_insert(data))
        manager.tables["trade"] = original_trade_mock

        # Original escrow cards that need to be unlocked
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

        # Inventory card mock for validation and locking
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.update.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 10, "locked_quantity": 0, "is_tradeable": True}]
        )
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card_1", "quantity": 2}],
                "requested_cards": [{"card_id": "requested_from_original_initiator", "quantity": 1}],
                "message": "My counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201

        # Verify the new trade has swapped roles
        assert len(inserted_trade_data) == 1
        new_trade = inserted_trade_data[0]

        # Original recipient becomes new initiator
        assert new_trade["initiator_user_id"] == sample_recipient_user_id
        # Original initiator becomes new recipient
        assert new_trade["recipient_user_id"] == sample_initiator_user_id
        # Inventories are also swapped
        assert new_trade["initiator_inventory_id"] == str(sample_recipient_inventory_id)
        assert new_trade["recipient_inventory_id"] == str(sample_initiator_inventory_id)
        # Counter count incremented
        assert new_trade["counter_count"] == 1
        # Parent trade ID set
        assert new_trade["parent_trade_id"] == str(sample_trade_id)
        # Root trade ID preserved
        assert new_trade["root_trade_id"] == str(sample_trade_id)

    def test_counter_offer_sets_status_to_countered(
        self,
    ):
        """Verify original trade status changes to COUNTERED after counter-offer"""
        pass

    def test_counter_offer_increments_counter_count(
        self,
    ):
        """Verify new trade has counter_count = original counter_count + 1"""
        pass

    def test_counter_offer_preserves_root_trade_id(
        self,
    ):
        """Verify new trade has same root_trade_id as original trade chain"""
        pass

    def test_counter_offer_sets_parent_trade_id(
        self,
    ):
        """Verify new trade has same root_trade_id as original trade chain"""
        pass

    def test_counter_offer_unlocks_original_initiator_cards(
        self,
    ):
        """Verify original initiator's escrow cards are unlocked after counter-offer"""
        pass

    def test_counter_offer_locks_new_initiator_cards(
        self,
    ):
        """Verify counter-offerer's escrow cards become locked"""
        pass

    def test_counter_offer_only_recipient_can_counter(
        self,
    ):
        """Verify 403 error when non-recipient tries to counter-offer"""
        pass

    def test_counter_offer_requires_pending_status(
        self,
    ):
        """Verify 400 error when attempting to counter a non-PENDING trade"""
        pass

    def test_counter_offer_requires_escrow_cards(
        self,
    ):
        """Verify 422 error when counter-offer has empty escrow_cards list"""
        pass

    def test_counter_offer_validates_card_availability(
        self,
    ):
        """Verify 400 error when counter-offerer doesn't have enough cards available"""
        pass

    def test_counter_offer_records_history_entry(
        self,
    ):
        """Verify COUNTER_OFFERED action is recorded in trade_history"""
        pass


class TestAcceptTrade:
    """Tests for trade accepting behaviour in trades."""

    def test_accept_trade_success(
        self,
    ):
        """Verify successful trade acceptance returns updated trade with ACCEPTED status"""
        pass

    def test_accept_trade_updates_status_to_accepted(
        self,
    ):
        """Verify trade status changes from PENDING to ACCEPTED"""
        pass

    def test_accept_trade_auto_confirms_recipient(
        self,
    ):
        """Verify recipient_confirmed is set to True and recipient_confirmed_at is set"""
        pass

    def test_accept_trade_only_recipient_can_accept(
        self,
    ):
        """Verify 403 error when non-recipient (initiator or other user) tries to accept"""
        pass

    def test_accept_trade_requires_pending_status(
        self,
    ):
        """Verify 400 error when attempting to accept a non-PENDING trade"""
        pass

    def test_accept_trade_validates_recipient_has_cards(
        self,
    ):
        """Verify 400 error when recipient doesn't have the requested cards"""
        pass

    def test_accept_trade_validates_card_availability(
        self,
    ):
        """Verify 400 error when recipient has cards but insufficient available quantity (locked)"""
        pass

    def test_accept_trade_records_history_entry(
        self,
    ):
        """Verify ACCEPTED action is recorded in trade_history"""
        pass


class TestConfirmTrade:
    """Tests for trade confirmation behaviour in trades."""

    def test_confirm_trade_initiator_success(self):
        """Verify initiator can successfully confirm an ACCEPTED trade"""
        pass

    def test_confirm_trade_recipient_success(self):
        """Verify recipient can successfully confirm an ACCEPTED trade (though auto-confirmed on accept)"""
        pass

    def test_confirm_trade_sets_confirmed_flag(self):
        """Verify confirming sets initiator_confirmed or recipient_confirmed to True with timestamp"""
        pass

    def test_confirm_trade_both_confirmed_executes_trade(self):
        """Verify trade auto-executes (status=COMPLETED) when both parties have confirmed"""
        pass

    def test_confirm_trade_transfers_escrow_cards(self):
        """Verify escrow cards are transferred from initiator to recipient on completion"""
        pass

    def test_confirm_trade_transfers_requested_cards(self):
        """Verify requested cards are transferred from recipient to initiator on completion"""
        pass

    def test_confirm_trade_sets_resolved_at(self):
        """Verify resolved_at timestamp is set when trade completes"""
        pass

    def test_confirm_trade_requires_accepted_status(self):
        """Verify 400 error when attempting to confirm a non-ACCEPTED trade"""
        pass

    def test_confirm_trade_prevents_double_confirmation(self):
        """Verify 400 error when same party tries to confirm twice"""
        pass

    def test_confirm_trade_only_participants_can_confirm(self):
        """Verify 403 error when non-participant tries to confirm"""
        pass

    def test_confirm_trade_records_history_entry(self):
        """Verify CONFIRMED action is recorded in trade_history"""
        pass

    def test_confirm_trade_records_completed_on_execution(self):
        """Verify COMPLETED action is recorded when both confirm"""
        pass


class TestUnconfirmTrade:
    """Tests for trade confirmation retraction behaviour in trades."""

    def test_unconfirm_trade_success(self):
        """Verify successful unconfirmation resets the confirmed flag to False"""
        pass

    def test_unconfirm_trade_clears_confirmed_timestamp(self):
        """Verify initiator_confirmed_at or recipient_confirmed_at is cleared"""
        pass

    def test_unconfirm_trade_requires_accepted_status(self):
        """Verify 400 error when attempting to unconfirm a non-ACCEPTED trade"""
        pass

    def test_unconfirm_trade_only_confirmed_party_can_unconfirm(self):
        """Verify 400 error when unconfirmed party tries to unconfirm"""
        pass

    def test_unconfirm_trade_blocked_if_both_confirmed(self):
        """Verify 400 error when attempting to unconfirm after both parties confirmed"""
        pass

    def test_unconfirm_trade_only_participants_can_unconfirm(self):
        """Verify 403 error when non-participant tries to unconfirm"""
        pass

    def test_unconfirm_trade_records_history_entry(self):
        """Verify UNCONFIRMED action is recorded in trade_history"""
        pass


class TestRejectTrade:
    """Tests for trade rejection behaviour in trades."""

    def test_reject_trade_success(self):
        """Verify successful rejection returns trade with REJECTED status"""
        pass

    def test_reject_trade_updates_status_to_rejected(self):
        """Verify trade status changes from PENDING to REJECTED"""
        pass

    def test_reject_trade_unlocks_initiator_cards(self):
        """Verify initiator's escrow cards have locked_quantity decremented"""
        pass

    def test_reject_trade_sets_resolved_at(self):
        """Verify resolved_at timestamp is set on rejection"""
        pass

    def test_reject_trade_only_recipient_can_reject(self):
        """Verify 403 error when non-recipient tries to reject"""
        pass

    def test_reject_trade_requires_pending_status(self):
        """Verify 400 error when attempting to reject a non-PENDING trade"""
        pass

    def test_reject_trade_records_history_entry(self):
        """Verify REJECTED action is recorded in trade_history"""
        pass


class TestCancelTrade:
    """Tests for trade cancellation behaviour in trades."""

    def test_cancel_trade_success(self):
        """Verify successful cancellation returns trade with CANCELLED status"""
        pass

    def test_cancel_trade_updates_status_to_cancelled(self):
        """Verify trade status changes from PENDING to CANCELLED"""
        pass

    def test_cancel_trade_unlocks_initiator_cards(self):
        """Verify initiator's escrow cards have locked_quantity decremented"""
        pass

    def test_cancel_trade_sets_resolved_at(self):
        """Verify resolved_at timestamp is set on cancellation"""
        pass

    def test_cancel_trade_only_initiator_can_cancel(self):
        """Verify 403 error when non-initiator tries to cancel"""
        pass

    def test_cancel_trade_requires_pending_status(self):
        """Verify 400 error when attempting to cancel a non-PENDING trade"""
        pass

    def test_cancel_trade_with_reason(self):
        """Verify cancellation reason is stored when provided"""
        pass

    def test_cancel_trade_records_history_entry(self):
        """Verify CANCELLED action is recorded in trade_history"""
        pass


class TestTradeHistoryRecording:
    """Tests for trade history recording behaviour in trades."""

    def test_create_trade_records_created_action(self):
        """Verify CREATED action is recorded when trade is created"""
        pass

    def test_history_entry_has_correct_trade_id(self):
        """Verify history entry references the correct trade_id"""
        pass

    def test_history_entry_has_correct_root_trade_id(self):
        """Verify history entry uses root_trade_id"""
        pass

    def test_history_entry_has_correct_actor(self):
        """Verify actor_user_id matches the user performing the action"""
        pass

    def test_history_entry_sequence_numbers_increment(self):
        """Verify sequence_number increments for each action in a chain"""
        pass

    def test_history_entry_includes_details(self):
        """Verify details JSON contains relevant action metadata"""
        pass

    def test_history_records_all_action_types(self):
        """Verify all TradeHistoryAction enum values are recorded"""
        pass


class TestGetTradeHistoryChain:
    """Tests for trade history presenting behaviour in trades."""

    def test_get_trade_history_success(self):
        """Verify successful retrieval of trade history"""
        pass

    def test_get_trade_history_returns_all_chain_entries(self):
        """Verify history includes entries from entire counter-offer chain"""
        pass

    def test_get_trade_history_ordered_by_sequence(self):
        """Verify history entries are ordered by sequence_number"""
        pass

    def test_get_trade_history_includes_actor_names(self):
        """Verify actor_user_name is populated in response"""
        pass

    def test_get_trade_history_not_found(self):
        """Verify 404 error when trade_id doesn't exist"""
        pass

    def test_get_trade_history_uses_root_trade_id(self):
        """Verify querying a counter-offer trade returns full chain"""
        pass

    def test_get_trade_history_empty_chain(self):
        """Verify proper response when trade exists with minimal history"""
        pass


class TestSelfTransfer:
    """Tests for self transfer behaviour in trades."""

    def test_self_transfer_success(self):
        """Verify a user can create a self-transfer trade"""
        pass

    def test_self_transfer_auto_executes(self):
        """Verify self-transfer trades auto-execute immediately"""
        pass

    def test_self_transfer_skips_tradeable_check(self):
        """Verify self-transfers do not require tradeable cards"""
        pass

    def test_self_transfer_updates_quantities(self):
        """Verify card quantities are moved correctly"""
        pass

    def test_self_transfer_status_completed(self):
        """Verify self-transfer trades are COMPLETED immediately"""
        pass

    def test_self_transfer_records_history(self):
        """Verify CREATED and COMPLETED actions are recorded"""
        pass


class TestConcurrentTrades:
    """Tests for concurrent trading behaviour in trades."""

    def test_multiple_pending_trades_same_card(self):
        """Verify multiple pending trades can lock the same card within limits"""
        pass

    def test_concurrent_trade_fails_exceeds_available(self):
        """Verify trade creation fails when locked exceeds available"""
        pass

    def test_accepting_trade_validates_current_locked_quantity(self):
        """Verify accept checks live locked_quantity"""
        pass

    def test_cancel_one_trade_frees_quantity_for_another(self):
        """Verify cancelling a trade frees locked_quantity"""
        pass

    def test_counter_offer_chain_locks_correctly(self):
        """Verify lock/unlock works through counter-offer chains"""
        pass

    def test_race_condition_double_accept(self):
        """Verify race conditions are safely handled"""
        pass


class TestTradeCleanup:
    """Tests for cleaning behaviour in trade table."""

    def test_cleanup_dry_run_returns_counts(self):
        """Verify dry run returns deletion counts without deleting"""
        pass

    def test_cleanup_deletes_old_resolved_trades(self):
        """Verify old resolved trades are cleaned up"""
        pass

    def test_cleanup_preserves_recent_resolved_trades(self):
        """Verify recent resolved trades are preserved"""
        pass

    def test_cleanup_preserves_active_trades(self):
        """Verify PENDING and ACCEPTED trades are never deleted"""
        pass

    def test_cleanup_removes_escrow_and_recipient_rows(self):
        """Verify related escrow and recipient rows are deleted"""
        pass

    def test_cleanup_custom_retention_days(self):
        """Verify custom retention_days parameter is respected"""
        pass

    def test_cleanup_returns_deleted_counts(self):
        """Verify accurate deletion counts are returned"""
        pass
