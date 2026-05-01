from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

from DatabaseModule.sqlite_store import get_sqlite_store
from HomeworkModule.service import HomeworkService
from TeachingInteractionModule.service import TeachingInteractionService
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/teaching-interaction", tags=["teaching-interaction"])
session_manager = get_session_manager()
sqlite_store = get_sqlite_store()
service = TeachingInteractionService()
homework_service = HomeworkService()


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


class AnnouncementUpdateRequest(BaseModel):
    title: str
    content: str
    class_name: str | None = None
    course_id: str | None = None


class DiscussionTopicUpdateRequest(BaseModel):
    title: str
    content: str
    class_name: str | None = None
    course_id: str | None = None


class PostUpdateRequest(BaseModel):
    content: str


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


def _require_student(session_id: Optional[str]) -> Dict[str, Any]:
    if not session_id:
        raise HTTPException(status_code=401, detail="请先登录")
    session = session_manager.get_session(session_id)
    if not session or session.get("user_type") != "student":
        raise HTTPException(status_code=403, detail="仅学生可访问")
    username = str(session.get("username") or "")
    if not sqlite_store.get_user("student", username):
        raise HTTPException(status_code=404, detail="学生账号不存在")
    return session


def _extract_student_context(student_username: str) -> Dict[str, str]:
    user = sqlite_store.get_user("student", student_username) or {}
    class_name = str(
        user.get("class_name")
        or user.get("class")
        or user.get("className")
        or ""
    ).strip()
    course_id = str(
        user.get("course_id")
        or user.get("course")
        or user.get("courseId")
        or ""
    ).strip()
    return {"class_name": class_name, "course_id": course_id}


def _extract_teacher_scope(student_username: str) -> set[str]:
    teacher_usernames: set[str] = set()
    for teacher in sqlite_store.list_users("teacher"):
        teacher_username = str(teacher.get("username") or "").strip()
        if not teacher_username:
            continue
        links = sqlite_store.list_teacher_students(teacher_username)
        for link in links:
            if str(link.get("student_username") or "").strip() == student_username:
                teacher_usernames.add(teacher_username)
                break
    return teacher_usernames


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

    announcements = service.list_announcements(teacher_username)
    for item in announcements:
        class_name = str(item.get("class_name") or "").strip()
        course_id = str(item.get("course_id") or "").strip()
        if class_name:
            classes.add(class_name)
        if course_id:
            courses[course_id] = course_id

    topics = service.list_topics(teacher_username)
    for item in topics:
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


@router.get("/announcements")
def list_announcements(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    rows = service.list_announcements(str(session.get("username") or ""))
    return {"success": True, "announcements": rows}


@router.get("/announcements/public")
def list_public_announcements(session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    student_username = str(session.get("username") or "")
    context = _extract_student_context(student_username)
    teacher_scope = _extract_teacher_scope(student_username)
    announcements = service.list_announcements_all()

    def visible(item: Dict[str, Any]) -> bool:
        teacher_username = str(item.get("teacher_username") or "").strip()
        if teacher_scope and teacher_username not in teacher_scope:
            return False
        class_name = str(item.get("class_name") or "").strip()
        course_id = str(item.get("course_id") or "").strip()
        if class_name and context["class_name"] and class_name != context["class_name"]:
            return False
        if course_id and context["course_id"] and course_id != context["course_id"]:
            return False
        return True

    rows = [item for item in announcements if visible(item)]
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


@router.put("/announcements/{announcement_id}")
def update_announcement(announcement_id: str, data: AnnouncementUpdateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        record = service.update_announcement(
            teacher_username=str(session.get("username") or ""),
            announcement_id=announcement_id,
            payload={
                "title": data.title,
                "content": data.content,
                "class_name": data.class_name,
                "course_id": data.course_id,
            },
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "announcement": record}


@router.delete("/announcements/{announcement_id}")
def delete_announcement(announcement_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        deleted = service.delete_announcement(str(session.get("username") or ""), announcement_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "deleted": deleted}


@router.get("/topics")
def list_topics(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    rows = service.list_topics(str(session.get("username") or ""))
    return {"success": True, "topics": rows}


@router.get("/topics/public")
def list_public_topics(session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    student_username = str(session.get("username") or "")
    context = _extract_student_context(student_username)
    teacher_scope = _extract_teacher_scope(student_username)
    topics = service.list_topics_all()

    def visible(item: Dict[str, Any]) -> bool:
        teacher_username = str(item.get("teacher_username") or "").strip()
        if teacher_scope and teacher_username not in teacher_scope:
            return False
        class_name = str(item.get("class_name") or "").strip()
        course_id = str(item.get("course_id") or "").strip()
        if class_name and context["class_name"] and class_name != context["class_name"]:
            return False
        if course_id and context["course_id"] and course_id != context["course_id"]:
            return False
        return True

    rows = [item for item in topics if visible(item)]
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


@router.put("/topics/{topic_id}")
def update_topic(topic_id: str, data: DiscussionTopicUpdateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        record = service.update_topic(
            teacher_username=str(session.get("username") or ""),
            topic_id=topic_id,
            payload={
                "title": data.title,
                "content": data.content,
                "class_name": data.class_name,
                "course_id": data.course_id,
            },
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "topic": record}


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        deleted = service.delete_topic(str(session.get("username") or ""), topic_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "deleted": deleted}


@router.get("/context-options")
def get_context_options(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    teacher_username = str(session.get("username") or "")
    return {"success": True, **_collect_context_options(teacher_username)}


@router.get("/analytics")
def get_interaction_analytics(window_days: int = 30, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    result = service.build_interaction_analytics(
        teacher_username=str(session.get("username") or ""),
        window_days=max(7, min(int(window_days or 30), 180)),
    )
    return {"success": True, "analytics": result}


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


@router.put("/posts/{post_id}")
def update_post(post_id: str, data: PostUpdateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        record = service.update_post(
            teacher_username=str(session.get("username") or ""),
            post_id=post_id,
            actor_username=str(session.get("username") or ""),
            actor_role="teacher",
            content=data.content,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "post": record}


@router.delete("/posts/{post_id}")
def delete_post(post_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        deleted = service.delete_post(
            teacher_username=str(session.get("username") or ""),
            post_id=post_id,
            actor_username=str(session.get("username") or ""),
            actor_role="teacher",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "deleted": deleted}


@router.post("/topics/{topic_id}/student-question")
def create_student_question(topic_id: str, content: str, session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    try:
        topic = service.repository.get_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="讨论话题不存在")
        record = service.add_post(
            teacher_username=str(topic.get("teacher_username") or ""),
            topic_id=topic_id,
            author_username=str(session.get("username") or ""),
            author_role="student",
            content=content,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "post": record}


@router.put("/posts/{post_id}/student")
def update_student_post(post_id: str, data: PostUpdateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    post = service.repository.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    topic = service.repository.get_topic(str(post.get("topic_id") or ""))
    if not topic:
        raise HTTPException(status_code=404, detail="讨论话题不存在")
    try:
        record = service.update_post(
            teacher_username=str(topic.get("teacher_username") or ""),
            post_id=post_id,
            actor_username=str(session.get("username") or ""),
            actor_role="student",
            content=data.content,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "post": record}


@router.delete("/posts/{post_id}/student")
def delete_student_post(post_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    post = service.repository.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    topic = service.repository.get_topic(str(post.get("topic_id") or ""))
    if not topic:
        raise HTTPException(status_code=404, detail="讨论话题不存在")
    try:
        deleted = service.delete_post(
            teacher_username=str(topic.get("teacher_username") or ""),
            post_id=post_id,
            actor_username=str(session.get("username") or ""),
            actor_role="student",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "deleted": deleted}
