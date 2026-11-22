"""Date labels for polls."""

from datetime import UTC, datetime


def date_label(timestamp: int) -> str:
    """Return a short label such as "Tue, Nov 3" (no zero padding on the day)."""
    moment = datetime.fromtimestamp(timestamp, tz=UTC)
    return moment.strftime(f"%a, %b {moment.day}")


def format_date(timestamp: int) -> str:
    """Return the weekday plus Discord's localised date and relative-time markup."""
    weekday = datetime.fromtimestamp(timestamp, tz=UTC).strftime("%A")
    return f"{weekday}, <t:{timestamp}:D> (<t:{timestamp}:R>)"
