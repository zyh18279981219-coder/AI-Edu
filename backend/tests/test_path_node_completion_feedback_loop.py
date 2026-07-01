from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from pydantic import ValidationError

from DigitalTwinModule import digital_twin_api
from fiveE import effectiveness_service


class _StatusStore:
    def __init__(self) -> None:
        self.calls = []

    def update_learning_path_node_status(
        self,
        username,
        node_id,
        *,
        path_id=None,
        plan_id=None,
        status,
        mastery_after=None,
        payload=None,
    ):
        self.calls.append(
            {
                "username": username,
                "node_id": node_id,
                "path_id": path_id or plan_id,
                "status": status,
                "mastery_after": mastery_after,
                "payload": payload,
            }
        )
        return {
            "status_id": 11,
            "path_id": path_id or plan_id or 7,
            "username": username,
            "course_id": "course_big_data",
            "node_id": node_id,
            "item_type": "course_knowledge_point",
            "source_type": "published_course_graph",
            "status": status,
            "mastery_after": mastery_after,
        }


class _Planner:
    calls = []

    def plan(self, username, *, course_id=None, trigger_type="diagnosis", manual_goal=None):
        self.calls.append(
            {
                "username": username,
                "course_id": course_id,
                "trigger_type": trigger_type,
                "manual_goal": manual_goal,
            }
        )
        return {
            "username": username,
            "course_id": course_id,
            "version_no": 3,
            "trigger_type": trigger_type,
            "formal_path_nodes": [],
            "supplemental_items": [],
        }


def test_completed_path_node_refreshes_path_by_default(monkeypatch):
    store = _StatusStore()
    _Planner.calls = []
    monkeypatch.setattr(digital_twin_api, "get_database_store", lambda: store)
    monkeypatch.setattr(digital_twin_api, "PathPlannerAgent", _Planner)
    monkeypatch.setattr(digital_twin_api, "_require_student_self_session", lambda username, session_id: {"username": username})
    monkeypatch.setattr(
        effectiveness_service,
        "link_path_continuation",
        lambda **kwargs: {
            "updated": True,
            "record_id": 5,
            "evidence_status": "outcome_supported",
            "mastery_update_policy": "not_updated_by_5e_effectiveness",
        },
    )

    result = asyncio.run(
        digital_twin_api.update_path_node_status(
            "zyh",
            "Kafka 数据接入",
            digital_twin_api.PathNodeStatusUpdateRequest(
                status="completed",
                path_id=7,
                mastery_after=78,
                payload={"source": "test"},
            ),
        )
    )

    assert result["success"] is True
    assert result["node_status"]["status"] == "completed"
    assert result["path_refresh"]["triggered"] is True
    assert result["path_refresh"]["trigger_type"] == "node_completed"
    assert result["path_refresh"]["path"]["version_no"] == 3
    assert result["fivee_outcome"]["updated"] is True
    assert result["fivee_outcome"]["mastery_update_policy"] == "not_updated_by_5e_effectiveness"
    assert _Planner.calls == [
        {
            "username": "zyh",
            "course_id": "course_big_data",
            "trigger_type": "node_completed",
            "manual_goal": "Completed path node: Kafka 数据接入",
        }
    ]


def test_path_node_status_can_skip_refresh(monkeypatch):
    store = _StatusStore()
    _Planner.calls = []
    monkeypatch.setattr(digital_twin_api, "get_database_store", lambda: store)
    monkeypatch.setattr(digital_twin_api, "PathPlannerAgent", _Planner)
    monkeypatch.setattr(digital_twin_api, "_require_student_self_session", lambda username, session_id: {"username": username})
    monkeypatch.setattr(
        effectiveness_service,
        "link_path_continuation",
        lambda **kwargs: {
            "updated": True,
            "record_id": 5,
            "evidence_status": "outcome_supported",
            "mastery_update_policy": "not_updated_by_5e_effectiveness",
        },
    )

    result = asyncio.run(
        digital_twin_api.update_path_node_status(
            "zyh",
            "Kafka 数据接入",
            digital_twin_api.PathNodeStatusUpdateRequest(
                status="completed",
                path_id=7,
                mastery_after=80,
                refresh_path=False,
            ),
        )
    )

    assert result["success"] is True
    assert result["node_status"]["status"] == "completed"
    assert result["path_refresh"]["triggered"] is False
    assert result["path_refresh"]["path"] is None
    assert result["fivee_outcome"]["updated"] is True
    assert _Planner.calls == []


def test_path_node_status_rejects_unknown_status():
    with pytest.raises(ValidationError):
        digital_twin_api.PathNodeStatusUpdateRequest(status="done")
