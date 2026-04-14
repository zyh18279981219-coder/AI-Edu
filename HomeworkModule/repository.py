from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class HomeworkRepository:
    """SQLite-backed repository for homework data."""

    def __init__(
        self,
        db_path: str | Path = "data/app.db",
        legacy_store_path: str | Path = "data/homework/homework_store.json",
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.legacy_store_path = Path(legacy_store_path)
        self._migrate_marker = self.legacy_store_path.with_name(".migrated_to_sqlite")
        self._lock = threading.RLock()
        self._initialize()
        self._migrate_legacy_json_once()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._lock, self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS homework_assignments (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    assignment_type TEXT NOT NULL,
                    class_name TEXT,
                    due_at TEXT,
                    allow_late INTEGER NOT NULL DEFAULT 0,
                    total_score REAL NOT NULL DEFAULT 100,
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
                    status TEXT NOT NULL DEFAULT 'submitted',
                    ai_score REAL,
                    ai_feedback TEXT,
                    ai_rationale TEXT,
                    teacher_score REAL,
                    teacher_comment TEXT,
                    graded_at TEXT,
                    grader_username TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (assignment_id) REFERENCES homework_assignments(id)
                );

                CREATE INDEX IF NOT EXISTS idx_homework_assignments_created_by
                    ON homework_assignments(created_by);
                CREATE INDEX IF NOT EXISTS idx_homework_assignments_created_at
                    ON homework_assignments(created_at);
                CREATE INDEX IF NOT EXISTS idx_homework_submissions_assignment
                    ON homework_submissions(assignment_id);
                CREATE INDEX IF NOT EXISTS idx_homework_submissions_student
                    ON homework_submissions(student_username);
                """
            )
            self._ensure_column(conn, "homework_assignments", "allow_late", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "homework_assignments", "total_score", "REAL NOT NULL DEFAULT 100")
            self._ensure_column(conn, "homework_submissions", "status", "TEXT NOT NULL DEFAULT 'submitted'")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row[1]) for row in rows}
        if column in existing:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _normalize_assignment_type(self, value: Any) -> str:
        raw = str(value or "subjective").strip().lower()
        if raw == "code_practice":
            return "code"
        if raw not in {"subjective", "objective", "choice", "code"}:
            return "subjective"
        return raw

    def _count_records(self) -> Dict[str, int]:
        with self._lock, self.connection() as conn:
            assignment_count = conn.execute("SELECT COUNT(1) AS c FROM homework_assignments").fetchone()["c"]
            submission_count = conn.execute("SELECT COUNT(1) AS c FROM homework_submissions").fetchone()["c"]
        return {
            "assignments": int(assignment_count or 0),
            "submissions": int(submission_count or 0),
        }

    def _migrate_legacy_json_once(self) -> None:
        if self._migrate_marker.exists():
            return
        if not self.legacy_store_path.exists():
            return

        counts = self._count_records()
        if counts["assignments"] > 0 or counts["submissions"] > 0:
            self._migrate_marker.parent.mkdir(parents=True, exist_ok=True)
            self._migrate_marker.write_text(self._now(), encoding="utf-8")
            return

        raw = self.legacy_store_path.read_text(encoding="utf-8")
        data = json.loads(raw or "{}")
        assignments = data.get("assignments", {}) if isinstance(data, dict) else {}
        submissions = data.get("submissions", {}) if isinstance(data, dict) else {}

        if not isinstance(assignments, dict):
            assignments = {}
        if not isinstance(submissions, dict):
            submissions = {}

        now = self._now()
        with self._lock, self.connection() as conn:
            for item in assignments.values():
                if not isinstance(item, dict):
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO homework_assignments
                    (id, title, description, assignment_type, class_name, due_at, allow_late, total_score, rubric,
                     questions_json, created_by, created_at, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.get("id", uuid4().hex),
                        item.get("title", ""),
                        item.get("description", ""),
                        self._normalize_assignment_type(item.get("assignment_type", "subjective")),
                        item.get("class_name", ""),
                        item.get("due_at"),
                        1 if item.get("allow_late") else 0,
                        float(item.get("total_score", 100) or 100),
                        item.get("rubric", ""),
                        json.dumps(item.get("questions", []), ensure_ascii=False),
                        item.get("created_by", ""),
                        item.get("created_at", now),
                        item.get("status", "draft"),
                        now,
                    ),
                )

            for item in submissions.values():
                if not isinstance(item, dict):
                    continue
                conn.execute(
                    """
                    INSERT OR REPLACE INTO homework_submissions
                    (id, assignment_id, student_username, answers_json, submitted_at, status,
                     ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                     graded_at, grader_username, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.get("id", uuid4().hex),
                        item.get("assignment_id", ""),
                        item.get("student_username", ""),
                        json.dumps(item.get("answers", []), ensure_ascii=False),
                        item.get("submitted_at", now),
                        item.get("status", "submitted"),
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

        self._migrate_marker.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_marker.write_text(now, encoding="utf-8")

    def create_assignment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        assignment_id = uuid4().hex
        now = self._now()
        record = {
            "id": assignment_id,
            "title": payload.get("title", ""),
            "description": payload.get("description", ""),
            "assignment_type": self._normalize_assignment_type(payload.get("assignment_type", "subjective")),
            "class_name": payload.get("class_name", ""),
            "due_at": payload.get("due_at"),
            "allow_late": bool(payload.get("allow_late", False)),
            "total_score": round(float(payload.get("total_score", 100) or 100), 2),
            "rubric": payload.get("rubric", ""),
            "questions": payload.get("questions", []),
            "created_by": payload.get("created_by", ""),
            "created_at": now,
            "status": payload.get("status", "draft"),
        }
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT INTO homework_assignments
                (id, title, description, assignment_type, class_name, due_at, allow_late, total_score, rubric,
                 questions_json, created_by, created_at, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["title"],
                    record["description"],
                    record["assignment_type"],
                    record["class_name"],
                    record["due_at"],
                    1 if record["allow_late"] else 0,
                    record["total_score"],
                    record["rubric"],
                    json.dumps(record["questions"], ensure_ascii=False),
                    record["created_by"],
                    record["created_at"],
                    record["status"],
                    now,
                ),
            )
        return record

    def list_assignments(
        self,
        created_by: Optional[str] = None,
        status: Optional[str] = None,
        include_statuses: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, title, description, assignment_type, class_name, due_at, allow_late,
                   total_score, rubric,
                   questions_json, created_by, created_at, status
            FROM homework_assignments
        """
        clauses: list[str] = []
        params: list[Any] = []
        if created_by:
            clauses.append("created_by = ?")
            params.append(created_by)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if include_statuses:
            placeholders = ",".join(["?"] * len(include_statuses))
            clauses.append(f"status IN ({placeholders})")
            params.extend(include_statuses)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC"

        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"] or "",
                    "assignment_type": self._normalize_assignment_type(row["assignment_type"]),
                    "class_name": row["class_name"] or "",
                    "due_at": row["due_at"],
                    "allow_late": bool(row["allow_late"]),
                    "total_score": float(row["total_score"] or 100),
                    "rubric": row["rubric"] or "",
                    "questions": json.loads(row["questions_json"] or "[]"),
                    "created_by": row["created_by"],
                    "created_at": row["created_at"],
                    "status": row["status"] or "draft",
                }
            )
        return result

    def get_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, title, description, assignment_type, class_name, due_at, rubric,
                      allow_late, total_score, questions_json, created_by, created_at, status
                FROM homework_assignments
                WHERE id = ?
                """,
                (assignment_id,),
            ).fetchone()

        if not row:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"] or "",
            "assignment_type": self._normalize_assignment_type(row["assignment_type"]),
            "class_name": row["class_name"] or "",
            "due_at": row["due_at"],
            "allow_late": bool(row["allow_late"]),
            "total_score": float(row["total_score"] or 100),
            "rubric": row["rubric"] or "",
            "questions": json.loads(row["questions_json"] or "[]"),
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "status": row["status"] or "draft",
        }

    def update_assignment(self, assignment_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self.get_assignment(assignment_id)
        if not current:
            return None

        merged = {**current, **updates}
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                UPDATE homework_assignments
                SET title = ?, description = ?, assignment_type = ?, class_name = ?,
                    due_at = ?, allow_late = ?, total_score = ?, rubric = ?, questions_json = ?,
                    status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    merged.get("title", ""),
                    merged.get("description", ""),
                    self._normalize_assignment_type(merged.get("assignment_type", "subjective")),
                    merged.get("class_name", ""),
                    merged.get("due_at"),
                    1 if merged.get("allow_late") else 0,
                    round(float(merged.get("total_score", 100) or 100), 2),
                    merged.get("rubric", ""),
                    json.dumps(merged.get("questions", []), ensure_ascii=False),
                    merged.get("status", current.get("status", "draft")),
                    self._now(),
                    assignment_id,
                ),
            )

        return self.get_assignment(assignment_id)

    def create_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        submission_id = uuid4().hex
        now = self._now()
        record = {
            "id": submission_id,
            "assignment_id": payload.get("assignment_id", ""),
            "student_username": payload.get("student_username", ""),
            "answers": payload.get("answers", []),
            "submitted_at": now,
            "status": "submitted",
            "ai_score": None,
            "ai_feedback": "",
            "ai_rationale": "",
            "teacher_score": None,
            "teacher_comment": "",
            "graded_at": None,
            "grader_username": "",
        }

        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT INTO homework_submissions
                (id, assignment_id, student_username, answers_json, submitted_at, status,
                 ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                 graded_at, grader_username, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["assignment_id"],
                    record["student_username"],
                    json.dumps(record["answers"], ensure_ascii=False),
                    record["submitted_at"],
                    record["status"],
                    record["ai_score"],
                    record["ai_feedback"],
                    record["ai_rationale"],
                    record["teacher_score"],
                    record["teacher_comment"],
                    record["graded_at"],
                    record["grader_username"],
                    now,
                ),
            )
        return record

    def list_submissions(
        self,
        assignment_id: Optional[str] = None,
        student_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, assignment_id, student_username, answers_json, submitted_at,
                     status, ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                   graded_at, grader_username
            FROM homework_submissions
        """
        clauses: list[str] = []
        params: list[Any] = []
        if assignment_id:
            clauses.append("assignment_id = ?")
            params.append(assignment_id)
        if student_username:
            clauses.append("student_username = ?")
            params.append(student_username)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY submitted_at DESC"

        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "id": row["id"],
                    "assignment_id": row["assignment_id"],
                    "student_username": row["student_username"],
                    "answers": json.loads(row["answers_json"] or "[]"),
                    "submitted_at": row["submitted_at"],
                    "status": row["status"] or "submitted",
                    "ai_score": row["ai_score"],
                    "ai_feedback": row["ai_feedback"] or "",
                    "ai_rationale": row["ai_rationale"] or "",
                    "teacher_score": row["teacher_score"],
                    "teacher_comment": row["teacher_comment"] or "",
                    "graded_at": row["graded_at"],
                    "grader_username": row["grader_username"] or "",
                }
            )
        return result

    def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, assignment_id, student_username, answers_json, submitted_at,
                      status, ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                       graded_at, grader_username
                FROM homework_submissions
                WHERE id = ?
                """,
                (submission_id,),
            ).fetchone()

        if not row:
            return None
        return {
            "id": row["id"],
            "assignment_id": row["assignment_id"],
            "student_username": row["student_username"],
            "answers": json.loads(row["answers_json"] or "[]"),
            "submitted_at": row["submitted_at"],
            "status": row["status"] or "submitted",
            "ai_score": row["ai_score"],
            "ai_feedback": row["ai_feedback"] or "",
            "ai_rationale": row["ai_rationale"] or "",
            "teacher_score": row["teacher_score"],
            "teacher_comment": row["teacher_comment"] or "",
            "graded_at": row["graded_at"],
            "grader_username": row["grader_username"] or "",
        }

    def update_submission(self, submission_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self.get_submission(submission_id)
        if not current:
            return None

        merged = {**current, **updates}
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                UPDATE homework_submissions
                SET status = ?, ai_score = ?, ai_feedback = ?, ai_rationale = ?,
                    teacher_score = ?, teacher_comment = ?, graded_at = ?,
                    grader_username = ?, answers_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    merged.get("status", "submitted"),
                    merged.get("ai_score"),
                    merged.get("ai_feedback", ""),
                    merged.get("ai_rationale", ""),
                    merged.get("teacher_score"),
                    merged.get("teacher_comment", ""),
                    merged.get("graded_at"),
                    merged.get("grader_username", ""),
                    json.dumps(merged.get("answers", []), ensure_ascii=False),
                    self._now(),
                    submission_id,
                ),
            )

        return self.get_submission(submission_id)

    def get_latest_submission(self, assignment_id: str, student_username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, assignment_id, student_username, answers_json, submitted_at,
                       status, ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                       graded_at, grader_username
                FROM homework_submissions
                WHERE assignment_id = ? AND student_username = ?
                ORDER BY submitted_at DESC
                LIMIT 1
                """,
                (assignment_id, student_username),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "assignment_id": row["assignment_id"],
            "student_username": row["student_username"],
            "answers": json.loads(row["answers_json"] or "[]"),
            "submitted_at": row["submitted_at"],
            "status": row["status"] or "submitted",
            "ai_score": row["ai_score"],
            "ai_feedback": row["ai_feedback"] or "",
            "ai_rationale": row["ai_rationale"] or "",
            "teacher_score": row["teacher_score"],
            "teacher_comment": row["teacher_comment"] or "",
            "graded_at": row["graded_at"],
            "grader_username": row["grader_username"] or "",
        }

    def get_stats(self) -> Dict[str, int]:
        return self._count_records()
