from sqlalchemy import String, Column, Text, JSON, Enum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Course(Base):
    __tablename__ = 'courses'

    course_id = Column(String(length=100), primary_key=True)
    course_name = Column(String(length=500))
    description = Column(Text, nullable=True)
    difficulty_level = Column(Enum(
        'beginner',
        'intermediate',
        'advanced',
    ), nullable=True)
    payload_json = Column(JSON, nullable=True)
