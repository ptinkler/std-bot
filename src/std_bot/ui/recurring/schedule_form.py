"""The name-and-schedule form shared by creating and editing a recurring poll."""

from dataclasses import dataclass
from datetime import time

import discord

from std_bot.domain.recurring import RecurringPollDraft
from std_bot.domain.schedule import POLL_OPEN_DAYS, WEEKDAY_NAMES
from std_bot.parsing import parse_reminder_days, parse_time, parse_weekday
from std_bot.ui.fields import TextField
from std_bot.ui.text import clock

DAY_ERROR = "Couldn't parse day. Use e.g. `Monday`, `Mon`, `Thurs`."
TIME_ERROR = "Couldn't parse time. Use e.g. `18:00`, `1800`, or `6:00 PM`."
REMINDER_ERROR = (
    f"Reminder lead time must be a whole number of days from 1 to {POLL_OPEN_DAYS - 1} "
    f"(the poll is open for {POLL_OPEN_DAYS} days)."
)


@dataclass(frozen=True)
class Schedule:
    """A validated schedule.

    Attributes:
        weekday: Day of the week, 0 = Monday.
        time: Time of day.
        reminder_days: Days before the reset to remind non-responders.
    """

    weekday: int
    time: time
    reminder_days: int


def check_schedule(day: str, time_text: str, reminder: str) -> Schedule | str:
    """Parse the three schedule inputs.

    Returns:
        The schedule, or the message to show for the first input that is not valid.
    """
    weekday = parse_weekday(day)
    if weekday is None:
        return DAY_ERROR
    start = parse_time(time_text)
    if start is None:
        return TIME_ERROR
    reminder_days = parse_reminder_days(reminder)
    if reminder_days is None:
        return REMINDER_ERROR
    return Schedule(weekday, start, reminder_days)


class ScheduleModal(discord.ui.Modal):
    """The five inputs: name, description, day, time and reminder lead time."""

    def __init__(self, *, title: str, defaults: RecurringPollDraft | None) -> None:
        """Create the form, pre-filled from `defaults` when editing."""
        super().__init__(title=title)
        self.name_input = TextField(
            label="Poll Name",
            max_length=100,
            placeholder="e.g. Weekly Game Night",
            default=defaults.event_name if defaults else None,
        )
        self.description_input = TextField(
            label="Description (optional)",
            required=False,
            max_length=300,
            style=discord.TextStyle.paragraph,
            default=defaults.description if defaults else None,
        )
        self.day_input = TextField(
            label="Post on which day?",
            placeholder="e.g. Thursday, Thurs, Thu",
            max_length=20,
            default=WEEKDAY_NAMES[defaults.post_weekday] if defaults else None,
        )
        self.time_input = TextField(
            label="Post at what time? (UTC)",
            placeholder="e.g. 18:00, 1800, or 6:00 PM",
            max_length=15,
            default=clock(defaults.post_hour, defaults.post_minute) if defaults else None,
        )
        self.reminder_input = TextField(
            label="Remind how many days before reset?",
            placeholder=f"1-{POLL_OPEN_DAYS - 1} (whole days)",
            max_length=2,
            default=str(defaults.reminder_days_before if defaults else 1),
        )
        for item in (
            self.name_input,
            self.description_input,
            self.day_input,
            self.time_input,
            self.reminder_input,
        ):
            self.add_item(item)

    async def read_schedule(self, interaction: discord.Interaction, *, error_suffix: str = "") -> Schedule | None:
        """Validate the day, time and reminder inputs.

        On bad input, tells the user which field failed (with `error_suffix` appended) and returns None.
        """
        result = check_schedule(str(self.day_input), str(self.time_input), str(self.reminder_input))
        if isinstance(result, str):
            await interaction.response.send_message(result + error_suffix, ephemeral=True)
            return None
        return result
