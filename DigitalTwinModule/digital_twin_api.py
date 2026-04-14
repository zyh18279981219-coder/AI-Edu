from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from DigitalTwinModule.data_collector import DataCollector
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


def _match_course_node(course_id: str, node: dict) -> bool:
    token = str(course_id or "").strip().lower()
    if not token:
        return False
    node_id = str(node.get("node_id") or "").lower()
    if token in node_id:
        return True
    for part in node.get("node_path") or []:
        if token in str(part).lower():
            return True
    return False


def _build_node_item(node: dict) -> dict:
    quiz_value = node.get("quiz_score")
    try:
        quiz_value = float(quiz_value) if quiz_value is not None else None
    except (TypeError, ValueError):
        quiz_value = None
    return {
        "node_id": node.get("node_id"),
        "node_path": node.get("node_path") or [],
        "mastery_score": round(float(node.get("mastery_score", 0) or 0), 2),
        "progress": round(float(node.get("progress", 0) or 0), 2),
        "quiz_score": round(float(quiz_value or 0), 2),
    }


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


@router.post("/student-course-profile")
async def get_student_course_profile(body: StudentCourseProfileRequest) -> dict:
    student_identifier = str(body.student_id or "").strip()
    course_id = str(body.course_id or "").strip()
    if not student_identifier:
        raise HTTPException(status_code=400, detail="student_id is required")
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required")

    store = get_sqlite_store()
    user = store.get_user_by_identifier("student", student_identifier)
    if not user:
        raise HTTPException(status_code=404, detail=f"Student '{student_identifier}' not found")
    username = str(user.get("username") or "")
    if not username:
        raise HTTPException(status_code=404, detail=f"Student '{student_identifier}' not found")

    profile_store = TwinProfileStore()
    if not profile_store.exists(username):
        raise HTTPException(status_code=404, detail=f"Twin profile for student '{student_identifier}' not found")

    profile = profile_store.load(username)
    trend = TrendTracker().get_trend(username, days=30)
    summary = StudentTwinService().build_summary(profile, trend)
    summary["student_id"] = student_identifier
    summary["course_id"] = course_id

    matched_raw = [node.model_dump() if hasattr(node, "model_dump") else node for node in (profile.knowledge_nodes or [])]
    matched_raw = [node for node in matched_raw if isinstance(node, dict) and _match_course_node(course_id, node)]
    matched_nodes = [_build_node_item(node) for node in matched_raw]
    weak_nodes = [node for node in matched_nodes if float(node.get("mastery_score") or 0) < 60]

    progress_values = [float(node.get("progress", 0) or 0) for node in matched_nodes]
    quiz_values = [float(node.get("quiz_score", 0) or 0) for node in matched_nodes]
    summary["weak_nodes"] = weak_nodes
    summary["course_node_count"] = len(matched_nodes)
    summary["matched_nodes"] = matched_nodes
    summary["node_summary"] = {
        "total_nodes": len(matched_nodes),
        "weak_node_count": len(weak_nodes),
        "strong_node_count": sum(1 for node in matched_nodes if float(node.get("mastery_score") or 0) >= 80),
        "average_progress": round(sum(progress_values) / len(progress_values), 2) if progress_values else 0.0,
        "average_quiz_score": round(sum(quiz_values) / len(quiz_values), 2) if quiz_values else 0.0,
    }
    summary["outputs"]["for_course_twin"]["weak_nodes"] = [item["node_id"] for item in weak_nodes[:5]]
    summary["outputs"]["for_teacher_twin"]["weak_nodes"] = weak_nodes[:5]
    return summary
