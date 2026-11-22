"""Adding every slash command to the bot."""

from std_bot.bot import StdBot
from std_bot.commands.help import register_help
from std_bot.commands.std import register_std


def register_commands(bot: StdBot) -> None:
    """Add all slash commands to the bot's command tree."""
    register_std(bot)
    register_help(bot.tree)
