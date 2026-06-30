import os
import sys

import pytest
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DigitalTwinModule import digital_twin_api


class _FakeSessionManager:
    def __init__(self, sessions):
        self.sessions = sessions

    def get_session(self, session_id):
        return self.sessions.get(session_id)


class _FakePathPlanner:
    def plan(self, username, *, course_id=None, trigger_type="diagnosis", manual_goal=None):
        return {
            "username": username,
            "course_id": course_id,
            "trigger_type": trigger_type,
            "manual_goal": manual_goal,
        }

    def get_latest_path(self, username):
        return {"username": username, "course_id": "course_big_data"}


class _FakeStore:
    def list_teacher_students(self, teacher_username):
        if teacher_username == "teacher":
            return [{"student_username": "zyh"}]
        return []


@pytest.fixture(autouse=True)
def patch_path_auth_dependencies(monkeypatch):
    monkeypatch.setattr(
        digital_twin_api,
        "_session_manager",
        _FakeSessionManager(
            {
                "student_zyh": {"username": "zyh", "user_type": "student"},
                "student_other": {"username": "other", "user_type": "student"},
                "teacher": {"username": "teacher", "user_type": "teacher"},
            }
        ),
    )
    monkeypatch.setattr(digital_twin_api, "PathPlannerAgent", _FakePathPlanner)
    monkeypatch.setattr(digital_twin_api, "get_database_store", lambda: _FakeStore())


@pytest.mark.anyio
async def test_student_can_generate_own_learning_path():
    result = await digital_twin_api.generate_path("zyh", session_id="student_zyh")

    assert result["username"] == "zyh"


@pytest.mark.anyio
async def test_generate_path_requires_student_self_session():
    with pytest.raises(HTTPException) as missing:
        await digital_twin_api.generate_path("zyh", session_id=None)
    assert missing.value.status_code == 403

    with pytest.raises(HTTPException) as cross_student:
        await digital_twin_api.generate_path("zyh", session_id="student_other")
    assert cross_student.value.status_code == 403

    with pytest.raises(HTTPException) as teacher:
        await digital_twin_api.generate_path("zyh", session_id="teacher")
    assert teacher.value.status_code == 403


@pytest.mark.anyio
async def test_teacher_can_read_authorized_path_but_not_generate():
    result = await digital_twin_api.get_current_path("zyh", session_id="teacher")

    assert result["username"] == "zyh"

    with pytest.raises(HTTPException) as outside_scope:
        await digital_twin_api.get_current_path("other", session_id="teacher")
    assert outside_scope.value.status_code == 403
