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


class _FakeProfileStore:
    def load(self, username):
        return type(
            "Profile",
            (),
            {
                "username": username,
                "overall_mastery": 75,
                "knowledge_nodes": [],
                "model_dump": lambda self: {"username": username},
            },
        )()


class _FakeDiagnosisService:
    def generate_student_diagnosis(self, username, course_id=None, persist=True):
        return {"username": username, "course_id": course_id, "weak_nodes": []}


class _FakeStore:
    def list_teacher_students(self, teacher_username):
        if teacher_username == "teacher":
            return [{"student_username": "zyh"}]
        return []

    def record_diagnosis_correction(self, **kwargs):
        return 1

    def list_diagnosis_corrections(self, **kwargs):
        return []


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(
        digital_twin_api,
        "_session_manager",
        _FakeSessionManager(
            {
                "student": {"username": "zyh", "user_type": "student"},
                "teacher": {"username": "teacher", "user_type": "teacher"},
                "admin": {"username": "admin", "user_type": "admin"},
                "other": {"username": "other", "user_type": "student"},
            }
        ),
    )
    monkeypatch.setattr(digital_twin_api, "TwinProfileStore", lambda: _FakeProfileStore())
    monkeypatch.setattr(digital_twin_api, "StudentDiagnosisService", lambda: _FakeDiagnosisService())
    monkeypatch.setattr(digital_twin_api, "get_database_store", lambda: _FakeStore())
    monkeypatch.setattr(digital_twin_api, "_current_session", lambda session_id: _FakeSessionManager({
        "student": {"username": "zyh", "user_type": "student"},
        "teacher": {"username": "teacher", "user_type": "teacher"},
        "admin": {"username": "admin", "user_type": "admin"},
        "other": {"username": "other", "user_type": "student"},
    }).get_session(session_id))
    monkeypatch.setattr(digital_twin_api, "build_student_course_profile", lambda student_id, course_id: {"student_id": student_id, "course_id": course_id})
    monkeypatch.setattr(digital_twin_api, "get_database_store", lambda: _FakeStore())


@pytest.mark.anyio
async def test_profile_requires_matching_session():
    with pytest.raises(HTTPException) as exc:
        await digital_twin_api.get_profile("zyh", session_id=None)
    assert exc.value.status_code == 403

    result = await digital_twin_api.get_profile("zyh", session_id="student")
    assert result["username"] == "zyh"

    with pytest.raises(HTTPException) as exc2:
        await digital_twin_api.get_profile("other", session_id="student")
    assert exc2.value.status_code == 403


@pytest.mark.anyio
async def test_diagnosis_requires_scope_before_generation():
    with pytest.raises(HTTPException) as exc:
        await digital_twin_api.generate_student_diagnosis("other", digital_twin_api.DiagnosisRequest(course_id="course_big_data"), session_id="student")
    assert exc.value.status_code == 403

    result = await digital_twin_api.generate_student_diagnosis("zyh", digital_twin_api.DiagnosisRequest(course_id="course_big_data"), session_id="student")
    assert result["username"] == "zyh"


@pytest.mark.anyio
async def test_diagnosis_corrections_require_teacher_scope():
    with pytest.raises(HTTPException) as exc:
        await digital_twin_api.record_diagnosis_correction(
            digital_twin_api.DiagnosisCorrectionRequest(
                report_id="r1",
                username="zyh",
                course_id="course_big_data",
                teacher_username="teacher",
            ),
            session_id="student",
        )
    assert exc.value.status_code == 403

    result = await digital_twin_api.record_diagnosis_correction(
        digital_twin_api.DiagnosisCorrectionRequest(
            report_id="r1",
            username="zyh",
            course_id="course_big_data",
            teacher_username="teacher",
        ),
        session_id="teacher",
    )
    assert result["success"] is True


@pytest.mark.anyio
async def test_student_course_profile_requires_scope():
    with pytest.raises(HTTPException) as exc:
        await digital_twin_api.get_student_course_profile(
            digital_twin_api.StudentCourseProfileRequest(student_id="other", course_id="course_big_data"),
        )
    assert exc.value.status_code == 403
