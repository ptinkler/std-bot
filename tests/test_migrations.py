import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

from db import Base

ROOT = Path(__file__).resolve().parent.parent


def _alembic(db_path, *args):
    import os

    env = {**os.environ, "DB_PATH": str(db_path)}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=ROOT, env=env, capture_output=True, text=True, check=False
    )


def test_migrations_build_the_schema_the_models_expect(tmp_path):
    db_path = tmp_path / "fresh.db"
    result = _alembic(db_path, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    inspector = inspect(create_engine(f"sqlite:///{db_path}"))
    for table in Base.metadata.sorted_tables:
        migrated = {c["name"] for c in inspector.get_columns(table.name)}
        assert migrated == {c.name for c in table.columns}, table.name


def test_models_and_migrations_have_not_drifted(tmp_path):
    db_path = tmp_path / "drift.db"
    assert _alembic(db_path, "upgrade", "head").returncode == 0
    result = _alembic(db_path, "check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_there_is_a_single_migration_head():
    result = _alembic(":memory:", "heads")
    assert result.stdout.count("(head)") == 1, result.stdout
