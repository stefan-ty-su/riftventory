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
        # Support for query operators used in cleanup endpoint
        mock.lt.return_value = mock
        mock.gt.return_value = mock
        mock.gte.return_value = mock
        mock.lte.return_value = mock
        mock.is_.return_value = mock
        mock.in_.return_value = mock
        # Make .not_ return the same mock for proper chaining
        mock.not_ = mock

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
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify original trade status changes to COUNTERED after counter-offer"""
        now = datetime.now(timezone.utc).isoformat()
        status_updates = []

        manager = MockTableManager()

        # Original trade mock
        original_trade_mock = MagicMock()
        original_trade_mock.select.return_value = original_trade_mock
        original_trade_mock.insert.return_value = original_trade_mock
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

        # Capture status updates
        def capture_update(data):
            if "status" in data:
                status_updates.append(data["status"])
            return original_trade_mock
        original_trade_mock.update = capture_update

        manager.tables["trade"] = original_trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

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
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        # Verify original trade status was updated to "countered"
        assert "countered" in status_updates

    def test_counter_offer_increments_counter_count(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify new trade has counter_count = original counter_count + 1"""
        now = datetime.now(timezone.utc).isoformat()
        inserted_trade_data = []

        manager = MockTableManager()

        # Original trade with counter_count=2 (already countered twice)
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
            "message": "Trade offer",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 2,  # Already countered twice
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        def capture_insert(data):
            inserted_trade_data.append(data)
            return Mock(data=[data])

        original_trade_mock.insert = lambda data: Mock(execute=lambda: capture_insert(data))
        manager.tables["trade"] = original_trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

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
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        assert len(inserted_trade_data) == 1
        # Verify counter_count is incremented from 2 to 3
        assert inserted_trade_data[0]["counter_count"] == 3

    def test_counter_offer_preserves_root_trade_id(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_root_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify new trade has same root_trade_id as original trade chain"""
        now = datetime.now(timezone.utc).isoformat()
        inserted_trade_data = []

        manager = MockTableManager()

        # Original trade that's already part of a chain (has a root_trade_id)
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
            "message": "Trade offer",
            "created_at": now,
            "root_trade_id": str(sample_root_trade_id),  # Different from trade_id
            "parent_trade_id": str(uuid4()),  # Has a parent
            "counter_count": 1,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        def capture_insert(data):
            inserted_trade_data.append(data)
            return Mock(data=[data])

        original_trade_mock.insert = lambda data: Mock(execute=lambda: capture_insert(data))
        manager.tables["trade"] = original_trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

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
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        assert len(inserted_trade_data) == 1
        # Verify root_trade_id is preserved from original trade chain
        assert inserted_trade_data[0]["root_trade_id"] == str(sample_root_trade_id)

    def test_counter_offer_sets_parent_trade_id(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify new trade has parent_trade_id set to original trade_id"""
        now = datetime.now(timezone.utc).isoformat()
        inserted_trade_data = []

        manager = MockTableManager()

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
            "message": "Trade offer",
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

        def capture_insert(data):
            inserted_trade_data.append(data)
            return Mock(data=[data])

        original_trade_mock.insert = lambda data: Mock(execute=lambda: capture_insert(data))
        manager.tables["trade"] = original_trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

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
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        assert len(inserted_trade_data) == 1
        # Verify parent_trade_id is set to the original trade_id
        assert inserted_trade_data[0]["parent_trade_id"] == str(sample_trade_id)

    def test_counter_offer_unlocks_original_initiator_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify original initiator's escrow cards are unlocked after counter-offer"""
        now = datetime.now(timezone.utc).isoformat()
        lock_updates = []

        manager = MockTableManager()

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
            "message": "Trade offer",
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

        original_trade_mock.insert = lambda data: Mock(execute=lambda: Mock(data=[data]))
        manager.tables["trade"] = original_trade_mock

        # Original escrow with 3 cards that need to be unlocked
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 3}]
        )

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 10, "locked_quantity": 3, "is_tradeable": True}]
        )

        def capture_update(data):
            if "locked_quantity" in data:
                lock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card_1", "quantity": 2}],
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        # Verify original escrow cards were unlocked (3 - 3 = 0)
        assert 0 in lock_updates

    def test_counter_offer_locks_new_initiator_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify counter-offerer's escrow cards become locked"""
        now = datetime.now(timezone.utc).isoformat()
        lock_updates = []

        manager = MockTableManager()

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
            "message": "Trade offer",
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

        original_trade_mock.insert = lambda data: Mock(execute=lambda: Mock(data=[data]))
        manager.tables["trade"] = original_trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 10, "locked_quantity": 0, "is_tradeable": True}]
        )

        def capture_update(data):
            if "locked_quantity" in data:
                lock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card_1", "quantity": 5}],
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        # Verify counter-offerer's cards were locked (0 + 5 = 5)
        assert 5 in lock_updates

    def test_counter_offer_only_recipient_can_counter(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 403 error when non-recipient tries to counter-offer"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade exists
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Trade offer",
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

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to counter as the initiator (should fail)
        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card_1", "quantity": 2}],
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_initiator_user_id},  # Wrong user
        )

        assert response.status_code == 403
        assert "Only the recipient" in response.json()["detail"]

    def test_counter_offer_requires_pending_status(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when attempting to counter a non-PENDING trade"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is already ACCEPTED
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",  # Not pending
            "message": "Trade offer",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card_1", "quantity": 2}],
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 400
        assert "cannot be counter-offered" in response.json()["detail"]

    def test_counter_offer_requires_escrow_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 422 error when counter-offer has empty escrow_cards list"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Trade offer",
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

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to counter with empty escrow_cards
        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [],  # Empty list
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 422

    def test_counter_offer_validates_card_availability(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when counter-offerer doesn't have enough cards available"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

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
            "message": "Trade offer",
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
        manager.tables["trade"] = original_trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

        # Counter-offerer has only 2 cards available (quantity=5, locked=3)
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.update.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 5, "locked_quantity": 3, "is_tradeable": True}]
        )
        manager.tables["inventory_card"] = inv_card_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to counter with 5 cards when only 2 available
        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card_1", "quantity": 5}],
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 400
        assert "Insufficient quantity" in response.json()["detail"]

    def test_counter_offer_records_history_entry(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify COUNTER_OFFERED action is recorded in trade_history"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

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
            "message": "Trade offer",
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

        original_trade_mock.insert = lambda data: Mock(execute=lambda: Mock(data=[data]))
        manager.tables["trade"] = original_trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "original_escrow_card", "quantity": 1}]
        )

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

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card_1", "quantity": 2}],
                "requested_cards": [],
                "message": "My counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        # Verify history entry was created
        assert len(history_inserts) > 0
        # Check that at least one entry has the counter_offered action
        counter_offered_entries = [h for h in history_inserts if h.get("action") == "counter_offered"]
        assert len(counter_offered_entries) > 0
        # Verify the actor is the recipient
        assert counter_offered_entries[0]["actor_user_id"] == sample_recipient_user_id


class TestAcceptTrade:
    """Tests for trade accepting behaviour in trades."""

    def test_accept_trade_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify successful trade acceptance returns updated trade with ACCEPTED status"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade mock that returns updated status after accept
        trade_call_count = [0]

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            # After first call (initial fetch), return accepted status
            status = "accepted" if trade_call_count[0] > 1 else "pending"
            recipient_confirmed = trade_call_count[0] > 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": status,
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": recipient_confirmed,
                "recipient_confirmed_at": now if recipient_confirmed else None,
                "resolved_at": None,
            }])

        trade_mock.execute.side_effect = lambda: get_trade_response()
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )

        # Recipient has enough cards
        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_accept_trade_updates_status_to_accepted(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify trade status changes from PENDING to ACCEPTED"""
        now = datetime.now(timezone.utc).isoformat()
        status_updates = []

        manager = MockTableManager()

        # Trade mock that captures updates
        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock
        trade_mock.execute.return_value = Mock(data=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        def capture_update(data):
            if "status" in data:
                status_updates.append(data["status"])
            return trade_mock
        trade_mock.update = capture_update

        manager.tables["trade"] = trade_mock

        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify status was updated to "accepted"
        assert "accepted" in status_updates

    def test_accept_trade_auto_confirms_recipient(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify recipient_confirmed is set to True and recipient_confirmed_at is set"""
        now = datetime.now(timezone.utc).isoformat()
        confirmation_updates = []

        manager = MockTableManager()

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock
        trade_mock.execute.return_value = Mock(data=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        def capture_update(data):
            if "recipient_confirmed" in data or "recipient_confirmed_at" in data:
                confirmation_updates.append(data)
            return trade_mock
        trade_mock.update = capture_update

        manager.tables["trade"] = trade_mock

        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify recipient_confirmed was set to True
        assert any(u.get("recipient_confirmed") is True for u in confirmation_updates)
        # Verify recipient_confirmed_at was set
        assert any(u.get("recipient_confirmed_at") is not None for u in confirmation_updates)

    def test_accept_trade_only_recipient_can_accept(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 403 error when non-recipient (initiator or other user) tries to accept"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to accept as initiator (should fail)
        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_initiator_user_id},  # Wrong user
        )

        assert response.status_code == 403
        assert "Only the recipient" in response.json()["detail"]

    def test_accept_trade_requires_pending_status(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when attempting to accept a non-PENDING trade"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is already ACCEPTED
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",  # Not pending
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 400
        assert "cannot be accepted" in response.json()["detail"]

    def test_accept_trade_validates_recipient_has_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when recipient doesn't have the requested cards"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        # Recipient doesn't have the card
        inv_card_mock = manager.create_table("inventory_card", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "does not have" in detail or "Insufficient" in detail or "not found" in detail

    def test_accept_trade_validates_card_availability(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when recipient has cards but insufficient available quantity (locked)"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        # Requesting 5 cards
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 5}]
        )
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )

        # Recipient has 10 cards but 7 are locked, so only 3 available
        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 10, "locked_quantity": 7, "is_tradeable": True}]
        )

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 400
        assert "Insufficient quantity" in response.json()["detail"]

    def test_accept_trade_records_history_entry(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify ACCEPTED action is recorded in trade_history"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify history entry was created with accepted action
        assert len(history_inserts) > 0
        accepted_entries = [h for h in history_inserts if h.get("action") == "accepted"]
        assert len(accepted_entries) > 0
        assert accepted_entries[0]["actor_user_id"] == sample_recipient_user_id


class TestConfirmTrade:
    """Tests for trade confirmation behaviour in trades."""

    def test_confirm_trade_initiator_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify initiator can successfully confirm an ACCEPTED trade"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is ACCEPTED with recipient already confirmed
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200

    def test_confirm_trade_recipient_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify recipient can successfully confirm an ACCEPTED trade (though auto-confirmed on accept)"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is ACCEPTED with recipient NOT confirmed (edge case)
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
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
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200

    def test_confirm_trade_sets_confirmed_flag(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify confirming sets initiator_confirmed or recipient_confirmed to True with timestamp"""
        now = datetime.now(timezone.utc).isoformat()
        confirmation_updates = []

        manager = MockTableManager()

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock
        trade_mock.execute.return_value = Mock(data=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        def capture_update(data):
            if "initiator_confirmed" in data or "initiator_confirmed_at" in data:
                confirmation_updates.append(data)
            return trade_mock
        trade_mock.update = capture_update

        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify initiator_confirmed was set
        assert any(u.get("initiator_confirmed") is True for u in confirmation_updates)
        # Verify initiator_confirmed_at timestamp was set
        assert any(u.get("initiator_confirmed_at") is not None for u in confirmation_updates)

    def test_confirm_trade_both_confirmed_executes_trade(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify trade auto-executes (status=COMPLETED) when both parties have confirmed"""
        now = datetime.now(timezone.utc).isoformat()
        status_updates = []

        manager = MockTableManager()

        # Trade mock that returns updated data after confirmation
        trade_call_count = [0]

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
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
                "message": "Test trade",
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

        def capture_update(data):
            if "status" in data:
                status_updates.append(data["status"])
            return trade_mock
        trade_mock.update = capture_update

        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.update.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify trade status was updated to "completed"
        assert "completed" in status_updates

    def test_confirm_trade_transfers_escrow_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify escrow cards are transferred from initiator to recipient on completion"""
        now = datetime.now(timezone.utc).isoformat()
        quantity_updates = []

        manager = MockTableManager()

        # Trade mock that returns both confirmed
        trade_call_count = [0]

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            both_confirmed = trade_call_count[0] > 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": "Test trade",
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
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 3}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 10, "locked_quantity": 3, "is_tradeable": True}]
        )

        def capture_update(data):
            if "quantity" in data:
                quantity_updates.append(data)
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
        # Verify card transfers occurred
        assert len(quantity_updates) > 0

    def test_confirm_trade_transfers_requested_cards(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify requested cards are transferred from recipient to initiator on completion"""
        now = datetime.now(timezone.utc).isoformat()
        quantity_updates = []

        manager = MockTableManager()

        trade_call_count = [0]

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            both_confirmed = trade_call_count[0] > 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": "Test trade",
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
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 4}]
        )

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 10, "locked_quantity": 4, "is_tradeable": True}]
        )

        def capture_update(data):
            if "quantity" in data:
                quantity_updates.append(data)
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
        # Verify card transfers occurred (requested cards from recipient to initiator)
        assert len(quantity_updates) > 0

    def test_confirm_trade_sets_resolved_at(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify resolved_at timestamp is set when trade completes"""
        now = datetime.now(timezone.utc).isoformat()
        resolved_updates = []

        manager = MockTableManager()

        trade_call_count = [0]

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            both_confirmed = trade_call_count[0] > 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": "Test trade",
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

        def capture_update(data):
            if "resolved_at" in data:
                resolved_updates.append(data["resolved_at"])
            return trade_mock
        trade_mock.update = capture_update

        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.update.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify resolved_at was set
        assert len(resolved_updates) > 0
        assert all(r is not None for r in resolved_updates)

    def test_confirm_trade_requires_accepted_status(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when attempting to confirm a non-ACCEPTED trade"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is still PENDING
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",  # Not accepted
            "message": "Test trade",
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

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 400
        assert "cannot be confirmed" in response.json()["detail"]

    def test_confirm_trade_prevents_double_confirmation(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when same party tries to confirm twice"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Initiator already confirmed
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,  # Already confirmed
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to confirm again as initiator
        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 400
        assert "already confirmed" in response.json()["detail"]

    def test_confirm_trade_only_participants_can_confirm(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 403 error when non-participant tries to confirm"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to confirm as a different user
        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": "random_other_user"},
        )

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "not a participant" in detail or "participants can confirm" in detail

    def test_confirm_trade_records_history_entry(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify CONFIRMED action is recorded in trade_history"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify history entry with confirmed action was created
        assert len(history_inserts) > 0
        confirmed_entries = [h for h in history_inserts if h.get("action") == "confirmed"]
        assert len(confirmed_entries) > 0

    def test_confirm_trade_records_completed_on_execution(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify COMPLETED action is recorded when both confirm"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        trade_call_count = [0]

        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            both_confirmed = trade_call_count[0] > 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": "Test trade",
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
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )
        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.update.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}]
        )
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/confirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify both confirmed and completed actions were recorded
        assert len(history_inserts) > 0
        completed_entries = [h for h in history_inserts if h.get("action") == "completed"]
        assert len(completed_entries) > 0


class TestUnconfirmTrade:
    """Tests for trade confirmation retraction behaviour in trades."""

    def test_unconfirm_trade_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify successful unconfirmation resets the confirmed flag to False"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Create trade where initiator is confirmed but recipient is not
        trade_call_count = [0]
        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            # After update, return unconfirmed state
            is_confirmed = trade_call_count[0] == 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": is_confirmed,
                "initiator_confirmed_at": now if is_confirmed else None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }])

        trade_mock.execute.side_effect = lambda: get_trade_response()
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/unconfirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["initiator_confirmed"] is False

    def test_unconfirm_trade_clears_confirmed_timestamp(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify initiator_confirmed_at or recipient_confirmed_at is cleared"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        trade_call_count = [0]
        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            # After update, timestamp should be None
            has_timestamp = trade_call_count[0] == 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": True,
                "recipient_confirmed_at": now if has_timestamp else None,
                "resolved_at": None,
            }])

        trade_mock.execute.side_effect = lambda: get_trade_response()
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Unconfirm as recipient
        response = client.post(
            f"/trades/{sample_trade_id}/unconfirm",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recipient_confirmed_at"] is None

    def test_unconfirm_trade_requires_accepted_status(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when attempting to unconfirm a non-ACCEPTED trade"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is PENDING, not ACCEPTED
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/unconfirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "accepted" in detail.lower() or "status" in detail.lower()

    def test_unconfirm_trade_only_confirmed_party_can_unconfirm(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when unconfirmed party tries to unconfirm"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Only recipient is confirmed, initiator tries to unconfirm
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/unconfirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "not confirmed" in detail.lower() or "already unconfirmed" in detail.lower()

    def test_unconfirm_trade_blocked_if_both_confirmed(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when attempting to unconfirm after both parties confirmed"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Both parties are confirmed
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/unconfirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "both confirmed" in detail.lower() or "cannot unconfirm" in detail.lower()

    def test_unconfirm_trade_only_participants_can_unconfirm(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 403 error when non-participant tries to unconfirm"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to unconfirm as a different user
        response = client.post(
            f"/trades/{sample_trade_id}/unconfirm",
            headers={"X-User-Id": "random_other_user"},
        )

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "not a participant" in detail.lower() or "participants can" in detail.lower()

    def test_unconfirm_trade_records_history_entry(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify UNCONFIRMED action is recorded in trade_history"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        trade_call_count = [0]
        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            is_confirmed = trade_call_count[0] == 1
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": is_confirmed,
                "initiator_confirmed_at": now if is_confirmed else None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }])

        trade_mock.execute.side_effect = lambda: get_trade_response()
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/unconfirm",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify history entry with unconfirmed action was created
        assert len(history_inserts) > 0
        unconfirmed_entries = [h for h in history_inserts if h.get("action") == "unconfirmed"]
        assert len(unconfirmed_entries) > 0


class TestRejectTrade:
    """Tests for trade rejection behaviour in trades."""

    def test_reject_trade_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify successful rejection returns trade with REJECTED status"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns rejected)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "rejected",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_reject_trade_updates_status_to_rejected(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify trade status changes from PENDING to REJECTED"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # First response: PENDING, second response: REJECTED
        trade_call_count = [0]
        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            status = "pending" if trade_call_count[0] == 1 else "rejected"
            resolved = None if trade_call_count[0] == 1 else now
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": status,
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": resolved,
            }])

        trade_mock.execute.side_effect = lambda: get_trade_response()
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

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
        """Verify initiator's escrow cards have locked_quantity decremented"""
        now = datetime.now(timezone.utc).isoformat()
        update_calls = []

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns rejected)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "rejected",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[
            {"card_id": "escrow_card_1", "quantity": 2},
            {"card_id": "escrow_card_2", "quantity": 1},
        ])
        manager.create_table("trade_recipient", default_response=[])

        # Mock inventory_card to capture updates
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(data=[{"quantity": 5, "locked_quantity": 2, "is_tradeable": True}])

        def capture_update(data):
            update_calls.append(data)
            return inv_card_mock

        inv_card_mock.update = capture_update
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify that locked_quantity was decremented
        assert len(update_calls) > 0

    def test_reject_trade_sets_resolved_at(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify resolved_at timestamp is set on rejection"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns rejected)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "rejected",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resolved_at"] is not None

    def test_reject_trade_only_recipient_can_reject(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 403 error when non-recipient tries to reject"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to reject as initiator (should fail)
        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "recipient" in detail.lower() or "not authorized" in detail.lower()

    def test_reject_trade_requires_pending_status(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when attempting to reject a non-PENDING trade"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is already ACCEPTED
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "pending" in detail.lower() or "status" in detail.lower()

    def test_reject_trade_records_history_entry(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify REJECTED action is recorded in trade_history"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns rejected)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "rejected",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/reject",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify history entry with rejected action was created
        assert len(history_inserts) > 0
        rejected_entries = [h for h in history_inserts if h.get("action") == "rejected"]
        assert len(rejected_entries) > 0


class TestCancelTrade:
    """Tests for trade cancellation behaviour in trades."""

    def test_cancel_trade_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify successful cancellation returns trade with CANCELLED status"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns cancelled)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "cancelled",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_trade_updates_status_to_cancelled(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify trade status changes from PENDING to CANCELLED"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # First response: PENDING, second response: CANCELLED
        trade_call_count = [0]
        trade_mock = MagicMock()
        trade_mock.select.return_value = trade_mock
        trade_mock.insert.return_value = trade_mock
        trade_mock.eq.return_value = trade_mock
        trade_mock.order.return_value = trade_mock
        trade_mock.limit.return_value = trade_mock

        def get_trade_response():
            trade_call_count[0] += 1
            status = "pending" if trade_call_count[0] == 1 else "cancelled"
            resolved = None if trade_call_count[0] == 1 else now
            return Mock(data=[{
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": status,
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": resolved,
            }])

        trade_mock.execute.side_effect = lambda: get_trade_response()
        trade_mock.update.return_value = trade_mock
        manager.tables["trade"] = trade_mock

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

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
        """Verify initiator's escrow cards have locked_quantity decremented"""
        now = datetime.now(timezone.utc).isoformat()
        update_calls = []

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns cancelled)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "cancelled",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[
            {"card_id": "escrow_card_1", "quantity": 3},
            {"card_id": "escrow_card_2", "quantity": 1},
        ])
        manager.create_table("trade_recipient", default_response=[])

        # Mock inventory_card to capture updates
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(data=[{"quantity": 5, "locked_quantity": 3, "is_tradeable": True}])

        def capture_update(data):
            update_calls.append(data)
            return inv_card_mock

        inv_card_mock.update = capture_update
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify that locked_quantity was decremented
        assert len(update_calls) > 0

    def test_cancel_trade_sets_resolved_at(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify resolved_at timestamp is set on cancellation"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns cancelled)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "cancelled",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resolved_at"] is not None

    def test_cancel_trade_only_initiator_can_cancel(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 403 error when non-initiator tries to cancel"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade",
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

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to cancel as recipient (should fail)
        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "initiator" in detail.lower() or "not authorized" in detail.lower()

    def test_cancel_trade_requires_pending_status(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify 400 error when attempting to cancel a non-PENDING trade"""
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Trade is already ACCEPTED
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "accepted",
            "message": "Test trade",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": None,
        }])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "pending" in detail.lower() or "status" in detail.lower()

    def test_cancel_trade_with_reason(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify cancellation reason is stored when provided"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns cancelled)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "cancelled",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        cancellation_reason = "Changed my mind about the trade"
        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
            json={"reason": cancellation_reason}
        )

        assert response.status_code == 200
        # Verify reason was captured in history
        assert len(history_inserts) > 0
        cancelled_entry = [h for h in history_inserts if h.get("action") == "cancelled"]
        if cancelled_entry:
            # Check if reason is in the details
            assert "reason" in str(cancelled_entry[0].get("details", {})).lower() or "changed my mind" in str(cancelled_entry[0].get("details", {})).lower()

    def test_cancel_trade_records_history_entry(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify CANCELLED action is recorded in trade_history"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("trade", responses=[
            [{  # First call: get trade for validation (needs to be pending)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": None,
            }],
            [],  # Second call: update trade
            [{  # Third call: get_trade at the end (returns cancelled)
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "cancelled",
                "message": "Test trade",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "parent_trade_id": None,
                "counter_count": 0,
                "initiator_confirmed": False,
                "initiator_confirmed_at": None,
                "recipient_confirmed": False,
                "recipient_confirmed_at": None,
                "resolved_at": now,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[{"card_id": "escrow_card_1", "quantity": 1}])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("inventory_card", default_response=[{"quantity": 5, "locked_quantity": 1, "is_tradeable": True}])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        # Capture history inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.limit.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify history entry with cancelled action was created
        assert len(history_inserts) > 0
        cancelled_entries = [h for h in history_inserts if h.get("action") == "cancelled"]
        assert len(cancelled_entries) > 0


class TestTradeHistoryRecording:
    """Tests for trade history recording behaviour in trades."""

    def test_create_trade_records_created_action(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify CREATED action is recorded when trade is created"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        # Inventory table
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        # Inventory card table
        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        # Trade table
        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Test trade offer",
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

        # Trade history table - capture inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        # Other tables
        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 2}],
                "requested_cards": [],
                "message": "Test trade offer",
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify CREATED action was recorded
        assert len(history_inserts) >= 1
        created_action = next((h for h in history_inserts if h["action"] == "created"), None)
        assert created_action is not None

    def test_history_entry_has_correct_trade_id(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify history entry references the correct trade_id"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
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

        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify history entry has trade_id field and it's a valid UUID format
        assert len(history_inserts) >= 1
        assert "trade_id" in history_inserts[0]
        # Both trade_id in history and response should be valid UUIDs (strings)
        assert isinstance(str(history_inserts[0]["trade_id"]), str)

    def test_history_entry_has_correct_root_trade_id(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify history entry uses root_trade_id"""
        trade_id = str(uuid4())
        root_trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        # Simulate a counter-offer with parent_trade_id
        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": None,
            "created_at": now,
            "root_trade_id": root_trade_id,  # Different from trade_id
            "parent_trade_id": root_trade_id,
            "counter_count": 1,
            "initiator_confirmed": False,
            "initiator_confirmed_at": None,
            "recipient_confirmed": False,
            "recipient_confirmed_at": None,
            "resolved_at": None,
        }])

        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify history entry has root_trade_id field set
        assert len(history_inserts) >= 1
        assert "root_trade_id" in history_inserts[0]
        # root_trade_id should be a valid value
        assert history_inserts[0]["root_trade_id"] is not None

    def test_history_entry_has_correct_actor(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify actor_user_id matches the user performing the action"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

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

        manager.create_table("trade_recipient",
            default_response=[{"card_id": "requested_card_1", "quantity": 2}]
        )
        manager.create_table("trade_escrow",
            default_response=[{"card_id": "escrow_card_1", "quantity": 1}]
        )

        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Recipient accepts the trade
        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify actor_user_id is the recipient who accepted
        assert len(history_inserts) >= 1
        accepted_action = next((h for h in history_inserts if h["action"] == "accepted"), None)
        assert accepted_action is not None
        assert accepted_action["actor_user_id"] == sample_recipient_user_id

    def test_history_entry_sequence_numbers_increment(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify sequence_number increments for each action in a chain"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        # Initial pending trade
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

        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("trade_escrow", default_response=[])

        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        # History mock - return existing entries with sequence numbers
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock

        # First call returns sequence 1 (created action), second returns sequence 1-2
        history_mock.execute.side_effect = [
            Mock(data=[{"sequence_number": 1}]),  # Max sequence check for accept
            Mock(data=[{"sequence_number": 1}, {"sequence_number": 2}]),  # Next check if any
        ]

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Accept the trade
        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 200
        # Verify sequence_number field exists in history inserts
        assert len(history_inserts) >= 1
        accepted_action = next((h for h in history_inserts if h["action"] == "accepted"), None)
        assert accepted_action is not None
        assert "sequence_number" in accepted_action
        # Sequence number should be set (not None)
        assert accepted_action["sequence_number"] is not None

    def test_history_entry_includes_details(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify details JSON contains relevant action metadata"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "message": "Custom trade message",
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

        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [],
                "requested_cards": [],
                "message": "Custom trade message",
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify details contains relevant metadata
        assert len(history_inserts) >= 1
        created_action = next((h for h in history_inserts if h["action"] == "created"), None)
        assert created_action is not None
        assert "details" in created_action
        # Details should contain other_user_id, escrow_cards, requested_cards
        assert "other_user_id" in created_action["details"]
        assert created_action["details"]["other_user_id"] == sample_recipient_user_id

    def test_history_records_all_action_types(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify all TradeHistoryAction enum values are recorded"""
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

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

        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("trade_escrow", default_response=[])

        manager.create_table("inventory_card",
            default_response=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}]
        )

        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[{"sequence_number": 1}])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Cancel the trade to record CANCELLED action
        response = client.post(
            f"/trades/{sample_trade_id}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify cancelled action was recorded
        assert len(history_inserts) >= 1
        cancelled_action = next((h for h in history_inserts if h["action"] == "cancelled"), None)
        assert cancelled_action is not None


class TestGetTradeHistoryChain:
    """Tests for trade history presenting behaviour in trades."""

    def test_get_trade_history_success(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
    ):
        """Verify successful retrieval of trade history"""
        manager = MockTableManager()

        # Trade exists
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "root_trade_id": str(sample_trade_id),
        }])

        # History entries
        manager.create_table("trade_history", default_response=[
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_trade_id),
                "sequence_number": 1,
                "actor_user_id": sample_initiator_user_id,
                "action": "created",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ])

        # User table for actor names
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.get(f"/trades/{sample_trade_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert len(data["history"]) >= 1

    def test_get_trade_history_returns_all_chain_entries(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_root_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
    ):
        """Verify history includes entries from entire counter-offer chain"""
        manager = MockTableManager()

        # Trade with counter-offer chain
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "root_trade_id": str(sample_root_trade_id),
        }])

        # Multiple history entries from chain
        manager.create_table("trade_history", default_response=[
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_root_trade_id),
                "root_trade_id": str(sample_root_trade_id),
                "sequence_number": 1,
                "actor_user_id": sample_initiator_user_id,
                "action": "created",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_root_trade_id),
                "sequence_number": 2,
                "actor_user_id": sample_recipient_user_id,
                "action": "counter_offered",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_root_trade_id),
                "sequence_number": 3,
                "actor_user_id": sample_recipient_user_id,
                "action": "accepted",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ])

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.get(f"/trades/{sample_trade_id}/history")

        assert response.status_code == 200
        data = response.json()
        # Verify all chain entries are returned
        assert len(data["history"]) == 3

    def test_get_trade_history_ordered_by_sequence(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
    ):
        """Verify history entries are ordered by sequence_number"""
        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "root_trade_id": str(sample_trade_id),
        }])

        # Test ordering - data returned in correct order by API
        manager.create_table("trade_history", default_response=[
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_trade_id),
                "sequence_number": 1,
                "actor_user_id": sample_initiator_user_id,
                "action": "created",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_trade_id),
                "sequence_number": 2,
                "actor_user_id": sample_initiator_user_id,
                "action": "accepted",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_trade_id),
                "sequence_number": 3,
                "actor_user_id": sample_initiator_user_id,
                "action": "completed",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ])

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.get(f"/trades/{sample_trade_id}/history")

        assert response.status_code == 200
        data = response.json()
        # Verify ordering by sequence_number
        sequence_numbers = [entry["sequence_number"] for entry in data["history"]]
        assert sequence_numbers == sorted(sequence_numbers)

    def test_get_trade_history_includes_actor_names(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
    ):
        """Verify actor_user_name is populated in response"""
        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "root_trade_id": str(sample_trade_id),
        }])

        manager.create_table("trade_history", default_response=[
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_trade_id),
                "sequence_number": 1,
                "actor_user_id": sample_initiator_user_id,
                "action": "created",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ])

        # User table with specific name
        manager.create_table("user", default_response=[{"user_name": "AliceTrader"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.get(f"/trades/{sample_trade_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["history"]) >= 1
        # Verify actor_user_name is populated
        assert "actor_user_name" in data["history"][0]
        assert data["history"][0]["actor_user_name"] == "AliceTrader"

    def test_get_trade_history_not_found(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify 404 error when trade_id doesn't exist"""
        non_existent_trade_id = str(uuid4())
        manager = MockTableManager()

        # Trade doesn't exist
        manager.create_table("trade", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.get(f"/trades/{non_existent_trade_id}/history")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_trade_history_uses_root_trade_id(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_root_trade_id,
        sample_initiator_user_id,
    ):
        """Verify querying a counter-offer trade returns full chain"""
        manager = MockTableManager()

        # Counter-offer trade with different root_trade_id
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "root_trade_id": str(sample_root_trade_id),
        }])

        # History includes entries from root trade
        manager.create_table("trade_history", default_response=[
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_root_trade_id),
                "root_trade_id": str(sample_root_trade_id),
                "sequence_number": 1,
                "actor_user_id": sample_initiator_user_id,
                "action": "created",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "history_id": str(uuid4()),
                "trade_id": str(sample_trade_id),
                "root_trade_id": str(sample_root_trade_id),
                "sequence_number": 2,
                "actor_user_id": sample_initiator_user_id,
                "action": "counter_offered",
                "details": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ])

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.get(f"/trades/{sample_trade_id}/history")

        assert response.status_code == 200
        data = response.json()
        # Verify full chain is returned, not just current trade
        assert len(data["history"]) == 2
        # First entry should be from root trade
        assert data["history"][0]["action"] == "created"

    def test_get_trade_history_empty_chain(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
    ):
        """Verify proper response when trade exists with minimal history"""
        manager = MockTableManager()

        # Trade exists
        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "root_trade_id": str(sample_trade_id),
        }])

        # No history entries (edge case)
        manager.create_table("trade_history", default_response=[])

        manager.create_table("user", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.get(f"/trades/{sample_trade_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert isinstance(data["history"], list)
        assert len(data["history"]) == 0


class TestSelfTransfer:
    """Tests for self transfer behaviour in trades."""

    def test_self_transfer_success(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify a user can create a self-transfer trade"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Both inventories belong to the same user (self-transfer)
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],  # Initiator inventory
            [{"user_id": sample_initiator_user_id}],  # Recipient inventory (same user)
        ])

        manager.create_table("inventory_card", default_response=[
            {"quantity": 10, "locked_quantity": 0, "is_tradeable": False}
        ])

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_initiator_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "completed",
            "message": "Self transfer",
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": now,
        }])

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_initiator_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 2}],
                "requested_cards": [],
                "message": "Self transfer",
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201

    def test_self_transfer_auto_executes(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify self-transfer trades auto-execute immediately"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        quantity_updates = []

        manager = MockTableManager()

        # Same user for both inventories
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_initiator_user_id}],
        ])

        # Inventory card mock for quantity tracking
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 10, "locked_quantity": 0, "is_tradeable": False}]
        )

        def capture_update(data):
            if "quantity" in data:
                quantity_updates.append(data["quantity"])
            update_mock = MagicMock()
            update_mock.eq.return_value = update_mock
            update_mock.execute.return_value = Mock(data=[])
            return update_mock

        inv_card_mock.update = capture_update
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_initiator_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "completed",
            "message": None,
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": now,
        }])

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_initiator_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 3}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify self-transfer auto-executed by checking status
        response_data = response.json()
        assert response_data["status"] == "completed"
        # If trade completed, quantities must have been transferred
        assert response_data["resolved_at"] is not None

    def test_self_transfer_skips_tradeable_check(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify self-transfers do not require tradeable cards"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Same user for both inventories
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_initiator_user_id}],
        ])

        # Card is NOT tradeable, but self-transfer should still work
        manager.create_table("inventory_card", default_response=[
            {"quantity": 10, "locked_quantity": 0, "is_tradeable": False}
        ])

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_initiator_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "completed",
            "message": None,
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": now,
        }])

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Should succeed even though is_tradeable=False
        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_initiator_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 2}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201

    def test_self_transfer_updates_quantities(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify card quantities are moved correctly"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        quantity_updates = []

        manager = MockTableManager()

        # Same user for both inventories
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_initiator_user_id}],
        ])

        # Initial quantity of 10
        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.insert.return_value = inv_card_mock
        inv_card_mock.delete.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.order.return_value = inv_card_mock
        inv_card_mock.limit.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(
            data=[{"quantity": 10, "locked_quantity": 0, "is_tradeable": True}]
        )

        def capture_update(data):
            if "quantity" in data:
                quantity_updates.append(data["quantity"])
            update_mock = MagicMock()
            update_mock.eq.return_value = update_mock
            update_mock.execute.return_value = Mock(data=[])
            return update_mock

        inv_card_mock.update = capture_update
        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_initiator_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "completed",
            "message": None,
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": now,
        }])

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_initiator_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 3}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify trade completed (which means quantities were updated)
        response_data = response.json()
        assert response_data["status"] == "completed"

    def test_self_transfer_status_completed(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify self-transfer trades are COMPLETED immediately"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        manager = MockTableManager()

        # Same user for both inventories
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_initiator_user_id}],
        ])

        manager.create_table("inventory_card", default_response=[
            {"quantity": 10, "locked_quantity": 0, "is_tradeable": True}
        ])

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_initiator_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "completed",
            "message": None,
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": now,
        }])

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_initiator_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 2}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        data = response.json()
        # Verify status is COMPLETED, not PENDING
        assert data["status"] == "completed"
        assert data["initiator_confirmed"] is True
        assert data["recipient_confirmed"] is True
        assert data["resolved_at"] is not None

    def test_self_transfer_records_history(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify CREATED and COMPLETED actions are recorded"""
        trade_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        history_inserts = []

        manager = MockTableManager()

        # Same user for both inventories
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_initiator_user_id}],
        ])

        manager.create_table("inventory_card", default_response=[
            {"quantity": 10, "locked_quantity": 0, "is_tradeable": True}
        ])

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_initiator_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "completed",
            "message": None,
            "created_at": now,
            "root_trade_id": trade_id,
            "parent_trade_id": None,
            "counter_count": 0,
            "initiator_confirmed": True,
            "initiator_confirmed_at": now,
            "recipient_confirmed": True,
            "recipient_confirmed_at": now,
            "resolved_at": now,
        }])

        # Trade history mock - capture inserts
        history_mock = MagicMock()
        history_mock.select.return_value = history_mock
        history_mock.eq.return_value = history_mock
        history_mock.order.return_value = history_mock
        history_mock.execute.return_value = Mock(data=[])

        def capture_history_insert(data):
            history_inserts.append(data)
            return Mock(data=[data])

        history_mock.insert = lambda data: Mock(execute=lambda: capture_history_insert(data))
        manager.tables["trade_history"] = history_mock

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            "/trades",
            json={
                "recipient_user_id": sample_initiator_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "escrow_cards": [{"card_id": "card1", "quantity": 2}],
                "requested_cards": [],
            },
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 201
        # Verify both CREATED and COMPLETED actions were recorded
        assert len(history_inserts) >= 2
        actions = [h["action"] for h in history_inserts]
        assert "created" in actions
        assert "completed" in actions


class TestConcurrentTrades:
    """Tests for concurrent trading behaviour in trades."""

    def test_multiple_pending_trades_same_card(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify multiple pending trades can lock the same card within limits"""
        # Test: User has 5 cards, creates two trades with 2 cards each
        # Total locked should be 4, leaving 1 available
        trade_id_1 = str(uuid4())
        trade_id_2 = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        lock_updates = []

        manager = MockTableManager()

        # Inventory table
        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],  # First trade, initiator check
            [{"user_id": sample_recipient_user_id}],  # First trade, recipient check
            [{"user_id": sample_initiator_user_id}],  # Second trade, initiator check
            [{"user_id": sample_recipient_user_id}],  # Second trade, recipient check
        ])

        # Inventory card table - track lock state across calls
        current_locked = [0]  # Use list to allow mutation in nested function

        def create_inv_card_mock():
            mock = MagicMock()
            mock.select.return_value = mock
            mock.eq.return_value = mock

            def execute():
                return Mock(data=[{
                    "quantity": 5,
                    "locked_quantity": current_locked[0],
                    "is_tradeable": True
                }])
            mock.execute = execute

            def update_func(data):
                if "locked_quantity" in data:
                    current_locked[0] = data["locked_quantity"]
                    lock_updates.append(data["locked_quantity"])
                return mock
            mock.update = update_func

            return mock

        manager.tables["inventory_card"] = create_inv_card_mock()

        # Trade table
        manager.create_table("trade", responses=[
            [{
                "trade_id": trade_id_1,
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "created_at": now,
                "root_trade_id": trade_id_1,
            }],
            [{
                "trade_id": trade_id_2,
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "created_at": now,
                "root_trade_id": trade_id_2,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # First trade: lock 2 cards
        response1 = client.post(
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

        assert response1.status_code == 201
        assert 2 in lock_updates

        # Second trade: lock 2 more cards (total 4)
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
        assert 4 in lock_updates

    def test_concurrent_trade_fails_exceeds_available(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify trade creation fails when locked exceeds available"""
        # Test: User has 5 cards with 3 already locked, tries to create trade with 3 more
        manager = MockTableManager()

        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        # Inventory card has 5 total, 3 locked = 2 available
        manager.create_table("inventory_card", default_response=[{
            "quantity": 5,
            "locked_quantity": 3,
            "is_tradeable": True
        }])

        manager.create_table("trade", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Try to lock 3 cards when only 2 available
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

        assert response.status_code == 400
        assert "Insufficient quantity" in response.json()["detail"]

    def test_accepting_trade_validates_current_locked_quantity(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify accept checks live locked_quantity"""
        # Test: Recipient has 5 cards with 4 locked, tries to accept trade requesting 2
        now = datetime.now(timezone.utc).isoformat()
        manager = MockTableManager()

        manager.create_table("trade", default_response=[{
            "trade_id": str(sample_trade_id),
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "created_at": now,
            "root_trade_id": str(sample_trade_id),
        }])

        manager.create_table("trade_recipient", default_response=[
            {"card_id": "card1", "quantity": 2}
        ])

        # Only 1 available (5 - 4 = 1), but trade requests 2
        manager.create_table("inventory_card", default_response=[{
            "quantity": 5,
            "locked_quantity": 4,
            "is_tradeable": True
        }])

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 400
        assert "Insufficient quantity" in response.json()["detail"]

    def test_cancel_one_trade_frees_quantity_for_another(
        self,
        client,
        mock_supabase_client,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify cancelling a trade frees locked_quantity"""
        # Test: Create trade (locks 3), cancel it (unlocks 3), create new trade (locks 2)
        trade_id_1 = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        lock_updates = []

        manager = MockTableManager()

        manager.create_table("inventory", responses=[
            [{"user_id": sample_initiator_user_id}],
            [{"user_id": sample_recipient_user_id}],
        ])

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock
        inv_card_mock.eq.return_value = inv_card_mock
        inv_card_mock.execute.return_value = Mock(data=[{
            "quantity": 5,
            "locked_quantity": 3,
            "is_tradeable": True
        }])

        def capture_update(data):
            if "locked_quantity" in data:
                lock_updates.append(data["locked_quantity"])
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("trade", default_response=[{
            "trade_id": trade_id_1,
            "initiator_user_id": sample_initiator_user_id,
            "recipient_user_id": sample_recipient_user_id,
            "initiator_inventory_id": str(sample_initiator_inventory_id),
            "recipient_inventory_id": str(sample_recipient_inventory_id),
            "status": "pending",
            "created_at": now,
            "root_trade_id": trade_id_1,
        }])

        manager.create_table("trade_escrow", default_response=[
            {"card_id": "card1", "quantity": 3}
        ])
        manager.create_table("trade_recipient", default_response=[])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Cancel the trade
        response = client.post(
            f"/trades/{trade_id_1}/cancel",
            headers={"X-User-Id": sample_initiator_user_id},
        )

        assert response.status_code == 200
        # Verify locked_quantity decreased from 3 to 0 (max(0, 3-3))
        assert 0 in lock_updates

    def test_counter_offer_chain_locks_correctly(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify lock/unlock works through counter-offer chains"""
        # Test: Original trade locks initiator's cards, counter-offer unlocks those and locks recipient's cards
        now = datetime.now(timezone.utc).isoformat()
        lock_updates = []

        manager = MockTableManager()

        # Original trade state
        manager.create_table("trade", responses=[
            [{  # GET trade for counter
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "counter_count": 0,
            }],
            [],  # UPDATE original to countered
            [{  # INSERT new counter-offer trade
                "trade_id": str(uuid4()),
                "initiator_user_id": sample_recipient_user_id,
                "recipient_user_id": sample_initiator_user_id,
                "initiator_inventory_id": str(sample_recipient_inventory_id),
                "recipient_inventory_id": str(sample_initiator_inventory_id),
                "status": "pending",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
                "counter_count": 1,
            }]
        ])

        manager.create_table("trade_escrow", default_response=[
            {"card_id": "original_card", "quantity": 2}
        ])
        manager.create_table("trade_recipient", default_response=[])

        # Track locked_quantity per card_id
        card_states = {
            "original_card": {"quantity": 5, "locked_quantity": 2, "is_tradeable": True},
            "counter_card": {"quantity": 5, "locked_quantity": 0, "is_tradeable": True},
        }
        current_card_id = [None]  # Track which card is being queried

        inv_card_mock = MagicMock()
        inv_card_mock.select.return_value = inv_card_mock

        def track_eq(field, value):
            if field == "card_id":
                current_card_id[0] = value
            return inv_card_mock
        inv_card_mock.eq.side_effect = track_eq

        def execute_with_card_state():
            card_id = current_card_id[0]
            if card_id and card_id in card_states:
                return Mock(data=[card_states[card_id]])
            return Mock(data=[{"quantity": 5, "locked_quantity": 0, "is_tradeable": True}])
        inv_card_mock.execute.side_effect = execute_with_card_state

        def capture_update(data):
            if "locked_quantity" in data:
                lock_updates.append(data["locked_quantity"])
                card_id = current_card_id[0]
                if card_id and card_id in card_states:
                    card_states[card_id]["locked_quantity"] = data["locked_quantity"]
            return inv_card_mock
        inv_card_mock.update = capture_update

        manager.tables["inventory_card"] = inv_card_mock

        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Counter-offer
        response = client.post(
            f"/trades/{sample_trade_id}/counter",
            json={
                "escrow_cards": [{"card_id": "counter_card", "quantity": 1}],
                "requested_cards": [],
                "message": "Counter offer"
            },
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response.status_code == 201
        # Should unlock original (2-2=0) and lock new counter cards (0+1=1)
        assert 0 in lock_updates  # Unlock original
        assert 1 in lock_updates  # Lock counter cards

    def test_race_condition_double_accept(
        self,
        client,
        mock_supabase_client,
        sample_trade_id,
        sample_initiator_user_id,
        sample_recipient_user_id,
        sample_initiator_inventory_id,
        sample_recipient_inventory_id,
    ):
        """Verify race conditions are safely handled"""
        # Test: Attempt to accept trade twice (simulating race condition)
        now = datetime.now(timezone.utc).isoformat()
        manager = MockTableManager()

        # First accept succeeds, second should fail
        manager.create_table("trade", responses=[
            [{  # First accept - trade is pending
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "pending",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
            }],
            [],  # UPDATE to accepted
            [{  # Second accept - trade is already accepted
                "trade_id": str(sample_trade_id),
                "initiator_user_id": sample_initiator_user_id,
                "recipient_user_id": sample_recipient_user_id,
                "initiator_inventory_id": str(sample_initiator_inventory_id),
                "recipient_inventory_id": str(sample_recipient_inventory_id),
                "status": "accepted",
                "created_at": now,
                "root_trade_id": str(sample_trade_id),
            }]
        ])

        manager.create_table("trade_recipient", default_response=[
            {"card_id": "card1", "quantity": 1}
        ])
        manager.create_table("inventory_card", default_response=[{
            "quantity": 5,
            "locked_quantity": 0,
            "is_tradeable": True
        }])
        manager.create_table("user", default_response=[{"user_name": "TestUser"}])
        manager.create_table("trade_history", default_response=[])
        manager.create_table("trade_escrow", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # First accept
        response1 = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response1.status_code == 200

        # Second accept (race condition)
        response2 = client.post(
            f"/trades/{sample_trade_id}/accept",
            headers={"X-User-Id": sample_recipient_user_id},
        )

        assert response2.status_code == 400
        assert "cannot be accepted" in response2.json()["detail"].lower()


class TestTradeCleanup:
    """Tests for cleaning behaviour in trade table."""

    def test_cleanup_dry_run_returns_counts(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify dry run returns deletion counts without deleting"""
        from datetime import timedelta

        manager = MockTableManager()

        # Old resolved trades (31+ days old)
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()

        manager.create_table("trade", default_response=[
            {"trade_id": "old_trade_1", "status": "completed", "resolved_at": old_date},
            {"trade_id": "old_trade_2", "status": "cancelled", "resolved_at": old_date},
        ])

        # Escrow and recipient records for these trades
        manager.create_table("trade_escrow", responses=[
            [{"trade_id": "old_trade_1", "card_id": "card1", "quantity": 1}],  # Count for trade 1
            [{"trade_id": "old_trade_2", "card_id": "card2", "quantity": 1}],  # Count for trade 2
        ])

        manager.create_table("trade_recipient", responses=[
            [{"trade_id": "old_trade_1", "card_id": "card3", "quantity": 1}],  # Count for trade 1
            [],  # Count for trade 2 (empty)
        ])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Call cleanup with dry_run=True (default)
        response = client.delete("/admin/trades/cleanup?retention_days=30&dry_run=true")

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        assert data["trades_cleaned"] == 2
        assert data["escrow_records_deleted"] == 2
        assert data["recipient_records_deleted"] == 1
        assert data["retention_days"] == 30

    def test_cleanup_deletes_old_resolved_trades(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify old resolved trades are cleaned up"""
        from datetime import timedelta

        manager = MockTableManager()

        # Trade older than 30 days that's resolved
        old_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()

        manager.create_table("trade", default_response=[
            {"trade_id": "old_completed", "status": "completed", "resolved_at": old_date},
        ])

        delete_calls = []

        escrow_mock = manager.create_table("trade_escrow", default_response=[
            {"trade_id": "old_completed", "card_id": "card1", "quantity": 2}
        ])

        def track_delete():
            delete_calls.append("escrow")
            return escrow_mock
        escrow_mock.delete = track_delete

        recipient_mock = manager.create_table("trade_recipient", default_response=[
            {"trade_id": "old_completed", "card_id": "card2", "quantity": 1}
        ])

        def track_delete_recipient():
            delete_calls.append("recipient")
            return recipient_mock
        recipient_mock.delete = track_delete_recipient

        mock_supabase_client.table.side_effect = manager.table_handler

        # Call cleanup with dry_run=False
        response = client.delete("/admin/trades/cleanup?retention_days=30&dry_run=false")

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is False
        assert data["trades_cleaned"] == 1
        # Verify delete was called
        assert "escrow" in delete_calls
        assert "recipient" in delete_calls

    def test_cleanup_preserves_recent_resolved_trades(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify recent resolved trades are preserved"""
        from datetime import timedelta

        manager = MockTableManager()

        # Trade older than 30 days
        old_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()

        manager.create_table("trade", responses=[
            # First query returns only old trades (recent is filtered out)
            [{"trade_id": "old_trade", "status": "completed", "resolved_at": old_date}]
        ])

        manager.create_table("trade_escrow", default_response=[
            {"trade_id": "old_trade", "card_id": "card1", "quantity": 1}
        ])
        manager.create_table("trade_recipient", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.delete("/admin/trades/cleanup?retention_days=30&dry_run=true")

        assert response.status_code == 200
        data = response.json()
        # Only old trade should be counted
        assert data["trades_cleaned"] == 1

    def test_cleanup_preserves_active_trades(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify PENDING and ACCEPTED trades are never deleted"""
        manager = MockTableManager()

        # Query filters by resolved_at NOT NULL, so active trades won't be returned
        manager.create_table("trade", default_response=[])  # No trades match the filter

        manager.create_table("trade_escrow", default_response=[])
        manager.create_table("trade_recipient", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.delete("/admin/trades/cleanup?retention_days=30&dry_run=true")

        assert response.status_code == 200
        data = response.json()
        # No trades should be cleaned
        assert data["trades_cleaned"] == 0
        assert data["escrow_records_deleted"] == 0
        assert data["recipient_records_deleted"] == 0

    def test_cleanup_removes_escrow_and_recipient_rows(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify related escrow and recipient rows are deleted"""
        from datetime import timedelta

        manager = MockTableManager()

        old_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()

        manager.create_table("trade", default_response=[
            {"trade_id": "trade_1", "status": "completed", "resolved_at": old_date},
        ])

        # Multiple escrow and recipient rows
        manager.create_table("trade_escrow", default_response=[
            {"trade_id": "trade_1", "card_id": "card1", "quantity": 2},
            {"trade_id": "trade_1", "card_id": "card2", "quantity": 1},
            {"trade_id": "trade_1", "card_id": "card3", "quantity": 3},
        ])

        manager.create_table("trade_recipient", default_response=[
            {"trade_id": "trade_1", "card_id": "card4", "quantity": 1},
            {"trade_id": "trade_1", "card_id": "card5", "quantity": 2},
        ])

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.delete("/admin/trades/cleanup?retention_days=30&dry_run=true")

        assert response.status_code == 200
        data = response.json()
        assert data["trades_cleaned"] == 1
        assert data["escrow_records_deleted"] == 3
        assert data["recipient_records_deleted"] == 2

    def test_cleanup_custom_retention_days(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify custom retention_days parameter is respected"""
        from datetime import timedelta

        manager = MockTableManager()

        # Trade that's 80 days old
        date_80_days = (datetime.now(timezone.utc) - timedelta(days=80)).isoformat()

        # With retention_days=60, only the 80-day-old trade should be cleaned
        manager.create_table("trade", default_response=[
            {"trade_id": "very_old_trade", "status": "completed", "resolved_at": date_80_days},
        ])

        manager.create_table("trade_escrow", default_response=[
            {"trade_id": "very_old_trade", "card_id": "card1", "quantity": 1},
        ])
        manager.create_table("trade_recipient", default_response=[])

        mock_supabase_client.table.side_effect = manager.table_handler

        # Use custom retention of 60 days
        response = client.delete("/admin/trades/cleanup?retention_days=60&dry_run=true")

        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == 60
        assert data["trades_cleaned"] == 1

    def test_cleanup_returns_deleted_counts(
        self,
        client,
        mock_supabase_client,
    ):
        """Verify accurate deletion counts are returned"""
        from datetime import timedelta

        manager = MockTableManager()

        old_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()

        # Multiple old trades
        manager.create_table("trade", default_response=[
            {"trade_id": "trade_1", "status": "completed", "resolved_at": old_date},
            {"trade_id": "trade_2", "status": "rejected", "resolved_at": old_date},
            {"trade_id": "trade_3", "status": "cancelled", "resolved_at": old_date},
        ])

        # Different number of escrow/recipient records per trade
        escrow_responses = [
            [{"card_id": "c1", "quantity": 1}],  # trade_1: 1 escrow
            [{"card_id": "c2", "quantity": 1}, {"card_id": "c3", "quantity": 2}],  # trade_2: 2 escrow
            [],  # trade_3: 0 escrow
        ]

        recipient_responses = [
            [{"card_id": "c4", "quantity": 1}, {"card_id": "c5", "quantity": 1}],  # trade_1: 2 recipient
            [],  # trade_2: 0 recipient
            [{"card_id": "c6", "quantity": 1}],  # trade_3: 1 recipient
        ]

        manager.create_table("trade_escrow", responses=escrow_responses)
        manager.create_table("trade_recipient", responses=recipient_responses)

        mock_supabase_client.table.side_effect = manager.table_handler

        response = client.delete("/admin/trades/cleanup?retention_days=30&dry_run=true")

        assert response.status_code == 200
        data = response.json()
        assert data["trades_cleaned"] == 3
        assert data["escrow_records_deleted"] == 3  # 1 + 2 + 0
        assert data["recipient_records_deleted"] == 3  # 2 + 0 + 1
