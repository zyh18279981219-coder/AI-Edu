from sqlalchemy import Column, String, Integer, TEXT
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserInteraction(Base):
    __tablename__ = 'user_interaction'

    user_id = Column(Integer,primary_key=True)
    course_id = Column(Integer,primary_key=True)
    stage = Column(TEXT)
    question_type = Column(TEXT)
    question_count = Column(Integer)
    error = Column(TEXT)
