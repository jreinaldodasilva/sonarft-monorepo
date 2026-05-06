"""
TicketStore unit tests — single-use WebSocket auth tickets.

Covers: issue, redeem, expiry, single-use enforcement,
unknown ticket, capacity cap, and eviction.
"""
from __future__ import annotations

import time

import pytest
from src.websocket.tickets import TicketStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _store(ttl: int = 30) -> TicketStore:
    return TicketStore(ttl=ttl)


# ---------------------------------------------------------------------------
# 1. Issue & redeem — happy path
# ---------------------------------------------------------------------------

class TestIssueAndRedeem:

    def test_issue_returns_non_empty_string(self):
        ticket = _store().issue("client-1")
        assert isinstance(ticket, str)
        assert len(ticket) > 0

    def test_issue_returns_unique_tickets(self):
        store = _store()
        t1 = store.issue("client-1")
        t2 = store.issue("client-1")
        assert t1 != t2

    def test_redeem_returns_correct_identity(self):
        store = _store()
        ticket = store.issue("client-abc")
        assert store.redeem(ticket) == "client-abc"

    def test_redeem_different_identities(self):
        store = _store()
        t1 = store.issue("alice")
        t2 = store.issue("bob")
        assert store.redeem(t1) == "alice"
        assert store.redeem(t2) == "bob"

    def test_len_increases_on_issue(self):
        store = _store()
        assert len(store) == 0
        store.issue("client-1")
        assert len(store) == 1
        store.issue("client-2")
        assert len(store) == 2


# ---------------------------------------------------------------------------
# 2. Single-use enforcement
# ---------------------------------------------------------------------------

class TestSingleUse:

    def test_ticket_cannot_be_redeemed_twice(self):
        store = _store()
        ticket = store.issue("client-1")
        assert store.redeem(ticket) == "client-1"
        assert store.redeem(ticket) is None  # already consumed

    def test_len_decreases_after_redeem(self):
        store = _store()
        ticket = store.issue("client-1")
        assert len(store) == 1
        store.redeem(ticket)
        assert len(store) == 0

    def test_multiple_tickets_independent(self):
        store = _store()
        t1 = store.issue("client-1")
        t2 = store.issue("client-2")
        store.redeem(t1)
        # t2 must still be valid after t1 is consumed
        assert store.redeem(t2) == "client-2"


# ---------------------------------------------------------------------------
# 3. Unknown / invalid tickets
# ---------------------------------------------------------------------------

class TestUnknownTickets:

    def test_unknown_ticket_returns_none(self):
        store = _store()
        assert store.redeem("nonexistent-ticket") is None

    def test_empty_string_returns_none(self):
        store = _store()
        assert store.redeem("") is None

    def test_random_string_returns_none(self):
        store = _store()
        assert store.redeem("aaaa-bbbb-cccc") is None

    def test_redeem_does_not_raise_on_unknown(self):
        store = _store()
        # Must not raise any exception
        result = store.redeem("totally-unknown")
        assert result is None


# ---------------------------------------------------------------------------
# 4. Expiry
# ---------------------------------------------------------------------------

class TestExpiry:

    def test_expired_ticket_returns_none(self):
        store = _store(ttl=0)  # expires immediately
        ticket = store.issue("client-1")
        time.sleep(0.01)       # ensure monotonic clock advances past TTL
        assert store.redeem(ticket) is None

    def test_valid_ticket_within_ttl(self):
        store = _store(ttl=30)
        ticket = store.issue("client-1")
        # Redeem immediately — well within TTL
        assert store.redeem(ticket) == "client-1"

    def test_expired_ticket_not_counted_in_len_after_eviction(self):
        store = _store(ttl=0)
        store.issue("client-1")
        # Trigger eviction by issuing another ticket
        store.issue("client-2")
        # The expired ticket should have been evicted
        assert len(store) == 1  # only the new ticket remains


# ---------------------------------------------------------------------------
# 5. Capacity cap
# ---------------------------------------------------------------------------

class TestCapacityCap:

    def test_capacity_cap_raises_runtime_error(self):
        from unittest.mock import patch

        import src.websocket.tickets as tickets_module
        store = _store(ttl=30)
        # _MAX_TICKETS is a module-level constant — patch it at the module level
        with patch.object(tickets_module, "_MAX_TICKETS", 3):
            store.issue("a")
            store.issue("b")
            store.issue("c")
            with pytest.raises(RuntimeError, match="capacity"):
                store.issue("d")

    def test_capacity_not_exceeded_after_redeem(self):
        from unittest.mock import patch

        import src.websocket.tickets as tickets_module
        store = _store(ttl=30)
        with patch.object(tickets_module, "_MAX_TICKETS", 2):
            t1 = store.issue("a")
            store.issue("b")
            store.redeem(t1)  # free one slot
            # Should now be able to issue again without raising
            store.issue("c")
        assert len(store) == 2

    def test_capacity_not_exceeded_after_expiry_eviction(self):
        from unittest.mock import patch

        import src.websocket.tickets as tickets_module
        store = _store(ttl=0)
        with patch.object(tickets_module, "_MAX_TICKETS", 2):
            store.issue("a")  # expires immediately; evicted on next issue()
            store.issue("b")  # evicts "a", stores "b" (also expires immediately)
            store.issue("c")  # evicts "b", stores "c" — should not raise
        assert len(store) == 1


# ---------------------------------------------------------------------------
# 6. Eviction
# ---------------------------------------------------------------------------

class TestEviction:

    def test_evict_expired_removes_stale_entries(self):
        # With ttl=0, _evict_expired() is called at the start of each issue(),
        # so we insert directly into _tickets to bypass the eviction on issue.
        store = _store(ttl=0)
        import time as _t
        already_expired = _t.monotonic() - 1  # 1 second in the past
        store._tickets["ticket-a"] = ("a", already_expired)
        store._tickets["ticket-b"] = ("b", already_expired)
        assert len(store) == 2
        store._evict_expired()
        assert len(store) == 0

    def test_evict_expired_keeps_valid_entries(self):
        store = _store(ttl=30)
        store.issue("a")
        store.issue("b")
        store._evict_expired()
        assert len(store) == 2

    def test_evict_expired_mixed(self):
        # Issue one expired and one valid ticket
        expired_store = _store(ttl=0)
        expired_ticket = expired_store.issue("expired")
        time.sleep(0.01)

        valid_store = _store(ttl=30)
        valid_ticket = valid_store.issue("valid")

        # Manually merge into one store to test mixed eviction
        store = _store(ttl=30)
        store._tickets[expired_ticket] = expired_store._tickets[expired_ticket]
        store._tickets[valid_ticket] = valid_store._tickets[valid_ticket]
        assert len(store) == 2

        store._evict_expired()
        assert len(store) == 1
        assert store.redeem(valid_ticket) == "valid"


# ---------------------------------------------------------------------------
# 7. Module-level singleton
# ---------------------------------------------------------------------------

class TestModuleSingleton:

    def test_get_ticket_store_returns_same_instance(self):
        from src.websocket.tickets import get_ticket_store
        s1 = get_ticket_store()
        s2 = get_ticket_store()
        assert s1 is s2

    def test_singleton_is_ticket_store_instance(self):
        from src.websocket.tickets import get_ticket_store
        assert isinstance(get_ticket_store(), TicketStore)
