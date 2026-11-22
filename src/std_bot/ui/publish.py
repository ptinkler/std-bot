"""Posting a poll message and keeping it up to date."""

from contextlib import suppress

import discord

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData
from std_bot.embeds import build_poll_embed
from std_bot.polls.lifecycle import track_poll
from std_bot.ui.poll_view import PollView


async def publish_poll(
    bot: StdBot, channel: discord.abc.Messageable, poll: PollData, *, content: str | None = None
) -> int:
    """Post a poll, track and store it, and register its buttons so they survive a restart.

    Returns:
        The id of the new message.
    """
    view = PollView(bot, poll)
    message = await channel.send(content=content, embed=build_poll_embed(poll), view=view)
    track_poll(bot.state, message.id, poll)
    bot.add_view(view, message_id=message.id)
    return message.id


async def refresh_poll_message(bot: StdBot, channel: discord.abc.Messageable, msg_id: int, poll: PollData) -> None:
    """Re-render an existing poll message with fresh buttons, ignoring a message that is gone."""
    view = PollView(bot, poll)
    with suppress(discord.HTTPException):
        message = await channel.fetch_message(msg_id)
        await message.edit(embed=build_poll_embed(poll), view=view)
        bot.add_view(view, message_id=msg_id)
