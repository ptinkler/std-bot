"""Weekly schedule arithmetic."""

from datetime import datetime, timedelta

WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DAYS_IN_WEEK = len(WEEKDAY_NAMES)
POLL_OPEN_DAYS = DAYS_IN_WEEK
UPCOMING_DAY_CHOICES = 25


def iso_week(moment: datetime) -> str:
    """Return the ISO week of a moment, e.g. "2026-W47"."""
    return moment.strftime("%G-W%V")


def midnight(moment: datetime) -> datetime:
    """Return the start of the day of a moment, in the same timezone."""
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def next_post_datetime(weekday: int, hour: int, minute: int, now_local: datetime) -> datetime:
    """Return the next occurrence of a weekday at hour:minute strictly after `now_local`, in its timezone."""
    days_ahead = (weekday - now_local.weekday()) % DAYS_IN_WEEK
    candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
    if candidate <= now_local:
        candidate += timedelta(days=DAYS_IN_WEEK)
    return candidate


def next_week_dates(now: datetime) -> list[int]:
    """Return Monday to Sunday of the next ISO week as midnight timestamps in `now`'s timezone."""
    days_until_monday = (DAYS_IN_WEEK - now.weekday()) % DAYS_IN_WEEK or DAYS_IN_WEEK
    next_monday = midnight(now) + timedelta(days=days_until_monday)
    return [int((next_monday + timedelta(days=offset)).timestamp()) for offset in range(DAYS_IN_WEEK)]


def upcoming_days(now: datetime, count: int = UPCOMING_DAY_CHOICES) -> list[int]:
    """Return the next `count` days, starting tomorrow, as midnight timestamps in `now`'s timezone."""
    today = midnight(now)
    return [int((today + timedelta(days=offset)).timestamp()) for offset in range(1, count + 1)]
