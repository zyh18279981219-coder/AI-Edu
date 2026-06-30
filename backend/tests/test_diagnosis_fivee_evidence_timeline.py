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


class FakeStore:
    def connection(self):
        return EmptyConnection()

    def list_fivee_effectiveness_records(self, *, course_id, student_username, limit):
        assert course_id == "course_big_data"
        assert student_username == "zyh"
        assert limit == 40
        return [
            {
                "record_id": 12,
                "student_username": "zyh",
                "course_id": "course_big_data",
                "node_id": "kafka-basic",
                "stage": "explanation",
                "interaction_count": 3,
                "valid_interaction_count": 2,
                "completion_rate": 66.67,
                "effectiveness_score": 72.5,
                "calculated_at": "2026-06-28T10:30:00",
                "payload": {
                    "summary": "5E 单轮互动有效度记录",
                    "effectiveness_level": "基本有效",
                    "evidence_status": "process_only",
                    "mastery_update_policy": "not_updated_by_5e_effectiveness",
                },
            }
        ]


def test_fivee_effectiveness_records_enter_diagnosis_timeline_as_auxiliary_evidence():
    service = StudentDiagnosisService.__new__(StudentDiagnosisService)
    service.store = FakeStore()

    timeline = service._load_evidence_timeline("zyh", "course_big_data", limit=40)

    assert len(timeline) == 1
    item = timeline[0]
    assert item["type"] == "fivee_effectiveness"
    assert item["node_id"] == "kafka-basic"
    assert item["stage"] == "explanation"
    assert item["effectiveness_score"] == 72.5
    assert item["effectiveness_level"] == "基本有效"
    assert item["evidence_status"] == "process_only"
    assert item["mastery_update_policy"] == "not_updated_by_5e_effectiveness"

    student_timeline = service._student_evidence_timeline(timeline)
    assert "effectiveness_score" not in student_timeline[0]
    assert "interaction_count" not in student_timeline[0]
    assert "valid_interaction_count" not in student_timeline[0]

    assert student_timeline[0]["type_label"] == "5E 引导"
    assert "引导反馈" in student_timeline[0]["summary"]
    assert "72.5" not in student_timeline[0]["summary"]
    assert "需要结合后续测验或路径完成情况判断效果" in student_timeline[0]["summary"]
    assert "不直接改写掌握度" in student_timeline[0]["summary"]
