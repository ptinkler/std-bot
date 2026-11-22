"""Backup files on disk: naming, listing, pruning and the due check."""

import time
from pathlib import Path

PREFIX = "polls-"
SUFFIX = ".db"


def list_backups(directory: Path) -> list[Path]:
    """Return the backups, oldest first (the timestamp in the name sorts)."""
    return sorted(directory.glob(f"{PREFIX}*{SUFFIX}"))


def prune(directory: Path, keep: int) -> int:
    """Delete all but the newest `keep` backups.

    Returns:
        How many were removed.
    """
    old = list_backups(directory)[:-keep]
    for path in old:
        path.unlink(missing_ok=True)
    return len(old)


def is_due(directory: Path, interval: float) -> bool:
    """Return whether the newest backup is older than `interval` seconds, or there is none."""
    existing = list_backups(directory)
    return not existing or time.time() - existing[-1].stat().st_mtime >= interval
