from __future__ import annotations

import json
import os
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException
from langchain_openai import ChatOpenAI

from DatabaseModule.sqlite_store import get_sqlite_store
from DigitalTwinModule.models import TwinProfile
from DigitalTwinModule.teacher_twin_service import TeacherTwinService
from DigitalTwinModule.trend_tracker import TrendTracker
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from PathPlannerModule.weak_node_detector import WeakNodeDetector
from tools.llm_logger import get_llm_logger
from tools.session_manager import get_session_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

session_manager = get_session_manager()
_store = TwinProfileStore()
_tracker = TrendTracker()
_detector = WeakNodeDetector()
_sqlite_store = get_sqlite_store()
_teacher_twin_service = TeacherTwinService()

_model_name = os.environ.get("model_name")
_base_url = os.environ.get("base_url")
_api_key = os.environ.get("api_key")

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
    teacher_username = str(session.get("user_id") or "")
    try:
        return _teacher_twin_service.build_summary(teacher_username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Teacher twin summary failed: {exc}")


def _extract_json_object(raw_text: str) -> dict:
    text = raw_text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        left = text.find("{")
        right = text.rfind("}")
        if left >= 0 and right > left:
            try:
                return json.loads(text[left:right + 1])
            except json.JSONDecodeError:
                return {}
    return {}


@router.post("/teacher-twin/ai-suggestions")
def generate_teacher_twin_ai_suggestions(session=Depends(_require_teacher)):
    teacher_username = str(session.get("user_id") or "")
    summary = _teacher_twin_service.build_summary(teacher_username)
    teacher_log_username = str(summary.get("teacher_username") or teacher_username)

    if not (_model_name and _api_key):
        return {
            "mode": "manual-ai-button",
            "is_ai_generated": False,
            "teaching_strategy_suggestions": [],
            "intervention_suggestions": [],
            "message": "AI 服务未配置，请联系管理员配置模型参数。",
        }

    llm = ChatOpenAI(
        model=_model_name,
        temperature=0.2,
        base_url=_base_url,
        api_key=_api_key,
    )

    compact_summary = {
        "teacher_username": summary.get("teacher_username"),
        "overall_score": summary.get("overall_score"),
        "dimensions": summary.get("dimensions", []),
        "student_scope": summary.get("student_scope", {}),
        "data_diagnosis": summary.get("data_diagnosis", {}),
    }

    prompt = (
        "你是教师发展顾问。请基于以下教师六维画像生成建议，输出严格 JSON。\n"
        "要求：\n"
        "1) 给出 2-4 条教学策略建议，格式: [{\"dimension\":\"维度名\",\"advice\":\"建议\"}]\n"
        "2) 给出 2-4 条干预策略建议，格式: [{\"trigger\":\"触发条件\",\"action\":\"动作\"}]\n"
        "3) 建议要具体、可执行、面向教师实际操作。\n"
        "4) 输出格式必须是: {\"teaching_strategy_suggestions\": [...], \"intervention_suggestions\": [...]}\n"
        f"教师画像数据: {json.dumps(compact_summary, ensure_ascii=False)}"
    )

    try:
        response = llm.invoke(prompt)
        payload = _extract_json_object(getattr(response, "content", ""))

        teaching = payload.get("teaching_strategy_suggestions") if isinstance(payload, dict) else None
        intervention = payload.get("intervention_suggestions") if isinstance(payload, dict) else None
        if not isinstance(teaching, list):
            teaching = []
        if not isinstance(intervention, list):
            intervention = []

        get_llm_logger().log_llm_call(
            messages=[{"role": "user", "content": prompt}],
            response=response,
            model=_model_name,
            module="DashboardModule.dashboard_api",
            metadata={"function": "generate_teacher_twin_ai_suggestions"},
            username=teacher_log_username,
        )

        return {
            "mode": "manual-ai-button",
            "is_ai_generated": True,
            "teaching_strategy_suggestions": teaching,
            "intervention_suggestions": intervention,
            "message": "AI 建议生成完成。",
        }
    except Exception as exc:
        return {
            "mode": "manual-ai-button",
            "is_ai_generated": False,
            "teaching_strategy_suggestions": [],
            "intervention_suggestions": [],
            "message": f"AI 生成失败：{exc}",
        }
