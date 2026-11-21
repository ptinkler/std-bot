import os
import sqlite3
import time

import backup
from models import PollData
from persistence import save_poll


def _touch(directory, name, age_seconds=0):
    path = directory / name
    path.write_bytes(b"x")
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))
    return path


def test_env_settings_and_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("BACKUP_INTERVAL_HOURS", raising=False)
    monkeypatch.delenv("BACKUP_KEEP", raising=False)
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    assert backup.interval_seconds() == 24 * 3600
    assert backup.keep_count() == 7
    assert backup.backup_dir().name == "backups"

    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "0")
    monkeypatch.setenv("BACKUP_KEEP", "0")
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    assert backup.interval_seconds() == 0  # 0 turns backups off
    assert backup.keep_count() == 1  # never fewer than one
    assert backup.backup_dir() == tmp_path

    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "banana")
    assert backup.interval_seconds() == 24 * 3600  # bad value falls back to the default


def test_prune_keeps_the_newest(tmp_path):
    names = [f"polls-2026110{i}-000000.db" for i in range(1, 6)]
    for name in names:
        _touch(tmp_path, name)
    (tmp_path / "unrelated.txt").write_text("keep me")
    assert backup.prune(tmp_path, keep=2) == 3
    assert [p.name for p in backup.list_backups(tmp_path)] == names[-2:]
    assert (tmp_path / "unrelated.txt").exists()


def test_is_due(tmp_path):
    assert backup.is_due(tmp_path, 3600)  # none yet
    _touch(tmp_path, "polls-20261101-000000.db", age_seconds=10)
    assert not backup.is_due(tmp_path, 3600)
    stale = tmp_path / "polls-20261102-000000.db"
    stale.write_bytes(b"x")
    os.utime(stale, (time.time() - 7200, time.time() - 7200))
    assert backup.is_due(tmp_path, 3600)  # the newest by name is two hours old


def test_run_backup_writes_a_consistent_copy_and_prunes(tmp_path):
    save_poll(1, PollData("Game night", "", 1, 2, 3, [100]))
    for i in range(1, 4):
        _touch(tmp_path, f"polls-2000010{i}-000000.db")
    final = backup.run_backup(tmp_path, keep=2)
    assert final.parent == tmp_path
    assert not list(tmp_path.glob("*.partial"))
    assert len(backup.list_backups(tmp_path)) == 2
    with sqlite3.connect(final) as conn:
        assert conn.execute("SELECT count(*) FROM polls").fetchone() == (1,)


async def test_start_backups_is_off_when_interval_is_zero(monkeypatch):
    monkeypatch.setenv("BACKUP_INTERVAL_HOURS", "0")
    backup.start_backups()
    assert not backup._backup_if_due.is_running()
