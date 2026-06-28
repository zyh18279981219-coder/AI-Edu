from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from DatabaseModule.store import get_database_store


class TeachingResearchRepository:
    """MySQL repository for teaching research records."""

    def __init__(self) -> None:
        self.store = get_database_store()
        if os.getenv("DB_AUTO_MIGRATE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            self._initialize()

    def _initialize(self) -> None:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS teaching_research_records (
                        id VARCHAR(64) PRIMARY KEY,
                        teacher_username VARCHAR(100) NOT NULL,
                        activity_type VARCHAR(100) NOT NULL,
                        title VARCHAR(500) NOT NULL,
                        description TEXT,
                        resource_link VARCHAR(1000),
                        class_name VARCHAR(255),
                        course_id VARCHAR(100),
                        happened_at DATETIME NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_trr_teacher_time (teacher_username, happened_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO teaching_research_records
                    (id, teacher_username, activity_type, title, description, resource_link,
                     class_name, course_id, happened_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, teacher_username, activity_type, title, description, resource_link,
                           class_name, course_id, happened_at, created_at, updated_at
                    FROM teaching_research_records
                    WHERE teacher_username = %s
                    ORDER BY happened_at DESC, created_at DESC
                    """,
                    (teacher_username,),
                )
                return [dict(row) for row in cursor.fetchall()]

    def get_record(self, record_id: str) -> Dict[str, Any] | None:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, teacher_username, activity_type, title, description, resource_link,
                           class_name, course_id, happened_at, created_at, updated_at
                    FROM teaching_research_records
                    WHERE id = %s
                    """,
                    (record_id,),
                )
                row = cursor.fetchone()
        return dict(row) if row else None

    def update_record(self, record_id: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM teaching_research_records WHERE id = %s", (record_id,))
                if not cursor.fetchone():
                    return None
                cursor.execute(
                    """
                    UPDATE teaching_research_records
                    SET activity_type = %s,
                        title = %s,
                        description = %s,
                        resource_link = %s,
                        class_name = %s,
                        course_id = %s,
                        happened_at = %s,
                        updated_at = %s
                    WHERE id = %s
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
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM teaching_research_records WHERE id = %s", (record_id,))
                return int(cursor.rowcount or 0) > 0
