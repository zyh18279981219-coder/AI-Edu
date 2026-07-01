from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PathPlannerModule.path_planner_agent import PathPlannerAgent


class _LifecycleStore:
    def __init__(self, lifecycle_status: str = "published") -> None:
        self.archived_calls = []
        self.saved = []
        self.lifecycle_status = lifecycle_status
        self.active_payload = {
            "path_id": 22,
            "filename": "zyh_path_active.json",
            "data": {
                "username": "zyh",
                "course_id": "course_big_data",
                "path_id": 22,
                "version_no": 2,
                "lifecycle_status": "active",
                "formal_path_nodes": [],
            },
        }
        self.latest_payload = {
            "path_id": 21,
            "filename": "zyh_path_latest.json",
            "status": "archived",
            "updated_at": "2026-06-28T10:00:00",
            "data": {
                "username": "zyh",
                "course_id": "course_big_data",
                "path_id": 21,
                "version_no": 1,
                "lifecycle_status": "archived",
                "formal_path_nodes": [],
            },
        }

    def get_course_summary(self, course_id):
        if course_id == "draft_course":
            return {
                "course_id": course_id,
                "lifecycle_status": "draft",
            }
        return {
            "course_id": course_id,
            "lifecycle_status": self.lifecycle_status,
        }

    def archive_active_learning_paths(self, *, username, course_id=None):
        self.archived_calls.append({"username": username, "course_id": course_id})
        return 1

    def save_learning_path_version(self, **kwargs):
        self.saved.append(kwargs)
        kwargs["payload"]["path_id"] = 23
        kwargs["payload"]["version_no"] = 3
        return {"path_id": 23, "version_no": 3}

    def save_learning_plan(self, **kwargs):
        self.saved.append(kwargs)

    def get_active_learning_path(self, *, username, course_id=None, filename_prefix=None):
        assert username == "zyh"
        return self.active_payload

    def get_latest_learning_plan(self, **_kwargs):
        return self.latest_payload

    def list_learning_path_versions(self, *, username, course_id=None, limit=10):
        assert username == "zyh"
        rows = [self.active_payload, self.latest_payload]
        if course_id:
            rows = [
                item for item in rows
                if str(item.get("data", {}).get("course_id") or "") == str(course_id)
            ]
        return rows[:limit]

    def list_learning_path_node_status(self, username, path_id=None, plan_id=None):
        return [
            {
                "status_id": 1,
                "path_id": path_id or plan_id,
                "username": username,
                "node_id": "Kafka 数据接入",
                "item_type": "course_knowledge_point",
                "source_type": "published_course_graph",
                "status": "pending",
            }
        ]

    def list_learning_plans(self, username=None, categories=None):
        assert username == "zyh"
        assert categories == ["path"]
        return [
            self.active_payload,
            self.latest_payload,
            {
                "path_id": 20,
                "filename": "zyh_path_draft_course.json",
                "status": "archived",
                "updated_at": "2026-06-27T10:00:00",
                "data": {
                    "username": "zyh",
                    "course_id": "draft_course",
                    "path_id": 20,
                    "version_no": 9,
                    "lifecycle_status": "archived",
                    "formal_path_nodes": [],
                },
            },
        ]


def test_save_path_archives_previous_active_versions():
    agent = PathPlannerAgent.__new__(PathPlannerAgent)
    store = _LifecycleStore()
    agent.database_store = store

    payload = {
        "username": "zyh",
        "course_id": "course_big_data",
        "version_no": 3,
        "formal_path_nodes": [],
    }
    agent._save_path_result("zyh", payload)

    assert store.archived_calls == []
    assert store.saved[0]["payload"]["lifecycle_status"] == "active"
    assert store.saved[0]["payload"]["path_id"] == 23


def test_get_latest_path_prefers_active_path_lookup():
    agent = PathPlannerAgent.__new__(PathPlannerAgent)
    store = _LifecycleStore()
    agent.database_store = store

    result = agent.get_latest_path("zyh")

    assert result is not None
    assert result["version_no"] == 2
    assert result["lifecycle_status"] == "active"
    assert result["path_node_status"][0]["node_id"] == "Kafka 数据接入"


def test_get_latest_path_skips_active_path_for_unpublished_course():
    agent = PathPlannerAgent.__new__(PathPlannerAgent)
    store = _LifecycleStore(lifecycle_status="draft")
    agent.database_store = store

    result = agent.get_latest_path("zyh")

    assert result is None


def test_list_path_versions_returns_visible_history_with_status():
    agent = PathPlannerAgent.__new__(PathPlannerAgent)
    store = _LifecycleStore()
    agent.database_store = store

    result = agent.list_path_versions("zyh")

    assert [item["version_no"] for item in result] == [2, 1]
    assert result[0]["path_id"] == 22
    assert result[0]["lifecycle_status"] == "active"
    assert result[0]["path_node_status"][0]["path_id"] == 22
    assert result[1]["lifecycle_status"] == "archived"


def test_list_path_versions_hides_versions_for_unpublished_course():
    agent = PathPlannerAgent.__new__(PathPlannerAgent)
    store = _LifecycleStore(lifecycle_status="draft")
    agent.database_store = store

    result = agent.list_path_versions("zyh")

    assert result == []
