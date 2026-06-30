import os
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class DraftCourseStore:
    def __init__(self):
        self.recorded_events = []
        self.summary_calls = []

    def get_course_summary(self, course_id):
        self.summary_calls.append(course_id)
        return {
            "course_id": course_id,
            "course_name": "Draft Course",
            "lifecycle_status": "draft",
        }

    def get_course_payload(self, course_id):
        return {
            "root_name": "Draft Root",
            "children": [
                {"name": "Draft Node", "resource_path": ["draft.pdf"]},
            ],
        }

    def list_resources_for_node_name(self, course_id, node_name):
        return ["draft.pdf"]

    def record_resource_learning_event(self, **kwargs):
        self.recorded_events.append(kwargs)
        return 1

    def summarize_resource_learning_events(self, **kwargs):
        return {"total_events": 1, "total_duration_seconds": 60}

    def get_user_by_identifier(self, user_type, identifier):
        if user_type == "student":
            return {"username": "stu_a"}
        return None


def test_course_tree_does_not_load_draft_payload(monkeypatch, tmp_path):
    from DatabaseModule.database_factory import DatabaseFactory
    from DigitalTwinModule.course_tree import CourseTree

    fallback = tmp_path / "fallback.json"
    fallback.write_text('{"root_name": "Fallback", "children": []}', encoding="utf-8")
    monkeypatch.setattr(DatabaseFactory, "_instance", DraftCourseStore())

    tree = CourseTree("draft_course", path=str(fallback))

    assert tree.get_all_leaf_nodes() == []
    assert tree.get_resource_paths("Draft Node") == []


def test_diagnosis_rejects_draft_course():
    from DiagnosisModule.diagnosis_service import StudentDiagnosisService

    service = StudentDiagnosisService()
    service.store = DraftCourseStore()

    with pytest.raises(PermissionError):
        service._require_published_course("draft_course")


def test_resource_recommender_skips_draft_local_resources():
    from PathPlannerModule.resource_recommender import ResourceRecommender

    recommender = ResourceRecommender()
    recommender.store = DraftCourseStore()

    assert recommender._get_local_resources("Draft Node") == []


def test_student_graph_helper_hides_draft_but_staff_can_read(monkeypatch):
    import app as app_module

    store = DraftCourseStore()
    monkeypatch.setattr(app_module, "database_store", store)
    app_module._clear_course_cache_for_course("course_big_data")

    student_course_id, student_payload = app_module._load_course_graph_entity_only(
        {"username": "stu_a", "user_type": "student"}
    )
    staff_course_id, staff_payload = app_module._load_course_graph_entity_only(
        {"username": "teacher", "user_type": "teacher"}
    )

    assert student_course_id == "course_big_data"
    assert student_payload == {}
    assert staff_course_id == "course_big_data"
    assert staff_payload.get("root_name") == "Draft Root"


def test_learning_progress_rejects_draft_course_before_node_count(monkeypatch):
    import app as app_module

    store = DraftCourseStore()
    monkeypatch.setattr(app_module, "database_store", store)
    monkeypatch.setattr(
        app_module,
        "get_current_user",
        lambda session_id=None: {"username": "stu_a", "user_type": "student"},
    )

    with pytest.raises(HTTPException) as exc_info:
        import asyncio

        asyncio.run(app_module.get_learning_progress(session_id="student-session"))

    assert exc_info.value.status_code == 404


def test_resource_learning_event_rejects_draft_course(monkeypatch):
    import app as app_module
    import asyncio

    store = DraftCourseStore()
    monkeypatch.setattr(app_module, "database_store", store)
    monkeypatch.setattr(
        app_module,
        "get_current_user",
        lambda session_id=None: {"username": "stu_a", "user_id": 3, "user_type": "student"},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            app_module.record_resource_learning_event(
                app_module.ResourceLearningEventRequest(
                    course_id="course_big_data",
                    node_id="Draft Node",
                    resource_path="draft.pdf",
                    event_type="completed",
                ),
                session_id="student-session",
            )
        )

    assert exc_info.value.status_code == 404
    assert store.recorded_events == []


def test_resource_learning_summary_rejects_draft_course_for_student(monkeypatch):
    import app as app_module
    import asyncio

    store = DraftCourseStore()
    monkeypatch.setattr(app_module, "database_store", store)
    monkeypatch.setattr(
        app_module,
        "get_current_user",
        lambda session_id=None: {"username": "stu_a", "user_type": "student"},
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            app_module.get_resource_learning_summary(
                course_id="course_big_data",
                session_id="student-session",
            )
        )

    assert exc_info.value.status_code == 404


def test_student_course_profile_rejects_draft_course(monkeypatch):
    from DigitalTwinModule import student_course_profile_service as service

    monkeypatch.setattr(service, "get_database_store", lambda: DraftCourseStore())

    with pytest.raises(PermissionError):
        service.get_student_course_profile("stu_a", "draft_course")
