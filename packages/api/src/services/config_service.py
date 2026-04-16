"""
SonarFT Config Service
Handles reading and writing parameters and indicators configuration.
"""
from __future__ import annotations
import asyncio
import json
import os
from functools import lru_cache
from pathlib import Path

from ..core.config import get_settings
from ..models.schemas import ParametersConfig, IndicatorsConfig


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


class ConfigService:
    def __init__(self) -> None:
        self._data_dir = get_settings().data_dir

    # ### Parameters ###

    async def get_default_parameters(self) -> ParametersConfig:
        path = f"{self._data_dir}/config/parameters.json"
        data = await asyncio.to_thread(_read_json, path)
        return ParametersConfig(**data)

    async def get_parameters(self, client_id: str) -> ParametersConfig:
        path = f"{self._data_dir}/config/{client_id}_parameters.json"
        data = await asyncio.to_thread(_read_json, path)
        return ParametersConfig(**data)

    async def update_parameters(self, client_id: str, config: ParametersConfig) -> None:
        path = f"{self._data_dir}/config/{client_id}_parameters.json"
        await asyncio.to_thread(_write_json, path, config.model_dump())

    # ### Indicators ###

    async def get_default_indicators(self) -> IndicatorsConfig:
        path = f"{self._data_dir}/config/indicators.json"
        data = await asyncio.to_thread(_read_json, path)
        return IndicatorsConfig(**data)

    async def get_indicators(self, client_id: str) -> IndicatorsConfig:
        path = f"{self._data_dir}/config/{client_id}_indicators.json"
        data = await asyncio.to_thread(_read_json, path)
        return IndicatorsConfig(**data)

    async def update_indicators(self, client_id: str, config: IndicatorsConfig) -> None:
        path = f"{self._data_dir}/config/{client_id}_indicators.json"
        await asyncio.to_thread(_write_json, path, config.model_dump())


@lru_cache
def get_config_service() -> ConfigService:
    return ConfigService()
