from __future__ import annotations

import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DatabaseModule.mysql_store import MySQLStore
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


class InterventionEvidenceStore:
    def __init__(self, status: str = "completed") -> None:
        self.status = status

    def connection(self):
        return EmptyConnection()

    def list_fivee_effectiveness_records(self, *, course_id, student_username, limit):
        return []

    def list_intervention_completion_evidence(self, *, course_id, student_username, limit):
        assert course_id == "course_big_data"
        assert student_username == "zyh"
        if self.status != "completed":
            return []
        return [
            {
                "record_id": 21,
                "package_id": "pkg_1",
                "student_username": "zyh",
                "teacher_username": "teacher",
                "course_id": "course_big_data",
                "package_title": "Kafka 干预任务包",
                "status": "completed",
                "score": 86.5,
                "completed_at": "2026-06-28T12:00:00",
                "record_payload": {
                    "progress": {
                        "completion_rate": 1,
                        "answered_questions": 2,
                        "total_questions": 2,
                    },
                    "answers": [{"answer": "A"}, {"answer": "B"}],
                    "grades": [{"teacher_score": 88}, {"ai_score": 85}],
                    "score_summary": {"average_final_score": 86.5, "graded_questions": 2},
                },
                "package_payload": {
                    "diagnosis": {
                        "weak_nodes": [{"node_id": "kafka-basic"}],
                    }
                },
                "items": [
                    {
                        "item_id": 7,
                        "item_type": "practice_question",
                        "node_id": "kafka-basic",
                        "payload": {"question_id": "q1"},
                    }
                ],
            }
        ]


def test_completed_intervention_enters_diagnosis_timeline_as_auxiliary_evidence():
    service = StudentDiagnosisService.__new__(StudentDiagnosisService)
    service.store = InterventionEvidenceStore()

    timeline = service._load_evidence_timeline("zyh", "course_big_data", limit=40)

    assert len(timeline) == 1
    item = timeline[0]
    assert item["type"] == "intervention_completion"
    assert item["package_id"] == "pkg_1"
    assert item["node_id"] == "kafka-basic"
    assert item["score"] == 86.5
    assert item["completion_rate"] == 1
    assert item["teacher_graded"] is True
    assert item["mastery_update_policy"] == "intervention_completion_is_auxiliary_evidence"

    student_timeline = service._student_evidence_timeline(timeline)

    assert student_timeline[0]["type_label"] == "教师干预任务"
    assert "package_id" not in student_timeline[0]
    assert "teacher_username" not in student_timeline[0]
    assert "answered_questions" not in student_timeline[0]
    assert "total_questions" not in student_timeline[0]
    assert "完成度：100%" in student_timeline[0]["summary"]
    assert "任务得分：86.5" in student_timeline[0]["summary"]
    assert "教师已评分" in student_timeline[0]["summary"]
    assert "不直接替代测验或作业结论" in student_timeline[0]["summary"]


def test_unfinished_intervention_is_not_loaded_as_completion_evidence():
    service = StudentDiagnosisService.__new__(StudentDiagnosisService)
    service.store = InterventionEvidenceStore(status="in_progress")

    timeline = service._load_evidence_timeline("zyh", "course_big_data", limit=40)

    assert timeline == []


class CompletionCursor:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs):
        return None

    def fetchall(self):
        return self.rows


class CompletionConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return CompletionCursor(self.rows)


def test_completion_evidence_filters_non_course_node_ids():
    store = MySQLStore.__new__(MySQLStore)
    store._lock = threading.Lock()
    store.connection = lambda: CompletionConnection(
        [
            {
                "record_id": 21,
                "package_id": "pkg_1",
                "student_username": "zyh",
                "status": "completed",
                "score": 90,
                "feedback": "",
                "started_at": None,
                "completed_at": None,
                "record_payload_json": "{}",
                "created_at": None,
                "updated_at": None,
                "teacher_username": "teacher",
                "course_id": "course_big_data",
                "package_title": "Kafka intervention",
                "risk_level": "medium",
                "diagnosis_report_id": "diag_1",
                "package_payload_json": '{"diagnosis":{"course_id":"course_big_data"}}',
                "item_summary": (
                    '1|||FIELD|||concept_review|||FIELD|||Kafka 消息队列核心原理|||FIELD|||||FIELD|||{"concept":"Kafka 消息队列核心原理"}'
                    '|||ITEM|||2|||FIELD|||resource_review|||FIELD|||kafka-basic|||FIELD|||Kafka 基础讲解|||FIELD|||{"resource_task":{"node_id":"kafka-basic"}}'
                ),
            }
        ]
    )
    store.list_course_node_binding_candidates = lambda course_id: [
        {
            "node_id": "kafka-basic",
            "node_name": "Kafka 基础",
            "node_path": ["大数据课程", "Kafka 基础"],
            "is_leaf": True,
        }
    ]

    records = store.list_intervention_completion_evidence(
        course_id="course_big_data",
        student_username="zyh",
        limit=10,
    )

    assert records[0]["items"][0]["item_type"] == "concept_review"
    assert records[0]["items"][0]["node_id"] is None
    assert records[0]["items"][1]["item_type"] == "resource_review"
    assert records[0]["items"][1]["node_id"] == "kafka-basic"
