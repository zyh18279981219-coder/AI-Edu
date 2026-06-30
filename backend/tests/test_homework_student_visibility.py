import os
import sys

import pytest
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from HomeworkModule import api as homework_api


def _student_session(class_name: str = "Class-1"):
    return {
        "username": "zyh",
        "user_type": "student",
        "user_data": {"username": "zyh", "class_name": class_name},
    }


def test_student_assignment_list_is_filtered_by_class(monkeypatch):
    monkeypatch.setattr(homework_api.session_manager, "get_session", lambda session_id: _student_session())
    monkeypatch.setattr(
        homework_api.database_store,
        "get_user",
        lambda user_type, username: {"username": username, "class_name": "Class-1"},
    )
    monkeypatch.setattr(
        homework_api.service,
        "list_assignments",
        lambda **kwargs: [
            {"id": "same-class", "title": "同班作业", "status": "published", "class_name": "Class-1"},
            {"id": "other-class", "title": "其他班作业", "status": "published", "class_name": "Class-2"},
            {"id": "all-class", "title": "全体作业", "status": "published", "class_name": "全体"},
            {"id": "draft", "title": "草稿作业", "status": "draft", "class_name": "Class-1"},
        ],
    )

    result = homework_api.list_assignments(session_id="student-session")

    assert [item["id"] for item in result["assignments"]] == ["same-class", "all-class"]


def test_student_cannot_open_assignment_from_other_class(monkeypatch):
    monkeypatch.setattr(homework_api.session_manager, "get_session", lambda session_id: _student_session())
    monkeypatch.setattr(
        homework_api.database_store,
        "get_user",
        lambda user_type, username: {"username": username, "class_name": "Class-1"},
    )
    monkeypatch.setattr(
        homework_api.service,
        "get_assignment",
        lambda assignment_id: {
            "id": assignment_id,
            "title": "其他班作业",
            "status": "published",
            "class_name": "Class-2",
        },
    )

    with pytest.raises(HTTPException) as exc:
        homework_api.get_assignment("other-class", session_id="student-session")

    assert exc.value.status_code == 403
    assert "可见范围" in exc.value.detail


def test_student_can_submit_visible_assignment(monkeypatch):
    monkeypatch.setattr(homework_api.session_manager, "get_session", lambda session_id: _student_session())
    monkeypatch.setattr(
        homework_api.database_store,
        "get_user",
        lambda user_type, username: {"username": username, "class_name": "Class-1"},
    )
    monkeypatch.setattr(
        homework_api.service,
        "get_assignment",
        lambda assignment_id: {
            "id": assignment_id,
            "title": "同班作业",
            "status": "published",
            "class_name": "Class-1",
        },
    )
    monkeypatch.setattr(
        homework_api.service,
        "submit_assignment",
        lambda payload: {"id": "submission-1", **payload},
    )

    result = homework_api.submit_assignment(
        "same-class",
        homework_api.AssignmentSubmitRequest(answers=[{"question_index": 0, "answer": "答案"}]),
        session_id="student-session",
    )

    assert result["submission"]["student_username"] == "zyh"
    assert result["submission"]["assignment_id"] == "same-class"
