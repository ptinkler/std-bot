from dataclasses import dataclass, field


@dataclass
class RecurringPollConfig:
    event_name: str
    description: str
    creator_id: int
    guild_id: int
    channel_id: int
    post_weekday: int   # 0=Mon … 6=Sun
    post_hour: int
    post_minute: int
    post_timezone: str  # IANA key
    last_posted_week: str | None = None
    last_poll_msg_id: int | None = None
    mention_role_id: int | None = None
    expected_respondent_ids: list[int] = field(default_factory=list)
    expected_role_id: int | None = None
    allow_cannot_attend: bool = True
    last_reminded_week: str | None = None
    id: int | None = None


active_recurring_configs: dict[int, RecurringPollConfig] = {}  # id -> config


@dataclass
class PollData:
    event_name: str
    description: str
    creator_id: int
    guild_id: int
    channel_id: int
    dates: list[int]  # unix timestamps (midnight UTC per date)
    votes: dict[int, set[int]] = field(default_factory=dict)  # date_idx -> user_ids
    cannot_attend: set[int] = field(default_factory=set)  # users who can't make any date
    allow_cannot_attend: bool = True  # whether the "can't make any" option is offered
    expected_respondent_ids: list[int] = field(default_factory=list)  # who is expected to respond

    def responded_users(self) -> set[int]:
        """Everyone who has given any response: a date vote or a can't-attend tick."""
        users = set(self.cannot_attend)
        for voters in self.votes.values():
            users |= voters
        return users


active_polls: dict[int, PollData] = {}  # poll message_id -> PollData


TIMEZONES = [
    ("UTC",                 "UTC"),
    ("Europe/London",       "London (GMT/BST)"),
    ("Europe/Paris",        "Paris / Berlin (CET/CEST)"),
    ("Europe/Helsinki",     "Helsinki / Kyiv (EET/EEST)"),
    ("Europe/Moscow",       "Moscow (MSK)"),
    ("America/New_York",    "New York (ET)"),
    ("America/Chicago",     "Chicago (CT)"),
    ("America/Denver",      "Denver (MT)"),
    ("America/Los_Angeles", "Los Angeles (PT)"),
    ("America/Sao_Paulo",   "São Paulo (BRT)"),
    ("Africa/Johannesburg", "Johannesburg (SAST)"),
    ("Asia/Dubai",          "Dubai (GST)"),
    ("Asia/Kolkata",        "India (IST)"),
    ("Asia/Bangkok",        "Bangkok / Jakarta (ICT)"),
    ("Asia/Singapore",      "Singapore / KL (SGT)"),
    ("Asia/Shanghai",       "Beijing / Shanghai (CST)"),
    ("Asia/Tokyo",          "Tokyo (JST)"),
    ("Asia/Seoul",          "Seoul (KST)"),
    ("Australia/Sydney",    "Sydney (AEST/AEDT)"),
    ("Pacific/Auckland",    "Auckland (NZST/NZDT)"),
]
