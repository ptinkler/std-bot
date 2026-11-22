"""Step 2: type the start time."""

import discord

from std_bot.parsing import parse_time
from std_bot.ui.fields import TextField
from std_bot.ui.finalize.context import FinalizeContext
from std_bot.ui.finalize.timezone import TimezoneSelectView


class TimeInputModal(discord.ui.Modal, title="Set Event Time"):
    """Asks for the start time of the event on the chosen date."""

    event_time = TextField(label="Start time", placeholder="e.g. 19:00 or 7:00 PM", max_length=10)

    def __init__(self, context: FinalizeContext, *, date_index: int) -> None:
        """Create the modal for date number `date_index` of the poll in `context`."""
        super().__init__()
        self.context = context
        self.date_index = date_index

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Parse the time and ask for the timezone."""
        start = parse_time(str(self.event_time))
        if start is None:
            await interaction.response.send_message("Couldn't parse time. Use `19:00` or `7:00 PM`.", ephemeral=True)
            return
        view = TimezoneSelectView(self.context, self.date_index, start)
        await interaction.response.send_message(
            f"Time set to **{self.event_time}**. Now pick your timezone:", view=view, ephemeral=True
        )
