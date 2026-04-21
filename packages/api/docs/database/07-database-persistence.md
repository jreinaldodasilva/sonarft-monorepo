# Prompt 07 — Database, Persistence & Data Storage Review

**Generated:** July 2025 | **Updated:** July 2025 (post-implementation)
**Reviewer:** Amazon Q (Senior Python / Data Architecture / SQLite)
**Status:** ✅ All high findings resolved

---

## Executive Summary

All critical database issues have been resolved. Config file writes are now atomic via `tempfile` + `os.replace`. The corrupted `[object Object]_parameters.json` file has been deleted. SQLite WAL mode is enabled — reads no longer block writes. Pagination (`LIMIT`/`OFFSET`) is implemented on all history queries. The daily loss accumulator is persisted to SQLite and survives process restarts. A 10,000-record retention policy and hot backup API have been added. Composite `(botid, timestamp)` indexes support efficient date-range queries.

---

## Storage Architecture (Current)

| Store | Technology | Status |
|---|---|---|
| Trade & order history | SQLite (`sonarft.db`) WAL mode | ✅ WAL + indexes + retention + backup |
| Per-client runtime config | JSON files (`config/`) | ✅ Atomic writes + client_id sanitization |
| Bot static config | JSON files (`sonarftdata/`) | ✅ Read-only at runtime |
| Bot registry | JSON files (`bots/`) | ✅ `asyncio.to_thread` |
| Daily loss accumulator | SQLite `daily_loss` table | ✅ Persisted across restarts |
| Bot instance state | In-memory (`BotManager._bots`) | ℹ️ Still in-memory — requires Redis for multi-process |

---

## SQLite Schema (Current)

```sql
-- WAL mode + NORMAL sync
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE orders (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    botid     TEXT NOT NULL,
    timestamp TEXT,
    data      TEXT NOT NULL
);
CREATE TABLE trades (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    botid     TEXT NOT NULL,
    timestamp TEXT,
    data      TEXT NOT NULL
);
CREATE INDEX idx_orders_botid ON orders(botid);
CREATE INDEX idx_trades_botid ON trades(botid);
CREATE INDEX idx_orders_botid_ts ON orders(botid, timestamp);  -- ✅ New
CREATE INDEX idx_trades_botid_ts ON trades(botid, timestamp);  -- ✅ New

CREATE TABLE daily_loss (                                       -- ✅ New
    botid TEXT NOT NULL,
    date  TEXT NOT NULL,
    loss  REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (botid, date)
);
```

---

## Atomic Config Writes (Implemented)

```python
def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    dir_name = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=dir_name, delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=4)
        tmp_path = tmp.name
    os.replace(tmp_path, path)  # atomic on POSIX
```

Concurrent reads during write never produce truncated JSON.

---

## Pagination (Implemented)

```python
@classmethod
def _db_query(cls, table, botid, limit=100, offset=0):
    with sqlite3.connect(cls._DB_PATH) as conn:
        rows = conn.execute(
            f"SELECT data FROM {table} WHERE botid = ?"
            f" ORDER BY id DESC LIMIT ? OFFSET ?",
            (str(botid), limit, offset)
        ).fetchall()
    return [json.loads(row[0]) for row in rows]
```

- Default: 100 records, most recent first
- Max: 1000 records per request
- API: `?limit=100&offset=0` query params

---

## Daily Loss Persistence (Implemented)

```python
# sonarft_search.py
def set_botid(self, botid: str) -> None:
    self._botid = botid
    self.daily_loss_accumulated = _load_daily_loss(botid, self._loss_reset_date)

def record_trade_result(self, profit: float):
    self._check_daily_reset()
    if profit < 0:
        self.daily_loss_accumulated += abs(profit)
        if getattr(self, '_botid', None):
            _save_daily_loss(self._botid, self._loss_reset_date, self.daily_loss_accumulated)
```

Process restart mid-day no longer resets the daily loss counter.

---

## Data Retention Policy (Implemented)

```python
@classmethod
def _db_purge(cls, table, botid, keep_last=10_000):
    with sqlite3.connect(cls._DB_PATH) as conn:
        conn.execute(f"""
            DELETE FROM {table}
            WHERE botid = ? AND id NOT IN (
                SELECT id FROM {table} WHERE botid = ?
                ORDER BY id DESC LIMIT ?
            )
        """, (str(botid), str(botid), keep_last))
        conn.commit()

async def purge_history(self, botid, keep_last=10_000):
    await asyncio.to_thread(self._db_purge, 'orders', botid, keep_last)
    await asyncio.to_thread(self._db_purge, 'trades', botid, keep_last)
```

---

## Backup Strategy (Implemented)

```python
@classmethod
def backup_db(cls, dst_path: str) -> None:
    """Hot backup using sqlite3's built-in backup API — safe while DB is in use."""
    src = sqlite3.connect(cls._DB_PATH)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

async def async_backup_db(self, dst_path: str) -> None:
    await asyncio.to_thread(self.backup_db, dst_path)
```

---

## Resolved Issues

| # | Original Issue | Resolution |
|---|---|---|
| 1 | Non-atomic config writes | ✅ `tempfile` + `os.replace` |
| 2 | `[object Object]_parameters.json` | ✅ Deleted |
| 3 | No pagination | ✅ `LIMIT`/`OFFSET` + `ORDER BY id DESC` |
| 4 | SQLite WAL mode not enabled | ✅ `PRAGMA journal_mode=WAL` |
| 5 | Reads block writes | ✅ WAL mode; read lock removed |
| 6 | Daily loss resets on restart | ✅ `daily_loss` table persists across restarts |
| 7 | No retention policy | ✅ `_db_purge` keeps last 10k records |
| 8 | No backup strategy | ✅ `backup_db` via `sqlite3.Connection.backup()` |
| 9 | No timestamp index | ✅ Composite `(botid, timestamp)` indexes |

---

## Remaining Items

| Item | Status |
|---|---|
| Multi-process scaling (PostgreSQL) | ℹ️ Phase 4 — requires architectural change |
| Config file locking between API and bot | ℹ️ Mitigated by atomic writes; full fix requires file locking |
| Backup scheduling | ℹ️ Call `async_backup_db` from a scheduled task or lifespan |

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 07_
_Previous: [Prompt 06 — Error Handling](../error-handling/06-error-handling-logging.md)_
_Next: [Prompt 08 — Performance](../performance/08-performance-optimization.md)_
