from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

from DatabaseModule.sqlite_store import get_sqlite_store
from TeachingResearchModule.service import TeachingResearchService
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/teaching-research", tags=["teaching-research"])
session_manager = get_session_manager()
sqlite_store = get_sqlite_store()
service = TeachingResearchService()


class TeachingResearchCreateRequest(BaseModel):
    activity_type: str
    title: str
    description: str = ""
    resource_link: str = ""
    class_name: str = ""
    course_id: str = ""
    happened_at: str | None = None


def _require_teacher(session_id: Optional[str]) -> Dict[str, Any]:
    if not session_id:
        raise HTTPException(status_code=401, detail="请先登录")
    session = session_manager.get_session(session_id)
    if not session or session.get("user_type") != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可访问")
    username = str(session.get("username") or "")
    if not sqlite_store.get_user("teacher", username):
        raise HTTPException(status_code=404, detail="教师账号不存在")
    return session


@router.get("/records")
def list_research_records(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    rows = service.list_records(str(session.get("username") or ""))
    return {"success": True, "records": rows}


@router.post("/records")
def create_research_record(data: TeachingResearchCreateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    record = service.create_record(
        {
            "teacher_username": str(session.get("username") or ""),
            "activity_type": data.activity_type,
            "title": data.title,
            "description": data.description,
            "resource_link": data.resource_link,
            "class_name": data.class_name,
            "course_id": data.course_id,
            "happened_at": data.happened_at,
        }
    )
    return {"success": True, "record": record}

