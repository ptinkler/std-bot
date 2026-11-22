"""Builders for domain objects and fake Discord objects."""

from dataclasses import fields, replace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData
from std_bot.domain.recurring import RecurringPollConfig, RecurringPollDraft

_DRAFT_FIELDS = {field.name for field in fields(RecurringPollDraft)}


def make_poll(**changes: Any) -> PollData:
    """Return a poll with two dates, overriding fields with `changes`."""
    base = PollData(
        event_name="Game night",
        creator_id=1,
        guild_id=2,
        channel_id=3,
        dates=[1_000_000, 1_086_400],
    )
    return replace(base, **changes)


def make_draft(**changes: Any) -> RecurringPollDraft:
    """Return an unsaved recurring poll for Fridays at 18:00 UTC, overriding fields with `changes`."""
    base = RecurringPollDraft(
        event_name="Weekly",
        description="d",
        creator_id=1,
        guild_id=2,
        channel_id=3,
        post_weekday=4,
        post_hour=18,
        post_minute=0,
        post_timezone="UTC",
        expected_respondent_ids=[10, 11],
    )
    return replace(base, **changes)


def make_config(config_id: int = 1, **changes: Any) -> RecurringPollConfig:
    """Return a saved-looking recurring poll (it is not written to the database), overriding fields with `changes`."""
    draft = make_draft(**{name: value for name, value in changes.items() if name in _DRAFT_FIELDS})
    progress = {name: value for name, value in changes.items() if name not in _DRAFT_FIELDS}
    progress = {
        name: changes[name]
        for name in ("last_posted_week", "last_poll_msg_id", "last_reminded_week")
        if name in changes
    }
    fields = {**vars(draft), **progress}
    return RecurringPollConfig(id=config_id, **fields)


def make_interaction(user_id: int = 1, *, message_id: int = 555, manage_guild: bool = False) -> Any:
    """Return a fake interaction whose responses can be awaited and inspected."""
    interaction = MagicMock()
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = user_id
    interaction.user.guild_permissions.manage_guild = manage_guild
    interaction.guild_id = 2
    interaction.channel_id = 3
    interaction.message.id = message_id
    interaction.message.delete = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.edit_message = AsyncMock()
    interaction.response.send_modal = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


def make_channel(msg_id: int = 777) -> Any:
    """Return a fake text channel; `send` returns a message with id `msg_id`."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=MagicMock(id=msg_id))
    channel.fetch_message = AsyncMock()
    return channel


def make_guild(channel: Any, role_members: tuple[int, ...] = ()) -> Any:
    """Return a fake guild that has `channel` and a role whose non-bot members are `role_members`."""
    guild = MagicMock(spec=discord.Guild)
    role = MagicMock()
    role.members = [MagicMock(id=user_id, bot=False) for user_id in role_members]
    guild.get_channel.return_value = channel
    guild.get_role.return_value = role
    return guild


def serve_guild(bot: StdBot, monkeypatch: pytest.MonkeyPatch, guild: Any) -> None:
    """Make `bot.get_guild` return `guild` whatever id is asked for."""

    def get_guild(_guild_id: int) -> Any:
        return guild

    monkeypatch.setattr(bot, "get_guild", get_guild)
