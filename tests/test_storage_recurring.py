"""Persistence of recurring poll configurations."""

from dataclasses import replace

from sqlalchemy import text

from std_bot.database.engine import get_engine
from std_bot.domain.recurring import RecurringPollConfig
from std_bot.storage.recurring import (
    delete_recurring,
    load_recurring,
    mark_posted,
    mark_reminded,
    save_recurring,
    update_recurring,
)
from tests.factories import make_draft


def _saved() -> RecurringPollConfig:
    return save_recurring(
        make_draft(
            post_minute=30,
            post_timezone="Europe/London",
            mention_role_id=7,
            expected_role_id=8,
            allow_cannot_attend=False,
            reminder_days_before=2,
        )
    )


def test_saving_returns_the_config_with_its_id() -> None:
    """The saved config round-trips through the database unchanged."""
    config = _saved()
    assert load_recurring() == {config.id: config}
    assert config.allow_cannot_attend is False
    assert (config.last_posted_week, config.last_poll_msg_id, config.last_reminded_week) == (None, None, None)


def test_update_changes_user_editable_fields_only() -> None:
    """The timezone and the owner are fixed at creation."""
    config = _saved()
    edited = replace(
        config,
        event_name="Renamed",
        post_weekday=1,
        expected_respondent_ids=[9],
        allow_cannot_attend=True,
        reminder_days_before=3,
        post_timezone="Asia/Tokyo",
    )
    update_recurring(edited)
    loaded = load_recurring()[config.id]
    assert (loaded.event_name, loaded.post_weekday, loaded.expected_respondent_ids) == ("Renamed", 1, [9])
    assert (loaded.allow_cannot_attend, loaded.reminder_days_before) == (True, 3)
    assert loaded.post_timezone == "Europe/London"


def test_progress_markers() -> None:
    """Posting and reminding are recorded separately."""
    config = _saved()
    mark_posted(config.id, "2026-W47", 4242)
    mark_reminded(config.id, "2026-W48")
    loaded = load_recurring()[config.id]
    assert (loaded.last_posted_week, loaded.last_poll_msg_id, loaded.last_reminded_week) == (
        "2026-W47",
        4242,
        "2026-W48",
    )


def test_a_row_with_nothing_expected_loads_with_an_empty_list() -> None:
    """A NULL expected-respondents column means nobody."""
    config = save_recurring(make_draft(expected_respondent_ids=[], expected_role_id=None))
    with get_engine().begin() as connection:
        connection.execute(text("UPDATE recurring_polls SET expected_respondents = NULL"))
    assert load_recurring()[config.id].expected_respondent_ids == []


def test_delete_recurring() -> None:
    """Deleting twice is harmless."""
    config = _saved()
    delete_recurring(config.id)
    delete_recurring(config.id)
    assert load_recurring() == {}
