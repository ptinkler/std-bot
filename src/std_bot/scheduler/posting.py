"""Posting the weekly poll of a recurring config."""

import logging
from contextlib import suppress
from datetime import datetime

import discord

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData
from std_bot.domain.recurring import RecurringPollConfig
from std_bot.domain.schedule import next_week_dates
from std_bot.embeds import build_closed_poll_embed
from std_bot.guilds import resolve_expected_ids
from std_bot.polls.lifecycle import untrack_poll
from std_bot.storage.recurring import mark_posted
from std_bot.ui.publish import publish_poll

log = logging.getLogger(__name__)


async def _close_previous_poll(bot: StdBot, channel: discord.abc.Messageable, config: RecurringPollConfig) -> None:
    """Replace last week's poll message with a "closed" notice and stop tracking it."""
    msg_id = config.last_poll_msg_id
    if msg_id is None:
        return
    old_poll = untrack_poll(bot.state, msg_id)
    if old_poll is None:
        return
    with suppress(discord.HTTPException):
        message = await channel.fetch_message(msg_id)
        await message.edit(embed=build_closed_poll_embed(old_poll), view=None)


async def post_recurring_poll(bot: StdBot, config: RecurringPollConfig, week: str, now: datetime) -> None:
    """Close last week's poll and post this week's, then record it as posted for `week`.

    Does nothing if the server or channel can no longer be found.
    """
    guild = bot.get_guild(config.guild_id)
    channel = guild.get_channel(config.channel_id) if guild else None
    if guild is None or not isinstance(channel, discord.abc.Messageable):
        return

    await _close_previous_poll(bot, channel, config)

    dates = next_week_dates(now)
    poll = PollData(
        event_name=config.event_name,
        description=config.description,
        creator_id=config.creator_id,
        guild_id=config.guild_id,
        channel_id=config.channel_id,
        dates=dates,
        votes={index: set() for index in range(len(dates))},
        allow_cannot_attend=config.allow_cannot_attend,
        expected_respondent_ids=resolve_expected_ids(guild, config.expected_role_id, config.expected_respondent_ids),
    )
    content = f"<@&{config.mention_role_id}>" if config.mention_role_id else None
    msg_id = await publish_poll(bot, channel, poll, content=content)
    mark_posted(config.id, week, msg_id)
    config.last_posted_week = week
    config.last_poll_msg_id = msg_id
    log.info("recurring poll posted: %s week=%s msg=%d", config.event_name, week, msg_id)
