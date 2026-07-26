import os

from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "/data/polls.db")

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class PollRow(Base):
    __tablename__ = "polls"
    msg_id = Column(Integer, primary_key=True)
    data = Column(String, nullable=False)


class RecurringPollRow(Base):
    __tablename__ = "recurring_polls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    creator_id = Column(Integer, nullable=False)
    guild_id = Column(Integer, nullable=False)
    channel_id = Column(Integer, nullable=False)
    post_weekday = Column(Integer, nullable=False)
    post_hour = Column(Integer, nullable=False)
    post_minute = Column(Integer, nullable=False)
    post_timezone = Column(String, nullable=False)
    last_posted_week = Column(String, nullable=True)
    last_poll_msg_id = Column(Integer, nullable=True)
    mention_role_id = Column(Integer, nullable=True)
