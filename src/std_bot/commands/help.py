"""The /std-help command."""

import discord
from discord import app_commands

HELP_FIELDS = (
    (
        "/std → One-time Poll",
        (
            "Creates a poll with selectable dates from the next 25 days.\n"
            "Members click dates to toggle availability.\n"
            "Creator can **Finalize** to pick a date and schedule a Discord event, or **Cancel** to remove the poll."
        ),
    ),
    (
        "/std → Weekly Recurring Poll",
        (
            "Posts a new availability poll automatically every week.\n"
            "You pick: poll name, which weekday to post, what time, and timezone.\n"
            "Optionally ping a role when the poll goes out.\n"
            "Optionally set **expected respondents** — a list of people and/or a whole role. "
            "Anyone expected who hasn't responded ~24h before the poll resets gets an @ping "
            "in the channel.\n"
            "Each poll shows **Mon-Sun of the following week** for members to vote on.\n"
            "The previous week's poll is automatically closed when the new one posts."
        ),
    ),
    (
        '🚫 "Can\'t make any" option',
        (
            "Both poll types can offer a **Can't make any** button (toggle it on/off when creating).\n"
            "Ticking it counts as responding, so expected respondents who genuinely can't "
            "attend won't be reminded."
        ),
    ),
    (
        "/std → Manage Recurring Polls",
        (
            "Lists all recurring polls in this server.\n"
            "Poll creator or server admins can **edit** the name, day, time, mention role, "
            "expected respondents, and the can't-make-any option, or **cancel** a recurring poll."
        ),
    ),
)


def build_help_embed() -> discord.Embed:
    """Return the help text as an embed."""
    embed = discord.Embed(title="📅 STD Bot — Help", color=discord.Color.blurple())
    for name, value in HELP_FIELDS:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text="Votes are saved across bot restarts.")
    return embed


def register_help(tree: app_commands.CommandTree) -> None:
    """Add /std-help to a command tree."""

    @tree.command(name="std-help", description="How to use the STD availability poll bot")
    async def std_help(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=build_help_embed(), ephemeral=True)
