"""Persistence of open polls."""

import json
from typing import TypedDict

from std_bot.database.engine import open_session
from std_bot.database.tables import PollRow
from std_bot.domain.poll import PollData


class _PollCore(TypedDict):
    """The keys every stored poll has."""

    event_name: str
    description: str
    creator_id: int
    guild_id: int
    channel_id: int
    dates: list[int]
    votes: dict[str, list[int]]


class PollRecord(_PollCore):
    """A poll as written to the `polls.data` column."""

    cannot_attend: list[int]
    allow_cannot_attend: bool
    expected_respondent_ids: list[int]


class StoredPoll(_PollCore, total=False):
    """A poll as read back: rows written by older versions lack the newer keys."""

    cannot_attend: list[int]
    allow_cannot_attend: bool
    expected_respondent_ids: list[int]


def _encode(poll: PollData) -> str:
    record = PollRecord(
        event_name=poll.event_name,
        description=poll.description,
        creator_id=poll.creator_id,
        guild_id=poll.guild_id,
        channel_id=poll.channel_id,
        dates=poll.dates,
        votes={str(index): sorted(voters) for index, voters in poll.votes.items()},
        cannot_attend=sorted(poll.cannot_attend),
        allow_cannot_attend=poll.allow_cannot_attend,
        expected_respondent_ids=poll.expected_respondent_ids,
    )
    return json.dumps(record)


def _decode(raw: str) -> PollData:
    record: StoredPoll = json.loads(raw)
    return PollData(
        event_name=record["event_name"],
        description=record["description"],
        creator_id=record["creator_id"],
        guild_id=record["guild_id"],
        channel_id=record["channel_id"],
        dates=record["dates"],
        votes={int(index): set(voters) for index, voters in record["votes"].items()},
        cannot_attend=set(record.get("cannot_attend", [])),
        allow_cannot_attend=record.get("allow_cannot_attend", True),
        expected_respondent_ids=record.get("expected_respondent_ids", []),
    )


def save_poll(msg_id: int, poll: PollData) -> None:
    """Insert or update the poll posted as message `msg_id`."""
    with open_session() as session:
        row = session.get(PollRow, msg_id)
        if row:
            row.data = _encode(poll)
        else:
            session.add(PollRow(msg_id=msg_id, data=_encode(poll)))
        session.commit()


def delete_poll(msg_id: int) -> None:
    """Delete a stored poll; does nothing if it is not there."""
    with open_session() as session:
        row = session.get(PollRow, msg_id)
        if row:
            session.delete(row)
            session.commit()


def load_polls() -> dict[int, PollData]:
    """Return every stored poll by message id."""
    with open_session() as session:
        return {row.msg_id: _decode(row.data) for row in session.query(PollRow)}
