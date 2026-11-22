"""Discord embeds for polls."""

from collections.abc import Iterator

import discord

from std_bot.domain.poll import PollData
from std_bot.formatting import mention_limited, mention_users, person_count
from std_bot.timestamps import format_date

MAX_MENTIONS_SHOWN = 6
FOOTER = "Click dates to toggle availability • anyone can Finalize to schedule"
FOOTER_WITH_CANNOT_ATTEND = "Click dates, or 🚫 if you can't make any • anyone can Finalize to schedule"


def build_closed_poll_embed(poll: PollData) -> discord.Embed:
    """Return the embed that replaces a weekly poll once it has closed."""
    return discord.Embed(
        title=f"📅 {poll.event_name} — Poll Closed",
        description="This weekly poll has closed. A new one has been posted.",
        color=discord.Color.dark_gray(),
    )


def build_finalized_poll_embed(poll: PollData, event_ts: int) -> discord.Embed:
    """Return the embed that replaces a poll once its event has been scheduled."""
    description = f"*{poll.description}*\n\n" if poll.description else ""
    return discord.Embed(
        title=f"📅 {poll.event_name}",
        description=f"{description}Event scheduled for <t:{event_ts}:F>",
        color=discord.Color.green(),
    )


def _lines(poll: PollData) -> Iterator[str]:
    if poll.description:
        yield f"*{poll.description}*\n"
    for index, timestamp in enumerate(poll.dates):
        voters = poll.voters(index)
        mentions = mention_limited(sorted(voters), MAX_MENTIONS_SHOWN) if voters else "*no votes yet*"
        yield f"{format_date(timestamp)} — **{len(voters)}** {person_count(len(voters))}\n{mentions}"
    if poll.cannot_attend:
        count = len(poll.cannot_attend)
        mentions = mention_limited(sorted(poll.cannot_attend), MAX_MENTIONS_SHOWN)
        yield f"🚫 **Can't make any** — **{count}** {person_count(count)}\n{mentions}"
    if poll.expected_respondent_ids:
        pending = poll.pending_among(poll.expected_respondent_ids)
        yield (
            f"\n⏳ **Waiting on:** {mention_users(pending)}" if pending else "\n✅ **Everyone expected has responded.**"
        )


def build_poll_embed(poll: PollData) -> discord.Embed:
    """Return the embed of an open poll: the dates, who voted for each, and who is still expected."""
    embed = discord.Embed(
        title=f"📅 {poll.event_name} — When can you attend?",
        description="\n".join(_lines(poll)),
        color=discord.Color.blue(),
    )
    embed.set_footer(text=FOOTER_WITH_CANNOT_ATTEND if poll.allow_cannot_attend else FOOTER)
    return embed


def build_votes_embed(poll: PollData) -> discord.Embed:
    """Return the private "See Votes" embed: everyone who voted for each date."""
    embed = discord.Embed(title=f"📅 {poll.event_name} — Votes", color=discord.Color.blurple())
    for index, timestamp in enumerate(poll.dates):
        voters = poll.voters(index)
        embed.add_field(
            name=f"{format_date(timestamp)} — {len(voters)} {person_count(len(voters))}",
            value=mention_users(sorted(voters)) or "*no votes*",
            inline=False,
        )
    if poll.cannot_attend:
        embed.add_field(
            name=f"🚫 Can't make any — {len(poll.cannot_attend)}",
            value=mention_users(sorted(poll.cannot_attend)),
            inline=False,
        )
    if poll.expected_respondent_ids:
        pending = poll.pending_among(poll.expected_respondent_ids)
        embed.add_field(
            name="⏳ Expected but not yet responded",
            value=mention_users(pending) or "*everyone has responded*",
            inline=False,
        )
    return embed
