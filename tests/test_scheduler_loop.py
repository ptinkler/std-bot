"""The minute loop that posts recurring polls."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from std_bot.bot import StdBot
from std_bot.scheduler import loop
from std_bot.storage.recurring import save_recurring
from tests.factories import make_draft

FRIDAY_18_UTC = datetime(2026, 11, 27, 18, 0, tzinfo=UTC)


@pytest.fixture
def post(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Replace posting and reminders with mocks that record their calls."""
    posting = AsyncMock()
    monkeypatch.setattr(loop, "post_recurring_poll", posting)
    monkeypatch.setattr(loop, "send_reminders", AsyncMock())
    return posting


def _scheduler(bot: StdBot, moment: datetime) -> loop.RecurringScheduler:
    return loop.RecurringScheduler(bot, clock=lambda: moment)


async def test_posts_at_the_scheduled_local_time_once_per_week(bot: StdBot, post: AsyncMock) -> None:
    """Friday 18:00 in London (GMT in November) is 18:00 UTC; a second check the same week does nothing."""
    config = save_recurring(make_draft(post_timezone="Europe/London"))
    bot.state.recurring[config.id] = config

    await _scheduler(bot, FRIDAY_18_UTC).run_once()
    post.assert_awaited_once_with(bot, bot.state.recurring[config.id], "2026-W48", FRIDAY_18_UTC)

    config.last_posted_week = "2026-W48"
    await _scheduler(bot, FRIDAY_18_UTC).run_once()
    assert post.await_count == 1


async def test_does_not_post_at_the_wrong_minute(bot: StdBot, post: AsyncMock) -> None:
    """Only the scheduled minute counts."""
    config = save_recurring(make_draft(post_timezone="Europe/London"))
    bot.state.recurring[config.id] = config
    await _scheduler(bot, datetime(2026, 11, 27, 18, 1, tzinfo=UTC)).run_once()
    post.assert_not_awaited()


async def test_follows_daylight_saving(bot: StdBot, post: AsyncMock) -> None:
    """In July, Friday 18:00 in London is 17:00 UTC."""
    config = save_recurring(make_draft(post_timezone="Europe/London"))
    bot.state.recurring[config.id] = config
    moment = datetime(2026, 7, 10, 17, 0, tzinfo=UTC)
    assert moment.astimezone(ZoneInfo("Europe/London")).hour == 18
    await _scheduler(bot, moment).run_once()
    post.assert_awaited_once()


async def test_one_broken_config_does_not_stop_the_others(bot: StdBot, post: AsyncMock) -> None:
    """A config with an unknown timezone is logged and skipped."""
    bad = save_recurring(make_draft(post_timezone="Not/AZone"))
    good = save_recurring(make_draft())
    bot.state.recurring.update({bad.id: bad, good.id: good})
    await _scheduler(bot, FRIDAY_18_UTC).run_once()
    post.assert_awaited_once_with(bot, good, "2026-W48", FRIDAY_18_UTC)
