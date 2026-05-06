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

from ..core.config import get_settings
from ..core.errors import ConfigNotFoundError, ConfigWriteError
from ..models.schemas import IndicatorsConfig, ParametersConfig

_logger = logging.getLogger(__name__)

# Allowlist: alphanumeric, hyphens, underscores, 1–64 chars
_SAFE_CLIENT_ID = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


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

    # ### Parameters ###

    async def get_default_parameters(self) -> ParametersConfig:
        path = _default_path(self._data_dir, "parameters.json")
        try:
            data = await asyncio.to_thread(_read_json, path)
        except FileNotFoundError:
            raise ConfigNotFoundError("Default parameters file not found") from None
        except Exception as exc:
            _logger.exception("Failed to read default parameters: %s", exc)
            raise ConfigWriteError("Failed to read default parameters") from exc
        return ParametersConfig(**data)

    async def get_parameters(self, client_id: str) -> ParametersConfig:
        path = _client_path(self._data_dir, client_id, "parameters")
        try:
            data = await asyncio.to_thread(_read_json, path)
        except FileNotFoundError:
            raise ConfigNotFoundError(f"Parameters not found for client: {client_id}") from None
        except Exception as exc:
            _logger.exception("Failed to read parameters for %s: %s", client_id, exc)
            raise ConfigWriteError("Failed to read parameters") from exc
        return ParametersConfig(**data)

    async def update_parameters(self, client_id: str, config: ParametersConfig) -> None:
        path = _client_path(self._data_dir, client_id, "parameters")
        try:
            await asyncio.to_thread(_write_json, path, config.model_dump())
        except Exception as exc:
            _logger.exception("Failed to write parameters for %s: %s", client_id, exc)
            raise ConfigWriteError("Failed to write parameters") from exc

    # ### Indicators ###

    async def get_default_indicators(self) -> IndicatorsConfig:
        path = _default_path(self._data_dir, "indicators.json")
        try:
            data = await asyncio.to_thread(_read_json, path)
        except FileNotFoundError:
            raise ConfigNotFoundError("Default indicators file not found") from None
        except Exception as exc:
            _logger.exception("Failed to read default indicators: %s", exc)
            raise ConfigWriteError("Failed to read default indicators") from exc
        return IndicatorsConfig(**data)

    async def get_indicators(self, client_id: str) -> IndicatorsConfig:
        path = _client_path(self._data_dir, client_id, "indicators")
        try:
            data = await asyncio.to_thread(_read_json, path)
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
    Falls back to the lru_cache singleton if app.state is not populated.
    """
    service = getattr(request.app.state, "config_service", None)
    if service is None:
        return get_config_service()
    return service
