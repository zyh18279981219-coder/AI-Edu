import json
import sqlite3
from pathlib import Path

from HomeworkModule.exporter import export_homework_json_to_sqlite


def test_export_homework_json_to_sqlite(tmp_path: Path):
    store = tmp_path / "homework_store.json"
    db_path = tmp_path / "app.db"

    payload = {
        "assignments": {
            "a1": {
                "id": "a1",
                "title": "主观题作业",
                "description": "说明概念",
                "assignment_type": "subjective",
                "class_name": "Class-1",
                "due_at": None,
                "rubric": "rubric",
                "questions": [{"title": "Q1", "prompt": "P1"}],
                "created_by": "teacher_a",
                "created_at": "2026-01-01T00:00:00",
                "status": "published",
            }
        },
        "submissions": {
            "s1": {
                "id": "s1",
                "assignment_id": "a1",
                "student_username": "student_a",
                "answers": [{"answer": "text"}],
                "submitted_at": "2026-01-01T01:00:00",
                "ai_score": 80,
                "ai_feedback": "ok",
                "ai_rationale": "r",
                "teacher_score": 85,
                "teacher_comment": "good",
                "graded_at": "2026-01-01T02:00:00",
                "grader_username": "teacher_a",
            }
        },
    }
    store.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = export_homework_json_to_sqlite(store, db_path)
    assert result["success"] is True
    assert result["assignments_exported"] == 1
    assert result["submissions_exported"] == 1

    with sqlite3.connect(db_path) as conn:
        row_a = conn.execute("SELECT id, title, assignment_type FROM homework_assignments WHERE id='a1'").fetchone()
        row_s = conn.execute("SELECT id, assignment_id, student_username FROM homework_submissions WHERE id='s1'").fetchone()

    assert row_a == ("a1", "主观题作业", "subjective")
    assert row_s == ("s1", "a1", "student_a")
