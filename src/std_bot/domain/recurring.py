"""A weekly recurring poll configuration."""

from dataclasses import dataclass, field


@dataclass(kw_only=True)
class RecurringPollDraft:
    """The settings of a recurring poll, before it has been saved.

    Attributes:
        event_name: Title of each weekly poll.
        description: Optional text under the title.
        creator_id: Discord user who set it up.
        guild_id: Server it belongs to.
        channel_id: Channel the polls are posted in.
        post_weekday: Day of the week to post, 0 = Monday.
        post_hour: Hour to post, in `post_timezone`.
        post_minute: Minute to post, in `post_timezone`.
        post_timezone: IANA timezone key the post time is in.
        mention_role_id: Role to ping when posting, if any.
        expected_respondent_ids: Users expected to respond.
        expected_role_id: Role whose members are all expected to respond.
        allow_cannot_attend: Whether polls offer "can't make any".
        reminder_days_before: Days before the reset to remind non-responders.
    """

    event_name: str
    description: str = ""
    creator_id: int
    guild_id: int
    channel_id: int
    post_weekday: int
    post_hour: int
    post_minute: int
    post_timezone: str
    mention_role_id: int | None = None
    expected_respondent_ids: list[int] = field(default_factory=list)
    expected_role_id: int | None = None
    allow_cannot_attend: bool = True
    reminder_days_before: int = 1


@dataclass(kw_only=True)
class RecurringPollConfig(RecurringPollDraft):
    """A saved recurring poll, with its id and progress through the weeks.

    Attributes:
        id: Database id.
        last_posted_week: ISO week (e.g. "2026-W47") of the last poll posted.
        last_poll_msg_id: Message id of the poll currently open.
        last_reminded_week: ISO week the last reminder was sent for.
    """

    id: int
    last_posted_week: str | None = None
    last_poll_msg_id: int | None = None
    last_reminded_week: str | None = None
