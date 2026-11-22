"""Shared fixtures: a throwaway database per test and a bot that never connects."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from std_bot.bot import StdBot
from std_bot.database.engine import get_engine
from std_bot.database.tables import Base


@pytest.fixture(autouse=True)
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point the bot at an empty database that lives only for the test."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "polls.db"))
    get_engine.cache_clear()
    Base.metadata.create_all(get_engine())
    yield
    get_engine().dispose()
    get_engine.cache_clear()


async def _no_setup(_bot: StdBot) -> None:
    """Skip the one-time setup, which would start loops and sync commands."""


@pytest.fixture
def bot() -> StdBot:
    """Return a bot with empty state that is never logged in."""
    return StdBot(_no_setup)
