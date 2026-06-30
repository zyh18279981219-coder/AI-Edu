from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DiagnosisModule.diagnosis_service import StudentDiagnosisService


class SequencedCursor:
    def __init__(self, result_sets):
        self.result_sets = list(result_sets)
        self.index = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs):
        self.index += 1

    def fetchall(self):
        if self.index < 0 or self.index >= len(self.result_sets):
            return []
        return self.result_sets[self.index]


class SequencedConnection:
    def __init__(self, result_sets):
        self.result_sets = result_sets

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return SequencedCursor(self.result_sets)


class TimelineStore:
    def connection(self):
        return SequencedConnection(
            [
                [
                    {
                        "node_id": "kafka-basic",
                        "score": 1,
                        "total": 5,
                        "passed": 0,
                        "payload_json": {
                            "extra": {
                                "definition_status": "generated_fallback",
                                "definition_source": "generated",
                                "evidence_policy": "generated_quiz_is_supplemental_evidence",
                            }
                        },
                        "created_at": "2026-06-29 10:00:00",
                    },
                    {
                        "node_id": "flink-window",
                        "score": 4,
                        "total": 5,
                        "passed": 1,
                        "payload_json": {
                            "extra": {
                                "definition_id": "quizdef_1",
                                "definition_status": "published",
                                "definition_source": "published_definition",
                                "evidence_policy": "published_quiz_definition",
                            }
                        },
                        "created_at": "2026-06-29 09:00:00",
                    },
                ],
                [],
                [],
            ]
        )

    def list_fivee_effectiveness_records(self, *, course_id, student_username, limit):
        return []

    def list_intervention_completion_evidence(self, *, course_id, student_username, limit):
        return []

    def list_learning_path_node_status(self, username, *, plan_id=None, status=None):
        return []


def build_service(store=None):
    service = StudentDiagnosisService.__new__(StudentDiagnosisService)
    service.store = store or object()
    return service


def test_generated_quiz_fallback_is_not_strong_quiz_evidence():
    service = build_service()
    item = service._diagnose_node(
        {
            "node_id": "kafka-basic",
            "mastery_score": 72,
            "quiz_score": 0,
            "progress": 0,
            "study_duration_minutes": 0,
            "updated_at": None,
        },
        {
            "attempt_count": 0,
            "avg_score": 0,
            "supplemental_attempt_count": 1,
            "total_attempt_count": 1,
            "last_attempt_at": None,
            "last_any_attempt_at": "2026-06-29T10:00:00",
        },
        {},
    )

    assert item["evidence_level"] == "partial"
    assert item["evidence_insufficiency_reason"] == "supplemental_quiz_only"
    assert item["reason_type"] == "currently_stable"
    assert item["is_weak"] is False
    assert item["quiz"]["supplemental_attempt_count"] == 1


def test_published_quiz_definition_can_support_quiz_weak_diagnosis():
    service = build_service()
    item = service._diagnose_node(
        {
            "node_id": "kafka-basic",
            "mastery_score": 72,
            "quiz_score": 0,
            "progress": 70,
            "study_duration_minutes": 12,
            "updated_at": None,
        },
        {
            "attempt_count": 2,
            "avg_score": 45,
            "supplemental_attempt_count": 0,
            "total_attempt_count": 2,
            "last_attempt_at": "2026-06-29T10:00:00",
            "last_any_attempt_at": "2026-06-29T10:00:00",
        },
        {},
    )

    assert item["evidence_level"] == "sufficient"
    assert item["reason_type"] == "quiz_errors_concentrated"
    assert item["is_weak"] is True


def test_quiz_timeline_marks_formal_and_supplemental_policy():
    service = build_service(TimelineStore())

    timeline = service._load_evidence_timeline("zyh", "course_big_data", limit=40)
    quiz_items = [item for item in timeline if item["type"] == "quiz"]

    assert quiz_items[0]["node_id"] == "kafka-basic"
    assert quiz_items[0]["definition_status"] == "generated_fallback"
    assert quiz_items[0]["evidence_status"] == "supplemental_evidence"
    assert quiz_items[0]["evidence_policy"] == "generated_quiz_is_supplemental_evidence"
    assert quiz_items[1]["definition_status"] == "published"
    assert quiz_items[1]["evidence_status"] == "formal_evidence"

    student_items = service._student_evidence_timeline(quiz_items)
    assert "仅作辅助参考" in student_items[0]["summary"]
    assert "可用于正式诊断" in student_items[1]["summary"]
    assert "definition_status" not in student_items[0]
    assert "definition_id" not in student_items[1]
