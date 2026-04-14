from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def export_homework_json_to_sqlite(
    homework_store_path: str | Path = "data/homework/homework_store.json",
    sqlite_db_path: str | Path = "data/app.db",
) -> Dict[str, Any]:
    store_path = Path(homework_store_path)
    db_path = Path(sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not store_path.exists():
        return {
            "success": True,
            "assignments_exported": 0,
            "submissions_exported": 0,
            "message": f"homework store not found: {store_path}",
        }

    raw = store_path.read_text(encoding="utf-8")
    data = json.loads(raw or "{}")
    assignments = data.get("assignments", {}) if isinstance(data, dict) else {}
    submissions = data.get("submissions", {}) if isinstance(data, dict) else {}
    if not isinstance(assignments, dict):
        assignments = {}
    if not isinstance(submissions, dict):
        submissions = {}

    now = datetime.now().isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS homework_assignments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                assignment_type TEXT NOT NULL,
                class_name TEXT,
                due_at TEXT,
                rubric TEXT,
                questions_json TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS homework_submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT NOT NULL,
                student_username TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                ai_score REAL,
                ai_feedback TEXT,
                ai_rationale TEXT,
                teacher_score REAL,
                teacher_comment TEXT,
                graded_at TEXT,
                grader_username TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_homework_assignments_created_by
                ON homework_assignments(created_by);
            CREATE INDEX IF NOT EXISTS idx_homework_submissions_assignment
                ON homework_submissions(assignment_id);
            CREATE INDEX IF NOT EXISTS idx_homework_submissions_student
                ON homework_submissions(student_username);
            """
        )

        for item in assignments.values():
            if not isinstance(item, dict):
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO homework_assignments
                (id, title, description, assignment_type, class_name, due_at, rubric,
                 questions_json, created_by, created_at, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("id", ""),
                    item.get("title", ""),
                    item.get("description", ""),
                    item.get("assignment_type", "subjective"),
                    item.get("class_name", ""),
                    item.get("due_at"),
                    item.get("rubric", ""),
                    json.dumps(item.get("questions", []), ensure_ascii=False),
                    item.get("created_by", ""),
                    item.get("created_at", now),
                    item.get("status", "published"),
                    now,
                ),
            )

        for item in submissions.values():
            if not isinstance(item, dict):
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO homework_submissions
                (id, assignment_id, student_username, answers_json, submitted_at,
                 ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                 graded_at, grader_username, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("id", ""),
                    item.get("assignment_id", ""),
                    item.get("student_username", ""),
                    json.dumps(item.get("answers", []), ensure_ascii=False),
                    item.get("submitted_at", now),
                    item.get("ai_score"),
                    item.get("ai_feedback", ""),
                    item.get("ai_rationale", ""),
                    item.get("teacher_score"),
                    item.get("teacher_comment", ""),
                    item.get("graded_at"),
                    item.get("grader_username", ""),
                    now,
                ),
            )

        conn.commit()

    return {
        "success": True,
        "assignments_exported": len(assignments),
        "submissions_exported": len(submissions),
        "sqlite_db_path": str(db_path),
        "exported_at": now,
    }
