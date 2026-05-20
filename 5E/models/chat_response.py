from typing import List

from pydantic import BaseModel, Field


class Button(BaseModel):
    showText: str
    sendText: str


class Resource(BaseModel):
    showText: str
    resourceId: str


class Test(BaseModel):
    showText: str
    testId: str

class ChatResponse(BaseModel):
    role:str
    content: str
    buttonList: List[Button]
    resourceList: List[Resource]
    testList: List[Test]
    timestamp:float
