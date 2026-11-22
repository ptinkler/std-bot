"""Writing a backup and the loop that runs it."""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from discord.ext import tasks

from std_bot.backup.files import PREFIX, SUFFIX, is_due, prune
from std_bot.backup.settings import SECONDS_PER_HOUR, backup_dir, interval_seconds, keep_count
from std_bot.database.engine import get_engine

log = logging.getLogger(__name__)

# How often to ask "is a backup due?", so a restart never skips or doubles one.
CHECK_EVERY_HOURS = 1


def run_backup(directory: Path, keep: int) -> Path:
    """Write one backup, then prune.

    The copy goes to a temporary name first, so a crash never leaves a half-written
    file that looks real. SQLite's own `VACUUM INTO` keeps it consistent while the bot writes.

    Returns:
        The path of the new backup.
    """
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / f"{PREFIX}{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}{SUFFIX}"
    partial = final.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    with get_engine().connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.exec_driver_sql("VACUUM INTO ?", (str(partial),))
    partial.replace(final)
    prune(directory, keep)
    return final


@tasks.loop(hours=CHECK_EVERY_HOURS)
async def backup_loop() -> None:
    """Take a backup if the newest one is older than the interval."""
    directory = backup_dir()
    try:
        if is_due(directory, interval_seconds()):
            path = await asyncio.to_thread(run_backup, directory, keep_count())
            log.info("database backup: %s", path.name)
    except Exception:
        log.exception("database backup failed")


def start_backups() -> None:
    """Start the backup loop unless backups are off or it is already running."""
    if not interval_seconds():
        log.info("database backups are off (BACKUP_INTERVAL_HOURS=0)")
        return
    if not backup_loop.is_running():
        backup_loop.start()
        log.info(
            "database backups every %g h, keeping %d, in %s",
            interval_seconds() / SECONDS_PER_HOUR,
            keep_count(),
            backup_dir(),
        )
