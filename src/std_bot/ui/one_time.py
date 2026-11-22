"""Creating a one-time poll: name it, then pick its dates."""

import logging
from datetime import UTC, datetime
from typing import Self

import discord

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData
from std_bot.domain.schedule import upcoming_days
from std_bot.timestamps import date_label, format_date
from std_bot.ui.context import require_guild_context
from std_bot.ui.fields import TextField
from std_bot.ui.publish import publish_poll
from std_bot.ui.text import cannot_attend_label

log = logging.getLogger(__name__)

MAX_DATES = 20
PICK_DATES_PROMPT = f"Pick dates to include in the poll (up to {MAX_DATES}):"


class EventModal(discord.ui.Modal, title="Create Availability Poll"):
    """Asks for the poll's name and description."""

    event_name = TextField(label="Event Name", max_length=100, placeholder="e.g. Game Night")
    description = TextField(
        label="Description (optional)",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph,
        placeholder="What's this about?",
    )

    def __init__(self, bot: StdBot) -> None:
        """Create the modal."""
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Offer the next days as candidate dates."""
        log.info("poll created: %s", self.event_name)
        days = upcoming_days(datetime.now(UTC))
        view = DateSelectView(self.bot, str(self.event_name), str(self.description), days)
        await interaction.response.send_message(PICK_DATES_PROMPT, view=view, ephemeral=True)


class DateSelectView(discord.ui.View):
    """Pick the candidate dates, choose whether to offer "can't make any", and post the poll."""

    def __init__(self, bot: StdBot, name: str, description: str, days: list[int]) -> None:
        """Create the view offering `days` (midnight timestamps) for the poll `name`."""
        super().__init__(timeout=300)
        self.bot = bot
        self.name = name
        self.description = description
        self.selected: list[int] = []
        self.allow_cannot_attend = True
        self.dates.options = [discord.SelectOption(label=date_label(day), value=str(day)) for day in days]
        self.dates.max_values = min(len(days), MAX_DATES)
        self.cannot_toggle.label = cannot_attend_label(enabled=self.allow_cannot_attend)

    def _prompt(self) -> str:
        lines = "\n".join(format_date(day) for day in self.selected) or "*none yet*"
        return f"{PICK_DATES_PROMPT}\n**Selected:**\n{lines}"

    @discord.ui.select(placeholder="Select dates...", min_values=1, row=0)
    async def dates(self, interaction: discord.Interaction, select: discord.ui.Select[Self]) -> None:
        """Remember the chosen dates and enable the Confirm button."""
        self.selected = sorted(int(value) for value in select.values)
        self.confirm.disabled = False
        await interaction.response.edit_message(content=self._prompt(), view=self)

    @discord.ui.button(style=discord.ButtonStyle.secondary, row=1)
    async def cannot_toggle(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        """Switch the "can't make any" option on or off."""
        self.allow_cannot_attend = not self.allow_cannot_attend
        button.label = cannot_attend_label(enabled=self.allow_cannot_attend)
        await interaction.response.edit_message(content=self._prompt(), view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, disabled=True, row=2)
    async def confirm(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Post the poll in the channel."""
        context = await require_guild_context(interaction)
        if context is None or not isinstance(interaction.channel, discord.abc.Messageable):
            return
        poll = PollData(
            event_name=self.name,
            description=self.description,
            creator_id=context.user_id,
            guild_id=context.guild_id,
            channel_id=context.channel_id,
            dates=self.selected,
            votes={index: set() for index in range(len(self.selected))},
            allow_cannot_attend=self.allow_cannot_attend,
        )
        await publish_poll(self.bot, interaction.channel, poll)
        log.info("poll posted: %s", poll.event_name)
        await interaction.response.edit_message(content="✅ Poll posted!", view=None)
