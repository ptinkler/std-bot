"""Looking up expected respondents on a guild."""

from unittest.mock import MagicMock

from std_bot.guilds import resolve_expected_ids
from tests.factories import make_guild


def test_manual_ids_and_role_members_are_merged_without_bots() -> None:
    """The result is sorted, de-duplicated and leaves bots out."""
    guild = make_guild(None, role_members=(5, 2))
    guild.get_role.return_value.members.append(MagicMock(id=6, bot=True))
    assert resolve_expected_ids(guild, 99, [2, 1]) == [1, 2, 5]


def test_missing_role_or_guild_falls_back_to_the_manual_ids() -> None:
    """A deleted role or an unreachable guild must not lose the listed users."""
    guild = make_guild(None)
    guild.get_role.return_value = None
    assert resolve_expected_ids(guild, 404, [3]) == [3]
    assert resolve_expected_ids(guild, None, [3, 3]) == [3]
    assert resolve_expected_ids(None, 99, [4]) == [4]
