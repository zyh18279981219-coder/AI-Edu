from __future__ import annotations

from typing import Any, Dict, List

from DigitalTwinModule.student_twin_service import StudentTwinService
from DigitalTwinModule.trend_tracker import TrendTracker
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from DatabaseModule.sqlite_store import get_sqlite_store


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


def get_student_course_profile(student_id: str, course_id: str) -> Dict[str, Any]:
    """
    Build one student's profile for one course.
    Returns a JSON-serializable dict.
    Raises:
    - ValueError: bad input
    - LookupError: missing user/profile
    """
    student_identifier = str(student_id or "").strip()
    normalized_course_id = str(course_id or "").strip()
    if not student_identifier:
        raise ValueError("student_id is required")
    if not normalized_course_id:
        raise ValueError("course_id is required")

    store = get_sqlite_store()
    user = store.get_user_by_identifier("student", student_identifier)
    if not user:
        raise LookupError(f"Student '{student_identifier}' not found")

    username = str(user.get("username") or "")
    if not username:
        raise LookupError(f"Student '{student_identifier}' not found")

    profile_store = TwinProfileStore()
    if not profile_store.exists(username):
        raise LookupError(f"Twin profile for student '{student_identifier}' not found")

    profile = profile_store.load(username)
    trend = TrendTracker().get_trend(username, days=30)
    summary = StudentTwinService().build_summary(profile, trend)
    summary["student_id"] = student_identifier
    summary["course_id"] = normalized_course_id

    matched_raw: List[dict] = [
        node.model_dump() if hasattr(node, "model_dump") else node
        for node in (profile.knowledge_nodes or [])
    ]
    matched_raw = [
        node
        for node in matched_raw
        if isinstance(node, dict) and _match_course_node(normalized_course_id, node)
    ]
    matched_nodes = [_build_node_item(node) for node in matched_raw]
    weak_nodes = [
        node for node in matched_nodes if float(node.get("mastery_score") or 0) < 60
    ]

    progress_values = [float(node.get("progress", 0) or 0) for node in matched_nodes]
    quiz_values = [float(node.get("quiz_score", 0) or 0) for node in matched_nodes]
    summary["weak_nodes"] = weak_nodes
    summary["course_node_count"] = len(matched_nodes)
    summary["matched_nodes"] = matched_nodes
    summary["node_summary"] = {
        "total_nodes": len(matched_nodes),
        "weak_node_count": len(weak_nodes),
        "strong_node_count": sum(
            1 for node in matched_nodes if float(node.get("mastery_score") or 0) >= 80
        ),
        "average_progress": round(sum(progress_values) / len(progress_values), 2)
        if progress_values
        else 0.0,
        "average_quiz_score": round(sum(quiz_values) / len(quiz_values), 2)
        if quiz_values
        else 0.0,
    }
    summary["outputs"]["for_course_twin"]["weak_nodes"] = [
        item["node_id"] for item in weak_nodes[:5]
    ]
    summary["outputs"]["for_teacher_twin"]["weak_nodes"] = weak_nodes[:5]
    return summary
