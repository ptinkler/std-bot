"""Starting and stopping tracking of a poll: memory and database together."""

from std_bot.domain.poll import PollData
from std_bot.state import BotState
from std_bot.storage.polls import delete_poll, save_poll


def track_poll(state: BotState, msg_id: int, poll: PollData) -> None:
    """Remember a poll in memory and store it."""
    state.polls[msg_id] = poll
    save_poll(msg_id, poll)


def untrack_poll(state: BotState, msg_id: int) -> PollData | None:
    """Forget a poll in memory and delete it from the database.

    Returns:
        The poll that was tracked, or None if there was none.
    """
    poll = state.polls.pop(msg_id, None)
    delete_poll(msg_id)
    return poll
