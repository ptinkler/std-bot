"""Lookups on a Discord guild."""

import discord


def resolve_expected_ids(guild: discord.Guild | None, role_id: int | None, user_ids: list[int]) -> list[int]:
    """Return the expected respondents: the listed users plus the non-bot members of the role, sorted."""
    ids = set(user_ids)
    if role_id and guild is not None:
        role = guild.get_role(role_id)
        if role is not None:
            ids |= {member.id for member in role.members if not member.bot}
    return sorted(ids)
