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
