from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserInteraction(Base):
    __tablename__ = "user_interaction"

    interaction_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_identifier = Column(String(100), nullable=False)
    student_user_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    student_username = Column(String(100), nullable=True)
    course_id = Column(String(100), nullable=True)
    session_id = Column(String(255), nullable=True)
    stage = Column(String(64), nullable=False)
    question_type = Column(String(100), nullable=True)
    question_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
