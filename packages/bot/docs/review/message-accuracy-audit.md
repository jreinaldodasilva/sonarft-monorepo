# Bot Package — Message Accuracy Audit

All issues found during a full review of log messages, docstrings, comments,
and inline documentation against the actual implementation. All items below
have been fixed.

---

## sonarft_bot.py

| # | Location | Issue | Fix |
|---|---|---|---|
| 1 | `create_bot` docstring | Said "starts the bot's main loop" — `create_bot` only initialises; `run_bot()` starts the loop | Removed the false claim |
| 2 | `create_bot` body | `"Initializing Bot manager module..."` logged inside `create_bot`, not inside BotManager | Removed the misleading log line |
| 3 | `apply_parameters` comment | Said "rollback-safe: _validate_parameters raises before propagation" — values are applied *before* validation, not after | Corrected to "Saves old values before applying so they can be restored if validation fails" |
| 4 | `create_botid` return annotation | Declared `-> int` but returns `str(uuid.uuid4())` | Changed to `-> str` |

---

## sonarft_manager.py

| # | Location | Issue | Fix |
|---|---|---|---|
| 5 | `create_bot` docstring | "amd rum the bot" (typo) and claimed it runs the bot — it only creates and stores it | Rewrote docstring; added `library` and `config` parameter docs |
| 6 | `run_bot` docstring | Parameter list contained `sonarft` and `botid` with no descriptions | Replaced with accurate `botid` parameter description |
| 7 | `run_bot` body | `f"Running {sonarft} - {botid}"` logged *before* the `if not sonarft` guard — would print `None` if bot not found | Moved guard before the log |

---

## sonarft_execution.py

| # | Location | Issue | Fix |
|---|---|---|---|
| 8 | `SonarftExecution` class docstring | Referenced "SonarftTrades class" — that class does not exist | Changed to `SonarftSearch` |
| 9 | `_execute_single_trade` docstring | Same wrong "SonarftTrades class" reference | Changed to `SonarftSearch` |
| 10 | `execute_order` simulation block | Computed slippage-adjusted prices (`price * (1 ± slippage)`) but never assigned the result — dead code | Assigned to `latest_price` |
| 11 | `check_balance` | Logged insufficient balance at `logger.info` — should be a warning | Changed to `logger.warning` |

---

## sonarft_indicators.py

| # | Location | Issue | Fix |
|---|---|---|---|
| 12 | `get_short_term_market_trend` docstring | Said "last N trades" — uses OHLCV candles, not trade ticks | Changed to "N OHLCV candles" |
| 13 | `get_price_change` docstring | Same "last N trades" inaccuracy | Changed to "N OHLCV candles" |
| 14 | `get_historical_volume` docstring | Did not mention that `limit` controls how many candles are fetched even though only the last one is returned | Added clarification |

---

## sonarft_api_manager.py

| # | Location | Issue | Fix |
|---|---|---|---|
| 15 | `get_balance` | `# TODO: Finish implementation` — implementation is complete | Removed the TODO |
| 16 | `get_trades_history` | `# TODO: Finish the Implementation - use the since and limit` and docstring said "Get the history" — `since`/`limit` are still not forwarded | Updated TODO and docstring to accurately describe the current state |
| 17 | `wait_for_rate_limit` docstring | Said "no longer called from call_api_method" but framed as "kept for compatibility" — misleading | Reworded to "Kept for backward compatibility. Rate limiting is handled internally by ccxt." |

---

## sonarft_prices.py

| # | Location | Issue | Fix |
|---|---|---|---|
| 18 | `_adjust_market_making` docstring | Listed distinct bull/bear behaviours ("buy cheaper before further drop", etc.) but all three RSI branches in both buy and sell sides apply the *same* spread factor | Replaced with accurate description: all branches apply the same factor; RSI/StochRSI refine the signal only |

---

## trade_processor.py

| # | Location | Issue | Fix |
|---|---|---|---|
| 19 | `process_trade_combination` log | `"(v1009)"` hardcoded string literal in the "NEW TRADE HAS BEEN FOUND" log — `_BOT_VERSION` constant is defined at the top of the file but not used here | Replaced literal with `{_BOT_VERSION}` |
