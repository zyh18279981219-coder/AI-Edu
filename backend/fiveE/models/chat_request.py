from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: str
    course_id: str
    content: str
    node_id: str | None = None
