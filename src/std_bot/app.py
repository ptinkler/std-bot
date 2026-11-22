"""Wiring: configure logging, build the bot and run it."""

import logging

from dotenv import load_dotenv

from std_bot.backup.runner import start_backups
from std_bot.bot import StdBot
from std_bot.commands.register import register_commands
from std_bot.config import discord_token
from std_bot.restore import restore_state
from std_bot.scheduler.loop import RecurringScheduler


async def setup(bot: StdBot) -> None:
    """Restore stored polls, add the commands, start the background jobs and sync the commands."""
    restore_state(bot)
    register_commands(bot)
    RecurringScheduler(bot).start()
    start_backups()
    await bot.tree.sync()


def main() -> None:
    """Configure logging, read the token and run the bot until it is stopped."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    StdBot(setup).run(discord_token())
