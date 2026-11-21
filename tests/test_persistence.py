import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from db import PollRow, engine
from models import PollData, RecurringPollConfig
from persistence import (
    delete_poll,
    delete_recurring,
    load_polls,
    load_recurring_polls,
    save_poll,
    save_recurring,
    update_recurring,
    update_recurring_after_post,
    update_recurring_reminded,
)


def _poll():
    return PollData(
        "Game night", "bring snacks", 1, 2, 3, [100, 200],
        votes={0: {10, 11}, 1: set()}, cannot_attend={12}, allow_cannot_attend=False, expected_respondent_ids=[10, 11, 12],
    )  # fmt: skip


def test_poll_round_trip_keeps_everything():
    save_poll(555, _poll())
    [(msg_id, loaded)] = load_polls()
    assert msg_id == 555
    assert loaded == _poll()
    assert isinstance(loaded.votes[0], set)


def test_saving_a_poll_twice_updates_in_place():
    poll = _poll()
    save_poll(555, poll)
    poll.votes[1].add(99)
    save_poll(555, poll)
    [(_, loaded)] = load_polls()
    assert loaded.votes[1] == {99}


def test_delete_poll_and_deleting_a_missing_one():
    save_poll(1, _poll())
    delete_poll(1)
    delete_poll(1)
    assert load_polls() == []


def test_old_poll_rows_without_newer_fields_load_with_defaults():
    legacy = {
        "event_name": "Old", "description": "", "creator_id": 1, "guild_id": 2, "channel_id": 3,
        "dates": [1], "votes": {"0": [5]},
    }  # fmt: skip
    with Session(engine) as session:
        session.add(PollRow(msg_id=9, data=json.dumps(legacy)))
        session.commit()
    [(_, poll)] = load_polls()
    assert poll.cannot_attend == set()
    assert poll.allow_cannot_attend is True
    assert poll.expected_respondent_ids == []


def _config(**kw):
    base = {
        "event_name": "Weekly", "description": "d", "creator_id": 1, "guild_id": 2, "channel_id": 3,
        "post_weekday": 4, "post_hour": 18, "post_minute": 30, "post_timezone": "Europe/London",
        "mention_role_id": 7, "expected_respondent_ids": [1, 2], "expected_role_id": 8,
        "allow_cannot_attend": False, "reminder_days_before": 2,
    }  # fmt: skip
    return RecurringPollConfig(**{**base, **kw})


def test_recurring_round_trip_assigns_an_id():
    new_id = save_recurring(_config())
    [loaded] = load_recurring_polls()
    assert loaded.id == new_id
    assert loaded == _config(id=new_id)


def test_recurring_edit_updates_user_editable_fields_only():
    config = _config()
    config.id = save_recurring(config)
    config.event_name = "Renamed"
    config.post_weekday = 1
    config.expected_respondent_ids = [9]
    config.allow_cannot_attend = True
    config.reminder_days_before = 3
    config.post_timezone = "Asia/Tokyo"  # not editable through update_recurring
    update_recurring(config)
    [loaded] = load_recurring_polls()
    assert (loaded.event_name, loaded.post_weekday, loaded.expected_respondent_ids) == ("Renamed", 1, [9])
    assert (loaded.allow_cannot_attend, loaded.reminder_days_before) == (True, 3)
    assert loaded.post_timezone == "Europe/London"


def test_recurring_progress_markers():
    config_id = save_recurring(_config())
    update_recurring_after_post(config_id, "2026-W47", 4242)
    update_recurring_reminded(config_id, "2026-W48")
    [loaded] = load_recurring_polls()
    assert (loaded.last_posted_week, loaded.last_poll_msg_id, loaded.last_reminded_week) == ("2026-W47", 4242, "2026-W48")


def test_recurring_with_nothing_expected_and_zero_reminder_days():
    config_id = save_recurring(_config(expected_respondent_ids=[], expected_role_id=None))
    with engine.begin() as conn:
        conn.execute(text("UPDATE recurring_polls SET expected_respondents = NULL, reminder_days_before = 0"))
    [loaded] = load_recurring_polls()
    assert loaded.id == config_id
    assert loaded.expected_respondent_ids == []
    assert loaded.reminder_days_before == 1  # 0 falls back to the default


def test_delete_recurring():
    config_id = save_recurring(_config())
    delete_recurring(config_id)
    delete_recurring(config_id)
    assert load_recurring_polls() == []
