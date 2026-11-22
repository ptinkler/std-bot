import os
import tempfile

# db.py reads DB_PATH at import time, so point it at a throwaway file before anything imports it.
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="std-bot-tests-"), "polls.db")
os.environ.setdefault("DISCORD_TOKEN", "test-token")

import pytest

from db import Base, engine
from models import active_polls, active_recurring_configs


@pytest.fixture(autouse=True)
def clean_state():
    """Every test starts with empty tables and no in-memory polls."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    active_polls.clear()
    active_recurring_configs.clear()
