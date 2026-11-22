"""Step 3: pick the timezone the time was given in."""

from datetime import UTC, datetime, time
from typing import Self
from zoneinfo import ZoneInfo

import discord

from std_bot.domain.timezones import TIMEZONES
from std_bot.ui.finalize.context import FinalizeContext
from std_bot.ui.finalize.location import LocationView


class TimezoneSelectView(discord.ui.View):
    """A drop-down of common timezones."""

    def __init__(self, context: FinalizeContext, date_index: int, start: time) -> None:
        """Create the view for the given date and start time of the poll in `context`."""
        super().__init__(timeout=600)
        self.context = context
        self.date_index = date_index
        self.start = start
        self.zone.options = [discord.SelectOption(label=label, value=iana) for iana, label in TIMEZONES]

    @discord.ui.select(placeholder="Select timezone...")
    async def zone(self, interaction: discord.Interaction, select: discord.ui.Select[Self]) -> None:
        """Work out the event's timestamp and ask for a voice channel."""
        zone = ZoneInfo(select.values[0])
        date = datetime.fromtimestamp(self.context.poll.dates[self.date_index], tz=UTC)
        start = datetime(date.year, date.month, date.day, self.start.hour, self.start.minute, tzinfo=zone)
        event_ts = int(start.timestamp())
        await interaction.response.edit_message(
            content=f"<t:{event_ts}:F> — pick a voice channel or skip straight to Create:",
            view=LocationView(self.context, event_ts),
        )
