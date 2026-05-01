from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4


class TeachingResearchRepository:
    def __init__(self, db_path: str | Path = "data/app.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

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
                CREATE TABLE IF NOT EXISTS teaching_research_records (
                    id TEXT PRIMARY KEY,
                    teacher_username TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    resource_link TEXT,
                    class_name TEXT,
                    course_id TEXT,
                    happened_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_teaching_research_records_teacher
                ON teaching_research_records(teacher_username, happened_at);
                """
            )

    def _now(self) -> str:
        return datetime.now().isoformat()

    def create_record(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = {
            "id": uuid4().hex,
            "teacher_username": str(payload.get("teacher_username") or "").strip(),
            "activity_type": str(payload.get("activity_type") or "").strip(),
            "title": str(payload.get("title") or "").strip(),
            "description": str(payload.get("description") or "").strip(),
            "resource_link": str(payload.get("resource_link") or "").strip(),
            "class_name": str(payload.get("class_name") or "").strip(),
            "course_id": str(payload.get("course_id") or "").strip(),
            "happened_at": str(payload.get("happened_at") or now),
            "created_at": now,
            "updated_at": now,
        }
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT INTO teaching_research_records
                (id, teacher_username, activity_type, title, description, resource_link, class_name, course_id, happened_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["teacher_username"],
                    record["activity_type"],
                    record["title"],
                    record["description"],
                    record["resource_link"],
                    record["class_name"],
                    record["course_id"],
                    record["happened_at"],
                    record["created_at"],
                    record["updated_at"],
                ),
            )
        return record

    def list_records(self, teacher_username: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, teacher_username, activity_type, title, description, resource_link, class_name, course_id, happened_at, created_at, updated_at
                FROM teaching_research_records
                WHERE teacher_username = ?
                ORDER BY happened_at DESC, created_at DESC
                """,
                (teacher_username,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_record(self, record_id: str) -> Dict[str, Any] | None:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, teacher_username, activity_type, title, description, resource_link, class_name, course_id, happened_at, created_at, updated_at
                FROM teaching_research_records
                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_record(self, record_id: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM teaching_research_records WHERE id = ?",
                (record_id,),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE teaching_research_records
                SET activity_type = ?,
                    title = ?,
                    description = ?,
                    resource_link = ?,
                    class_name = ?,
                    course_id = ?,
                    happened_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    str(payload.get("activity_type") or "").strip(),
                    str(payload.get("title") or "").strip(),
                    str(payload.get("description") or "").strip(),
                    str(payload.get("resource_link") or "").strip(),
                    str(payload.get("class_name") or "").strip(),
                    str(payload.get("course_id") or "").strip(),
                    str(payload.get("happened_at") or self._now()),
                    self._now(),
                    record_id,
                ),
            )
        return self.get_record(record_id)

    def delete_record(self, record_id: str) -> bool:
        with self._lock, self.connection() as conn:
            result = conn.execute("DELETE FROM teaching_research_records WHERE id = ?", (record_id,))
        return int(result.rowcount or 0) > 0
