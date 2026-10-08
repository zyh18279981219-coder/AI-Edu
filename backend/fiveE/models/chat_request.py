from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: str
    course_id: int
    content: str
