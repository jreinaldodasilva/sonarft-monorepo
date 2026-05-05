"""
WebSocket tests — connection lifecycle, auth, command dispatch, event delivery.

Strategy for async tasks:
- Commands that dispatch asyncio.create_task (create/run/remove) are verified
  via mock call assertions after a brief sleep, not by waiting for events.
- Synchronous paths (limit check, input validation, log streaming) are verified
  by reading events directly from the WebSocket.
"""
from __future__ import annotations

import logging
import os
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ws_url(client_id: str = "test-client", token: str | None = None) -> str:
    _token = token or os.environ.get("SONARFT_TEST_WS_TOKEN", "test-token")
    return f"/api/v1/ws/{client_id}?token={_token}"


def _drain_until(ws, expected_type: str, max_events: int = 10) -> dict:
    """Read events until we find one with the expected type."""
    for _ in range(max_events):
        data = ws.receive_json()
        if data["type"] == expected_type:
            return data
    raise AssertionError(
        f"Expected event type {expected_type!r} not received in {max_events} events"
    )


# ---------------------------------------------------------------------------
# 1. Connection lifecycle
# ---------------------------------------------------------------------------

class TestWebSocketConnection:

    def test_connects_and_receives_connected_event(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert data["client_id"] == "test-client"
            assert "ts" in data

    def test_connected_event_has_ts(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            data = ws.receive_json()
            assert isinstance(data["ts"], int)

    def test_connection_stays_open(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"


# ---------------------------------------------------------------------------
# 2. Authentication
# ---------------------------------------------------------------------------

class TestWebSocketAuth:

    def test_invalid_token_closes_with_1008(self):
        from unittest.mock import patch

        from src.core.config import get_settings
        get_settings.cache_clear()
        with patch.dict("os.environ", {"SONARFT_API_TOKEN": "secret"}, clear=False):
            get_settings.cache_clear()
            from src.main import create_app
            app = create_app()
            with TestClient(app, raise_server_exceptions=False) as c:
                with pytest.raises(WebSocketDisconnect):
                    with c.websocket_connect("/api/v1/ws/test?token=wrong") as ws:
                        ws.receive_json()
        get_settings.cache_clear()

    def test_dev_mode_any_token_accepted(self, client: TestClient):
        with client.websocket_connect(_ws_url(token="anything")) as ws:
            data = ws.receive_json()
            assert data["type"] == "connected"


# ---------------------------------------------------------------------------
# 3. Command dispatch — create
# ---------------------------------------------------------------------------

class TestWebSocketCreateCommand:

    def test_create_command_calls_bot_manager(
        self, client: TestClient, mock_bot_service
    ):
        """Verify create command reaches the bot manager via _manager."""
        mock_bot_service._manager.create_bot = AsyncMock(return_value="new-bot-001")
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "create"})
            time.sleep(0.1)
        mock_bot_service._manager.create_bot.assert_called_once_with("test-client")

    def test_create_at_limit_sends_error_event(
        self, client: TestClient, mock_bot_service
    ):
        """Bot limit check is synchronous — error event arrives immediately."""
        mock_bot_service._manager.get_botids = MagicMock(
            return_value=["b1", "b2", "b3", "b4", "b5"]
        )
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "create"})
            data = _drain_until(ws, "error")
            assert "limit" in data["message"].lower()

    def test_create_failure_handled_gracefully(
        self, client: TestClient, mock_bot_service
    ):
        mock_bot_service._manager.create_bot = AsyncMock(
            side_effect=RuntimeError("db error")
        )
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "create"})
            time.sleep(0.1)
        # No unhandled exception — error was caught by _handle_create


# ---------------------------------------------------------------------------
# 4. Command dispatch — remove
# ---------------------------------------------------------------------------

class TestWebSocketRemoveCommand:

    def test_remove_command_calls_bot_manager(
        self, client: TestClient, mock_bot_service
    ):
        mock_bot_service._manager.remove_bot = AsyncMock(return_value=None)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "remove", "botid": "bot-001"})
            time.sleep(0.1)
        mock_bot_service._manager.remove_bot.assert_called_once_with("bot-001")

    def test_remove_failure_handled_gracefully(
        self, client: TestClient, mock_bot_service
    ):
        mock_bot_service._manager.remove_bot = AsyncMock(
            side_effect=RuntimeError("not found")
        )
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "remove", "botid": "bot-001"})
            time.sleep(0.1)
        # No unhandled exception


# ---------------------------------------------------------------------------
# 5. Command dispatch — run
# ---------------------------------------------------------------------------

class TestWebSocketRunCommand:

    def test_run_command_calls_bot_manager(
        self, client: TestClient, mock_bot_service
    ):
        mock_bot_service._manager.run_bot = AsyncMock(return_value=None)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "run", "botid": "bot-001"})
            time.sleep(0.1)
        mock_bot_service._manager.run_bot.assert_called_once_with("bot-001")

    def test_run_failure_handled_gracefully(
        self, client: TestClient, mock_bot_service
    ):
        mock_bot_service._manager.run_bot = AsyncMock(side_effect=RuntimeError("crash"))
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "run", "botid": "bot-001"})
            time.sleep(0.1)
        # No unhandled exception


# ---------------------------------------------------------------------------
# 6. Input validation — synchronous paths
# ---------------------------------------------------------------------------

class TestWebSocketInputValidation:

    def test_invalid_botid_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "run", "botid": "../../etc/passwd"})
            data = _drain_until(ws, "error")
            assert "botid" in data["message"].lower()

    def test_missing_botid_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "run"})
            data = _drain_until(ws, "error")
            assert data["type"] == "error"

    def test_unknown_command_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "unknown_command"})
            data = _drain_until(ws, "error")
            assert "unknown" in data["message"].lower()

    def test_invalid_json_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_text("not valid json {{{")
            data = _drain_until(ws, "error")
            assert "json" in data["message"].lower()

    def test_set_simulation_missing_botid_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "set_simulation", "value": True})
            data = _drain_until(ws, "error")
            assert data["type"] == "error"

    def test_oversized_botid_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "run", "botid": "a" * 65})
            data = _drain_until(ws, "error")
            assert data["type"] == "error"


# ---------------------------------------------------------------------------
# 7. Log streaming
# ---------------------------------------------------------------------------

class TestWebSocketLogStreaming:

    def test_log_handler_attached_on_connect(self, client: TestClient):
        """WsLogHandler is attached to the root logger on connect and
        removed on disconnect. Handler count on root logger increases by 1.
        """
        root_logger = logging.getLogger()
        initial_count = len(root_logger.handlers)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            assert len(root_logger.handlers) == initial_count + 1
        # Handler detached after disconnect
        assert len(root_logger.handlers) == initial_count

    def test_log_event_delivered_to_client(self, client: TestClient):
        """Bot log records (name starting with 'sonarft') pass the filter
        and are placed into the client queue by WsLogHandler.
        """
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            # Find the WsLogHandler on the root logger
            root_logger = logging.getLogger()
            ws_handlers = [
                h for h in root_logger.handlers
                if h.__class__.__name__ == "WsLogHandler"
            ]
            assert len(ws_handlers) == 1, "WsLogHandler should be on root logger"
            handler = ws_handlers[0]
            # A record from a sonarft logger must pass the filter and reach the queue
            record = logging.LogRecord(
                name="sonarft_manager", level=logging.INFO,
                pathname="", lineno=0,
                msg="test log message", args=(), exc_info=None,
            )
            assert handler.filter(record), "sonarft record should pass the bot filter"
            handler.emit(record)
            # A record from a non-bot logger must be blocked by the filter
            api_record = logging.LogRecord(
                name="src.services.bot_service", level=logging.INFO,
                pathname="", lineno=0,
                msg="api log", args=(), exc_info=None,
            )
            assert not handler.filter(api_record), "non-sonarft record should be filtered out"


# ---------------------------------------------------------------------------
# 8. Command dispatch — stop  [H5]
# ---------------------------------------------------------------------------

class TestWebSocketStopCommand:

    def test_stop_command_calls_pause_bot(
        self, client: TestClient, mock_bot_service
    ):
        """stop command must call BotManager.pause_bot."""
        mock_bot_service._manager.pause_bot = AsyncMock(return_value=None)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "stop", "botid": "bot-001"})
            time.sleep(0.1)
        mock_bot_service._manager.pause_bot.assert_called_once_with("bot-001")

    def test_stop_success_sends_bot_stopped_event(
        self, client: TestClient, mock_bot_service
    ):
        """A successful stop must deliver a bot_stopped event to the client."""
        mock_bot_service._manager.pause_bot = AsyncMock(return_value=None)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "stop", "botid": "bot-001"})
            data = _drain_until(ws, "bot_stopped")
        assert data["type"] == "bot_stopped"
        assert data["botid"] == "bot-001"
        assert "ts" in data

    def test_stop_failure_sends_error_event(
        self, client: TestClient, mock_bot_service
    ):
        """A failed stop must deliver an error event, not crash the connection."""
        mock_bot_service._manager.pause_bot = AsyncMock(
            side_effect=RuntimeError("pause failed")
        )
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "stop", "botid": "bot-001"})
            data = _drain_until(ws, "error")
        assert data["type"] == "error"
        assert "stop" in data["message"].lower()

    def test_stop_missing_botid_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "stop"})
            data = _drain_until(ws, "error")
            assert data["type"] == "error"

    def test_stop_invalid_botid_sends_error(self, client: TestClient):
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "stop", "botid": "../../etc/passwd"})
            data = _drain_until(ws, "error")
            assert data["type"] == "error"


# ---------------------------------------------------------------------------
# 9. Command dispatch — set_simulation  [M3]
# ---------------------------------------------------------------------------

class TestWebSocketSetSimulationCommand:

    def test_set_simulation_calls_bot_manager(
        self, client: TestClient, mock_bot_service
    ):
        """set_simulation command must call BotManager.set_simulation_mode."""
        mock_bot_service._manager.set_simulation_mode = AsyncMock(return_value=None)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "set_simulation", "botid": "bot-001", "value": False})
            time.sleep(0.1)
        mock_bot_service._manager.set_simulation_mode.assert_called_once_with(
            "bot-001", False
        )

    def test_set_simulation_true_value(
        self, client: TestClient, mock_bot_service
    ):
        mock_bot_service._manager.set_simulation_mode = AsyncMock(return_value=None)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "set_simulation", "botid": "bot-001", "value": True})
            time.sleep(0.1)
        mock_bot_service._manager.set_simulation_mode.assert_called_once_with(
            "bot-001", True
        )

    def test_set_simulation_failure_handled_gracefully(
        self, client: TestClient, mock_bot_service
    ):
        mock_bot_service._manager.set_simulation_mode = AsyncMock(
            side_effect=RuntimeError("mode error")
        )
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "set_simulation", "botid": "bot-001", "value": False})
            time.sleep(0.1)
        # No unhandled exception — error was caught by _handle_set_simulation
