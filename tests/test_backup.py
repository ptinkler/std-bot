"""Scheduled database backups."""

import os
import sqlite3
import time
from pathlib import Path

import pytest

from std_bot.backup.files import is_due, list_backups, prune
from std_bot.backup.runner import backup_loop, run_backup, start_backups
from std_bot.backup.settings import backup_dir, interval_seconds, keep_count
from std_bot.storage.polls import save_poll
from tests.factories import make_poll

DAY = 24 * 3600


def _touch(directory: Path, name: str, age_seconds: float = 0) -> Path:
    path = directory / name
    path.write_bytes(b"x")
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))
    return path


def test_settings_default_and_read_from_the_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Defaults are daily, keep seven, beside the database; the environment overrides them."""
    for name in ("BACKUP_INTERVAL_HOURS", "BACKUP_KEEP", "BACKUP_DIR"):
        monkeypatch.delenv(name, raising=False)
    assert interval_seconds() == DAY
    assert keep_count() == 7
    assert backup_dir().name == "backups"

    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "0")
    monkeypatch.setenv("BACKUP_KEEP", "0")
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    assert interval_seconds() == 0
    assert keep_count() == 1
    assert backup_dir() == tmp_path


def test_a_bad_interval_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A value that is not a number is ignored."""
    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "banana")
    assert interval_seconds() == DAY


def test_prune_keeps_the_newest(tmp_path: Path) -> None:
    """Older backups go; other files are left alone."""
    names = [f"polls-2026110{i}-000000.db" for i in range(1, 6)]
    for name in names:
        _touch(tmp_path, name)
    (tmp_path / "unrelated.txt").write_text("keep me")
    assert prune(tmp_path, keep=2) == 3
    assert [path.name for path in list_backups(tmp_path)] == names[-2:]
    assert (tmp_path / "unrelated.txt").exists()


def test_is_due(tmp_path: Path) -> None:
    """A backup is due when there is none, or the newest is older than the interval."""
    assert is_due(tmp_path, 3600)
    _touch(tmp_path, "polls-20261101-000000.db", age_seconds=10)
    assert not is_due(tmp_path, 3600)
    _touch(tmp_path, "polls-20261102-000000.db", age_seconds=7200)
    assert is_due(tmp_path, 3600)  # the newest by name is two hours old


def test_run_backup_writes_a_consistent_copy_and_prunes(tmp_path: Path) -> None:
    """The copy contains the stored polls, leaves no partial file and respects `keep`."""
    save_poll(1, make_poll())
    for index in range(1, 4):
        _touch(tmp_path, f"polls-2000010{index}-000000.db")
    final = run_backup(tmp_path, keep=2)
    assert final.parent == tmp_path
    assert not list(tmp_path.glob("*.partial"))
    assert len(list_backups(tmp_path)) == 2
    with sqlite3.connect(final) as connection:
        assert connection.execute("SELECT count(*) FROM polls").fetchone() == (1,)


async def test_start_backups_is_off_when_the_interval_is_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the interval at zero the loop never starts."""
    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "0")
    start_backups()
    assert not backup_loop.is_running()
