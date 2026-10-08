from typing import List, Optional

from fastapi import HTTPException, APIRouter, Cookie
from fastapi.responses import StreamingResponse

from .models import CourseNameRequest, ChatHistoryRequest
from .models.chat_request import ChatRequest
from .models.chat_response import ChatResponse
from . import service
from .effectiveness_service import get_effectiveness_summary
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


@router.get("/effectiveness/summary")
async def effectiveness_summary(
    course_id: Optional[str] = None,
    student_username: Optional[str] = None,
    limit: int = 500,
    low_score_threshold: float = 60.0,
    session_id: Optional[str] = Cookie(None),
):
    session = get_current_user(session_id)
    requested_student = _student_username_for_effectiveness(session, student_username)
    result = get_effectiveness_summary(
        course_id=course_id,
        student_username=requested_student,
        limit=limit,
        low_score_threshold=low_score_threshold,
    )
    return _effectiveness_for_session(result, session)


session_manager = get_session_manager()


def get_current_user(session_id: str):
    if not session_id:
        return None
    return session_manager.get_session(session_id)


def _session_username(session: dict | None) -> str:
    return str((session or {}).get("username") or (session or {}).get("user_id") or "").strip()


def _student_username_for_effectiveness(session: dict | None, requested: str | None) -> str | None:
    user_type = str((session or {}).get("user_type") or "").strip()
    session_username = _session_username(session)
    requested_username = str(requested or "").strip()
    if user_type != "student":
        return requested_username or None
    if requested_username and requested_username != session_username:
        raise HTTPException(status_code=403, detail="Students can only read their own 5E effectiveness summary")
    return session_username or requested_username or None


def _student_safe_effectiveness_summary(result: dict) -> dict:
    safe = {
        "status": result.get("status"),
        "course_id": result.get("course_id"),
        "student_username": result.get("student_username"),
        "record_count": result.get("record_count", 0),
        "outcome_supported_count": result.get("outcome_supported_count", 0),
        "process_only_count": result.get("process_only_count", 0),
        "insufficient_evidence_count": result.get("insufficient_evidence_count", 0),
        "effectiveness_level": result.get("effectiveness_level"),
        "evidence_status": result.get("evidence_status"),
        "stage_distribution": result.get("stage_distribution") or [],
        "student_view": result.get("student_view") or {},
        "recent_evidence": [],
        "message": result.get("message") or "",
    }
    for item in result.get("recent_evidence") or []:
        if not isinstance(item, dict):
            continue
        safe["recent_evidence"].append(
            {
                "record_id": item.get("record_id"),
                "course_id": item.get("course_id"),
                "node_id": item.get("node_id"),
                "stage": item.get("stage"),
                "effectiveness_level": item.get("effectiveness_level"),
                "evidence_status": item.get("evidence_status"),
                "calculated_at": item.get("calculated_at"),
                "summary": item.get("student_feedback") or item.get("summary") or "",
                "student_feedback": item.get("student_feedback"),
                "mastery_update_policy": item.get("mastery_update_policy"),
            }
        )
    return safe


def _effectiveness_for_session(result: dict, session: dict | None) -> dict:
    user_type = str((session or {}).get("user_type") or "").strip()
    if user_type == "student":
        return _student_safe_effectiveness_summary(result)
    return result
