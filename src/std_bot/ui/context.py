"""What a command or modal needs to know about where it was used."""

from dataclasses import dataclass

import discord


@dataclass(frozen=True)
class GuildContext:
    """The server, channel and user of an interaction.

    Attributes:
        guild_id: Server the interaction came from.
        channel_id: Channel it came from.
        user_id: User who triggered it.
    """

    guild_id: int
    channel_id: int
    user_id: int


async def require_guild_context(interaction: discord.Interaction) -> GuildContext | None:
    """Return where the interaction happened, or tell the user and return None if it was not in a server channel."""
    if interaction.guild_id is None or interaction.channel_id is None:
        await interaction.response.send_message("This only works in a server channel.", ephemeral=True)
        return None
    return GuildContext(interaction.guild_id, interaction.channel_id, interaction.user.id)
