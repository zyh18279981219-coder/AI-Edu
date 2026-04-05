from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from DigitalTwinModule.data_collector import DataCollector
from DigitalTwinModule.student_twin_service import StudentTwinService
from DigitalTwinModule.trend_tracker import TrendTracker
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from PathPlannerModule.path_planner_agent import PathPlannerAgent

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])
logger = logging.getLogger(__name__)


class QuizScoreRequest(BaseModel):
    username: str
    node_id: str
    score: float


class NodeScoreUpdateRequest(BaseModel):
    new_score: float


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
