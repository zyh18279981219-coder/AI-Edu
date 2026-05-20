from typing import List, Optional

from fastapi import HTTPException, APIRouter, Cookie
from fastapi.responses import StreamingResponse

import service
from models import CourseNameRequest, ChatHistoryRequest
from models.chat_request import ChatRequest
from models.chat_response import ChatResponse
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/5e")
fiveE_router = router


@router.get("/chat/history/{user_id}/{lesson_id}", response_model=List[ChatResponse])
async def conversation_history(user_id: str, lesson_id: str):
    return await service.get_history_by_student_and_course(user_id, lesson_id)


@router.post("/chat/history")
async def get_conversation_history(data: ChatHistoryRequest):
    return await service.get_history_by_student_and_course(data.student_id, data.course_id)


@router.post("/chat/message")
async def receive_chat_content(data: ChatRequest):
    return StreamingResponse(service.chat_message_stream(data), media_type="text/plain")


@router.post("/course/id-by-name")
async def api_get_course_id_by_name(data: CourseNameRequest, session_id: Optional[str] = Cookie(None)):
    session = get_current_user(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    course_name = data.course_name
    course_id = await service.get_course_id_by_name(course_name)
    if not course_id:
        raise HTTPException(status_code=404, detail=f"Course '{course_name}' not found")
    return {"success": True, "course_id": course_id}


@router.get("/ping")
async def ping():
    return "pong"


session_manager = get_session_manager()


def get_current_user(session_id: str):
    if not session_id:
        return None
    return session_manager.get_session(session_id)
