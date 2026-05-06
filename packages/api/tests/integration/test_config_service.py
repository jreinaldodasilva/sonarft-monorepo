"""
ConfigService integration tests — real filesystem, no mocks.

Uses pytest's tmp_path fixture to create an isolated sonarftdata/config/
directory for each test. Exercises the full read/write/validate cycle
including atomic writes, path traversal guard, and Pydantic round-trip.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.errors import ConfigNotFoundError, ConfigWriteError
from src.models.schemas import IndicatorsConfig, ParametersConfig
from src.services.config_service import ConfigService

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def config_service(tmp_path: Path) -> ConfigService:
    """Return a ConfigService wired to a temporary data directory."""
    (tmp_path / "config").mkdir()
    svc = ConfigService.__new__(ConfigService)
    svc._data_dir = str(tmp_path)
    return svc


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Parameters — read/write round-trip
# ---------------------------------------------------------------------------

class TestParametersRoundTrip:

    @pytest.mark.asyncio
    async def test_update_then_get_parameters(
        self, config_service: ConfigService, tmp_path: Path
    ):
        config = ParametersConfig(
            exchanges={"Binance": True, "OKX": False},
            symbols={"BTC/USDT": True},
            strategy="arbitrage",
        )
        await config_service.update_parameters("test-client", config)
        result = await config_service.get_parameters("test-client")
        assert result.exchanges == {"Binance": True, "OKX": False}
        assert result.symbols == {"BTC/USDT": True}
        assert result.strategy == "arbitrage"

    @pytest.mark.asyncio
    async def test_update_overwrites_existing(
        self, config_service: ConfigService
    ):
        first = ParametersConfig(exchanges={"Binance": True}, symbols={})
        await config_service.update_parameters("client-a", first)

        second = ParametersConfig(exchanges={"OKX": True}, symbols={"ETH/USDT": True})
        await config_service.update_parameters("client-a", second)

        result = await config_service.get_parameters("client-a")
        assert result.exchanges == {"OKX": True}
        assert result.symbols == {"ETH/USDT": True}

    @pytest.mark.asyncio
    async def test_file_written_as_valid_json(
        self, config_service: ConfigService, tmp_path: Path
    ):
        config = ParametersConfig(exchanges={"Binance": True}, symbols={})
        await config_service.update_parameters("test-client", config)

        path = tmp_path / "config" / "test-client_parameters.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["exchanges"] == {"Binance": True}

    @pytest.mark.asyncio
    async def test_multiple_clients_isolated(
        self, config_service: ConfigService
    ):
        await config_service.update_parameters(
            "alice", ParametersConfig(exchanges={"Binance": True}, symbols={})
        )
        await config_service.update_parameters(
            "bob", ParametersConfig(exchanges={"OKX": True}, symbols={})
        )
        alice = await config_service.get_parameters("alice")
        bob = await config_service.get_parameters("bob")
        assert alice.exchanges == {"Binance": True}
        assert bob.exchanges == {"OKX": True}


# ---------------------------------------------------------------------------
# 2. Parameters — error cases
# ---------------------------------------------------------------------------

class TestParametersErrors:

    @pytest.mark.asyncio
    async def test_get_missing_parameters_raises_config_not_found(
        self, config_service: ConfigService
    ):
        with pytest.raises(ConfigNotFoundError):
            await config_service.get_parameters("nonexistent-client")

    @pytest.mark.asyncio
    async def test_get_default_parameters_missing_raises_config_not_found(
        self, config_service: ConfigService
    ):
        with pytest.raises(ConfigNotFoundError):
            await config_service.get_default_parameters()

    @pytest.mark.asyncio
    async def test_get_default_parameters_reads_file(
        self, config_service: ConfigService, tmp_path: Path
    ):
        defaults = {"exchanges": {"Binance": True}, "symbols": {}, "strategy": "arbitrage"}
        _write_json(tmp_path / "config" / "parameters.json", defaults)
        result = await config_service.get_default_parameters()
        assert result.exchanges == {"Binance": True}

    @pytest.mark.asyncio
    async def test_corrupt_json_raises_config_write_error(
        self, config_service: ConfigService, tmp_path: Path
    ):
        path = tmp_path / "config" / "bad-client_parameters.json"
        path.write_text("{ not valid json", encoding="utf-8")
        with pytest.raises(ConfigWriteError):
            await config_service.get_parameters("bad-client")


# ---------------------------------------------------------------------------
# 3. Indicators — read/write round-trip
# ---------------------------------------------------------------------------

class TestIndicatorsRoundTrip:

    @pytest.mark.asyncio
    async def test_update_then_get_indicators(
        self, config_service: ConfigService
    ):
        config = IndicatorsConfig(
            periods={"5min": True, "15min": False},
            oscillators={"Relative Strength Index (14)": True},
            movingaverages={"Exponential Moving Average (10)": True},
        )
        await config_service.update_indicators("test-client", config)
        result = await config_service.get_indicators("test-client")
        assert result.periods == {"5min": True, "15min": False}
        assert result.oscillators == {"Relative Strength Index (14)": True}
        assert result.movingaverages == {"Exponential Moving Average (10)": True}

    @pytest.mark.asyncio
    async def test_get_missing_indicators_raises_config_not_found(
        self, config_service: ConfigService
    ):
        with pytest.raises(ConfigNotFoundError):
            await config_service.get_indicators("nonexistent-client")

    @pytest.mark.asyncio
    async def test_get_default_indicators_reads_file(
        self, config_service: ConfigService, tmp_path: Path
    ):
        defaults = {
            "periods": {"5min": True},
            "oscillators": {},
            "movingaverages": {},
        }
        _write_json(tmp_path / "config" / "indicators.json", defaults)
        result = await config_service.get_default_indicators()
        assert result.periods == {"5min": True}

    @pytest.mark.asyncio
    async def test_get_default_indicators_missing_raises_config_not_found(
        self, config_service: ConfigService
    ):
        with pytest.raises(ConfigNotFoundError):
            await config_service.get_default_indicators()


# ---------------------------------------------------------------------------
# 4. Atomic write — partial-read safety
# ---------------------------------------------------------------------------

class TestAtomicWrite:

    @pytest.mark.asyncio
    async def test_no_tmp_file_left_after_write(
        self, config_service: ConfigService, tmp_path: Path
    ):
        """Atomic write must not leave .tmp files behind."""
        config = ParametersConfig(exchanges={"Binance": True}, symbols={})
        await config_service.update_parameters("test-client", config)

        tmp_files = list((tmp_path / "config").glob("*.tmp"))
        assert tmp_files == [], f"Unexpected .tmp files: {tmp_files}"

    @pytest.mark.asyncio
    async def test_final_file_is_valid_json_after_write(
        self, config_service: ConfigService, tmp_path: Path
    ):
        config = ParametersConfig(exchanges={"Binance": True}, symbols={})
        await config_service.update_parameters("test-client", config)

        path = tmp_path / "config" / "test-client_parameters.json"
        data = json.loads(path.read_text())
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# 5. Path traversal guard
# ---------------------------------------------------------------------------

class TestPathTraversalGuard:

    @pytest.mark.asyncio
    async def test_traversal_client_id_raises_400(
        self, config_service: ConfigService
    ):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await config_service.get_parameters("../../etc/passwd")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_slash_in_client_id_raises_400(
        self, config_service: ConfigService
    ):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await config_service.get_parameters("foo/bar")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_space_in_client_id_raises_400(
        self, config_service: ConfigService
    ):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await config_service.get_parameters("foo bar")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_client_id_passes_guard(
        self, config_service: ConfigService
    ):
        # A valid client_id must reach the filesystem (ConfigNotFoundError = file not found, not 400)
        with pytest.raises(ConfigNotFoundError):
            await config_service.get_parameters("valid-client-01")

    @pytest.mark.asyncio
    async def test_write_traversal_client_id_raises_400(
        self, config_service: ConfigService
    ):
        from fastapi import HTTPException
        config = ParametersConfig(exchanges={}, symbols={})
        with pytest.raises(HTTPException) as exc_info:
            await config_service.update_parameters("../../evil", config)
        assert exc_info.value.status_code == 400
