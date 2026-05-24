import re
from datetime import datetime, timedelta, timezone
from datetime import time as dtime

import discord

from models import PollData


def upcoming_days(count: int = 25) -> list[int]:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return [int((today + timedelta(days=i)).timestamp()) for i in range(1, count + 1)]


def parse_time(s: str) -> dtime | None:
    s = s.strip().upper()
    for pattern, has_min, has_ampm in [
        (r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", True, True),
        (r"^(\d{1,2})\s*(AM|PM)$", False, True),
        (r"^(\d{1,2}):(\d{2})$", True, False),
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

    embed = discord.Embed(
        title=f"📅 {poll.event_name} — When can you attend?",
        description="\n".join(lines),
        color=discord.Color.blue(),
    )
    embed.set_footer(text="Click dates to toggle availability • creator can Finalize to schedule")
    return embed
