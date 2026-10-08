from pydantic import BaseModel


class CourseNameRequest(BaseModel):
    course_name:str
    course_id: str | None = None
