"""
SonarFT Config Service
Handles reading and writing parameters and indicators configuration.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, Request

from ..core.config import ID_PATTERN, get_settings
from ..core.errors import ConfigNotFoundError, ConfigWriteError
from ..models.schemas import ClientParametersConfig, IndicatorsConfig

_logger = logging.getLogger(__name__)

# Allowlist: alphanumeric, hyphens, underscores, 1–64 chars — from core/config.py
_SAFE_CLIENT_ID = re.compile(ID_PATTERN)


def _validate_client_id(client_id: str) -> str:
    """Raise HTTP 400 if client_id contains unsafe characters."""
    if not _SAFE_CLIENT_ID.match(client_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid client_id: {client_id!r}",
        )
    return client_id


def _client_path(data_dir: str, client_id: str, suffix: str) -> str:
    """Build a safe, validated config file path for a client.
    Resolves the final path and confirms it stays within data_dir/config/
    to prevent path traversal via symlinks or encoded sequences.
    """
    _validate_client_id(client_id)
    base = Path(data_dir).resolve() / "config"
    target = (base / f"{client_id}_{suffix}.json").resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Invalid client_id")
    return str(target)


def _default_path(data_dir: str, filename: str) -> str:
    return str(Path(data_dir) / "config" / filename)


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: dict) -> None:
    """Atomic write: write to a temp file then rename to avoid partial reads."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    dir_name = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=dir_name, delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=4)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


class ConfigService:
    def __init__(self) -> None:
        self._data_dir = get_settings().data_dir
        self._cache: dict[str, tuple[float, dict]] = {}

    @property
    def _json_cache(self) -> dict[str, tuple[float, dict]]:
        """Lazy cache initialisation — safe when __new__ is used without __init__."""
        if not hasattr(self, "_cache"):
            self._cache = {}
        return self._cache

    def _read_json_cached(self, path: str) -> dict:
        """Return cached JSON if the file mtime is unchanged; otherwise re-read.
        Runs synchronously — always call via asyncio.to_thread.
        """
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            raise FileNotFoundError(path) from None
        cached = self._json_cache.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        data = _read_json(path)
        self._json_cache[path] = (mtime, data)
        return data

    def _invalidate_cache(self, path: str) -> None:
        """Remove a path from the cache after a write."""
        self._json_cache.pop(path, None)

    # ### Parameters ###

    async def get_default_parameters(self) -> ClientParametersConfig:
        path = _default_path(self._data_dir, "parameters.json")
        try:
            data = await asyncio.to_thread(self._read_json_cached, path)
        except FileNotFoundError:
            raise ConfigNotFoundError("Default parameters file not found") from None
        except Exception as exc:
            _logger.exception("Failed to read default parameters: %s", exc)
            raise ConfigWriteError("Failed to read default parameters") from exc
        return ClientParametersConfig(**data)

    async def get_parameters(self, client_id: str) -> ClientParametersConfig:
        path = _client_path(self._data_dir, client_id, "parameters")
        try:
            data = await asyncio.to_thread(self._read_json_cached, path)
        except FileNotFoundError:
            raise ConfigNotFoundError(f"Parameters not found for client: {client_id}") from None
        except Exception as exc:
            _logger.exception("Failed to read parameters for %s: %s", client_id, exc)
            raise ConfigWriteError("Failed to read parameters") from exc
        return ClientParametersConfig(**data)

    async def update_parameters(self, client_id: str, config: ClientParametersConfig) -> None:
        path = _client_path(self._data_dir, client_id, "parameters")
        try:
            await asyncio.to_thread(_write_json, path, config.model_dump())
            self._invalidate_cache(path)
        except Exception as exc:
            _logger.exception("Failed to write parameters for %s: %s", client_id, exc)
            raise ConfigWriteError("Failed to write parameters") from exc

    # ### Indicators ###

    async def get_default_indicators(self) -> IndicatorsConfig:
        path = _default_path(self._data_dir, "indicators.json")
        try:
            data = await asyncio.to_thread(self._read_json_cached, path)
        except FileNotFoundError:
            raise ConfigNotFoundError("Default indicators file not found") from None
        except Exception as exc:
            _logger.exception("Failed to read default indicators: %s", exc)
            raise ConfigWriteError("Failed to read default indicators") from exc
        return IndicatorsConfig(**data)

    async def get_indicators(self, client_id: str) -> IndicatorsConfig:
        path = _client_path(self._data_dir, client_id, "indicators")
        try:
            data = await asyncio.to_thread(self._read_json_cached, path)
        except FileNotFoundError:
            raise ConfigNotFoundError(f"Indicators not found for client: {client_id}") from None
        except Exception as exc:
            _logger.exception("Failed to read indicators for %s: %s", client_id, exc)
            raise ConfigWriteError("Failed to read indicators") from exc
        return IndicatorsConfig(**data)

    async def update_indicators(self, client_id: str, config: IndicatorsConfig) -> None:
        path = _client_path(self._data_dir, client_id, "indicators")
        try:
            await asyncio.to_thread(_write_json, path, config.model_dump())
            self._invalidate_cache(path)
        except Exception as exc:
            _logger.exception("Failed to write indicators for %s: %s", client_id, exc)
            raise ConfigWriteError("Failed to write indicators") from exc


@lru_cache
def get_config_service() -> ConfigService:
    """Fallback singleton — used by tests and when app.state is unavailable."""
    return ConfigService()


def get_config_service_from_state(request: Request) -> ConfigService:
    """
    FastAPI dependency — reads ConfigService from app.state (set by lifespan).
    Returns 503 Service Unavailable if the service failed to initialise.
    Falls back to the lru_cache singleton if app.state is not populated.
    """
    service = getattr(request.app.state, "config_service", None)
    if service is None:
        try:
            return get_config_service()
        except Exception:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Config service unavailable — check server logs",
                headers={"Retry-After": "30"},
            ) from None
    return service
