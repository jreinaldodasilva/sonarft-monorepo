"""
SonarFT WebSocket Ticket Store
Short-lived, single-use opaque tickets for WebSocket authentication.
Keeps the JWT out of server logs and browser history.
"""
from __future__ import annotations

import secrets
import time

_TICKET_TTL_SECONDS = 30
_MAX_TICKETS = 10_000  # safety cap to prevent memory exhaustion


class TicketStore:
    """
    In-memory store for single-use WebSocket tickets.
    Each ticket maps to a client identity and expires after TTL seconds.
    Thread-safe for single-process use (asyncio event loop).
    """

    def __init__(self, ttl: int = _TICKET_TTL_SECONDS) -> None:
        self._ttl = ttl
        self._tickets: dict[str, tuple[str, float]] = {}  # ticket -> (identity, expires_at)

    def issue(self, identity: str) -> str:
        """Issue a new single-use ticket for the given identity. Returns the ticket string."""
        self._evict_expired()
        if len(self._tickets) >= _MAX_TICKETS:
            raise RuntimeError("Ticket store capacity exceeded")
        ticket = secrets.token_urlsafe(32)
        self._tickets[ticket] = (identity, time.monotonic() + self._ttl)
        return ticket

    def redeem(self, ticket: str) -> str | None:
        """
        Validate and consume a ticket. Returns the identity if valid, None otherwise.
        A ticket can only be redeemed once.
        """
        entry = self._tickets.pop(ticket, None)
        if entry is None:
            return None
        identity, expires_at = entry
        if time.monotonic() > expires_at:
            return None
        return identity

    def _evict_expired(self) -> None:
        """Remove expired tickets to prevent unbounded growth."""
        now = time.monotonic()
        expired = [t for t, (_, exp) in self._tickets.items() if now > exp]
        for t in expired:
            del self._tickets[t]

    def __len__(self) -> int:
        return len(self._tickets)


# Module-level singleton — shared across the application
_store = TicketStore()


def get_ticket_store() -> TicketStore:
    return _store
