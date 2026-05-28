"""
BotService integration tests — verify the real BotService initialisation path.

These tests mock the bot package imports but exercise the actual BotService
constructor, catching regressions like the logger name mismatch that broke
WebSocket log streaming (SEC-003).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


class TestBotServiceLoggerInjection:

    def test_bot_manager_receives_sonarft_namespaced_logger(self):
        """SEC-003: BotManager must receive a logger whose name starts with
        'sonarft' so WsLogHandler._is_bot_record() passes its records through
        to WebSocket clients.

        If this test fails it means the logger injection was changed back to
        logging.getLogger(__name__) which resolves to 'src.services.bot_service'
        — a name that does NOT pass the WsLogHandler filter.
        """
        with patch("sonarft_manager.BotManager") as MockBM, \
             patch("sonarft_helpers.SonarftHelpers"):
            MockBM.return_value = MagicMock()
            from src.services.bot_service import BotService
            BotService()
            call_kwargs = MockBM.call_args
            injected_logger = (
                call_kwargs.kwargs.get("logger")
                or (call_kwargs.args[0] if call_kwargs.args else None)
            )
            # None is acceptable — bot uses its own sonarft.* loggers
            if injected_logger is not None:
                assert injected_logger.name.startswith("sonarft"), (
                    f"BotManager received logger '{injected_logger.name}'. "
                    "WsLogHandler will not stream its records to WebSocket clients. "
                    "Use logging.getLogger('sonarft.api_bridge') or pass logger=None."
                )
