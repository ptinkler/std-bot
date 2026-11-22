"""Persistence of recurring poll configurations."""

import json

from sqlalchemy import select

from std_bot.database.engine import open_session
from std_bot.database.tables import RecurringPollRow
from std_bot.domain.recurring import RecurringPollConfig, RecurringPollDraft


def _write_editable_fields(row: RecurringPollRow, draft: RecurringPollDraft) -> None:
    """Copy the user-editable fields onto a row (used by both create and update)."""
    row.event_name = draft.event_name
    row.description = draft.description
    row.post_weekday = draft.post_weekday
    row.post_hour = draft.post_hour
    row.post_minute = draft.post_minute
    row.mention_role_id = draft.mention_role_id
    row.expected_respondents = json.dumps(draft.expected_respondent_ids)
    row.expected_role_id = draft.expected_role_id
    row.allow_cannot_attend = draft.allow_cannot_attend
    row.reminder_days_before = draft.reminder_days_before


def _config_from_row(row: RecurringPollRow) -> RecurringPollConfig:
    return RecurringPollConfig(
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
        allow_cannot_attend=row.allow_cannot_attend,
        reminder_days_before=row.reminder_days_before,
        last_reminded_week=row.last_reminded_week,
    )


def save_recurring(draft: RecurringPollDraft) -> RecurringPollConfig:
    """Insert a new recurring poll and return it with its database id."""
    with open_session() as session:
        row = RecurringPollRow(
            creator_id=draft.creator_id,
            guild_id=draft.guild_id,
            channel_id=draft.channel_id,
            post_timezone=draft.post_timezone,
        )
        _write_editable_fields(row, draft)
        session.add(row)
        session.commit()
        return _config_from_row(row)


def update_recurring(config: RecurringPollConfig) -> None:
    """Persist all user-editable fields of an existing recurring poll."""
    with open_session() as session:
        row = session.get(RecurringPollRow, config.id)
        if row:
            _write_editable_fields(row, config)
            session.commit()


def mark_posted(config_id: int, week: str, msg_id: int) -> None:
    """Record that the poll of an ISO week was posted as message `msg_id`."""
    with open_session() as session:
        row = session.get(RecurringPollRow, config_id)
        if row:
            row.last_posted_week = week
            row.last_poll_msg_id = msg_id
            session.commit()


def mark_reminded(config_id: int, week: str) -> None:
    """Record that the reminder for an ISO week was handled."""
    with open_session() as session:
        row = session.get(RecurringPollRow, config_id)
        if row:
            row.last_reminded_week = week
            session.commit()


def delete_recurring(config_id: int) -> None:
    """Delete a recurring poll; does nothing if it is not there."""
    with open_session() as session:
        row = session.get(RecurringPollRow, config_id)
        if row:
            session.delete(row)
            session.commit()


def load_recurring() -> dict[int, RecurringPollConfig]:
    """Return every recurring poll by id."""
    with open_session() as session:
        return {row.id: _config_from_row(row) for row in session.scalars(select(RecurringPollRow))}
