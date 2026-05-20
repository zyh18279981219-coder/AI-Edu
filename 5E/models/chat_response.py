from typing import List

from pydantic import BaseModel, Field


class Button(BaseModel):
    showText: str = Field(description="按钮显示文字")
    sendText: str = Field(description="点击后自动发送到后台的文字")


class Resource(BaseModel):
    showText: str = Field(description="资料显示名称")
    resourceId: str = Field(description="资料唯一ID")


class Test(BaseModel):
    showText: str = Field(description="测验显示名称")
    testId: str = Field(description="测验唯一ID")


class ChatResponse(BaseModel):
    context: str = Field(description="必填：文字对话内容")
    buttonList: List[Button] = Field(description="交互按钮列表")
    resourcesList: List[Resource] = Field(description="资料列表")
    testList: List[Test] = Field(description="测验列表")

class OrchestratorResponse(BaseModel):
    target_agent: str =Field(description="目标调用的agent名称")
