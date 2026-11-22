"""The recurring-poll setup modal, its confirm view and the schedule form shared with editing."""

from typing import Any

import discord
import pytest

from std_bot.bot import StdBot
from std_bot.storage.recurring import load_recurring
from std_bot.ui.recurring.confirm import RecurringConfirmView
from std_bot.ui.recurring.schedule_form import (
    DAY_ERROR,
    REMINDER_ERROR,
    TIME_ERROR,
    Schedule,
    ScheduleModal,
    check_schedule,
)
from std_bot.ui.recurring.setup import RecurringSetupModal
from tests.factories import make_draft, make_interaction


def _typed(monkeypatch: pytest.MonkeyPatch, modal: ScheduleModal, **values: str) -> None:
    """Make the modal's text inputs answer with the given text, as after a real submission."""
    answers = {
        id(modal.name_input): values.get("name", ""),
        id(modal.description_input): "",
        id(modal.day_input): values["day"],
        id(modal.time_input): values["time"],
        id(modal.reminder_input): values["reminder"],
    }
    monkeypatch.setattr(discord.ui.TextInput, "value", property(lambda item: answers[id(item)]))


def test_check_schedule_accepts_good_input() -> None:
    """Day, time and reminder are parsed into a schedule."""
    schedule = check_schedule("Thu", "6:30 PM", "2")
    assert isinstance(schedule, Schedule)
    assert (schedule.weekday, schedule.time.hour, schedule.time.minute, schedule.reminder_days) == (3, 18, 30, 2)


@pytest.mark.parametrize(
    ("day", "time_text", "reminder", "expected"),
    [
        ("someday", "18:00", "1", DAY_ERROR),
        ("Thu", "late", "1", TIME_ERROR),
        ("Thu", "18:00", "9", REMINDER_ERROR),
    ],
)
def test_check_schedule_reports_the_first_bad_field(day: str, time_text: str, reminder: str, expected: str) -> None:
    """The message names the field that failed."""
    assert check_schedule(day, time_text, reminder) == expected


async def test_bad_input_is_reported_privately_with_the_suffix(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """The user gets an ephemeral message and nothing else happens."""
    modal = RecurringSetupModal(bot)
    _typed(monkeypatch, modal, day="someday", time="18:00", reminder="1")
    interaction = make_interaction()
    assert await modal.read_schedule(interaction, error_suffix=" No changes saved.") is None
    interaction.response.send_message.assert_awaited_once_with(DAY_ERROR + " No changes saved.", ephemeral=True)


async def test_the_setup_modal_hands_a_draft_to_the_confirm_view(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid input leads to the options view; nothing is saved yet."""
    modal = RecurringSetupModal(bot)
    _typed(monkeypatch, modal, name="Game night", day="Friday", time="18:00", reminder="2")
    interaction = make_interaction()

    await modal.on_submit(interaction)

    view: Any = interaction.response.send_message.await_args.kwargs["view"]
    assert isinstance(view, RecurringConfirmView)
    assert (view.draft.event_name, view.draft.post_weekday, view.draft.post_hour) == ("Game night", 4, 18)
    assert (view.draft.creator_id, view.draft.guild_id, view.draft.channel_id) == (1, 2, 3)
    assert view.draft.reminder_days_before == 2
    assert not bot.state.recurring
    assert not load_recurring()


async def test_confirming_saves_the_draft_with_the_picked_options(bot: StdBot) -> None:
    """The picked role, people and toggle land on the saved config, which is tracked."""
    view = RecurringConfirmView(bot, make_draft(reminder_days_before=2))
    view.mention_role_id, view.expected_ids, view.expected_role_id = 55, [10, 11], 66
    view.allow_cannot_attend = False
    interaction = make_interaction()

    await view.commit_button.callback(interaction)

    [stored] = load_recurring().values()
    assert (stored.mention_role_id, stored.expected_respondent_ids, stored.expected_role_id) == (55, [10, 11], 66)
    assert stored.allow_cannot_attend is False
    assert bot.state.recurring[stored.id] == stored
    message = interaction.response.edit_message.await_args.kwargs["content"]
    assert "Pings <@&55>" in message
    assert "2 listed member(s) and everyone in <@&66>" in message
    assert "2 days before each reset" in message
