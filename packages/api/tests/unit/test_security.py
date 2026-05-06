"""
Security tests for the SonarFT API.
Covers:
- Authentication: dev mode, static token, JWT (mocked)
- Authorization: protected endpoints reject missing/invalid tokens
- Input validation: botid regex, client_id sanitization (path traversal)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patched_client(env: dict):
    """
    Return a TestClient with Settings overridden via environment patch.
    lru_cache on get_settings is cleared so the new env takes effect.
    """
    from src.core.config import get_settings
    get_settings.cache_clear()
    with patch.dict("os.environ", env, clear=False):
        get_settings.cache_clear()
        from src.main import create_app
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        yield client
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# 1. Dev mode — no auth configured
# ---------------------------------------------------------------------------

class TestDevModeAuth:
    """When neither NETLIFY_SITE_URL nor SONARFT_API_TOKEN is set, all requests pass."""

    def test_health_no_token(self, client: TestClient):
        assert client.get("/api/v1/health").status_code == 200

    def test_bots_no_token_passes_in_dev_mode(self, client: TestClient, mock_bot_service):
        """Dev mode: missing token is accepted."""
        response = client.get("/api/v1/bots?client_id=test")
        assert response.status_code == 200

    def test_bots_any_token_passes_in_dev_mode(self, client: TestClient, mock_bot_service):
        response = client.get(
            "/api/v1/bots?client_id=test",
            headers={"Authorization": "Bearer anything"},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. Static token auth
# ---------------------------------------------------------------------------

class TestStaticTokenAuth:
    """When SONARFT_API_TOKEN is set, only matching tokens are accepted."""

    @pytest.fixture
    def static_client(self):
        from src.core.config import get_settings
        from src.services.bot_service import get_bot_service
        get_settings.cache_clear()
        get_bot_service.cache_clear()

        with patch.dict("os.environ", {"SONARFT_API_TOKEN": "secret-token"}, clear=False):
            get_settings.cache_clear()
            from src.main import create_app
            app = create_app()
            with TestClient(app, raise_server_exceptions=False) as c:
                yield c

        get_settings.cache_clear()
        get_bot_service.cache_clear()

    def test_correct_token_accepted(self, static_client: TestClient, mock_bot_service):
        response = static_client.get(
            "/api/v1/bots?client_id=test",
            headers={"Authorization": "Bearer secret-token"},
        )
        assert response.status_code == 200

    def test_wrong_token_rejected(self, static_client: TestClient):
        response = static_client.get(
            "/api/v1/bots?client_id=test",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401

    def test_missing_token_rejected(self, static_client: TestClient):
        response = static_client.get("/api/v1/bots?client_id=test")
        assert response.status_code == 401

    def test_empty_bearer_rejected(self, static_client: TestClient):
        response = static_client.get(
            "/api/v1/bots?client_id=test",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == 401

    def test_health_bypasses_auth(self, static_client: TestClient):
        """Health endpoint must remain accessible without a token."""
        response = static_client.get("/api/v1/health")
        assert response.status_code == 200

    def test_all_protected_endpoints_require_token(self, static_client: TestClient):
        """Spot-check that every protected endpoint returns 401 without a token."""
        endpoints = [
            ("GET",    "/api/v1/bots?client_id=test"),
            ("POST",   "/api/v1/bots?client_id=test"),
            ("POST",   "/api/v1/bots/some-bot/run"),
            ("POST",   "/api/v1/bots/some-bot/stop"),
            ("DELETE", "/api/v1/bots/some-bot"),
            ("GET",    "/api/v1/bots/some-bot/orders"),
            ("GET",    "/api/v1/bots/some-bot/trades"),
            ("GET",    "/api/v1/parameters/defaults"),
            ("GET",    "/api/v1/parameters?client_id=test"),
            ("PUT",    "/api/v1/parameters?client_id=test"),
            ("GET",    "/api/v1/indicators/defaults"),
            ("GET",    "/api/v1/indicators?client_id=test"),
            ("PUT",    "/api/v1/indicators?client_id=test"),
        ]
        for method, path in endpoints:
            response = static_client.request(method, path)
            assert response.status_code == 401, (
                f"{method} {path} expected 401, got {response.status_code}"
            )


# ---------------------------------------------------------------------------
# 3. verify_token unit tests
# ---------------------------------------------------------------------------

class TestVerifyToken:
    """Unit tests for core/security.py:verify_token."""

    def _clear(self):
        from src.core.config import get_settings
        get_settings.cache_clear()

    def test_dev_mode_none_token_passes(self):
        from src.core.security import verify_token
        with patch("src.core.security.get_settings") as mock:
            mock.return_value.netlify_site_url = ""
            mock.return_value.sonarft_api_token = ""
            verify_token(None)  # must not raise

    def test_dev_mode_any_token_passes(self):
        from src.core.security import verify_token
        with patch("src.core.security.get_settings") as mock:
            mock.return_value.netlify_site_url = ""
            mock.return_value.sonarft_api_token = ""
            verify_token("anything")  # must not raise

    def test_static_token_correct_passes(self):

        from src.core.security import verify_token
        with patch("src.core.security.get_settings") as mock:
            mock.return_value.netlify_site_url = ""
            mock.return_value.sonarft_api_token = "my-secret"
            verify_token("my-secret")  # must not raise

    def test_static_token_wrong_raises_401(self):
        from fastapi import HTTPException
        from src.core.security import verify_token
        with patch("src.core.security.get_settings") as mock:
            mock.return_value.netlify_site_url = ""
            mock.return_value.sonarft_api_token = "my-secret"
            with pytest.raises(HTTPException) as exc_info:
                verify_token("wrong")
            assert exc_info.value.status_code == 401

    def test_missing_token_with_static_auth_raises_401(self):
        from fastapi import HTTPException
        from src.core.security import verify_token
        with patch("src.core.security.get_settings") as mock:
            mock.return_value.netlify_site_url = ""
            mock.return_value.sonarft_api_token = "my-secret"
            with pytest.raises(HTTPException) as exc_info:
                verify_token(None)
            assert exc_info.value.status_code == 401

    def test_missing_token_with_netlify_raises_401(self):
        from fastapi import HTTPException
        from src.core.security import verify_token
        with patch("src.core.security.get_settings") as mock:
            mock.return_value.netlify_site_url = "https://example.netlify.app"
            mock.return_value.sonarft_api_token = ""
            with pytest.raises(HTTPException) as exc_info:
                verify_token(None)
            assert exc_info.value.status_code == 401

    def test_invalid_jwt_raises_401(self):
        from fastapi import HTTPException
        from src.core.security import verify_token
        with patch("src.core.security.get_settings") as mock, \
             patch("src.core.security._get_jwks_client") as jwks_mock:
            mock.return_value.netlify_site_url = "https://example.netlify.app"
            mock.return_value.sonarft_api_token = ""
            from jwt import InvalidTokenError
            jwks_client = MagicMock()
            jwks_client.get_signing_key_from_jwt.side_effect = InvalidTokenError("bad token")
            jwks_mock.return_value = jwks_client
            with pytest.raises(HTTPException) as exc_info:
                verify_token("not.a.valid.jwt")
            assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 4. Input validation — botid regex
# ---------------------------------------------------------------------------

class TestBotIdValidation:
    """botid path parameter must match ^[a-zA-Z0-9_-]{1,64}$."""

    VALID_BOTIDS = [
        "abc123",
        "bot-001",
        "bot_001",
        "a" * 64,
        "ABC-xyz_123",
    ]
    INVALID_BOTIDS = [
        "../etc/passwd",
        "bot/evil",
        "bot evil",
        "",
        "a" * 65,
        "bot;drop",
        "bot<script>",
    ]

    @pytest.mark.parametrize("botid", VALID_BOTIDS)
    def test_valid_botid_accepted(self, client: TestClient, mock_bot_service, auth_headers, botid):
        """Valid botids must not be rejected with 422 (pattern mismatch).
        400 = client_id missing (expected in tests without client_id param).
        200/404/500 = reached the handler.
        """
        response = client.post(f"/api/v1/bots/{botid}/run?client_id=test", headers=auth_headers)
        assert response.status_code in (200, 400, 404, 500), (
            f"botid={botid!r} got unexpected {response.status_code}"
        )

    @pytest.mark.parametrize("botid", INVALID_BOTIDS)
    def test_invalid_botid_rejected(self, client: TestClient, auth_headers, botid):
        """Invalid botids must never reach the handler.
        - 422: FastAPI pattern validation rejected it
        - 404: HTTP router consumed path segments (e.g. '/' in botid) before validation
        - 400: client_id missing (get_client_id dependency fires before botid validation)
        All outcomes mean the handler was never called with the bad input.
        """
        response = client.post(f"/api/v1/bots/{botid}/run", headers=auth_headers)
        assert response.status_code in (400, 404, 422), (
            f"botid={botid!r} expected 400/404/422, got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# 5. Input validation — client_id path traversal
# ---------------------------------------------------------------------------

class TestClientIdSanitization:
    """client_id must be sanitized before use in file paths."""

    TRAVERSAL_ATTEMPTS = [
        "../../etc/passwd",
        "../config",
        "foo/bar",
        "foo bar",
        "",
        "a" * 65,
        "foo;bar",
    ]

    # __proto__ matches the safe regex (alphanumeric + underscore) — it is not
    # a path traversal risk and correctly reaches the service layer (404 = file not found).
    PROTO_POLLUTION_ATTEMPTS = ["__proto__"]

    @pytest.mark.parametrize("client_id", TRAVERSAL_ATTEMPTS)
    def test_traversal_client_id_returns_400_or_422(
        self, client: TestClient, auth_headers, client_id
    ):
        """Malicious client_id must never reach the filesystem."""
        response = client.get(
            f"/api/v1/parameters?client_id={client_id}",
            headers=auth_headers,
        )
        assert response.status_code in (400, 422), (
            f"client_id={client_id!r} expected 400/422, got {response.status_code}"
        )

    @pytest.mark.parametrize("client_id", PROTO_POLLUTION_ATTEMPTS)
    def test_proto_client_id_reaches_service_not_filesystem(
        self, client: TestClient, auth_headers, client_id
    ):
        """__proto__ is a valid identifier — sanitizer passes it, service returns 404
        (config file not found), not a filesystem error."""
        response = client.get(
            f"/api/v1/parameters?client_id={client_id}",
            headers=auth_headers,
        )
        # 404 = sanitizer passed, config file not found (correct)
        # 400 = sanitizer rejected (also acceptable if policy tightened)
        assert response.status_code in (400, 404)

    def test_valid_client_id_passes_sanitizer(
        self, client: TestClient, auth_headers
    ):
        """A well-formed client_id must reach the service layer (returns 404 = file not found,
        not 400/500 = sanitizer/server error). This confirms the sanitizer passed it through."""
        response = client.get(
            "/api/v1/parameters?client_id=valid-client-01",
            headers=auth_headers,
        )
        # 404 = sanitizer passed, config file not found in test env (correct)
        # 200 = mock intercepted (also correct)
        assert response.status_code in (200, 404)
