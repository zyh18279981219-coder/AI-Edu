from __future__ import annotations

import os
import sys

import pytest
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fiveE.apis import (  # noqa: E402
    _effectiveness_for_session,
    _student_username_for_effectiveness,
)


def _summary() -> dict:
    return {
        "status": "ok",
        "course_id": "course_big_data",
        "student_username": "zyh",
        "record_count": 2,
        "outcome_supported_count": 1,
        "process_only_count": 1,
        "insufficient_evidence_count": 0,
        "overall_effectiveness_score": 78.5,
        "effectiveness_level": "基本有效",
        "evidence_status": "outcome_supported",
        "dimension_scores": {
            "stage_completion": 80,
            "valid_interaction": 90,
            "learning_gain": 70,
            "learning_transfer": 60,
        },
        "low_effectiveness_nodes": [
            {
                "node_id": "Kafka 数据接入",
                "student_count": 3,
                "avg_effectiveness_score": 45,
            }
        ],
        "stage_distribution": [{"stage": "evaluation", "count": 2}],
        "student_view": {
            "show_numeric_score": False,
            "summary": "本次 5E 引导已关联到后续学习结果。",
            "effectiveness_level": "基本有效",
            "evidence_status": "outcome_supported",
            "next_steps": ["完成一次小测"],
        },
        "teacher_view": {
            "summary": "教师侧分析摘要",
            "dimension_scores": {"learning_gain": 70},
        },
        "recent_evidence": [
            {
                "record_id": 11,
                "student_username": "zyh",
                "course_id": "course_big_data",
                "node_id": "Kafka 数据接入",
                "stage": "evaluation",
                "effectiveness_score": 78.5,
                "effectiveness_level": "基本有效",
                "evidence_status": "outcome_supported",
                "dimension_scores": {"learning_gain": 70},
                "summary": "教师可见摘要",
                "student_feedback": "学生可见反馈",
                "mastery_update_policy": "not_updated_by_5e_effectiveness",
                "calculated_at": "2026-06-29T10:00:00",
            }
        ],
    }


def test_student_effectiveness_summary_is_student_safe():
    result = _effectiveness_for_session(
        _summary(),
        {"user_type": "student", "username": "zyh"},
    )

    assert "teacher_view" not in result
    assert "dimension_scores" not in result
    assert "overall_effectiveness_score" not in result
    assert "low_effectiveness_nodes" not in result
    assert result["student_view"]["show_numeric_score"] is False
    evidence = result["recent_evidence"][0]
    assert "effectiveness_score" not in evidence
    assert "dimension_scores" not in evidence
    assert "student_username" not in evidence
    assert evidence["summary"] == "学生可见反馈"
    assert evidence["mastery_update_policy"] == "not_updated_by_5e_effectiveness"


def test_teacher_effectiveness_summary_keeps_teacher_view():
    result = _effectiveness_for_session(
        _summary(),
        {"user_type": "teacher", "username": "teacher"},
    )

    assert "teacher_view" in result
    assert result["overall_effectiveness_score"] == 78.5
    assert result["low_effectiveness_nodes"][0]["student_count"] == 3


def test_student_can_only_request_own_effectiveness_summary():
    with pytest.raises(HTTPException) as exc_info:
        _student_username_for_effectiveness(
            {"user_type": "student", "username": "zyh"},
            "other_student",
        )

    assert exc_info.value.status_code == 403


def test_student_request_defaults_to_session_username():
    result = _student_username_for_effectiveness(
        {"user_type": "student", "username": "zyh"},
        None,
    )

    assert result == "zyh"
