"""Start-up wiring: restoring polls, registering commands, and the entry point."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from std_bot import app
from std_bot.bot import StdBot
from std_bot.commands.help import build_help_embed
from std_bot.commands.register import register_commands
from std_bot.config import MissingTokenError, discord_token
from std_bot.restore import restore_state
from std_bot.storage.polls import save_poll
from std_bot.storage.recurring import save_recurring
from tests.factories import make_draft, make_poll


async def test_restore_tracks_stored_polls_and_reattaches_their_buttons(
    bot: StdBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Open polls and recurring configs come back into memory after a restart."""
    save_poll(555, make_poll())
    config = save_recurring(make_draft())
    add_view = MagicMock()
    monkeypatch.setattr(bot, "add_view", add_view)

    restore_state(bot)

    assert list(bot.state.polls) == [555]
    assert bot.state.recurring == {config.id: config}
    add_view.assert_called_once()
    assert add_view.call_args.kwargs["message_id"] == 555


async def test_the_slash_commands_are_registered(bot: StdBot) -> None:
    """Both /std and /std-help exist on the command tree."""
    register_commands(bot)
    assert {command.name for command in bot.tree.get_commands()} == {"std", "std-help"}


def test_the_help_embed_has_a_field_per_feature() -> None:
    """The help text covers the four flows and carries its footer."""
    embed = build_help_embed()
    assert len(embed.fields) == 4
    assert embed.footer.text == "Votes are saved across bot restarts."


def test_a_missing_token_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without DISCORD_TOKEN there is nothing to log in with."""
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    with pytest.raises(MissingTokenError, match="DISCORD_TOKEN"):
        discord_token()
    monkeypatch.setenv("DISCORD_TOKEN", "abc")
    assert discord_token() == "abc"


def test_main_runs_the_bot_with_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() reads the token and hands it to the client."""
    run = MagicMock()
    monkeypatch.setattr(StdBot, "run", run)
    monkeypatch.setattr(app, "load_dotenv", lambda: None)
    monkeypatch.setenv("DISCORD_TOKEN", "abc")
    app.main()
    run.assert_called_once_with("abc")


async def test_setup_starts_everything_once(bot: StdBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup restores state, registers commands, starts the loops and syncs the commands."""
    calls: list[str] = []

    def restore(_bot: StdBot) -> None:
        calls.append("restore")

    def commands(_bot: StdBot) -> None:
        calls.append("commands")

    def scheduler_for(_bot: StdBot) -> MagicMock:
        return scheduler

    scheduler = MagicMock()
    monkeypatch.setattr(app, "restore_state", restore)
    monkeypatch.setattr(app, "register_commands", commands)
    monkeypatch.setattr(app, "start_backups", lambda: calls.append("backups"))
    monkeypatch.setattr(app, "RecurringScheduler", scheduler_for)
    monkeypatch.setattr(bot.tree, "sync", AsyncMock(side_effect=lambda: calls.append("sync")))

    await app.setup(bot)

    assert calls == ["restore", "commands", "backups", "sync"]
    scheduler.start.assert_called_once()
