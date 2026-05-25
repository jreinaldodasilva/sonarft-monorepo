"""
SonarFT Bot — Path constants.

Single source of truth for all filesystem paths used by the bot package.
Import from here instead of redefining _BOT_DIR / _bot_path / _DB_PATH
in each module.
"""
import os

# Absolute path to the bot package directory (the directory containing this file).
# All other paths are anchored here so the bot works regardless of CWD.
BOT_DIR: str = os.path.dirname(os.path.abspath(__file__))

# Default SQLite database path.
DB_PATH: str = os.path.join(BOT_DIR, "sonarftdata", "history", "sonarft.db")


def bot_path(*parts: str) -> str:
    """Return an absolute path anchored to the bot package directory."""
    return os.path.join(BOT_DIR, *parts)
