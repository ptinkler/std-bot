"""Editing the name and schedule of a saved recurring poll."""

import logging

import discord

from std_bot.domain.recurring import RecurringPollConfig
from std_bot.formatting import day_count
from std_bot.storage.recurring import update_recurring
from std_bot.ui.recurring.schedule_form import ScheduleModal
from std_bot.ui.text import describe_post_time

log = logging.getLogger(__name__)


class RecurringScheduleEditModal(ScheduleModal):
    """The schedule form, pre-filled from a saved recurring poll."""

    def __init__(self, config: RecurringPollConfig) -> None:
        """Create the form for `config`."""
        super().__init__(title="Edit Name & Schedule", defaults=config)
        self.config = config

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Validate the form, save the changes and confirm."""
        schedule = await self.read_schedule(interaction, error_suffix=" No changes saved.")
        if schedule is None:
            return
        self.config.event_name = str(self.name_input)
        self.config.description = str(self.description_input)
        self.config.post_weekday = schedule.weekday
        self.config.post_hour = schedule.time.hour
        self.config.post_minute = schedule.time.minute
        self.config.reminder_days_before = schedule.reminder_days
        update_recurring(self.config)
        log.info("recurring poll schedule edited id=%s", self.config.id)
        await interaction.response.send_message(
            f"✅ **{self.config.event_name}** now posts {describe_post_time(self.config)}, reminding "
            f"non-responders {day_count(schedule.reminder_days)} before each reset. "
            "(Takes effect from the next weekly cycle.)",
            ephemeral=True,
        )
