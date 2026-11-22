"""Backup settings from the environment.

BACKUP_INTERVAL_HOURS (default 24; 0 turns backups off), BACKUP_KEEP (default 7) and BACKUP_DIR
(default: a `backups` folder beside the database).
"""

import os
from pathlib import Path

from std_bot.config import database_path

DEFAULT_INTERVAL_HOURS = 24.0
DEFAULT_KEEP = 7
SECONDS_PER_HOUR = 3600


def _number(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, "")))
    except ValueError:
        return default


def interval_seconds() -> float:
    """Return the seconds between backups; 0 means backups are off."""
    return _number("BACKUP_INTERVAL_HOURS", DEFAULT_INTERVAL_HOURS) * SECONDS_PER_HOUR


def keep_count() -> int:
    """Return how many backups to keep (at least 1)."""
    return max(1, int(_number("BACKUP_KEEP", DEFAULT_KEEP)))


def backup_dir() -> Path:
    """Return where backups go: BACKUP_DIR, else a backups folder beside the database."""
    configured = os.getenv("BACKUP_DIR")
    return Path(configured) if configured else database_path().parent / "backups"
