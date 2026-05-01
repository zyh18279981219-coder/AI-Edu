from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from DigitalTwinModule.data_collector import DataCollector
from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
from DigitalTwinModule.student_course_profile_service import (
    get_student_course_profile as build_student_course_profile,
)
from DigitalTwinModule.student_twin_service import StudentTwinService
from DigitalTwinModule.teacher_twin_service import TeacherTwinService
from DigitalTwinModule.trend_tracker import TrendTracker
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from DatabaseModule.sqlite_store import get_sqlite_store
from PathPlannerModule.path_planner_agent import PathPlannerAgent

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])
logger = logging.getLogger(__name__)


class QuizScoreRequest(BaseModel):
    username: str
    node_id: str
    score: float


class NodeScoreUpdateRequest(BaseModel):
    new_score: float


class TeacherExternalMetricsRequest(BaseModel):
    metrics: dict


class StudentCourseProfileRequest(BaseModel):
    student_id: str
    course_id: str


class TeacherInteractionEventRequest(BaseModel):
    teacher_username: str
    event_type: str
    course_id: str | None = None
    class_name: str | None = None
    target_id: str | None = None
    student_username: str | None = None
    response_minutes: float | None = None
    occurred_at: str | None = None
    payload: dict = {}


class TeacherResearchEventRequest(BaseModel):
    teacher_username: str
    event_type: str
    resource_id: str | None = None
    occurred_at: str | None = None
    payload: dict = {}


class TeacherGradingEventRequest(BaseModel):
    assignment_id: str
    teacher_username: str
    event_type: str
    submission_id: str | None = None
    student_username: str | None = None
    grading_minutes: float | None = None
    is_ai_recommended: bool = False
    is_ai_executed: bool = False
    occurred_at: str | None = None
    payload: dict = {}


@router.post("/collect/{username}")
async def collect_data(username: str) -> dict:
    store = TwinProfileStore()
    store.load_or_create(username)
    DataCollector().collect_all(username)
    profile = store.load_or_create(username)
    return {"status": "ok", "username": username, "last_updated": profile.last_updated}


@router.get("/profile/{username}")
async def get_profile(username: str) -> dict:
    store = TwinProfileStore()
    if not store.exists(username):
        raise HTTPException(status_code=404, detail=f"TwinProfile for user '{username}' not found")
    return store.load(username).model_dump()


@router.get("/student-profile/{username}")
async def get_student_profile_summary(username: str) -> dict:
    try:
        store = TwinProfileStore()
        if not store.exists(username):
            raise HTTPException(status_code=404, detail=f"TwinProfile for user '{username}' not found")
        profile = store.load(username)
        trend = TrendTracker().get_trend(username, days=30)
        return StudentTwinService().build_summary(profile, trend)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_student_profile_summary failed for %s", username)
        raise HTTPException(status_code=500, detail=f"Student twin summary failed: {exc}")


@router.post("/quiz-score")
async def update_quiz_score(body: QuizScoreRequest) -> dict:
    DataCollector().collect_quiz_score(body.username, body.node_id, body.score)
    store = TwinProfileStore()
    profile = store.load_or_create(body.username)
    return profile.model_dump()


@router.post("/path/generate/{username}")
async def generate_path(username: str) -> dict:
    try:
        return PathPlannerAgent().plan(username)
    except Exception as exc:
        logger.exception("generate_path failed for %s", username)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/path/{username}/current")
async def get_current_path(username: str) -> dict:
    latest = PathPlannerAgent().get_latest_path(username)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"No learning path found for user '{username}'")
    return latest


@router.patch("/path/{username}/node/{node_id}")
async def update_node_mastery(username: str, node_id: str, body: NodeScoreUpdateRequest) -> dict:
    result = PathPlannerAgent().update_path_on_mastery_change(username, node_id, body.new_score)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.get("/teacher-profile/{teacher_username}")
async def get_teacher_profile_summary(teacher_username: str) -> dict:
    try:
        return TeacherTwinService().build_summary(teacher_username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("get_teacher_profile_summary failed for %s", teacher_username)
        raise HTTPException(status_code=500, detail=f"Teacher twin summary failed: {exc}")


@router.post("/teacher-profile/{teacher_username}/external-sync")
async def sync_teacher_external_metrics(teacher_username: str, body: TeacherExternalMetricsRequest) -> dict:
    """
    Reserved for automatic external integrations.
    ETL jobs can push missing teaching-research / assessment detail metrics here.
    """
    store = get_sqlite_store()
    teacher = store.get_user_by_identifier("teacher", teacher_username)
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher '{teacher_username}' not found")
    canonical_teacher_username = str(teacher.get("username") or teacher_username)

    key = f"teacher_ext::{canonical_teacher_username}"
    current = store.get_user_state(key) or {}
    if not isinstance(current, dict):
        current = {}
    current.update(body.metrics or {})
    store.save_user_state(key, current)
    return {
        "status": "ok",
        "teacher_username": canonical_teacher_username,
        "saved_fields": sorted(list((body.metrics or {}).keys())),
    }


@router.post("/teacher-events/interaction")
async def record_teacher_interaction_event(body: TeacherInteractionEventRequest) -> dict:
    store = get_sqlite_store()
    teacher = store.get_user_by_identifier("teacher", body.teacher_username)
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher '{body.teacher_username}' not found")
    canonical = str(teacher.get("username") or body.teacher_username)
    get_teacher_event_repository().record_interaction_event(
        teacher_username=canonical,
        event_type=body.event_type,
        course_id=body.course_id,
        class_name=body.class_name,
        target_id=body.target_id,
        student_username=body.student_username,
        response_minutes=body.response_minutes,
        payload=body.payload,
        created_at=body.occurred_at,
    )
    return {"status": "ok", "teacher_username": canonical, "event_type": body.event_type}


@router.post("/teacher-events/research")
async def record_teacher_research_event(body: TeacherResearchEventRequest) -> dict:
    store = get_sqlite_store()
    teacher = store.get_user_by_identifier("teacher", body.teacher_username)
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher '{body.teacher_username}' not found")
    canonical = str(teacher.get("username") or body.teacher_username)
    get_teacher_event_repository().record_research_event(
        teacher_username=canonical,
        event_type=body.event_type,
        resource_id=body.resource_id,
        payload=body.payload,
        created_at=body.occurred_at,
    )
    return {"status": "ok", "teacher_username": canonical, "event_type": body.event_type}


@router.post("/teacher-events/grading")
async def record_teacher_grading_event(body: TeacherGradingEventRequest) -> dict:
    store = get_sqlite_store()
    teacher = store.get_user_by_identifier("teacher", body.teacher_username)
    if not teacher:
        raise HTTPException(status_code=404, detail=f"Teacher '{body.teacher_username}' not found")
    canonical = str(teacher.get("username") or body.teacher_username)
    get_teacher_event_repository().record_grading_event(
        assignment_id=body.assignment_id,
        submission_id=body.submission_id,
        teacher_username=canonical,
        student_username=body.student_username,
        event_type=body.event_type,
        grading_minutes=body.grading_minutes,
        is_ai_recommended=body.is_ai_recommended,
        is_ai_executed=body.is_ai_executed,
        payload=body.payload,
        created_at=body.occurred_at,
    )
    return {"status": "ok", "teacher_username": canonical, "event_type": body.event_type}


@router.post("/student-course-profile")
async def get_student_course_profile(body: StudentCourseProfileRequest) -> dict:
    try:
        return build_student_course_profile(body.student_id, body.course_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
