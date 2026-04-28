from sqlalchemy import INTEGER, Column, String, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CourseNode(Base):
    __tablename__ = 'course_nodes'

    node_detail_id = Column(INTEGER, primary_kay=True, nullable=False)
    course_id = Column(String(length=100), nullable=False)
    node_name = Column(String(length=500), nullable=False)
    node_path_json = Column(JSON, nullable=False)
