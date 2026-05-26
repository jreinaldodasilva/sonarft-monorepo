"""
SonarFT Bot Configuration Module

BotConfig dataclass and load_bot_config() function extracted from SonarftBot
(T30). Separating config loading from the bot lifecycle makes configuration
independently testable and reduces SonarftBot's responsibilities.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from config_schemas import FeeConfig, ParametersConfig, SymbolConfig
from paths import bot_path

_VALID_INDICATORS = frozenset({'rsi', 'stoch rsi', 'macd', 'sma', 'ema'})


class BotCreationError(Exception):
    """Raised when bot configuration cannot be loaded or is invalid."""

    def __init__(self, message: str = "Failed to create the bot.") -> None:
        self.message = message
        super().__init__(self.message)


@dataclass
class BotConfig:
    """All configuration values loaded from JSON files for one bot instance.

    Produced by load_bot_config() and consumed by SonarftBot.create_bot().
    Keeping config data in a plain dataclass makes it independently testable
    and serialisable without instantiating a full SonarftBot.
    """
    # Market
    market: list

    # Trading parameters
    strategy: str
    profit_percentage_threshold: float
    trade_amount: float
    is_simulating_trade: int
    max_daily_loss: float
    max_trade_amount: float
    max_orders_per_minute: int
    spread_increase_factor: float
    spread_decrease_factor: float
    slippage_buffer: float
    flash_crash_threshold: float
    max_daily_trades: int
    max_total_exposure: float

    # Symbols, exchanges, fees, indicators
    symbols: list
    exchanges: list
    exchanges_fees: list
    active_indicators: list


def _load_config_section(pathname: str, key: str):
    """Generic JSON config loader: opens pathname and returns data[key]."""
    if not os.path.isabs(pathname):
        pathname = bot_path(pathname)
    try:
        with open(pathname) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise BotCreationError(f"Configuration file not found: {pathname}") from None
    except json.JSONDecodeError as e:
        raise BotCreationError(f"Invalid JSON in {pathname}: {e}") from e
    if key not in data:
        raise BotCreationError(f"Configuration key '{key}' not found in {pathname}")
    return data[key]


def load_bot_config(config_setup: str = "config_1") -> BotConfig:
    """Load and validate all configuration sections for one bot instance.

    Reads config.json to locate per-section files, then loads and validates
    each section using Pydantic models. Raises BotCreationError with a clear
    message on any missing file, invalid JSON, or validation failure.

    This function is synchronous and safe to call from asyncio.to_thread().
    """
    config = _load_config_section(
        bot_path("sonarftdata", "config.json"), config_setup
    )[0]

    market = _load_config_section(
        config["markets_pathname"], f"market_{config['markets_setup']}"
    )

    parameters_raw = _load_config_section(
        config["parameters_pathname"], f"parameters_{config['parameters_setup']}"
    )[0]
    try:
        parameters = ParametersConfig(**parameters_raw)
    except Exception as e:
        raise BotCreationError(f"Invalid trading parameters: {e}") from e

    symbols_raw = _load_config_section(
        config["symbols_pathname"], f"symbols_{config['symbols_setup']}"
    )
    try:
        symbols = [SymbolConfig(**s).model_dump() for s in symbols_raw]
    except Exception as e:
        raise BotCreationError(f"Invalid symbols configuration: {e}") from e
    if not symbols:
        raise BotCreationError("symbols list must not be empty")

    exchanges_raw = _load_config_section(
        config["exchanges_pathname"], f"exchanges_{config['exchanges_setup']}"
    )
    if not exchanges_raw:
        raise BotCreationError("exchanges list must not be empty")

    # Validate exchange names against ccxt registry
    try:
        import ccxt as _ccxt
        valid_exchanges = set(_ccxt.exchanges)
        unknown = [e for e in exchanges_raw if e not in valid_exchanges]
        if unknown:
            raise BotCreationError(
                f"Unknown exchange(s) in config: {unknown}. "
                f"Check spelling against ccxt.exchanges."
            )
    except ImportError:
        pass  # ccxt unavailable — skip validation

    fees_raw = _load_config_section(
        config["fees_pathname"], f"exchanges_fees_{config['fees_setup']}"
    )
    try:
        exchanges_fees = [FeeConfig(**f).model_dump(exclude_none=True) for f in fees_raw]
    except Exception as e:
        raise BotCreationError(f"Invalid fees configuration: {e}") from e

    active_indicators = _load_config_section(
        config["indicators_pathname"], f"indicators_{config['indicators_setup']}"
    )
    unknown_indicators = [
        ind for ind in active_indicators
        if ind.lower() not in _VALID_INDICATORS
    ]
    if unknown_indicators:
        raise BotCreationError(
            f"Unknown indicator(s) in config: {unknown_indicators}. "
            f"Valid values: {sorted(_VALID_INDICATORS)}"
        )

    return BotConfig(
        market=market,
        strategy=parameters.strategy,
        profit_percentage_threshold=parameters.profit_percentage_threshold,
        trade_amount=parameters.trade_amount,
        is_simulating_trade=parameters.is_simulating_trade,
        max_daily_loss=parameters.max_daily_loss,
        max_trade_amount=parameters.max_trade_amount,
        max_orders_per_minute=parameters.max_orders_per_minute,
        spread_increase_factor=parameters.spread_increase_factor,
        spread_decrease_factor=parameters.spread_decrease_factor,
        slippage_buffer=parameters.slippage_buffer,
        flash_crash_threshold=parameters.flash_crash_threshold,
        max_daily_trades=parameters.max_daily_trades,
        max_total_exposure=parameters.max_total_exposure,
        symbols=symbols,
        exchanges=exchanges_raw,
        exchanges_fees=exchanges_fees,
        active_indicators=active_indicators,
    )
