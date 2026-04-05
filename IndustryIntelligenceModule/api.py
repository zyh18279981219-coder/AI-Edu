"""FastAPI router for industry intelligence."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock, Thread
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel, Field

from IndustryIntelligenceModule.service import CITY_OPTIONS, COUNTRY_OPTIONS, SOURCE_OPTIONS, IndustryIntelligenceService
from IndustryIntelligenceModule.settings import settings
from tools.session_manager import get_session_manager


router = APIRouter(prefix="/api/industry-intelligence", tags=["industry-intelligence"])
session_manager = get_session_manager()
service = IndustryIntelligenceService()
_task_lock = Lock()
_tasks: Dict[str, Dict[str, Any]] = {}
_USER_TASK_ID_KEY = "industry_latest_task_id"
_USER_TASK_SNAPSHOT_KEY = "industry_latest_task_snapshot"


class TaskCancelledError(Exception):
    pass


class AnalyzeRequest(BaseModel):
    keyword: str
    country: str = "中国"
    city: str = "全国"
    include_global: bool = False
    job_limit: int = Field(default=20, ge=1, le=50)
    relevance_threshold: int = Field(default=5, ge=0, le=12)
    sources: List[str] = Field(default_factory=lambda: list(SOURCE_OPTIONS))
    fetch_desc: bool = False


class ReanalyzeRequest(BaseModel):
    jobs: List[Dict[str, Any]]


def _require_authenticated_user(session_id: Optional[str] = Cookie(None)):
    if not session_id:
        raise HTTPException(status_code=401, detail="请先登录后再使用行业情报功能。")
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录。")
    return session


def _public_task_snapshot(task: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = deepcopy(task)
    snapshot.pop("session_id", None)
    snapshot.pop("username", None)
    return snapshot


def _persist_task_snapshot(task: Dict[str, Any]):
    username = task.get("username")
    snapshot = _public_task_snapshot(task)
    if username:
        session_manager.set_user_value(username, _USER_TASK_ID_KEY, snapshot["task_id"])
        session_manager.set_user_value(username, _USER_TASK_SNAPSHOT_KEY, snapshot)


def _set_task_state(task_id: str, **updates):
    with _task_lock:
        task = _tasks.get(task_id)
        if not task:
            return
        task.update(updates)
        snapshot = deepcopy(task)
    _persist_task_snapshot(snapshot)


def _get_task_snapshot(task_id: str) -> Optional[Dict[str, Any]]:
    with _task_lock:
        task = _tasks.get(task_id)
        return _public_task_snapshot(task) if task else None


def _get_task_for_session(task_id: str, session_id: Optional[str]) -> Dict[str, Any]:
    session = _require_authenticated_user(session_id)
    with _task_lock:
        task = _tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在。")
        if task.get("session_id") != session_id and task.get("username") != session.get("username"):
            raise HTTPException(status_code=403, detail="无权访问该任务。")
        return task


def _create_task_record(task_type: str, session_id: str, username: str) -> str:
    task_id = uuid4().hex
    task = {
        "task_id": task_id,
        "task_type": task_type,
        "session_id": session_id,
        "username": username,
        "status": "queued",
        "message": "任务已创建，等待开始。",
        "meta": {"step": 0},
        "result": None,
        "error": None,
        "cancel_requested": False,
    }
    with _task_lock:
        _tasks[task_id] = task
    _persist_task_snapshot(task)
    return task_id


def _check_cancelled(task_id: str):
    with _task_lock:
        task = _tasks.get(task_id)
        if task and task.get("cancel_requested"):
            raise TaskCancelledError("任务已终止。")


def _status_callback(task_id: str, status: str, message: str, meta: Dict[str, Any]):
    _check_cancelled(task_id)
    _set_task_state(task_id, status=status, message=message, meta=meta)


def _run_analysis_task(task_id: str, payload: AnalyzeRequest):
    try:
        _check_cancelled(task_id)
        _set_task_state(task_id, status="running", message="正在校验参数与模型配置...", meta={"step": 0})
        result = service.run_full_analysis(
            keyword=payload.keyword.strip(),
            country=payload.country,
            city=payload.city,
            job_limit=payload.job_limit,
            relevance_threshold=payload.relevance_threshold,
            sources=payload.sources,
            fetch_desc=payload.fetch_desc,
            status_callback=lambda status, message, meta: _status_callback(task_id, status, message, meta),
            include_global=payload.include_global,
        )
        _check_cancelled(task_id)
        _set_task_state(task_id, status="completed", message="分析完成。", meta={"step": 5}, result=result, error=None)
    except TaskCancelledError:
        _set_task_state(task_id, status="cancelled", message="任务已终止。", error=None)
    except Exception as exc:
        _set_task_state(task_id, status="failed", message="分析失败。", error=str(exc))


def _run_reanalyze_task(task_id: str, jobs: List[Dict[str, Any]]):
    try:
        _check_cancelled(task_id)
        _set_task_state(task_id, status="analyzing", message="正在重新提取技能与结构化字段...", meta={"step": 3, "current": 0, "total": len(jobs)})
        analyzed = service.analyze_jobs(jobs, status_callback=lambda status, message, meta: _status_callback(task_id, status, message, meta))
        _check_cancelled(task_id)
        _set_task_state(task_id, status="rendering", message="正在整理结果...", meta={"step": 4})
        result = service.build_payload(analyzed)
        _check_cancelled(task_id)
        _set_task_state(task_id, status="completed", message="重新分析完成。", meta={"step": 5}, result=result, error=None)
    except TaskCancelledError:
        _set_task_state(task_id, status="cancelled", message="任务已终止。", error=None)
    except Exception as exc:
        _set_task_state(task_id, status="failed", message="重新分析失败。", error=str(exc))


@router.get("/status")
def get_status():
    ok, messages = settings.validate()
    city_map = {country: config.get("cities", []) for country, config in COUNTRY_OPTIONS.items()}
    return {
        "ok": ok,
        "messages": messages,
        "countries": list(COUNTRY_OPTIONS.keys()),
        "cities": CITY_OPTIONS,
        "city_map": city_map,
        "sources": SOURCE_OPTIONS,
    }


@router.get("/tasks/{task_id}")
def get_task(task_id: str, session_id: Optional[str] = Cookie(None)):
    task = _get_task_for_session(task_id, session_id)
    return _public_task_snapshot(task)


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, session_id: Optional[str] = Cookie(None)):
    task = _get_task_for_session(task_id, session_id)
    if task.get("status") in {"completed", "failed", "cancelled"}:
        return {"success": True, "task": _public_task_snapshot(task)}
    _set_task_state(task_id, cancel_requested=True, status="cancelled", message="正在终止任务...", error=None)
    return {"success": True, "task": _get_task_snapshot(task_id)}


@router.get("/current")
def get_current_task(session_id: Optional[str] = Cookie(None)):
    session = _require_authenticated_user(session_id)
    username = session.get("username")
    user_task_id = session_manager.get_user_value(username, _USER_TASK_ID_KEY) if username else None
    if user_task_id:
        task = _get_task_snapshot(user_task_id)
        if task:
            return {"task": task}
    user_snapshot = session_manager.get_user_value(username, _USER_TASK_SNAPSHOT_KEY) if username else None
    return {"task": user_snapshot or None}


@router.post("/analyze")
def analyze(data: AnalyzeRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_authenticated_user(session_id)
    if not data.keyword.strip():
        raise HTTPException(status_code=400, detail="请输入搜索关键词。")
    if not data.include_global:
        if data.country not in COUNTRY_OPTIONS:
            raise HTTPException(status_code=400, detail=f"当前不支持国家/地区: {data.country}")
        if data.city not in COUNTRY_OPTIONS[data.country].get("cities", []):
            raise HTTPException(status_code=400, detail=f"{data.country} 下不支持城市: {data.city}")
    invalid_sources = [source for source in data.sources if source not in SOURCE_OPTIONS]
    if invalid_sources:
        raise HTTPException(status_code=400, detail=f"存在不支持的数据源: {', '.join(invalid_sources)}")
    ok, messages = settings.validate()
    if not ok:
        raise HTTPException(status_code=400, detail="；".join(messages))

    task_id = _create_task_record("analyze", session_id, session.get("username", ""))
    Thread(target=_run_analysis_task, args=(task_id, data), daemon=True).start()
    return {"success": True, "task_id": task_id}


@router.post("/reanalyze")
def reanalyze(data: ReanalyzeRequest, session_id: Optional[str] = Cookie(None)):
    session = _require_authenticated_user(session_id)
    ok, messages = settings.validate()
    if not ok:
        raise HTTPException(status_code=400, detail="；".join(messages))
    if not data.jobs:
        raise HTTPException(status_code=400, detail="当前没有可重新分析的职位数据。")

    task_id = _create_task_record("reanalyze", session_id, session.get("username", ""))
    Thread(target=_run_reanalyze_task, args=(task_id, data.jobs), daemon=True).start()
    return {"success": True, "task_id": task_id}
