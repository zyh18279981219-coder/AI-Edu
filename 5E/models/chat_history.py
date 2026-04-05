from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ChatHistory(Base):
    __tablename__ = "events"

    id = Column(String(length=128), primary_key=True, index=True)
    app_name = Column(String(length=128), index=True, nullable=False)
    user_id = Column(String(length=128), index=True, nullable=False)
    session_id = Column(String(length=128), nullable=False)  # e.g., 'user', 'assistant'
    invocation_id = Column(String(length=256), nullable=False)
    timestamp = Column(DateTime,nullable=False)
    event_data=Column(Text, nullable=True)