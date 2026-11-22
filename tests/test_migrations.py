"""The Alembic migrations against the table definitions."""

import sqlite3
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from std_bot.database.engine import get_engine
from std_bot.database.tables import Base

ROOT = Path(__file__).resolve().parent.parent
PREVIOUS_HEAD = "d4e5f6a7b8c9"


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the migrations (via DB_PATH) at a new empty database file."""
    path = tmp_path / "migrated.db"
    monkeypatch.setenv("DB_PATH", str(path))
    get_engine.cache_clear()
    return path


def test_migrations_build_the_schema_the_models_expect(db_path: Path) -> None:
    """Every table and column the models declare exists after upgrading a fresh database."""
    command.upgrade(_config(), "head")
    inspector = inspect(create_engine(f"sqlite:///{db_path}"))
    for table in Base.metadata.sorted_tables:
        migrated = {column["name"] for column in inspector.get_columns(table.name)}
        assert migrated == {column.name for column in table.columns}, table.name


@pytest.mark.usefixtures("db_path")
def test_models_and_migrations_have_not_drifted() -> None:
    """`alembic check` finds no change that still needs a migration."""
    command.upgrade(_config(), "head")
    command.check(_config())


def test_there_is_a_single_migration_head() -> None:
    """Two heads would make `upgrade head` ambiguous."""
    assert len(ScriptDirectory.from_config(_config()).get_heads()) == 1


def test_the_boolean_migration_keeps_existing_values(db_path: Path) -> None:
    """A row written before the column became BOOLEAN keeps its 0/1 value, and the migration reverses cleanly."""
    command.upgrade(_config(), PREVIOUS_HEAD)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO recurring_polls (event_name, description, creator_id, guild_id, channel_id, post_weekday,"
            " post_hour, post_minute, post_timezone, allow_cannot_attend, reminder_days_before)"
            " VALUES ('Weekly', '', 1, 2, 3, 4, 18, 0, 'UTC', 0, 1)"
        )
    command.upgrade(_config(), "head")
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT allow_cannot_attend FROM recurring_polls").fetchone() == (0,)
    columns = inspect(create_engine(f"sqlite:///{db_path}")).get_columns("recurring_polls")
    assert isinstance(next(c["type"] for c in columns if c["name"] == "allow_cannot_attend"), sa.Boolean)
    command.downgrade(_config(), "-1")
