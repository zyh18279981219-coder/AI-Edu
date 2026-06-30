from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app as backend_app


class FakeStudentApiStore:
    def __init__(self):
        self.teacher_lookup_calls: list[str] = []

    def list_users(self, user_type):
        if user_type == "student":
            return [
                {"username": "stu_a", "user_type": "student", "display_name": "A"},
                {"username": "stu_b", "user_type": "student", "display_name": "B"},
            ]
        if user_type == "teacher":
            return [
                {"username": "teacher", "user_type": "teacher"},
                {"username": "other_teacher", "user_type": "teacher"},
            ]
        return []

    def list_teacher_students(self, teacher_identifier):
        self.teacher_lookup_calls.append(str(teacher_identifier))
        if teacher_identifier == "teacher":
            return [{"student_username": "stu_a"}]
        if teacher_identifier == "other_teacher":
            return [{"student_username": "stu_b"}]
        return []

    def list_twin_profiles(self):
        return [
            {
                "username": "stu_a",
                "knowledge_nodes": [{"node_id": "node_1", "mastery_score": 80}],
            },
            {
                "username": "stu_b",
                "knowledge_nodes": [{"node_id": "node_1", "mastery_score": 10}],
            },
        ]


class EmptyCourseUserManager:
    def get_user_course_path(self, username):
        return f"missing-{username}.json"


def test_teacher_students_api_filters_by_teacher_username_before_user_id(monkeypatch):
    fake_store = FakeStudentApiStore()
    monkeypatch.setattr(backend_app, "database_store", fake_store)
    monkeypatch.setattr(backend_app, "user_manager", EmptyCourseUserManager())
    monkeypatch.setattr(
        backend_app,
        "get_current_user",
        lambda session_id=None: {"username": "teacher", "user_id": 999, "user_type": "teacher"},
    )

    result = asyncio.run(backend_app.get_students(session_id="session-teacher"))

    assert [item["username"] for item in result] == ["stu_a"]
    assert "teacher" in fake_store.teacher_lookup_calls
    assert "999" not in fake_store.teacher_lookup_calls


def test_teacher_students_api_returns_empty_when_teacher_has_no_scope(monkeypatch):
    fake_store = FakeStudentApiStore()
    monkeypatch.setattr(backend_app, "database_store", fake_store)
    monkeypatch.setattr(backend_app, "user_manager", EmptyCourseUserManager())
    monkeypatch.setattr(
        backend_app,
        "get_current_user",
        lambda session_id=None: {"username": "no_scope_teacher", "user_id": 998, "user_type": "teacher"},
    )

    result = asyncio.run(backend_app.get_students(session_id="session-teacher"))

    assert result == []


def test_teacher_heatmap_filters_by_teacher_scope(monkeypatch):
    fake_store = FakeStudentApiStore()
    monkeypatch.setattr(backend_app, "database_store", fake_store)
    monkeypatch.setattr(
        backend_app,
        "get_current_user",
        lambda session_id=None: {"username": "teacher", "user_id": 999, "user_type": "teacher"},
    )

    result = asyncio.run(backend_app.get_heatmap(session_id="session-teacher"))

    assert result["nodes"] == [{"node_id": "node_1", "avg_mastery": 80.0, "student_count": 1}]
