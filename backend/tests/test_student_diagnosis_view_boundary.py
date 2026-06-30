import os
import sys

import pytest
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DigitalTwinModule import digital_twin_api


def sample_diagnosis():
    return {
        "report_id": "diag_1",
        "username": "zyh",
        "user_id": 1,
        "course_id": "course_big_data",
        "report_date": "2026-06-29",
        "diagnosis_type": "student_learning",
        "evidence_level": "partial",
        "confidence": 72,
        "persona_summary": "存在薄弱点",
        "student_view": {
            "summary": "建议复习基础概念",
            "evidence_timeline": [{"type": "quiz", "summary": "测验表现待提升"}],
        },
        "teacher_view": {
            "weak_nodes": [{"node_id": "node_1"}],
            "all_nodes": [{"node_id": "node_1", "raw_score": 42}],
            "evidence_timeline": [{"type": "quiz", "raw_answer": "teacher-only"}],
            "manual_correction_supported": True,
        },
        "weak_nodes": [{"node_id": "node_1"}],
        "formulas": {"node_mastery_weak": "mastery_score < 60"},
        "thresholds": {"weak_mastery": 60},
        "generated_at": "2026-06-29T12:00:00",
    }


def test_student_session_receives_student_safe_diagnosis():
    result = digital_twin_api._diagnosis_for_session(
        sample_diagnosis(),
        {"username": "zyh", "user_type": "student"},
        "zyh",
    )

    assert "student_view" in result
    assert "teacher_view" not in result


def test_student_safe_diagnosis_strips_teacher_only_fields():
    result = digital_twin_api._diagnosis_for_session(
        sample_diagnosis(),
        {"username": "zyh", "user_type": "student"},
        "zyh",
    )

    payload_text = str(result)
    assert "teacher-only" not in payload_text
    assert "raw_answer" not in payload_text
    assert "manual_correction_supported" not in payload_text
    assert "formulas" in result
    assert result["student_view"]["evidence_timeline"] == [{"type": "quiz", "summary": "测验表现待提升"}]


def test_anonymous_session_defaults_to_student_safe_diagnosis():
    result = digital_twin_api._diagnosis_for_session(sample_diagnosis(), None, "zyh")

    assert "student_view" in result
    assert "teacher_view" not in result


def test_teacher_session_receives_teacher_view():
    result = digital_twin_api._diagnosis_for_session(
        sample_diagnosis(),
        {"username": "teacher", "user_type": "teacher"},
        "zyh",
    )

    assert "teacher_view" in result
    assert result["teacher_view"]["manual_correction_supported"] is True


def test_student_cannot_read_other_student_diagnosis():
    with pytest.raises(HTTPException) as exc_info:
        digital_twin_api._diagnosis_for_session(
            sample_diagnosis(),
            {"username": "other_student", "user_type": "student"},
            "zyh",
        )

    assert exc_info.value.status_code == 403
