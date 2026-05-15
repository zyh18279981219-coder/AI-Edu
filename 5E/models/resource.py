from sqlalchemy import Column, INTEGER, String
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Resource(Base):
    __tablename__ = 'resources'

    resource_id = Column(INTEGER, primary_key=True)
    course_id = Column(String(length=100), nullable=False)
    node_id = Column(String(length=200), nullable=False)
    resource_path = Column(String(length=1000), nullable=False)
    resource_type = Column(String(length=200), nullable=False)
    title = Column(String(length=500), nullable=True)
    is_deleted = Column(TINYINT, nullable=False)
