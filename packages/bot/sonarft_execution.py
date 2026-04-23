"""
SonarFT Execution Module
Order execution (real and simulated), price monitoring, balance checking.
"""
import asyncio
import logging
import random

# sonarft classes
from sonarft_api_manager import SonarftApiManager
from sonarft_helpers import SonarftHelpers, Trade

# used to force maximum precision 8

class SonarftExecution:
    """
    SonarftExecution class is responsible for executing the trades found by the SonarftTrades class.
    """

    def __init__(self,
                 api_manager: SonarftApiManager,
                 sonarft_helpers: SonarftHelpers,
                 is_simulation_mode: bool, logger=None,
                 max_trade_amount: float = 0.0,
                 max_orders_per_minute: int = 0):
        self.logger = logger or logging.getLogger(__name__)
        self.api_manager = api_manager
        self.sonarft_helpers = sonarft_helpers
        self.is_simulation_mode = is_simulation_mode
        # max_trade_amount: 0 = disabled (no limit)
        self.max_trade_amount = max_trade_amount
        # max_orders_per_minute: 0 = disabled
        self.max_orders_per_minute = max_orders_per_minute
        self._order_timestamps: list = []  # rolling window for rate limiting
        self._alert_callback = None  # set by SonarftBot after construction

    # ### Entry Point for the trade execution ********************************
    async def execute_trade(self, botid, trade: dict) -> bool:
        """
        Execute the given trade, enforcing position size and order rate limits.
        """
        try:
            trade_obj = Trade(**trade)

            # Max position size check (task 3.4)
            if self.max_trade_amount > 0 and trade_obj.buy_trade_amount > self.max_trade_amount:
                self.logger.warning(
                    f"Bot {botid}: trade_amount {trade_obj.buy_trade_amount} exceeds "
                    f"max_trade_amount {self.max_trade_amount} — skipping"
                )
                return False

            # Order rate limiting (task 3.3)
            if self.max_orders_per_minute > 0:
                import time as _t
                now = _t.monotonic()
                self._order_timestamps = [t for t in self._order_timestamps if now - t < 60]
                if len(self._order_timestamps) >= self.max_orders_per_minute:
                    self.logger.warning(
                        f"Bot {botid}: order rate limit reached "
                        f"({self.max_orders_per_minute}/min) — skipping"
                    )
                    return False
                self._order_timestamps.append(now)

            buy_order_success, sell_order_success, trade_success = await self._execute_single_trade(botid, trade_obj)
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return False
        return trade_success

    async def _execute_single_trade(self, botid, trade: Trade) -> tuple[bool, bool, bool]:
        """
        Execute the given found trade from the SonarftTrades class.
        """
        # Extract trade data
        base = trade.base
        quote = trade.quote
        buy_exchange_id = trade.buy_exchange
        sell_exchange_id = trade.sell_exchange
        buy_price = trade.buy_price
        sell_price = trade.sell_price
        buy_trade_amount = trade.buy_trade_amount
        sell_trade_amount = trade.sell_trade_amount

        buy_order_success = False
        sell_order_success = False
        trade_success = False

        try:
            # Indicators are always passed through trade_data from weighted_adjust_prices
            market_direction_buy = trade.market_direction_buy
            market_direction_sell = trade.market_direction_sell
            market_rsi_buy = trade.market_rsi_buy
            market_rsi_sell = trade.market_rsi_sell
            market_stoch_rsi_buy_k = trade.market_stoch_rsi_buy_k
            market_stoch_rsi_buy_d = trade.market_stoch_rsi_buy_d
            market_stoch_rsi_sell_k = trade.market_stoch_rsi_sell_k
            market_stoch_rsi_sell_d = trade.market_stoch_rsi_sell_d

            # Guard: if indicators are missing, skip execution
            if any(v is None for v in [market_direction_buy, market_direction_sell,
                                        market_rsi_buy, market_rsi_sell,
                                        market_stoch_rsi_buy_k, market_stoch_rsi_sell_k]):
                self.logger.warning(
                    f"Bot {botid}: missing indicators in trade_data — skipping execution"
                )
                return False, False, False

            # Flash crash protection: skip if buy/sell price deviation > 2%
            if buy_price > 0 and sell_price > 0:
                price_deviation = abs(sell_price - buy_price) / buy_price
                if price_deviation > 0.02:
                    self.logger.warning(
                        f"Bot {botid}: price deviation {price_deviation:.4f} (>{0.02}) — "
                        f"possible flash crash, skipping execution"
                    )
                    return False, False, False


            trade_position = None
            buy_order_id = None
            sell_order_id = None

            #Long or Reverse to Short
            if market_direction_buy == 'bull' and market_direction_sell == 'bull':
                if market_rsi_buy >= 70 and market_rsi_sell >= 70 and market_stoch_rsi_buy_k > market_stoch_rsi_buy_d and market_stoch_rsi_sell_k > market_stoch_rsi_sell_d:
                    trade_position = 'SHORT'
                    result_buy_order, result_sell_order = await self.execute_short_trade(buy_exchange_id, sell_exchange_id, base, quote, buy_trade_amount, sell_trade_amount, buy_price, sell_price)
                    buy_order_id, sell_order_id, buy_order_success, sell_order_success, trade_success = await self.handle_trade_results(trade, result_buy_order, result_sell_order)
                else:
                    trade_position = 'LONG'
                    result_buy_order, result_sell_order = await self.execute_long_trade(buy_exchange_id, sell_exchange_id, base, quote, buy_trade_amount, sell_trade_amount, buy_price, sell_price)
                    buy_order_id, sell_order_id, buy_order_success, sell_order_success, trade_success = await self.handle_trade_results(trade, result_buy_order, result_sell_order)

            #Short or Reverse to Long
            elif market_direction_buy == 'bear' and market_direction_sell == 'bear':
                if market_rsi_buy <= 30 and market_rsi_sell <= 30 and market_stoch_rsi_buy_k < market_stoch_rsi_buy_d and market_stoch_rsi_sell_k < market_stoch_rsi_sell_d:
                    trade_position = 'LONG'
                    result_buy_order, result_sell_order = await self.execute_long_trade(buy_exchange_id, sell_exchange_id, base, quote, buy_trade_amount, sell_trade_amount, buy_price, sell_price)
                    buy_order_id, sell_order_id, buy_order_success, sell_order_success, trade_success = await self.handle_trade_results(trade, result_buy_order, result_sell_order)
                else:
                    trade_position = 'SHORT'
                    result_buy_order, result_sell_order = await self.execute_short_trade(buy_exchange_id, sell_exchange_id, base, quote, buy_trade_amount, sell_trade_amount, buy_price, sell_price)
                    buy_order_id, sell_order_id, buy_order_success, sell_order_success, trade_success = await self.handle_trade_results(trade, result_buy_order, result_sell_order)

            else:
                self.logger.warning(
                    f"Bot {botid}: neutral/mixed market direction "
                    f"(buy={market_direction_buy}, sell={market_direction_sell}) — skipping trade execution"
                )
                return False, False, False

            if trade_position:
                await self.sonarft_helpers.save_order_history(botid, trade, trade_position)

            if trade_success:
                await self.sonarft_helpers.save_trade_history(botid, trade, buy_order_id, sell_order_id, trade_position, buy_order_success, sell_order_success, trade_success)

            return buy_order_success, sell_order_success, trade_success
        except Exception as e:
            self.logger.error(str(e))
            return False, False, False

    async def execute_long_trade(self, buy_exchange_id, sell_exchange_id, base, quote, buy_trade_amount, sell_trade_amount, buy_price, sell_price):
        result_buy_order = None
        result_sell_order = None
        buy_balance_status = await self.check_balance(buy_exchange_id, base, quote, 'buy', buy_trade_amount, buy_price)
        if not buy_balance_status:
            return result_buy_order, result_sell_order

        result_buy_order = await self.create_order(buy_exchange_id, base, quote, buy_price, buy_trade_amount, 'buy', True)
        if result_buy_order is None:
            return result_buy_order, result_sell_order

        buy_order_id, buy_executed_amount, buy_remaining_amount = result_buy_order

        # Use the actually filled amount for the sell leg (partial fill safe)
        actual_sell_amount = buy_executed_amount
        if actual_sell_amount <= 0:
            self.logger.warning(f"Buy order {buy_order_id} filled 0 — skipping sell leg")
            return result_buy_order, result_sell_order

        # Cancel remaining buy amount if partially filled (B2)
        if buy_remaining_amount > 0:
            self.logger.warning(
                f"Buy order {buy_order_id} partially filled ({buy_executed_amount}/{buy_trade_amount}) "
                f"— cancelling remaining {buy_remaining_amount}"
            )
            await self._cancel_order_with_retry(buy_exchange_id, buy_order_id, base, quote)

        sell_balance_status = await self.check_balance(sell_exchange_id, base, quote, 'sell', actual_sell_amount, sell_price)
        if sell_balance_status:
            result_sell_order = await self.create_order(sell_exchange_id, base, quote, sell_price, actual_sell_amount, 'sell', True)

        if result_sell_order is None:
            self.logger.error(
                f"Sell leg failed after buy {buy_order_id} filled — "
                f"attempting to cancel buy order to avoid unhedged position"
            )
            await self._cancel_order_with_retry(buy_exchange_id, buy_order_id, base, quote)
        elif result_sell_order[2] > 0:
            # Second leg partially filled — imbalanced position (B1)
            sell_order_id, sell_executed, sell_remaining = result_sell_order
            imbalance = actual_sell_amount - sell_executed
            msg = (
                f"IMBALANCE: Sell order {sell_order_id} partially filled "
                f"({sell_executed}/{actual_sell_amount}) on {sell_exchange_id} — "
                f"unhedged {imbalance} {base}. Cancelling remaining."
            )
            self.logger.warning(msg)
            await self._cancel_order_with_retry(sell_exchange_id, sell_order_id, base, quote)
            if self._alert_callback:
                await self._alert_callback(msg)

        return result_buy_order, result_sell_order

    async def execute_short_trade(self, buy_exchange_id, sell_exchange_id, base, quote, buy_trade_amount, sell_trade_amount, buy_price, sell_price):
        result_buy_order = None
        result_sell_order = None
        sell_balance_status = await self.check_balance(sell_exchange_id, base, quote, 'sell', sell_trade_amount, sell_price)
        if not sell_balance_status:
            return result_buy_order, result_sell_order

        result_sell_order = await self.create_order(sell_exchange_id, base, quote, sell_price, sell_trade_amount, 'sell', True)
        if result_sell_order is None:
            return result_buy_order, result_sell_order

        sell_order_id, sell_executed_amount, sell_remaining_amount = result_sell_order

        actual_buy_amount = sell_executed_amount
        if actual_buy_amount <= 0:
            self.logger.warning(f"Sell order {sell_order_id} filled 0 — skipping buy leg")
            return result_buy_order, result_sell_order

        # Cancel remaining sell amount if partially filled (B2)
        if sell_remaining_amount > 0:
            self.logger.warning(
                f"Sell order {sell_order_id} partially filled ({sell_executed_amount}/{sell_trade_amount}) "
                f"— cancelling remaining {sell_remaining_amount}"
            )
            await self._cancel_order_with_retry(sell_exchange_id, sell_order_id, base, quote)

        buy_balance_status = await self.check_balance(buy_exchange_id, base, quote, 'buy', actual_buy_amount, buy_price)
        if buy_balance_status:
            result_buy_order = await self.create_order(buy_exchange_id, base, quote, buy_price, actual_buy_amount, 'buy', True)

        if result_buy_order is None:
            self.logger.error(
                f"Buy leg failed after sell {sell_order_id} filled — "
                f"attempting to cancel sell order to avoid unhedged position"
            )
            await self._cancel_order_with_retry(sell_exchange_id, sell_order_id, base, quote)
        elif result_buy_order[2] > 0:
            # Second leg partially filled — imbalanced position (B1)
            buy_order_id, buy_executed, buy_remaining = result_buy_order
            imbalance = actual_buy_amount - buy_executed
            msg = (
                f"IMBALANCE: Buy order {buy_order_id} partially filled "
                f"({buy_executed}/{actual_buy_amount}) on {buy_exchange_id} — "
                f"unhedged {imbalance} {base}. Cancelling remaining."
            )
            self.logger.warning(msg)
            await self._cancel_order_with_retry(buy_exchange_id, buy_order_id, base, quote)
            if self._alert_callback:
                await self._alert_callback(msg)

        return result_buy_order, result_sell_order

    async def _cancel_order_with_retry(
        self, exchange_id: str, order_id: str, base: str, quote: str,
        max_retries: int = 3,
    ) -> bool:
        """Cancel an order with exponential backoff retry. Alerts on final failure."""
        for attempt in range(1, max_retries + 1):
            result = await self.api_manager.cancel_order(exchange_id, order_id, base, quote)
            if result is not None:
                self.logger.info(f"Order {order_id} cancelled on {exchange_id} (attempt {attempt})")
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
    async def handle_trade_results(self, trade: Trade, result_buy_order, result_sell_order) -> tuple[bool, bool, bool]:
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
            sell_order_id: sell_remaining_amount <= 0
        }

        trade_success = order_success[buy_order_id] and order_success[sell_order_id]

        return buy_order_id, sell_order_id, order_success[buy_order_id], order_success[sell_order_id], trade_success

    # ### Handle orders *******************************************************
    # Create orders
    async def create_order(self, exchange_id: str, base: str, quote: str, price: float, trade_amount: float, side: str, monitor_order) -> tuple[str, float, float]:
        """
        Create an order on the specified exchange.
        """
        # Minimum order size validation (task 3.5)
        if trade_amount <= 0 or price <= 0:
            self.logger.warning(
                f"Skipping {side} order on {exchange_id}: invalid amount={trade_amount} or price={price}"
            )
            return None

        self.logger.info(f"Creating {side} order on {exchange_id} for {trade_amount} {base} at {price} {quote}...")

        # Validate against exchange minimum order size (T21)
        symbol = f"{base}/{quote}"
        market = (self.api_manager.markets or {}).get(exchange_id, {}).get(symbol, {})
        if isinstance(market, dict):
            limits = market.get('limits') or {}
            min_amount = ((limits.get('amount') or {}).get('min')) or 0
            min_cost = ((limits.get('cost') or {}).get('min')) or 0
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
        else:
            latest_price = await self.monitor_price(exchange_id, base, quote, side, price)
            if latest_price is None:
                self.logger.warning(f"monitor_price returned None for {exchange_id} {side} — skipping order")
                return None
            # Round monitored price to exchange precision (T20)
            precision = self.api_manager.get_symbol_precision(exchange_id, base, quote)
            if precision:
                latest_price = round(latest_price, precision['prices_precision'])

        order_placed_id, total_executed_amount, total_remaining_amount = await self.execute_order(
            exchange_id, base, quote, side, trade_amount, latest_price, monitor_order
        )

        if total_executed_amount == trade_amount:
            self.logger.info(f"{side} order on {exchange_id} for {trade_amount} {base} at {latest_price} {quote} executed.")

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
                    self.logger.warning(f"get_last_price returned None for {exchange_id} {base}/{quote} — retrying")
                    continue
                if side == 'buy' and price_to_check >= price:
                    return price
                if side == 'sell' and price_to_check <= price:
                    return price
            self.logger.warning(
                f"monitor_price timed out after {max_wait_seconds}s for {exchange_id} {base}/{quote} {side}"
            )
            return None
        except Exception as e:
            self.logger.error(f"error monitoring price for {exchange_id}: {e}")
            return None

    async def execute_order(self, exchange_id: str, base: str, quote: str, side: str, trade_amount: float, price: float, monitor_order):
        if not self.is_simulation_mode:
            order_placed = await self.api_manager.create_order(exchange_id, base, quote, side, trade_amount, price)
            if order_placed is None:
                self.logger.error(f"Order placement returned None for {side} on {exchange_id} — possible untracked order")
                return None
            order_placed_id = order_placed['id']
            if monitor_order:
                executed_amount, remaining_amount = await self.monitor_order(exchange_id, order_placed['id'], side, base, quote, trade_amount, price)
            else:
                executed_amount = trade_amount
                remaining_amount = 0
        else:
            # Simulation: model small random slippage (0-0.1%)
            slippage = random.uniform(0, 0.001)
            if side == 'buy':
                price * (1 + slippage)
            else:
                price * (1 - slippage)
            executed_amount = trade_amount
            remaining_amount = 0
            order_placed_id = f"{side}_{random.randint(100000, 999999)}"

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
        """
        self.logger.info(f"Monitoring {side_order} order: {order_id} at price: {price}")
        deadline = asyncio.get_running_loop().time() + max_wait_seconds
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(1)
            orders = await self.api_manager.watch_orders(exchange_id, base, quote)

            if not orders:
                return target_amount, 0

            desired_order = next((o for o in orders if o["id"] == order_id), None)

            if desired_order is None:
                self.logger.info(f"{side_order} order {order_id} already filled.")
                return target_amount, 0

            if desired_order['status'] == 'closed':
                self.logger.info(f"{side_order} order {order_id} executed.")
                filled = desired_order.get('filled', target_amount)
                remaining = desired_order.get('remaining', 0)
                return filled if filled > 0 else target_amount, remaining

            if desired_order['status'] == 'canceled':
                self.logger.warning(f"{side_order} order {order_id} was canceled.")
                return 0, target_amount

        self.logger.warning(
            f"monitor_order timed out after {max_wait_seconds}s for order {order_id} — cancelling"
        )
        cancelled = await self._cancel_order_with_retry(exchange_id, order_id, base, quote)
        if not cancelled:
            self.logger.error(
                f"Order {order_id} on {exchange_id} could not be cancelled after timeout — "
                f"order may still be open on exchange"
            )
        return 0, target_amount

    # ### Handle Balance **************************************************
    async def check_balance(self, exchange_id: str, base: str, quote: str, side: str, trade_amount: float, price: float) -> bool:
        try:
            if self.is_simulation_mode:
                return True

            balance = await self.api_manager.get_balance(exchange_id)

            if side == 'buy':
                amount = trade_amount*price
                if balance['free'][quote] < amount:
                    self.logger.info(
                        f"Not enough buy balance: {balance['free'][quote]} < {amount}")
                    return False
            elif side == 'sell':
                if balance['free'][base] < trade_amount:
                    self.logger.info(
                        f"Not enough sell balance: {balance['free'][base]} < {trade_amount}")
                    return False
        except Exception as e:
            self.logger.error(f"Error checking balance: {e}")
            return False

        return True

