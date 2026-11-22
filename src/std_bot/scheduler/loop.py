"""The minute loop that drives recurring polls."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from discord.ext import tasks

from std_bot.bot import StdBot
from std_bot.domain.recurring import RecurringPollConfig
from std_bot.domain.schedule import iso_week
from std_bot.scheduler.posting import post_recurring_poll
from std_bot.scheduler.reminders import send_reminders

log = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return the current time, timezone-aware in UTC."""
    return datetime.now(UTC)


def _is_post_time(config: RecurringPollConfig, now_local: datetime) -> bool:
    return (now_local.weekday(), now_local.hour, now_local.minute) == (
        config.post_weekday,
        config.post_hour,
        config.post_minute,
    )


class RecurringScheduler:
    """Once a minute, posts each recurring poll that is due and sends the reminders that are due."""

    def __init__(self, bot: StdBot, clock: Callable[[], datetime] = utc_now) -> None:
        """Create the scheduler; `clock` returns the current aware time (replaced in tests)."""
        self._bot = bot
        self._clock = clock

    def start(self) -> None:
        """Start the loop; it waits for the bot to be connected before its first run."""
        self._tick.start()

    async def run_once(self) -> None:
        """Check every recurring poll against the current time."""
        now = self._clock()
        for config in list(self._bot.state.recurring.values()):
            await self._check(config, now)

    async def _check(self, config: RecurringPollConfig, now: datetime) -> None:
        # A broken config (e.g. a bad timezone) must not stop the others.
        try:
            now_local = now.astimezone(ZoneInfo(config.post_timezone))
            week = iso_week(now)
            if _is_post_time(config, now_local) and config.last_posted_week != week:
                await post_recurring_poll(self._bot, config, week, now)
            await send_reminders(self._bot, config, now_local)
        except Exception:
            log.exception("error in recurring poll check id=%d", config.id)

    @tasks.loop(minutes=1)
    async def _tick(self) -> None:
        await self.run_once()

    @_tick.before_loop
    async def _wait_until_connected(self) -> None:
        await self._bot.wait_until_ready()
