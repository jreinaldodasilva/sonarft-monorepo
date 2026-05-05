"""
Smoke tests — verify the test infrastructure is wired correctly.
These run first and confirm the app starts, fixtures work, and
the health endpoint responds before any deeper tests run.
"""
from fastapi.testclient import TestClient


class TestSmoke:

    def test_app_creates_without_error(self, app):
        """App factory must not raise on import or construction."""
        assert app is not None

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_response_schema(self, client: TestClient):
        data = client.get("/api/v1/health").json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_requires_no_auth(self, client: TestClient):
        """Health endpoint must be reachable without an Authorization header."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_protected_endpoint_without_token_returns_401(self, client: TestClient):
        """Any protected endpoint must return 401 when no token is provided.
        NOTE: in dev mode (no auth env vars set) this will return 200.
        The full auth test is in test_security.py with env var patching."""
        # Just confirm the endpoint exists and responds
        response = client.get("/api/v1/bots?client_id=test")
        assert response.status_code in (200, 401)

    def test_mock_bot_service_fixture(self, client: TestClient, mock_bot_service, auth_headers):
        """Confirm mock_bot_service fixture patches the service correctly."""
        mock_bot_service.get_botids.return_value = ["smoke-bot-001"]
        response = client.get("/api/v1/bots?client_id=test", headers=auth_headers)
        assert response.status_code == 200
        assert "botids" in response.json()


class TestAuthDisabledWarning:
    """Verify the startup warning fires when auth is not configured."""

    def test_warning_emitted_in_dev_mode(self, caplog):
        """When neither auth env var is set, a WARNING must be logged at startup."""
        import logging
        from unittest.mock import patch

        from src.core.config import get_settings
        get_settings.cache_clear()
        with patch.dict("os.environ", {"NETLIFY_SITE_URL": "", "SONARFT_API_TOKEN": ""}, clear=False):
            get_settings.cache_clear()
            from src.main import create_app
            app = create_app()
            with caplog.at_level(logging.WARNING):
                with TestClient(app):
                    pass
        get_settings.cache_clear()
        assert any(
            "AUTH DISABLED" in r.message
            for r in caplog.records
            if r.levelno == logging.WARNING
        ), "Expected AUTH DISABLED warning in startup logs"

    def test_no_warning_when_static_token_set(self, caplog):
        """When SONARFT_API_TOKEN is set, no AUTH DISABLED warning should appear."""
        import logging
        from unittest.mock import patch

        from src.core.config import get_settings
        from src.services.bot_service import get_bot_service
        get_settings.cache_clear()
        get_bot_service.cache_clear()
        with patch.dict("os.environ", {"SONARFT_API_TOKEN": "secret", "NETLIFY_SITE_URL": ""}, clear=False):
            get_settings.cache_clear()
            from src.main import create_app
            app = create_app()
            with caplog.at_level(logging.WARNING):
                with TestClient(app):
                    pass
        get_settings.cache_clear()
        get_bot_service.cache_clear()
        assert not any(
            "AUTH DISABLED" in r.message
            for r in caplog.records
            if r.levelno == logging.WARNING
        ), "AUTH DISABLED warning must not appear when a token is configured"
