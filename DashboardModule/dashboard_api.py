from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException

from DatabaseModule.sqlite_store import get_sqlite_store
from DigitalTwinModule.models import TwinProfile
from DigitalTwinModule.teacher_twin_service import TeacherTwinService
from DigitalTwinModule.trend_tracker import TrendTracker
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from PathPlannerModule.weak_node_detector import WeakNodeDetector
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

session_manager = get_session_manager()
_store = TwinProfileStore()
_tracker = TrendTracker()
_detector = WeakNodeDetector()
_sqlite_store = get_sqlite_store()
_teacher_twin_service = TeacherTwinService()

def _require_teacher(session_id: Optional[str] = Cookie(None)):
    if not session_id:
        raise HTTPException(status_code=403, detail="Teacher authentication required")
    session = session_manager.get_session(session_id)
    if not session or session.get("user_type") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher authentication required")
    return session


def _load_all_profiles() -> list[TwinProfile]:
    profiles: list[TwinProfile] = []
    try:
        raw_profiles = _sqlite_store.list_twin_profiles()
        for raw in raw_profiles:
            try:
                profiles.append(TwinProfile.model_validate(raw))
            except Exception:
                pass
    except Exception:
        pass
    return profiles


@router.get("/class-overview")
def get_class_overview(session=Depends(_require_teacher)):
    profiles = _load_all_profiles()

    if not profiles:
        return {
            "class_avg_mastery": 0.0,
            "student_count": 0,
            "distribution": {"excellent": 0, "good": 0, "needs_improvement": 0},
            "students": [],
            "node_avg_mastery": [],
        }

    masteries = [p.overall_mastery for p in profiles]
    class_avg = round(sum(masteries) / len(masteries), 2)

    distribution = {"excellent": 0, "good": 0, "needs_improvement": 0}
    for mastery in masteries:
        if mastery >= 80:
            distribution["excellent"] += 1
        elif mastery >= 60:
            distribution["good"] += 1
        else:
            distribution["needs_improvement"] += 1

    students = [
        {"username": profile.username, "overall_mastery": profile.overall_mastery}
        for profile in profiles
    ]

    node_scores: dict[str, list[float]] = {}
    for profile in profiles:
        for node in profile.knowledge_nodes:
            node_scores.setdefault(node.node_id, []).append(node.mastery_score)

    node_avg_mastery = [
        {"node_id": node_id, "avg_mastery": round(sum(scores) / len(scores), 2)}
        for node_id, scores in node_scores.items()
    ]

    return {
        "class_avg_mastery": class_avg,
        "student_count": len(profiles),
        "distribution": distribution,
        "students": students,
        "node_avg_mastery": node_avg_mastery,
    }


@router.get("/student/{username}")
def get_student_detail(username: str, session=Depends(_require_teacher)):
    if not _store.exists(username):
        raise HTTPException(status_code=404, detail=f"TwinProfile for user '{username}' not found")
    profile = _store.load(username)
    weak_nodes = _detector.detect(profile)
    for idx, node in enumerate(weak_nodes, start=1):
        node.priority = idx
    result = profile.model_dump()
    result["weak_nodes"] = [w.model_dump() for w in weak_nodes]
    return result


@router.get("/student/{username}/trend")
def get_student_trend(username: str, session=Depends(_require_teacher)):
    if not _store.exists(username):
        raise HTTPException(status_code=404, detail=f"TwinProfile for user '{username}' not found")
    trend = _tracker.get_trend(username, 30)
    return {"username": username, "trend": [t.model_dump() for t in trend]}


@router.get("/node/{node_id}/ranking")
def get_node_ranking(node_id: str, session=Depends(_require_teacher)):
    profiles = _load_all_profiles()

    ranking_data: list[dict] = []
    for profile in profiles:
        for node in profile.knowledge_nodes:
            if node.node_id == node_id:
                ranking_data.append(
                    {
                        "username": profile.username,
                        "mastery_score": node.mastery_score,
                    }
                )
                break

    ranking_data.sort(key=lambda x: x["mastery_score"], reverse=True)
    ranking = [
        {"rank": idx + 1, "username": item["username"], "mastery_score": item["mastery_score"]}
        for idx, item in enumerate(ranking_data)
    ]
    return {"node_id": node_id, "ranking": ranking}


@router.get("/teacher-twin")
def get_teacher_twin(session=Depends(_require_teacher)):
    teacher_username = session.get("username", "")
    try:
        return _teacher_twin_service.build_summary(teacher_username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Teacher twin summary failed: {exc}")
