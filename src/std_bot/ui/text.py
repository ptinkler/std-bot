"""Wording shared by several views."""

from std_bot.domain.recurring import RecurringPollDraft
from std_bot.domain.schedule import WEEKDAY_NAMES


def on_off(*, enabled: bool) -> str:
    """Return "ON" or "OFF"."""
    return "ON" if enabled else "OFF"


def cannot_attend_label(*, enabled: bool) -> str:
    """Return the label of the "can't make any" toggle button."""
    return f"🚫 Can't make any option: {on_off(enabled=enabled)}"


def clock(hour: int, minute: int) -> str:
    """Return "HH:MM"."""
    return f"{hour:02d}:{minute:02d}"


def describe_reminded(user_ids: list[int], role_id: int | None) -> list[str]:
    """Return the parts of "who gets reminded": the listed members and/or a whole role."""
    parts: list[str] = []
    if user_ids:
        parts.append(f"{len(user_ids)} listed member(s)")
    if role_id:
        parts.append(f"everyone in <@&{role_id}>")
    return parts


def describe_post_time(draft: RecurringPollDraft) -> str:
    """Return "every <day> at HH:MM UTC" for a recurring poll."""
    return f"every **{WEEKDAY_NAMES[draft.post_weekday]}** at **{clock(draft.post_hour, draft.post_minute)} UTC**"
