"""An availability poll and its voting rules."""

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class PollData:
    """One availability poll.

    Attributes:
        event_name: Title shown on the poll.
        description: Optional text under the title.
        creator_id: Discord user who created the poll.
        guild_id: Server the poll belongs to.
        channel_id: Channel the poll was posted in.
        dates: Candidate dates as unix timestamps (midnight UTC).
        votes: Date index to the users who can attend that date.
        cannot_attend: Users who ticked "can't make any".
        allow_cannot_attend: Whether the "can't make any" option is offered.
        expected_respondent_ids: Users who are expected to respond.
    """

    event_name: str
    description: str = ""
    creator_id: int
    guild_id: int
    channel_id: int
    dates: list[int]
    votes: dict[int, set[int]] = field(default_factory=dict)
    cannot_attend: set[int] = field(default_factory=set)
    allow_cannot_attend: bool = True
    expected_respondent_ids: list[int] = field(default_factory=list)

    def voters(self, date_index: int) -> set[int]:
        """Return the users who voted for a date."""
        return self.votes.get(date_index, set())

    def responded_users(self) -> set[int]:
        """Return everyone who has responded: a date vote or a can't-attend tick."""
        users = set(self.cannot_attend)
        for voters in self.votes.values():
            users |= voters
        return users

    def pending_among(self, expected_ids: Iterable[int]) -> list[int]:
        """Return the given users who have not responded yet, in the order given."""
        responded = self.responded_users()
        return [user_id for user_id in expected_ids if user_id not in responded]

    def toggle_vote(self, date_index: int, user_id: int) -> bool:
        """Add or remove a user's vote for a date; voting clears "can't make any".

        Returns:
            True if the vote was added, False if it was removed.
        """
        voters = self.votes.setdefault(date_index, set())
        if user_id in voters:
            voters.discard(user_id)
            return False
        voters.add(user_id)
        self.cannot_attend.discard(user_id)
        return True

    def toggle_cannot_attend(self, user_id: int) -> bool:
        """Add or remove a user's "can't make any" mark; adding clears their date votes.

        Returns:
            True if the mark was added, False if it was removed.
        """
        if user_id in self.cannot_attend:
            self.cannot_attend.discard(user_id)
            return False
        self.cannot_attend.add(user_id)
        for voters in self.votes.values():
            voters.discard(user_id)
        return True
