"""Step 1 of setting up a recurring poll: name and schedule."""

import discord

from std_bot.bot import StdBot
from std_bot.domain.recurring import RecurringPollDraft
from std_bot.ui.context import require_guild_context
from std_bot.ui.recurring.confirm import RecurringConfirmView
from std_bot.ui.recurring.schedule_form import ScheduleModal
from std_bot.ui.text import describe_post_time


class RecurringSetupModal(ScheduleModal):
    """Asks for the name and schedule, then moves on to the optional roles and people."""

    def __init__(self, bot: StdBot) -> None:
        """Create the form."""
        super().__init__(title="Set Up Weekly Recurring Poll", defaults=None)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Validate the form and show the confirmation view."""
        schedule = await self.read_schedule(interaction)
        if schedule is None:
            return
        context = await require_guild_context(interaction)
        if context is None:
            return
        draft = RecurringPollDraft(
            event_name=str(self.name_input),
            description=str(self.description_input),
            creator_id=context.user_id,
            guild_id=context.guild_id,
            channel_id=context.channel_id,
            post_weekday=schedule.weekday,
            post_hour=schedule.time.hour,
            post_minute=schedule.time.minute,
            post_timezone="UTC",
            reminder_days_before=schedule.reminder_days,
        )
        await interaction.response.send_message(
            f"**{draft.event_name}** — {describe_post_time(draft)}\nOptionally ping a role, then confirm:",
            view=RecurringConfirmView(self.bot, draft),
            ephemeral=True,
        )
