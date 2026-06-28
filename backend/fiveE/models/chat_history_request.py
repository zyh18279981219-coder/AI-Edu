from pydantic import BaseModel


class ChatHistoryRequest(BaseModel):
    student_id:str
    course_id:str