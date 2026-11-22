"""Step 2 of setting up a recurring poll: options, then save."""

import logging

import discord

from std_bot.bot import StdBot
from std_bot.domain.recurring import RecurringPollDraft
from std_bot.formatting import day_count
from std_bot.storage.recurring import save_recurring
from std_bot.ui.recurring.options import RecurringOptionsView
from std_bot.ui.text import describe_post_time, describe_reminded

log = logging.getLogger(__name__)


class RecurringConfirmView(RecurringOptionsView):
    """The options form that saves a new recurring poll."""

    def __init__(self, bot: StdBot, draft: RecurringPollDraft) -> None:
        """Create the view for a draft that has not been saved yet."""
        super().__init__(bot, draft, commit_label="Confirm & Save")

    async def commit(self, interaction: discord.Interaction) -> None:
        """Save the draft, start tracking it and confirm."""
        config = save_recurring(self.draft)
        self.bot.state.recurring[config.id] = config
        log.info("recurring poll saved id=%d name=%s", config.id, config.event_name)
        role_note = f" Pings <@&{config.mention_role_id}>." if config.mention_role_id else ""
        who = describe_reminded(config.expected_respondent_ids, config.expected_role_id)
        reminder_note = (
            f"\n⏳ Will remind {' and '.join(who)} who haven't responded "
            f"{day_count(config.reminder_days_before)} before each reset."
            if who
            else ""
        )
        await interaction.response.edit_message(
            content=f"✅ **{config.event_name}** saved! Posts {describe_post_time(config)} in this channel."
            f"{role_note}{reminder_note}",
            view=None,
        )
