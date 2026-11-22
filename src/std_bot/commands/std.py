"""The /std command."""

import discord

from std_bot.bot import StdBot
from std_bot.ui.poll_type import PollTypeView


def register_std(bot: StdBot) -> None:
    """Add /std to the bot's command tree."""

    @bot.tree.command(
        name="std",
        description="Create a one-time or weekly recurring availability poll. Use /std-help for details.",
    )
    async def std(interaction: discord.Interaction) -> None:
        await interaction.response.send_message("What type of poll?", view=PollTypeView(bot), ephemeral=True)
