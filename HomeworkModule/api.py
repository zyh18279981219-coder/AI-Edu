from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Cookie, HTTPException

from DatabaseModule.sqlite_store import get_sqlite_store
from HomeworkModule.exporter import export_homework_json_to_sqlite
from HomeworkModule.models import (
    AIAssignmentDraftRequest,
    AIGradeRequest,
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentQuestionGenerateRequest,
    AssignmentSubmitRequest,
    FinalGradeRequest,
)
from HomeworkModule.service import HomeworkService
from tools.session_manager import get_session_manager


router = APIRouter(prefix="/api/homework", tags=["homework"])
service = HomeworkService()
session_manager = get_session_manager()
sqlite_store = get_sqlite_store()


def _flatten_course_nodes(graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []

    def children_of(node: Dict[str, Any]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for key in ("children", "grandchildren", "great-grandchildren"):
            raw = node.get(key)
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        result.append(item)
        return result

    def walk(node: Dict[str, Any], path: List[str], depth: int) -> None:
        node_name = str(node.get("name", "")).strip()
        if not node_name:
            return
        node_id = str(node.get("node_id") or node.get("id") or node_name).strip()
        current_path = [*path, node_name]
        nodes.append(
            {
                "node_id": node_id,
                "node_name": node_name,
                "node_path": current_path,
                "depth": depth,
            }
        )
        for child in children_of(node):
            walk(child, current_path, depth + 1)

    for child in _flatten_course_children(graph_data):
        walk(child, [], 0)

    return nodes


def _flatten_course_children(graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = graph_data.get("children")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


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
    if not sqlite_store.get_user("teacher", session.get("username", "")):
        raise HTTPException(status_code=404, detail="教师账号不存在")
    return session


def _require_student(session_id: Optional[str]) -> Dict[str, Any]:
    session = _require_session(session_id)
    if session.get("user_type") != "student":
        raise HTTPException(status_code=403, detail="仅学生可访问")
    if not sqlite_store.get_user("student", session.get("username", "")):
        raise HTTPException(status_code=404, detail="学生账号不存在")
    return session


def _require_teacher_or_admin(session_id: Optional[str]) -> Dict[str, Any]:
    session = _require_session(session_id)
    user_type = session.get("user_type")
    username = session.get("username", "")
    if user_type == "teacher":
        if not sqlite_store.get_user("teacher", username):
            raise HTTPException(status_code=404, detail="教师账号不存在")
        return session
    if user_type == "admin":
        if not sqlite_store.get_user("admin", username):
            raise HTTPException(status_code=404, detail="管理员账号不存在")
        return session
    raise HTTPException(status_code=403, detail="仅教师或管理员可访问")


@router.post("/assignments")
def publish_assignment(data: AssignmentCreateRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    teacher_username = session.get("username", "")
    payload = {
        "title": data.title,
        "description": data.description,
        "assignment_type": data.assignment_type,
        "class_name": data.class_name,
        "due_at": data.due_at,
        "allow_late": data.allow_late,
        "total_score": data.total_score,
        "rubric": data.rubric,
        "course_id": data.course_id,
        "node_id": data.node_id,
        "node_name": data.node_name,
        "node_path": data.node_path,
        "chapter_context": data.chapter_context,
        "questions": [item.model_dump() for item in data.questions],
        "publish_now": data.publish_now,
        "created_by": teacher_username,
    }
    created = service.create_assignment(payload)
    return {"success": True, "assignment": created}


@router.get("/assignments")
def list_assignments(
    only_mine: bool = False,
    course_id: Optional[str] = None,
    node_id: Optional[str] = None,
    node_name: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_session(session_id)
    user_type = session.get("user_type")
    username = session.get("username")

    if user_type == "teacher":
        created_by = username if only_mine else None
        assignments = service.list_assignments(
            created_by=created_by,
            course_id=course_id,
            node_id=node_id,
            node_name=node_name,
        )
    elif user_type == "student":
        assignments = service.list_assignments(
            status="published",
            course_id=course_id,
            node_id=node_id,
            node_name=node_name,
        )
    else:
        assignments = service.list_assignments(
            course_id=course_id,
            node_id=node_id,
            node_name=node_name,
        )
    return {"success": True, "assignments": assignments}


@router.get("/assignments/{assignment_id}")
def get_assignment(assignment_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_session(session_id)
    assignment = service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")

    user_type = session.get("user_type")
    if user_type == "teacher" and assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权查看该作业")
    if user_type == "student" and assignment.get("status") != "published":
        raise HTTPException(status_code=403, detail="该作业暂未发布")
    return {"success": True, "assignment": assignment}


@router.put("/assignments/{assignment_id}")
def update_assignment(
    assignment_id: str,
    data: AssignmentUpdateRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher(session_id)
    assignment = service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权修改该作业")

    updated = service.update_assignment(
        assignment_id,
        {
            "title": data.title,
            "description": data.description,
            "assignment_type": data.assignment_type,
            "class_name": data.class_name,
            "due_at": data.due_at,
            "allow_late": data.allow_late,
            "total_score": data.total_score,
            "rubric": data.rubric,
            "course_id": data.course_id,
            "node_id": data.node_id,
            "node_name": data.node_name,
            "node_path": data.node_path,
            "chapter_context": data.chapter_context,
            "questions": [item.model_dump() for item in data.questions],
        },
    )
    if not updated:
        raise HTTPException(status_code=404, detail="作业不存在")
    return {"success": True, "assignment": updated}


@router.post("/assignments/{assignment_id}/publish")
def publish_assignment_status(assignment_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    assignment = service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权发布该作业")
    updated = service.publish_assignment(assignment_id)
    return {"success": True, "assignment": updated}


@router.post("/assignments/{assignment_id}/close")
def close_assignment_status(assignment_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    assignment = service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权关闭该作业")
    updated = service.close_assignment(assignment_id)
    return {"success": True, "assignment": updated}


@router.post("/assignments/{assignment_id}/reopen")
def reopen_assignment_status(assignment_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    assignment = service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权重开该作业")
    updated = service.reopen_assignment(assignment_id)
    return {"success": True, "assignment": updated}


@router.post("/assignments/{assignment_id}/submissions")
def submit_assignment(
    assignment_id: str,
    data: AssignmentSubmitRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_student(session_id)
    assignment = service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")

    try:
        submission = service.submit_assignment(
            {
                "assignment_id": assignment_id,
                "student_username": session.get("username", ""),
                "answers": data.answers,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"success": True, "submission": submission}


@router.get("/twin/student-results")
def get_student_results_for_twin(
    student_username: str,
    assignment_id: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher_or_admin(session_id)
    user_type = str(session.get("user_type") or "")
    teacher_owner = str(session.get("username") or "") if user_type == "teacher" else None

    data = service.get_student_twin_homework_snapshot(
        student_username=str(student_username or "").strip(),
        assignment_id=str(assignment_id or "").strip() or None,
        teacher_owner=teacher_owner,
    )
    return {"success": True, "data": data}


@router.get("/twin/my-results")
def get_my_results_for_twin(
    assignment_id: Optional[str] = None,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_student(session_id)
    student_username = str(session.get("username") or "").strip()
    data = service.get_student_twin_homework_snapshot(
        student_username=student_username,
        assignment_id=str(assignment_id or "").strip() or None,
        teacher_owner=None,
    )
    return {"success": True, "data": data}


@router.post("/ai/generate-draft")
def ai_generate_draft(data: AIAssignmentDraftRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    result = service.generate_assignment_draft(
        assignment_type=data.assignment_type,
        topic=data.topic,
        difficulty=data.difficulty,
        class_name=data.class_name,
        teacher_username=session.get("username", ""),
        course_id=data.course_id,
        node_id=data.node_id,
        node_name=data.node_name,
        node_path=data.node_path,
        chapter_context=data.chapter_context,
    )
    return {"success": True, **result}


@router.get("/course-nodes")
def list_course_nodes(course_id: str = "course_big_data", session_id: Optional[str] = Cookie(None)):
    _require_teacher(session_id)
    payload = sqlite_store.get_course_payload(course_id)
    if not isinstance(payload, dict):
        return {"success": True, "course_id": course_id, "nodes": []}
    nodes = _flatten_course_nodes(payload)
    return {"success": True, "course_id": course_id, "nodes": nodes}


@router.get("/assignments/{assignment_id}/submissions")
def list_assignment_submissions(assignment_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_teacher(session_id)
    assignment = service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权查看该作业提交")

    submissions = service.list_submissions(assignment_id=assignment_id)
    return {"success": True, "submissions": submissions}


@router.get("/submissions/{submission_id}")
def get_submission_detail(submission_id: str, session_id: Optional[str] = Cookie(None)):
    session = _require_session(session_id)
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")

    assignment = service.get_assignment(submission.get("assignment_id", ""))
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")

    user_type = session.get("user_type")
    username = session.get("username", "")
    if user_type == "teacher" and assignment.get("created_by") != username:
        raise HTTPException(status_code=403, detail="无权查看该提交")
    if user_type == "student" and submission.get("student_username") != username:
        raise HTTPException(status_code=403, detail="无权查看该提交")
    if user_type not in {"teacher", "student", "admin"}:
        raise HTTPException(status_code=403, detail="无权查看该提交")

    return {
        "success": True,
        "submission": submission,
        "assignment": assignment,
    }


@router.get("/my-submissions")
def list_my_submissions(assignment_id: Optional[str] = None, session_id: Optional[str] = Cookie(None)):
    session = _require_student(session_id)
    submissions = service.list_submissions(
        assignment_id=assignment_id,
        student_username=session.get("username", ""),
    )
    return {"success": True, "submissions": submissions}


@router.post("/submissions/{submission_id}/ai-grade")
def ai_grade_submission(
    submission_id: str,
    data: AIGradeRequest,
    session_id: Optional[str] = Cookie(None),
):
    del data
    session = _require_teacher(session_id)
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")

    assignment = service.get_assignment(submission.get("assignment_id", ""))
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权批改该提交")

    graded = service.grade_with_ai(
        assignment=assignment,
        submission=submission,
        teacher_username=session.get("username", ""),
    )
    return {"success": True, "submission": graded}


@router.post("/submissions/{submission_id}/final-grade")
def finalize_grade(
    submission_id: str,
    data: FinalGradeRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher(session_id)
    submission = service.get_submission(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="提交不存在")

    assignment = service.get_assignment(submission.get("assignment_id", ""))
    if not assignment:
        raise HTTPException(status_code=404, detail="作业不存在")
    if assignment.get("created_by") != session.get("username"):
        raise HTTPException(status_code=403, detail="无权终审该提交")

    updated = service.finalize_grade(
        submission_id=submission_id,
        teacher_score=data.teacher_score,
        teacher_comment=data.teacher_comment,
        grader_username=session.get("username", ""),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="提交不存在")
    return {"success": True, "submission": updated}


@router.post("/ai/generate-questions")
def ai_generate_questions(
    data: AssignmentQuestionGenerateRequest,
    session_id: Optional[str] = Cookie(None),
):
    session = _require_teacher(session_id)
    questions = service.generate_questions(data, teacher_username=session.get("username", ""))
    return {"success": True, "questions": questions}


@router.post("/export/sqlite")
def export_homework_to_sqlite(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher_or_admin(session_id)
    result = export_homework_json_to_sqlite()
    return {
        "success": True,
        "operator": session.get("username", ""),
        "result": result,
    }


@router.post("/assignments/seed-oj-smoke")
def seed_oj_smoke_assignment(session_id: Optional[str] = Cookie(None)):
    session = _require_teacher_or_admin(session_id)
    result = service.create_builtin_oj_smoke_assignment(created_by=session.get("username", "system"))
    return {
        "success": True,
        "created": result.get("created", False),
        "assignment": result.get("assignment"),
    }
