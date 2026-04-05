from typing import List

from pydantic import BaseModel


class ContentPart(BaseModel):
    text: str


class Content(BaseModel):
    parts: List[ContentPart]
    role: str


class ChatResponse(BaseModel):
    model_version: str=''
    content: Content
    partial: bool = False
    finish_reason: str = ''
    invocation_id: str
    author: str
    id: str
    timestamp: float

    class Config:
        from_attributes = True
        exclude = ['actions', 'usage_metadata']
