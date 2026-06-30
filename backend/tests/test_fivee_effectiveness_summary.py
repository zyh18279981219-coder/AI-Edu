from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fiveE.effectiveness_service import build_effectiveness_summary


def test_fivee_effectiveness_empty_state_has_no_fake_score():
    result = build_effectiveness_summary([], course_id="course_big_data")

    assert result["status"] == "empty"
    assert result["record_count"] == 0
    assert result["scored_record_count"] == 0
    assert result["overall_effectiveness_score"] is None
    assert result["evidence_status"] == "empty"
    assert result["student_view"]["show_numeric_score"] is False
    assert result["low_effectiveness_nodes"] == []
    assert "暂无" in result["message"]


def test_fivee_effectiveness_summary_aggregates_records():
    rows = [
        {
            "record_id": 1,
            "student_username": "zyh",
            "course_id": "course_big_data",
            "node_id": "Kafka 数据接入",
            "stage": "engagement",
            "interaction_count": 5,
            "valid_interaction_count": 4,
            "completion_rate": 70,
            "quiz_score_before": None,
            "quiz_score_after": None,
            "path_continue_rate": None,
            "effectiveness_score": 55,
            "calculated_at": "2026-06-28T10:00:00",
            "payload": {
                "summary": "学生完成互动但后续测验提升有限",
                "dimension_scores": {
                    "stage_completion": 20,
                    "valid_interaction": 80,
                    "learning_gain": None,
                    "learning_transfer": None,
                },
                "evidence_status": "process_only",
                "effectiveness_level": "效果一般",
            },
        },
        {
            "record_id": 2,
            "student_username": "stu_b",
            "course_id": "course_big_data",
            "node_id": "Kafka 数据接入",
            "stage": "explanation",
            "interaction_count": 4,
            "valid_interaction_count": 2,
            "completion_rate": 50,
            "effectiveness_score": 45,
            "calculated_at": "2026-06-28T11:00:00",
            "payload": {"note": "有效互动偏低", "evidence_status": "process_only"},
        },
        {
            "record_id": 3,
            "student_username": "zyh",
            "course_id": "course_big_data",
            "node_id": "Flink 窗口计算",
            "stage": "evaluation",
            "interaction_count": 6,
            "valid_interaction_count": 6,
            "completion_rate": 95,
            "quiz_score_before": 50,
            "quiz_score_after": 76,
            "path_continue_rate": 80,
            "effectiveness_score": 88,
            "calculated_at": "2026-06-28T12:00:00",
        },
    ]

    result = build_effectiveness_summary(rows, course_id="course_big_data", low_score_threshold=60)

    assert result["status"] == "ok"
    assert result["record_count"] == 3
    assert result["scored_record_count"] == 3
    assert result["outcome_supported_count"] == 1
    assert result["process_only_count"] == 2
    assert result["evidence_status"] == "outcome_supported"
    assert result["overall_effectiveness_score"] == 62.67
    assert result["effectiveness_level"] == "基本有效"
    assert result["student_view"]["show_numeric_score"] is False
    assert result["teacher_view"]["dimension_scores"]["learning_gain"] is not None
    assert result["stage_distribution"] == [
        {"stage": "engagement", "count": 1},
        {"stage": "evaluation", "count": 1},
        {"stage": "explanation", "count": 1},
    ]
    assert len(result["low_effectiveness_nodes"]) == 1
    low = result["low_effectiveness_nodes"][0]
    assert low["node_id"] == "Kafka 数据接入"
    assert low["record_count"] == 2
    assert low["student_count"] == 2
    assert low["avg_effectiveness_score"] == 50
    assert low["avg_valid_interaction_rate"] == 65
    assert low["evidence_status"] == "process_only"
    assert result["recent_evidence"][0]["node_id"] == "Flink 窗口计算"
    assert result["recent_evidence"][0]["evidence_status"] == "outcome_supported"
    assert result["recent_evidence"][1]["summary"] == "有效互动偏低"


def test_fivee_effectiveness_summary_marks_all_process_records_without_outcome_claim():
    rows = [
        {
            "record_id": 1,
            "student_username": "zyh",
            "course_id": "course_big_data",
            "node_id": "Kafka 数据接入",
            "stage": "exploration",
            "interaction_count": 1,
            "valid_interaction_count": 1,
            "completion_rate": 100,
            "effectiveness_score": 80,
            "calculated_at": "2026-06-28T10:00:00",
            "payload": {"evidence_status": "process_only"},
        }
    ]

    result = build_effectiveness_summary(rows, course_id="course_big_data")

    assert result["evidence_status"] == "process_only"
    assert result["outcome_supported_count"] == 0
    assert "不能据此认定学习提升" in result["teacher_view"]["summary"]
    assert result["student_view"]["show_numeric_score"] is False
