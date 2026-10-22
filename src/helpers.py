import re
from datetime import datetime, timedelta, timezone
from datetime import time as dtime

import discord

from models import PollData

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def parse_weekday(s: str) -> int | None:
    s = s.strip().lower()
    for i, name in enumerate(WEEKDAY_NAMES):
        n = name.lower()
        if s == n or s == str(i) or (len(s) >= 2 and n.startswith(s)):
            return i
    return None


def resolve_expected_ids(guild, expected_role_id: int | None, manual_ids: list[int]) -> list[int]:
    """Expected respondents = manual list ∪ non-bot members of the expected role."""
    ids = set(manual_ids)
    if expected_role_id and guild is not None:
        role = guild.get_role(expected_role_id)
        if role is not None:
            ids |= {m.id for m in role.members if not m.bot}
    return sorted(ids)


def next_post_datetime(weekday: int, hour: int, minute: int, now_local: datetime) -> datetime:
    """Next occurrence of weekday at hour:minute strictly after now_local (same tz)."""
    days_ahead = (weekday - now_local.weekday()) % 7
    candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    if candidate <= now_local:
        candidate += timedelta(days=7)
    return candidate


def next_week_dates() -> list[int]:
    """Mon–Sun of next ISO week as midnight UTC timestamps."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    days_until_monday = (7 - today.weekday()) % 7 or 7
    next_monday = today + timedelta(days=days_until_monday)
    return [int((next_monday + timedelta(days=i)).timestamp()) for i in range(7)]


def upcoming_days(count: int = 25) -> list[int]:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return [int((today + timedelta(days=i)).timestamp()) for i in range(1, count + 1)]


def parse_time(s: str) -> dtime | None:
    s = s.strip().upper()
    for pattern, has_min, has_ampm in [
        (r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", True, True),
        (r"^(\d{1,2})\s*(AM|PM)$", False, True),
        (r"^(\d{1,2}):(\d{2})$", True, False),
        (r"^(\d{2})(\d{2})$", True, False),
        (r"^(\d{1,2})$", False, False),
    ]:
        m = re.match(pattern, s)
        if not m:
            continue
        g = m.groups()
        h, mn = int(g[0]), (int(g[1]) if has_min else 0)
        if has_ampm:
            ap = g[2] if has_min else g[1]
            if ap == "PM" and h != 12:
                h += 12
            elif ap == "AM" and h == 12:
                h = 0
        if 0 <= h < 24 and 0 <= mn < 60:
            return dtime(h, mn)
    return None


def date_label(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime(f"%a, %b {dt.day}")


def fmt_date(ts: int) -> str:
    dow = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%A")
    return f"{dow}, <t:{ts}:D> (<t:{ts}:R>)"


def build_closed_poll_embed(poll: PollData) -> discord.Embed:
    return discord.Embed(
        title=f"📅 {poll.event_name} — Poll Closed",
        description="This weekly poll has closed. A new one has been posted.",
        color=discord.Color.dark_gray(),
    )


def build_poll_embed(poll: PollData, finalized_ts: int | None = None) -> discord.Embed:
    if finalized_ts is not None:
        desc = ""
        if poll.description:
            desc = f"*{poll.description}*\n\n"
        desc += f"Event scheduled for <t:{finalized_ts}:F>"
        return discord.Embed(title=f"📅 {poll.event_name}", description=desc, color=discord.Color.green())

    lines = []
    if poll.description:
        lines.append(f"*{poll.description}*\n")
    for i, ts in enumerate(poll.dates):
        voters = poll.votes.get(i, set())
        count = len(voters)
        if voters:
            voter_list = list(voters)
            shown = " ".join(f"<@{uid}>" for uid in voter_list[:6])
            mentions = shown + (f" *+{count - 6} more…*" if count > 6 else "")
        else:
            mentions = "*no votes yet*"
        lines.append(f"{fmt_date(ts)} — **{count}** {'person' if count == 1 else 'people'}\n{mentions}")

    if poll.cannot_attend:
        count = len(poll.cannot_attend)
        ca_list = list(poll.cannot_attend)
        shown = " ".join(f"<@{uid}>" for uid in ca_list[:6])
        mentions = shown + (f" *+{count - 6} more…*" if count > 6 else "")
        lines.append(f"🚫 **Can't make any** — **{count}** {'person' if count == 1 else 'people'}\n{mentions}")

    if poll.expected_respondent_ids:
        responded = poll.responded_users()
        pending = [uid for uid in poll.expected_respondent_ids if uid not in responded]
        if pending:
            lines.append("\n⏳ **Waiting on:** " + " ".join(f"<@{uid}>" for uid in pending))
        else:
            lines.append("\n✅ **Everyone expected has responded.**")

    embed = discord.Embed(
        title=f"📅 {poll.event_name} — When can you attend?",
        description="\n".join(lines),
        color=discord.Color.blue(),
    )
    footer = "Click dates to toggle availability • anyone can Finalize to schedule"
    if poll.allow_cannot_attend:
        footer = "Click dates, or 🚫 if you can't make any • anyone can Finalize to schedule"
    embed.set_footer(text=footer)
    return embed
