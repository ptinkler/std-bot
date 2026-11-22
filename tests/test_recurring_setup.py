"""The recurring-poll setup modal, its confirm view and the schedule parsing both modals share."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from models import RecurringPollConfig, active_recurring_configs
from persistence import load_recurring_polls
from ui import RecurringRoleConfirmView, RecurringSetupModal, _parse_schedule


def _interaction():
    return SimpleNamespace(
        user=SimpleNamespace(id=1),
        guild_id=2,
        channel_id=3,
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock()),
    )


async def test_parse_schedule_accepts_good_input():
    interaction = _interaction()
    schedule = await _parse_schedule(interaction, "Thu", "6:30 PM", "2")
    assert (schedule.weekday, schedule.time.hour, schedule.time.minute, schedule.reminder_days) == (3, 18, 30, 2)
    interaction.response.send_message.assert_not_awaited()


async def test_parse_schedule_names_the_bad_field_and_stops():
    for args, expected in [
        (("someday", "18:00", "1"), "Couldn't parse day"),
        (("Thu", "late", "1"), "Couldn't parse time"),
        (("Thu", "18:00", "9"), "Reminder lead time"),
    ]:
        interaction = _interaction()
        assert await _parse_schedule(interaction, *args) is None
        interaction.response.send_message.assert_awaited_once()
        assert expected in interaction.response.send_message.await_args.args[0]
        assert interaction.response.send_message.await_args.kwargs["ephemeral"] is True


async def test_parse_schedule_appends_the_suffix_to_day_and_time_errors():
    interaction = _interaction()
    await _parse_schedule(interaction, "nope", "18:00", "1", suffix=" No changes saved.")
    assert interaction.response.send_message.await_args.args[0].endswith("No changes saved.")


async def test_setup_modal_hands_a_draft_to_the_confirm_view():
    modal = RecurringSetupModal()
    modal.event_name._value = "Game night"
    modal.post_day._value = "Friday"
    modal.post_time_input._value = "18:00"
    modal.reminder_days_input._value = "2"
    interaction = _interaction()

    await modal.on_submit(interaction)

    view = interaction.response.send_message.await_args.kwargs["view"]
    assert isinstance(view, RecurringRoleConfirmView)
    assert (view.draft.event_name, view.draft.post_weekday, view.draft.post_hour) == ("Game night", 4, 18)
    assert (view.draft.creator_id, view.draft.guild_id, view.draft.channel_id) == (1, 2, 3)
    assert view.draft.reminder_days_before == 2
    assert not active_recurring_configs  # nothing is saved until the user confirms


async def test_confirming_saves_the_draft_with_the_picked_options():
    draft = RecurringPollConfig("Game night", "", 1, 2, 3, 4, 18, 0, "UTC", reminder_days_before=2)
    view = RecurringRoleConfirmView(draft)
    view.selected_role_id, view.expected_ids, view.expected_role_id = 55, [10, 11], 66
    view.allow_cannot_attend = False
    interaction = _interaction()

    await view._on_confirm(interaction)

    [stored] = load_recurring_polls()
    assert stored.id == draft.id
    assert (stored.mention_role_id, stored.expected_respondent_ids, stored.expected_role_id) == (55, [10, 11], 66)
    assert stored.allow_cannot_attend is False
    assert active_recurring_configs[stored.id] is draft
    message = interaction.response.edit_message.await_args.kwargs["content"]
    assert "Pings <@&55>" in message
    assert "2 listed member(s) and everyone in <@&66>" in message
    assert "2 days before each reset" in message
