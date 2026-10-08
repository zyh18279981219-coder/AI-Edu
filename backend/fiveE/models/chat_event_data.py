from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    """A model-generated function call (tool call) carried by a content part."""
    id: Optional[str] = None
    name: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)


class ContentPart(BaseModel):
    """A single content part. It may carry plain text, a function_call, or both."""
    text: Optional[str] = None
    function_call: Optional[FunctionCall] = None


class Content(BaseModel):
    parts: List[ContentPart]
    role: str


class ChatEventData(BaseModel):
    model_version: str = ''
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
