from sqlalchemy import Column, Integer, DECIMAL, String
from sqlalchemy.orm import declarative_base

Base=declarative_base()

class TwinProfile(Base):
    __tablename__ = 'twin_profile'

    profile_id = Column(Integer, primary_key=True)
    username=Column(String(length=100), nullable=False)
    user_id=Column(Integer,nullable=False)
    overall_mastery=Column(DECIMAL(5,4),nullable=True)
