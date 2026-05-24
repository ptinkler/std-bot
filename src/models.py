from dataclasses import dataclass, field


@dataclass
class PollData:
    event_name: str
    description: str
    creator_id: int
    guild_id: int
    channel_id: int
    dates: list[int]  # unix timestamps (midnight UTC per date)
    votes: dict[int, set[int]] = field(default_factory=dict)  # date_idx -> user_ids


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
