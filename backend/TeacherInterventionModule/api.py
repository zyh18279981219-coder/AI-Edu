from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Cookie, HTTPException

from DatabaseModule.store import get_database_store
from TeacherInterventionModule.models import (
    DiagnoseStudentsRequest,
    GenerateInterventionDraftRequest,
    StudentAnswerUpdateRequest,
    StudentDecisionRequest,
    StudentProgressUpdateRequest,
    StudentStructuredTaskUpdateRequest,
    TeacherQuestionGradeRequest,
    UpdateInterventionDraftRequest,
)
from TeacherInterventionModule.service import TeacherInterventionService
from tools.session_manager import get_session_manager


router = APIRouter(prefix="/api/intervention", tags=["teacher-intervention"])
session_manager = get_session_manager()
database_store = get_database_store()
service = TeacherInterventionService()


def _require_session(session_id: Optional[str]) -> Dict[str, Any]:
    if not session_id:
        raise HTTPException(status_code=401, detail="请先登录")
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录")
    return session


def _require_teacher(session_id: Optional[str]) -> Dict[str, Any]:
    session = _require_session(session_id)
    if session.get("user_type") != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可访问")
    if not database_store.get_user("teacher", str(session.get("username") or "")):
        raise HTTPException(status_code=404, detail="教师账号不存在")
    return session


def _require_student(session_id: Optional[str]) -> Dict[str, Any]:
    session = _require_session(session_id)
    if session.get("user_type") != "student":
        raise HTTPException(status_code=403, detail="仅学生可访问")
    if not database_store.get_user("student", str(session.get("username") or "")):
        raise HTTPException(status_code=404, detail="学生账号不存在")
    return session


@router.get("/teacher/students-overview")
def get_teacher_students_overview(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    data = service.get_students_overview(session)
    return {"success": True, "data": data}


@router.post("/teacher/diagnose")
def diagnose_students(data: DiagnoseStudentsRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    result = service.diagnose_students(session, data.student_usernames)
    return {"success": True, "data": result}


@router.post("/teacher/generate-draft")
def generate_intervention_draft(
    data: GenerateInterventionDraftRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher(session_id)
    try:
        package = service.generate_intervention_draft(
            teacher_session=session,
            student_username=str(data.student_username).strip(),
            question_count=int(data.question_count),
            difficulty=str(data.difficulty).strip() or "中等",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.get("/teacher/packages")
def list_teacher_packages(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    packages = service.list_teacher_packages(str(session.get("username") or ""))
    return {"success": True, "packages": packages}


@router.get("/teacher/packages/{package_id}")
def get_teacher_package_detail(package_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        package = service.get_teacher_package(
            teacher_username=str(session.get("username") or ""),
            package_id=package_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.put("/teacher/packages/{package_id}")
def update_teacher_package(
    package_id: str,
    data: UpdateInterventionDraftRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher(session_id)
    try:
        package = service.update_teacher_package(
            teacher_username=str(session.get("username") or ""),
            package_id=package_id,
            updates={
                "strategy_summary": data.strategy_summary,
                "recommended_concepts": data.recommended_concepts,
                "recommended_videos": data.recommended_videos,
                "resource_tasks": [item.model_dump() for item in data.resource_tasks],
                "assignment_tasks": [item.model_dump() for item in data.assignment_tasks],
                "quiz_tasks": [item.model_dump() for item in data.quiz_tasks],
                "code_tasks": [item.model_dump() for item in data.code_tasks],
                "questions": [item.model_dump() for item in data.questions],
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.post("/teacher/packages/{package_id}/push")
def push_teacher_package(package_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    try:
        package = service.push_package_to_student(
            teacher_username=str(session.get("username") or ""),
            package_id=package_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.get("/teacher/progress")
def list_teacher_progress(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    rows = service.get_teacher_progress(str(session.get("username") or ""))
    return {"success": True, "rows": rows}


@router.get("/teacher/task-reference-options")
def list_teacher_task_reference_options(
    course_id: str = "course_big_data",
    session_id: Optional[str] = Cookie(None),
):
    _require_teacher(session_id)
    return {"success": True, "options": service.get_task_reference_options(course_id)}


@router.post("/teacher/packages/{package_id}/grade")
def grade_teacher_package_question(
    package_id: str,
    data: TeacherQuestionGradeRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher(session_id)
    try:
        package = service.grade_teacher_question(
            teacher_username=str(session.get("username") or ""),
            package_id=package_id,
            question_id=data.question_id,
            teacher_score=float(data.teacher_score),
            teacher_comment=data.teacher_comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.get("/student/packages")
def list_student_packages(session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    packages = service.list_student_packages(str(session.get("username") or ""))
    return {"success": True, "packages": packages}


@router.get("/student/packages/{package_id}")
def get_student_package_detail(package_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    try:
        package = service.get_student_package(
            student_username=str(session.get("username") or ""),
            package_id=package_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.post("/student/packages/{package_id}/decision")
def student_decide_package(
    package_id: str,
    data: StudentDecisionRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_student(session_id)
    try:
        package = service.student_decide_package(
            student_username=str(session.get("username") or ""),
            package_id=package_id,
            decision=data.decision,
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.post("/student/packages/{package_id}/answers")
def student_save_answer(
    package_id: str,
    data: StudentAnswerUpdateRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_student(session_id)
    try:
        package = service.student_save_answer(
            student_username=str(session.get("username") or ""),
            package_id=package_id,
            question_id=data.question_id,
            answer=data.answer,
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.post("/student/packages/{package_id}/tasks")
def student_update_structured_task(
    package_id: str,
    data: StudentStructuredTaskUpdateRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_student(session_id)
    try:
        package = service.student_update_structured_task(
            student_username=str(session.get("username") or ""),
            package_id=package_id,
            task_type=data.task_type,
            task_id=data.task_id,
            completed=bool(data.completed),
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "package": package}


@router.post("/student/packages/{package_id}/progress")
def student_update_package_progress(
    package_id: str,
    data: StudentProgressUpdateRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_student(session_id)
    try:
        package = service.student_update_progress(
            student_username=str(session.get("username") or ""),
            package_id=package_id,
            status=data.status,
            completion_rate=data.completion_rate,
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"success": True, "package": package}
