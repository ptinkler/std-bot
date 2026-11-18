"""Scheduled backups of the SQLite database.

Every BACKUP_INTERVAL_HOURS (default 24; 0 turns it off) a consistent copy goes to
<database folder>/backups/polls-<timestamp>.db (or BACKUP_DIR), and all but the newest
BACKUP_KEEP (default 7) are deleted. The copy is made with SQLite's own VACUUM INTO, so it
is consistent even while the bot is writing.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from discord.ext import tasks

from db import DB_PATH, engine

log = logging.getLogger(__name__)

PREFIX = "polls-"
SUFFIX = ".db"
DEFAULT_INTERVAL_HOURS = 24.0
DEFAULT_KEEP = 7
CHECK_EVERY_HOURS = 1  # how often to ask "is a backup due?" (so a restart never skips or doubles one)


def _number_env(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, "")))
    except ValueError:
        return default


def interval_seconds() -> float:
    """Seconds between backups; 0 means backups are off."""
    return _number_env("BACKUP_INTERVAL_HOURS", DEFAULT_INTERVAL_HOURS) * 3600


def keep_count() -> int:
    """How many backups to keep (at least 1)."""
    return max(1, int(_number_env("BACKUP_KEEP", DEFAULT_KEEP)))


def backup_dir() -> Path:
    """Where backups go: BACKUP_DIR, else a backups folder beside the database."""
    return Path(os.getenv("BACKUP_DIR") or Path(DB_PATH).parent / "backups")


def list_backups(directory: Path) -> list[Path]:
    """The backups, oldest first (the timestamp in the name sorts)."""
    return sorted(directory.glob(f"{PREFIX}*{SUFFIX}"))


def prune(directory: Path, keep: int) -> int:
    """Delete all but the newest `keep` backups; returns how many were removed."""
    old = list_backups(directory)[:-keep]
    for path in old:
        path.unlink(missing_ok=True)
    return len(old)


def is_due(directory: Path, interval: float) -> bool:
    """Whether the newest backup is older than the interval (or there is none)."""
    existing = list_backups(directory)
    return not existing or time.time() - existing[-1].stat().st_mtime >= interval


def run_backup(directory: Path, keep: int) -> Path:
    """Write one backup (to a temp name first, so a crash never leaves a half file that looks real), then prune."""
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / f"{PREFIX}{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}{SUFFIX}"
    partial = final.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    raw = engine.raw_connection()
    try:
        raw.driver_connection.execute("VACUUM INTO ?", (str(partial),))
    finally:
        raw.close()
    partial.replace(final)
    prune(directory, keep)
    return final


@tasks.loop(hours=CHECK_EVERY_HOURS)
async def _backup_if_due():
    directory, interval = backup_dir(), interval_seconds()
    try:
        if is_due(directory, interval):
            path = await asyncio.to_thread(run_backup, directory, keep_count())
            log.info("database backup: %s", path.name)
    except Exception:  # a failed backup must not stop the bot or the next attempt
        log.exception("database backup failed")


def start_backups() -> None:
    """Start the backup loop unless disabled or already running."""
    if not interval_seconds():
        log.info("database backups are off (BACKUP_INTERVAL_HOURS=0)")
        return
    if not _backup_if_due.is_running():
        _backup_if_due.start()
        log.info("database backups every %g h, keeping %d, in %s", interval_seconds() / 3600, keep_count(), backup_dir())
