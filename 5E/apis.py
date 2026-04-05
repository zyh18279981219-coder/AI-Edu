from typing import List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

import service
from models.chat_request import ChatRequest
from models.chat_response import ChatResponse
router = APIRouter(prefix='/chat')


@router.get("/history/{user_id}/{lesson_id}", response_model=List[ChatResponse])
async def get_conversation_history(user_id: str, lesson_id: str):
    return await service.get_history_by_user_and_lesson(user_id, lesson_id)


@router.post("/message")
async def receive_chat_content(request: ChatRequest):
    return StreamingResponse(service.chat_message_stream(request), media_type="text/plain")
