"""Table definitions."""

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class of all tables."""


class PollRow(Base):
    """An open poll: its message id and the poll serialised as JSON."""

    __tablename__ = "polls"

    msg_id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[str] = mapped_column(String)


class RecurringPollRow(Base):
    """A weekly recurring poll configuration."""

    __tablename__ = "recurring_polls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    creator_id: Mapped[int]
    guild_id: Mapped[int]
    channel_id: Mapped[int]
    post_weekday: Mapped[int]
    post_hour: Mapped[int]
    post_minute: Mapped[int]
    post_timezone: Mapped[str] = mapped_column(String)
    last_posted_week: Mapped[str | None] = mapped_column(String)
    last_poll_msg_id: Mapped[int | None]
    mention_role_id: Mapped[int | None]
    expected_respondents: Mapped[str | None] = mapped_column(String)
    expected_role_id: Mapped[int | None]
    allow_cannot_attend: Mapped[bool] = mapped_column(default=True)
    reminder_days_before: Mapped[int] = mapped_column(default=1)
    last_reminded_week: Mapped[str | None] = mapped_column(String)
