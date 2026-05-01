from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

from DatabaseModule.sqlite_store import get_sqlite_store
from HomeworkModule.service import HomeworkService
from TeachingResearchModule.service import TeachingResearchService
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/teaching-research", tags=["teaching-research"])
session_manager = get_session_manager()
sqlite_store = get_sqlite_store()
service = TeachingResearchService()
homework_service = HomeworkService()


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


def _collect_context_options(teacher_username: str) -> Dict[str, list[Dict[str, str]]]:
    classes: set[str] = set()
    courses: dict[str, str] = {}

    assignments = homework_service.list_assignments(created_by=teacher_username)
    for assignment in assignments:
        class_name = str(assignment.get("class_name") or "").strip()
        course_id = str(assignment.get("course_id") or "").strip()
        if class_name:
            classes.add(class_name)
        if course_id:
            courses[course_id] = course_id

    records = service.list_records(teacher_username)
    for item in records:
        class_name = str(item.get("class_name") or "").strip()
        course_id = str(item.get("course_id") or "").strip()
        if class_name:
            classes.add(class_name)
        if course_id:
            courses[course_id] = course_id

    links = sqlite_store.list_teacher_students(teacher_username)
    for link in links:
        payload = link.get("student_payload") or {}
        class_name = str(
            payload.get("class_name")
            or payload.get("class")
            or payload.get("className")
            or ""
        ).strip()
        course_id = str(
            payload.get("course_id")
            or payload.get("course")
            or payload.get("courseId")
            or ""
        ).strip()
        if class_name:
            classes.add(class_name)
        if course_id:
            courses[course_id] = course_id

    return {
        "class_options": [{"label": item, "value": item} for item in sorted(classes)],
        "course_options": [{"label": value, "value": key} for key, value in sorted(courses.items(), key=lambda x: x[0])],
    }


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


@router.get("/context-options")
def get_context_options(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    teacher_username = str(session.get("username") or "")
    return {"success": True, **_collect_context_options(teacher_username)}
