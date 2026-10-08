from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import declarative_base

Base=declarative_base()

class User(Base):
    __tablename__ = 'user'

    user_id = Column(Integer, primary_key=True)
    username = Column(String(length=100))
