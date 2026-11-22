"""What every step of finalising a poll carries along."""

from dataclasses import dataclass

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData


@dataclass(frozen=True)
class FinalizeContext:
    """The poll being finalised.

    Attributes:
        bot: The running bot.
        poll: The poll.
        msg_id: Id of the poll's message.
    """

    bot: StdBot
    poll: PollData
    msg_id: int
