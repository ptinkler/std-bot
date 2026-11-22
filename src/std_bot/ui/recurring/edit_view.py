"""Editing the options of a saved recurring poll."""

import logging
from typing import Self

import discord

from std_bot.bot import StdBot
from std_bot.domain.recurring import RecurringPollConfig
from std_bot.guilds import resolve_expected_ids
from std_bot.storage.polls import save_poll
from std_bot.storage.recurring import update_recurring
from std_bot.ui.publish import refresh_poll_message
from std_bot.ui.recurring.edit_modal import RecurringScheduleEditModal
from std_bot.ui.recurring.options import RecurringOptionsView
from std_bot.ui.text import describe_reminded, on_off

log = logging.getLogger(__name__)


class RecurringEditView(RecurringOptionsView):
    """The options form that updates a saved recurring poll, with a button to edit its name and schedule."""

    def __init__(self, bot: StdBot, config: RecurringPollConfig) -> None:
        """Create the view for `config`."""
        super().__init__(bot, config, commit_label="Save Changes")
        self.config = config

    @discord.ui.button(label="Edit Name & Schedule", style=discord.ButtonStyle.secondary, row=3)
    async def schedule(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Open the name-and-schedule form."""
        await interaction.response.send_modal(RecurringScheduleEditModal(self.config))

    async def _sync_open_poll(self) -> None:
        """Apply the new expected set and can't-attend option to the poll that is open right now, if any."""
        msg_id = self.config.last_poll_msg_id
        poll = self.bot.state.polls.get(msg_id) if msg_id is not None else None
        if msg_id is None or poll is None:
            return
        guild = self.bot.get_guild(self.config.guild_id)
        poll.expected_respondent_ids = resolve_expected_ids(
            guild, self.config.expected_role_id, self.config.expected_respondent_ids
        )
        poll.allow_cannot_attend = self.config.allow_cannot_attend
        save_poll(msg_id, poll)
        channel = guild.get_channel(self.config.channel_id) if guild else None
        if isinstance(channel, discord.abc.Messageable):
            await refresh_poll_message(self.bot, channel, msg_id, poll)

    async def commit(self, interaction: discord.Interaction) -> None:
        """Save the options, update the open poll and confirm."""
        update_recurring(self.config)
        log.info(
            "recurring poll edited id=%s expected_users=%d role=%s",
            self.config.id,
            len(self.config.expected_respondent_ids),
            self.config.expected_role_id,
        )
        await self._sync_open_poll()
        who = describe_reminded(self.config.expected_respondent_ids, self.config.expected_role_id)
        await interaction.response.edit_message(
            content=(
                f"✅ Updated **{self.config.event_name}** — "
                f"reminders: {' and '.join(who) or 'nobody (reminders off)'}; "
                f"can't-make-any option {on_off(enabled=self.config.allow_cannot_attend)}."
            ),
            view=None,
        )
