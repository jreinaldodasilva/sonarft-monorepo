"""
SonarFT Metrics Module
Structured JSON event emission for all observability categories.
"""
import json
import logging
import time as _time
from typing import Any

_metrics_logger = logging.getLogger("sonarft.metrics")


def _emit(event_type: str, severity: str, component: str, **fields: Any) -> None:
    """Emit a single structured JSON log record."""
    record = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime()),
        "component": component,
        "event_type": event_type,
        "severity": severity,
        **fields,
    }
    level = getattr(logging, severity, logging.INFO)
    _metrics_logger.log(level, json.dumps(record))


# ── Strategy ──────────────────────────────────────────────────────────────────

def log_signal(
    botid: str,
    symbol: str,
    buy_exchange: str,
    sell_exchange: str,
    signal_type: str,          # "entry" | "skipped"
    decision_reason: str,
    profit: float,
    profit_pct: float,
    rsi_buy: float,
    rsi_sell: float,
    direction_buy: str,
    direction_sell: str,
    weight: float,
    volatility: float,
) -> None:
    _emit(
        "signal",
        "INFO",
        "bot.strategy",
        botid=botid,
        symbol=symbol,
        buy_exchange=buy_exchange,
        sell_exchange=sell_exchange,
        signal_type=signal_type,
        decision_reason=decision_reason,
        expected_profit=profit,
        expected_profit_pct=profit_pct,
        rsi_buy=rsi_buy,
        rsi_sell=rsi_sell,
        direction_buy=direction_buy,
        direction_sell=direction_sell,
        weight=weight,
        volatility=volatility,
    )


# ── Execution ─────────────────────────────────────────────────────────────────

def log_order(
    botid: str,
    order_id: str,
    symbol: str,
    exchange: str,
    side: str,
    requested_price: float,
    executed_price: float,
    amount: float,
    slippage: float,
    fill_status: str,          # "full" | "partial" | "failed"
    simulated: bool,
) -> None:
    _emit(
        "order_execution",
        "INFO",
        "bot.execution",
        botid=botid,
        order_id=order_id,
        symbol=symbol,
        exchange=exchange,
        side=side,
        requested_price=requested_price,
        executed_price=executed_price,
        amount=amount,
        slippage_pct=round(slippage * 100, 6),
        fill_status=fill_status,
        simulated=simulated,
    )


def log_trade_result(
    botid: str,
    symbol: str,
    buy_exchange: str,
    sell_exchange: str,
    position: str,
    buy_order_id: str,
    sell_order_id: str,
    buy_price: float,
    sell_price: float,
    amount: float,
    profit: float,
    profit_pct: float,
    success: bool,
) -> None:
    severity = "INFO" if success else "WARNING"
    _emit(
        "trade_result",
        severity,
        "bot.execution",
        botid=botid,
        symbol=symbol,
        buy_exchange=buy_exchange,
        sell_exchange=sell_exchange,
        position=position,
        buy_order_id=buy_order_id,
        sell_order_id=sell_order_id,
        buy_price=buy_price,
        sell_price=sell_price,
        amount=amount,
        realized_profit=profit,
        realized_profit_pct=profit_pct,
        success=success,
    )


# ── Risk ──────────────────────────────────────────────────────────────────────

def log_risk_event(
    botid: str,
    event: str,               # "daily_loss_limit" | "rate_limit" | "size_limit" | "flash_crash" | "liquidity_fail"
    detail: str,
    daily_loss: float = 0.0,
    max_daily_loss: float = 0.0,
) -> None:
    _emit(
        "risk_event",
        "WARNING",
        "bot.risk",
        botid=botid,
        risk_event=event,
        detail=detail,
        daily_loss_accumulated=daily_loss,
        max_daily_loss=max_daily_loss,
    )


# ── Liquidity validation ───────────────────────────────────────────────────────

def log_liquidity_check(
    botid: str,
    symbol: str,
    exchange: str,
    side: str,
    required_amount: float,
    available_depth: float,
    passed: bool,
) -> None:
    severity = "DEBUG" if passed else "WARNING"
    _emit(
        "liquidity_check",
        severity,
        "bot.validator",
        botid=botid,
        symbol=symbol,
        exchange=exchange,
        side=side,
        required_amount=required_amount,
        available_depth=available_depth,
        passed=passed,
    )


# ── API ───────────────────────────────────────────────────────────────────────

def log_api_call(
    exchange: str,
    method: str,
    latency_ms: float,
    success: bool,
    error: str = "",
) -> None:
    severity = "DEBUG" if success else "WARNING"
    _emit(
        "api_call",
        severity,
        "bot.api",
        exchange=exchange,
        method=method,
        latency_ms=round(latency_ms, 2),
        success=success,
        error=error,
    )


# ── System health ─────────────────────────────────────────────────────────────

def log_cycle(
    botid: str,
    cycle_ms: float,
    trades_found: int,
    trades_skipped: int,
) -> None:
    _emit(
        "cycle",
        "DEBUG",
        "bot.search",
        botid=botid,
        cycle_duration_ms=round(cycle_ms, 2),
        trades_found=trades_found,
        trades_skipped=trades_skipped,
    )


def log_session_pnl(
    botid: str,
    session_trades: int,
    session_profit: float,
    daily_loss: float,
) -> None:
    _emit(
        "session_pnl",
        "INFO",
        "bot.risk",
        botid=botid,
        session_trades=session_trades,
        session_profit=session_profit,
        daily_loss_accumulated=daily_loss,
    )
