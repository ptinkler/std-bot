"""Step 5: create the Discord scheduled event and close the poll."""

import logging
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import discord

from std_bot.domain.poll import PollData
from std_bot.embeds import build_finalized_poll_embed
from std_bot.polls.lifecycle import untrack_poll
from std_bot.ui.finalize.context import FinalizeContext

log = logging.getLogger(__name__)

EVENT_DURATION = timedelta(hours=2)
UNKNOWN_LOCATION = "TBD"


async def _create_event(
    guild: discord.Guild, poll: PollData, event_ts: int, voice_channel: discord.abc.Snowflake | None
) -> discord.ScheduledEvent:
    start = datetime.fromtimestamp(event_ts, tz=UTC)
    if voice_channel is not None:
        return await guild.create_scheduled_event(
            name=poll.event_name,
            description=poll.description,
            start_time=start,
            end_time=start + EVENT_DURATION,
            entity_type=discord.EntityType.voice,
            privacy_level=discord.PrivacyLevel.guild_only,
            channel=voice_channel,
        )
    return await guild.create_scheduled_event(
        name=poll.event_name,
        description=poll.description,
        start_time=start,
        end_time=start + EVENT_DURATION,
        entity_type=discord.EntityType.external,
        privacy_level=discord.PrivacyLevel.guild_only,
        location=UNKNOWN_LOCATION,
    )


async def finalize_poll(
    context: FinalizeContext,
    interaction: discord.Interaction,
    event_ts: int,
    voice_channel: discord.abc.Snowflake | None,
) -> None:
    """Create the scheduled event, mark the poll message as finalised and stop tracking the poll."""
    poll = context.poll
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This only works in a server.", ephemeral=True)
        return
    try:
        event = await _create_event(guild, poll, event_ts, voice_channel)
    except discord.HTTPException as error:
        await interaction.response.send_message(f"Failed to create event: {error}", ephemeral=True)
        return

    channel = guild.get_channel(poll.channel_id)
    if isinstance(channel, discord.abc.Messageable):
        with suppress(discord.HTTPException):
            message = await channel.fetch_message(context.msg_id)
            await message.edit(embed=build_finalized_poll_embed(poll, event_ts), view=None)

    untrack_poll(context.bot.state, context.msg_id)
    log.info("event created: %s", poll.event_name)
    await interaction.response.edit_message(content="✅ Event created!", view=None)
    await interaction.followup.send(f"✅ **{poll.event_name}** scheduled for <t:{event_ts}:F>!\n{event.url}")
