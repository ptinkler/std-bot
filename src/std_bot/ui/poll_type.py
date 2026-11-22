"""The first screen of /std: one-time, recurring, or manage recurring polls."""

from typing import Self

import discord

from std_bot.bot import StdBot
from std_bot.ui.one_time import EventModal
from std_bot.ui.recurring.manage import ManageRecurringView
from std_bot.ui.recurring.setup import RecurringSetupModal


class PollTypeView(discord.ui.View):
    """Buttons for choosing what to do."""

    def __init__(self, bot: StdBot) -> None:
        """Create the view."""
        super().__init__(timeout=120)
        self.bot = bot

    @discord.ui.button(label="One-time Poll", style=discord.ButtonStyle.primary, row=0)
    async def one_time(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Start creating a one-time poll."""
        await interaction.response.send_modal(EventModal(self.bot))

    @discord.ui.button(label="Weekly Recurring Poll", style=discord.ButtonStyle.secondary, row=0)
    async def recurring(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Start setting up a weekly recurring poll."""
        await interaction.response.send_modal(RecurringSetupModal(self.bot))

    @discord.ui.button(label="Manage Recurring Polls", style=discord.ButtonStyle.danger, row=1)
    async def manage(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """List this server's recurring polls."""
        configs = [config for config in self.bot.state.recurring.values() if config.guild_id == interaction.guild_id]
        if not configs:
            await interaction.response.send_message("No recurring polls set up in this server.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Manage recurring polls:", view=ManageRecurringView(self.bot, configs), ephemeral=True
        )
