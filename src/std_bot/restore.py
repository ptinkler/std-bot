"""Loading stored polls back into the running bot."""

import logging

from std_bot.bot import StdBot
from std_bot.storage.polls import load_polls
from std_bot.storage.recurring import load_recurring
from std_bot.ui.poll_view import PollView

log = logging.getLogger(__name__)


def restore_state(bot: StdBot) -> None:
    """Track every stored poll and recurring config, and re-attach the buttons of the open polls."""
    bot.state.polls.update(load_polls())
    for msg_id, poll in bot.state.polls.items():
        bot.add_view(PollView(bot, poll), message_id=msg_id)
    log.info("restored %d active poll(s)", len(bot.state.polls))
    bot.state.recurring.update(load_recurring())
    log.info("restored %d recurring poll config(s)", len(bot.state.recurring))
