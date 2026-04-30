"""
SonarFT Helpers Module
Utility functions, Trade dataclass, and async-safe file persistence.

Trade and order history is stored in SQLite (sonarftdata/history/sonarft.db)
for O(1) writes, concurrent-safe access, and efficient querying.
Falls back to JSON append if SQLite is unavailable.
"""
import asyncio
import json
import logging
import os
import re
import sqlite3
import time

# Resolve the bot package directory so data paths work regardless of CWD.
_BOT_DIR = os.path.dirname(os.path.abspath(__file__))


def _bot_path(*parts: str) -> str:
    """Return an absolute path anchored to the bot package directory."""
    return os.path.join(_BOT_DIR, *parts)


# Trade dataclass lives in models.py; re-exported here for backward compatibility
from models import Trade


def sanitize_client_id(client_id: str) -> str:
    """Sanitize client_id for safe use in file paths and dict keys.
    Allows only alphanumeric characters, hyphens, and underscores.
    Raises ValueError if the result is empty."""
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', str(client_id))
    if not sanitized:
        raise ValueError(f"Invalid client_id after sanitization: {client_id!r}")
    return sanitized


_ALLOWED_TABLES = frozenset({'orders', 'trades', 'daily_loss'})


class SonarftHelpers:
    """
    SonarFTHelpers class contains helper functions for the trading bot.
    Trade/order history is persisted to SQLite for O(1) writes and concurrent safety.
    All file operations are async-safe via asyncio.to_thread.
    """

    _DB_PATH = _bot_path('sonarftdata', 'history', 'sonarft.db')

    def __init__(self, is_simulation_mode: bool, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.is_simulation_mode = is_simulation_mode
        self._file_locks: dict = {}
        self._db_lock = asyncio.Lock()
        # Initialise DB schema in a thread at construction time (sync context)
        try:
            self._init_db()
        except Exception as e:
            self.logger.warning(f"SQLite init failed, will fall back to JSON: {e}")

    # ### SQLite helpers *************************************************

    @classmethod
    def _init_db(cls) -> None:
        """Create tables if they don't exist. Safe to call multiple times.
        WAL mode is enabled for concurrent read/write access — reads no longer
        block writes and writes no longer block reads.
        """
        os.makedirs(os.path.dirname(cls._DB_PATH), exist_ok=True)
        with sqlite3.connect(cls._DB_PATH) as conn:
            # WAL journal mode: readers don't block writers, writers don't block readers
            conn.execute("PRAGMA journal_mode=WAL")
            # NORMAL sync is safe with WAL and significantly faster than FULL
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    botid     TEXT NOT NULL,
                    timestamp TEXT,
                    data      TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    botid     TEXT NOT NULL,
                    timestamp TEXT,
                    data      TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    order_id    TEXT NOT NULL,
                    botid       TEXT NOT NULL,
                    exchange    TEXT NOT NULL,
                    symbol      TEXT NOT NULL,
                    side        TEXT NOT NULL,
                    amount      REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    opened_at   TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'open',
                    closed_at   TEXT,
                    PRIMARY KEY (botid, order_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_botid ON orders(botid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_botid ON trades(botid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_botid_ts ON orders(botid, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_botid_ts ON trades(botid, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_botid_status ON positions(botid, status)")
            conn.commit()

    @classmethod
    def _db_insert(cls, table: str, botid: str, timestamp: str, data: dict) -> None:
        """Insert one record into the given table. Runs in a thread."""
        if table not in _ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {table!r}")
        with sqlite3.connect(cls._DB_PATH) as conn:
            conn.execute(
                f"INSERT INTO {table} (botid, timestamp, data) VALUES (?, ?, ?)",
                (str(botid), timestamp, json.dumps(data))
            )
            conn.commit()

    @classmethod
    def _db_query(cls, table: str, botid: str, limit: int = 100, offset: int = 0) -> list:
        """Return records for botid as a list of dicts, most recent first.
        Runs in a thread. LIMIT/OFFSET prevent unbounded result sets.
        """
        if table not in _ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {table!r}")
        with sqlite3.connect(cls._DB_PATH) as conn:
            rows = conn.execute(
                f"SELECT data FROM {table} WHERE botid = ?"
                f" ORDER BY id DESC LIMIT ? OFFSET ?",
                (str(botid), limit, offset)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    @classmethod
    def _db_purge(cls, table: str, botid: str, keep_last: int = 10_000) -> None:
        """Delete oldest records beyond keep_last for a given bot.
        Runs in a thread. Called periodically to enforce retention policy.
        """
        if table not in _ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {table!r}")
        with sqlite3.connect(cls._DB_PATH) as conn:
            conn.execute(f"""
                DELETE FROM {table}
                WHERE botid = ? AND id NOT IN (
                    SELECT id FROM {table}
                    WHERE botid = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
            """, (str(botid), str(botid), keep_last))
            conn.commit()

    def _get_lock(self, file_name: str) -> asyncio.Lock:
        """Return (creating if needed) a per-file asyncio.Lock."""
        if file_name not in self._file_locks:
            self._file_locks[file_name] = asyncio.Lock()
        return self._file_locks[file_name]

    # ### Sync helpers (run inside to_thread) ****************************

    @staticmethod
    def _append_json(file_name: str, record: dict) -> None:
        """Read-modify-write a JSON array file. Runs in a thread."""
        if os.path.exists(file_name):
            with open(file_name, encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        history.append(record)
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)

    @staticmethod
    def _write_json(file_name: str, data: dict) -> None:
        """Write a JSON object to a file. Runs in a thread."""
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    # ### Async public API ***********************************************

    async def save_botid(self, botid):
        """Save botid info to a json file."""
        file_name = _bot_path('sonarftdata', 'bots', f"{botid}.json")
        async with self._get_lock(file_name):
            await asyncio.to_thread(self._write_json, file_name, {"botid": botid})

    async def save_order_data(self, botid, order_info: dict) -> None:
        """Persist order info to SQLite (async-safe)."""
        timestamp = order_info.get('timestamp', '')
        async with self._db_lock:
            await asyncio.to_thread(self._db_insert, 'orders', botid, timestamp, order_info)
        self.logger.info("Order: Success")

    async def save_order_history(self, botid, trade: Trade, trade_position: str) -> None:
        """Save trade search info to SQLite."""
        t = time.localtime()
        current_time = time.strftime("%Y-%m-%dT%H:%M:%S", t)
        trade_info = {
            'timestamp': current_time,
            'position': trade_position,
            'base': trade.base,
            'quote': trade.quote,
            'buy_exchange': trade.buy_exchange,
            'sell_exchange': trade.sell_exchange,
            'buy_price': trade.buy_price,
            'sell_price': trade.sell_price,
            'buy_trade_amount': trade.buy_trade_amount,
            'sell_trade_amount': trade.sell_trade_amount,
            'executed_amount': trade.executed_amount,
            'buy_value': trade.buy_value,
            'sell_value': trade.sell_value,
            'buy_fee_rate': trade.buy_fee_rate,
            'sell_fee_rate': trade.sell_fee_rate,
            'buy_fee_base': trade.buy_fee_base,
            'buy_fee_quote': trade.buy_fee_quote,
            'sell_fee_quote': trade.sell_fee_quote,
            'profit': trade.profit,
            'profit_percentage': trade.profit_percentage,
        }
        await self.save_order_data(botid, trade_info)

    async def save_trade_data(self, botid, trade_info: dict) -> None:
        """Persist trade info to SQLite (async-safe)."""
        timestamp = trade_info.get('timestamp', '')
        async with self._db_lock:
            await asyncio.to_thread(self._db_insert, 'trades', botid, timestamp, trade_info)
        self.logger.info("Trade: Success")

    async def save_trade_history(
        self, botid, trade: Trade,
        buy_order_id, sell_order_id, trade_position,
        order_buy_success: bool, order_sell_success: bool, trade_success: bool
    ) -> None:
        """Save execution trade info to SQLite."""
        t = time.localtime()
        current_time = time.strftime("%Y-%m-%dT%H:%M:%S", t)
        trade_info = {
            'timestamp': current_time,
            'position': trade_position,
            'buy_order_id': buy_order_id,
            'sell_order_id': sell_order_id,
            'base': trade.base,
            'quote': trade.quote,
            'buy_exchange': trade.buy_exchange,
            'sell_exchange': trade.sell_exchange,
            'buy_price': trade.buy_price,
            'sell_price': trade.sell_price,
            'buy_trade_amount': trade.buy_trade_amount,
            'sell_trade_amount': trade.sell_trade_amount,
            'executed_amount': trade.executed_amount,
            'buy_value': trade.buy_value,
            'sell_value': trade.sell_value,
            'buy_fee_rate': trade.buy_fee_rate,
            'sell_fee_rate': trade.sell_fee_rate,
            'buy_fee_base': trade.buy_fee_base,
            'buy_fee_quote': trade.buy_fee_quote,
            'sell_fee_quote': trade.sell_fee_quote,
            'profit': trade.profit,
            'profit_percentage': trade.profit_percentage,
            'order_buy_success': order_buy_success,
            'order_sell_success': order_sell_success,
            'trade_success': trade_success,
        }
        await self.save_trade_data(botid, trade_info)

    async def get_orders(self, botid) -> list:
        """Retrieve all orders for a bot from SQLite.
        No lock needed — WAL mode allows concurrent reads alongside writes.
        """
        return await asyncio.to_thread(self._db_query, 'orders', botid)

    async def get_trades(self, botid) -> list:
        """Retrieve all trades for a bot from SQLite.
        No lock needed — WAL mode allows concurrent reads alongside writes.
        """
        return await asyncio.to_thread(self._db_query, 'trades', botid)

    @classmethod
    async def _async_query(cls, table: str, botid: str, limit: int = 100, offset: int = 0) -> list:
        """Classmethod async query — usable without a full instance (e.g. from HTTP endpoints).
        No lock needed — WAL mode allows concurrent reads.
        """
        return await asyncio.to_thread(cls._db_query, table, botid, limit, offset)

    async def purge_history(self, botid, keep_last: int = 10_000) -> None:
        """Enforce retention policy: keep only the most recent keep_last records per bot.
        Safe to call after save_order_data / save_trade_data.
        """
        await asyncio.to_thread(self._db_purge, 'orders', botid, keep_last)
        await asyncio.to_thread(self._db_purge, 'trades', botid, keep_last)

    @classmethod
    def backup_db(cls, dst_path: str) -> None:
        """Create a hot backup of the SQLite database to dst_path.
        Uses sqlite3's built-in backup API — safe to call while the DB is in use.
        Runs synchronously; wrap in asyncio.to_thread for async contexts.
        """
        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
        src = sqlite3.connect(cls._DB_PATH)
        dst = sqlite3.connect(dst_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    async def async_backup_db(self, dst_path: str) -> None:
        """Async wrapper for backup_db. Call from a scheduled task or lifespan handler."""
        await asyncio.to_thread(self.backup_db, dst_path)
        self.logger.info("Database backed up to %s", dst_path)

    async def save_error(self, error_info: dict) -> None:
        """Save error info to a json file."""
        file_name = _bot_path('sonarftdata', 'errors_history.json')
        async with self._get_lock(file_name):
            await asyncio.to_thread(self._append_json, file_name, error_info)
        self.logger.info(f"Errors info saved to {file_name}")

    async def save_balance_data(self, balance_info: dict) -> None:
        """Save balance info to a json file."""
        file_name = _bot_path('sonarftdata', 'balance_history.json')
        async with self._get_lock(file_name):
            await asyncio.to_thread(self._append_json, file_name, balance_info)
        self.logger.info(f"Balance info saved to {file_name}")

    # ### Position tracker *********************************************

    @classmethod
    def _position_open_sync(
        cls, botid: str, order_id: str, exchange: str, symbol: str,
        side: str, amount: float, entry_price: float, opened_at: str
    ) -> None:
        """Insert an open position record. Runs in a thread."""
        with sqlite3.connect(cls._DB_PATH) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO positions
                    (order_id, botid, exchange, symbol, side, amount, entry_price, opened_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')
            """, (order_id, str(botid), exchange, symbol, side, amount, entry_price, opened_at))
            conn.commit()

    @classmethod
    def _position_close_sync(cls, botid: str, order_id: str, closed_at: str) -> None:
        """Mark a position as closed. Runs in a thread."""
        with sqlite3.connect(cls._DB_PATH) as conn:
            conn.execute("""
                UPDATE positions SET status = 'closed', closed_at = ?
                WHERE botid = ? AND order_id = ?
            """, (closed_at, str(botid), order_id))
            conn.commit()

    @classmethod
    def _positions_open_sync(cls, botid: str) -> list:
        """Return all open positions for a bot. Runs in a thread."""
        with sqlite3.connect(cls._DB_PATH) as conn:
            rows = conn.execute("""
                SELECT order_id, exchange, symbol, side, amount, entry_price, opened_at
                FROM positions
                WHERE botid = ? AND status = 'open'
                ORDER BY opened_at ASC
            """, (str(botid),)).fetchall()
        return [
            {
                'order_id': r[0], 'exchange': r[1], 'symbol': r[2],
                'side': r[3], 'amount': r[4], 'entry_price': r[5], 'opened_at': r[6],
                'status': 'open',
            }
            for r in rows
        ]

    async def open_position(
        self, botid: str, order_id: str, exchange: str, symbol: str,
        side: str, amount: float, entry_price: float
    ) -> None:
        """Record that the first leg of a trade has filled — position is now open."""
        opened_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        async with self._db_lock:
            await asyncio.to_thread(
                self._position_open_sync,
                botid, order_id, exchange, symbol, side, amount, entry_price, opened_at
            )
        self.logger.info(
            f"Position opened: {side} {amount} {symbol} @ {entry_price} on {exchange} "
            f"(order {order_id})"
        )

    async def close_position(self, botid: str, order_id: str) -> None:
        """Mark a position as closed after the second leg fills."""
        closed_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        async with self._db_lock:
            await asyncio.to_thread(self._position_close_sync, botid, order_id, closed_at)
        self.logger.info(f"Position closed: order {order_id} for bot {botid}")

    async def get_open_positions(self, botid: str) -> list:
        """Return all open positions for a bot. No lock needed — WAL mode."""
        return await asyncio.to_thread(self._positions_open_sync, botid)

    def percentage_difference(self, value1, value2):
        """Calculate the percentage difference between two values."""
        if value1 == 0 or value2 == 0 or value1 == value2:
            return 0
        return abs((value1 - value2) / ((value1 + value2) / 2)) * 100
