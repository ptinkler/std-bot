"""Step 4: optionally pick a voice channel, then create the event."""

from typing import Self

import discord

from std_bot.ui.finalize.context import FinalizeContext
from std_bot.ui.finalize.event import finalize_poll


class LocationView(discord.ui.View):
    """A voice-channel picker and the Create button."""

    def __init__(self, context: FinalizeContext, event_ts: int) -> None:
        """Create the view for the event starting at `event_ts` for the poll in `context`."""
        super().__init__(timeout=600)
        self.context = context
        self.event_ts = event_ts
        self.voice_channel: discord.abc.Snowflake | None = None

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="Voice channel (optional)...",
        channel_types=[discord.ChannelType.voice],
        min_values=0,
        max_values=1,
        row=0,
    )
    async def channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect[Self]) -> None:
        """Remember the chosen voice channel."""
        self.voice_channel = select.values[0] if select.values else None
        await interaction.response.defer()

    @discord.ui.button(label="Create Event", style=discord.ButtonStyle.success, row=1)
    async def create(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Create the event."""
        await finalize_poll(self.context, interaction, self.event_ts, self.voice_channel)
