from __future__ import annotations

import os
import sys
import asyncio

import pytest
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app as app_module


class _ResourceLearningStore:
    def __init__(self) -> None:
        self.calls = []

    def record_resource_learning_event(self, **kwargs):
        self.calls.append(kwargs)
        return 901


@pytest.fixture()
def resource_store(monkeypatch):
    store = _ResourceLearningStore()
    monkeypatch.setattr(app_module, "database_store", store)
    return store


def test_resource_learning_event_records_student_evidence(resource_store, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_current_user",
        lambda session_id=None: {"username": "zyh", "user_id": 7, "user_type": "student"},
    )

    result = asyncio.run(
        app_module.record_resource_learning_event(
            app_module.ResourceLearningEventRequest(
                course_id="course_big_data",
                node_id="Kafka 数据接入",
                resource_path="data/Book/101.PDF",
                event_type="completed",
                duration_seconds=180,
                progress_percent=100,
                is_completed=True,
                payload={"source": "course_content"},
            ),
            session_id="s1",
        )
    )

    assert result == {"success": True, "event_id": 901}
    assert resource_store.calls == [
        {
            "username": "zyh",
            "user_id": 7,
            "course_id": "course_big_data",
            "node_id": "Kafka 数据接入",
            "resource_id": None,
            "resource_path": "data/Book/101.PDF",
            "event_type": "completed",
            "duration_seconds": 180,
            "progress_percent": 100.0,
            "is_completed": True,
            "payload": {"source": "course_content"},
        }
    ]


def test_resource_learning_event_rejects_teacher(resource_store, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_current_user",
        lambda session_id=None: {"username": "teacher", "user_id": 2, "user_type": "teacher"},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            app_module.record_resource_learning_event(
                app_module.ResourceLearningEventRequest(
                    course_id="course_big_data",
                    node_id="Kafka 数据接入",
                    event_type="started",
                ),
                session_id="s1",
            )
        )

    assert exc_info.value.status_code == 403
    assert resource_store.calls == []
