from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DiagnosisModule.diagnosis_service import StudentDiagnosisService


class EmptyCursor:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs):
        return None

    def fetchall(self):
        return []


class EmptyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return EmptyCursor()


class PathCompletionEvidenceStore:
    def connection(self):
        return EmptyConnection()

    def list_learning_path_node_status(self, username, *, path_id=None, plan_id=None, status=None):
        assert username == "zyh"
        assert status == "completed"
        return [
            {
                "status_id": 31,
                "path_id": 9,
                "username": "zyh",
                "course_id": "course_big_data",
                "node_id": "kafka-basic",
                "item_type": "course_knowledge_point",
                "source_type": "published_course_graph",
                "status": "completed",
                "mastery_before": 42,
                "mastery_after": 76,
                "completed_at": "2026-06-28T13:20:00",
                "payload": {
                    "status_update": {"source": "student_path_panel"},
                },
            },
            {
                "status_id": 32,
                "path_id": 10,
                "username": "zyh",
                "course_id": "other_course",
                "node_id": "other-node",
                "status": "completed",
                "completed_at": "2026-06-28T14:20:00",
            },
        ]

    def list_fivee_effectiveness_records(self, *, course_id, student_username, limit):
        return []

    def list_intervention_completion_evidence(self, *, course_id, student_username, limit):
        return []


def test_completed_path_node_enters_diagnosis_timeline_as_auxiliary_evidence():
    service = StudentDiagnosisService.__new__(StudentDiagnosisService)
    service.store = PathCompletionEvidenceStore()

    timeline = service._load_evidence_timeline("zyh", "course_big_data", limit=40)

    assert len(timeline) == 1
    item = timeline[0]
    assert item["type"] == "path_node_completion"
    assert item["node_id"] == "kafka-basic"
    assert item["mastery_before"] == 42
    assert item["mastery_after"] == 76
    assert item["path_id"] == 9
    assert item["mastery_update_policy"] == "path_completion_is_auxiliary_evidence"

    student_timeline = service._student_evidence_timeline(timeline)

    assert student_timeline[0]["type_label"] == "个性化路径"
    assert "plan_id" not in student_timeline[0]
    assert "path_id" not in student_timeline[0]
    assert "status_id" not in student_timeline[0]
    assert "payload" not in student_timeline[0]
    assert "完成前掌握度：42.0" in student_timeline[0]["summary"]
    assert "完成后自评记录掌握度：76.0" in student_timeline[0]["summary"]
    assert "不直接替代测验或作业结论" in student_timeline[0]["summary"]
