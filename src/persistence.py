import json

from sqlalchemy.orm import Session

from db import Base, PollRow, engine
from models import PollData


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
        )
        result.append((row.msg_id, poll))
    return result
