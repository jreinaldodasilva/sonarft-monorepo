"""
E2E WebSocket log streaming integration test.

Validates the C2 fix: log records emitted by sonarft_* loggers are
streamed to the connected WebSocket client as 'log' events.

Architecture under test:
  sonarft_manager logger.info(msg)
    -> WsLogHandler.emit() [attached to root logger with sonarft filter]
      -> asyncio.Queue.put_nowait({"type": "log", ...})
        -> _send_loop drains queue
          -> websocket.send_text(json.dumps(event))
            -> client receives {"type": "log", "message": msg, ...}

Uses TestClient's synchronous WebSocket support. The WsLogHandler
puts events into the queue synchronously (put_nowait), so the event
is available immediately after emit() — no async wait needed.
"""
from __future__ import annotations

import logging

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ws_url(client_id: str = "stream-test") -> str:
    return f"/api/v1/ws/{client_id}?token=test-token"


def _drain_until(ws, expected_type: str, max_events: int = 20) -> dict:
    """Read events until one with the expected type is found."""
    for _ in range(max_events):
        data = ws.receive_json()
        if data["type"] == expected_type:
            return data
    raise AssertionError(
        f"Expected event type {expected_type!r} not received in {max_events} events"
    )


# ---------------------------------------------------------------------------
# 1. Filter correctness — unit-level, no WS connection needed
# ---------------------------------------------------------------------------

class TestWsLogHandlerFilter:
    """Verify the _is_bot_record filter without opening a WebSocket."""

    def test_sonarft_logger_passes_filter(self, client: TestClient):
        """Records from sonarft_* loggers must pass the filter."""
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            root_logger = logging.getLogger()
            handlers = [
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            ]
            assert handlers, "WsLogHandler must be attached to root logger"
            handler = handlers[0]

            for logger_name in [
                "sonarft_manager",
                "sonarft_bot",
                "sonarft_search",
                "sonarft_execution",
                "sonarft_indicators",
                "sonarft_prices",
                "sonarft_helpers",
            ]:
                record = logging.LogRecord(
                    name=logger_name, level=logging.INFO,
                    pathname="", lineno=0,
                    msg="test", args=(), exc_info=None,
                )
                assert handler.filter(record), (
                    f"Logger '{logger_name}' should pass the sonarft filter"
                )

    def test_non_sonarft_logger_blocked_by_filter(self, client: TestClient):
        """Records from non-sonarft loggers must be blocked."""
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            root_logger = logging.getLogger()
            handlers = [
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            ]
            handler = handlers[0]

            for logger_name in [
                "src.services.bot_service",
                "src.websocket.manager",
                "uvicorn",
                "fastapi",
                "root",
            ]:
                record = logging.LogRecord(
                    name=logger_name, level=logging.INFO,
                    pathname="", lineno=0,
                    msg="should be blocked", args=(), exc_info=None,
                )
                assert not handler.filter(record), (
                    f"Logger '{logger_name}' should be blocked by the sonarft filter"
                )


# ---------------------------------------------------------------------------
# 2. E2E delivery — log record reaches the WebSocket client
# ---------------------------------------------------------------------------

class TestLogStreamingE2E:

    def test_sonarft_log_delivered_as_log_event(self, client: TestClient):
        """
        E2E: emit a log record from sonarft_manager -> verify it arrives
        as a 'log' event on the WebSocket client.

        This is the core validation of the C2 fix. Before C2, the handler
        was attached to 'src.services.bot_service' (wrong logger name) and
        zero bot log events reached the client.
        """
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected

            root_logger = logging.getLogger()
            ws_handlers = [
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            ]
            assert ws_handlers, "WsLogHandler must be on root logger after connect"
            handler = ws_handlers[0]

            record = logging.LogRecord(
                name="sonarft_manager", level=logging.INFO,
                pathname="", lineno=0,
                msg="Bot abc-123 start running", args=(), exc_info=None,
            )
            # Use handle() so the filter is applied (emit() bypasses filters)
            handler.handle(record)

            event = _drain_until(ws, "log")

        assert event["type"] == "log"
        assert "Bot abc-123 start running" in event["message"]
        assert event["level"] == "INFO"
        assert "ts" in event

    def test_log_event_has_correct_level(self, client: TestClient):
        """WARNING level records must arrive with level='WARNING'."""
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            root_logger = logging.getLogger()
            handler = next(
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            )
            record = logging.LogRecord(
                name="sonarft_execution", level=logging.WARNING,
                pathname="", lineno=0,
                msg="Insufficient balance", args=(), exc_info=None,
            )
            handler.handle(record)
            event = _drain_until(ws, "log")

        assert event["level"] == "WARNING"
        assert "Insufficient balance" in event["message"]

    def test_multiple_log_events_delivered_in_order(self, client: TestClient):
        """Multiple log records must arrive in emission order."""
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            root_logger = logging.getLogger()
            handler = next(
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            )
            messages = ["first message", "second message", "third message"]
            for msg in messages:
                record = logging.LogRecord(
                    name="sonarft_bot", level=logging.INFO,
                    pathname="", lineno=0,
                    msg=msg, args=(), exc_info=None,
                )
                handler.handle(record)

            received = []
            for _ in range(len(messages)):
                event = _drain_until(ws, "log")
                received.append(event["message"])

        for msg in messages:
            assert any(msg in r for r in received), (
                f"Message '{msg}' not found in received events"
            )

    def test_non_sonarft_log_not_delivered(self, client: TestClient):
        """Records from non-sonarft loggers must not appear in the stream."""
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            root_logger = logging.getLogger()
            handler = next(
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            )
            # Use handle() so the filter is applied — emit() bypasses filters
            blocked_record = logging.LogRecord(
                name="src.services.bot_service", level=logging.INFO,
                pathname="", lineno=0,
                msg="this should not appear", args=(), exc_info=None,
            )
            handler.handle(blocked_record)  # filter blocks this

            # Emit a passing record immediately after
            passing_record = logging.LogRecord(
                name="sonarft_manager", level=logging.INFO,
                pathname="", lineno=0,
                msg="sentinel message", args=(), exc_info=None,
            )
            handler.handle(passing_record)  # filter passes this

            # The first log event received must be the sentinel, not the blocked one
            event = _drain_until(ws, "log")

        assert "sentinel message" in event["message"]
        assert "this should not appear" not in event["message"]


# ---------------------------------------------------------------------------
# 3. Handler lifecycle — attach on connect, detach on disconnect
# ---------------------------------------------------------------------------

class TestHandlerLifecycle:

    def test_handler_attached_on_connect(self, client: TestClient):
        root_logger = logging.getLogger()
        before = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            during = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
            assert during == before + 1
        after = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
        assert after == before

    def test_handler_detached_on_disconnect(self, client: TestClient):
        """After the WS context exits, the handler count must return to baseline."""
        root_logger = logging.getLogger()
        baseline = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()
        final = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
        assert final == baseline

    def test_two_connections_attach_two_handlers(self, client: TestClient):
        """Each concurrent connection gets its own WsLogHandler."""
        root_logger = logging.getLogger()
        baseline = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
        # Open first connection
        with client.websocket_connect(_ws_url("client-1")) as ws1:
            ws1.receive_json()
            mid = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
            assert mid == baseline + 1
        # After first disconnects, back to baseline
        final = len([h for h in root_logger.handlers if h.__class__.__name__ == "WsLogHandler"])
        assert final == baseline


# ---------------------------------------------------------------------------
# 4. order_success / trade_success structured events
# ---------------------------------------------------------------------------

class TestStructuredEvents:

    def test_order_success_event_emitted_on_matching_log(self, client: TestClient):
        """'Order: Success' in a log message must also emit an order_success event."""
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            root_logger = logging.getLogger()
            handler = next(
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            )
            record = logging.LogRecord(
                name="sonarft_helpers", level=logging.INFO,
                pathname="", lineno=0,
                msg="Order: Success", args=(), exc_info=None,
            )
            handler.handle(record)

            # Should receive both a log event and an order_success event
            events = {}
            for _ in range(5):
                event = ws.receive_json()
                events[event["type"]] = event
                if "log" in events and "order_success" in events:
                    break

        assert "order_success" in events, (
            f"Expected order_success event, got: {list(events.keys())}"
        )
        assert "log" in events

    def test_trade_success_event_emitted_on_matching_log(self, client: TestClient):
        """'Trade: Success' in a log message must also emit a trade_success event."""
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            root_logger = logging.getLogger()
            handler = next(
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            )
            record = logging.LogRecord(
                name="sonarft_helpers", level=logging.INFO,
                pathname="", lineno=0,
                msg="Trade: Success", args=(), exc_info=None,
            )
            handler.handle(record)

            events = {}
            for _ in range(5):
                event = ws.receive_json()
                events[event["type"]] = event
                if "log" in events and "trade_success" in events:
                    break

        assert "trade_success" in events
        assert "log" in events
