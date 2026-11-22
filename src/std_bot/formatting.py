"""Small text helpers for Discord messages."""

from collections.abc import Iterable


def mention_users(user_ids: Iterable[int]) -> str:
    """Return space-separated user mentions."""
    return " ".join(f"<@{user_id}>" for user_id in user_ids)


def mention_limited(user_ids: Iterable[int], limit: int) -> str:
    """Return user mentions, cut at `limit` with a "+N more" note."""
    ids = list(user_ids)
    shown = mention_users(ids[:limit])
    return shown + (f" *+{len(ids) - limit} more…*" if len(ids) > limit else "")


def person_count(count: int) -> str:
    """Return "person" for one, "people" otherwise."""
    return "person" if count == 1 else "people"


def day_count(days: int) -> str:
    """Return "1 day" or "N days"."""
    return "1 day" if days == 1 else f"{days} days"
