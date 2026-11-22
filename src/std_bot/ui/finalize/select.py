"""Step 1: pick the winning date."""

from typing import Self

import discord

from std_bot.timestamps import date_label
from std_bot.ui.finalize.context import FinalizeContext
from std_bot.ui.finalize.time_modal import TimeInputModal


class FinalizeSelectView(discord.ui.View):
    """A drop-down of the poll's dates with their vote counts."""

    def __init__(self, context: FinalizeContext) -> None:
        """Create the view for the poll in `context`."""
        super().__init__(timeout=600)
        self.context = context
        self.date.options = [
            discord.SelectOption(
                label=date_label(timestamp),
                description=f"{len(context.poll.voters(index))} votes",
                value=str(index),
            )
            for index, timestamp in enumerate(context.poll.dates)
        ]

    @discord.ui.select(placeholder="Choose date...")
    async def date(self, interaction: discord.Interaction, select: discord.ui.Select[Self]) -> None:
        """Ask for the event's start time."""
        await interaction.response.send_modal(TimeInputModal(self.context, date_index=int(select.values[0])))
