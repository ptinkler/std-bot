"""Who may change a poll."""

import discord


def can_manage(interaction: discord.Interaction, creator_id: int) -> bool:
    """Return whether the user is the creator or can manage the server."""
    user = interaction.user
    return user.id == creator_id or (isinstance(user, discord.Member) and user.guild_permissions.manage_guild)
