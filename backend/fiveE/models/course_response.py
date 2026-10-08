from pydantic import BaseModel

class CourseResponse(BaseModel):
    id:int
    name:str
