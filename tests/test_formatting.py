"""Text helpers for Discord messages."""

from std_bot.formatting import day_count, mention_limited, mention_users, person_count


def test_mentions() -> None:
    """Users are joined with spaces; an empty list gives an empty string."""
    assert mention_users([1, 2]) == "<@1> <@2>"
    assert not mention_users([])


def test_mentions_are_cut_at_the_limit_with_a_count() -> None:
    """Only `limit` users are shown, and the rest are counted."""
    assert mention_limited([1, 2], 6) == "<@1> <@2>"
    assert mention_limited(range(1, 10), 6).endswith("*+3 more…*")


def test_plurals() -> None:
    """One is singular; zero and many are plural."""
    assert [person_count(n) for n in (0, 1, 2)] == ["people", "person", "people"]
    assert [day_count(n) for n in (1, 2)] == ["1 day", "2 days"]
