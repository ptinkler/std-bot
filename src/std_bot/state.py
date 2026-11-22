"""The polls the bot is currently tracking."""

from dataclasses import dataclass, field

from std_bot.domain.poll import PollData
from std_bot.domain.recurring import RecurringPollConfig


@dataclass
class BotState:
    """In-memory copy of what is stored in the database.

    Attributes:
        polls: Open polls by message id.
        recurring: Recurring poll configs by id.
    """

    polls: dict[int, PollData] = field(default_factory=dict)
    recurring: dict[int, RecurringPollConfig] = field(default_factory=dict)
