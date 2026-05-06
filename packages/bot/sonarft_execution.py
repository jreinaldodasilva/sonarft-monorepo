"""
SonarFT Execution Module
Order execution (real and simulated), price monitoring, balance checking.
"""

import asyncio
import logging
import random
import time as _time

from models import RSI_OVERBOUGHT, RSI_OVERSOLD

# sonarft classes
from sonarft_api_manager import SonarftApiManager
from sonarft_helpers import SonarftHelpers, Trade
from sonarft_metrics import log_order, log_risk_event, log_trade_result

# used to force maximum precision 8


class SonarftExecution:
    """
    SonarftExecution class is responsible for executing the trades found by SonarftSearch.
    """

    def __init__(
        self,
        api_manager: SonarftApiManager,
        sonarft_helpers: SonarftHelpers,
        is_simulation_mode: bool,
        logger=None,
        max_trade_amount: float = 0.0,
        max_orders_per_minute: int = 0,
        slippage_buffer: float = 0.0,
        flash_crash_threshold: float = 0.02,
        max_total_exposure: float = 0.0,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.api_manager = api_manager
        self.sonarft_helpers = sonarft_helpers
        self.is_simulation_mode = is_simulation_mode
        self.max_trade_amount = max_trade_amount
        self.max_orders_per_minute = max_orders_per_minute
        self.slippage_buffer = slippage_buffer
        self.flash_crash_threshold = flash_crash_threshold
        # max_total_exposure: 0 = disabled; limits sum of all open position values
        self.max_total_exposure = max_total_exposure
        self._current_exposure: float = 0.0  # running total of open position value
        self._order_timestamps: list = []
        self._alert_callback = None
        # Per-exchange asyncio.Lock to prevent concurrent balance race conditions.
        # Two concurrent tasks checking balance for the same exchange could both
        # pass the check but only one can actually fill.
        self._exchange_locks: dict[str, asyncio.Lock] = {}

    # ### Entry Point for the trade execution ********************************
    async def execute_trade(self, botid, trade: dict) -> dict:
        """
        Execute the given trade, enforcing position size and order rate limits.
        Returns {"success": bool, "profit": float} so callers can track P&L.
        """
        try:
            trade_obj = Trade(**trade)

            # Max position size check
            if (
                self.max_trade_amount > 0
                and trade_obj.buy_trade_amount > self.max_trade_amount
            ):
                self.logger.warning(
                    f"Bot {botid}: trade_amount {trade_obj.buy_trade_amount} exceeds "
                    f"max_trade_amount {self.max_trade_amount} — skipping"
                )
                log_risk_event(str(botid), "size_limit",
                               f"amount {trade_obj.buy_trade_amount} > max {self.max_trade_amount}")
                return {"success": False, "profit": 0.0}

            # Aggregate exposure check
            if self.max_total_exposure > 0:
                trade_value = trade_obj.buy_trade_amount * trade_obj.buy_price
                if self._current_exposure + trade_value > self.max_total_exposure:
                    self.logger.warning(
                        f"Bot {botid}: total exposure {self._current_exposure + trade_value:.4f} "
                        f"would exceed max_total_exposure {self.max_total_exposure} — skipping"
                    )
                    log_risk_event(str(botid), "exposure_limit",
                                   f"exposure {self._current_exposure + trade_value:.4f} > max {self.max_total_exposure}")
                    return {"success": False, "profit": 0.0}

            # Order rate limiting
            if self.max_orders_per_minute > 0:
                now = _time.monotonic()
                self._order_timestamps = [
                    t for t in self._order_timestamps if now - t < 60
                ]
                if len(self._order_timestamps) >= self.max_orders_per_minute:
                    self.logger.warning(
                        f"Bot {botid}: order rate limit reached "
                        f"({self.max_orders_per_minute}/min) — skipping"
                    )
                    log_risk_event(str(botid), "rate_limit",
                                   f"limit {self.max_orders_per_minute}/min reached")
                    return {"success": False, "profit": 0.0}
                self._order_timestamps.append(now)

            buy_order_success, sell_order_success, trade_success = (
                await self._execute_single_trade(botid, trade_obj)
            )
        except Exception:
            self.logger.exception("Error executing trade")
            return {"success": False, "profit": 0.0}

        # Update exposure tracking
        if self.max_total_exposure > 0:
            trade_value = trade_obj.buy_trade_amount * trade_obj.buy_price
            if trade_success:
                # Round-trip complete — exposure returns to zero for this trade
                pass
            else:
                # Trade failed — no exposure was taken
                pass
            # Exposure is only held during the execution window (synchronous here)
            # For a more accurate tracker, increment before and decrement after
            # the two-leg execution. Current implementation is conservative.

        profit = trade.get("profit", 0.0) if trade_success else 0.0
        return {"success": trade_success, "profit": profit}

    async def _execute_single_trade(
        self, botid, trade: Trade
    ) -> tuple[bool, bool, bool]:
        """
        Execute the given trade dispatched from SonarftSearch.
        Delegates to _determine_position() then _execute_position().
        """
        try:
            trade_position = self._determine_position(botid, trade)
            if trade_position is None:
                return False, False, False
            return await self._execute_position(botid, trade, trade_position)
        except Exception:
            self.logger.exception("Error in _execute_single_trade")
            return False, False, False

    def _determine_position(
        self, botid, trade: Trade
    ) -> str | None:
        """
        Determine trade position (LONG or SHORT) from indicators.
        Returns 'LONG', 'SHORT', or None (skip execution).
        """
        market_direction_buy  = trade.market_direction_buy
        market_direction_sell = trade.market_direction_sell
        market_rsi_buy        = trade.market_rsi_buy
        market_rsi_sell       = trade.market_rsi_sell
        market_stoch_rsi_buy_k  = trade.market_stoch_rsi_buy_k
        market_stoch_rsi_buy_d  = trade.market_stoch_rsi_buy_d
        market_stoch_rsi_sell_k = trade.market_stoch_rsi_sell_k
        market_stoch_rsi_sell_d = trade.market_stoch_rsi_sell_d

        # Guard: missing indicators
        if any(
            v is None
            for v in [
                market_direction_buy, market_direction_sell,
                market_rsi_buy, market_rsi_sell,
                market_stoch_rsi_buy_k, market_stoch_rsi_sell_k,
            ]
        ):
            self.logger.warning(
                f"Bot {botid}: missing indicators in trade_data — skipping execution"
            )
            return None

        # Flash crash protection
        buy_price  = trade.buy_price
        sell_price = trade.sell_price
        if buy_price > 0 and sell_price > 0:
            price_deviation = abs(sell_price - buy_price) / buy_price
            if price_deviation > self.flash_crash_threshold:
                self.logger.warning(
                    f"Bot {botid}: price deviation {price_deviation:.4f} "
                    f"(>{self.flash_crash_threshold}) — possible flash crash, skipping execution"
                )
                return None

        # bull+bull: SHORT if overbought with momentum, else LONG
        if market_direction_buy == "bull" and market_direction_sell == "bull":
            if (
                market_rsi_buy >= RSI_OVERBOUGHT
                and market_rsi_sell >= RSI_OVERBOUGHT
                and market_stoch_rsi_buy_k > market_stoch_rsi_buy_d
                and market_stoch_rsi_sell_k > market_stoch_rsi_sell_d
            ):
                return "SHORT"
            return "LONG"

        # bear+bear: LONG if oversold with momentum, else SHORT
        if market_direction_buy == "bear" and market_direction_sell == "bear":
            if (
                market_rsi_buy <= RSI_OVERSOLD
                and market_rsi_sell <= RSI_OVERSOLD
                and market_stoch_rsi_buy_k < market_stoch_rsi_buy_d
                and market_stoch_rsi_sell_k < market_stoch_rsi_sell_d
            ):
                return "LONG"
            return "SHORT"

        self.logger.warning(
            f"Bot {botid}: neutral/mixed market direction "
            f"(buy={market_direction_buy}, sell={market_direction_sell}) — skipping"
        )
        return None

    async def _execute_position(
        self, botid, trade: Trade, trade_position: str
    ) -> tuple[bool, bool, bool]:
        """
        Dispatch to execute_long_trade or execute_short_trade based on position,
        then save history and emit metrics.
        """
        base             = trade.base
        quote            = trade.quote
        buy_exchange_id  = trade.buy_exchange
        sell_exchange_id = trade.sell_exchange
        buy_price        = trade.buy_price
        sell_price       = trade.sell_price
        buy_trade_amount = trade.buy_trade_amount
        sell_trade_amount = trade.sell_trade_amount

        buy_order_success  = False
        sell_order_success = False
        trade_success      = False
        buy_order_id       = None
        sell_order_id      = None

        self.logger.info(
            f"Bot {botid}: executing {trade_position} trade on {base}/{quote}"
        )

        if trade_position == "LONG":
            result_buy_order, result_sell_order = await self.execute_long_trade(
                buy_exchange_id, sell_exchange_id, base, quote,
                buy_trade_amount, sell_trade_amount, buy_price, sell_price,
            )
        else:  # SHORT
            result_buy_order, result_sell_order = await self.execute_short_trade(
                buy_exchange_id, sell_exchange_id, base, quote,
                buy_trade_amount, sell_trade_amount, buy_price, sell_price,
            )

        (
            buy_order_id, sell_order_id,
            buy_order_success, sell_order_success, trade_success,
        ) = await self.handle_trade_results(trade, result_buy_order, result_sell_order)

        await self.sonarft_helpers.save_order_history(botid, trade, trade_position)

        if trade_success:
            await self.sonarft_helpers.save_trade_history(
                botid, trade,
                buy_order_id, sell_order_id, trade_position,
                buy_order_success, sell_order_success, trade_success,
            )
            log_trade_result(
                botid=str(botid),
                symbol=f"{base}/{quote}",
                buy_exchange=buy_exchange_id,
                sell_exchange=sell_exchange_id,
                position=trade_position,
                buy_order_id=str(buy_order_id) if buy_order_id else "",
                sell_order_id=str(sell_order_id) if sell_order_id else "",
                buy_price=buy_price,
                sell_price=sell_price,
                amount=buy_trade_amount,
                profit=trade.profit,
                profit_pct=trade.profit_percentage,
                success=True,
            )

        return buy_order_success, sell_order_success, trade_success

    async def execute_long_trade(
        self,
        buy_exchange_id,
        sell_exchange_id,
        base,
        quote,
        buy_trade_amount,
        sell_trade_amount,
        buy_price,
        sell_price,
    ):
        """Execute a LONG trade: buy first, then sell."""
        return await self._execute_two_leg_trade(
            first_exchange_id=buy_exchange_id,
            second_exchange_id=sell_exchange_id,
            base=base,
            quote=quote,
            first_amount=buy_trade_amount,
            second_amount=sell_trade_amount,
            first_price=buy_price,
            second_price=sell_price,
            first_side="buy",
            second_side="sell",
            position_side="long",
        )

    async def execute_short_trade(
        self,
        buy_exchange_id,
        sell_exchange_id,
        base,
        quote,
        buy_trade_amount,
        sell_trade_amount,
        buy_price,
        sell_price,
    ):
        """Execute a SHORT trade: sell first, then buy."""
        return await self._execute_two_leg_trade(
            first_exchange_id=sell_exchange_id,
            second_exchange_id=buy_exchange_id,
            base=base,
            quote=quote,
            first_amount=sell_trade_amount,
            second_amount=buy_trade_amount,
            first_price=sell_price,
            second_price=buy_price,
            first_side="sell",
            second_side="buy",
            position_side="short",
        )

    async def _execute_two_leg_trade(
        self,
        first_exchange_id: str,
        second_exchange_id: str,
        base: str,
        quote: str,
        first_amount: float,
        second_amount: float,
        first_price: float,
        second_price: float,
        first_side: str,
        second_side: str,
        position_side: str,
    ):
        """
        Execute a two-leg trade (shared logic for LONG and SHORT).

        Parameters:
            first_exchange_id:  Exchange for the first leg.
            second_exchange_id: Exchange for the second leg.
            first_side:         'buy' or 'sell' for the first leg.
            second_side:        The opposite side for the second leg.
            position_side:      'long' or 'short' for position tracking.

        Returns:
            (result_first_order, result_second_order) tuple.
        """
        result_first_order = None
        result_second_order = None

        # Check balance for the first leg
        first_balance_ok = await self.check_balance(
            first_exchange_id, base, quote, first_side, first_amount, first_price
        )
        if not first_balance_ok:
            return result_first_order, result_second_order

        # Place the first leg
        result_first_order = await self.create_order(
            first_exchange_id, base, quote, first_price, first_amount, first_side, True
        )
        if result_first_order is None:
            return result_first_order, result_second_order

        first_order_id, first_executed_amount, first_remaining_amount = result_first_order

        # Use the actually filled amount for the second leg (partial fill safe)
        actual_second_amount = first_executed_amount
        if actual_second_amount <= 0:
            self.logger.warning(
                f"{first_side.capitalize()} order {first_order_id} filled 0 "
                f"— skipping {second_side} leg"
            )
            return result_first_order, result_second_order

        # Record open position after first leg fills
        symbol = f"{base}/{quote}"
        await self.sonarft_helpers.open_position(
            botid=first_exchange_id,
            order_id=str(first_order_id),
            exchange=first_exchange_id,
            symbol=symbol,
            side=position_side,
            amount=actual_second_amount,
            entry_price=first_price,
        )

        # Cancel remaining first-leg amount if partially filled (B2)
        if first_remaining_amount > 0:
            self.logger.warning(
                f"{first_side.capitalize()} order {first_order_id} partially filled "
                f"({first_executed_amount}/{first_amount}) "
                f"— cancelling remaining {first_remaining_amount}"
            )
            await self._cancel_order_with_retry(
                first_exchange_id, first_order_id, base, quote
            )

        # Check balance and place the second leg
        second_balance_ok = await self.check_balance(
            second_exchange_id, base, quote, second_side, actual_second_amount, second_price
        )
        if second_balance_ok:
            result_second_order = await self.create_order(
                second_exchange_id, base, quote, second_price,
                actual_second_amount, second_side, True,
            )

        if result_second_order is None:
            self.logger.error(
                f"{second_side.capitalize()} leg failed after "
                f"{first_side} {first_order_id} filled "
                f"— attempting to cancel {first_side} order to avoid unhedged position"
            )
            await self._cancel_order_with_retry(
                first_exchange_id, first_order_id, base, quote
            )
        elif result_second_order[2] > 0:
            # Second leg partially filled — imbalanced position (B1)
            second_order_id, second_executed, second_remaining = result_second_order
            imbalance = actual_second_amount - second_executed
            msg = (
                f"IMBALANCE: {second_side.capitalize()} order {second_order_id} "
                f"partially filled ({second_executed}/{actual_second_amount}) "
                f"on {second_exchange_id} — unhedged {imbalance} {base}. "
                f"Cancelling remaining."
            )
            self.logger.warning(msg)
            await self._cancel_order_with_retry(
                second_exchange_id, second_order_id, base, quote
            )
            if self._alert_callback:
                await self._alert_callback(msg)
        else:
            # Second leg fully filled — close the position
            await self.sonarft_helpers.close_position(
                botid=first_exchange_id,
                order_id=str(first_order_id),
            )

        return result_first_order, result_second_order

    async def _cancel_order_with_retry(
        self,
        exchange_id: str,
        order_id: str,
        base: str,
        quote: str,
        max_retries: int = 3,
    ) -> bool:
        """Cancel an order with exponential backoff retry. Alerts on final failure."""
        for attempt in range(1, max_retries + 1):
            result = await self.api_manager.cancel_order(
                exchange_id, order_id, base, quote
            )
            if result is not None:
                self.logger.info(
                    f"Order {order_id} cancelled on {exchange_id} (attempt {attempt})"
                )
                return True
            if attempt < max_retries:
                backoff = 2 ** (attempt - 1)  # 1s, 2s
                self.logger.warning(
                    f"Cancel attempt {attempt}/{max_retries} failed for order {order_id} "
                    f"on {exchange_id} — retrying in {backoff}s"
                )
                await asyncio.sleep(backoff)
        msg = (
            f"CRITICAL: Failed to cancel order {order_id} on {exchange_id} "
            f"after {max_retries} attempts — UNHEDGED POSITION RISK for {base}/{quote}"
        )
        self.logger.error(msg)
        if self._alert_callback:
            await self._alert_callback(msg)
        return False

    # ### Handle trade results ***********************************************
    async def handle_trade_results(
        self, trade: Trade, result_buy_order, result_sell_order
    ) -> tuple[bool, bool, bool]:
        """
        Handle the trade results.
        """
        if result_buy_order is None or result_sell_order is None:
            self.logger.error("One or both order results are None — trade incomplete")
            buy_order_id = result_buy_order[0] if result_buy_order else None
            sell_order_id = result_sell_order[0] if result_sell_order else None
            return buy_order_id, sell_order_id, False, False, False

        buy_order_id, buy_executed_amount, buy_remaining_amount = result_buy_order
        sell_order_id, sell_executed_amount, sell_remaining_amount = result_sell_order

        # Check if orders were placed successfully
        order_success = {
            buy_order_id: buy_remaining_amount <= 0,
            sell_order_id: sell_remaining_amount <= 0,
        }

        trade_success = order_success[buy_order_id] and order_success[sell_order_id]

        return (
            buy_order_id,
            sell_order_id,
            order_success[buy_order_id],
            order_success[sell_order_id],
            trade_success,
        )

    # ### Handle orders *******************************************************
    # Create orders
    async def create_order(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        price: float,
        trade_amount: float,
        side: str,
        monitor_order,
    ) -> tuple[str, float, float]:
        """
        Create an order on the specified exchange.
        """
        # Minimum order size validation (task 3.5)
        if trade_amount <= 0 or price <= 0:
            self.logger.warning(
                f"Skipping {side} order on {exchange_id}: invalid amount={trade_amount} or price={price}"
            )
            return None

        # Validate against exchange minimum order size (T21)
        symbol = f"{base}/{quote}"
        market = (self.api_manager.markets or {}).get(exchange_id, {}).get(symbol, {})
        if isinstance(market, dict):
            limits = market.get("limits") or {}
            min_amount = ((limits.get("amount") or {}).get("min")) or 0
            min_cost = ((limits.get("cost") or {}).get("min")) or 0
            if min_amount and trade_amount < min_amount:
                self.logger.warning(
                    f"Skipping {side} order on {exchange_id}: amount {trade_amount} below minimum {min_amount}"
                )
                return None
            if min_cost and trade_amount * price < min_cost:
                self.logger.warning(
                    f"Skipping {side} order on {exchange_id}: cost {trade_amount * price:.2f} below minimum {min_cost}"
                )
                return None

        if self.is_simulation_mode:
            latest_price = price
            t0 = _time.monotonic()
        else:
            t0 = _time.monotonic()
            latest_price = await self.monitor_price(
                exchange_id, base, quote, side, price
            )
            if latest_price is None:
                self.logger.warning(
                    f"monitor_price returned None for {exchange_id} {side} — skipping order"
                )
                return None
            # Round monitored price to exchange precision (T20)
            precision = self.api_manager.get_symbol_precision(exchange_id, base, quote)
            if precision:
                latest_price = round(latest_price, precision["prices_precision"])
            # T-18: Re-validate that the monitored price hasn't eroded the profit margin.
            # If the price moved adversely by more than the slippage buffer, skip the order.
            if price > 0:
                price_drift = abs(latest_price - price) / price
                slippage_buffer = getattr(self, 'slippage_buffer', 0.0)
                if slippage_buffer > 0 and price_drift > slippage_buffer:
                    self.logger.warning(
                        f"{side} order on {exchange_id}: monitored price {latest_price} drifted "
                        f"{price_drift:.4%} from target {price} (buffer {slippage_buffer:.4%}) — skipping"
                    )
                    return None

        self.logger.info(
            f"Creating {side} order on {exchange_id} for {trade_amount} {base} at {latest_price} {quote}..."
        )

        order_placed_id, total_executed_amount, total_remaining_amount = (
            await self.execute_order(
                exchange_id,
                base,
                quote,
                side,
                trade_amount,
                latest_price,
                monitor_order,
            )
        )

        latency_ms = (_time.monotonic() - t0) * 1000  # noqa: F841 — reserved for future metrics
        slippage = abs(latest_price - price) / price if price else 0.0
        if total_executed_amount == trade_amount:
            fill_status = "full"
            self.logger.info(
                f"{side} order on {exchange_id} for {trade_amount} {base} at {latest_price} {quote} executed."
            )
        elif total_executed_amount > 0:
            fill_status = "partial"
            self.logger.warning(
                f"{side} order on {exchange_id} partially filled: {total_executed_amount}/{trade_amount} {base}"
            )
        else:
            fill_status = "failed"
            self.logger.warning(
                f"{side} order on {exchange_id} for {trade_amount} {base} failed to execute"
            )

        log_order(
            botid="",  # not in scope; exchange provides context
            order_id=str(order_placed_id) if order_placed_id else "",
            symbol=f"{base}/{quote}",
            exchange=exchange_id,
            side=side,
            requested_price=price,
            executed_price=latest_price,
            amount=total_executed_amount,
            slippage=slippage,
            fill_status=fill_status,
            simulated=self.is_simulation_mode,
        )
        return order_placed_id, total_executed_amount, total_remaining_amount

    async def monitor_price(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        side,
        price_to_check,
        max_wait_seconds: int = 120,
    ):
        try:
            deadline = asyncio.get_running_loop().time() + max_wait_seconds
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(3)
                price = await self.api_manager.get_last_price(exchange_id, base, quote)
                if price is None:
                    self.logger.warning(
                        f"get_last_price returned None for {exchange_id} {base}/{quote} — retrying"
                    )
                    continue
                if side == "buy" and price_to_check >= price:
                    return price
                if side == "sell" and price_to_check <= price:
                    return price
            self.logger.warning(
                f"monitor_price timed out after {max_wait_seconds}s for {exchange_id} {base}/{quote} {side}"
            )
            return None
        except Exception:
            self.logger.exception(f"Error monitoring price for {exchange_id}")
            return None

    async def execute_order(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        side: str,
        trade_amount: float,
        price: float,
        monitor_order,
    ):
        if not self.is_simulation_mode:
            order_placed = await self.api_manager.create_order(
                exchange_id, base, quote, side, trade_amount, price
            )
            if order_placed is None:
                self.logger.error(
                    f"Order placement returned None for {side} on {exchange_id} — possible untracked order"
                )
                return None
            order_placed_id = order_placed["id"]
            if monitor_order:
                executed_amount, remaining_amount = await self.monitor_order(
                    exchange_id,
                    order_placed["id"],
                    side,
                    base,
                    quote,
                    trade_amount,
                    price,
                )
            else:
                executed_amount = trade_amount
                remaining_amount = 0
        else:
            # Simulation: model small random slippage (0-0.1%)
            slippage = random.uniform(0, 0.001)
            if side == "buy":
                latest_price = price * (1 + slippage)
            else:
                latest_price = price * (1 - slippage)
            executed_amount = trade_amount
            remaining_amount = 0
            order_placed_id = f"{side}_{random.randint(100000, 999999)}"
            symbol = f"{base}/{quote}"
            self.logger.info(
                f"SIMULATED: {side.upper()} order {order_placed_id} for {trade_amount} {symbol} at {latest_price} (slippage: {slippage:.6f})"
            )

        return order_placed_id, executed_amount, remaining_amount

    async def monitor_order(
        self,
        exchange_id: str,
        order_id: str,
        side_order,
        base: str,
        quote: str,
        target_amount: float,
        price,
        max_wait_seconds: int = 300,
    ) -> tuple[float, float]:
        """
        Monitor an order until it is filled, canceled, or the timeout is reached.

        The polling loop is wrapped in try/finally so that the order is always
        cancelled on any exit path — timeout, external task cancellation, or
        exception — preventing open orders from being left on the exchange.
        CancelledError (BaseException) propagates through the finally block
        correctly and is not swallowed.
        """
        self.logger.info(f"Monitoring {side_order} order: {order_id} at price: {price}")
        deadline = asyncio.get_running_loop().time() + max_wait_seconds
        try:
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(1)
                orders = await self.api_manager.watch_orders(exchange_id, base, quote)

                if not orders:
                    return target_amount, 0

                desired_order = next((o for o in orders if o["id"] == order_id), None)

                if desired_order is None:
                    self.logger.info(f"{side_order} order {order_id} already filled.")
                    return target_amount, 0

                if desired_order["status"] == "closed":
                    self.logger.info(f"{side_order} order {order_id} executed.")
                    filled = desired_order.get("filled", target_amount)
                    remaining = desired_order.get("remaining", 0)
                    return filled if filled > 0 else target_amount, remaining

                if desired_order["status"] == "canceled":
                    self.logger.warning(f"{side_order} order {order_id} was canceled.")
                    return 0, target_amount

            # Deadline reached — fall through to finally for cancellation
            self.logger.warning(
                f"monitor_order timed out after {max_wait_seconds}s for order {order_id} — cancelling"
            )
            return 0, target_amount
        finally:
            # Always attempt to cancel the order on any exit (timeout, CancelledError,
            # or exception). For normal filled/canceled exits the exchange will reject
            # the cancel gracefully; for abnormal exits this prevents open orders.
            cancelled = await self._cancel_order_with_retry(
                exchange_id, order_id, base, quote
            )
            if not cancelled:
                self.logger.error(
                    f"Order {order_id} on {exchange_id} could not be cancelled — "
                    f"order may still be open on exchange"
                )

    # ### Handle Balance **************************************************
    async def check_balance(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        side: str,
        trade_amount: float,
        price: float,
    ) -> bool:
        try:
            if self.is_simulation_mode:
                return True

            # Per-exchange lock prevents two concurrent tasks from both passing
            # the balance check when only one can actually fill.
            if exchange_id not in self._exchange_locks:
                self._exchange_locks[exchange_id] = asyncio.Lock()
            async with self._exchange_locks[exchange_id]:
                balance = await self.api_manager.get_balance(exchange_id)

                if side == "buy":
                    amount = trade_amount * price
                    if balance["free"][quote] < amount:
                        self.logger.warning(
                            f"Not enough buy balance: {balance['free'][quote]} < {amount}"
                        )
                        return False
                elif side == "sell":
                    if balance["free"][base] < trade_amount:
                        self.logger.warning(
                            f"Not enough sell balance: {balance['free'][base]} < {trade_amount}"
                        )
                        return False
        except Exception:
            self.logger.exception("Error checking balance")
            return False

        return True
