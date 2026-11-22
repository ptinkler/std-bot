"""The SQLAlchemy engine and sessions."""

from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from std_bot.config import database_path


@cache
def get_engine() -> Engine:
    """Return the engine for the configured database, created on first use."""
    return create_engine(f"sqlite:///{database_path()}", connect_args={"check_same_thread": False})


def open_session() -> Session:
    """Open a session on the shared engine; use it as a context manager."""
    return Session(get_engine())
