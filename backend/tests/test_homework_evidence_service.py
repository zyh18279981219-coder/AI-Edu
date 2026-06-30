import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DigitalTwinModule.homework_evidence_service import HomeworkEvidenceService


def _row(
    *,
    assignment_id: str,
    submission_id: str,
    assignment_type: str,
    score: float,
    total_score: float = 100,
    covered_node_id: str | None = None,
    chapter_context: str = "第五章 综合实践",
):
    return {
        "assignment_id": assignment_id,
        "submission_id": submission_id,
        "title": assignment_id,
        "assignment_type": assignment_type,
        "course_id": "course_big_data",
        "assignment_node_id": "chapter-5",
        "node_name": "第五章",
        "node_path_json": '["第五章", "综合实践"]',
        "chapter_context": chapter_context,
        "total_score": total_score,
        "score": score,
        "evidence_at": "2026-06-28 10:00:00",
        "covered_node_id": covered_node_id,
        "confirmed_by_teacher": bool(covered_node_id),
        "confidence": 88.0,
        "coverage_reason": "教师确认覆盖该叶子知识点",
    }


def test_chapter_practice_uses_code_subjective_weights_and_excludes_objective():
    service = object.__new__(HomeworkEvidenceService)
    rows = [
        _row(assignment_id="subjective-1", submission_id="sub-1", assignment_type="subjective", score=60),
        _row(assignment_id="code-1", submission_id="sub-2", assignment_type="code", score=100),
        _row(assignment_id="objective-1", submission_id="sub-3", assignment_type="objective", score=0),
    ]

    chapters = service._build_chapter_practice(rows)

    assert len(chapters) == 1
    chapter = chapters[0]
    assert chapter["chapter"] == "第五章 综合实践"
    assert chapter["practice_score"] == 84.0
    assert chapter["practice_level"] == "较好达成"
    assert chapter["evidence_count"] == 2
    assert chapter["code_evidence_count"] == 1
    assert chapter["subjective_evidence_count"] == 1
    assert {item["assignment_type"] for item in chapter["evidence_items"]} == {"subjective", "code"}


def test_knowledge_point_coverage_requires_teacher_confirmed_rows_from_query():
    service = object.__new__(HomeworkEvidenceService)
    rows = [
        _row(
            assignment_id="code-1",
            submission_id="sub-1",
            assignment_type="code",
            score=90,
            covered_node_id="leaf-flume-basic",
        ),
        _row(
            assignment_id="subjective-1",
            submission_id="sub-2",
            assignment_type="subjective",
            score=70,
            covered_node_id=None,
        ),
    ]

    coverage = service._build_coverage_evidence(rows)

    assert len(coverage) == 1
    item = coverage[0]
    assert item["node_id"] == "leaf-flume-basic"
    assert item["auxiliary_score"] == 90.0
    assert item["weighted_mastery_delta"] == 7.5
    assert item["evidence_count"] == 1
    assert item["calculation_note"] == "只有教师确认覆盖知识点的作业才作为叶子知识点辅助证据，不替代测验证据。"
