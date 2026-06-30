import os
import sys

import pytest
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DashboardModule import dashboard_api


class FakeDashboardStore:
    def list_teacher_students(self, teacher_identifier):
        if teacher_identifier == "teacher":
            return [{"student_username": "stu_a"}]
        return []

    def list_twin_profiles(self):
        return [
            {
                "username": "stu_a",
                "last_updated": "2026-06-28T10:00:00",
                "overall_mastery": 80,
                "knowledge_nodes": [
                    {
                        "node_id": "node_1",
                        "progress": 100,
                        "study_duration_minutes": 30,
                        "llm_interaction_count": 1,
                        "mastery_score": 85,
                    }
                ],
            },
            {
                "username": "stu_b",
                "last_updated": "2026-06-28T10:00:00",
                "overall_mastery": 20,
                "knowledge_nodes": [
                    {
                        "node_id": "node_1",
                        "progress": 20,
                        "study_duration_minutes": 5,
                        "llm_interaction_count": 0,
                        "mastery_score": 10,
                    }
                ],
            },
        ]


class EmptyProfileStore:
    def exists(self, username):
        return True


@pytest.fixture(autouse=True)
def patch_dashboard_dependencies(monkeypatch):
    monkeypatch.setattr(dashboard_api, "_database_store", FakeDashboardStore())
    monkeypatch.setattr(dashboard_api, "_store", EmptyProfileStore())
    yield


def test_class_overview_only_uses_authorized_students():
    result = dashboard_api.get_class_overview({"username": "teacher", "user_type": "teacher"})

    assert result["student_count"] == 1
    assert result["class_avg_mastery"] == 80
    assert [item["username"] for item in result["students"]] == ["stu_a"]


def test_node_ranking_only_uses_authorized_students():
    result = dashboard_api.get_node_ranking("node_1", {"username": "teacher", "user_type": "teacher"})

    assert result["ranking"] == [{"rank": 1, "username": "stu_a", "mastery_score": 85.0}]


def test_student_detail_rejects_unauthorized_student():
    with pytest.raises(HTTPException) as exc_info:
        dashboard_api.get_student_detail("stu_b", {"username": "teacher", "user_type": "teacher"})

    assert exc_info.value.status_code == 403


def test_student_trend_rejects_unauthorized_student():
    with pytest.raises(HTTPException) as exc_info:
        dashboard_api.get_student_trend("stu_b", {"username": "teacher", "user_type": "teacher"})

    assert exc_info.value.status_code == 403
