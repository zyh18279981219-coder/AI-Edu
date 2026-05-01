from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

from DatabaseModule.sqlite_store import get_sqlite_store
from TeachingInteractionModule.service import TeachingInteractionService
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/teaching-interaction", tags=["teaching-interaction"])
session_manager = get_session_manager()
sqlite_store = get_sqlite_store()
service = TeachingInteractionService()


class AnnouncementCreateRequest(BaseModel):
    title: str
    content: str
    class_name: str | None = None
    course_id: str | None = None


class DiscussionTopicCreateRequest(BaseModel):
    title: str
    content: str
    class_name: str | None = None
    course_id: str | None = None


class DiscussionPostCreateRequest(BaseModel):
    topic_id: str
    author_username: str
    author_role: str
    content: str
    replied_to_post_id: str | None = None
    replied_to_created_at: str | None = None


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


@router.get("/announcements")
def list_announcements(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    rows = service.list_announcements(str(session.get("username") or ""))
    return {"success": True, "announcements": rows}


@router.post("/announcements")
def create_announcement(data: AnnouncementCreateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    record = service.create_announcement(
        {
            "teacher_username": str(session.get("username") or ""),
            "title": data.title,
            "content": data.content,
            "class_name": data.class_name,
            "course_id": data.course_id,
        }
    )
    return {"success": True, "announcement": record}


@router.get("/topics")
def list_topics(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    rows = service.list_topics(str(session.get("username") or ""))
    return {"success": True, "topics": rows}


@router.post("/topics")
def create_topic(data: DiscussionTopicCreateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    record = service.create_topic(
        {
            "teacher_username": str(session.get("username") or ""),
            "title": data.title,
            "content": data.content,
            "class_name": data.class_name,
            "course_id": data.course_id,
        }
    )
    return {"success": True, "topic": record}


@router.post("/posts")
def create_post(data: DiscussionPostCreateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        author_role = str(data.author_role or "teacher").strip()
        author_username = str(session.get("username") or "") if author_role == "teacher" else data.author_username
        record = service.add_post(
            teacher_username=str(session.get("username") or ""),
            topic_id=data.topic_id,
            author_username=author_username,
            author_role=author_role,
            content=data.content,
            replied_to_post_id=data.replied_to_post_id,
            replied_to_created_at=data.replied_to_created_at,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "post": record}
