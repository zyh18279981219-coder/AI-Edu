from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DiagnosisModule.diagnosis_service import StudentDiagnosisService
from DigitalTwinModule.models import TrendPoint
from DigitalTwinModule.student_twin_service import StudentTwinService


def test_trend_drop_attribution_uses_same_day_evidence(monkeypatch):
    def fake_timeline(self, username, course_id, *, limit):
        assert username == "zyh"
        assert course_id == "course_big_data"
        return [
            {
                "type": "quiz",
                "node_id": "kafka-basic",
                "score": 45,
                "total": 100,
                "occurred_at": "2026-06-10T09:00:00",
            }
        ]

    monkeypatch.setattr(StudentDiagnosisService, "_load_evidence_timeline", fake_timeline)
    service = StudentTwinService.__new__(StudentTwinService)
    service.course_tree = type("CourseTreeStub", (), {"course_id": "course_big_data"})()

    result = service._build_trend_attribution_points(
        "zyh",
        [
            TrendPoint(date="2026-06-09", overall_mastery=76),
            TrendPoint(date="2026-06-10", overall_mastery=68),
        ],
        "course_big_data",
    )

    assert len(result) == 1
    assert result[0]["drop"] == 8
    assert result[0]["evidence_level"] == "partial"
    assert result[0]["evidence_status_label"] == "可追溯到当天学习证据"
    assert result[0]["primary_reason"] == "当天测验表现偏低"
    assert result[0]["snapshot_compare"]["change"] == -8
    assert result[0]["evidence_summary"][0]["type"] == "quiz"
    assert result[0]["evidence_summary"][0]["count"] == 1
    assert result[0]["evidence"][0]["type"] == "quiz"
    assert "测验" in result[0]["reason_summary"]


def test_trend_drop_attribution_does_not_force_reason_without_evidence(monkeypatch):
    monkeypatch.setattr(StudentDiagnosisService, "_load_evidence_timeline", lambda *_args, **_kwargs: [])
    service = StudentTwinService.__new__(StudentTwinService)
    service.course_tree = type("CourseTreeStub", (), {"course_id": "course_big_data"})()

    result = service._build_trend_attribution_points(
        "zyh",
        [
            TrendPoint(date="2026-06-09", overall_mastery=76),
            TrendPoint(date="2026-06-10", overall_mastery=68),
        ],
        "course_big_data",
    )

    assert result[0]["evidence_level"] == "insufficient"
    assert result[0]["evidence_status_label"] == "依据不足，不能强行归因"
    assert result[0]["primary_reason"] == "依据不足"
    assert result[0]["snapshot_compare"]["previous"]["overall_mastery"] == 76
    assert result[0]["snapshot_compare"]["current"]["overall_mastery"] == 68
    assert result[0]["evidence_summary"][0]["type"] == "missing"
    assert result[0]["evidence"] == []
    assert "暂不能强行归因" in result[0]["reason_summary"]
    assert "补充当天测验" in result[0]["suggested_actions"][0]
