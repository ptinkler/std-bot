"""Settings read from the environment."""

import os
from pathlib import Path

DEFAULT_DB_PATH = "/data/polls.db"


class MissingTokenError(RuntimeError):
    """DISCORD_TOKEN is not set."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("DISCORD_TOKEN environment variable not found")


def discord_token() -> str:
    """Return the bot token, or raise if it is not configured."""
    token = os.getenv("DISCORD_TOKEN")
    if token is None:
        raise MissingTokenError
    return token


def database_path() -> Path:
    """Return where the SQLite database lives."""
    return Path(os.getenv("DB_PATH", DEFAULT_DB_PATH))
