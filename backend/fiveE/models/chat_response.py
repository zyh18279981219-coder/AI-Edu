from typing import List, Optional

from pydantic import BaseModel, Field


class Button(BaseModel):
    show_text: str
    send_text: str


class Resource(BaseModel):
    show_text: str
    id: str


class Test(BaseModel):
    show_text: str
    id: str

class ChatResponse(BaseModel):
    role: str
    stage: Optional[str] = None
    content: str
    buttons: List[Button]
    resources: List[Resource]
    tests: List[Test]
    timestamp:float
