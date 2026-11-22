"""Reminding expected respondents who have not answered the open poll."""

import logging
from datetime import datetime, timedelta

import discord

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData
from std_bot.domain.recurring import RecurringPollConfig
from std_bot.domain.schedule import iso_week, next_post_datetime
from std_bot.formatting import mention_users
from std_bot.guilds import resolve_expected_ids
from std_bot.storage.recurring import mark_reminded

log = logging.getLogger(__name__)


def _open_poll(bot: StdBot, config: RecurringPollConfig) -> PollData | None:
    """Return the poll to remind about, or None if there is nobody to remind or nothing open."""
    if config.last_poll_msg_id is None:
        return None
    if not config.expected_respondent_ids and config.expected_role_id is None:
        return None
    return bot.state.polls.get(config.last_poll_msg_id)


async def send_reminders(bot: StdBot, config: RecurringPollConfig, now_local: datetime) -> None:
    """Ping the expected respondents who have not responded, once per cycle, when the reminder window opens."""
    poll = _open_poll(bot, config)
    if poll is None:
        return

    next_post = next_post_datetime(config.post_weekday, config.post_hour, config.post_minute, now_local)
    cycle = iso_week(next_post)
    reminder_at = next_post - timedelta(days=config.reminder_days_before)
    if now_local < reminder_at or config.last_reminded_week == cycle:
        return

    guild = bot.get_guild(config.guild_id)
    # Resolve the expected set live so role membership is current at reminder time.
    expected = resolve_expected_ids(guild, config.expected_role_id, config.expected_respondent_ids)
    pending = poll.pending_among(expected)

    # Mark the cycle done even if nobody is pending, so we don't re-check all day.
    config.last_reminded_week = cycle
    mark_reminded(config.id, cycle)
    channel = guild.get_channel(config.channel_id) if guild else None
    if not pending or not isinstance(channel, discord.abc.Messageable):
        return
    await channel.send(
        f"⏰ Reminder for **{config.event_name}** — the poll resets <t:{int(next_post.timestamp())}:R>. "
        f"Please respond (pick dates or 🚫 can't make any): {mention_users(pending)}"
    )
    log.info("reminder sent config=%d pending=%d", config.id, len(pending))
