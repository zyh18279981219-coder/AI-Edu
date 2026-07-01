from __future__ import annotations

import logging
import os
from time import monotonic
from typing import Literal

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel, Field

from DiagnosisModule.diagnosis_service import StudentDiagnosisService
from DigitalTwinModule.data_collector import DataCollector
from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
from DigitalTwinModule.student_course_profile_service import (
    get_student_course_profile as build_student_course_profile,
)
from DigitalTwinModule.score_calculator import ScoreCalculator
from DigitalTwinModule.student_twin_service import StudentTwinService
from DigitalTwinModule.teacher_twin_service import TeacherTwinService
from DigitalTwinModule.trend_tracker import TrendTracker
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from DatabaseModule.store import get_database_store
from PathPlannerModule.path_planner_agent import PathPlannerAgent
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])
logger = logging.getLogger(__name__)
_summary_cache: dict[str, tuple[float, dict]] = {}
_summary_cache_ttl_seconds = float(os.getenv("TWIN_SUMMARY_CACHE_SECONDS", "30"))
_session_manager = get_session_manager()


def _is_legacy_mastery_profile(profile) -> bool:
    nodes = list(profile.knowledge_nodes or [])
    overall = float(profile.overall_mastery or 0.0)
    if not nodes:
        return 0.0 <= overall <= 1.0

    has_percent_inputs = any(
        float(node.progress or 0.0) > 1.0
        or (node.quiz_score is not None and float(node.quiz_score) > 1.0)
        for node in nodes
    )
    has_fraction_outputs = 0.0 <= overall <= 1.0 and all(
        0.0 <= float(node.mastery_score or 0.0) <= 1.0
        for node in nodes
    )
    return has_percent_inputs and has_fraction_outputs


def _normalize_legacy_profile(store: TwinProfileStore, profile):
    if not _is_legacy_mastery_profile(profile):
        return profile

    normalized = ScoreCalculator().recalculate_profile(profile)
    try:
        store.save(normalized)
    except Exception:
        logger.exception("Failed to persist normalized legacy twin profile for %s", profile.username)
    else:
        logger.warning(
            "Normalized legacy twin profile scale for %s: %.2f -> %.2f",
            profile.username,
            float(profile.overall_mastery or 0.0),
            float(normalized.overall_mastery or 0.0),
        )
    return normalized


def _load_existing_profile(store: TwinProfileStore, username: str):
    try:
        return store.load(username)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"TwinProfile for user '{username}' not found")


def _normalize_legacy_trend(trend, current_overall: float):
    if not trend:
        return trend

    should_scale = current_overall > 1.0 or any(float(point.overall_mastery or 0.0) > 1.0 for point in trend)
    if not should_scale:
        return trend

    normalized = []
    changed = False
    for point in trend:
        value = float(point.overall_mastery or 0.0)
        if 0.0 <= value <= 1.0:
            value = round(value * 100.0, 2)
            changed = True
        normalized.append(point.model_copy(update={"overall_mastery": value}))

    if changed:
        logger.warning("Normalized legacy twin trend scale for current_overall=%.2f", current_overall)
    return normalized


def _current_session(session_id: str | None) -> dict | None:
    if not session_id:
        return None
    try:
        return _session_manager.get_session(session_id)
    except Exception:
        return None


def _session_username(session: dict | None) -> str:
    return str((session or {}).get("username") or (session or {}).get("login_id") or "").strip()


def _require_student_self_session(username: str, session_id: str | None) -> dict:
    session = _current_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="Student authentication required")
    if str(session.get("user_type") or "") != "student":
        raise HTTPException(status_code=403, detail="Only students can generate or update formal learning paths")
    if _session_username(session) != str(username or "").strip():
        raise HTTPException(status_code=403, detail="Students can only operate their own learning path")
    return session


def _teacher_student_usernames(teacher_username: str) -> set[str]:
    if not teacher_username:
        return set()
    store = get_database_store()
    try:
        return {
            str(item.get("student_username") or "").strip()
            for item in store.list_teacher_students(teacher_username)
            if str(item.get("student_username") or "").strip()
        }
    except Exception:
        logger.exception("Failed to load teacher student scope for %s", teacher_username)
        return set()


def _require_path_read_scope(username: str, session_id: str | None) -> dict:
    session = _current_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="Authentication required")
    user_type = str(session.get("user_type") or "")
    session_username = _session_username(session)
    if user_type == "student":
        if session_username != str(username or "").strip():
            raise HTTPException(status_code=403, detail="Students can only read their own learning path")
        return session
    if user_type == "teacher":
        if str(username or "").strip() not in _teacher_student_usernames(session_username):
            raise HTTPException(status_code=403, detail="Student is outside the teacher's authorized scope")
        return session
    if user_type == "admin":
        return session
    raise HTTPException(status_code=403, detail="Authentication required")


def _require_student_or_teacher_scope(username: str, session_id: str | None) -> dict:
    session = _current_session(session_id)
    if not session:
        raise HTTPException(status_code=403, detail="Authentication required")
    user_type = str(session.get("user_type") or "")
    session_username = _session_username(session)
    if user_type == "student":
        if session_username != str(username or "").strip():
            raise HTTPException(status_code=403, detail="Students can only read their own data")
        return session
    if user_type == "teacher":
        if str(username or "").strip() not in _teacher_student_usernames(session_username):
            raise HTTPException(status_code=403, detail="Student is outside the teacher's authorized scope")
        return session
    if user_type == "admin":
        return session
    raise HTTPException(status_code=403, detail="Authentication required")


def _student_safe_diagnosis(result: dict) -> dict:
    safe_keys = {
        "report_id",
        "username",
        "user_id",
        "course_id",
        "report_date",
        "diagnosis_type",
        "evidence_level",
        "confidence",
        "persona_summary",
        "student_view",
        "weak_nodes",
        "formulas",
        "thresholds",
        "generated_at",
    }
    return {key: value for key, value in result.items() if key in safe_keys}


def _diagnosis_for_session(result: dict, session: dict | None, username: str) -> dict:
    user_type = str((session or {}).get("user_type") or "").strip()
    session_username = str((session or {}).get("username") or (session or {}).get("user_id") or "").strip()
    if user_type in {"teacher", "admin"}:
        return result
    if user_type == "student" and session_username and session_username != username:
        raise HTTPException(status_code=403, detail="Students can only read their own diagnosis")
    return _student_safe_diagnosis(result)


class QuizScoreRequest(BaseModel):
    username: str
    node_id: str
    score: float


class NodeScoreUpdateRequest(BaseModel):
    new_score: float


class PathNodeStatusUpdateRequest(BaseModel):
    status: Literal["pending", "in_progress", "completed", "skipped"]
    plan_id: int | None = None
    mastery_after: float | None = None
    payload: dict = Field(default_factory=dict)
    refresh_path: bool | None = None


class TeacherExternalMetricsRequest(BaseModel):
    metrics: dict


class StudentCourseProfileRequest(BaseModel):
    student_id: str
    course_id: str


class DiagnosisRequest(BaseModel):
    course_id: str | None = None
    persist: bool = True


class PathGenerationRequest(BaseModel):
    course_id: str | None = None
    trigger_type: str = "diagnosis"
    manual_goal: str | None = None


class DiagnosisCorrectionRequest(BaseModel):
    report_id: str
    username: str
    course_id: str
    teacher_username: str
    node_id: str | None = None
    original_reason_type: str | None = None
    corrected_reason_type: str | None = None
    original_evidence_level: str | None = None
    corrected_evidence_level: str | None = None
    correction_note: str | None = None
    payload: dict = {}


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
async def collect_data(username: str, session_id: str | None = Cookie(None)) -> dict:
    _require_student_self_session(username, session_id)
    store = TwinProfileStore()
    store.load_or_create(username)
    DataCollector().collect_all(username)
    profile = store.load_or_create(username)
    return {"status": "ok", "username": username, "last_updated": profile.last_updated}


@router.get("/profile/{username}")
async def get_profile(username: str, session_id: str | None = Cookie(None)) -> dict:
    _require_student_or_teacher_scope(username, session_id)
    store = TwinProfileStore()
    profile = _normalize_legacy_profile(store, _load_existing_profile(store, username))
    return profile.model_dump()


@router.get("/student-profile/{username}")
async def get_student_profile_summary(username: str, session_id: str | None = Cookie(None)) -> dict:
    try:
        _require_student_or_teacher_scope(username, session_id)
        cached = _summary_cache.get(username)
        if cached and monotonic() - cached[0] < _summary_cache_ttl_seconds:
            return cached[1]

        store = TwinProfileStore()
        profile = _normalize_legacy_profile(store, _load_existing_profile(store, username))
        trend = TrendTracker().get_trend(username, days=30)
        trend = _normalize_legacy_trend(trend, float(profile.overall_mastery or 0.0))
        result = StudentTwinService().build_summary(profile, trend)
        _summary_cache[username] = (monotonic(), result)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_student_profile_summary failed for %s", username)
        raise HTTPException(status_code=500, detail=f"Student twin summary failed: {exc}")


@router.post("/quiz-score")
async def update_quiz_score(body: QuizScoreRequest, session_id: str | None = Cookie(None)) -> dict:
    _require_student_self_session(body.username, session_id)
    DataCollector().collect_quiz_score(body.username, body.node_id, body.score)
    store = TwinProfileStore()
    profile = store.load_or_create(body.username)
    return profile.model_dump()


@router.post("/path/generate/{username}")
async def generate_path(
    username: str,
    body: PathGenerationRequest | None = None,
    session_id: str | None = Cookie(None),
) -> dict:
    try:
        _require_student_self_session(username, session_id)
        payload = body or PathGenerationRequest()
        return PathPlannerAgent().plan(
            username,
            course_id=payload.course_id,
            trigger_type=payload.trigger_type,
            manual_goal=payload.manual_goal,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("generate_path failed for %s", username)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/diagnosis/{username}")
async def generate_student_diagnosis(
    username: str,
    body: DiagnosisRequest,
    session_id: str | None = Cookie(None),
) -> dict:
    try:
        _require_student_or_teacher_scope(username, session_id)
        result = StudentDiagnosisService().generate_student_diagnosis(
            username,
            course_id=body.course_id,
            persist=body.persist,
        )
        return _diagnosis_for_session(result, _current_session(session_id), username)
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        logger.exception("generate_student_diagnosis failed for %s", username)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/diagnosis-corrections")
async def record_diagnosis_correction(body: DiagnosisCorrectionRequest, session_id: str | None = Cookie(None)) -> dict:
    session = _current_session(session_id)
    if not session or str(session.get("user_type") or "") not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher authentication required")
    teacher_username = _session_username(session)
    if str(body.teacher_username or "").strip() and str(body.teacher_username or "").strip() != teacher_username:
        raise HTTPException(status_code=403, detail="Teacher identity mismatch")
    if str(session.get("user_type") or "") == "teacher" and str(body.username or "").strip() not in _teacher_student_usernames(teacher_username):
        raise HTTPException(status_code=403, detail="Student is outside the teacher's authorized scope")
    store = get_database_store()
    try:
        correction_id = store.record_diagnosis_correction(
            report_id=body.report_id,
            username=body.username,
            course_id=body.course_id,
            teacher_username=teacher_username,
            node_id=body.node_id,
            original_reason_type=body.original_reason_type,
            corrected_reason_type=body.corrected_reason_type,
            original_evidence_level=body.original_evidence_level,
            corrected_evidence_level=body.corrected_evidence_level,
            correction_note=body.correction_note,
            payload=body.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("record_diagnosis_correction failed for report %s", body.report_id)
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "correction_id": correction_id}


@router.get("/diagnosis-corrections")
async def list_diagnosis_corrections(
    report_id: str | None = None,
    username: str | None = None,
    course_id: str | None = None,
    teacher_username: str | None = None,
    limit: int = 100,
    session_id: str | None = Cookie(None),
) -> dict:
    session = _current_session(session_id)
    if not session or str(session.get("user_type") or "") not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher authentication required")
    if str(session.get("user_type") or "") == "teacher":
        session_teacher = _session_username(session)
        if str(teacher_username or "").strip() and str(teacher_username or "").strip() != session_teacher:
            raise HTTPException(status_code=403, detail="Teacher identity mismatch")
        if username and username not in _teacher_student_usernames(session_teacher):
            raise HTTPException(status_code=403, detail="Student is outside the teacher's authorized scope")
        teacher_username = session_teacher
    store = get_database_store()
    try:
        rows = store.list_diagnosis_corrections(
            report_id=report_id,
            username=username,
            course_id=course_id,
            teacher_username=teacher_username,
            limit=limit,
        )
    except Exception as exc:
        logger.exception("list_diagnosis_corrections failed")
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "rows": rows}


@router.get("/path/{username}/current")
async def get_current_path(
    username: str,
    course_id: str | None = None,
    session_id: str | None = Cookie(None),
) -> dict:
    _require_path_read_scope(username, session_id)
    agent = PathPlannerAgent()
    try:
        latest = agent.get_latest_path(username, course_id=course_id)
    except TypeError:
        latest = agent.get_latest_path(username)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"No learning path found for user '{username}'")
    return latest


@router.get("/path/{username}/versions")
async def list_path_versions(
    username: str,
    limit: int = 10,
    course_id: str | None = None,
    session_id: str | None = Cookie(None),
) -> dict:
    _require_path_read_scope(username, session_id)
    agent = PathPlannerAgent()
    safe_limit = max(1, min(int(limit or 10), 30))
    try:
        versions = agent.list_path_versions(username, limit=safe_limit, course_id=course_id)
    except TypeError:
        versions = agent.list_path_versions(username, limit=safe_limit)
    return {"versions": versions, "count": len(versions)}


@router.patch("/path/{username}/node-status/{node_id}")
async def update_path_node_status(
    username: str,
    node_id: str,
    body: PathNodeStatusUpdateRequest,
    session_id: str | None = Cookie(None),
) -> dict:
    _require_student_self_session(username, session_id)
    store = get_database_store()
    if not hasattr(store, "update_learning_path_node_status"):
        raise HTTPException(status_code=500, detail="Learning path node status update is not supported")
    try:
        updated = store.update_learning_path_node_status(
            username,
            node_id,
            plan_id=body.plan_id,
            status=body.status,
            mastery_after=body.mastery_after,
            payload=body.payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("update_path_node_status failed for %s/%s", username, node_id)
        raise HTTPException(status_code=500, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Learning path node '{node_id}' not found for user '{username}'")

    fivee_outcome = None
    if body.status == "completed":
        try:
            from fiveE.effectiveness_service import link_path_continuation
            fivee_outcome = link_path_continuation(
                student_username=username,
                course_id=str(updated.get("course_id") or "").strip() or None,
                node_id=node_id,
                path_continue_rate=100.0,
            )
        except Exception as exc:
            logger.warning("5E path continuation link failed for %s/%s: %s", username, node_id, exc)

    should_refresh = bool(body.refresh_path) if body.refresh_path is not None else body.status == "completed"
    path_refresh = {
        "triggered": False,
        "trigger_type": "node_completed",
        "path": None,
        "error": None,
    }
    if should_refresh and body.status == "completed":
        try:
            course_id = str(updated.get("course_id") or "").strip() or None
            refresh_payload = PathPlannerAgent().plan(
                username,
                course_id=course_id,
                trigger_type="node_completed",
                manual_goal=f"Completed path node: {node_id}",
            )
            path_refresh.update(
                {
                    "triggered": True,
                    "path": refresh_payload,
                }
            )
        except Exception as exc:
            logger.exception("path refresh after node completion failed for %s/%s", username, node_id)
            path_refresh.update(
                {
                    "triggered": True,
                    "error": str(exc),
                }
            )

    return {"success": True, "node_status": updated, "path_refresh": path_refresh, "fivee_outcome": fivee_outcome}


@router.patch("/path/{username}/node/{node_id}")
async def update_node_mastery(
    username: str,
    node_id: str,
    body: NodeScoreUpdateRequest,
    session_id: str | None = Cookie(None),
) -> dict:
    _require_student_self_session(username, session_id)
    result = PathPlannerAgent().update_path_on_mastery_change(username, node_id, body.new_score)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.get("/teacher-profile/{teacher_username}")
async def get_teacher_profile_summary(teacher_username: str, session_id: str | None = Cookie(None)) -> dict:
    session = _current_session(session_id)
    if not session or str(session.get("user_type") or "") not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher authentication required")
    if str(session.get("user_type") or "") == "teacher" and _session_username(session) != str(teacher_username or "").strip():
        raise HTTPException(status_code=403, detail="Teachers can only read their own profile")
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
    store = get_database_store()
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
    store = get_database_store()
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
    store = get_database_store()
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
    store = get_database_store()
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
async def get_student_course_profile(body: StudentCourseProfileRequest, session_id: str | None = Cookie(None)) -> dict:
    try:
        _require_student_or_teacher_scope(body.student_id, session_id)
        return build_student_course_profile(body.student_id, body.course_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
