import json

from sqlalchemy.orm import Session

from db import Base, PollRow, RecurringPollRow, engine
from models import PollData, RecurringPollConfig


def init_db():
    Base.metadata.create_all(engine)


def save_poll(msg_id: int, poll: PollData):
    data = json.dumps({
        "msg_id": msg_id,
        "event_name": poll.event_name,
        "description": poll.description,
        "creator_id": poll.creator_id,
        "guild_id": poll.guild_id,
        "channel_id": poll.channel_id,
        "dates": poll.dates,
        "votes": {str(k): list(v) for k, v in poll.votes.items()},
        "cannot_attend": list(poll.cannot_attend),
        "allow_cannot_attend": poll.allow_cannot_attend,
        "expected_respondent_ids": poll.expected_respondent_ids,
    })
    with Session(engine) as session:
        row = session.get(PollRow, msg_id)
        if row:
            row.data = data
        else:
            session.add(PollRow(msg_id=msg_id, data=data))
        session.commit()


def delete_poll(msg_id: int):
    with Session(engine) as session:
        row = session.get(PollRow, msg_id)
        if row:
            session.delete(row)
            session.commit()


def save_recurring(config: RecurringPollConfig) -> int:
    with Session(engine) as session:
        row = RecurringPollRow(
            event_name=config.event_name,
            description=config.description,
            creator_id=config.creator_id,
            guild_id=config.guild_id,
            channel_id=config.channel_id,
            post_weekday=config.post_weekday,
            post_hour=config.post_hour,
            post_minute=config.post_minute,
            post_timezone=config.post_timezone,
            last_posted_week=config.last_posted_week,
            last_poll_msg_id=config.last_poll_msg_id,
            mention_role_id=config.mention_role_id,
            expected_respondents=json.dumps(config.expected_respondent_ids),
            expected_role_id=config.expected_role_id,
            allow_cannot_attend=1 if config.allow_cannot_attend else 0,
            last_reminded_week=config.last_reminded_week,
        )
        session.add(row)
        session.commit()
        return row.id


def delete_recurring(config_id: int):
    with Session(engine) as session:
        row = session.get(RecurringPollRow, config_id)
        if row:
            session.delete(row)
            session.commit()


def update_recurring(config: RecurringPollConfig):
    """Persist all user-editable fields of an existing recurring config."""
    with Session(engine) as session:
        row = session.get(RecurringPollRow, config.id)
        if row:
            row.event_name = config.event_name
            row.description = config.description
            row.post_weekday = config.post_weekday
            row.post_hour = config.post_hour
            row.post_minute = config.post_minute
            row.mention_role_id = config.mention_role_id
            row.expected_respondents = json.dumps(config.expected_respondent_ids)
            row.expected_role_id = config.expected_role_id
            row.allow_cannot_attend = 1 if config.allow_cannot_attend else 0
            session.commit()


def update_recurring_after_post(config_id: int, week_str: str, msg_id: int):
    with Session(engine) as session:
        row = session.get(RecurringPollRow, config_id)
        if row:
            row.last_posted_week = week_str
            row.last_poll_msg_id = msg_id
            session.commit()


def update_recurring_reminded(config_id: int, week_str: str):
    with Session(engine) as session:
        row = session.get(RecurringPollRow, config_id)
        if row:
            row.last_reminded_week = week_str
            session.commit()


def load_recurring_polls() -> list[RecurringPollConfig]:
    with Session(engine) as session:
        rows = session.query(RecurringPollRow).all()
        return [
            RecurringPollConfig(
                id=row.id,
                event_name=row.event_name,
                description=row.description,
                creator_id=row.creator_id,
                guild_id=row.guild_id,
                channel_id=row.channel_id,
                post_weekday=row.post_weekday,
                post_hour=row.post_hour,
                post_minute=row.post_minute,
                post_timezone=row.post_timezone,
                last_posted_week=row.last_posted_week,
                last_poll_msg_id=row.last_poll_msg_id,
                mention_role_id=row.mention_role_id,
                expected_respondent_ids=json.loads(row.expected_respondents) if row.expected_respondents else [],
                expected_role_id=row.expected_role_id,
                allow_cannot_attend=bool(row.allow_cannot_attend),
                last_reminded_week=row.last_reminded_week,
            )
            for row in rows
        ]


def load_polls() -> list[tuple[int, PollData]]:
    with Session(engine) as session:
        rows = session.query(PollRow).all()
    result = []
    for row in rows:
        d = json.loads(row.data)
        poll = PollData(
            event_name=d["event_name"],
            description=d["description"],
            creator_id=d["creator_id"],
            guild_id=d["guild_id"],
            channel_id=d["channel_id"],
            dates=d["dates"],
            votes={int(k): set(v) for k, v in d["votes"].items()},
            cannot_attend=set(d.get("cannot_attend", [])),
            allow_cannot_attend=d.get("allow_cannot_attend", True),
            expected_respondent_ids=d.get("expected_respondent_ids", []),
        )
        result.append((row.msg_id, poll))
    return result
