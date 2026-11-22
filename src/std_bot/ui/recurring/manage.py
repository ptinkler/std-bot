"""Listing recurring polls, then editing or cancelling one."""

import logging
from typing import Self

import discord

from std_bot.bot import StdBot
from std_bot.domain.recurring import RecurringPollConfig
from std_bot.domain.schedule import WEEKDAY_NAMES
from std_bot.storage.recurring import delete_recurring
from std_bot.ui.permissions import can_manage
from std_bot.ui.recurring.edit_view import RecurringEditView
from std_bot.ui.text import clock

log = logging.getLogger(__name__)

MAX_LABEL_LENGTH = 100


class ManageRecurringView(discord.ui.View):
    """A drop-down of this server's recurring polls with Edit and Cancel buttons."""

    def __init__(self, bot: StdBot, configs: list[RecurringPollConfig]) -> None:
        """Create the view listing `configs`."""
        super().__init__(timeout=120)
        self.bot = bot
        self.configs = {config.id: config for config in configs}
        self.selected: RecurringPollConfig | None = None
        self.poll_select.options = [
            discord.SelectOption(
                label=config.event_name[:MAX_LABEL_LENGTH],
                description=(
                    f"Every {WEEKDAY_NAMES[config.post_weekday]} at {clock(config.post_hour, config.post_minute)}"
                ),
                value=str(config.id),
            )
            for config in configs
        ]

    @discord.ui.select(placeholder="Select recurring poll...", row=0)
    async def poll_select(self, interaction: discord.Interaction, select: discord.ui.Select[Self]) -> None:
        """Select a recurring poll and enable the buttons."""
        config = self.configs[int(select.values[0])]
        self.selected = config
        self.edit.disabled = False
        self.cancel.disabled = False
        for option in select.options:
            option.default = option.value == str(config.id)
        await interaction.response.edit_message(
            content=(
                f"Selected: **{config.event_name}** — every {WEEKDAY_NAMES[config.post_weekday]} "
                f"at {clock(config.post_hour, config.post_minute)}"
            ),
            view=self,
        )

    @discord.ui.button(label="Edit Respondents / Options", style=discord.ButtonStyle.primary, disabled=True, row=1)
    async def edit(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Open the options form for the selected poll."""
        config = self.selected
        if config is None or not can_manage(interaction, config.creator_id):
            await interaction.response.send_message(
                "Only the poll creator or a server admin can edit this.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content=f"Editing **{config.event_name}** — set expected respondents and options, then Save:",
            view=RecurringEditView(self.bot, config),
        )

    @discord.ui.button(label="Cancel This Recurring Poll", style=discord.ButtonStyle.danger, disabled=True, row=2)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Delete the selected recurring poll."""
        config = self.selected
        if config is None or not can_manage(interaction, config.creator_id):
            await interaction.response.send_message(
                "Only the poll creator or a server admin can cancel this.", ephemeral=True
            )
            return
        delete_recurring(config.id)
        self.bot.state.recurring.pop(config.id, None)
        log.info("recurring poll cancelled id=%d name=%s", config.id, config.event_name)
        await interaction.response.edit_message(
            content=f"✅ Recurring poll **{config.event_name}** cancelled.", view=None
        )
