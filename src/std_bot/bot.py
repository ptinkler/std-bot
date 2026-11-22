"""The Discord client."""

from collections.abc import Awaitable, Callable
from typing import Self

import discord
from discord import app_commands

from std_bot.state import BotState


class StdBot(discord.Client):
    """The bot: a Discord client with a slash-command tree, the tracked polls, and a one-time setup step.

    Attributes:
        tree: Slash commands.
        state: Polls and recurring configs currently tracked in memory.
    """

    def __init__(self, setup: Callable[[Self], Awaitable[None]]) -> None:
        """Create the client; `setup` runs once, after login and before the gateway connects."""
        intents = discord.Intents.default()
        # Needed to read role membership for expected-respondent reminders.
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.state = BotState()
        self._setup = setup

    async def setup_hook(self) -> None:
        """Run the one-time setup."""
        await self._setup(self)
